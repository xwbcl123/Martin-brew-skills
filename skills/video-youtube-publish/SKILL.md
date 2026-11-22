---
name: video-youtube-publish
description: Plan, execute, and reconcile an explicitly operator-authorized private YouTube smoke upload from a sealed video-release-contract package. Verify the owned channel, private status, processing, thumbnail, timed captions, and optional private playlist by independent readback.
---

# Private YouTube smoke publishing

Use the paired `video-release-contract` Python environment and local `ytpub-cli` checkout. Keep the package, OAuth files, operator ledger and job state on the local filesystem outside the vault and Git.

1. Have the operator run `scripts/operator.py login` in their own terminal to register the exact smoke channel and complete Desktop OAuth consent. This entry point selects file storage for the smoke setup. Direct `ytpub auth login` defaults to macOS Keychain. File storage uses explicit backend selection and the `YTPUB_CLIENT_SECRET` and `YTPUB_TOKEN_PATH` paths.
2. Build and review a local synthetic package with the paired contract Skill. Have the operator run `scripts/operator.py approve --package ROOT --cache-backend file` and retain the returned authorization ID.
3. Run `scripts/publish.py --mode plan --package ROOT --profile smoke-test --authorization ID --cache-backend file`. Inspect the channel, planned writes, privacy, notifications, and quota. Pass `--preview PATH` if the preview name differs from `video-release-preview.html`.
4. Use the same arguments with `--mode publish` for an approved package. The expected request is private with subscriber notifications disabled, no scheduled time, and an explicit synthetic-media boolean. For an approved literal `false`, an omitted owner readback key can pass with `observed: null` and evidence status `api_omitted_false_default`. A present value must exactly match the expected boolean. Inspect the receipt and readback after success. Repeat with the same sealed candidate and ID to confirm idempotency.
5. If a request may have reached YouTube, run `--mode reconcile`. Preserve the job directory and intent history. Submit an operator resolution only when its exact evidence and attempt are known. See [operations](references/operations.md).

Invoke scripts with the contract environment's Python. An authorization argument is a registered ID. For expiry during a job, have the operator approve a successor with `--supersedes ID` for the same sealed package. Leave the resulting smoke video private.
