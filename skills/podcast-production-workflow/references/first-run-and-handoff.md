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
