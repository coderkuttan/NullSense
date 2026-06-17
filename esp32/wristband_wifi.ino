/*
  NullSense — ESP32 Wristband (WiFi Client)
  ==========================================
  Connects to phone/laptop WiFi server, polls for
  navigation signals, and fires LRA actuators.

  ARCHITECTURE:
    Phone runs phone_server.py (the brain)
    This ESP32 polls http://SERVER_IP:5000/signal
    Server responds: "SIGNAL,front,mid,back"
    e.g. "STOP,3,3,3" or "MOVE LEFT,2,2,0"

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
  - WiFi (built-in for ESP32)
  - HTTPClient (built-in)

  BEFORE UPLOADING:
  1. Set WIFI_SSID + WIFI_PASS to your phone hotspot
  2. Set SERVER_IP to the IP shown when phone_server.py starts
  3. Set BAND_SIDE to "LEFT" or "RIGHT"

  Team: NullVision | BCA304A-5 Computer Vision
  Christ (Deemed to be University) | 2025-26
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_DRV2605.h>

// ── CONFIGURE THESE ──
const char* WIFI_SSID = "NullSense";        // Phone hotspot name
const char* WIFI_PASS = "nullsense123";     // Phone hotspot password
const char* SERVER_IP = "192.168.43.1";     // Phone IP (shown on server start)
const int   SERVER_PORT = 5000;
const char* BAND_SIDE = "LEFT";             // "LEFT" or "RIGHT"

// ── DRV2605 ──
Adafruit_DRV2605 drv;
String last_signal = "";
unsigned long last_poll = 0;
const int POLL_INTERVAL = 80;  // ms between polls (~12 Hz)

// ── LRA Intensity -> DRV2605 effect ──
uint8_t getEffect(uint8_t intensity) {
  switch(intensity) {
    case 1: return 16;  // soft click
    case 2: return 14;  // medium click
    case 3: return 1;   // strong click
    default: return 0;
  }
}

void fireLRA(uint8_t intensity) {
  if (intensity == 0) return;
  drv.setWaveform(0, getEffect(intensity));
  drv.setWaveform(1, 0);
  drv.go();
  delay(60);
}

// ── Apply pattern: "front,mid,back" ──
void applyPattern(String signal, uint8_t front, uint8_t mid, uint8_t back) {
  if (signal == last_signal) return;  // skip duplicate
  last_signal = signal;

  Serial.printf("[%s] %s -> F:%d M:%d B:%d\n",
    BAND_SIDE, signal.c_str(), front, mid, back);

  fireLRA(front);
  fireLRA(mid);
  fireLRA(back);

  // Double pulse for STOP
  if (signal == "STOP") {
    delay(100);
    fireLRA(3);
    delay(80);
    fireLRA(3);
  }
}

// ── Parse server response: "SIGNAL,front,mid,back" ──
void parseAndApply(String response) {
  response.trim();

  int c1 = response.indexOf(',');
  int c2 = response.indexOf(',', c1 + 1);
  int c3 = response.indexOf(',', c2 + 1);

  if (c1 == -1 || c2 == -1 || c3 == -1) return;

  String signal = response.substring(0, c1);
  uint8_t front = response.substring(c1+1, c2).toInt();
  uint8_t mid   = response.substring(c2+1, c3).toInt();
  uint8_t back  = response.substring(c3+1).toInt();

  applyPattern(signal, front, mid, back);
}

// ── Connect WiFi ──
void connectWiFi() {
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("Connecting to ");
  Serial.print(WIFI_SSID);

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
    // Success pulse
    fireLRA(1); delay(150); fireLRA(1);
  } else {
    Serial.println(" Failed!");
  }
}

// ── Setup ──
void setup() {
  Serial.begin(115200);
  Serial.printf("\nNullSense %s Band (WiFi) starting\n", BAND_SIDE);

  Wire.begin();
  if (!drv.begin()) {
    Serial.println("ERROR: DRV2605L not found! Check wiring.");
    while(1) delay(1000);
  }
  drv.selectLibrary(1);
  drv.setMode(DRV2605_MODE_INTTRIG);
  Serial.println("DRV2605L OK");

  connectWiFi();
}

// ── Loop ──
void loop() {
  // Reconnect if dropped
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost — reconnecting...");
    connectWiFi();
    return;
  }

  // Poll server at interval
  if (millis() - last_poll >= POLL_INTERVAL) {
    last_poll = millis();

    HTTPClient http;
    String url = "http://" + String(SERVER_IP) + ":" +
                 String(SERVER_PORT) + "/signal?band=" + BAND_SIDE;
    http.begin(url);
    http.setTimeout(200);  // fast timeout for responsiveness

    int code = http.GET();
    if (code == 200) {
      String response = http.getString();
      parseAndApply(response);
    }
    http.end();
  }
}
