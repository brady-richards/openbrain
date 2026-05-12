---
name: brief-me
description: Phase 3 of /orient. Produce orientation.md framing the day — new tasks, task stock/flow vs last business day, and per-meeting briefings for every meeting on today's calendar.
---

# /brief-me

Phase 3 of the `/orient` pipeline. Produces a focused orientation note that answers three questions:

1. What new work landed on me since the last business day?
2. Is my task pile growing or shrinking (count + effort)?
3. What do I need to know going into each meeting today?

## Inputs

- `$1` (optional): target date `YYYY-MM-DD`. Defaults to today (resolved via `date "+%Y-%m-%d"` — do NOT trust session-injected `currentDate`).

## Output

Writes `+ Inbox/orient/$DATE/orientation.md` (overwrite if it already exists).

## Procedure

> **Date math.** Resolve `$DATE` first. Then compute `$LAST_BIZ` as the previous business day:
> - If `$DATE` is Mon → `$LAST_BIZ` = previous Friday.
> - If `$DATE` is Tue–Fri → `$LAST_BIZ` = `$DATE` - 1 day.
> - If `$DATE` falls on a weekend → `$LAST_BIZ` = the most recent Friday.
> Compute via `python3 -c "from datetime import date,timedelta; d=date.fromisoformat('$DATE'); off={0:3,6:2,5:1}.get(d.weekday(),1); print((d-timedelta(days=off)).isoformat())"`.
> `$WINDOW_START` is `$LAST_BIZ T00:00:00` local; `$NOW` is the current timestamp.

> **Parallelization.** Steps 1, 2, and 3 are independent and must fan out together in a single tool-use block. Step 4 (meeting-prep per-meeting) fans out across meetings, but each meeting's substeps mirror `/meeting-prep` steps 2–6 and themselves parallelize.

### 1. New tasks since `$LAST_BIZ`

Fetch all of Brady's Asana tasks across configured workspaces, including those completed in the window:

- `mcp__asana_work__asana_get_my_tasks` with `completed_since=$WINDOW_START`, `opt_fields=name,gid,created_at,completed,completed_at,due_on,projects.name,permalink_url,custom_fields,assignee.name`.
- Filter to `assignee.name == "Brady Richards"` (defense-in-depth — the workspace already scopes this).

From the returned set, derive:

- **New tasks** — `created_at >= $WINDOW_START`. Capture `gid`, `name`, `permalink_url`, `Effort` (from `custom_fields`), `projects[0].name`, `created_at`.
- **Completed tasks** — `completed == true AND completed_at >= $WINDOW_START`. Same fields plus `completed_at`.
- **Open tasks now** — `completed == false`. Used for stock counts.

### 2. Task stock & flow

Compute:

- **Stock (now):** count of open tasks, sum of `Effort` across open tasks (treat null Effort as 0 but report the count of null-Effort tasks separately so the user knows how stale the estimate is).
- **Flow since `$LAST_BIZ`:**
    - Added: count + total effort of new tasks.
    - Completed: count + total effort of completed tasks.
    - Net change: `added - completed` for both count and effort.

Format as a compact table — see the orientation template below.

### 3. Meeting prep — every meeting today

Across all `google_*` MCPs:

- `google_calendar_list_events` for `$DATE T00:00 → $DATE T23:59` local.
- Merge into a single timeline; dedupe identical events that appear on multiple accounts (same title + start time).
- **Skip** events where any of:
    - The event is a personal block / focus-time / "Lunch" / transit buffer (🚇 prefix) / "DND".
    - You are the sole attendee.
    - `responseStatus` is `declined`.
    - It's a recurring routine with no external attendees AND the same routine ran in the last 7 days (e.g. daily standup) — surface the time + title but skip the full prep dossier.

For every remaining event, run the `/meeting-prep` procedure inline (see `.claude/skills/meeting-prep/SKILL.md` steps 2–6). Specifically:

1. **Attendees → people notes.** For each non-Brady attendee email, look up `+ Atlas/People/*.md` via `emails` frontmatter. Flag unknowns inline (don't stage stubs — that's `/people-sync`'s job).
2. **Recent interactions.** Grep `+ Atlas/Interactions/*.md` for `[[wikilinks]]` to each known attendee; read up to 3 most recent per person.
3. **Open commitments.** Extract `## Open commitments` from each person note + unresolved follow-ups from the recent interactions.
4. **Related projects.** Follow `[[wikilinks]]` from person/interaction notes to `+ Spaces/*` MOCs; one-line status each.
5. **Recent threads.** For each attendee: search the matching `google_*` and `slack_*` MCP for messages in the last 14 days. Cap 3 per source. Summarize — never dump raw content.

**Parallelization within the meeting set:** issue all read calls (person note reads, interaction greps, Gmail/Slack searches, project MOC reads) across all meetings in a single fan-out block. Compose per-meeting briefings only after the reads complete.

### 4. Assemble `orientation.md`

Write `+ Inbox/orient/$DATE/orientation.md` with this structure (omit sections that are empty):

```markdown
# Orientation — $DATE

_(Compared against $LAST_BIZ — $WEEKDAY)_

## What landed since $LAST_BIZ

### New tasks (N)
- [Task Name](permalink) — Effort **X** · _project_ · created `<HH:MM>`
- ...

### Closed since $LAST_BIZ (N)
- [Task Name](permalink) — Effort **X** · completed `<HH:MM>`
- ...

## Stock & flow

|              | Count | Effort |
|--------------|-------|--------|
| Open now     | N     | E      |
| Added        | +n    | +e     |
| Completed    | -n    | -e     |
| **Net**      | ±n    | ±e     |

_(M open tasks have no Effort estimate — pile is partially unmeasured.)_

## Today's meetings

### `HH:MM–HH:MM` <Meeting Title> · `account-slug`
**Attendees:** [[Person A]], [[Person B]], unknown:person.c@external.com

**Recent context:** <≤3 lines summarizing last interactions>

**Open commitments**
- Theirs → mine: <list>
- Mine → them: <list>

**Related projects**
- [[Space MOC]] — <one-line status>

**Recent threads**
- ✉️ <subject> (<account>, <date>) — <gist>
- 💬 <slack thread snippet> (<workspace>, <date>) — <gist>

---

### `HH:MM–HH:MM` <Next Meeting> · ...
(repeat per meeting)

## Focus suggestion

<single line drawing on new tasks + meeting load — what one thing matters most today>
```

### 5. Report

Echo the path to the written file and a one-paragraph summary: total new tasks, net effort delta, number of meetings prepped. Do not paste the file body back into chat.

## Forbidden patterns

- Do NOT write into the daily note (`+ Atlas/Daily/`). That's `/daily-brief`'s territory; orientation.md is the `/orient` artifact.
- Do NOT call `asana_search_tasks` — `assignee_any:me` is broken (see memory `feedback_asana_assignee_filter`). Use `asana_get_my_tasks` and filter by `assignee.name`.
- Do NOT run `/meeting-prep` as a separate skill invocation per meeting — inline the read fan-out across all meetings to keep total tool calls down.
- Do NOT trust the snapshot in `data/asana.csv` for the stock/flow numbers. It's stale; always fetch live for this skill.
