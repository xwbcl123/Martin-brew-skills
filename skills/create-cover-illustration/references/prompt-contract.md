# Prompt Contract

Use this reference when creating prompts for `create-cover-illustration`.

## Default Style

- Hand-drawn cartoon infographic.
- Landscape 16:9.
- Warm, personal, memory-friendly, and clean.
- Use simple cartoon elements, icons, workflow boards, sticky notes, generic people, and symbolic objects.
- Use concise text labels in the same language as the source content. Use Chinese for Chinese journals.
- Use ample whitespace and a clear visual hierarchy.
- Avoid realistic photos, 3D renders, glossy UI, dark cinematic scenes, official logos, and brand marks.
- Do not include bananas or monkey-related elements unless the source content explicitly requires them.
- If the source mentions sensitive or copyrighted figures, replace them with generic visually similar alternatives.

## Source Extraction Rules

- Full source context is allowed. Modern image models can infer themes from a complete note, and long context can preserve nuance.
- If you include the full source, add an explicit instruction to extract only the visually important themes before composing the image.
- If you summarize first, use 3-5 short theme bullets. This is often faster and more controllable, but it is not mandatory.
- Preserve the details that change the picture: places, objects, workflows, emotional tone, and 3-6 concrete visual keywords.
- Prefer visual labels over prose labels. Keep labels short enough to be legible in the image.
- For Chinese journals, labels should be Chinese except unavoidable product names, tool names, or technical terms present in the source, such as `Jupyter` or `pandas`.
- If the day has multiple threads, assign each thread to a visible cluster instead of forcing every fact into one paragraph.

## Journal Cover Prompt Template

```text
Create a hand-drawn cartoon-style infographic cover image for a Chinese daily journal entry. Landscape 16:9 aspect ratio.

Source themes:
- [theme 1]
- [theme 2]
- [theme 3]

Optional full source:
[paste the source note only when useful]

If full source is provided, first infer the 3-5 most visual themes, then create the cover from those themes. Do not try to depict every sentence.

Visual style:
- Pure hand-drawn illustration style, simple cartoon infographic, warm and memorable.
- Use a small number of simple cartoon elements/icons.
- Chinese text only, concise keywords, hand-lettered look.
- No realistic elements, no photos, no 3D, no glossy UI.
- No bananas, no monkeys, no official logos, no brand marks.

Composition:
- Center: [main metaphor].
- Left cluster: [supporting theme].
- Right cluster: [supporting theme].
- Bottom strip: [human/life/energy theme if present].
- Main title text: "[short title]".
- Secondary keywords: "[keyword 1]", "[keyword 2]", "[keyword 3]".

Keep the layout clean, legible, spacious, and suitable as a daily journal chapter image.
```

## Journal Cover Example Pattern

Use this pattern when a daily note mixes family/life events and technical work:

```text
Source themes:
- Family rhythm: [1-2 concrete life scenes], warm and grounded.
- Field test or creative tool: [device/tool] lowers creation friction.
- Work method: [pipeline/method] turns messy input into structured output.
- Skill flywheel: reusable tools, automation, or learning loop.

Composition:
- Center: [single metaphor that connects the day, such as a workbench, map, flywheel, or dashboard].
- Left cluster: life or reflective scenes with concrete objects.
- Right cluster: technical/workflow board with 3-4 short step labels.
- Bottom strip: chronological or emotional arc of the day.
```

## Writing Illustration Prompt Template

```text
Create a hand-drawn cartoon-style infographic illustration for a Markdown article or briefing. Landscape 16:9 aspect ratio.

Core idea:
[one-sentence summary]

Key concepts:
- [concept 1]
- [concept 2]
- [concept 3]

Visual requirements:
- Hand-drawn cartoon infographic, not realistic.
- Concise labels in the source language.
- Minimal icons and clean clusters.
- Ample whitespace.
- Avoid logos, watermarks, photorealism, 3D, glossy effects, and clutter.

Main title text: "[short title]"
Secondary keywords: "[keyword 1]", "[keyword 2]", "[keyword 3]"
```

## Prompt-Only Output

When the user asks for prompt-only output, return the final prompt and do not call an image model. Mention the intended mode and aspect ratio.

## Quality Checklist

- The subject matches the source content.
- Text is readable and in the right language.
- The image is 16:9 landscape.
- The style is hand-drawn and cartoon-like.
- There is enough whitespace.
- There are no banned elements or official logos.
- The image can work as a memory cue without reading the full note.
