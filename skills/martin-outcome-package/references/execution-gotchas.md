# Execution Gotchas and Gates

Use this reference when the package is time-sensitive, deck-led, research-heavy, or delegated to multiple workers/tools.

## Deck-First Scheduling

If the final user-facing deliverable is a deck, D4/D5 is the critical path.

Required operating rules:

- Produce a first D4 deck outline from local context early.
- Get D4 into user review within the first 25-30% of available time when feasible.
- Start D5/deck route production no later than the midpoint of the available time.
- Reserve 30-40% of the time budget for deck QA, editability fixes, and manual polish.
- Do not spend most of the budget on D0/background research unless the topic is genuinely new or high-risk.

## D0 / Deep Research Escape Hatch

D0 is not automatically a hard gate for every outcome package.

Use full Deep Research only when one or more are true:

- The topic is new and local project context is weak.
- External facts, current rules, or official positions are material to the deliverable.
- High-impact claims need authoritative validation before use.
- The user explicitly asks for Deep Research as a required deliverable.

Cap D0 as auxiliary background when:

- Existing vault/project context already contains the decision logic.
- Deep Research output is mostly generic background.
- The main deliverable is a deck/report with a near-term deadline.

When capped, record the decision in the README or session log and move to D1-D4/D5.

## Local Context First

For Martin's project work, prioritize:

- `.req.md`, intake/grill notes, and direct oral requirements.
- Project wiki, meeting notes, prior session files, and source notes.
- Social/community signals as hypothesis sources.
- External research as gap filling and fact checking.

Do not let generic synthesis override a high-signal local source. Mark social/community sources as `hypothesis`, `operational clue`, or `direction-setting signal` unless verified by official/authoritative evidence.

## External Package Access Gate

Local package existence is not enough for GPT Pro, Gemini, Claude, or any Cloud Expert route.

Before telling the user a package is ready for an external tool, verify:

- The target-accessible folder exists, such as Google Drive `cloud-expert-delegations/`.
- `START_HERE` / launch prompt / task brief / source manifest are present and non-empty.
- A zip fallback exists when the external tool may not traverse folders reliably.
- The launch prompt tells the external tool how to locate the package.
- Sensitive local-only context is excluded, redacted, or summarized according to the source manifest.

## Delegation and Acceptance Gate

When delegating through cmux or shore:

- Create a durable task package first, preferably under `tasks/shore/YYYYMMDD_slug/`.
- Do not treat `/tmp` as the authoritative delegation package.
- Worker `completed` / `done` means only `worker_done`.
- Master must inspect landed files and set the final state: `accepted`, `needs_rework`, or `blocked`.
- For multiple cmux workers, prefer a cmux surface agent as master. Codex App is better as reviewer/archive/closeout when callbacks must be reliable.
- Define the comparison scorecard before launching parallel routes.

Suggested route comparison dimensions:

| Dimension | What to check |
|---|---|
| Narrative fit | Does it match Martin's stated angle and audience? |
| Source discipline | Are high-impact claims traceable and caveated? |
| Deck convertibility | Can D4 become slides without rewriting? |
| CN quality | Is Chinese output natural and stakeholder-ready? |
| Sensitivity handling | Are customer/model/regulator details abstracted as required? |

## Deck Route Readiness Gate

Before relying on a deck route, verify:

- Authentication/session readiness for the target tool.
- Ability to download the returned artifact.
- Artifact format: PPTX/PDF/HTML/images.
- PPTX editability: text nodes exist, not only image-baked slides.
- Compatibility with `martin-pptx-skill` / `pptx-polish` when a formal editable deck is required.

Default route posture:

- Gamma AI route: candidate for formal/editable deck, subject to PPTX QA and polish.
- NotebookLM route: visual reference by default unless editability is verified.
- Image-baked deck: acceptable as visual reference, not as the primary editable deliverable.

## State Synchronization Gate

Major gates must update state files while the work is still fresh.

After each major gate, update the relevant package/session status:

- Package `README.md`: deliverables produced, gate status, route status, archive destination.
- Session `20_execute.md`: receipts, decisions, verification, residual risks.
- Session `30_report.md`: output inventory and acceptance summary.
- Session `index.md` or task index when the task status changes.

Do not report a package as complete while the report/status files still imply it is pending.
