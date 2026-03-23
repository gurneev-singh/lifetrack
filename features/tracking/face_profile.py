# LifeTrack - features/tracking/face_profile.py
import os
import cv2
import numpy as np
import face_recognition
import time
import threading
import json
from datetime import datetime

ROOT       = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR   = os.path.join(ROOT, "data")
FACE_FILE  = os.path.join(DATA_DIR, "my_face.npy")
PHOTOS_DIR = os.path.join(DATA_DIR, "face_photos")
REG_FLAG   = os.path.join(DATA_DIR, ".register_requested")
RESULT_FILE= os.path.join(DATA_DIR, ".register_result.txt")

_known_encodings = []
_face_loaded     = False
_load_lock       = threading.Lock()


def ensure_dirs():
    os.makedirs(DATA_DIR,   exist_ok=True)
    os.makedirs(PHOTOS_DIR, exist_ok=True)


def is_registered() -> bool:
    return os.path.exists(FACE_FILE)


def load_face_profile() -> bool:
    global _known_encodings, _face_loaded
    with _load_lock:
        if not os.path.exists(FACE_FILE):
            print("[Face] No face profile found. Register via dashboard.")
            return False
        try:
            _known_encodings = list(np.load(FACE_FILE, allow_pickle=True))
            _face_loaded = True
            print(f"[Face] Loaded profile — {len(_known_encodings)} encodings.")
            return True
        except Exception as e:
            print(f"[Face] Failed to load profile: {e}")
            return False


def is_me(frame_rgb) -> bool:
    global _known_encodings, _face_loaded
    if not _face_loaded or not _known_encodings:
        return True
    try:
        locs = face_recognition.face_locations(frame_rgb, model="hog")
        if not locs:
            return False
        encs = face_recognition.face_encodings(frame_rgb, locs)
        if not encs:
            return False
        matches = face_recognition.compare_faces(
            _known_encodings, encs[0], tolerance=0.55
        )
        return any(matches)
    except Exception as e:
        print(f"[Face] Recognition error: {e}")
        return True


def request_registration():
    ensure_dirs()
    if os.path.exists(RESULT_FILE):
        os.remove(RESULT_FILE)
    with open(REG_FLAG, 'w') as f:
        f.write('1')
    print("[Face] Registration requested via flag file.")


def is_registration_requested() -> bool:
    return os.path.exists(REG_FLAG)


def get_registration_result():
    if not os.path.exists(RESULT_FILE):
        return None
    try:
        with open(RESULT_FILE, 'r') as f:
            data = json.load(f)
        os.remove(RESULT_FILE)
        return data
    except Exception:
        return None


def complete_registration(cap):
    global _known_encodings, _face_loaded

    if os.path.exists(REG_FLAG):
        os.remove(REG_FLAG)

    ensure_dirs()
    encodings    = []
    photos_taken = 0

    print("[Face] Starting face capture — look at the camera...")

    for attempt in range(50):
        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.3)
                continue

            # Basic validation
            if not hasattr(frame, 'shape') or len(frame.shape) != 3:
                print(f"[Face] Invalid frame shape: {getattr(frame, 'shape', 'None')}")
                continue

            frame = np.array(frame, dtype=np.uint8)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb   = np.ascontiguousarray(rgb, dtype=np.uint8)

            locs = face_recognition.face_locations(rgb, model="hog")
            if not locs:
                time.sleep(0.3)
                continue

            encs = face_recognition.face_encodings(rgb, locs)
            if not encs:
                continue

            encodings.append(encs[0])
            photos_taken += 1
            print(f"[Face] Captured {photos_taken}/10...")

            photo_path = os.path.join(PHOTOS_DIR, f"face_{photos_taken:02d}.jpg")
            cv2.imwrite(photo_path, frame)

            if photos_taken >= 10:
                break
            time.sleep(0.4)
        except Exception as e:
            print(f"[Face] Capture attempt {attempt} error: {e}")
            if "Unsupported image type" in str(e):
                print(f"[Face] DEBUG: rgb.shape={rgb.shape}, rgb.dtype={rgb.dtype}")
            time.sleep(0.5)

    if photos_taken < 5:
        result = {
            "success": False,
            "message": f"Only captured {photos_taken} photos. Make sure your face is clearly visible.",
            "count": photos_taken
        }
        with open(RESULT_FILE, 'w') as f:
            json.dump(result, f)
        return

    np.save(FACE_FILE, np.array(encodings))

    with _load_lock:
        _known_encodings = encodings
        _face_loaded     = True

    result = {
        "success": True,
        "message": f"Face registered successfully with {photos_taken} photos.",
        "count": photos_taken
    }
    with open(RESULT_FILE, 'w') as f:
        json.dump(result, f)

    print(f"[Face] Registration complete — {photos_taken} photos saved.")


def delete_face_profile() -> bool:
    global _known_encodings, _face_loaded
    try:
        if os.path.exists(FACE_FILE):
            os.remove(FACE_FILE)
        if os.path.exists(PHOTOS_DIR):
            for f in os.listdir(PHOTOS_DIR):
                os.remove(os.path.join(PHOTOS_DIR, f))
        with _load_lock:
            _known_encodings = []
            _face_loaded     = False
        return True
    except Exception as e:
        print(f"[Face] Delete error: {e}")
        return False


def get_status() -> dict:
    registered = is_registered()
    count = len(_known_encodings) if _face_loaded else 0
    return {
        "registered":     registered,
        "loaded":         _face_loaded,
        "encoding_count": count,
        "profile_path":   FACE_FILE if registered else None
    }