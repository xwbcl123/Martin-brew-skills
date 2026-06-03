# Runtime Registration

## Skill Discovery

This Skill is discovered by agents through standard skill registration mechanisms:

1. **Direct file discovery**: Agents can discover this skill by scanning their configured skill directory for `*/SKILL.md` files with matching trigger keywords. Common roots include `skills/`, `.agents/skills/`, or a user-level skill directory.
2. **ASPG validation and bridge refresh**: `aspg lint` validates `SKILL.md`; `aspg doctor` checks topology; `aspg apply` refreshes vendor bridges when the local bridge topology supports it.

## ASPG Configuration

The `SKILL.md` frontmatter contains:

```yaml
aspg:
  origin:
    vendor: custom
    imported_at: 2026-06-03
```

This marks the skill as a custom (non-vendor) skill imported on the specified date.

## Trigger Keywords

The skill activates on these intents (encoded in the `description` field):

- `outcome-package`
- `delivery-package`
- `executive-report-plus-deck`
- `transcript-to-deliverables`
- `task-session packaging`
- Transcript processing requests
- `.req.md` processing
- Inbox capture processing
- Any request for a structured multi-deliverable output

## Visibility

- **Primary**: `martin-outcome-package/SKILL.md` inside the configured skill root.
- **ASPG bridge**: Generated or refreshed by `aspg apply` when the vendor bridge path is ASPG-managed; do not manually edit generated bridges.
- **Note**: In repos where `.claude/skills` is a redirect file (not a directory), per-skill Claude bridge directories are not expected. Visibility is through the `.agents/skills/` path directly.

## Dependencies

- **Required**: None (self-contained)
- **Optional downstream**: `martin-pptx-skill` for D5→deck production pipeline
- **Optional adapter**: Vault-specific adapter doc for local routing conventions
