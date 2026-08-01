# Quality and Retry Contract

## Freeze the prompt

Finalize the visual profile, storyboard, exact labels, composition, and exclusions before the first tool call. Record or calculate a prompt hash when the workflow keeps an operation log.

## Retry policy

Allow three total attempts on the primary built-in image path:

1. Run the frozen prompt.
2. If the tool reports that it is still running, wait. Do not classify it as failure.
3. Retry only after an explicit retryable network or service failure.
4. Reuse the exact same prompt for attempts two and three.
5. After three explicit failures, use the permitted fallback with the same profile and storyboard.

Do not blindly retry authentication, authorization, policy, or malformed-request errors. Record the original error and stop or route appropriately.

A generated image that misses the brief is a quality failure, not a network failure. Use a targeted edit for a localized defect and regenerate for structural drift.

## Hard gates

Reject the image if any applicable gate fails:

- Real local image bytes exist and MIME matches the expected format.
- Landscape dimensions are approximately 16:9.
- The title and journal date are correct.
- The central story matches the source.
- No major event is invented or assigned to the wrong day.
- Critical labels and proper nouns are readable and correctly spelled.
- No banned content or misleading endorsement appears.
- A journal mutation contains exactly one H1-adjacent Markdown cover block.

## Preference gates

Score candidate quality with evidence rather than generic taste:

| Dimension | Strong result |
|---|---|
| Semantic coverage | Covers the source's major threads or time blocks |
| Specificity | Uses recognizable objects, actions, tools, and places from the source |
| Hierarchy | Central narrative, event clusters, and timeline are visually distinct |
| Retrieval value | The image helps reconstruct the day without opening the journal |
| Balance | Represents work, life, health, family, or learning in source-grounded proportion |
| Legibility | Dense content remains readable at useful viewing size |
| Originality | Avoids generic AI infographic filler and repetitive metaphors |

When comparing candidates, state which hard gates passed and why the selected candidate wins on preference gates.
