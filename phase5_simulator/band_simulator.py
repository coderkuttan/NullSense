"""
NullSense — Phase 5: Band Simulator GUI
=========================================
Full pygame GUI: camera feed (left) + wristband simulation (right).

Owner: Lead | Status: COMPLETED
"""

import sys, os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources is deprecated.*")
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ultralytics import YOLO
import cv2
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import pygame
from shared.config import (
    get_camera_source, COCO_MODEL_PATH, POTHOLE_MODEL_PATH,
    BLACK, WHITE, GRAY, DARK_GRAY,
    RED, ORANGE, YELLOW, GREEN, TEAL,
    SCREEN_W, SCREEN_H, FPS, HIGH_PRIORITY,
    SIGNAL_PRIORITY, OBSTACLE_ALERT_CM, GROUND_SPIKE_MM,
)
from shared.navigation import process_frame, get_sig_color, signal_to_bands
from shared.sensors import SensorClient

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption('NullSense Phase 5 — Band Simulator')
font_l = pygame.font.SysFont('Arial', 28, bold=True)
font_m = pygame.font.SysFont('Arial', 20)
font_s = pygame.font.SysFont('Arial', 15)


def draw_camera(frame, dets, signal, zone, label, distance):
    cw, ch = 600, 520
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = cv2.resize(rgb, (cw, ch))

    for r in [0.2,0.4,0.6,0.8]:
        cv2.line(res, (int(cw*r),0),(int(cw*r),ch),(60,60,60),1)

    sx, sy = cw/frame.shape[1], ch/frame.shape[0]
    for (x1,y1,x2,y2,lbl,conf,dist) in dets:
        c = (255,0,0) if lbl in HIGH_PRIORITY else (0,255,0)
        cv2.rectangle(res, (int(x1*sx),int(y1*sy)),(int(x2*sx),int(y2*sy)), c, 2)
        cv2.putText(res, f'{lbl} {conf:.0%}',
            (int(x1*sx), max(int(y1*sy)-8,10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, c, 1)

    cv2.rectangle(res, (0,ch-60),(cw,ch),(20,20,20),-1)
    sb = (0,0,220) if 'STOP' in signal else \
         (0,140,230) if 'CAUTION' in signal else \
         (0,200,220) if 'MOVE' in signal else (0,180,50)
    cv2.putText(res, f'SIGNAL: {signal}',
        (10,ch-35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, sb, 2)
    cv2.putText(res, f'Object: {label} | Zone: {zone} | {distance}',
        (10,ch-10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180,180,180), 1)

    surf = pygame.surfarray.make_surface(res.swapaxes(0,1))
    screen.blit(surf, (0,0))


def draw_band(x, y, vals, label, sc):
    bw, bh = 140, 280
    pygame.draw.rect(screen, DARK_GRAY, (x,y,bw,bh), border_radius=15)
    pygame.draw.rect(screen, GRAY, (x,y,bw,bh), 2, border_radius=15)
    lbl = font_m.render(label, True, WHITE)
    screen.blit(lbl, (x+bw//2-lbl.get_width()//2, y+10))
    for i,(v,n) in enumerate(zip(vals, ['FRONT','MID','BACK'])):
        cy, cx = y+65+i*72, x+bw//2
        pygame.draw.circle(screen, GRAY, (cx,cy), 30)
        if v==0:   col,r = (40,40,40),18
        elif v==1: col,r = GREEN,20
        elif v==2: col,r = ORANGE,25
        else:      col,r = RED,29
        pygame.draw.circle(screen, col, (cx,cy), r)
        if v>0: pygame.draw.circle(screen, sc, (cx,cy), r+4, 2)
        nt = font_s.render(n, True, WHITE if v>0 else GRAY)
        screen.blit(nt, (cx-nt.get_width()//2, cy+32))


def draw_arrow(signal, cx, cy):
    s = 22
    if 'LEFT' in signal:
        pygame.draw.polygon(screen, YELLOW, [(cx-s,cy),(cx,cy-s),(cx,cy+s)])
    elif 'RIGHT' in signal:
        pygame.draw.polygon(screen, YELLOW, [(cx+s,cy),(cx,cy-s),(cx,cy+s)])
    elif signal=='STOP':
        pygame.draw.rect(screen, RED, (cx-s,cy-s,s*2,s*2))
    elif signal=='CAUTION CENTER':
        pygame.draw.polygon(screen, ORANGE, [(cx,cy-s),(cx-s,cy+s),(cx+s,cy+s)])
    else:
        pygame.draw.circle(screen, GREEN, (cx,cy), s)
        pygame.draw.line(screen, WHITE, (cx-10,cy),(cx-3,cy+8), 3)
        pygame.draw.line(screen, WHITE, (cx-3,cy+8),(cx+10,cy-6), 3)


def sensor_alert_flags(sensors):
    """(left_alert, right_alert, ground_alert) booleans from the latest sensor reading."""
    if not sensors.get('online'):
        return False, False, False
    left_alert  = 0 <= sensors['left_cm']  < OBSTACLE_ALERT_CM
    right_alert = 0 <= sensors['right_cm'] < OBSTACLE_ALERT_CM
    gnd_alert   = sensors['gnd_l_mm'] > GROUND_SPIKE_MM or sensors['gnd_r_mm'] > GROUND_SPIKE_MM
    return left_alert, right_alert, gnd_alert


def obstacle_intensity(cm):
    if cm < 0:                return 0
    if cm < OBSTACLE_ALERT_CM / 3: return 3
    if cm < OBSTACLE_ALERT_CM * 2 / 3: return 2
    return 1


def sensor_signal(sensors):
    """Map the latest sensor reading straight to a (signal, intensity) pair."""
    left_alert, right_alert, gnd_alert = sensor_alert_flags(sensors)
    if gnd_alert:
        return 'STOP', 3
    if left_alert and right_alert:
        return 'STOP', 3
    if left_alert:
        return 'MOVE RIGHT', obstacle_intensity(sensors['left_cm'])
    if right_alert:
        return 'MOVE LEFT', obstacle_intensity(sensors['right_cm'])
    return 'CLEAR', 0


def combine_signal(cam_signal, cam_intensity, sen_signal, sen_intensity):
    """Camera and sensor each propose a signal; the higher-priority one wins."""
    if SIGNAL_PRIORITY.get(sen_signal, 1) > SIGNAL_PRIORITY.get(cam_signal, 1):
        return sen_signal, sen_intensity
    return cam_signal, cam_intensity


def draw_band_panel(signal, zone, label, distance, intensity, sensors, alert_active):
    pygame.draw.rect(screen, DARK_GRAY, (600,0,400,600))
    border_color = RED if alert_active else GRAY
    pygame.draw.line(screen, border_color, (600,0),(600,600), 4 if alert_active else 2)
    sc = get_sig_color(signal)
    t = font_l.render('NULLSENSE BANDS', True, TEAL)
    screen.blit(t, (800-t.get_width()//2, 15))
    if alert_active and (pygame.time.get_ticks() // 400) % 2 == 0:
        badge = font_m.render('ALERT', True, RED)
        screen.blit(badge, (985-badge.get_width(), 15))
    s = font_l.render(signal, True, sc)
    screen.blit(s, (800-s.get_width()//2, 50))
    draw_arrow(signal, 800, 100)
    lv, rv = signal_to_bands(signal, intensity)
    draw_band(615, 140, lv, 'LEFT', sc)
    draw_band(845, 140, rv, 'RIGHT', sc)
    pygame.draw.rect(screen, (20,20,20), (600,450,400,150))
    pygame.draw.line(screen, GRAY, (600,450),(1000,450), 1)

    left_alert, right_alert, gnd_alert = sensor_alert_flags(sensors)
    if sensors.get('online'):
        sensor_txt = f"L:{sensors['left_cm']:.0f}cm  R:{sensors['right_cm']:.0f}cm"
        ground_txt = f"L:{sensors['gnd_l_mm']}mm  R:{sensors['gnd_r_mm']}mm"
    else:
        sensor_txt, ground_txt = 'offline', 'offline'

    lines = [
        (f'Object  : {label}', (180,180,180)),
        (f'Zone    : {zone}', (180,180,180)),
        (f'Distance: {distance}', (180,180,180)),
        (f'Sensor  : {sensor_txt}', RED if (left_alert or right_alert) else (180,180,180)),
        (f'Ground  : {ground_txt}', RED if gnd_alert else (180,180,180)),
        (f'Pressure: {"#"*intensity}{"-"*(3-intensity)}', sc),
    ]
    for i, (line, color) in enumerate(lines):
        t = font_s.render(line, True, color)
        screen.blit(t, (615, 458+i*23))


def run():
    models = [YOLO(COCO_MODEL_PATH)]
    if os.path.exists(POTHOLE_MODEL_PATH):
        models.append(YOLO(POTHOLE_MODEL_PATH))
    else:
        print(f"[warn] Pothole model not found at '{POTHOLE_MODEL_PATH}' — "
              "running with COCO detection only. Train it via phase6_training/train_potholes.py.")
    cap   = cv2.VideoCapture(get_camera_source('single'))
    clock = pygame.time.Clock()
    sensor_client = SensorClient().start()
    print("Phase 5 — Band Simulator | Press Q to quit")

    running = True
    try:
        while running:
            for e in pygame.event.get():
                if e.type == pygame.QUIT: running = False
                if e.type == pygame.KEYDOWN and e.key == pygame.K_q: running = False

            ret, frame = cap.read()
            if not ret:
                continue

            dets, cam_signal, zone, label, distance, cam_intensity = process_frame(frame, models)

            sensors = sensor_client.latest()
            sen_signal, sen_intensity = sensor_signal(sensors)
            signal, intensity = combine_signal(cam_signal, cam_intensity, sen_signal, sen_intensity)
            left_alert, right_alert, gnd_alert = sensor_alert_flags(sensors)
            alert_active = left_alert or right_alert or gnd_alert

            screen.fill(BLACK)
            draw_camera(frame, dets, signal, zone, label, distance)
            draw_band_panel(signal, zone, label, distance, intensity, sensors, alert_active)
            pygame.display.flip()
            clock.tick(FPS)
    finally:
        sensor_client.stop()
        cap.release()
        pygame.quit()


if __name__ == '__main__':
    run()
