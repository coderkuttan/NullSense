# NullSense 🧢
### A Wearable Haptic Navigation System for the Blind

**Team NullVision** 

---

## What is NullSense?
NullSense is an IoT + Computer Vision wearable that gives blind 
individuals a new sense — detecting obstacles from all directions 
and communicating navigation instructions through pressure bands 
on the wrist.

---

## System Architecture

Front Camera (IMX219-160)  ─┐
Back Camera  (IMX219-160)  ─┤
HC-SR04 Ultrasonic x2     ─┤→ Raspberry Pi 4 → BLE → Wristbands
VL53L1X ToF Sensors x2    ─┘    (YOLOv8 AI)        (LRA pressure)

---

## Tech Stack
- Python 3.11
- YOLOv8 (Ultralytics)
- OpenCV
- Pygame
- ESP32-C3 + DRV2605L
- Raspberry Pi 4

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/NullSense.git
cd NullSense
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure camera
Edit `main/band_simulator.py`:
```python
USE_PHONE_CAM = True         # True = DroidCam, False = webcam
PHONE_IP      = '192.168.x.x'  # Your DroidCam IP
```

### 4. Run
```bash
py main/band_simulator.py
```

---

## Project Phases

| Phase | Description | Status |
|---|---|---|
| 1 | Environment setup | ✅ Done |
| 2 | YOLO object detection | ✅ Done |
| 3 | Depth estimation | ✅ Done |
| 4 | Navigation logic | ✅ Done |
| 5 | Band simulator GUI | ✅ Done |
| 6 | Indian dataset + custom model | 🔄 In Progress |
| 7 | Dual camera logic | 🔄 In Progress |
| 8 | 360° sensor fusion | ⏳ Pending |
| 9 | Hardware assembly | ⏳ Pending |
| 10 | BLE integration | ⏳ Pending |

---

## Team
| Member | Role |
|---|---|
| [Your Name] | Lead + Navigation Logic |
| [Friend 1] | Indian Dataset + Model Training |
| [Friend 2] | Dual Camera Logic |
| [Friend 3] | Hardware + Assembly |

---

## Hardware Components
- Raspberry Pi 4 (2GB)
- 2x Waveshare IMX219-160 Camera
- 2x HC-SR04 Ultrasonic Sensor
- 2x VL53L1X ToF Sensor
- 2x Seeed XIAO ESP32-C3
- 2x DRV2605L Haptic Driver
- 6x LRA 10mm Actuators
