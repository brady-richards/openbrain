---
name: daily-brief
description: Produce today's daily briefing across all Google Calendars, Gmail accounts, Slack workspaces, and Asana. Writes to + Atlas/Daily/YYYY-MM-DD.md and surfaces anything that needs the user's attention today. Safe to re-run — refreshes the `## Morning brief` section in place.
---

# /daily-brief

Assemble the user's daily briefing for today (or a date passed as `$1`). Creates or updates the matching daily note in `+ Atlas/Daily/`. Re-runnable: the skill replaces the `## Morning brief` section in place rather than appending a new one.

## Inputs

- `$1` (optional): target date in `YYYY-MM-DD`. Defaults to today.

## Procedure

1. **Calendar sweep.** For each `gcal_*` MCP, call `gcal_list_events` for the target date (00:00 → 23:59 local). Merge into a single timeline; tag each event with the owning account slug. Collapse duplicate events that appear on multiple calendars (same title + time).
1b. **Fathom recordings.** Call `mcp__fathom__list_meetings` for meetings in the last 24h. Cross-reference each recording's title against the calendar events from step 1 (case-insensitive title match). Discard recordings with no matching calendar event — those are team members' meetings the user wasn't part of. For recordings that do match, use the user's `responseStatus` on the matched calendar event to determine treatment:
   - **Declined** — omit entirely. The user opted out intentionally.
   - **⚠️ Missed** (`tentative` or `needsAction`) — the user may not know what was discussed. Fetch the recording summary (`include_summary: true`) and surface it at the top of the Recordings section so the user can catch up.
   - **★ Attended** (`accepted`) — the user was there. Fetch action items (`include_action_items: true`), filter to those assigned to the user, and surface them as a checklist. No need to repeat the summary.
   Surface missed recordings before attended ones.
2. **Priority mail.** For each `gmail_*` MCP, `gmail_search_messages` with `is:unread newer_than:2d (is:important OR is:starred OR label:^iim)`. Cap at 5 per account. Capture subject, sender, account slug.
3. **Slack attention.** For each `slack_*` MCP, search for mentions of the user in the last 24h and list unread DMs. Cap at 5 per workspace.
4. **Overdue tasks.** For both `asana_personal` and `asana_work`, `asana_get_my_tasks` filtered to `completed_since=now` and due date < today.
5. **Stale relationships.** Grep `+ Atlas/People/*.md` for notes whose `last_contact` is older than their `cadence` allows (weekly: > 7d, monthly: > 30d, quarterly: > 90d, asneeded: never stale). Cap at 5.
6. **People detection pass.** From the calendar attendees + priority mail senders/recipients + Slack counterparties gathered in steps 1–3, check each identifier against `+ Atlas/People/*.md` frontmatter (`emails`, `slack`, `title`, `aliases`). Unknown humans (after filtering no-reply/bots/resources per `/people-sync` rules) become a **New faces** candidate list — do not stage stubs from this skill; just surface them. Recommend `/people-sync` if the list is non-empty.
7. **Compose the daily note.** If `+ Atlas/Daily/<date>.md` does not exist, scaffold from `+ Extras/Templates/Daily.md`. If a `## Morning brief` section already exists in the note, **replace its body in place** (find the `## Morning brief` heading and overwrite everything up to the next H2 or EOF). Otherwise insert a new `## Morning brief` section near the top. Contents:
   - **Today's calendar** (merged timeline, grouped bullet list, `[HH:MM–HH:MM] Title · account-slug · other attendees if any`)
   - **Recent recordings** (Fathom meetings from last 24h not yet captured as interaction notes — title, attendees, `fathom:<id>` ref; omit section if empty)
   - **Needs a reply** (mail + slack, grouped by account/workspace)
   - **Overdue in Asana**
   - **People past cadence** (link with `[[wikilinks]]`)
   - **New faces** — unknown humans seen in today's activity, one line each with source context. Omit the section if empty.
   - A single-line **Focus suggestion** based on the above
8. **Update the Today link** in both `Home.md` and `README.md`. Find the line matching `**Today:** [...](<...>)` in each file and replace it with `**Today:** [<date>](<+ Atlas/Daily/<date>.md>)` where `<date>` is the target date. This keeps the GitHub-rendered links current.
9. Never touch any other section of the daily note. Only the `## Morning brief` section and the Today links in `Home.md`/`README.md` are managed by this skill.

## Output shape

Create or refresh the `## Morning brief` section in `+ Atlas/Daily/<date>.md`. Report a short summary of what was (re)generated to the user in chat.

## Notes

- **Idempotent by design.** Running `/daily-brief` twice on the same date replaces the section rather than duplicating it. The section header stays `## Morning brief` (the name reflects content intent, not the time of day the skill was invoked).
- Never send any email or Slack message — this is read-only aggregation.
- If a given MCP server fails, note it in the brief (`_(gmail_<slug> or gcal_<slug>: unavailable)_`) and continue.
- Respect the `#workspace/personal` vs `#workspace/work` split only if the user asks for a single-workspace brief (e.g. `/daily-brief work` → skip all `workspace=personal` sources). Without a flag, include everything.
