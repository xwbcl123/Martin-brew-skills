# COSTAR Framework — Quick Reference

## The 6 Fields

| Field | Question to Answer | Common Mistakes |
|-------|--------------------|-----------------|
| **C — Context** | What background does the agent need? | Too much irrelevant info; missing tool/input descriptions |
| **O — Objective** | What does "done well" look like? | Vague goals ("do a good job"); missing scope boundaries |
| **S — Style** | How should it write? | No formatting guidance; mixing casual and formal |
| **T — Tone** | What personality/voice? | Contradictory tone instructions; ignoring brand voice |
| **A — Audience** | Who reads the output? | Assuming expert audience when end-users are novices |
| **R — Response** | What format/structure? | No schema; saying "be creative" when structure is needed |

## Optional Extensions

Add these when the use case demands it:

| Extension | When to Use |
|-----------|-------------|
| **MODELS** | Multi-model deployment; include model-specific tweaks |
| **EXAMPLES** | Complex tasks where format/quality is hard to describe in words |
| **GUARDRAILS** | Sensitive domains (legal, medical, financial); user-facing outputs |
| **EVAL** | Any prompt intended for production use |

## Completeness Checklist

Before finalizing any prompt, verify:

- [ ] All 6 COSTAR fields are present and substantive (not placeholder text)
- [ ] At least 1 good example is included for complex tasks
- [ ] Output format is precisely specified (not just "Markdown" but which sections/keys)
- [ ] Uncertainty handling is addressed ("say you don't know" rule)
- [ ] Eval criteria are testable (yes/no or measurable, not subjective)

## Example: Well-Formed vs. Poorly-Formed

### Poorly-Formed Prompt
```
You are a helpful assistant. Answer the user's question about cybersecurity.
```
**Issues**: No objective boundaries, no output format, no examples, no guardrails.

### Well-Formed COSTAR Prompt
```
## Context
You are a senior cybersecurity analyst at a Fortune 500 company.
You have access to the company's threat intelligence database and
NIST CVE records. The user will provide a CVE ID.

## Objective
Produce a risk assessment for the given CVE, including:
severity rating, affected systems, and recommended mitigations.
Scope: only assess impact on Linux-based server infrastructure.

## Style
Technical but accessible. Use bullet points for mitigations.
Include severity in CVSS 3.1 format.

## Tone
Professional, direct, no hedging. Confidence calibrated to evidence.

## Audience
IT security team leads with 5+ years experience.

## Response
Output as Markdown with these exact sections:
- **CVE Summary** (2-3 sentences)
- **CVSS Score** (numeric + vector string)
- **Affected Systems** (bulleted list)
- **Mitigations** (numbered, priority-ordered)
- **References** (linked sources only — no fabricated URLs)
```
