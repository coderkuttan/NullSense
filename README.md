# NullSense 🧢
### A Wearable Haptic Navigation System for the Blind

**Team NullVision** | BCA304A-5 — Computer Vision | Christ (Deemed to be University) | 2025-26

---

## Architecture — Phone + ESP32 (No Raspberry Pi)

```
Cap: 2x ESP32-CAM ──WiFi stream──┐
                                  ↓
                    Phone (YOLOv8 + Flask server)
                                  ↓ WiFi HTTP
                    ESP32-C3 wristbands → LRA pressure
```

The phone does all the AI. ESP32 wristbands just poll for signals and fire LRA motors.

---

## ⚙️ CURRENT MODE: DroidCam Testing

We're testing with **DroidCam** (phone camera streamed to laptop) before hardware arrives.

### Setup DroidCam:
1. Install **DroidCam app** on your phone (Play Store)
2. Install **DroidCam Client** on laptop (dev47apps.com)
3. Connect phone + laptop to **same WiFi**
4. Open DroidCam app — note the **IP address**
5. Put that IP in `shared/config.py`:
   ```python
   DROIDCAM_IP = '192.168.1.14'   # <-- your IP here
   ```

That's the ONLY setting you need to change. All phases read from it automatically.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your DroidCam IP in shared/config.py

# 3. Verify setup
py phase1_setup/setup_test.py

# 4. Run any phase
py phase2_detection/detection.py
py phase5_simulator/band_simulator.py
py phase7_dual_camera/dual_camera.py
```

---

## 📁 Folder Structure

```
NullSense/
│
├── shared/                  ← EDIT config.py FIRST
│   ├── config.py            ← DroidCam IP + all settings
│   └── navigation.py        ← Core detection logic (don't edit lightly)
│
├── phase1_setup/            ← Environment check
├── phase2_detection/        ← YOLO detection
├── phase3_depth/            ← Distance estimation
├── phase4_navigation/       ← Navigation signals
├── phase5_simulator/        ← Band simulator GUI ⭐
├── phase6_training/         ← Indian dataset training (Friend 1)
├── phase7_dual_camera/      ← Front + back cameras (Friend 2)
│
├── phone_server/            ← Phone-as-brain server (final deployment)
│   ├── phone_server.py      ← single camera server
│   ├── phone_server_dual.py ← dual camera server
│   └── esp32_simulator.py   ← test ESP32 without hardware
│
├── esp32/
│   └── wristband_wifi.ino   ← upload to ESP32 wristbands
│
├── models/                  ← trained models go here
├── docs/                    ← synopsis + reports
├── README.md
└── requirements.txt
```

---

## 🔀 Switching Camera Source

In `shared/config.py`:

```python
CAM_SOURCE = 'droidcam'   # phone via DroidCam (testing)
# CAM_SOURCE = 'webcam'   # laptop built-in webcam

# For Phase 7 dual camera:
FRONT_SOURCE = 'droidcam'  # front = phone
BACK_SOURCE  = 'webcam'    # back = laptop webcam
```

---

## 👥 Team Assignments

| Member | Folder | Task |
|---|---|---|
| You (Lead) | shared + phase4/5 | Core logic + band simulator |
| Friend 1 | phase6_training | Indian dataset + model training |
| Friend 2 | phase7_dual_camera | Dual camera logic |
| Friend 3 | esp32 + phone_server | Firmware + wristband hardware |

---

## ✅ Phase Status

| Phase | Description | Status |
|---|---|---|
| 1 | Environment setup | ✅ Done |
| 2 | YOLO detection | ✅ Done |
| 3 | Depth estimation | ✅ Done |
| 4 | Navigation logic | ✅ Done |
| 5 | Band simulator | ✅ Done |
| 6 | Indian dataset + model | 🔄 In Progress |
| 7 | Dual camera | 🔄 In Progress |
| — | Phone server + ESP32 | ✅ Ready (test mode) |

---

## 🧪 Test ESP32 Flow Without Hardware

```bash
# Terminal 1 — the brain
py phone_server/phone_server.py

# Terminal 2 — fake ESP32 wristbands
py phone_server/esp32_simulator.py
```

The simulator polls the server exactly like real ESP32 wristbands will.

---

## 🛠️ Tech Stack
Python 3.11 · YOLOv8 Nano · OpenCV · Pygame · Flask · ESP32-C3 · DRV2605L · LRA
