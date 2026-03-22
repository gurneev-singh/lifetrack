# LifeTrack - privacy.py
# Pause hotkey, app blacklist, auto-stop after 11pm.
# Win+Shift+P = pause screenshots for 5 minutes.

import time
import platform
import threading
from datetime import datetime

# ─── Pause state ──────────────────────────────────────────────────────────────
_paused_until = 0
_pause_lock = threading.Lock()
PAUSE_DURATION = 300  # 5 minutes

def pause_screenshots(duration=PAUSE_DURATION):
    """Pause screenshot capture for N seconds."""
    global _paused_until
    with _pause_lock:
        _paused_until = time.time() + duration
    print(f"[Privacy] Screenshots paused for {duration//60} minutes.")

def resume_screenshots():
    """Resume screenshot capture immediately."""
    global _paused_until
    with _pause_lock:
        _paused_until = 0
    print("[Privacy] Screenshots resumed.")

def is_paused() -> bool:
    """Returns True if screenshots are currently paused."""
    with _pause_lock:
        return time.time() < _paused_until

def get_pause_remaining() -> int:
    """Returns seconds remaining in pause, or 0 if not paused."""
    with _pause_lock:
        remaining = _paused_until - time.time()
        return max(0, int(remaining))


# ─── App blacklist ────────────────────────────────────────────────────────────
# Add any app window title keywords here to skip screenshots
BLACKLISTED_APPS = [
    "1password", "keepass", "bitwarden",   # password managers
    "bank", "hdfc", "sbi", "icici",        # banking
    "incognito", "private browsing",        # private browser modes
    "zoom", "meet",                         # video calls (privacy)
    "whatsapp",                             # personal messages
    "task manager",                         # system tools
]

def is_blacklisted_app(app_name: str) -> bool:
    """Returns True if the current app should not be screenshotted."""
    if not app_name:
        return False
    app_lower = app_name.lower()
    return any(kw in app_lower for kw in BLACKLISTED_APPS)


# ─── Auto night stop ──────────────────────────────────────────────────────────
NIGHT_STOP_HOUR  = 23   # stop screenshots at 11pm
NIGHT_START_HOUR = 7    # resume screenshots at 7am

def is_night_time() -> bool:
    """Returns True during night hours when screenshots should stop."""
    hour = datetime.now().hour
    return hour >= NIGHT_STOP_HOUR or hour < NIGHT_START_HOUR


# ─── Active window helper ─────────────────────────────────────────────────────
def get_active_app() -> str:
    """Get the currently active application name."""
    if platform.system() != "Windows":
        return "Unknown"
    try:
        import pygetwindow as gw
        win = gw.getActiveWindow()
        if win and win.title:
            # Extract app name from window title
            title = win.title
            for sep in [" - ", " | ", " — "]:
                if sep in title:
                    return title.split(sep)[-1].strip()
            return title[:40]
        return "Unknown"
    except Exception:
        return "Unknown"


# ─── Hotkey listener ──────────────────────────────────────────────────────────
def start_hotkey_listener():
    """
    Listen for Win+Shift+P to pause screenshots.
    Runs in background thread.
    """
    try:
        from pynput import keyboard

        _pressed = set()

        def on_press(key):
            _pressed.add(key)
            try:
                # Win+Shift+P
                if (keyboard.Key.cmd in _pressed and
                    keyboard.Key.shift in _pressed and
                    hasattr(key, 'char') and key.char == 'p'):
                    if is_paused():
                        resume_screenshots()
                    else:
                        pause_screenshots()
            except Exception:
                pass

        def on_release(key):
            _pressed.discard(key)

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.daemon = True
        listener.start()
        print("[Privacy] Hotkey active — Win+Shift+P to pause/resume screenshots")

    except Exception as e:
        print(f"[Privacy] Hotkey setup failed: {e}")
