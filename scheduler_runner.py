import os
import time
import subprocess
from datetime import datetime

SCHEDULE_FILE = "scheduled_meeting.json"
VENV_ACTIVATE = "venv\\Scripts\\activate"  # Windows path
ZOOM_BOT_COMMAND = "python zoom_bot.py"    # Adjust if needed

def run_zoom_bot():
    print("🚀 Running Zoom bot...")

    try:
        # On Windows: use cmd to activate venv and run script
        subprocess.Popen([
            "cmd.exe", "/k", f"{VENV_ACTIVATE} && {ZOOM_BOT_COMMAND}"
        ])
    except Exception as e:
        print(f"❌ Failed to start Zoom bot: {e}")

def main():
    if not os.path.exists(SCHEDULE_FILE):
        print("❌ No scheduled meeting found. Exiting.")
        return

    with open(SCHEDULE_FILE, "r") as f:
        scheduled_time = datetime.fromisoformat(f.read().strip())

    print(f"⏳ Waiting until {scheduled_time}...")

    while datetime.now() < scheduled_time:
        time.sleep(5)

    print("⏰ Time reached!")
    run_zoom_bot()

    # Clean up
    os.remove(SCHEDULE_FILE)
    print("🧹 Removed scheduled_meeting.json")

if __name__ == "__main__":
    main()
