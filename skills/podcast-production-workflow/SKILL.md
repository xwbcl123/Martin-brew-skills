---
name: podcast-production-workflow
description: "Build, resume, human-review, subtitle-QC, incrementally invalidate, package, and optionally create one separately approved Transistor draft from immutable podcast source media; public publish is never available."
---

# Podcast Production Workflow

Use this Skill when producing or resuming a Family Podcast episode, reviewing an aggressive rough cut, validating accurate audio/video subtitles, planning narrow dependency invalidation, or preparing a contract package.

## Authority And Sources

1. Read the episode task `goal.md`, session status, and Workshop episode declaration before acting.
2. Treat source media and raw Whisper outputs as immutable evidence.
3. Treat `podcast-release-package` as the downstream delivery contract; this Skill produces its inputs but cannot weaken its gates.
4. Treat Filmora/Verbatim/Subs references as evaluation evidence in calibration lanes. The separately authorized user-directed rough-cut recovery route (see Lessons from EP04) consumes frozen user project/export inputs under its own contract.

## Modes

- **Review routing**: default `review_mode=human` keeps every existing production
  gate below. An explicitly user-authorized episode may select `agent_draft` for
  the separate bounded local draft path described below; never reinterpret it as
  a human receipt or a release approval.

- **Inspect / resume**: validate hashes/state and identify the earliest incomplete stage.
- **Bootstrap / deterministic stages**: extract role-separated render/analysis audio, run raw ASR, generate candidates, render approved EDLs, build timeline maps, master, and assemble text/assets.
- **Human restore review**: apply deterministic local edit signals aggressively, then use a hash-bound risk-stratified review sample. Playback is mutually exclusive and time-bounded; sampled cuts default to accept and explicit mistakes restore source audio. This is internal Gate 1 evidence, not a separate user interruption.
- **Judge R&D (non-production)**: historical text/audio Judge tooling may be used only in an explicitly declared `r&d` lane. Its outputs never authorize an EDL, selected edit, mastering, package acceptance, upload, or publish.
- **Filmora calibration (evaluation-only)**: hash-bind the source and Filmora final edit, reconstruct an uncertainty-aware reference EDL, compare it with an auto EDL, and collect human-labeled disagreements. Duration similarity alone never passes an edit, and calibration output has zero production authority.
- **Evaluate**: run sample-timeline invariants, reference metrics, and disagreement analysis. Any episode used for policy tuning is development evidence and cannot later be claimed as held-out.
- **Incremental invalidation**: compare previous/current artifact locks against the canonical Dependency DAG; invalidate only changed roots and transitive dependants.
- **Package**: invoke Workshop `release-gap`, `release-prepare`, and `release-seal`; stop at local accepted preview with `publish_authorized=false`.
- **Unified Gate 1 UAT**: present edit continuity, release-audio listening, transcript/subtitles, chapters, metadata, artwork and rights in one local preview; one receipt binds the exact UAT payload and artifacts. Historical H2/H3b/H4 receipts may remain as compatibility evidence.
- **Gate 2 distribution adapter**: only after a fresh 12/12 accepted and growth-ready package plus an episode/action-specific exact-hash approval, run the approved external action. The bundled adapter supports draft creation only and has no publish/schedule command.

## Hard Invariants

- Canonical edit intervals are integer samples and half-open `[start_sample, end_sample)` on the 48 kHz render/source-audio timebase.
- A 16 kHz mono analysis proxy cannot become the release master.
- Any input/policy/model byte or version change creates a new run key/revision, but invalidates only nodes and approvals that transitively depend on the changed identity in `references/artifact-dependency-dag.json`.
- A default-accept review page is never unattended approval: the Gate 1 edit section must cover every canonical targeted/sample cut, bind EDL/render-report/edited-audio/review-plan hashes, and pass every sampling stratum. Two restores in one stratum fail the edit section and require expanded review or policy revision.
- Judge output has zero production authority regardless of agreement or stability. Missing human review, timeline ambiguity, or hash mismatch fails closed.
- Preserve raw evidence, parsed verdict, adjudication, human override, render, and release artifacts as separate layers.
- Filmora alignment, reference EDL and delta reports created in calibration lanes are evaluation-only and cannot be copied into production or approval. The separately authorized rough-cut production route consumes frozen user project/export inputs under its own contract; it does not change calibration authority.
- S00-S13 never persist credentials or perform third-party mutation. S15 may create one H6-approved Transistor draft; it never persists credentials/presigned URLs and never publishes, schedules, newsletters, or posts socially.

## Required References

- Before any explicitly declared Judge R&D experiment, read [references/judge-contract.md](references/judge-contract.md); never connect that result to production authorization.
- Before scoring a run against a human edit, read [references/evaluation-contract.md](references/evaluation-contract.md).
- Before Filmora calibration or gate consolidation, read [references/filmora-calibration-contract.md](references/filmora-calibration-contract.md).
- Before adopting rough-cut ideas from `timkulbaev/ai-video-editor`, read [references/ai-video-editor-transfer-notes.md](references/ai-video-editor-transfer-notes.md); transfer detectors as candidate-only evidence until calibration supports promotion.
- For invalidation, use [references/artifact-dependency-dag.json](references/artifact-dependency-dag.json); do not replace its artifact-level edges with stage-order invalidation.
- For Chinese subtitles, use [references/subtitle-profile.zh-v1.json](references/subtitle-profile.zh-v1.json) or a separately versioned and approved profile.
- Before packaging, read the separate `podcast-release-package` Skill and its contract.

## Verification

- Validate the Episode benchmark declaration with `scripts/validate_benchmark.py`.
- Validate reconstructed reference EDLs and delta reports against `references/reference-edl.schema.json` and `references/edl-delta-report.schema.json`.
- Validate every candidate, aggressive EDL, H2 receipt and recovered EDL against its schema before promotion.
- A stage is complete only when its output hashes, timebase, tool/model/prompt identity, logs and gate evidence read back successfully.
- A package is complete only when the canonical validator passes 12/12. This still does not authorize publication.

## Stable Local Entry

### Authorized agent draft entry (existing artifacts only)

For `review_mode=agent_draft`, read the downstream
`podcast-release-package/references/agent-draft-contract.md` and schema completely.
Inventory the authorized episode's existing lossless review WAV and optional
text artifacts, document missing stages, and request an independent agent review
against the exact manifest and artifact hashes. Invoke that Skill's
`validate_agent_draft.py --review-mode agent_draft` with the user authorization's
trusted digest, reviewer receipt and new report/preview paths. This local branch
does **not** require H2/H3/H4 or UAT human receipts and must not enter the human
release sequence below. A passing local draft is not a production-complete episode.

This change adds validation/preview, not autonomous mastering or postcut ASR.
Existing human-gated commands remain unchanged; missing draft build stages are
implementation gaps to report, never grounds to synthesize human receipts.
Agent review remains advisory and cannot establish listening, rights, consent,
upload or publication. All external mutation is denied in agent draft mode.

### Human production entry (unchanged)

Run the deterministic S01-S03 baseline from the project root:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/run_local_baseline.py \
  --config $PODCAST_WORKSPACE/00_control/episodes/<episode_id>/workflow-inputs-v1.json
```

This command may extract/verify role-separated audio, align the held-out Filmora reference, create a human label template, and generate edit candidates. It never dispatches Judges, applies cuts, uploads, or publishes.

Run the complete local Filmora Golden Reference calibration lane:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/run_filmora_calibration.py \
  --config <filmora-calibration-config.json>
```

The config binds exact source/render audio, Filmora final edit, auto EDL and an isolated output root. The command emits `alignment.json`, `reference-edl.json`, `edl-delta-report.json`, `feedback-template.json`, a local audio-assisted review HTML and `calibration-smoke-report.json`. A repeat run reuses matching content-addressed stages. This lane performs no external mutation and always reports `publish_authorized=false`.

For a new production episode without Filmora/Verbatim gold references, use the generic S00-S02 entries:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/bootstrap_audio_roles.py \
  --intake <episode-intake.json> --manifest <workflow-manifest.json> \
  --render <render-48k.wav> --analysis <analysis-16k-mono.wav> --report <S00-S01-report.json>

python3 .agents/skills/podcast-production-workflow/scripts/run_whisper_raw.py \
  --episode-id <episode-id> --analysis-audio <analysis-16k-mono.wav> \
  --model <ggml-model.bin> --output-base <immutable-raw-output-base> \
  --report <S02-report.json> --log <S02.log> --language zh
```

The bootstrap verifies source identity before and after extraction. The Whisper executor refuses to overwrite raw outputs that lack a matching verified report.

For a configured episode, the single stable entry is:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/run_episode_baseline.py \
  --config <episode-workflow-inputs.json>
```

Build an aggressive local EDL without consuming an LLM Judge, then render only a lossless review artifact:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/build_aggressive_human_edl.py \
  --candidates <candidate-bundle.json> --policy <editorial-policy.json> \
  --render-audio <render-48k.wav> --output <aggressive-edl.json>
```

```bash
python3 .agents/skills/podcast-production-workflow/scripts/render_sample_edl.py \
  --edl <aggressive-edl.json> --output <aggressive-review-48k.wav> --report <render-report.json>
```

Create the one-click Origin-vs-Edited review page. It uses the sample-accurate render mapping, pauses the opposite player, auto-stops each short clip, and shows only targeted/risk-stratified sample points by default. Optional full expansion remains available:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/render_human_restore_review.py \
  --edl <aggressive-edl.json> --render-report <render-report.json> \
  --original-audio <render-48k.wav> \
  --edited-audio <aggressive-review-48k.wav> --output <human-restore-review.html>
```

The v1 sampling policy includes all recording-control/mixed-category/long cuts as targeted sentinels, plus deterministic timeline-spread samples from high/medium/low risk strata. A stratum permits at most one sampled restore; its second restore fails H2. Apply only a passing receipt; reviewed `restore_source` decisions remove those cuts, while unsampled cuts retain the declared default. H2 still does not approve the final selected edit:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/apply_human_restore_review.py \
  --edl <aggressive-edl.json> --render-report <render-report.json> \
  --edited-audio <aggressive-review-48k.wav> \
  --review <H2-human-restore-review.json> --output <human-recovered-edl.json>
```

True crossfade regions are recorded as two-source, non-invertible transitions. They are excluded from the one-sample inverse-mapping assertion and always require human join listening.

After H3a approves the exact selected lossless edit hash, create the local archive master and release MP3:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/master_audio_local.py \
  --episode-id <episode-id> \
  --selected-edit <selected-edit-48k.wav> \
  --editorial-approval <H3a-exact-hash-approval.json> \
  --archive-master <episode-master.wav> \
  --release-mp3 <episode-release.mp3> \
  --report <mastering-report.json> \
  --log-dir <mastering-log-directory>
```

The stage performs measured two-pass FFmpeg loudness normalization, writes a 48 kHz 24-bit PCM archive master and 128 kbps MP3, then freshly measures both outputs. Its technical pass does not satisfy H3b: final release-audio listening remains a separate exact-hash approval.

After H3b binds the mastered release MP3, rerun immutable Whisper on the release timeline:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/run_whisper_raw.py \
  --stage S11a-postcut-whisper-raw \
  --episode-id <episode-id> --analysis-audio <release.mp3> \
  --release-approval <H3b-release-audio-approval.json> \
  --model <ggml-model.bin> --output-base <immutable-postcut-raw-base> \
  --report <S11a-report.json> --log <S11a.log> --language zh
```

Treat `--analysis-audio` as the executor's legacy argument name; the S11a report records it as `release_audio`, and every raw output uses the `immutable-postcut-raw-whisper` role.

Validate proposed canonical Verbatim, timed Subs and the correction/speaker ledger, first without and later with H4 approval. The default `audio` profile still performs subtitle QC:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/validate_postcut_text.py \
  --episode-id <episode-id> --release-audio <release.mp3> \
  --raw-report <S11a-report.json> --verbatim <verbatim.txt> --subs <subs.vtt> \
  --correction-ledger <correction-ledger.json> [--approval <H4-postcut-text.json>] \
  --report <S11b-validation-report.json>
```

For a video episode, bind the exact final video and the versioned Chinese subtitle profile:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/validate_postcut_text.py \
  --episode-id <episode-id> --delivery-profile video \
  --release-audio <release.mp3> --final-video <final-video.mp4> \
  --raw-report <S11a-report.json> --verbatim <verbatim.txt> --subs <subs.vtt> \
  --correction-ledger <correction-ledger.json> \
  --subtitle-profile references/subtitle-profile.zh-v1.json \
  [--approval <H4-postcut-text.json>] --report <S11b-validation-report.json>
```

Without H4 the validator intentionally returns `review_required`. H4 separately approves terminology, speaker attribution, semantic fidelity, timing and—under `video`—visual subtitle review while binding release-audio/raw/verbatim/subs/ledger/profile/final-video hashes. Automatic QC covers cue order, overlap, duration, line count/length, reading speed and final audio/video duration alignment.

Render a cue-by-cue local review page from the live validation report. It verifies subtitle/media hashes, jumps directly to every cue, highlights QC violations, and exports a complete H4 approval only after every required human review checkbox is confirmed:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/render_subtitle_review.py \
  --validation-report <S11b-validation-report.json> --subs <subs.vtt> \
  --output <subtitle-review.html>
```

Plan a narrow rerun after any artifact change:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/build_artifact_lock.py \
  --dag .agents/skills/podcast-production-workflow/references/artifact-dependency-dag.json \
  --episode-id <episode-id> \
  --artifact release_audio=<release.mp3> \
  --artifact postcut_raw_asr=<S11a-report.json> \
  --artifact show_notes=<show-notes.md> \
  --output <current-artifact-lock.json>

python3 .agents/skills/podcast-production-workflow/scripts/plan_incremental_invalidation.py \
  --dag .agents/skills/podcast-production-workflow/references/artifact-dependency-dag.json \
  --previous-lock <previous-artifact-lock.json> --current-lock <current-artifact-lock.json> \
  --output <invalidation-plan.json>
```

Every `--artifact` key must be a node in the canonical DAG. The lock records live path, byte size and SHA-256; it is a snapshot, not an approval. A Show Notes-only correction invalidates metadata/release-candidate/package descendants, but leaves mastering and post-cut ASR reusable. A changed release audio still invalidates its actual transcript, chapter, package and approval dependants.

Inspect an accepted package without mutation:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/transistor_draft_controller.py \
  --manifest <package>/manifest.json \
  --acceptance-report <package>/qc/acceptance-report.json
```

Only after H6 approval binds the exact acceptance-report, manifest, release-candidate payload, release MP3 and show ID, execute one draft attempt:

```bash
python3 .agents/skills/podcast-production-workflow/scripts/transistor_draft_controller.py \
  --manifest <package>/manifest.json \
  --acceptance-report <package>/qc/acceptance-report.json \
  --approval <H6-transistor-draft-upload.json> \
  --receipt <sanitized-draft-receipt.json> \
  --execute
```

The controller freshly re-runs the canonical package validator, performs an exact-title duplicate probe, writes an attempt lock before upload, dry-runs draft creation, creates once, and independently reads back `draft`. Any interrupted mutation becomes reconciliation-required and is never blindly retried.

Attempt and receipt paths must resolve distinctly and may not overwrite inputs.
The adapter verifies manifest/report/audio and all transmitted text hashes, copies
the transmitted files into a private read-only temporary snapshot, and rechecks
both original and snapshot identities after the remote duplicate probe before
recording the attempt or uploading. Provider reads use only that snapshot, so
ordinary concurrent edits to original files cannot alter approved upload bytes.
This is not an OS security boundary against a hostile process running as the same
user. Snapshot files are removed after the attempt; ambiguous external outcomes
still require reconciliation and must never be retried automatically.


## Version 2 finished-audio / delegated release

Use the independent v2 contract for explicitly user-authorized autonomous publication; do not reinterpret any v1 human gate or agent_draft permission. See `../podcast-release-package/references/v2/contract.md`.
The thin orchestrator is `podcast-production-workflow/scripts/v2/workflow.py`; downstream skills are podcast-transcription, podcast-enrichment, podcast-release-package and podcast-transistor-publish. Imported/generated finished audio skips internal edit/master lineage; explicit gain/peak derivatives remain separately named. Real audio, hashes, full texts, designed HTML and independent reviews remain required. Current user authorization can replace human review only with honest delegated receipts; user_reviewed remains false.

### Autonomous listener revision route

For explicitly authorized autonomous publication or same-ID revisions, use transcription calibration (bounded anomalous snippets and the current glossary snapshot), enrichment `public_content.version=1`, an immersive retained `preview.html`, independent content/experience review, then a newly sealed v2 package. User Scout confirmations outrank provisional model decisions; only autonomous mode uses independent distinct-model votes. Dissent stays in the collapsed terminology review and correction ledger, and does not itself stop overnight publishing. Next-day decision exports require trusted user provenance and current bindings before import and downstream rebuilding.

Existing published episodes use `podcast-transistor-publish/scripts/update_existing.py`, not create/publish. CLI file-input smoke is the first journaled final-content PATCH, followed by same-ID API/media/share/RSS verification. All runtime changes finish before review/seal. Audio already rendered/mastered may enter at transcription; Final Edit remains optional.

Default platform transcript selection is the reviewed reading edition: Transistor's separate transcript page must match preview/reading-transcript.txt, with readable paragraphs. Keep canonical timed text for subtitles and preview audio comparison. Require the new package publication_transcript marker/artifact; verify every public paragraph in order and inspect actual desktop/mobile paragraph layout. A first/last-text check alone is insufficient.

## Lessons from EP04 (2026-10-11)

Rationale, timings and evidence live in the owner's private EP04 session notes (not included in this repository).

- **User rough cut → recovered EDL → three-stem mastering.** When the user asks to reconstruct their NLE rough cut onto the original speaker tracks, follow [references/rough-cut-to-three-stem-collaboration.md](references/rough-cut-to-three-stem-collaboration.md) (entry conditions, `.wfp`-first inputs via `scripts/wfp_extract_edl.py`, export/project binding, tiered seam policy, rebuilt-vs-export check, explicit user acceptance, time budget) and give the user a short companion guide (owner-maintained, not included here). A finished delivery supplied for transcription/enrichment skips this route unless reconstruction is requested. The route never replaces v1 human gates, v2 independent reviews, seals or hash-bound publication authority; user acceptance is never recorded as an independent ACCEPT.
- **Intake (ask once, record in decision_log):** who is on each track and whether tracks are duplicated to L/R (ask; correlation only verifies); filler policy per token with source counts; whether the user rough-cuts themselves; single mix vs per-speaker mastering; cover limits; copy-button acceptance.
- **Cadence:** classify new requirements (replacement/addition/note) when they arrive; write handoff/status after every gate; run reviews in parallel; batch low-risk content changes before one freeze (each freeze invalidates all three receipts); script-written timestamps; distinguish `cut-rN` from `revision-NNN`; write a handoff before launching long reviews.
