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

The goal is to find all potential work across all channels (Slack, email, messages). To avoid losing work to over-eager filtering, **every fetched message is recorded as a row in the CSV**. The work-vs-noise judgment moves into the `potential_work` / `potential_work_reason` columns: rows that previously would have been dropped (FYI senders, automated, addressed to someone else, no commitment language) are now written with `potential_work=N` and a reason. Refinement (`/refine-work`) is responsible for filtering down to actionable rows.

### Definitions

“Work” means "something I need to do." Both business and personal requests count. These definitions drive the `potential_work` Y/N decision for each row — they no longer drive whether the row is written at all.

The “time period” is from the previous working day to today.

- **Inbound work** (`direction=inbound`, `potential_work=Y`): A request directed at me. Look for "can you...", "please...", "we need you...", or messages ending with a question mark.
    - In a group of ≤5: any ask qualifies unless it specifically names someone else.
    - In a group of >5: only qualifies if the message @mentions me by handle, or addresses me by name in the text. A general question to the group does not qualify.
- **Outbound work** (`direction=outbound`, `potential_work=Y`): A commitment from me. Look for "I'll", "I will", "let me", "I'll send", "I'll follow up", "I'll get back", "I'll check", "I'll connect", "I'll introduce", "will have this to you", "I'll loop you in", "I'll look into", "sending over shortly", "I'll make sure", "will do".
    - A question I sent is NOT a commitment.
- **Not work** (`potential_work=N`): everything else — FYI/announcements, automated/system senders (1Password, Stripe, DocuSign, SimpleMDM, LinkedIn invites, shipping, marketing, OTP codes, delivery notifications), CC-only or list traffic where I'm not addressed, group asks naming someone else, my own questions/requests without commitment language, observer-only threads. Set `potential_work=N` and put the rule that fired into `potential_work_reason`.

 ## Forbidden patterns

- Do NOT drop a fetched message because it looks like noise. Write the row with `potential_work=N` and a reason instead.
- Do NOT classify from subject lines. Subjects are routing data, not content.
- Do NOT use search-result snippets as your body source — they are truncated and may contain garbage bytes.
- Do NOT write hedging caveats ("may resolve differently", "possible follow-through pending") into reason fields. State the rule that fired.

 ## Output: CSV row contract

Write all captured work to `.claude/skills/gather-work/data/current.csv` (path relative to the vault root). Create the `data/` directory if it doesn't exist. If `current.csv` already exists, append rows to it; otherwise create it with the header line below as the first row. Do not rewrite or dedupe existing rows in this phase — refinement is `/refine-work`'s job.

Columns, in this order:

```
source_url | received | source_mcp | forum | thread | direction | work_or_personal | counterparty | summary | potential_work | potential_work_reason | acknowledged | acknowledged_reason | done | done_reason
```

- `source_url`: deep link to the original message (Gmail permalink, Slack archive URL, `messages://` or equivalent). Required.
- `received`: ISO-8601 date the message arrived (or was sent, for outbound).
- `source_mcp`: the MCP server slug that produced the row (e.g. `gmail_brady_doromind_com`, `slack_doromind_slack_com`, `messages`).
- `forum`: where it happened.
    - **Email inbound:** the receiving mailbox — the Brady-owned address the message landed in (the Gmail account being searched). For cc/bcc deliveries, still use the receiving mailbox, not the To: header.
    - **Email outbound:** the From: address (the address Brady sent from).
    - **Slack channel:** channel name (e.g. `proj-licensing`).
    - **Slack DM/MPIM:** the counterparty's resolved Slack handle or display name (call `slack_users_search` to map user IDs to names — never write the raw `U…` user ID or `D…` channel ID).
    - **iMessage:** `iMessage 1:1` or `iMessage group: <name>`.
- `thread`: stable thread identifier (Gmail threadId, Slack thread_ts, Messages chat guid). Empty if the message has no thread.
- `direction`: `inbound` or `outbound`.
- `work_or_personal`: `work` or `personal`.
- `counterparty`: the other human (or list, comma-separated) — name preferred, email/handle if no name.
- `summary`: ≤20 words, declarative, no hedging. Captures the ask or commitment.
- `potential_work` / `potential_work_reason`: `Y` or `N`, plus ≤15-word reason. `Y` means it represents an ask directed at me or a self-commitment. `N` means it doesn't (FYI, automated, addressed to someone else, etc.).
- `acknowledged` / `acknowledged_reason`: `Y` or `N`, plus ≤15-word reason. `Y` if I've replied in the thread, OR reacted on Slack with a positive emoji (👍 `:thumbsup:` / `:+1:`, ❤️ `:heart:`, ✅ `:white_check_mark:`, `:eyes:`, `:ok:`, or any "yes"-shaped emoji), OR sent a tapback on iMessage that reads as affirmative (Liked, Loved, "Yes" — Disliked / "?" / Laughed do NOT count as ack). For email, only a reply counts (no reactions to inspect). Cite the signal in the reason ("👍 react from me 14:02", "I replied 09:11", "Loved tapback").
- `done` / `done_reason`: `Y` or `N`, plus ≤15-word reason. `Y` means the work is fulfilled — answer sent, commitment delivered, ask resolved. On Slack: a `:done:` reaction on the message counts as fulfillment, AND a later thread message (from me or the counterparty) saying "done", "shipped", "fixed", "merged", "resolved", "thanks!", "got it, all set", or equivalent counts. Other reactions (👍/❤️/etc.) do NOT count as done — only as ack. Cite the signal in the reason ("`:done:` react from me", "counterparty said 'shipped' 15:40").

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

Do not pre-filter by subject or sender display name before reading bodies. Every fetched message becomes a row — exclusions go into `potential_work=N` with a reason, not into a skip list.

#### Capture per channel

##### Slack — inbound

For each slack_* MCP:

1. Call slack_conversations_unreads with limit: 200. (limit caps channels scanned, not messages — small limits silently miss DMs.)
2. Call slack_my_mentions with hours covering the time period.
3. For each candidate message, call slack_conversations_replies on its thread to fetch the full message text, any subsequent messages, AND the reactions array on the original message.
4. Apply the inbound definition to set `potential_work` (Y/N + reason): group size, @mention, addressed-by-name. Group asks naming someone else → `N`.
5. Fill `acknowledged`: `Y` if I posted a reply in the thread OR my user id appears in any positive reaction (👍/❤️/✅/eyes/ok/yes-shaped). Fill `done`: `Y` if the message has a `:done:` reaction OR a later thread message (mine or counterparty's) signals fulfillment ("done", "shipped", "fixed", "merged", "resolved", "thanks!", etc.). Other reactions are not done.
6. Write the row regardless of `potential_work` value.

##### Slack — outbound

For each slack_* MCP:

1. Call slack_conversations_search_messages with from:@me (or workspace equivalent) over the time period.
2. For EACH result, call slack_conversations_replies to fetch the full message and the rest of the thread.
3. From the body, identify commitment language. Subject/preview text does not qualify. Set `potential_work=Y` if a self-promise is present, else `N` (e.g. "question, no commitment").
4. Fill `acknowledged` from later thread messages from me OR my reaction on the original. Fill `done` only from later messages signalling fulfillment.
5. Write the row regardless of `potential_work` value.

##### Email — inbound

For each gmail_* MCP:

1. Call search_emails with is:unread (is:important OR is:starred) after:<period_start>. Capture all IDs.
2. For EACH id: call read_email(id). You may not classify before this call.
3. From the body, extract: To/Cc list, the literal ask, whether I'm the addressee.
4. Set `potential_work` Y/N + reason. `N` reasons include: sender is guides@doromind.com (FYI); I'm neither To nor Cc and not mentioned in body; sender is automated (1Password, Stripe, DocuSign, SimpleMDM, LinkedIn invitations, shipping, marketing); no actionable ask.
5. If a subsequent message in the thread is from me, call read_email on it and use it to fill `acknowledged` and `done`.
6. Write the row regardless of `potential_work` value.

##### Email — outbound

For each gmail_* MCP:

1. Call search_emails with in:sent after:<period_start>. Capture all IDs.
2. For EACH id: call read_email(id). You may not classify before this call.
3. Scan the body for commitment language. Set `potential_work=Y` if a self-promise is present; `N` otherwise (e.g. "question, no commitment", "FYI to recipient").
4. If later messages exist in the thread, call read_email on them to fill `acknowledged` and `done`.
5. Write the row regardless of `potential_work` value.

##### Messages — inbound

1. Use search_messages with received_only: true.
2. date_to is exclusive — pass today + 1 to include today's messages.
3. For EACH candidate (search previews are truncated and contain garbage bytes), call get_conversation(contact, date_from, date_to) before classifying. Read at minimum the candidate message and the next message from me. Use `get_reactions` on the candidate message to capture tapbacks.
4. Set `potential_work` Y/N + reason. `N` reasons include: automated/system senders (OTP codes, delivery notifications, appointment reminders), service short-codes, business contacts with no saved name, no ask directed at me. Apply the inbound definition for `Y`.
5. Fill `acknowledged` from later iMessages from me in the thread OR an affirmative tapback (Liked/Loved/Yes) on the candidate message. Disliked, "?", or Laughed do NOT ack. Fill `done` only from later messages signalling fulfillment.
6. Write the row regardless of `potential_work` value.

#### Messages — outbound

1. Use search_messages with sent_only: true and the date_to + 1 rule.
2. For EACH candidate, call get_conversation to read the full message and any subsequent reply.
3. Scan body for commitment language. Set `potential_work=Y` if a self-promise is present; `N` otherwise (e.g. "unanswered question, no commitment").
4. Read later messages to fill `acknowledged` and `done`.
5. Write the row regardless of `potential_work` value.

### Verification

Before considering the run complete, verify:

- Every row's `summary` and three `*_reason` fields are non-empty and grounded in a body fetched via `read_email` / `get_conversation` / `slack_conversations_replies`.
- Every row has `Y`/`N` (not blank, not other values) in `potential_work`, `acknowledged`, `done`.
- Every row has a non-empty `source_url` and `received` date.
- Total `read_email` calls ≥ total email candidates considered (including excluded).
- Total `get_conversation` calls ≥ total message candidates considered.
- No row's `summary` contains "may", "possibly", "likely", or "appears to".

If any check fails, fix the underlying gap. Do not annotate the gap.

