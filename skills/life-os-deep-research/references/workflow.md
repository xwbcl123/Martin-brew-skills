# Workflow And State Machine

## Session packet

```text
tasks/sessions/YYYY-MM-DD/deep-research-<slug>/
├── index.md
├── 00_request.md
├── 05_grill_me.md
├── 10_plan.md
├── 20_status.json
├── 30_handoff.md
├── 40_results.md
├── 50_reflect.md
├── context/research_brief.md
├── packet_T1_gemini-research.md
├── packet_T2_codex-challenge.md
├── packet_T3_gemini-integrate.md
└── source-ledger.jsonl
```

Use repo-relative paths. Follow the vault's current date-bucket session rules.

## State machine

```text
clarifying -> brief_approved -> initialized -> dispatched_research
-> researching -> challenge_pending -> challenged -> integrating
-> markdown_validated -> pdf_rendering -> artifact_validated -> delivered
```

Optional visual/public branch after `artifact_validated`:

```text
html_requested -> html_rendering -> html_validated
-> publishing -> published -> delivered
```

Terminal exceptions:

```text
cancelled | blocked_input | worker_failed | degraded_single_worker
evidence_failed | pdf_failed | delivery_failed
| html_failed | publish_failed
```

## cmux routing

Read the vault references `workflow-cmux-agent-delegation` and
`workflow-cmux-session-state`. Discover `Open-Research`, identify Gemini and
Codex from their live screen/runtime, then record the current workspace,
surface, role, and model in `20_status.json`. Surface IDs are volatile.

Workers write only their assigned artifacts. Gemini integrates the challenger
review; Codex never edits Gemini's report directly. Hermes only checks gates,
dispatches the next packet, and delivers validated artifacts.

## Evidence ledger

Each JSONL record includes:

```json
{
  "source_id": "S01",
  "url": "https://example.com",
  "title": "...",
  "publisher": "...",
  "published_at": "...",
  "accessed_at": "...",
  "source_type": "primary|secondary|social|dataset",
  "worker": "gemini|codex",
  "status": "verified|partial|blocked",
  "claim_ids": ["C01"],
  "notes": ""
}
```

Material claims map to source IDs and clickable URLs. Conflicts stay visible.
Search snippets, inaccessible pages, and estimated figures must be labeled.

## Supervision

Persist state before waiting. Prefer completion markers, handoff files, and
cmux notifications over repeated screen polling. Do not keep one Telegram LLM
turn open for the entire research run. Resume delivery from durable state and
make it idempotent by task ID plus final artifact hash.

## Optional HTML and publication branch

Only enter this branch when the approved Research Brief contains `#html` or
`#publish`. Gemini receives the validated report, source ledger and Martin Brand
System references, then authors a standalone `viz-brief.html`. Codex does not
redo frontend production. Hermes validates the file and archives it locally.

`#publish` implies `#html`, then invokes `cloudflare-r2-publisher`. The
publication command owns immutable object keys, public readback, task manifest,
global registry and lifecycle actions. Hermes must not implement S3 operations
inside this workflow.
