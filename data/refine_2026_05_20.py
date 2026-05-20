#!/usr/bin/env python3
"""Refine-work for 2026-05-20: classify the 14 remaining working-set rows.

Steps 2-8: collapse, cross-medium, match Asana, rewrite next_action, write back.
"""
import csv, re, sqlite3, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'stuff.db'
ASANA = ROOT / 'data' / 'asana.csv'

# Load Asana snapshot, build indexes restricted to Brady-assigned tasks.
rows = list(csv.DictReader(open(ASANA)))
brady_rows = [r for r in rows if r.get('assignee_name') == 'Brady Richards']

by_thread = {}
by_url = {}
for r in brady_rows:
    tid = (r.get('Gmail Thread Id') or '').strip()
    if tid:
        by_thread.setdefault(tid, r['gid'])
    su = (r.get('Source URLs') or '') + '\n' + (r.get('notes') or '')
    for m in re.findall(r'https?://\S+', su):
        m = m.rstrip('.,;)>')
        by_url.setdefault(m, r['gid'])

# Survey: print a quick lookup for the working rows.
con = sqlite3.connect(DB)
cur = con.cursor()
cur.execute("""SELECT url, received, source, forum, thread, direction,
                       counterparty, body, summary
                FROM stuff WHERE bucket IS NULL OR bucket=''
                ORDER BY received""")
working = [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]
print(f'working rows: {len(working)}')

# Manual verdicts based on inspection.
# Format: url -> dict(bucket, asana_gid, asana_match_reason, next_action)
verdicts = {}

# 1) Shaun Zetlin SMS coaching tip — not work, personal training note. drop.
verdicts['messages://+13027402422/r84629'] = dict(
    bucket='dropped',
    asana_match_reason='personal golf coaching note; not actionable work',
)

# 2) Pao Feedback Week nudge — collapse into earlier survivor in same Slack thread.
verdicts['https://doromind.slack.com/archives/C05N7RXUJEB/p177920098491563'
         '9?thread_ts=1778510239.002709'] = dict(
    bucket='collapsed',
    asana_match_reason='collapsed into https://doromind.slack.com/archives/C05N7RXUJEB/p17785102390'
                       '02709?thread_ts=1778510239.002709',
)

# 3) Minna nudges Jon to keep Kate/Hannah updated; suggests Kate or Mimi/Brady reach out to Rob.
# Real ask on Brady. Probable new work.
verdicts['https://doromind.slack.com/archives/C06KPV9SYD6/p177920254196'
         '6129?thread_ts=1779200128.535649'] = dict(
    bucket='probable_new_work',
    next_action='Reach out to Rob with Kate/Mimi update on Hannah situation',
)

# 4) PJ SVB NDA for venture debt — Brady is recipient; Lauren will follow up with diligence.
verdicts['https://mail.google.com/mail/u/0/#all/19e40ebe97e939eb'] = dict(
    bucket='probable_new_work',
    next_action='Review/sign SVB venture-debt NDA; expect Lauren diligence list',
)

# 5) Minna shares Amigo tech dive Fathom + folder — informational FYI.
verdicts['https://doromind.slack.com/archives/C07082PQ132/p177920882070'
         '5409?thread_ts=1776458944.003089'] = dict(
    bucket='dropped',
    asana_match_reason='FYI share of Fathom recording/folder; no ask on Brady',
)

# 6) Brady outbound to Beth ("I will get on the csv exports now") — same Pilot/books thread.
verdicts['https://mail.google.com/mail/u/0/#all/19e414e0e8be0272'] = dict(
    bucket='collapsed',
    asana_match_reason='collapsed into https://mail.google.com/mail/u/0/#all/19e2961e98e39503',
)

# 7) Bedford Road Medical / Chase Nelson Virtru-encrypted reply (outbound counterparty list).
# Brady forwarded/received; needs Brady to open Virtru and review. Probable new work.
verdicts['https://mail.google.com/mail/u/0/#all/19e41613ed2547f4'] = dict(
    bucket='probable_new_work',
    next_action='Open Nelson Chase Virtru reply re Bedford Road Medical account',
)

# 8) GitHub Cursor app permissions request on doromind org — admin action.
verdicts['https://mail.google.com/mail/u/0/#all/19e417d78b44c9d5'] = dict(
    bucket='probable_new_work',
    next_action='Approve/deny Cursor app updated permissions on doromind GitHub org',
)

# 9) Mike Farry asks procurement to confirm receipt of IPF proposal — Brady was on procurement.
# Thread 19e078fceed2299f — check for prior peer.
verdicts['https://mail.google.com/mail/u/0/#all/19e4197f1572d0c3'] = dict(
    bucket='probable_new_work',
    next_action='Confirm receipt of Mike Farry IPF proposal; route internally',
)

# 10) Northwest Registered Agent uploaded mail doc for Bedford Road Medical — review doc.
verdicts['https://mail.google.com/mail/u/0/#all/19e41e0bcd09622f'] = dict(
    bucket='probable_new_work',
    next_action='Download/review Northwest mail doc for Bedford Road Medical (5/18)',
)

# 11) Rho daily summary: expenses awaiting approval — recurring action.
verdicts['https://mail.google.com/mail/u/0/#all/19e420bdd1dbe224'] = dict(
    bucket='probable_new_work',
    next_action='Approve pending Rho expenses (daily summary)',
)

# 12) David Chang Product Backlog v6 — owners review R/A and fill C/I before Tuesday.
verdicts['https://doromind.slack.com/archives/C0B1XQ2RSFN/p17792280726'
         '99269'] = dict(
    bucket='probable_new_work',
    next_action='Review R/A and fill C/I on Product Backlog v6 before Tuesday',
)

# 13) Paloma "Sapporo unless I really want Brooklyn lager" — personal/spousal, no work.
verdicts['messages://+17608143153/r84651'] = dict(
    bucket='dropped',
    asana_match_reason='personal grocery banter; not work',
)

# 14) Sooah Cho asks if Brady wants intro to Google mental health lead.
verdicts['https://mail.google.com/mail/u/0/#all/19e440e3ea56e3c7'] = dict(
    bucket='probable_new_work',
    next_action='Reply to Sooah re Google mental-health lead intro (yes/no)',
)

# Apply matching against Asana for the probable_new_work items.
for url, v in verdicts.items():
    if v['bucket'] != 'probable_new_work':
        continue
    # Find matching row in working set for thread lookup
    row = next((r for r in working if r['url'] == url), None)
    if not row:
        continue
    tid = row['thread']
    if tid in by_thread:
        v['bucket'] = 'definite_duplicate'
        v['asana_gid'] = by_thread[tid]
        v['asana_match_reason'] = 'Gmail threadId match'
    elif url in by_url:
        v['bucket'] = 'definite_duplicate'
        v['asana_gid'] = by_url[url]
        v['asana_match_reason'] = 'source URL in task notes'

# Write back in a transaction.
cur.execute('BEGIN')
for url, v in verdicts.items():
    cur.execute("""UPDATE stuff SET bucket=?, asana_gid=?, asana_match_reason=?,
                       next_action=? WHERE url=?""",
                (v['bucket'], v.get('asana_gid'),
                 v.get('asana_match_reason') or ('no matching Asana task found'
                                                  if v['bucket']=='probable_new_work' else None),
                 v.get('next_action'),
                 url))
con.commit()
print('verdicts applied:', len(verdicts))

# Verification
for q,label in [
    ("SELECT COUNT(*) FROM stuff WHERE (bucket IS NULL OR bucket='') AND potential_work IN ('Y','N')", 'unbucketed'),
    ("SELECT COUNT(*) FROM stuff WHERE bucket IN ('definite_duplicate','possible_duplicate') AND (asana_gid IS NULL OR asana_gid='')", 'dupe-no-gid'),
    ("SELECT COUNT(*) FROM stuff WHERE bucket IN ('probable_new_work','possible_duplicate','definite_duplicate') AND (next_action IS NULL OR next_action='')", 'no-action'),
    ("SELECT COUNT(*) FROM stuff WHERE bucket='probable_new_work' AND asana_gid IS NOT NULL AND asana_gid<>''", 'prob-has-gid'),
    ("SELECT COUNT(*) FROM stuff WHERE bucket='collapsed' AND (asana_match_reason IS NULL OR asana_match_reason NOT LIKE 'collapsed into %')", 'bad-collapsed'),
]:
    cur.execute(q)
    print(label, cur.fetchone()[0])

con.close()
