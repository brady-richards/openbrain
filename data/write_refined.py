#!/usr/bin/env python3
"""Write refined.csv from stuff.db for 2026-05-20 working set."""
import csv, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'stuff.db'
OUT = ROOT / '+ Inbox' / 'orient' / '2026-05-20' / 'refined.csv'

# The working set for this run was the 14 rows that were unbucketed
# coming into the refine, plus their collapse peers from this date's
# capture.csv. Use capture.csv as the row roster, then join verdicts
# from the DB.
CAP = ROOT / '+ Inbox' / 'orient' / '2026-05-20' / 'capture.csv'

with open(CAP) as fh:
    raw = fh.read().splitlines()
# Strip any non-header preamble lines.
while raw and not raw[0].startswith('url,'):
    raw.pop(0)
import io
cap_rows = list(csv.DictReader(io.StringIO('\n'.join(raw))))
urls = [r['url'] for r in cap_rows]

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Build URL -> verdict map.
qmarks = ','.join('?' * len(urls))
cur.execute(f"""SELECT url, bucket, asana_gid, asana_match_reason, next_action
                FROM stuff WHERE url IN ({qmarks})""", urls)
verdicts = {row['url']: dict(row) for row in cur.fetchall()}

fields = list(cap_rows[0].keys()) + ['bucket', 'asana_gid', 'asana_match_reason', 'next_action']
with open(OUT, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for r in cap_rows:
        v = verdicts.get(r['url'], {})
        out = dict(r)
        out['bucket'] = v.get('bucket') or ''
        out['asana_gid'] = v.get('asana_gid') or ''
        out['asana_match_reason'] = v.get('asana_match_reason') or ''
        out['next_action'] = v.get('next_action') or ''
        w.writerow(out)

print('wrote', OUT, 'rows', len(cap_rows))
con.close()
