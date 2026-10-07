# ASF brand profile

ASF means **AI Security Forum** when this identity is explicit in the request. Select ASF before the general Life/Work route. ASF is its own forum identity, not a Organization Brand deck and not Martin-Borealis. If an unrelated acronym ASF is used, resolve its meaning from context.

## Authority and resolution

The independent `asf-brand` repository owns DESIGN.md, tokens, logos, icons and font licensing. Pin **v1.2.2**, commit `13741fedd7d3b28b57aa9e74d99700c2f663aa9c`; the annotated tag object is `dd07a281cf22bed7287e53cdde39e3fbb8222866`. Do not confuse them.

Resolve a read-only source via `ASF_BRAND_ROOT` (or the resolver's `--root`), otherwise the sibling `artifact-template-asf-deck/assets/source/assets/asf-brand-v1.2.2` locked snapshot when installed. Run:

```sh
python3 scripts/resolve_asf_brand.py --register paper
```

Paths in that command are relative to this skill directory. Read the resolved `llms.txt`, `DESIGN.md`, `tokens/tokens.json` and relevant registry entries. The resolver checks critical asset hashes, not just the version label. Missing/mismatched assets require an authorized locked source; never substitute personal or employer branding. A packaged snapshot is a reproducibility dependency, not a second editable brand authority.

## Register and typography

- **Paper publishes:** documents, evidence-heavy reading, printed handouts. Warm paper ground, ink text, teal accent.
- **Ink convenes:** stage, forum sessions and dark presentation settings. Ink ground, light text, mint accent. The selected deck display font remains Georgia.
- Consume register-resolved semantic tokens. Mint never sits on Paper/white; avoid glow, glass and gradient washes. Keep square editorial surfaces and fine rules.
- Office roles follow DESIGN §7: Georgia display, Arial body, Consolas metadata. Spline Sans belongs inside the official logo image. Verify installed fonts; the audited macOS HTML runtime falls back from Consolas to Courier New. Do not promise identical Office metrics without a target-environment check, or distribute proprietary fonts.
- Use official icons with text labels. Preserve logo geometry, contrast variant and clear space. Host/partner template may frame cover and thank-you only when the brief calls for it; content pages keep ASF.
- Name/byline must follow the actual forum brief; neither Life pen name nor employer endorsement is added automatically.

## Deck family

Use `artifact-template-asf-deck`: one family, two variants, each with 10 core archetypes and 2 optional reference appendices. The family owns approved deck geometry and native mappings; upstream brand owns identity tokens. The selected Paper/Georgia Ink references override generic style defaults. Choose the register from purpose and explicit user preference, then adapt content without reopening approved typography choices.

For a real event, replace illustrative chart values, photography and contact placeholders with approved material. Samples are not ASF performance claims. Keep source/permission notes where relevant. Review the actual output and its declared editing level; HTML preview does not prove native PPTX editability.
