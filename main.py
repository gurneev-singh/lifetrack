# LifeTrack - main.py
# Entry point. Starts all tracking threads.
# Usage: python main.py
# Usage: python main.py --report

import sys
import threading
import schedule
import time
from datetime import datetime

from core.database import init_db, log_screenshot, log_webcam
from features.tracking.tracker import run_tracker
from features.tracking.screenshot_analyzer import run_screenshot_analyzer
from features.tracking.webcam_analyzer import run_webcam_analyzer, release_camera
from features.reporting.reporter import generate_daily_report
from core.privacy import start_hotkey_listener
from core.config import REPORT_HOUR, REPORT_MINUTE


def schedule_daily_report():
    t = f"{REPORT_HOUR:02d}:{REPORT_MINUTE:02d}"
    schedule.every().day.at(t).do(generate_daily_report)
    print(f"[Main] Auto report at {t} every night")
    while True:
        schedule.run_pending()
        time.sleep(30)


def main():
    print("""
==========================================
        LIFETRACK v2.1
   Screen + Webcam AI analysis
   Win+Shift+P to pause all capture
==========================================
    """)

    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        init_db()
        generate_daily_report(print_to_terminal=True)
        return

    init_db()
    print(f"[Main] Started at {datetime.now().strftime('%H:%M:%S')}")
    print("[Main] Ctrl+C to stop and generate report.\n")

    # Privacy hotkey
    start_hotkey_listener()

    # Window title tracker (fallback)
    threading.Thread(target=run_tracker, daemon=True).start()

    # Screen AI analyzer
    threading.Thread(
        target=run_screenshot_analyzer,
        args=(log_screenshot,),
        daemon=True
    ).start()

    # Webcam AI analyzer
    threading.Thread(
        target=run_webcam_analyzer,
        args=(log_webcam,),
        daemon=True
    ).start()

    # Daily report scheduler
    threading.Thread(target=schedule_daily_report, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Main] Stopping — releasing camera...")
        release_camera()
        print("[Main] Generating final report...")
        generate_daily_report(print_to_terminal=True)
        print("[Main] Done. See you tomorrow.")


if __name__ == "__main__":
    main()