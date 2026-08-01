#!/usr/bin/env python3
"""Generate hand-drawn cover illustration prompts or images via Gemini fallback API."""

from __future__ import annotations

import argparse
import base64
import io
import os
import re
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - runtime dependency message
    print("[ERROR] Missing dependency: requests. Install with: python3 -m pip install requests", file=sys.stderr)
    raise SystemExit(2)


ASPECT_RATIO_SUFFIX = {
    "1:1": "",
    "16:9": "-16-9",
    "9:16": "-9-16",
    "4:3": "-4-3",
    "3:4": "-3-4",
}

IMAGE_EXT_BY_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"RIFF", ".webp"),
)


@dataclass
class Config:
    api_key: str
    endpoint: str
    model: str
    fallback_model: str
    timeout: int
    max_retries: int


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = strip_inline_comment(value.strip()).strip('"').strip("'")
        os.environ.setdefault(key, value)


def strip_inline_comment(value: str) -> str:
    if not value:
        return value
    if value[0] in {"'", '"'}:
        return value
    if " #" in value:
        return value.split(" #", 1)[0].rstrip()
    return value


def load_local_env(extra_env_file: str | None = None) -> None:
    script_path = Path(__file__).resolve()
    candidates = []
    explicit_env = extra_env_file or os.getenv("COVER_ILLUSTRATION_ENV_FILE", "")
    if explicit_env:
        candidates.append(Path(explicit_env).expanduser())
    for parent in [Path.cwd(), *Path.cwd().parents, script_path.parent, *script_path.parents]:
        candidates.append(parent / ".env")

    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        load_dotenv_file(candidate)


def get_config(extra_env_file: str | None = None) -> Config:
    load_local_env(extra_env_file)
    return Config(
        api_key=os.getenv("GEMINI_API_KEY", ""),
        endpoint=os.getenv("GEMINI_PROXY_ENDPOINT", "").rstrip("/"),
        model=os.getenv("GEMINI_MODEL", "gemini-3-pro-image-preview"),
        fallback_model=os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash-image"),
        timeout=int(os.getenv("GEMINI_TIMEOUT", os.getenv("REQUEST_TIMEOUT", "120"))),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
    )


def strip_markdown(content: str, max_chars: int = 4000) -> str:
    content = re.sub(r"---\n[\s\S]*?\n---", "", content, count=1)
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
    content = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", content)
    content = re.sub(r"<[^>]+>", "", content)
    content = re.sub(r"\s+", " ", content).strip()
    return content[:max_chars]


def journal_context(content: str, max_sections: int = 16, per_section: int = 620) -> str:
    """Keep the opening plus bounded H2/H3 samples across the full journal."""
    content = re.sub(r"---\n[\s\S]*?\n---", "", content, count=1)
    content = re.sub(r"```[\s\S]*?```", "", content)
    content = re.sub(r"!\[.*?\]\(.*?\)", "", content)
    sections = re.split(r"(?=^#{2,3}\s+)", content, flags=re.MULTILINE)
    selected: list[str] = []
    for section in sections[: max_sections + 1]:
        cleaned = re.sub(r"\s+", " ", section).strip()
        if cleaned:
            selected.append(cleaned[:per_section])
    return "\n".join(selected)


def extract_title(content: str, fallback: str) -> str:
    title_match = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
    if title_match:
        return title_match.group(1).strip()
    fm_title = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", content, flags=re.MULTILINE)
    if fm_title:
        return fm_title.group(1).strip()
    return fallback


def compact_keywords(text: str, limit: int = 6) -> list[str]:
    candidates = re.findall(r"[\u4e00-\u9fffA-Za-z0-9][\u4e00-\u9fffA-Za-z0-9 +#./-]{1,24}", text)
    stop = {"title", "status", "created", "updated", "type", "tags", "aliases"}
    keywords: list[str] = []
    for item in candidates:
        cleaned = item.strip(" -_#.,，。:：;；")
        if not cleaned or cleaned.lower() in stop:
            continue
        if len(cleaned) > 18:
            cleaned = cleaned[:18]
        if cleaned not in keywords:
            keywords.append(cleaned)
        if len(keywords) >= limit:
            break
    return keywords


def extract_date(content: str) -> str:
    for pattern in (
        r"^created:\s*[\"']?(\d{4}-\d{2}-\d{2})",
        r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})",
        r"(\d{4})/(\d{2})/(\d{2})",
        r"(\d{4})-(\d{2})-(\d{2})",
    ):
        match = re.search(pattern, content, flags=re.MULTILINE)
        if not match:
            continue
        if len(match.groups()) == 1:
            return match.group(1)
        return "-".join(match.groups())
    return ""


def journal_main_title(title: str, source_date: str) -> str:
    dated_heading = re.search(r"([\u4e00-\u9fff]{0,4}日志@\d{4}/\d{2}/\d{2})", title)
    if dated_heading:
        return dated_heading.group(1)
    if source_date:
        return f"{source_date} 日志"
    return short_title(title, 24)


def resolve_layout_profile(mode: str, layout_profile: str) -> str:
    if layout_profile != "auto":
        return layout_profile
    return "journal-memory-map" if mode == "journal-cover" else "minimal-editorial"


def build_prompt(
    source: str,
    title: str,
    mode: str,
    aspect_ratio: str,
    style: str,
    layout_profile: str = "auto",
) -> str:
    profile = resolve_layout_profile(mode, layout_profile)
    summary = strip_markdown(source)
    keywords = compact_keywords(summary, limit=10)
    keyword_text = "、".join(keywords[:4]) if keywords else "主题、结构、洞察"
    chinese_hint = "Chinese text only" if re.search(r"[\u4e00-\u9fff]", source) else "Use the source language for any labels"

    if profile == "journal-memory-map":
        source_date = extract_date(source)
        map_title = journal_main_title(title, source_date)
        context = journal_context(source)
        return f"""Create a hand-drawn journal memory-map infographic. Landscape {aspect_ratio} aspect ratio.

Purpose:
- Let the reader reconstruct the day at a glance.
- This is a rich daily memory map, not a minimalist editorial cover.

Exact source date: "{source_date or 'preserve the source date exactly'}"
Main title: "{map_title}"

Source-grounded journal context:
{context}

Composition:
- First infer one central narrative and one concrete central scene.
- Build 5-8 visible event clusters covering the major time blocks or top-level threads.
- Use a bottom strip for the chronological or emotional arc.
- Preserve work, family, health, learning, and personal-life balance when present.
- Prefer source-specific documents, devices, activities, repairs, meals, exercise, places, and workflows over generic gears or lightbulbs.

Text and style:
- {chinese_hint}; preserve unavoidable product and technical names.
- Keep the exact date, title, cluster headings, names, and critical numbers readable and correctly spelled.
- Pure hand-drawn cartoon infographic, warm, personal, vivid, and memory-friendly.
- Information-rich but legible through grouped panels, clear hierarchy, and restrained colors.
- No photorealism, 3D, glossy UI, dark cinematic scene, watermark, bananas, or monkeys.
- Avoid unnecessary official logos or misleading endorsements, while retaining faithful real-world cues.

Do not invent events or copy text from another day. Do not collapse this into a generic workbench with only a few keywords."""

    return f"""Create a hand-drawn cartoon-style infographic illustration for a Markdown article or briefing. Landscape {aspect_ratio} aspect ratio.

Core title:
{title}

Core idea and source context:
{summary}

Visual requirements:
- Hand-drawn cartoon infographic, not realistic.
- {chinese_hint}, concise keywords, hand-lettered look.
- Minimal icons and clean clusters.
- Ample whitespace.
- Avoid watermarks, photorealism, 3D, glossy effects, monkeys, bananas, and clutter.
- Avoid unnecessary official logos or misleading endorsements, but preserve vivid real-world cues when they improve the illustration.

Main title text: "{short_title(title)}"
Secondary keywords: "{keyword_text}"

Create a polished image that can work as a memorable cover illustration."""


def short_title(title: str, max_chars: int = 16) -> str:
    title = re.sub(r"^[^\w\u4e00-\u9fff]+", "", title).strip()
    return title[:max_chars] if len(title) > max_chars else title


def call_api(prompt: str, config: Config, aspect_ratio: str) -> dict:
    suffix = ASPECT_RATIO_SUFFIX.get(aspect_ratio)
    if suffix is None:
        raise ValueError(f"Unsupported aspect ratio: {aspect_ratio}")
    model_name = f"{config.model}{suffix}"
    url = f"{config.endpoint}/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {config.api_key}"}
    payload = {"model": model_name, "messages": [{"role": "user", "content": prompt}]}

    last_error = None
    for attempt in range(config.max_retries):
        attempt_number = attempt + 1
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=config.timeout)
            if response.status_code == 200:
                return response.json()
            last_error = f"HTTP {response.status_code}: {response.text[:300]}"
            if 400 <= response.status_code < 500 and response.status_code != 429:
                raise RuntimeError(f"Non-retryable Gemini API error: {last_error}")
        except requests.exceptions.Timeout:
            last_error = "request timeout"
        except RuntimeError:
            raise
        except Exception as exc:  # pragma: no cover - runtime diagnostics
            last_error = str(exc)
        if attempt < config.max_retries - 1:
            print(
                f"[WARN] Gemini proxy attempt {attempt_number}/{config.max_retries} failed: {last_error}; retrying identical prompt",
                file=sys.stderr,
            )
            time.sleep(2**attempt)
    raise RuntimeError(f"Gemini API call failed: {last_error}")


def call_native_gemini(prompt: str, config: Config, aspect_ratio: str) -> bytes:
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"google-genai not available: {exc}") from exc

    client = genai.Client(api_key=config.api_key)
    models = [config.model, config.model, config.fallback_model]
    last_error = None
    for attempt in range(config.max_retries):
        attempt_number = attempt + 1
        model = models[min(attempt, len(models) - 1)]
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
            return extract_native_image_bytes(response)
        except Exception as exc:
            last_error = str(exc)
            if attempt < config.max_retries - 1:
                print(
                    f"[WARN] Native Gemini attempt {attempt_number}/{config.max_retries} with {model} failed: {last_error}; retrying identical prompt",
                    file=sys.stderr,
                )
                time.sleep(2**attempt)
    raise RuntimeError(f"Native Gemini API call failed: {last_error}")


def extract_native_image_bytes(response: object) -> bytes:
    candidates = getattr(response, "candidates", [])
    for cand in candidates:
        content = getattr(cand, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", []):
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                data = inline.data
                if isinstance(data, bytes):
                    return data
                if isinstance(data, str):
                    return base64.b64decode(data)
    raise RuntimeError("Gemini response missing image bytes")


def extract_image_bytes(response: dict) -> bytes:
    choices = response.get("choices") or []
    if not choices:
        raise RuntimeError("API response has no choices")
    content = choices[0].get("message", {}).get("content", "")
    match = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=\n\r]+)", str(content))
    if not match:
        raise RuntimeError("API response has no base64 image data")
    return base64.b64decode(re.sub(r"\s+", "", match.group(1)))


def detect_ext(data: bytes) -> str:
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    for magic, ext in IMAGE_EXT_BY_MAGIC:
        if data.startswith(magic):
            return ext
    return ".jpg"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "cover-illustration"


def resolve_output(args: argparse.Namespace, title: str, data: bytes) -> Path:
    ext = detect_ext(data)
    if args.output:
        output = Path(args.output)
        if not output.suffix:
            output = output.with_suffix(ext)
        return output
    output_dir = Path(args.output_dir or ".")
    return output_dir / f"{slugify(title)[:80]}{ext}"


def normalize_image_for_output(data: bytes, output: Path) -> bytes:
    """Make the encoded MIME agree with an explicitly requested file suffix."""
    detected = detect_ext(data)
    requested = output.suffix.lower()
    if requested in {".jpeg", ".jpg"}:
        requested = ".jpg"
    if not requested or requested == detected:
        return data
    formats = {".png": "PNG", ".jpg": "JPEG", ".webp": "WEBP"}
    target_format = formats.get(requested)
    if not target_format:
        raise ValueError(f"Unsupported output image suffix: {output.suffix}")
    try:
        from PIL import Image  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            f"Pillow is required to convert Gemini {detected} bytes to {requested}"
        ) from exc
    with Image.open(io.BytesIO(data)) as image:
        converted = io.BytesIO()
        if target_format == "JPEG" and image.mode not in {"RGB", "L"}:
            image = image.convert("RGB")
        image.save(converted, format=target_format)
        return converted.getvalue()


def read_source(args: argparse.Namespace) -> tuple[str, str]:
    if args.input_md:
        path = Path(args.input_md)
        content = path.read_text(encoding="utf-8")
        return content, args.title or extract_title(content, path.stem)
    if args.input_text:
        return args.input_text, args.title or short_title(args.input_text, 24)
    raise ValueError("Provide --input-md or --input-text")


def print_status(extra_env_file: str | None = None) -> int:
    config = get_config(extra_env_file)
    endpoint_online = is_endpoint_online(config.endpoint) if config.endpoint else False
    backend = choose_backend(config)
    print("=" * 50)
    print("create-cover-illustration fallback status")
    print("=" * 50)
    print(f"[Gemini API] {'[OK] Ready' if bool(config.api_key) else '[X] Not configured'}")
    print(f"  - Backend: {backend}")
    print(f"  - Proxy endpoint: {config.endpoint or '<not configured>'}")
    print(f"  - Proxy health: {'[OK] Online' if endpoint_online else '[X] Offline'}")
    print(f"  - Model: {config.model}")
    print(f"  - Fallback model: {config.fallback_model}")
    print(f"  - Timeout: {config.timeout}s")
    print(f"  - Max retries: {config.max_retries}")
    print("=" * 50)
    return 0 if config.api_key and backend in {"native", "proxy"} else 1


def choose_backend(config: Config) -> str:
    if config.endpoint and is_endpoint_online(config.endpoint):
        return "proxy"
    return "native" if config.api_key else "unavailable"


def is_endpoint_online(endpoint: str, timeout: float = 1.0) -> bool:
    match = re.match(r"^https?://([^/:]+)(?::(\d+))?", endpoint)
    if not match:
        return False
    host = match.group(1)
    port = int(match.group(2) or (443 if endpoint.startswith("https://") else 80))
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate cover illustration prompts or images.")
    parser.add_argument("--input-md", help="Markdown source file")
    parser.add_argument("--input-text", help="Inline source text")
    parser.add_argument("--title", help="Override title text used in the prompt")
    parser.add_argument("--mode", choices=["journal-cover", "writing-illustration", "prompt-only"], default="writing-illustration")
    parser.add_argument(
        "--layout-profile",
        choices=["auto", "journal-memory-map", "minimal-editorial"],
        default="auto",
        help="Visual content profile; auto selects memory-map for journals and minimal-editorial otherwise",
    )
    parser.add_argument("--aspect-ratio", default="16:9", choices=sorted(ASPECT_RATIO_SUFFIX))
    parser.add_argument("--style", default="handdrawn-cartoon")
    parser.add_argument("--env-file", help="Optional .env path for Gemini fallback configuration")
    parser.add_argument("--output", help="Output image path")
    parser.add_argument("--output-dir", help="Output directory when --output is omitted")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt only")
    parser.add_argument("--status", action="store_true", help="Show fallback API configuration status")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.status:
        return print_status(args.env_file)

    try:
        source, title = read_source(args)
        prompt = build_prompt(
            source,
            title,
            args.mode,
            args.aspect_ratio,
            args.style,
            args.layout_profile,
        )
        if args.dry_run or args.mode == "prompt-only":
            print(prompt)
            return 0

        config = get_config(args.env_file)
        if not config.api_key:
            print("[ERROR] GEMINI_API_KEY is not configured.", file=sys.stderr)
            return 2

        if choose_backend(config) == "proxy":
            response = call_api(prompt, config, args.aspect_ratio)
            data = extract_image_bytes(response)
        else:
            data = call_native_gemini(prompt, config, args.aspect_ratio)
        output = resolve_output(args, title, data)
        data = normalize_image_for_output(data, output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        print(f"[OK] Saved image: {output} ({len(data)} bytes)")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
