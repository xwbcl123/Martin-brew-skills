# ASF Icons — registry (track: icon)

Sprite: [`asf-icons.svg`](asf-icons.svg) · Tokens: `--asf-icon-size` 24px, `--asf-icon-size-sm` 18px, `--asf-icon-stroke` 1.7

## Spec
- 24×24 grid, 2px safe area, stroke only: 1.7, round caps and joins, `currentColor`. No fills except a dot of 1×1 path.
- Icons support a text label and never replace it. Decorative icons get `aria-hidden="true"`. An icon-only control needs `aria-label`.
- Usage: `<svg class="asf-icon" viewBox="0 0 24 24" aria-hidden="true"><use href="/design/asf-icons.svg#publication"/></svg>`.

## Registry
| id | Set | Meaning | Source | Status |
|---|---|---|---|---|
| `arrow` | editorial | outbound / next (↗) | asf-website editorial-icons.svg | stable |
| `archive` | editorial | archive, past records | 〃 | stable |
| `record` | editorial | event record | 〃 | stable |
| `concept` | editorial | concept / idea (dashed) | 〃 | stable |
| `publication` | editorial | document / report | 〃 | stable |
| `reserved` | editorial | reserved / planned slot | 〃 | stable |
| `development` | editorial | in development (dotted) | 〃 | stable |
| `download` | ui | download | asf-website Glyph.astro | stable |
| `audio` | ui | podcast / audio | 〃 | stable |
| `chapters` | ui | chapter list | 〃 | stable |
| `read` | ui | read online | 〃 | stable |
| `search` | ui | search | 〃 | stable |
| `back` / `forward` | ui | seek −/+ | 〃 | stable |
| `video` | ui | video / film | 〃 | stable |

## Fallback library
For a concept not in the registry, use **Lucide** (same 24 grid, round joins) with `stroke-width="1.7"`, then propose it here. The old site already uses 30 Lucide icons. The candidates to promote first, because the event pages need them: `Calendar`, `MapPin`, `Users`, `Mail`, `Linkedin`, `ExternalLink`, `Ticket`, `Globe`.

**Never use:** shields, padlocks, brains, circuit motifs (`ShieldCheck`, `LockKeyhole`, `BrainCircuit` from the old site). They break the Field Notes rule against security clichés.

## Known drift (to fix in W4)
- asf-website `global.css` sets `.icon{stroke-width:1.5}`, which overrides Glyph's `1.7` attribute, so every icon currently renders at 1.5. The spec says 1.7.
- Two sources (sprite and inline Glyph paths) should collapse into this one sprite.
