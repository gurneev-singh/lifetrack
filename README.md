# LifeTrack

> **You think you studied 6 hours today. You actually studied 2h 10m.**
> LifeTrack tells you the truth.

A free, open-source, privacy-first life analytics OS that tracks everything you do on your laptop — every app, every website, every minute — and gives you a brutally honest AI report every night.

No subscription. No cloud. No bullshit. Your data stays on your machine forever.

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-local-green?style=flat-square&logo=sqlite)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-blue?style=flat-square&logo=windows)

---

## What it actually does

Every 60 seconds, LifeTrack silently checks what you're doing and saves it. At the end of the day it tells you:

- How much you **actually** studied vs how much you think you did
- Every app and website you used and for how long
- Your **focus score** out of 100
- Exactly when you got distracted and for how long
- An **AI coach message** that calls you out on your habits

```
==================================================
  LIFETRACK — Saturday 21 March 2026
==================================================

  FOCUS SCORE: 78/100
  [████████████████░░░░]

  Study            4h 20m
  Distraction      1h 10m
  Break               30m
  Idle                20m
  Total            6h 20m

  TOP APPS
  Visual Studio Code              4h 20m
  Google Chrome                   1h 10m
  Instagram Reels                    50m

  AI COACH:
  You coded for 4h 20m — solid work. But the 50-minute
  Reels session at 2pm wiped out a full hour of potential
  study time. Over a year, fixing just the Reels habit
  adds 300 hours of study time.
==================================================
```

---

## How it works

```
┌─────────────────────────────────────────────┐
│              INPUT LAYER                    │
│  Active window  │  Chrome history  │  Idle  │
│   (every 60s)   │   (every hour)   │ detect │
└────────────────────────┬────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────┐
│              CLASSIFIER                     │
│  VS Code → study  │  YouTube → distraction  │
│  Settings → break │  No input → idle        │
└────────────────────────┬────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────┐
│         LOCAL SQLITE DATABASE               │
│   timestamp │ app │ category │ duration     │
│   Zero cloud. Your data. Your machine.      │
└────────────────────────┬────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────┐
│      WEB DASHBOARD  (localhost:5000)        │
│  Timeline  │  Charts  │  Focus ring         │
│  Top apps  │  Flags   │  AI coach           │
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
pip install groq pygetwindow pynput schedule flask
```

### 3. Configure
```bash
cp config.example.py config.py
```

Open `config.py` and add your free Groq API key:
```python
GROQ_API_KEY = "your_key_here"  # free at console.groq.com
```

You can also customize which apps count as study vs distraction:
```python
APP_CATEGORIES = {
    "notion": "study",
    "discord": "distraction",
}
```

### 4. Run

**Terminal 1 — start the tracker:**
```bash
python main.py
```

**Terminal 2 — start the dashboard:**
```bash
python server.py
```

Open `http://localhost:5000` in your browser.

**Generate a report anytime:**
```bash
python main.py --report
```

---

## File structure

```
lifetrack/
├── main.py              ← entry point, starts everything
├── config.py            ← your settings + API key (gitignored)
├── config.example.py    ← safe template for new users
├── tracker.py           ← watches active window every 60s
├── classifier.py        ← labels apps as study/distract/break
├── database.py          ← all SQLite read/write operations
├── reporter.py          ← daily report + Groq AI coach
└── server.py            ← Flask web dashboard
```

---

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| Tracking | `pygetwindow` + `psutil` | reads active window on Windows |
| Idle detection | `pynput` | keyboard and mouse listener |
| Browser history | `sqlite3` | reads Chrome's local DB directly |
| Database | `SQLite3` | zero setup, fully local |
| AI coach | `Groq LLaMA 3.3-70b` | free, fast, brutally honest |
| Dashboard | `Flask` + `Chart.js` | clean web UI, no framework needed |
| Scheduling | `schedule` | auto report every night at 11pm |

---

## Roadmap

- [x] Laptop activity tracker
- [x] Chrome history import
- [x] Local SQLite database
- [x] AI coaching report via Groq
- [x] Web dashboard with live charts
- [ ] Camera integration (Android phone or Pi Zero as AI eye)
- [ ] iPhone PWA for outside-home capture
- [ ] Raspberry Pi Zero 2W standalone device
- [ ] macOS and Linux support
- [ ] Weekly digest email

---

## Why I built this

I'm a 16-year-old developer from Lucknow, India. I kept lying to myself about how much I was actually studying. I'd sit at my desk for 6 hours and call it a productive day — but really I was on my phone half the time.

So I built a tool that makes lying to yourself impossible.

Every existing alternative either costs money (Rewind AI is $19/month), only works on Mac, requires cloud access, or doesn't combine laptop + camera + phone data. LifeTrack is free, local, open source, and cross-source.

---

## Contributing

Pull requests are welcome. If you add macOS support, Linux support, Firefox history, or a new data source — open a PR and I'll review it fast.

---

## License

MIT — use it, fork it, build on it.

---

<p align="center">Built with Python in Lucknow, India</p>
