const SERVER = window.location.origin;
let isOnline = false;
let queue = JSON.parse(localStorage.getItem('lt_queue') || '[]');
let mediaRecorder = null;
let audioChunks = [];
let recInterval = null;
let recSeconds = 0;

function showPage(name, btn) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('page-' + name).classList.add('active');
    btn.classList.add('active');
    if (name === 'today') loadTodayMobile();
    if (name === 'queue') renderQueue();
}

async function checkConnection() {
    try {
        const r = await fetch(SERVER + '/api/live', {signal: AbortSignal.timeout(3000)});
        if (r.ok) {
            isOnline = true;
            document.getElementById('dot').className = 'online-dot on';
            document.getElementById('conn-status').textContent = 'Connected';
            showSyncBar('Connected to laptop', false);
            syncQueue();
        }
    } catch {
        isOnline = false;
        document.getElementById('dot').className = 'online-dot';
        document.getElementById('conn-status').textContent = 'Offline';
        const pending = queue.filter(q => q.status === 'pending').length;
        if (pending > 0) showSyncBar(pending + ' items waiting to sync', true);
    }
}

function showSyncBar(msg, warn) {
    const bar = document.getElementById('sync-bar');
    bar.className = 'sync-banner' + (warn ? ' warn' : '');
    bar.textContent = msg;
    if (!warn) setTimeout(() => bar.textContent = '', 3000);
}

async function startVoice() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({audio: true});
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        recSeconds = 0;
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(t => t.stop());
            clearInterval(recInterval);
            document.getElementById('rec-box').classList.remove('active');
            addToQueue({type: 'voice', note: 'Voice note — ' + recSeconds + 's', duration: recSeconds});
        };
        mediaRecorder.start();
        document.getElementById('rec-box').classList.add('active');
        recInterval = setInterval(() => {
            recSeconds++;
            const m = Math.floor(recSeconds / 60);
            const s = recSeconds % 60;
            document.getElementById('rec-timer').textContent = m + ':' + String(s).padStart(2, '0');
        }, 1000);
    } catch {
        alert('Microphone access denied. Allow mic in Safari settings.');
    }
}

function stopVoice() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
}

function selectMood(mood, el) {
    document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
    el.classList.add('selected');
    addToQueue({type: 'mood', mood: mood, note: 'Mood: ' + mood});
    setTimeout(() => el.classList.remove('selected'), 1500);
}

function saveNote() {
    const text = document.getElementById('note-input').value.trim();
    if (!text) return;
    addToQueue({type: 'note', note: text});
    document.getElementById('note-input').value = '';
    showSyncBar('Note saved!', false);
}

function addToQueue(item) {
    const entry = {...item, id: Date.now(), timestamp: new Date().toISOString(), status: 'pending'};
    queue.unshift(entry);
    localStorage.setItem('lt_queue', JSON.stringify(queue.slice(0, 100)));
    renderQueue();
    showSyncBar('Saved' + (isOnline ? ' — syncing...' : ' offline'), !isOnline);
    if (isOnline) syncQueue();
}

function renderQueue() {
    const el = document.getElementById('queue-list');
    if (queue.length === 0) {
        el.innerHTML = '<div class="empty">No pending items.</div>';
        return;
    }
    el.innerHTML = queue.slice(0, 20).map(q => {
        const time = new Date(q.timestamp).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        const typeClass = {voice: 'qb-voice', mood: 'qb-mood', note: 'qb-note'}[q.type] || '';
        const statusClass = q.status === 'synced' ? 'qb-synced' : 'qb-pending';
        return `<div class="queue-item">
            <div style="flex:1">
                <span class="badge ${typeClass}">${q.type}</span>
                <span class="badge ${statusClass}">${q.status}</span>
                <div class="queue-text">${q.note || q.mood || 'entry'}</div>
            </div>
            <div class="queue-time">${time}</div>
        </div>`;
    }).join('');
}

async function syncQueue() {
    const pending = queue.filter(q => q.status === 'pending');
    if (!pending.length || !isOnline) return;
    for (const item of pending) {
        try {
            const r = await fetch(SERVER + '/api/mobile/log', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({type: item.type, note: item.note, mood: item.mood, timestamp: item.timestamp, duration: item.duration})
            });
            if (r.ok) {
                const idx = queue.findIndex(q => q.id === item.id);
                if (idx !== -1) queue[idx].status = 'synced';
            }
        } catch { break; }
    }
    localStorage.setItem('lt_queue', JSON.stringify(queue.slice(0, 100)));
    renderQueue();
}

function syncNow() { checkConnection(); }

async function loadTodayMobile() {
    if (!isOnline) return;
    try {
        const [todayRes, ssRes] = await Promise.all([
            fetch(SERVER + '/api/today'),
            fetch(SERVER + '/api/screenshots')
        ]);
        const d = await todayRes.json();
        const screenshots = await ssRes.json();

        document.getElementById('mobile-stats').innerHTML = `
            <div class="metric"><div class="metric-val" style="color:#3B6D11">${d.study_fmt}</div><div class="metric-lbl">Study time</div></div>
            <div class="metric"><div class="metric-val" style="color:#534AB7">${d.focus_score}/100</div><div class="metric-lbl">Focus score</div></div>
            <div class="metric"><div class="metric-val" style="color:#A32D2D">${d.distraction_fmt}</div><div class="metric-lbl">Distraction</div></div>
            <div class="metric"><div class="metric-val" style="color:#854F0B">${d.break_fmt}</div><div class="metric-lbl">Break</div></div>
        `;

        document.getElementById('mobile-ai').textContent = d.ai_report;

        // Screenshot descriptions
        const ssEl = document.getElementById('mobile-descriptions');
        if (screenshots && screenshots.length > 0) {
            const catCls = {study:'ss-study', distraction:'ss-distraction', break:'ss-break'};
            ssEl.innerHTML = screenshots.slice(0, 15).map(s => {
                const time = s.timestamp ? s.timestamp.substring(11, 16) : '';
                const cls = catCls[s.category] || 'ss-unknown';
                return `<div class="ss-row">
                    <span class="ss-time">${time}</span>
                    <span class="ss-badge ${cls}">${s.category}</span>
                    <div class="ss-desc">${s.description}</div>
                </div>`;
            }).join('');
        } else {
            ssEl.innerHTML = '<div class="empty">No AI descriptions yet.</div>';
        }

    } catch {
        document.getElementById('mobile-ai').textContent = 'Could not load. Make sure laptop server is running.';
    }
}

checkConnection();
setInterval(checkConnection, 30000);
renderQueue();
