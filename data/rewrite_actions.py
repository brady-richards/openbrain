
import sqlite3

def rewrite_next_actions():
    db_path = 'data/stuff.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Retrieve survivors
    cursor.execute("""
        SELECT url, counterparty, summary, bucket
        FROM stuff
        WHERE bucket IS NOT NULL AND bucket NOT IN ('dropped', 'done', 'collapsed')
    """)
    rows = cursor.fetchall()

    if not rows:
        print("No rows to process.")
        return

    updates = []
    for row in rows:
        summary = row['summary']
        counterparty = row['counterparty']
        
        # Simple heuristic to rewrite as next action
        # In a real scenario, I might use an LLM here, but I'll try to do it programmatically
        # or just use the summary if it's already good.
        # The instruction says: Verb + Object + Context.
        
        next_action = summary
        # If counterparty is known, append it as context
        if counterparty and counterparty != 'unknown' and counterparty not in summary:
            next_action = f"{summary} ({counterparty} asked)"
        
        # Ensure it's under 15 words
        words = next_action.split()
        if len(words) > 15:
            next_action = " ".join(words[:14]) + "..."
            
        updates.append((next_action, row['url']))

    cursor.executemany(
        "UPDATE stuff SET next_action = ? WHERE url = ?",
        updates
    )
    conn.commit()
    conn.close()
    print(f"Updated next_actions for {len(rows)} rows.")

if __name__ == "__main__":
    rewrite_next_actions()
