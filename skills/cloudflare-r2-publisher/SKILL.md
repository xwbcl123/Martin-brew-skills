---
name: cloudflare-r2-publisher
description: Publish validated local HTML, image, PDF, audio, video, or other artifact bundles to a dedicated Cloudflare R2 Bucket. Use only after explicit public-upload authorization such as #publish, or when the user asks to publish, pin, unpin, unpublish, inventory, or age-clean R2 artifacts. Creates immutable version URLs, verifies public readback, maintains task-local manifests and a global event registry, and requires dry-run plus plan-ID confirmation for batch cleanup.
---

# Cloudflare R2 Publisher

Publish artifacts; do not generate or rewrite their content. Treat R2 as a
public delivery plane and Life-OS as the durable source of truth.

## Required boundary

- Require explicit `#publish` or equivalent public-upload authorization.
- Never publish a bare URL/topic request, draft, failed validation artifact, or
  file containing secrets.
- Read credentials only from `$HERMES_HOME/.env`; never print, copy, or persist
  their values.
- Use the dedicated Hermes Bucket. Do not reuse another project Bucket.
- Never overwrite a published object. Every publish creates an immutable
  version bundle and URL.

## Preflight

Run with the Hermes virtual environment:

```bash
PY="$HERMES_HOME/hermes-agent/venv/bin/python"
CLI="$HERMES_HOME/skills/cloudflare-r2-publisher/scripts/r2_publisher.py"
"$PY" "$CLI" preflight --remote
```

The required environment variables are documented in
`references/configuration.md`. Stop if preflight fails.

Configure them without placing secrets in shell history:

```bash
export HERMES_HOME="/absolute/path/to/hermes-home"
"$HERMES_HOME/hermes-agent/venv/bin/python" \
  "$HERMES_HOME/skills/cloudflare-r2-publisher/scripts/configure_r2.py"
```

The configurator uses hidden input for both credential values and Hermes'
secure environment writer. Run `preflight --remote` afterward.

## Publish

Use a validated file or self-contained directory. For a Deep Research report,
set `--package-dir` to its durable report package so the task-local manifest is
stored beside the artifacts.

```bash
"$PY" "$CLI" publish \
  --source "/absolute/path/to/viz-brief.html" \
  --task-id "deep-research-example" \
  --package-dir "/absolute/path/to/report-package"
```

For a directory bundle, include exactly one `index.html` when the public result
is a web page. The command uploads every regular file under the version prefix,
verifies public readback of the entrypoint, writes `publish-manifest.json`, and
appends a `published` event to the global registry.

Return the public URL only when the CLI exits `0` and reports
`status: published`. Preserve the exact error otherwise.

## Lifecycle commands

Pin or unpin a published revision by immutable URL or publication ID:

```bash
"$PY" "$CLI" pin --target "<publication-id-or-url>"
"$PY" "$CLI" unpin --target "<publication-id-or-url>"
```

Unpublish one explicit revision:

```bash
"$PY" "$CLI" unpublish --target "<publication-id-or-url>"
```

Batch cleanup is always two-stage:

```bash
"$PY" "$CLI" cleanup-plan --age 3m
"$PY" "$CLI" cleanup-confirm --plan-id "<plan-id>"
```

Supported selectors are `3m`, `9m`, `1y`, or `--before YYYY-MM-DD`. Never run
`cleanup-confirm` unless Martin explicitly sends the exact plan ID after seeing
the dry-run summary. Pinned revisions and objects not managed by this Skill are
excluded. Delete complete version bundles, never individual child assets.

Use `inventory --remote` for capacity review. It compares the append-only
registry with the actual Bucket inventory and reports total remote bytes,
untracked objects, and recorded objects missing from R2. Never delete an
untracked object automatically.

## Validation and delivery

- Read `references/publication-contract.md` before integrating another Skill.
- Treat public readback and S3 deletion verification as distinct checks.
- `r2.dev` is the approved personal-sharing MVP endpoint; do not claim custom
  domain behavior.
- Telegram may receive the immutable URL after successful verification. Never
  expose Bucket credentials, S3 endpoint, registry internals, or object lists.
