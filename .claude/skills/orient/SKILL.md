---
name: orient
description: Sequence the three orientation phases — gather potential work, refine it, and produce an orientation. Each phase runs as an isolated subagent that hands off via CSV files in + Inbox/orient/.
---

# /orient

Three-phase pipeline that turns raw signals (Slack, email, Messages) into an oriented view of what to do today. Each phase is heavy enough to deserve its own context, so they run as separate subagents and hand off via files.

## Inputs

- `$1` (optional): target date in `YYYY-MM-DD`. Defaults to today.

## Procedure

> **Date check first.** If `$1` is not supplied, resolve "today" by running `Bash: date "+%Y-%m-%d"`. Do not trust session-injected `currentDate`. Use the shell result as `$DATE` below.

> **Hand-off contract.** Each phase reads from and writes to `+ Inbox/orient/<DATE>/`:
> - Phase 1 writes `capture.csv`
> - Phase 2 reads `capture.csv`, writes `refined.csv`
> - Phase 3 reads `refined.csv`, writes `orientation.md`

> **Why subagents.** Each phase fires 50–300+ tool calls and reads heavy bodies (email, transcripts, threads). Running them in this skill's context would bloat it past usefulness by phase 3. Spawn a subagent per phase so each starts clean.

1. **Preflight — fail fast on broken tools.** Before spawning any subagent, ping every external system /orient depends on with one cheap read each. Run all of these in parallel in a single tool-use block:
   - Each `google_*` MCP: `google_calendar_list_calendars` (proves Gmail/Calendar OAuth is alive)
   - Each `slack_*` MCP: `slack_<slug>_channels_list` with `limit: 1`
   - `asana_work`: `asana_get_my_tasks` with `limit: 1`
   - `fathom`: `fathom_list_teams` (if configured)
   - `messages`: `messages_list_contacts` with `limit: 1`
   - `gcloud` / `gsutil` (needed by `/brief-me` to fetch Fathom transcripts from GCS): `Bash: gcloud auth print-access-token >/dev/null 2>&1 && gsutil ls gs:// >/dev/null 2>&1` — fails if no active credentialed account or `gsutil` isn't on `PATH`. On failure, instruct the user to run `gcloud auth login` (or `gcloud auth application-default login` for ADC).

   For each failure, capture the tool name and error. If **any** call errors (auth expired, MCP not connected, network), stop immediately and report to the user:
   - Which tools failed and the error message
   - What to do (e.g. "re-auth `gcal_brady_doromind_com` via `claude mcp` or the OAuth flow")
   - Do **not** proceed to phase 1 — partial inputs produce a misleading orientation.

   Only continue if every preflight call returned successfully.

2. **Prep.** `mkdir -p "+ Inbox/orient/$DATE"`. Confirm the directory exists before spawning anything.

3. **Phase 1 — gather.** Spawn a subagent:
   - `subagent_type`: `general-purpose`
   - `description`: "Gather potential work"
   - `prompt`: "Run the `/gather-work` skill for $DATE. Output goes to `+ Inbox/orient/$DATE/capture.csv`. Report the row count and any channels that returned zero results when you finish."
   Wait for completion before proceeding.

   **After it returns, verify the puller actually ran.** Subagents can silently skip Step 0 of `/gather-work` (the `pull.py` invocation), causing classification of stale data. Check the mtime of `data/stuff.db` against the time the subagent started:
   ```bash
   stat -f "%m" data/stuff.db
   ```
   If the mtime predates phase 1 by more than a couple of minutes, the puller did not run. Run it from the parent and re-spawn phase 1:
   ```bash
   cd ~/repos/puller && dotenv run -- ./pull.py --after 1d --sqlite ../openbrain/data/stuff.db && dotenv run -- ./asana_pull.py --since 1d --csv >! ../openbrain/data/asana.csv
   ```
   Then re-spawn the phase 1 subagent. Do not proceed to phase 2 with stale inputs.

4. **Phase 2 — refine.** Spawn a subagent:
   - `subagent_type`: `general-purpose`
   - `description`: "Refine captured work"
   - `prompt`: "Run the `/refine-work` skill for $DATE. Input is `+ Inbox/orient/$DATE/capture.csv`. Output goes to `+ Inbox/orient/$DATE/refined.csv`. **Run all steps of the skill, including Step 10 (Fibonacci effort estimation on every unestimated open task assigned to Brady).** The CSV is one hand-off artifact; the DB write-back and the Asana effort estimation are required behavior, not optional. Report what was dropped, merged, or rewritten, and how many Effort estimates were set."
   Wait for completion.

5. **Interactive Asana push (runs in parent).** `AskUserQuestion` is unavailable inside subagents, so Step 9 of `/refine-work` cannot run from phase 2. The parent picks it up here.

   Read all rows where `bucket IN ('probable_new_work', 'possible_duplicate', 'definite_duplicate')` and `received >= $DATE - 1 day` from `data/stuff.db`. Surface them via `AskUserQuestion` and push selected items to Asana exactly as described in `/refine-work` Step 9 (Founders Backlog `1208193100268936`, two-call `asana_create_task` + `asana_update_task` to set custom fields, then `UPDATE stuff` to record the result).

   This step always runs — Brady wants to triage new work into Asana on every `/orient`. Do not skip it because the bucket counts are small.

6. **Phase 3 — orient.** Spawn a subagent:
   - `subagent_type`: `general-purpose`
   - `description`: "Produce orientation"
   - `prompt`: "Run the `/brief-me` skill for $DATE. Input is `+ Inbox/orient/$DATE/refined.csv`. Output goes to `+ Inbox/orient/$DATE/orientation.md`. Return the orientation summary."
   Wait for completion.

7. **Mirror to README.md.** Copy `+ Inbox/orient/$DATE/orientation.md` to `README.md` at the repo root (overwrite). This makes today's orientation the front-door view of the repo.

8. **Commit and push.** Stage `README.md` and the new `+ Inbox/orient/$DATE/` directory, commit with message `docs: mirror $DATE orientation to README`, and `git push`. This is standing authorization — do not ask first. GitHub only reflects pushed commits, so without this step the front-door view stays stale. Do not pass `--no-verify` or skip hooks; if the pre-commit linter fails, fix the underlying issue and retry.

9. **Report.** Echo the path to `orientation.md` and a one-paragraph summary drawn from the phase 3 subagent's return value. Do not re-summarize from the CSV — trust the phase 3 output.

## Notes

- If any phase's subagent returns an error, stop and surface it. Do not proceed to the next phase with stale or partial input.
- Phases are sequential by design — phase 2 needs phase 1's output, phase 3 needs phase 2's. Do not parallelize.
- The CSV files are durable hand-offs. If phase 3 fails, the user can re-run `/brief-me` directly on the existing `refined.csv` without redoing the gather.
