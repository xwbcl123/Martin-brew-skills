# Visual–text composition contract

Read for explanatory visuals or changes to composition. Reuse approved content and template/Design.md/Style.md; narrow edits update only affected decisions. Corporate imagery defaults to formal, restrained and topic-specific, using the deck's palette.

## Workflow and authority

For new/material visual work, use [Deck Outline](deck-outline.md), inherit the selected template and existing Design/Style, and save production decisions in `visual-contract.json` under [verification](verification.md). Use one authority for palette/font/logo/grid; every asset prompt and builder consumes the same resolved style. A separate prose Design.md is optional when this information already exists. A narrow correction reuses unaffected records.

Keep two independent classifications: expression form (infographic/chart/diagram/illustration/photo/background/evidence) and assembly responsibility (background, structure/frame, subjects/icons, text). Layers are responsibilities, not four mandatory image files. An infographic can be native, generated, or a composite. Authentic screenshots/report covers retain their original evidence text; generated photos must not masquerade as real event evidence.

Generate/acquire assets for their target region and inspect them before the dependent builder. Existing accepted assets may be reused with placement QA. Asset review must bind actual file hashes and the current contract. Run `verify_visual_contract.py --stage assets` successfully before assembly; final stage also checks the exported package and recorded rendered reviews. Consult verification.md for exact arguments and limitations.

## Design image and words together

The outline specifies content and visual composition. Choose the communication form (infographic, diagram, chart, illustration, photo, background, evidence), then the text mode. Textless describes an asset, not a completed infographic: the finished diagram consists of image, labels and relationships together.

| Text mode | Composition | Acceptance |
|---|---|---|
| `integrated_native` | Textless artwork with native editable labels inside reserved image regions or immediately beside/below corresponding components. Share reading direction, grouping, alignment and connectors where useful. | Every semantic component has an unambiguous nearby label at final slide size. A detached list that forces readers to infer correspondence fails. |
| `embedded_text` | A self-contained infographic with explanatory words, including when the visual stands apart from narrative copy. Supply exact approved strings in the image prompt. | Check every rendered label, name, number and unit against source; omissions, duplicates, spelling, legibility, arrows, grouping and label-to-object meaning. Repair/regenerate and recheck. Disclose baked text as noneditable. |

Real quantitative charts default to native data-driven geometry; raster charts require source-to-mark/axis/unit checks and a declared noneditable scope. A data update must change the geometry, not merely its overlaid number.

Choose by communication and editability needs, not a blanket ban on generated text. Explicitly required editable text/data stays native: use integrated_native or a self-contained hybrid with native labels anchored in the diagram. A model's expected text accuracy does not replace inspecting its actual output. Editable numbers over a raster chart do not make chart geometry editable.

Image-and-text columns remain appropriate for atmospheric photos, evidence, or an already self-contained labeled graphic. Do not place a textless explanatory diagram beside a detached text list and call it an integrated infographic. Narrative copy may be separate; labels needed to understand the visual belong with it.

## Record before asset production

- Bind the content/outline revision and template/style. Use the same resolved palette and treatment in image prompts and assembly.
- Record `visual_form`, `text_mode`, image region, reading direction, title/footer protected zones and exact source strings.
- For integrated_native, define `component_label_map`: component ID/anchor or region, exact label, native label box, relative placement and connector endpoint if needed. Reserve quiet overlay regions; changed composition invalidates affected anchors.
- For embedded_text, map each exact embedded string to its intended object and state the baked/native boundary.
- Size the target region first. Check actual subject size, not just image bounds: internal whitespace can make subjects tiny. Preserve aspect ratio; do not stretch.

For a four-stage left-to-right process, a suitable composition is an enlarged centered visual, four native label groups directly beneath its motifs, and a horizontal connector. Match centers to actual motifs rather than mechanically dividing uneven artwork into equal quarters. This is an example, not a mandatory layout for all slides.

## Accept the composition

Finish content and visual planning, acquire/generate the real asset, then inspect it with the planned label placement at final page size before writing the dependent deck builder. Reuse suitable accepted assets and record hashes plus acceptance of revised placement. Proof overlays can precede assembly. Reuse current approval for the stated correction.

For integrated_native, check proximity, alignment, contrast, shared reading order and unambiguous correspondence. Native words may sit safely inside the image or immediately adjacent to their objects without obscuring meaning. For embedded_text, verify words **and** meaning: correct text attached to the wrong object fails.

Render the actual exported PPTX and repeat composition checks. Edit and rerender a representative native label when editability is promised. Asset QA and final-slide QA are separate; hashes and overflow checks alone cannot prove semantic integration. Record concise evidence in the existing manifest; repair only affected components.
