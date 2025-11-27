# db/rules.py
from datetime import datetime
from .connection import _get_conn

PRIORITY_ORDER = {
    "immediate": 1,
    "mid_term": 2,
    "long_term": 3,
}

def get_active_rules() -> list[dict]:
    """
    Devuelve reglas activas ordenadas por prioridad.
    Filtra: active=1 y (expires_at IS NULL o > ahora)
    """
    conn = _get_conn()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    rows = cur.execute("""
        SELECT id, rule_text, priority, expires_at
        FROM rules
        WHERE active = 1
          AND (expires_at IS NULL OR expires_at > ?)
        ORDER BY
            CASE priority
                WHEN 'immediate' THEN 1
                WHEN 'mid_term' THEN 2
                WHEN 'long_term' THEN 3
            END ASC,
            id ASC
    """, (now,)).fetchall()

    return [dict(row) for row in rows]


def get_active_schedules() -> list[dict]:
    """
    Devuelve todos los setup_schedule activos.
    """
    conn = _get_conn()
    cur = conn.cursor()

    rows = cur.execute("""
        SELECT id, zone_id, days, start_time, end_time, temp_min, temp_max
        FROM setup_schedule
        WHERE active = 1
    """).fetchall()

    return [dict(row) for row in rows]


def get_formatted_rules_context() -> str:
    """
    Builds a clean natural-language block with all active system rules.
    This result is injected into the System Prompt of the decisor agent.
    """
    rules = get_active_rules()

    lines = []
    lines.append("=== ACTIVE SYSTEM RULES ===")

    for r in rules:
        pr = r["priority"]
        txt = r["rule_text"].strip()
        exp = r["expires_at"]
        exp_info = f" (expires at {exp})" if exp else ""
        lines.append(f"[{pr.upper()}]{exp_info}: {txt}")

    return "\n".join(lines)