# First-time setup, episode handoff and acceptance

This guide is for any new user; it must not require the original author's accounts, device layout, private knowledge base or terminal roster. The agent guides setup once, then reuses verified settings. Do not ask the user to select every downstream Skill or prepare machine hashes/receipts.

## 1. Explain the working boundary

Today the recommended workflow is: **you perform the editorial rough cut in Filmora; save the WFP and declare who occupies each audio track/channel; the agent handles the remaining production and authorized publication**.

A transcript omits tone, pauses, breaths, laughter and overlapping speech. Fully automatic rough cutting can still be slow or imprecise without reliable sound-based decisions. Audio-capable join listening reduces risk but is not proof of full editorial equivalence. Explain this before accepting a raw-only input as an unattended editing promise. Users who already have finished audio may skip WFP and multi-track reconstruction.

## 2. Resolve initial configuration once

Ask one compact batch: workspace location; language; target show/provider identity; available ASR/audio-review access; desired series artwork/bookends if any. Reuse explicit existing settings. Ask for secrets only through the supported credential mechanism, never in metadata, prompts, reports or shared files.

- Install/expose this Skill with its adjacent `podcast-final-edit`, `podcast-mastering`, `podcast-transcription`, `podcast-enrichment`, `podcast-release-package` and `podcast-transistor-publish` dependencies as needed for the selected route. Their relative paths matter. A standalone copy of this SKILL.md is insufficient. Use the host's supported Skill installation process; do not copy another user's absolute paths.
- Verify Python and the installed dependencies of the scripts actually selected, FFmpeg/ffprobe, the ASR CLI/model, an actual audio-capable review route and a browser route. The agent reports exact missing capabilities and installation instructions appropriate to the host before installing anything that lacks authorization. Native subagents are optional orchestration support; an external terminal multiplexer is not required.
- Start personal defaults from `../../podcast-release-package/references/config.example.json`. Store outside the Skills at `~/.config/podcast-skills/config.json` or the configured `PODCAST_CONFIG` path. Replace example paths, show IDs and branding with the user's values. Only use the ten supported keys; do not add invented design/theme/role-map keys.
- For Transistor publication, follow `../../podcast-transistor-publish/SKILL.md`: resolve the user's CLI installation, actual show and credential environment. Do not print or persist `TRANSISTOR_API_KEY`. Missing provider access does not prevent independent local production.
- Series branding, artwork and bookends must refer to the user's actual assets/policy. Missing optional series assets are disclosed; do not silently use another show's materials. Configure the chosen release profile and verify its actual constraints rather than copying a prior episode's thresholds blindly.

## Executable local installation

For a terminal-based installation, clone the public repository, then install the family side by side in the workspace chosen by the user. Run from that repository root:

```bash
mkdir -p /path/to/project/.agents/skills
cp -R skills/podcast-* /path/to/project/.agents/skills/
python3 -m venv /path/to/project/.venv
/path/to/project/.venv/bin/python -m pip install -r /path/to/project/.agents/skills/podcast-production-workflow/requirements-local.txt
```

Replace `/path/to/project` with the chosen absolute workspace path. Use this virtual environment's Python for all subsequent commands; globally installed packages are not assumed. The local dependency list covers production/preview/package tools; optional external ASR or audio-review adapters have their own provider requirements. FFmpeg/ffprobe and whisper-cli remain external executables. Follow the official [whisper.cpp model instructions](https://github.com/ggml-org/whisper.cpp/blob/master/models/README.md) to obtain a real model; test-only empty model files are not usable inference weights.

A family installation is required: a successful workflow `--help` does not prove its imported downstream Skills or Python dependencies are usable. Do not use the legacy human-gated local scripts as the new delegated entry merely because their filenames mention baseline.

## Executable configuration and intake check

The agent can run these commands on the user's behalf. They are not extra approval steps. After installation, use the chosen virtual environment and absolute paths:

```bash
/path/to/project/.venv/bin/python /path/to/project/.agents/skills/podcast-production-workflow/scripts/startup.py setup --config /path/to/user-config/podcast-skills.json --workspace /path/to/project --language en --whisper-cli /path/to/whisper-cli --whisper-model /path/to/ggml-model.bin
/path/to/project/.venv/bin/python /path/to/project/.agents/skills/podcast-production-workflow/scripts/startup.py check --config /path/to/user-config/podcast-skills.json --episode-dir /path/to/episode --mode local --output /path/to/task/startup-r001.json
```

Point `PODCAST_CONFIG` to that same absolute config file for downstream tools, or create the config at the default `~/.config/podcast-skills/config.json` location. Setup refuses to overwrite an existing config; reuse and inspect it instead. The checker uses the Markdown handoff template below; the agent normalizes other layouts from actual user metadata rather than asking the user to invent a new JSON file. Metadata-relative source/WFP paths resolve beside `_meta.md`, independently of the shell's working directory.

The checker batches real missing/conflicting input facts, probes streams, and records source hashes. `ready` means ready to begin its named next stage. WFP semantic/source binding, dual-mono acoustic checks, actual ASR, listening and preview behavior remain Agent work in `pending_checks`; their being unperformed does not create another user confirmation. Local mode requires no hosting credential or real provider show ID. A publish check does not grant authority, access an account, or create a remote episode. Reports refuse to overwrite source/config or an existing report; use a new report revision after changed inputs.

## 3. Verify setup before a long production run

Perform a bounded local smoke: probe actual sample media, verify ASR/model availability, send a short permitted audio clip through the selected listening route, and test preview playback/seek with HTTP Range and browser interaction. A configured model name or installed CLI alone is insufficient. This smoke does not publish, create a draft or claim full-episode acceptance.

Check only capabilities required now. Before a requested publication, verify provider/show access through the supported read/plan path; do not use an upload as a connectivity test. Record paths, tool versions and capabilities without credentials so subsequent episodes do not repeat the interview. Unverified items remain explicitly unverified.

## 4. Give the user a small handoff template

Keep originals available. Save the final selected Filmora project; make sure referenced original files remain accessible. Metadata can be ordinary Markdown; this is a human/agent intake template, not a newly supported machine JSON schema:

```markdown
# Episode handoff
- Episode: <show name / episode number or stable episode key>
- Target show ID: <actual provider show, or resolve during setup>
- Original media: <absolute file path or exact source list>
- Rough-cut WFP: <absolute saved project path>
- Edit intent: preserve my rough-cut deletions; agent completes via FFmpeg
- Speakers:
  - <speaker A>: absolute stream <N>, audio-relative index <M>, left
  - <speaker B>: absolute stream <N>, audio-relative index <M>, right
  - <host>: absolute stream <N>, audio-relative index <M>, dual mono
- Other tracks: <declared unused/silent/unknown; agent verifies>
- Episode exceptions: <optional pronunciation/privacy/branding instructions>
```

All indices and speakers above are placeholders; the agent probes and explains them if the user needs help. Dual-mono must be verified, not summed twice. A Filmora streamId is not an FFmpeg stream index. The user declares who is speaking; the agent does geometry/extraction work. A conflict is resolved once before rendering.

## 5. One instruction starts the episode

> $podcast-production-workflow /goal 发布这一集：<单集目录绝对路径>。人工粗剪已完成；按 WFP 和 _meta.md 接手，独立验收通过后正式发布。

This carries publication intent for the resolved episode. The agent handles any required final hash-binding from that original instruction. Do not ask the user to approve mastering, generated text, screenshots, draft or publish again on a passing delegated path. If the user requests local review instead, respect that scope. Host-specific `/goal` availability is checked rather than assumed.

## 6. Explain what completion means

At closeout provide:

- Correct show/episode identity and public state, share/transcript links and local deliverables.
- Source/WFP-to-delivery lineage, measured audio QC and actual listening coverage, including unresolved uncertainty and whether anyone listened to the full episode.
- Independent content, experience and implementation acceptance; actual desktop/mobile preview behavior and screenshots; current package validation/seal.
- Provider metadata/media/transcript/artwork readback and duplicate-prevention/recovery receipts. Public reading text is checked completely and in order.
- Honest limits: agent-delegated review is not human review; desktop mobile viewport checks are not a physical-phone rehearsal; rights provenance is recorded as declared/verified/unknown as supported by evidence.

These are agent completion duties, not a checklist the user must click through. A repairable failed check sends work back to the responsible agent. A critical unresolved input, integrity, required review, capability, concrete risk or mutation ambiguity is surfaced clearly with the smallest decision needed.

## 7. Future automatic rough cutting

Keep it explicitly experimental until representative held-out episodes demonstrate acoustic continuity, retention of meaning/tone, missed cuts, false cuts, human correction effort and wall-clock time. Compare against the user's cut using real audio, not transcript similarity alone. New model availability is a reason to evaluate, not a reason to remove the human rough-cut boundary by default.
