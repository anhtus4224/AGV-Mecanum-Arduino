// AGV_CORNER90_V1 - ban thu goc vuong, CHUA thu tren xe.
// Moc runout 1216ms la uoc luong; chua do duoc troi co khi / goc xoay.
// Giu chan, LOW, chieu cam bien va ne can cua file nguoi dung.
// Thang/runout/xoay toi da 255; khi om cua thuong hai ben cung tien.

// 1. CẤU HÌNH 8 CHÂN CHO 4 DRIVER BTS7960 (GIỮ NGUYÊN 100% PHẦN CỨNG)
const int D1_RPWM = 44;  // Trước - Trái (FL) - Kênh Lùi (Đã phục hồi băm PWM)
const int D1_LPWM = 3;   // Trước - Trái (FL) - Kênh Tiến (Pin 3 PWM)
const int D2_RPWM = 5;   // Trước - Phải (FR)
const int D2_LPWM = 9;   // Trước - Phải (FR)
const int D3_RPWM = 7;   // Sau - Trái (RL)
const int D3_LPWM = 8;   // Sau - Trái (RL)
const int D4_RPWM = 11;  // Sau - Phải (RR)
const int D4_LPWM = 12;  // Sau - Phải (RR)

// 2. CHÂN SERVO & NÚT BẤM VẬT LÝ & ĐO ĐIỆN ÁP
const int SERVO_PIN       = 10; // Servo điều khiển bằng xung mềm (Tránh chiếm Timer 5)
const int BUTTON_MODE_PIN = 31; // Nút bấm vật lý chuyển chế độ (INPUT_PULLUP)
const int VOLT_PIN        = A5; // Chân Analog đọc phân áp Pin/Ắc quy

// 3. CẤU HÌNH 4 CẢM BIẾN SIÊU ÂM
const int TRIG_FRONT = 22; const int ECHO_FRONT = 23;
const int TRIG_BACK  = 24; const int ECHO_BACK  = 25;
const int TRIG_LEFT  = 26; const int ECHO_LEFT  = 27;
const int TRIG_RIGHT = 28; const int ECHO_RIGHT = 29;

const bool USE_ULTRASONIC = true;
const int  OBSTACLE_CM    = 18; // Ngưỡng phát hiện vật cản trước
const unsigned long SONAR_SLOT_MS = 40; // Đọc xoay vòng mỗi 40ms/cảm biến

// 4. CẤU HÌNH THANH DÒ LINE 5 MẮT TCRT5000 (A0 - A4)
const int PIN_RAW_1 = A0; // Mắt 1: Ngoài cùng trái (L2)
const int PIN_RAW_2 = A1; // Mắt 2: Giữa trái (L1)
const int PIN_RAW_3 = A2; // Mắt 3: Tâm giữa (M)
const int PIN_RAW_4 = A3; // Mắt 4: Giữa phải (R1)
const int PIN_RAW_5 = A4; // Mắt 5: Ngoài cùng phải (R2)

const bool REVERSE_SENSOR_ORDER = false;  // true: mắt A0 nằm bên PHẢI xe (đảo thứ tự). Xe đang NÉ vạch => đổi cờ này
const int  LINE_DETECTED = LOW; // DA DO OUT3/A2: trang ADC~952 (HIGH), den ADC~18 (LOW).

// 5. THÔNG SỐ VẬN HÀNH & ĐIỀU TỐC P-D
const int WIFI_MAX_SPEED   = 255;
const int AVOID_STRAFE_SPD = 160;
const int AVOID_FORWARD_SPEED = 200;
const unsigned long AVOID_OUT_MS         = 2900;  // [1] dạt ngang RA
const unsigned long AVOID_FORWARD_MS     = 3500;  // [2] tiến thẳng song song vượt vật cản
const unsigned long AVOID_BACK_BLIND_MS  = 2000;  // [3a] dạt ngang NGƯỢC LẠI cố định (vượt khoảng cách xa)
const unsigned long AVOID_BACK_SEARCH_MS = 4500;  // [3b] tiếp tục dạt dò tìm line tối đa

// --- Dieu khien cua lien tuc: cac gia tri nay CAN THU TREN XE ---
const int LINE_BASE_SPEED = 120; // phuc hoi, khong phai toc do cua binh thuong
const int LINE_FAST_SPEED = 255;
const int CURVE_SPEED = 190; // PWM banh ngoai khi om cua
const int CURVE_INNER_MIN = 90; // banh trong van tien khi con thay line
const float STEER_KP = 20.0f;
const float EDGE_EXTRA_KP = 10.0f; // tang luc lai khi |err| > 2
const float STEER_MAX = 100.0f;
const float ERROR_FILTER_MS = 20.0f;
const float ACCEL_PER_10MS = 4.0f;
const float DECEL_PER_10MS = 10.0f;
const float STEER_PER_10MS = 8.0f;
const unsigned long SIDE_CURVE_MS = 100;
const unsigned long CURVE_EXIT_MS = 160;
const int LOST_FORWARD_SPEED = 100;
const int SEARCH_OUTER_SPEED = 160;
const int SLEW_STEP = 40; // gioi han them cho phuc hoi / mat line
const bool ENABLE_90_TURN = true; // bat goc vuong: Q/E cho phep xoay hai ben nguoc chieu
const unsigned long CONTROL_PERIOD_MS = 10;

// --- Goc vuong: cac thoi gian xoay chua phai hieu chuan goc ---
// Cac gia tri tiep can tinh tu phep do, CHUA xac nhan tren goc that.
const unsigned long MEASURED_80CM_MS = 6707;
const unsigned long SENSOR_OFFSET_MM = 145;
const unsigned long RUNOUT_RIGHT_MS = (MEASURED_80CM_MS * SENSOR_OFFSET_MM + 400) / 800;
const unsigned long RUNOUT_LEFT_MS = RUNOUT_RIGHT_MS;
const int RUNOUT_SPEED = 255;
const int TURN_RIGHT_SPEED = 255;
const int TURN_LEFT_SPEED = 255;
const unsigned long MIN_TURN_MS = 200; // chi chong bat lai qua som, KHONG phai goc 90
const unsigned long TURN_TIMEOUT_MS = 4000;
const unsigned long SETTLE_MS = 80;
const unsigned long CORNER_LOCK_MS = 1200;
const unsigned long MANUAL_TURN_TIMEOUT_MS = 180; // chu ky lenh trong video ~80ms

// --- Bộ lọc mất vạch 3 tầng ---
const unsigned long HOLD_LAST_MS  = 150;
const unsigned long CREEP_MS      = 300;
const unsigned long SEARCH_MAX_MS = 1200;

const int FAILSAFE_MS        = 700;

// --- Chống lặp phím M & chẩn đoán ---
const unsigned long MODE_TOGGLE_LOCK_MS = 800;
const bool DEBUG_HEARTBEAT = true;
const bool DEBUG_RX = true;
const int DEBOUNCE_DELAY     = 80;

enum TurnState { IDLE_LINE, RUNOUT_90, BRAKE_90, TURNING_90, SETTLE_90, CORNER_FAULT };
TurnState turnState = IDLE_LINE;

bool isLineTrackingMode   = false;
bool isExecutingAvoidance = false;
char currentCommand       = 'S';
char pendingTurnDir       = 'E';

unsigned long lastPacketTime          = 0;
unsigned long turnTimer               = 0;
unsigned long lostLineTimer           = 0;
unsigned long postAvoidanceBlindTimer = 0;
unsigned long lastTelemetryTime       = 0;
unsigned long lastSonarTime           = 0;
unsigned long lastControlTime         = 0;
unsigned long lastToggleTime          = 0;
bool lostReported = false;
unsigned long lastHeartbeat = 0;
unsigned long rxUSB = 0, rxESP = 0, rxRejected = 0;
char lastRx = ' ';

int buttonState     = HIGH;
int lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;

long distF = 120, distB = 180, distL = 75, distR = 80;
int  frontHits   = 0;
int  sonarSlot   = 0;
int  cornerCount = 0;
float lastErr    = 0.0f;
int  lastLeftCmd  = LINE_BASE_SPEED;
int  lastRightCmd = LINE_BASE_SPEED;
int  curL = 0, curR = 0;
int cruiseSpeed = LINE_BASE_SPEED;
bool curveActive = false;
bool centerPending = false;
unsigned long centerSince = 0;
char lineZone = 'S'; // S: thang, C: cua, L: mat line, X: hai mat ria cung bat
unsigned int logicalLineMask = 0; // bit0=L2, bit1=L1, bit2=M, bit3=R1, bit4=R2
int lineTargetL = 0, lineTargetR = 0;
bool adcHadLine = false;
float lineAbsError = 0.0f;
float filteredErr = 0.0f;
float forwardPwm = 0.0f;
float steeringPwm = 0.0f;
bool sidePending = false;
int sideSign = 0;
unsigned long sideSince = 0;
unsigned long lastCornerFinished = 0;
unsigned long cornerSampleTime = 0;
bool cornerBlankSeen = false;
bool cornerSideSeen = false;
uint8_t cornerBlankCount = 0;
uint8_t cornerCenterCount = 0;

// Khai báo nguyên mẫu hàm
void stopAllMotors();
void motor(int rpwm, int lpwm, int v);
void drive(int fl, int fr, int rl, int rr);
void steerChassis(int speedLeft, int speedRight);
void steerSigned(int speedLeft, int speedRight);
void applyMecanumChassis(char cmd, int spd);
long readUltrasonicCM(int trigPin, int echoPin);
void updateSonar();
void servoMove(int angle, unsigned long holdMs);
void executeCorridorAvoidance();
bool checkEmergencyAbort();
void toggleMode(const char* source);
void stopLineLost();
void resetLineTracking();
void cornerFail(const char* reason);
void logCorner(const char* event);
int slewTo(int cur, int target);
float moveToward(float value, float target, float step);
float readBatteryVoltage();
void sendTelemetry();
void printLineAdc();
void checkModeButton();
void readSerialCommands();
void parseSingleChar(char c, char src);
void handleManualMode();
void handleLineAndObstacleMode();
bool nonBlockingAction(char cmd, int spd, unsigned long durationMs);

void setup() {
  Serial.begin(115200); // Giao tiếp USB Jetson Nano
  Serial2.begin(9600);  // Giao tiếp ESP Wi-Fi

  pinMode(D1_RPWM, OUTPUT); pinMode(D1_LPWM, OUTPUT);
  pinMode(D2_RPWM, OUTPUT); pinMode(D2_LPWM, OUTPUT);
  pinMode(D3_RPWM, OUTPUT); pinMode(D3_LPWM, OUTPUT);
  pinMode(D4_RPWM, OUTPUT); pinMode(D4_LPWM, OUTPUT);
  stopAllMotors();

  pinMode(BUTTON_MODE_PIN, INPUT_PULLUP);
  pinMode(SERVO_PIN, OUTPUT);
  servoMove(90, 300); // Khởi tạo góc nhìn thẳng 90 độ cho Servo

  pinMode(TRIG_FRONT, OUTPUT); pinMode(ECHO_FRONT, INPUT);
  pinMode(TRIG_BACK,  OUTPUT); pinMode(ECHO_BACK,  INPUT);
  pinMode(TRIG_LEFT,  OUTPUT); pinMode(ECHO_LEFT,  INPUT);
  pinMode(TRIG_RIGHT, OUTPUT); pinMode(ECHO_RIGHT, INPUT);

  pinMode(PIN_RAW_1, INPUT); pinMode(PIN_RAW_2, INPUT);
  pinMode(PIN_RAW_3, INPUT); pinMode(PIN_RAW_4, INPUT);
  pinMode(PIN_RAW_5, INPUT);

  pinMode(VOLT_PIN, INPUT);

  isLineTrackingMode = false;
  currentCommand = 'S';
  lastPacketTime = millis();

  Serial.print(">> [AGV_CORNER90_V1 READY] fast="); Serial.print(LINE_FAST_SPEED);
  Serial.print(" curve="); Serial.print(CURVE_SPEED);
  Serial.print(" runoutR/L="); Serial.print(RUNOUT_RIGHT_MS); Serial.print('/');
  Serial.print(RUNOUT_LEFT_MS); Serial.println(" ms; corner turn255, LOW, order=0");
}

void loop() {
  checkModeButton();
  readSerialCommands();
  updateSonar();

  if (isLineTrackingMode) {
    handleLineAndObstacleMode();
  } else {
    handleManualMode();
  }

  if (DEBUG_HEARTBEAT && millis() - lastHeartbeat > 1000) {
    lastHeartbeat = millis();
    Serial.print(">> HB fw=AGV_CORNER90_V1 up="); Serial.print(millis() / 1000);
    Serial.print("s mode="); Serial.print(isLineTrackingMode ? "AUTO" : "MANUAL");
    Serial.print(" rxUSB="); Serial.print(rxUSB);
    Serial.print(" rxESP="); Serial.print(rxESP);
    Serial.print(" rejESP="); Serial.print(rxRejected);
    Serial.print(" last='"); Serial.print(lastRx); Serial.print("'");
    Serial.print(" cruise="); Serial.print(cruiseSpeed);
    Serial.print(" zone="); Serial.print(lineZone);
    Serial.print(" a="); Serial.print(lineAbsError, 2);
    Serial.print(" ef="); Serial.print(filteredErr, 2);
    Serial.print(" steer="); Serial.print(steeringPwm, 1);
    Serial.print(" turnState="); Serial.print((int)turnState);
    Serial.print(" bits=");
    for (int bit = 0; bit < 5; ++bit) Serial.print((logicalLineMask >> bit) & 1);
    Serial.print(" target="); Serial.print(lineTargetL); Serial.print('/'); Serial.print(lineTargetR);
    Serial.print(" L/R="); Serial.print(curL); Serial.print('/'); Serial.println(curR);
  }

  // Bắn Telemetry chu kỳ 150ms cho Web 3D
  if (millis() - lastTelemetryTime > 150) {
    sendTelemetry();
    lastTelemetryTime = millis();
  }
}

// XỬ LÝ LỆNH TRUYỀN THÔNG (TÁCH BIỆT 'R' ĐỂ KHÔNG XUNG ĐỘT)
void parseSingleChar(char c, char src) {
  if (DEBUG_RX) {
    Serial.print(">> RX["); Serial.print(src); Serial.print("]: '");
    if (c >= 32 && c < 127) Serial.print(c); else Serial.print('?');
    Serial.print("' 0x"); Serial.print((int)(unsigned char)c, HEX);
    Serial.print(" @"); Serial.println(millis());
  }
  if (src == 'U') rxUSB++; else rxESP++;
  if (c != '\r' && c != '\n') lastRx = c;
  if (c == '\r' || c == '\n' || c == 0) return;

  if (src == 'E' && !strchr("FBLRQESMZ", c)) { rxRejected++; return; }

  if (c == 'M' || c == 'm' || c == 'X' || c == 'x') {
    if (millis() - lastToggleTime < MODE_TOGGLE_LOCK_MS) return;
    toggleMode("PHIM M");
    return;
  }

  if (c == 'Z' || c == 'z') {
    isLineTrackingMode = false;
    turnState = IDLE_LINE;
    currentCommand = 'S';
    stopAllMotors();
    Serial.println(">> VE CHE DO LAI TAY");
    return;
  }

  if (isLineTrackingMode) {
    if (!strchr("FWwBsSLAaRDdQqEe", c)) return;
    isLineTrackingMode = false;
    turnState = IDLE_LINE;
    stopAllMotors();
    Serial.println(">> PHIM LAI TAY -> THOAT TU HANH, VE LAI TAY");
  }

  if      (c == 'F' || c == 'W' || c == 'w') currentCommand = 'F';
  else if (c == 'B' || c == 's')             currentCommand = 'B';
  else if (c == 'L' || c == 'A' || c == 'a') currentCommand = 'L';
  else if (c == 'R' || c == 'D' || c == 'd') currentCommand = 'R';
  else if (c == 'Q' || c == 'q')             currentCommand = 'Q';
  else if (c == 'E' || c == 'e')             currentCommand = 'E';
  else if (c == 'S' || c == ' ') {
    currentCommand = 'S';
    stopAllMotors();
  }
  else {
    return;
  }

  if (!isLineTrackingMode) {
    if (currentCommand == 'S') {
      stopAllMotors();
    } else {
      applyMecanumChassis(currentCommand, WIFI_MAX_SPEED);
    }
  }
  lastPacketTime = millis();
}

void readSerialCommands() {
  while (Serial.available() > 0)  parseSingleChar(Serial.read(), 'U');
  while (Serial2.available() > 0) parseSingleChar(Serial2.read(), 'E');
}

void toggleMode(const char* source) {
  isLineTrackingMode = !isLineTrackingMode;
  turnState = IDLE_LINE;
  currentCommand = 'S';
  stopAllMotors();

  lastErr = 0.0f;
  lastLeftCmd = lastRightCmd = LINE_BASE_SPEED; curL = curR = 0; cruiseSpeed = LINE_BASE_SPEED; resetLineTracking();
  lostLineTimer = millis();
  cornerCount = 0;
  frontHits = 0;
  lostReported = false;
  lastToggleTime = millis();

  Serial.print(">> [");
  Serial.print(source);
  Serial.print("]: CHUYEN SANG -> ");
  Serial.println(isLineTrackingMode ? "TU HANH DO LINE" : "LAI TAY (MANUAL)");
}

void checkModeButton() {
  int reading = digitalRead(BUTTON_MODE_PIN);
  if (reading != lastButtonState) lastDebounceTime = millis();
  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
    if (reading != buttonState) {
      buttonState = reading;
      if (buttonState == LOW) toggleMode("NUT BAM VAT LY PIN 31");
    }
  }
  lastButtonState = reading;
}

void handleManualMode() {
  unsigned long timeout = (currentCommand == 'E' || currentCommand == 'Q')
      ? MANUAL_TURN_TIMEOUT_MS : FAILSAFE_MS;
  if (millis() - lastPacketTime > timeout) {
    if (currentCommand != 'S') {
      currentCommand = 'S';
      stopAllMotors();
      Serial.println(">> MANUAL_TIMEOUT: PWM=0 (app khong gui S)");
    }
  }
}

// ADC samples are taken sequentially, not simultaneous with DATA/digitalRead.
// Discard first ADC conversion after switching channel to allow settling.
void printLineAdc() {
  const uint8_t pins[5] = {A0, A1, A2, A3, A4};
  int values[5];
  for (uint8_t i = 0; i < 5; ++i) {
    analogRead(pins[i]);
    values[i] = analogRead(pins[i]);
  }
  Serial.print("ADC5:");
  for (uint8_t i = 0; i < 5; ++i) {
    if (i) Serial.print(',');
    Serial.print(values[i]);
  }
  Serial.println();
}

void sendTelemetry() {
  bool s1 = (digitalRead(PIN_RAW_1) == LINE_DETECTED);
  bool s2 = (digitalRead(PIN_RAW_2) == LINE_DETECTED);
  bool s3 = (digitalRead(PIN_RAW_3) == LINE_DETECTED);
  bool s4 = (digitalRead(PIN_RAW_4) == LINE_DETECTED);
  bool s5 = (digitalRead(PIN_RAW_5) == LINE_DETECTED);

  const char* act = "STOP";
  if      (currentCommand == 'F') act = "FORWARD";
  else if (currentCommand == 'B') act = "BACKWARD";
  else if (currentCommand == 'L') act = "STRAFE_LEFT";
  else if (currentCommand == 'R') act = "STRAFE_RIGHT";
  else if (currentCommand == 'Q') act = "ROTATE_LEFT";
  else if (currentCommand == 'E') act = "ROTATE_RIGHT";

  Serial.print("DATA:");
  Serial.print(s1 ? '1' : '0'); Serial.print(s2 ? '1' : '0'); Serial.print(s3 ? '1' : '0');
  Serial.print(s4 ? '1' : '0'); Serial.print(s5 ? '1' : '0');
  Serial.print(",");
  Serial.print(act);
  Serial.print(",");
  Serial.println(readBatteryVoltage(), 2);

  Serial.print("SONAR:");
  Serial.print(distF); Serial.print(",");
  Serial.print(distB); Serial.print(",");
  Serial.print(distL); Serial.print(",");
  Serial.println(distR);
  printLineAdc();
}

float readBatteryVoltage() {
  int raw = analogRead(VOLT_PIN);
  if (raw < 30) return 12.4;
  return (float)raw * (5.0 / 1023.0) * 4.0;
}

long readUltrasonicCM(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  long duration = pulseIn(echoPin, HIGH, 8000);
  if (duration <= 0) return 999;
  return duration * 0.034 / 2;
}

void updateSonar() {
  if (millis() - lastSonarTime < SONAR_SLOT_MS) return;
  lastSonarTime = millis();

  switch (sonarSlot) {
    case 0: case 2: case 4:
      distF = readUltrasonicCM(TRIG_FRONT, ECHO_FRONT);
      if (distF > 3 && distF <= OBSTACLE_CM) {
        if (frontHits < 100) frontHits++;
      } else {
        frontHits = 0;
      }
      break;
    case 1: distL = readUltrasonicCM(TRIG_LEFT,  ECHO_LEFT);  break;
    case 3: distR = readUltrasonicCM(TRIG_RIGHT, ECHO_RIGHT); break;
    case 5: distB = readUltrasonicCM(TRIG_BACK,  ECHO_BACK);  break;
  }
  sonarSlot = (sonarSlot + 1) % 6;
}

// THUẬT TOÁN TỰ HÀNH VI SAI P-D & BỘ LỌC MẤT VẠCH 3 TẦNG
void handleLineAndObstacleMode() {
  unsigned long now = millis();

  if (USE_ULTRASONIC && frontHits >= 2) {
    frontHits = 0;
    if (turnState != IDLE_LINE) { cornerFail("OBSTACLE_DURING_CORNER"); return; }
    stopAllMotors();
    executeCorridorAvoidance();
    return;
  }

  bool l2, l1, m, r1, r2;
  if (!REVERSE_SENSOR_ORDER) {
    l2 = (digitalRead(PIN_RAW_1) == LINE_DETECTED);
    l1 = (digitalRead(PIN_RAW_2) == LINE_DETECTED);
    m  = (digitalRead(PIN_RAW_3) == LINE_DETECTED);
    r1 = (digitalRead(PIN_RAW_4) == LINE_DETECTED);
    r2 = (digitalRead(PIN_RAW_5) == LINE_DETECTED);
  } else {
    l2 = (digitalRead(PIN_RAW_5) == LINE_DETECTED);
    l1 = (digitalRead(PIN_RAW_4) == LINE_DETECTED);
    m  = (digitalRead(PIN_RAW_3) == LINE_DETECTED);
    r1 = (digitalRead(PIN_RAW_2) == LINE_DETECTED);
    r2 = (digitalRead(PIN_RAW_1) == LINE_DETECTED);
  }

  if (turnState != IDLE_LINE) {
    // Chuyen goc co bo doc 10ms rieng; khong goi xu ly mat line binh thuong.
    if (now - cornerSampleTime < CONTROL_PERIOD_MS) return;
    cornerSampleTime = now;
    logicalLineMask = (unsigned int)l2 | ((unsigned int)l1 << 1) |
        ((unsigned int)m << 2) | ((unsigned int)r1 << 3) | ((unsigned int)r2 << 4);
    if (turnState == CORNER_FAULT) { stopAllMotors(); return; }
    if (turnState == RUNOUT_90) {
      unsigned long runout = pendingTurnDir == 'E' ? RUNOUT_RIGHT_MS : RUNOUT_LEFT_MS;
      if (now - turnTimer < runout) {
        steerChassis(RUNOUT_SPEED, RUNOUT_SPEED);
        curL = curR = lineTargetL = lineTargetR = RUNOUT_SPEED;
        cruiseSpeed = RUNOUT_SPEED;
        return;
      }
      // Khong chen dung/pha giam toc xoay: chuyen truc tiep sang xoay nhanh.
      turnState = TURNING_90; turnTimer = now;
      cornerBlankSeen = false; cornerSideSeen = false;
      cornerBlankCount = cornerCenterCount = 0;
      logCorner("SPIN_START");
    }
    if (turnState == TURNING_90) {
      if (now - turnTimer >= TURN_TIMEOUT_MS) { cornerFail("SPIN_TIMEOUT"); return; }
      bool blank = !(l2 || l1 || m || r1 || r2);
      if (blank) {
        if (cornerBlankCount < 2) ++cornerBlankCount;
        if (cornerBlankCount >= 2) cornerBlankSeen = true;
      } else { cornerBlankCount = 0; }
      bool expectedSide = pendingTurnDir == 'E' ? (r1 || r2) : (l1 || l2);
      if (cornerBlankSeen && expectedSide) cornerSideSeen = true;
      bool center = m && !l2 && !r2;
      if (cornerBlankSeen && cornerSideSeen && center && now - turnTimer >= MIN_TURN_MS) {
        if (cornerCenterCount < 2) ++cornerCenterCount;
      } else { cornerCenterCount = 0; }
      if (cornerCenterCount >= 2) {
        // Ngat PWM ngay, khong doi goi WiFi, khong dao chieu de phanh.
        stopAllMotors(); curL = curR = lineTargetL = lineTargetR = 0;
        logCorner("CENTER_STOP"); turnState = SETTLE_90; turnTimer = now;
        currentCommand = 'S'; return;
      }
      int speed = pendingTurnDir == 'E' ? TURN_RIGHT_SPEED : TURN_LEFT_SPEED;
      applyMecanumChassis(pendingTurnDir, speed);
      // L/R la lenh co dau trong luc xoay, duong=tien.
      curL = lineTargetL = pendingTurnDir == 'E' ? speed : -speed;
      curR = lineTargetR = -curL;
      currentCommand = pendingTurnDir; return;
    }
    if (turnState == SETTLE_90) {
      stopAllMotors();
      if (now - turnTimer < SETTLE_MS) return;
      if (!(m && !l2 && !r2)) { cornerFail("LINE_MOVED_AFTER_STOP"); return; }
      logCorner("LOCK_OK");
      turnState = IDLE_LINE; lastCornerFinished = now;
      resetLineTracking(); forwardPwm = LINE_BASE_SPEED; curveActive = true;
      lastErr = 0; lastLeftCmd = lastRightCmd = LINE_BASE_SPEED;
      lostLineTimer = now; lastControlTime = now; currentCommand = 'F';
      cornerCount = 0; return;
    }
    cornerFail("INVALID_STATE"); return;
  }

  unsigned long elapsed = now - lastControlTime;
  if (elapsed < CONTROL_PERIOD_MS) return;
  lastControlTime = now;
  if (elapsed > 30) elapsed = 30; // khong nhay lenh sau mot lan chan lau
  float tickScale = elapsed / 10.0f;

  if (ENABLE_90_TURN) {
    bool enabled = now - postAvoidanceBlindTimer > 400 && now - lastCornerFinished > CORNER_LOCK_MS;
    bool rightCorner = m && r1 && r2 && !l2;
    bool leftCorner = m && l1 && l2 && !r2;
    char dir = rightCorner ? 'E' : 'Q';
    if (enabled && (rightCorner || leftCorner)) {
      if (pendingTurnDir != dir) cornerCount = 0;
      pendingTurnDir = dir;
      if (++cornerCount >= 2) {
        cornerCount = 0; turnState = RUNOUT_90; turnTimer = now;
        cornerSampleTime = now; lineZone = 'T';
        logCorner("DETECT_RUNOUT");
        steerChassis(RUNOUT_SPEED, RUNOUT_SPEED);
        curL = curR = lineTargetL = lineTargetR = RUNOUT_SPEED;
        cruiseSpeed = RUNOUT_SPEED; currentCommand = 'F'; return;
      }
    } else { cornerCount = 0; }
  }

  logicalLineMask = (unsigned int)l2 | ((unsigned int)l1 << 1) |
                    ((unsigned int)m << 2) | ((unsigned int)r1 << 3) |
                    ((unsigned int)r2 << 4);
  int cnt = (int)l2 + (int)l1 + (int)m + (int)r1 + (int)r2;
  int targetL, targetR;

  if (cnt > 0) {
    adcHadLine = true;
    lostReported = false;
    lostLineTimer = now;
    float sum = -4.0f * l2 - 2.0f * l1 + 2.0f * r1 + 4.0f * r2;
    float err = sum / cnt;
    float a = fabs(err);
    lineAbsError = a;
    const bool edge = l2 || r2;
    const bool ambiguous = l2 && r2;
    float alpha = elapsed / (ERROR_FILTER_MS + elapsed);
    filteredErr += alpha * (err - filteredErr);

    // Lech thoang qua van di nhanh; lech cung phia lau -> om cua 190,
    // khong reset ve 120 nhu ban cu.
    int sign = (err > 0) ? 1 : ((err < 0) ? -1 : 0);
    if (!edge && a >= 2.0f) {
      if (!sidePending || sign != sideSign) {
        sidePending = true; sideSign = sign; sideSince = now;
      }
      if (now - sideSince >= SIDE_CURVE_MS) curveActive = true;
    } else {
      sidePending = false;
    }
    if (edge) curveActive = true;

    // Roi mat ria chua co nghia da het cua. Chi tang lai khi gan tam on dinh.
    if (curveActive && !edge && a <= 1.0f) {
      if (!centerPending) { centerPending = true; centerSince = now; }
      if (now - centerSince >= CURVE_EXIT_MS) {
        curveActive = false; centerPending = false;
      }
    } else {
      centerPending = false;
    }

    float speedTarget = curveActive ? CURVE_SPEED : LINE_FAST_SPEED;
    float steerTarget;
    if (ambiguous) {
      lineZone = 'X'; speedTarget = LINE_BASE_SPEED; steerTarget = 0;
    } else {
      lineZone = curveActive ? 'C' : 'S';
      float e = fabs(filteredErr);
      float trim = STEER_KP * e;
      if (e > 2.0f) trim += EDGE_EXTRA_KP * (e - 2.0f);
      trim = constrain(trim, 0.0f, STEER_MAX);
      steerTarget = (filteredErr >= 0) ? trim : -trim;
    }
    forwardPwm = moveToward(forwardPwm, speedTarget,
        ((speedTarget < forwardPwm) ? DECEL_PER_10MS : ACCEL_PER_10MS) * tickScale);
    steeringPwm = moveToward(steeringPwm, steerTarget, STEER_PER_10MS * tickScale);
    cruiseSpeed = (int)(forwardPwm + 0.5f);
    // Mot ben giu base, ben trong giam dan. Khong khoa banh khi cua binh thuong.
    float maxTrim = forwardPwm - CURVE_INNER_MIN;
    if (maxTrim < 0) maxTrim = 0;
    float trim = min((float)fabs(steeringPwm), maxTrim);
    int inner = (int)(forwardPwm - trim + 0.5f);
    targetL = (steeringPwm < 0) ? inner : cruiseSpeed;
    targetR = (steeringPwm > 0) ? inner : cruiseSpeed;

    lastErr = err;
    lastLeftCmd = targetL;
    lastRightCmd = targetR;
    currentCommand = 'F';
  }
  else {
    if (adcHadLine) {
      adcHadLine = false;
      Serial.print(">> FIRST_LOSS ");
      printLineAdc();
    }
    unsigned long lost = now - lostLineTimer;
    lineZone = 'L';
    cruiseSpeed = LINE_BASE_SPEED;
    curveActive = true; // bat lai line phai qua giai doan on dinh, khong phong ngay
    centerPending = false;
    sidePending = false;
    filteredErr = lastErr;
    // Dong bo trang thai dieu khien voi muc phuc hoi, khong bat lai len 250.
    forwardPwm = min(forwardPwm, (float)LINE_BASE_SPEED);
    steeringPwm = 0;
    if (lost < HOLD_LAST_MS) {
      // Giu huong nhung KHONG giu PWM 190/200 trong 150ms mat line.
      targetL = min(lastLeftCmd, LINE_BASE_SPEED);
      targetR = min(lastRightCmd, LINE_BASE_SPEED);
    } else if (lost < SEARCH_MAX_MS) {
      if (lastErr >= 1.5f)       { targetL = SEARCH_OUTER_SPEED; targetR = 0; }
      else if (lastErr <= -1.5f) { targetL = 0; targetR = SEARCH_OUTER_SPEED; }
      else if (lost < HOLD_LAST_MS + CREEP_MS) {
        targetL = targetR = LOST_FORWARD_SPEED;
      } else { stopLineLost(); return; }
    } else { stopLineLost(); return; }
    currentCommand = 'F';
  }

  lineTargetL = targetL;
  lineTargetR = targetR;
  curL = slewTo(curL, targetL);
  curR = slewTo(curR, targetR);
  steerChassis(curL, curR);
}

void logCorner(const char* event) {
  Serial.print(">> CORNER "); Serial.print(event);
  Serial.print(" dir="); Serial.print(pendingTurnDir);
  Serial.print(" at="); Serial.print(millis());
  Serial.print(" elapsed="); Serial.println(millis() - turnTimer);
}

void cornerFail(const char* reason) {
  stopAllMotors(); curL = curR = lineTargetL = lineTargetR = 0;
  currentCommand = 'S'; turnState = CORNER_FAULT; lineZone = 'F';
  Serial.print(">> CORNER_FAULT: "); Serial.println(reason);
  Serial.println(">> Kiem tra vi tri xe. Dung M de thoat AUTO; M lan nua de thu lai.");
}

void resetLineTracking() {
  filteredErr = 0; forwardPwm = 0; steeringPwm = 0;
  sidePending = false; sideSign = 0;
  adcHadLine = false;
  curveActive = false;
  centerPending = false;
  lineZone = 'S';
  lineTargetL = lineTargetR = 0;
  logicalLineMask = 0;
  lineAbsError = 0.0f;
}

float moveToward(float value, float target, float step) {
  if (target > value + step) return value + step;
  if (target < value - step) return value - step;
  return target;
}

int slewTo(int cur, int target) {
  if (target > cur + SLEW_STEP) return cur + SLEW_STEP;
  if (target < cur - SLEW_STEP) return cur - SLEW_STEP;
  return target;
}

void stopLineLost() {
  stopAllMotors();
  curL = curR = 0; cruiseSpeed = LINE_BASE_SPEED; resetLineTracking();
  lineZone = 'L';
  currentCommand = 'S';
  if (!lostReported) {
    lostReported = true;
    Serial.println(">> TU HANH: KHONG THAY VACH -> DUNG (xem DATA:xxxxx, kiem tra LINE_DETECTED/do cao cam bien)");
  }
}

// ĐIỀU KHIỂN CẦU H BTS7960
void motor(int rpwm, int lpwm, int v) {
  v = constrain(v, -255, 255);
  if (v > 0) {
    analogWrite(lpwm, 0);
    analogWrite(rpwm, v);
  } else if (v < 0) {
    analogWrite(rpwm, 0);
    analogWrite(lpwm, -v);
  } else {
    analogWrite(rpwm, 0);
    analogWrite(lpwm, 0);
  }
}

void drive(int fl, int fr, int rl, int rr) {
  motor(D1_RPWM, D1_LPWM, -fl);
  motor(D2_RPWM, D2_LPWM,  fr);
  motor(D3_RPWM, D3_LPWM, -rl);
  motor(D4_RPWM, D4_LPWM,  rr);
}

void steerChassis(int speedLeft, int speedRight) {
  speedLeft  = constrain(speedLeft,  0, 255);
  speedRight = constrain(speedRight, 0, 255);
  drive(speedLeft, speedRight, speedLeft, speedRight);
}

void steerSigned(int speedLeft, int speedRight) {
  speedLeft  = constrain(speedLeft,  -255, 255);
  speedRight = constrain(speedRight, -255, 255);
  drive(speedLeft, speedRight, speedLeft, speedRight);
}

void applyMecanumChassis(char cmd, int spd) {
  switch (cmd) {
    case 'F': drive( spd,  spd,  spd,  spd); break;
    case 'B': drive(-spd, -spd, -spd, -spd); break;
    case 'L': drive(-spd,  spd,  spd, -spd); break;
    case 'R': drive( spd, -spd, -spd,  spd); break;
    case 'Q': drive(-spd,  spd, -spd,  spd); break;
    case 'E': drive( spd, -spd,  spd, -spd); break;
    case 'S':
    default:  stopAllMotors(); break;
  }
}

void stopAllMotors() {
  analogWrite(D1_RPWM, 0); analogWrite(D1_LPWM, 0);
  analogWrite(D2_RPWM, 0); analogWrite(D2_LPWM, 0);
  analogWrite(D3_RPWM, 0); analogWrite(D3_LPWM, 0);
  analogWrite(D4_RPWM, 0); analogWrite(D4_LPWM, 0);
}

void servoMove(int angle, unsigned long holdMs) {
  int us = map(angle, 0, 180, 600, 2400);
  unsigned long t0 = millis();
  do {
    digitalWrite(SERVO_PIN, HIGH);
    delayMicroseconds(us);
    digitalWrite(SERVO_PIN, LOW);
    delay(20);
  } while (millis() - t0 < holdMs);
}

bool checkEmergencyAbort() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'M' || c == 'm' || c == 'S' || c == 's' || c == ' ' || c == 'Z' || c == 'z') {
      toggleMode("NGAT KHAN CAP USB");
      return true;
    }
  }
  while (Serial2.available() > 0) {
    char c = Serial2.read();
    if (c == 'M' || c == 'm' || c == 'S' || c == 's' || c == ' ' || c == 'Z' || c == 'z') {
      toggleMode("NGAT KHAN CAP WIFI");
      return true;
    }
  }
  return false;
}

bool nonBlockingAction(char cmd, int spd, unsigned long durationMs) {
  unsigned long startT = millis();
  while (millis() - startT < durationMs) {
    if (checkEmergencyAbort()) return false;
    applyMecanumChassis(cmd, spd);
    delay(10);
  }
  return true;
}

// THUẬT TOÁN NÉ VẬT CẢN: DẠT RA -> TIẾN VƯỢT -> DẠT 90 ĐỘ BẮT LẠI LINE
void executeCorridorAvoidance() {
  isExecutingAvoidance = true;
  stopAllMotors();
  delay(150);

  long distSideLeft  = readUltrasonicCM(TRIG_LEFT,  ECHO_LEFT);
  long distSideRight = readUltrasonicCM(TRIG_RIGHT, ECHO_RIGHT);

  servoMove(135, 420);
  long distAngle135 = readUltrasonicCM(TRIG_FRONT, ECHO_FRONT);
  servoMove(45, 420);
  long distAngle45 = readUltrasonicCM(TRIG_FRONT, ECHO_FRONT);
  servoMove(90, 250);

  if (checkEmergencyAbort()) { isExecutingAvoidance = false; return; }

  if (distSideLeft  > 300) distSideLeft  = 300;
  if (distSideRight > 300) distSideRight = 300;
  if (distAngle135  > 300) distAngle135  = 300;
  if (distAngle45   > 300) distAngle45   = 300;

  char primaryDir, returnDir;
  if (distSideRight < 35 || distAngle45 < 30)       { primaryDir = 'L'; returnDir = 'R'; }
  else if (distSideLeft < 35 || distAngle135 < 30)  { primaryDir = 'R'; returnDir = 'L'; }
  else if (distSideRight >= distSideLeft)           { primaryDir = 'R'; returnDir = 'L'; }
  else                                              { primaryDir = 'L'; returnDir = 'R'; }

  // [1] DẠT NGANG RA NÉ VẬT CẢN
  Serial.println(">> NE CAN [1/3]: DAT NGANG RA");
  if (!nonBlockingAction(primaryDir, AVOID_STRAFE_SPD, AVOID_OUT_MS)) { isExecutingAvoidance = false; return; }
  stopAllMotors(); delay(150);

  // [2] TIẾN THẲNG SONG SONG VƯỢT VẬT CẢN
  Serial.println(">> NE CAN [2/3]: TIEN THANG SONG SONG");
  if (!nonBlockingAction('F', AVOID_FORWARD_SPEED, AVOID_FORWARD_MS)) { isExecutingAvoidance = false; return; }
  stopAllMotors(); delay(150);

  // [3] DẠT NGANG NGƯỢC LẠI ĐỂ VỀ LINE:
  Serial.println(">> NE CAN [3/3]: DAT NGANG QUAY LAI LINE");

  // Giai đoạn 3a: Dạt nhanh một đoạn cố định (1.8s) để thu hẹp khoảng cách ban đầu, tránh bắt nhiễu sàn
  if (!nonBlockingAction(returnDir, AVOID_STRAFE_SPD, AVOID_BACK_BLIND_MS)) { isExecutingAvoidance = false; return; }
  stopAllMotors();

  // Giai đoạn 3b: Dạt chậm và quét liên tục cụm 3 mắt giữa. Hễ bắt gặp line là ngắt ngay tức khắc!
  const int AVOID_RETURN_SPEED = 150;
  unsigned long t0 = millis();
  bool found = false;

  while (millis() - t0 < AVOID_BACK_SEARCH_MS) {
    if (checkEmergencyAbort()) { isExecutingAvoidance = false; return; }

    applyMecanumChassis(returnDir, AVOID_RETURN_SPEED);

    // Đọc trạng thái cụm 3 mắt giữa của thanh TCRT5000
    bool hitM  = (digitalRead(PIN_RAW_3) == LINE_DETECTED);
    bool hitL1 = (digitalRead(PIN_RAW_2) == LINE_DETECTED);
    bool hitR1 = (digitalRead(PIN_RAW_4) == LINE_DETECTED);

    // Chỉ cần 1 trong 3 mắt giữa chạm line đen là phanh đứng yên ngay lập tức
    if (hitM || hitL1 || hitR1) {
      stopAllMotors();
      found = true;
      break;
    }
    delay(5);
  }

  stopAllMotors();
  Serial.println(found ? ">> NE CAN: DA BAT DUNG CUM 3 MAT GIUA -> DUNG VA DO LINE" : ">> NE CAN: HET THOI GIAN TIM LINE");
  delay(150);

  currentCommand = 'S';
  isExecutingAvoidance = false;
  postAvoidanceBlindTimer = millis();
  lastErr = 0.0f;
  lastLeftCmd = lastRightCmd = LINE_BASE_SPEED; curL = curR = 0; cruiseSpeed = LINE_BASE_SPEED; resetLineTracking();
  lostLineTimer = millis();
  frontHits = 0;
}
