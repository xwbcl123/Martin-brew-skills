#!/usr/bin/env python3
"""
Outlook font safety for HTML email bodies (check + fix).

Why: Outlook desktop renders HTML mail with the Word engine. It does not walk a
CSS font-family fallback chain when the first font is missing, it needs the East
Asian font declared separately (mso-fareast-font-family), and it often drops
<style>/outer-container styles before they reach table cells. Chinese text then
falls back to SimSun and Latin text to Times New Roman.

Rule (Martin 2026-10-09): every text-bearing element carries an inline
font-family whose FIRST font is Microsoft YaHei; <head> carries an
<!--[if mso]> block with mso-fareast-font-family: Microsoft YaHei; no web fonts.

Scope: email BODY HTML only. The visual-mail 1080px Tailwind brief that is
screenshotted is not an email body and is out of scope.

Usage:
  python3 outlook_email_fonts.py check <email.html> [...]
  python3 outlook_email_fonts.py fix <in.html> <out.html>

This file exists in both visual-mail/scripts and monthly-report-workflow/scripts.
Keep the two copies identical (test_outlook_email_fonts.py checks this).
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

FONT_STACK = "'Microsoft YaHei','微软雅黑',Arial,'PingFang SC',sans-serif"
INLINE_FONT = f"font-family:{FONT_STACK}; mso-fareast-font-family:'Microsoft YaHei';"

MSO_BLOCK = """<!--[if mso]>
<style type="text/css">
  body, table, td, th, p, span, a, li, div, h1, h2, h3, h4, h5, h6, strong, b, em {
    font-family: "Microsoft YaHei", Arial, sans-serif !important;
    mso-fareast-font-family: "Microsoft YaHei";
  }
</style>
<![endif]-->"""

# Elements whose direct text must be covered by their own inline font-family.
TEXT_TAGS = {"td", "th", "p", "span", "a", "li", "div",
             "h1", "h2", "h3", "h4", "h5", "h6"}
# Elements the fixer also stamps (inline formatting + containers), harmless and
# more robust in Word.
FIX_TAGS = TEXT_TAGS | {"body", "table", "strong", "b", "em", "i", "u", "font"}
SKIP_TEXT_IN = {"head", "title", "style", "script"}
VOID_TAGS = {"br", "img", "hr", "meta", "link", "input", "col", "area", "base", "wbr", "source"}

YAHEI_FIRST = re.compile(r"^\s*[\"']?(Microsoft YaHei|微软雅黑)[\"']?\s*(,|$)", re.I)
MSO_RE = re.compile(r"<!--\[if mso\]>(.*?)<!\[endif\]-->", re.I | re.S)
WEB_FONT_PATTERNS = [
    (re.compile(r"@font-face", re.I), "@font-face rule"),
    (re.compile(r"@import", re.I), "@import (external CSS / font)"),
    (re.compile(r"fonts\.googleapis\.com|fonts\.gstatic\.com|use\.typekit\.net|fonts\.bunny\.net", re.I), "web font CDN URL"),
    (re.compile(r"<link\b[^>]*(font|googleapis)[^>]*>", re.I), "<link> font stylesheet"),
    (re.compile(r"font-family\s*:[^;\"]*\b(Inter|Spline Sans|Roboto|Open Sans|Lato|Montserrat|Noto Sans SC)\b", re.I),
     "web font family in font-family"),
]


def _font_family(style: str | None) -> str | None:
    if not style:
        return None
    m = re.search(r"(?:^|;)\s*font-family\s*:\s*([^;]+)", style, re.I)
    return m.group(1).strip() if m else None


class _Walker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[dict] = []
        self.bad: dict[int, dict] = {}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in VOID_TAGS:
            return
        style = dict(attrs).get("style")
        self.stack.append({"tag": tag, "style": style, "line": self.getpos()[0], "id": len(self.bad) + len(self.stack) * 100000 + self.getpos()[0] * 10 + self.getpos()[1]})

    def handle_startendtag(self, tag, attrs):
        return

    def handle_endtag(self, tag):
        tag = tag.lower()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if not data.strip():
            return
        if any(e["tag"] in SKIP_TEXT_IN for e in self.stack):
            return
        owner = next((e for e in reversed(self.stack) if e["tag"] in TEXT_TAGS), None)
        if owner is None:
            owner = self.stack[-1] if self.stack else {"tag": "(root)", "style": None, "line": self.getpos()[0], "id": -1}
        ff = _font_family(owner["style"]) if owner["tag"] in TEXT_TAGS else None
        if ff is None or not YAHEI_FIRST.match(ff):
            self.bad.setdefault(owner["id"], {"tag": owner["tag"], "line": owner["line"],
                                              "font": ff, "text": data.strip()[:30]})


def check_html(content: str) -> list[tuple[int, str]]:
    """Return a list of (line, message). Empty list means Outlook-font safe."""
    issues: list[tuple[int, str]] = []
    blocks = MSO_RE.findall(content)
    if not any(re.search(r"mso-fareast-font-family\s*:\s*[\"']?Microsoft YaHei", b, re.I) for b in blocks):
        issues.append((1, "Missing <!--[if mso]> block declaring mso-fareast-font-family: \"Microsoft YaHei\" in <head>"))
    for pat, label in WEB_FONT_PATTERNS:
        m = pat.search(content)
        if m:
            issues.append((content[:m.start()].count("\n") + 1, f"Web font not allowed in email HTML: {label} ({m.group(0)[:50]})"))
    w = _Walker()
    w.feed(content)
    w.close()
    for b in sorted(w.bad.values(), key=lambda x: x["line"]):
        why = "no inline font-family" if b["font"] is None else f"font-family starts with {b['font'].split(',')[0].strip()}"
        issues.append((b["line"], f"<{b['tag']}> text without Microsoft YaHei first ({why}): {b['text']}"))
    return issues


_TAG_RE = re.compile(r"<(" + "|".join(sorted(FIX_TAGS, key=len, reverse=True)) + r")\b([^>]*)>", re.I)


def _stamp(match: re.Match) -> str:
    tag, attrs = match.group(1), match.group(2)
    sm = re.search(r"\sstyle\s*=\s*\"([^\"]*)\"", attrs, re.I)
    if sm:
        decls = [d.strip() for d in sm.group(1).split(";") if d.strip()]
        decls = [d for d in decls if not re.match(r"(font-family|mso-fareast-font-family)\s*:", d, re.I)]
        new_style = INLINE_FONT + (" " + "; ".join(decls) + ";" if decls else "")
        attrs = attrs[:sm.start()] + f' style="{new_style}"' + attrs[sm.end():]
    else:
        selfclose = attrs.endswith("/")
        core = attrs[:-1] if selfclose else attrs
        attrs = f'{core} style="{INLINE_FONT}"' + ("/" if selfclose else "")
    return f"<{tag}{attrs}>"


def fix_html(content: str) -> str:
    """Stamp the YaHei stack on every text/container tag and add the mso block.
    Only tag attributes and <head> change; visible text is untouched."""
    head_end = content.lower().find("</head>")
    body = content if head_end < 0 else content[head_end:]
    prefix = "" if head_end < 0 else content[:head_end]
    body = _TAG_RE.sub(_stamp, body)
    if not any("mso-fareast-font-family" in b for b in MSO_RE.findall(prefix)):
        if head_end >= 0:
            prefix = prefix.rstrip("\n") + "\n" + MSO_BLOCK + "\n"
        else:
            prefix = "<head>\n" + MSO_BLOCK + "\n</head>\n"
    return prefix + body


def visible_text(content: str) -> str:
    class T(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.out, self.skip = [], 0
        def handle_starttag(self, tag, attrs):
            if tag in SKIP_TEXT_IN:
                self.skip += 1
        def handle_endtag(self, tag):
            if tag in SKIP_TEXT_IN:
                self.skip -= 1
        def handle_data(self, d):
            if not self.skip:
                self.out.append(d)
    t = T()
    t.feed(MSO_RE.sub("", content))
    return re.sub(r"\s+", " ", "".join(t.out)).strip()


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "check":
        rc = 0
        for p in argv[1:]:
            issues = check_html(Path(p).read_text(encoding="utf-8"))
            print(f"{p}: {'PASS' if not issues else f'FAIL ({len(issues)} issues)'}")
            for line, msg in issues[:40]:
                print(f"  line {line}: {msg}")
            if len(issues) > 40:
                print(f"  ... {len(issues) - 40} more")
            rc |= 1 if issues else 0
        return rc
    if len(argv) == 3 and argv[0] == "fix":
        src = Path(argv[1]).read_text(encoding="utf-8")
        out = fix_html(src)
        if visible_text(src) != visible_text(out):
            print("ERROR: visible text changed; aborting", file=sys.stderr)
            return 2
        Path(argv[2]).write_text(out, encoding="utf-8")
        issues = check_html(out)
        print(f"wrote {argv[2]}; remaining issues: {len(issues)}")
        for line, msg in issues:
            print(f"  line {line}: {msg}")
        return 1 if issues else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
