# Image to editable text: two layers

Independent subworkflow interface: invoke `martin-pptx-skill` with route `text-editable`, source images or image deck, and any known original text. Output: one background per slide plus native ordinary text. Charts, icons, frames and decoration remain baked together. No green-screen extraction or icon slicing.

1. Extract each source page at its real dimensions. Inspect it with agent vision. Prefer supplied original text as truth; verify OCR suggestions against the image. Record reading order, exact text, bbox `[x,y,w,h]` in source pixels, font size in source pixels, typeface, weight, color, alignment and confidence. Never use thumbnail coordinates with full-size dimensions.
2. Inspect each source image, then send that actual file as the edit target to the current image tool. Request removal of all ordinary text and numbers while preserving all non-text graphics, chart geometry, colors, linework and positions. Keep logo/art lettering only as an explicit manifest exception. Save prompt, input/output hashes and real tool result path.
3. Inspect the edited background for residual letters, changed charts, shifted edges and damaged logo. The original full slide beneath identical overlay text fails because it creates double lettering. If image editing cannot preserve a required visual, repair that page or report it as blocked; do not auto-approve based on image dimensions.
4. Use schema v2 and `compose_layers.mjs`. Coordinates are normalized from source pixels independently on X and Y. Font size maps by actual page height: `font_px_out = font_px_source × slide_height_px / source_height_px`; points are `font_px_out × 72/96`. Choose explicit line breaks and zero insets for alignment.
5. Render the PPTX. Compare each page to its source: text/numbers/footnotes, placement, wrapping, font, missing graphics, double text and clipping. Record the visual review in the manifest. Low confidence or unknown words need resolution, not invented replacement.
6. Run `validate_layers.py` against the final package. Edit one representative text object in a copy of the exported PPTX, reopen/re-render it and verify the new text appears. XML-only text detection is insufficient for the visual claim.

Changing a native number will not update a baked chart's data geometry. Tasks that change chart data use native or regenerate the chart background. Do not promise every object is editable. Source material remains unchanged.

For a clean, already textless input, set `background_origin: provided-textless` and record source inspection evidence. This saves an unnecessary image call. It cannot describe an unclean slide.
