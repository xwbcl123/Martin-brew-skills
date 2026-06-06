---
title: "Handoff - WezTerm Testing for Martin Agent Roster"
type: task-handoff
status: active
created: 2026-06-06
updated: 2026-06-06
---

# Handoff - WezTerm Testing for Martin Agent Roster

## Current Status

`martin-agent-roster` is implemented and tested on macOS cmux for the `Life` and `Work` workspaces.

The cmux path is considered functionally validated:

- Profile detection selects `macos-cmux`.
- Roster validation passes with `27` services and `0` schema errors.
- Guarded dry-run works for `Life` and `Work`.
- Explicit apply works for `Life` and `Work`.
- Update commands work:
  - Claude Code: `brew upgrade --cask claude-code@latest`
  - Codex: `codex update`
  - Antigravity: `agy update`
  - Cursor Agent: `agent update`
- Launch commands work for Claude Code, Codex, Antigravity, Cursor Agent, and Codex remote control.

## Known Residual cmux Notes

- Antigravity (`agy`) cannot reliably select the model by startup flag in the current implementation.
- `agy` surfaces must still use `/model` inside the TUI for model-specific lanes.
- In the Work apply test, `work-opus` launched but defaulted to Gemini 3.5 Flash; it still needs manual `/model` switch to Opus 4.6 Thinking.
- CWD drift is real. Apply logic should use explicit `cd <workspace> && <launch>` before starting a harness. This fixed the first `life-sonnet` launch issue.

## WezTerm Test Goal

Verify whether the same skill architecture can operate Martin's WezTerm topology.

The expected WezTerm differences:

- WezTerm does not have cmux's workspace layer.
- Windows / Linux use WezTerm.
- Linux may be reached through `wezterm connect <target>`, which is effectively a WezTerm SSH-server-backed tmux-style remote terminal mode.
- Profile detection must decide whether the effective agent host is local Windows, local Linux, or a Linux remote reached through WezTerm.

## Required WezTerm Work

1. Add a WezTerm profile.

Suggested config path:

```text
skills/martin-agent-roster/config/profiles/wezterm-*.yaml
```

2. Add WezTerm inspector support to `scripts/roster.py`.

Likely commands to research / verify on the target machine:

```bash
wezterm cli list --format json
wezterm cli get-text --pane-id <id>
wezterm cli list-clients
wezterm cli list-tabs
```

3. Map WezTerm topology into the same internal rows used by cmux.

Current cmux row shape:

```json
{
  "window_ref": "...",
  "workspace_ref": "...",
  "workspace_title": "...",
  "pane_ref": "...",
  "pane_index": 0,
  "surface_ref": "...",
  "surface_title": "...",
  "index_in_pane": 0,
  "type": "terminal",
  "tty": "...",
  "selected": true
}
```

For WezTerm, use `workspace_title: null` or a profile-level synthetic workspace name if needed.

4. Implement guarded dry-run first.

Do not apply live WezTerm control until dry-run confirms:

- profile detection is unambiguous;
- tab / pane matching is correct;
- all target panes are idle shell or explicitly safe;
- launch commands are correct for the target OS / remote host.

5. Only then test explicit apply.

Use a separate command such as:

```bash
python3 skills/martin-agent-roster/scripts/roster.py dry-run --profile wezterm-<host>
```

Then, after manual confirmation:

```bash
python3 skills/martin-agent-roster/scripts/roster.py apply --profile wezterm-<host>
```

`apply` is not implemented in the synced v1 script yet; cmux apply was performed manually through `cmux send` after dry-run.

## Suggested Implementation Notes

- Keep `agent_harness` separate from `model_slot` and `observed_model`.
- Keep command catalogs profile-aware.
- Do not assume title equals runtime model.
- Use explicit CWD prefixes before launch.
- Preserve three authority modes:
  - `guarded`
  - `apply`
  - `dream`
- If WezTerm profile detection is ambiguous, stop and ask Martin to confirm.

## Files To Start From

```text
skills/martin-agent-roster/SKILL.md
skills/martin-agent-roster/config/commands.yaml
skills/martin-agent-roster/config/model_catalog.yaml
skills/martin-agent-roster/config/profiles/macos-cmux.yaml
skills/martin-agent-roster/scripts/roster.py
```

## Completion Criteria For WezTerm Phase

- A WezTerm profile exists.
- `validate-roster` passes for the WezTerm profile.
- `detect-profile` can select or safely ask for the WezTerm profile.
- WezTerm dry-run produces a correct startup plan.
- At least one explicit WezTerm apply test succeeds.
- Handoff/result notes clearly state whether Windows local, Linux local, and `wezterm connect` remote modes were tested.

