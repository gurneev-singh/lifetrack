let weekChart, scoreChart;
let allScreenshots = [];
let currentFilter = 'all';
let ssExpanded = false;
let showAll = false;
const SHOW_LIMIT = 15;

const CAT_COLORS = {study:'#639922',distraction:'#E24B4A',break:'#BA7517',idle:'#888780',unknown:'#888780'};
const APP_COLORS = ['#639922','#378ADD','#E24B4A','#BA7517','#534AB7','#888780'];

function fmt(m) {
    m = Math.round(m);
    if (m < 60) return m + 'm';
    const h = Math.floor(m/60), min = m%60;
    return min ? h+'h '+min+'m' : h+'h';
}

function scoreLabel(s) {
    if (s >= 85) return 'Excellent — MIT mode';
    if (s >= 70) return 'Good — keep pushing';
    if (s >= 50) return 'Average — improve tomorrow';
    return 'Needs work — focus up';
}

function catBadgeClass(cat) {
    return {study:'ss-study',distraction:'ss-distraction',break:'ss-break'}[cat] || 'ss-unknown';
}

// ─── Collapsible toggle ───────────────────────────────────────────────────────
function toggleScreenshots() {
    ssExpanded = !ssExpanded;
    const body = document.getElementById('ss-body');
    const arrow = document.getElementById('ss-arrow');
    body.classList.toggle('open', ssExpanded);
    arrow.classList.toggle('open', ssExpanded);
}

// ─── Filter buttons ───────────────────────────────────────────────────────────
function filterScreenshots(cat, btn) {
    currentFilter = cat;
    showAll = false;
    document.querySelectorAll('.ss-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderScreenshotFeed();
}

// ─── Render screenshot feed ───────────────────────────────────────────────────
function renderScreenshotFeed() {
    const el = document.getElementById('screenshot-feed');
    const countEl = document.getElementById('ss-visible-count');

    if (!allScreenshots.length) {
        el.innerHTML = '<div class="empty">No AI descriptions yet. Make sure main.py is running with screenshot analyzer.</div>';
        countEl.textContent = '';
        return;
    }

    const filtered = currentFilter === 'all'
        ? allScreenshots
        : allScreenshots.filter(s => s.category === currentFilter);

    const visible = showAll ? filtered : filtered.slice(0, SHOW_LIMIT);
    countEl.textContent = `${filtered.length} entries`;

    el.innerHTML = visible.map(s => {
        const time = s.timestamp ? s.timestamp.substring(11,16) : '';
        return `<div class="ss-row">
            <span class="ss-time">${time}</span>
            <span class="ss-badge ${catBadgeClass(s.category)}">${s.category}</span>
            <div>
                <div class="ss-desc">${s.description}</div>
                <div class="ss-app">${s.app || ''}</div>
            </div>
        </div>`;
    }).join('');

    // Show more button
    if (!showAll && filtered.length > SHOW_LIMIT) {
        el.innerHTML += `<button class="ss-show-more" onclick="expandAll()">Show all ${filtered.length} entries</button>`;
    } else if (showAll && filtered.length > SHOW_LIMIT) {
        el.innerHTML += `<button class="ss-show-more" onclick="collapseAll()">Show less</button>`;
    }
}

function expandAll() { showAll = true; renderScreenshotFeed(); }
function collapseAll() { showAll = false; renderScreenshotFeed(); }

// ─── Load today ───────────────────────────────────────────────────────────────
async function loadToday() {
    const r = await fetch('/api/today');
    const d = await r.json();

    document.getElementById('date-str').textContent = d.date_pretty;

    document.getElementById('metric-cards').innerHTML = `
        <div class="metric"><div class="metric-val" style="color:#3B6D11">${d.study_fmt}</div><div class="metric-lbl">Real study</div></div>
        <div class="metric"><div class="metric-val" style="color:#A32D2D">${d.distraction_fmt}</div><div class="metric-lbl">Distraction</div></div>
        <div class="metric"><div class="metric-val" style="color:#854F0B">${d.break_fmt}</div><div class="metric-lbl">Break</div></div>
        <div class="metric"><div class="metric-val" style="color:#534AB7">${d.focus_score}/100</div><div class="metric-lbl">Focus score</div></div>
    `;

    const filled = (d.focus_score/100)*176;
    document.getElementById('score-ring').setAttribute('stroke-dasharray', `${filled} ${176-filled}`);
    document.getElementById('score-text').textContent = d.focus_score;
    document.getElementById('score-big').innerHTML = `${d.focus_score}<span style="font-size:18px;color:#888780">/100</span>`;
    document.getElementById('score-label').textContent = scoreLabel(d.focus_score);

    // Activity feed
    const feed = document.getElementById('activity-feed');
    if (!d.timeline || !d.timeline.length) {
        feed.innerHTML = '<div class="empty">No data yet — start the tracker.</div>';
    } else {
        const groups = [];
        let cur = null;
        for (const e of d.timeline) {
            const cat = e.idle ? 'idle' : (e.category||'unknown');
            if (cur && cur.cat===cat && cur.app===e.app) { cur.count++; }
            else { if (cur) groups.push(cur); cur={cat,app:e.app||'Unknown',ts:e.ts,count:1}; }
        }
        if (cur) groups.push(cur);
        feed.innerHTML = groups.slice(-12).map(g => {
            const time = g.ts ? g.ts.substring(11,16) : '';
            return `<div class="feed-row">
                <span class="feed-time">${time}</span>
                <span class="feed-cat" style="background:${CAT_COLORS[g.cat]||'#888'}"></span>
                <div><div class="feed-desc">${g.app}</div><div class="feed-app">${g.cat} — ${g.count} min</div></div>
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
                <div class="bar-bg"><div class="bar-fill" style="width:${Math.round((a.mins/maxMins)*100)}%;background:${APP_COLORS[i]||'#888'}"></div></div>
                <span class="app-time">${a.fmt}</span>
            </div>`).join('')
        : '<div class="empty">No data yet.</div>';

    document.getElementById('ai-report').textContent = d.ai_report;
}

// ─── Load screenshots ─────────────────────────────────────────────────────────
async function loadScreenshots() {
    const r = await fetch('/api/screenshots?limit=200');
    allScreenshots = await r.json();

    // Update count badge on header
    document.getElementById('ss-count-badge').textContent = allScreenshots.length
        ? `${allScreenshots.length} entries`
        : '';

    renderScreenshotFeed();
}

// ─── Load weekly charts ───────────────────────────────────────────────────────
async function loadWeekly() {
    const r = await fetch('/api/weekly');
    const data = await r.json();
    const labels = data.map(d => d.label);
    const study = data.map(d => Math.round(d.study/60*10)/10);
    const dist = data.map(d => Math.round(d.distraction/60*10)/10);
    const scores = data.map(d => d.focus_score);

    if (weekChart) weekChart.destroy();
    weekChart = new Chart(document.getElementById('weekChart'), {
        type:'bar',
        data:{labels,datasets:[
            {label:'Study',data:study,backgroundColor:'#C0DD97',borderRadius:4,stack:'a'},
            {label:'Distraction',data:dist,backgroundColor:'#F09595',borderRadius:4,stack:'a'}
        ]},
        options:{responsive:true,maintainAspectRatio:false,
            plugins:{legend:{display:false}},
            scales:{
                x:{grid:{display:false},ticks:{font:{size:10},color:'#888780'},stacked:true},
                y:{grid:{color:'#f1efe8'},ticks:{font:{size:10},color:'#888780',callback:v=>v+'h'},stacked:true}
            }}
    });

    if (scoreChart) scoreChart.destroy();
    scoreChart = new Chart(document.getElementById('scoreChart'), {
        type:'line',
        data:{labels,datasets:[{
            label:'Focus score',data:scores,
            borderColor:'#7F77DD',backgroundColor:'#EEEDFE',
            fill:true,tension:0.4,pointRadius:4,pointBackgroundColor:'#7F77DD',borderWidth:2
        }]},
        options:{responsive:true,maintainAspectRatio:false,
            plugins:{legend:{display:false}},
            scales:{
                x:{grid:{display:false},ticks:{font:{size:10},color:'#888780'}},
                y:{min:0,max:100,grid:{color:'#f1efe8'},ticks:{font:{size:10},color:'#888780',callback:v=>v+'/100'}}
            }}
    });
}

// ─── Load live status ─────────────────────────────────────────────────────────
async function loadLive() {
    try {
        const r = await fetch('/api/live');
        const d = await r.json();
        if (d.app && d.app !== 'Nothing yet') {
            document.getElementById('live-app').textContent = 'Now: ' + d.app;
            document.getElementById('dot').className = 'live-dot on';
        }
    } catch {}
}

async function loadAll() {
    await Promise.all([loadToday(), loadScreenshots(), loadWeekly(), loadLive()]);
}

loadAll();
setInterval(loadLive, 60000);
setInterval(loadAll, 300000);