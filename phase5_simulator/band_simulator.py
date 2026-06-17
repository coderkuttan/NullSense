"""
NullSense — Phase 5: Band Simulator GUI
=========================================
Full pygame GUI: camera feed (left) + wristband simulation (right).

Owner: Lead | Status: COMPLETED
"""

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ultralytics import YOLO
import cv2
import pygame
from shared.config import (
    get_camera_source, MODEL_PATH,
    BLACK, WHITE, GRAY, DARK_GRAY,
    RED, ORANGE, YELLOW, GREEN, TEAL,
    SCREEN_W, SCREEN_H, FPS, HIGH_PRIORITY
)
from shared.navigation import process_frame, get_sig_color, signal_to_bands

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


def draw_band_panel(signal, zone, label, distance, intensity):
    pygame.draw.rect(screen, DARK_GRAY, (600,0,400,600))
    pygame.draw.line(screen, GRAY, (600,0),(600,600), 2)
    sc = get_sig_color(signal)
    t = font_l.render('NULLSENSE BANDS', True, TEAL)
    screen.blit(t, (800-t.get_width()//2, 15))
    s = font_l.render(signal, True, sc)
    screen.blit(s, (800-s.get_width()//2, 50))
    draw_arrow(signal, 800, 100)
    lv, rv = signal_to_bands(signal, intensity)
    draw_band(615, 140, lv, 'LEFT', sc)
    draw_band(845, 140, rv, 'RIGHT', sc)
    pygame.draw.rect(screen, (20,20,20), (600,450,400,150))
    pygame.draw.line(screen, GRAY, (600,450),(1000,450), 1)
    for i, line in enumerate([
        f'Object  : {label}', f'Zone    : {zone}',
        f'Distance: {distance}',
        f'Pressure: {"#"*intensity}{"-"*(3-intensity)}'
    ]):
        t = font_s.render(line, True, sc if i==3 else (180,180,180))
        screen.blit(t, (615, 460+i*30))


def run():
    model = YOLO(MODEL_PATH)
    cap   = cv2.VideoCapture(get_camera_source('single'))
    clock = pygame.time.Clock()
    print("Phase 5 — Band Simulator | Press Q to quit")

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_q: running = False

        ret, frame = cap.read()
        if not ret:
            continue

        dets, signal, zone, label, distance, intensity = process_frame(frame, model)
        screen.fill(BLACK)
        draw_camera(frame, dets, signal, zone, label, distance)
        draw_band_panel(signal, zone, label, distance, intensity)
        pygame.display.flip()
        clock.tick(FPS)

    cap.release()
    pygame.quit()


if __name__ == '__main__':
    run()
