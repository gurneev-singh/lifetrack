# LifeTrack

> **You think you studied 6 hours today. You actually studied 2h 10m.**
> LifeTrack tells you the truth.

A free, open-source, privacy-first life analytics OS that watches your screen every 30 seconds, reads exactly what you're doing using AI vision, and gives you a brutally honest report every night.

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

Privacy-first by design. Not as an afterthought.

---

## What it actually does

Every 30 seconds, LifeTrack reads your screen with AI and saves what you were actually doing. At the end of the day:

- Exactly what you were doing — not just which app, but what specifically
- Real study time vs distraction time
- Focus score out of 100
- AI coach that calls you out on your habits

```
==================================================
  LIFETRACK — Sunday 22 March 2026
==================================================

  FOCUS SCORE: 78/100
  [████████████████░░░░]

  Study            4h 20m
  Distraction      1h 10m
  Break               30m
  Total            6h 00m

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
Every 30 seconds:
┌─────────────────────────────────────────────┐
│  Screenshot taken (never saved to disk)     │
│           │                                 │
│           ▼                                 │
│  Groq LLaMA 4 Scout Vision API              │
│           │                                 │
│           ▼                                 │
│  "Debugging Python in VS Code — study"      │
│           │                                 │
│           ▼                                 │
│  Saved to local SQLite (text only)          │
│  Screenshot deleted from memory             │
└─────────────────────────────────────────────┘

Every night at 11pm:
┌─────────────────────────────────────────────┐
│  Groq LLaMA reads your full day             │
│  Generates brutally honest coaching report  │
│  Calculates focus score                     │
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
pip install groq pygetwindow pynput schedule flask Pillow pyautogui
```

### 3. Configure
```bash
cp config.example.py config.py
```

Open `config.py` and add your free Groq API key:
```python
GROQ_API_KEY = "your_key_here"  # free at console.groq.com
```

### 4. Run

**Terminal 1 — tracker + AI analysis:**
```bash
python main.py
```

**Terminal 2 — web dashboard:**
```bash
python server.py
```

Open `http://localhost:5000` in your browser.

**Generate a report anytime:**
```bash
python main.py --report
```

---

## Privacy controls

| Feature | How |
|---|---|
| Pause screenshots | `Win+Shift+P` — pauses for 5 minutes |
| App blacklist | Add any app to `BLACKLISTED_APPS` in `privacy.py` |
| Auto night stop | Screenshots pause at 11pm, resume at 7am |
| No image storage | Raw screenshots deleted from memory immediately after AI analysis |
| No cloud | Everything stays on your machine. Always. |

---

## iPhone PWA

LifeTrack has a mobile app that installs directly from Safari — no App Store needed.

1. Run `python server.py` on your laptop
2. On iPhone Safari, open `http://your-laptop-ip:5000/mobile`
3. Tap Share → Add to Home Screen
4. Done — it's on your home screen like a real app

Features: voice notes, mood check-ins, text notes, offline queue that syncs when back on WiFi.

---

## File structure

```
lifetrack/
├── main.py                  ← entry point, starts everything
├── config.py                ← your settings + API key (gitignored)
├── config.example.py        ← safe template for new users
├── tracker.py               ← window title tracker (fallback)
├── screenshot_analyzer.py   ← AI vision analysis every 30s
├── privacy.py               ← pause hotkey, blacklist, night stop
├── classifier.py            ← labels apps as study/distract/break
├── database.py              ← all SQLite operations
├── reporter.py              ← daily report + Groq AI coach
├── server.py                ← Flask web dashboard + mobile API
└── mobile.html              ← iPhone PWA
```

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Screen capture | `Pillow` ImageGrab | captures screen every 30s |
| AI vision | `Groq LLaMA 4 Scout` | reads screen, free, fast |
| Window tracking | `pygetwindow` | fallback when AI unavailable |
| Idle detection | `pynput` | keyboard and mouse listener |
| Browser history | `sqlite3` | reads Chrome local DB |
| Database | `SQLite3` | zero setup, fully local |
| AI coach | `Groq LLaMA 3.3-70b` | weekly coaching report |
| Dashboard | `Flask` + `Chart.js` | web UI, no framework needed |
| Mobile | PWA | installs on iPhone from Safari |

---

## Roadmap

- [x] Laptop activity tracker
- [x] AI screenshot analysis (sees exactly what you do)
- [x] Privacy controls (pause hotkey, blacklist, night stop)
- [x] Chrome history import
- [x] Local SQLite database
- [x] AI coaching report via Groq
- [x] Web dashboard with live charts
- [x] iPhone PWA with offline sync
- [ ] Camera integration (Android/Pi Zero as room AI eye)
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

---

## License

MIT — use it, fork it, build on it.

---

<p align="center">Built with Python in Lucknow, India</p>