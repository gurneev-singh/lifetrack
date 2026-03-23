# LifeTrack - server.py
# Run: python server.py
# Then open: http://localhost:5000

from flask import Flask, jsonify, render_template, request
import sqlite3
from datetime import datetime, timedelta
from core.config import DB_PATH
from features.tracking.cross_verify import cross_verify_today
from features.tracking.face_profile import delete_face_profile, get_status, is_registered
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from core.logger import setup_server_logging

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

app = Flask(__name__,
    template_folder=os.path.join(ROOT, 'templates'),
    static_folder=os.path.join(ROOT, 'static')
)
setup_server_logging(app)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fmt(minutes):
    minutes = int(minutes or 0)
    if minutes < 60:
        return f"{minutes}m"
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m}m" if m else f"{h}h"

# ─── Main dashboard ────────────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# ─── Mobile PWA ────────────────────────────────────────────────────────────────
@app.route("/mobile")
def mobile():
    return render_template("mobile.html")

# ─── API: today's stats ────────────────────────────────────────────────────────
@app.route("/api/today")
def api_today():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()

    # Category totals — prefer screenshot_log if available
    ss_count = conn.execute(
        "SELECT COUNT(*) as n FROM screenshot_log WHERE date=?", (today,)
    ).fetchone()["n"] if table_exists(conn, "screenshot_log") else 0

    if ss_count > 0:
        rows = conn.execute("""
            SELECT category, COUNT(*) as mins
            FROM screenshot_log WHERE date=?
            GROUP BY category
        """, (today,)).fetchall()
        cats = {"study": 0, "distraction": 0, "break": 0, "idle": 0, "unknown": 0}
        for r in rows:
            cats[r["category"] or "unknown"] = cats.get(r["category"] or "unknown", 0) + r["mins"]
    else:
        rows = conn.execute("""
            SELECT category, is_idle, COUNT(*) as mins
            FROM activity_log WHERE date=?
            GROUP BY category, is_idle
        """, (today,)).fetchall()
        cats = {"study": 0, "distraction": 0, "break": 0, "idle": 0, "unknown": 0}
        for r in rows:
            if r["is_idle"]:
                cats["idle"] += r["mins"]
            else:
                cats[r["category"] or "unknown"] = cats.get(r["category"] or "unknown", 0) + r["mins"]

    total = sum(cats.values())
    active = cats["study"] + cats["distraction"]
    focus = max(0, min(100, int((cats["study"] / active - (cats["distraction"] / active) * 0.5) * 100))) if active else 0

    # Top apps
    apps = []
    if table_exists(conn, "screenshot_log") and ss_count > 0:
        apps = conn.execute("""
            SELECT app, COUNT(*) as mins FROM screenshot_log
            WHERE date=? AND app IS NOT NULL
            GROUP BY app ORDER BY mins DESC LIMIT 6
        """, (today,)).fetchall()
    if not apps:
        apps = conn.execute("""
            SELECT app, COUNT(*) as mins FROM activity_log
            WHERE date=? AND is_idle=0 AND app IS NOT NULL
            GROUP BY app ORDER BY mins DESC LIMIT 6
        """, (today,)).fetchall()

    # Timeline
    timeline = conn.execute("""
        SELECT timestamp, app, category, is_idle FROM activity_log
        WHERE date=? ORDER BY timestamp ASC
    """, (today,)).fetchall()

    # AI coach
    summary = conn.execute(
        "SELECT ai_report FROM daily_summary WHERE date=?", (today,)
    ).fetchone()

    # Flags
    late_nights = conn.execute("""
        SELECT COUNT(DISTINCT date) as n FROM activity_log
        WHERE hour >= 1 AND hour <= 4 AND date >= date('now','-7 days')
    """).fetchone()

    distract_today = conn.execute("""
        SELECT COUNT(*) as n FROM activity_log
        WHERE date=? AND category='distraction'
    """, (today,)).fetchone()

    weekly_study = conn.execute("""
        SELECT SUM(study_minutes) as s FROM daily_summary
        WHERE date >= date('now','-7 days')
    """).fetchone()

    conn.close()

    return jsonify({
        "date": today,
        "date_pretty": datetime.now().strftime("%A, %d %B %Y"),
        "study": cats["study"],
        "distraction": cats["distraction"],
        "break": cats["break"],
        "idle": cats["idle"],
        "total": total,
        "focus_score": focus,
        "study_fmt": fmt(cats["study"]),
        "distraction_fmt": fmt(cats["distraction"]),
        "break_fmt": fmt(cats["break"]),
        "idle_fmt": fmt(cats["idle"]),
        "top_apps": [{"app": r["app"], "mins": r["mins"], "fmt": fmt(r["mins"])} for r in apps],
        "timeline": [{"ts": r["timestamp"], "app": r["app"], "category": r["category"], "idle": r["is_idle"]} for r in timeline],
        "ai_report": summary["ai_report"] if summary and summary["ai_report"] else "Run tracker all day then press Ctrl+C to generate your AI coaching report.",
        "flags": {
            "late_nights": late_nights["n"] if late_nights else 0,
            "distract_mins_today": distract_today["n"] if distract_today else 0,
            "weekly_study_mins": weekly_study["s"] if weekly_study and weekly_study["s"] else 0,
        }
    })

# ─── API: screenshot descriptions ─────────────────────────────────────────────
@app.route("/api/screenshots")
def api_screenshots():
    conn = get_conn()
    if not table_exists(conn, "screenshot_log"):
        conn.close()
        return jsonify([])

    limit = request.args.get("limit", 50, type=int)
    date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    rows = conn.execute("""
        SELECT timestamp, app, description, category
        FROM screenshot_log
        WHERE date=?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (date, limit)).fetchall()
    conn.close()

    return jsonify([{
        "timestamp": r["timestamp"],
        "app": r["app"],
        "description": r["description"],
        "category": r["category"]
    } for r in rows])

# ─── API: weekly trend ─────────────────────────────────────────────────────────
@app.route("/api/weekly")
def api_weekly():
    conn = get_conn()
    rows = conn.execute("""
        SELECT date, study_minutes, distract_minutes, focus_score
        FROM daily_summary ORDER BY date DESC LIMIT 14
    """).fetchall()
    conn.close()

    today = datetime.now().date()
    data = {r["date"]: dict(r) for r in rows}
    result = []
    for i in range(13, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        label = (today - timedelta(days=i)).strftime("%a")
        entry = data.get(d, {})
        result.append({
            "date": d, "label": label,
            "study": entry.get("study_minutes", 0),
            "distraction": entry.get("distract_minutes", 0),
            "focus_score": entry.get("focus_score", 0),
        })
    return jsonify(result)

# ─── API: live status ──────────────────────────────────────────────────────────
@app.route("/api/live")
def api_live():
    conn = get_conn()
    latest = conn.execute("""
        SELECT app, category, timestamp FROM activity_log
        ORDER BY timestamp DESC LIMIT 1
    """).fetchone()
    conn.close()
    if latest:
        return jsonify({"app": latest["app"], "category": latest["category"], "ts": latest["timestamp"]})
    return jsonify({"app": "Nothing yet", "category": "unknown", "ts": ""})

# ─── API: mobile log ───────────────────────────────────────────────────────────
@app.route("/api/mobile/log", methods=["POST"])
def mobile_log():
    data = request.json
    if not data:
        return jsonify({"error": "no data"}), 400
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mobile_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT, date TEXT, type TEXT,
            note TEXT, mood TEXT, duration INTEGER
        )
    """)
    now = data.get("timestamp", datetime.now().isoformat())
    conn.execute("""
        INSERT INTO mobile_log (timestamp, date, type, note, mood, duration)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now, now[:10], data.get("type"), data.get("note"),
          data.get("mood"), data.get("duration")))
    conn.commit()
    conn.close()
    return jsonify({"status": "saved"})

# ─── Helper ────────────────────────────────────────────────────────────────────
def table_exists(conn, name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None

@app.route("/api/webcam")
def api_webcam():
    """Get today's webcam entries for dashboard."""
    from core.database import get_webcam_today
    try:
        rows = get_webcam_today(limit=100)
        return jsonify([{
            "timestamp": r["timestamp"],
            "description": r["description"],
            "physical": r["physical"]
        } for r in rows])
    except Exception as e:
        return jsonify([])
 
@app.route("/api/crossverify")
def api_crossverify():
    """Get cross-verification truth analysis."""
    try:
        return jsonify(cross_verify_today())
    except Exception as e:
        return jsonify({"available": False, "reason": str(e)})

@app.route("/api/face/status")
def face_status():
    from features.tracking.face_profile import get_status
    return jsonify(get_status())
 
 
@app.route("/api/face/register", methods=["POST"])
def face_register():
    from features.tracking.face_profile import request_registration, get_registration_result
    import time
    request_registration()
    # Wait up to 30 seconds for main.py to complete registration
    for _ in range(60):
        result = get_registration_result()
        if result is not None:
            return jsonify(result)
        time.sleep(0.5)
    return jsonify({"success": False, "message": "Timed out. Make sure main.py is running."})
 
 
 
@app.route("/api/face/delete", methods=["POST"])
def face_delete():
    from features.tracking.face_profile import delete_face_profile
    success = delete_face_profile()
    return jsonify({"success": success})

# ─── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("""
==========================================
     LIFETRACK DASHBOARD
     Open: http://localhost:5000
==========================================
    """)
    app.run(host="0.0.0.0", port=5000, debug=False)