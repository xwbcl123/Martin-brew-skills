# Base Contract

## Directory Contract

```text
wiki_root/
  raw/                # immutable source copy
  raw-normalized/     # optional normalized working copy
  analysis/
    ingest-src/       # rich/binary extraction output, not required for native text
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
- Native text files such as Markdown and TXT remain readable in `raw/` or `raw-normalized/`; do not create redundant `analysis/ingest-src/` copies for them.

## Generic Governance

The generated governance files are generic. They enforce:

- root cleanliness
- raw purity
- frontmatter minimum keys
- append-only log discipline
- traceability from analysis/evidence back to raw files
- root-level semantic MoC pages when synthesis is in scope
- coverage QC for source files represented in MoC pages

They must not assume a project-specific domain, tag set, or page numbering convention unless a profile explicitly adds that layer.

## Semantic Wiki Contract

A complete wiki run must include more than scaffold pages:

- `index.md` states the domain-specific core thesis.
- `analysis/overview.md` summarizes the actual content and implications.
- root-level MoC pages route the reader by semantic clusters derived from the input set.
- every MoC entry includes source links and click-free summary value.
- final handoff reports coverage QC and unresolved omissions.
