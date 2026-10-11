# Calibration interface v1

`python3 scripts/calibration.py detect --input raw-or-aligned.json --duration SECONDS --output NEW.json`

Detector outputs `route`, policy, flags and `publication_blocked:false`. Timeline/coverage flags do not bypass separate package corruption checks. Library accepts `repeat_count` and `gap_seconds` overrides and records them. Raw is never edited.

`glossary --source PRIVATE-glossary.md --episode-text LOCAL.txt --output relevant.json`

Parses bullet aliases separated by `/` and mappings using `=`, `=>`, `→`. Keeps canonical spelling including parenthetical qualifiers because their interpretation requires context. Duplicate/conflicting entries retain source line numbers. Latin aliases match word boundaries; short aliases never trigger global replacement. UTF-8 source byte hash (including original CRLF/BOM) identifies the snapshot. Only resulting relevant candidates may enter a reviewer packet.

`extract --delivery FINAL.mp3 --authorization authorized.json --output NEW_DIRECTORY`

Authorization shape:

```json
{"source_sha256":"…", "source_kind":"final_delivery", "source_ref":"user authorization reference", "external_snippet_asr_authorized":true, "ranges":[{"start":10,"end":30}]}
```

Ranges are explicit final-timeline seconds, sorted/nonoverlapping, each ≤60 s, sum ≤180 s and strictly less than full episode duration. Generate one manifest per episode/run containing the entire authorized set; do not split calls to evade the total cap. Final audio must already exclude private removed material. An authorization is an audit record derived from the user's scope, not authority newly invented by this helper. `manifest.json` contains verified final source hash, authorization hash, snippet hashes, durations and absolute offsets. Extraction produces mono 16kHz PCM WAV for ASR only, never delivery replacement.

`gemini --manifest clips/manifest.json --output NEW_DIRECTORY`

Explicit invocation performs external requests using `GEMINI_API_KEY` (fallback `GOOGLE_API_KEY`). Calls REST `generateContent`, primary `gemini-3.5-transcribe`, then `gemini-3.8-flash` if empty/failing. Revalidates source/snippet hashes and ranges. Every actual response is retained. Network errors retain class/HTTP status without raw error body/credential/URL. A nonempty unparseable response remains raw evidence with unavailable timing; it is not trusted aligned output. Valid relative timing maps to absolute snippet offset, labeled estimated. No transcript context, glossary, or full audio is accepted as prompt input.

Official interfaces: [generateContent](https://ai.google.dev/api/generate-content), [audio input](https://ai.google.dev/gemini-api/docs/audio). Model availability is observed separately by the coordinator; success is determined by actual nonempty response, never listing alone.

Library `reconcile(term,votes,mode,user_decision=None)` takes `term={id,current,bindings}`. `bindings` contains nonempty episode_key/audio_sha256/timeline_sha256/content_sha256/glossary_sha256. The content hash excludes the terminology-review object to avoid self-reference. `votes` must contain distinct actual model IDs, `reviewed_by_kind:agent`, `independent:true`, `request_sha256`, `source_ref`, `raw_response`, `response_sha256=digest(raw_response)` and `choice`. The coordinator runs isolated prompts without other reviewers' answers and preserves the exact request evidence. No helper can establish actual model independence from an invented JSON claim; the review receipt must be backed by runtime evidence. Ties preserve current text. All model choices are provisional and need user confirmation, with explicit single/no-model degradation.

`import_user_decisions(document,binding,terms,actor_kind,source_ref)` consumes enrichment preview JSON `{bindings,decisions:[{term_id,decision:confirm|edit|defer,text}]}`. `actor_kind=human` requires observed user-submitted export/source; passing agent-created JSON as human is forbidden. The caller remains responsible for authentic interaction provenance. Stale/incomplete bindings, duplicates, unknown terms and empty edits fail. `reconcile` rechecks decision bindings and term ID. A confirm preserves current text; edit adopts provided text. Interactive mode rejects model votes and returns awaiting_user; it does not impose a publication block.

`run_key(stage,inputs)` hashes upstream input identities, implementation and policy. Supply audio/timeline/model/tool/options/glossary/reviewer-policy hashes appropriate to the stage. Own output hashes are rejected; resulting artifacts belong in the report, outside this identity.
