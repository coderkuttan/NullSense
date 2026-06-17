"""
NullSense — Shared Configuration
==================================
Central config used by ALL phases. EDIT THIS FIRST.

CURRENT MODE: DroidCam testing
  - Install DroidCam app on phone + DroidCam client on laptop
  - Connect phone and laptop to same WiFi
  - Put your DroidCam IP below in DROIDCAM_IP

Team: NullVision | BCA304A-5 Computer Vision
Christ (Deemed to be University) | 2025-26
"""

# ══════════════════════════════════════════════
#  CAMERA SOURCE  — change CAM_SOURCE to switch
# ══════════════════════════════════════════════
# Options:
#   'droidcam' -> phone camera via DroidCam (TESTING — current)
#   'webcam'   -> laptop built-in webcam
CAM_SOURCE = 'droidcam'

DROIDCAM_IP   = '192.168.1.14'    # <-- CHANGE to your DroidCam IP
DROIDCAM_PORT = 4747

# For dual camera testing (Phase 7):
#   FRONT = DroidCam (phone)
#   BACK  = laptop webcam (index 0)
FRONT_SOURCE = 'droidcam'   # 'droidcam' or 'webcam'
BACK_SOURCE  = 'webcam'     # 'droidcam' or 'webcam'
WEBCAM_INDEX = 0


def get_camera_source(which='single'):
    """
    Returns the cv2.VideoCapture argument for the requested camera.
    which = 'single' | 'front' | 'back'
    """
    droidcam_url = f'http://{DROIDCAM_IP}:{DROIDCAM_PORT}/video'

    if which == 'single':
        return droidcam_url if CAM_SOURCE == 'droidcam' else WEBCAM_INDEX
    elif which == 'front':
        return droidcam_url if FRONT_SOURCE == 'droidcam' else WEBCAM_INDEX
    elif which == 'back':
        return droidcam_url if BACK_SOURCE == 'droidcam' else WEBCAM_INDEX
    return WEBCAM_INDEX


# ══════════════════════════════════════════════
#  MODEL
# ══════════════════════════════════════════════
MODEL_PATH = 'yolov8n.pt'   # change to 'models/nullsense_best.pt' after Phase 6
CONFIDENCE = 0.5

# ══════════════════════════════════════════════
#  PHONE SERVER (for ESP32 wristbands)
# ══════════════════════════════════════════════
SERVER_HOST = '0.0.0.0'
SERVER_PORT = 5000
HOTSPOT_SSID = 'NullSense'
HOTSPOT_PASS = 'nullsense123'

# ══════════════════════════════════════════════
#  DETECTION OBJECTS
# ══════════════════════════════════════════════
RELEVANT_OBJECTS = [
    'person',
    'bicycle', 'car', 'motorcycle', 'bus', 'truck', 'train',
    'dog', 'cat', 'cow', 'horse', 'bird',
    'traffic light', 'stop sign', 'fire hydrant', 'bench',
    'chair', 'couch', 'bed', 'dining table', 'toilet',
    'bottle', 'backpack', 'handbag', 'suitcase', 'umbrella',
]

HIGH_PRIORITY = [
    'person', 'car', 'motorcycle',
    'bus', 'truck', 'dog', 'cow'
]

# ══════════════════════════════════════════════
#  SIGNAL PRIORITY + INDEX
# ══════════════════════════════════════════════
SIGNAL_PRIORITY = {
    'STOP':           5,
    'CAUTION CENTER': 4,
    'MOVE RIGHT':     3,
    'MOVE LEFT':      3,
    'SLIGHT RIGHT':   2,
    'SLIGHT LEFT':    2,
    'CLEAR':          1
}

SIGNAL_INDEX = {
    'CLEAR':          0,
    'STOP':           1,
    'CAUTION CENTER': 2,
    'MOVE LEFT':      3,
    'MOVE RIGHT':     4,
    'SLIGHT LEFT':    5,
    'SLIGHT RIGHT':   6,
}

# ══════════════════════════════════════════════
#  COLORS (Pygame RGB)
# ══════════════════════════════════════════════
BLACK     = (15,  15,  15)
WHITE     = (255, 255, 255)
GRAY      = (60,  60,  60)
DARK_GRAY = (30,  30,  30)
RED       = (220, 50,  50)
ORANGE    = (230, 140, 30)
YELLOW    = (220, 200, 0)
GREEN     = (50,  200, 80)
TEAL      = (0,   200, 180)
PURPLE    = (150, 80,  220)

SIGNAL_COLORS = {
    'STOP':           RED,
    'CAUTION CENTER': ORANGE,
    'MOVE RIGHT':     YELLOW,
    'MOVE LEFT':      YELLOW,
    'SLIGHT RIGHT':   GREEN,
    'SLIGHT LEFT':    GREEN,
    'CLEAR':          TEAL,
}

# ══════════════════════════════════════════════
#  DISPLAY
# ══════════════════════════════════════════════
SCREEN_W = 1000
SCREEN_H = 600
FPS      = 30
