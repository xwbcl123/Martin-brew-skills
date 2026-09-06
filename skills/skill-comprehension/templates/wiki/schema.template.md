# Wiki schema

- page types: `dossier`, `module`, `studio`, `meta`
- required flattened frontmatter: `type`, `unit_id`, `page_id`, `sources[]`, `generated_by`, `compiler_version`, `evidence_boundary`
- present sources stay `unconfirmed` until a locator upgrades a claim
- `item_id` is a kebab-case slug; destination symlinks and path escapes are rejected
- `log.md` is append-only runtime history and is outside content identity
- quiz/flashcard answers enter `reading/` only when `quiz_answers_collected` is the JSON boolean `true` with path+sha256+non-empty locator
- unknown JSON is a metadata card; known JSON schemas may pretty-print
