---
name: podcast-release-package
description: Define, validate, and preview a podcast episode release package before hosting upload or publication. Use for podcast delivery contracts, release readiness, package QC, acceptance reports, or generating a standalone human review page from episode artifacts; this skill does not upload or publish.
---

# Podcast Release Package

Treat the episode package manifest as the machine-readable source of truth. The preview is derived from the manifest and referenced artifacts; never scrape a preview page to reconstruct release metadata.

## Boundaries

- Validate local artifacts only. Do not upload media, mutate Transistor, distribute feeds, or publish social posts.
- `contract_passed=true` means the package satisfies the release contract. It never means `publish_authorized=true`.
- Publication requires a later, episode-specific approval bound to the accepted manifest hash and release-audio hash.
- Preserve source media and upstream artifacts. Write only requested reports/previews or a new package manifest.
- Do not place credentials, presigned URLs, cookies, or tokens in manifests, reports, previews, or logs.

## Modes

### Explicit local agent draft (separate contract)

The default review mode is `human`. For a user-authorized episode explicitly
selecting `review_mode=agent_draft`, read
[references/agent-draft-contract.md](references/agent-draft-contract.md) and
[references/agent-draft.schema.json](references/agent-draft.schema.json) completely.
Use `scripts/validate_agent_draft.py --review-mode agent_draft` with trusted
user-authorization identity and independent hash-bound reviewer evidence.
It validates existing PCM WAV review artifacts and can generate a local preview
without human release receipts. It never satisfies the release contract, creates
human approvals, uploads or publishes. A passing draft reports
`draft_contract_passed=true` and `contract_passed=false`. Do not send this report
to the release preview renderer or any external distribution adapter.

### Create or revise a contract/package

Read [references/contract.md](references/contract.md) and [references/episode-package.schema.json](references/episode-package.schema.json). Start from [references/episode-package.example.json](references/episode-package.example.json) when useful. Keep paths relative to the package root and record SHA-256 for every release-critical artifact.

### Validate release readiness

Run:

```bash
python3 scripts/validate_release_package.py \
  --manifest /absolute/path/to/manifest.json \
  --report /absolute/path/to/acceptance-report.json
```

Exit `0` means all hard gates pass. Exit `1` means the contract is not satisfied. Warnings do not block the core contract, but must remain visible in the report. Do not override validator failures by prose judgment.

The validator checks schema/semantics, path containment, file identity, media properties, loudness/true peak, artwork dimensions, transcript and chapter integrity, review approvals, rights/consent, Transistor metadata, preview inputs, and exposure assets.

### Generate the human preview

Only render from a package that passes validation:

```bash
python3 scripts/render_release_preview.py \
  --manifest /absolute/path/to/manifest.json \
  --acceptance-report /absolute/path/to/acceptance-report.json \
  --output /absolute/path/to/episode-release-preview.html
```

The result is one deterministic, dependency-free **Final Preflight** HTML page. It references the accepted package's local media/artwork by relative URL and includes an explicit Visual Assets section (approved artwork, dimensions, bytes, RGB evidence, SHA-256 and approver), metadata, audio playback, chapters, transcript excerpt, QC, checksums, approval evidence, and publication-boundary status.

## Acceptance behavior

Report four distinct states:

1. `contract_passed`: every hard release gate passed.
2. `human_preview_ready`: the preview can be rendered from accepted artifacts.
3. `growth_ready`: baseline discoverability and share assets are complete.
4. `publish_authorized`: always `false`; only the downstream publishing workflow can establish it from a separate explicit approval.

If the package fails, return the exact gate IDs, evidence, and remediation. If it passes, return the manifest SHA-256, release-audio SHA-256, report path, and preview path. Those hashes are the handoff contract for downstream publishing.

## Downstream handoff

The publishing workflow may consume only a passing acceptance report whose manifest and release-audio hashes still match disk. It should then create/update a Transistor draft, read it back, compare provider state with the manifest, and stop for explicit publish approval.


## Version 2 finished-audio / delegated release

Use the independent v2 contract for explicitly user-authorized autonomous publication; do not reinterpret any v1 human gate or agent_draft permission. See `references/v2/contract.md`.
The thin orchestrator is `podcast-production-workflow/scripts/v2/workflow.py`; downstream skills are podcast-transcription, podcast-enrichment, podcast-release-package and podcast-transistor-publish. Imported/generated finished audio skips internal edit/master lineage; explicit gain/peak derivatives remain separately named. Real audio, hashes, full texts, designed HTML and independent reviews remain required. Current user authorization can replace human review only with honest delegated receipts; user_reviewed remains false.

### Listener content and metadata-only chapter revisions

V2 authoring may contain `public_content.version=1`; the flat provider payload stays at ten fields. `description` comes from enrichment's controlled public HTML, with derived plain summary. Internal audit metadata must not be concatenated into listener copy. Unknown authoring versions fail validation; legacy content remains on the old renderer path.

For ID3-only chapters use `scripts/v2/chapters.py` on a new MP3. Preserve the base delivery. Manifest roles `base_delivery_audio` and `audio_metadata_lineage` bind the base path/hash, tagged hash, chapter_input and freshly recomputable encoded-byte/PCM proof. Canonical transcripts/subtitles/QC bind tagged audio, raw roles retain actual inference-source hashes. Existing sample-edit lineage still verifies against the pre-tag base; no new ASR is claimed. The validator recomputes both chapter/PCM identity and original sample-edit provenance. Generate new reviews and seal after runtime/templates/schema freeze; never edit a sealed revision.

## Standalone publication transcript

New packages declare episode.json `publication_transcript: {version: 1, source: reading_transcript}`. The assembler publishes the complete reviewed reading paragraphs, joined with a blank line, as `payload.transcript_text`; the `publication_transcript` artifact binds `preview/reading-transcript.txt`. Paragraphs must cover canonical segment IDs in order exactly once and contain no internal CR/LF. Validate exact reading file/payload equality and bind the marker into review_context. Unknown variants fail. Historical unmarked packages retain their aligned transcript contract; never silently reinterpret an existing seal. SRT/VTT and the preview's audio-aligned panel continue using canonical timed segments.

## Freeze and review discipline (EP04)

- Run the v2 regression suite before requesting an implementation review (EP04: stale fixture without `provider_metadata`, 7/47 failing, forced `fix-first`). Code or contract changes inside the hashed closure (`implementation_hash()`, `contract_bundle_sha256`) invalidate existing receipts and seals when re-validated under the changed runtime; use a matching frozen runtime or a new reviewed revision.
- Every change to content, preview, payload or artwork changes the bound hashes and invalidates all three receipts. Batch cover/reading/copy changes before one freeze. Keep superseded receipts under `reviews/stale-*`.
- Reviewers are read-only: grant exactly one receipt path to write, or have the primary materialize the receipt from the report and say so in it.
- Artwork: the local `podcast_mp3` profile requires an RGB square image, 1400–3000 px, ≤512,000 bytes; JPG/WebP are preferred delivery choices, not a claim that the validator rejects PNG or that 512,000 B is Transistor's universal limit. Put these limits in the cover brief.
- A stale local seal after shared-runtime drift is not evidence that the published provider object changed. Preserve the original package, receipts and mutation state. Further authorized provider mutations require a verified matching frozen runtime, or a separately reviewed and sealed new revision with current bindings. Never manufacture a passing seal by removing concurrent files or rewriting historical hashes.
