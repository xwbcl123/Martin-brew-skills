# Outcomes Layout Contract

Human default surface and agent transport must stay separate.

```text
outcomes/
├── index.md
├── *_g3-comprehension-dossier.md          # live dossier; not a wiki compile source
├── reading/                               # human hub
│   ├── README.md
│   └── wiki/
└── _transport/                            # receipts, stderr, snapshots, raw exports
    ├── slash-command-outputs/
    ├── notebook-artifacts/
    ├── ingestion/
    ├── receipts/
    └── dossier-snapshots/
```

## Rules

- New receipt / stderr / json index files go to `_transport/` only.
- `reading/README.md` must reach dossier, wiki, experiments, and readable media.
- Default reading pages must not embed `*-receipt.json` or `*.stderr`.
- Paths are unit-relative. Escapes and outbound symlinks are rejected.
- Wiki compile reads `_transport/dossier-snapshots/<sha256>.md`, never the live
  dossier body after `wiki.*` writeback.

## Migration

Build `old_path → new_path → sha256 → action` before any move. Include top-level
`outcomes/*-receipt.json`, not only `outcomes/artifacts/*`.

1. Dry-run the map.
2. Apply on an isolated copy; verify links and compile.
3. Apply on the real unit with a rollback copy until verification passes.
4. Preserve original bytes. Rewrite only mutable indexes. Explain historical
   paths inside immutable receipts with a relocation map.

Old learning units are not batch-migrated by this Skill.
