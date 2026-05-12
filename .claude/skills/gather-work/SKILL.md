---
name: gather-work
description: Phase 1 of /orient. Read unclassified rows from data/stuff.db and fill in summary + work/ack/done classification columns. Stub — to be fleshed out.
---

# /gather-work

## Procedure

## Classify potential work

### Tool budget

This skill is thoroughness-bound, not call-bound. Expect one read + one update per unclassified row, batched. Do NOT optimize for fewer calls. The only acceptable reason to skip a row is that all classification columns are already populated (see "Refetch rule" below).

### Justification

Messages from Slack, email, and iMessage are ingested into `data/stuff.db` by an upstream process. This skill does not pull from those sources. Its job is to read each row's `body` and fill the classification columns (`summary`, `potential_work`, `potential_work_reason`, `acknowledged`, `acknowledged_reason`, `done`, `done_reason`) by applying the rules below.

To avoid losing work to over-eager filtering, **every row gets classified** — rows that would have been dropped (FYI senders, automated, addressed to someone else, no commitment language) are written with `potential_work=N` and a reason. Refinement (`/refine-work`) is responsible for filtering down to actionable rows.

### Definitions

"Work" means "something I need to do." Both business and personal requests count. These definitions drive the `potential_work` Y/N decision for each row.

The "time period" — the slice of rows to classify — is from the previous working day to today, inferred from the `received` column.

- **Inbound work** (`direction=inbound`, `potential_work=Y`): A request directed at me. Look for "can you...", "please...", "we need you...", or messages ending with a question mark.
    - In a group of ≤5 (forum is a small DM/MPIM/group thread): any ask qualifies unless it specifically names someone else.
    - In a group of >5 (channel, large group chat, mailing list): only qualifies if the message @mentions me by handle, or addresses me by name in the body.
- **Outbound work** (`direction=outbound`, `potential_work=Y`): A commitment from me. Look for "I'll", "I will", "let me", "I'll send", "I'll follow up", "I'll get back", "I'll check", "I'll connect", "I'll introduce", "will have this to you", "I'll loop you in", "I'll look into", "sending over shortly", "I'll make sure", "will do".
    - A question I sent is NOT a commitment.
- **Not work** (`potential_work=N`): everything else — FYI/announcements, automated/system senders (1Password, Stripe, DocuSign, SimpleMDM, LinkedIn invites, shipping, marketing, OTP codes, delivery notifications), CC-only or list traffic where I'm not addressed, group asks naming someone else, my own questions/requests without commitment language, observer-only threads. Set `potential_work=N` and put the rule that fired into `potential_work_reason`.

## Forbidden patterns

- Do NOT skip a row because the body looks like noise. Update it with `potential_work=N` and a reason.
- Do NOT classify from `forum` or `counterparty` alone — those are routing data, not content. Read the `body`.
- Do NOT write hedging caveats ("may resolve differently", "possible follow-through pending") into reason fields. State the rule that fired.

## Database contract

The database lives at `data/stuff.db` (path relative to the vault root) and contains one table:

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

Columns `url`, `received`, `source`, `forum`, `thread`, `direction`, `work_or_personal`, `counterparty`, and `body` are populated by the upstream ingestion process. **Do not modify them.** This skill only writes to:

- `summary`: ≤140 characters, declarative, no hedging. Captures the ask, commitment, or — for `potential_work=N` — what the message actually is. If the body is shorter than 140 characters and already declarative, copy it verbatim.
- `potential_work` / `potential_work_reason`: `Y` or `N`, plus ≤15-word reason. `Y` means the body represents an ask directed at me or a self-commitment from me. `N` means it doesn't (FYI, automated, addressed to someone else, etc.).
- `acknowledged` / `acknowledged_reason`: `Y` or `N`, plus ≤15-word reason. Only meaningful when `potential_work=Y`. `Y` if the thread shows I've acknowledged — replied in-thread, reacted on Slack with a positive emoji (👍 `:thumbsup:` / `:+1:`, ❤️ `:heart:`, ✅ `:white_check_mark:`, `:eyes:`, `:ok:`, or any "yes"-shaped emoji), or sent an affirmative tapback on iMessage (Liked, Loved, "Yes" — Disliked / "?" / Laughed do NOT count). Cite the signal in the reason ("👍 react from me 14:02", "I replied 09:11", "Loved tapback").
- `done` / `done_reason`: `Y` or `N`, plus ≤15-word reason. Only meaningful when `potential_work=Y`. `Y` if the work is fulfilled — answer sent, commitment delivered, ask resolved. On Slack: a `:done:` reaction on the message counts as fulfillment, AND a later thread message saying "done", "shipped", "fixed", "merged", "resolved", "thanks!", "got it, all set", or equivalent counts. Other reactions (👍/❤️/etc.) do NOT count as done — only as ack. Cite the signal in the reason.

Acknowledgement and done signals must come from later rows in `stuff` that are in the same conversation as the row being classified — see "What counts as a follow-up" under the Reclassification rule for what qualifies per source. If no qualifying follow-up row exists yet, set `acknowledged=N` / `done=N` with reason "no later message in conversation".

Rules:
- Every row's classification must come from the `body` actually read.
- **Reclassification rule:** `summary` and `potential_work` / `potential_work_reason` come from the row's own `body` and never change once set — bodies are immutable across all sources. `acknowledged` and `done`, however, depend on later messages in the same conversation and may flip from `N` to `Y` as the conversation continues. Re-evaluate ack/done on any `potential_work=Y` row when a newer row exists in `stuff` that is plausibly in reply to it (see "What counts as a follow-up" below) whose `received` is later than the last time this row was classified. For Slack, reactions on the original message can also change ack/done if the ingester refreshes the row's `body` (or stores reaction metadata in a related row); refresh accordingly. Gmail rows have no reactions, so only later same-thread rows matter. Select unprocessed rows with: any of (`summary`, `potential_work`) NULL/empty, OR `potential_work='Y'` with at least one qualifying follow-up row received after this row's last update.

- **What counts as a follow-up** (for ack/done evaluation) depends on the source:
    - **Email:** same `thread` only. Gmail threadIds are reliable; same-`forum` (mailbox) is far too broad.
    - **Slack thread reply:** same `thread`. Most ack/done signals live here.
    - **Slack top-level reply in channel/DM:** same `forum` AND empty/different `thread`, from the counterparty (or me, for outbound rows), received within ~24h of the original. Slack users often reply un-threaded, especially in 1:1 DMs.
    - **iMessage:** same `forum` from the counterparty (or me, for outbound). iMessage has no real thread concept beyond the conversation itself, so `thread` is usually empty and `forum` (the chat) is the conversation.
- Reasons must cite what was read (e.g. "I replied 14:02 with answer", "no later message from me in thread", "thread continues without my reply").
- **If `potential_work=N`, write `acknowledged`, `acknowledged_reason`, `done`, and `done_reason` as empty strings.** Those columns are only meaningful for actual work; spending fields on "is the FYI broadcast acknowledged" is noise.
- Rows missing `summary`, `potential_work`, or `potential_work_reason` after this skill runs are invalid. For `potential_work=Y` rows, `acknowledged` / `done` (Y/N) and their reasons are also required.

## Execution shape

Process in batches of 50 rows:

1. Pick up two cohorts:
   - **Unclassified:** `SELECT … FROM stuff WHERE summary IS NULL OR summary = '' OR potential_work IS NULL OR potential_work = '' ORDER BY received DESC LIMIT 50;`
   - **Ack/done refresh:** `potential_work='Y'` rows that have a newer same-thread row in `stuff` than they did last classification. The `body`-derived `summary` and `potential_work` stay; only `acknowledged*` / `done*` get rewritten.
2. For each row, read the `body` and apply the rules below to derive the classification fields.
3. For each row needing follow-up context (any `potential_work=Y` candidate), pull later same-conversation rows per the "What counts as a follow-up" rules above. Roughly:
   - Email: `WHERE thread = ? AND received > ?`
   - Slack: `WHERE (thread = ? OR (forum = ? AND received BETWEEN ? AND datetime(?, '+1 day'))) AND received > ?`
   - iMessage: `WHERE forum = ? AND received > ?`
   Order ascending by `received` and read the first one or two from the counterparty (or me, for outbound) to derive `acknowledged` and `done`.
4. `UPDATE stuff SET summary = ?, potential_work = ?, potential_work_reason = ?, acknowledged = ?, acknowledged_reason = ?, done = ?, done_reason = ? WHERE url = ?` — one statement per row, run inside a single transaction per batch.
5. Pull the next batch.

Do not pre-filter by `forum` or `counterparty` before reading bodies. Every row in the unclassified set gets updated — exclusions go into `potential_work=N` with a reason.

#### Per-source classification notes

##### Slack (source starts with `slack_`)

1. Determine group size from `forum`: a channel name (`forum` not a person handle) implies >5; a 1:1 DM implies 2; an MPIM may be inferred from the `counterparty` list length. When in doubt, treat as >5 and require @mention or by-name addressing.
2. For inbound rows, apply the inbound definition. Group asks naming someone else → `N`.
3. For outbound rows, scan body for commitment language (see Definitions). Questions are not commitments.
4. For ack/done, look at later same-thread rows in `stuff`. The `body` column for Slack rows preserves reaction metadata if the ingestion process recorded it; if reactions are not in the body, fall back to looking for explicit ack/done text in later thread messages.

##### Email (source starts with `gmail_`)

1. From the `body`, extract: To/Cc list (often present in quoted headers when the body is a reply chain), the literal ask, whether I'm the addressee.
2. Set `potential_work` Y/N + reason. `N` reasons include: sender is `guides@doromind.com` (FYI per memory rule); I'm neither To nor Cc and not mentioned in body; sender is automated (1Password, Stripe, DocuSign, SimpleMDM, LinkedIn invitations, shipping, marketing, calendar invites without an embedded ask); no actionable ask.
3. For outbound rows, scan the most recent message segment of the body (the un-quoted top portion) for commitment language. `N` reasons include: question with no commitment, FYI to recipient, automated forward via shared alias.
4. For ack/done on inbound rows, look for a later same-thread row with `direction=outbound` (my reply). For outbound rows, look for a later same-thread row from the counterparty signaling fulfillment.

##### iMessage (source = `messages`)

1. Determine group size from `forum`: `iMessage 1:1` = 2, `iMessage group: <name>` = >2 (treat ≤5 as small unless the group has a known large membership).
2. Apply inbound/outbound definitions normally.
3. For ack/done, look at later same-thread rows. Tapback metadata, if recorded by the ingestion process, will appear in the `body` of a synthetic later row or as a marker in the candidate row's body — follow whatever convention the ingester uses; if there is no signal, set ack/done to `N` with reason "no later message in thread".

### Verification

Before considering the run complete, verify with SQL:

```sql
-- All targeted rows have summary + classification
SELECT COUNT(*) FROM stuff
WHERE (summary IS NULL OR summary = ''
       OR potential_work IS NULL OR potential_work = ''
       OR potential_work_reason IS NULL OR potential_work_reason = '')
  AND received >= '<period_start>';
-- Expected: 0

-- Every potential_work=Y row has ack/done
SELECT COUNT(*) FROM stuff
WHERE potential_work = 'Y'
  AND (acknowledged NOT IN ('Y','N') OR done NOT IN ('Y','N')
       OR acknowledged_reason IS NULL OR acknowledged_reason = ''
       OR done_reason IS NULL OR done_reason = '')
  AND received >= '<period_start>';
-- Expected: 0

-- No hedging language in summaries
SELECT url FROM stuff
WHERE summary LIKE '%may %' OR summary LIKE '%possibly%'
   OR summary LIKE '%likely%' OR summary LIKE '%appears to%';
-- Expected: 0 rows

-- Summary length cap
SELECT url, length(summary) FROM stuff WHERE length(summary) > 140;
-- Expected: 0 rows
```

If any check fails, fix the underlying gap. Do not annotate the gap.
