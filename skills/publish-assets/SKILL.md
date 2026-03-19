---
name: publish-assets
description: |
  Publishes local image assets referenced in Markdown files through an external
  image-hosting toolkit, then rewrites the document with public URLs.
  Use when the user asks to publish local images, upload report assets, or
  replace local Markdown image links with hosted URLs.
---

# Publish Assets Skill

## Overview

This is an integration skill. It does not bundle a hosting backend by itself.

Instead, it expects an external publishing toolkit to be available locally. The skill's job is to:

- locate the target Markdown file
- run the external uploader
- replace local image links with hosted URLs
- keep a backup when supported by the tool

## Expected External Dependency

Required external tool:

- `image-hosting-portable-kit` or an equivalent uploader with a CLI entrypoint

Recommended configuration pattern:

- configure provider credentials via environment variables or a local `.env`
- keep provider-specific values out of this repository
- document local setup in your own workspace if needed

See the repository root `.env.example` for placeholder variable names.

## Pre-flight Check

Before uploading anything:

1. Confirm the external toolkit is installed
2. Confirm credentials are present
3. Confirm the target Markdown file uses absolute or correctly resolvable local paths
4. Confirm the user wants publishing, not just validation

## Generic Execution Pattern

The exact command depends on your external toolkit. A typical flow looks like:

```bash
# Verify provider status
python <path-to-toolkit>/main.py status

# Upload and rewrite a markdown file
python <path-to-toolkit>/main.py upload-doc "/absolute/path/to/target.md" --provider <provider-name>
```

## Safety Rules

- Always use an absolute path for the target document when possible
- Keep backups enabled
- Do not delete original local images unless the user explicitly asks for cleanup
- If the external toolkit fails, summarize which files failed and stop

## Error Handling

- If no local images are found, tell the user the document is already clean or has nothing to upload
- If credentials are missing, stop and ask the user to configure them locally
- If the target file does not exist, resolve the path before retrying

## Notes for Reuse

- This skill is intentionally provider-agnostic at the repository level
- In Martin's private workspace it may be wired to R2 or another backend
- If you reuse it elsewhere, replace the dependency path and provider details with your own local setup
