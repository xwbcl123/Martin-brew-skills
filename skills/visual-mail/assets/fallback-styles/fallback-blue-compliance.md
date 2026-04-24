---
brand_name: "Blue Compliance"
mode: "light"
use_when: "Regulatory, compliance, government-facing, policy analysis, security briefings"
colors:
  primary_accent: "#2563EB"
  accent_1: "#3B82F6"
  accent_2: "#60A5FA"
  text_heading: "#1E3A5F"
  text_body: "#374151"
  background_card: "#FFFFFF"
  background_page: "#F0F4F8"
  border_card: "#BFDBFE"
gradients:
  header:
    css: "linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%)"
typography:
  heading:
    font_family: "'Inter', sans-serif"
    font_weight: 700
  body:
    font_family: "'Inter', sans-serif"
    font_weight: 400
tailwind_classes:
  header_bg: "bg-gradient-to-br from-blue-900 to-blue-600"
  card_border: "border-l-4 border-blue-500"
  card_bg: "bg-white"
  icon_color: "text-blue-600"
  icon_bg: "bg-blue-100"
  badge_bg: "bg-blue-200 text-blue-800"
  heading_text: "text-blue-900"
---

# Blue Compliance Fallback Style

A clean, authoritative light-mode style for compliance, policy, and regulatory content.

Header uses a deep navy-to-blue gradient. Cards are white with a blue left-border accent. Typography is Inter throughout. Body text is dark gray for high readability.

## Usage in HTML

```css
/* Header gradient */
background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%);

/* Card accent */
border-left: 4px solid #3B82F6;
background: #FFFFFF;

/* Page background */
background: #F0F4F8;
```

Use Tailwind classes:
- Header: `bg-gradient-to-br from-blue-900 to-blue-600 text-white`
- Card: `bg-white border-l-4 border-blue-500 shadow-lg rounded-xl`
- Icon badge: `bg-blue-100 p-3 rounded-lg` + icon `text-blue-600`
