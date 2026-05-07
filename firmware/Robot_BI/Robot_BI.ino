// ═══════════════════════════════════════════════
// Robot Bi — ESP32 Motor Controller Firmware
// ESP32 Arduino Core v3.x
// L298N wiring:
//   IN1 = GPIO 26, IN2 = GPIO 27  (Motor A - trái)
//   IN3 = GPIO 14, IN4 = GPIO 12  (Motor B - phải)
//   ENA = GPIO 25 (PWM), ENB = GPIO 13 (PWM)
// ═══════════════════════════════════════════════

#include <WiFi.h>
#include <WebSocketsServer.h>

#define IN1 26
#define IN2 27
#define IN3 14
#define IN4 12
#define ENA 25
#define ENB 13

#define PWM_FREQ  1000
#define PWM_RES   8

// ── WiFi config ──────────────────────────────
const char* WIFI_SSID     = "Tang 4";      // ← đổi thành SSID thật
const char* WIFI_PASSWORD = "nha16ngo120"; // ← đổi thành password thật
const int   WS_PORT       = 81;

WebSocketsServer wsServer(WS_PORT);

unsigned long lastCmdTime = 0;
const unsigned long WATCHDOG_MS = 500;

void onWsEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
  if (type != WStype_TEXT) return;

  String line = String((char*)payload);
  line.trim();
  if (line.length() == 0) return;

  Serial.print("WS RECV: "); Serial.println(line);

  // Reset watchdog
  lastCmdTime = millis();

  if      (line.startsWith("drive"))      cmdDrive(line);
  else if (line.startsWith("forward"))    cmdForward(line);
  else if (line.startsWith("backward"))   cmdBackward(line);
  else if (line.startsWith("turn_left"))  cmdLeft(line);
  else if (line.startsWith("turn_right")) cmdRight(line);
  else if (line.startsWith("spin"))       cmdSpin(line);
  else if (line.startsWith("stop"))       { motorStop(); lastCmdTime = 0; wsServer.sendTXT(num, "OK:stop"); }
  else if (line.startsWith("go_home"))    { motorStop(); lastCmdTime = 0; wsServer.sendTXT(num, "OK:go_home"); }
  else                                    { wsServer.sendTXT(num, "ERR:unknown"); }
}

void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);

  ledcAttach(ENA, PWM_FREQ, PWM_RES);
  ledcAttach(ENB, PWM_FREQ, PWM_RES);

  motorStop();
  Serial.println("Bi Motor Ready");

  // Connect WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("WiFi connected — IP: ");
  Serial.println(WiFi.localIP());

  // Start WebSocket server
  wsServer.begin();
  wsServer.onEvent(onWsEvent);
  Serial.print("WebSocket server started on port ");
  Serial.println(WS_PORT);
}

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

// ── Speed: 0-100 → 0-255 ─────────────────────
int toPWM(int speed) {
  return constrain(map(speed, 0, 100, 0, 255), 0, 255);
}

// ── Parse từ command string ───────────────────
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

// ── Command handlers ──────────────────────────
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

// ── Continuous drive: left/right PWM độc lập, không duration ──
// left/right: -100 đến 100 (âm = lùi, dương = tiến)
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

  int pwm_l = toPWM(abs(left));
  int pwm_r = toPWM(abs(right));

  setMotorA(left  >= 0, pwm_l);
  setMotorB(right >= 0, pwm_r);

  lastCmdTime = millis();
  Serial.println("OK:drive");
}

// ── Main loop ─────────────────────────────────
void loop() {
  wsServer.loop();

  // ── Watchdog: tự dừng nếu mất lệnh quá 500ms ──
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