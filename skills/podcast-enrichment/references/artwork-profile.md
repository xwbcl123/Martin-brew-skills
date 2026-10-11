# External artwork profile v1

`profile` is a caller-supplied absolute YAML/JSON file, not a built-in show preset. For enrichment input use `metadata.artwork.profile_ref`. An explicit `--profile` takes precedence; if it conflicts with a supplied metadata reference, resolve the conflict before generation. Resolve a dashboard reference only when the exact show identity matches. Never select a profile by vague title similarity.

## Contract

Required: `schema_version: "1.0"`, nonempty `profile_id`, `revision`, `show_id`, `brand`, `shared`, `styles`, `asset_rules`. Style keys are arbitrary strings, with one or more entries. Each style requires a stable `id`, human `name`, `medium`, and `composition_rule`. Optional: `brand_en`, `composition_prompt`, `reference_manifest`, per-style `primary_reference` / `secondary_reference`, texture and avoid rules, approval notes and dates.

- `shared.canvas`: aspect ratio, text margins and output expectations. Draft size and delivery size are distinct; inspect actual output.
- `shared.palette`: named hex colors. `shared.lockup`: copy hierarchy, language and small-size QA. `shared.characters`, mood and prohibitions are optional and show-specific.
- `asset_rules.show`: enduring series identity, title hierarchy and allowed/forbidden copy. `asset_rules.episode`: current transcript grounding, episode marker, short title and scene limits. Supply both when the profile supports both assets.
- Reference paths and composition template are relative to the profile directory. Use portable paths contained in the profile folder; no symlinks escaping it. Attach actual reference images for generation, never the YAML instead of images.
- `reference_manifest` is an array of `{path, sha256, role}` records; `style` is optional. Every declared reference must be represented and match its actual SHA-256. A profile can intentionally have no references; this is visibly a text-only profile, not a failed reference fallback.
- `workflow` and `variables_per_episode` are optional editorial guidance; user instructions retain precedence. A YAML approval label is provenance, not fresh publication authorization.

Copy [artwork-profile-template.yaml](artwork-profile-template.yaml) to the show's brand library, fill all placeholders from approved show materials, replace example style IDs, add images and real hashes, then validate. A new show need not use three styles.

## Resolution and fallback

1. Explicit path or metadata reference: validate it, match `show_id`, and check all declared files/hashes. Missing file, malformed/unsupported schema, wrong show, or hash mismatch is an error; do not silently swap to another style.
2. No explicit profile: derive show identity from the user-named podcast, package metadata, provider show relationship or canonical brand brief, then resolve exact `show_id` through the explicitly configured artwork registry. Registry entries contain `show_id`, `show_name`, optional aliases and `profile_ref` relative to the registry. No topic-only classification: a technology discussion may belong to a family podcast. Multiple matching profiles are an error; an invalid registered profile does not trigger fallback. Do not add show names or IDs to the generic skill.
3. No registered profile: read the show's available website/brand design system and construct a temporary profile. Brief `design_system.shared` holds sourced palette, typography/lockup, mood and canvas rules; optional `styles` and `asset_rules` follow the same contract. Supply `design_system_source_refs`. Record `design-system-fallback` and persist the complete `temporary_profile` in the plan. This is a temporary derived profile, not a permanently approved brand revision. If the design system contains image references, first materialize a local temporary profile with files and hash manifest and validate it explicitly.
4. Neither profile nor trustworthy design system: use neutral editorial treatment, record `neutral-fallback` and do not invent brand identity or attribution. Missing trustworthy show identity/content requires clarification.

The helper never scans the current directory or a project tree. The profile is the explicit `--profile` / `metadata.artwork.profile_ref`; otherwise the registry comes from `--profile-registry` > `PODCAST_ARTWORK_PROFILE_REGISTRY` > config `artwork_registry`, matched by exact `show_id`. Without a registry the helper only follows the declared design-system/neutral fallback; "a registry may exist somewhere on this machine" is never treated as resolved. The plan is written to a new file: `--output` refuses to overwrite any input (brief, profile, manifest, composition guide, references, registry) and refuses an existing plan unless `--overwrite` is given. When only a show name is supplied, the agent uses registry aliases and canonical context to fill that exact ID before planning. It never asks the user to resupply an already registered profile.

## Local planning command

```sh
python3 scripts/plan_artwork.py --brief /absolute/brief.json --profile /absolute/style.yaml --output /absolute/artwork-plan.json
```

Brief: `show_id`, `show_name`, `asset_type` (`show` or `episode`), `source_refs` (nonempty paths/URLs), `composition`, `copy` (array of exact strings). Episode briefs additionally contain `episode_number`. Optional `style_keys` selects a subset. Read and interpret the actual sources before authoring the brief. This helper validates the profile and freezes per-style prompt plans; it does not read transcripts, generate images, grant selection or publish. Use the image generation tool separately, then record actual prompt/output hashes.

## Maintenance

The show brand README links to one canonical profile and its guideline. Changes to palette, medium, references or lockup create a new revision and retained history. Episode composition and copy do not mutate the style profile. Record profile/ref/prompt/source/output hashes in candidate provenance. Only an exact selected artifact enters `cover_path`; provider publication remains a separate authorized operation.
