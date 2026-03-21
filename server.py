# LifeTrack - server.py
# Run: python server.py
# Then open: http://localhost:5000

from flask import Flask, jsonify, render_template_string
import sqlite3
import os
from datetime import datetime, timedelta
from config import DB_PATH

app = Flask(__name__)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fmt(minutes):
    if minutes < 60:
        return f"{int(minutes)}m"
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h}h {m}m" if m else f"{h}h"

# ─── API: today's stats ────────────────────────────────────────────────────────
@app.route("/api/today")
def api_today():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_conn()

    # Category totals
    rows = conn.execute("""
        SELECT category, is_idle, COUNT(*) as mins
        FROM activity_log WHERE date=?
        GROUP BY category, is_idle
    """, (today,)).fetchall()

    cats = {"study":0,"distraction":0,"break":0,"idle":0,"unknown":0}
    for r in rows:
        if r["is_idle"]:
            cats["idle"] += r["mins"]
        else:
            cats[r["category"] or "unknown"] = cats.get(r["category"] or "unknown",0) + r["mins"]

    total = sum(cats.values())
    active = cats["study"] + cats["distraction"]
    focus = max(0, min(100, int((cats["study"]/active - (cats["distraction"]/active)*0.5)*100))) if active else 0

    # Top apps
    apps = conn.execute("""
        SELECT app, COUNT(*) as mins FROM activity_log
        WHERE date=? AND is_idle=0 AND app IS NOT NULL
        GROUP BY app ORDER BY mins DESC LIMIT 6
    """, (today,)).fetchall()

    # Timeline (hourly blocks)
    timeline = conn.execute("""
        SELECT timestamp, app, category, is_idle FROM activity_log
        WHERE date=? ORDER BY timestamp ASC
    """, (today,)).fetchall()

    # AI coach from daily_summary
    summary = conn.execute("""
        SELECT ai_report FROM daily_summary WHERE date=?
    """, (today,)).fetchone()

    # Behavior flags
    late_nights = conn.execute("""
        SELECT COUNT(DISTINCT date) as n FROM activity_log
        WHERE hour >= 1 AND hour <= 4
        AND date >= date('now','-7 days')
    """).fetchone()

    distract_study = conn.execute("""
        SELECT COUNT(*) as n FROM activity_log
        WHERE date=? AND category='distraction'
    """, (today,)).fetchone()

    commits_row = conn.execute("""
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
        "ai_report": summary["ai_report"] if summary and summary["ai_report"] else "Run the tracker all day then press Ctrl+C to generate your AI coaching report.",
        "flags": {
            "late_nights": late_nights["n"] if late_nights else 0,
            "distract_mins_today": distract_study["n"] if distract_study else 0,
            "weekly_study_mins": commits_row["s"] if commits_row and commits_row["s"] else 0,
        }
    })

# ─── API: weekly trend ─────────────────────────────────────────────────────────
@app.route("/api/weekly")
def api_weekly():
    conn = get_conn()
    rows = conn.execute("""
        SELECT date, study_minutes, distract_minutes, focus_score
        FROM daily_summary
        ORDER BY date DESC LIMIT 14
    """).fetchall()
    conn.close()

    # Fill missing days with zeros
    today = datetime.now().date()
    data = {r["date"]: dict(r) for r in rows}
    result = []
    for i in range(13, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        day_label = (today - timedelta(days=i)).strftime("%a")
        entry = data.get(d, {})
        result.append({
            "date": d,
            "label": day_label,
            "study": entry.get("study_minutes", 0),
            "distraction": entry.get("distract_minutes", 0),
            "focus_score": entry.get("focus_score", 0),
        })

    return jsonify(result)

# ─── API: live status (updates every 60s) ─────────────────────────────────────
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

# ─── Main dashboard page ───────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

# ─── HTML template (inline for single-file simplicity) ────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LifeTrack</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f4f0;color:#1a1a18;font-size:14px}
.wrap{max-width:1100px;margin:0 auto;padding:24px 20px}
.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
.header h1{font-size:20px;font-weight:600}
.header p{font-size:12px;color:#888780;margin-top:3px}
.live-dot{width:8px;height:8px;border-radius:50%;background:#639922;display:inline-block;margin-right:6px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.live-status{font-size:12px;color:#888780;display:flex;align-items:center}
.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-bottom:16px}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-bottom:14px}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:14px}
.card{background:#fff;border-radius:12px;border:0.5px solid #e8e6e0;padding:16px 18px}
.metric{background:#f1efe8;border-radius:8px;padding:14px;text-align:center}
.metric-val{font-size:24px;font-weight:600;margin-bottom:3px}
.metric-lbl{font-size:11px;color:#888780}
.sec{font-size:10px;font-weight:700;color:#888780;letter-spacing:.08em;margin-bottom:12px}
.tl-row{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.tl-time{font-size:10px;color:#888780;min-width:42px;text-align:right}
.tl-bar{height:20px;border-radius:4px;display:flex;align-items:center;padding:0 8px;transition:width .3s}
.tl-lbl{font-size:10px;font-weight:500;white-space:nowrap;overflow:hidden}
.ring-wrap{display:flex;align-items:center;gap:16px;margin-bottom:16px}
.ring-big{font-size:36px;font-weight:700}
.ring-sub{font-size:12px;color:#888780;margin-top:3px}
.flag-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:0.5px solid #f1efe8}
.flag-row:last-child{border-bottom:none}
.flag-text{font-size:12px;color:#444441}
.badge{font-size:11px;font-weight:500;padding:2px 8px;border-radius:4px}
.bad{background:#FCEBEB;color:#791F1F}
.warn{background:#FAEEDA;color:#633806}
.good{background:#EAF3DE;color:#27500A}
.app-row{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.app-name{font-size:12px;color:#1a1a18;min-width:140px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-bg{flex:1;background:#f1efe8;border-radius:3px;height:6px}
.bar-fill{height:6px;border-radius:3px;transition:width .5s}
.app-time{font-size:11px;color:#888780;min-width:40px;text-align:right}
.ai-box{border-left:3px solid #7F77DD;padding:12px 16px;background:#EEEDFE;font-size:13px;color:#26215C;line-height:1.8}
.refresh-btn{font-size:11px;color:#888780;border:0.5px solid #e8e6e0;background:#fff;padding:4px 10px;border-radius:6px;cursor:pointer}
.refresh-btn:hover{background:#f5f4f0}
</style>
</head>
<body>
<div class="wrap">

  <div class="header">
    <div>
      <h1>LifeTrack</h1>
      <p id="date-str">Loading...</p>
    </div>
    <div style="display:flex;align-items:center;gap:12px">
      <div class="live-status"><span class="live-dot"></span><span id="live-app">Tracking...</span></div>
      <button class="refresh-btn" onclick="loadAll()">Refresh</button>
    </div>
  </div>

  <div class="grid4" id="metric-cards">
    <div class="metric"><div class="metric-val" style="color:#888780">--</div><div class="metric-lbl">Real study</div></div>
    <div class="metric"><div class="metric-val" style="color:#888780">--</div><div class="metric-lbl">Distraction</div></div>
    <div class="metric"><div class="metric-val" style="color:#888780">--</div><div class="metric-lbl">Break</div></div>
    <div class="metric"><div class="metric-val" style="color:#888780">--</div><div class="metric-lbl">Focus score</div></div>
  </div>

  <div class="grid2">

    <div class="card">
      <div class="sec">TODAY'S TIMELINE</div>
      <div id="timeline">Loading...</div>
    </div>

    <div>
      <div class="card" style="margin-bottom:14px">
        <div class="sec">FOCUS SCORE</div>
        <div class="ring-wrap">
          <svg width="72" height="72" viewBox="0 0 72 72">
            <circle cx="36" cy="36" r="28" fill="none" stroke="#f1efe8" stroke-width="7"/>
            <circle id="score-ring" cx="36" cy="36" r="28" fill="none" stroke="#639922" stroke-width="7"
              stroke-dasharray="0 176" stroke-dashoffset="44" stroke-linecap="round"
              style="transition:stroke-dasharray .8s ease"/>
            <text id="score-text" x="36" y="41" text-anchor="middle" font-size="15" font-weight="700" fill="#1a1a18">--</text>
          </svg>
          <div>
            <div class="ring-big" id="score-big">--<span style="font-size:18px;color:#888780">/100</span></div>
            <div class="ring-sub" id="score-label">Loading...</div>
          </div>
        </div>
        <div class="sec">BEHAVIOR FLAGS</div>
        <div id="flags">Loading...</div>
      </div>
    </div>

  </div>

  <div class="grid2">
    <div class="card">
      <div class="sec">TOP APPS TODAY</div>
      <div id="top-apps">Loading...</div>
    </div>
    <div class="card">
      <div class="sec">AI COACH</div>
      <div class="ai-box" id="ai-report">Loading your coaching report...</div>
    </div>
  </div>

  <div class="card" style="margin-bottom:14px">
    <div class="sec">14-DAY STUDY TREND</div>
    <div style="position:relative;height:180px"><canvas id="weekChart"></canvas></div>
  </div>

  <div class="card">
    <div class="sec">FOCUS SCORE OVER TIME</div>
    <div style="position:relative;height:160px"><canvas id="scoreChart"></canvas></div>
  </div>

</div>

<script>
let weekChart, scoreChart;

const CAT_COLORS = {
  study: '#C0DD97', distraction: '#F09595',
  break: '#FAC775', idle: '#D3D1C7', unknown: '#D3D1C7'
};
const APP_COLORS = ['#639922','#378ADD','#E24B4A','#BA7517','#534AB7','#888780'];

function fmt(m) {
  if (m < 60) return Math.round(m) + 'm';
  return Math.floor(m/60) + 'h ' + (m%60 ? (m%60)+'m' : '');
}

function scoreLabel(s) {
  if (s >= 85) return 'Excellent — MIT mode';
  if (s >= 70) return 'Good — keep pushing';
  if (s >= 50) return 'Average — improve tomorrow';
  return 'Needs work — focus up';
}

async function loadToday() {
  const r = await fetch('/api/today');
  const d = await r.json();

  document.getElementById('date-str').textContent = d.date_pretty;

  // Metric cards
  const cards = document.getElementById('metric-cards');
  cards.innerHTML = `
    <div class="metric"><div class="metric-val" style="color:#3B6D11">${d.study_fmt}</div><div class="metric-lbl">Real study</div></div>
    <div class="metric"><div class="metric-val" style="color:#A32D2D">${d.distraction_fmt}</div><div class="metric-lbl">Distraction</div></div>
    <div class="metric"><div class="metric-val" style="color:#854F0B">${d.break_fmt}</div><div class="metric-lbl">Break</div></div>
    <div class="metric"><div class="metric-val" style="color:#534AB7">${d.focus_score}/100</div><div class="metric-lbl">Focus score</div></div>
  `;

  // Focus ring
  const circ = 176;
  const filled = (d.focus_score / 100) * circ;
  document.getElementById('score-ring').setAttribute('stroke-dasharray', `${filled} ${circ - filled}`);
  document.getElementById('score-text').textContent = d.focus_score;
  document.getElementById('score-big').innerHTML = `${d.focus_score}<span style="font-size:18px;color:#888780">/100</span>`;
  document.getElementById('score-label').textContent = scoreLabel(d.focus_score);

  // Timeline
  const tl = document.getElementById('timeline');
  if (!d.timeline || d.timeline.length === 0) {
    tl.innerHTML = '<p style="color:#888780;font-size:12px">No data yet — start the tracker.</p>';
  } else {
    const maxW = 260;
    // Group consecutive same-category entries
    const groups = [];
    let cur = null;
    for (const e of d.timeline) {
      const cat = e.idle ? 'idle' : (e.category || 'unknown');
      if (cur && cur.cat === cat && cur.app === e.app) {
        cur.count++;
      } else {
        if (cur) groups.push(cur);
        cur = {cat, app: e.app || 'Unknown', ts: e.ts, count: 1};
      }
    }
    if (cur) groups.push(cur);

    const maxCount = Math.max(...groups.map(g => g.count), 1);
    tl.innerHTML = groups.slice(-14).map(g => {
      const w = Math.max(30, Math.round((g.count / maxCount) * maxW));
      const time = g.ts ? g.ts.substring(11,16) : '';
      const label = g.app !== 'Unknown' ? g.app : g.cat;
      return `<div class="tl-row">
        <span class="tl-time">${time}</span>
        <div class="tl-bar" style="width:${w}px;background:${CAT_COLORS[g.cat]||'#D3D1C7'}">
          <span class="tl-lbl" style="color:${g.cat==='study'?'#27500A':g.cat==='distraction'?'#791F1F':'#633806'}">${label}</span>
        </div>
      </div>`;
    }).join('');
  }

  // Flags
  const f = d.flags;
  document.getElementById('flags').innerHTML = `
    <div class="flag-row"><span class="flag-text">Late nights this week</span><span class="badge ${f.late_nights>2?'bad':f.late_nights>0?'warn':'good'}">${f.late_nights} nights</span></div>
    <div class="flag-row"><span class="flag-text">Distraction time today</span><span class="badge ${f.distract_mins_today>60?'bad':f.distract_mins_today>30?'warn':'good'}">${fmt(f.distract_mins_today)}</span></div>
    <div class="flag-row"><span class="flag-text">Weekly study total</span><span class="badge ${f.weekly_study_mins>600?'good':f.weekly_study_mins>300?'warn':'bad'}">${fmt(f.weekly_study_mins)}</span></div>
  `;

  // Top apps
  const maxMins = d.top_apps.length ? d.top_apps[0].mins : 1;
  document.getElementById('top-apps').innerHTML = d.top_apps.length
    ? d.top_apps.map((a,i) => `
      <div class="app-row">
        <span class="app-name">${a.app}</span>
        <div class="bar-bg"><div class="bar-fill" style="width:${Math.round((a.mins/maxMins)*100)}%;background:${APP_COLORS[i]||'#888780'}"></div></div>
        <span class="app-time">${a.fmt}</span>
      </div>`).join('')
    : '<p style="color:#888780;font-size:12px">No data yet.</p>';

  // AI report
  document.getElementById('ai-report').textContent = d.ai_report;
}

async function loadWeekly() {
  const r = await fetch('/api/weekly');
  const data = await r.json();

  const labels = data.map(d => d.label);
  const study  = data.map(d => Math.round(d.study / 60 * 10) / 10);
  const dist   = data.map(d => Math.round(d.distraction / 60 * 10) / 10);
  const scores = data.map(d => d.focus_score);

  if (weekChart) weekChart.destroy();
  weekChart = new Chart(document.getElementById('weekChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {label:'Study',data:study,backgroundColor:'#C0DD97',borderRadius:4,stack:'a'},
        {label:'Distraction',data:dist,backgroundColor:'#F09595',borderRadius:4,stack:'a'}
      ]
    },
    options: {
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{
        x:{grid:{display:false},ticks:{font:{size:10},color:'#888780'},stacked:true},
        y:{grid:{color:'#f1efe8'},ticks:{font:{size:10},color:'#888780',callback:v=>v+'h'},stacked:true}
      }
    }
  });

  if (scoreChart) scoreChart.destroy();
  scoreChart = new Chart(document.getElementById('scoreChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label:'Focus score',data:scores,
        borderColor:'#7F77DD',backgroundColor:'#EEEDFE',
        fill:true,tension:0.4,pointRadius:4,
        pointBackgroundColor:'#7F77DD',borderWidth:2
      }]
    },
    options: {
      responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{
        x:{grid:{display:false},ticks:{font:{size:10},color:'#888780'}},
        y:{min:0,max:100,grid:{color:'#f1efe8'},ticks:{font:{size:10},color:'#888780',callback:v=>v+'/100'}}
      }
    }
  });
}

async function loadLive() {
  const r = await fetch('/api/live');
  const d = await r.json();
  const el = document.getElementById('live-app');
  if (d.app && d.app !== 'Nothing yet') {
    el.textContent = `Now: ${d.app}`;
  }
}

async function loadAll() {
  await Promise.all([loadToday(), loadWeekly(), loadLive()]);
}

loadAll();
setInterval(loadLive, 60000);
setInterval(loadAll, 300000);
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("""
==========================================
     LIFETRACK DASHBOARD
     Open: http://localhost:5000
==========================================
    """)
    app.run(host="0.0.0.0", port=5000, debug=False)
