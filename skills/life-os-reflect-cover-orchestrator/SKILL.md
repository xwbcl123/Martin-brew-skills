---
name: "life-os-reflect-cover-orchestrator"
description: "Orchestrate Life-OS daily journal reflection and cover creation across cmux or WezTerm workers. Use when the user asks to send `/reflect YYYYMMDD` to sonnet, babysit approvals, then assign Codex or another worker to run `$create-cover-illustration` only after the journal is complete."
---

# Life-OS Reflect Cover Orchestrator

Use this skill when the task is not merely "write a journal" or "make a cover", but coordinating multiple agents to do both in order.

The common pattern is:

1. Assign `/reflect YYYYMMDD` to a writing worker, usually `sonnet`.
2. Babysit the writing worker without taking over too early.
3. After the journal exists and is no longer a template, assign a cover task to a Codex worker using `create-cover-illustration`.
4. Verify the image pipeline, hosted URL, and operation log.

## Preconditions

- Read the nearest `_meta.md` before editing the journal library or system docs.
- Prefer Obsidian CLI for vault reads when it works; fall back to shell when Obsidian IPC is unavailable.
- Discover live terminal topology first. Do not rely on stale surface IDs.
- Use `surface:<n>` or WezTerm pane IDs as the delegation unit, not visual pane position.
- Choose the terminal surface from the operating system and current machine, not from habit:
  - macOS / Mac mini: prefer the `cmux` Life-OS workspace when present.
  - Windows laptop: prefer WezTerm CLI panes/tabs.
  - If the user names a surface, use that surface after verifying its working directory.
- Never assume the visible agent's default directory is the Life-OS vault. Verify the real working directory before assigning `/reflect` or cover work.

## Life-OS Root Verification

Resolve the Life-OS root before assigning work. Do not hard-code one laptop's path as universal.

Accepted roots are directories that contain both `AGENTS.md` and `10-19_Me-Health/13.10_personal-journal-lib/_meta.md`.

Common candidates:

- `H:\我的云端硬盘\Life-OS`
- `F:\我的云端硬盘\Life-OS`
- `/Users/<user>/Library/CloudStorage/GoogleDrive-*/我的云端硬盘/Life-OS`
- `/Volumes/*/我的云端硬盘/Life-OS`

Windows PowerShell check:

```powershell
$candidates = @(
  'H:\我的云端硬盘\Life-OS',
  'F:\我的云端硬盘\Life-OS'
)
$candidates | Where-Object {
  Test-Path (Join-Path $_ 'AGENTS.md') -and
  Test-Path (Join-Path $_ '10-19_Me-Health\13.10_personal-journal-lib\_meta.md')
}
```

Unix/macOS check:

```bash
find "$HOME" /Volumes -maxdepth 5 -type d -name Life-OS 2>/dev/null |
  while read -r root; do
    test -f "$root/AGENTS.md" &&
    test -f "$root/10-19_Me-Health/13.10_personal-journal-lib/_meta.md" &&
    printf '%s\n' "$root"
  done
```

If multiple valid roots exist, prefer the root in the active terminal workspace; otherwise report the candidates and choose the one the user explicitly named or the one containing the latest target journal/transcript.

## Discover Workers

For cmux on macOS / Mac mini:

```bash
cmux tree --all --json
cmux list-notifications
cmux read-screen --surface surface:<id> --lines 60
```

Prefer a dedicated Life-OS cmux workspace/surface when it exists. Verify the surface cwd or visible prompt points at the resolved Life-OS root before sending `/reflect`.

For WezTerm, use the available local CLI or terminal state commands in that environment, then capture:

- pane/tab id
- visible agent/model
- whether it is idle, running, blocked, or waiting for approval
- current working directory

Windows WezTerm discovery:

```powershell
wezterm cli list --format json
wezterm cli get-text --pane-id <id> --escapes --start-line -80
```

If a WezTerm pane is running the right agent but the wrong directory, exit the agent, change the shell directory with PowerShell, and restart from the resolved Life-OS root:

```powershell
wezterm cli send-text --pane-id <id> --no-paste "/exit`r"
wezterm cli send-text --pane-id <id> --no-paste "Set-Location -LiteralPath '<Life-OS root>'`rclaude --model sonnet`r"
```

For Codex cover work on Windows, prefer a fresh pane if the old Codex pane is stuck in command completion or cannot cleanly exit:

```powershell
wezterm cli spawn --window-id <window-id> --cwd '<Life-OS root>' powershell.exe
wezterm cli send-text --pane-id <new-pane-id> --no-paste "codex -m gpt-5.5`r"
```

After restart, read the screen again and confirm it shows the expected agent/model and the Life-OS directory before sending the task.

If both cmux and WezTerm are present, prefer the surface the user named. Otherwise use the active Life-OS worker pool.

## Assignment Order

Never assign the cover task until the journal file is complete enough to summarize.

Reflect assignment packet:

```text
/reflect YYYYMMDD
```

If the worker only loads the skill and does not start, send a concise follow-up:

```text
Please continue the loaded /reflect workflow for YYYYMMDD. Generate or update the Life-OS daily journal, then output JOURNAL_REFLECT_DONE and the journal path.
```

Cover assignment packet, after journal completion:

```text
DELEGATION TASK
Objective: Use create-cover-illustration journal-cover workflow for <journal-path>.
Repo/Vault: <Life-OS path>
Scope: <journal file>, 13.10 _assets/YYYY/MM, matching 90_logs operation log, URL map produced by the image pipeline.
Constraints:
- Read AGENTS.md, nearest _meta.md, the journal note, and .agents/skills/create-cover-illustration/SKILL.md.
- If running in Codex with built-in image_gen available, use built-in image_gen first.
- Save the source image under _assets/YYYY/MM/YYYYMMDD_journal-cover.png.
- Insert Markdown image syntax immediately after the H1.
- Run the 13.10 image pipeline dry-run and then real execution.
- Verify the note points to a hosted URL and curl HEAD returns HTTP 200 with image content-type.
- Append or create the operation log; do not overwrite existing log content from another agent.
Completion marker: END_DELEGATION_RESULT
```

## Babysitting Rules

- Approve visible prompts that are consistent with the assigned scope.
- Use `/btw` or a non-interruptive status message before interrupting a worker.
- For writing-heavy reflection tasks, give `sonnet` a full 15 minutes after it clearly enters the writing/reflection phase before taking over.
- Before the 15-minute threshold, do not rewrite the target journal unless the worker reports a blocker, shows an explicit error, or waits at an approval/confirmation prompt.
- If another agent has edited the same file, send a fact sync before the worker writes:

```text
/btw Another agent has updated <file>. Before writing, reread it and merge. Preserve existing hosted cover image blocks and append to operation logs instead of overwriting them.
```

## Completion Checks

For the journal:

```bash
rg -n "待填|待定主题|TODO|昨天是\\.\\.\\." <journal-path>
sed -n '1,80p' <journal-path>
```

For the cover:

```bash
rg -n "img\\.bruxelles|journal-cover|_assets" <journal-path> <urls-json> <operation-log>
ls -la 10-19_Me-Health/13.10_personal-journal-lib/_assets/YYYY/MM/ | rg YYYYMMDD
curl -I -L --max-time 20 "<hosted-image-url>"
```

Final report must include:

- which worker received `/reflect`
- whether the 15-minute rule was respected or why it was bypassed
- which worker ran cover generation
- journal path
- local image paths
- hosted URL and HTTP/content-type verification
- operation log path
