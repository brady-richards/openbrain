
import sqlite3
import csv
import io

def match_asana():
    db_path = 'data/stuff.db'
    asana_path = 'data/asana.csv'
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Retrieve survivors
    cursor.execute("""
        SELECT url, thread, counterparty, summary, body
        FROM stuff
        WHERE bucket IS NULL OR (bucket NOT IN ('dropped', 'done', 'collapsed'))
    """)
    survivors = cursor.fetchall()

    if not survivors:
        print("No survivors to process.")
        return

    # Load Asana data
    asana_tasks = []
    with open(asana_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            asana_tasks.append(row)

    matches = []
    for s in survivors:
        url = s['url']
        thread = s['thread']
        summary = s['summary'].lower() if s['summary'] else ""
        counterparty = s['counterparty'].lower() if s['counterparty'] else ""
        
        match_gid = None
        match_reason = None
        bucket = 'probable_new_work'

        for t in asana_tasks:
            # 1. Definite Match: Thread ID
            if thread and t.get('Gmail Thread Id') == thread:
                match_gid = t['gid']
                match_reason = f"Definite match: Gmail Thread Id {thread}"
                bucket = 'definite_duplicate'
                break
            
            # 2. Definite Match: Source URL in Source URLs or Notes
            source_urls = t.get('Source URLs', '')
            notes = t.get('notes', '')
            if url and (url in source_urls or url in notes):
                match_gid = t['gid']
                match_reason = f"Definite match: URL in Source URLs/Notes"
                bucket = 'definite_duplicate'
                break
            
            # 3. Possible Match: Semantic similarity (Counterparty + Topic)
            # This is naive but better than nothing
            task_name = t['name'].lower()
            if counterparty and counterparty in task_name and counterparty != 'unknown':
                # Check for keyword overlap
                keywords = ['superbill', 'sendbird', 'fathom', 'rippling', 'asana', 'board approval', 'western alliance']
                for kw in keywords:
                    if kw in summary and kw in task_name:
                        match_gid = t['gid']
                        match_reason = f"Possible match: Counterparty '{counterparty}' and keyword '{kw}' overlap"
                        bucket = 'possible_duplicate'
                        break
                if bucket == 'possible_duplicate':
                    break

        matches.append((bucket, match_gid, match_reason, url))

    # Apply updates
    cursor.executemany(
        "UPDATE stuff SET bucket = ?, asana_gid = ?, asana_match_reason = ? WHERE url = ?",
        matches
    )
    conn.commit()
    conn.close()

    print(f"Total survivors processed: {len(survivors)}")
    buckets = [m[0] for m in matches]
    print(f"Probable new work: {buckets.count('probable_new_work')}")
    print(f"Possible duplicates: {buckets.count('possible_duplicate')}")
    print(f"Definite duplicates: {buckets.count('definite_duplicate')}")

if __name__ == "__main__":
    match_asana()
