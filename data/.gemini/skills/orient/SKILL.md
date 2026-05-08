---
name: orient
description: Orchestrates the three-phase orientation pipeline — gather potential work, refine it, and produce an orientation. Use this to get a bird's-eye view of your day.
---

# orient

The `/orient` skill is a three-phase pipeline that turns raw signals (Slack, email, Messages) into an oriented view of what to do today. It sequences three specialized skills, running each in an isolated subagent to maintain a clean context.

## Inputs

- `date` (optional): The target date in `YYYY-MM-DD` format. Defaults to the current date.

## Procedure

1. **Resolve Date:** Determine the target date. If not provided, run `Bash: date "+%Y-%m-%d"` to get today's date. Use this as `$DATE`.
2. **Phase 1: Gather:** Invoke a `generalist` subagent with the following prompt:
   - "Run the `/gather-work` skill for $DATE. Output goes to `current.csv`. Report the row count and any issues when you finish."
3. **Phase 2: Refine:** Invoke a `generalist` subagent with the following prompt:
   - "Run the `/refine-work` skill for $DATE. Input is `current.csv`. Output goes to `refined.csv`. Report what was dropped, merged, or rewritten."
4. **Phase 3: Orient:** Invoke a `generalist` subagent with the following prompt:
   - "Run the `/brief-me` skill for $DATE. Input is `refined.csv`. Output goes to `orientation.md`. Return the orientation summary."
5. **Final Report:** Echo the path to the final `orientation.md` and provide a one-paragraph summary based on the output of Phase 3.

## Notes

- **Sequential Execution:** Phases are sequential. If a phase fails, do not proceed.
- **Durable Handoffs:** Data is handed off via CSV files in the root `data` directory.
- **Clean Context:** Each phase runs as a subagent to prevent context bloat from heavy tool usage in earlier phases.
