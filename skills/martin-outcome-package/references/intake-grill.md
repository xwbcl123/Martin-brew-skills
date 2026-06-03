# Intake Grill

## Purpose

The intake grill is a structured interview that collects all necessary context before deliverable production begins. It draws from the `grill-me` pattern: one decision at a time, inspecting available context first, and capturing decisions as structured metadata.

## When to Grill

- Always run before starting D1 if the source material is ambiguous or incomplete.
- Skip or abbreviate if the source is a well-structured `.req.md` with clear objective, audience, and scope.

## Grill Questions

Ask these in order, skipping any that are already answered by the source material:

### 1. Source & Objective
- What is the source material? (transcript, req.md, inbox capture, session notes, fuzzy task description)
- What is the core objective? (inform, persuade, align, decide, educate)
- Who is the primary audience? (executive, technical team, customer, mixed)

### 2. Scope & Deliverables
- Which deliverables are needed? (D1-D6, minimum D1+D2)
- Is a deck needed? (determines whether D4-D5 are produced)
- Is stakeholder email distribution needed? (determines whether D6 is produced)

### 3. Output Constraints
- Target language? (default: zh-CN with English technical terms)
- Target output format for deck? (pptx, pdf, html, graphic, hybrid)
- Approximate slide count? (if deck is needed)
- Deck scenario? (formal-company-report, customer-communication, personal-creative, research-report, training-course, or custom)

### 4. Context & Routing
- Project or area association? (for deliverable_home routing)
- Brand or design constraints? (optional; graceful degradation if absent)
- Source references to preserve? (for source index in evidence-heavy work)

## Grill Output

Capture answers as structured metadata in the package README:

```yaml
intake:
  source_type: transcript
  objective: inform
  audience: executive
  deliverables: [D1, D2, D4, D5]
  language: zh-CN
  deck_scenario: formal-company-report
  target_output: pptx
  slide_count_estimate: 15
  deliverable_home: resolved/path/here
  brand_constraints: none
  needs_archive_destination: false
```

## Abbreviation Rules

If the source `.req.md` or session already contains:
- Clear objective → skip Q1
- Explicit deliverable list → skip Q2
- Language/format specified → skip Q3
- Project path known → skip Q4

Log skipped questions as "auto-resolved from source" in the intake metadata.
