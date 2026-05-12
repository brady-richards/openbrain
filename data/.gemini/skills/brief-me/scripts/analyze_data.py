import pandas as pd
import sqlite3
import json
import sys
import os
from datetime import datetime, timedelta, timezone

def find_file(name):
    # Search in current dir and parent dirs
    curr = os.getcwd()
    while True:
        target = os.path.join(curr, name)
        if os.path.exists(target):
            return target
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return name # Fallback to name

def analyze_asana(file_path):
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    df = pd.read_csv(file_path)
    # Convert dates and ensure they are UTC-aware if they have timezone info
    df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', utc=True)
    df['completed_at'] = pd.to_datetime(df['completed_at'], errors='coerce', utc=True)
    
    # Effort cleanup - assume it's a number or empty
    df['Effort'] = pd.to_numeric(df['Effort'], errors='coerce').fillna(0)
    
    # Stock: Incomplete tasks
    stock_df = df[df['completed'].astype(str).str.lower() == 'false']
    stock_count = len(stock_df)
    stock_effort = stock_df['Effort'].sum()
    
    # Flow: Last 7 days
    from datetime import timezone
    now = datetime.now(timezone.utc) # UTC now
    seven_days_ago = now - timedelta(days=7)
    
    inflow_df = df[df['created_at'] >= seven_days_ago]
    inflow_count = len(inflow_df)
    inflow_effort = inflow_df['Effort'].sum()
    
    outflow_df = df[df['completed_at'] >= seven_days_ago]
    outflow_count = len(outflow_df)
    outflow_effort = outflow_df['Effort'].sum()
    
    # Top tasks (incomplete, sorted by priority/due date if available)
    # We'll just take the top 10 for the LLM to see
    # Priority (custom) might not exist or be named differently, handle gracefully
    sort_cols = []
    if 'due_on' in df.columns:
        sort_cols.append('due_on')
    if 'Priority (custom)' in df.columns:
        sort_cols.append('Priority (custom)')
    
    if sort_cols:
        top_tasks = stock_df.sort_values(by=sort_cols, ascending=[True, False]).head(10)
    else:
        top_tasks = stock_df.head(10)
        
    top_tasks_list = top_tasks[['name', 'due_on', 'Effort']].to_dict('records') if 'due_on' in top_tasks.columns else top_tasks[['name', 'Effort']].to_dict('records')
    
    return {
        "stock": {"count": int(stock_count), "effort": float(stock_effort)},
        "flow": {
            "inflow": {"count": int(inflow_count), "effort": float(inflow_effort)},
            "outflow": {"count": int(outflow_count), "effort": float(outflow_effort)}
        },
        "top_tasks": top_tasks_list
    }

def analyze_stuff(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
    
    query = "SELECT url, summary, next_action, potential_work_reason FROM stuff WHERE received >= ?"
    cursor.execute(query, (seven_days_ago,))
    rows = cursor.fetchall()
    
    items = [dict(row) for row in rows]
    conn.close()
    
    return items

def get_next_business_day(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    # 0=Mon, 4=Fri, 5=Sat, 6=Sun
    if dt.weekday() == 4: # Friday
        next_day = dt + timedelta(days=3)
    elif dt.weekday() == 5: # Saturday
        next_day = dt + timedelta(days=2)
    else:
        next_day = dt + timedelta(days=1)
    return next_day.strftime('%Y-%m-%d')

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    next_biz_day = get_next_business_day(date_str)
    
    asana_path = find_file('asana.csv')
    stuff_path = find_file('stuff.db')
    
    asana_stats = analyze_asana(asana_path)
    stuff_items = analyze_stuff(stuff_path)
    
    result = {
        "target_date": date_str,
        "next_business_day": next_biz_day,
        "asana": asana_stats,
        "stuff_new_items": stuff_items
    }
    
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
