---
name: video-youtube-publish
description: Plan, execute, and reconcile operator-authorized YouTube uploads, in-place updates and revision republishes from sealed packages. Supports registered production profiles and a strictly private smoke workflow with independent owner readback.
---

# YouTube publishing

Use the paired video release contract environment and local `ytpub-cli` checkout. Store packages, OAuth files, approvals and job state outside the vault and Git. `YTPUB_CLI_ROOT` can select the CLI checkout and `VIDEO_SKILLS_CONFIG` can select the profile map.

1. Register the exact channel in the operator's terminal using `scripts/operator.py login --profile PROFILE`. Use `--scope-set console-production` for the declared Console scope set. The literal `smoke-test` profile defaults to file cache and retains its private, unscheduled, unnotified policy.
2. Seal a candidate with the release contract, review its local HTML preview, and have the operator run `scripts/operator.py approve --package ROOT --profile PROFILE`. For an in-place update use `--mode update` with the same MP4, higher revision and optional `--video-id` assertion. For a new MP4 use `--supersedes-revision N` to approve the prior revision and video.
3. Run `scripts/publish.py --mode plan --package ROOT --profile PROFILE --authorization ID`. Review the profile, target, exact operation plan, privacy, schedule and notifications. Use `--preview PATH` if the preview has a nondefault name.
4. Run with `--mode publish` or `--mode update` as approved. Inspect the receipt and independent readback. Running the same sealed revision again returns the corresponding noop or a verification failure. A revision upload leaves the older YouTube video in place.
5. If an effect is uncertain use `--mode reconcile`, preserving the exact journal and receipt. Where called for, register an operator resolution and provide its ID. See [operations](references/operations.md) for the terminal and migration flows.

The smoke policy protects the underlying channel through aliases. Its verified disclosure rule accepts an omitted owner key only when the sealed literal `containsSyntheticMedia` is false. A present value must match the sealed boolean.
