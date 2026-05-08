import sqlite3
import json

def main():
    conn = sqlite3.connect('/Users/brichards/repos/openbrain/stuff.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT url, received, source_mcp, forum, thread, direction, work_or_personal, counterparty, body FROM stuff WHERE received >= '2026-05-06' AND received < '2026-05-08'")
    rows = cursor.fetchall()
    data = [dict(row) for row in rows]
    with open('records.json', 'w') as f:
        json.dump(data, f)
    print(len(data))

if __name__ == '__main__':
    main()
