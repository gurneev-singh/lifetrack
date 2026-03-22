# LifeTrack - features/tracking/cross_verify.py
# Compares screen activity vs webcam physical state.
# Generates a "truth score" — catches when screen says study
# but camera says phone in hand.

import sqlite3
from datetime import datetime, timedelta
from core.config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cross_verify_today() -> dict:
    """
    Compare today's screen logs vs webcam logs.
    Returns truth analysis dict.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()

    # Get screen activity (screenshot_log preferred, fallback to activity_log)
    ss_count = conn.execute(
        "SELECT COUNT(*) as n FROM screenshot_log WHERE date=?", (today,)
    ).fetchone()["n"]

    if ss_count > 0:
        screen_rows = conn.execute("""
            SELECT timestamp, category FROM screenshot_log
            WHERE date=? ORDER BY timestamp ASC
        """, (today,)).fetchall()
    else:
        screen_rows = conn.execute("""
            SELECT timestamp, category FROM activity_log
            WHERE date=? AND is_idle=0 ORDER BY timestamp ASC
        """, (today,)).fetchall()

    # Get webcam data
    webcam_rows = conn.execute("""
        SELECT timestamp, physical FROM webcam_log
        WHERE date=? ORDER BY timestamp ASC
    """, (today,)).fetchall() if table_exists(conn, "webcam_log") else []

    conn.close()

    if not webcam_rows:
        return {"available": False, "reason": "No webcam data yet"}

    # Build minute-by-minute map
    screen_map  = {r["timestamp"][:16]: r["category"] for r in screen_rows}
    webcam_map  = {r["timestamp"][:16]: r["physical"] for r in webcam_rows}

    # Cross verify
    confirmed_study   = 0
    claimed_study     = 0
    phone_while_study = 0
    away_while_active = 0
    total_compared    = 0

    for ts, physical in webcam_map.items():
        screen_cat = screen_map.get(ts, "unknown")
        total_compared += 1

        if screen_cat == "study":
            claimed_study += 1
            if physical == "present":
                confirmed_study += 1
            elif physical == "distracted":
                phone_while_study += 1
            elif physical == "away":
                away_while_active += 1

    # Calculate truth score
    truth_score = int((confirmed_study / claimed_study) * 100) if claimed_study > 0 else 100

    return {
        "available": True,
        "claimed_study_min": claimed_study,
        "confirmed_study_min": confirmed_study,
        "phone_while_study_min": phone_while_study,
        "away_while_active_min": away_while_active,
        "truth_score": truth_score,
        "total_compared": total_compared,
        "lost_minutes": claimed_study - confirmed_study,
    }


def get_webcam_timeline(date_str=None, limit=50) -> list:
    """Get webcam log entries for dashboard timeline."""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()
    if not table_exists(conn, "webcam_log"):
        conn.close()
        return []
    rows = conn.execute("""
        SELECT timestamp, description, physical
        FROM webcam_log WHERE date=?
        ORDER BY timestamp DESC LIMIT ?
    """, (date_str, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def table_exists(conn, name) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None