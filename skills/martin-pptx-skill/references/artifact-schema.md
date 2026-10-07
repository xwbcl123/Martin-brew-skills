# Image composer manifest v2

This schema is the existing image/two-layer composer input, not the deck-wide Visual Contract. New/material production uses [Visual Contract v1](verification.md) for plan/assets/final checks. Generate this composer input from the same accepted sources when needed; do not replace or silently reinterpret its v2 fields. Native builders need only the Visual Contract plus host inputs.

One UTF-8 JSON manifest is enough. Content, design and QC can be sections of it; no duplicate outline/spec is required. Paths resolve relative to the manifest. Keep source hashes immutable. Example shape:

```json
{
  "schema_version": 2,
  "route": "text-editable",
  "slide_size": {"width": 1280, "height": 720},
  "design": {"template": "selected contract", "fonts": ["Arial"]},
  "slides": [{
    "id": "slide-01",
    "source": "source/slide-01.png",
    "source_sha256": "64 hex characters",
    "source_size": {"width": 1600, "height": 900},
    "background": "background/slide-01.png",
    "background_sha256": "64 hex characters",
    "background_origin": "image-edit",
    "generation": {"tool": "actual tool name", "input_sha256": "source hash", "generated_source": "actual result path", "prompt": "prompts/slide-01.md"},
    "exceptions": [{"text": "F", "reason": "fictional logo artwork remains baked"}],
    "texts": [{"id": "title", "text": "标题", "bbox": [90,70,1000,90], "font_px": 54, "font_family": "Arial", "color": "#132A40", "bold": true, "align": "left", "confidence": 1}],
    "notes": "Source citation or synthetic test label",
    "qa": {"background_review": "pass", "background_review_note": "No residual ordinary text; chart and logo inspected", "visual_review": "pending", "visual_review_note": ""}
  }]
}
```

`image-deck` uses `source`, `source_sha256`, `source_size`, `generation` for newly generated pages and empty `texts`; no background needed. `provided-textless` backgrounds require source inspection notes and skip generation metadata. `image-edit` requires the exact input hash and prompt file. All ordinary text must occur once in the native layer. Bbox and source dimensions are positive finite numbers; out-of-page boxes, aspect distortion, empty text and duplicate IDs fail. Template governs styles. The composer records new output and preview hashes separately in `composition.json` rather than overwriting source truth.

QA values: `pending`, `pass`, `fail`; scripts cannot infer semantic visual pass. All applicable reviews must pass before final acceptance. `native` uses host-native object manifests rather than the image-specific composer.
