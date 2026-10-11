# Content interface: legacy plain text and public_content v1

Optional `metadata.artwork` may retain canonical series-profile/reference hashes, style ID, frozen prompt hash, selected cover hash and a trusted selection receipt reference. See [series-artwork.md](series-artwork.md). It does not select an image, authorize publishing or change the required final raster `cover_path`.

The legacy format below uses UTF-8 plain text, separated into paragraphs by blank lines. HTML is displayed as literal text. No remote script/font dependencies are used. Both CLI commands accept `--content JSON --package-root DIRECTORY`; build additionally requires `--output PATH` within that root. Relative output paths resolve from the current working directory. Asset paths must be package-relative, nonempty files; traversal and symlinks are rejected. Build writes the requested page and sibling artifacts, so use a dedicated preview directory.

Required JSON fields:

- `title`, `show_title`, `summary`, `description`, `show_notes`, `launch_copy`: nonempty strings, reflecting the actual episode. Public payload must use these same final values.
- `language`: detected source language code, such as `en` or `zh`.
- `ai_disclosure`: honest nonempty statement. Unknown generator remains unknown. For synthetic audio, this statement must also enter the actual outbound description/show notes.
- `cover_path`: final PNG/JPEG/WebP package-relative path; caller verifies square dimensions and visual quality.
- `audio_path`: final delivery MP3/M4A/WAV/OGG/OPUS/AAC package-relative path.
- `segments`: all aligned source segments as `{ "id": "s0001", "start": 0.0, "end": 2.4, "text": "Original text", "speaker": "optional verified identity" }`. IDs are nonnegative integers or nonempty strings; identity comparisons normalize via str (so 0 and "0" collide). IDs are unique, times finite nonnegative seconds, ends exceed starts, starts ordered. `duration` should contain measured final playback seconds; all segment ends must fit it. If omitted, maximum segment end is used for display only.
- `chapters`: ordered `{ "start": 0, "title": "Opening", "summary": "What this part covers", "source_segment_ids": ["s0001"] }`. Starts must increase and fit duration. References must exist; independent editorial review confirms chapter placement actually matches those sources.
- `reading_transcript`: full paragraph objects `{ "text": "Readable paragraph", "source_segment_ids": ["s0001", "s0002"] }`. The union must cover every aligned source segment. This check cannot prove semantic completeness: independent review must confirm the text actually preserves the complete conversation rather than attaching all IDs to an abstract.
- `resources`: `{ "title": "Source name", "url": "https://..." }` list; empty when none supplied/verified. Only HTTP(S), without embedded credentials.
- `metadata`: `{ "reading_language": "zh", "reading_mode": "translation", "corrections": [] }`. Mode is `edited` for same-language editorial text or `translation`. Different source/reading languages require translation. Corrections are `{ "source_segment_id": "s0001", "original": "ASR token", "corrected": "Reviewed token", "reason": "Evidence and scope" }`.

Optional:

- `status`: `{ "label": "本地预览 · 待核验", "publication_url": "https://confirmed-episode-page" }`. This is caller evidence, not inferred by renderer; omit URL before readback. A renderer build never certifies this label.
- `assets`: additional human-facing `{ "title": "Subtitle file", "path": "transcripts/full.vtt", "kind": "download" }`. `image` and `audio` embed native media; `text` reads and renders the complete file; `download` opens/downloads the entire original. Raster-only for image type. Use this list for every required public/review role beyond standard outputs.
- `audit_links`: `{ "title": "Audio QA report", "path": "qc/audio.json" }`, shown only in collapsed technical details.

Generated sibling artifacts: `aligned-transcript.json`, `reading-transcript.json`, `transcript.txt`, `reading-transcript.txt`, `show-notes.txt`, `launch-copy.txt`, `chapters.json`, `summary.txt`, `description.txt`, `ai-disclosure.txt`, `content-metadata.json`, `enrichment-manifest.json`. The manifest binds content JSON, audio, cover and generated outputs with SHA-256, and records reference coverage. It is an enrichment artifact, not a sealed release manifest or permission grant. Attach its current hash to the surrounding release package.

The page carries no external mutation logic. Serve package root over local HTTP so media relative links and clipboard work. Build success is local technical readiness only; browser experience and publication decisions remain external evidence.

## public_content v1 (new packages)

`public_content` is an authoring extension inside package contract 2.0; never pass it as an API field. The public description is rendered once from these nodes, with `public_html(content)`, `public_text(content)` and `public_summary(content)` in enrich.py. No additional summary, legacy notes, resources, chapters or disclosure is concatenated by the publisher. Summary is the first paragraph as plain text, at most 240 Unicode code points; it is a separate compatibility field. New content may omit legacy `summary`, `description`, `show_notes`, `ai_disclosure`; if retained they are compatibility copies, not render inputs.

```json
{"public_content":{"version":1,"nodes":[
  {"type":"paragraph","children":[{"type":"text","text":"一起聊聊这个选择。"}]},
  {"type":"heading","level":2,"children":[{"type":"text","text":"这一集聊什么"}]},
  {"type":"list","ordered":false,"items":[[{"type":"strong","children":[{"type":"text","text":"动手试一次"}]}]]},
  {"type":"erratum","children":[{"type":"text","text":"事后查证，发现搞错了：这里其实有一个修复步骤。"}]},
  {"type":"chapters"},
  {"type":"resources"},
  {"type":"transcript","url":"https://example.org/transcript","label":"完整文字稿"}
]}}
```

Inline nodes: `text` with text; `strong` / `em` with children; `link` with url and children. Blocks: paragraph / erratum with children, heading with level 2 or 3 and children, list with boolean ordered and a list of inline-node lists. Maximum inline nesting 8. Exact keys only: arbitrary tags/attributes, script/style and unknown versions/types are rejected. Text resembling HTML is escaped, never interpreted. URLs require HTTP(S) without credentials/control characters. Chapters/resources resolve against the validated top-level lists and each reference kind appears at most once. Transcript requires a verified actual URL; this renderer does not emit unverified platform placeholders. Literal public wording remains an editorial responsibility.

Public body HTML is saved as `description.html`; `description.txt` and `show-notes.txt` contain the same plain fallback. Optional AI-generated-audio disclosure is a short public paragraph node when applicable; do not publish unknown-generator boilerplate. Longer correction provenance stays in metadata. The preview places chapters and resources in their dedicated interactive sections, retaining core prose in the notes section. All legacy surfaces and local downloads remain available. Use `--output PACKAGE/preview/preview.html` or `episode.html`; both filenames work.

## Terminology confirmation

Optional `terminology_review` has exactly `bindings` and `terms`. Bindings are `episode_key` (nonempty string), plus lowercase SHA-256 strings `audio_sha256`, `timeline_sha256`, `content_sha256`, `glossary_sha256`. Audio binds the actual current delivery file. Timeline binds the caller's immutable final timeline identity; the surrounding package validates that source. Content hash is `terminology_content_hash(content)`: UTF-8 JSON, ensure_ascii=False, sort_keys=True, compact separators, excluding only top-level terminology_review. This excludes self-reference while binding the rest of the content. Glossary binds the current private source snapshot; do not embed its full contents.

Terms have exactly `{id,current,alternatives,start,end,reason}`. IDs are unique strings, alternatives a string list, and finite times fit the final duration. Include only episode-relevant words and a short natural reason. Default-closed details permit listening, confirm/edit, an explicit user attestation and JSON download. The UI cannot update the provider. Export has version=1, origin=user_preview, attestation="I reviewed these term decisions", bindings and decisions `{term_id,decision:confirm|edit,text}`.

`import_terminology_decisions(content, export)` rejects unknown/missing fields, stale bindings, changed content, duplicate/unknown terms and changed confirm text. It returns provenance `user_preview_attestation`, never human-confirmed. Browser JSON is not identity proof: the transcription calibration importer separately requires trusted external actor_kind and source_ref before granting user-confirmed precedence. Agent callers must retain agent provenance. The authoritative ledger handles replay and rebuilding downstream artifacts. A user export is a next-revision input; keep old sealed packages intact.
