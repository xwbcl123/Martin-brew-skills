---
name: podcast-enrichment
description: Create grounded podcast reading transcripts, show notes, chapter copy, promotion assets and an immersive single-episode local HTML preview from final delivery audio and aligned transcripts. Use after ASR; publication remains with podcast-release-package.
---

# Podcast enrichment

For cover creation, refresh or recurring series artwork, read [series-artwork.md](references/series-artwork.md). Automatically resolve the show profile from source/package identity and the brand profile registry; an external `profile` path or `metadata.artwork.profile_ref` overrides discovery, following [artwork-profile.md](references/artwork-profile.md). Resolve the series' approved artwork profile from the supplied brief or brand dashboard before using generic branding. Reuse its actual reference images and locked style families; vary episode composition and copy from current source content. A style-family approval is not selection of an episode image. Keep candidates separate from the final `cover_path` and external publication. The renderer consumes existing artwork; it does not generate or select covers.

Turn the complete delivery-aligned transcript into useful listening and reading material. Read [content-interface.md](references/content-interface.md) when building input JSON. The deterministic renderer validates supplied copy; it does not generate facts, translate, perform ASR, or certify semantic completeness.

Use final delivery audio and its current-hash transcript as the source. Read the entire transcript before preparing copy. Preserve the original-language aligned text; label a different-language reading edition as translation. Include every source segment in the reading edition, keep uncertainty and disagreement, and record substantive term/speaker corrections with source segment IDs. Never invent speaker identity or voice generator. Keep promotional copy specific to what is said; distinguish a speaker's claim from an independently verified fact. Cite supplied or verified source URLs only.

For new packages, author the listener-facing description once as public_content v1 controlled nodes; derive HTML, plain fallback and the first-paragraph summary. Keep corrections brief and conversational (for example, “事后查证，发现搞错了：”). Longer investigation and provenance belong in metadata. Include meaningful timestamped chapters, complete reading transcript and launch copy. Synthetic-audio disclosure, when applicable, is a concise public paragraph; human-recorded audio needs no unknown-generator boilerplate. Record the source references behind reading paragraphs and chapters. Cover creation is a design task: use the applicable image/brand skill and retain the actual final raster artifact. This renderer accepts existing artwork and never creates a placeholder cover. Resolve artwork through the external profile contract; when no profile is supplied, use neutral editorial styling based on the supplied show identity, without borrowing another show or personal brand.

Build the local bundle:

```sh
python3 .agents/skills/podcast-enrichment/scripts/enrich.py validate --content /absolute/content.json --package-root /absolute/package
python3 .agents/skills/podcast-enrichment/scripts/enrich.py build --content /absolute/content.json --package-root /absolute/package --output /absolute/package/preview/episode.html
```

The output is a single-episode editorial page with actual audio, square cover, complete reading/chronological text, searching, seekable chapters, exact clipboard copy and downloadable full assets. Add every other applicable human-facing output through `assets`; technical reports go in collapsed `audit_links`. Keep public text consistent with the eventual release payload; the content JSON remains the authoring source, not a second independently edited metadata copy.

Add a default-closed terminology_review panel for provisional episode terms. User Scout confirmation takes precedence. Only autonomous mode uses independent model opinions; keep disagreements and next-day confirmations without stopping an authorized release for textual uncertainty. Export is a user-attested local input, not proof of actor identity or a platform mutation. Import through the trusted transcription calibration boundary, reject stale decisions, and rebuild derived outputs.

Default state is `本地预览 · 待核验`. Set `status.label` to `代理已核验 · 供事后复核` only after actual independent QA. Never infer user acceptance, published state, cleared rights or experience readiness from successful rendering. Publication links require confirmed actual URLs. The generated manifest intentionally records `experience_ready: false`; the release-package acceptance receipt owns the external visual/interaction conclusion.

Serve the package over local HTTP for real browser review. Verify screenshots at 1440px and 390px, native play/pause/seek/speed, chapter navigation, a late-transcript search, both text tabs, exact clipboard readback and full asset links. Source inspection is not browser QA. Review source-to-reading semantic coverage independently: ID coverage proves references, not fidelity. Save screenshots and evidence outside this skill. Rebuild after input changes and invalidate earlier acceptance receipts.

Run reusable checks with `python3 -m unittest discover -s .agents/skills/podcast-enrichment/tests -v`. These cover text escaping, hostile URLs, containment/symlinks, missing files, timeline, complete source reference coverage and actual output hashes. Media decoding, square cover visual quality, factual grounding and browser usability require the surrounding workflow's checks.

For repeatable local QA, use `python3 scripts/serve_preview.py --directory PACKAGE_PARENT --port 8769`. It binds only 127.0.0.1 and supports byte Range requests; verify a 206 response before accepting native audio/chapter seeking. A plain server returning 200 for Range can reset seeks to the start.

The Transistor standalone transcript page uses the complete `reading_transcript` edition, preserving paragraph breaks. It is not the subtitle/segment display and must not be replaced by a summary. Keep every canonical source segment covered once in order; emit one nonempty line per reading paragraph in reading-transcript.txt, separated by blank lines. The preview retains both reading and audio-aligned editions for their different uses.

## Reading-edition editing rules (EP04)

- The reading transcript is for readers; the timed/aligned transcript stays verbatim. Remove only contextually non-semantic disfluencies and stutters; preserve meaningful responses, emotion, emphasis, negation and uncertainty (啊/哦/嗯 can carry meaning). Put spaces between English tokens and Chinese, normalize names, group into sentence-aligned paragraphs. Keep every source segment ID once, in order, with no CR/LF inside a paragraph.
- Unconfirmed substantive words are retained with a neutral uncertainty marker or a faithful noncommittal rendering, with source cue IDs and `unresolved_terms`; never silently omit a claim, qualifier or name. A speculative proper noun must not appear as an established fact in any public edition, including the reading transcript (it becomes the public Transistor transcript). Use the confirmed wording or a clearly marked uncertain reference pending evidence.
- Log each substantive correction in `metadata.corrections` with its actual witness (final-audio Whisper, supplied SRT, context, user) and confidence; source-ID coverage alone does not prove semantic fidelity. Do not attribute a line to a speaker without evidence. Keep spoken profanity consistent with the provider `explicit` flag. Public copy must match what is said (EP04 review caught “帆船” vs 冲浪).
- Preview QA: use a local Range-capable server and verify 206/`Content-Range` plus real playback and seek; `serve_preview.py` is the tested helper (equivalent verified servers are acceptable). EP04 observed a stalled media load in one hidden browser-extension surface; switch to an isolated `agent-browser` session when diagnosis warrants it, and use real clicks for playback.
