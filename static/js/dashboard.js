let weekChart, scoreChart;
let allScreenshots = [];
let currentFilter = 'all';
let ssExpanded = true;
let showAll = false;
let timeRangeStart = null;
let timeRangeEnd = null;
const SHOW_LIMIT = 20;

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

function toggleScreenshots() {
    ssExpanded = !ssExpanded;
    document.getElementById('ss-body').classList.toggle('open', ssExpanded);
    document.getElementById('ss-arrow').classList.toggle('open', ssExpanded);
}

function filterScreenshots(cat, btn) {
    currentFilter = cat;
    showAll = false;
    document.querySelectorAll('.ss-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderScreenshotFeed();
}

function applyTimeRange() {
    timeRangeStart = document.getElementById('time-start').value;
    timeRangeEnd   = document.getElementById('time-end').value;
    showAll = false;
    renderScreenshotFeed();
}

function clearTimeRange() {
    timeRangeStart = null;
    timeRangeEnd   = null;
    document.getElementById('time-start').value = '';
    document.getElementById('time-end').value   = '';
    renderScreenshotFeed();
}

function renderScreenshotFeed() {
    const el      = document.getElementById('screenshot-feed');
    const countEl = document.getElementById('ss-visible-count');

    if (!allScreenshots.length) {
        el.innerHTML = '<div class="empty">No AI descriptions yet. Make sure main.py is running.</div>';
        countEl.textContent = '';
        return;
    }

    let filtered = currentFilter === 'all'
        ? allScreenshots
        : allScreenshots.filter(s => s.category === currentFilter);

    if (timeRangeStart) filtered = filtered.filter(s => (s.timestamp||'').substring(11,16) >= timeRangeStart);
    if (timeRangeEnd)   filtered = filtered.filter(s => (s.timestamp||'').substring(11,16) <= timeRangeEnd);

    const visible = showAll ? filtered : filtered.slice(0, SHOW_LIMIT);
    countEl.textContent = filtered.length + ' entries';

    if (!visible.length) {
        el.innerHTML = '<div class="empty">No entries match this filter.</div>';
        return;
    }

    el.innerHTML = visible.map(s => {
        const time = (s.timestamp||'').substring(11,16);
        return `<div class="ss-row">
            <span class="ss-time">${time}</span>
            <span class="ss-badge ${catBadgeClass(s.category)}">${s.category}</span>
            <div>
                <div class="ss-desc">${s.description}</div>
                <div class="ss-app">${s.app||''}</div>
            </div>
        </div>`;
    }).join('');

    if (!showAll && filtered.length > SHOW_LIMIT) {
        el.innerHTML += `<button class="ss-show-more" onclick="expandAll()">Show all ${filtered.length} entries</button>`;
    } else if (showAll && filtered.length > SHOW_LIMIT) {
        el.innerHTML += `<button class="ss-show-more" onclick="collapseAll()">Show less</button>`;
    }
}

function expandAll()  { showAll = true;  renderScreenshotFeed(); }
function collapseAll(){ showAll = false; renderScreenshotFeed(); }

async function loadToday() {
    const r = await fetch('/api/today');
    const d = await r.json();

    document.getElementById('date-str').textContent = d.date_pretty;

    document.getElementById('metric-cards').innerHTML = `
        <div class="metric"><div class="metric-val" style="color:#3B6D11">${d.study_fmt}</div><div class="metric-lbl">Real study</div></div>
        <div class="metric"><div class="metric-val" style="color:#A32D2D">${d.distraction_fmt}</div><div class="metric-lbl">Distraction</div></div>
        <div class="metric"><div class="metric-val" style="color:#854F0B">${d.break_fmt}</div><div class="metric-lbl">Break</div></div>
        <div class="metric"><div class="metric-val" style="color:#534AB7">${d.focus_score}/100</div><div class="metric-lbl">Focus score</div></div>
        <div class="metric" id="truth-card" title="Matches between what apps you used and what the webcam saw."><div class="metric-val" id="truth-val">--</div><div class="metric-lbl">Truth score</div></div>
    `;

    const filled = (d.focus_score/100)*176;
    document.getElementById('score-ring').setAttribute('stroke-dasharray',`${filled} ${176-filled}`);
    document.getElementById('score-text').textContent = d.focus_score;
    document.getElementById('score-big').innerHTML = `${d.focus_score}<span style="font-size:18px;color:#888780">/100</span>`;
    document.getElementById('score-label').textContent = scoreLabel(d.focus_score);

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

    const f = d.flags;
    document.getElementById('flags').innerHTML = `
        <div class="flag-row"><span class="flag-text">Late nights this week</span><span class="badge ${f.late_nights>2?'bad':f.late_nights>0?'warn':'good'}">${f.late_nights} nights</span></div>
        <div class="flag-row"><span class="flag-text">Distraction time today</span><span class="badge ${f.distract_mins_today>60?'bad':f.distract_mins_today>30?'warn':'good'}">${fmt(f.distract_mins_today)}</span></div>
        <div class="flag-row"><span class="flag-text">Weekly study total</span><span class="badge ${f.weekly_study_mins>600?'good':f.weekly_study_mins>300?'warn':'bad'}">${fmt(f.weekly_study_mins)}</span></div>
    `;

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

async function loadScreenshots() {
    try {
        const r = await fetch('/api/screenshots?limit=200');
        allScreenshots = await r.json();
        document.getElementById('ss-count-badge').textContent =
            allScreenshots.length ? allScreenshots.length + ' entries' : '';
        renderScreenshotFeed();
    } catch {
        document.getElementById('screenshot-feed').innerHTML =
            '<div class="empty">Could not load screenshot data.</div>';
    }
}

async function loadWeekly() {
    const r = await fetch('/api/weekly');
    const data = await r.json();
    const labels = data.map(d => d.label);
    const study  = data.map(d => Math.round(d.study/60*10)/10);
    const dist   = data.map(d => Math.round(d.distraction/60*10)/10);
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

async function loadCrossVerify() {
    try {
        const r = await fetch('/api/crossverify');
        const d = await r.json();
        const el = document.getElementById('truth-val');
        if (d.available) {
            el.textContent = d.truth_score + '%';
            el.style.color = d.truth_score >= 80 ? '#3B6D11' : d.truth_score >= 50 ? '#854F0B' : '#A32D2D';
        } else {
            el.textContent = '--';
        }
    } catch {
        document.getElementById('truth-val').textContent = 'Error';
    }
}

async function loadWebcam() {
    const el = document.getElementById('webcam-feed');
    try {
        const r = await fetch('/api/webcam');
        const data = await r.json();
        if (!data || !data.length) {
            el.innerHTML = '<div class="empty">No physical data yet.</div>';
            return;
        }

        const physicalCls = {present:'ss-study', away:'ss-break', distracted:'ss-distraction', tired:'ss-unknown', break:'ss-break'};

        el.innerHTML = data.slice(0, 12).map(w => {
            const time = w.timestamp ? w.timestamp.substring(11, 16) : '';
            const cls = physicalCls[w.physical] || 'ss-unknown';
            return `<div class="feed-row">
                <span class="feed-time">${time}</span>
                <span class="ss-badge ${cls}">${w.physical}</span>
                <div><div class="ss-desc">${w.description}</div></div>
            </div>`;
        }).join('');
    } catch {
        el.innerHTML = '<div class="empty">Error loading webcam data.</div>';
    }
}

async function loadFaceStatus() {
    try {
        const r = await fetch('/api/face/status');
        const d = await r.json();
        document.getElementById('face-indicator').style.background = d.registered ? '#639922' : '#E24B4A';
        document.getElementById('face-status-text').textContent = d.registered
            ? `Face registered — ${d.encoding_count} encodings. Webcam only logs when it sees you.`
            : 'No face registered — webcam logs everyone. Register to track only yourself.';
        document.getElementById('face-btn').textContent = d.registered ? 'Re-register' : 'Register face';
        document.getElementById('face-delete-btn').style.display = d.registered ? 'inline-block' : 'none';
    } catch {
        document.getElementById('face-status-text').textContent = 'Face API unavailable.';
    }
}

async function registerFace() {
    const btn         = document.getElementById('face-btn');
    const progress    = document.getElementById('face-progress');
    const progressBar = document.getElementById('face-progress-bar');
    const progressText= document.getElementById('face-progress-text');

    btn.disabled = true;
    btn.textContent = 'Capturing...';
    progress.style.display = 'block';
    progressText.textContent = 'Look directly at your webcam...';
    progressBar.style.width = '10%';

    let fakeProgress = 10;
    const fakeInterval = setInterval(() => {
        fakeProgress = Math.min(fakeProgress + 8, 90);
        progressBar.style.width = fakeProgress + '%';
        progressText.textContent = `Capturing... ${Math.round(fakeProgress/10)} of 10 photos`;
    }, 1200);

    try {
        const r = await fetch('/api/face/register', {method:'POST'});
        const d = await r.json();
        clearInterval(fakeInterval);
        progressBar.style.width = '100%';
        progressBar.style.background = d.success ? '#639922' : '#E24B4A';
        progressText.textContent = d.message;
        setTimeout(() => {
            progress.style.display = 'none';
            progressBar.style.width = '0%';
            progressBar.style.background = '#639922';
            loadFaceStatus();
        }, 2500);
    } catch {
        clearInterval(fakeInterval);
        progressText.textContent = 'Error — make sure server is running.';
    }

    btn.disabled = false;
    btn.textContent = 'Register face';
}

async function deleteFace() {
    if (!confirm('Delete face profile? Webcam will log everyone until you re-register.')) return;
    await fetch('/api/face/delete', {method:'POST'});
    loadFaceStatus();
}

async function loadAll() {
    await Promise.all([
        loadToday(),
        loadScreenshots(),
        loadWebcam(),
        loadCrossVerify(),
        loadWeekly(),
        loadLive(),
        loadFaceStatus()
    ]);
}

async function sendChatMessage() {
    const input = document.getElementById('chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    const container = document.getElementById('chat-messages');
    const sendBtn = document.getElementById('chat-send');

    // Add user message
    container.innerHTML += `<div class="chat-msg user">${msg}</div>`;
    input.value = '';
    container.scrollTop = container.scrollHeight;

    // Loading state
    sendBtn.disabled = true;
    const loadingId = 'loading-' + Date.now();
    container.innerHTML += `<div class="chat-msg ai" id="${loadingId}">Thinking...</div>`;
    container.scrollTop = container.scrollHeight;

    try {
        const r = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg })
        });
        const d = await r.json();
        document.getElementById(loadingId).textContent = d.response || d.error;
    } catch {
        document.getElementById(loadingId).textContent = 'Error: Could not connect to server.';
    } finally {
        sendBtn.disabled = false;
        container.scrollTop = container.scrollHeight;
    }
}

window.onload = function() { 
    loadAll();
    
    // Add event listener for Enter key on chat input
    document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });
};
setInterval(loadLive, 60000);
setInterval(loadAll, 300000);