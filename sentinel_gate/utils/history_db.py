import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "history.db")

def init_db():
    """Initializes the SQLite database for execution history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_history (
            id TEXT PRIMARY KEY,
            timestamp DATETIME,
            score REAL,
            total_rows INTEGER,
            mode TEXT,
            status TEXT,
            report_path TEXT,
            contract_json TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_execution(result: Dict[str, Any], contract: Dict[str, Any]):
    """Logs a workflow execution result to the history database."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Extract data from result
    exec_id = result.get("execution_id", "unknown")
    score = result.get("scores", {}).get("final_score", 0.0)
    total_rows = result.get("total_rows", 0)
    mode = result.get("mode", "single")
    status = result.get("status", "FAIL")
    report_path = result.get("report_path", "")
    contract_json = json.dumps(contract)
    
    cursor.execute("""
        INSERT INTO execution_history (id, timestamp, score, total_rows, mode, status, report_path, contract_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (exec_id, datetime.now(), score, total_rows, mode, status, report_path, contract_json))
    
    conn.commit()
    conn.close()

def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves the execution history."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM execution_history ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
