---
name: brand-guidelines
description: Applies Martin's default brand system to documents, decks, blogs, reports, visual assets, and Kami outputs. Use whenever the user mentions branding, visual identity, style guidelines, Logo usage, Martin, Martin-Borealis, Life versus Work, an organization-authorized artifact, or asks to make an artifact feel consistent with Martin's style. Classifies Life versus Work first, routes to the correct identity, and preserves explicit Anthropic styling only when requested.
license: Complete terms for the archived Anthropic source are in LICENSE.txt
metadata:
  origin_vendor: martin-custom
  based_on: claude-brand-guidelines
  customized_at: 2026-07-21
---

# Martin Brand Guidelines

Use this skill as the default brand router. Do not start by choosing colors. First determine whose artifact it is and what authority it represents.

## Required read

Read `references/martin-brand-system.md` completely before creating or restyling an artifact. It defines brand architecture, voice, tokens, typography, imagery, data visualization, accessibility, document behavior, and governance.

For public or cross-project use, also read `references/public-portability.md`. The packaged `Organization Brand` is a placeholder adapter and must be replaced with authorized organization assets before producing a real Work artifact.

When the task uses Kami, also read `references/kami-brand-profile.md` and Kami's `references/brand-profile.md`.

When the user explicitly requests Anthropic styling, read `references/anthropic-original.md` and do not apply Martin defaults.

## Routing contract

1. Classify the artifact:
   - `Life`: personal life, learning, reflection, insight, or creative work.
   - `Work`: company responsibilities, organizational communication, compliance, customer trust, market access, or a department-authorized artifact.
2. Select one primary brand:
   - Life → M/Martin.
   - Work → Organization Brand.
3. Select the mode:
   - Life default → Light Editorial.
   - Life explicit dark/expressive/keynote/cover → Martin-Borealis.
   - Work slides → an organization-approved template supplied at runtime.
   - Other Work artifacts → Work Editorial tokens.
4. Apply the shared voice: Calm Authority + Evidence-led Insight + Human Curiosity.
5. Verify Logo hierarchy, contrast, typography fallback, evidence integrity, and output-specific layout.

If Life versus Work is genuinely ambiguous and the choice changes Logo or authority, ask one focused question. Otherwise infer from context and continue.

## Core identity rules

- Personal promise: `From complexity to clarity` / `化繁为简，洞见本质`.
- Personal method: `由此及彼，由表及里，去粗存精，去伪存真`.
- Never make the personal Logo a co-equal mark on Work artifacts.
- Never import the obsolete organization Publish Logo into Martin-Borealis.
- Never import the personal blue-green system into Organization Brand by default.
- Explicit task instructions override the profile and defaults.

## Asset routes

- Personal brand: `assets/martin-personal/`
- Martin-Borealis: `references/martin-borealis.md`
- Work brand: `assets/organization-placeholder/`
- Work template contract: `references/public-portability.md`
- Kami vault profile: `references/kami-brand-profile.md`

## Reference samples

- `references/martin-brand-system-visual-reference.html` is the broad visual system gallery for comparing identity modes, Logo variants, tokens, and Life versus Work scenarios.
- `references/martin-brand-system-one-pager-reference.html` is an approved implementation reference for a Life / Light Editorial one-page HTML/PDF. Read it when building a personal one-pager or reviewing Logo/metadata alignment, fixed A4 footer placement, or narrow-screen footer fallback.
- Treat both files as reference samples, not mandatory templates. Reuse their verified principles and QA patterns while adapting composition, density, evidence, and content to the actual artifact.

## Delivery check

Before handoff, confirm:

- the artifact uses one primary brand;
- Life/Work routing is visible in asset and template selection;
- the Logo variant matches background and size;
- every Logo/byline or Logo/metadata lockup shares one explicit alignment axis and is checked by visible optical bounds, not canvas bounds alone;
- body text meets contrast/readability requirements;
- images and charts are evidence-bearing rather than decorative;
- the result contains no fabricated facts, broken asset paths, obsolete Logos, or unrequested co-branding.
