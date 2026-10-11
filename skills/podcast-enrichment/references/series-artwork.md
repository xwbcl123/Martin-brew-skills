# Series artwork: profile, composition, selection

Read when creating/refreshing covers or maintaining recurring series identity. Other enrichment tasks can use a supplied final cover directly.

## Resolve the brand

Use the exact show identity and supplied series brief/brand dashboard to find the approved artwork profile. Explicit series branding overrides generic personal defaults. The profile belongs to the show's canonical brand library, not this generic skill. The site repository can link to it. A useful project layout is `style.yaml`, actual reference PNGs with a hash manifest, and a composition-prompt document. The brand dashboard links to the canonical location; do not create competing profile copies inside the skill.

Accept a caller-supplied profile using [artwork-profile.md](artwork-profile.md). Style keys, number of variants, characters, colors and show identity come from the profile. Never hardcode a particular podcast in this skill. For show artwork use `asset_rules.show`; for episode artwork use `asset_rules.episode`.

## Style versus story

- **Reference image:** visual medium, pigment/paper/ink texture, brand lockup and type hierarchy. Attach actual files to generation, preserving hashes. Previous episode activities, poses, titles and objects are not facts about the new episode.
- **Style profile:** palette, series mark, safe margins, square format, allowed family IDs and family-specific constraints. Do not drift approved styles between episodes.
- **Episode composition:** source-backed theme and tension, main subject/action/setting, up to three supporting objects, exact short title/subtitle, emotional arc and episode-specific exclusions. Read current final/public content; a planning draft can contain scenes never recorded.

Reuse the family's composition rule, not its previous composition. An intimate family scene, a strong single metaphor and a paper journey solve the same source differently. Never place parents on a child's solo school trip, show a canceled activity as completed, or upgrade a wish/claim into a factual outcome.

## Produce an actual choice

Follow the series' review mode. When requested, generate one actual candidate per configured style family with the applicable image skill. Freeze the complete prompt. Record generator, profile digest, reference-image digests, source hashes, prompt digest and output image digest. Preserve native originals; draft dimensions are not proof of final delivery resolution.

Deliver an engagement sheet with candidate IDs, scene rationale, original files and 80/160px views. Label candidates clearly. A direct human choice selects an exact episode + style ID + artifact hash; a page click, generated recommendation or agent simulation is not approval. If autonomous selection was explicitly authorized, retain that authorization and agent-selected provenance.

Only selected artwork enters `cover_path`. Keep series-family approval separate from each episode's artwork selection. Preserve other candidates for review. Existing-episode refresh retains the old provider artwork reference and exact identity for rollback.

## Preserve provenance with the current schema

Optional `metadata.artwork` in content JSON can record:

- `profile_ref`, `profile_sha256`, `style_id`;
- `prompt_sha256`, reference-image paths and hashes;
- `selected_cover_sha256`, `selection_source`, `selection_receipt_ref`.

Bind actual values and a trusted decision record; these fields are provenance, not an approval token. Do not pass them to provider APIs. The current renderer accepts metadata and uses an actual raster `cover_path`; this workflow needs no new release schema or renderer generation dependency.

## Final review and publication

Inspect actual output: square dimensions, exact readable Simplified Chinese, series and episode markers, content-specific correctness, style-reference fidelity, one clear visual hierarchy and 80/160px legibility. Dimensions do not establish visual quality. Fix malformed lettering or unrequested slogans before final release.

Palette, medium, brand lockup or reference changes require a series-style revision. Ordinary episodes vary composition and copy within the profile. External hosting/provider mutation stays with the publishing workflow and current user authorization; selecting a family or building a preview does not authorize upload.
