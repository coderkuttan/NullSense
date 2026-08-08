"""
NullSense — Phone Server (The Brain)
======================================
Runs on phone (via Termux) OR laptop for testing.
Camera (DroidCam) + helmet sensors -> fusion -> Flask -> wristbands,
with a live pygame view (camera + detection boxes + band panels) —
all in this one process/file.

ARCHITECTURE:
  Phone camera + helmet ESP32 (ultrasonic + ground ToF) -> per-hand fusion
  ESP32 wristbands poll /signal?band=LEFT|RIGHT and fire their LRAs
  Flask runs on a background thread; the camera/fusion/pygame loop owns
  the main thread (pygame needs it).

HOW TO RUN:
  On laptop (testing):  py phone_server.py
  On phone (Termux):    python phone_server.py   (no display -> run headless,
                          see run_headless() below)

  ESP32 wristbands connect to the server IP shown on startup.
  ESP32 helmet node must be reachable at shared.config.SENSOR_POLL_URL.
  Press Q or close the window to quit — this also stops the Flask thread.

Team: NullVision | BCA304A-5 Computer Vision
Christ (Deemed to be University) | 2025-26
"""

import sys, os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources is deprecated.*")
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import threading
import time
import socket

import cv2
import numpy as np
import requests
from flask import Flask, request, jsonify
from ultralytics import YOLO
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import pygame

from shared.config import (
    get_camera_source, COCO_MODEL_PATH, CONFIDENCE,
    SERVER_HOST, SERVER_PORT, SENSOR_POLL_URL,
    RELEVANT_OBJECTS, SIDE_OBSTACLE_CM, GROUND_SPIKE_MM,
    BLACK, WHITE, GRAY, DARK_GRAY, RED, ORANGE, GREEN, TEAL,
    SCREEN_W, SCREEN_H, FPS,
)

app = Flask(__name__)
model = YOLO(COCO_MODEL_PATH)

# ── Shared State ──
# `state`   — latest per-hand signal, written by the main loop, read by Flask
# `sensors` — latest helmet reading, written by poll_sensors, read by the main loop
state = {'left': ('CLEAR', 0), 'right': ('CLEAR', 0), 'running': True}
sensors = {'left_cm': -1, 'right_cm': -1, 'gnd_l_mm': 0, 'gnd_r_mm': 0}
lock = threading.Lock()

SIG_COLORS = {'CLEAR': TEAL, 'OBSTACLE': ORANGE, 'STOP': RED}   # phone_server's own vocabulary


def sig_color(signal):
    return SIG_COLORS.get(signal, WHITE)


def bgr(rgb_color):
    """pygame wants RGB, cv2 wants BGR — flip config colors for cv2 drawing."""
    return tuple(int(c) for c in reversed(rgb_color))


BOX_COLORS_BGR = {0: bgr((90, 90, 90)), 1: bgr(GREEN), 2: bgr(ORANGE), 3: bgr(RED)}


def poll_sensors():
    """Background thread — keeps helmet sensor data fresh."""
    global sensors
    while state['running']:
        try:
            sensors = requests.get(SENSOR_POLL_URL, timeout=0.3).json()
        except Exception:
            pass
        time.sleep(0.1)


def get_zone(cx, width):
    """3-way split — a 2-hand system only needs LEFT/CENTER/RIGHT."""
    r = cx / width
    if r < 0.33: return 'LEFT'
    if r < 0.66: return 'CENTER'
    return 'RIGHT'


def bbox_closeness(box_h, frame_h):
    """Rough 0-3 intensity from how much vertical frame the object fills."""
    ratio = box_h / frame_h
    if ratio > 0.6: return 3
    if ratio > 0.4: return 2
    if ratio > 0.2: return 1
    return 0


def fuse(frame):
    """
    Return (left_signal, left_intensity), (right_signal, right_intensity), detections.
    detections = [(x1,y1,x2,y2,label,conf,zone,closeness), ...] for every relevant
    object seen this frame — closeness 0 means "seen but too far to matter", still
    included so the live view can show it.
    """
    h, w = frame.shape[:2]
    s = sensors

    left_hit = right_hit = center_hit = False
    intensity = 0
    detections = []

    # ---- ground hazard: highest priority, fires BOTH hands (skips camera this frame) ----
    if s.get('gnd_l_mm', 0) > GROUND_SPIKE_MM or s.get('gnd_r_mm', 0) > GROUND_SPIKE_MM:
        return ('STOP', 3), ('STOP', 3), detections

    # ---- ultrasonic side detection ----
    lcm = s.get('left_cm', - 1)
    rcm = s.get('right_cm', -1)
    if 0 < lcm < SIDE_OBSTACLE_CM:
        left_hit = True
        intensity = max(intensity, 3 if lcm < 30 else 2)
    if 0 < rcm < SIDE_OBSTACLE_CM:
        right_hit = True
        intensity = max(intensity, 3 if rcm < 30 else 2)

    # ---- camera detection ----
    results = model(frame, conf=CONFIDENCE, verbose=False)[0]
    for b in results.boxes:
        cls = model.names[int(b.cls[0])]
        conf = float(b.conf[0])
        if cls not in RELEVANT_OBJECTS:
            continue
        x1, y1, x2, y2 = map(int, b.xyxy[0])
        zone = get_zone((x1 + x2) // 2, w)
        close = bbox_closeness(y2 - y1, h)
        detections.append((x1, y1, x2, y2, cls, conf, zone, close))
        if close == 0:
            continue
        intensity = max(intensity, close)
        if zone == 'LEFT':    left_hit = True
        elif zone == 'RIGHT': right_hit = True
        else:                 center_hit = True

    # ---- decide per hand ----
    if center_hit and intensity >= 2:
        return ('STOP', intensity), ('STOP', intensity), detections   # both hands
    if left_hit and right_hit:
        return ('STOP', intensity), ('STOP', intensity), detections
    if left_hit:
        return ('OBSTACLE', intensity), ('CLEAR', 0), detections
    if right_hit:
        return ('CLEAR', 0), ('OBSTACLE', intensity), detections
    return ('CLEAR', 0), ('CLEAR', 0), detections


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


# ── ENDPOINTS ──

@app.route('/signal')
def get_signal():
    """
    ESP32 wristbands poll this endpoint.
    band param tells us which band is asking (LEFT/RIGHT).
    Format: "SIGNAL,intensity"   e.g. "STOP,3" or "CLEAR,0"
    """
    band = request.args.get('band', 'LEFT').upper()
    with lock:
        sig, inten = state['left'] if band == 'LEFT' else state['right']
    return f'{sig},{inten}'


@app.route('/status')
def get_status():
    """Full status as JSON — for debugging or a dashboard."""
    with lock:
        return jsonify({'left': state['left'], 'right': state['right'], 'sensors': sensors})


@app.route('/')
def home():
    """Simple auto-refreshing landing page."""
    with lock:
        left, right = state['left'], state['right']
    return f"""
    <html><head><title>NullSense Server</title>
    <meta http-equiv="refresh" content="1">
    <style>
      body{{font-family:sans-serif;background:#111;color:#eee;
            text-align:center;padding:40px}}
      .sig{{font-size:36px;font-weight:bold;margin:14px}}
      .info{{font-size:16px;color:#aaa}}
    </style></head>
    <body>
      <h1>NullSense Server</h1>
      <div class="sig" style="color:#00c8b4">LEFT: {left[0]} ({left[1]})</div>
      <div class="sig" style="color:#00c8b4">RIGHT: {right[0]} ({right[1]})</div>
      <div class="info">US L:{sensors.get('left_cm',-1):.0f}cm R:{sensors.get('right_cm',-1):.0f}cm</div>
      <div class="info">Gnd L:{sensors.get('gnd_l_mm',0)}mm R:{sensors.get('gnd_r_mm',0)}mm</div>
    </body></html>
    """


# ── Pygame view ──

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption('NullSense — Phone Server')
font_l = pygame.font.SysFont('Arial', 26, bold=True)
font_m = pygame.font.SysFont('Arial', 19)
font_s = pygame.font.SysFont('Arial', 15)


def draw_camera(frame, detections, left, right):
    cw, ch = 600, 600
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = cv2.resize(rgb, (cw, ch))
    sx, sy = cw / frame.shape[1], ch / frame.shape[0]

    for r in (0.33, 0.66):   # matches get_zone's LEFT/CENTER/RIGHT split
        cv2.line(res, (int(cw * r), 0), (int(cw * r), ch), (60, 60, 60), 1)

    for (x1, y1, x2, y2, label, conf, _zone, close) in detections:
        c = BOX_COLORS_BGR.get(close, BOX_COLORS_BGR[0])
        p1 = (int(x1 * sx), int(y1 * sy))
        p2 = (int(x2 * sx), int(y2 * sy))
        cv2.rectangle(res, p1, p2, c, 2)
        cv2.putText(res, f'{label} {conf:.0%}', (p1[0], max(p1[1] - 8, 10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1)

    cv2.rectangle(res, (0, ch - 70), (cw, ch), (20, 20, 20), -1)
    lc = bgr(sig_color(left[0]))
    rc = bgr(sig_color(right[0]))
    cv2.putText(res, f'L: {left[0]} ({left[1]})', (10, ch - 42),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, lc, 2)
    rtxt = f'R: {right[0]} ({right[1]})'
    (tw, _), _ = cv2.getTextSize(rtxt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.putText(res, rtxt, (cw - tw - 10, ch - 42),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, rc, 2)

    s = sensors
    sensor_txt = (f"US  L:{s.get('left_cm',-1):.0f}cm  R:{s.get('right_cm',-1):.0f}cm    "
                  f"ToF L:{s.get('gnd_l_mm',0)}mm  R:{s.get('gnd_r_mm',0)}mm")
    cv2.putText(res, sensor_txt, (10, ch - 12),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    surf = pygame.surfarray.make_surface(res.swapaxes(0, 1))
    screen.blit(surf, (0, 0))


def draw_hand(x, y, label, signal, intensity, us_cm, gnd_mm, alert):
    bw, bh = 380, 240
    sc = sig_color(signal)
    pygame.draw.rect(screen, DARK_GRAY, (x, y, bw, bh), border_radius=15)
    border_c = RED if alert else GRAY
    pygame.draw.rect(screen, border_c, (x, y, bw, bh), 3 if alert else 2, border_radius=15)

    lbl = font_m.render(f'{label} BAND', True, WHITE)
    screen.blit(lbl, (x + bw // 2 - lbl.get_width() // 2, y + 12))
    sig = font_l.render(signal, True, sc)
    screen.blit(sig, (x + bw // 2 - sig.get_width() // 2, y + 42))

    cx, cy = x + bw // 2, y + 130
    pygame.draw.circle(screen, GRAY, (cx, cy), 48)
    if   intensity == 0: col, r = (40, 40, 40), 30
    elif intensity == 1: col, r = GREEN, 36
    elif intensity == 2: col, r = ORANGE, 42
    else:                  col, r = RED,    47
    pygame.draw.circle(screen, col, (cx, cy), r)
    if intensity > 0:
        pygame.draw.circle(screen, sc, (cx, cy), r + 5, 2)
    it = font_s.render(f'intensity {intensity}/3 (all 3 LRAs)', True, WHITE if intensity > 0 else GRAY)
    screen.blit(it, (cx - it.get_width() // 2, cy + r + 10))

    us_alert = 0 <= us_cm < SIDE_OBSTACLE_CM
    gnd_alert = gnd_mm > GROUND_SPIKE_MM
    info = font_s.render(f'US: {us_cm:.0f}cm    Gnd: {gnd_mm}mm', True,
        RED if (us_alert or gnd_alert) else (180, 180, 180))
    screen.blit(info, (x + bw // 2 - info.get_width() // 2, y + bh - 24))


def draw_no_camera():
    cw, ch = 600, 600
    pygame.draw.rect(screen, (25, 20, 20), (0, 0, cw, ch))
    msg = font_l.render('NO CAMERA', True, RED)
    screen.blit(msg, (cw // 2 - msg.get_width() // 2, ch // 2 - 40))
    sub = font_s.render('Check DroidCam IP in shared/config.py — running sensor-only', True, GRAY)
    screen.blit(sub, (cw // 2 - sub.get_width() // 2, ch // 2 + 10))


def run_display():
    """Main-thread loop: camera + fusion + pygame view. Flask runs on a background thread.
    Camera being unavailable degrades to sensor-only fusion (still services WiFi wristbands
    and the pygame window) rather than exiting — this thread dying would kill the Flask
    daemon thread too, taking the whole server down with it."""
    cap = cv2.VideoCapture(get_camera_source('single'))
    camera_ok = cap.isOpened()
    if camera_ok:
        print('[ok] Camera open — fusion running')
    else:
        print('[!] Cannot open camera — check DroidCam IP in shared/config.py')
        print('[!] Continuing in sensor-only mode (ground + ultrasonic fusion still active)')
    clock = pygame.time.Clock()
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    while state['running']:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: state['running'] = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_q: state['running'] = False

        if camera_ok:
            ok, frame = cap.read()
            if not ok:
                continue
        else:
            frame = blank_frame   # camera-detection stays empty; ground/ultrasonic still run

        left, right, detections = fuse(frame)
        with lock:
            state['left'], state['right'] = left, right
        s = sensors

        left_alert  = s.get('gnd_l_mm', 0) > GROUND_SPIKE_MM or 0 <= s.get('left_cm', -1)  < SIDE_OBSTACLE_CM
        right_alert = s.get('gnd_r_mm', 0) > GROUND_SPIKE_MM or 0 <= s.get('right_cm', -1) < SIDE_OBSTACLE_CM

        screen.fill(BLACK)
        if camera_ok:
            draw_camera(frame, detections, left, right)
        else:
            draw_no_camera()
        draw_hand(610, 40,  'LEFT',  left[0],  left[1],  s.get('left_cm', -1),  s.get('gnd_l_mm', 0),  left_alert)
        draw_hand(610, 320, 'RIGHT', right[0], right[1], s.get('right_cm', -1), s.get('gnd_r_mm', 0), right_alert)
        pygame.display.flip()
        clock.tick(FPS)

    cap.release()
    pygame.quit()


def run_headless():
    """No-display fallback (e.g. running on-phone via Termux) — same fusion, console output only."""
    cap = cv2.VideoCapture(get_camera_source('single'))
    if not cap.isOpened():
        print('[!] Cannot open camera — check DroidCam IP in shared/config.py')
        state['running'] = False
        return
    print('[ok] Camera open — fusion running (headless)')

    while state['running']:
        ok, frame = cap.read()
        if not ok:
            continue
        left, right, _ = fuse(frame)
        with lock:
            state['left'], state['right'] = left, right
        print(f"\rL:{left[0]}({left[1]})  R:{right[0]}({right[1]})  "
              f"US L:{sensors.get('left_cm',-1):.0f} R:{sensors.get('right_cm',-1):.0f}  "
              f"Gnd {sensors.get('gnd_l_mm',0)}/{sensors.get('gnd_r_mm',0)}", end='')

    cap.release()


# ── Main ──
if __name__ == '__main__':
    local_ip = get_local_ip()

    print('=' * 50)
    print('  NullSense Phone Server')
    print('=' * 50)
    print(f'  Server IP:    {local_ip}')
    print(f'  Server Port:  {SERVER_PORT}')
    print(f'  Helmet node:  {SENSOR_POLL_URL}')
    print(f'  ESP32 URL:    http://{local_ip}:{SERVER_PORT}/signal?band=LEFT')
    print(f'  Dashboard:    http://{local_ip}:{SERVER_PORT}/')
    print('=' * 50)
    print('  Set SERVER_IP in your wristband firmware to the IP above!')
    print('=' * 50)

    threading.Thread(target=poll_sensors, daemon=True).start()
    threading.Thread(
        target=lambda: app.run(host=SERVER_HOST, port=SERVER_PORT,
                                threaded=True, debug=False, use_reloader=False),
        daemon=True,
    ).start()

    try:
        run_display()
    except KeyboardInterrupt:
        pass
    finally:
        state['running'] = False
        print('\nServer stopped')
