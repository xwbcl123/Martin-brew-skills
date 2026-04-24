---
brand_name: "Mono Executive"
mode: "light"
use_when: "Executive briefings, board-level reports, high-stakes decision memos, formal institutional communication"
colors:
  primary_accent: "#374151"
  accent_1: "#4B5563"
  accent_2: "#6B7280"
  text_heading: "#111827"
  text_body: "#374151"
  background_card: "#FFFFFF"
  background_page: "#F9FAFB"
  border_card: "#E5E7EB"
gradients:
  header:
    css: "linear-gradient(135deg, #111827 0%, #374151 100%)"
typography:
  heading:
    font_family: "'Inter', sans-serif"
    font_weight: 700
  body:
    font_family: "'Inter', sans-serif"
    font_weight: 400
tailwind_classes:
  header_bg: "bg-gradient-to-br from-gray-900 to-gray-700"
  card_border: "border-l-4 border-gray-500"
  card_bg: "bg-white"
  icon_color: "text-gray-600"
  icon_bg: "bg-gray-100"
  badge_bg: "bg-gray-200 text-gray-800"
  heading_text: "text-gray-900"
---

# Mono Executive Fallback Style

A minimal, high-authority monochrome style for executive-level documents. No color distractions — structure and content carry the message.

Header is deep charcoal. Cards are white with a gray left-border accent. Typography is Inter with tight spacing.

## Usage in HTML

```css
/* Header gradient */
background: linear-gradient(135deg, #111827 0%, #374151 100%);

/* Card accent */
border-left: 4px solid #4B5563;
background: #FFFFFF;

/* Page background */
background: #F9FAFB;
```

Use Tailwind classes:
- Header: `bg-gradient-to-br from-gray-900 to-gray-700 text-white`
- Card: `bg-white border-l-4 border-gray-500 shadow-lg rounded-xl`
- Icon badge: `bg-gray-100 p-3 rounded-lg` + icon `text-gray-600`
