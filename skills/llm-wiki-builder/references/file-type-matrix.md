# File Type Matrix

## Categories

- `supported-and-parsed`: copy to `raw/`, attempt extraction to `analysis/ingest-src/`
- `copied-only`: preserve in `raw/`, do not claim stable parsing
- `manual-review-required`: record in `skipped_files` or `uncertain_items`

## Default v1 Matrix

| Extension | Behavior | Notes |
| --- | --- | --- |
| `.md` | supported-and-parsed | copied and mirrored into ingest layer |
| `.pdf` | supported-and-parsed | uses `markitdown` when available; otherwise manual review |
| `.docx` | supported-and-parsed | uses `markitdown` when available; otherwise manual review |
| `.pptx` | supported-and-parsed | uses `markitdown` when available; otherwise manual review |
| `.png` `.jpg` `.jpeg` `.webp` | copied-only | OCR only when explicitly enabled and backend exists |
| `.xlsx` `.xlsm` `.csv` `.tsv` | copied-only | preserve for later specialist parsing |
| `.zip` | manual-review-required | nested archive handling is not automatic in v1 |
| unknown | manual-review-required | must be listed, not silently ignored |

## Extraction Notes

- `markitdown` is the preferred extraction backend for v1.
- If extraction fails, downgrade the file to `manual-review-required`.
- Never present copied-only or manual-review-required files as parsed knowledge.
