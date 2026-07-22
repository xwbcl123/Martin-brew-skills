# Configuration

Store these variables only in `$HERMES_HOME/.env` with file mode `600`:

```dotenv
HERMES_R2_ACCESS_KEY_ID=...
HERMES_R2_SECRET_ACCESS_KEY=...
HERMES_R2_BUCKET_NAME=agent-public-artifacts
HERMES_R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
HERMES_R2_PUBLIC_URL=https://<bucket-id>.r2.dev
HERMES_R2_UPLOAD_PREFIX=deep-research
```

The token must have Object Read & Write permission scoped only to the dedicated
Bucket. `HERMES_R2_PUBLIC_URL` is replaceable with a Custom Domain later; object
keys and manifests must not depend on the host name.

Runtime paths:

```text
Global registry:  <Life-OS>/.automation/r2-publisher/publications.jsonl
Cleanup plans:    <Life-OS>/.automation/r2-publisher/cleanup-plans/
Task manifest:    <report-package>/publish-manifest.json
```

Optional runtime override:

```dotenv
LIFE_OS_ROOT=/absolute/path/to/Life-OS
```

If unset, the CLI discovers the Vault root from its installed Skill source or
the current working directory.
