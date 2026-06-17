"""
NullSense — Phase 1: Environment Setup & Test
===============================================
Run this FIRST to verify everything is installed.

Owner: Any member | Status: COMPLETED

Team: NullVision | BCA304A-5 Computer Vision
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


def check(pkg, imp=None):
    imp = imp or pkg
    try:
        m = __import__(imp)
        v = getattr(m, '__version__', 'ok')
        print(f"  [OK] {pkg:<22} {v}")
        return True
    except ImportError:
        print(f"  [--] {pkg:<22} NOT INSTALLED")
        return False


def test_camera():
    import cv2
    from shared.config import get_camera_source, CAM_SOURCE
    src = get_camera_source('single')
    cap = cv2.VideoCapture(src)
    ok = cap.isOpened()
    if ok:
        ret, frame = cap.read()
        if ret:
            print(f"  [OK] Camera ({CAM_SOURCE})    Working {frame.shape}")
            cap.release()
            return True
    print(f"  [--] Camera ({CAM_SOURCE})    NOT WORKING")
    print(f"       Source tried: {src}")
    print(f"       If DroidCam: check IP in shared/config.py + app running")
    cap.release()
    return False


def test_yolo():
    from ultralytics import YOLO
    import numpy as np
    model = YOLO('yolov8n.pt')
    model(np.zeros((480, 640, 3), dtype='uint8'), verbose=False)
    print("  [OK] YOLOv8                Running")
    return True


if __name__ == '__main__':
    print("\n" + "="*48)
    print("  NullSense — Phase 1 Setup Check")
    print("="*48)

    print("\nPackages:")
    pkgs = [('ultralytics','ultralytics'), ('opencv-python','cv2'),
            ('pygame','pygame'), ('numpy','numpy'), ('flask','flask'),
            ('requests','requests')]
    for p, i in pkgs:
        check(p, i)

    print("\nTests:")
    try: test_yolo()
    except Exception as e: print(f"  [--] YOLOv8 FAILED: {e}")

    test_camera()

    print("\n" + "="*48)
    print("  If all OK -> proceed to Phase 2")
    print("="*48 + "\n")
