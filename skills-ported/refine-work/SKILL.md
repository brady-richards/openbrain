---
name: refine-work
description: Phase 2 of the orientation workflow. Deduplicate potential work from data/stuff.db, match against Asana tasks in data/asana.csv, and interactively push new items to Asana. Use this after /gather-work to triage incoming requests and commitments.
---

# Refine Work

## Overview

This skill triages "potential work" identified in `data/stuff.db`. It groups related messages (collapsing), matches them against existing Asana tasks (deduplication), rewrites summaries into actionable "next actions", and lets the user choose which items to push to Asana.

## Inputs
- `data/stuff.db`: SQLite database containing classified messages.
- `data/asana.csv`: Snapshot of Asana tasks.

## Procedure

### 1. Schema Preparation
Ensure the `stuff` table has these columns:
```sql
ALTER TABLE stuff ADD COLUMN bucket TEXT;
ALTER TABLE stuff ADD COLUMN asana_gid TEXT;
ALTER TABLE stuff ADD COLUMN asana_match_reason TEXT;
ALTER TABLE stuff ADD COLUMN next_action TEXT;
```

### 2. Initial Bucketing
- `potential_work = 'N'` -> `bucket = 'dropped'`
- `done = 'Y'` -> `bucket = 'done'`

### 3. Collapsing & Linking
Group surviving rows to avoid duplicate triaging:
- **Thread Collapsing**: Group by `thread` (Gmail `threadId` or Slack `thread_ts`). Earliest inbound ask wins as survivor.
- **Cross-Medium Linking**: Detect related work across Slack/Email (e.g., forwarded email to Slack). Match by keyword overlap (e.g., "Pam Levin superbill") or same counterparty + close timestamps (~24h).
- **Non-survivors**: Set `bucket = 'collapsed'` and `asana_match_reason = 'collapsed into <survivor_url>'`.

### 4. Asana Matching
Use `data/asana.csv` to build lookup indexes (`by_thread`, `by_url`).
Match survivors:
1. **Definite Match**: `thread` matches `Gmail Thread Id` OR `url` is in `Source URLs`/`notes`. Set `bucket = 'definite_duplicate'`.
2. **Possible Match**: Semantic similarity (Subject/Counterparty/Topic). Set `bucket = 'possible_duplicate'`.
3. **No Match**: Set `bucket = 'probable_new_work'`.

### 5. Rewrite Next Actions
Rewrite summaries into imperative "next actions" (≤15 words).
- *Format*: Verb + Object + Context.
- *Example*: "Coordinate w/ Minna on PL superbill response (Mimi asked)"

### 6. Interactive Push (Ask User)
Surface items to the user via `ask_user`:
- Use `multiSelect: true`.
- Header: `Probable new`, `Possible dupe`, or `Def. dupe`.
- Option Label: `For <counterparty>: <next_action>`

### 7. Asana Implementation
For selected items, create/update in Asana:
- **Project**: `1208193100268936` (Founders Backlog).
- **Custom Fields**:
    - Status (Global) [`1207543199556043`]: `1207543199556046` (Backlog)
    - Gmail Thread Id [`1213297635072824`]: `<thread_id>`
- **Effort Estimation**: Estimate Fibonacci score (1, 2, 3, 5, 8, 13, 21) based on scope/ambiguity. Set in Effort field [`1214179053266044`] and post a `:bot: Effort explanation:` story.

## Verification
- Every `potential_work = 'Y'` row should have a `bucket`.
- All survivors (`bucket != 'collapsed'`) should have a `next_action`.
- Report collapse ratio: `count(survivors) / count(total_rows)`.
