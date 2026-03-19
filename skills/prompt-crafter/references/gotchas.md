# Prompt Crafter — Common Gotchas & Fixes

This file provides detailed examples and remediation for each pitfall listed in SKILL.md `## Common Pitfalls`. Read this when you encounter one of these patterns or need to explain a fix to the user.

---

## 1. Verbosity over Density

**Symptom**: The generated prompt has filler phrases ("In order to effectively...", "It is important to note that..."), redundant restatements, or sections that add no actionable constraint.

**Fix**: After drafting, do a density pass:
- Remove every sentence that doesn't add a constraint, example, or guardrail
- Replace multi-sentence explanations with a single directive
- Target: every line in the prompt should be load-bearing

**Before**:
```
In order to effectively summarize the article, you should carefully read through
the entire content and identify the key points that the author is making. It is
important to note that the summary should be concise and capture the main ideas.
```

**After**:
```
Summarize the article in ≤3 bullet points. Each bullet: one key claim + its evidence.
Omit background context the reader already knows.
```

---

## 2. Missing Output Format Spec

**Symptom**: The prompt asks for structured output (e.g., "create a report") but doesn't define the schema, field names, or section order. Downstream systems can't parse the result.

**Fix**: Always include a `## Response` section with:
- Exact format (JSON, Markdown table, numbered list, etc.)
- Required fields/columns with types
- A concrete example of the expected output shape

**Before**:
```
## Response
Provide a summary report.
```

**After**:
```
## Response
Return a Markdown document with exactly these sections in order:
1. **Executive Summary** (1 paragraph, ≤50 words)
2. **Key Findings** (bulleted list, 3-5 items)
3. **Recommendations** (numbered list with priority: High/Medium/Low)
4. **Data Sources** (bulleted list of references used)
```

---

## 3. Blind Cross-Model Copy

**Symptom**: A prompt designed for Claude (using `<xml>` tags, `system` parameter, prefill) is pasted directly into GPT or Gemini, producing confused or degraded output.

**Fix**: Consult `references/vendor-cheatsheet.md` and apply the target model's native patterns:

| Claude Pattern | GPT Equivalent | Gemini Equivalent |
|---------------|----------------|-------------------|
| `<context>...</context>` XML tags | `## Context` markdown headers | XML-based system instructions |
| `system` parameter for role | `system` message in chat array | System instruction field |
| Prefill (`assistant: {"`) | `response_format: json_object` | `"explain your reasoning"` pattern |

Always produce a **Migration Notes** section listing every structural change made.

---

## 4. Parroting User Text

**Symptom**: The COSTAR fields contain near-verbatim copies of the user's casual request instead of restructured, precise prompt engineering language.

**Fix**: Treat the user's input as a **brief**, not as prompt text:
- Extract the **intent** (what they want to achieve)
- Identify **implicit constraints** they didn't state
- Reformulate into engineering-grade specifications

**Before** (user said: "I need a prompt to help me write better emails"):
```
## Objective
Help the user write better emails.
```

**After**:
```
## Objective
Given a draft email or bullet-point intent, produce a revised email that is:
- Clear and actionable (one CTA per email)
- Appropriate in tone for the stated audience
- Under 200 words unless the user specifies otherwise
```

---

## 5. Skipping Edge Cases

**Symptom**: The prompt works for the happy path but fails on ambiguous inputs, missing data, multi-language content, or adversarial queries.

**Fix**: Always add a `## Guardrails` section covering:
- **Missing data**: "If [field] is not provided, ask the user before proceeding / use [default]"
- **Ambiguity**: "If the request is ambiguous, list your assumptions before proceeding"
- **Out of scope**: "If the request falls outside [domain], say so explicitly instead of guessing"
- **Language**: "Respond in the same language as the user's input unless instructed otherwise"
