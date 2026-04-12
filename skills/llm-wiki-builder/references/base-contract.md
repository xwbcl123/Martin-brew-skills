# Base Contract

## Directory Contract

```text
wiki_root/
  raw/                # immutable source copy
  raw-normalized/     # optional normalized working copy
  analysis/
    ingest-src/
    overview.md
  evidence/
    source-inventory.md
  index.md
  log.md
  AGENTS.md
  LINTS.md
  _meta.md
```

## Safety Rules

- Never mutate the original `source_path` in place.
- If `source_path` is external to the wiki root, copy it into `wiki_root/raw/`.
- If `source_path` is already `wiki_root/raw/`, treat it as the immutable source copy.
- Only rename files inside `raw-normalized/`.
- Never back-write normalized names into `raw/`.
- Default rerun policy is `refuse-with-report`.

## Generic Governance

The generated governance files are generic. They enforce:

- root cleanliness
- raw purity
- frontmatter minimum keys
- append-only log discipline
- traceability from analysis/evidence back to raw files

They must not assume a project-specific domain, tag set, or page numbering convention unless a profile explicitly adds that layer.
