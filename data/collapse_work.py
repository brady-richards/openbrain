
import sqlite3
import re
from datetime import datetime, timedelta

def collapse_and_link():
    db_path = 'data/stuff.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Retrieve items to refine
    cursor.execute("""
        SELECT url, thread, counterparty, summary, received, source, body
        FROM stuff
        WHERE bucket IS NULL OR (bucket NOT IN ('dropped', 'done', 'collapsed'))
    """)
    rows = cursor.fetchall()

    if not rows:
        print("No rows to process.")
        return

    # 1. Thread Collapsing
    threads = {}
    for row in rows:
        thread_id = row['thread']
        if not thread_id:
            # If no thread_id, use URL as a fallback for uniqueness
            thread_id = row['url']
        
        if thread_id not in threads:
            threads[thread_id] = []
        threads[thread_id].append(row)

    survivors = []
    collapsed_updates = []

    for thread_id, thread_rows in threads.items():
        # Sort by received time
        thread_rows.sort(key=lambda x: x['received'] if x['received'] else '')
        survivor = thread_rows[0]
        survivors.append(dict(survivor))
        
        for non_survivor in thread_rows[1:]:
            collapsed_updates.append((
                'collapsed',
                f"collapsed into {survivor['url']}",
                non_survivor['url']
            ))

    # 2. Cross-Medium Linking (Simple keyword & counterparty match)
    # This is a bit more complex, let's look for strong indicators like "superbill" or "sendbird"
    final_survivors = []
    already_linked = set()

    # Keywords that strongly suggest related work
    keywords = ['superbill', 'sendbird', 'fathom', 'rippling', 'asana', 'board approval', 'western alliance']

    for i, s1 in enumerate(survivors):
        if s1['url'] in already_linked:
            continue
        
        current_group = [s1]
        already_linked.add(s1['url'])

        for j, s2 in enumerate(survivors[i+1:], i+1):
            if s2['url'] in already_linked:
                continue
            
            linked = False
            # Check counterparty and time (~24h)
            if s1['counterparty'] == s2['counterparty'] and s1['counterparty'] and s1['counterparty'] != 'unknown':
                try:
                    t1 = datetime.fromisoformat(s1['received'].replace('Z', '+00:00'))
                    t2 = datetime.fromisoformat(s2['received'].replace('Z', '+00:00'))
                    if abs(t1 - t2) < timedelta(hours=24):
                        linked = True
                except:
                    pass
            
            # Check keywords in summary
            if not linked:
                sum1 = s1['summary'].lower() if s1['summary'] else ""
                sum2 = s2['summary'].lower() if s2['summary'] else ""
                for kw in keywords:
                    if kw in sum1 and kw in sum2:
                        linked = True
                        break
            
            if linked:
                current_group.append(s2)
                already_linked.add(s2['url'])
                collapsed_updates.append((
                    'collapsed',
                    f"collapsed into {s1['url']}",
                    s2['url']
                ))
        
        final_survivors.append(s1)

    # Apply updates
    cursor.executemany(
        "UPDATE stuff SET bucket = ?, asana_match_reason = ? WHERE url = ?",
        collapsed_updates
    )
    conn.commit()
    conn.close()

    print(f"Total rows processed: {len(rows)}")
    print(f"Survivors after collapsing: {len(survivors)}")
    print(f"Final survivors after linking: {len(final_survivors)}")
    print(f"Collapse ratio: {len(final_survivors) / len(rows):.2f}")

if __name__ == "__main__":
    collapse_and_link()
