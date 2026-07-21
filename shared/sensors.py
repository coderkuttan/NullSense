"""
NullSense — Shared Sensor Client
===================================
Background reader for the ESP32 sensor node's live SSE feed.
Stream format (one event per line, per the SSE spec):
    data: {"left_cm":3.9,"right_cm":16.0,"gnd_l_mm":188,"gnd_r_mm":79}

Import from here instead of polling the sensor node directly — a plain
blocking GET never returns on a persistent stream.

Team: NullVision | BCA304A-5 Computer Vision
Christ (Deemed to be University) | 2025-26
"""

import json
import threading

import requests

import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.config import SENSOR_URL

RECONNECT_DELAY = 1.0   # seconds to wait before retrying a dropped/failed stream
READ_TIMEOUT = 2.0      # ESP32 sends an event every ~100ms; no gap should ever approach this

DEFAULT_READING = {'left_cm': -1, 'right_cm': -1, 'gnd_l_mm': 0, 'gnd_r_mm': 0, 'online': False}


class SensorClient:
    """Runs the SSE reader on a background thread; latest() is thread-safe."""

    def __init__(self, url=SENSOR_URL):
        self.url = url
        self._lock = threading.Lock()
        self._latest = dict(DEFAULT_READING)
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()

    def latest(self):
        with self._lock:
            return dict(self._latest)

    def _run(self):
        while not self._stop.is_set():
            try:
                resp = requests.get(self.url, stream=True, timeout=(3, READ_TIMEOUT))
                # chunk_size=1: the ESP32 sends short, unframed (no Content-Length /
                # chunked encoding) writes. The default 512-byte chunk_size makes the
                # underlying reader block trying to fill a full chunk, so an already
                # -received event sits unyielded until enough bytes arrive — on a
                # stall it's discarded entirely when the read times out.
                for line in resp.iter_lines(decode_unicode=True, chunk_size=1):
                    if self._stop.is_set():
                        break
                    if not line or not line.startswith('data:'):
                        continue
                    try:
                        data = json.loads(line[len('data:'):].strip())
                    except ValueError:
                        continue
                    data['online'] = True
                    with self._lock:
                        self._latest.update(data)
            except Exception:
                pass

            with self._lock:
                self._latest['online'] = False
            self._stop.wait(RECONNECT_DELAY)
