#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pptx", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    pdf_dir = args.out
    log_path = args.out / "render_log.txt"
    soffice = shutil.which("libreoffice") or shutil.which("soffice")
    if not soffice:
        log_path.write_text("LibreOffice/soffice not found\n", encoding="utf-8")
        print("render failed: libreoffice missing")
        return 1

    cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(pdf_dir), str(args.pptx)]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    log_path.write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        print("render failed: libreoffice export")
        return proc.returncode

    pdf_path = pdf_dir / f"{args.pptx.stem}.pdf"
    canonical_pdf = pdf_dir / "deck.pdf"
    if pdf_path.exists() and pdf_path != canonical_pdf:
        shutil.copy2(pdf_path, canonical_pdf)

    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm and canonical_pdf.exists():
        png_dir = args.out / "png"
        png_dir.mkdir(exist_ok=True)
        proc2 = subprocess.run(
            [pdftoppm, "-png", "-r", "144", str(canonical_pdf), str(png_dir / "slide")],
            text=True,
            capture_output=True,
        )
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("\n[pdftoppm]\n")
            fh.write(proc2.stdout + "\n" + proc2.stderr)
        if proc2.returncode != 0:
            print("render warning: pdf to png failed")
            return proc2.returncode

    print(f"rendered {canonical_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
