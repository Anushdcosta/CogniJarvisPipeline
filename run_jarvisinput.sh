#!/bin/bash

DASHBOARD_URL="http://127.0.0.1:5173"
LOG_FILE="/home/pi/Desktop/jarvis_startup.log"

echo "--- Jarvis Startup $(date) ---" > "$LOG_FILE"

echo "Waiting for dashboard at $DASHBOARD_URL..." >> "$LOG_FILE"

while ! curl -s "$DASHBOARD_URL" > /dev/null; do
    echo "Dashboard not ready" >> "$LOG_FILE"
    sleep 2
done

echo "Dashboard is LIVE!." >> "$LOG_FILE"

cd /home/pi/Desktop/trial1
/home/pi/.local/bin/uv run python -u Cogni_pipeline.py >> "$LOG_FILE" 2>&1
