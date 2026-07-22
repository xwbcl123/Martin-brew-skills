# HTML And Public Publication

## Authorization

| Request marker | Result |
|---|---|
| none | Canonical Markdown + Kami PDF only |
| `#html` | Default artifacts + local `viz-brief.html`; no upload |
| `#publish` | Default artifacts + local HTML + verified R2 publication |

`#publish` is explicit authorization for the current approved report only. It
does not authorize future revisions, other tasks, embedded remote resources, or
bulk publication.

## Gemini visual packet

Give Gemini only validated inputs:

- canonical Markdown and source ledger;
- report manifest and approved Research Brief;
- `brand-guidelines` visual reference and relevant Life/Work identity route;
- destination filename and responsive-delivery contract.

Require a standalone, responsive HTML report with semantic headings, working
citations, mobile layout, accessible contrast, no secret values, no analytics,
no external scripts, and no invented facts. Prefer embedded CSS and local or
embedded assets. The visual report may reorganize information but may not add
claims absent from the canonical report.

## Local HTML gate

Verify before publishing:

- one non-empty HTML file at the canonical package path;
- title, executive summary, key findings and references present;
- every visible factual link is a valid `http` or `https` URL;
- no Markdown residue, local absolute paths, environment names/values, tokens,
  placeholder text, console errors, broken local assets or horizontal overflow;
- desktop and `375 px` mobile rendering pass;
- HTML content hash is recorded in the report manifest.

## Public gate

Load `cloudflare-r2-publisher` and publish the validated file or self-contained
bundle. Every revision receives a new immutable URL. Do not overwrite an older
revision or synthesize a `latest` alias. Record the returned publication ID,
version and URL in the task result and task-local publish manifest.

If credentials, Bucket access, public readback or registry persistence fails,
retain the valid local HTML, set `publish_failed`, and report that public
delivery did not complete. Never substitute an unverified URL.
