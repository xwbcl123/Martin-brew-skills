# Brand Guideline Selection Policy

## Priority Order

1. **User-specified**: If `brand_guideline` parameter is provided, use that file path. No further selection needed.

2. **Workspace brand pool** (for example `40 Resources/brand-styles/*.brand_guideline.md`): If a brand-style directory is accessible, select by content tone:

   | Content tone | Preferred styles |
   |---|---|
   | Compliance / policy / regulation / security | Blue-Steel, Blue-Tone, Martin-Borealis |
   | Research / insight / analysis / trend | Aurora, Nebulae, Nova |
   | External market-facing / commercial | Martin-Gradient-1, Martin-Spectrum |
   | Formal enterprise / institutional | Huawei-Template |
   | General / neutral | Any available; avoid repeating last used |

   Rotation rule: avoid using the same style in consecutive outputs if history is accessible.

3. **Bundled fallback** (when vault is unavailable): use one of the three styles in `assets/fallback-styles/`:

   | File | Use when |
   |---|---|
   | `fallback-blue-compliance.md` | Regulatory, compliance, government-facing |
   | `fallback-mono-executive.md` | Executive briefings, high-stakes decisions |
   | `fallback-warm-briefing.md` | Internal updates, project progress, team summaries |

## Applying Brand Tokens

Once selected, extract from the guideline frontmatter:

- `colors.primary_accent` → header gradient start
- `gradients.heading.css` → title gradient text or header background
- `colors.background_card` → card background (dark mode) or white (light mode)
- `colors.text_body` → body text color
- `typography.heading.font_family` → heading font

If the guideline is dark mode (`mode: dark`), set the page background to `colors.background_page`. For light mode, use `bg-gray-50`.

## Slash Command Integration (future-compatible)

When available as slash commands, these can be used before invoking `visual-mail`:

- `/brand-style list` — show available workspace styles
- `/brand-style random` — pick a random style
- `/brand-style use <style-name>` — set active style for next output
