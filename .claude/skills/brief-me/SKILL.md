---
name: brief-me
description: Phase 3 of /orient. Read refined.csv and produce orientation.md — a short note that frames the day. Stub — to be fleshed out.
---

# /brief-me

Stub. Phase 3 of the `/orient` pipeline.

## Inputs

- `$1` (required when run via /orient): target date `YYYY-MM-DD`.

## Procedure

1. Resolve `$DATE`.
2. Read `+ Inbox/orient/$DATE/refined.csv`. If missing, error out.
3. No-op orientation: write `+ Inbox/orient/$DATE/orientation.md` containing:
   ```
   # Orientation — $DATE

   Stub. Refined row count: <N>.
   ```
4. Report: "stub: wrote placeholder orientation.md".

## TODO

- Group rows by theme (e.g., commitments due today, decisions waiting on me, asks blocked on others).
- Pick a single "what matters most today" framing.
- Cross-reference calendar to flag rows that conflict with meetings.
- Optionally write into the day's daily note rather than a standalone file.
