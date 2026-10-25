# Minimal recurring episode entry

## Standard handoff

User supplies access to:

1. Original media (a WFP alone contains no usable original sound).
2. A saved human rough-cut `.wfp`, with one identifiable source/timeline.
3. `_meta.md` declaring episode/show identity, media/project locations and speaker-to-stream/channel roles.

These can live at separate paths referenced by metadata. Existing rough-cut subtitles or an export help when available, but are not mandatory for direct-FFmpeg deletion-structure processing. Already finished audio skips the rough-cut requirement and enters at the earliest applicable missing stage.

## One prompt

> $podcast-production-workflow /goal 发布这一集：<单集目录绝对路径>。人工粗剪已完成；按 WFP 和 _meta.md 接手，独立验收通过后正式发布。

Identity in metadata avoids repeating show/episode IDs in chat. If missing, add them once. Without publication intent, complete the selected local work; do not invent distribution authority. The agent records the real instruction and later binds it to the frozen package; the user need not compute hashes or approve each stage again.

## Agent startup checklist

Use `scripts/startup.py setup` once when configuration is absent, then `scripts/startup.py check --episode-dir ... --mode local --config ...` for local intake; see the first-run guide for complete commands. These are offline internal checks, not user approval forms.

- Read the metadata and current user instruction before asking. Resolve source and WFP identity, exact episode/show, declared role/channel map, edit intent and output mode. Batch only critical gaps.
- Resume the existing task/goal, validate prior outputs, reconcile existing remote IDs. Do not repeat an ambiguous mutation or create a second episode to bypass recovery.
- Probe actual streams, channels, rate and duration; validate WFP source references and deletion structure. Use FFmpeg; no NLE operation or export-equivalence requirement on the standard branch.
- Read supported personal config and episode overrides. Check the selected route's FFmpeg, ASR model/runtime, actual audio-review provider, preview/browser and eventual publisher capabilities. Diagnose missing CLI entries separately from missing installation. Do not print secrets or install dependencies without applicable permission.
- Record evidence-backed `ready`, `needs_input` or `blocked` and the next stage in the owning task. This is an internal readiness report, not a user approval form or a promised success probability.
- Assign bounded work to available native subagents or external workers. Prefer the simpler working route. Fine audio listening requires actual audio input, regardless of execution fabric; independent reviewers do not review their own production.
- Preserve the human cut. Process/verify synchronized stems, master, transcribe final audio, calibrate anomalies, author listener copy, produce cover/chapters/reading edition, test real preview interactions, freeze, obtain the three v2 reviews and seal.
- Execute authorized publication through the sole publisher and read back API, media, share, RSS and every public transcript paragraph. Close with a user-readable acceptance summary and receipts.

## Stops and limits

No routine user checkpoint is inserted between stages on the authorized passing path. Stop only for a critical ambiguity, unrepairable required QC/review failure, concrete rights/privacy risk, missing required capability or uncertain external mutation needing reconciliation; continue independent local work where possible.

The mature baseline is human rough cut followed by agent completion. Transcript-led automatic rough cutting is optional experimental work; it cannot silently replace the handed-off edit. Report actual listening coverage and retain `user_reviewed=false` unless a real user review occurred.

This agent-facing entry does not add a CLI or JSON schema. `scripts/v2/workflow.py` remains a prepared-input planner/runner; one Skill invocation coordinates the missing authoring and review steps. A universal one-command media-directory runner still requires implementation and separate E2E validation.
