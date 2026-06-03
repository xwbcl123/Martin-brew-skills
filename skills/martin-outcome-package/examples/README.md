# Examples

This directory contains examples of how the martin-outcome-package skill integrates with specific environments.

## Work-PKM Vault Integration

When used within Martin's Work-PKM vault:

- **Session routing**: Packages created from `.req.md` files follow the `tasks/sessions/YYYYMMDD_slug/` convention.
- **deliverable_home**: May resolve to project folders (e.g., `20 Projects/{project}/70_delivery/`) or area folders (e.g., `30 Areas/{area}/deliverables/`).
- **Daily logging**: Package completion is logged in `Daily/YYYY/MM/YYYY-MM-DD.md`.
- **Archive routing**: Session-local deliverables with `needs_archive_destination: true` should be moved to their permanent location during session closeout.

See `80 Blueprint/agent-rules/workflow-martin-outcome-package.md` for the full Work-PKM adapter.

## Standalone Usage

The skill works without any vault-specific configuration:

```
# Agent reads SKILL.md, resolves intake from source material,
# produces D1 + D2 (minimum) under the specified deliverable_home.
```

No external dependencies, brand libraries, or vault-specific paths are required.

## Example: Quick D1+D2 from Transcript

Input: A meeting transcript or voice note.

Expected flow:
1. Intake grill identifies source as transcript, objective as inform/align.
2. D1 deep report synthesizes the transcript content.
3. D2 executive summary distills key decisions and action items.
4. Package README captures metadata and routing.

## Example: Full D1-D5 for Formal Report

Input: A `.req.md` requesting an executive report with presentation.

Expected flow:
1. Intake resolves all six deliverable gates.
2. D1-D4 produced sequentially.
3. D5 authors `design.md`, `design-stack.md`, and `martin-pptx-handoff.md`.
4. Handoff file enables `martin-pptx-skill` to start Stage 0 directly.
