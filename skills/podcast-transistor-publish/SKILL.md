---
name: podcast-transistor-publish
description: Publish a sealed podcast release-package v2 to an exact Transistor show with hash-bound user authorization, draft readback, independent transformed-artwork verification, and resumable mutation journals.
---

# Transistor publication

Use this skill for explicitly authorized public distribution of a final v2 `delegated_release` package. The controller does not generate authorization or review receipts. v1 and `agent_draft` packages cannot enter this route. Schedule, update, deletion, show creation, and social posting are outside this controller's operations.

The caller holding distribution ownership executes actual external calls. Implementation or review workers use mocked providers; a CLI `--yes`, skill invocation, or passing test is never authorization.

## Inputs and commands

The shared validator is `../podcast-release-package/scripts/v2/package.py validate --package ROOT --release --require-seal`. The controller invokes it again before every mutation, including after each dry-run. Package root contains `episode.json`, an artifact `delivery_audio`, flat ten-field `transistor_payload`, and `artwork`. Shared schema and seal rules remain owned by release-package.

```bash
python3 scripts/publish.py --package ROOT --authorization AUTH.json --state-dir STATE_ROOT --mode plan
python3 scripts/publish.py --package ROOT --authorization AUTH.json --state-dir STATE_ROOT --mode publish
# Resume same candidate and remote ID after transformed artwork review:
python3 scripts/publish.py --package ROOT --authorization AUTH.json --state-dir STATE_ROOT --mode publish --artwork-verification ART_REVIEW.json
```

Resolve the script relative to this skill. The CLI defaults to `transistor` on PATH (override with `TRANSISTOR_CLI`); credentials come only from its environment. No raw output, credentials or presigned upload URLs are saved. Mutation CLI retry count is zero. HTTP timeout defaults to 300 seconds and can be set with `--http-timeout`; the value is passed to the CLI HTTP client. Failures retain only allowlisted structured error fields, never raw output or presigned URLs.

Within one controller process, an unchanged content closure may reuse one complete shared-validator result. Every `fresh()` still rechecks authority and hashes actual manifest, seal, artifacts, source/derived evidence, review files/screenshots, implementation/contracts and relevant tool identities. Before/after validation closure hashes must match. Any drift invalidates the cache and invokes full validation; paths, mtimes and a saved pass flag are insufficient. No persistent cross-run validation cache is used.

The payload must contain exactly `title`, `summary`, `description`, `author`, `explicit`, `type`, `number`, `season`, `image_url`, `transcript_text`, with non-null values. The payload SHA is SHA-256 of UTF-8 JSON with `ensure_ascii=False, sort_keys=True, separators=(',', ':')`; artifact hashes are raw file hashes.

Authorization JSON:

```json
{
  "contract_version": "2.0",
  "authorization_id": "unique-user-authority-record",
  "actor": "user",
  "source_ref_kind": "original_user_message",
  "source_ref": "actual original message reference",
  "original_user_quote": "verbatim user instruction covering these operations",
  "authorized_at": null,
  "episode_key": "exact episode key",
  "show_id": "exact provider show ID",
  "package_revision": 2,
  "manifest_sha256": "raw episode.json SHA256",
  "release_audio_sha256": "delivery_audio raw SHA256",
  "payload_sha256": "canonical flat payload SHA256",
  "allowed_operations": ["upload", "create_draft", "readback", "publish"],
  "revoked": false
}
```

Optional `expires_at` is a timezone-aware ISO instant. Optional `remote_id` binds an already identified episode; only supply it after primary-source identity reconciliation. `actor:user` describes the authority's provenance, not a cryptographic signature. The record must quote real authority; do not fabricate a user message or turn an agent verdict into authority. Missing message timestamp remains null. Modified audio, payload or manifest invalidates the prior binding.

## State and recovery

Use the same persistent `STATE_ROOT` for all runs of an episode. The work directory is `STATE_ROOT/SHA256(episode_key)`. It contains a frozen upload input, `state.json`, fsynced `journal.jsonl`, and final `receipt.json`. An OS flock keyed by episode, independent of the supplied state root, excludes simultaneous controllers. Do not delete state/locks to force a retry or use a new episode key to bypass an existing mapping.

The run validates authority before provider reads, snapshots audio, reads any existing remote ID, checks all pages for same-title conflicts, dry-runs and uploads audio once, creates a draft once, verifies processing and metadata, then dry-runs and publishes once. The final provider readback must be published. A matching already-published episode is a read-only no-op.

Unknown upload outcomes stop for reconciliation. Unknown create outcomes can be recovered only with one exact returned upload-URL association plus full payload/show match; a title alone cannot establish identity. If the provider has already transformed the media URL and no causal association remains, the controller stops for primary-source reconciliation. Unknown publish outcomes use GET; a still-draft result does not trigger a second publish attempt. The recorded remote ID is reused after restart. Changed revision or binding stops for a separate explicit reconciliation decision rather than creating another episode.

Existing historical IDs must be identified by actual content, show relationship and available audio evidence before authorization binds them. Never infer episode identity from a remembered ID.

## Provider transformations

Provider readiness requires `audio_processing:false`, no processing failure, and a public `media_url` (or `audio_url`). Every ready readback streams the actual remote audio into a private temporary directory, requires an audio MIME type, and compares byte count and SHA-256 with the authorized delivery. Download size is bounded to local bytes plus 8 MiB for embedded metadata/artwork. When file bytes differ, FFmpeg decodes both files to complete f32le PCM without resampling or channel changes; PCM SHA-256, byte count, sample frames, sample rate, and channel count must all match exactly. This applies to newly created drafts, explicitly bound existing IDs, timeout reconciliation, and already-published no-op checks. Final receipts carry exact remote file hashes and identify either `exact_delivery_bytes_sha256` or `exact_decoded_pcm_sha256`; the latter also carries both PCM identities and does not claim file-byte equality. A changed sample or different geometry blocks. There is no correlation threshold, timing alignment, sample tolerance, resampling, or general transcode exemption. Private remote/PCM temporary files are removed after verification.

Metadata matches exactly except integer string representations for season/number and boolean strings. When `transcript_text` is absent from GET, fetch the single `transcripts` entry with `format:txt`; require text/plain, decode UTF-8 and normalize only CRLF/CR to LF. Unknown differences block publishing.

If the provider transforms `image_url`, the draft remains recorded and publication stops with its `remote_id`. Have an independent reviewer inspect the original sealed artwork and downloaded remote artwork, then create this separate proof:

```json
{
  "contract_version": "2.0",
  "episode_key": "exact key",
  "show_id": "exact show ID",
  "package_revision": 2,
  "remote_id": "exact draft ID",
  "source_image_url": "authorized payload image_url",
  "source_image_sha256": "sealed artwork artifact SHA256",
  "remote_image_url": "exact provider image_url",
  "remote_image_sha256": "downloaded remote image SHA256",
  "verification_method": "independent_visual_review",
  "verified": true,
  "reviewer_id": "actual independent reviewer identity",
  "source_ref": "actual review evidence reference"
}
```

Pass it with `--artwork-verification` when resuming. The controller verifies the source against the sealed artwork artifact, downloads the remote image again, and checks its MIME and SHA against the proof. This allows evidenced provider image conversion; it does not auto-approve visual similarity. The controller never produces this proof itself.

## Validation

Run `python3 -m unittest discover -s tests -v` from this skill. Tests use mocked provider calls and temporary fixtures; they cover wrong or missing authority, binding drift, cross-process locking, create/upload/publish uncertainty, already-published no-op, metadata/transcript/artwork mismatches, wrong remote audio despite identical metadata, required seal invocation, real MP3 metadata-only PCM equality and different-audio rejection, and same-ID resumption after artwork review. Mock success does not establish live publication.

## Authorized updates of published episodes

The separate `scripts/update_existing.py` route implements updates under current explicit user authority. It never calls create or publish. Existing `publish.py` retains the original operation set. Run `--package ROOT --authorization AUTH --state-dir STATE --mode plan`, then `--mode update-existing --artwork-verification PROOF`.

Keep contract_version `2.0` and the ten flat payload fields. Bind actual revision and `remote_id`, allowed_operations `[readback,update_existing]`, plus `[upload,replace_media]` for chapter-tagged media. Authority adds `cli_identity` (the `cli_identity()` function's commit/runtime hash), and `baseline` with exact old `manifest_path`, `manifest_sha256`, prior API `snapshot_path`, `snapshot_sha256`, and the independently read-back `remote_image_sha256`. The old local delivery is the rollback audio source; retain it and the baseline. No CDN URL is assumed equivalent without readback.

Each mutation rechecks clean CLI source/commit/hash, same show/published date, current metadata/transcript/artwork against baseline or intended content, and the old audio's complete PCM identity. JSON fields use `--fields-file-sha256` so the exact bytes checked inside the CLI are those parsed for HTTP. Durable intent precedes upload/PATCH; unknown upload stops for reconciliation, unknown PATCH can only reconcile by GET. Same accepted state is a read-only NOOP. The controller records old/new media URL, chapter readback, PCM proof and actual CLI commit. Explicit chapter lists are used when provider placeholder adoption is not verified; retained embedded chapters require actual remote MP3 readback.

Semantic transcription disagreement is a provisional review item under autonomous user authority, not a publication veto. Keep user_reviewed false; only technical identity/integrity or unknown-operation failures stop this controller. Preserve `preview.html` for next-day review. Retain rollback-inputs.json with exact old local audio/payload; any recovery upload/PATCH must use its own durable intent, dry-run and same-ID readback.

### Observed same-ID recovery: CDN URL rotation

A successful PATCH can assign a new artwork CDN URL while serving exactly the previously independently reviewed WebP bytes. Keep the old proof, fetch the new URL and record the actual response plus SHA. If the bytes match the reviewed remote SHA exactly, rebind only the separate proof's remote URL, citing the original visual review and new byte-identity evidence. Do not alter baseline authorization, sealed package, or pending state. Resume the same state: pending update_existing performs GET reconciliation, then a repeated run must produce already_updated_noop. If bytes differ, obtain a new independent visual review. Never repeat PATCH merely to recover from proof URL drift.

For public RSS readback, Transistor was observed to convert h2 headings to p/b while retaining the remaining rich HTML, list structure and hrefs. Compare the full transformed HTML and actual chapter JSON; a plain-text-only match cannot establish rich-text preservation. Record only transformations observed in the current episode. The API stored description and preview remain bound to the submitted HTML.

For new reading-transcript packages, transcript readback accepts exact text after transport decoding, or only a change in blank-line count with every nonempty line otherwise identical and in order. Record the actual comparison and text hashes; do not trim spaces inside text-bearing lines. This normalization is not evidence of readable layout: separately verify all paragraphs in the public transcript DOM and inspect desktop/mobile screenshots. Preserve the old aligned branch for unmarked historical packages. Retry stale transcript CDN reads with bounded GET only; never repeat an unknown PATCH. New reading-only revisions with identical delivery SHA require no audio upload.

## Observed on EP04

- Transistor transformed the artwork URL (EP04 proof records a 1400×1400 q:60 WebP; the RSS item pointed to a `.jpg` URL, so a suffix alone does not prove the response format). Treat a transformed `image_url` as a possible event: read it back, keep the independent visual review required for changed artwork (SSIM/PSNR are supporting diagnostics, not thresholds), then resume the **same** remote ID with `--artwork-verification`.
- Remote MP3 file bytes may differ from the local delivery; acceptance rests on the controller's exact complete decoded-PCM identity and geometry check, never on a byte-size or duration match.
- Public RSS can lag the API: poll with bounded GET retries and a deadline, report unresolved status if it never appears; a cache-busting query is a tactic, not a freshness guarantee.
