# LifeTrack - features/tracking/webcam_analyzer.py
# Captures one webcam frame every 60 seconds.
# Sends to Groq vision, saves description only.
# Frame is NEVER saved to disk.

import cv2
import base64
import time
import threading
from datetime import datetime
from groq import Groq
from core.config import GROQ_API_KEY, WEBCAM_INTERVAL
from core.privacy import is_paused, is_night_time

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY != "your_groq_api_key_here" else None

PROMPT = """Look at this webcam photo and describe what the person is physically doing.
Be specific and concise — one sentence only.
Also classify into exactly one of: present / away / distracted / tired / break

Definitions:
- present = at desk, looking at screen, focused
- away = not visible, left the room
- distracted = at desk but looking at phone, looking away from screen frequently
- tired = head drooping, slouched, eyes closing
- break = eating, drinking, stretching

Examples:
- "Person sitting upright at desk, focused on screen — present"
- "Person not visible, chair empty — away"
- "Person at desk holding phone, not looking at screen — distracted"
- "Person slouched, head resting on hand, appears tired — tired"
- "Person eating at desk — break"

If the image is dark or unclear, respond with:
DESCRIPTION: Camera image unclear
PHYSICAL: away

Respond in EXACTLY this format:
DESCRIPTION: <one sentence>
PHYSICAL: <present/away/distracted/tired/break>
"""

# ─── Webcam capture ───────────────────────────────────────────────────────────

_cap = None
_cap_lock = threading.Lock()

def get_camera():
    """Get or initialize webcam. Returns VideoCapture or None."""
    global _cap
    with _cap_lock:
        if _cap is None or not _cap.isOpened():
            _cap = cv2.VideoCapture(0)
            if _cap.isOpened():
                _cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                _cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print("[Webcam] Camera initialized.")
            else:
                print("[Webcam] Could not open webcam. Check if camera is connected.")
                _cap = None
        return _cap

def capture_frame():
    """Capture one frame from webcam. Returns base64 string or None."""
    cap = get_camera()
    if cap is None:
        return None
    try:
        # Discard a few frames so camera adjusts exposure
        for _ in range(3):
            cap.read()
        ret, frame = cap.read()
        if not ret or frame is None:
            return None

        # Encode to JPEG in memory — never saved to disk
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ret:
            return None

        b64 = base64.standard_b64encode(buffer.tobytes()).decode('utf-8')

        # Explicitly delete frame from memory
        del frame
        del buffer
        return b64

    except Exception as e:
        print(f"[Webcam] Capture error: {e}")
        return None

# ─── Groq vision analysis ─────────────────────────────────────────────────────

def analyze_frame(b64_image: str) -> dict:
    """Send frame to Groq vision. Returns description and physical category."""
    if client is None:
        return {"description": "API key not set", "physical": "unknown"}

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{b64_image}"
                    }}
                ]
            }],
            max_tokens=80
        )

        text = response.choices[0].message.content.strip()
        description = "Unknown"
        physical = "unknown"

        for line in text.split("\n"):
            if line.startswith("DESCRIPTION:"):
                description = line.replace("DESCRIPTION:", "").strip()
            elif line.startswith("PHYSICAL:"):
                physical = line.replace("PHYSICAL:", "").strip().lower()
                if physical not in ["present", "away", "distracted", "tired", "break"]:
                    physical = "unknown"

        return {"description": description, "physical": physical}

    except Exception as e:
        print(f"[Webcam] API error: {e}")
        return {"description": "API error", "physical": "unknown"}

# ─── Main loop ────────────────────────────────────────────────────────────────

def run_webcam_analyzer(db_log_fn):
    """
    Main loop. Runs in background thread.
    db_log_fn = core.database.log_webcam
    """
    print(f"[Webcam] Started. Analyzing every {WEBCAM_INTERVAL}s...")

    while True:
        try:
            # Skip if paused or night time
            if is_paused():
                print(f"[{datetime.now().strftime('%H:%M')}] [Webcam] Paused — skipping")
                time.sleep(WEBCAM_INTERVAL)
                continue

            if is_night_time():
                time.sleep(WEBCAM_INTERVAL)
                continue

            # Capture frame
            b64 = capture_frame()
            if b64 is None:
                time.sleep(WEBCAM_INTERVAL)
                continue

            # Analyze
            result = analyze_frame(b64)
            del b64  # delete from memory immediately

            # Save to database
            db_log_fn(
                description=result["description"],
                physical=result["physical"]
            )

            print(f"[{datetime.now().strftime('%H:%M')}] [Webcam] {result['physical'].upper()} — {result['description'][:60]}")

        except Exception as e:
            print(f"[Webcam] Error: {e}")

        time.sleep(WEBCAM_INTERVAL)


def release_camera():
    """Release webcam when stopping."""
    global _cap
    with _cap_lock:
        if _cap is not None:
            _cap.release()
            _cap = None
            print("[Webcam] Camera released.")