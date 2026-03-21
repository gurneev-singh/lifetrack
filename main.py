import sys
import threading
import schedule
import time
from datetime import datetime
from database import init_db
from tracker  import run_tracker
from reporter import generate_daily_report
from config   import REPORT_HOUR, REPORT_MINUTE

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
           LIFETRACK v1.0
    Your brutal honest life tracker
==========================================
    """)
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        init_db()
        generate_daily_report(print_to_terminal=True)
        return

    init_db()
    print(f"[Main] Started at {datetime.now().strftime('%H:%M:%S')}")
    print("[Main] Ctrl+C to stop and generate report.\n")

    threading.Thread(target=run_tracker, daemon=True).start()
    threading.Thread(target=schedule_daily_report, daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Main] Generating final report...")
        generate_daily_report(print_to_terminal=True)
        print("[Main] Done. See you tomorrow.")

if __name__ == "__main__":
    main()
