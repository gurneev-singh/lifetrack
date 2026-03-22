# LifeTrack - database.py
import sqlite3
from datetime import datetime
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            date        TEXT NOT NULL,
            hour        INTEGER NOT NULL,
            window      TEXT,
            app         TEXT,
            url         TEXT,
            category    TEXT,
            is_idle     INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS screenshot_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            date        TEXT NOT NULL,
            hour        INTEGER NOT NULL,
            app         TEXT,
            description TEXT,
            category    TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS browser_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            date        TEXT NOT NULL,
            url         TEXT,
            title       TEXT,
            category    TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_summary (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            date             TEXT UNIQUE NOT NULL,
            study_minutes    INTEGER DEFAULT 0,
            distract_minutes INTEGER DEFAULT 0,
            break_minutes    INTEGER DEFAULT 0,
            idle_minutes     INTEGER DEFAULT 0,
            focus_score      INTEGER DEFAULT 0,
            top_app          TEXT,
            top_distraction  TEXT,
            ai_report        TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mobile_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            date      TEXT,
            type      TEXT,
            note      TEXT,
            mood      TEXT,
            duration  INTEGER
        )
    """)
    conn.commit()
    conn.close()
    print("[DB] Database ready.")


def log_activity(window, app, url, category, is_idle=False):
    now = datetime.now()
    conn = get_connection()
    conn.execute("""
        INSERT INTO activity_log
            (timestamp, date, hour, window, app, url, category, is_idle)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (now.isoformat(), now.strftime("%Y-%m-%d"), now.hour,
          window, app, url, category, int(is_idle)))
    conn.commit()
    conn.close()


def log_screenshot(description, category, app):
    now = datetime.now()
    conn = get_connection()
    conn.execute("""
        INSERT INTO screenshot_log
            (timestamp, date, hour, app, description, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now.isoformat(), now.strftime("%Y-%m-%d"), now.hour,
          app, description, category))
    conn.commit()
    conn.close()


def log_browser_history(entries):
    conn = get_connection()
    for ts, url, title, category in entries:
        date = ts[:10] if ts else datetime.now().strftime("%Y-%m-%d")
        conn.execute("""
            INSERT INTO browser_history (timestamp, date, url, title, category)
            VALUES (?, ?, ?, ?, ?)
        """, (ts, date, url, title, category))
    conn.commit()
    conn.close()


def get_today_activities():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM activity_log WHERE date=? ORDER BY timestamp ASC",
        (today,)).fetchall()
    conn.close()
    return rows


def get_today_screenshots():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM screenshot_log WHERE date=? ORDER BY timestamp ASC",
        (today,)).fetchall()
    conn.close()
    return rows


def get_today_minutes_by_category():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    ss_count = conn.execute(
        "SELECT COUNT(*) as n FROM screenshot_log WHERE date=?",
        (today,)).fetchone()["n"]
    if ss_count > 0:
        rows = conn.execute("""
            SELECT category, COUNT(*) as count
            FROM screenshot_log WHERE date=?
            GROUP BY category
        """, (today,)).fetchall()
        conn.close()
        result = {"study": 0, "distraction": 0, "break": 0, "idle": 0, "unknown": 0}
        for row in rows:
            cat = row["category"] or "unknown"
            result[cat] = result.get(cat, 0) + row["count"]
        return result
    else:
        rows = conn.execute("""
            SELECT category, is_idle, COUNT(*) as count
            FROM activity_log WHERE date=?
            GROUP BY category, is_idle
        """, (today,)).fetchall()
        conn.close()
        result = {"study": 0, "distraction": 0, "break": 0, "idle": 0, "unknown": 0}
        for row in rows:
            if row["is_idle"]:
                result["idle"] += row["count"]
            else:
                cat = row["category"] or "unknown"
                result[cat] = result.get(cat, 0) + row["count"]
        return result


def get_top_apps_today(limit=5):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute("""
        SELECT app, COUNT(*) as minutes FROM screenshot_log
        WHERE date=? AND app IS NOT NULL
        GROUP BY app ORDER BY minutes DESC LIMIT ?
    """, (today, limit)).fetchall()
    if not rows:
        rows = conn.execute("""
            SELECT app, COUNT(*) as minutes FROM activity_log
            WHERE date=? AND is_idle=0 AND app IS NOT NULL
            GROUP BY app ORDER BY minutes DESC LIMIT ?
        """, (today, limit)).fetchall()
    conn.close()
    return rows


def get_top_distractions_today(limit=3):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute("""
        SELECT app, COUNT(*) as minutes FROM screenshot_log
        WHERE date=? AND category='distraction'
        GROUP BY app ORDER BY minutes DESC LIMIT ?
    """, (today, limit)).fetchall()
    if not rows:
        rows = conn.execute("""
            SELECT app, COUNT(*) as minutes FROM activity_log
            WHERE date=? AND category='distraction'
            GROUP BY app ORDER BY minutes DESC LIMIT ?
        """, (today, limit)).fetchall()
    conn.close()
    return rows


def get_recent_descriptions(limit=20):
    conn = get_connection()
    rows = conn.execute("""
        SELECT timestamp, app, description, category
        FROM screenshot_log
        ORDER BY timestamp DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows


def save_daily_summary(date_str, study_min, distract_min, break_min,
                        idle_min, focus_score, top_app, top_distraction, ai_report):
    conn = get_connection()
    conn.execute("""
        INSERT INTO daily_summary
            (date, study_minutes, distract_minutes, break_minutes,
             idle_minutes, focus_score, top_app, top_distraction, ai_report)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            study_minutes=excluded.study_minutes,
            distract_minutes=excluded.distract_minutes,
            break_minutes=excluded.break_minutes,
            idle_minutes=excluded.idle_minutes,
            focus_score=excluded.focus_score,
            top_app=excluded.top_app,
            top_distraction=excluded.top_distraction,
            ai_report=excluded.ai_report
    """, (date_str, study_min, distract_min, break_min,
          idle_min, focus_score, top_app, top_distraction, ai_report))
    conn.commit()
    conn.close()


def get_week_summary():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM daily_summary ORDER BY date DESC LIMIT 7"
    ).fetchall()
    conn.close()
    return rows