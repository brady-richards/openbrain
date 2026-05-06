---
name: gather-work
description: Phase 1 of /orient. Sweep Slack, email, and Messages for potential work over the previous-working-day window and write it to .claude/skills/gather-work/data/current.csv. Stub — to be fleshed out.
---

# /gather-work


## Procedure

## Gather potential work


### Tool budget

This skill is thoroughness-bound, not call-bound. Expect 50–300+ tool calls per run. Do NOT optimize for fewer calls. The only acceptable reason to skip a per-item read is that the item was excluded by an earlier rule (e.g., sender is guides@doromind.com). Terseness applies to your prose, not your tool use.

### Justification

The goal is to find all potential work across all channels (Slack, email, messages), capture it, and refine it. Primary goal: capture work. Secondary goal: don't duplicate work already  tracked in Asana.

### Definitions

“Work” means "something I need to do." Both business and personal requests count.

The “time period” is from the previous working day to today

- Inbound work: A request directed at me. Look for "can you...", "please...", "we need you...", or messages ending with a question mark.
    - In a group of ≤5: any ask is potential work unless it specifically names someone else.
    - In a group of >5: only include if the message @mentions me by handle, or addresses me by name in the text. A general question to the group does not qualify. If unsure, exclude.
- Outbound work: A commitment from me. Look for "I'll", "I will", "let me", "I'll send", "I'll follow up", "I'll get back", "I'll check", "I'll connect", "I'll introduce", "will have this to you", "I'll loop you in", "I'll look into", "sending over shortly", "I'll make sure", "will do".
    - Sending someone a question or request is NOT a commitment. Outbound rows require a self-promise; threads waiting on the other person's reply are excluded.

 ## Forbidden patterns

- Do NOT write "did not read every body", "subjects only", "may resolve differently", "possible follow-through pending", or any equivalent caveat. If you can't verify a row, drop it.
- Do NOT classify from subject lines. Subjects are routing data, not content.
- Do NOT use search-result snippets as your body source — they are truncated and may contain garbage bytes.

 ## Output: CSV row contract

Write all captured work to `.claude/skills/gather-work/data/current.csv` (path relative to the vault root). Create the `data/` directory if it doesn't exist. If `current.csv` already exists, append rows to it; otherwise create it with the header line below as the first row. Do not rewrite or dedupe existing rows in this phase — refinement is `/refine-work`'s job.

Columns, in this order:

```
source_url | received | source_mcp | forum | thread | direction | work_or_personal | counterparty | summary | potential_work | potential_work_reason | acknowledged | acknowledged_reason | done | done_reason
```

- `source_url`: deep link to the original message (Gmail permalink, Slack archive URL, `messages://` or equivalent). Required.
- `received`: ISO-8601 date the message arrived (or was sent, for outbound).
- `source_mcp`: the MCP server slug that produced the row (e.g. `gmail_brady_doromind_com`, `slack_doromind_slack_com`, `messages`).
- `forum`: where it happened — Slack channel name, Slack DM counterparty, email To/Cc list, or "iMessage 1:1" / "iMessage group".
- `thread`: stable thread identifier (Gmail threadId, Slack thread_ts, Messages chat guid). Empty if the message has no thread.
- `direction`: `inbound` or `outbound`.
- `work_or_personal`: `work` or `personal`.
- `counterparty`: the other human (or list, comma-separated) — name preferred, email/handle if no name.
- `summary`: ≤20 words, declarative, no hedging. Captures the ask or commitment.
- `potential_work` / `potential_work_reason`: `Y` or `N`, plus ≤15-word reason. `Y` means it represents an ask directed at me or a self-commitment. `N` means it doesn't (FYI, automated, addressed to someone else, etc.).
- `acknowledged` / `acknowledged_reason`: `Y` or `N`, plus ≤15-word reason. `Y` means I've replied / reacted / otherwise indicated I saw it. Determined by reading later messages from me in the thread.
- `done` / `done_reason`: `Y` or `N`, plus ≤15-word reason. `Y` means the work is fulfilled (answer sent, commitment delivered, ask resolved). Read the rest of the thread to decide.

Rules:
- Every row must come from a body fetched via `read_email` / `get_conversation` / `slack_conversations_replies`. Subjects and search snippets do not qualify as evidence.
- Reasons must cite what was read (e.g. "I replied 14:02 with answer", "no later message from me in thread", "thread continues without my reply").
- Rows missing `summary`, `potential_work_reason`, `acknowledged_reason`, or `done_reason` are invalid.
- Quote any field containing `,`, `|`, `"`, or newlines per RFC 4180 (use `,` as the delimiter — the `|` above is just for readability in this doc). Actual file is comma-separated.

 ## Execution shape

Process each channel in 10-candidate batches:

1. Pull a batch of 10 IDs from the search.
2. Fire all required read_* / get_conversation / slack_conversations_replies calls for the batch in parallel.
3. Write rows for the batch to the CSV.
4. Pull the next 10.

Do not pre-filter by subject or sender display name before reading bodies. The only pre-read filters are exact-sender exclusions (e.g., guides@doromind.com, *-noreply@*, OTP/system senders).

#### Capture per channel

##### Slack — inbound

For each slack_* MCP:

1. Call slack_conversations_unreads with limit: 200. (limit caps channels scanned, not messages — small limits silently miss DMs.)
2. Call slack_my_mentions with hours covering the time period.
3. For each candidate message, call slack_conversations_replies on its thread to fetch (a) the full message text and (b) any subsequent message from me.
4. Apply the inbound definition (group size, addressed-to-me).
5. Read later messages in the thread to fill `acknowledged` and `done`.
6. Write the row.

##### Slack — outbound

For each slack_* MCP:

1. Call slack_conversations_search_messages with from:@me (or workspace equivalent) over the time period.
2. For EACH result, call slack_conversations_replies to fetch the full message and the rest of the thread.
3. From the body, identify commitment language. Subject/preview text does not qualify.
4. Determine fulfillment by reading any later messages from me in the thread.
5. Write the row.

##### Email — inbound

For each gmail_* MCP:

1. Call search_emails with is:unread (is:important OR is:starred) after:<period_start>. Capture all IDs.
2. For EACH id: call read_email(id). You may not classify before this call.
3. From the body, extract: To/Cc list, the literal ask, whether I'm the addressee.
4. Apply exclusion rules: sender is guides@doromind.com (FYI); I'm neither To nor Cc and not mentioned in body; sender is automated (1Password, Stripe, DocuSign, SimpleMDM, LinkedIn
invitations, shipping notifications, marketing).
5. If a subsequent message in the thread is from me, call read_email on it and decide fulfillment. Record in fulfillment_check.
  6. Write the row.

##### Email — outbound

For each gmail_* MCP:

1. Call search_emails with in:sent after:<period_start>. Capture all IDs.
2. For EACH id: call read_email(id). You may not classify before this call.
3. Scan the body for commitment language. A question I sent is NOT a commitment.
4. If later messages exist in the thread (from me or others), call read_email on them to determine fulfillment.
5. Write the row.

##### Messages — inbound

1. Use search_messages with received_only: true
2. date_to is exclusive — pass today + 1 to include today's messages.
3. For EACH candidate (search previews are truncated and contain garbage bytes), call get_conversation(contact, date_from, date_to) before classifying. Read at minimum the candidate message and the next message from me.
4. Exclude: automated/system senders (OTP codes, delivery notifications, appointment reminders), service short-codes, contacts with no saved name that look like businesses.  5. Apply the inbound definition.
6. Write the row.

#### Messages — outbound

1. Use search_messages with sent_only: true and the date_to + 1 rule.
2. For EACH candidate, call get_conversation to read the full message and any subsequent reply.
3. Scan body for commitment language. Unanswered messages without commitment language are NOT outbound work — drop them.
4. Write the row.

### Verification

Before considering the run complete, verify:

- Every row's `summary` and three `*_reason` fields are non-empty and grounded in a body fetched via `read_email` / `get_conversation` / `slack_conversations_replies`.
- Every row has `Y`/`N` (not blank, not other values) in `potential_work`, `acknowledged`, `done`.
- Every row has a non-empty `source_url` and `received` date.
- Total `read_email` calls ≥ total email candidates considered (including excluded).
- Total `get_conversation` calls ≥ total message candidates considered.
- No row's `summary` contains "may", "possibly", "likely", or "appears to".

If any check fails, fix the underlying gap. Do not annotate the gap.

