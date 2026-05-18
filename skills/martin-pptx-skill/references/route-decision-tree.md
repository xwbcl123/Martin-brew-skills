# Route Decision Tree

## Route Registry

| Route | Name | Purpose | Status |
| --- | --- | --- | --- |
| Option 5 | Header/footer/background master + Python editable reconstruction | Main formal PPTX route | v0 main |
| Option 4 | Presentations / artifact-tool route | Independent editorial backup | optional backup |
| Option 1 | Direct Python PPTX | Deterministic native-object reconstruction | foundation / fallback |
| Option 3 | HTML-first editable PPTX export | Rich preview and component authoring | v1 R&D |
| Option 2 | Image-gen textless background + editable text | Visual acceleration in special cases | special-case only |

## Default Decision Logic

```text
if scenario == formal-company-report:
    require editable PPTX
    require visual motherboard before PPTX reconstruction
    select Option 5 as main route
    if Presentations/artifact-tool runtime is available and backup requested/useful:
        also run Option 4 as independent backup
    if BG extraction is unsafe or visual motherboard unavailable:
        use Option 1 direct Python reconstruction

elif target_output includes pptx and editable_text_required:
    select Option 5 when visual motherboard / shared master exists
    else select Option 1
    optionally run Option 4 if runtime available

elif target_output in [html, pdf, graphic] and user accepts non-editable visual delivery:
    stop after Stage 3 visual motherboard + export + QC

elif rich HTML/CSS authoring is the primary need and editable PPTX export can be mapped to native PPTX objects:
    use Option 3 as R&D / experimental route

elif speed and approximate visual richness matter more than structural editability:
    consider Option 2 only after documenting cleanup risks

else:
    run Stage 0/1/2 and ask for delivery endpoint or propose default based on scenario
```

## Scenario Decision Table

| Scenario | Main Route | Backup | Stop Rule |
| --- | --- | --- | --- |
| Formal company report | Option 5 | Option 4 if available | Must deliver editable PPTX. |
| Board / leadership policy deck | Option 5 | Option 4 if available | Editable PPTX + PDF preview. |
| Customer communication | HTML/PDF first; Option 5 if PPTX required | Option 4 | Can stop at approved HTML/PDF. |
| Visual essay / blog / personal project | Stage 3 visual + HTML/PDF | Option 4 | Can stop at graphic/PDF/HTML. |
| Research report | HTML/PDF + source/evidence QC | Option 5 if requested | Can stop at report/deck PDF. |
| Training course | Depends on distribution | Option 5 if editable PPTX needed | Stop at format user will distribute. |

## Option 5 — v0 Main Route

Use when:

- Formal PPTX is required.
- `deck-outline.md` and `design.md` exist or can be created.
- Visual motherboard or approved reference exists.
- Business-critical text must remain editable.
- User accepts editable reconstruction rather than pixel-perfect clone.

Required artifacts:

```text
output/full_deck_option5/deck.pptx
output/full_deck_option5/rendered/deck.pdf
output/full_deck_option5/rendered/png/slide_*.png
output/full_deck_option5/contact_sheet.png
output/full_deck_option5/bg_gate_report.json
output/full_deck_option5/text_extraction.json
output/full_deck_option5/text_fidelity_gate.md
output/full_deck_option5/qc_report.md
```

Pass conditions:

- BG Gate pass.
- Text Fidelity Gate has no fail.
- Render gate pass.
- Critical text is editable.
- Page count matches `deck-outline.md`.

Known tradeoffs:

- Not a pixel-perfect visual motherboard clone.
- Background chrome may be raster.
- Python reconstruction can become bespoke unless component builders are extracted.

## Option 4 — Independent Backup Route

Use when:

- `Presentations` / `artifact-tool` runtime exists.
- A high-quality independent editorial deck is valuable.
- User wants alternate creative direction or comparator.
- Main route needs risk reduction.

Do not use when:

- The environment lacks runtime.
- The user needs strict visual reproduction of the visual motherboard.
- The backup would delay mandatory formal PPTX delivery.

Required artifacts when used:

```text
output/backup_option4/deck.pptx or generated artifact
output/backup_option4/rendered/deck.pdf
output/backup_option4/rendered/png/slide_*.png
output/backup_option4/layout.json
output/backup_option4/scorecard.md
output/backup_option4/qc_report.md
```

Decision note:

Option 4 is an independent backup route, not a hard dependency for v0 and not a strict visual clone route.

## Option 1 — Direct Python PPTX

Use when:

- Need deterministic PowerPoint-native text/shapes.
- Background extraction is unsafe.
- Visual design can be represented through simple shape/layout grammar.
- The deck needs quick repairability more than rich visual texture.

Use inside Option 5 as the reconstruction foundation.

Failure mode:

- Deck may feel too plain if component library is weak.

Recovery:

- Add reusable components: cards, chips, matrices, timelines, maps, control ladders.

## Option 3 — HTML-first Editable Export

Use when:

- Design exploration benefits from HTML/CSS preview loop.
- Dense visual layouts need rapid grid tuning.
- Export can map HTML components to PPTX-native objects.

Do not use as formal main route if export is screenshot-only.

Status:

- v1 R&D direction, not v0 dependency.

Required evidence before promotion:

- Native PPTX object mapping.
- Font and overflow checks.
- Render parity checks.

## Option 2 — Image-gen Textless Background + Editable Text

Use only when:

- Speed and approximate visual fidelity matter more than structural editability.
- Background cleanup can be validated.
- Business-critical content remains editable and not baked into the image.

Do not use as default because:

- Textless background cleanup can leave residual artifacts.
- Body icon/card/chart overlap risk is high.
- Reproducibility depends on image-generation variance.

Gate requirement:

- Textless background QC must pass before overlaying editable text.

## Parallel Production Model

For high-stakes formal decks:

```text
Option 5 main deck
+ Option 4 independent backup deck if runtime available
-> render both
-> score both
-> deliver Option 5 by default
-> optionally include Option 4 as alternate/reference
```

Do not count a direct `deck-outline.md + design.md -> PPTX` run as a full Option 5 quality benchmark. It may be used only to smoke-test scripts.

Comparison criteria:

| Criterion | Option 5 | Option 4 |
| --- | --- | --- |
| Visual fidelity to approved motherboard | high | medium / independent |
| Editability | high | depends on output but often high |
| Runtime dependency | local Python | runtime-specific |
| Repeatability | high after scripts | medium |
| Editorial polish | medium-high | high |
| v0 dependency | yes | no |

## Route Decision Artifact

Every run that reaches Stage 4 should create `output/route_decision.md`:

```markdown
# Route Decision

- Run ID:
- Scenario:
- Target output:
- Editable PPTX required: yes/no
- Selected main route:
- Backup route:
- Runtime availability:
- Stop condition:
- Rationale:
- Risks:
- Gates required:
```
