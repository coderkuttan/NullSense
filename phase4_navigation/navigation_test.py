"""
NullSense — Phase 4: Navigation Logic
=======================================
Detection + depth -> navigation signals with zone map.

Owner: Lead | Status: COMPLETED
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ultralytics import YOLO
import cv2
from shared.config import get_camera_source, COCO_MODEL_PATH, POTHOLE_MODEL_PATH, HIGH_PRIORITY
from shared.navigation import process_frame

CV2_COLORS = {
    'STOP': (0,0,220), 'CAUTION CENTER': (0,140,230),
    'MOVE RIGHT': (0,200,220), 'MOVE LEFT': (0,200,220),
    'SLIGHT RIGHT': (0,180,50), 'SLIGHT LEFT': (0,180,50),
    'CLEAR': (180,200,0),
}


def draw_dashboard(frame, signal, label, zone, distance, intensity):
    h, w = frame.shape[:2]
    color = CV2_COLORS.get(signal, (255,255,255))

    for ratio in [0.2,0.4,0.6,0.8]:
        cv2.line(frame, (int(w*ratio),0),(int(w*ratio),h-80),(60,60,60),1)

    cv2.rectangle(frame, (0,h-80),(w,h),(20,20,20),-1)
    cv2.putText(frame, f'SIGNAL: {signal}',
        (15,h-50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    cv2.putText(frame, f'Object: {label} | Zone: {zone} | Distance: {distance}',
        (15,h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180,180,180), 1)

    for i in range(3):
        c = color if i < intensity else (60,60,60)
        cv2.rectangle(frame, (w-120+i*35,h-55),(w-95+i*35,h-35), c, -1)


def run():
    coco_model = YOLO(COCO_MODEL_PATH)
    pothole_model = YOLO(POTHOLE_MODEL_PATH)
    models = (coco_model, pothole_model)
    cap   = cv2.VideoCapture(get_camera_source('single'))

    print("Phase 4 — Navigation | Press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        dets, signal, zone, label, distance, intensity = process_frame(frame, models)

        for (x1,y1,x2,y2,lbl,conf,dist) in dets:
            color = (0,0,255) if lbl in HIGH_PRIORITY else (0,255,0)
            cv2.rectangle(frame, (x1,y1),(x2,y2), color, 2)
            cv2.putText(frame, f'{lbl} {conf:.0%}',
                (x1,y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        draw_dashboard(frame, signal, label, zone, distance, intensity)
        print(f'\rSignal: {signal:<16} {label:<12} {zone:<10} {distance}', end='')

        cv2.imshow('NullSense Phase 4 — Navigation', frame)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    run()
