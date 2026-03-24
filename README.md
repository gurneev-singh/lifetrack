# LifeTrack

> **You think you studied 6 hours today. You actually studied 2h 10m.**
> LifeTrack tells you the truth.

A free, open-source, privacy-first life analytics OS that watches your screen **and** your webcam using AI vision, cross-verifies both to generate a truth score, and gives you a brutally honest report every night.

No subscription. No cloud. No screenshots stored. Ever. Your data stays on your machine forever.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-local-green?style=flat-square&logo=sqlite)
![Groq](https://img.shields.io/badge/Groq-LLaMA_4_Scout-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-blue?style=flat-square&logo=windows)

---

## What makes this different

Every other tool like this (Rewind AI — $19/month, Limitless — $99 device) stores your screenshots forever. LifeTrack takes a screenshot, sends it to AI, gets back a one-line description, and **immediately deletes the image from memory**. Only the text is stored. Always.

```
Instead of storing:  [screenshot.png — 2MB of your screen]
LifeTrack stores:    "Debugging Python script in VS Code — study"
```

**And it doesn't stop at your screen.** LifeTrack also uses your webcam to verify you're *actually* at your desk. If the screen says "studying" but the camera sees you on your phone — it knows.

Privacy-first by design. Not as an afterthought.

---

## What it actually does

Every 60 seconds, LifeTrack reads your screen **and** your webcam with AI, then cross-verifies both:

- **Screen AI** — not just which app, but *what specifically* you're doing
- **Webcam AI** — are you present, away, distracted, tired, or on break?
- **Cross-verification** — compares screen activity vs physical state to generate a truth score
- **Face recognition** — only tracks *you*, skips strangers
- **Smart tracking** — skips redundant AI calls when idle or the window hasn't changed
- **Habit learning** — AI learns *your* app categories over time (YouTube for tutorials? It'll mark it as study)
- **Activity Chat** — ask natural language questions about your day right from the dashboard
- **AI coach** — calls you out on your habits with a brutally honest daily report

```
==================================================
  LIFETRACK — Sunday 22 March 2026
==================================================

  FOCUS SCORE: 78/100
  [████████████████░░░░]

  TRUTH SCORE: 85/100
  Screen said study: 4h 20m
  Camera confirmed:  3h 41m
  Phone in hand:        22m
  Away from desk:       17m

  WHAT YOU ACTUALLY DID TODAY
  11:46  Debugging Python script in VS Code to fix model name issue
  12:15  Reading Stack Overflow about SQLite query optimization
  13:00  Scrolling Instagram Reels
  14:30  Writing Flask API routes for mobile PWA
  16:00  Watching YouTube video about Raspberry Pi Zero 2W

  AI COACH:
  You coded for 4h 20m — solid work. The 50-minute Reels
  session at 1pm wiped out a full hour of MIT prep. Fix
  that one habit and you add 300 hours of study per year.
==================================================
```

---

## How it works

```
Every 60 seconds — TWO parallel AI pipelines:

SCREEN PIPELINE                           WEBCAM PIPELINE
┌────────────────────────┐     ┌────────────────────────────┐
│ Screenshot taken       │     │ Webcam frame captured      │
│ (never saved to disk)  │     │ (never saved to disk)      │
│         │              │     │         │                  │
│         ▼              │     │         ▼                  │
│ Smart check: same      │     │ Face recognition:          │
│ window as before?      │     │ is this me?                │
│    ├─YES→ Reuse result │     │    ├─NO→  Skip (stranger)  │
│    └─NO → Groq AI      │     │    └─YES→ Groq AI          │
│         │              │     │         │                  │
│         ▼              │     │         ▼                  │
│ "Debugging Python      │     │ "Person at desk, focused   │
│  in VS Code — study"   │     │  on screen — present"      │
│         │              │     │         │                  │
│         ▼              │     │         ▼                  │
│ Saved to SQLite        │     │ Saved to SQLite            │
│ (text only)            │     │ (text only)                │
└────────────────────────┘     └────────────────────────────┘
                    │                    │
                    ▼                    ▼
           ┌──────────────────────────────────┐
           │    CROSS-VERIFICATION ENGINE     │
           │  Screen says study + Camera says │
           │  distracted = CAUGHT             │
           │  Generates truth score           │
           └──────────────────────────────────┘

Every night at 11pm:
┌─────────────────────────────────────────────┐
│  Groq LLaMA reads your full day             │
│  Generates brutally honest coaching report  │
│  Calculates focus score + truth score       │
└─────────────────────────────────────────────┘
```

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/gurneev-singh/lifetrack
cd lifetrack
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

> **Note:** `face_recognition` requires [CMake](https://cmake.org/download/) and [dlib](http://dlib.net/) to be installed. On Windows, install Visual Studio Build Tools first.

### 3. Configure
```bash
cp config.example.py core/config.py
```

Open `core/config.py` and add your free Groq API key:
```python
GROQ_API_KEY = "your_key_here"  # free at console.groq.com
```

### 4. Run
```bash
python main.py
```

This starts everything in one terminal — the tracker, both AI analyzers (screen + webcam), and the web dashboard at `http://localhost:5000`.

**Run without dashboard:**
```bash
python main.py --no-dashboard
```

**Generate a report anytime:**
```bash
python main.py --report
```

---

## Privacy controls

| Feature | How |
|---|---|
| Pause all capture | `Win+Shift+P` — pauses for 5 minutes, press again to resume |
| App blacklist | Add any app to `BLACKLISTED_APPS` in `core/privacy.py` |
| Auto night stop | Capture pauses at 11pm, resumes at 7am (configurable) |
| No image storage | Screenshots and webcam frames deleted from memory immediately after AI analysis |
| No cloud | Everything stays on your machine. Always. |
| Face recognition | Only tracks YOUR face — skips anyone else on camera |
| Idle detection | Stops AI calls when no keyboard/mouse input for 5 minutes |
| Smart tracking | Skips redundant AI calls when active window hasn't changed |

---

## Face registration

LifeTrack uses face recognition so it only tracks **you** — if someone else sits at your desk, it won't log their activity.

1. Start LifeTrack: `python main.py`
2. Open the dashboard at `http://localhost:5000`
3. Register your face via the dashboard UI
4. LifeTrack captures 10 photos and builds your face profile
5. From now on, webcam analysis only runs when it recognizes you

Face data is stored locally in `data/my_face.npy`. You can delete your profile anytime from the dashboard.

---

## Activity Chat

Talk to your data. The dashboard includes an AI chat interface (in the AI Coach card) that lets you ask natural language questions about your day:

- *"When did I start studying today?"*
- *"How much time did I spend on documentation?"*
- *"What was the most distracting thing I did this afternoon?"*
- *"Was I more productive in the morning or evening?"*

The chat sends your daily logs to Groq as context and returns an answer grounded in your actual tracked data.

---

## Dynamic Habit Learning

LifeTrack doesn't rely only on a hardcoded app list. It **learns from your behavior**:

1. Every screenshot analysis records the AI's suggested category for the active app
2. The system stores suggestions in the `app_knowledge` table
3. After enough data (last 20 samples, >60% majority), the learned category overrides the default

**Example:** YouTube is classified as "distraction" by default. But if you mostly watch coding tutorials, LifeTrack will learn that and start marking your YouTube time as "study."

---

## iPhone PWA

LifeTrack has a mobile app that installs directly from Safari — no App Store needed.

1. Run `python main.py` on your laptop
2. On iPhone Safari, open `http://your-laptop-ip:5000/mobile`
3. Tap Share → Add to Home Screen
4. Done — it's on your home screen like a real app

Features: voice notes, mood check-ins, text notes, offline queue that syncs when back on WiFi.

---

## Project structure

```
lifetrack/
├── main.py                          ← entry point, starts all threads
├── config.example.py                ← safe template for new users
├── requirements.txt                 ← all dependencies
│
├── core/                            ← shared infrastructure
│   ├── config.py                    ← settings + API key (gitignored)
│   ├── database.py                  ← all SQLite operations
│   ├── privacy.py                   ← pause hotkey, blacklist, night stop
│   ├── classifier.py                ← labels apps as study/distraction/break
│   └── logger.py                    ← dual logging (Groq → file + console)
│
├── features/
│   ├── tracking/
│   │   ├── screenshot_analyzer.py   ← screen AI vision every 60s
│   │   ├── webcam_analyzer.py       ← webcam AI analysis every 60s
│   │   ├── face_profile.py          ← face registration + recognition
│   │   ├── cross_verify.py          ← screen vs webcam truth score
│   │   └── tracker.py               ← window title tracker (fallback)
│   │
│   ├── dashboard/
│   │   └── server.py                ← Flask web dashboard + API
│   │
│   ├── reporting/
│   │   └── reporter.py              ← daily report + Groq AI coach
│   │
│   └── mobile/                      ← iPhone PWA support
│
├── templates/
│   ├── dashboard.html               ← web dashboard UI
│   └── mobile.html                  ← mobile PWA interface
│
├── static/                          ← CSS + JS assets
├── logs/                            ← auto-created log files
│   ├── groq.log                     ← all AI analysis results
│   └── server.log                   ← Flask server logs (hidden from terminal)
└── data/                            ← face profiles + local data (gitignored)
```

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Screen capture | `Pillow` ImageGrab | Captures screen every 60s, never saved to disk |
| Webcam capture | `OpenCV` | Captures webcam every 60s, never saved to disk |
| AI vision | `Groq LLaMA 4 Scout` | Reads screen + webcam, free tier, fast inference |
| Face recognition | `face_recognition` + `dlib` | Only tracks the registered user |
| Window tracking | `pygetwindow` | Fallback when AI unavailable |
| Idle detection | `pynput` | Keyboard + mouse activity listener |
| Smart tracking | Custom | Skips AI when window unchanged or user idle |
| Database | `SQLite3` | Zero setup, fully local, 7 tables |
| AI coach | `Groq LLaMA 3.3-70b` | Daily coaching report |
| Dashboard | `Flask` + `Chart.js` | Web UI with live charts |
| Mobile | PWA | Installs on iPhone from Safari |
| Logging | Python `logging` | Dual output — file + console for AI, file-only for server |

---

## Roadmap

- [x] Screen activity tracker with AI vision
- [x] Webcam AI analysis (present / away / distracted / tired / break)
- [x] Face recognition (only tracks you)
- [x] Cross-verification engine (truth score)
- [x] Smart tracking (skip idle + unchanged windows)
- [x] Privacy controls (pause hotkey, blacklist, night stop)
- [x] Habit learning (AI learns your app categories over time)
- [x] Local SQLite database
- [x] AI coaching report via Groq
- [x] Web dashboard with live charts
- [x] iPhone PWA with offline sync
- [x] Structured logging (Groq + server logs)
- [x] Activity Chat — natural language queries on your data
- [ ] Raspberry Pi Zero 2W standalone device
- [ ] macOS and Linux support
- [ ] Weekly digest email
- [ ] Habit streak tracking

---

## Why I built this

I'm a 16-year-old developer from Lucknow, India. I kept lying to myself about how much I was actually studying. I'd sit at my desk for 6 hours and call it productive — but the AI camera would catch me on my phone half the time.

So I built a tool that makes lying to yourself impossible.

Rewind AI charges $19/month and stores your screenshots forever. LifeTrack is free, stores only AI text descriptions, and works on Windows with a phone you already own.

---

## Contributing

Pull requests welcome. Especially interested in:
- macOS support
- Linux support
- Firefox history reader
- Android app for outside-home capture
- Activity Chat — natural language queries on historical data

---

## License

MIT — use it, fork it, build on it.

---

<p align="center">Built with Python in Lucknow, India 🇮🇳</p>