# Journal Memory Map

Use this profile by default for daily journals and reflective logs. Its purpose is retrieval: the reader should be able to reconstruct the day from the image.

## Storyboard contract

Build an in-memory storyboard before the final image prompt:

```yaml
date: exact journal date
main_title: short title that includes the correct date
central_narrative: one phrase connecting the day
central_scene: one person, place, object, or metaphor anchoring the layout
event_clusters:
  - time_or_role: morning, work, family, health, learning, or another source-grounded division
    event: concrete action or outcome
    visible_objects: 2-4 objects that make the event recognizable
    exact_labels: 1-3 critical labels
bottom_timeline: chronological or emotional arc
tone: source-grounded emotional tone
must_preserve: dates, names, numbers, or relationships that cannot drift
must_avoid: unsupported events, wrong date, and generic filler
```

Use 5-8 event clusters for a rich day. Use fewer only when the source is genuinely narrow. Cover every major time block or top-level thread, not every sentence.

## Composition

- Put the central narrative and main scene in the visual center.
- Arrange event clusters around it with clear borders, color zones, arrows, or spatial grouping.
- Use a bottom strip for time progression, life rhythm, or the day's emotional close.
- Preserve work, family, health, learning, and personal-life balance when present.
- Prefer source-specific artifacts, devices, documents, repairs, meals, exercises, or locations over generic infographic symbols.
- Permit dense content, but maintain hierarchy through size, grouping, and restrained colors rather than excessive whitespace.

## Text

- Include the exact journal date in the main title unless the user explicitly removes it.
- Keep critical labels short and quote their exact spelling in the prompt.
- Prioritize the title, date, central narrative, and cluster headings. Decorative microcopy is optional.
- State whether any additional text is allowed.

## Final prompt pattern

```text
Create a hand-drawn 16:9 journal memory-map infographic from this storyboard.

Purpose: let the reader reconstruct the day at a glance. This is a rich daily memory map, not a minimalist editorial cover.

Exact main title: "[title with correct date]"
Central narrative: "[narrative]"
Central scene: [concrete scene]

Event clusters:
1. [position/time]: [event]; show [objects]; exact labels: "..."
2. ...

Bottom timeline: [chronological or emotional arc].
Tone and palette: [source-grounded tone].

Keep the layout information-rich but legible through clear visual hierarchy and grouped panels. Preserve all must-preserve facts. Do not invent events. Use the shared hand-drawn style and exclusions.
```

When an accepted reference cover is available, use it for layout density and style only. Do not copy its date, events, labels, or personal likeness.
