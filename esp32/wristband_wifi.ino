/*
  NullSense — Wristband (LEFT or RIGHT)
  XIAO ESP32-C3 · DRV2605L · 3× LRA wired in PARALLEL (no MOSFETs)
  All three LRAs fire together — direction is conveyed by
  WHICH wristband buzzes, not which motor within it.

  ARCHITECTURE:
    Laptop/phone runs phone_server.py (camera + helmet-sensor fusion)
    This ESP32 polls http://SERVER_IP:5000/signal?band=LEFT|RIGHT
    Server responds: "SIGNAL,intensity"   e.g. "STOP,3" or "CLEAR,0"

  Hardware wiring (Seeed XIAO ESP32-C3):
  ┌─────────────┬──────────────┐
  │ XIAO ESP32  │  DRV2605L    │
  ├─────────────┼──────────────┤
  │ 3.3V        │  VCC         │
  │ GND         │  GND         │
  │ D4 (SDA)    │  SDA         │
  │ D5 (SCL)    │  SCL         │
  └─────────────┴──────────────┘

  Libraries (Arduino IDE):
  - Adafruit DRV2605 Library
  - WiFi + HTTPClient (built-in for ESP32)

  BEFORE UPLOADING:
  1. Set SSID + PASS to your phone hotspot
  2. Set SERVER_IP to the IP shown when phone_server.py starts
  3. Set BAND_SIDE to "LEFT" or "RIGHT"

  >>> CHANGE BAND_SIDE TO "RIGHT" FOR THE SECOND BOARD <<<

  Team: NullVision | BCA304A-5 Computer Vision
  Christ (Deemed to be University) | 2025-26
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_DRV2605.h>

const char* SSID      = "NullSense";
const char* PASS      = "nullsense123";
const char* SERVER_IP = "192.168.137.1";   // laptop hotspot IP
const char* BAND_SIDE = "LEFT";            // <<< "LEFT" or "RIGHT"

Adafruit_DRV2605 drv;
String lastSignal = "";
unsigned long lastPoll = 0;
const int POLL_INTERVAL = 80;  // ms between polls (~12 Hz)

uint8_t effectFor(uint8_t intensity) {
  switch (intensity) {
    case 1: return 16;   // soft click
    case 2: return 14;   // medium click
    case 3: return 1;    // strong click
    default: return 0;
  }
}

void buzz(uint8_t intensity) {
  if (intensity == 0) return;
  drv.setWaveform(0, effectFor(intensity));
  drv.setWaveform(1, 0);
  drv.go();
  delay(80);
}

// ── Parse server response: "SIGNAL,intensity" ──
void parseAndApply(String response) {
  response.trim();

  int c = response.indexOf(',');
  if (c <= 0) return;

  String sig = response.substring(0, c);
  uint8_t intensity = response.substring(c + 1).toInt();

  if (sig == lastSignal) return;   // skip duplicate
  lastSignal = sig;

  Serial.printf("[%s] %s  intensity=%d\n", BAND_SIDE, sig.c_str(), intensity);
  buzz(intensity);

  if (sig == "STOP") {          // double-pulse for STOP
    delay(120);
    buzz(3);
  }
}

void connectWiFi() {
  WiFi.begin(SSID, PASS);
  WiFi.setSleep(false);
  Serial.print("Connecting");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" Connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
    buzz(1); delay(150); buzz(1);   // startup double-tap
  } else {
    Serial.println(" Failed!");
  }
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.printf("\nNullSense %s Band (WiFi) starting\n", BAND_SIDE);

  Wire.begin();
  if (!drv.begin()) {
    Serial.println("ERROR: DRV2605L not found! Check wiring.");
    while (1) delay(1000);
  }
  drv.useLRA();
  drv.selectLibrary(1);
  drv.setMode(DRV2605_MODE_INTTRIG);
  Serial.println("DRV2605L OK");

  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost — reconnecting...");
    connectWiFi();
    return;
  }

  if (millis() - lastPoll >= POLL_INTERVAL) {
    lastPoll = millis();

    HTTPClient http;
    String url = String("http://") + SERVER_IP + ":5000/signal?band=" + BAND_SIDE;
    http.begin(url);
    http.setTimeout(300);

    if (http.GET() == 200) {
      parseAndApply(http.getString());
    }
    http.end();
  }
}
