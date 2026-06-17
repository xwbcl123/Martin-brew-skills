# NotebookLM Deck Run Package

Use this scaffold for every NotebookLM deck run:

```text
notebooklm-output/<YYYYMMDD_slug>/
├── README.md
├── source_index.md
├── handover.md
├── input/
│   └── deck-outline.md              # normalized with references/deck-outline-template.md when needed
├── design/
│   └── <theme>-design.md            # normalized with references/design-template.md when needed
├── prompt/
│   └── generate_slide_deck_prompt.md
├── notebook/
│   ├── notebook_manifest.json
│   └── artifact_manifest.json
├── deck/
│   └── <run>_<deck>.pptx
└── qa/
    ├── <run>_<deck>.pdf
    ├── lo-export/
    ├── rendered/
    └── qc_report.md
```

## Minimal Manifest Fields

`notebook_manifest.json`:

```json
{
  "notebook": {"id": "...", "title": "..."},
  "sources": [
    {"index": 1, "id": "...", "title": "...", "type": "markdown", "status": "ready"}
  ],
  "source_gate": "pass"
}
```

`artifact_manifest.json`:

```json
{
  "notebook": {"id": "...", "title": "..."},
  "artifact": {"id": "...", "title": "...", "type": "Slide Deck", "status": "completed"},
  "downloads": {"pptx": "deck/...", "pdf": "qa/...", "libreoffice_pdf": "qa/lo-export/..."},
  "qa_summary": {
    "pptx_zip_test": "pass",
    "downloaded_pdf_pages": 15,
    "libreoffice_pdf_pages": 15,
    "slides": 15,
    "pptx_text_nodes": 0,
    "pptx_picture_nodes": 15,
    "editability": "fail_for_formal_editable_pptx",
    "route_label": "NotebookLM visual alternate / image-baked PPTX"
  }
}
```

## Prompt Skeleton

```markdown
# NotebookLM Slide Deck Generation Prompt

Generate an English executive slide deck titled:

**<title>**

Use the imported `<deck-outline.md>` as the content and narrative source of truth.

## Required Content Behavior

- Follow the deck-outline slide order and narrative spine.
- Use research reports only as evidence backing and factual grounding.
- Do not replace the outline with a generic structure.
- Keep the deck concise and executive-ready.
- Include compact evidence markers or short source labels where helpful.
- Include a final References / Evidence slide if possible.

## Required Style Behavior

Use `<design.md>` as the visual style source.

- Output language: `<language>`.
- Follow the specified palette, typography, slide archetypes, and negative rules.
- Keep text readable for the target audience.

## Factual Safety

- Do not invent facts, dates, institutions, model names, regulatory milestones, or quotes.
- Label uncertain or planned claims as planned / reported / draft.
```
