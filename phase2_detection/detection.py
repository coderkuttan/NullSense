"""
NullSense — Phase 2: Object Detection
=======================================
YOLO detection on DroidCam/webcam with object filtering.

Owner: Any member | Status: COMPLETED
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ultralytics import YOLO
import cv2
from shared.config import (
    get_camera_source, MODEL_PATH, CONFIDENCE,
    RELEVANT_OBJECTS, HIGH_PRIORITY
)


def run():
    model = YOLO(MODEL_PATH)
    cap   = cv2.VideoCapture(get_camera_source('single'))

    print("Phase 2 — Object Detection | Press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        results = model(frame, verbose=False, conf=CONFIDENCE)

        for box in results[0].boxes:
            cls   = int(box.cls[0])
            label = model.names[cls]
            conf  = float(box.conf[0])
            if label not in RELEVANT_OBJECTS:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            color = (0,0,255) if label in HIGH_PRIORITY else (0,255,0)
            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cv2.putText(frame, f'{label} {conf:.0%}',
                (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.imshow('NullSense Phase 2 — Detection', frame)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    run()
