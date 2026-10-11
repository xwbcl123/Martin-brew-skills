---
name: podcast-mastering
description: Create immutable MP3 delivery candidates with explicit synchronized channel mixing, mandatory series intro/outro, sample timeline mapping and fresh decoded-output QC.
---

# Podcast Mastering

Use `python3 scripts/mastering.py --input SOURCE --output-dir NEW_DIR` from this Skill. Default `encode_only` encodes MP3 at 192 kbps without a loudness filter. Inspect `report.json` actual codec and decoded sample count; a `.mp3` suffix does not establish an MP3 codec.

Select `--mode loudness_only` only when amplitude processing is within the task scope. This reuses the existing production workflow's pure loudness measurement, applies measured static gain plus an oversampled peak limiter with latency compensation, and measures the final encoded MP3 again. The limiter changes peak dynamics; the report states the actual method and gain. This avoids FFmpeg loudnorm's implicit dynamic fallback when linear constraints cannot be satisfied. The default pre-encoding peak headroom is 2 dB below the shared profile ceiling. Source clipping is not repaired. Use a new output directory with larger `--peak-headroom` if MP3 true peak remains above profile. Never relax the profile to pass.

Threshold authority is `../podcast-release-package/references/v2/profiles.json`, `profiles.podcast_mp3`; override location with `--profile-file`, identity with `--profile-id`. No copied threshold defaults. The production workflow's old CLI and approval gates remain intact; these candidate compute functions do not grant release permission.

Output: `delivery.mp3`, before/after measurement logs, encoding log and `report.json`. The report binds input, implementation, tool, profile and options; cache reuse verifies a separate report digest, the required output set, every output hash and freshly measured QC. Unsupported source sample rates are explicitly resampled to floating PCM first, then counted exactly; non-integer durations do not rely on guessed rounding. Partial/changed directories are rejected, requiring a new directory. A successful command may return `qc_status=fail`; publication requires passing checks. Container duration and decoded timeline can differ; encoder delay/padding is explicitly unknown when not extracted. ASR must consume this final delivery file.

Validation: `python3 -m unittest discover -s tests -v`. Fixtures synthesize short audio in a temporary directory and do not process private episodes.

Chapter tags are a separate metadata-only release derivative: use release-package `scripts/v2/chapters.py` after final audio selection. Keep the original delivery/report immutable and prove encoded audio and full decoded PCM unchanged. Do not re-run mastering or transcription solely because ID3 chapter metadata changes the file hash.

## Series music and synchronized multitrack input

For a named series, require `--series-profile PROFILE_JSON`. The profile must require **both** intro and outro, with relative asset paths, SHA-256, `sample_rate: 48000` and exact `samples`. Both assets must actually decode to stereo 48 kHz and last 3–5 seconds. Paths escaping the profile directory, missing/tampered assets and inaccurate metadata fail before output creation. Select actual generated candidates and keep audition evidence in the series asset directory. Never infer a series profile from an episode name; resolve the series profile through the calling workflow/configuration. A series invocation without that binding is incomplete. No family-specific absolute path is built into the compute code.

```sh
python3 scripts/mastering.py --input BODY_48K.wav --series-profile SERIES/series-profile.json \
  --mode loudness_only --output-dir NEW_CANDIDATE
```

For multitrack input use `--mix-manifest MIX_JSON` instead of `--input`. See [series-and-mix.md](references/series-and-mix.md). The manifest binds every source hash, selected audio stream and a 2-by-input-channel matrix. All tracks must share the actual 48 kHz clock and identical decoded sample counts. The renderer does not silently pad, truncate, normalize summing weights, or invent isolated speakers. Audit duplicated channels and microphone bleed before selecting the matrix. Matrix coefficients carry routing and gain; absent source isolation must remain explicit.

The series renderer concatenates intro, body and outro without speech overlap. `composed.wav` and `timeline.json` record half-open integer sample ranges and the exact body offset. `report.json` v3 binds the profile, assets, matrices, implementation and final MP3 hash. MP3 decoded sample accounting is a QC requirement. Intermediate mixing and composition use floating PCM. Both timeline trust flags stay false until independent acoustic boundary verification; passing sample counts alone does not establish aligned boundaries. This timeline maps the body input, so compose it with the rough-cut source mapping before converting raw-source timestamps. Crossfade regions remain non-invertible. Always transcribe **delivery.mp3** anew and rebuild chapter boundaries after bookends; translating an old transcript alone is insufficient. QC and an automated audition do not grant editorial or publication approval.
