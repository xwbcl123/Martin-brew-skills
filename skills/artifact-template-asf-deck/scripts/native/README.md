# Native generator

Requires Node with `@oai/artifact-tool`, `@napi-rs/canvas`, plus Chrome/Playwright for HTML recapture. Use the installed Presentations skill's finalizer and bundled Python. Configure `ASF_RUNTIME_NODE_MODULES` or `NODE_PATH`, `PRESENTATIONS_SKILL_DIR`, and `RUNTIME_PYTHON`; optionally `ASF_BRAND_ROOT`.

See `../../references/native-contract.md` for all semantics and limits.

- `capture.mjs --source-root DIR --output-dir NATIVE_ROOT --brand-root DIR`: compile accepted production HTML into portable layouts and sample JSON. Official brand hashes are required; Git metadata is not.
- `build.mjs --input JSON --resource-root NATIVE_ROOT --output-dir NEW_ROOT --brand-root DIR --name NAME`: create/finalize/reimport/render 12 native slides. Output name must be unused.
- `smoke.mjs --input FINAL.pptx --output-dir NEW_WORK_DIR`: edit imported text, table, chart and diagram node, validate embedded workbook, save and reopen.
- `verify_ooxml.py --input FINAL.pptx --layout LAYOUT.json --content INPUT.json --report REPORT.json`: assert source text, native structures, connector attachment/direction, 12pt floor, grid removal, native theme and 0/50/100 chart scale.

The layouts freeze source geometry; inputs independently supply fresh text/data. `*.sample.json` preserves the approved instructional copy. `*.fresh.json` is a test-only generic reuse fixture. Production build intermediates live under work; test-only output roots also live inside work.
