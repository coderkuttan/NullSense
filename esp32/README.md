# NullSense — ESP32 Wristband Firmware

Upload wristband_wifi.ino to Seeed XIAO ESP32-C3.

## Before uploading
1. Set WIFI_SSID + WIFI_PASS (phone hotspot)
2. Set SERVER_IP (shown when phone_server.py starts)
3. Set BAND_SIDE = "LEFT" or "RIGHT"

## Wiring (XIAO ESP32-C3 → DRV2605L)
3.3V→VCC, GND→GND, D4→SDA, D5→SCL

## Libraries
- Adafruit DRV2605 Library
- WiFi + HTTPClient (built-in)
