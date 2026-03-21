# LifeTrack Setup Script
# Run this once to write all files correctly
# Usage: powershell -ExecutionPolicy Bypass -File setup.ps1

Write-Host "Writing LifeTrack files..." -ForegroundColor Cyan

# ─── config.py ────────────────────────────────────────────────────────────────
Set-Content config.py @'
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "lifetrack.db")
TRACK_INTERVAL_SECONDS = 60
IDLE_THRESHOLD_SECONDS = 300
CHROME_HISTORY_PATH = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\History")

APP_CATEGORIES = {
    "code": "study", "visual studio": "study", "pycharm": "study",
    "jupyter": "study", "notion": "study", "obsidian": "study",
    "word": "study", "docs": "study", "stackoverflow": "study",
    "github": "study", "leetcode": "study", "coursera": "study",
    "khan": "study", "claude": "study", "chatgpt": "study",
    "wikipedia": "study",
    "youtube": "distraction", "instagram": "distraction",
    "twitter": "distraction", "facebook": "distraction",
    "netflix": "distraction", "reddit": "distraction",
    "tiktok": "distraction", "snapchat": "distraction",
    "whatsapp": "distraction", "telegram": "distraction",
    "discord": "distraction", "spotify": "distraction",
    "steam": "distraction", "game": "distraction",
    "file explorer": "break", "settings": "break",
    "calculator": "break", "task manager": "break",
}

GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL   = "llama-3.3-70b-versatile"
REPORT_HOUR   = 23
REPORT_MINUTE = 0
'@

# ─── database.py ──────────────────────────────────────────────────────────────
Set-Content database.py @'
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
        CREATE TABLE IF NOT EXISTS browser_history (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            date      TEXT NOT NULL,
            url       TEXT,
            title     TEXT,
            category  TEXT
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
        "SELECT * FROM activity_log WHERE date = ? ORDER BY timestamp ASC",
        (today,)).fetchall()
    conn.close()
    return rows

def get_today_minutes_by_category():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute("""
        SELECT category, is_idle, COUNT(*) as count
        FROM activity_log WHERE date = ?
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
        SELECT app, COUNT(*) as minutes FROM activity_log
        WHERE date = ? AND is_idle = 0 AND app IS NOT NULL
        GROUP BY app ORDER BY minutes DESC LIMIT ?
    """, (today, limit)).fetchall()
    conn.close()
    return rows

def get_top_distractions_today(limit=3):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    rows = conn.execute("""
        SELECT app, COUNT(*) as minutes FROM activity_log
        WHERE date = ? AND category = 'distraction'
        GROUP BY app ORDER BY minutes DESC LIMIT ?
    """, (today, limit)).fetchall()
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
'@

# ─── classifier.py ────────────────────────────────────────────────────────────
Set-Content classifier.py @'
from config import APP_CATEGORIES

def classify_window(window_title: str, app_name: str) -> str:
    if not window_title and not app_name:
        return "unknown"
    combined = f"{window_title} {app_name}".lower()
    for keyword, category in APP_CATEGORIES.items():
        if keyword in combined:
            return category
    return "unknown"

def classify_url(url: str) -> str:
    if not url:
        return "unknown"
    for keyword, category in APP_CATEGORIES.items():
        if keyword in url.lower():
            return category
    return "unknown"

def get_app_name_from_window(window_title: str) -> str:
    if not window_title:
        return "Unknown"
    for sep in [" - ", " | ", " - "]:
        if sep in window_title:
            parts = window_title.split(sep)
            return parts[-1].strip()
    return window_title[:30]
'@

# ─── tracker.py ───────────────────────────────────────────────────────────────
Set-Content tracker.py @'
import time
import os
import shutil
import sqlite3
import platform
from datetime import datetime, timedelta
from config import TRACK_INTERVAL_SECONDS, IDLE_THRESHOLD_SECONDS, CHROME_HISTORY_PATH
from classifier import classify_window, classify_url, get_app_name_from_window
from database import log_activity, log_browser_history

_win_ok = False
if platform.system() == "Windows":
    try:
        import pygetwindow as gw
        import pynput.keyboard as kb
        import pynput.mouse as ms
        _win_ok = True
    except ImportError:
        print("[Tracker] WARNING: pygetwindow or pynput not installed.")
        print("[Tracker] Run: pip install pygetwindow pynput")

_last_input = datetime.now()

def _on_activity(*a, **k):
    global _last_input
    _last_input = datetime.now()

def start_input_listeners():
    if not _win_ok:
        return
    kb.Listener(on_press=_on_activity, daemon=True).start()
    ms.Listener(on_move=_on_activity, on_click=_on_activity, daemon=True).start()

def is_idle():
    return (datetime.now() - _last_input).total_seconds() >= IDLE_THRESHOLD_SECONDS

def get_active_window():
    if not _win_ok:
        return ("Unknown Window", "Unknown App")
    try:
        win = gw.getActiveWindow()
        if win is None:
            return ("", "Unknown")
        title = win.title or ""
        app = get_app_name_from_window(title)
        return (title, app)
    except Exception:
        return ("", "Unknown")

_last_chrome = None

def import_chrome_history():
    global _last_chrome
    now = datetime.now()
    if _last_chrome and (now - _last_chrome).seconds < 3600:
        return
    if not os.path.exists(CHROME_HISTORY_PATH):
        return
    tmp = CHROME_HISTORY_PATH + "_tmp"
    try:
        shutil.copy2(CHROME_HISTORY_PATH, tmp)
        conn = sqlite3.connect(tmp)
        conn.row_factory = sqlite3.Row
        epoch = datetime(1601, 1, 1)
        cutoff = int(((now - timedelta(hours=1)) - epoch).total_seconds() * 1_000_000)
        rows = conn.execute(
            "SELECT url, title, last_visit_time FROM urls WHERE last_visit_time > ? ORDER BY last_visit_time DESC LIMIT 200",
            (cutoff,)).fetchall()
        conn.close()
        entries = []
        for row in rows:
            ts = (epoch + timedelta(microseconds=row["last_visit_time"])).strftime("%Y-%m-%dT%H:%M:%S")
            entries.append((ts, row["url"], row["title"], classify_url(row["url"])))
        if entries:
            log_browser_history(entries)
            print(f"[Tracker] Imported {len(entries)} Chrome entries.")
    except Exception as e:
        print(f"[Tracker] Chrome error: {e}")
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass
    _last_chrome = now

def run_tracker():
    print("[Tracker] Started. Logging every 60 seconds...")
    start_input_listeners()
    while True:
        try:
            idle = is_idle()
            title, app = get_active_window()
            category = classify_window(title, app)
            log_activity(window=title, app=app, url=None, category=category, is_idle=idle)
            status = "IDLE" if idle else category.upper()
            print(f"[{datetime.now().strftime('%H:%M')}] {status} — {app}")
            import_chrome_history()
        except Exception as e:
            print(f"[Tracker] Error: {e}")
        time.sleep(TRACK_INTERVAL_SECONDS)
'@

# ─── reporter.py ──────────────────────────────────────────────────────────────
Set-Content reporter.py @'
from datetime import datetime
from config import GROQ_API_KEY, GROQ_MODEL
from database import (get_today_minutes_by_category, get_top_apps_today,
                      get_top_distractions_today, save_daily_summary)

def fmt(minutes):
    if minutes < 60:
        return f"{minutes}m"
    return f"{minutes//60}h {minutes%60}m" if minutes%60 else f"{minutes//60}h"

def focus_score(study, distract, total):
    if total == 0:
        return 0
    score = int((study/total - (distract/total)*0.5) * 100)
    return max(0, min(100, score))

def get_ai_coaching(study, distract, break_t, idle, score, top_apps, top_dist):
    if GROQ_API_KEY == "your_groq_api_key_here":
        return "Add your Groq API key in config.py to get AI coaching."
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        apps = ", ".join([f"{r['app']}({r['minutes']}min)" for r in top_apps])
        dist = ", ".join([f"{r['app']}({r['minutes']}min)" for r in top_dist])
        prompt = f"""You are a brutally honest AI life coach for Gurneev, a 16-year-old developer targeting MIT.

Today:
- Study time: {fmt(study)}
- Distraction: {fmt(distract)}
- Break: {fmt(break_t)}
- Idle: {fmt(idle)}
- Focus score: {score}/100
- Top apps: {apps or 'none'}
- Top distractions: {dist or 'none'}

Write 4-5 sentences: one thing done well, one habit that hurt, one action for tomorrow, MIT reminder. Be direct. Use real numbers."""
        r = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"AI coaching unavailable: {e}"

def generate_daily_report(print_to_terminal=True):
    today = datetime.now().strftime("%Y-%m-%d")
    cats  = get_today_minutes_by_category()
    apps  = get_top_apps_today(5)
    dist  = get_top_distractions_today(3)

    study   = cats.get("study", 0)
    distract= cats.get("distraction", 0)
    break_t = cats.get("break", 0)
    idle    = cats.get("idle", 0)
    total   = study + distract + break_t + idle + cats.get("unknown", 0)
    score   = focus_score(study, distract, total)

    top_app  = apps[0]["app"] if apps else "none"
    top_dis  = dist[0]["app"] if dist else "none"
    ai       = get_ai_coaching(study, distract, break_t, idle, score, list(apps), list(dist))

    save_daily_summary(today, study, distract, break_t, idle, score, top_app, top_dis, ai)

    if print_to_terminal:
        SEP = "=" * 50
        print(f"\n{SEP}")
        print(f"  LIFETRACK — {datetime.now().strftime('%A %d %B %Y')}")
        print(SEP)
        print(f"\n  FOCUS SCORE: {score}/100")
        bar = "█"*int(score/5) + "░"*(20-int(score/5))
        print(f"  [{bar}]")
        print(f"\n  Study       {fmt(study):>10}")
        print(f"  Distraction {fmt(distract):>10}")
        print(f"  Break       {fmt(break_t):>10}")
        print(f"  Idle        {fmt(idle):>10}")
        print(f"  Total       {fmt(total):>10}")
        if apps:
            print(f"\n  TOP APPS")
            for r in apps:
                print(f"  {r['app']:<30} {fmt(r['minutes'])}")
        if dist:
            print(f"\n  DISTRACTIONS")
            for r in dist:
                print(f"  {r['app']:<30} {fmt(r['minutes'])}")
        print(f"\n  AI COACH:")
        print(f"  {ai}")
        print(f"\n{SEP}\n")

    return {"date": today, "study": study, "distraction": distract,
            "focus_score": score, "ai_report": ai}
'@

# ─── main.py ──────────────────────────────────────────────────────────────────
Set-Content main.py @'
import sys
import threading
import schedule
import time
from datetime import datetime
from database import init_db
from tracker  import run_tracker
from reporter import generate_daily_report
from config   import REPORT_HOUR, REPORT_MINUTE

def schedule_daily_report():
    t = f"{REPORT_HOUR:02d}:{REPORT_MINUTE:02d}"
    schedule.every().day.at(t).do(generate_daily_report)
    print(f"[Main] Auto report at {t} every night")
    while True:
        schedule.run_pending()
        time.sleep(30)

def main():
    print("""
==========================================
           LIFETRACK v1.0
    Your brutal honest life tracker
==========================================
    """)
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        init_db()
        generate_daily_report(print_to_terminal=True)
        return

    init_db()
    print(f"[Main] Started at {datetime.now().strftime('%H:%M:%S')}")
    print("[Main] Ctrl+C to stop and generate report.\n")

    threading.Thread(target=run_tracker, daemon=True).start()
    threading.Thread(target=schedule_daily_report, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Main] Generating final report...")
        generate_daily_report(print_to_terminal=True)
        print("[Main] Done. See you tomorrow.")

if __name__ == "__main__":
    main()
'@

Write-Host ""
Write-Host "All files written successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. pip install groq pygetwindow pynput schedule"
Write-Host "  2. Add your Groq key in config.py"
Write-Host "  3. python main.py"
Write-Host ""
