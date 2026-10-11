# Podcast Episode Release Package Contract v1.0

## Purpose

This contract defines the minimum local delivery standard for a public podcast episode. It is provider-aware enough for Transistor, while remaining a provider-neutral production target for the Workshop pipeline.

The manifest is the package SSOT. Audio, text, artwork, approvals, receipts, and previews are derived or referenced artifacts. HTML preview pages are never authoritative inputs.

## Package root

Recommended layout:

```text
<episode-package>/
├── manifest.json
├── media/
│   ├── episode-master.wav
│   └── episode-release.mp3
├── metadata/
│   ├── summary.txt
│   └── description.html
├── transcripts/
│   ├── transcript.txt
│   └── transcript.vtt
├── chapters/chapters.json
├── artwork/episode-artwork.jpg
├── promo/launch-copy.md
├── qc/
├── approvals/
├── receipts/
└── preview/
```

All manifest paths must be relative to the package root, resolve inside it, and not traverse symlinks outside it.

## Hard gates

| Gate | Requirement | Evidence |
|---|---|---|
| `G01_MANIFEST` | Schema v1.0, stable episode key and package revision | Manifest parse and semantic validation |
| `G02_PROVENANCE` | Immutable source identity and production run identity recorded | Source SHA-256, run key, source-relative timeline policy |
| `G03_RELEASE_AUDIO` | Final MP3 exists, identity matches, and is distinct from analysis/review audio | Path, bytes, SHA-256, media role |
| `G04_AUDIO_TECHNICAL_QC` | MP3; 44.1/48 kHz; mono/stereo; >=96 kbps; target -16 LUFS within ±1 LU; true peak <= -1 dBTP | Fresh ffprobe/ffmpeg measurement plus approved mastering QC |
| `G05_EDITORIAL_QC` | Final listen-through and editorial cut approved against the release-audio hash | Named approval, timestamp, audio hash |
| `G06_TRANSCRIPT` | Approved canonical TXT plus at least one timed VTT/SRT; identities match | File hashes and transcript approval |
| `G07_CHAPTERS` | Approved, strictly increasing chapters on the release-audio timebase | Chapter JSON and matching audio SHA-256 |
| `G08_METADATA` | Title, author, summary, description, type, season/number, explicit flag and language complete | Manifest and referenced text |
| `G09_ARTWORK` | Square RGB JPEG/PNG, 1400–3000 px, <=512 KB, approved | Fresh image probe and artwork approval |
| `G10_RIGHTS_CONSENT` | Content/music/artwork rights and minor consent resolved or explicitly not applicable | Rights declarations and reviewer identity |
| `G11_PREVIEW_INPUTS` | Accepted audio, artwork, metadata, chapters, transcript and QC can render one review page | Preview readiness checks |
| `G12_RELEASE_CANDIDATE` | A final approver accepts the exact release-candidate payload and release-audio hashes | Release-candidate approval |

The audio loudness target follows this project's frozen baseline. A future contract revision may introduce separate mono/stereo targets, but v1.0 deliberately uses one predictable release target.

## Canonical release-candidate hash

The manifest contains an approval, so hashing the complete manifest would create a circular dependency. `release_candidate.payload_sha256` is therefore the SHA-256 of the canonical JSON payload formed by removing `approvals.release_candidate` and serializing the rest with sorted keys and compact separators. The validator computes this value independently.

## Growth gate

`growth_ready` is reported separately but is part of the expected standard:

- descriptive, topic-forward title;
- episode-specific square artwork;
- approved transcript;
- listener-oriented summary and show notes;
- call to action with `{{share_url}}` placeholder before provider publication;
- at least one platform-neutral launch copy asset;
- optional guest kit, audiogram/vertical clip, localization, newsletter, and day-7/day-10 reshare plan.

The RSS `keywords` field is optional and must not be treated as a substitute for title, transcript, artwork, direct links, or promotion.

## Transistor field mapping

| Contract field | Transistor episode field/action |
|---|---|
| `provider.show_id` | `episodes create --show-id` |
| `episode.title` | `episode[title]` |
| `episode.author` | `episode[author]` |
| summary file | `episode[summary]` |
| description file | `episode[description]` |
| `episode.explicit` | `episode[explicit]` |
| `episode.type` | `episode[type]` |
| `episode.season/number` | `episode[season]`, `episode[number]` |
| release MP3 | `episodes upload`, then `episode[audio_url]` |
| transcript TXT | `episode[transcript_text]` |
| public artwork URL | `episode[image_url]` |
| optional video URL | `episode[video_url]` |
| publication plan | `episodes publish --status published|scheduled` |

The current CLI accepts generic `--set KEY=VALUE`. A downstream controller should pass arguments as an argv array, not an interpolated shell string. File-backed metadata should remain files until the controller constructs the provider call.

## Acceptance report contract

The validator emits:

```json
{
  "contract_version": "1.0",
  "contract_passed": true,
  "human_preview_ready": true,
  "growth_ready": true,
  "publish_authorized": false,
  "manifest_sha256": "...",
  "release_candidate_payload_sha256": "...",
  "release_audio_sha256": "...",
  "gates": [],
  "warnings": []
}
```

Downstream upload/publishing must reject a report if any bound hash no longer matches.

## Versioning

Changes to hard gates, required fields, or semantics require a new contract version. Editorial copy, examples, warnings, and optional growth recommendations may be clarified without silently weakening v1.0.
