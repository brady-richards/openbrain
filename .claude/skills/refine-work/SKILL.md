---
name: refine-work
description: Phase 2 of /orient. Read potential work from data/stuff.db, match against the Asana snapshot in data/asana.csv, classify each row into a bucket (definite_duplicate, possible_duplicate, probable_new_work, done, dropped), and write the verdict back into data/stuff.db.
---

# /refine-work

## Framing

**Asana is the source of truth** for work that survives refinement. Two competing goals:

1. Capture all work (don't drop a real ask just because we're not sure).
2. Avoid duplicating work (don't propose creating an Asana task that already exists).

The refinement pass turns the raw, multi-row, multi-channel `stuff` table from `/gather-work` into a classified set of candidate work items, one per real work item, scored against the current Asana snapshot.

## Inputs

- **`data/stuff.db`** — the `stuff` table populated by `/gather-work`. See `gather-work/SKILL.md` for the schema. The columns this skill reads are `url, received, source, forum, thread, direction, work_or_personal, counterparty, body, summary, potential_work, acknowledged, done`.
- **`data/asana.csv`** — a snapshot of Brady's Asana tasks across both workspaces. Header columns include `workspace_gid, workspace_name, category, gid, name, resource_subtype, completed, completed_at, due_on, permalink_url, assignee_name, assigned_by_name, assignee_section, modified_at, created_at, projects, sections, tags, notes, Effort, …, Gmail Thread Id, …, Source URLs, …, Status (Global), …`. Treat this as a point-in-time replacement for live `get_my_tasks` results — fresh enough for matching but not authoritative for writes.

## Outputs

The skill writes its verdict back into the `stuff` table by populating four columns that may need to be added to the schema on first run:

```sql
ALTER TABLE stuff ADD COLUMN bucket TEXT;
ALTER TABLE stuff ADD COLUMN asana_gid TEXT;
ALTER TABLE stuff ADD COLUMN asana_match_reason TEXT;
ALTER TABLE stuff ADD COLUMN next_action TEXT;
```

Add the columns idempotently (`PRAGMA table_info(stuff)` first; skip the `ALTER` if they already exist).

Column semantics:

- `bucket`: one of `probable_new_work`, `possible_duplicate`, `definite_duplicate`, `done`, `dropped`, `collapsed`.
    - `collapsed` is for non-survivor rows folded into a representative row (see Step 2). The survivor row holds the bucket verdict; collapsed peers point to it via `asana_match_reason = "collapsed into <survivor url>"`.
- `asana_gid`: matched Asana task gid, if any.
- `asana_match_reason`: ≤20-word reason citing the signal that drove the match (thread-id, subject, semantic similarity, collapse pointer, etc.).
- `next_action`: rewritten action-verb summary describing what Brady should *do* — e.g. "Reply to Mimi confirming superbills coordination plan", not "Mimi asked Brady to coordinate". Empty for `dropped`, `done`, and `collapsed` buckets.

## Procedure

### Step 1 — Select the working set; bucket the obvious

```sql
SELECT url, received, source, forum, thread, direction, work_or_personal,
       counterparty, body, summary, potential_work, acknowledged, done
FROM stuff
WHERE bucket IS NULL OR bucket = ''
ORDER BY received;
```

For each row:

- `potential_work = 'N'` → `bucket = 'dropped'`. Skip the rest of refinement.
- `done = 'Y'` → `bucket = 'done'`. Skip the rest (closed loop; kept in table for audit).
- Otherwise carry into Step 2.

Write these two verdicts via `UPDATE` in a single transaction at the end of Step 1.

### Step 2 — Thread collapsing

Group surviving rows by `thread`:

- For Gmail: rows with the same `thread` (Gmail threadId) collapse to **one** survivor.
- For Slack: rows with the same `thread` (thread_ts) collapse similarly. Top-level messages without a thread_ts stay as their own row.
- For iMessage: collapse by `thread` (chat guid) **only if the rows are part of the same back-and-forth on the same topic**. iMessage groups everything under a chat_id even when topics differ — don't merge unrelated topics. If you must split, use clusters of `received` timestamps within ~6 hours plus body-keyword overlap.

Survivor rules:

- The **earliest inbound ask** wins (or **earliest outbound commitment** if no inbound).
- The survivor's effective `acknowledged` and `done` come from the **latest** state across all collapsed peers — if any peer has `done='Y'`, the survivor is reclassified to `bucket='done'` here and skips the rest.
- Non-survivors get `bucket='collapsed'` and `asana_match_reason = 'collapsed into <survivor.url>'`.
- The survivor's `asana_match_reason` (built up later) should list all collapsed-peer URLs so the eventual Asana task can reference all of them.

### Step 3 — Cross-medium linking

Some work crosses channels. Examples seen in this vault:

- A member-escalation **email** (Pam Levin SuperBill) gets **forwarded into a Slack mpdm** for coordination, and Brady commits via Slack. The email row and the Slack rows are the same work.
- A **Slack DM** referencing an **email thread** (Magdiel reschedule) — same work.

Heuristics to detect cross-medium pairs (over the post-Step-2 survivors):

- **Subject / body keyword overlap** — Slack body contains the email subject, or both rows name the same person + topic ("PL superbills", "Pam Levin SuperBill", "Magdiel reschedule"). Body is in the `body` column; use it directly.
- **Same counterparty + close timestamps** — `counterparty` matches and `received` timestamps within ~24h.
- **Explicit reference in the message** — "I just forwarded", "see email", "started a Slack thread for us to work it through", "pulled y'all into the thread".

When a cross-medium pair is detected, collapse to one survivor using the same rules as Step 2 (earliest inbound ask wins; latest done state wins). Mark non-survivors `bucket='collapsed'` and reference the survivor in `asana_match_reason`.

### Step 4 — Cross-mailbox dedup

A shared-alias inbound sweep can produce duplicate rows for the same external email when the sender CCs both `brady@doromind.com` and a shared alias (`finance@`, `guides@`). Two rows, different `url`, identical sender / subject / timestamp.

Heuristics:

- Same `From:` line (visible inside `body`) + same subject-like first line (stripping `Re:` / `Fwd:`) + `received` within 60 seconds → same external delivery.
- Prefer the `brady@doromind.com`-direct row as the survivor (forum = `brady@doromind.com`); collapse the alias row.

### Step 5 — Load the Asana snapshot

Read `data/asana.csv`. Parse with a real CSV reader (e.g. Python `csv.DictReader`) — many `notes` cells contain embedded newlines and commas.

For each task row, keep:

- `gid`, `name`, `notes`, `permalink_url`, `completed`
- `assignee_name`, `assignee_section`
- `projects`, `sections`, `tags`
- `due_on`, `modified_at`
- `Gmail Thread Id`, `Source URLs`
- `Status (Global)`, `Effort`

**Hard precheck before any write action:** filter to `assignee_name == 'Brady Richards'` (or the Brady-named alias used in your snapshot). Any later step that creates or updates tasks via the MCP MUST iterate only over this filtered list. Never trust the upstream filter — apply your own.

Build two lookup indexes for matching:

- `by_thread`: dict mapping Gmail Thread Id → task gid (skip blank values).
- `by_url`: dict mapping each URL found in `Source URLs` or `notes` → task gid (split `Source URLs` on whitespace/newlines; pull `https://` substrings from `notes` via regex).

Hold both in memory for the run.

**Field-gid discovery for the eventual Asana push (Step 9):**

- The Asana CSV gives names; the MCP needs gids. On first run, fetch field gids via `mcp__asana_work__asana_get_project` or by inspecting one task with `mcp__asana_work__asana_get_task` (Brady's current gids per prior runs: `Gmail Thread Id` = `1213297635072824`, `Status (Global)` = `1207543199556043`, Backlog enum = `1207543199556046`, `Effort` = `1214179053266044`). Cache them.

### Step 6 — Match candidates to Asana tasks

For each survivor row that's still `bucket IS NULL` after steps 1–4, in this order:

1. **Definite match: Gmail thread ID equals the row's `thread`.**
    - Look up `row.thread` in `by_thread`. If hit, `bucket='definite_duplicate'`, `asana_gid=<gid>`, `asana_match_reason='Gmail threadId match'`.

2. **Definite match: row's `url` appears in `Source URLs` or `notes` of any task.**
    - Look up `row.url` in `by_url`. If hit, `bucket='definite_duplicate'`, `asana_gid=<gid>`, `asana_match_reason='source URL in task notes'`.

3. **Possible match: subject / counterparty / topic semantic similarity.**
    - Compare `row.summary + row.counterparty + key body terms` against open Asana task `name + notes`. Use judgment — same person + same noun phrase (e.g., "Pam Levin superbill", "CT license") is a strong signal even without exact string match.
    - `bucket='possible_duplicate'`, `asana_gid=<best gid>`, `asana_match_reason` cites the overlap ("counterparty 'Mimi Liu' + topic 'superbill' matches Asana task 'Sam Levin Medicare SuperBills'").

4. **No match.**
    - `bucket='probable_new_work'`, `asana_gid=NULL`, `asana_match_reason='no matching Asana task found'`.

### Step 7 — Rewrite `next_action`

For each row in `probable_new_work`, `possible_duplicate`, or `definite_duplicate`:

- Rewrite `summary` into an action verb describing what *Brady should do next*.
- Format: imperative verb + object + (optional context). ≤15 words.
- Examples:
    - "Mimi asked Brady to coordinate with Minna on superbills" → "Coordinate w/ Minna on PL superbill response (Mimi asked, traveling)"
    - "Kate re-pinged Brady on temp CT license" → "Decide on pursuing temp CT license; reply to Kate"
    - "Jon flagged Cursor payment failed Visa 3445" → "Fix Cursor card-on-file (failed payment, Jon flagged)"
- For `definite_duplicate`, set `next_action = '(see Asana: <task name>)'` since the work is already tracked.

### Step 8 — Write verdicts back

In a single transaction, `UPDATE` each survivor and collapsed row with its `bucket`, `asana_gid`, `asana_match_reason`, and `next_action` values. Don't touch any other column.

### Step 9 — Interactive Asana push

After verdicts are written, surface candidate work to Brady via `AskUserQuestion` and let him pick which items to push to Asana.

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

- `<actor>` = the row's `counterparty`. For self-commitments (outbound), use the recipient's name.
- `<next_action>` = the rewritten action verb from Step 7.

Option description:

```
<one-line context>. <url>
```

For `definite_duplicate` rows, also include the matched gid in the description: `Already in Asana <gid>`.

Recommendation hint:

- For `probable_new_work` and `possible_duplicate`, don't add "(Recommended)" labels — the bucket header already implies the recommendation.
- For `definite_duplicate`, the default is **don't** push (the work is already tracked). Show them anyway so Brady can override if the existing Asana task is wrong/stale.

After the user answers:

1. For each selected `probable_new_work` / `possible_duplicate` item, **two-call sequence**: `asana_create_task` then `asana_update_task`. The create tool does NOT accept a `custom_fields` parameter — custom fields must be set via a follow-up update.

    **Call 1 — `asana_create_task`:**
    - `name`: from `next_action`.
    - `notes`: include the source `summary`, all collapsed source URLs (read collapsed peers from the `stuff` table where `asana_match_reason` points at this survivor), and the receiving date(s).
    - `assignee`: `me`.
    - `project_id`: **`1208193100268936`** ("Founders Backlog"). Always.
    - `due_on`: omit / leave null. New work lands in the backlog without a due date; Brady triages later.

    **Call 2 — `asana_update_task` on the gid returned by Call 1:**
    - `custom_fields`: a map keyed by custom_field gid:
        - `"1207543199556043": "1207543199556046"` → set `Status (Global)` to `Backlog`.
        - `"1213297635072824": "<gmail thread id>"` → set `Gmail Thread Id` (only when `source` starts with `gmail_`; omit the key entirely otherwise).
2. For each selected `definite_duplicate` item, **don't** create a new task. Default to leaving it alone; only post a story/comment on the existing task with the new Slack/email URL as a "fresh activity" pointer if the user explicitly opts in.
3. After creation, `UPDATE` rows in the `stuff` table:
    - **Pushed survivor**: set `asana_gid` to the new task gid; rewrite `asana_match_reason = 'pushed to Asana <gid>'`.
    - **Pushed collapsed peers**: also set `asana_gid` to the new gid; keep their `bucket='collapsed'` and append the gid to their `asana_match_reason`.
    - **Declined rows** (probable_new_work / possible_duplicate the user did NOT select): prepend `asana_match_reason` with `user declined; original reason: ` so it's clear the row was surfaced and dismissed, not missed.
    - **Definite duplicates** (already-tracked, not pushed): leave `asana_gid` as the matched task's gid — it was set during Step 6.

Report back:

- Count of pushed tasks, with links.
- Count of declined items (user-skipped probable_new_work).
- Count of definite duplicates left in place.

### Step 10 — Fibonacci effort estimation

Set an effort estimate on every incomplete task assigned to Brady that doesn't already have one. Operate against the filtered task list from Step 5 (after the assignee precheck).

The `Effort` custom field has gid `1214179053266044` (number, integer). Identify tasks where the `Effort` column in `asana.csv` is empty.

For each such task:

1. If the snapshot row's `notes` are too truncated to judge scope, fetch live via `mcp__asana_work__asana_get_task` with `opt_fields=name,notes,due_on,projects.name,custom_fields,dependencies,permalink_url,stories` to get description, dependency list, project context, and existing stories (for idempotency).
2. Estimate a Fibonacci score from `{1, 2, 3, 5, 8, 13, 21}` based on:
    - **Scope** — how much work is in the task body / notes.
    - **Description clarity** — sparse one-liners with no notes trend 1–3; rich scope docs trend higher.
    - **Ambiguity** — vague language ("figure out", "explore", "see if") trends higher.
    - **Dependencies** — `dependencies` non-empty, or notes describe blockers, trends 8+.
    - Anchors: a copy-paste fix or single-message reply ≈ 1; a half-day investigation ≈ 5; a multi-day cross-team coordination ≈ 13; week-plus initiatives ≈ 21.
3. Set the `Effort` custom field via `asana_update_task` with `custom_fields: {"1214179053266044": <number>}`.
4. Post a task comment via `asana_create_task_story` with body:
    ```
    :bot: Effort explanation: <one sentence>
    ```
    The sentence should cite the signals that drove the score ("One-line task with clear single action"; "Multi-team coordination with two open dependencies and 5/8 deadline"; etc.).

**Skip rules (idempotency):**

- Skip if the task already has a story whose text starts with `:bot: Effort explanation:` (a previous run already covered this task — fetch stories via `asana_get_task` if not already cached).
- Skip if `Effort` is already set (non-empty in `asana.csv`, or non-null `number_value` on a live fetch).

**Custom-field-not-enabled handling:**

Brady's convention is that any task assigned to him should have `Effort` available. If `asana_update_task` returns `Bad Request` because the field isn't enabled on the task's project, that's a configuration gap.

- Do NOT post the `:bot: Effort explanation:` story (would be misleading without a real value set).
- Log the gid + project name + the effort estimate you would have applied.
- At the end of Step 10, report the unique list of projects that lack `Effort` so Brady can enable the field via the Asana UI (Project → Customize → Add field → Effort). The MCP toolkit does not include a `create_project_custom_field_setting` action — this is a manual fix per project.

**Note on snapshot freshness:** `asana.csv` is a snapshot. If a task's `Effort` was set after the snapshot was taken, Step 10 will believe it's missing and attempt to update — the MCP write will overwrite the existing value. To avoid that, the idempotency check should be **live** for any task the run is about to write to: re-fetch via `asana_get_task` (custom fields enumerated as in the original Step 5 opt_fields) and skip if `number_value` is already non-null. Treat the snapshot as a fast pre-filter, not the final source of truth for writes.

**Report back:**

- Count of effort estimates set, broken down by Fibonacci value.
- Count of tasks skipped (idempotency).
- Count of tasks blocked (project lacks Effort field), with project list.
- Sample of 5 task names + assigned effort + one-sentence justification, so Brady can sanity-check.

## Verification

Before completing, run these queries:

```sql
-- Every working-set row got a bucket
SELECT COUNT(*) FROM stuff
WHERE (bucket IS NULL OR bucket = '')
  AND (potential_work IN ('Y','N'));
-- Expected: 0

-- definite_duplicate and possible_duplicate rows have an asana_gid
SELECT COUNT(*) FROM stuff
WHERE bucket IN ('definite_duplicate','possible_duplicate')
  AND (asana_gid IS NULL OR asana_gid = '');
-- Expected: 0

-- probable_new_work / possible_duplicate / definite_duplicate rows have a next_action
SELECT COUNT(*) FROM stuff
WHERE bucket IN ('probable_new_work','possible_duplicate','definite_duplicate')
  AND (next_action IS NULL OR next_action = '');
-- Expected: 0

-- probable_new_work rows must NOT have an asana_gid (contradiction guard)
SELECT COUNT(*) FROM stuff
WHERE bucket = 'probable_new_work' AND asana_gid IS NOT NULL AND asana_gid <> '';
-- Expected: 0

-- Collapsed rows point at a survivor
SELECT COUNT(*) FROM stuff
WHERE bucket = 'collapsed'
  AND (asana_match_reason IS NULL OR asana_match_reason NOT LIKE 'collapsed into %');
-- Expected: 0
```

Report the collapse ratio: `count(non-collapsed survivors) / count(working-set rows)`.

## Forbidden patterns

- Do NOT auto-create Asana tasks. This skill only proposes; creation is the user's call.
- Do NOT drop rows silently. Every working-set row ends up with a `bucket` value — `dropped`, `done`, `collapsed`, or one of the three duplicate/new buckets.
- Do NOT use email subject (first line of `body`) as the dedup key alone — many Doro Guides templates share subjects ("Follow-up from Doro Mind").
- Do NOT treat `asana.csv` as authoritative for writes. It's a fast match index. Before any `asana_update_task` call that overwrites a value, re-fetch the live task to avoid clobbering changes made since the snapshot.
