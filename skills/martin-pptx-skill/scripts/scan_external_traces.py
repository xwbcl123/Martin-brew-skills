#!/usr/bin/env python3
"""Scan a deck (PPTX and/or PDF) for internal traces before it leaves the team.

Checks every text-bearing part, not just visible slide text:
  - slide text, tables, speaker notes, chart titles (all PPTX XML parts)
  - image descriptions (descr/title attributes) and docProps (core.xml, app.xml)
  - PDF text layer and PDF metadata (via pdftotext / pdfinfo when available)

Default deny patterns cover workspace words, absolute paths, git/commit traces, hash-like
tokens in visible text, and known template leftovers. Add project terms with --deny or
--deny-file (one regex per line, '#' comments). --zh-style also flags corner quotes and
em/en dashes in Chinese decks.

Usage:
  python3 scan_external_traces.py deck.pptx [deck.pdf] [--deny REGEX ...] [--deny-file FILE] [--zh-style]
Exit code 0 = clean, 1 = findings, 2 = usage/IO error. A clean result is heuristic, not proof.
"""
import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

DEFAULT_DENY = [
    r"\bvault\b", r"\bobsidian\b", r"\bInbox\b", r"tasks/sessions", r"\.agents/skills",
    r"/Users/[^\s<\"']+", r"[A-Za-z]:\\\\Users\\\\", r"~/[A-Za-z]",
    r"\bcommit\b", r"\bgit\b",
    r"Walnut Exporter",
]
ZH_STYLE = [r"[「」]", r"——", r"—", r"–"]
TEXT_TAGS = re.compile(r"<a:t>([^<]*)</a:t>|<c:v>([^<]*)</c:v>|<t>([^<]*)</t>")
ATTR = re.compile(r'\b(?:descr|title)="([^"]*)"')
HASHLIKE = re.compile(r"\b[0-9a-f]{7,40}\b")


def texts_from_pptx(path):
    out = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".xml"):
                continue
            s = z.read(name).decode("utf-8", "ignore")
            if name.startswith("docProps/"):
                out.append((name, re.sub(r"<[^>]+>", " ", s)))
                continue
            vis = " ".join(next(g for g in m.groups() if g is not None) for m in TEXT_TAGS.finditer(s))
            if vis.strip():
                out.append((name, vis))
            attrs = " ".join(m.group(1) for m in ATTR.finditer(s))
            if attrs.strip():
                out.append((name + "#attrs", attrs))
    return out


def texts_from_pdf(path):
    out = []
    for tool, args in (("pdftotext", [str(path), "-"]), ("pdfinfo", [str(path)])):
        if shutil.which(tool):
            r = subprocess.run([tool] + args, capture_output=True, text=True)
            out.append((f"{path.name}:{tool}", r.stdout))
        else:
            print(f"warning: {tool} not found; PDF {tool} layer not scanned", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--deny", action="append", default=[])
    ap.add_argument("--deny-file")
    ap.add_argument("--zh-style", action="store_true")
    a = ap.parse_args()
    pats = DEFAULT_DENY + a.deny
    if a.deny_file:
        pats += [l.strip() for l in Path(a.deny_file).read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.lstrip().startswith("#")]
    if a.zh_style:
        pats += ZH_STYLE
    rx = re.compile("|".join(f"(?:{p})" for p in pats), re.IGNORECASE)
    findings = 0
    for f in a.files:
        p = Path(f)
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr)
            return 2
        parts = texts_from_pptx(p) if p.suffix.lower() == ".pptx" else texts_from_pdf(p)
        for name, text in parts:
            hits = [m.group(0) for m in rx.finditer(text)]
            if "docProps" not in name and not name.endswith("pdfinfo"):
                hits += [h for h in HASHLIKE.findall(text) if not h.isdigit() and re.search(r"[a-f]", h)]
            for h in sorted(set(hits)):
                i = text.find(h)
                ctx = text[max(0, i - 40): i + len(h) + 40].replace("\n", " ")
                print(f"{p.name} | {name} | {h!r} | …{ctx}…")
                findings += 1
    print(f"{findings} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
