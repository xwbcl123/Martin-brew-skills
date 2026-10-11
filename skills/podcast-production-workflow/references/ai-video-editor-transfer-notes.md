# `timkulbaev/ai-video-editor` Rough-Cut Transfer Notes

Audited upstream revision: `cce2114019ca237a5e38468789ddac5eb764b9bd` (2026-08-29). Repository: <https://github.com/timkulbaev/ai-video-editor>.

## Source Inventory

- Read: `SKILL.md`, `README.md`, `config.default.yml`.
- Read implementation: `src/pipeline.py`, `src/config.py`, `src/cli.py`, `src/steps/detect_speech.py`, `transcribe.py`, `edit_decisions.py`, `assemble.py`, `enhance_audio.py`, and supporting JSON/FFmpeg utilities.
- Read tests: `tests/test_edit_decisions.py`, `tests/test_config.py`.
- Not executed or installed. Capability conclusions come from inspected source, not README claims.

## Confirmed Architecture

```text
16 kHz extract → Silero VAD → word-timed faster-whisper
→ keep-segment rules → per-segment frame-accurate FFmpeg re-encode/concat
→ optional audio/color/hook/chapters → final encode
```

Confirmed useful patterns:

1. Keep VAD and ASR as independent evidence, then fuse them in edit-decision logic.
2. Detect explicit restart phrases and repeated multi-token sentence starts before filler trimming.
3. Apply breathing-room padding after all edit decisions and merge overlaps afterward.
4. Separate machine JSON on stdout from progress JSONL on stderr.
5. Deep-merge versioned configuration instead of hard-coding every threshold.

## Safe Transfers Into This Workflow

- Added candidate-only `explicit_restart_phrase` and `repeated_segment_start` detectors. They emit source-timeline evidence and never apply cuts.
- Existing local architecture already satisfies the stronger equivalents of late padding, role-separated analysis/render audio and structured output.
- A future VAD lane may add `short_burst` candidates, but blanket auto-removal is prohibited until Golden Reference labels demonstrate acceptable false-cut risk.

## Rejected Or Deferred Patterns

- Upstream removes every VAD speech burst shorter than a configurable duration (default 2s), treating coughs, markers and false starts as equivalent. In a three-person Chinese family conversation this can delete short meaningful replies or emotion; do not transfer as automatic authority.
- Upstream restart phrase handling drops an entire merged speech segment. We transfer only a bounded candidate from segment start through the marker, still requiring review/calibration.
- Upstream uses floating seconds and ephemeral temp state, has no content-addressed cache, immutable provenance, atomic stage promotion, resumable manifests or approval binding. Keep the Life-OS 48 kHz integer-sample and recovery contracts.
- `crossfade_ms` is documented as reserved and not used by the upstream pipeline. Do not treat that README/config field as implemented splice safety.
- Optional OpenRouter features silently skip when credentials are absent. This conflicts with auditability; our workflow records explicit `skipped/blocked` states.
- Per-segment video re-encoding is frame-accurate but expensive and lossy across many cuts. Revisit only in the future video workflow, not the audio master path.

## Three Critique Filters

- **Systems thinking**: upstream temporary state and all-at-once orchestration make interruption expensive. Minimal verification for any transferred detector is content-addressed replay plus delta comparison against the Filmora reference.
- **Critical thinking**: README claims “frame-accurate assembly,” but it does not prove sample-accurate audio joins or crossfade use. Evidence that would change adoption is a timestamp/render-map test with join QC and failure recovery.
- **Cognitive fallacy**: a talking-head Russian/English success case cannot be generalized to three-speaker Chinese podcast speech. Treat all transferred heuristics as candidate generators until labeled disagreement data supports promotion.

## Adoption Decision

Adopt the modular candidate patterns, not the upstream execution architecture. The Filmora calibration loop is the promotion gate: a detector moves from `candidate_only` toward the aggressive review EDL only after measured delta improvement and zero observed meaningful-speech false cuts on labeled development data, followed by separate held-out episodes.
