# Acoustic boundary review

ASR and forced alignment locate recognized tokens. They do not establish the full
audible extent of a filler. A cut can remove the aligned core while leaving a
voiced tail; expanding it can instead remove a neighboring syllable. Model frame
spacing is not boundary accuracy.

Before constructing an accepted filler cut:

1. Bind the uncut context, analysis, word evidence and proposed sample EDL to their
   hashes. Check their clocks against the actual source. Cross-correlation can
   diagnose a global offset, but cannot label a phoneme.
2. Inspect both sides with the neighboring words present. Preserve low-confidence
   alignment, overlapping voices, continuous voicing into the next word, chunk
   seams and meaningful or emotional responses. Keep an ambiguous token.
3. Treat energy, periodicity and spectrograms as acoustic observations. Record
   filter, frame, hop and thresholds; include the frame's full support when
   discussing an observed tail. These measurements do not identify which word
   produced the sound. Do not turn a voiced-frame group into a deletion label.
4. Include both source contributors of each crossfade in the neighborhood audit.
   The right contributor starts at the cut endpoint and extends by the fade
   length. Retained-sample equality outside the fade proves mechanics, not a
   safe join or absence of swallowed speech.
5. Render immutable local A/B hypotheses. A bounded endpoint-sensitivity test can
   help investigate residual sound. Independently transcribe the actual rendered
   files if that destination and audio scope are authorized. A token disappearing
   from recognition is evidence of recognition sensitivity, not proof that its
   whole sound disappeared. Neighboring text remaining is not proof that every
   phonetic onset survived.
6. Listen to deletion and retention cases in context with an authorized reviewer.
   Keep model, input hash, original response, uncertainty and disagreement. A
   reviewer that cannot distinguish known A/B changes cannot certify those cuts.
   A high aggregate score never overrides a concrete swallowed-word report.

Record the source word ID, proposed half-open sample interval, crossfade length,
neighbor evidence, rejected variants, reviewer identity and final keep/delete or
uncertain decision. A review hypothesis remains `keep_pending_review` until the
semantic and boundary evidence supports acceptance. Never silently expand ASR
intervals by a universal padding constant.

For benchmarks, report harmful deletion and restore counts with the number of
actually reviewed decisions and ambiguous cases. Zero observed harm with no
accepted, reviewed deletions provides no precision evidence. Boundary error
requires independently labeled audible boundaries; disagreement between two
models is not an accuracy measurement. Publish both whole-reference alignment
coverage and any explicitly excluded reference regions. Nonmonotonic human edits
cannot serve as a delete-only source map. Freeze the review policy after
representative development A/B evidence and before inspecting held-out content;
do not tune on holdout failures and then call the same material independent.

Waveform pairing has a separate resolution limit. An integer-lag search after
heavy downsampling can reject the correct origin because a fractional lag is
coarse relative to the remaining waveform. Investigate weak matches at a higher
analysis rate and independently check selected matches from the original media
on a common clock. Keep the previous results. When rate, window hop or search
priors change, report both the same original anchor grid and the new grid;
otherwise a higher percentage can hide a changed denominator. For overlapping
windows, compute their union for time coverage instead of summing their lengths.
Preserve low-energy and unmatched regions in the whole-reference denominator,
and disclose the denominator after any nonmonotonic-reference exclusion.
Numerical pairing coverage is not semantic acceptance or exact cut provenance.

## Verify the hearing coverage and unchanged context

An audio-available flag and a successful provider response do not establish that the reviewer assessed the entire supplied clip. Compare its stated ending, excerpt edges and concrete tail content with the actual decoded duration. If it describes an early ending while the same-file tail contains independently corroborated speech, retain the original response and mark the full-window review insufficient. Preserve that window in the whole denominator; an ASR diagnostic is not a replacement audition. Report supplied coverage, returned-window coverage and independently accepted listening separately.

For overlapping reviews, bind the common region to the same parent clock and compare actual child PCM bytes. Opposite words in byte-identical shared content establish reviewer/recognizer disagreement, not the correct word. Preserve both quotations and uncertainty, even if both responses give high scores and claim intact words. Never select a noun, negation, speaker or proper name by a vote alone.

Before attributing a missing returned word to an edit, locate the actual EDL joins and both fade contributors in the supplied context. If an entire context has no current edit join, state only that locality fact. It does not prove phonetic correctness, speaker audibility or transparent mastering. Inspect recognition, overlap and mix evidence rather than counting every transcript difference as a harmful deletion.
