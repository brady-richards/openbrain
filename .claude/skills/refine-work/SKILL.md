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
