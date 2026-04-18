# Multi-Agent Delegation

Use terminal delegation only as an optional accelerator. The main agent remains accountable for taxonomy, synthesis, acceptance, and final handoff.

## Good Parallel Work

- inventory review
- semantic clustering candidates
- source sampling and thesis extraction
- extraction QA
- MoC coverage QC
- link cleanup

## Role Split

Explorer agents can do read-only work:

- list source files by type and theme
- propose semantic clusters
- sample important files and extract candidate theses
- compare MoC links against inventory for omissions

Worker agents can write only when ownership is explicit:

- one worker may draft one assigned MoC page
- another worker may clean one assigned evidence page
- no two workers should write the same file

The main agent must keep:

- final taxonomy
- profile selection
- index and overview synthesis
- final acceptance
- coverage QC sign-off

## Required Probe

Before dispatching:

1. detect `wezterm` or `tmux`
2. verify pane/session is idle
3. verify cwd matches the target vault or repo
4. dispatch a short bounded task
5. require a completion callback or poll explicitly

## Keep With Main Agent

- profile selection
- rerun mode choice
- acceptance of generated governance files
- final synthesis of overview/index pages
- final MoC taxonomy
- final coverage QC decision
