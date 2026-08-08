# NullSense — ESP32 Firmware

Two sketches, three boards (XIAO ESP32-C3):

| File | Board | Role |
|---|---|---|
| `sensor_node.ino` | Helmet | Reads 2× HC-SR04 + 2× VL53L0X, serves readings over WiFi |
| `wristband_wifi.ino` | Left wristband | Polls the server, buzzes its DRV2605L |
| `wristband_wifi.ino` | Right wristband | Same sketch, flash with `BAND_SIDE = "RIGHT"` |

All three talk to `phone_server/phone_server.py` (run on the laptop/phone),
which does camera + sensor fusion and decides what each wristband should feel.

## sensor_node.ino (helmet)

Before uploading:
1. Set `SSID` + `PASS` (phone hotspot)

Wiring:
- HC-SR04 (left): `TRIG_L`→D2, `ECHO_L`→D3
- HC-SR04 (right): `TRIG_R`→D6, `ECHO_R`→D7
- VL53L0X `XSHUT` pins: left→D0, right→D1 (both sensors share the I2C bus; left is
  re-addressed to `0x30` in `setup()` so both can coexist at their default `0x29`/`0x30`)

Reachable at `http://nullsense-helmet.local/` via mDNS — no need to update
`shared/config.py` when its DHCP-assigned IP changes each boot. If mDNS
resolution isn't working on your network, use the IP printed on Serial
Monitor instead (set `SENSOR_NODE_ADDR` in `shared/config.py`).

Serves:
- `GET /sensors` — one-shot JSON, e.g. `{"left_cm":4.8,"right_cm":16.0,"gnd_l_mm":172,"gnd_r_mm":76}` — used by `phone_server.py`
- `GET /stream` — same data as a live SSE feed — used by `phase8_fusion/fusion.py`
- Both ToF sensors have a bounded read timeout (`setTimeout`), so a stuck sensor can't freeze the server.
- `/stream` blocks the whole server while a client is connected — only one client (browser tab, script, etc.) can use it at a time.
- WiFi drop mid-run auto-reconnects (with status diagnostics on Serial) instead of hanging forever.

## wristband_wifi.ino (LEFT / RIGHT)

Before uploading:
1. Set `SSID` + `PASS` (phone hotspot)
2. Set `SERVER_IP` (shown when `phone_server.py` starts)
3. Set `BAND_SIDE = "LEFT"` or `"RIGHT"`

Wiring (XIAO ESP32-C3 → DRV2605L):
`3.3V→VCC, GND→GND, D4→SDA, D5→SCL`

The 3 LRAs are wired in parallel (no MOSFETs) — all three fire together, so
direction is conveyed by *which wristband* buzzes, not by which motor within it.

Polls `GET /signal?band=LEFT|RIGHT` every ~80ms. Server responds
`"SIGNAL,intensity"` (e.g. `"STOP,3"`, `"OBSTACLE,2"`, `"CLEAR,0"`). `STOP` gets an
extra double-pulse.

## Libraries

- Adafruit DRV2605 Library
- Pololu VL53L0X Arduino library
- WiFi + WebServer + HTTPClient (built-in for ESP32)
