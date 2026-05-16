#!/usr/bin/env python3
"""Refine work: match six working-set rows against Asana snapshot."""
import csv
import re
import sqlite3
import sys

ASANA_CSV = "data/asana.csv"
DB = "data/stuff.db"

THREADS = {
    "19e2d6badd711d7b": "Beth Pilot pay-raise amortization + Apex statements",
    "1778876948.997539": "Kate green-light CT provisional license $200",
    "19e2d9f69611fa7b": "Nick Jurkowitz consulting docs review",
    "19e31751a78d7cc4": "Laura Desrosiers Mailchimp 404 link broken",
    "19e238c270f9078a": "Michael Livshutz Doro Mind LEAP study aids",
}

# Load Asana - filter to Brady's tasks only, not completed
def load_asana():
    by_thread = {}
    by_url = {}
    tasks = []
    with open(ASANA_CSV, encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('assignee_name', '').strip() != 'Brady Richards':
                continue
            if row.get('completed', '').lower() == 'true':
                continue
            tasks.append(row)
            tid = (row.get('Gmail Thread Id') or '').strip()
            if tid:
                by_thread[tid] = row['gid']
            srcs = (row.get('Source URLs') or '') + '\n' + (row.get('notes') or '')
            for m in re.findall(r'https?://\S+', srcs):
                by_url[m.rstrip('>),.;]')] = row['gid']
    return tasks, by_thread, by_url

def main():
    tasks, by_thread, by_url = load_asana()
    print(f"Loaded {len(tasks)} open Brady-assigned Asana tasks", file=sys.stderr)
    print(f"by_thread entries: {len(by_thread)}", file=sys.stderr)

    # Try matches per row
    for thread, label in THREADS.items():
        print(f"\nThread {thread}: {label}")
        if thread in by_thread:
            gid = by_thread[thread]
            name = next((t['name'] for t in tasks if t['gid'] == gid), '?')
            print(f"  DEFINITE: gid={gid} name={name}")
        else:
            # try semantic by keyword
            kws = label.lower().split()
            hits = []
            for t in tasks:
                blob = (t['name'] + ' ' + (t.get('notes') or '')).lower()
                score = sum(1 for kw in kws if len(kw) > 3 and kw in blob)
                if score >= 2:
                    hits.append((score, t['gid'], t['name']))
            hits.sort(reverse=True)
            for h in hits[:3]:
                print(f"  candidate: score={h[0]} gid={h[1]} name={h[2]}")

if __name__ == '__main__':
    main()
