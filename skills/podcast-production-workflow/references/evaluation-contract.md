# Smart Edit Evaluation Contract

## Primary Labels

Use blinded human labels:

- `must_cut`: leaving the event is an editorial failure;
- `acceptable_cut`: removal is stylistic and not required;
- `must_keep`: removal changes meaning, speaker identity, emotion, turn-taking or natural continuity.

The Filmora export is a calibration reference without a source EDL. Align waveform/features first; score only confident regions. Do not translate its MP3 timestamps directly into source cuts.

## Primary Thresholds

- must-cut candidate recall >= 0.95;
- recording-control and technical-failure recall = 1.0;
- applied-cut precision >= 0.98;
- must-keep false cuts = 0;
- meaning-changing or word-truncating cuts = 0;
- audible join defects = 0.

## Timeline Thresholds

- duration accounting and mapping round trip <= 1 source sample;
- Filmora comparable-speech coverage >= 0.95;
- alignment anchor residual median <= 20 ms, p95 <= 80 ms;
- otherwise the reference score is `invalid`, not pass/fail.

## Secondary Diagnostics

Filmora interval overlap, total removed duration, residual filler counts and normalized transcript similarity are diagnostics. They cannot override primary safety metrics or drive a rule change alone.

Freeze policy/prompt/challenge-set revisions before opening held-out labels. Episode 001 can establish fixture acceptance only; reusable-editor acceptance requires two additional held-out episodes.
