"""
NullSense — Phase 7: Dual Camera Logic
=======================================
Front + back camera coverage with combined signal.

TESTING SETUP (DroidCam):
  FRONT = DroidCam phone   (set in shared/config.py FRONT_SOURCE='droidcam')
  BACK  = laptop webcam    (set in shared/config.py BACK_SOURCE='webcam')

Owner: Friend 2 | Status: IN PROGRESS
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
    BLACK, GRAY, DARK_GRAY,
    RED, ORANGE, YELLOW, GREEN, TEAL, PURPLE,
    SIGNAL_PRIORITY, FPS, HIGH_PRIORITY
)
from shared.navigation import process_frame, get_sig_color

pygame.init()
SCREEN_W, SCREEN_H = 1200, 650
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption('NullSense Phase 7 — Dual Camera')
font_l = pygame.font.SysFont('Arial', 26, bold=True)
font_m = pygame.font.SysFont('Arial', 18)
font_s = pygame.font.SysFont('Arial', 14)

CAM_W = 400
CAM_H = SCREEN_H // 2


def combine_signals(f_sig, f_int, b_sig, b_int):
    """Front camera priority; back camera triggers rear alerts."""
    fp = SIGNAL_PRIORITY.get(f_sig, 1)
    bp = SIGNAL_PRIORITY.get(b_sig, 1)
    if fp >= bp:
        return f_sig, f_int, 'FRONT'
    back_map = {
        'STOP': 'CAUTION CENTER', 'CAUTION CENTER': 'SLIGHT LEFT',
        'MOVE RIGHT': 'SLIGHT RIGHT', 'MOVE LEFT': 'SLIGHT LEFT',
        'SLIGHT RIGHT': 'CLEAR', 'SLIGHT LEFT': 'CLEAR', 'CLEAR': 'CLEAR',
    }
    return back_map.get(b_sig, 'CLEAR'), b_int, 'BACK'


def draw_cam(frame, dets, signal, zone, label, distance, ox, oy, title, tc):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = cv2.resize(rgb, (CAM_W, CAM_H-80))
    for r in [0.2,0.4,0.6,0.8]:
        cv2.line(res, (int(CAM_W*r),0),(int(CAM_W*r),CAM_H-80),(60,60,60),1)
    sx, sy = CAM_W/frame.shape[1], (CAM_H-80)/frame.shape[0]
    for (x1,y1,x2,y2,lbl,conf,dist) in dets:
        c = (255,0,0) if lbl in HIGH_PRIORITY else (0,255,0)
        cv2.rectangle(res, (int(x1*sx),int(y1*sy)),(int(x2*sx),int(y2*sy)), c, 2)
        cv2.putText(res, f'{lbl} {conf:.0%}',
            (int(x1*sx),max(int(y1*sy)-6,10)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, c, 1)
    surf = pygame.surfarray.make_surface(res.swapaxes(0,1))
    screen.blit(surf, (ox, oy+30))
    sc = get_sig_color(signal)
    pygame.draw.rect(screen, DARK_GRAY, (ox,oy,CAM_W,30))
    screen.blit(font_m.render(f'{title} — {signal}', True, tc), (ox+8,oy+6))
    by = oy+CAM_H-48
    pygame.draw.rect(screen, DARK_GRAY, (ox,by,CAM_W,48))
    pygame.draw.line(screen, GRAY, (ox,by),(ox+CAM_W,by), 1)
    screen.blit(font_s.render(f'Signal: {signal}', True, sc), (ox+8,by+6))
    screen.blit(font_s.render(f'Object: {label} | Zone: {zone} | {distance}',
        True, (180,180,180)), (ox+8,by+26))


def draw_center(f_sig,f_lbl,f_dist,b_sig,b_lbl,b_dist,cs,ci,src):
    px, pw = 400, 400
    cx = px+pw//2
    pygame.draw.rect(screen, (20,20,20), (px,0,pw,SCREEN_H))
    pygame.draw.line(screen, GRAY, (px,0),(px,SCREEN_H), 1)
    pygame.draw.line(screen, GRAY, (px+pw,0),(px+pw,SCREEN_H), 1)
    sc = get_sig_color(cs)
    t = font_l.render('NULLSENSE', True, TEAL)
    screen.blit(t, (cx-t.get_width()//2, 18))
    screen.blit(font_s.render('Dual Camera System', True, GRAY),
        (cx-70, 50))
    pygame.draw.line(screen, GRAY, (px+20,70),(px+pw-20,70), 1)
    pygame.draw.rect(screen, DARK_GRAY, (px+20,82,pw-40,68), border_radius=8)
    l = font_s.render('COMBINED SIGNAL', True, GRAY)
    screen.blit(l, (cx-l.get_width()//2, 90))
    st = font_l.render(cs, True, sc)
    screen.blit(st, (cx-st.get_width()//2, 114))
    screen.blit(font_s.render('Intensity:', True, GRAY), (px+28,164))
    for i in range(3):
        c = sc if i < ci else (60,60,60)
        pygame.draw.rect(screen, c, (px+108+i*36,162,28,14), border_radius=4)
    pygame.draw.line(screen, GRAY, (px+20,195),(px+pw-20,195), 1)
    screen.blit(font_m.render('FRONT', True, GREEN), (px+28,208))
    fc = get_sig_color(f_sig)
    for i,txt in enumerate([f'Signal:   {f_sig}', f'Object:   {f_lbl}', f'Distance: {f_dist}']):
        screen.blit(font_s.render(txt, True, fc if i==0 else (180,180,180)), (px+28,232+i*20))
    pygame.draw.line(screen, GRAY, (px+20,300),(px+pw-20,300), 1)
    screen.blit(font_m.render('BACK', True, PURPLE), (px+28,312))
    bc = get_sig_color(b_sig)
    for i,txt in enumerate([f'Signal:   {b_sig}', f'Object:   {b_lbl}', f'Distance: {b_dist}']):
        screen.blit(font_s.render(txt, True, bc if i==0 else (180,180,180)), (px+28,336+i*20))
    pygame.draw.line(screen, GRAY, (px+20,400),(px+pw-20,400), 1)
    src_c = GREEN if src=='FRONT' else PURPLE
    screen.blit(font_s.render('Active source:', True, GRAY), (px+28,412))
    screen.blit(font_m.render(f'{src} CAMERA', True, src_c), (px+28,432))
    pygame.draw.line(screen, GRAY, (px+20,462),(px+pw-20,462), 1)
    screen.blit(font_s.render('Band output:', True, GRAY), (px+28,472))
    bm = {
        'STOP':'BOTH — FULL', 'CAUTION CENTER':'BOTH — MID',
        'MOVE LEFT':'LEFT — FRONT+MID', 'MOVE RIGHT':'RIGHT — FRONT+MID',
        'SLIGHT LEFT':'LEFT — MID', 'SLIGHT RIGHT':'RIGHT — MID',
        'CLEAR':'NO PRESSURE',
    }
    screen.blit(font_s.render(bm.get(cs,'NO PRESSURE'), True, sc), (px+28,494))
    # coverage arcs
    pygame.draw.line(screen, GRAY, (px+20,518),(px+pw-20,518), 1)
    screen.blit(font_s.render('Coverage:', True, GRAY), (px+28,526))
    dcx, dcy = cx, 572
    pygame.draw.circle(screen, GRAY, (dcx,dcy), 16, 2)
    screen.blit(font_s.render('cap', True, GRAY), (dcx-13,dcy-7))
    pygame.draw.arc(screen, GREEN, (dcx-48,dcy-62,96,48), 0, 3.14, 2)
    screen.blit(font_s.render('front', True, GREEN), (dcx-16,dcy-70))
    pygame.draw.arc(screen, PURPLE, (dcx-48,dcy+16,96,48), 3.14, 6.28, 2)
    screen.blit(font_s.render('back', True, PURPLE), (dcx-14,dcy+50))


def draw_right(src):
    pygame.draw.rect(screen, DARK_GRAY, (800,0,400,SCREEN_H))
    pygame.draw.line(screen, GRAY, (800,0),(800,SCREEN_H), 1)
    screen.blit(font_l.render('PHASE 7', True, TEAL), (820,20))
    screen.blit(font_s.render('Dual Camera System', True, GRAY), (820,52))
    pygame.draw.line(screen, GRAY, (820,72),(1180,72), 1)
    src_c = GREEN if src=='FRONT' else PURPLE
    screen.blit(font_m.render('Active:', True, GRAY), (820,85))
    screen.blit(font_m.render(f'{src} CAM', True, src_c), (820,110))
    pygame.draw.line(screen, GRAY, (820,138),(1180,138), 1)
    for i, line in enumerate([
        'Controls:', '', 'Q = Quit', '',
        'Green = Front camera', 'Purple = Back camera',
        '', 'Front cam = priority', 'Back cam = rear alert']):
        screen.blit(font_s.render(line, True, (150,150,150)), (820,150+i*24))


def run():
    coco_model = YOLO(COCO_MODEL_PATH)
    pothole_model = YOLO(POTHOLE_MODEL_PATH)
    models = (coco_model, pothole_model)
    front_cap = cv2.VideoCapture(get_camera_source('front'))
    back_cap  = cv2.VideoCapture(get_camera_source('back'))
    clock = pygame.time.Clock()
    print("Phase 7 — Dual Camera | Q to quit")

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_q: running = False

        screen.fill(BLACK)
        rf, ff = front_cap.read()
        rb, bf = back_cap.read()

        if rf: fd,fs,fz,fl,fdist,fi = process_frame(ff, models)
        else:  fd,fs,fz,fl,fdist,fi = [],'CLEAR','CENTER','none','FAR',0
        if rb: bd,bs,bz,bl,bdist,bi = process_frame(bf, models)
        else:  bd,bs,bz,bl,bdist,bi = [],'CLEAR','CENTER','none','FAR',0

        cs, ci, src = combine_signals(fs,fi,bs,bi)

        if rf: draw_cam(ff,fd,fs,fz,fl,fdist,0,0,'FRONT',GREEN)
        if rb: draw_cam(bf,bd,bs,bz,bl,bdist,0,CAM_H,'BACK',PURPLE)
        draw_center(fs,fl,fdist,bs,bl,bdist,cs,ci,src)
        draw_right(src)

        pygame.display.flip()
        clock.tick(FPS)

    front_cap.release()
    back_cap.release()
    pygame.quit()


if __name__ == '__main__':
    run()
