# D6 — Email Package

## Header

```yaml
deliverable: D6
title: "{{TITLE}}"
date: {{ISO_DATE}}
author: martin-outcome-package
source_deliverable: D1, D2
language: {{LANGUAGE}}
```

---

## Email Metadata

| Field | Value |
|-------|-------|
| To | {{RECIPIENTS}} |
| CC | {{CC_OR_NONE}} |
| Subject | {{SUBJECT_LINE}} |
| Attachments | {{ATTACHMENT_LIST}} |

## Email Body

> Written in Martin's email style: direct, professional, non-performative. Opens with the conclusion, then supporting points.

---

{{GREETING}},

{{BOTTOM_LINE_OPENING}}

{{KEY_POINTS_AS_BULLETS}}

{{ATTACHMENTS_REFERENCE}}

{{CALL_TO_ACTION_OR_NEXT_STEPS}}

{{SIGN_OFF}}

---

## Attachments Checklist

| Attachment | Format | Source | Status |
|-----------|--------|--------|--------|
| Executive Summary | Word/PDF | D2 | {{STATUS}} |
| Presentation | PPTX/PDF | D5 pipeline | {{STATUS}} |
| Deep Report | PDF | D1 | {{STATUS}} |

## Visual Embed (Optional)

> If using visual-mail skill, embed a screenshot of D3 visual briefing in the email body.

Image source: `{{PATH_TO_SCREENSHOT_OR_NA}}`
Embed syntax: `![Visual Brief](cid:visual-brief)`

## Distribution Notes

{{DISTRIBUTION_NOTES_OR_NONE}}
