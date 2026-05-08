import sqlite3
import csv
import os

db_path = "/Users/brichards/repos/openbrain/stuff.db"
output_path = "/Users/brichards/repos/openbrain/data/+ Inbox/orient/2026-05-07/capture.csv"

# Classification logic
def classify_record(body, direction, source_mcp, forum):
    body_lower = body.lower()
    potential_work = "N"
    potential_work_reason = "Informational or personal chat"
    acknowledged = "N"
    acknowledged_reason = ""
    done = "N"
    done_reason = ""

    # Potential Work Heuristics
    if direction == "inbound":
        if any(word in body_lower for word in ["can you", "please", "could you", "need", "urgent", "task", "action"]):
            potential_work = "Y"
            potential_work_reason = "Request directed at user"
    elif direction == "outbound":
        if any(word in body_lower for word in ["i will", "i'll", "let me", "i can", "working on", "will do"]):
            potential_work = "Y"
            potential_work_reason = "Commitment from user"
            acknowledged = "Y"
            acknowledged_reason = "User initiated or committed"

    # Acknowledged Heuristics
    if "[reaction:" in body_lower or any(word in body_lower for word in ["ok", "👍", "sounds good", "got it", "thanks"]):
        acknowledged = "Y"
        acknowledged_reason = "Positive reaction or acknowledgment"

    # Done Heuristics
    if ":done:" in body_lower or any(word in body_lower for word in ["done", "shipped", "finished", "completed"]):
        done = "Y"
        done_reason = "Signal of completion"

    return potential_work, potential_work_reason, acknowledged, acknowledged_reason, done, done_reason

def main():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM stuff WHERE received >= '2026-05-06T00:00:00' AND received < '2026-05-08T00:00:00'"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    with open(output_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Header (if file is empty/newly created)
        if os.path.getsize(output_path) == 0:
            writer.writerow(['source_url', 'received', 'source_mcp', 'forum', 'thread', 'direction', 'work_or_personal', 'counterparty', 'summary', 'potential_work', 'potential_work_reason', 'acknowledged', 'acknowledged_reason', 'done', 'done_reason'])
            
        count = 0
        for row in rows:
            pw, pwr, ack, ackr, dn, dnr = classify_record(row['body'] or "", row['direction'], row['source_mcp'], row['forum'])
            
            writer.writerow([
                row['url'],
                row['received'],
                row['source_mcp'],
                row['forum'],
                row['thread'],
                row['direction'],
                row['work_or_personal'],
                row['counterparty'],
                row['summary'] or "",
                pw,
                pwr,
                ack,
                ackr,
                dn,
                dnr
            ])
            count += 1
    
    print(f"Processed {count} records.")
    conn.close()

if __name__ == "__main__":
    main()
