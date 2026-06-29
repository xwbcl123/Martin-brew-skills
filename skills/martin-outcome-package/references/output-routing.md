# Output Routing

## deliverable_home Resolution

The `deliverable_home` is the root directory where all package deliverables are written. Resolution order:

1. **User-specified path**: If the user provides an explicit output directory, use it.
2. **Project/Area folder**: If the source material maps to a known project or area, use its deliverables folder.
3. **Session-local fallback**: Create a `deliverables/` subfolder in the current working directory or session folder.

When the session-local fallback is used, set `needs_archive_destination: true` in the package README to signal that outputs should be moved to a permanent location.

For project-matched work, verify the final `deliverable_home` exists or can be created before D1 production. Session-local output is staging/cache only unless the user explicitly wants the final package there.

## Folder Structure

Under `deliverable_home`:

```
{deliverable_home}/
├── README.md                      # Package metadata (from template)
├── d1-deep-report.md             # D1
├── d2-executive-summary.md       # D2
├── d3-visual-briefing/           # D3 (if produced)
│   ├── briefing.html
│   └── assets/
├── d4-deck-outline-brief.md      # D4 (if produced)
├── d5-design/                    # D5 (if produced)
│   ├── design.md
│   ├── design-stack.md
│   └── martin-pptx-handoff.md
└── d6-email-package.md           # D6 (if produced)
```

## Naming Convention

- Use lowercase with hyphens for filenames.
- Prefix with deliverable ID (`d1-`, `d2-`, etc.) for sorting.
- Sub-deliverables (D3 assets, D5 design files) go in their own subfolder.

## Metadata Capture

The package README must record:
- `deliverable_home` (resolved path)
- `needs_archive_destination` (boolean)
- Which deliverables were actually produced
- Timestamp of completion
- Gate/route status when D4-D6 or delegated deck routes are produced
- Whether any external/Cloud Expert package was verified as tool-accessible
