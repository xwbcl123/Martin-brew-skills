# Filmora Golden Reference Calibration Contract v1.0

## Purpose And Authority

This contract converts a hash-bound Filmora human edit into evaluation evidence. It does not create a production edit and grants no approval authority.

Evidence layers are immutable and separate:

1. source render audio;
2. Filmora final edit reference;
3. monotonic alignment report;
4. reconstructed reference EDL;
5. automatic candidate EDL;
6. delta report;
7. human disagreement labels;
8. later policy revision citing label IDs.

Filmora is a development Golden Reference. Once an episode informs rules, prompts, thresholds or policies, that episode cannot be claimed as held-out evidence.

## Identity And Cache Contract

- Verify source audio, Filmora audio, alignment, auto EDL and reference EDL SHA-256 identities before consuming them.
- A run key includes all input hashes, algorithm/stage version and thresholds.
- Existing output may be reused only when its run key matches and the output parses successfully.
- Writes use partial-file plus atomic promotion. Credentials, presigned URLs and external mutations are forbidden.

## Alignment Acceptance

- Decode a mono analysis proxy at 8 or 16 kHz; never substitute it for release audio.
- Mapping must be monotonic and deletion-only on the source timeline.
- Confident reference coverage must be at least 95%.
- Anchor residual median must be at most 20 ms and p95 at most 80 ms.
- A failed alignment emits no evaluation-eligible reference EDL.

## Reconstructed Reference EDL

- Canonical timebase is 48 kHz source/render audio with integer half-open intervals.
- Every cut records the Filmora transition ID, start/end sample, duration, boundary uncertainty, confidence and eligibility.
- Default confidence bands: `high <= 0.40s`, `medium <= 0.80s`, `low > 0.80s`.
- Primary metrics use only high/medium eligible cuts. Low-confidence cuts remain visible and require review.
- Reconstructed cuts always declare `production_edl_eligible=false`.

## Delta Semantics

Match auto cuts to reference cuts one-to-one. A pair may match when their raw or uncertainty-expanded intervals overlap. Prefer highest intersection-over-union, then smallest boundary error.

Report:

- cut-level precision and recall;
- matched, auto-only and reference-only counts;
- start/end/mean/p95 boundary error in milliseconds;
- excluded low-confidence reference count;
- removed-duration diagnostics;
- category breakdown for auto-only items.

These are calibration diagnostics, not automatic production acceptance. A Filmora mismatch can reflect an auto-editor error, an acceptable alternative edit, a Filmora style choice or alignment uncertainty.

## Feedback Taxonomy

Every disagreement label uses one outcome:

- `auto_error`
- `reference_style_only`
- `acceptable_alternative`
- `alignment_uncertain`
- `needs_context`

Optional reason:

- `meaningful_speech`
- `laughter_or_emotion`
- `filler`
- `repetition_or_false_start`
- `recording_control`
- `silence`
- `technical_failure`
- `join_or_boundary_defect`
- `other`

Human labels are append-only derivatives. Policy changes must cite label IDs and create a new policy/run key.

## Human Gate Consolidation

The production interaction surface has two core gates:

- **Gate 1 — Unified UAT**: one local preview and one receipt binds final edit continuity, mastered release audio, transcript/subtitles, chapters, metadata, artwork and rights. H2/H3b/H4 artifacts may remain as internal evidence or compatibility receipts, but the user is not interrupted for three separate approvals.
- **Gate 2 — Distribution approval**: one action-specific receipt for `draft_upload`, `schedule` or `publish`. It binds the exact accepted package, payload, release audio, provider/show target and action. One action never authorizes another.

The release-package 12-gate validator remains the technical acceptance contract. Gate consolidation reduces human interruptions; it does not remove evidence, QC or hash binding.
