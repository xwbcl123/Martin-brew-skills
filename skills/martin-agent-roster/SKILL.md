---
name: martin-agent-roster
description: Operate Martin's local command-line agent fleet across cmux and WezTerm profiles. Use for detecting the active roster profile, inspecting cmux/WezTerm topology, planning CLI agent updates, dry-running or applying guarded agent restarts, and maintaining model/harness routing for Claude Code, Codex, Antigravity, and Cursor Agent.
---

# Martin Agent Roster

Use this Skill when Martin asks to update, inspect, restart, cold-start, or maintain local terminal agent rosters.

## Core Model

- `agent_harness`: the CLI harness that hosts the agent, such as `claude-code`, `codex`, `antigravity`, or `cursor-agent`.
- `model_slot`: the intended model lane named by the tab/surface, such as `deepseek`, `gpt-5.5-high`, or `gemini-3.5-flash`. For Codex GPT-5.5 lanes, `high` / `xhigh` are reasoning effort values, not model names.
- `observed_model`: runtime state inferred from screen/status/process inspection.
- `layout`: terminal topology, such as cmux `workspace -> pane -> surface`.
- `service`: desired semantic agent slot attached to a layout selector.

Do not conflate harness and model. Claude Code can drive Anthropic models and API-backed model profiles through `ccs`; Antigravity model choice may require an in-TUI `/model` change after launch.

## Authority Modes

- `guarded`: default. Inspect, validate, and produce plans only. Do not send commands to live surfaces.
- `apply`: explicit user-authorized live control. May send exit/restart commands after dry-run review.
- `dream`: explicit overnight full-auto mode. Must verify idle/stopped state before live control.

If profile detection is ambiguous, stop and ask Martin to confirm.

## Scripts

Prefer the bundled script interface:

```bash
python3 skills/martin-agent-roster/scripts/roster.py detect-profile
python3 skills/martin-agent-roster/scripts/roster.py validate-roster --profile macos-cmux
python3 skills/martin-agent-roster/scripts/roster.py dry-run --profile macos-cmux --workspace Life
```

Shortcut wrappers exist in `scripts/detect-profile`, `scripts/inspect-cmux`, and `scripts/validate-roster`.

## Workflow

1. Detect profile automatically; use `--profile` only as an override.
2. Validate config before planning.
3. Run `dry-run` and review:
   - update commands;
   - matched/missing/extra surfaces;
   - startup commands;
   - `needs_review` fields;
   - manual post-launch steps such as Antigravity `/model`.
4. Only use `apply` or `dream` if Martin explicitly requests live control.

## Important Local Rules

- macOS cmux Claude Code is Homebrew-managed through `claude-code@latest`; update with `brew upgrade --cask claude-code@latest`.
- Codex prefers `codex update`; fallback is `npm install -g @openai/codex`.
- Antigravity prefers `agy update`; installer script is only install/repair fallback.
- Cursor Agent local binary is `agent`; update with `agent update`.
- Claude Code third-party model launch:
  - DeepSeek: `ccs reset && ccs use deepseek && claude`
  - GLM overseas: `ccs reset && ccs use glm2 && claude`
  - MiniMax: `ccs reset && ccs use minimax && claude`
- Claude Code native model launch:
  - Sonnet: `ccs reset && claude --model sonnet`
  - Opus: `ccs reset && claude --model opus`
- Special aliases:
  - `master`: `codex -m gpt-5.5 -c 'model_reasoning_effort="high"'`
  - `planner`: `ccs reset && claude --model opus`
  - `reviewer`: `codex -m gpt-5.5 -c 'model_reasoning_effort="xhigh"'`
  - `codex-5.3-spark`: `codex -m codex-5.3-spark -c 'model_reasoning_effort="high"'`
