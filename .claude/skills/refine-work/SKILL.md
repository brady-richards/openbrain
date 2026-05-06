---
name: refine-work
description: Phase 2 of /orient. Read capture.csv, dedupe and merge related rows, drop noise, and write refined.csv. Stub — to be fleshed out.
---

# /refine-work

Stub. Phase 2 of the `/orient` pipeline.

## Inputs

- `$1` (required when run via /orient): target date `YYYY-MM-DD`.

## Procedure

1. Resolve `$DATE`.
2. Read `+ Inbox/orient/$DATE/capture.csv`. If missing, error out — phase 1 must run first.
3. No-op refinement: copy the file to `+ Inbox/orient/$DATE/refined.csv` unchanged.
4. Report: "stub: refined.csv is a copy of capture.csv".

## TODO

- Merge rows that point at the same underlying work across channels (e.g., a Slack ping + email follow-up about the same thing).
- Drop rows superseded by later activity not visible to the gather phase.
- Rewrite summaries into action verbs with concrete next steps.
- Sort by priority signal (deadline language, sender seniority, blocking dependencies).
