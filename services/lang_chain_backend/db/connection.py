import sqlite3
from config import settings

def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.db_path), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def execute_sql_write(query: str) -> str:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(query)
        conn.commit()
        return "OK"
    except Exception as e:
        return str(e)
    finally:
        conn.close()
