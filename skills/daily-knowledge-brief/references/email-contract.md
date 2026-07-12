# Gmail delivery contract

## Recipients

Read the current automation whitelist from `LIFE_OS_ROOT/AGENTS.md`. Do not embed private recipient addresses in a portable skill.

## Send gate

1. Local Markdown exists and passes `validate_brief.py`.
2. HTML and plain-text bodies are non-empty.
3. Run manifest is initialized.
4. Recipient is whitelisted and not already `sent` for this run.

Use the profile-scoped Google Workspace helper beneath `HERMES_HOME`. Send one request per recipient so each message ID and retry state is independent. Subject:

```text
Life-OS 每日知识简报｜YYYY-MM-DD
```
