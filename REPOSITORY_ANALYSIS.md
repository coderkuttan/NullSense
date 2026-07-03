# NullSense Repository Analysis
## Comprehensive Documentation of the Wearable Haptic Navigation System

> **Team NullVision** | BCA304A-5 Computer Vision | Christ (Deemed to be University) | 2025-26  
> **Last Updated**: 2026-07-03  
> **Repository**: `NullSense` (GitHub)

---

## 📋 Executive Summary

NullSense is a **wearable haptic navigation system for the blind** using a **phone + ESP32 architecture** (no Raspberry Pi). The phone runs YOLOv8 object detection and serves navigation signals over WiFi to ESP32-C3 wristbands equipped with LRA (Linear Resonant Actuator) haptic motors via DRV2605L drivers.

### Architecture Overview
```
Cap: 2x ESP32-CAM ──WiFi stream──┐
                                  ↓
                    Phone (YOLOv8 + Flask server)
                                  ↓ WiFi HTTP
                    ESP32-C3 wristbands → LRA pressure
```

### Tech Stack
| Layer | Technology |
|-------|------------|
| **AI/ML** | YOLOv8 Nano (ultralytics), PyTorch |
| **Computer Vision** | OpenCV |
| **GUI/Simulation** | Pygame |
| **Backend** | Flask (REST API) |
| **Hardware** | ESP32-C3 (XIAO), DRV2605L, LRA motors |
| **Communication** | WiFi (HTTP polling ~12 Hz) |
| **Language** | Python 3.11, C++ (Arduino) |

---

## ✅ What's Done (Completed Phases)

### Phase 1: Environment Setup & Test (`phase1_setup/`)
**Status**: ✅ **COMPLETED**  
**File**: `phase1_setup/setup_test.py`  
**Purpose**: Verify all dependencies installed and camera source works.

**Features**:
- Checks 6 required packages: ultralytics, opencv-python, pygame, numpy, flask, requests
- Tests YOLOv8 model loads and runs inference on dummy frame
- Tests camera connection (DroidCam or webcam) with helpful error messages
- Auto-reads camera config from `shared/config.py`

### Phase 2: Object Detection (`phase2_detection/`)
**Status**: ✅ **COMPLETED**  
**File**: `phase2_detection/detection.py`  
**Purpose**: Real-time YOLOv8 detection with object filtering.

**Features**:
- Runs YOLOv8 on camera stream (DroidCam/webcam)
- Filters detections to `RELEVANT_OBJECTS` (70+ classes from config)
- Color-codes bounding boxes: **Red** = HIGH_PRIORITY objects, **Green** = others
- Shows confidence percentages
- Press `Q` to quit

### Phase 3: Depth Estimation (`phase3_depth/`)
**Status**: ✅ **COMPLETED**  
**File**: `phase3_depth/depth.py`  
**Purpose**: Distance estimation from bounding box size.

**Features**:
- Uses `shared.navigation.get_distance()` to estimate distance from box area ratio
- 4 distance levels: **VERY CLOSE** (>25% frame), **CLOSE** (>10%), **MEDIUM** (>3%), **FAR** (≤3%)
- Color-coded distance labels on bounding boxes
- Visual legend showing distance color mapping
- Center point marker on each detection

### Phase 4: Navigation Logic (`phase4_navigation/`)
**Status**: ✅ **COMPLETED**  
**File**: `phase4_navigation/navigation_test.py`  
**Purpose**: Full detection → depth → navigation signal pipeline.

**Features**:
- Uses `shared.navigation.process_frame()` for complete pipeline
- 5-zone horizontal division: FAR LEFT, LEFT, CENTER, RIGHT, FAR RIGHT
- 7 navigation signals with priority: STOP (5), CAUTION CENTER (4), MOVE RIGHT/LEFT (3), SLIGHT RIGHT/LEFT (2), CLEAR (1)
-1)
- Dashboard overlay showing signal, object, zone, distance, intensity bars
- Console logging of current signal
- High-priority object boosting (+1 priority)

### Phase 5: Band Simulator GUI (`phase5_simulator/`)
**Status**: ✅ **COMPLETED**  
**File**: `phase5_simulator/band_simulator.py`  
**Purpose**: Full pygame GUI with camera feed + dual wristband visualization.

**Features**:
- **Left panel (600×520)**: Camera feed with zone lines, detections, signal overlay
- **Right panel (400×600)**: Dual wristband simulation (LEFT/RIGHT)
- Each band shows 3 actuators: FRONT, MID, BACK with intensity 0-3
- Visual pressure circles (size/color = intensity)
- Directional arrow for signal type
- Real-time signal info panel
- 30 FPS with pygame clock

### Phase 6: Indian Dataset & Custom Model Training (`phase6_training/`)
**Status**: 🔄 **IN PROGRESS**  
**File**: `phase6_training/train_indian_model.py`  
**Purpose**: Train custom YOLOv8 model on Indian road datasets.

**Features**:
- **Dataset list**: Auto-rickshaw, pothole, cow, stray dog, manhole, construction barrier, speed breaker (7 datasets)
- **Merge function**: Combines multiple YOLOv8 datasets with class remapping
- **Training config**: 50 epochs, 640 imgsz, batch 16, patience 10, GPU
- **Validation**: Tests model on dummy image, prints classes
- **Google Drive save**: Copies best.pt to Drive for download
- **Target**: `models/nullsense_best.pt` → update `MODEL_PATH` in config

### Phase 7: Dual Camera Logic (`phase7_dual_camera/`)
**Status**: 🔄 **IN PROGRESS**  
**File**: `phase7_dual_camera/dual_camera.py`  
**Purpose**: Front + back camera coverage with combined signal.

**Features**:
- **Front camera**: DroidCam (phone) — forward detection
- **Back camera**: Laptop webcam — rear detection
- **Signal combination logic**: Front camera priority; back camera maps to rear alerts
- **GUI layout**: 
  - Top-left: Front camera feed (400×285)
  - Bottom-left: Back camera feed (400×285)
  - Center (400×650): Combined signal dashboard with source indicator
  - Right (400×650): Controls/legend panel
- **Coverage visualization**: Semi-circle arcs for front/back coverage
- Band output mapping table

### Phone Server — Deployment Brain (`phone_server/`)
**Status**: ✅ **READY (test mode)**  
**Files**: 
- `phone_server.py` — Single camera server
- `phone_server_dual.py` — Dual camera server
- `esp32_simulator.py` — Test client without hardware

**Architecture**:
```
Phone camera → YOLOv8 → process_frame() → navigation signal
                                                         ↓
                    Flask server (port 5000) ←─────────────
                                                         ↓
                    ESP32 wristbands poll /signal?band=LEFT/RIGHT
```

**Endpoints**:
| Endpoint | Description | Response Format |
|----------|-------------|-----------------|
| `GET /signal?band=LEFT/RIGHT` | ESP32 polls this | `SIGNAL,front,mid,back` (e.g., `STOP,3,3,3`) |
| `GET /status` | JSON status for debugging | Full state object |
| `GET /` | Web dashboard | Auto-refresh HTML |

**Threading**: Detection runs in daemon thread; Flask serves requests in main thread.

### ESP32 Wristband Firmware (`esp32/`)
**Status**: ✅ **READY (test mode)**  
**File**: `esp32/wristband_wifi.ino`  
**Purpose**: ESP32-C3 connects to phone hotspot, polls server, fires LRA.

**Hardware Wiring (Seeed XIAO ESP32-C3)**:
| ESP32 Pin | DRV2605L |
|-----------|----------|
| 3.3V | VCC |
| GND | GND |
| D4 (SDA) | SDA |
| D5 (SCL) | SCL |

**Features**:
- WiFi connection with retry logic (30 attempts)
- HTTP polling every 80ms (~12 Hz)
- Response parsing: `SIGNAL,front,mid,back`
- **Duplicate signal suppression** (skips if same as last)
- Intensity → DRV2605 effect mapping: 1=soft, 2=medium, 3=strong
- **STOP signal**: Double pulse pattern
- Auto-reconnect on WiFi loss
- Success pulse on connection

### Shared Core Logic (`shared/`)
**Status**: ✅ **COMPLETED**  
**Files**:
- `config.py` — Central configuration (ALL phases read from here)
- `navigation.py` — Core detection/navigation functions

**Config Sections**:
1. **Camera Source**: CAM_SOURCE, DROIDCAM_IP, FRONT_SOURCE, BACK_SOURCE, WEBCAM_INDEX
2. **Model**: MODEL_PATH, CONFIDENCE
3. **Phone Server**: SERVER_HOST, SERVER_PORT, HOTSPOT_SSID, HOTSPOT_PASS
4. **Detection Objects**: RELEVANT_OBJECTS (70+), HIGH_PRIORITY (8)
5. **Signal Priority/Index**: SIGNAL_PRIORITY (7 levels), SIGNAL_INDEX (0-6)
6. **Colors**: Pygame RGB constants + SIGNAL_COLORS mapping
7. **Display**: SCREEN_W, SCREEN_H, FPS

**Navigation Functions**:
| Function | Purpose |
|----------|---------|
| `get_distance(box_area, frame_area)` | Returns (label, intensity 0-3) |
| `get_zone(cx, frame_width)` | Returns zone string (5 zones) |
| `get_signal(zone, distance)` | Returns navigation signal |
| `get_sig_color(signal)` | Returns Pygame RGB color |
| `signal_to_bands(signal, intensity)` | Returns (left_band, right_band) each = [front,mid,back] 0-3 |
| `process_frame(frame, model)` | **Main pipeline** — returns detections + top signal |

---

## ⚠️ Flaws & Issues

### Critical Flaws

| # | Issue | Location | Severity | Impact |
|---|-------|----------|----------|--------|
| 1 | **No stereo depth** | `phase3_depth/depth.py` | **HIGH** | Distance estimation from 2D box size is unreliable; no true depth |
| 2 | **Single model for all classes** | `shared/config.py:52` | **HIGH** | YOLOv8n trained on COCO; poor on Indian objects (auto-rickshaw, pothole, cow) |
| 3 | **No temporal smoothing** | `shared/navigation.py` | **HIGH** | Signal flickers frame-to-frame; no hysteresis/debouncing |
| 4 | **HTTP polling latency** | `esp32/wristband_wifi.ino:53` | **MEDIUM** | 80ms poll + network latency = ~100-200ms delay; not real-time |
| 5 | **No calibration** | `shared/navigation.py:19-25` | **MEDIUM** | Distance thresholds hardcoded; vary by camera FOV/resolution |
| 6 | **Thread safety** | `phone_server/phone_server.py:40-47` | **MEDIUM** | Shared `state` dict accessed by detection thread + Flask threads without locks |
| 7 | **No fallback on detection failure** | `phone_server/phone_server.py:123-136` | **MEDIUM** | If camera drops, state freezes at last value |

### Architecture Flaws

| # | Issue | Description |
|---|-------|-------------|
| 8 | **Phone as single point of failure** | If phone dies, entire system stops; no edge processing on ESP32 |
| 9 | **WiFi dependency** | Requires phone hotspot; range limited; interference in crowded areas |
| 10 | **No battery management** | ESP32 code has no sleep/low-power mode; LRA driving not optimized |
| 11 | **Single-band-type firmware** | `BAND_SIDE` compile-time constant; need separate builds for left/right |
| 12 | **No OTA updates** | Firmware updates require physical USB connection |

### Code Quality Issues

| # | Issue | Location |
|---|-------|----------|
| 13 | **Magic numbers** | `shared/navigation.py:21-25` (0.25, 0.10, 0.03), `phase7_dual_camera.py:39-50` |
| 14 | **Duplicate signal combination logic** | `phase7_dual_camera.py:39-50` AND `phone_server/phone_server_dual.py:46-63` |
| 15 | **No type hints** | All Python files — makes maintenance harder |
| 16 | **No unit tests** | Zero test coverage for core logic (`shared/navigation.py`) |
| 17 | **Hardcoded IPs in firmware** | `esp32/wristband_wifi.ino:45` — must recompile for each deployment |
| 18 | **No logging framework** | Uses `print()` everywhere; no levels, no file output |
| 19 | **Global state mutation** | `shared/navigation.py` modifies no state but config imports create coupling |
| 20 | **Inconsistent error handling** | Some functions return tuples, others raise; no unified pattern |

### Documentation Gaps

| # | Missing |
|---|---------|
| 21 | **No API specification** | `/signal` endpoint format not formally documented |
| 22 | **No hardware assembly guide** | Wiring diagram only in firmware comments |
| 23 | **No deployment guide** | Phone hotspot setup, Termux install, auto-start not covered |
| 24 | **No troubleshooting guide** | Common issues (DroidCam IP change, WiFi drops, model not found) |

---

## 🚀 Improvements (Priority Order)

### P0 — Must Fix Before Deployment

| # | Improvement | Effort | Files to Change |
|---|-------------|--------|-----------------|
| 1 | **Add temporal smoothing/hysteresis** | Medium | `shared/navigation.py` — add signal history, require N consistent frames |
| 2 | **Thread-safe state with locks** | Low | `phone_server/phone_server.py` — use `threading.Lock` for `state` dict |
| 3 | **Camera reconnection logic** | Medium | `phone_server/phone_server.py:118-119` — retry on `cap.read()` failure |
| 4 | **Calibration routine** | Medium | New `phase_calibration/` — auto-tune distance thresholds per camera |
| 5 | **Firmware: runtime band selection** | Low | `esp32/wristband_wifi.ino` — read from GPIO pin or NVS instead of compile-time |
| 6 | **Firmware: configurable server IP** | Low | `esp32/wristband_wifi.ino` — store in NVS/preferences, not hardcoded |

### P1 — High Value

| # | Improvement | Effort | Files to Change |
|---|-------------|--------|-----------------|
| 7 | **WebSocket instead of HTTP polling** | Medium | `phone_server/*.py` + `esp32/wristband_wifi.ino` — use `WebSocketClient` |
| 8 | **Add stereo depth (dual camera disparity)** | High | `phase7_dual_camera/` + new depth module — requires calibrated stereo pair |
| 9 | **Custom model integration** | Medium | `phase6_training/` → `shared/config.py:52` — seamless model swap |
| 10 | **Battery-aware ESP32 firmware** | Medium | `esp32/wristband_wifi.ino` — deep sleep between polls, battery monitor |
| 11 | **Unified signal combination module** | Low | Extract to `shared/signal_fusion.py` — used by phase7 + phone_server_dual |
| 12 | **Add type hints + mypy** | Low | All `.py` files — incremental adoption |

### P2 — Quality of Life

| # | Improvement | Effort | Files to Change |
|---|-------------|--------|-----------------|
| 13 | **Structured logging** | Low | Replace `print()` with `logging` module; levels + file rotation |
| 14 | **Unit tests for navigation logic** | Medium | New `tests/test_navigation.py` — pytest + fixtures |
| 15 | **Configuration validation** | Low | `shared/config.py` — validate ranges, types on import |
| 16 | **CLI argument parsing** | Low | Each phase — `argparse` for camera source, model path, etc. |
| 17 | **Hot-reload config** | Medium | `shared/config.py` — watch file, reload without restart |
| 18 | **Docker support** | Medium | `Dockerfile` + `docker-compose.yml` for phone_server |

---

## 🔮 Possible Changes & Enhancements

### Near-Term (1-2 months)

| Idea | Description | Feasibility |
|------|-------------|-------------|
| **Audio feedback** | Add TTS announcements ("Obstacle left, 2 meters") via phone speaker | Easy — `pyttsx3` or Android TTS |
| **Vibration patterns for object types** | Distinct patterns for person vs vehicle vs pothole | Medium — extend `signal_to_bands()` |
| **Obstacle tracking (SORT/DeepSORT)** | Track objects across frames; predict trajectory | Medium — `ultralytics` has built-in tracking |
| **Offline map integration** | Cache OpenStreetMap for GPS-assisted navigation | Hard — requires GPS + map matching |
| **Multi-user server** | One phone serves multiple wristband pairs | Medium — extend `/signal` with user ID |

### Medium-Term (3-6 months)

| Idea | Description | Feasibility |
|------|-------------|-------------|
| **Edge inference on ESP32-S3** | Run TinyML (YOLOv8n-seg quantized) on ESP32-S3 camera | Hard — needs ESP32-S3, model quantization, ESP-DL |
| **IMU fusion** | Add ESP32 IMU (MPU6050) for step detection, orientation | Medium — I2C sensor, sensor fusion |
| **Haptic language** | Encode direction + distance + urgency in vibration syntax | Medium — design haptic alphabet |
| **Cloud fallback** | Phone streams to cloud GPU when available; local when offline | Hard — needs cloud infra, sync logic |
| **Community dataset platform** | Web app for users to upload/label Indian road images | Hard — full stack web dev |

### Long-Term (6+ months / Research)

| Idea | Description | Feasibility |
|------|-------------|-------------|
| **Monocular depth estimation** | Replace box-size heuristic with MiDaS/Depth-Anything | Medium — runs on phone CPU/GPU |
| **Semantic segmentation** | YOLOv8-seg for pixel-level obstacle boundaries | Medium — `ultralytics` supports seg |
| **SLAM + obstacle map** | Build local map; persistent obstacle memory | Hard — ORB-SLAM3 + custom fusion |
| **Cross-device mesh** | Multiple users share obstacle data via Bluetooth mesh | Hard — BLE mesh, privacy |
| **AI-powered scene description** | LLaVA/GPT-4V describes scene; audio output | Hard — needs cloud or heavy edge |

### Hardware Variants

| Variant | Components | Use Case |
|---------|------------|----------|
| **Minimal** | 1× ESP32-C3 + 1× LRA + phone | Single wristband, basic nav |
| **Standard** | 2× ESP32-C3 + 2× LRA (left/right) + phone | Current design |
| **Pro** | 2× ESP32-S3-CAM + 4× LRA (2 per band) + phone | Stereo depth + richer haptics |
| **Standalone** | ESP32-S3 + camera + LRA + battery (no phone) | Fully wearable, no phone needed |

---

## 📁 Repository Structure (Annotated)

```
NullSense/
│
├── shared/                          ← CORE — EDIT config.py FIRST
│   ├── config.py                    ← Central config (ALL phases import this)
│   └── navigation.py                ← Core logic (process_frame, get_signal, etc.)
│
├── phase1_setup/                    ✅ DONE
│   ├── README.md
│   └── setup_test.py                ← Run first: verifies deps + camera
│
├── phase2_detection/                ✅ DONE
│   ├── README.md
│   └── detection.py                 ← Basic YOLO detection + filtering
│
├── phase3_depth/                    ✅ DONE
│   ├── README.md
│   └── depth.py                     ← Distance from box size
│
├── phase4_navigation/               ✅ DONE
│   ├── README.md
│   └── navigation_test.py           ← Full pipeline + dashboard
│
├── phase5_simulator/                ✅ DONE
│   ├── README.md
│   └── band_simulator.py            ← Pygame GUI: camera + dual bands
│
├── phase6_training/                 🔄 IN PROGRESS
│   ├── README.md
│   └── train_indian_model.py        ← Colab training pipeline (7 Indian datasets)
│
├── phase7_dual_camera/              🔄 IN PROGRESS
│   ├── README.md
│   └── dual_camera.py               ← Front+back cameras + combined signal
│
├── phone_server/                    ✅ READY (test mode)
│   ├── README.md
│   ├── phone_server.py              ← Single camera Flask server
│   ├── phone_server_dual.py         ← Dual camera Flask server
│   └── esp32_simulator.py           ← Pygame ESP32 simulator (test client)
│
├── esp32/                           ✅ READY (test mode)
│   ├── README.md
│   └── wristband_wifi.ino           ← ESP32-C3 firmware (Arduino)
│
├── models/                          ← Trained models go here
│   └── .gitkeep
│
├── docs/                            ← Project docs
│   ├── NullSense_CloudSolutions_Report.docx
│   └── NullSense_Synopsis.docx
│
├── yolov8n.pt                       ← Base model (COCO pretrained)
├── requirements.txt                 ← Python deps
├── README.md                        ← Main documentation
├── .gitignore
└── .venv/                         ← Virtual env (ignored)
```

---

## 🏃 Quick Reference Commands

```bash
# Setup
pip install -r requirements.txt
# Edit shared/config.py → set DROIDCAM_IP

# Phase tests (run in order)
py phase1_setup/setup_test.py
py phase2_detection/detection.py
py phase3_depth/depth.py
py phase4_navigation/navigation_test.py
py phase5_simulator/band_simulator.py
py phase7_dual_camera/dual_camera.py

# Phone server + ESP32 simulator (2 terminals)
# Terminal 1:
py phone_server/phone_server.py
# Terminal 2:
py phone_server/esp32_simulator.py

# Dual camera server
py phone_server/phone_server_dual.py

# Training (on Google Colab)
# Upload phase6_training/train_indian_model.py + datasets → run steps
```

---

## 📊 Phase Status Summary

| Phase | Component | Status | Owner | Key File |
|-------|-----------|--------|-------|----------|
| 1 | Environment Setup | ✅ Done | Any | `phase1_setup/setup_test.py` |
| 2 | Object Detection | ✅ Done | Any | `phase2_detection/detection.py` |
| 3 | Depth Estimation | ✅ Done | Any | `phase3_depth/depth.py` |
| 4 | Navigation Logic | ✅ Done | Lead | `phase4_navigation/navigation_test.py` |
| 5 | Band Simulator | ✅ Done | Lead | `phase5_simulator/band_simulator.py` |
| 6 | Indian Dataset + Training | 🔄 In Progress | Friend 1 | `phase6_training/train_indian_model.py` |
| 7 | Dual Camera | 🔄 In Progress | Friend 2 | `phase7_dual_camera/dual_camera.py` |
| — | Phone Server + ESP32 | ✅ Ready | Friend 3 | `phone_server/` + `esp32/` |

---

## 🎯 Recommended Next Steps

1. **Immediate (this week)**:
   - Add temporal smoothing to `shared/navigation.py`
   - Fix thread safety in `phone_server/phone_server.py`
   - Extract signal fusion to `shared/signal_fusion.py`

2. **Short-term (2-4 weeks)**:
   - Complete Phase 6: Train custom model on Indian datasets
   - Complete Phase 7: Polish dual camera logic + test on hardware
   - Add calibration routine for distance thresholds

3. **Medium-term (1-2 months)**:
   - WebSocket replacement for HTTP polling
   - Battery-aware ESP32 firmware with deep sleep
   - Unit tests + CI pipeline
   - Deployment guide for phone (Termux) + hardware assembly

4. **Long-term**:
   - Monocular depth estimation integration
   - Edge inference on ESP32-S3
   - Community dataset platform

---

## 📝 Notes for Contributors

- **Always edit `shared/config.py` first** — all phases read from it
- **Don't modify `shared/navigation.py` lightly** — it's the core pipeline used by all phases
- **Test with `esp32_simulator.py` before hardware** — saves debug time
- **Run Phase 1 before any other phase** — verifies environment
- **Keep firmware configs in sync** — `SERVER_IP`, `WIFI_SSID`, `BAND_SIDE` must match deployment

---

*Generated from repository analysis on 2026-07-03. Update this document as the project evolves.*