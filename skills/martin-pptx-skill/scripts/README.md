# Current route tools

Resolve Node/Python/packages through the current host dependency tool. Do not install substitutes into the bundle. In Codex, read the current Presentations implementation, call its operation marker once before authoring, and use its finalizer after composition. If LibreOffice is needed, use the absolute bundled binary path returned by the host, never the user's desktop installation.

## Visual Contract verifier (all production routes)

Read [schema, review records and commands](../references/verification.md). `verify_visual_contract.py` uses Python standard library only. Plan/assets/final checks enforce frozen file bindings, label/component geometry and recorded phase order; final also inspects actual PPTX objects and bound render reviews. It cannot certify image semantics or reviewer truth. `tests/test_visual_contract.py` creates synthetic positive/tamper/failure cases only in auto-cleaned temporary directories:

```bash
python3 -B -m unittest discover -s <skill>/tests -v
```

## Two-layer composer

```bash
# RUNTIME_NODE and RUNTIME_NODE_MODULES come from load_workspace_dependencies.
RUNTIME_NODE_MODULES="<bundled packages>" "<bundled Node>" "<skill>/scripts/compose_layers.mjs" manifest.json build/draft.pptx build/previews
"<bundled Python>" "<skill>/scripts/validate_layers.py" manifest.json build/draft.pptx --require-visual-review --out build/validation.json
```

Read [manifest schema](../references/artifact-schema.md). The composer resolves images and prompts relative to the manifest, rejects hash changes/invalid coordinates/aspect distortion and refuses output overwrite. It writes one image plus ordinary native text per slide (or image-only for `image-deck`), previews, layouts and `composition.json`. It does not call imagegen, perform OCR, certify background hygiene, or produce a finalizer-approved file.

`validate_layers.py` checks package slide count, disk hashes, embedded media byte hashes through slide relationships, original image dimensions, page/layer geometry, one image layer, ordered text and recorded review. Media transcoding fails byte comparison; a host that transcodes needs an explicit pixel comparison adapter, not a silently skipped check. It requires Pillow in the selected Python. It does not determine whether QA notes are true. Final acceptance requires actual source/background/render inspection and a representative exported-text edit/re-render test.

## Route / run helpers

```bash
python3 scripts/decide_route.py --source-images
python3 scripts/decide_route.py --editable-data
python3 scripts/decide_route.py --route image-deck
python3 scripts/verify_run_folder.py --run-folder <run>
```

`decide_route.py` emits only one route; impossible image+editable-data requests fail. `verify_run_folder.py` checks a current manifest exists. It is an inventory check, not deck acceptance. Use `--legacy --formal-pptx true` only for the old multi-file schema.

## Historical helpers

`build_option5_deck.py`, `build_motherboard_from_outline.py`, `build_imagegen_motherboard_prompts.py`, `build_qc_report.py`, `text_fidelity_gate.py`, `deck_utils.py`, `render_pptx.py`, `make_contact_sheet.py` and `extract_pptx_text_metrics.py` support historical runs. They may assume older fonts, filenames, Python backends or runtimes. They do not supersede the current host contract. Do not call the historical `render_pptx.py` in Codex if it resolves the user's desktop LibreOffice. `bg_gate.py` is dimensions-only; clean dimensions leave the semantic review pending.
