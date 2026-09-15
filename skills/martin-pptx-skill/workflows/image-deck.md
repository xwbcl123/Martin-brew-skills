# Image-generated deck

Use when the user selects baked/image-generated slides. Image generation must actually run; deterministic cards, chart renders or HTML screenshots do not prove this route.

1. Define per-slide content and brand/template tokens in the shared manifest. Keep all required text/numbers verbatim in self-contained page prompts. Let the evidence and audience set density; there is no minimum of 20 facts, mandatory cover, complex framework or default no-logo rule.
2. Use the current host raster image generator. For a reference edit, inspect and pass the actual source image through the tool's supported image argument. A prompt containing a local filename is insufficient.
3. Copy each returned image into the task build directory without deleting the generated source. Record prompt, actual tool result path, source and copy SHA-256, dimensions and slide mapping. Inspect content and branding before assembly.
4. Retry only defective pages. Respect actual tool rate-limit responses; there is no fixed universal 10-call quota. Do not schedule indefinite retries.
5. Compose one full-page image per slide with `compose_layers.mjs` route `image-deck`. Use the actual aspect ratio, and reject unnoticed crop/stretch. Finish with current host validation and rendered QA.
6. Deliver as image-only PPTX. If ordinary text must be editable, feed those same images and text truth into [text-editable](image-to-text-editable.md). Do not regenerate a second outline/spec.

Prompts are resumable work, not completed images. A tool success is not text/visual acceptance. No external publication is implied by producing a deck.
