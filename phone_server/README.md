# NullSense — Phone Server (The Brain)

Final deployment: phone runs YOLO + serves signals to ESP32 wristbands over WiFi.

## Files
- phone_server.py      — single camera
- phone_server_dual.py — front + back cameras
- esp32_simulator.py   — test ESP32 without hardware

## Test without hardware
```
Terminal 1:  py phone_server/phone_server.py
Terminal 2:  py phone_server/esp32_simulator.py
```

## Endpoints
- GET /signal?band=LEFT  → "SIGNAL,front,mid,back"
- GET /status            → JSON status
- GET /                  → web dashboard
