---
name: video-release-contract
description: Assemble, validate, and seal an offline video release package with an MP4, thumbnail, timed captions, reading transcript, enrichment, credits, and explicit YouTube metadata. Render a local review preview before handing a sealed package to a release operator.
---

# Video release contract

Use an absolute, local package directory outside the vault and Git. Install Python 3.12, the locked dependencies in this Skill, and FFmpeg with FFprobe. Use the same locked environment, FFmpeg, and FFprobe throughout one candidate review.

1. Supply an assembly input naming the material files and fields from `references/video-package.schema.json`. File records in the input are relative path strings. The assembler resolves their bytes and writes `video-package.json` and the exact `youtube_payload.json`.
2. Run `scripts/validate.py --package ROOT --profile PROFILE --report REPORT.json`. Review G01–G13, including technical quality, metadata, subtitles, rights, and the profile-to-channel binding.
3. Run `scripts/seal.py --package ROOT --profile PROFILE` on the reviewed revision. Run `scripts/render_preview.py --package ROOT --profile PROFILE --output PREVIEW.html` with the preview beside the package. Inspect the thumbnail, synopsis, captions and video in Chrome using the local file.
4. Recheck using `scripts/validate.py --package ROOT --profile PROFILE --require-seal`. Review reports and the preview belong outside the sealed directory. Reassemble and seal a new revision if any bound bytes change. 
5. Hand the sealed package and local preview to `video-youtube-publish` with its registered profile. For the same MP4, use a higher package revision and an in-place update approval. A higher revision with a changed MP4 requires an explicit republish approval. The operator grants authority separately.

Invoke the scripts with the contract environment's Python. The channel profile map defaults to `~/.config/video-skills/config.json` and accepts the same explicit `--config` path across all stages. Keep OAuth and approval material outside the package. `scripts/make_smoke.py --directory NEW_DIRECTORY --profile smoke-test` builds a synthetic 15-second test package and preview locally.

See [contract operations](references/operations.md) for the file layout and report interpretation.
