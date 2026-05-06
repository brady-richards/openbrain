---
name: gather-work
description: Phase 1 of /orient. Sweep Slack, email, and Messages for potential work over the previous-working-day window and write it to capture.csv. Stub — to be fleshed out.
---

# /gather-work

Stub. Phase 1 of the `/orient` pipeline.

## Inputs

- `$1` (required when run via /orient): target date `YYYY-MM-DD`.

## Procedure

1. Resolve `$DATE` (use `$1` or `Bash: date "+%Y-%m-%d"`).
2. Ensure `+ Inbox/orient/$DATE/` exists.
3. Write a no-op `capture.csv` with the header row only:
   ```
   source_mcp,direction,work_or_personal,counterparty,source_url,body_quote,fulfillment_check,summary
   ```
4. Report: "stub: wrote header-only capture.csv at + Inbox/orient/$DATE/capture.csv".

## TODO

- Port the gather logic from the working session of 2026-05-06 (Slack unreads + mentions + outbound search; Gmail unread/important/starred + sent across all accounts; Messages received + sent for the window).
- Apply the inbound/outbound definitions and pre-read sender exclusions.
- Asana cross-reference for `[tracked]` tagging.
