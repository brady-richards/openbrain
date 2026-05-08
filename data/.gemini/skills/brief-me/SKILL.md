---
name: brief-me
description: Phase 3 of the orientation pipeline. Processes refined.csv to produce a concise orientation.md note summarizing the day's priorities.
---

# brief-me

Phase 3 of the `/orient` pipeline. It reads the refined work items and frames them into an actionable daily orientation.

## Inputs

- `date` (optional): The target date in `YYYY-MM-DD` format. Defaults to the current date.

## Procedure

1. **Resolve Date:** Determine the target date. If not provided, use the current date.
2. **Read Refined Data:** Locate the refined work data at `refined.csv` in the root directory. If this file does not exist, the previous phases of the orientation pipeline may have failed or were not run. Report this error and stop.
3. **Generate Orientation:**
   - Read the content of `refined.csv`.
   - Count the total number of rows (excluding the header).
   - Generate a markdown file at `orientation.md` in the root directory with the following initial content:
     ```markdown
     # Orientation — <DATE>

     Stub. Refined row count: <N>.
     ```
4. **Report:** Confirm that the orientation file has been written.

## TODO (Future Enhancements)

- Group rows by theme (e.g., commitments due today, decisions waiting on me, asks blocked on others).
- Pick a single "what matters most today" framing.
- Cross-reference calendar to flag rows that conflict with meetings.
- Optionally write into the day's daily note rather than a standalone file.
