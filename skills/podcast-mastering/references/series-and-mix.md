# Series and mix contracts

`series-profile.json` is stored with reusable assets outside the generic Skill:

```json
{
  "schema_version": "1.0",
  "series_id": "example",
  "intro_required": true,
  "outro_required": true,
  "intro": {"path": "intro.wav", "sha256": "ASSET_SHA256", "sample_rate": 48000, "samples": 201600, "gain_db": 0},
  "outro": {"path": "outro.wav", "sha256": "ASSET_SHA256", "sample_rate": 48000, "samples": 201600, "gain_db": 0}
}
```

Asset hashes are file hashes; `samples` is the observed decoded frame count per channel. The optional finite `gain_db` adjusts each bookend before overall mastering. The renderer enforces 3–5 seconds even if descriptive profile text requests another duration. In episode orchestration, absence of a profile for a named series must stop that series invocation. Anonymous finished-audio intake retains the legacy single-input route.

`mix.json` can reference an audio file or a video with multiple audio streams. `audio_stream` is zero-based among audio streams, not the global FFprobe stream index. Paths are absolute or resolved relative to the manifest. Matrices define the two output channels; coefficients specify linear amplitude, including any gain. For example, map channel 0 from one route and channel 1 from another into a centered stereo mix, without counting the duplicated microphone twice:

```json
{
  "schema_version": "1.0",
  "tracks": [
    {"path": "route-a.wav", "sha256": "SOURCE_A_SHA256", "audio_stream": 0, "role": "near microphone with bleed", "matrix": [[0.5, 0], [0.5, 0]]},
    {"path": "route-b.wav", "sha256": "SOURCE_B_SHA256", "audio_stream": 0, "role": "composite route", "matrix": [[0, 0.5], [0, 0.5]]}
  ]
}
```

Apply a common rough-cut EDL to every route before mastering. Actual clock/range equality is checked on decoded frames. This command handles channel mixing and music composition, not speaker separation or editorial cutting. Caller-supplied coefficients require headroom analysis; pre-existing source clipping cannot be restored by the final loudness limiter.

Output `mixed-body.wav` and `composed.wav` use floating PCM32 and preserve values above full scale until explicit loudness processing. Matrices and music gains run in floating point before final MP3 encoding. Hashes and `composition_timeline` bind the chain. `sample_accounting` checks exact decoded frames against explicit pre-mastering resampled floating PCM when a new sample clock is needed; `timeline_trusted` and `mapping_valid_on_decoded_delivery` remain false until separate acoustic boundary verification. Cache reuse checks the report digest, exact required artifact set, and fresh decoded-audio measurements against the QC profile. The final output still requires final-audio ASR, chapter review and release-package gates.
