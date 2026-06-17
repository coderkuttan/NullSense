"""
NullSense — Shared Navigation Logic
=====================================
Core logic functions used by ALL phases.
Import from here instead of rewriting in each phase.

Team: NullVision | BCA304A-5 Computer Vision
Christ (Deemed to be University) | 2025-26
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.config import (
    RELEVANT_OBJECTS, HIGH_PRIORITY,
    SIGNAL_PRIORITY, SIGNAL_COLORS, CONFIDENCE
)


def get_distance(box_area, frame_area):
    """Estimate distance from bounding box size. Returns (label, intensity 0-3)."""
    ratio = box_area / frame_area
    if ratio > 0.25:   return 'VERY CLOSE', 3
    elif ratio > 0.10: return 'CLOSE',      2
    elif ratio > 0.03: return 'MEDIUM',     1
    else:              return 'FAR',        0


def get_zone(cx, frame_width):
    """Divide frame into 5 zones based on object x-position."""
    r = cx / frame_width
    if r < 0.20:   return 'FAR LEFT'
    elif r < 0.40: return 'LEFT'
    elif r < 0.60: return 'CENTER'
    elif r < 0.80: return 'RIGHT'
    else:          return 'FAR RIGHT'


def get_signal(zone, distance):
    """Convert zone + distance into a navigation signal."""
    if distance == 'FAR':
        return 'CLEAR'
    if zone == 'CENTER':
        return 'STOP' if distance == 'VERY CLOSE' else 'CAUTION CENTER'
    elif zone == 'LEFT':     return 'MOVE RIGHT'
    elif zone == 'RIGHT':    return 'MOVE LEFT'
    elif zone == 'FAR LEFT': return 'SLIGHT RIGHT'
    else:                    return 'SLIGHT LEFT'


def get_sig_color(signal):
    """Pygame RGB color for a signal."""
    return SIGNAL_COLORS.get(signal, (255, 255, 255))


def signal_to_bands(signal, intensity):
    """
    Map signal to LRA pressure pattern.
    Returns (left_band, right_band), each = [front, mid, back] intensity 0-3.
    """
    i = intensity
    patterns = {
        'CLEAR':          ([0, 0, 0], [0, 0, 0]),
        'STOP':           ([i, i, i], [i, i, i]),
        'CAUTION CENTER': ([0, i, 0], [0, i, 0]),
        'MOVE RIGHT':     ([0, 0, 0], [i, i, 0]),
        'MOVE LEFT':      ([i, i, 0], [0, 0, 0]),
        'SLIGHT RIGHT':   ([0, 0, 0], [0, i, 0]),
        'SLIGHT LEFT':    ([0, i, 0], [0, 0, 0]),
    }
    return patterns.get(signal, ([0, 0, 0], [0, 0, 0]))


def process_frame(frame, model):
    """
    Run YOLO on a frame, return top-priority signal + all detections.

    Returns:
        detections    : list of (x1,y1,x2,y2,label,conf,distance)
        top_signal, top_zone, top_label, top_distance, top_intensity
    """
    h, w       = frame.shape[:2]
    frame_area = h * w

    results = model(frame, verbose=False, conf=CONFIDENCE)

    top_signal    = 'CLEAR'
    top_priority  = 0
    top_zone      = 'CENTER'
    top_label     = 'none'
    top_distance  = 'FAR'
    top_intensity = 0
    detections    = []

    for box in results[0].boxes:
        cls   = int(box.cls[0])
        label = model.names[cls]
        conf  = float(box.conf[0])

        if label not in RELEVANT_OBJECTS:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cx       = (x1 + x2) // 2
        box_area = (x2 - x1) * (y2 - y1)

        zone               = get_zone(cx, w)
        distance, intensity = get_distance(box_area, frame_area)
        signal             = get_signal(zone, distance)
        priority           = SIGNAL_PRIORITY.get(signal, 1)

        if label in HIGH_PRIORITY:
            priority += 1

        detections.append((x1, y1, x2, y2, label, conf, distance))

        if priority > top_priority:
            top_priority  = priority
            top_signal    = signal
            top_zone      = zone
            top_label     = label
            top_distance  = distance
            top_intensity = intensity

    return (detections, top_signal, top_zone,
            top_label, top_distance, top_intensity)
