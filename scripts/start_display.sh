#!/bin/bash

# Configuration
DISPLAY_NUM=":99"
SCREEN_RES="1280x720x24"
VNC_PORT="5900"
WEB_PORT="6080"

echo "[Display] Starting Xvfb on $DISPLAY_NUM with resolution $SCREEN_RES..."
Xvfb $DISPLAY_NUM -screen 0 $SCREEN_RES &
XVFB_PID=$!
export DISPLAY=$DISPLAY_NUM

# Wait for X server to start
sleep 2

echo "[Display] Starting Window Manager (fluxbox)..."
fluxbox &
FLUXBOX_PID=$!

echo "[Display] Starting x11vnc..."
x11vnc -display $DISPLAY_NUM -forever -shared -nopw -bg -rfbport $VNC_PORT -o /tmp/x11vnc.log

echo "[Display] Starting Websockify on port $WEB_PORT..."
# Using python module execution for websockify if binary not in path, or assume binary
websockify --web=/usr/share/novnc $WEB_PORT localhost:$VNC_PORT &
WEBSOCKIFY_PID=$!

echo "[Display] System Ready."
echo "XVFB_PID=$XVFB_PID"
echo "FLUXBOX_PID=$FLUXBOX_PID"
echo "WEBSOCKIFY_PID=$WEBSOCKIFY_PID"

# Trap cleanup
cleanup() {
    echo "Shutting down display services..."
    kill $XVFB_PID $FLUXBOX_PID $WEBSOCKIFY_PID
    exit
}
trap cleanup SIGINT SIGTERM

wait $XVFB_PID
