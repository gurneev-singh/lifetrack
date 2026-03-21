# LifeTrack - config.example.py
# ─────────────────────────────────────────────
# SETUP INSTRUCTIONS:
# 1. Copy this file and rename it to config.py
# 2. Fill in your Groq API key (free at console.groq.com)
# 3. Never push config.py to GitHub — it's in .gitignore
# ─────────────────────────────────────────────

import os

# ─── Database ─────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "lifetrack.db")

# ─── Tracking ─────────────────────────────────
TRACK_INTERVAL_SECONDS = 60       # check active window every 60 seconds
IDLE_THRESHOLD_SECONDS = 300      # 5 min no input = idle

# ─── Chrome history (Windows) ─────────────────
CHROME_HISTORY_PATH = os.path.expandvars(
    r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\History"
)

# ─── App classifier ───────────────────────────
# Add or remove apps here to customize tracking
APP_CATEGORIES = {
    # Study / productive
    "code"           : "study",
    "visual studio"  : "study",
    "pycharm"        : "study",
    "jupyter"        : "study",
    "notion"         : "study",
    "obsidian"       : "study",
    "word"           : "study",
    "docs"           : "study",
    "stackoverflow"  : "study",
    "github"         : "study",
    "leetcode"       : "study",
    "coursera"       : "study",
    "khan"           : "study",
    "claude"         : "study",
    "chatgpt"        : "study",
    "wikipedia"      : "study",

    # Distraction
    "youtube"        : "distraction",
    "instagram"      : "distraction",
    "twitter"        : "distraction",
    "facebook"       : "distraction",
    "netflix"        : "distraction",
    "reddit"         : "distraction",
    "tiktok"         : "distraction",
    "snapchat"       : "distraction",
    "whatsapp"       : "distraction",
    "telegram"       : "distraction",
    "discord"        : "distraction",
    "spotify"        : "distraction",
    "steam"          : "distraction",
    "game"           : "distraction",

    # Break (neutral)
    "file explorer"  : "break",
    "settings"       : "break",
    "calculator"     : "break",
    "task manager"   : "break",
}

# ─── Groq API ─────────────────────────────────
# Get your free key at: https://console.groq.com
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL   = "llama-3.3-70b-versatile"

# ─── Auto report time ─────────────────────────
REPORT_HOUR   = 23    # 11pm every night
REPORT_MINUTE = 0
