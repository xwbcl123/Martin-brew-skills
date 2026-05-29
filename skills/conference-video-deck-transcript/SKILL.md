---
name: conference-video-deck-transcript
description: Use when the user wants to turn a conference, keynote, webinar, meeting, or YouTube replay video plus transcript/agenda into per-speaker Deck PDFs and Transcript Markdown files, with numbered filenames and archived processing artifacts.
license: Internal
---

# Conference Video Deck Transcript

## Goal

Produce a clean per-speaker package from a long conference video:

- `NN_speaker_slug-Deck.pdf`
- `NN_speaker_slug-Transcript.md`
- optional `event_manifest.csv`

Move all non-final process artifacts to an archive folder so the final output folder stays reviewable.

## Workflow

1. **Locate source material**
   - Prefer the user's vault/search tooling for local clipping files when available.
   - Read the video URL/path, full transcript, agenda, and any existing notes.
   - Do not guess facts that can be read from local files.

2. **Build the speaker segment map**
   - Create CSV or JSON with at least: `slug`, `speaker`, `title`, `start`, `end`.
   - Use sortable slugs such as `01_wim_de_meyer_opening`.
   - Time source priority: agenda/transcript explicit times, then host transition markers, then user clarification.
   - Optional CSV/JSON field: `keep_ranges`, using candidate frame numbers such as `5-17;20;23-25` after contact-sheet QA.

3. **Prepare media**
   - Use `yt-dlp` for online video and `ffprobe`/`ffmpeg` for inspection.
   - Prefer 720p or 1080p when stable; downgrade if download reliability matters more than image sharpness.
   - Store source media in the archive/media area, not the final deliverable folder.
   - Python script dependencies are listed in `requirements.txt`.

4. **Extract Deck PDFs**
   - Determine the presentation crop from sampled frames. For livestream layouts, crop the projected deck area rather than the whole stage.
   - Run `scripts/extract_decks.py` with the video, segment map, crop, output dir, and work dir.
   - Inspect contact sheets; if stage/audience/Q&A/transition frames remain, add `keep_ranges` to the segment map and rerun.

5. **Split transcripts**
   - Run `scripts/split_transcripts.py` with the full transcript and same segment map.
   - Preserve original timestamps.
   - Add frontmatter with `speaker`, `talk`, `video_range`, and matching `deck`.

6. **Archive artifacts**
   - Run `scripts/archive_artifacts.py`.
   - Final output folder should contain only `*-Deck.pdf`, `*-Transcript.md`, and optionally the manifest.
   - Archive raw frames, selected JPGs, contact sheets, scripts, partial downloads, source media, and debug files.

7. **Verify**
   - Count matching deck/transcript pairs.
   - Confirm every number has both a `-Deck.pdf` and `-Transcript.md`.
   - Confirm the final folder has no accidental JPG/raw frame/script artifacts.
   - Record caveats such as low video resolution, uncertain speaker boundaries, or crop quality.

## Script Quickstart

Create `segments.csv`:

```csv
slug,speaker,title,start,end,keep_ranges
01_speaker_name,"Speaker Name","Talk Title",0:04,11:49,
02_next_speaker,"Next Speaker","Second Talk",11:49,29:16,5-24
```

Extract decks:

```powershell
python skills\conference-video-deck-transcript\scripts\extract_decks.py `
  --video path\to\video.mp4 `
  --segments segments.csv `
  --output-dir path\to\final `
  --work-dir path\to\archive\processing-artifacts `
  --event-prefix "YYYY-MM-DD_event_" `
  --crop 0:118:858:482
```

Split transcripts:

```powershell
python skills\conference-video-deck-transcript\scripts\split_transcripts.py `
  --transcript path\to\full-transcript.md `
  --segments segments.csv `
  --output-dir path\to\final `
  --event-prefix "YYYY-MM-DD_event_"
```

Archive non-final artifacts:

```powershell
python skills\conference-video-deck-transcript\scripts\archive_artifacts.py `
  --final-dir path\to\final `
  --archive-dir path\to\archive\processing-artifacts `
  --work-dir path\to\work
```

## Naming

Use sortable numeric prefixes:

- `01_speaker_slug-Deck.pdf`
- `01_speaker_slug-Transcript.md`

For dated clipping workflows, preserve the event prefix:

- `YYYY-MM-DD_event_01_speaker_slug-Deck.pdf`
- `YYYY-MM-DD_event_01_speaker_slug-Transcript.md`

## Boundaries

- This skill produces aligned source material packages.
- It does not summarize the conference, write insight reports, or infer business conclusions.
- Keep content-analysis work in a separate summary/research skill after the package is generated.
