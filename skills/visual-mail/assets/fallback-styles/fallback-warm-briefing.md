---
brand_name: "Warm Briefing"
mode: "light"
use_when: "Internal project updates, progress reports, team summaries, meeting minutes, accessible cross-team communication"
colors:
  primary_accent: "#D97706"
  accent_1: "#F59E0B"
  accent_2: "#FCD34D"
  text_heading: "#92400E"
  text_body: "#374151"
  background_card: "#FFFFFF"
  background_page: "#FFFBF0"
  border_card: "#FDE68A"
gradients:
  header:
    css: "linear-gradient(135deg, #92400E 0%, #D97706 100%)"
typography:
  heading:
    font_family: "'Inter', sans-serif"
    font_weight: 700
  body:
    font_family: "'Inter', sans-serif"
    font_weight: 400
tailwind_classes:
  header_bg: "bg-gradient-to-br from-amber-900 to-amber-500"
  card_border: "border-l-4 border-amber-500"
  card_bg: "bg-white"
  icon_color: "text-amber-600"
  icon_bg: "bg-amber-100"
  badge_bg: "bg-amber-200 text-amber-800"
  heading_text: "text-amber-900"
---

# Warm Briefing Fallback Style

A warm amber-tone style that feels approachable and human without sacrificing professionalism. Suitable for progress updates and cross-team communication.

Header uses an amber gradient. Cards are white with an amber left-border accent. Page background has a very slight warm tint.

## Usage in HTML

```css
/* Header gradient */
background: linear-gradient(135deg, #92400E 0%, #D97706 100%);

/* Card accent */
border-left: 4px solid #F59E0B;
background: #FFFFFF;

/* Page background */
background: #FFFBF0;
```

Use Tailwind classes:
- Header: `bg-gradient-to-br from-amber-900 to-amber-500 text-white`
- Card: `bg-white border-l-4 border-amber-500 shadow-lg rounded-xl`
- Icon badge: `bg-amber-100 p-3 rounded-lg` + icon `text-amber-600`
