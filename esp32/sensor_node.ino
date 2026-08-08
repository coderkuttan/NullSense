/*
  NullSense — Helmet Sensor Node
  XIAO ESP32-C3 · 2× HC-SR04 · 2× VL53L0X (all on 3.3V)
  Serves JSON at http://nullsense-helmet.local/sensors (one-shot, used by
  phone_server.py) and a live feed at .../stream (SSE, used by
  phase8_fusion/fusion.py). Reachable via that mDNS hostname regardless of
  whatever IP DHCP hands it — no more updating shared/config.py every boot.
*/

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Wire.h>
#include <VL53L0X.h>

#define MDNS_HOSTNAME "nullsense-helmet"   // reachable at http://nullsense-helmet.local

// ─── EDIT THESE TWO ───
const char* SSID = "NullSense";
const char* PASS = "nullsense123";
// ──────────────────────

#define TRIG_L  D2
#define ECHO_L  D3
#define TRIG_R  D6
#define ECHO_R  D7
#define XSHUT_L D0
#define XSHUT_R D1

#define TOF_TIMEOUT_MS 500   // bail out instead of hanging forever on a stuck/disconnected ToF sensor

VL53L0X tofL, tofR;
WebServer server(80);

// ----------------------
// Ultrasonic Function
// ----------------------
float readUS(int trig, int echo) {
  digitalWrite(trig, LOW);  delayMicroseconds(2);
  digitalWrite(trig, HIGH); delayMicroseconds(10);
  digitalWrite(trig, LOW);
  long dur = pulseIn(echo, HIGH, 12000);
  if (dur == 0) return -1;
  return dur * 0.0343 / 2.0;
}

// ----------------------
// Ground (ToF) Function
// ----------------------
// setTimeout() in setup() bounds this. On timeout the library returns a
// sentinel instead of hanging: ~8191mm if the sensor is communicating but
// sees no valid target in range (normal, occasional), or 65535 if the
// sensor never initialized / isn't responding on I2C at all (hardware
// problem — check wiring). Both read as a hazard downstream, which is a
// fine default for an occasional miss but not for a sensor stuck at 65535.
int readGround(VL53L0X &tof) {
  return tof.readRangeContinuousMillimeters();
}

// ----------------------
// HTTP Root
// ----------------------
void handleRoot() {
  server.send(200, "text/plain",
              "NullSense helmet node. Hit /sensors or /stream");
}

// ----------------------
// JSON Endpoint (one-shot GET)
// ----------------------
void handleSensors() {
  float lcm = readUS(TRIG_L, ECHO_L);
  float rcm = readUS(TRIG_R, ECHO_R);
  int gl = readGround(tofL);
  int gr = readGround(tofR);

  String json = "{";
  json += "\"left_cm\":"  + String(lcm, 1) + ",";
  json += "\"right_cm\":" + String(rcm, 1) + ",";
  json += "\"gnd_l_mm\":" + String(gl) + ",";
  json += "\"gnd_r_mm\":" + String(gr);
  json += "}";
  server.send(200, "application/json", json);
}

// ----------------------
// Live Streaming Endpoint (SSE)
// ----------------------
void handleStream() {
  WiFiClient client = server.client();

  client.println("HTTP/1.1 200 OK");
  client.println("Content-Type: text/event-stream");
  client.println("Cache-Control: no-cache");
  client.println("Connection: keep-alive");
  client.println();

  while (client.connected()) {
    float lcm = readUS(TRIG_L, ECHO_L);
    float rcm = readUS(TRIG_R, ECHO_R);
    int gl = readGround(tofL);
    int gr = readGround(tofR);

    client.print("data: {\"left_cm\":");
    client.print(lcm, 1);
    client.print(",\"right_cm\":");
    client.print(rcm, 1);
    client.print(",\"gnd_l_mm\":");
    client.print(gl);
    client.print(",\"gnd_r_mm\":");
    client.print(gr);
    client.println("}");
    client.println();

    delay(100);
  }
}

// ----------------------
// WiFi
// ----------------------
const char* wifiStatusStr(wl_status_t s) {
  switch (s) {
    case WL_IDLE_STATUS:     return "idle";
    case WL_NO_SSID_AVAIL:   return "SSID not found";
    case WL_SCAN_COMPLETED:  return "scan completed";
    case WL_CONNECTED:       return "connected";
    case WL_CONNECT_FAILED:  return "connect failed (wrong password?)";
    case WL_CONNECTION_LOST: return "connection lost";
    case WL_DISCONNECTED:    return "disconnected";
    default:                 return "unknown";
  }
}

// Blocks until connected. Retries with a fresh WiFi.begin() every 15s and
// prints the WiFi status code each time, instead of hanging silently forever
// with no way to tell whether it's still negotiating or truly stuck.
void connectWiFi() {
  Serial.print("Connecting to "); Serial.println(SSID);
  WiFi.begin(SSID, PASS);
  WiFi.setSleep(false);

  unsigned long attemptStart = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
    if (millis() - attemptStart > 15000) {
      Serial.println();
      Serial.print("[!] Still not connected after 15s (status: ");
      Serial.print(wifiStatusStr(WiFi.status()));
      Serial.println(") — retrying...");
      WiFi.disconnect();
      delay(200);
      WiFi.begin(SSID, PASS);
      attemptStart = millis();
    }
  }
  Serial.println();
  Serial.print("[ok] IP: "); Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  Serial.println("\n=== NullSense helmet node ===");

  pinMode(TRIG_L, OUTPUT); pinMode(ECHO_L, INPUT);
  pinMode(TRIG_R, OUTPUT); pinMode(ECHO_R, INPUT);
  Wire.begin();
  Wire.setTimeOut(1000);   // bound the I2C bus itself — without this, a sensor that
                            // doesn't ACK cleanly (bad wiring, floating XSHUT) can lock
                            // the bus and hang ANY Wire call forever, including init(),
                            // which VL53L0X::setTimeout() does NOT protect against

  // Hold ToF sensors in reset
  pinMode(XSHUT_L, OUTPUT); digitalWrite(XSHUT_L, LOW);
  pinMode(XSHUT_R, OUTPUT); digitalWrite(XSHUT_R, LOW);
  delay(20);

  // LEFT
  pinMode(XSHUT_L, INPUT); delay(20);
  tofL.setTimeout(TOF_TIMEOUT_MS);   // MUST be set before init() — init() itself has
                                       // internal wait loops (e.g. getSpadInfo) that are
                                       // only bounded if a timeout is already configured
  if (!tofL.init()) Serial.println("[!] ToF LEFT not detected");
  else Serial.println("[ok] ToF LEFT");
  tofL.setAddress(0x30);
  tofL.startContinuous();

  // RIGHT
  pinMode(XSHUT_R, INPUT); delay(20);
  tofR.setTimeout(TOF_TIMEOUT_MS);   // same — before init(), not after
  Serial.println("Initializing ToF RIGHT...");
  if (!tofR.init()) Serial.println("[!] ToF RIGHT not detected");
  else Serial.println("[ok] ToF RIGHT");
  tofR.startContinuous();

  connectWiFi();

  if (MDNS.begin(MDNS_HOSTNAME)) {
    MDNS.addService("http", "tcp", 80);
    Serial.print("[ok] mDNS up — reachable at http://");
    Serial.print(MDNS_HOSTNAME); Serial.println(".local");
  } else {
    Serial.println("[!] mDNS failed to start — use the IP address above instead");
  }

  server.on("/", handleRoot);
  server.on("/sensors", handleSensors);
  server.on("/stream", handleStream);
  server.begin();
  Serial.println("[ok] HTTP server up");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost — reconnecting...");
    connectWiFi();   // blocks until back online, with the same retry+diagnostics as setup()
    MDNS.end();       // mDNS is bound to the old network state — restart it fresh
    if (MDNS.begin(MDNS_HOSTNAME)) {
      MDNS.addService("http", "tcp", 80);
    }
    return;
  }
  server.handleClient();
}
