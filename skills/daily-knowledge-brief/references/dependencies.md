# Dependencies

## Google Workspace

- OAuth token: `$HERMES_HOME/google_token.json`.
- Helper: `$HERMES_HOME/hermes-agent/skills/productivity/google-workspace/scripts/google_api.py`.
- Prefer the `gws` binary route when installed.
- Prefer `$HERMES_HOME/hermes-agent/venv/bin/python` when the Google Workspace dependencies are installed in the Hermes application environment.
- Otherwise use an isolated venv or uv-managed interpreter with `google-api-python-client`, `google-auth-oauthlib`, and `google-auth-httplib2`.
- Never install packages into externally-managed system Python and never copy OAuth tokens into Life-OS.

Before recurring Cron activation, run a live auth check, a read-only Gmail smoke, and one explicitly marked test send.
