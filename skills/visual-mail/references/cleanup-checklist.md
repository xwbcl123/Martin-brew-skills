# Cleanup Checklist

Run before marking the delivery package complete.

## Banned strings in public-facing outputs

Public-facing outputs are: email `.md`, visual brief `.html`, screenshot caption or alt text, any published link title.

Check that none of the following appear in those files:

```bash
rg -n "Agent|worker|AI generated|Main Agent|prompt|task\.md|handoff\.md|请读取|shore" \
  <email_file> <html_file>
```

If the grep returns hits, inspect each match:

- In internal test logs or `test-report.md`: acceptable, explain in handoff.
- In the email body or HTML visible content: fix before delivery.

## Additional checks

- [ ] Email subject line is descriptive and does not contain internal slugs or `shore/`.
- [ ] Email body contains exactly two link placeholders or real published URLs — not both.
- [ ] Screenshot embed uses Obsidian `![[...]]` syntax and the path is correct relative to vault root.
- [ ] Visual HTML renders without JS errors (check browser console if possible).
- [ ] Visual HTML footer shows only the configured brand footer, with no generation/provenance traces.
- [ ] No `> Martin` review comment block in email.
- [ ] No internal note, draft watermark, or `[DRAFT]` label in the final email body.
- [ ] No unexpanded template variables (e.g., `<AUDIENCE>`, `<REPORT_TITLE>`) remain in any output.
- [ ] Links that are placeholders use the exact format: `<BRIEF_LINK_PLACEHOLDER>` and `<VIZ_LINK_PLACEHOLDER>`.
- [ ] File names follow the `YYYYMMDD_<slug>` convention with no spaces.

## Security checks

- [ ] No internal file paths, vault root paths, or task directory paths appear in any public-facing content.
- [ ] No session tokens, API keys, or credentials included.
- [ ] Draft materials are marked as drafts (via YAML `status: draft`) — not written as already-published facts.
