"""
NullSense — ESP32 Simulator (Test Client)
===========================================
Simulates an ESP32 wristband WITHOUT real hardware.
Polls the phone_server.py just like a real ESP32 would,
and shows what the band would do in a pygame window.

Use this to test the full client-server flow before
buying any hardware.

HOW TO RUN:
  1. Start the server:  py phone_server/phone_server.py
  2. In another terminal: py phone_server/esp32_simulator.py

Team: NullVision | BCA304A-5 Computer Vision
Christ (Deemed to be University) | 2025-26
"""

import sys, os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources is deprecated.*")
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import requests
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import pygame
import time
from shared.config import (
    SERVER_PORT, BLACK, WHITE, GRAY, DARK_GRAY,
    RED, ORANGE, YELLOW, GREEN, TEAL
)
from shared.navigation import get_sig_color

# ── Config ──
SERVER_IP = '127.0.0.1'  # localhost for testing on same machine
POLL_MS   = 80

# ── Pygame ──
pygame.init()
W, H   = 700, 450
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption('NullSense — ESP32 Simulator (both bands)')
font_l = pygame.font.SysFont('Arial', 26, bold=True)
font_m = pygame.font.SysFont('Arial', 18)
font_s = pygame.font.SysFont('Arial', 14)


def poll_band(band):
    """Poll server for a band's signal. Returns (signal, intensity)."""
    try:
        url  = f'http://{SERVER_IP}:{SERVER_PORT}/signal?band={band}'
        resp = requests.get(url, timeout=0.2)
        signal, intensity = resp.text.strip().split(',')
        return signal, int(intensity)
    except Exception:
        return 'NO CONNECTION', 0


def draw_band(x, y, label, intensity, signal):
    """All 3 LRAs are wired in parallel on real hardware and fire together
    at one intensity — draw a single indicator, not a front/mid/back triplet."""
    bw, bh = 280, 300
    sc = get_sig_color(signal) if signal != 'NO CONNECTION' else GRAY

    pygame.draw.rect(screen, DARK_GRAY, (x, y, bw, bh), border_radius=15)
    pygame.draw.rect(screen, GRAY, (x, y, bw, bh), 2, border_radius=15)

    lbl = font_m.render(f'{label} BAND', True, WHITE)
    screen.blit(lbl, (x + bw//2 - lbl.get_width()//2, y + 12))

    sig = font_m.render(signal, True, sc)
    screen.blit(sig, (x + bw//2 - sig.get_width()//2, y + 40))

    cx, cy = x + bw // 2, y + 170
    pygame.draw.circle(screen, GRAY, (cx, cy), 55)
    if   intensity == 0: color, r = (40, 40, 40), 35
    elif intensity == 1: color, r = GREEN,  42
    elif intensity == 2: color, r = ORANGE, 48
    else:                 color, r = RED,    54
    pygame.draw.circle(screen, color, (cx, cy), r)
    if intensity > 0:
        pygame.draw.circle(screen, sc, (cx, cy), r + 5, 2)
    nt = font_s.render(f'intensity {intensity}/3 (all 3 LRAs)', True, WHITE if intensity > 0 else GRAY)
    screen.blit(nt, (cx - nt.get_width()//2, cy + 65))


def main():
    clock     = pygame.time.Clock()
    last_poll = 0
    left_sig, left_int   = 'CLEAR', 0
    right_sig, right_int = 'CLEAR', 0

    print(f"ESP32 Simulator polling http://{SERVER_IP}:{SERVER_PORT}")
    print("Make sure phone_server.py is running!")

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN and e.key == pygame.K_q:
                running = False

        # Poll server
        now = pygame.time.get_ticks()
        if now - last_poll >= POLL_MS:
            last_poll = now
            left_sig,  left_int  = poll_band('LEFT')
            right_sig, right_int = poll_band('RIGHT')

        # Draw
        screen.fill(BLACK)
        title = font_l.render('NULLSENSE — ESP32 SIMULATOR', True, TEAL)
        screen.blit(title, (W//2 - title.get_width()//2, 15))
        sub = font_s.render(
            f'Polling {SERVER_IP}:{SERVER_PORT} every {POLL_MS}ms',
            True, GRAY)
        screen.blit(sub, (W//2 - sub.get_width()//2, 48))

        draw_band(40,  90, 'LEFT',  left_int,  left_sig)
        draw_band(380, 90, 'RIGHT', right_int, right_sig)

        hint = font_s.render('Q = Quit', True, GRAY)
        screen.blit(hint, (W//2 - hint.get_width()//2, H - 30))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == '__main__':
    main()
