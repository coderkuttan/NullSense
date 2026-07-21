"""
NullSense — Phase 8: Camera + Sensor Fusion
==============================================
Front camera (DroidCam) YOLO detections fused with ESP32 ultrasonic +
ground sensor readings, read live off the sensor node's SSE stream on
a background thread so it never stalls the camera loop.

Owner: Lead | Status: IN PROGRESS
"""

import sys, os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources is deprecated.*")
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import csv
import time

import cv2
from ultralytics import YOLO

from shared.config import (
    get_camera_source, COCO_MODEL_PATH,
    RELEVANT_OBJECTS, HIGH_PRIORITY, SIGNAL_PRIORITY, GROUND_SPIKE_MM,
)
from shared.navigation import get_zone, get_signal
from shared.sensors import SensorClient

CONFIDENCE = 0.5
AGREE_TOLERANCE_CM = 40       # camera vs sensor agreement window

CV2_COLORS = {
    'STOP': (0, 0, 220), 'CAUTION CENTER': (0, 140, 230),
    'MOVE RIGHT': (0, 200, 220), 'MOVE LEFT': (0, 200, 220),
    'SLIGHT RIGHT': (0, 180, 50), 'SLIGHT LEFT': (0, 180, 50),
    'CLEAR': (180, 200, 0),
}
COL_AGREE  = (0, 200, 0)     # camera + sensor agree
COL_SENSOR = (0, 140, 220)   # sensor overrides camera
COL_CAMERA = (150, 150, 150) # camera-only (center zone / sensor offline)

LOG_DIR = 'logs'

# ─────────────────────────────────────────────
#  Distance helpers
# ─────────────────────────────────────────────
def cm_to_distance(cm):
    """Map a cm distance to the shared 4-level distance vocabulary."""
    if cm < 0:   return 'FAR', 0
    if cm < 50:  return 'VERY CLOSE', 3
    if cm < 100: return 'CLOSE', 2
    if cm < 200: return 'MEDIUM', 1
    return 'FAR', 0


def bbox_depth_cm(box_h, frame_h):
    """Rough camera-only depth estimate from box height: bigger box = closer."""
    ratio = box_h / frame_h
    if ratio > 0.8: return 40
    if ratio > 0.6: return 70
    if ratio > 0.4: return 110
    if ratio > 0.2: return 180
    return 300


def fuse(zone, cam_cm, sensors):
    """
    Fuse camera depth estimate with the ultrasonic reading for this zone.
    Returns (fused_cm, source, agree, sensor_cm).
    CENTER has no forward sensor, so it always falls back to camera-only.
    """
    if not sensors.get('online'):
        return cam_cm, 'camera', False, None

    if zone in ('FAR LEFT', 'LEFT'):
        s_cm = sensors.get('left_cm', -1)
    elif zone in ('RIGHT', 'FAR RIGHT'):
        s_cm = sensors.get('right_cm', -1)
    else:
        return cam_cm, 'camera', False, None

    if s_cm < 0:
        return cam_cm, 'camera', False, None

    agree = abs(s_cm - cam_cm) < AGREE_TOLERANCE_CM
    return s_cm, 'sensor', agree, s_cm


def box_color(source, agree):
    if agree:            return COL_AGREE
    if source == 'sensor': return COL_SENSOR
    return COL_CAMERA


# ─────────────────────────────────────────────
#  Drawing
# ─────────────────────────────────────────────
def draw_zones(frame):
    h, w = frame.shape[:2]
    for r in (0.2, 0.4, 0.6, 0.8):
        cv2.line(frame, (int(w * r), 0), (int(w * r), h), (60, 60, 60), 1)


def draw_topbar(frame, signal, sensors):
    h, w = frame.shape[:2]
    bar = frame.copy()
    cv2.rectangle(bar, (0, 0), (w, 70), (20, 20, 25), -1)
    cv2.addWeighted(bar, 0.6, frame, 0.4, 0, frame)

    color = CV2_COLORS.get(signal, (255, 255, 255))
    cv2.putText(frame, f'SIGNAL: {signal}', (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    if sensors.get('online'):
        txt = (f"L:{sensors['left_cm']:.0f}cm  R:{sensors['right_cm']:.0f}cm  "
               f"GndL:{sensors['gnd_l_mm']}  GndR:{sensors['gnd_r_mm']}")
    else:
        txt = 'SENSORS: offline'
    cv2.putText(frame, txt, (10, 55),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)


def draw_detection(frame, x1, y1, x2, y2, label, zone, cam_cm, fused_cm, color):
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    cv2.putText(frame, f'{label} {zone}', (x1, max(y1 - 22, 10)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    cv2.putText(frame, f'cam~{cam_cm}cm fused={fused_cm:.0f}cm', (x1, max(y1 - 6, 22)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)


# ─────────────────────────────────────────────
#  Main loop
# ─────────────────────────────────────────────
def run():
    model = YOLO(COCO_MODEL_PATH)
    cap = cv2.VideoCapture(get_camera_source('front'))
    if not cap.isOpened():
        print(f"Cannot open front camera. Check DroidCam IP/app in shared/config.py.")
        return

    sensor_client = SensorClient().start()

    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, f'fusion_log_{time.strftime("%Y%m%d_%H%M%S")}.csv')
    log_file = open(log_path, 'w', newline='')
    log_writer = csv.writer(log_file)
    log_writer.writerow([
        'timestamp', 'object_class', 'zone', 'cam_depth_estimate',
        'sensor_distance', 'fused_distance', 'source', 'agree', 'final_signal',
    ])

    print("Phase 8 — Fusion | Press Q to quit")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("frame drop..."); continue

            h, w = frame.shape[:2]
            sensors = sensor_client.latest()

            ground_stop = (sensors.get('gnd_l_mm', 0) > GROUND_SPIKE_MM or
                           sensors.get('gnd_r_mm', 0) > GROUND_SPIKE_MM)

            results = model(frame, conf=CONFIDENCE, verbose=False)[0]

            best_signal, best_priority = 'CLEAR', 0
            rows = []

            for box in results.boxes:
                label = model.names[int(box.cls[0])]
                if label not in RELEVANT_OBJECTS:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, box_h = (x1 + x2) // 2, y2 - y1
                zone = get_zone(cx, w)
                cam_cm = bbox_depth_cm(box_h, h)
                fused_cm, source, agree, sensor_cm = fuse(zone, cam_cm, sensors)
                distance, _ = cm_to_distance(fused_cm)
                signal = get_signal(zone, distance)

                priority = SIGNAL_PRIORITY.get(signal, 1)
                if label in HIGH_PRIORITY:
                    priority += 1
                if priority > best_priority:
                    best_priority, best_signal = priority, signal

                draw_detection(frame, x1, y1, x2, y2, label, zone, cam_cm, fused_cm,
                                box_color(source, agree))
                rows.append((label, zone, cam_cm, sensor_cm, fused_cm, source, agree))

            if ground_stop:
                best_signal = 'STOP'

            for label, zone, cam_cm, sensor_cm, fused_cm, source, agree in rows:
                log_writer.writerow([
                    time.time(), label, zone, cam_cm,
                    sensor_cm if sensor_cm is not None else '', f'{fused_cm:.0f}',
                    source, agree, best_signal,
                ])

            draw_zones(frame)
            draw_topbar(frame, best_signal, sensors)

            cv2.imshow('NullSense Phase 8 — Fusion', frame)
            if cv2.waitKey(1) == ord('q'):
                break
    finally:
        sensor_client.stop()
        log_file.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    run()
