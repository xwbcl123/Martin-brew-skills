---
name: podcast-production-workflow
description: "Start or resume podcast production from a human Filmora rough cut (WFP), original media and speaker-role metadata, or finished audio. Guide first-time setup; coordinate editing, mastering, audio review, transcription, enrichment, preview, independent acceptance and explicitly authorized v2 publication without repeated human checkpoints."
---

# Podcast Production Workflow

Use this Skill as the single entry for a podcast episode. The recommended handoff is **human rough cut → saved WFP + original media + `_meta.md` role declarations → agent completion through publication**. Existing finished audio may enter downstream. Personal identities, show IDs, models and machine paths are configured inputs, not prerequisites tied to one owner.

## Recommended Entry: Human Rough Cut, Agent Completion

Read [references/minimal-start.md](references/minimal-start.md). For a first-time user, also read [references/first-run-and-handoff.md](references/first-run-and-handoff.md); guide setup once and reuse verified configuration on later episodes. The packaged `scripts/startup.py setup/check` provides offline configuration and batched intake diagnostics; `requirements-local.txt` declares local Python dependencies.

Minimal repeat-use prompt, when episode metadata resolves show identity and input paths:

> $podcast-production-workflow /goal 发布这一集：<单集目录绝对路径>。人工粗剪已完成；按 WFP 和 _meta.md 接手，独立验收通过后正式发布。

- The user supplies access to original media, their saved rough-cut WFP and `_meta.md` containing the declared speaker/track/channel map. Files may be referenced by path rather than copied into one directory. Read existing metadata before asking; confirm only missing or conflicting critical facts in one batch. SRT/export is optional for the direct-FFmpeg structure route.
- An explicit episode-specific instruction to publish authorizes the v2 delegated-release route through its downstream controller. Capture that real instruction; bind the actual show/revision/hashes after freezing. Do not ask again at mastering, text approval, preview, seal, draft creation or publish solely because a legacy step names a human gate. Keep `user_reviewed=false`; never fabricate human listening or approval.
- Start or resume one owning task/goal through public readback and closeout. Use the host's goal facility only when available and requested; otherwise keep persistent task state without claiming a goal tool was invoked. Reuse valid artifacts and reconcile remote state before any new mutation.
- Use direct FFmpeg to apply the frozen user's deletion structure to synchronized original stems; independently validate source identity, sample clock, integrity and acoustic joins. Do not add new editorial deletions or claim Filmora DSP equivalence. Read the direct-FFmpeg branch in [rough-cut collaboration](references/rough-cut-to-three-stem-collaboration.md). Export-equivalence reconstruction and legacy human review are separate opt-in routes.
- Route planning/advice, bounded production, copywriting and independent review by current capabilities. Native subagents are sufficient where available; external terminal workspaces are optional when an external harness supplies needed capability. Do not make the user choose an agent fleet or install an external terminal multiplexer to begin. A role may be combined when independence requirements permit; reviewers cannot approve their own production.
- Audio review must receive actual audio through an audio-capable route. A text-only native review does not replace fine listening. Prefer a currently verified Gemini audio route when suitable; model labels and the user's preferred Flash copywriter are preferences, not proof of capability. Record clips, coverage, results and limitations; expand or repair failed seams before continuing. This evidence enters v2 review, never an R&D Judge authorization.
- Finish implementation/content changes, then obtain current independent content/experience/implementation receipts, validate and seal. The sole publisher performs authorized mutation and API/media/share/RSS/full-transcript readback. No user checkpoint is required on this passing path. Deliver a concise acceptance summary, local files, public links and retained limitations.
- Interrupt only for critical source/identity/role/intent ambiguity, a technical integrity failure that cannot be repaired within scope, unresolved required review failures or concrete rights/privacy risk, missing required capability with no authorized route, or ambiguous external mutation needing reconciliation. Attempt bounded evidence-backed recovery and continue independent work first. A passing startup checklist alone never authorizes publication.

## Current Rough-Cut Limitation

The recommended route still relies on the human's editorial rough cut. Transcript-led automatic cutting can miss tone, overlap, breaths, laughter and acoustic continuity; neither transcript agreement nor a model name proves listening precision. Do not sell automatic rough cutting as the mature default. Audio-capable seam review strengthens the handed-off cut, but is not evidence that fully automatic editing matches the user's judgment. Promote future automation only after measured audio-based quality, speed and correction-rate evidence on representative held-out episodes.

## Route Scope: v2 Main Path and Legacy v1

The recommended explicitly authorized end-to-end path uses the **Version 2 finished-audio / delegated release** section below. The following S00–S15, H2/H3/H4/H6 and draft-only commands are retained **legacy v1 references**, not extra user checkpoints for v2. An explicit request for local/human review or `agent_draft` selects its own existing lane; absence of publication intent does not authorize publication. Preserve the downstream v2 evidence, seal, authorization and idempotency contracts.


## Authority And Sources

1. Read the existing episode task/goal, session status and episode declaration before acting; initialize the owning task when absent. Do not require a private owner-specific folder or goal.md on a new installation.
2. Treat source media and raw Whisper outputs as immutable evidence.
3. Treat `podcast-release-package` as the downstream delivery contract; this Skill produces its inputs but cannot weaken its gates.
4. Treat Filmora/Verbatim/Subs references as evaluation evidence in calibration lanes. The separately authorized user-directed rough-cut recovery route (see Lessons from EP04) consumes frozen user project/export inputs under its own contract.

## Legacy v1 Modes

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

Sample clocks, immutable evidence and dependency invalidation apply to all routes. Human-receipt and S00–S15 restrictions in this section belong to legacy v1; v2 uses its actual delegated receipts and sole downstream publisher.

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

## Legacy v1 Local Entries

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
- **Intake (resolve once, record in decision_log):** read the supplied `_meta.md` role/channel declarations and rough-cut decision first; correlation verifies geometry, not speaker names. Ask only for gaps or conflicts. Use declared series/default policies for processing, cover and copy; the standard handed-off route preserves the user cut without requiring a fresh filler-policy interview.
- **Cadence:** classify new requirements (replacement/addition/note) when they arrive; write handoff/status after every gate; run reviews in parallel; batch low-risk content changes before one freeze (each freeze invalidates all three receipts); script-written timestamps; distinguish `cut-rN` from `revision-NNN`; write a handoff before launching long reviews.

## Personal defaults

Whisper tool/model/language defaults come from the personal config (`podcast-release-package/references/config.example.json`); per-episode values in `workflow-inputs-v1.json` and CLI flags win. `run_whisper_raw.py` defaults to `--language auto` unless the config sets `language`. `validate_benchmark_protocol.py --approval` requires `--expected-approver` (or config `approver`) and never accepts an arbitrary `approved_by`. The human review pages start with an empty Reviewer field.
