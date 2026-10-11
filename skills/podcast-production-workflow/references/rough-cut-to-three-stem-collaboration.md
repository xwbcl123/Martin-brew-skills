# Rough cut → recovered EDL → three-stem mastering: human/agent collaboration protocol

Status: v2 (EP04 lessons, 2026-10-11; revised after three independent review rounds recorded in the owner's private session notes).
A user-facing companion guide exists in the owner's private knowledge base (not included here).
History, timings and rationale live in the owner's private EP04 session notes, not here.

## Entry conditions and authority

This route applies only when the user requests reconstruction of their rough cut onto the original speaker stems. Frozen project/export media are production inputs; calibration artifacts remain evaluation-only and are never promoted by relabeling. Create a separately identified production candidate with its own source bindings and validation. A finished delivery supplied for transcription/enrichment skips this route unless reconstruction is requested.

User acceptance may settle disclosed editorial seam uncertainty only. It does not replace v1 human gates, v2 independent content/experience/implementation reviews, seal validation, or exact episode/action/hash-bound publication authority. Stages S0–S6 are local and do not authorize third-party mutation. S7 hands off to the selected downstream contract; it is not a publish command.

Supported edit class: **deletions only** (constant speed 1.0, no reordering, insertions, music, bookends, time-varying processing). Structural deletions with unknown transition effects remain candidates; admit a transition only if the versioned model supports it and its residual/listening evidence passes. Unsupported rate changes, insertions, reordering or unmodelled fades stop automatic reconstruction and go back to the user. Do not infer that an effect is disabled because its parameters are unreadable.

## Inputs: the Filmora project (.wfp) first, audio reconstruction as fallback

Observed on EP04 (Filmora 16.0.10.13397; not a format guarantee for other versions): the saved project is a ZIP (members are both stored and deflated) of JSON. The selected leaf timeline had 229 audio clips (228 internal deletions), constant speed 1.0, one `streamId`, a monotonic source, no timeline gaps and audio/video ranges identical, reached via the project's current timeline → its soloed nested clip. Use `scripts/wfp_extract_edl.py PROJECT.wfp --inventory`, then `--output` (selectors `--timeline-member/--timeline-id/--track-index` when the chain is not unique; it fails closed otherwise). The EP04 extraction output is kept in the owner's private session notes.

- Nominal positions are **coordinate resolution, not acoustic accuracy.** For delta = user-accepted refined candidate (R007) source_start − nominal: −27.0417…+26.3125 ms, median −0.375 ms (182/229 > 5 ms; 34/229 > 20 ms); timeline starts matched on 226/229. These are differences from a user-accepted candidate, not a Filmora precision specification or proof of cut error. EP04's recorded mapping search used ±4800 samples (±100 ms); a ±50 ms first pass must report edge hits, ambiguity and failed matches and keep them unresolved rather than assert success.
- The examined leaf's effect records expose names (`fade`, `clip_volume`, `change_channel`, `volume`, `ducking`) but no readable parameters; the extractor does not reconstruct fade/gain/denoise processing. Other `.wfp` records may contain readable parameters—do not generalize. Unknown effects require audio validation and stay unverified if reconstruction fails.
- Search for the `.wfp` before anything else: default Filmora folder on this machine `~/Movies/Wondershare Filmora Mac/App-support-def/Wondershare Filmora Mac/Projects/`; if not found, ask for the actual path. Do not search only the podcast workspace (EP04 lost hours that way). Never select a project by mtime.
- **Bind one export/project/source tuple** by hashes, selected timeline/track, actual decoded geometry, source identity and audio anchors across the full mapped timeline. Project save metadata and export provenance are supporting evidence only. A project saved after export, mismatched clip order/content, unexplained duration/offset, stale source reference or ambiguous duplicate project enters `mismatch_pending`: obtain a matching saved revision/re-export or an explicitly chosen audio-only recovery route. Duration agreement alone is never sufficient. Preserve full export evidence and record any tail-trim range and derivative hash separately.
- No usable project: reconstruct from the export audio (S2 below), time-boxed.
- Track roles are asked, not guessed (EP04: stream 0 = speaker A left / speaker B right, stream 1 = host dual-mono, stream 2 silent). Record the audio-relative index and the absolute container stream index separately; a Filmora `streamId` is not an FFmpeg index.

## Roles

| Human (target ≈15 min of extra communication, excluding their editing) | Agent |
|---|---|
| T0 intake answers (≈5 min) | Stems, hashing, project/export binding, tail/offset checks |
| T1 cut in the NLE, save, export per the guide | Nominal EDL → sample-level refinement → seam table |
| T2 one listening audit (target ≤10 min) | Rebuilt-vs-export check; stems cut by one EDL |
| T3 explicit accept / correct decisions | Three-stem mastering, transcription, enrichment, package, reviews, publish per other contracts |

The agent never asks the human to align, convert, split or inspect files.

## Stages and gates

**S0 Intake.** Record in decision_log (script-written timestamps): track roles and whether any track is duplicated to L/R; filler policy per token with source counts; three-stem vs single mix; cover limits (RGB square 1400–3000 px, ≤512,000 B per the local `podcast_mp3` profile; JPG/WebP recommended); copy-button acceptance; publish authorization wording. Reconcile contradictions immediately.

**S1 Prepare.** Extract stems from the frozen raw MP4 (48 kHz mono PCM24; hash; equal lengths). Check the export spec (48 kHz PCM, duration, digital-zero tail, clipping, level steps, SRT offset). Hash everything.

**S2 Nominal map.** With a `.wfp`: extract and validate (above). Without: anchor correlation of export vs a reference mix gives a monotonic path whose jumps are deletions. Non-monotonic or unmatched content stops the run.

**S3 Seam refinement at native rate.** Freeze a **versioned measurement policy** before classification: target sample rate, window/hop samples, lag-search bounds, energy floor, minimum usable evidence per side, correlation threshold, peak-ambiguity rule, crossfade model/maximum length, and thresholds for normalized residual and seam-local peak error. An unset or unvalidated policy leaves the candidate pending; EP04 values are pilot settings, not universal gates. Per boundary record samples, lag, correlation, crossfade fit and tier:
- **C1** — sufficient independent usable windows, a unique consistent alignment and passing integrity checks.
- **C2** — bounded uncertainty under the declared policy; *not* sample-exact proof.
- **C3** — insufficient evidence, conflicting offsets, edge hits or failed residual checks.

(Tier names C1/C2/C3 are used so they are not confused with the T0–T3 human touchpoints.) Exact dual-mono channels count as one witness; select one verified channel without summing duplicate gain. A transition inferred for one speaker from another speaker/reference remains proxy-only and is labelled.

**S4 Rebuilt-vs-export check.** Fit gains only on mapped, non-transition training spans; freeze them and verify on disjoint spans. For each non-silent window report `residual_db = 10*log10(sum((rebuilt-export)^2)/sum(export^2))`; below the declared energy floor report absolute error and “insufficient correlation evidence” (silence is not correlation success). Compare all output channels on overlapping windows, add short windows around every seam, and preserve full-duration coverage including unmeasurable regions. Separately verify each stem's retained samples, timebase, count and source mapping: a matching mix cannot prove each stem or semantic correctness, and averaged windows can hide short clicks.

**S5 Human audit.** One self-contained page (served with the project's Range server). It lists **every unresolved C2/C3 seam** with its ID, bounded uncertainty, evidence limits and current candidate binding. C3 items and residual-flagged windows require the A/B audit (≈6 s, export vs rebuilt) with choices *acceptable / needs correction / cannot judge* and an optional free-text correction. C2 items may be grouped for explicit acceptance under the frozen policy, but the user must see the complete group membership and the disclosed uncertainty, with optional A/B expansion. An explicit tickbox “I accept the listed uncertainty” binds the **exact displayed item IDs**; omitted or unsubmitted items stay pending. Only resolved C1 items may be omitted. Silence, an unsubmitted form and “cannot judge” are **not** acceptance. The target is ≤10 minutes; if mandatory items exceed that, report the estimate and obtain a scope/time decision—never silently omit items.

**S6 Freeze.** Freeze only mechanically valid candidates. Each unresolved seam stays pending until the user explicitly accepts the disclosed uncertainty or supplies a correction. The receipt binds episode/revision, source/export/project hashes, EDL and rendered-stem hashes, policy/risk-table hashes, actual human-interaction provenance and each presented item's decision. Record explicit acceptance as **user acceptance**, never as an independent ACCEPT or sample-exact verification. Re-rendered audio or changed boundaries invalidate affected decisions. Technical source-identity, clock, containment or render-integrity failures cannot be waived by listening acceptance. All three stems share clock, start and frame count.

**S7 Handoff to downstream contracts.** Per-track assessment/denoise (record `denoise_applied` and reason), latency/compensation per chain, balanced mix, series bookends, loudness/true-peak per the active profile, transcription of the final MP3, enrichment, package, reviews, publish—each under its own skill.

## Time budget

The 45-minute checkpoint reports elapsed time, mapped coverage, unresolved seams, mismatch classes and remaining work. At 90 minutes stop refinement, retain the candidate and request an explicit extension or alternative route; a timeout never grants acceptance. The new flow's total duration is a target to be measured on the next episode.

## Anti-patterns observed on EP04

- Reconstructing the cut with seven sequential one-off scripts and ~25 probe scripts instead of one tool with a policy and tier table.
- Applying a strict independent ACCEPT to millisecond seam offsets and rebuilding after every rejection; nominal-cut-only QA missed the actual switch-centre step.
- Not finding the saved Filmora project (searched only the workspace) and rebuilding blindly.
- Assuming Track 2 was a composite from correlation instead of asking.
- Reading “use the Filmora cut” as “drop the stems”, and later “fast path” as “do not recover the cut”—both contradict the intended workflow.
- Letting the reviewer queue gate the primary instead of running reviews in parallel.

## Tooling status

`scripts/wfp_extract_edl.py` (+ `tests/test_wfp_extract_edl.py`, 31 tests) implements only the nominal extraction; automatic selection requires an unambiguous audible route and identity wrappers, an explicit selector is a diagnostic extraction whose export association stays unverified. Refinement, the rebuilt-vs-export check and the audit page are not yet one tool; prototype scripts from EP04 exist only in the owner's private workspace. Until consolidated, follow the gates above, not the EP04 iteration pattern.
