---
name: orient
description: Sequence the three orientation phases — gather potential work, refine it, and produce an orientation. Each phase runs as an isolated subagent that hands off via CSV files in + Inbox/orient/.
---

# /orient

Three-phase pipeline that turns raw signals (Slack, email, Messages) into an oriented view of what to do today. Each phase is heavy enough to deserve its own context, so they run as separate subagents and hand off via files.

## Inputs

- `$1` (optional): target date in `YYYY-MM-DD`. Defaults to today.

## Procedure

> **Date check first.** If `$1` is not supplied, resolve "today" by running `Bash: date "+%Y-%m-%d"`. Do not trust session-injected `currentDate`. Use the shell result as `$DATE` below.

> **Hand-off contract.** Each phase reads from and writes to `+ Inbox/orient/<DATE>/`:
> - Phase 1 writes `capture.csv`
> - Phase 2 reads `capture.csv`, writes `refined.csv`
> - Phase 3 reads `refined.csv`, writes `orientation.md`

> **Why subagents.** Each phase fires 50–300+ tool calls and reads heavy bodies (email, transcripts, threads). Running them in this skill's context would bloat it past usefulness by phase 3. Spawn a subagent per phase so each starts clean.

1. **Prep.** `mkdir -p "+ Inbox/orient/$DATE"`. Confirm the directory exists before spawning anything.

2. **Phase 1 — gather.** Spawn a subagent:
   - `subagent_type`: `general-purpose`
   - `description`: "Gather potential work"
   - `prompt`: "Run the `/gather-work` skill for $DATE. Output goes to `+ Inbox/orient/$DATE/capture.csv`. Report the row count and any channels that returned zero results when you finish."
   Wait for completion before proceeding.

3. **Phase 2 — refine.** Spawn a subagent:
   - `subagent_type`: `general-purpose`
   - `description`: "Refine captured work"
   - `prompt`: "Run the `/refine-work` skill for $DATE. Input is `+ Inbox/orient/$DATE/capture.csv`. Output goes to `+ Inbox/orient/$DATE/refined.csv`. Report what was dropped, merged, or rewritten."
   Wait for completion.

4. **Phase 3 — orient.** Spawn a subagent:
   - `subagent_type`: `general-purpose`
   - `description`: "Produce orientation"
   - `prompt`: "Run the `/set-orientation` skill for $DATE. Input is `+ Inbox/orient/$DATE/refined.csv`. Output goes to `+ Inbox/orient/$DATE/orientation.md`. Return the orientation summary."
   Wait for completion.

5. **Report.** Echo the path to `orientation.md` and a one-paragraph summary drawn from the phase 3 subagent's return value. Do not re-summarize from the CSV — trust the phase 3 output.

## Notes

- If any phase's subagent returns an error, stop and surface it. Do not proceed to the next phase with stale or partial input.
- Phases are sequential by design — phase 2 needs phase 1's output, phase 3 needs phase 2's. Do not parallelize.
- The CSV files are durable hand-offs. If phase 3 fails, the user can re-run `/set-orientation` directly on the existing `refined.csv` without redoing the gather.
