# NullSense 🧢
### A Wearable Haptic Navigation System for the Blind

**Team NullVision** | BCA304A-5 — Computer Vision | Christ (Deemed to be University) | 2025-26

---

## Architecture (final, as-built)

```
Phone camera (DroidCam) ──video stream──┐
                                         ├──> LAPTOP (phone_server/phone_server.py)
Helmet ESP32 (sensor_node.ino) ─sensors─┘      - YOLO detection
                                                - camera + sensor fusion
                                                - Flask server :5000
                                                       │
                                     ┌─────────────────┴─────────────────┐
                                     ▼                                   ▼
                          LEFT wristband ESP32               RIGHT wristband ESP32
                          (wristband_wifi.ino,                (wristband_wifi.ino,
                           BAND_SIDE="LEFT")                   BAND_SIDE="RIGHT")
                          DRV2605L → 3× LRA (parallel)         DRV2605L → 3× LRA (parallel)
```

The laptop does all the AI + fusion. ESP32 wristbands just poll `/signal` and buzz.

**Hardware decision — no MOSFETs:** all 3 LRA actuators per wristband are wired
directly in parallel to the DRV2605L's single OUT+/OUT- pair (closed-loop
feedback broke with a switch between driver and motor). Consequence: **all 3
LRAs in a wristband always fire together, at one intensity** — direction is
conveyed by *which wristband* buzzes, not by an internal pattern. The server's
`/signal` response reflects this: `"SIGNAL,intensity"` (e.g. `"STOP,3"`), not a
front/mid/back triplet.

---

## ⚙️ Setup before running

### 1. Network
All devices (laptop, phone, helmet ESP32, both wristband ESP32s) must be on the
**same WiFi network** — either your laptop's Windows Mobile Hotspot
(`SSID=NullSense`, `password=nullsense123`) or your home WiFi.

### 2. DroidCam (phone camera)
1. Install **DroidCam** app on your phone + **DroidCam Client** on the laptop
2. Open the app, note the IP it shows
3. Put it in `shared/config.py`:
   ```python
   DROIDCAM_IP = '192.168.1.14'   # <-- your phone's IP
   ```

### 3. Helmet sensor node
1. Flash `esp32/sensor_node.ino` (set `SSID`/`PASS` if different)
2. That's it — it's reachable at `nullsense-helmet.local` via mDNS, so
   `shared/config.py`'s `SENSOR_NODE_ADDR` doesn't need updating even as its
   DHCP-assigned IP changes each boot. If mDNS isn't resolving on your
   network, open Serial Monitor for the IP it prints and set
   `SENSOR_NODE_ADDR` to that instead.

### 4. Wristbands (flash the SAME sketch twice)
1. Open `esp32/wristband_wifi.ino`
2. Set `SSID`/`PASS`, and `SERVER_IP` to your laptop's hotspot IP (`192.168.137.1`
   if using the laptop's own hotspot — **not** necessarily whatever IP
   `phone_server.py` prints on startup; that autodetect can pick the wrong
   network adapter if your laptop has more than one active)
3. Set `BAND_SIDE = "LEFT"` → upload to the left board
4. Change `BAND_SIDE = "RIGHT"` → upload to the right board
5. Power on both — each should give a double-tap buzz once WiFi connects

### 5. Install Python deps
```bash
pip install -r requirements.txt
```

---

## 🚀 Running

```bash
# From repo root, with everything above powered on and configured:
py phone_server/phone_server.py
```

Startup prints a dashboard URL (`http://<ip>:5000/`) — open it in a browser to
watch live signals/sensor readings without needing the physical wristbands yet.

**Test without wristband hardware:**
```bash
# Terminal 1
py phone_server/phone_server.py
# Terminal 2
py phone_server/esp32_simulator.py
```
Pygame window shows what each wristband would feel — same `/signal` polling a
real ESP32 does.

**Standalone demos (no server/wristbands needed):**
```bash
py phase5_simulator/band_simulator.py   # camera + live sensor bands, single window
py phase8_fusion/fusion.py              # camera + sensor fusion, cv2 window + CSV log
```

---

## 📁 Folder Structure

```
NullSense/
│
├── shared/
│   ├── config.py         ← EDIT FIRST: DroidCam IP, sensor node IP, thresholds
│   ├── navigation.py     ← YOLO + zone/signal logic (phases 2-5, 7)
│   └── sensors.py        ← SensorClient: background SSE reader for /stream
│
├── phase1_setup/          ← Environment check
├── phase2_detection/       ← YOLO detection
├── phase3_depth/           ← Distance estimation
├── phase4_navigation/      ← Navigation signals
├── phase5_simulator/       ← Camera + live sensor band simulator ⭐
├── phase6_training/        ← Pothole dataset + training scripts
├── phase7_dual_camera/     ← Front + back camera demo
├── phase8_fusion/          ← Camera + sensor fusion demo, CSV logging
│
├── phone_server/
│   ├── phone_server.py       ← ⭐ FINAL: single camera + sensor fusion + wristbands
│   ├── esp32_simulator.py    ← test client, no ESP32 hardware needed
│   └── phone_server_dual.py  ← older dual-camera variant — NOT wired to the new
│                                 protocol/wristband firmware, needs an upgrade
│                                 pass before use (still expects the old 4-value
│                                 "SIGNAL,front,mid,back" reply, and loads the
│                                 pothole model unconditionally)
│
├── esp32/
│   ├── sensor_node.ino       ← helmet: 2× HC-SR04 + 2× VL53L0X
│   └── wristband_wifi.ino    ← flash TWICE (BAND_SIDE = "LEFT" | "RIGHT")
│
├── models/                  ← trained models go here
├── docs/                    ← synopsis + reports
└── requirements.txt
```

---

## 🔀 Switching Camera / Sensor Source

In `shared/config.py`:

```python
CAM_SOURCE = 'droidcam'   # phone via DroidCam
# CAM_SOURCE = 'webcam'   # laptop built-in webcam (for testing without a phone)

SENSOR_NODE_ADDR = 'nullsense-helmet.local'   # mDNS hostname; swap for an IP if needed
```

Two distance thresholds exist deliberately, for different tools:
- `OBSTACLE_ALERT_CM = 15` — tight, used by `band_simulator.py`'s own alert flag
- `SIDE_OBSTACLE_CM = 60` — wider early-warning range, used by `phone_server.py`

---

## ✅ Phase Status

| Phase | Description | Status |
|---|---|---|
| 1 | Environment setup | ✅ Done |
| 2 | YOLO detection | ✅ Done |
| 3 | Depth estimation | ✅ Done |
| 4 | Navigation logic | ✅ Done |
| 5 | Band simulator (camera + live sensors) | ✅ Done |
| 6 | Pothole dataset + model training | 🔄 In progress (no trained weight yet) |
| 7 | Dual camera | 🔄 In progress |
| 8 | Camera + sensor fusion demo | ✅ Done |
| — | Phone server + wristbands (final deployment) | ✅ Done |

---

## 🛠️ Tech Stack
Python 3.11 · YOLOv11 Nano · OpenCV · Pygame · Flask · ESP32-C3 · DRV2605L · LRA · VL53L0X · HC-SR04

---

## 👥 Team

Alan James (hardware/model) · Dennis Mathew Abee (requirements) · R Mithra Bharathi (architecture/use cases) · K Prasanna (database/cloud) · G Vignesh (intro/synopsis) — Guide: Dr. Limna Das P
