---
name: "life-os-reflect-cover-orchestrator"
description: "Orchestrate Life-OS daily journal reflection and cover creation across cmux or WezTerm workers. Use when the user asks to send `/reflect YYYYMMDD` to a writing worker, babysit approvals, then assign Codex or another worker to run `$create-cover-illustration` only after the journal is complete."
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
- Prefer the user's vault CLI for vault reads when it works; fall back to shell when IPC is unavailable.
- Discover live terminal topology first. Do not rely on stale surface IDs.
- Use `surface:<n>` or WezTerm pane IDs as the delegation unit, not visual pane position.

## Discover Workers

For cmux:

```bash
cmux tree --all --json
cmux list-notifications
cmux read-screen --surface surface:<id> --lines 60
```

For WezTerm, use the available local CLI or terminal state commands in that environment, then capture:

- pane/tab id
- visible agent/model
- whether it is idle, running, blocked, or waiting for approval
- current working directory

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
Scope: <journal file>, matching journal cover asset folder, matching operation log, URL map produced by the image pipeline.
Constraints:
- Read AGENTS.md, nearest _meta.md, the journal note, and the local create-cover-illustration SKILL.md.
- If running in Codex with built-in image_gen available, use built-in image_gen first.
- Save the source image under the journal asset folder as YYYYMMDD_journal-cover.png.
- Insert Markdown image syntax immediately after the H1.
- Run the configured journal image pipeline dry-run and then real execution.
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
rg -n "TODO|TBD|待填|待定|template placeholder" <journal-path>
sed -n '1,80p' <journal-path>
```

For the cover:

```bash
rg -n "https?://|journal-cover|_assets" <journal-path> <urls-json> <operation-log>
ls -la <journal-assets-dir>/YYYY/MM/ | rg YYYYMMDD
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
