#!/bin/bash
sleep 15 

export PATH=$PATH:/usr/bin:/usr/local/bin:/home/pi/.local/bin

LOG="/home/pi/Desktop/bt_startup_debug.log"
echo "Startup attempt at $(date)" > $LOG

cd /home/pi/Desktop/trial1 || echo "Folder not found" >> $LOG

/home/pi/.local/bin/uv run python -u Bluetooth_pipeline.py >> /home/pi/Desktop/bt_startup_debug.log 2>&1
