---
name: refine-work
description: Phase 2 of /orient. Read data/current.csv, drop noise, collapse threads, cross-link work that moved between media, match against Asana, and write data/refined.csv with three candidate buckets (definite_duplicate, possible_duplicate, probable_new_work). Asana is the source of truth.
---

# /refine-work

## Framing

**Asana is the source of truth** for work that survives refinement. Two competing goals:

1. Capture all work (don't drop a real ask just because we're not sure).
2. Avoid duplicating work (don't propose creating an Asana task that already exists).

The refinement pass turns the raw, multi-row, multi-channel `data/current.csv` from `/gather-work` into `data/refined.csv` — one row per real candidate work item, classified against the current Asana state.

## Inputs

- `data/current.csv` — gather-work output. 15 columns described in `gather-work/SKILL.md`.
- Live Asana state for both workspaces Brady has access to. Per memory `project_asana_config.md`, currently work-only at doromind workspace GID `1205801040312777`.

## Outputs

- `data/refined.csv` — superset of `current.csv` with 4 added columns:
    - `bucket`: one of `probable_new_work`, `possible_duplicate`, `definite_duplicate`, `done`, `dropped`.
    - `asana_gid`: matched Asana task gid, if any.
    - `asana_match_reason`: ≤20-word reason citing the signal that drove the match (thread-id, subject, semantic similarity, etc.).
    - `next_action`: rewritten action-verb summary describing what Brady should *do* — e.g. "Reply to Mimi confirming superbills coordination plan", not "Mimi asked Brady to coordinate". Empty for `dropped` and `done` buckets.

## Procedure

### Step 1 — Drop and set-aside passes

For each row in `current.csv`:

- `potential_work == N` → bucket = `dropped`. Skip the rest of refinement for this row.
- `done == Y` → bucket = `done`. Skip the rest of refinement. (These are closed loops worth keeping in the file for audit; `/brief-me` will ignore them.)

Everything else (`potential_work=Y` and `done=N`) flows to step 2.

### Step 2 — Thread collapsing

Group surviving rows by `thread`:

- For Gmail: all rows with the same `thread` value (Gmail threadId) collapse to **one** row representing the thread's open work state.
- For Slack: all rows with the same `thread` (thread_ts) collapse similarly. Top-level messages without a thread_ts stay as their own row.
- For iMessage: collapse by `thread` (chat_id) **only if the rows are part of the same back-and-forth on the same topic**. iMessage groups everything under a chat_id even when topics differ — don't merge unrelated topics.

Collapse rules:

- Take the **earliest inbound ask** (or **earliest outbound commitment** if no inbound) as the representative row.
- The representative row's `acknowledged` and `done` reflect the **latest** state across all collapsed rows. If any later row in the same thread has `done=Y`, the collapsed row is `done=Y` → bucket = `done` and we skip the rest of refinement.
- Note all collapsed source URLs in `asana_match_reason` so the Asana task we eventually link to (or create) can reference all the deep links.

### Step 3 — Cross-medium linking

Some work crosses channels. Examples seen in this vault:

- A member-escalation **email** (Pam Levin SuperBill) gets **forwarded into a Slack mpdm** for coordination, and Brady commits via Slack. The email row and the Slack rows are the same work.
- A **Slack DM** referencing an **email thread** (Magdiel reschedule) — same work.

Heuristics to detect cross-medium pairs:

- **Subject / body keyword overlap** — Slack message body contains the email subject, or both rows name the same person + topic ("PL superbills", "Pam Levin SuperBill", "Magdiel reschedule").
- **Same counterparty + close timestamps** — counterparty matches and timestamps within ~24 hours.
- **Explicit reference in the message** — "I just forwarded", "see email", "started a Slack thread for us to work it through", "pulled y'all into the thread".

When a cross-medium pair is detected, collapse to **one** row using the same rules as Step 2 (earliest inbound ask wins; latest done state wins). Record the linkage in `asana_match_reason`.

### Step 4 — Cross-mailbox dedup

The shared-alias inbound sweep can produce duplicate rows for the same external email when the sender CCs both `brady@doromind.com` and a shared alias (`finance@`, `guides@`). Two rows, different `source_url`, identical sender / subject / timestamp.

Heuristics:

- Same `From:` address + same subject (after stripping `Re:` / `Fwd:`) + sent within 60 seconds → same external delivery.
- Prefer the brady@-direct row as the survivor; cite the alias row in `asana_match_reason`.

### Step 5 — Fetch Asana state

Pull all Asana tasks where Brady is `assignee` OR `created_by`, across configured workspaces. Include:

- `gid`, `name`, `notes`, `permalink_url`
- `assignee`, `created_by`, `created_at`, `modified_at`, `due_on`, `completed`, `completed_at`
- `projects`, `tags`, `parent` (for subtask context)
- **All custom fields** — include the full custom_fields array so we can match on Gmail thread ID, Slack permalink, etc.

Cache the fetch in memory for the run. Re-running this fetch within a single skill invocation is wasteful — pull once, hold the list.

**Discover the thread-link custom field on first run.** Look for a custom field named like `Gmail Thread ID`, `Email Thread`, `Source Thread`, or similar. If found, record its `gid` for the matching step. If no such field exists, fall back to scanning task `notes` for thread IDs and permalinks.

### Step 6 — Match candidates to Asana tasks

For each candidate row that survived steps 1–4, in this order:

1. **Definite match: Gmail thread ID equals the row's `thread`.**
    - Either via the custom field discovered in step 5, OR via the task `notes` / `permalink_url` containing the thread ID string.
    - Bucket = `definite_duplicate`. Set `asana_gid` and reason "Gmail threadId match".

2. **Definite match: Slack permalink contained in task notes.**
    - Bucket = `definite_duplicate`. Reason: "Slack permalink in task notes".

3. **Possible match: subject / counterparty / topic semantic similarity.**
    - Compare row's `summary` + `counterparty` + key terms against open Asana task names + notes. Use judgment — same person + same noun phrase (e.g., "Pam Levin superbill", "CT license") is a strong signal even without exact string match.
    - Bucket = `possible_duplicate`. Reason: cite the overlap ("counterparty 'Mimi Liu' + topic 'superbill' matches Asana task 'Sam Levin Medicare SuperBills'").

4. **No match.**
    - Bucket = `probable_new_work`. Reason: "no matching Asana task found".

### Step 7 — Rewrite `next_action`

For each row in `probable_new_work`, `possible_duplicate`, or `definite_duplicate`:

- Rewrite `summary` into an action verb describing what *Brady should do next*.
- Format: imperative verb + object + (optional context). ≤15 words.
- Examples:
    - "Mimi asked Brady to coordinate with Minna on superbills" → "Coordinate w/ Minna on PL superbill response (Mimi asked, traveling)"
    - "Kate re-pinged Brady on temp CT license" → "Decide on pursuing temp CT license; reply to Kate"
    - "Jon flagged Cursor payment failed Visa 3445" → "Fix Cursor card-on-file (failed payment, Jon flagged)"
- For `definite_duplicate`, `next_action` is "(see Asana: <task name>)" since the work is already tracked.

### Step 8 — Sort and write

Order the output:

1. `probable_new_work` first (likely most actionable, not yet tracked).
2. Then `possible_duplicate` (needs Brady's eye to decide).
3. Then `definite_duplicate` (already tracked — confirms our gather caught real work).
4. Then `done` (audit trail).
5. Then `dropped` (deepest archive).

Within each bucket, sort by `received` date descending (newest first).

Write `data/refined.csv` with 19 columns: 15 from `current.csv` + 4 new (`bucket`, `asana_gid`, `asana_match_reason`, `next_action`).

### Step 9 — Interactive Asana push

After `refined.csv` is written, surface the candidate work to Brady via `AskUserQuestion` and let him pick which items to push to Asana.

Constraints of `AskUserQuestion`:
- Max 4 questions per call.
- Each question takes 2–4 options.
- No native pre-select / default-checked support — only labels, descriptions, and a multiSelect flag.
- `header` (chip/tag, max 12 chars) is the natural place to surface the **bucket category**.

Layout:

- One question per non-empty bucket among `probable_new_work`, `possible_duplicate`, `definite_duplicate`. Use `multiSelect: true`.
- `header` = bucket name in short form: `Probable new`, `Possible dupe`, `Def. dupe`.
- If a bucket has more than 4 items, split into multiple questions with the same header (e.g., `Probable new (1 of 2)`).
- If a bucket has only 1 item, you cannot ask about it alone (min 2 options) — pair it with the next bucket's items in a single question and put the bucket label inside the option label.

Option label format (now that the bucket is in the pane header):

```
For <actor>: <next_action>
```

- `<actor>` = the row's `counterparty`. For self-commitments (outbound), use the recipient's name ("For Magdiel: ...").
- `<next_action>` = the rewritten action verb from Step 7.

Option description:

```
<one-line context>. <source_url>
```

For `definite_duplicate` rows, also include the matched Asana gid in the description: `Already in Asana <gid>`.

Recommendation hint:

- For `probable_new_work` and `possible_duplicate`, the user almost always wants to push — those are the bucket's reason for being. Don't add "(Recommended)" labels — the bucket header already implies the recommendation.
- For `definite_duplicate`, the default is **don't** push (the work is already tracked). Show them anyway for completeness so Brady can override if the existing Asana task is wrong/stale.

After the user answers:

1. For each selected `probable_new_work` / `possible_duplicate` item, **two-call sequence**: `asana_create_task` then `asana_update_task`. The create tool does NOT accept a `custom_fields` parameter — custom fields must be set via a follow-up update.

    **Call 1 — `asana_create_task`:**
    - `name`: from `next_action`.
    - `notes`: include the source `summary`, all collapsed source URLs from `asana_match_reason`, and the receiving date(s).
    - `assignee`: `me`.
    - `project_id`: **`1208193100268936`** ("Founders Backlog"). Always.
    - `due_on`: omit / leave null. New work lands in the backlog without a due date; Brady triages later.

    **Call 2 — `asana_update_task` on the gid returned by Call 1:**
    - `custom_fields`: a map keyed by custom_field gid, with values that are enum_option gids (for enum fields) or strings/numbers/dates (for text/number/date fields).
        - `"1207543199556043": "1207543199556046"` → set `Status (Global)` to `Backlog`.
        - `"1213297635072824": "<gmail thread id>"` → set `Gmail Thread Id` (only when `source_mcp` starts with `gmail_`; omit the key entirely otherwise).
2. For each selected `definite_duplicate` item, **don't** create a new task. Either: (a) leave alone, or (b) post a story/comment on the existing task with the new Slack/email URL as a "fresh activity" pointer. Default to (a) unless the user explicitly opts in.
3. After creation, update `refined.csv` rows in place:
    - **Pushed rows** (selected probable_new_work / possible_duplicate, including all collapsed peers): set `asana_gid` to the new task gid and rewrite `asana_match_reason` to `pushed to Asana <gid>` (preserving "(collapsed into ...)" hint for non-survivor rows).
    - **Declined rows** (probable_new_work / possible_duplicate the user did NOT select): prepend `asana_match_reason` with `user declined; original reason: ` so it's clear the row was surfaced and dismissed, not missed.
    - **Definite duplicates** (already-tracked, not pushed): leave `asana_gid` as the matched task's gid (it was set during Step 6 matching). No reason update needed.

Report back:

- Count of pushed tasks, with links.
- Count of declined items (user-skipped probable_new_work).
- Count of definite duplicates left in place.

### Step 10 — Fibonacci effort + focusing questions

This step grooms Brady's open Asana queue so each task has an effort estimate and is immediately actionable. Run against **all incomplete tasks assigned to Brady** in the work workspace — both the existing tasks we fetched in Step 5 AND any tasks just created in Step 9.

**Pass 10a — Estimate effort on tasks missing it.**

The `Effort` custom field has gid `1214179053266044` (number, integer). Identify tasks where this field is absent or its `number_value` is null.

For each such task:

1. If full task details aren't already cached from Step 5, fetch via `asana_get_task` with `opt_fields=name,notes,due_on,projects.name,custom_fields,dependencies,permalink_url` to get description, dependency list, and project context.
2. Estimate a Fibonacci score from `{1, 2, 3, 5, 8, 13, 21}` based on:
    - **Scope** — how much work is in the task body / notes.
    - **Description clarity** — sparse one-liners with no notes are usually 1–3; rich scope docs trend higher.
    - **Ambiguity** — vague language ("figure out", "explore", "see if") trends higher.
    - **Dependencies** — `dependencies` list non-empty, or notes describe blockers, trends 8+.
    - Anchors: a copy-paste fix or single-message reply ≈ 1; a half-day investigation ≈ 5; a multi-day cross-team coordination ≈ 13; week-plus initiatives ≈ 21.
3. Set the `Effort` custom field via `asana_update_task` with `custom_fields: {"1214179053266044": <number>}`.
4. Post a task comment via `asana_create_task_story` with body:
    ```
    :bot: Effort explanation: <one sentence>
    ```
    The sentence should cite the signals that drove the score ("One-line task with clear single action"; "Multi-team coordination with two open dependencies and 5/8 deadline"; etc.).

**Pass 10b — Focusing questions for tasks that aren't immediately actionable.**

For every incomplete task (including those that already had an effort score), check if it's *immediately actionable*: i.e., a clear next physical action that Brady could start without further clarification. Examples of NOT immediately actionable:

- Vague verb ("figure out", "explore", "look into", "review") with no concrete artifact.
- Definition of done is unclear.
- Owner of an underlying decision isn't named.
- The system/account/context isn't specified.
- Has unresolved dependencies that need to be unblocked first.

If not immediately actionable, draft **up to 5** focusing questions whose answers would make it actionable. Common shapes: "Who owns the decision on X?", "What's the definition of done?", "Is this blocked by Y?", "Which Stripe / Rippling / Asana account is this in?", "What format does the deliverable take — doc, deck, code?"

Post via `asana_create_task_story`:
```
Questions to make this actionable:
- <question 1>
- <question 2>
- ...
```

If the task IS immediately actionable, do nothing for pass 10b.

**Skip rules:**

- Don't re-estimate or re-question tasks where Brady has already commented (look for stories authored by Brady's user gid). Idempotency on re-run.
- Don't post duplicate `:bot: Effort explanation:` or `Questions to make this actionable:` comments — if the task already has a story whose text starts with either of those literal strings, skip the post.

**Custom-field-not-enabled — surface, don't skip silently.**

Brady's standing convention: any task assigned to him should have `Effort` available. If `asana_update_task` returns `Bad Request` because the field isn't enabled on the task's project, that's a configuration gap to fix, not a graceful-degradation case.

When this happens:

- Do NOT post the `:bot: Effort explanation:` story for that task (the explanation would be misleading without a real value set).
- Still run Pass 10b (focusing questions) on the task — that path doesn't depend on the custom field.
- Log the gid + project name + the effort estimate you would have applied (in the audit JSON) so Brady can apply it after enabling the field.

**At the end of Step 10, report the unique list of projects that lack `Effort`** so Brady can enable the field via the Asana UI (Project → Customize → Add field → Effort). The MCP toolkit does not currently include a `create_project_custom_field_setting` action, so this is a manual one-time fix per project.

After Brady enables the field on those projects, re-running `/refine-work` will pick up the missing estimates (idempotent skip rules ensure existing estimates aren't overwritten).

**Report back:**

- Count of effort estimates set, broken down by Fibonacci value.
- Count of focusing-question comments posted.
- Sample of 3–5 task names + the effort/questions you assigned, so Brady can sanity-check.

## Verification

Before completing:

- Every row in `current.csv` is represented in `refined.csv` exactly once OR is collapsed into another row's `asana_match_reason`.
- Every `definite_duplicate` row has a non-empty `asana_gid`.
- Every `possible_duplicate` row has a non-empty `asana_gid` AND an `asana_match_reason` citing the overlap signals.
- Every `probable_new_work` row has a non-empty `next_action`.
- No row has `bucket=probable_new_work` AND `asana_gid` populated (contradiction).
- Counts: `len(refined) ≤ len(current)`. Report the collapse ratio.

## Forbidden patterns

- Do NOT auto-create Asana tasks. This skill only proposes; creation is the user's call (or `/process-inbox`'s job).
- Do NOT drop rows silently. Every dropped/collapsed row must show up either as its own line or be cited in the `asana_match_reason` of the surviving row.
- Do NOT use Gmail subject as the dedup key alone — many Doro Guides templates share subjects ("Follow-up from Doro Mind").
