# Publication Contract

## Immutable bundle

Each publication receives:

```text
<prefix>/<task-id>/<version>/index.html
<prefix>/<task-id>/<version>/assets/...
```

`version` is a UTC timestamp plus a content digest. A single HTML file is
published as `index.html`; other single files retain their sanitized filename.
A directory preserves relative paths and must not contain symlinks.

## Required publication record

Every `published` event records:

- publication ID, task ID and immutable version;
- publication time and lifecycle state;
- source path, entrypoint, object keys and public URLs;
- byte totals, per-file SHA-256, MIME types and aggregate digest;
- pin state, Bucket name, configurable public base URL and package manifest.

Registry events are append-only. Current state is reconstructed by replaying
`published`, `pinned`, `unpinned`, `deleted`, and cleanup events. Never edit an
old registry line to hide history.

## Cleanup transaction

1. `cleanup-plan` queries the actual R2 inventory, compares it with the event
   registry, then computes a cutoff and materializes eligible active,
   non-pinned publication bundles.
2. The plan contains a unique ID, creation/expiry time, registry snapshot hash,
   task/version grouping, URLs, object keys and total bytes.
3. Martin reviews the dry-run result and explicitly confirms its exact plan ID.
4. `cleanup-confirm` replays current state and rejects stale, expired, pinned,
   missing, already-deleted, or changed candidates.
5. Delete all objects in each approved version bundle, verify absence through
   the S3 API, append lifecycle events, and update task manifests.

Untracked R2 objects are inventory findings only and are never automatically
deleted. A recorded bundle with missing remote objects is excluded from the
plan for explicit reconciliation.

Public cache disappearance can lag S3 deletion. Report S3 verification exactly;
do not claim instant public-cache purge on `r2.dev`.
