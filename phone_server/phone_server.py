"""
NullSense — Phone Server (The Brain)
======================================
Runs on phone (via Termux) OR laptop for testing.
Does YOLO detection + serves navigation signals to ESP32 wristbands over WiFi.

ARCHITECTURE:
  Phone camera -> YOLOv8 -> navigation signal -> HTTP server
  ESP32 wristbands poll /signal endpoint over WiFi and fire LRA

HOW TO RUN:
  On laptop (testing):  py phone_server.py
  On phone (Termux):    python phone_server.py

  ESP32 connects to the server IP shown on startup.

Team: NullVision | BCA304A-5 Computer Vision
Christ (Deemed to be University) | 2025-26
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import threading
import socket
from flask import Flask, request, jsonify
from ultralytics import YOLO
import cv2

from shared.config import (
    get_camera_source, MODEL_PATH, CONFIDENCE,
    SERVER_HOST, SERVER_PORT, SIGNAL_PRIORITY
)
from shared.navigation import process_frame, signal_to_bands

# ── Flask App ──
app = Flask(__name__)

# ── Shared State (thread-safe enough for our use) ──
state = {
    'signal':    'CLEAR',
    'intensity': 0,
    'label':     'none',
    'zone':      'CENTER',
    'distance':  'FAR',
    'running':   True,
}


# ── ENDPOINTS ──

@app.route('/signal')
def get_signal():
    """
    ESP32 wristbands poll this endpoint.
    Returns just the signal string (e.g. "STOP").
    band param tells us which band is asking (LEFT/RIGHT).
    """
    band = request.args.get('band', 'LEFT')

    # Get band-specific pattern
    left_vals, right_vals = signal_to_bands(
        state['signal'], state['intensity'])

    if band == 'LEFT':
        pattern = left_vals
    else:
        pattern = right_vals

    # Return signal + pattern as plain text
    # Format: "SIGNAL,front,mid,back"
    return f"{state['signal']},{pattern[0]},{pattern[1]},{pattern[2]}"


@app.route('/status')
def get_status():
    """Full status as JSON — for debugging or a dashboard."""
    return jsonify({
        'signal':    state['signal'],
        'intensity': state['intensity'],
        'label':     state['label'],
        'zone':      state['zone'],
        'distance':  state['distance'],
    })


@app.route('/')
def home():
    """Simple landing page."""
    return f"""
    <html><head><title>NullSense Server</title>
    <meta http-equiv="refresh" content="1">
    <style>
      body{{font-family:sans-serif;background:#111;color:#eee;
            text-align:center;padding:40px}}
      .sig{{font-size:48px;font-weight:bold;margin:20px;
            color:#00c8b4}}
      .info{{font-size:18px;color:#aaa}}
    </style></head>
    <body>
      <h1>NullSense Server</h1>
      <div class="sig">{state['signal']}</div>
      <div class="info">Object: {state['label']}</div>
      <div class="info">Zone: {state['zone']} | Distance: {state['distance']}</div>
      <div class="info">Intensity: {state['intensity']}/3</div>
    </body></html>
    """


# ── Detection Loop (background thread) ──
def detection_loop():
    """
    Continuously reads camera and updates the shared signal state.
    Runs in a background thread so the Flask server stays responsive.
    """
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(
        get_camera_source('single'))

    print("Detection loop started...")

    while state['running']:
        ret, frame = cap.read()
        if not ret:
            continue

        (dets, signal, zone,
         label, distance, intensity) = process_frame(frame, model)

        # Update shared state
        state['signal']    = signal
        state['intensity'] = intensity
        state['label']     = label
        state['zone']      = zone
        state['distance']  = distance

        # Print to console
        print(f"\rSignal: {signal:<16} | {label:<12} | "
              f"{zone:<10} | {distance}", end='')

    cap.release()


def get_local_ip():
    """Get the local IP address to show ESP32 where to connect."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


# ── Main ──
if __name__ == '__main__':
    local_ip = get_local_ip()

    print("=" * 50)
    print("  NullSense Phone Server")
    print("=" * 50)
    print(f"  Server IP:    {local_ip}")
    print(f"  Server Port:  {SERVER_PORT}")
    print(f"  ESP32 URL:    http://{local_ip}:{SERVER_PORT}/signal")
    print(f"  Dashboard:    http://{local_ip}:{SERVER_PORT}/")
    print("=" * 50)
    print("  Set this IP in your ESP32 firmware!")
    print("=" * 50)

    # Start detection in background
    t = threading.Thread(target=detection_loop, daemon=True)
    t.start()

    # Start Flask server
    try:
        app.run(host=SERVER_HOST, port=SERVER_PORT,
                threaded=True, debug=False)
    except KeyboardInterrupt:
        state['running'] = False
        print("\nServer stopped")
