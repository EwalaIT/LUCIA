from .connection import _get_conn

def insert_memory_entry(session_id: str, input_json: str, output_json: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO memory (session_id, input_json, output_json)
        VALUES (?, ?, ?)
    """, (session_id, input_json, output_json))
    conn.commit()


def get_memory_entries(session_id: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT input_json, output_json, created_at
        FROM memory
        WHERE session_id = ?
        ORDER BY created_at ASC
    """, (session_id,))
    return cur.fetchall()


def clear_memory_for_session(session_id: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM memory WHERE session_id = ?", (session_id,))
    conn.commit()
    