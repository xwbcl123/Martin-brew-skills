---
name: martin-pptx-skill
description: Create or revise branded PPTX decks. Select native objects, image-generated slides, or a background plus editable text. Use for deck production, image-to-PPTX conversion, and final deck verification.
---
# Martin PPTX

Deliver the requested deck using the supplied content, template and approval. For new decks and material visual revisions, design content and visuals together with [Deck Outline](references/deck-outline.md) and [Visual Contract](references/visual-contract.md). Use the host's `/deck-outline` command if available; otherwise follow the same portable reference directly. Do not claim a slash invocation that the host cannot perform. Reuse complete approved outlines and existing design decisions; a narrow correction does not restart planning or permission.

Production order: content + visual outline → template/style-bound contract → real assets and placement review → verified assembly gate → host PPTX builder → actual export/render review. Keep one `visual-contract.json` using [verification schema and commands](references/verification.md); an existing Design/Style document may supply its design rationale without becoming a second brand authority. Run the verifier's plan/assets/final stages at the corresponding boundary. A script pass cannot replace semantic image inspection.

## Route selection

| User need                                                       | Route                    | Read                                                     |
| --------------------------------------------------------------- | ------------------------ | -------------------------------------------------------- |
| New or existing PPTX with editable charts, tables and diagrams  | `native` (default)     | [native](workflows/native.md)                               |
| Baked/image-generated visuals or an image-only deck        | `image-deck`           | [image deck](workflows/image-deck.md)                       |
| Convert existing slide images; only ordinary text needs editing | `text-editable`        | [two-layer conversion](workflows/image-to-text-editable.md) |
| Explicitly selected NotebookLM generation                       | optional source workflow | [NotebookLM](workflows/notebooklm.md)                       |

If the user requests editable data charts, select native. A text-editable chart image does not update its geometry when a number changes. Reuse the source deck's size. Otherwise use 16:9. Formal/company work defaults to editable delivery. Per-visual `embedded_text` is allowed when its noneditable scope is selected; keep promised editable titles, data and labels native. This does not require flattening the entire slide.

## Shared contract

- For explanatory visuals, read [Visual–text composition contract](references/visual-contract.md). Plan content and composition together. Choose textless artwork with tightly anchored native labels, or a self-contained embedded-text infographic with exact text/meaning QA. A detached image and text list is not the default.
- Read `brand-guidelines` and the selected artifact template when applicable. The user's chosen template governs font family, sizes, colors, logo and layout. This skill adds no conflicting Calibri/16pt floor.
- Discover the current host and authoring backend. In Codex with Presentations, follow its current JS `@oai/artifact-tool` contract and finalizer. On another host use its approved backend. A cached plugin, model name or CLI path does not prove capability.
- Run only the selected route. Gamma, NotebookLM, image generation and alternate models are optional unless the requested route needs them.
- Use the host project's existing task/session convention. Declare the final `artifact_class` and authoritative destination before writing. Put temporary assets and QA in that session's private build directory. Preserve source files.
- Record source references, exact text/numbers, selected route, design constraints and per-slide artifact hashes in one manifest. See [schema](references/artifact-schema.md).
- Render and inspect the final deck; compare content, brand/template and editability to the request. Repair only affected pages and dependencies. Stop after required checks pass. See [gates](references/gates.md).
- The selected visual form (infographic/chart/diagram/illustration/photo/background/evidence) is separate from text mode and rendering backend. Four assembly responsibilities—background, structure/frame, subjects/icons and text—do not require four files.
- Image generation authorization covers requested deck assets, not publication, global account changes or a comparative paid benchmark. Use approval already given; a source or capability blocker blocks only its dependent step.
- Return the verified deck and material limitations. Keep build notes, quality records and optional planning documents out of product slides.

## Executable tools

[scripts/README.md](scripts/README.md) documents the two-layer composer, package validator and route decision helper. The composer produces a draft and previews; it does not perform OCR, image editing or semantic visual acceptance. Agent vision and image editing complete those steps.

Existing Option 1–6 scripts/templates are historical adapters, not required production stages. Read [legacy adapters](references/legacy-adapters.md) only when resuming an old run. The current entry and four workflows replace their routing defaults.

## Origin

The image workflow and coordinate discipline draw on Gorden Sun's GordenSuperPPTSkills at a frozen revision. [Attribution and adaptation](references/upstream-gorden.md) records source, differences and rights. No claim of fully editable graphic objects is made for the two-layer route.
