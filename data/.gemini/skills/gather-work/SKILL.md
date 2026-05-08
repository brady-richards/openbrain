---
name: gather-work
description: Phase 1 of the orientation pipeline. Enriches stuff.db with work classifications and exports them to current.csv.
---

# gather-work

Phase 1 of the `/orient` pipeline. It processes unclassified messages in the `stuff.db` database and exports the classified set for the target date.

## Inputs

- `date` (optional): The target date in `YYYY-MM-DD` format. Defaults to today.

## Procedure

### 1. Resolve Time Period
- The search window is from the previous working day to the target `$DATE`.

### 2. Identify and Classify (The Sweep)
**Goal:** Fill in missing classifications and synchronize thread/forum states in the database.

**Source:** `stuff.db` (Table: `stuff`)

#### Classification Workflow
1.  **Query Unclassified:** Select records where `received` is within the search window AND `potential_work` IS NULL.
2.  **Contextual Analysis (Bidirectional):**
    - **Look-Ahead:** Query **subsequent** messages in the same `thread` (or same `forum` if no thread exists) to determine if this message was later acknowledged or done.
    - **Look-Back (State Fulfillment):** If the current message signals acknowledgment (e.g., "👍", "ok") or completion (e.g., "done", "shipped", "✅"):
        - Identify the **most recent preceding work item** (`potential_work == Y`) in the same `thread`.
        - If no `thread` exists, look for the most recent preceding work item in the same `forum` (within a reasonable 24-48h window).
3.  **Analyze & Classify:** Determine states for the current message AND required updates for previous context.
4.  **Update Database:** 
    - `UPDATE` the current record with its classification.
    - `UPDATE` historical records if the current message fulfills or acknowledges them.

#### Definitions
- **Work:** "Something I need to do." (Business or Personal).
- **Inbound Work:** A request directed at you ("can you...", "please...", mentions in groups).
- **Outbound Work:** A commitment from you ("I'll", "I will", "let me").
- **Not Work:** FYI, automated system messages, CC-only, list traffic where you aren't addressed.

### 3. Classification Guidance
When updating a record, fill the following fields:
- `summary`: **(MANDATORY)** A concise one-sentence summary. **CRITICAL:** The summary must NEVER be longer than the original `body`.
- `potential_work`: `Y` if it meets the Work definition, `N` otherwise.
- `potential_work_reason`: Grounded explanation for the classification.

#### Conditional Fields (Informed by Context)
- If `potential_work == Y`:
    - `acknowledged`: `Y` if a later message in the thread/forum (including look-ahead) shows a reply or affirmative reaction.
    - `done`: `Y` if a later message/reaction in the thread/forum signals completion.
- **Fulfillment Rule:** If a message like "done" or a checkmark reaction is found, it "completes" the most relevant preceding ask in that channel/thread. Update that historical record to `done=Y`.

### 4. Output: CSV Row Contract
After classification and synchronization, query **ALL** records for the search window from `stuff.db` and write them to `current.csv`.

**Columns (Comma-Separated):**
`source_url`, `received`, `source_mcp`, `forum`, `thread`, `direction`, `work_or_personal`, `counterparty`, `summary`, `potential_work`, `potential_work_reason`, `acknowledged`, `acknowledged_reason`, `done`, `done_reason`

### 5. Execution Shape
- Process messages in batches of 10-20.
- Execute database updates immediately.

## Verification
- Every `summary` is shorter than or equal to its `body`.
- Acknowledgment and completion signals are mapped to the correct preceding asks, even without explicit threading.
- Historical records in `stuff.db` reflect fulfillment from new interactions.
