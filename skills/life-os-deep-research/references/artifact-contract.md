# Artifact And Delivery Contract

## Package

```text
50-59_Knowledge-Writing/51.15_deep-research-reports-lib/YYYY/YYYYMMDD_<slug>/
├── YYYYMMDD_<slug>_deep-research.md
├── YYYYMMDD_<slug>_deep-research.pdf
├── YYYYMMDD_<slug>_manifest.json
├── sources.jsonl
├── YYYYMMDD_<slug>_viz-brief.html  # only with #html or #publish
├── publish-manifest.json          # only after first #publish
└── assets/
```

An internal Kami staging HTML may remain for reproducibility. It is not the
public-capable `viz-brief.html` and must not be advertised as a published page.

## Markdown gate

Require title/question/scope/date, Executive Summary, Key Findings, evidence
analysis, counter-evidence and uncertainty, implications, methodology, and
working references. Reject placeholders, fabricated claims, broken source IDs,
and unlabeled estimates.

## PDF gate

Use `brand-guidelines` then `kami` Long Doc. For the default Life route:

- keep Kami's warm parchment canvas and warm neutrals;
- use the Martin identity as a restrained lockup;
- avoid repeated or unexplained large ivory panels;
- render more than one page for substantive reports;
- verify A4 geometry, page count, fonts, no blank pages, no clipping, no
  Markdown residue, and representative cover/body/table/reference pages;
- treat visual QA as independent from HTML/source validation.

## Delivery gate

The manifest records task/session, evidence cut-off, worker roles, source
counts, publishing state, file list, validation results, and SHA-256 hashes.
Attach the PDF only after the package validator succeeds. `#html` requires a
separate responsive visual-artifact validation. `#publish` additionally
requires an immutable R2 publication record and verified public readback.
