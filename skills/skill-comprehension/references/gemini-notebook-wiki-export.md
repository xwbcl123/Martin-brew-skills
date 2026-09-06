# Skill Wiki Compile

Compile existing comprehension outputs into an Obsidian-compatible wiki.
This is a deterministic view of already-produced knowledge. It is not a second
LLM ingest and is not mastery evidence.

## Trigger

- Notebook add-on exported → default compile.
- No Notebook → dossier-only compile; list missing modules.
- `wiki_compiled` means compile + integrity checks passed. It does not set
  `artifact_exported_to_vault` or Stage 7/8 mastery fields.

## Command

```bash
python3 scripts/compile_skill_wiki.py \
  --learning-unit /path/to/YYYY-MM-DD_slug \
  --input-manifest /path/to/wiki-input-manifest.json \
  --output outcomes/reading/wiki \
  --dry-run
```

`--dry-run` writes nothing.

## Input manifest

Compiler consumes only the allowlist. Live Dossier `wiki.*` writeback is not a
source. Use an immutable snapshot:

`outcomes/_transport/dossier-snapshots/<sha256>.md`

Each input: `role`, `item_id`, `path` or `null`, `sha256` or `null`, `status`,
`artifact_type`, optional `format`, optional `order`.

`item_id` is a kebab-case slug (`architecture`, `slide-deck`). Slashes and `..`
are rejected before any write. Destination paths and parent chains must stay
under `--output`; destination symlinks are refused.

Optional `playback` on an input (`path`, `sha256`, `format`) is the only legal
embed alias. It is part of input identity. Undeclared sibling files are ignored.
A declared alias that is missing or hash-mismatched fails.

`dossier_snapshot` path must be `outcomes/_transport/dossier-snapshots/<sha256>.md`.
Live Dossier bodies are not compile sources.

Page names are `NN-slug.md` (modules at wiki root, studio under `studio/`).
`NN` comes from `order`, else a `NN_` filename prefix, else the slash/artifact
map (`01` Architecture … `08` Artifact Prompt; studio `01` Custom report …
`09` Mind map).

- Multiple modules are legal.
- Same `role+item_id+format` twice without an explicit choice is an error.
- Dual formats of one `item_id` share one studio page as separate format cards.
- `pending` / `missing` use `sha256: null`. Do not invent hashes.

Quiz control (part of content identity):

```json
{
  "quiz_answers_collected": false,
  "quiz_evidence": { "path": null, "sha256": null, "locator": null }
}
```

`quiz_answers_collected` must be a JSON boolean. `1`, `"true"`, and other
truthy values are errors. `true` requires a non-empty Martin-answer file,
matching sha256, and a non-empty locator. Default reading navigation must not
show quiz/flashcard answers otherwise. Unlocking answers is not Stage 7 mastery.

## Render

| Type | Behavior |
|---|---|
| markdown | full source text |
| json | known schemas: typed pretty-print; unknown JSON: metadata card + original link |
| csv | Markdown table + link to original CSV |
| pdf / png / mp3 / mp4 | Obsidian embed `![](relative)` plus open link |
| pptx | open link; prefer PDF sibling for preview |
| pending/missing/unsupported | visible placeholder |

Do not turn receipt/stderr JSON into the reading body. Studio pages must point
at the artifact file itself.

`log.md` is append-only and excluded from `content_hash`.

The compiler records per-page SHA-256 in `content-manifest.json`. Overwrite or
delete requires the current bytes to match that fingerprint. A `generated_by`
substring is not ownership. Leftover `.next` is refused. Unregistered files in
the live wiki are copied byte-for-byte into the new tree; they are never
dropped by directory swap. Only the exact leftover directory `.next/` is
ignored, not names that merely start with `.next`. Automatic recovery requires
a complete `content-manifest.json` (`pages` == `page_hashes` keys, matching
`content_hash`, current `unit_id`). Unknown or incomplete commit/prev
directories stay untouched and fail closed. Human files added to `prev` after
an interrupted swap are merged into live before `prev` is removed.
`--adopt-legacy-pages` is a one-time upgrade for manifests that have `pages`
but no `page_hashes`.

## Frontmatter

Flattened fields (not a nested `wiki:` blob): `type`, `unit_id`, `page_id`,
`sources[{path,sha256,locator,status}]`, `generated_by`, `compiler_version`,
`evidence_boundary`. A present source file is `unconfirmed`, not `confirmed`.
Dual-format studio pages keep every format in `sources[]`.
