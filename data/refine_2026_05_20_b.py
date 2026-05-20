#!/usr/bin/env python3
"""Refine-work for 2026-05-20 (second pass): classify the 11 remaining candidates
plus auto-drop the 95 potential_work='N' rows still unbucketed.
"""
import csv, re, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'stuff.db'
ASANA = ROOT / 'data' / 'asana.csv'

# Load Asana snapshot.
rows = list(csv.DictReader(open(ASANA)))
brady_rows = [r for r in rows if r.get('assignee_name') == 'Brady Richards']
by_thread, by_url = {}, {}
for r in brady_rows:
    tid = (r.get('Gmail Thread Id') or '').strip()
    if tid:
        by_thread.setdefault(tid, r['gid'])
    su = (r.get('Source URLs') or '') + '\n' + (r.get('notes') or '')
    for m in re.findall(r'https?://\S+', su):
        m = m.rstrip('.,;)>')
        by_url.setdefault(m, r['gid'])

con = sqlite3.connect(DB)
cur = con.cursor()

# 1) Auto-drop potential_work=N rows.
cur.execute("""UPDATE stuff SET bucket='dropped', asana_match_reason='not potential work'
               WHERE (bucket IS NULL OR bucket='') AND potential_work='N'""")
auto_dropped = cur.rowcount
print(f'auto-dropped: {auto_dropped}')

# Manual verdicts for the 11 candidates.
verdicts = {}

# 1) Robert Laitman SMS: "send me Dee's talk link" -- simple ask, probable new work.
verdicts['messages://chat42546307063245870/r84657'] = dict(
    bucket='probable_new_work',
    next_action="Send Robert Laitman the link to Dee's talk",
)

# 2) Mimi Liu Google Docs comment reply on Sandra Clarke advisory agreement.
# Action: review Mimi's reply on the doc. Probable new work.
verdicts['https://mail.google.com/mail/u/0/#all/19e46d29876adaa6'] = dict(
    bucket='probable_new_work',
    next_action="Review Mimi's reply on Sandra Clarke advisory agreement doc",
)

# 3 & 4) Two Sooah Cho emails on thread 19e440e3ea56e3c7 — collapse into existing
# survivor (already probable_new_work). Update survivor's next_action to reflect
# the latest ask: a Doro Mind / CA grants blurb for Dan Tsai + Steve Farmer.
SOOAH_SURVIVOR = 'https://mail.google.com/mail/u/0/#all/19e440e3ea56e3c7'
verdicts['https://mail.google.com/mail/u/0/#all/19e46320cf5c6c3a'] = dict(
    bucket='collapsed',
    asana_match_reason=f'collapsed into {SOOAH_SURVIVOR}',
)
verdicts['https://mail.google.com/mail/u/0/#all/19e464ae9804ee4f'] = dict(
    bucket='collapsed',
    asana_match_reason=f'collapsed into {SOOAH_SURVIVOR}',
)
# Rewrite the survivor next_action.
cur.execute("""UPDATE stuff SET next_action=? WHERE url=?""",
            ("Send Sooah Doro Mind + CA grants blurb for Dan Tsai/Steve Farmer", SOOAH_SURVIVOR))

# 5) Brady (via guides@) outbound to Brian Jones with Doro Compass info.
# Outbound; no return ask yet -- drop (FYI/info-send completed).
verdicts['https://mail.google.com/mail/u/0/#all/19e4624fee5e4836'] = dict(
    bucket='dropped',
    asana_match_reason='outbound info-send to Brian Jones; no return ask yet',
)

# 6) Keren asks Brady if any specific questions for Assured team in today's meeting.
verdicts['https://doromind.slack.com/archives/C0AT7AG80RM/p17792905212'
         '15039?thread_ts=1779290521.215039'] = dict(
    bucket='probable_new_work',
    next_action='Reply to Keren with any questions for Assured team meeting',
)

# 7) Dhanica scheduled Cursor planning meeting; asks if reschedule needed.
verdicts['https://doromind.slack.com/archives/C08EU2RMU6P/p17792911810'
         '28699?thread_ts=1779291181.028699'] = dict(
    bucket='probable_new_work',
    next_action='Confirm or reschedule Dhanica Cursor planning meeting',
)

# 8) Dhanica re Shayna purchases concern buried in DMs.
verdicts['https://doromind.slack.com/archives/C08EU2RMU6P/p17792945795'
         '06459?thread_ts=1779294579.506459'] = dict(
    bucket='probable_new_work',
    next_action='Address Shayna purchases concern Dhanica flagged in DMs',
)

# 9) Mimi: let me know when to chat about workstreams (sheet linked).
verdicts['https://doromind.slack.com/archives/C08EU2RMU6P/p17792954414'
         '56679?thread_ts=1779295441.456679'] = dict(
    bucket='probable_new_work',
    next_action='Schedule chat with Mimi on workstreams sheet',
)

# 10) Stephanie: $549 CSCSW job posting spend approval.
verdicts['https://doromind.slack.com/archives/C097UG634PJ/p17792977338'
         '79129?thread_ts=1779297733.879129'] = dict(
    bucket='probable_new_work',
    next_action='Approve/deny $549 CSCSW job posting spend for Stephanie',
)

# 11) Britt: Patrick tagged Brady in post-event luma messaging doc; lmk when ready.
verdicts['https://doromind.slack.com/archives/C0B1QAF0KML/p17793062663'
         '38999?thread_ts=1779306266.338999'] = dict(
    bucket='probable_new_work',
    next_action='Review luma post-event messaging doc Patrick tagged; greenlight Britt to send',
)

# Apply Asana matching for probable_new_work items.
cur.execute("SELECT url, thread FROM stuff WHERE url IN (%s)" % ','.join('?'*len(verdicts)),
            list(verdicts.keys()))
row_thread = dict(cur.fetchall())

for url, v in verdicts.items():
    if v['bucket'] != 'probable_new_work':
        continue
    tid = row_thread.get(url, '')
    if tid and tid in by_thread:
        v['bucket'] = 'definite_duplicate'
        v['asana_gid'] = by_thread[tid]
        v['asana_match_reason'] = 'Gmail threadId match'
    elif url in by_url:
        v['bucket'] = 'definite_duplicate'
        v['asana_gid'] = by_url[url]
        v['asana_match_reason'] = 'source URL in task notes'

# Write back.
for url, v in verdicts.items():
    reason = v.get('asana_match_reason')
    if not reason and v['bucket'] == 'probable_new_work':
        reason = 'no matching Asana task found'
    cur.execute("""UPDATE stuff SET bucket=?, asana_gid=?, asana_match_reason=?,
                       next_action=? WHERE url=?""",
                (v['bucket'], v.get('asana_gid'), reason, v.get('next_action'), url))
con.commit()
print('manual verdicts applied:', len(verdicts))

# Verification queries.
checks = [
    ("SELECT COUNT(*) FROM stuff WHERE (bucket IS NULL OR bucket='') AND potential_work IN ('Y','N')", 'unbucketed'),
    ("SELECT COUNT(*) FROM stuff WHERE bucket IN ('definite_duplicate','possible_duplicate') AND (asana_gid IS NULL OR asana_gid='')", 'dupe-no-gid'),
    ("SELECT COUNT(*) FROM stuff WHERE bucket IN ('probable_new_work','possible_duplicate','definite_duplicate') AND (next_action IS NULL OR next_action='')", 'no-action'),
    ("SELECT COUNT(*) FROM stuff WHERE bucket='probable_new_work' AND asana_gid IS NOT NULL AND asana_gid<>''", 'prob-has-gid'),
    ("SELECT COUNT(*) FROM stuff WHERE bucket='collapsed' AND (asana_match_reason IS NULL OR asana_match_reason NOT LIKE 'collapsed into %')", 'bad-collapsed'),
]
for q, label in checks:
    cur.execute(q)
    print(label, cur.fetchone()[0])

con.close()
