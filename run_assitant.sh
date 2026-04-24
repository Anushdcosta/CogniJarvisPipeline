#!/bin/bash
LOG_FILE="/home/pi/Desktop/dashboard_startup.log"
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000

echo "Starting Jarvis Startup Video" >> "$LOG_FILE"
mpv --fullscreen --ontop --no-osc --no-input-cursor \
    --loop-file=inf --ab-loop-a=7.5 --video-zoom=0.2 \
    /usr/share/plymouth/themes/Cogni-Jarvis-boot/input/video.mp4 > /dev/null 2>&1 &

sleep 2
wlr-randr --output HDMI-A-1 --off >> "$LOG_FILE" 2>&1

cd /home/pi/Desktop/dashboard || exit 1
npm run dev >> "$LOG_FILE" 2>&1 &

echo "Waiting for Port 5173 to open..." >> "$LOG_FILE"

while ! nc -z localhost 5173; do   
  sleep 0.5
done

echo "Port open. Holding shield for compilation..." >> "$LOG_FILE"
sleep 10 

pkill mpv
echo "Dashboard ready. Shield dropped." >> "$LOG_FILE"
