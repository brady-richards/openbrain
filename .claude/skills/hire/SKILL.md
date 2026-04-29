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

**2d. People vault** — grep `+ Atlas/People/` for a note matching the candidate name. If found, read it for `emails`, `relationship`, and open commitments.

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

In the Contract Templates folder (`1702O7tprYUOZSECU9m1a8UZNKvSK6-Nm`), find the correct template:
- W-2: search for "employment agreement" (or "W-2 agreement")
- 1099: search for "consulting agreement" (or "1099 agreement")
- Clinician with equity: copy both the hourly and equity agreements

Use `mcp__gdrive_brady_doromind_com__copyFile` to copy the template(s) into the employee's folder. Name each copy: `[Employee Name] — [Agreement Type] Agreement`.

### 6. Draft — fill in variables

Read the copied contract(s) with `mcp__gdrive_brady_doromind_com__readDocument`. Identify all variable fields (typically wrapped in `{{` `}}` or highlighted). Use `mcp__gdrive_brady_doromind_com__replaceDocumentWithMarkdown` (or `findAndReplace`) to substitute:

| Variable | Value |
|---|---|
| `{{Employee Name}}` | Full legal name (ask if not known) |
| `{{Title}}` | Resolved title |
| `{{Salary}}` / `{{Rate}}` | Resolved compensation |
| `{{Start Date}}` | Resolved start date |
| `{{Equity}}` / `{{Shares}}` | Equity if applicable |
| `{{Personal Email}}` | Personal email |

Report back any variables that couldn't be resolved automatically.

### 7. Equity spreadsheet (if applicable)

If equity_pct is set, open [Doro Mind Option Stock Grants](https://docs.google.com/spreadsheets/d/1bI8Lo69cXOM72p1EXnWlY-EMteYT2Zzg5oUfCyFZHwc/edit) with `mcp__gdrive_brady_doromind_com__readSpreadsheet`. Find the next empty row. Append a new row with:
- Employee name
- Title
- Grant date (= start date or today)
- Equity % / share count
- Status: **Offered**
- Reference % (if translating from % → shares, note the conversion)

Use `mcp__gdrive_brady_doromind_com__appendRows` to write the row.

### 8. eSignature

Report to the user:

> **Ready to send for eSignature:**
> Document(s): [list with Drive links]
> Recipients: [personal email] + brady@doromind.com
>
> In the document, go to **Tools → eSignature** to route for signatures. (eSignature must be initiated manually in the Google Docs UI — it cannot be triggered via API.)

### 9. Asana — "[New Hire] Pre-prep" template

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

Next step: send eSignature from Google Docs, then mark the Asana task "Contract sent".
```

## Notes

- **Never send the offer email directly.** eSignature is initiated from Google Docs UI (Tools → eSignature) — this skill prepares the document and reports when it's ready.
- **Do not create duplicate Asana tasks.** Check step 2c before creating anything in step 9.
- **Personal email is a hard blocker** for step 5 onward — the employee needs it before @doromind.com is provisioned.
- **Clinicians** typically get two agreements (hourly + equity) — copy both templates.
- The equity spreadsheet uses share counts in the actual grant; the "Reference %" column is only for translating a %-based offer conversation into the share number that goes in the document.
