# Smoke Test Acceptance Criteria

## Purpose

Validates that the martin-outcome-package skill can produce a minimum viable package (D1 + D2) from a fixture input.

## Test Setup

1. Use `tests/fixture-req.md` as source material.
2. Set `deliverable_home` to a temporary directory (e.g., `/tmp/martin-outcome-smoke-test/` or session-local `deliverables/`).

## Acceptance Checks

### Intake Resolution
- [ ] Source type identified as `fuzzy-task`
- [ ] Objective resolved (align)
- [ ] Audience resolved (MSSD leadership)
- [ ] Deliverables resolved (D1, D2)
- [ ] Language resolved (zh-CN)
- [ ] `deliverable_home` captured

### D1 Deep Report
- [ ] File exists at `{deliverable_home}/d1-deep-report.md`
- [ ] Contains YAML header with deliverable metadata
- [ ] Contains Executive Overview section
- [ ] Contains Core Analysis section(s)
- [ ] Contains Key Findings section
- [ ] Contains Recommendations section
- [ ] Content relates to EU cybersecurity regulation (NIS2, CRA, DORA)
- [ ] Language is zh-CN with English regulatory terms preserved

### D2 Executive Summary
- [ ] File exists at `{deliverable_home}/d2-executive-summary.md`
- [ ] Contains YAML header with deliverable metadata
- [ ] Contains Bottom Line section
- [ ] Contains Key Findings section
- [ ] Contains Recommendations section
- [ ] References D1 as source
- [ ] Word count approximately 500 words

### Package README
- [ ] File exists at `{deliverable_home}/README.md`
- [ ] Contains package metadata (package_id, created, source_type, deliverable_home)
- [ ] `deliverables_produced` lists D1 and D2
- [ ] `needs_archive_destination` is set appropriately

### Negative Checks
- [ ] No D3-D6 files produced (not requested)
- [ ] No absolute local paths in output files
- [ ] No placeholder text remaining in final deliverables (e.g., `{{TITLE}}`)

## Pass Criteria

All checked items above must pass. Any failure should be documented with the specific file and line that failed.
