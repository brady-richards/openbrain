---
name: gather-work
description: Classify unclassified rows in data/stuff.db to identify potential work, commitments, and status. Use this as Phase 1 of the orientation workflow to process inbound and outbound messages from Slack, Email, and iMessage.
---

# Gather Work

## Overview

This skill identifies "potential work" from messages ingested into `data/stuff.db`. It reads the `body` of unclassified rows and populates columns for `summary`, `potential_work`, `acknowledged`, and `done` based on specific rules for inbound requests and outbound commitments.

## Database Schema

The database lives at `data/stuff.db` and contains the `stuff` table:

```sql
CREATE TABLE stuff (
  url TEXT NOT NULL PRIMARY KEY,
  received TEXT,
  source TEXT,
  forum TEXT,
  thread TEXT,
  direction TEXT,
  work_or_personal TEXT,
  counterparty TEXT,
  body TEXT,
  summary TEXT,
  potential_work TEXT,
  potential_work_reason TEXT,
  acknowledged TEXT,
  acknowledged_reason TEXT,
  done TEXT,
  done_reason TEXT
);
```

## Procedure

Process rows in batches of up to 50.

### 1. Fetch Cohorts

Pick up two types of rows:
- **Unclassified**: `SELECT * FROM stuff WHERE (summary IS NULL OR summary = '') ORDER BY received DESC LIMIT 50;`
- **Ack/Done Refresh**: `SELECT * FROM stuff WHERE potential_work = 'Y' AND (acknowledged = 'N' OR done = 'N') ORDER BY received DESC LIMIT 20;` (Re-evaluate if newer messages in the same conversation exist).

### 2. Classify Each Row

Read the `body` and apply these definitions:

#### Inbound Work (`direction=inbound`)
- **Y**: A request directed at me ("can you...", "please...", ending with ?).
    - Group ≤ 5: Any ask qualifies unless it names someone else.
    - Group > 5: Only qualifies if @mentioned or addressed by name.
- **N**: FYI, automated, addressed to others, no commitment language.

#### Outbound Work (`direction=outbound`)
- **Y**: A commitment from me ("I'll", "I will", "let me", "I'll follow up").
- **N**: Questions I sent without commitment, FYIs.

#### Metadata Columns
- `summary`: ≤ 140 chars. Declarative summary of the ask or commitment.
- `potential_work_reason`: ≤ 15 words. The rule that fired.
- `acknowledged`/`done`: For `potential_work=Y`, check later messages in the same conversation (`thread` or `forum` depending on source). Cite the signal (e.g., "👍 react", "I replied").

### 3. Update Database

Execute updates in a transaction.
```sql
UPDATE stuff SET 
  summary = ?, 
  potential_work = ?, 
  potential_work_reason = ?, 
  acknowledged = ?, 
  acknowledged_reason = ?, 
  done = ?, 
  done_reason = ? 
WHERE url = ?;
```

## Source-Specific Rules

### Slack
- Forum name is channel (>5 people) or DM/MPIM (≤5).
- Body preserves reaction metadata (e.g., `:done:`, `:eyes:`).

### Email
- Check To/Cc list in body headers.
- Ignore automated senders (e.g., `guides@doromind.com`, 1Password, Stripe).

### iMessage
- `forum` is the chat. No real threads; use chronological follow-ups.

## Verification

Run these checks after processing:
- `SELECT COUNT(*) FROM stuff WHERE summary IS NULL AND received >= date('now', '-2 days');` (Should be 0)
- `SELECT COUNT(*) FROM stuff WHERE potential_work = 'Y' AND acknowledged IS NULL;` (Should be 0)
