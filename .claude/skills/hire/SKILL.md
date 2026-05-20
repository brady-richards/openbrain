# /hire

Execute the Doro Mind offer process for a new hire. Picks up immediately after verbal acceptance. Orchestrates Drive, eSignature, the equity spreadsheet, and the Asana onboarding template.

## Input

- `$*` — candidate name plus any known offer terms, e.g.:
  `/hire Kate Douglas — title: Care Coordinator, salary: $62,000, start: 2026-05-12, equity: 0.05%, type: W-2`

Parse `$*` into:
- **name** (required)
- **title** (optional — look up from context if missing)
- **salary** (optional)
- **start_date** (optional)
- **equity_pct** (optional — signals equity component)
- **type** — `W-2` (default) or `1099`
- **personal_email** (optional — look up if missing)

## Offer process (source of truth)

The authoritative process lives at:
> [Onboarding — Offers section](https://docs.google.com/document/d/1L8tlXAUYMBnvi46vaZFWXAtotM8sASjZR0GyqI11Bsc/edit)

The markdown version of the process is reproduced below for reference; the skill executes it step-by-step.

---

### Offer process (markdown)

**Policy:** minimize time from joining to traction. Show don't tell, reveal progressively, don't repeat yourself, plain language, respect privacy.

**Offers** (picks up after verbal acceptance):

1. Obtain the new employee's **preferred personal email address** (needed before @doromind.com is provisioned).
2. Find or create a folder in [Employment Offers & Engagements](https://drive.google.com/drive/folders/1oQRqX4bAt_HvDkOd_hUC8YbJK1t_f1d-) named after the new employee.
3. Go to [Contract Templates](https://drive.google.com/drive/folders/1702O7tprYUOZSECU9m1a8UZNKvSK6-Nm), copy either the W-2 (employment) or 1099 (consulting) agreement into the employee's folder. Clinicians typically get two agreements (hourly + equity).
4. Use **Tools → Variables** to fill in all variable fields in the contract.
5. If there is an equity component, record it in [Doro Mind Option Stock Grants](https://docs.google.com/spreadsheets/d/1bI8Lo69cXOM72p1EXnWlY-EMteYT2Zzg5oUfCyFZHwc/edit) with status **Offered**. The "Reference %" column translates percentage-based offers to share counts.
6. Send via **Tools → eSignature** — routes to the employee and Brady to sign.
7. Once both sides have signed, file the executed contract in the employee's folder.

**Post-Offer:**

8. In Asana, open the onboarding project and apply the **"[New Hire] Pre-prep"** task template for this employee. Have the executed agreement in hand — it contains the details needed for subsequent steps.

---

## Procedure

> **Parallelization:** steps 1–2 (context gather) are independent reads — fan them out in a single tool-use block.

### 1. Parse offer terms

Extract all fields from `$*`. If **name** is missing, stop and ask. For any other missing field that can be looked up (personal email, title, salary), proceed to step 2 and resolve it from context.

### 2. Gather context (parallel)

Fan out simultaneously:

**2a. Gmail search** — search `mcp__gmail_brady_doromind_com__search_emails` for the candidate name + any known email. Look for:
- Prior correspondence containing personal email address
- Any offer letter drafts already in flight
- Signed NDA or background check threads

**2b. Slack search** — `mcp__slack_doromind_slack_com__conversations_search_messages` for the candidate name. Look for:
- Hiring channel discussion of this candidate
- Agreed terms (title, salary, start date, equity)
- Any pending blockers

**2c. Asana search** — `mcp__asana_work__asana_search_tasks` for the candidate name across the work workspace. Look for:
- Existing hiring funnel task (may contain agreed terms in notes/comments)
- Any onboarding tasks already created (check for duplicate before proceeding)

**2d. Google Calendar** — search `mcp__google_brady_doromind_com__calendar_search_events` for the candidate name. Attendee email addresses on past events are often the fastest way to find a personal/contact email.

**2e. People vault** — grep `+ Atlas/People/` for a note matching the candidate name. If found, read it for `emails`, `relationship`, and open commitments.

### 3. Resolve missing fields

After the parallel gather, fill in any fields still missing:

- **personal_email**: extract from Gmail thread, Slack, or Asana task notes. If still not found, surface it as a blocker — do not proceed to step 4 without it.
- **title / salary / start_date**: pull from Asana task notes or Slack hiring channel. If still ambiguous, surface and ask before continuing.
- **type** (W-2 vs 1099): default W-2 unless context says otherwise.
- **equity_pct**: if mentioned anywhere in context, confirm the value. If not mentioned, assume no equity component.

Present a summary of resolved terms to the user and confirm before proceeding:

> **Resolved offer terms for [Name]:**
> - Personal email: …
> - Title: …
> - Salary: …
> - Start date: …
> - Type: W-2 / 1099
> - Equity: X% / none
>
> Proceed?

### 4. Drive — find or create employee folder

Using `mcp__gdrive_brady_doromind_com__searchDriveFiles`, search inside the Employment Offers & Engagements folder (`1oQRqX4bAt_HvDkOd_hUC8YbJK1t_f1d-`) for a folder named after the employee.

- If found: note the folder ID.
- If not found: create it with `mcp__gdrive_brady_doromind_com__createFolder` inside that parent.

### 5. Drive — copy contract template

In the Contract Templates folder (`1702O7tprYUOZSECU9m1a8UZNKvSK6-Nm`), find the correct template. Known templates as of 2026-05-20:
- **Employment Agreement** (W-2) — id `1iIE-i8KTKmtf65jfF9u-yuoYioQ8efcCW8NOKCOYLHA`
- **Consulting Agreement** (1099 generic) — id `1xNQi6wJnx2PYOU9TnvPB2ETxphUS1XbXFbuLxhwMKMI`
- **Advisory Agreement** (advisors, equity-only) — id `1E3LPnxZAdxj20fn0KNQFCaj3Dq7D2U8WAdhM9o6Lhbs`
- **Nurse Practitioner Independent Contractor Agreement** (clinicians) — id `1OZcatJWZImGCZXvqD4sh2aiiWk8S7QNusTPsFet30X4`
- **Medical Director Agreement** — id `1h6ov7o7Bzxp1HVSlVx37pg1o0pIKw9gNG0ziJ0hiFqo`

Choose by title:
- Advisor → Advisory Agreement
- W-2 employee → Employment Agreement
- 1099 consultant → Consulting Agreement
- Clinician → Nurse Practitioner Independent Contractor Agreement (+ equity agreement if applicable)

Use `mcp__gdrive_brady_doromind_com__copyFile` to copy the template(s) into the employee's folder. Name each copy: `[Employee Name] — [Agreement Type] Agreement`.

### 6. Draft — fill in variables

Templates use the **`{{Placeholder Name|default value}}`** convention (the `|default` is optional). Read the copied contract with `mcp__google_brady_doromind_com__docs_read_document` (format=text), then grep the content for `\{\{[^}]+\}\}` to inventory placeholders.

For each placeholder, use `mcp__google_brady_doromind_com__docs_find_and_replace` (match the **full literal**, including the default if present):
- **If you have a confident value**: replace `{{X|default}}` (or `{{X}}`) with the actual value.
- **If you don't have a value but a default exists**: replace `{{X|default}}` → `default` to keep the default text and remove the braces.
- **If you don't have a value and no default exists**: leave the placeholder in the doc and flag it in the final report — do not guess substantive terms.

#### Known placeholders + default fill logic

| Placeholder | Strategy |
|---|---|
| `{{Advisor Name}}` / `{{Employee Name}}` | Resolved full legal name |
| `{{Company Description\|...}}` | Keep default |
| `{{Company Name\|...}}` | Keep default |
| `{{Supervisor\|Co-CEO}}` | Keep default |
| `{{Expense Approver}}` | Mirror Supervisor (`Co-CEO`) unless otherwise specified |
| `{{Pre-Approved Expenses\|None.}}` | Keep default |
| `{{Termination Period\|...}}` | Keep default |
| `{{Time to Cure Breach\|...}}` | Keep default |
| `{{Time Commitment}}` | Compose from term + hours (e.g. "Advisor will commit approximately fifty (50) hours over the six (6) month term of this Agreement.") |
| `{{Title}}` | Resolved title (employment / NP agreements) |
| `{{Salary}}` / `{{Rate}}` | Resolved compensation (employment / consulting) |
| `{{Start Date}}` | Resolved start date |
| `{{Equity}}` / `{{Shares}}` | Equity if applicable |
| `{{Personal Email}}` | Personal email |
| **`{{Compensation Terms}}`** | **Leave for user** — Exhibit B / equity share count needs the current FD share count and vesting schedule |
| **`{{Services To Be Provided}}`** | **Leave for user** — Exhibit A scope is substantive, don't draft |

Report back any placeholders left unfilled so the user can complete them before eSignature.

#### Equity snippet insertion (if equity component)

Equity terms aren't part of the base contract template — they're maintained as separate snippet docs in [Equity Agreement Snippets](https://drive.google.com/drive/folders/1tdDFKn2BxJg8kgwOekgHvuBGuo1LbXHe) (folder id `1tdDFKn2BxJg8kgwOekgHvuBGuo1LbXHe`).

When `equity_pct` is set:

1. **List the snippet folder** via `drive_list_folder_contents` and pick the snippet that matches the engagement type (e.g. advisor equity grant vs employee equity grant). If you can't tell which to use, surface and ask before continuing.
2. **Read the snippet** via `docs_read_document`.
3. **Insert into the contract's Compensation section, *after* any cash compensation paragraphs.** The Compensation section is typically Exhibit B or the "Fees" / "Compensation" section in the body — locate it by section heading.
4. Carry placeholders forward: the snippet may use the same `{{Placeholder|default}}` convention. After insertion, re-run the placeholder grep on the contract and fill new placeholders per the table above.
5. If the contract has no Compensation section yet (or the snippet supplies the whole section), append the snippet at the end of the Fees paragraph or as a new Exhibit B.

Note in the final report which snippet was inserted and at what location.

### 7. Equity spreadsheet (if applicable)

If equity_pct is set, open [Doro Mind Option Stock Grants](https://docs.google.com/spreadsheets/d/1bI8Lo69cXOM72p1EXnWlY-EMteYT2Zzg5oUfCyFZHwc/edit) (spreadsheetId `1bI8Lo69cXOM72p1EXnWlY-EMteYT2Zzg5oUfCyFZHwc`, `Grants` tab, sheetId `467999115`).

**Do NOT use `sheets_append_rows`** — it scans for table boundaries and can place rows far below the actual data when validation/formatting extends down. Also loses chip rendering on Status (col A) and Agreement (col N) because new rows don't inherit column data validation. Use the **duplicate-and-overwrite** pattern instead:

1. **Find last data row** via `sheets_read` on `Grants!B:B` (Name column) — last non-empty index = `N`. New row = `N+1`.
2. **Read formulas** in row `N` via `sheets_read` with `valueRenderOption=FORMULA` so you know which columns are formula-driven (currently G `# of Stock Options` and K `Ownership` are formulas). Note row `N`'s G formula — if it's hardcoded (e.g. an older row), use the canonical formula instead: `=IF(F<row>="","",ROUND(F<row>*'Outstanding Shares'!$B$5,-2))`.
3. **Copy row N → row N+1** via `sheets_copy_range` (`sheetId=467999115`, `sourceStartRow=N-1`, `sourceEndRow=N`, `destStartRow=N`, `pasteType=PASTE_NORMAL`). This inherits chips, data validation, and adjusts relative formulas.
4. **Overwrite with the new hire's values** via `sheets_batch_write` (USER_ENTERED), **skipping K** (let the copied Ownership formula stay) and re-asserting the canonical G formula for the new row. Columns to write:

| Col | Field | Value |
|---|---|---|
| A | Status | `Proposed` (or `Offered` if past board approval) |
| B | Name | Full legal name |
| C | Personal Email | resolved personal email |
| D | State of Residence | resolved state, or `""` |
| E | ISO or NSO? | **leave blank** — counsel decides |
| F | Reference % | e.g. `0.025%` (USER_ENTERED parses to decimal) |
| G | # of Stock Options | formula: `=IF(F<row>="","",ROUND(F<row>*'Outstanding Shares'!$B$5,-2))` |
| H, I, J | Pool Impact / New Policy / Advantage | `""` (clear inherited) |
| K | Ownership | **skip** — preserve copied formula `=G<row>/'Outstanding Shares'!$B$5` |
| L | Vesting Start Date | start date (YYYY-MM-DD) |
| M | Vesting Schedule | e.g. `4 years: 1 year cliff, monthly after` or `6 months; monthly, no cliff` (advisor) |
| N | Agreement | **paste the contract Doc URL** — auto-renders as a Doc smart chip |
| O, P | Vesting End Date / Termination Agreement | `""` |
| Q | Notes | free text, e.g. "6-month advisory, ~50 hrs, 0.025% anchored to $30M post-money" |

Verify after write: read `Grants!A<n+1>:Q<n+1>` and confirm Status + Agreement render as chips in the UI.

**Outstanding Shares freshness check (required before write):**

The G/K formulas reference a fixed cell like `'Outstanding Shares'!$B$5`. That cell is supposed to point at the most recent "As Of" row in the **Outstanding Shares** tab (sheetId `925107379`). It's a fixed reference, so it goes stale silently when a new row is added below it.

Before writing the new hire's row:

1. Read the formula in row N's G or K column to extract the referenced cell (e.g. `$B$5`).
2. Read the Outstanding Shares tab (`sheets_read` on the relevant As Of / share-count columns).
3. Identify the row in Outstanding Shares with the most recent `As Of` date that has a populated share count.
4. **If that row is below the row the formula references**, warn the user before writing:

   > ⚠️ The equity formula references `'Outstanding Shares'!$B$<n>` (As Of: <date>), but a newer row exists at `$B$<m>` (As Of: <newer-date>). The share-count calculation will use the stale value. Proceed anyway, or update the formula first?

   Do NOT silently change the formula — share counts in already-granted rows depend on it being stable. Surface, let user decide.

5. If the referenced row IS the most recent, proceed silently.

Keep using the existing formula (`=IF(F<row>="","",ROUND(F<row>*'Outstanding Shares'!$B$<n>,-2))`) — substitute the same `$B$<n>` reference as the prior row uses, so all rows in a vintage point at the same denominator.

### 8. eSignature

Report to the user:

> **Ready to send for eSignature:**
> Document(s): [list with Drive links]
> Recipients: [personal email] + brady@doromind.com
>
> In the document, go to **Tools → eSignature** to route for signatures. (eSignature must be initiated manually in the Google Docs UI — it cannot be triggered via API.)

### 9. Asana — "[New Hire] Pre-prep" template

**Skip this entire step if the title is Advisor** — advisors don't go through the employee onboarding flow. Note "Asana onboarding: skipped (Advisor)" in the final report.

Search for the onboarding project using `mcp__asana_work__asana_search_projects` (query: "onboarding" or "new hire"). Once found, get its sections via `mcp__asana_work__asana_get_project_sections`.

Find the **"[New Hire] Pre-prep"** task template. If a task template API is available, instantiate it; otherwise create a task titled `[New Hire] Pre-prep — [Employee Name]` in the onboarding project with notes summarizing:
- Employee name, title, personal email, start date
- Link to the employee's Drive folder
- Link to the executed contract (leave blank until signed)
- Equity row link (if applicable)

Assign to Brady and set due date to 3 business days before start date.

### 10. People vault — create or update person note

Check if a person note exists at `+ Atlas/People/[Full Name].md`.
- If not: scaffold one using the Person template (stage in `+ Inbox/people-candidates/` per §12 candidate staging rules).
- If exists: update `last_contact` to today, add a bullet under `## Threads`: `- [date] · offer sent · personal: [email] · start: [date]`.

### 11. Report

Output a summary:

```
✅ Hire process initiated for [Name]

Drive folder:    [link]
Contract(s):     [link(s)] — ready for eSignature (initiate manually via Tools → eSignature)
Equity sheet:    [link to row] (status: Offered) [or: N/A]
Asana task:      [link] — "[New Hire] Pre-prep — [Name]"
Person note:     + Atlas/People/[Name].md [or: staged in + Inbox/people-candidates/]

Contract URL(s) (raw, for paste):
  https://docs.google.com/document/d/<docId>/edit

Next step: send eSignature from Google Docs, then mark the Asana task "Contract sent".
```

**Always print the contract URL(s) as raw `https://...` strings** in addition to any markdown links — Brady often needs to copy/paste the URL directly, and markdown links don't survive that.

## Notes

- **Never send the offer email directly.** eSignature is initiated from Google Docs UI (Tools → eSignature) — this skill prepares the document and reports when it's ready.
- **Do not create duplicate Asana tasks.** Check step 2c before creating anything in step 9.
- **Personal email is a hard blocker** for step 5 onward — the employee needs it before @doromind.com is provisioned.
- **Clinicians** typically get two agreements (hourly + equity) — copy both templates.
- The equity spreadsheet uses share counts in the actual grant; the "Reference %" column is only for translating a %-based offer conversation into the share number that goes in the document.
