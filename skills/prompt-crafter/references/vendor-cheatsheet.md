# Model-Specific Prompting Cheatsheet

Quick reference for adapting prompts across Claude, GPT, and Gemini.

---

## Claude (Anthropic)

### Strengths
- Excellent at following structured, detailed instructions
- Native XML tag parsing for context boundaries
- Strong at refusing unsafe content gracefully

### Key Patterns
| Pattern | Implementation |
|---------|---------------|
| **Role assignment** | Use the `system` parameter; be specific about identity and constraints |
| **Context boundaries** | Wrap with XML tags: `<context>`, `<instructions>`, `<examples>` |
| **Output forcing** | Prefill the assistant response (e.g., start with `{` for JSON) |
| **Reasoning** | Use `<thinking>` tags for internal scratchpad before `<answer>` |
| **Extended thinking** | For complex tasks, set a "thinking budget" rather than over-specifying steps |
| **Anti-hallucination** | `<investigate_before_answering>` — force reading/checking before generating |

### Watch Out For
- Overly long system prompts can dilute instruction following
- Claude is conservative by default; explicitly permit creative freedom when needed
- Parallel tool calls are aggressive in Claude 4.5+; use control tags if needed

---

## GPT (OpenAI)

### Strengths
- Strong at structured output (JSON mode, function calling)
- Good at creative and conversational tasks
- Effective with markdown-structured prompts

### Key Patterns
| Pattern | Implementation |
|---------|---------------|
| **Role assignment** | System message with clear persona definition |
| **Structured output** | Use JSON mode or function calling with explicit schemas |
| **Reasoning** | "Let's think step by step" or chain-of-thought prompting |
| **Context management** | Use markdown headers (##) to separate sections |
| **Output control** | Define JSON schema explicitly; use `response_format` parameter |
| **Few-shot** | Place examples in the system message or as user/assistant pairs |

### Watch Out For
- Can be verbose; explicitly say "Be concise" or "No preamble"
- May hallucinate URLs and citations; add "only cite provided sources"
- Temperature affects reasoning quality; use lower values for factual tasks

---

## Gemini (Google)

### Strengths
- Excellent multimodal capabilities (text, image, audio, video)
- Strong reasoning with "explain your reasoning" patterns
- Good at following XML-structured system instructions

### Key Patterns
| Pattern | Implementation |
|---------|---------------|
| **Role assignment** | Define in system instruction with XML structure |
| **Context structure** | Use XML tags: `<role>`, `<task>`, `<constraints>`, `<output_format>` |
| **Reasoning** | "Explain your reasoning step by step before giving the final answer" |
| **Task decomposition** | Break complex tasks into numbered sub-tasks |
| **Grounding** | Use Google Search grounding for factual accuracy |
| **Safety** | Built-in safety filters; align with rather than fight them |

### Watch Out For
- System instruction content is treated differently from conversation context
- Safety filters can be aggressive; frame sensitive topics in professional context
- For agentic reasoning tasks, use the patterns from dedicated agentic reasoner templates

---

## Cross-Model Migration Checklist

When adapting a prompt from Model A to Model B:

- [ ] **Role**: Reformat role assignment to target model's convention
- [ ] **Structure**: Convert context boundaries (XML tags vs. markdown headers)
- [ ] **Output format**: Adjust to target's output control mechanism
- [ ] **Reasoning**: Adapt thinking/reasoning instructions to target's pattern
- [ ] **Examples**: Verify examples still work with target model's tendencies
- [ ] **Safety**: Align guardrails with target model's safety conventions
- [ ] **Test**: Run at least 3 representative inputs through the adapted prompt
