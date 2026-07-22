# Intake And Grill Contract

## Research Brief gate

Use `grill-me` to resolve the highest-risk missing decision one message at a
time. Inspect URLs, local notes, and prior sessions before asking something that
can be discovered.

The gate is complete only when the session records:

| Field | Required content |
|---|---|
| Core question | One falsifiable or decision-relevant question |
| Audience | Who will read or use the report |
| Scope | Included and explicitly excluded topics |
| Time horizon | Historical comparison and evidence cut-off |
| Geography | Countries, markets, or jurisdictions |
| Evidence standard | Primary/official preference and acceptable secondary sources |
| Desired conclusion | Analysis, options, recommendation, or due diligence |
| Deliverables | Markdown + multi-page Kami PDF by default |
| Brand route | Life by default; Work only when explicit |
| Publication | Local only unless a future explicit `#publish` gate succeeds |

Write the question/answer log to `05_grill_me.md` and the stable approved brief
to `context/research_brief.md`. Set `implementation_ready: true` only when a
worker can execute without inventing the intended direction.

## Recommended opening question

For a broad topic, ask what decision the report should enable. Recommend a
bounded analytical question rather than a general encyclopedia-style survey.

For a URL, first inspect it, summarize what it establishes, and ask which claim
or implication should be tested beyond the page.

## Do not grill unnecessarily

Do not create a task for greetings, help, status, cancellation, or reset
commands. If the initial request already fixes every material field, present a
compact Research Brief for confirmation instead of asking redundant questions.
