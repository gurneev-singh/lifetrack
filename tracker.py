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
