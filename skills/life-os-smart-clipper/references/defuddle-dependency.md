# Defuddle dependency

Defuddle is an external Node.js CLI, not code bundled in this skill. Verify it before using the article extraction route:

```bash
command -v defuddle
defuddle --version
```

## Install

Require Node.js and npm. With user authorization to install software, use:

```bash
npm install -g defuddle
```

Then verify again with `command -v defuddle` and `defuddle --version`.

## Hermes runtime check

The command must be discoverable from the Hermes terminal runtime, not only from an interactive shell. If it works interactively but not for Hermes, report the resolved binary path and repair the runtime `PATH` through the host's normal service configuration. Do not hard-code a machine-specific binary directory in this skill.

## Use and fallback

Extract article-like HTML with:

```bash
defuddle parse "$URL" --md
```

If the CLI is unavailable and installation has not been authorized, use the configured Firecrawl or browser extractor and report `extraction_method` accurately. Never label a fallback result as `defuddle`.

Do not use Defuddle for YouTube/podcasts, PDFs, raw Markdown, social-platform pages, or pages requiring authentication.
