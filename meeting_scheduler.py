import streamlit as st
from datetime import datetime
import json
import os
import subprocess

st.set_page_config(page_title="Zoom Meeting Scheduler", layout="centered")
st.title("🕒 Schedule a Zoom Meeting with Proxy-Meet Bot")

# 1. Inputs
date = st.date_input("Select meeting date")
time_input = st.time_input("Select meeting time")
zoom_link = st.text_input("Enter your Zoom link", placeholder="https://zoom.us/j/123...")

# 2. On button click
if st.button("✅ Schedule Meeting"):
    meeting_datetime = datetime.combine(date, time_input)

    # --- Update .env ---
    env_file = ".env"
    env_updated = False
    new_lines = []

    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()
    else:
        lines = []

    for line in lines:
        if line.startswith("ZOOM_LINK="):
            new_lines.append(f'ZOOM_LINK="{zoom_link}"\n')
            env_updated = True
        else:
            new_lines.append(line)

    if not env_updated:
        new_lines.append(f'ZOOM_LINK="{zoom_link}"\n')

    with open(env_file, "w") as f:
        f.writelines(new_lines)

    # --- Save datetime to file ---
    with open("scheduled_meeting.json", "w") as f:
        f.write(meeting_datetime.isoformat())

    # --- Feedback ---
    st.success(f"✅ Meeting scheduled for {meeting_datetime.strftime('%Y-%m-%d %H:%M')}")
    st.info("⏳ Background scheduler started — Zoom bot will launch at that time.")

    # --- Auto-run scheduler_runner.py ---
    try:
        subprocess.Popen(["python", "scheduler_runner.py"])
    except Exception as e:
        st.error(f"❌ Failed to start scheduler: {e}")
