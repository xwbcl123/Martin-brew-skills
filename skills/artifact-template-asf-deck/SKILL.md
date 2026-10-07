---
name: artifact-template-asf-deck
description: "Create a presentation using the ASF Deck template and its retained reference file. Use when the user selects this template, names ASF Deck, or explicitly invokes $artifact-template-asf-deck. ASF Paper and Georgia Ink editorial presentation family with editable native charts, tables and diagrams."
---

# ASF Deck

Create a presentation from this template. Keep the reference file unchanged.

## Family selection and authority

Read `references/family-contract.md` and `references/template-registry.json`. This is one family with two variants: Paper for publishing and evidence review; Ink for events and convening. Both keep Georgia editorial headings. Explicit user choice wins; infer the register from the artifact purpose when clear.

Use the ASF branch of `brand-guidelines` when installed. Its profile and this family resolve the same independent `asf-brand` v1.2.2 source; do not copy ASF tokens into the personal Life/Work brand system. Use the bundled pinned dependency or `ASF_BRAND_ROOT`, verified by `scripts/native/brand-lock.json`.

## Workflow

1. Read `artifact-template.json` and resolve its paths relative to this skill directory.
2. Load [@presentations](plugin://presentations@openai-primary-runtime) and invoke its reference/template workflow with the retained file.
3. Treat the user's prompt and available sources as the content input. Do not invent facts merely to fill a template slot.
4. Clone or import the reference instead of replacing its visual system with generic defaults.
5. Render and verify the finished presentation, then return the final artifact.

## Fidelity

Preserve source slides, layouts, masters, typography, geometry, images, charts, tables, and recurring slide chrome.

User instructions control requested content and explicit deviations. The retained reference controls layout and formatting where the user has not requested a change.

## Native production and reuse

The default gallery reference is Paper. For Ink load `assets/reference-ink.pptx`; do not recolor Paper mechanically. The samples contain 10 core archetypes and two appendices. A new presentation uses the requested content and appropriate page count, not necessarily all 12 sample pages.

Read `references/native-contract.md` for the installed runtime, content JSON contract, rebuild, and edit/save/reopen checks. `scripts/native/build.mjs` deliberately supports only the fixed 12-slide sample contract. For arbitrary length or materially different content, use the Presentations template workflow, retaining suitable source slides and adapting native objects. Do not stretch the sample builder beyond its text capacity guards.

Run `python3 scripts/validate_package.py` from this skill root to verify retained native samples and source hashes. For generated output, validate chart data, table editability, connectors, font availability and every rendered page. Keep Georgia/Arial; the verified macOS metadata fallback is Courier New where Consolas is unavailable. Font binaries are not embedded or redistributed.

## Browser companion

`assets/source/` contains the paired HTML references and regression script. It is useful for layout inspection and accessible review, but does not certify PowerPoint output. Work on copies outside this skill. Preserve the user's latest soft background surfaces, selected typography and diagram semantics.

## Output boundary

Return the editable PPTX and a visual preview. Keep all sample statements and chart values labeled illustrative until replaced with sourced content. Never copy real meeting records or machine-specific paths into reusable template assets. Read `NOTICE.md` for asset and font rights.
