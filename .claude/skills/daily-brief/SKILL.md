---
name: daily-brief
description: Produce today's daily briefing across all Google Calendars, Gmail accounts, Slack workspaces, and Asana. Writes to + Atlas/Daily/YYYY-MM-DD.md and surfaces anything that needs the user's attention today. Safe to re-run — refreshes the `## Morning brief` section in place.
---

# /daily-brief

Assemble the user's daily briefing for today (or a date passed as `$1`). Creates or updates the matching daily note in `+ Atlas/Daily/`. Re-runnable: the skill replaces the `## Morning brief` section in place rather than appending a new one.

## Inputs

- `$1` (optional): target date in `YYYY-MM-DD`. Defaults to today.

## Procedure

> **Date check first.** Before any other work, if `$1` is not supplied, resolve "today" by running `Bash: date "+%Y-%m-%d %A %H:%M %Z"`. Do **not** trust the session-injected `currentDate` field — it can lag the real clock by a day. Use the shell result as the target date for everything below.

> **Parallelization:** steps 1–6 are mostly independent read-only gathers. Fan out **every** MCP call — all `google_*` accounts, all `slack_*` workspaces, all configured Asana workspaces, Fathom, and Messages — in a single tool-use block unless a step depends on prior results. Do not serialize across accounts or across unrelated steps. Step 1c (missed-meeting Fathom summaries) is a **second-wave** fan-out after step 1 results are in hand. Step 4b writes happen after reads complete.

1. **Calendar sweep.** For each `google_*` MCP, call `google_calendar_list_events` for the target date (00:00 → 23:59 local). Merge into a single timeline; tag each event with the owning account slug. Collapse duplicate events that appear on multiple calendars (same title + time). For each attendee entry, capture `self`, `responseStatus`, and event start/end times — needed for step 1c.

1b. **Fathom recordings.** Call the Fathom list tool your server exposes (`mcp__fathom__fathom_list_meetings` or `mcp__fathom__list_meetings`) for meetings in the last 24h. For each, note title, participants, and whether a summary is available. Surface under a **Recent recordings** section in the brief — title, attendees, and a `fathom:<meeting-id>` reference the user can pass to `/capture-meeting` if they haven't already processed it.

1c. **Missed-meeting Fathom summaries.** From the calendar sweep (step 1), identify events that have already ended on the target date (and the preceding day if the brief runs before 10:00 local) where **you** were an invited attendee (`self: true`) but `responseStatus` is `declined`, `tentative`, or `needsAction`. For each such event, search Fathom (`mcp__fathom__fathom_search_meetings` by title or time window, or scan the list from step 1b) for a matching recording. If a recording exists and a summary is available, fetch it via `mcp__fathom__fathom_get_summary`. Surface under a **Missed meetings** section — meeting title, time, organizer, attendees, and the Fathom summary (truncated to 3–5 bullets). Omit the section if no matches.

2. **Priority mail.** For each `google_*` MCP, `google_gmail_search_emails` with `is:unread newer_than:2d (is:important OR is:starred OR label:^iim)`. Capture subject, sender, account slug. Cap at **5** items **per account** in the prose you write into the brief and dashboard — still execute the query fully; summarize the strongest signals.

2b. **Sent-email commitment scan.** For each `google_*` MCP, search sent mail: `in:sent newer_than:2d`. For each result, read the message body and look for language where **you** made a commitment or promised a next action — phrases like "I'll", "I will", "let me", "I'll send", "I'll follow up", "I'll get back", "I'll check", "I'll connect", "I'll introduce", "will have this to you", "I'll loop you in", "I'll look into", "sending over shortly", "I'll make sure", "will do", etc. Extract each distinct commitment as a short snippet (≤ 100 chars) plus its thread subject and counterparty.

   After step 4 data is in hand, cross-reference each extracted commitment against the open Asana task list: do a loose keyword match on the counterparty name and action verb. A commitment is **tracked** if a matching incomplete Asana task exists (same person + similar action). A commitment is **dangling** if no matching task is found.

   Surface dangling commitments in a **Dangling commitments** section of the brief (and in the dashboard `## Needs a reply / open loops` section). For each:

   - Email subject + counterparty
   - The commitment snippet
   - A `[→ create Asana task]` hint so you can act on it quickly

   Omit the section if every commitment found is already tracked. Cap at 10 per run. Skip automated/templated emails (Asana digests, GitHub notifications, commercial threads).

   **Parallelization:** the `in:sent` searches run in the initial step 1–6 fan-out. The cross-reference against Asana happens in a second wave after step 4 completes — no extra API calls needed.

3. **Slack attention.** For each `slack_*` MCP, search for mentions of the user in the last 24h and list unread DMs. **`slack_conversations_unreads` with `limit: 200`** — the `limit` param caps **channels scanned**, not unreads returned; small limits silently miss DMs. After fetching, summarize the **top ~10** most relevant unread threads.

3b. **Unanswered SMS.** Call `mcp__messages__double_texts` for the past 3 days to surface conversations where someone texted you without receiving a reply. Exclude: automated/system messages (OTP codes, delivery notifications, appointment reminders), group chats with > 10 members, contacts that appear to be services or bots (no saved name, or name looks like a business/short code). Cap at 10. For each remaining candidate, note the sender name, the last unanswered message (truncated to 80 chars), and days since last received.

4. **Overdue tasks.** For each configured Asana workspace (`asana_personal`, `asana_work`), `asana_get_my_tasks` with `completed_since=now`, `opt_fields=name,due_on,due_at,completed,assignee_section.name,projects.name,permalink_url,recurrence,custom_fields`, and post-filter to tasks strictly before today (`due_on` / due datetime). The `recurrence` field is mandatory — see "Asana display ordering" below.

4b. **Effort field grooming.** Fetch all assigned incomplete tasks from each configured Asana workspace: `asana_get_my_tasks` with `completed_since=now` and `opt_fields=name,notes,due_on,projects.name,permalink_url,custom_fields,gid`. Identify tasks where the `Effort` custom field is absent or null. Cap at 10 tasks per run (prefer tasks by due date ascending — soonest first). For each such task:

   1. Fetch full task details via `asana_get_task` with `opt_fields=name,notes,due_on,projects.name,custom_fields,dependencies,permalink_url` to get description and context.
   2. Estimate a Fibonacci effort score (1, 2, 3, 5, 8, 13, 21) based on scope, description clarity, ambiguity, and dependencies. A one-liner with no description is usually a 1–3; a task with multiple dependencies or vague scope is 8+. Document reasoning in one sentence.
   3. Draft 2–5 questions whose answers would make the task immediately actionable (examples: who owns a decision, what is the definition of done, are there blockers, which system/account does this apply to, etc.).
   4. Post the estimate + questions as a task comment via `asana_create_task_story` with body:

      ```
      🤖 Effort estimate (auto-draft): **X**
      Reasoning: <one sentence>

      Questions to make this actionable:
      - <question 1>
      - <question 2>
      ...
      ```

   5. Do **not** update the Effort custom field value itself — the comment is a draft for you to review; you set the field after reviewing.
   6. **Email next step.** If the task name, notes, or questions suggest the immediate next action is sending an email (e.g. "email X about Y", "follow up with", "send proposal", "reach out"), draft that email via `mcp__superhuman__create_or_update_draft`. Use the correct work account where applicable. Subject from context; body should be concise and match your voice (see CLAUDE.md §6). Include a note in the Asana comment: `📧 Draft email saved in Superhuman — review before sending.`

   **Parallelization:** fan out all `asana_get_task` reads in one block, then fan out all `asana_create_task_story` writes and `mcp__superhuman__create_or_update_draft` calls in the next block after reads complete.

5. **Stale relationships.** Grep `+ Atlas/People/*.md` for notes whose `last_contact` is older than their `cadence` allows (weekly: > 7d, monthly: > 30d, quarterly: > 90d, asneeded: never stale). Cap at 5.

6. **People detection pass.** From the calendar attendees + priority mail senders/recipients + Slack counterparties gathered in steps 1–3, check each identifier against `+ Atlas/People/*.md` frontmatter (`emails`, `slack`, `title`, `aliases`). Unknown humans (after filtering no-reply/bots/resources per `/people-sync` rules) become a **New faces** candidate list — do not stage stubs from this skill; just surface them. Recommend `/people-sync` if the list is non-empty.

6b. **Draft replies for actionable threads.** After steps 1–6, draft responses for "Needs a reply" items where the user is the next actor. Skip:

   - Items classified as `Delegated / FYI` (care team, ops auto-alerts)
   - Observer-only threads
   - Automated notifications (Asana digests, Dependabot, commercial mailing lists)

   For each actionable item:

   1. **Resolve account + thread.** Use the `google_*` MCP that surfaced the message (from step 2), or the `slack_*` workspace (from step 3).
   2. **Gather context.** Read the full thread via `google_gmail_read_email` on the matching `google_*` MCP (using the message ID from step 2). Check `+ Atlas/People/` for the sender's person note — pull open commitments, recent interactions, and relationship context. For Slack, read the thread via `slack_<slug>_conversations_replies`.
   3. **Compose draft.** Match the user's voice (see CLAUDE.md §6). Lead with the ask or the answer. For email: use `Re: <original subject>`. For Slack: no subject. **Email formatting:** write each paragraph as a single unbroken line; only use blank lines (`\n\n`) between paragraphs — never `\n` inside a paragraph (Gmail preserves hard breaks and renders a narrow column).
   4. **Save draft.**
      - **Email:** `google_gmail_draft_email` on the matching `google_*` MCP with `threadId` + `inReplyTo` set so it appears as an in-thread reply.
      - **Slack:** `mcp__claude_ai_Slack__slack_send_message_draft` with `channel_id` + `thread_ts` if replying in-thread. (This is the one approved use of the deprecated connector — see CLAUDE.md §9.)
   5. **Log vault trail.** If the sender resolved to a person note, append a bullet under its `## Threads` section: `- <date> · drafted follow-up (<channel>:<draft-id>) — <one-line gist>`. Do NOT update `last_contact` — a draft is not a touchpoint.

   **Parallelization:** fan out all `google_gmail_read_email` / thread-read calls in one tool-use block, then fan out all `google_gmail_draft_email` / `slack_send_message_draft` calls in the next block.

7. **Compose the daily note.** If `+ Atlas/Daily/<date>.md` does not exist, scaffold from `+ Extras/Templates/Daily.md`. If a `## Morning brief` section already exists in the note, **replace its body in place** (find the `## Morning brief` heading and overwrite everything up to the next H2 or EOF). Otherwise insert a new `## Morning brief` section near the top. Contents:

   - **Today's calendar** (merged timeline, grouped bullet list, `[HH:MM–HH:MM] Title · account-slug · other attendees if any`)
   - **Recent recordings** (Fathom meetings from last 24h not yet captured as interaction notes — title, attendees, `fathom:<id>` ref; omit section if empty)
   - **Missed meetings** (from step 1c — meetings you were invited to but did not attend, with Fathom summaries if available; omit section if empty)
   - **Needs a reply** (mail + Slack, grouped by account/workspace)
   - **Unanswered SMS** (from step 3b — sender, truncated message, days waiting; omit section if empty)
   - **Drafted replies** — list of drafts saved in step 6b. One bullet per draft: `- ✉️ [[Person]] — Re: Subject · gmail draft <draft-id> · <account>` (or `💬` for Slack). Include a footer: `_(Review and send from Gmail / Slack. Drafts are not sent automatically.)_`. Omit the section if no drafts were generated (all items were delegated/FYI).
   - **Overdue in Asana**
   - **Effort comments posted** (from step 4b — one bullet per task: `- [Task Name](<permalink>) — estimated **X**, comment posted`)
   - **People past cadence** (link with `[[wikilinks]]`)
   - **New faces** — unknown humans seen in today's activity, one line each with source context. Omit the section if empty.
   - A single-line **Focus suggestion** based on the above

8. Never touch any other section of the daily note. Only the `## Morning brief` section is managed by this skill.

9. **Refresh `Dashboard.md` at the vault root.** Only run when the target date is **today** — historical reruns must not rewrite the dashboard. For each dashboard H2 described below, **replace the section body in place** (from the heading through the next H2). If `Dashboard.md` is missing, log a warning and skip step 9. Never touch **`## Quick links`** (static).

   - **Owned by `/daily-brief`** — rebuild **every** run:
     - `## Today — <Day YYYY-MM-DD>` — pivot meeting + condensed timeline anchors; refresh the heading date.
     - `## Needs a reply / open loops` — mirror the brief plus dangling commitments where appropriate; filter delegated/FYI noise.
     - `## People past cadence`
     - `## Delegated / FYI`
   - **Owned by `/weekly-review`** — do **not** overwrite fresh content: leave `## This week (...)`, `## Top priorities`, and **`## Notes / carry`** alone when they were updated this ISO week **unless** a section body is obviously empty placeholder text. Compare `Dashboard.md` frontmatter `updated:` to week context; see `/weekly-review` for ownership. When you **must** stub because the section is empty or stale ahead of `/weekly-review`, pull **fresh calendar + Asana**:

     - **Calendar stub:** across all `google_*` MCPs, `google_calendar_list_events` from Monday 00:00 through Sunday 23:59 of the ISO week containing today — split into concise **meetings that matter** vs **personal anchors** as in `/weekly-review` expectations.
     - **Asana stub:** use the widened **`## Top priorities`** query from “Asana scope note” (`due_on` from today through today + 7 days); apply recurrence grouping rules.

   - **Frontmatter.** Set `updated:` to `<today>` after writing dashboard sections `/daily-brief` touched.

   **Idempotence.** Same-day reruns overwrite in place; never append.

## Output shape

Create or refresh the `## Morning brief` section in `+ Atlas/Daily/<date>.md`, plus whichever `Dashboard.md` sections this skill rebuilt (step 9). Brief the user — include dashboard refresh status, count of Effort comments posted (if step 4b ran), missed meetings found, unanswered SMS surfaced, and drafted replies saved.

## Asana scope note

Step 4 ("Overdue tasks") is for the brief itself. When stubbing **`## Top priorities`** for the dashboard, widen Asana results to tasks with `due_on` between today and today + 7 days across workspaces (`asana_get_my_tasks` widened compared with step 4’s overdue-only filter).

## Asana display ordering

Whenever this skill renders a flat list of Asana tasks (in **`Overdue in Asana`** in the brief, today's must-do strips on **`Dashboard.md`**, or **`## Top priorities`**), group by **`recurrence.type`** with sub-headings sorted least-frequent → most-frequent so one-offs surface first.

**Source of truth: `recurrence.type`.** Never guess cadence from the task title alone.

**Required `opt_fields`.** **`recurrence` and `custom_fields` must be requested** anytime tasks feed numbered lists needing grouping or Effort-aware commentary. Recommended string:
`name,due_on,due_at,completed,assignee_section.name,projects.name,permalink_url,recurrence,custom_fields`

### `recurrence.type` → display group

| `recurrence.type` | Display group | Order |
|---|---|---|
| `never` | **One-off** | 1 (highest priority) |
| `yearly` | **Annually** | 2 |
| `monthly` | **Monthly** | 3 |
| `weekly` | **Weekly** | 4 |
| `daily` | **Daily** | 5 (collapsed bottom) |

If `recurrence` is missing from a response (API quirks), assume `never`, flag with **`?`** for manual follow-up.

Within each bucket, secondary sort by `due_on` ascending; omit empty groups. Use bold inline labels (`**One-off**`), not H3, inside stacked lists.

## Notes

- **Idempotent by design** for regenerated markdown sections (`## Morning brief` + dashboard shards above).
- **Effort comments are not idempotent** — step 4b posts Asana comments. Before posting another `🤖 Effort estimate`, check for one already on the thread; skip if present.
- Never **send** mail or Slack from this skill (drafts only; step 6b).
- MCP failures belong in prose as `_(google_<slug>: unavailable)_`; otherwise continue.

- Respect **`#workspace/personal`** vs **`#workspace/work`** filtering only when the brief is explicitly scoped — e.g. `/daily-brief work` → skip assets tagged purely personal unless asked.
