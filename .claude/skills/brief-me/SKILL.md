---
name: brief-me
description: Phase 3 of /orient. Produce orientation.md framing the day — new tasks, task stock/flow vs last business day, summaries of missed meetings since last business day, and per-meeting briefings for every meeting on today's calendar.
---

# /brief-me

Phase 3 of the `/orient` pipeline. Produces a focused orientation note that answers four questions:

1. What new work landed on me since the last business day?
2. Is my task pile growing or shrinking (count + effort)?
3. What happened in meetings I was invited to but missed since the last business day?
4. What do I need to know going into each meeting today?

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
- **Open tasks now (stock universe)** — `completed == false` AND the task is in Brady's current working set, defined as:
    - Status (Global) `In Progress`, OR
    - Status (Global) `To Do`, OR
    - Status (Global) `Backlog` AND `due_on` is null (this is Brady's "Inbox").
  Tasks in `Backlog` with a due date, `On Hold`, `Blocked`, `Done`, etc. are excluded from stock — they're not part of the current pile.

### 2. Task stock & flow

Compute:

- **Stock (now):** count of tasks in the stock universe (defined above), sum of `Effort` across them (treat null Effort as 0 but report the count of null-Effort tasks separately so the user knows how stale the estimate is). Do not include `Backlog`-with-due-date, `On Hold`, or `Blocked` tasks in the stock totals.
- **Flow since `$LAST_BIZ`:**
    - Added: count + total effort of new tasks.
    - Completed: count + total effort of completed tasks.
    - Net change: `added - completed` for both count and effort.

Format as a compact table — see the orientation template below.

### 3. Missed meetings since `$LAST_BIZ`

Identify meetings Brady was invited to in the `[$WINDOW_START, $NOW]` window where he did **not** attend, and summarize what happened from the Fathom transcript.

**Step A — find missed invites.** From the calendar sweep used elsewhere in the pipeline (or a fresh one if running standalone): across all `google_*` MCPs, `google_calendar_list_events` for `$WINDOW_START → $NOW`. Keep events where:

- `self: true` on the attendee row, AND
- `responseStatus` is `declined`, `tentative`, or `needsAction`, AND
- the event's end time is in the past.

Also keep events where `responseStatus` is `accepted` but Brady's calendar shows a conflicting block (out-of-office, overlapping accepted meeting on a different account) — he RSVP'd yes but couldn't be in two places.

Skip: solo blocks, transit buffers (🚇), DND/focus, and personal anchors (gym, school pickup, etc.).

**Step B — fetch the transcript map.** Run:

```bash
python3 ~/repos/fathom-asana-sync/scripts/transcripts_gcs_map.py --interval 7d
```

Output is `meeting title<TAB>gs://bucket/path/to/archive.json` (one row per recording in the rolling 7-day window). Parse into a dict keyed by meeting title.

**Step C — match invites to transcripts.** For each missed invite from Step A, find the best matching transcript by title (exact match preferred; fall back to case-insensitive substring match on the meaningful portion of the title — e.g. "Mimi <> Brady 1:1" should match "Mimi / Brady 1:1"). If no match, note the meeting under a "no transcript available" subsection.

**Step D — summarize each matched transcript.** For each match, pull the JSON from GCS:

```bash
gsutil cat <gs://...> | jq '.'   # or python3 -c "import sys,json; ..."
```

The archive typically contains `meeting_title`, `attendees`, `summary`, `action_items`, and the raw `transcript` segments. Use whatever fields are present:

- If `summary` is present, lift its key points (≤5 bullets).
- If only raw `transcript` is present, produce a 5-bullet summary yourself: what was decided, what's pending, who has next steps, anything Brady would have weighed in on, and anything that affects his open tasks.
- Always pull `action_items` if present — these become candidate follow-ups for Brady.

Cap at 10 missed meetings per run. If there are more, prioritize meetings with: more attendees, longer duration, recent (closer to today), or where Brady is named in `action_items`.

### 4. Meeting prep — every meeting today

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

### 5. Draft replies & next-step emails

Email and Slack drafting is owned by this phase (moved out of `/daily-brief`). Two sources of drafts:

**A. Task next-step emails.** Walk the **open tasks** set from step 1 (not the new tasks — every open task). For each task where the name, notes, or pending questions imply the immediate next action is sending an email (e.g. "email X about Y", "follow up with", "send proposal", "reach out", "ping <name>"), draft that email via `google_gmail_draft_email` on the matching `google_*` MCP. Use the correct account; set `threadId` + `inReplyTo` when replying within an existing thread (look up via `google_gmail_search_emails` with the counterparty's address). Subject from context; body concise, matching the user's voice (CLAUDE.md §6). Post a comment on the Asana task via `asana_create_task_story`: `📧 Draft email saved in Gmail — review before sending. <gmail-draft-permalink-or-id>`.

**B. Actionable inbound threads.** Sweep priority mail and Slack mentions (this skill normally doesn't, so do a focused pass here):

- For each `google_*` MCP: `google_gmail_search_emails` with `is:unread newer_than:2d (is:important OR is:starred OR label:^iim)`. Cap 10 per account.
- For each `slack_*` MCP: `slack_<slug>_my_mentions` + `slack_<slug>_conversations_unreads` with `limit: 200`. Cap 10.

Skip: `guides@` FYI threads, observer-only threads, automated notifications (Asana digests, Dependabot, commercial mailing lists), and items already covered by a closed Asana task referencing the same thread ID/subject (see memory `feedback_priority_mail_asana_crossref`).

For each remaining actionable item:

1. **Gather context.** Read the full thread via `google_gmail_read_email` (or `slack_<slug>_conversations_replies`). Check `+ Atlas/People/` for the sender's note — pull open commitments and recent interactions.
2. **Compose draft.** Match the user's voice. Lead with the ask or the answer. Email subject `Re: <original>`. **Email formatting:** each paragraph is a single unbroken line; only blank lines (`\n\n`) between paragraphs — never `\n` inside a paragraph. Greeting starts with "Hey [Name]," (see memory `feedback_email_greeting`).
3. **Save draft.**
   - Email: `google_gmail_draft_email` on the matching MCP with `threadId` + `inReplyTo` set.
   - Slack: `mcp__claude_ai_Slack__slack_send_message_draft` with `channel_id` + `thread_ts` if replying in-thread (the one approved use of the deprecated connector — see CLAUDE.md §9).
4. **Log vault trail.** If the sender resolved to a person note, append a bullet under its `## Threads` section: `- <date> · drafted follow-up (<channel>:<draft-id>) — <one-line gist>`. Do NOT update `last_contact` — a draft is not a touchpoint.

**Parallelization:** fan out all Gmail/Slack reads in one block, then fan out all draft writes + Asana comment writes in the next block.

Track drafts in a list to surface in step 6 — one entry per draft: `(channel, person-or-counterparty, subject-or-gist, draft-id, account-slug, source-task-gid-if-any)`.

### 6. Assemble `orientation.md`

Write `+ Inbox/orient/$DATE/orientation.md` with this structure (omit sections that are empty):

```markdown
# Orientation — $DATE

_(Compared against $LAST_BIZ — $WEEKDAY)_ · [← yesterday's orientation](+ Inbox/orient/$LAST_BIZ/orientation.md)

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

## Missed since $LAST_BIZ

### <Meeting Title> · `<YYYY-MM-DD HH:MM>` · <duration>
**Attendees:** [[Person A]], [[Person B]], ...
**Why missed:** declined / tentative / no-response / accepted-but-conflicted
**Summary**
- <bullet 1>
- <bullet 2>
- ...
**Action items**
- <person>: <ask>
- ...
**Source:** `gs://...` (or `no transcript available`)

---

(repeat per missed meeting; omit the whole section if none)

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

## Drafted replies & next-step emails

- ✉️ [[Person]] — Re: Subject · gmail draft `<draft-id>` · `<account>` _(source: task [Task Name](permalink) — optional)_
- 💬 [[Person]] — Slack draft in `#channel` · `<workspace>` — <one-line gist>
- ...

_(Review and send from Gmail / Slack. Drafts are not sent automatically.)_

## Focus suggestion

<single line drawing on new tasks + meeting load — what one thing matters most today>

---

[About this repo](ABOUT.md)
```

- The "yesterday's orientation" link is omitted if `+ Inbox/orient/$LAST_BIZ/orientation.md` does not exist.
- Paths in the header and footer are written relative to the repo root so they resolve correctly in the mirrored `README.md` (the canonical front-door view).

### 7. Report

Echo the path to the written file and a one-paragraph summary: total new tasks, net effort delta, number of meetings prepped. Do not paste the file body back into chat.

## Forbidden patterns

- Do NOT write into the daily note (`+ Atlas/Daily/`). That's `/daily-brief`'s territory; orientation.md is the `/orient` artifact.
- Do NOT call `asana_search_tasks` — `assignee_any:me` is broken (see memory `feedback_asana_assignee_filter`). Use `asana_get_my_tasks` and filter by `assignee.name`.
- Do NOT run `/meeting-prep` as a separate skill invocation per meeting — inline the read fan-out across all meetings to keep total tool calls down.
- Do NOT trust the snapshot in `data/asana.csv` for the stock/flow numbers. It's stale; always fetch live for this skill.
