# Judge Contract

## Independence

- Text Judge: receives candidate metadata, local Transcript context and protected tokens; it never receives audio, Filmora evidence, target duration or the Audio Judge result.
- Audio Judge: receives a bounded analysis-audio window plus minimal candidate context; it never receives Filmora evidence, target duration or the Text Judge result.
- Neither Judge emits or edits the EDL. They emit only `cut | keep | abstain` verdicts against the declared candidate core interval.
- The adjudicator reads both immutable responses after both finish.

## Data Scope Gate

Before dispatch, the episode declaration must record:

- provider/harness and exact observed model identifier;
- input role and exact SHA-256;
- bounded transcript/audio window policy;
- the user's authorization record for model processing;
- minor-consent status when a minor is present.

Missing evidence is `blocked`, not implicit consent.

## Stability

The challenge set runs each Judge three times with independent fresh packets. Any candidate-level label drift becomes `review_required`; majority voting cannot make it auto-cut eligible. Raw text and parsed JSON are both content-addressed evidence.

## Schemas

- Candidate: `candidate-packet.schema.json`
- Response: `judge-response.schema.json`

Every response binds candidate, prompt, model, input and raw-response hashes. Confidence is evidence for review ordering, never authority to extend a cut beyond the candidate interval.
