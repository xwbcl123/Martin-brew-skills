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

Do not conflate harness and model. Claude Code can drive Anthropic models and API-backed model profiles through `ccs`; Antigravity can pin the session model at launch with `agy --model <exact model name>` on current local builds. Use `agy models` to refresh exact model names before changing roster config.

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
skills/martin-agent-roster/scripts/bootstrap-cmux-workspaces
```

Shortcut wrappers exist in `scripts/detect-profile`, `scripts/inspect-cmux`, and `scripts/validate-roster`.
Use `scripts/bootstrap-cmux-workspaces` to render Life/Work cmux workspace layouts from the roster YAML. It defaults to dry-run; pass `--apply` only after Martin authorizes live workspace creation. Pass `--no-launch` to create titled shells without starting the agents.

## Workflow

1. Detect profile automatically; use `--profile` only as an override.
2. Validate config before planning.
3. Run `dry-run` and review:
   - update commands;
   - matched/missing/extra surfaces;
   - startup commands;
   - `needs_review` fields;
   - manual post-launch steps only for lanes that cannot be fully scripted.
4. Only use `apply` or `dream` if Martin explicitly requests live control.

## Important Local Rules

- macOS cmux Claude Code is Homebrew-managed through `claude-code@latest`; update with `brew upgrade --cask claude-code@latest`.
- Codex prefers `codex update`; fallback is `npm install -g @openai/codex`.
- Antigravity prefers `agy update`; installer script is only install/repair fallback.
- Antigravity model launch:
  - Gemini: `agy --model 'Gemini 3.5 Flash (High)'`
  - Opus: `agy --model 'Claude Opus 4.6 (Thinking)'`
  - Verify available names with `agy models`; model names are display strings and must match exactly.
  - When restarting both Gemini and Opus Antigravity lanes, launch Gemini first and delay Opus by at least 30 seconds to avoid auth/session contention.
- Cursor Agent local binary is `agent`; update with `agent update`.
- Claude Code third-party model launch:
  - DeepSeek: `zsh -lic 'ccs reset && ccs use deepseek && claude'`
  - GLM overseas: `zsh -lic 'ccs reset && ccs use glm2 && claude'`
  - MiniMax: `zsh -lic 'ccs reset && ccs use minimax && claude'`
  - Long-context behavior belongs in `ccs`, not roster labels: these profiles should export third-party model names with `[1m]` where supported plus `CLAUDE_CODE_AUTO_COMPACT_WINDOW=1000000`.
  - Verify long-context lanes with `ccs show`; `ANTHROPIC_MODEL` / `ANTHROPIC_BIG_MODEL` should show values such as `deepseek-v4-pro[1m]`, `glm-5.2[1m]`, or `MiniMax-M3[1m]`.
- Claude Code native model launch:
  - Sonnet: `zsh -lic 'ccs reset && claude --model sonnet'`
  - Opus: `zsh -lic 'ccs reset && claude --model opus'`
- Special aliases:
  - `master`: `codex -m gpt-5.5 -c 'model_reasoning_effort="high"'`
  - `planner`: `zsh -lic 'ccs reset && claude --model opus'`
  - `reviewer`: `codex -m gpt-5.5 -c 'model_reasoning_effort="xhigh"'`
  - `gpt-5.3-codex-spark`: `codex -m gpt-5.3-codex-spark -c 'model_reasoning_effort="high"'`

## Gotchas

- Antigravity auth/session contention: when restarting both Gemini and Opus Antigravity lanes, start all Gemini lanes first, wait at least 30 seconds, then start Opus lanes. This avoids concurrent auth/session refresh conflicts observed during full-roster restarts.
- cmux surface refs can drift after upgrade/restart. If `respawn-pane` causes missing or misplaced surfaces, rebuild the workspace layout from the roster, rename tabs from `surface_title_hint`, then launch agents with `cmux send` + `send-key Enter`.
