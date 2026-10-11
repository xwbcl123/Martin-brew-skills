# Conservative rough-cut research

The current implementation emits review candidates only. It has no measured precision claim and does not infer speech intent from isolated words. Recording-control phrases may be quoted content; silence may express thought or emotion. Candidate detection must not be treated as an approved EDL.

Create paired raw audio and human-edited audio records with SHA-256, episode ID, source sample rate, the human EDL where available, policy/version, edit rationale and reviewer identity. Preserve raw ASR and restored intervals. Align the actual samples/segments and record uncertain alignments; duration similarity is not correctness evidence.

Split train/development/holdout by episode/session or speaker before tuning so adjacent snippets cannot leak across splits. Keep unseen speakers and emotional speech in holdout. Evaluate separate control/filler/silence classes with precision, harmful deletion rate, restore rate and coverage; report ambiguous labels separately. Prefer precision over removal coverage. Sample both proposed deletions and retained spans for contextual listening, especially breaths, emotional pauses and semantic fillers.

Use existing `render_human_restore_review.py` and the established restore ledger for paired candidate/manual review. Record restore decisions and boundary adjustments against source sample coordinates. Crossfade renders require explicit mapping because overlapping samples are not invertible. No optimization is accepted solely because the result has a human-like duration or removes more pauses.

Promotion to automatic edits requires a separately reviewed policy with observed holdout results, clearly allowed deletion categories, bounded context and restore evidence. It remains distinct from episode release authorization.

Follow [acoustic-boundaries.md](acoustic-boundaries.md) for complete voiced extent, neighbor/crossfade protection and endpoint sensitivity. Keep recognizer disagreement and missing boundary labels explicit; neither a shorter render nor a filler absent from new ASR supplies listening approval.

## PAYG cloud ASR calibration

Use the Speech console API key from an environment variable; never put credential values in commands, output or manifests. For the current [bidirectional streaming API](https://docs.volcengine.com/docs/DoubaoVoice/bidirectional-streaming-automatic-speech-recognition-websocket?lang=zh), the endpoint is `wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async`. Model 2.0 uses `volc.seedasr.sauc.duration` for the hourly service or `volc.seedasr.sauc.concurrent` for the concurrency service. Select the resource matching the activated billing service; an authorization or quota failure of one resource does not establish that the other resource is unavailable. This route is separate from Agent Plan.

For a verbatim-oriented calibration request, explicitly disable `enable_ddc`, `enable_itn` and `enable_punc`; enable `show_utterances`. The documented `enable_nonstream=true` enables two-pass recognition. Preserve all responses and bind the final response to the exact submitted audio hash and request configuration. Successful authentication alone is insufficient: require a terminal response, matching audio duration, non-empty recognition and no provider error. These settings improve observability but do not guarantee filler completeness or transcription accuracy.

Keep the provider's words with negative timestamps in the immutable raw response. Exclude them from cut coordinates and flag substantive unlocated tokens for review; whitespace placeholders do not define audio intervals. Keep corrections in a separate ledger. Treat model timestamps and differences against forced alignment as calibration evidence, not ground-truth boundaries or automatic cut approval.
