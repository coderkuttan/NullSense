"""
NullSense — Phase 3: Depth Estimation
=======================================
Distance estimation from bounding box size.

Owner: Any member | Status: COMPLETED
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ultralytics import YOLO
import cv2
from shared.config import (
    get_camera_source, MODEL_PATH, CONFIDENCE, RELEVANT_OBJECTS
)
from shared.navigation import get_distance

COLORS = {
    'VERY CLOSE': (0,0,255), 'CLOSE': (0,165,255),
    'MEDIUM': (0,255,255),   'FAR': (0,255,0),
}


def run():
    model = YOLO(MODEL_PATH)
    cap   = cv2.VideoCapture(get_camera_source('single'))

    print("Phase 3 — Depth Estimation | Press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        h, w = frame.shape[:2]
        frame_area = h * w
        results = model(frame, verbose=False, conf=CONFIDENCE)

        for box in results[0].boxes:
            cls   = int(box.cls[0])
            label = model.names[cls]
            if label not in RELEVANT_OBJECTS:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            box_area = (x2-x1)*(y2-y1)
            distance, _ = get_distance(box_area, frame_area)
            color = COLORS.get(distance, (255,255,255))

            cv2.rectangle(frame, (x1,y1),(x2,y2), color, 2)
            cv2.putText(frame, f'{label} - {distance}',
                (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
            cv2.circle(frame, ((x1+x2)//2,(y1+y2)//2), 5, color, -1)

        y = 30
        for d, c in COLORS.items():
            cv2.putText(frame, d, (10,y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, c, 2)
            y += 25

        cv2.imshow('NullSense Phase 3 — Depth', frame)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    run()
