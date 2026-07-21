#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <VL53L0X.h>

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

#define TOF_TIMEOUT_MS 200   // bail out instead of hanging forever on a stuck/disconnected ToF sensor

VL53L0X tofL, tofR;
WebServer server(80);

// ----------------------
// Ultrasonic Function
// ----------------------
float readUS(int trig, int echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);

  digitalWrite(trig, HIGH);
  delayMicroseconds(10);

  digitalWrite(trig, LOW);

  long dur = pulseIn(echo, HIGH, 12000);

  if (dur == 0) return -1;

  return dur * 0.0343 / 2.0;
}

// ----------------------
// Ground (ToF) Function
// ----------------------
// readRangeContinuousMillimeters() blocks forever by default if the sensor
// never raises its data-ready flag (bad wiring, address conflict, etc).
// setTimeout() in setup() + timeoutOccurred() here bound that wait so one
// dead sensor can't freeze the whole server.
int readGround(VL53L0X &tof) {
  int mm = tof.readRangeContinuousMillimeters();
  if (tof.timeoutOccurred()) return -1;
  return mm;
}

// ----------------------
// HTTP Root
// ----------------------
void handleRoot() {
  server.send(200, "text/plain",
              "NullSense helmet node. Hit /sensors or /stream");
}

// ----------------------
// JSON Endpoint
// ----------------------
void handleSensors() {
  float lcm = readUS(TRIG_L, ECHO_L);
  float rcm = readUS(TRIG_R, ECHO_R);
  int gl = readGround(tofL);
  int gr = readGround(tofR);

  String json = "{";
  json += "\"left_cm\":" + String(lcm,1) + ",";
  json += "\"right_cm\":" + String(rcm,1) + ",";
  json += "\"gnd_l_mm\":" + String(gl) + ",";
  json += "\"gnd_r_mm\":" + String(gr);
  json += "}";

  server.send(200, "application/json", json);
}

// ----------------------
// Live Streaming Endpoint
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
    client.print(lcm,1);

    client.print(",\"right_cm\":");
    client.print(rcm,1);

    client.print(",\"gnd_l_mm\":");
    client.print(gl);

    client.print(",\"gnd_r_mm\":");
    client.print(gr);

    client.println("}");
    client.println();

    delay(100);
  }
}

void setup() {

  Serial.begin(115200);
  delay(1500);

  pinMode(TRIG_L, OUTPUT);
  pinMode(ECHO_L, INPUT);

  pinMode(TRIG_R, OUTPUT);
  pinMode(ECHO_R, INPUT);

  Wire.begin();

  // Hold ToF sensors in reset
  pinMode(XSHUT_L, OUTPUT);
  digitalWrite(XSHUT_L, LOW);

  pinMode(XSHUT_R, OUTPUT);
  digitalWrite(XSHUT_R, LOW);

  delay(20);

  // LEFT
  pinMode(XSHUT_L, INPUT);
  delay(20);

  tofL.init();
  tofL.setAddress(0x30);
  tofL.setTimeout(TOF_TIMEOUT_MS);
  tofL.startContinuous();

  // RIGHT
  pinMode(XSHUT_R, INPUT);
  delay(20);

  tofR.init();
  tofR.setTimeout(TOF_TIMEOUT_MS);
  tofR.startContinuous();

  WiFi.begin(SSID, PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println(WiFi.localIP());

  // Register endpoints
  server.on("/", handleRoot);
  server.on("/sensors", handleSensors);
  server.on("/stream", handleStream);

  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
}
