# Route-aware acceptance

For explanatory visuals, apply [visual/text composition](visual-contract.md). Textless mode must pass component-to-native-label proximity and shared reading-order checks at final slide size. Embedded-text mode must pass source-exact wording and text-to-object/topology checks, with its noneditable boundary disclosed. A tidy side-by-side image and detached list does not satisfy integrated infographic acceptance.

| Check | native | image-deck | text-editable |
|---|---|---|---|
| Source facts, numbers, slide count | required | required | required |
| Selected brand/template font/layout | required | required | required |
| Actual generated image provenance | if generated | new generated pages | if background edited |
| Background text removal + visual preservation | if used | N/A | required |
| Render every final page and inspect | required | required | required |
| Editable content | required native objects | explicitly image-only | ordinary text only |
| Edit exported object and re-render copy | representative | N/A | representative |

A manifest or script pass proves only the checks it performs. Width/height checks do not prove background cleanliness. Source-to-render review must identify double letters, chart changes, cut-off text and missing logo. Template font/size requirements supersede old Calibri/16pt defaults. Notes and visible evidence retain the source's uncertainty.

Check the affected pages and dependencies after repair. Do not create extra route outputs or run indefinite verification. Failures block delivery of the affected promised feature; finish independent authorized outputs and report the exact limitation. Keep test logs in the Task Session and final deliverables in the declared artifact root.

Before assembly: verify Martin approval of the current Outline revision/section and current Spec/Plan binding. Inherit the selected organization template when supplied; new style/material deviation triggers design review. Design rationale may reuse an existing Design/Style file; new/material work still requires the machine-readable Visual Contract and its verification phases. After verified stage delivery or changed gate, refresh the parent handoff.


## Executable gates

Follow [verification](verification.md): `plan` before asset production, `assets` before dependent assembly, `final` after actual export and render review. Keep receipts with the run, not in the reusable Skill. Stale hashes/plans, missing reviews, early recorded build start and final native/image mismatches block the dependent stage. These checks supplement host finalization, template compliance, actual text/meaning review and promised representative edit/rerender; they do not replace them.

## Visual QC and production discipline

- Compliance/finalizer PASS is necessary, not sufficient. Before delivery, score the rendered deck with the [visual QC rubric](visual-qc-rubric.md): 8 items, 16 points, per-slide side by side with a reference deck, weakest 3 slides listed. Below 13/16 or any item at 0 blocks delivery.
- The Outline gate is the default. A waiver must be recorded in the session decision log (who, when, why) and followed by a 3-slide sample check (render, rubric, reference comparison) before the remaining slides are built.
- A first draft of 10 or more slides finished in under 10 minutes triggers stop-and-review: render, score and compare before continuing.
- Production stays with an agent that can render and view slides; do not outsource building to an executor that cannot.

## External traces and delivery channel

- Before anything leaves the team, run `python3 scripts/scan_external_traces.py <deck.pptx> <deck.pdf>` with the project's deny terms (`--deny`, `--deny-file`; add `--zh-style` for Chinese decks). It reads slide text, speaker notes, chart text, image descriptions, docProps and the PDF text layer. Any finding blocks the send. Template docProps often carry a foreign author/application; reset them before export.
- Review rounds: send each intermediate version to the reviewer with a one-line change list. Before every send, re-read the newest instructions; a send is irreversible and later "pause" or scope messages may already be waiting.
- Final: after acceptance, publish the final through the host's closeout/publication channel rather than e-mailing it again. Record the published path and checksums in the session report.
- Verify a sent message from the mail client's Sent folder (recipients, attachment names); never batch-operate on other agents' outgoing messages.
