# Local agent draft contract v1

Default `review_mode=human` retains the entire release v1.0 contract and all
existing production approvals. Explicit `agent_draft` selects a **different**
local evidence contract; it never passes G01–G12 or authorizes distribution.

## Inputs and authorization

Read `agent-draft.schema.json` completely. The root schema is the manifest;
`$defs.authorization` and `$defs.review` are separate JSON documents. All
artifact and reviewer-evidence paths are package-relative and containment-checked.

The actual user task must explicitly authorize the exact episode and local draft
scope. Record its durable source reference in `authorization.source_ref`, bind
the final manifest SHA-256, and retain the authorization SHA-256 in that trusted
task record. Pass that trusted digest on the command line; do not infer consent
from a manifest, reviewer verdict, or a self-generated authorization file. This
is a caller-enforced provenance boundary, not cryptographic user authentication.

Required existing input is nonempty 48 kHz mono/stereo PCM WAV review audio
(16/24/32-bit). Optional UTF-8 transcript/notes are inventory artifacts, not
certified accurate subtitles or canonical text. The manifest must list concrete
limitations, including incomplete stages. This validator does not build audio.

## Independent review

Dispatch an independent reviewer only within the episode's user-authorized scope.
The producer must not create their own reviewer verdict. Record actual producer
and reviewer task/agent identities, exact manifest hash, **all** artifact hashes,
coverage (including whether audio was actually assessed), and a distinct nonempty
hash-bound evidence artifact. Reviewer kind is `independent_agent_draft_review`,
Evidence must be a separate nonblank UTF-8 Markdown/text review, not the manifest,
authorization, reviewer receipt, another artifact, or JSON control data disguised
as text. Coverage and every limitation must contain non-whitespace content.
verdict is `draft_acceptable`; human approval fields are forbidden by schema.
Identity inequality is machine-checked; actual independence and honesty must also
be checked against task dispatch/readback evidence by the coordinator. No claim
of listening may be inferred from a text-only review.

## Run and invalidation

```bash
python3 .agents/skills/podcast-release-package/scripts/validate_agent_draft.py \
  --review-mode agent_draft --manifest <package>/agent-draft.json \
  --authorization <user-local-authorization.json> \
  --authorization-sha256 <trusted-task-record-digest> \
  --review <independent-agent-review.json> \
  --report <new-draft-report.json> --preview <package>/new-agent-draft.html
```

Outputs must not already exist; the preview must be beside the manifest. Preview
generation performs validation in the same invocation and renders no remote assets
or executable metadata. Exit 0 means **draft_contract_passed only**. Release
`contract_passed`, `human_preview_ready`, `growth_ready`, `upload_authorized`,
`external_mutation_authorized`, and `publish_authorized` remain false.

Dependency chain: any artifact byte/path, limitation, producer or revision change
changes the manifest identity → invalidates authorization and independent review
→ invalidates draft report and preview. Reviewer evidence changes invalidate its
receipt hash → report/preview. Rerun with a new revision and new hash-bound records;
do not transplant a stale review. Upstream audio stages remain reusable if their
own identities are unchanged. This draft chain is isolated from the canonical
release DAG; no draft verdict can satisfy H2/H3/H4/UAT/H6.

## Deliberate limits

Fresh technical checks cover WAV encoding, channel/rate/sample-width, nonzero
duration and complete PCM bytes. They do not certify loudness/true peak, editorial
continuity, speaker/semantic fidelity, subtitle timing, rights, consent, artwork,
or readiness for external consumption. The output is a bounded local preview,
not a complete autonomous podcast production pipeline. Existing human-gated
mastering and postcut-ASR commands are unchanged; do not forge receipts to run
them. Missing draft build stages require separately scoped implementation.
