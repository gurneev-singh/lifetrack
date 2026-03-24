# LifeTrack - screenshot_analyzer.py
# Takes a screenshot every 30 seconds, sends to Groq vision,
# stores ONLY the text description. Raw image is never saved.

import base64
import io
import time
import platform
from datetime import datetime
from PIL import ImageGrab, Image
from groq import Groq
from core.config import GROQ_API_KEY, SCREENSHOT_INTERVAL
from core.privacy import is_paused, is_blacklisted_app, is_night_time
from features.tracking.tracker import is_idle, get_active_window
from core.logger import log_groq
from core.database import record_app_suggestion

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY != "your_groq_api_key_here" else None

PROMPT = """Look at this screenshot and describe in ONE short sentence what the person is doing.
Be specific — not just the app name but the actual activity.
Also classify as one of: study / distraction / break / unknown

Examples:
- "Watching YouTube video about neural networks — study"
- "Scrolling Instagram Reels — distraction"  
- "Writing Python code in VS Code, working on a tracker — study"
- "Reading Stack Overflow about async functions — study"
- "Playing BGMI mobile game — distraction"
- "Browsing Reddit memes — distraction"
- "Writing essay in Google Docs — study"
- "Watching Netflix series — distraction"

Respond in this exact format:
DESCRIPTION: <one sentence>
CATEGORY: <study/distraction/break/unknown>
"""


def capture_screenshot() -> Image.Image | None:
    """Take a screenshot. Returns PIL Image or None if failed."""
    try:
        screenshot = ImageGrab.grab()
        # Resize to reduce API cost — 1280px wide is enough for AI to read
        w, h = screenshot.size
        if w > 1280:
            ratio = 1280 / w
            screenshot = screenshot.resize((1280, int(h * ratio)), Image.LANCZOS)
        return screenshot
    except Exception as e:
        print(f"[Screenshot] Capture failed: {e}")
        return None


def image_to_base64(img: Image.Image) -> str:
    """Convert PIL image to base64 string for API. Image never saved to disk."""
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=75)
    buffer.seek(0)
    b64 = base64.standard_b64encode(buffer.read()).decode("utf-8")
    buffer.close()
    return b64


def analyze_screenshot(img: Image.Image) -> dict:
    """Send screenshot to Groq vision. Returns description and category."""
    if client is None:
        return {"description": "API key not set", "category": "unknown"}

    try:
        b64 = image_to_base64(img)
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }],
            max_tokens=100
        )

        text = response.choices[0].message.content.strip()

        # Parse response
        description = "Unknown activity"
        category = "unknown"

        for line in text.split("\n"):
            if line.startswith("DESCRIPTION:"):
                description = line.replace("DESCRIPTION:", "").strip()
            elif line.startswith("CATEGORY:"):
                category = line.replace("CATEGORY:", "").strip().lower()
                if category not in ["study", "distraction", "break", "unknown"]:
                    category = "unknown"

        return {"description": description, "category": category}

    except Exception as e:
        print(f"[Screenshot] API error: {e}")
        return {"description": "API error", "category": "unknown"}
    finally:
        # Explicitly delete image from memory — never stored on disk
        del img


def run_screenshot_analyzer(db_log_fn):
    """
    Main loop. Runs forever in a background thread.
    db_log_fn is the function to call to save a result to database.
    """
    print(f"[Screenshot] Started. Analyzing every {SCREENSHOT_INTERVAL}s...")

    last_window = None
    last_result = None

    while True:
        try:
            # Skip if paused by user
            if is_paused():
                print(f"[{datetime.now().strftime('%H:%M')}] [Screenshot] Paused — skipping")
                time.sleep(SCREENSHOT_INTERVAL)
                continue

            # Skip if idle (no input for 5 minutes)
            if is_idle():
                print(f"[{datetime.now().strftime('%H:%M')}] [Screenshot] IDLE — skipping AI analysis")
                time.sleep(SCREENSHOT_INTERVAL)
                continue

            # Skip if night time
            if is_night_time():
                from core.config import NIGHT_STOP_HOUR
                print(f"[{datetime.now().strftime('%H:%M')}] [Screenshot] NIGHT MODE ({datetime.now().hour} >= {NIGHT_STOP_HOUR}) — skipping AI analysis")
                time.sleep(SCREENSHOT_INTERVAL)
                continue

            # Get current window and app
            active_window, active_app = get_active_window()

            # Skip if blacklisted app is active
            if is_blacklisted_app(active_app):
                print(f"[{datetime.now().strftime('%H:%M')}] [Screenshot] Blacklisted app ({active_app}) — skipping")
                time.sleep(SCREENSHOT_INTERVAL)
                continue

            # Smart Check: If window title is same as last time, reuse the AI result
            if active_window == last_window and last_result:
                result = last_result
                print(f"[{datetime.now().strftime('%H:%M')}] [Screenshot] Reusing result (Window unchanged: {active_app})")
            else:
                # Take screenshot
                img = capture_screenshot()
                if img is None:
                    time.sleep(SCREENSHOT_INTERVAL)
                    continue

                # Analyze with AI
                result = analyze_screenshot(img)
                last_window = active_window
                last_result = result

            # Save to database (only text, never image)
            db_log_fn(
                description=result["description"],
                category=result["category"],
                app=active_app
            )

            # Record habit learning suggestion
            if result["category"] != "unknown":
                record_app_suggestion(active_app, result["category"])

            log_groq("Screenshot", result['category'], result['description'][:60])

        except Exception as e:
            print(f"[Screenshot] Error: {e}")

        time.sleep(SCREENSHOT_INTERVAL)
