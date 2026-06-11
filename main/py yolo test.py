from ultralytics import YOLO
import cv2
import pygame
import threading
import time
import sys

# ── Init Pygame ──
pygame.init()
BAND_WIDTH, BAND_HEIGHT = 400, 600
band_screen = pygame.display.set_mode((BAND_WIDTH, BAND_HEIGHT))
pygame.display.set_caption('NullSense - Band Simulator')

# ── Fonts ──
font_large = pygame.font.SysFont('Arial', 28, bold=True)
font_med   = pygame.font.SysFont('Arial', 20)
font_small = pygame.font.SysFont('Arial', 15)

# ── Colors ──
BLACK      = (15, 15, 15)
WHITE      = (255, 255, 255)
GRAY       = (60, 60, 60)
DARK_GRAY  = (30, 30, 30)
RED        = (220, 50, 50)
ORANGE     = (230, 140, 30)
YELLOW     = (220, 200, 0)
GREEN      = (50, 200, 80)
BLUE       = (50, 120, 220)
TEAL       = (0, 200, 180)

# ── Global State ──
state = {
    'signal':    'CLEAR',
    'zone':      'CENTER',
    'label':     'none',
    'distance':  'FAR',
    'intensity': 0,
    'left_band':  [0, 0, 0],   # 3 LRAs per band [front, mid, back]
    'right_band': [0, 0, 0],
}

# ── Signal → Band Pattern ──
def signal_to_bands(signal, intensity):
    """
    Returns (left_band, right_band)
    Each band = [front_lra, mid_lra, back_lra]
    Value 0-3 = pressure intensity
    """
    i = intensity

    patterns = {
        'CLEAR':          ([0,0,0], [0,0,0]),
        'STOP':           ([i,i,i], [i,i,i]),   # Both bands full
        'CAUTION CENTER': ([0,i,0], [0,i,0]),   # Both mid pulse
        'MOVE RIGHT':     ([0,0,0], [i,i,0]),   # Right band front+mid
        'MOVE LEFT':      ([i,i,0], [0,0,0]),   # Left band front+mid
        'SLIGHT RIGHT':   ([0,0,0], [0,i,0]),   # Right band mid only
        'SLIGHT LEFT':    ([0,i,0], [0,0,0]),   # Left band mid only
    }

    return patterns.get(signal, ([0,0,0], [0,0,0]))

# ── Draw Single Band ──
def draw_band(surface, x, y, band_values, label, signal_color):
    band_w, band_h = 140, 300
    lra_names = ['FRONT', 'MID', 'BACK']

    # Band background
    pygame.draw.rect(surface, DARK_GRAY,
        (x, y, band_w, band_h), border_radius=20)
    pygame.draw.rect(surface, GRAY,
        (x, y, band_w, band_h), 2, border_radius=20)

    # Band label
    lbl = font_med.render(label, True, WHITE)
    surface.blit(lbl, (x + band_w//2 - lbl.get_width()//2, y + 12))

    # LRA circles
    for i, (val, name) in enumerate(zip(band_values, lra_names)):
        cy = y + 70 + i * 80
        cx = x + band_w // 2

        # Outer ring
        pygame.draw.circle(surface, GRAY, (cx, cy), 35)

        # Active fill based on intensity
        if val == 0:
            color = (40, 40, 40)
            radius = 20
        elif val == 1:
            color = GREEN
            radius = 22
        elif val == 2:
            color = ORANGE
            radius = 28
        else:
            color = RED
            radius = 33

        pygame.draw.circle(surface, color, (cx, cy), radius)

        # Pulse ring when active
        if val > 0:
            pygame.draw.circle(surface, signal_color,
                (cx, cy), radius + 5, 2)

        # LRA name
        name_txt = font_small.render(name, True,
            WHITE if val > 0 else GRAY)
        surface.blit(name_txt,
            (cx - name_txt.get_width()//2, cy + 38))

# ── Draw Signal Arrow ──
def draw_arrow(surface, signal, cx, cy):
    color = WHITE
    size  = 25

    if signal == 'MOVE LEFT' or signal == 'SLIGHT LEFT':
        # Left arrow
        pygame.draw.polygon(surface, YELLOW, [
            (cx-size, cy),
            (cx, cy-size),
            (cx, cy+size)
        ])
    elif signal == 'MOVE RIGHT' or signal == 'SLIGHT RIGHT':
        # Right arrow
        pygame.draw.polygon(surface, YELLOW, [
            (cx+size, cy),
            (cx, cy-size),
            (cx, cy+size)
        ])
    elif signal == 'STOP':
        # Stop square
        pygame.draw.rect(surface, RED,
            (cx-size, cy-size, size*2, size*2))
    elif signal == 'CAUTION CENTER':
        # Warning triangle
        pygame.draw.polygon(surface, ORANGE, [
            (cx, cy-size),
            (cx-size, cy+size),
            (cx+size, cy+size)
        ])
    else:
        # Clear checkmark circle
        pygame.draw.circle(surface, GREEN, (cx, cy), size)
        pygame.draw.line(surface, WHITE,
            (cx-12, cy), (cx-4, cy+10), 3)
        pygame.draw.line(surface, WHITE,
            (cx-4, cy+10), (cx+12, cy-8), 3)

# ── Draw Full Band Screen ──
def draw_band_screen(signal, zone, label, distance, intensity):
    band_screen.fill(BLACK)

    # Signal color
    sig_colors = {
        'STOP':           RED,
        'CAUTION CENTER': ORANGE,
        'MOVE RIGHT':     YELLOW,
        'MOVE LEFT':      YELLOW,
        'SLIGHT RIGHT':   GREEN,
        'SLIGHT LEFT':    GREEN,
        'CLEAR':          TEAL,
    }
    sig_color = sig_colors.get(signal, WHITE)

    # Title
    title = font_large.render('NULLSENSE BANDS', True, TEAL)
    band_screen.blit(title,
        (BAND_WIDTH//2 - title.get_width()//2, 15))

    # Signal display
    sig_txt = font_large.render(signal, True, sig_color)
    band_screen.blit(sig_txt,
        (BAND_WIDTH//2 - sig_txt.get_width()//2, 50))

    # Arrow
    draw_arrow(band_screen, signal, BAND_WIDTH//2, 105)

    # Left + Right bands
    left_vals, right_vals = signal_to_bands(signal, intensity)
    draw_band(band_screen, 20,  160, left_vals,  'LEFT BAND',  sig_color)
    draw_band(band_screen, 240, 160, right_vals, 'RIGHT BAND', sig_color)

    # Info bar
    pygame.draw.rect(band_screen, DARK_GRAY, (0, 470, BAND_WIDTH, 130))
    pygame.draw.line(band_screen, GRAY, (0, 470), (BAND_WIDTH, 470), 1)

    info_lines = [
        f'Object  :  {label}',
        f'Zone    :  {zone}',
        f'Distance:  {distance}',
        f'Intensity: {"█" * intensity}{"░" * (3-intensity)}',
    ]
    for i, line in enumerate(info_lines):
        txt = font_small.render(line, True,
            sig_color if i == 3 else (180, 180, 180))
        band_screen.blit(txt, (20, 478 + i * 28))

    pygame.display.flip()

# ── Object + Navigation Logic ──
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

def get_distance(box_area, frame_area):
    ratio = box_area / frame_area
    if ratio > 0.25:   return 'VERY CLOSE', 3
    elif ratio > 0.10: return 'CLOSE', 2
    elif ratio > 0.03: return 'MEDIUM', 1
    else:              return 'FAR', 0

def get_zone(cx, frame_width):
    r = cx / frame_width
    if r < 0.20:   return 'FAR LEFT'
    elif r < 0.40: return 'LEFT'
    elif r < 0.60: return 'CENTER'
    elif r < 0.80: return 'RIGHT'
    else:          return 'FAR RIGHT'

def get_signal(zone, distance):
    if distance == 'FAR':    return 'CLEAR'
    if zone == 'CENTER':
        return 'STOP' if distance == 'VERY CLOSE' else 'CAUTION CENTER'
    elif zone == 'LEFT':     return 'MOVE RIGHT'
    elif zone == 'RIGHT':    return 'MOVE LEFT'
    elif zone == 'FAR LEFT': return 'SLIGHT RIGHT'
    else:                    return 'SLIGHT LEFT'

SIGNAL_PRIORITY = {
    'STOP': 5, 'CAUTION CENTER': 4,
    'MOVE RIGHT': 3, 'MOVE LEFT': 3,
    'SLIGHT RIGHT': 2, 'SLIGHT LEFT': 2,
    'CLEAR': 1
}

# ── Main ──
model = YOLO('yolov8n.pt')

# DroidCam or webcam
USE_PHONE_CAM = True         # Set True for DroidCam
PHONE_IP      = '10.6.26.75' # Replace with your IP

cap = cv2.VideoCapture(
    f'http://{PHONE_IP}:4747/video' if USE_PHONE_CAM
    else 0
)

clock = pygame.time.Clock()

while True:
    # ── Pygame events ──
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            cap.release()
            pygame.quit()
            sys.exit()

    ret, frame = cap.read()
    if not ret:
        continue

    h, w = frame.shape[:2]
    frame_area = h * w

    # Zone lines
    for ratio in [0.2, 0.4, 0.6, 0.8]:
        cv2.line(frame,
            (int(w*ratio), 0),
            (int(w*ratio), h-100),
            (60,60,60), 1)

    results = model(frame, verbose=False, conf=0.5)

    top_signal   = 'CLEAR'
    top_priority = 0
    top_zone     = 'CENTER'
    top_label    = 'none'
    top_distance = 'FAR'
    top_intensity= 0

    for box in results[0].boxes:
        cls   = int(box.cls[0])
        label = model.names[cls]
        conf  = float(box.conf[0])

        if label not in RELEVANT_OBJECTS:
            continue

        x1,y1,x2,y2 = map(int, box.xyxy[0])
        cx       = (x1+x2)//2
        box_area = (x2-x1)*(y2-y1)

        zone     = get_zone(cx, w)
        distance, intensity = get_distance(box_area, frame_area)
        signal   = get_signal(zone, distance)

        priority = SIGNAL_PRIORITY.get(signal, 1)
        if label in HIGH_PRIORITY:
            priority += 1

        if priority > top_priority:
            top_priority  = priority
            top_signal    = signal
            top_zone      = zone
            top_label     = label
            top_distance  = distance
            top_intensity = intensity

        color = (0,0,255) if label in HIGH_PRIORITY else (0,255,0)
        cv2.rectangle(frame, (x1,y1),(x2,y2), color, 2)
        cv2.putText(frame,
            f'{label} {conf:.0%} | {distance}',
            (x1, y1-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5, color, 2)

    # ── Camera dashboard ──
    cv2.rectangle(frame, (0,h-80),(w,h),(30,30,30),-1)
    cv2.putText(frame, f'SIGNAL: {top_signal}',
        (20, h-50),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7, (0,255,255), 2)
    cv2.putText(frame,
        f'Object: {top_label} | Zone: {top_zone} | {top_distance}',
        (20, h-20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5, (200,200,200), 1)

    # ── Update band screen ──
    draw_band_screen(
        top_signal, top_zone,
        top_label, top_distance,
        top_intensity
    )

    cv2.imshow('NullSense - Camera', frame)

    if cv2.waitKey(1) == ord('q'):
        break

    clock.tick(30)

cap.release()
pygame.quit()
cv2.destroyAllWindows()
