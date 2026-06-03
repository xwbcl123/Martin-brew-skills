# D3 — Visual Briefing

## Header

```yaml
deliverable: D3
title: "{{TITLE}}"
date: {{ISO_DATE}}
author: martin-outcome-package
source_deliverable: D1, D2
format: HTML (single-file, self-contained)
language: {{LANGUAGE}}
```

---

## Design Direction

> Visual briefing style. Use bundled defaults unless brand-style input is provided.

- **Layout**: Card grid, responsive, max-width 1200px
- **Color palette**: Professional dark or light scheme (adapt to content tone)
- **Typography**: System font stack or specified brand font
- **Cards**: Rounded corners, subtle shadows, clear hierarchy

## Content Sections

### Hero / Title Card

- Title: {{TITLE}}
- Subtitle: {{SUBTITLE_OR_DATE}}
- Visual accent: gradient or icon

### Key Metrics / At-a-Glance

> 3-5 metric cards showing the most important numbers or status indicators.

| Metric | Value | Trend |
|--------|-------|-------|
| {{METRIC_1}} | {{VALUE}} | {{TREND}} |
| {{METRIC_2}} | {{VALUE}} | {{TREND}} |
| {{METRIC_3}} | {{VALUE}} | {{TREND}} |

### Findings Cards

> One card per key finding from D1/D2. Each card has:
- Title (finding headline)
- 2-3 sentence explanation
- Visual indicator (icon, color-coded importance)

### Recommendations Section

> Action cards or timeline visualization of recommended next steps.

### Sources / Footer

> Compact source attribution and generation metadata.

## Technical Requirements

- Single HTML file with embedded CSS and inline SVG where needed
- No external dependencies (no CDN links, no external images unless provided)
- Responsive: readable on desktop and tablet
- Print-friendly: clean layout when printed to PDF

## Optional Enhancements

- Animated counters for metrics (CSS-only)
- Hover effects on cards
- Dark/light mode toggle (if brand allows)

## Output

Write to: `{deliverable_home}/d3-visual-briefing/briefing.html`
Assets (if any): `{deliverable_home}/d3-visual-briefing/assets/`
