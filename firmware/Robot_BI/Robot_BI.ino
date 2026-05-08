// ═══════════════════════════════════════════════
// Robot Bi — ESP32 Motor Controller Firmware
// ESP32 Arduino Core v3.x
// L298N wiring:
//   IN1 = GPIO 26, IN2 = GPIO 27  (Motor A - trái)
//   IN3 = GPIO 14, IN4 = GPIO 12  (Motor B - phải)
//   ENA = GPIO 25 (PWM), ENB = GPIO 13 (PWM)
// ═══════════════════════════════════════════════

#include <WiFi.h>
#include <WiFiMulti.h>
#include <WiFiManager.h>
#include <Preferences.h>
#include <WebSocketsServer.h>

#define IN1 26
#define IN2 27
#define IN3 14
#define IN4 12
#define ENA 25
#define ENB 13

#define PWM_FREQ  1000
#define PWM_RES   8
#define MAX_WIFI  10

const int WS_PORT = 81;

WiFiMulti    wifiMulti;
Preferences  preferences;
WebSocketsServer wsServer(WS_PORT);

unsigned long lastCmdTime = 0;
const unsigned long WATCHDOG_MS = 2000;

// ── Motor primitives ──────────────────────────
void setMotorA(bool fwd, int pwm) {
  digitalWrite(IN1, fwd ? HIGH : LOW);
  digitalWrite(IN2, fwd ? LOW : HIGH);
  ledcWrite(ENA, pwm);
}

void setMotorB(bool fwd, int pwm) {
  digitalWrite(IN3, fwd ? HIGH : LOW);
  digitalWrite(IN4, fwd ? LOW : HIGH);
  ledcWrite(ENB, pwm);
}

void motorStop() {
  ledcWrite(ENA, 0);
  ledcWrite(ENB, 0);
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}

// ── Speed helpers ─────────────────────────────
int toPWM(int speed) {
  return constrain(map(speed, 0, 100, 0, 255), 0, 255);
}

int parseSpeed(String cmd) {
  int idx = cmd.indexOf("'speed': ");
  if (idx == -1) return 50;
  return cmd.substring(idx + 9).toInt();
}

int parseDuration(String cmd) {
  int idx = cmd.indexOf("'duration_ms': ");
  if (idx == -1) return 1000;
  return cmd.substring(idx + 15).toInt();
}

int parseDegrees(String cmd) {
  int idx = cmd.indexOf("'degrees': ");
  if (idx == -1) return 90;
  return cmd.substring(idx + 11).toInt();
}

// ── WiFi persistence ─────────────────────────

void loadSavedWifi() {
  preferences.begin("wifilist", true);
  int count = preferences.getInt("count", 0);
  for (int i = 0; i < count; i++) {
    String ssid = preferences.getString(("ssid" + String(i)).c_str(), "");
    String pass = preferences.getString(("pass" + String(i)).c_str(), "");
    if (ssid.length() > 0) {
      wifiMulti.addAP(ssid.c_str(), pass.c_str());
      Serial.printf("Loaded WiFi[%d]: %s\n", i, ssid.c_str());
    }
  }
  preferences.end();
}

bool saveWifi(String ssid, String pass) {
  preferences.begin("wifilist", false);
  int count = preferences.getInt("count", 0);
  // Update password if SSID already exists
  for (int i = 0; i < count; i++) {
    String existing = preferences.getString(("ssid" + String(i)).c_str(), "");
    if (existing == ssid) {
      preferences.putString(("pass" + String(i)).c_str(), pass.c_str());
      preferences.end();
      return true;
    }
  }
  // Evict oldest if full
  if (count >= MAX_WIFI) {
    for (int i = 0; i < count - 1; i++) {
      String s = preferences.getString(("ssid" + String(i+1)).c_str(), "");
      String p = preferences.getString(("pass" + String(i+1)).c_str(), "");
      preferences.putString(("ssid" + String(i)).c_str(), s.c_str());
      preferences.putString(("pass" + String(i)).c_str(), p.c_str());
    }
    count--;
  }
  preferences.putString(("ssid" + String(count)).c_str(), ssid.c_str());
  preferences.putString(("pass" + String(count)).c_str(), pass.c_str());
  preferences.putInt("count", count + 1);
  preferences.end();
  return true;
}

bool deleteWifi(String ssid) {
  preferences.begin("wifilist", false);
  int count = preferences.getInt("count", 0);
  int found = -1;
  for (int i = 0; i < count; i++) {
    String s = preferences.getString(("ssid" + String(i)).c_str(), "");
    if (s == ssid) { found = i; break; }
  }
  if (found == -1) { preferences.end(); return false; }
  for (int i = found; i < count - 1; i++) {
    String s = preferences.getString(("ssid" + String(i+1)).c_str(), "");
    String p = preferences.getString(("pass" + String(i+1)).c_str(), "");
    preferences.putString(("ssid" + String(i)).c_str(), s.c_str());
    preferences.putString(("pass" + String(i)).c_str(), p.c_str());
  }
  preferences.putInt("count", count - 1);
  preferences.end();
  return true;
}

String getSavedWifiJson() {
  preferences.begin("wifilist", true);
  int count = preferences.getInt("count", 0);
  String json = "[";
  for (int i = 0; i < count; i++) {
    String ssid = preferences.getString(("ssid" + String(i)).c_str(), "");
    if (ssid.length() > 0) {
      if (json != "[") json += ",";
      json += "{\"ssid\":\"" + ssid + "\"}";
    }
  }
  json += "]";
  preferences.end();
  return json;
}

String scanWifiJson() {
  int n = WiFi.scanNetworks();
  String json = "[";
  for (int i = 0; i < n; i++) {
    if (i > 0) json += ",";
    String ssid = WiFi.SSID(i);
    ssid.replace("\"", "\\\"");
    json += "{\"ssid\":\"" + ssid + "\",\"rssi\":" + String(WiFi.RSSI(i)) +
            ",\"secure\":" + String(WiFi.encryptionType(i) != WIFI_AUTH_OPEN ? "true" : "false") + "}";
  }
  json += "]";
  WiFi.scanDelete();
  return json;
}

// ── Motor command handlers ────────────────────
void cmdForward(String raw) {
  lastCmdTime = millis();
  int spd = toPWM(parseSpeed(raw));
  int dur = parseDuration(raw);
  setMotorA(true, spd);
  setMotorB(true, spd);
  delay(dur);
  motorStop();
  Serial.println("OK:forward");
}

void cmdBackward(String raw) {
  lastCmdTime = millis();
  int spd = toPWM(parseSpeed(raw));
  int dur = parseDuration(raw);
  setMotorA(false, spd);
  setMotorB(false, spd);
  delay(dur);
  motorStop();
  Serial.println("OK:backward");
}

void cmdLeft(String raw) {
  lastCmdTime = millis();
  int deg = parseDegrees(raw);
  int dur = map(deg, 0, 360, 0, 2000);
  setMotorA(false, 180);
  setMotorB(true,  180);
  delay(dur);
  motorStop();
  Serial.println("OK:turn_left");
}

void cmdRight(String raw) {
  lastCmdTime = millis();
  int deg = parseDegrees(raw);
  int dur = map(deg, 0, 360, 0, 2000);
  setMotorA(true,  180);
  setMotorB(false, 180);
  delay(dur);
  motorStop();
  Serial.println("OK:turn_right");
}

void cmdSpin(String raw) {
  lastCmdTime = millis();
  int spd = toPWM(parseSpeed(raw));
  int dur = parseDuration(raw);
  setMotorA(true,  spd);
  setMotorB(false, spd);
  delay(dur);
  motorStop();
  Serial.println("OK:spin");
}

void cmdDrive(String raw) {
  int idx_l = raw.indexOf("'left': ");
  int idx_r = raw.indexOf("'right': ");
  if (idx_l == -1 || idx_r == -1) {
    Serial.println("ERR:drive_parse");
    return;
  }
  int left  = raw.substring(idx_l + 8).toInt();
  int right = raw.substring(idx_r + 9).toInt();

  left  = constrain(left,  -100, 100);
  right = constrain(right, -100, 100);

  setMotorA(left  >= 0, toPWM(abs(left)));
  setMotorB(right >= 0, toPWM(abs(right)));

  lastCmdTime = millis();
  Serial.println("OK:drive");
}

// ── WebSocket event handler ───────────────────
void onWsEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
  if (type != WStype_TEXT) return;

  String line = String((char*)payload);
  line.trim();
  if (line.length() == 0) return;

  Serial.print("WS RECV: "); Serial.println(line);

  // Only reset watchdog for motor commands
  if (!line.startsWith("wifi_") && !line.startsWith("add_wifi")) {
    lastCmdTime = millis();
  }

  if      (line.startsWith("drive"))      cmdDrive(line);
  else if (line.startsWith("forward"))    cmdForward(line);
  else if (line.startsWith("backward"))   cmdBackward(line);
  else if (line.startsWith("turn_left"))  cmdLeft(line);
  else if (line.startsWith("turn_right")) cmdRight(line);
  else if (line.startsWith("spin"))       cmdSpin(line);
  else if (line.startsWith("stop"))       { motorStop(); lastCmdTime = 0; wsServer.sendTXT(num, "OK:stop"); }
  else if (line.startsWith("go_home"))    { motorStop(); lastCmdTime = 0; wsServer.sendTXT(num, "OK:go_home"); }
  else if (line.startsWith("add_wifi")) {
    // Format: add_wifi:{'ssid': 'TenWifi', 'password': 'MatKhau'}
    int ssid_idx = line.indexOf("'ssid': '");
    int pass_idx = line.indexOf("'password': '");
    if (ssid_idx != -1 && pass_idx != -1) {
      String ssid = line.substring(ssid_idx + 9, line.indexOf("'", ssid_idx + 9));
      String pass = line.substring(pass_idx + 13, line.indexOf("'", pass_idx + 13));
      bool ok = saveWifi(ssid, pass);
      wsServer.sendTXT(num, ok ? "OK:add_wifi" : "ERR:add_wifi_save");
      delay(500);
      ESP.restart();
    } else {
      wsServer.sendTXT(num, "ERR:add_wifi_parse");
    }
  }
  else if (line.startsWith("wifi_list")) {
    String json = getSavedWifiJson();
    wsServer.sendTXT(num, "wifi_list:" + json);
  }
  else if (line.startsWith("wifi_scan")) {
    wsServer.sendTXT(num, "wifi_scanning:true");
    String json = scanWifiJson();
    wsServer.sendTXT(num, "wifi_scan:" + json);
  }
  else if (line.startsWith("wifi_delete")) {
    int idx = line.indexOf("'ssid': '");
    if (idx != -1) {
      String ssid = line.substring(idx + 9, line.indexOf("'", idx + 9));
      bool ok = deleteWifi(ssid);
      wsServer.sendTXT(num, ok ? "OK:wifi_delete" : "ERR:wifi_delete_notfound");
    } else {
      wsServer.sendTXT(num, "ERR:wifi_delete_parse");
    }
  }
  else if (line.startsWith("wifi_connect")) {
    int idx = line.indexOf("'ssid': '");
    if (idx != -1) {
      wsServer.sendTXT(num, "OK:wifi_connecting");
      delay(200);
      ESP.restart();
    } else {
      wsServer.sendTXT(num, "ERR:wifi_connect_parse");
    }
  }
  else if (line.startsWith("wifi_status")) {
    String status = "{\"ssid\":\"" + WiFi.SSID() +
                    "\",\"ip\":\"" + WiFi.localIP().toString() +
                    "\",\"rssi\":" + String(WiFi.RSSI()) +
                    ",\"connected\":" + String(WiFi.status() == WL_CONNECTED ? "true" : "false") + "}";
    wsServer.sendTXT(num, "wifi_status:" + status);
  }
  else { wsServer.sendTXT(num, "ERR:unknown"); }
}

// ── Setup ─────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

  ledcAttach(ENA, PWM_FREQ, PWM_RES);
  ledcAttach(ENB, PWM_FREQ, PWM_RES);

  motorStop();
  Serial.println("Bi Motor Ready");

  // Load tất cả WiFi đã lưu vào WiFiMulti
  loadSavedWifi();

  preferences.begin("wifilist", true);
  int count = preferences.getInt("count", 0);
  preferences.end();

  if (count == 0) {
    // Lần đầu chưa có WiFi — mở hotspot cấu hình
    Serial.println("No saved WiFi — starting setup portal...");
    WiFiManager wm;
    wm.setConfigPortalTimeout(180);
    bool connected = wm.autoConnect("Robot-Bi-Setup", "robotbi123");
    if (connected) {
      saveWifi(WiFi.SSID(), WiFi.psk());
    }
  } else {
    // Kết nối WiFi mạnh nhất trong danh sách
    Serial.print("Connecting to best WiFi");
    int attempts = 0;
    while (wifiMulti.run() != WL_CONNECTED && attempts < 30) {
      delay(500); Serial.print("."); attempts++;
    }
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\nWiFi connected — IP: %s\n", WiFi.localIP().toString().c_str());
    wsServer.begin();
    wsServer.onEvent(onWsEvent);
    Serial.printf("WebSocket server started on port %d\n", WS_PORT);
  } else {
    Serial.println("\nWiFi connect failed — restarting...");
    ESP.restart();
  }
}

// ── Main loop ─────────────────────────────────
void loop() {
  wsServer.loop();

  // Watchdog: tự dừng nếu mất lệnh quá WATCHDOG_MS
  if (lastCmdTime > 0 && millis() - lastCmdTime > WATCHDOG_MS) {
    motorStop();
    lastCmdTime = 0;
    Serial.println("WATCHDOG:stop");
  }

  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  Serial.print("RECV: "); Serial.println(line);

  if      (line.startsWith("drive"))      cmdDrive(line);
  else if (line.startsWith("forward"))    cmdForward(line);
  else if (line.startsWith("backward"))   cmdBackward(line);
  else if (line.startsWith("turn_left"))  cmdLeft(line);
  else if (line.startsWith("turn_right")) cmdRight(line);
  else if (line.startsWith("spin"))       cmdSpin(line);
  else if (line.startsWith("stop"))       { motorStop(); lastCmdTime = 0; Serial.println("OK:stop"); }
  else if (line.startsWith("go_home"))    { motorStop(); lastCmdTime = 0; Serial.println("OK:go_home"); }
  else                                    { Serial.println("ERR:unknown"); }
}
