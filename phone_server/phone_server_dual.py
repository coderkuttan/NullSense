"""
NullSense — Phone Server (Dual Camera)
========================================
Same as phone_server.py but uses TWO cameras:
  Front camera (DroidCam / index 1) -> forward detection
  Back camera  (webcam index 0)     -> rear detection

Combines both into one signal served to ESP32.

HOW TO RUN:
  py phone_server_dual.py

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
    get_camera_source, MODEL_PATH,
    SERVER_HOST, SERVER_PORT, SIGNAL_PRIORITY
)
from shared.navigation import process_frame, signal_to_bands

app = Flask(__name__)

state = {
    'signal':       'CLEAR',
    'intensity':    0,
    'source':       'NONE',
    'front_signal': 'CLEAR',
    'back_signal':  'CLEAR',
    'front_label':  'none',
    'back_label':   'none',
    'running':      True,
}


def combine_signals(f_sig, f_int, b_sig, b_int):
    """Front camera priority, back camera triggers rear alerts."""
    fp = SIGNAL_PRIORITY.get(f_sig, 1)
    bp = SIGNAL_PRIORITY.get(b_sig, 1)

    if fp >= bp:
        return f_sig, f_int, 'FRONT'

    back_map = {
        'STOP':           'CAUTION CENTER',
        'CAUTION CENTER': 'SLIGHT LEFT',
        'MOVE RIGHT':     'SLIGHT RIGHT',
        'MOVE LEFT':      'SLIGHT LEFT',
        'SLIGHT RIGHT':   'CLEAR',
        'SLIGHT LEFT':    'CLEAR',
        'CLEAR':          'CLEAR',
    }
    return back_map.get(b_sig, 'CLEAR'), b_int, 'BACK'


@app.route('/signal')
def get_signal():
    band = request.args.get('band', 'LEFT')
    left_vals, right_vals = signal_to_bands(
        state['signal'], state['intensity'])
    pattern = left_vals if band == 'LEFT' else right_vals
    return f"{state['signal']},{pattern[0]},{pattern[1]},{pattern[2]}"


@app.route('/status')
def get_status():
    return jsonify(state)


@app.route('/')
def home():
    return f"""
    <html><head><title>NullSense Dual</title>
    <meta http-equiv="refresh" content="1">
    <style>
      body{{font-family:sans-serif;background:#111;color:#eee;
            text-align:center;padding:30px}}
      .sig{{font-size:42px;font-weight:bold;color:#00c8b4;margin:15px}}
      .row{{display:flex;justify-content:center;gap:40px;margin:20px}}
      .card{{background:#222;padding:20px;border-radius:10px;width:180px}}
      .front{{color:#32c850}} .back{{color:#9650dc}}
    </style></head>
    <body>
      <h1>NullSense Dual Camera</h1>
      <div class="sig">{state['signal']}</div>
      <div>Source: {state['source']}</div>
      <div class="row">
        <div class="card">
          <div class="front">FRONT</div>
          <div>{state['front_signal']}</div>
          <div>{state['front_label']}</div>
        </div>
        <div class="card">
          <div class="back">BACK</div>
          <div>{state['back_signal']}</div>
          <div>{state['back_label']}</div>
        </div>
      </div>
    </body></html>
    """


def detection_loop():
    model = YOLO(MODEL_PATH)

    front_cap = cv2.VideoCapture(
        get_camera_source('front'))
    back_cap  = cv2.VideoCapture(get_camera_source('back'))

    print("Dual camera detection started...")

    while state['running']:
        ret_f, ff = front_cap.read()
        ret_b, bf = back_cap.read()

        if ret_f:
            _, fs, _, fl, _, fi = process_frame(ff, model)
        else:
            fs, fl, fi = 'CLEAR', 'none', 0

        if ret_b:
            _, bs, _, bl, _, bi = process_frame(bf, model)
        else:
            bs, bl, bi = 'CLEAR', 'none', 0

        sig, intensity, source = combine_signals(fs, fi, bs, bi)

        state['signal']       = sig
        state['intensity']    = intensity
        state['source']       = source
        state['front_signal'] = fs
        state['back_signal']  = bs
        state['front_label']  = fl
        state['back_label']   = bl

        print(f"\r{sig:<16} | src:{source:<6} | "
              f"F:{fs:<14} B:{bs:<14}", end='')

    front_cap.release()
    back_cap.release()


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


if __name__ == '__main__':
    ip = get_local_ip()
    print("=" * 50)
    print("  NullSense Phone Server (Dual Camera)")
    print("=" * 50)
    print(f"  ESP32 URL:  http://{ip}:{SERVER_PORT}/signal")
    print(f"  Dashboard:  http://{ip}:{SERVER_PORT}/")
    print("=" * 50)

    t = threading.Thread(target=detection_loop, daemon=True)
    t.start()

    try:
        app.run(host=SERVER_HOST, port=SERVER_PORT,
                threaded=True, debug=False)
    except KeyboardInterrupt:
        state['running'] = False
