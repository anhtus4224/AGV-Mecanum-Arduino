// ==============================================================================
// DỰ ÁN XE MECANUM 4 BÁNH BTS7960: ĐỒNG BỘ JETSON NANO & APP WIFI & WEB 3D MAP
// BAN SUA 190 PWM: tach bam thang / giu cua; chua thu tren xe.
// PHIÊN BẢN GỐC (giữ chân, WiFi, né cản):
// 1. BỎ THƯ VIỆN SERVO -> GIẢI PHÓNG TIMER 5 -> PIN 44 BĂM PWM MƯỢT MÀ BÌNH THƯỜNG
// 2. DÒ LINE VI SAI P-D LIÊN TỤC: 4 BÁNH ĐỀU LĂN TIẾN, ÔM CUA MƯỢT NHƯ VIDEO 1 & 2
// 3. XỬ LÝ MẤT VẠCH 3 TẦNG: VƯỢT GỜ SÀN LỒI LÕM AN TOÀN, TỰ DỪNG HẲN KHI HẾT LINE
// 4. SIÊU ÂM ĐỌC XOAY VÒNG KHÔNG CHẶN VÒNG LẶP (TIMEOUT 8MS)
// 5. ĐÃ SỬA CHUẨN XÁC: DẠT VỀ ĐỦ HÀNH TRÌNH VÀ BẮT CỤM 3 MẮT GIỮA DỪNG NGAY
// ==============================================================================

// ------------------------------------------------------------------------------
// 1. CẤU HÌNH 8 CHÂN CHO 4 DRIVER BTS7960 (GIỮ NGUYÊN 100% PHẦN CỨNG)
// ------------------------------------------------------------------------------
const int D1_RPWM = 44;  // Trước - Trái (FL) - Kênh Lùi (Đã phục hồi băm PWM)
const int D1_LPWM = 3;   // Trước - Trái (FL) - Kênh Tiến (Pin 3 PWM)
const int D2_RPWM = 5;   // Trước - Phải (FR)
const int D2_LPWM = 9;   // Trước - Phải (FR)
const int D3_RPWM = 7;   // Sau - Trái (RL)
const int D3_LPWM = 8;   // Sau - Trái (RL)
const int D4_RPWM = 11;  // Sau - Phải (RR)
const int D4_LPWM = 12;  // Sau - Phải (RR)

// ------------------------------------------------------------------------------
// 2. CHÂN SERVO & NÚT BẤM VẬT LÝ & ĐO ĐIỆN ÁP
// ------------------------------------------------------------------------------
const int SERVO_PIN       = 10; // Servo điều khiển bằng xung mềm (Tránh chiếm Timer 5)
const int BUTTON_MODE_PIN = 31; // Nút bấm vật lý chuyển chế độ (INPUT_PULLUP)
const int VOLT_PIN        = A5; // Chân Analog đọc phân áp Pin/Ắc quy

// ------------------------------------------------------------------------------
// 3. CẤU HÌNH 4 CẢM BIẾN SIÊU ÂM
// ------------------------------------------------------------------------------
const int TRIG_FRONT = 22; const int ECHO_FRONT = 23;
const int TRIG_BACK  = 24; const int ECHO_BACK  = 25; 
const int TRIG_LEFT  = 26; const int ECHO_LEFT  = 27;
const int TRIG_RIGHT = 28; const int ECHO_RIGHT = 29;

const bool USE_ULTRASONIC = true;
const int  OBSTACLE_CM    = 18; // Ngưỡng phát hiện vật cản trước
const unsigned long SONAR_SLOT_MS = 40; // Đọc xoay vòng mỗi 40ms/cảm biến

// ------------------------------------------------------------------------------
// 4. CẤU HÌNH THANH DÒ LINE 5 MẮT TCRT5000 (A0 - A4)
// ------------------------------------------------------------------------------
const int PIN_RAW_1 = A0; // Mắt 1: Ngoài cùng trái (L2)
const int PIN_RAW_2 = A1; // Mắt 2: Giữa trái (L1)
const int PIN_RAW_3 = A2; // Mắt 3: Tâm giữa (M)
const int PIN_RAW_4 = A3; // Mắt 4: Giữa phải (R1)
const int PIN_RAW_5 = A4; // Mắt 5: Ngoài cùng phải (R2)

const bool REVERSE_SENSOR_ORDER = true;  // true: mắt A0 nằm bên PHẢI xe (đảo thứ tự). Xe đang NÉ vạch => đổi cờ này 
const int  LINE_DETECTED = HIGH; // Module của bạn: trên vạch đen LED TẮT => chân DO = HIGH (nền trắng = LOW)

// ------------------------------------------------------------------------------
// 5. THÔNG SỐ VẬN HÀNH & ĐIỀU TỐC P-D
// ------------------------------------------------------------------------------
const int WIFI_MAX_SPEED   = 240; 
const int AVOID_STRAFE_SPD = 160; 
const unsigned long AVOID_OUT_MS         = 3300;  // [1] dạt ngang RA
const unsigned long AVOID_FORWARD_MS     = 5400;  // [2] tiến thẳng song song vượt vật cản
const unsigned long AVOID_BACK_BLIND_MS  = 2300;  // [3a] dạt ngang NGƯỢC LẠI cố định (vượt khoảng cách xa)
const unsigned long AVOID_BACK_SEARCH_MS = 4500;  // [3b] tiếp tục dạt dò tìm line tối đa

// --- Do line: thu 190 truoc; chi doi LINE_FAST_SPEED len 200 sau khi thu xe ---
const int LINE_BASE_SPEED = 120;
const int LINE_FAST_SPEED = 190;
const int RAMP_UP_STEP = 2; // moi chu ky dieu khien, khong nhay thang len 190
const unsigned long CENTER_HOLD_MS = 120; // chap nhan lech nhe trong cum giua
const int STRAIGHT_TRIM_MAX = 20; // a=1: giam 10; a=2: giam 20 PWM
const float SIDE_CURVE_MIN_A = 1.5f;
const unsigned long SIDE_CURVE_MS = 100; // lech cung phia keo dai -> vao cua
const unsigned long CURVE_EXIT_MS = 100; // ve gan tam on dinh moi thoat cua
const int LOST_FORWARD_SPEED = 100;
const int SEARCH_OUTER_SPEED = 160;
// Giu nguyen bang cua da co tren xe, CHI dung trong trang thai cua.
const int INNER_TBL[5] = {120, 0, 0, 0, 0};
const int OUTER_TBL[5] = {120, 190, 235, 255, 255};
const int SLEW_STEP = 40;
// Mac dinh tat xung de tranh pha phanh ca 4 banh 25ms.
// Neu bat lai, xung chi duoc phep trong trang thai cua, a >= 2.5.
const bool ENABLE_TURN_PULSE = false;
const float PULSE_MIN_A = 2.5f;
const unsigned long TURN_PULSE_ON_MS = 40;
const unsigned long TURN_PULSE_OFF_MS = 25;
const bool ENABLE_90_TURN = false;
const unsigned long CONTROL_PERIOD_MS = 10;

// --- Góc vuông 90 độ ---
const int TURN_90_SPEED        = 135;
const int RUNOUT_SPEED         = 105;
const unsigned long RUNOUT_MS       = 100; 
const unsigned long BRAKE_MS        = 50;  
const unsigned long MIN_TURN_MS     = 140; 
const unsigned long TURN_TIMEOUT_MS = 900;
const unsigned long SETTLE_MS       = 40;

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

enum TurnState { IDLE_LINE, RUNOUT_90, BRAKE_90, TURNING_90, SETTLE_90 };
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
bool wasPulsing = false;
unsigned long pulseStart = 0;
int cruiseSpeed = LINE_BASE_SPEED;      
unsigned long lastDeviationTime = 0;
bool curveActive = false;
bool sidePending = false;
int sideDirection = 0;
unsigned long sideSince = 0;
bool centerPending = false;
unsigned long centerSince = 0;
char lineZone = 'S'; // S: thang, C: cua, L: mat line, X: hai mat ria cung bat
float lineAbsError = 0.0f;    

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
int slewTo(int cur, int target);
int lerpTbl(const int* t, float a, int row0);
float readBatteryVoltage();
void sendTelemetry();
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

  Serial.println(">> [AGV READY] - DA SUA CHUAN BUOC 3 DAT NGANG HOI QUY VE LINE");
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
    Serial.print(">> HB up="); Serial.print(millis() / 1000);
    Serial.print("s mode="); Serial.print(isLineTrackingMode ? "AUTO" : "MANUAL");
    Serial.print(" rxUSB="); Serial.print(rxUSB);
    Serial.print(" rxESP="); Serial.print(rxESP);
    Serial.print(" rejESP="); Serial.print(rxRejected);
    Serial.print(" last='"); Serial.print(lastRx); Serial.print("'");
    Serial.print(" cruise="); Serial.print(cruiseSpeed);
    Serial.print(" zone="); Serial.print(lineZone);
    Serial.print(" a="); Serial.print(lineAbsError, 2);
    Serial.print(" L/R="); Serial.print(curL); Serial.print('/'); Serial.println(curR);
  }

  // Bắn Telemetry chu kỳ 150ms cho Web 3D
  if (millis() - lastTelemetryTime > 150) {
    sendTelemetry();
    lastTelemetryTime = millis();
  }
}

// ==============================================================================
// XỬ LÝ LỆNH TRUYỀN THÔNG (TÁCH BIỆT 'R' ĐỂ KHÔNG XUNG ĐỘT)
// ==============================================================================
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
  lastLeftCmd = lastRightCmd = LINE_BASE_SPEED; curL = curR = 0; wasPulsing = false; cruiseSpeed = LINE_BASE_SPEED; resetLineTracking();
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
  if (millis() - lastPacketTime > FAILSAFE_MS) {
    if (currentCommand != 'S') {
      currentCommand = 'S';
      stopAllMotors();
    }
  }
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

// ==============================================================================
// THUẬT TOÁN TỰ HÀNH VI SAI P-D & BỘ LỌC MẤT VẠCH 3 TẦNG
// ==============================================================================
void handleLineAndObstacleMode() {
  unsigned long now = millis();

  if (USE_ULTRASONIC && turnState == IDLE_LINE && frontHits >= 2) {
    frontHits = 0;
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

  switch (turnState) {
    case RUNOUT_90:
      steerChassis(RUNOUT_SPEED, RUNOUT_SPEED);
      if (now - turnTimer >= RUNOUT_MS) {
        stopAllMotors();
        turnState = BRAKE_90;
        turnTimer = now;
      }
      return;

    case BRAKE_90:
      if (now - turnTimer >= BRAKE_MS) {
        turnState = TURNING_90;
        turnTimer = now;
      }
      return;

    case TURNING_90: {
      applyMecanumChassis(pendingTurnDir, TURN_90_SPEED);
      unsigned long dur = now - turnTimer;
      bool leadSensor = (pendingTurnDir == 'E') ? r1 : l1;
      bool caught   = (m || leadSensor) && (dur > MIN_TURN_MS);
      bool timedOut = (dur > TURN_TIMEOUT_MS);
      if (caught || timedOut) {
        stopAllMotors();
        turnState = SETTLE_90;
        turnTimer = now;
      }
      return;
    }

    case SETTLE_90:
      if (now - turnTimer >= SETTLE_MS) {
        turnState = IDLE_LINE;
        lastErr = 0.0f;
        lastLeftCmd = lastRightCmd = LINE_BASE_SPEED; curL = curR = 0; wasPulsing = false; cruiseSpeed = LINE_BASE_SPEED; resetLineTracking();
        lostLineTimer = now;
      }
      return;

    default: break;
  }

  if (now - lastControlTime < CONTROL_PERIOD_MS) return;
  lastControlTime = now;

  if (ENABLE_90_TURN) {
    bool canDetect90 = (now - postAvoidanceBlindTimer > 400);
    bool rightCorner = r2 && r1 && m && !l2;
    bool leftCorner  = l2 && l1 && m && !r2;
    if (canDetect90 && (rightCorner || leftCorner)) {
      if (++cornerCount >= 2) {
        cornerCount = 0;
        pendingTurnDir = rightCorner ? 'E' : 'Q';
        lastErr = rightCorner ? 4.0f : -4.0f;
        turnState = RUNOUT_90;
        turnTimer = now;
        return;
      }
    } else {
      cornerCount = 0;
    }
  }

  int cnt = (int)l2 + (int)l1 + (int)m + (int)r1 + (int)r2;
  int targetL, targetR;
  bool needPulse = false;

  if (cnt > 0) {
    lostReported = false;
    lostLineTimer = now;
    float sum = -4.0f * l2 - 2.0f * l1 + 2.0f * r1 + 4.0f * r2;
    float err = sum / cnt;
    float a = fabs(err);
    lineAbsError = a;
    const bool edge = l2 || r2;
    const bool ambiguous = l2 && r2;
    const int direction = (err > 0.01f) ? 1 : ((err < -0.01f) ? -1 : 0);

    // Mat ria: vao cua ngay. Mat ben lech cung phia lau: cung phai giam toc.
    if (edge) {
      curveActive = true;
      sidePending = false;
    } else if (a >= SIDE_CURVE_MIN_A) {
      if (!sidePending || sideDirection != direction) {
        sidePending = true;
        sideDirection = direction;
        sideSince = now;
      }
      if (now - sideSince >= SIDE_CURVE_MS) curveActive = true;
    } else {
      sidePending = false;
    }

    // Hysteresis: khong tang toc lai ngay khi mat ria vua roi vach.
    if (curveActive && !edge && a <= 1.0f) {
      if (!centerPending) { centerPending = true; centerSince = now; }
      if (now - centerSince >= CURVE_EXIT_MS) {
        curveActive = false;
        centerPending = false;
        lastDeviationTime = now;
      }
    } else {
      centerPending = false;
    }

    if (ambiguous) {
      // Hai ria cung bat: khong lay trung binh err=0 de phong nhanh.
      lineZone = 'X';
      cruiseSpeed = LINE_BASE_SPEED;
      lastDeviationTime = now;
      targetL = targetR = LINE_BASE_SPEED;
    } else if (curveActive) {
      lineZone = 'C';
      cruiseSpeed = LINE_BASE_SPEED;
      lastDeviationTime = now;
      int inner = lerpTbl(INNER_TBL, a, LINE_BASE_SPEED);
      int outer = lerpTbl(OUTER_TBL, a, LINE_BASE_SPEED);
      inner = constrain(inner, 0, 255);
      if (direction > 0)      { targetL = outer; targetR = inner; }
      else if (direction < 0) { targetL = inner; targetR = outer; }
      else                   { targetL = targetR = LINE_BASE_SPEED; }
      needPulse = (a >= PULSE_MIN_A);
    } else {
      lineZone = 'S';
      if (now - lastDeviationTime >= CENTER_HOLD_MS) {
        cruiseSpeed = min(cruiseSpeed + RAMP_UP_STEP, LINE_FAST_SPEED);
      }
      int trim = constrain((int)(a * (STRAIGHT_TRIM_MAX / 2.0f) + 0.5f),
                           0, STRAIGHT_TRIM_MAX);
      targetL = cruiseSpeed - ((direction < 0) ? trim : 0);
      targetR = cruiseSpeed - ((direction > 0) ? trim : 0);
      // Vung nay khong dung bang cua va khong bat xung.
    }

    lastErr = err;
    lastLeftCmd = targetL;
    lastRightCmd = targetR;
    currentCommand = 'F';
  }
  else {
    unsigned long lost = now - lostLineTimer;
    lineZone = 'L';
    cruiseSpeed = LINE_BASE_SPEED;
    lastDeviationTime = now;
    curveActive = true; // bat lai line phai qua giai doan on dinh, khong phong ngay
    centerPending = false;
    sidePending = false;
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
    needPulse = false; // tim line lien tuc, khong phanh theo xung
    currentCommand = 'F';
  }

  if (ENABLE_TURN_PULSE && needPulse) {
    if (!wasPulsing) { pulseStart = now; wasPulsing = true; }
    unsigned long ph = (now - pulseStart) % (TURN_PULSE_ON_MS + TURN_PULSE_OFF_MS);
    if (ph < TURN_PULSE_ON_MS) { curL = targetL; curR = targetR; }
    else                       { curL = 0;       curR = 0;       }
  } else {
    wasPulsing = false;
    curL = slewTo(curL, targetL);
    curR = slewTo(curR, targetR);
  }
  steerChassis(curL, curR);
}

void resetLineTracking() {
  curveActive = false;
  sidePending = false;
  sideDirection = 0;
  centerPending = false;
  lastDeviationTime = millis();
  lineZone = 'S';
  lineAbsError = 0.0f;
}

int lerpTbl(const int* t, float a, int row0) {
  if (a <= 0.0f) return row0;
  if (a >= 4.0f) return t[4];
  int i = (int)a;
  float f = a - i;
  int v0 = (i == 0) ? row0 : t[i];
  return v0 + (int)((t[i + 1] - v0) * f);
}

int slewTo(int cur, int target) {
  if (target > cur + SLEW_STEP) return cur + SLEW_STEP;
  if (target < cur - SLEW_STEP) return cur - SLEW_STEP;
  return target;
}

void stopLineLost() {
  stopAllMotors();
  curL = curR = 0; wasPulsing = false; cruiseSpeed = LINE_BASE_SPEED; resetLineTracking();
  lineZone = 'L';
  currentCommand = 'S';
  if (!lostReported) {
    lostReported = true;
    Serial.println(">> TU HANH: KHONG THAY VACH -> DUNG (xem DATA:xxxxx, kiem tra LINE_DETECTED/do cao cam bien)");
  }
}

// ==============================================================================
// ĐIỀU KHIỂN CẦU H BTS7960
// ==============================================================================
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

// ==============================================================================
// THUẬT TOÁN NÉ VẬT CẢN: DẠT RA -> TIẾN VƯỢT -> DẠT 90 ĐỘ BẮT LẠI LINE
// ==============================================================================
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
  if (!nonBlockingAction('F', LINE_BASE_SPEED, AVOID_FORWARD_MS)) { isExecutingAvoidance = false; return; }
  stopAllMotors(); delay(150);

  // [3] DẠT NGANG NGƯỢC LẠI ĐỂ VỀ LINE:
  Serial.println(">> NE CAN [3/3]: DAT NGANG QUAY LAI LINE");
  
  // Giai đoạn 3a: Dạt nhanh một đoạn cố định (1.8s) để thu hẹp khoảng cách ban đầu, tránh bắt nhiễu sàn
  if (!nonBlockingAction(returnDir, AVOID_STRAFE_SPD, AVOID_BACK_BLIND_MS)) { isExecutingAvoidance = false; return; }
  delay(50);

  // Giai đoạn 3b: Dạt chậm và quét liên tục cụm 3 mắt giữa. Hễ bắt gặp line là ngắt ngay tức khắc!
  const int AVOID_RETURN_SPEED = 120; 
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
  lastLeftCmd = lastRightCmd = LINE_BASE_SPEED; curL = curR = 0; wasPulsing = false; cruiseSpeed = LINE_BASE_SPEED; resetLineTracking();
  lostLineTimer = millis();
  frontHits = 0;
}