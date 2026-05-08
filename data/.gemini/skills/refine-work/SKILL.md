---
name: refine-work
description: Phase 2 of the orientation pipeline. Processes current.csv to drop noise, collapse threads, and match items against Asana tasks.
---

# refine-work

Phase 2 of the `/orient` pipeline. It cleans and organizes the raw data captured in Phase 1, linking it to existing Asana tasks or proposing new ones.

## Inputs

- `date` (optional): The target date in `YYYY-MM-DD` format. Defaults to today.

## Procedure

### 1. Drop and Thread-Collapse
- Read `current.csv` from the root directory.
- **Drop:** Ignore rows where `potential_work == N` or `done == Y`.
- **Collapse:** Group remaining rows by `thread`. Use the earliest inbound ask as the representative.
- **Cross-Medium Linking:** Link Slack messages that reference emails (by keyword/counterparty similarity).

### 2. Asana Integration
- **Source of Truth:** Asana is the source of truth for work assigned to Brady.
- **Fetch Tasks:** Use `asana_get_my_tasks` for workspace `1205801040312777`.
- **Match:**
  - **Definite:** Gmail thread ID or Slack permalink matches.
  - **Possible:** Semantic similarity in topic/counterparty.
  - **New:** No match found.

### 3. Interactive Push
- Use `ask_user` to present `probable_new_work` and `possible_duplicate` items to Brady.
- For selected items, create/update Asana tasks in the "Founders Backlog" (`1208193100268936`).

### 4. Fibonacci Effort Estimation
- For incomplete tasks assigned to Brady, estimate effort from `{1, 2, 3, 5, 8, 13, 21}`.
- Use the `Effort` custom field (`1214179053266044`).
- Post an explanation story starting with `:bot: Effort explanation:`.

### 5. Output: refined.csv
Write `refined.csv` to the root directory with the original 15 columns plus:
- `bucket`: `probable_new_work`, `possible_duplicate`, `definite_duplicate`, `done`, `dropped`.
- `asana_gid`: Matched Asana task GID.
- `asana_match_reason`: Signal that drove the match.
- `next_action`: Imperative verb rewrite of the task (e.g., "Reply to Mimi...").

## Verification
- Every row in `current.csv` must be accounted for in `refined.csv`.
- `probable_new_work` must have a `next_action`.
- `definite_duplicate` must have an `asana_gid`.
