# ASF Brand System — Agent Instructions

This repository is the single source of truth for the AI Security Forum (ASF) brand: tokens, logo, icons, fonts, component registry and page patterns. Consumers (the ASF website, decks, newsletters, social art) read it; they never copy values out of it by hand.

## Read in this order
1. `llms.txt` — index of every file and when to read it.
2. `DESIGN.md` — brand rules: registers, logo, colour, type, UI, channels, Office documents, layout.
3. `tokens/tokens.json` (generated) or `tokens/tokens.css` (SSOT) — every value.
4. `registry/components.json`, `registry/patterns.json`, `registry/icons.json` — what exists and its status.
5. `CHANGELOG.md` and `migrations/` — what changed between the consumer's locked version and now.

## Rules for consumers
1. **Pick a register first.** Paper (publish) or Ink (convene). Declare it with `data-register="paper|ink"` on the page or band root. Use register-resolved variables (`--asf-accent`, `--asf-kicker`, `--asf-text-muted`, `--asf-border`, `--asf-raised`, `--asf-positive|info|warning|critical`).
2. **Tokens only.** No raw colour, font size, spacing, radius, shadow or duration in consumer code. A missing value is a proposal to this repo, never a local invention.
3. **Component status.** `stable`: use. `draft`: use and complete the spec. `gap`: do not invent visuals; propose here first. `retire`: never use.
4. **Forbidden.** Mint on paper or white; glow; glass blur; gradient washes; shield, padlock or brain icons; invented numbers.
5. **Versions.** Consumers pin a tag. Majors require running `migrations/<from>-to-<to>.json` (old → new variable names).
6. **Verify.** After any change in a consumer, run its brand lint, build and visual regression.

## Rules for changing this repo
- Edit `tokens/tokens.css`, then run `python3 scripts/build-tokens-json.py`. Never hand-edit `tokens.json`.
- Semver: rename or remove = major (add a `migrations/` file); add = minor; value change within a role = patch.
- Run `python3 scripts/coverage-audit.py` against consumers and update `docs/coverage-audit.md`.
- Update `CHANGELOG.md`, rebuild `dist/` (`python3 scripts/build-dist.py`), commit, then tag `vX.Y.Z`.
- Governance and decisions remain in the brand owner’s records.
