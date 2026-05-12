---
name: brief-me
description: Phase 3 of the orientation pipeline. Processes Asana tasks, recent communications, and weekly focus to produce a prioritized daily orientation.
---

# brief-me

Phase 3 of the `/orient` pipeline. It synthesizes data from multiple sources to provide a high-signal daily orientation, including task metrics, meeting preparation, and focus suggestions.

## Inputs

- `date` (optional): The target date in `YYYY-MM-DD` format. Defaults to the current date.

## Procedure

1. **Analyze Data:** Run the analysis script to gather metrics from `asana.csv` and `stuff.db`.
   - Command: `python3 .gemini/skills/brief-me/scripts/analyze_data.py <DATE>`
   - This provides Asana "stock and flow" (counts and effort) and recent items from communications.
2. **Fetch Weekly Focus:** Read the weekly focus document.
   - URL: `https://docs.google.com/document/d/1nYFN1nTPGl12EqILjf5Z4GJJA7KNwD3gzqYnSgwSX_8/edit?tab=t.0`
   - Extract key priorities and themes for the current week.
3. **Prepare Meetings:** Run the meeting preparation command for the next business day.
   - Determine `NEXT_BUSINESS_DAY` from the analysis script output.
   - Run: `/prepare-meetings --date <NEXT_BUSINESS_DAY>`
4. **Synthesize & Prioritize:**
   - **Weekly Alignment:** Match open Asana tasks and new `stuff.db` items against the weekly focus.
   - **Meeting Context:** Incorporate any urgent prep or follow-ups identified in the meeting preparation.
   - **Stock & Flow:** Report the current state of the task list (Stock) and recent velocity (Flow).
   - **Prioritization:** Identify 3-5 high-impact tasks to focus on first today.
5. **Generate Orientation:** Write the final synthesis to `orientation.md` in the root directory.

## Orientation Structure

The `orientation.md` should include:
- **Header:** Date and high-level theme for the day.
- **Weekly Focus:** Summary of the focus from the Google Doc.
- **Stock & Flow:**
  - Stock: Total open tasks and total effort.
  - Flow: Tasks created vs. completed in the last 7 days.
- **Next Business Day Prep:** Summary of `/prepare-meetings` results.
- **Focus First:** 3-5 specific tasks suggested for immediate focus, with rationale.
- **New Signals:** Highlights from `stuff.db` that might need attention.

## Notes

- If the Google Doc is inaccessible, note it and rely on existing task data.
- If `/prepare-meetings` is unavailable as a command, proceed with other steps and report the omission.
