# Single-Agent Workflow

1. Resolve `source_path` and `wiki_root`.
2. Probe whether a wiki contract already exists.
3. Choose `rerun_mode`.
4. Ingest sources into `raw/`.
5. If enabled, build `raw-normalized/` and write `rename_map`.
6. Extract supported files into `analysis/ingest-src/`.
7. Generate the base governance and starter wiki pages.
8. Review `skipped_files` and `uncertain_items`.
9. Summarize outputs and residual gaps.
