# LifeTrack - features/tracking/webcam_analyzer.py
import cv2
import base64
import time
import threading
import numpy as np
from datetime import datetime
from groq import Groq
from core.config import GROQ_API_KEY, WEBCAM_INTERVAL
from core.logger import log_groq
from core.privacy import is_paused, is_night_time
from features.tracking.face_profile import is_me, load_face_profile, is_registered
from features.tracking.tracker import is_idle

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY != "your_groq_api_key_here" else None

PROMPT = """Look at this webcam photo and describe what the person is physically doing.
Be specific and concise — one sentence only.
Also classify into exactly one of: present / away / distracted / tired / break

Definitions:
- present = at desk, looking at screen, focused, or thinking (even with hand on head)
- away = not visible, left the room, chair empty
- distracted = at desk but phone clearly visible in hand, or completely turned away from screen
- tired = head drooping, slouched heavily, eyes clearly closing
- break = eating, drinking, stretching

Examples:
- "Person sitting upright at desk, focused on screen — present"
- "Person sitting with hand on head, facing screen, thinking — present"
- "Person at desk looking slightly away but no phone visible — present"
- "Person leaning back in chair, looking at screen — present"
- "Person scratching head while looking at screen — present"
- "Person not visible, chair empty — away"
- "Person at desk with phone clearly in hand, not looking at screen — distracted"
- "Person completely turned away from screen, using phone — distracted"
- "Person slouched heavily, eyes closing, head drooping — tired"
- "Person eating at desk — break"

Respond in EXACTLY this format:
DESCRIPTION: <one sentence>
PHYSICAL: <present/away/distracted/tired/break>
"""

_cap = None
_cap_lock = threading.Lock()


def get_camera():
    global _cap
    with _cap_lock:
        if _cap is None or not _cap.isOpened():
            _cap = cv2.VideoCapture(0)
            if _cap.isOpened():
                _cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                _cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print("[Webcam] Camera initialized.")
            else:
                print("[Webcam] Could not open webcam.")
                _cap = None
        return _cap


def capture_frame():
    cap = get_camera()
    if cap is None:
        return None, None
    try:
        for _ in range(3):
            cap.read()
        ret, frame = cap.read()
        if not ret or frame is None:
            return None, None
        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        if not ret:
            return None, None
        b64 = base64.standard_b64encode(buffer.tobytes()).decode('utf-8')
        return frame, b64
    except Exception as e:
        print(f"[Webcam] Capture error: {e}")
        return None, None


def analyze_frame(b64_image: str) -> dict:
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


def run_webcam_analyzer(db_log_fn):
    print(f"[Webcam] Started. Analyzing every {WEBCAM_INTERVAL}s...")

    if is_registered():
        load_face_profile()
    else:
        print("[Webcam] No face profile — register via dashboard.")

    while True:
        try:
            # Check for registration request first
            from features.tracking.face_profile import is_registration_requested, complete_registration
            if is_registration_requested():
                print("[Webcam] Registration requested — capturing face...")
                complete_registration(get_camera())
                print("[Webcam] Registration complete.")
                continue

            if is_paused() or is_night_time() or is_idle():
                time.sleep(WEBCAM_INTERVAL)
                continue

            frame_bgr, b64 = capture_frame()
            if frame_bgr is None:
                time.sleep(WEBCAM_INTERVAL)
                continue

            # Face recognition check
            if is_registered():
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                frame_rgb = np.ascontiguousarray(frame_rgb, dtype=np.uint8)
                if not is_me(frame_rgb):
                    print(f"[{datetime.now().strftime('%H:%M')}] [Webcam] SKIPPED — unknown person")
                    del frame_bgr, frame_rgb, b64
                    time.sleep(WEBCAM_INTERVAL)
                    continue
                del frame_rgb

            if b64 is None:
                del frame_bgr
                time.sleep(WEBCAM_INTERVAL)
                continue

            result = analyze_frame(b64)
            del b64

            if result:
                db_log_fn(
                    description=result["description"],
                    physical=result["physical"]
                )
                log_groq("Webcam", result['physical'], result['description'][:60])

        except Exception as e:
            print(f"[Webcam] Error: {e}")

        time.sleep(WEBCAM_INTERVAL)


def release_camera():
    global _cap
    with _cap_lock:
        if _cap is not None:
            _cap.release()
            _cap = None
            print("[Webcam] Camera released.")