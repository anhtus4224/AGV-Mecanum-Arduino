#include <Arduino.h>
#include "VectorMotion.h"
#include <stdio.h>
// AGV_CHUANDET_90_V2
// Dua truc tiep tren ZIP chuandet.
// CHUA THU TREN XE / CHUA HIEU CHUAN GOC90.
// Runout608ms =1216*15/30 theo phep thu lo thuc te.

// 1. CHAN MOTOR
const int D1_RPWM = 44;
const int D1_LPWM = 3;
const int D2_RPWM = 5;
const int D2_LPWM = 9;
const int D3_RPWM = 7;
const int D3_LPWM = 8;
const int D4_RPWM = 11;
const int D4_LPWM = 12;

// 2. SERVO, NUT BAM, DIEN AP
const int SERVO_PIN = 10;
const int BUTTON_MODE_PIN = 31;
const int VOLT_PIN = A5;

// 3. SIEU AM
const int TRIG_FRONT = 22;
const int ECHO_FRONT = 23;
const int TRIG_BACK = 24;
const int ECHO_BACK = 25;
const int TRIG_LEFT = 26;
const int ECHO_LEFT = 27;
const int TRIG_RIGHT = 28;
const int ECHO_RIGHT = 29;

const bool USE_ULTRASONIC = true;
const int OBSTACLE_CM = 18;
const unsigned long SONAR_SLOT_MS = 40;

// 4. CAM BIEN LINE
const int PIN_RAW_1 = A0;
const int PIN_RAW_2 = A1;
const int PIN_RAW_3 = A2;
const int PIN_RAW_4 = A3;
const int PIN_RAW_5 = A4;

const bool REVERSE_SENSOR_ORDER = false;
const int LINE_DETECTED = LOW;

// 5. WIFI VA NE VAT CAN
const int WIFI_MAX_SPEED = 255;
const int AVOID_STRAFE_SPD = 160;
const int AVOID_FORWARD_SPEED = 200;

const unsigned long AVOID_OUT_MS = 2900;
const unsigned long AVOID_FORWARD_MS = 3500;
const unsigned long AVOID_BACK_BLIND_MS = 2000;
const unsigned long AVOID_BACK_SEARCH_MS = 4500;

// 6. DO LINE THONG THUONG
const int LINE_BASE_SPEED = 120;
const int LINE_FAST_SPEED = 255;
const int STRAIGHT_TRIM_MAX = 20;

const unsigned long CURVE_EXIT_MS = 60;
const int CURVE_OUTER_MAX = 190;

const int LOST_FORWARD_SPEED = 100;
const int SEARCH_OUTER_SPEED = 160;

const int INNER_TBL[5] = {120, 0, 0, 0, 0};
const int OUTER_TBL[5] = {120, 190, 235, 255, 255};
const int SLEW_STEP = 40;

const bool ENABLE_TURN_PULSE = false;
const float PULSE_MIN_A = 2.5f;
const unsigned long TURN_PULSE_ON_MS = 40;
const unsigned long TURN_PULSE_OFF_MS = 25;

const bool ENABLE_90_TURN = true;
const unsigned long CONTROL_PERIOD_MS = 10;

// 7. GOC VUONG
// V1 tienbu1216ms lam front vuot khoang30cm.
// Muc tieu15cm -> moc thu moi608ms.
const unsigned long RUNOUT_RIGHT_MS = 608;
const unsigned long RUNOUT_LEFT_MS = 608;

const int RUNOUT_SPEED = 255;
const int TURN_RIGHT_SPEED = 255;
const int TURN_LEFT_SPEED = 255;

// Chi chong bat lai qua som, KHONG phai phep do90do.
const unsigned long MIN_TURN_MS = 200;

// Gioi han tim line, KHONG phai thoi gian xoay90do.
const unsigned long TURN_TIMEOUT_MS = 2200;

// Line on dinh de tu chay lai sau loi tim line.
const unsigned long CORNER_RESUME_MS = 120;

// Kiem tra sau khi ngat PWM.
const unsigned long SETTLE_MS = 80;

// Chong nhan lai cung mot goc.
const unsigned long CORNER_LOCK_MS = 1200;

// Timeout rieng lenh xoay WiFi Q/E.
const unsigned long MANUAL_TURN_TIMEOUT_MS = 180;

// 8. MAT LINE
const unsigned long HOLD_LAST_MS = 150;
const unsigned long CREEP_MS = 300;
const unsigned long SEARCH_MAX_MS = 1200;

// Timeout cac lenh lai tay khac Q/E.
const int FAILSAFE_MS = 700;

// 9. DEBUG VA NUT BAM
const unsigned long MODE_TOGGLE_LOCK_MS = 800;
const bool DEBUG_HEARTBEAT = true;
const bool DEBUG_RX = true;
const int DEBOUNCE_DELAY = 80;

enum TurnState {
  IDLE_LINE,
  RUNOUT_90,
  BRAKE_90,
  TURNING_90,
  SETTLE_90,
  CORNER_FAULT
};

TurnState turnState = IDLE_LINE;

bool isLineTrackingMode = false;
bool isExecutingAvoidance = false;

char currentCommand = 'S';
char pendingTurnDir = 'E';

unsigned long lastPacketTime = 0;
unsigned long turnTimer = 0;
unsigned long lostLineTimer = 0;
unsigned long postAvoidanceBlindTimer = 0;
unsigned long lastTelemetryTime = 0;
unsigned long lastSonarTime = 0;
unsigned long lastControlTime = 0;
unsigned long lastToggleTime = 0;

bool lostReported = false;
unsigned long lastHeartbeat = 0;

unsigned long rxUSB = 0;
unsigned long rxESP = 0;
unsigned long rxRejected = 0;
char lastRx = ' ';

int buttonState = HIGH;
int lastButtonState = HIGH;
unsigned long lastDebounceTime = 0;

long distF = 120;
long distB = 180;
long distL = 75;
long distR = 80;

int frontHits = 0;
int sonarSlot = 0;
int cornerCount = 0;

float lastErr = 0.0f;

int lastLeftCmd = LINE_BASE_SPEED;
int lastRightCmd = LINE_BASE_SPEED;

int curL = 0;
int curR = 0;

bool wasPulsing = false;
unsigned long pulseStart = 0;

int cruiseSpeed = LINE_BASE_SPEED;

bool curveActive = false;
bool centerPending = false;
unsigned long centerSince = 0;

// S: thang, C: cua thuong, L: mat line,
// X: hai ria, T: goc90, F: loi goc90.
char lineZone = 'S';

// Bit0=L2, bit1=L1, bit2=M, bit3=R1, bit4=R2.
unsigned int logicalLineMask = 0;

int lineTargetL = 0;
int lineTargetR = 0;

bool adcHadLine = false;
float lineAbsError = 0.0f;

unsigned long lastCornerFinished = 0;
unsigned long cornerSampleTime = 0;

bool cornerBlankSeen = false;
bool cornerSideSeen = false;

bool cornerAutoResume = false;
bool cornerResumePending = false;
unsigned long cornerResumeSince = 0;

uint8_t cornerBlankCount = 0;
uint8_t cornerCenterCount = 0;

// VECTOR1 integration. Old line/corner implementation below is preserved.
VmAvoid vectorAvoid;
int actualWheels[4]={0,0,0,0},vectorTarget[4]={0,0,0,0};
uint32_t vectorTickAt=0,motionAt=0,motionSeq=0,hostAt=0,driveAt=0;
uint32_t hostSession=0,hostSequence=0;bool hostOwned=false,vectorManual=false;
VmRange rangeF={999,0},rangeB={999,0},rangeL={999,0},rangeR={999,0};
int scanLeft=999,scanRight=999,scanSideL=999,scanSideR=999,servoAngle=90;
uint32_t servoAt=0;char frameBuffer[110];uint8_t frameLength=0;bool frameActive=false,frameOverflow=false;
void vectorService();void vectorRead();void vectorStop();void vectorMotion();
void vectorBeginAvoidance();void vectorSonar();void vectorApply(int f,int s,int rot,int cap);

// KHAI BAO HAM
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
void finishCorner();

int slewTo(int cur, int target);
int lerpTbl(const int* t, float a, int row0);

float readBatteryVoltage();
void sendTelemetry();
void printLineAdc();

void checkModeButton();
void readSerialCommands();
void parseSingleChar(char c, char src);

void handleManualMode();
void handleLineAndObstacleMode();

bool nonBlockingAction(
  char cmd,
  int spd,
  unsigned long durationMs
);

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600);

  pinMode(D1_RPWM, OUTPUT);
  pinMode(D1_LPWM, OUTPUT);
  pinMode(D2_RPWM, OUTPUT);
  pinMode(D2_LPWM, OUTPUT);
  pinMode(D3_RPWM, OUTPUT);
  pinMode(D3_LPWM, OUTPUT);
  pinMode(D4_RPWM, OUTPUT);
  pinMode(D4_LPWM, OUTPUT);

  stopAllMotors();

  pinMode(BUTTON_MODE_PIN, INPUT_PULLUP);
  pinMode(SERVO_PIN, OUTPUT);

  servoMove(90, 300);

  pinMode(TRIG_FRONT, OUTPUT);
  pinMode(ECHO_FRONT, INPUT);
  pinMode(TRIG_BACK, OUTPUT);
  pinMode(ECHO_BACK, INPUT);
  pinMode(TRIG_LEFT, OUTPUT);
  pinMode(ECHO_LEFT, INPUT);
  pinMode(TRIG_RIGHT, OUTPUT);
  pinMode(ECHO_RIGHT, INPUT);

  pinMode(PIN_RAW_1, INPUT);
  pinMode(PIN_RAW_2, INPUT);
  pinMode(PIN_RAW_3, INPUT);
  pinMode(PIN_RAW_4, INPUT);
  pinMode(PIN_RAW_5, INPUT);

  pinMode(VOLT_PIN, INPUT);

  isLineTrackingMode = false;
  currentCommand = 'S';
  lastPacketTime = millis();

  Serial.print(">> [AGV_CHUANDET_90_V2 READY] fast=");
  Serial.print(LINE_FAST_SPEED);
  Serial.print(" wifi=");
  Serial.print(WIFI_MAX_SPEED);
  Serial.print(" runoutR/L=");
  Serial.print(RUNOUT_RIGHT_MS);
  Serial.print('/');
  Serial.print(RUNOUT_LEFT_MS);
  Serial.println(" ms; spin255; LOW; order=0");
}

void loop() {
  checkModeButton();
  vectorRead();
  vectorService();
  if (vectorAvoid.phase == VmAvoid::OFF) updateSonar();
  else vectorSonar();
  vectorMotion();

  if (vectorAvoid.phase != VmAvoid::OFF) {
    // vectorService owns motor output until handoff or an explicit STOP.
  } else if (vectorManual) {
    // Timed vector commands are serviced above.
  } else if (isLineTrackingMode) {
    handleLineAndObstacleMode();
  } else {
    handleManualMode();
  }

  if (DEBUG_HEARTBEAT && millis() - lastHeartbeat > 1000) {
    lastHeartbeat = millis();

    Serial.print(">> HB fw=AGV_CHUANDET_90_V2 up=");
    Serial.print(millis() / 1000);

    Serial.print("s mode=");
    Serial.print(isLineTrackingMode ? "AUTO" : "MANUAL");

    Serial.print(" rxUSB=");
    Serial.print(rxUSB);
    Serial.print(" rxESP=");
    Serial.print(rxESP);
    Serial.print(" rejESP=");
    Serial.print(rxRejected);

    Serial.print(" last='");
    Serial.print(lastRx);
    Serial.print("'");

    Serial.print(" cruise=");
    Serial.print(cruiseSpeed);
    Serial.print(" zone=");
    Serial.print(lineZone);
    Serial.print(" a=");
    Serial.print(lineAbsError, 2);
    Serial.print(" turnState=");
    Serial.print((int)turnState);

    Serial.print(" bits=");
    for (int bit = 0; bit < 5; ++bit) {
      Serial.print((logicalLineMask >> bit) & 1);
    }

    Serial.print(" target=");
    Serial.print(lineTargetL);
    Serial.print('/');
    Serial.print(lineTargetR);

    Serial.print(" L/R=");
    Serial.print(curL);
    Serial.print('/');
    Serial.println(curR);
  }

  if (millis() - lastTelemetryTime > 150) {
    sendTelemetry();
    lastTelemetryTime = millis();
  }
}

// LENH USB / WIFI
void parseSingleChar(char c, char src) {
  if (DEBUG_RX) {
    Serial.print(">> RX[");
    Serial.print(src);
    Serial.print("]: '");

    if (c >= 32 && c < 127) {
      Serial.print(c);
    } else {
      Serial.print('?');
    }

    Serial.print("' 0x");
    Serial.print((int)(unsigned char)c, HEX);
    Serial.print(" @");
    Serial.println(millis());
  }

  if (src == 'U') {
    rxUSB++;
  } else {
    rxESP++;
  }

  if (c != '\r' && c != '\n') {
    lastRx = c;
  }

  if (c == '\r' || c == '\n' || c == 0) {
    return;
  }

  if (src == 'E' && !strchr("FBLRQESMZ", c)) {
    rxRejected++;
    return;
  }

  if (c == 'M' || c == 'm' || c == 'X' || c == 'x') {
    if (millis() - lastToggleTime < MODE_TOGGLE_LOCK_MS) {
      return;
    }

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
    if (!strchr("FWwBsSLAaRDdQqEe", c)) {
      return;
    }

    isLineTrackingMode = false;
    turnState = IDLE_LINE;

    stopAllMotors();
    Serial.println(">> PHIM LAI TAY -> THOAT TU HANH, VE LAI TAY");
  }

  if (c == 'F' || c == 'W' || c == 'w') {
    currentCommand = 'F';

  } else if (c == 'B' || c == 's') {
    currentCommand = 'B';

  } else if (c == 'L' || c == 'A' || c == 'a') {
    currentCommand = 'L';

  } else if (c == 'R' || c == 'D' || c == 'd') {
    currentCommand = 'R';

  } else if (c == 'Q' || c == 'q') {
    currentCommand = 'Q';

  } else if (c == 'E' || c == 'e') {
    currentCommand = 'E';

  } else if (c == 'S' || c == ' ') {
    currentCommand = 'S';
    stopAllMotors();

  } else {
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
  while (Serial.available() > 0) {
    parseSingleChar(Serial.read(), 'U');
  }

  while (Serial2.available() > 0) {
    parseSingleChar(Serial2.read(), 'E');
  }
}

void toggleMode(const char* source) {
  vectorManual=false; vectorAvoid.phase=VmAvoid::OFF;
  isLineTrackingMode = !isLineTrackingMode;
  turnState = IDLE_LINE;
  currentCommand = 'S';

  stopAllMotors();

  lastErr = 0.0f;
  lastLeftCmd = lastRightCmd = LINE_BASE_SPEED;

  curL = curR = 0;
  wasPulsing = false;
  cruiseSpeed = LINE_BASE_SPEED;

  resetLineTracking();

  lostLineTimer = millis();
  cornerCount = 0;
  frontHits = 0;
  lostReported = false;
  lastToggleTime = millis();

  Serial.print(">> [");
  Serial.print(source);
  Serial.print("]: CHUYEN SANG -> ");

  Serial.println(
    isLineTrackingMode ? "TU HANH DO LINE" : "LAI TAY (MANUAL)"
  );
}

void checkModeButton() {
  int reading = digitalRead(BUTTON_MODE_PIN);

  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > DEBOUNCE_DELAY) {
    if (reading != buttonState) {
      buttonState = reading;

      if (buttonState == LOW) {
        toggleMode("NUT BAM VAT LY PIN 31");
      }
    }
  }

  lastButtonState = reading;
}

void handleManualMode() {
  unsigned long timeout =
      (currentCommand == 'E' || currentCommand == 'Q')
      ? MANUAL_TURN_TIMEOUT_MS
      : FAILSAFE_MS;

  if (millis() - lastPacketTime > timeout &&
      currentCommand != 'S') {

    currentCommand = 'S';
    stopAllMotors();

    Serial.println(">> MANUAL_TIMEOUT: PWM=0");
  }
}

// ADC doc ke tiep, khong dong thoi voi DATA/digitalRead.
void printLineAdc() {
  const uint8_t pins[5] = {A0, A1, A2, A3, A4};
  int values[5];

  for (uint8_t i = 0; i < 5; ++i) {
    analogRead(pins[i]);
    values[i] = analogRead(pins[i]);
  }

  Serial.print("ADC5:");

  for (uint8_t i = 0; i < 5; ++i) {
    if (i) {
      Serial.print(',');
    }

    Serial.print(values[i]);
  }

  Serial.println();
}

void sendTelemetry() {
  bool s1 = digitalRead(PIN_RAW_1) == LINE_DETECTED;
  bool s2 = digitalRead(PIN_RAW_2) == LINE_DETECTED;
  bool s3 = digitalRead(PIN_RAW_3) == LINE_DETECTED;
  bool s4 = digitalRead(PIN_RAW_4) == LINE_DETECTED;
  bool s5 = digitalRead(PIN_RAW_5) == LINE_DETECTED;

  const char* act = "STOP";

  if (currentCommand == 'F') {
    act = "FORWARD";
  } else if (currentCommand == 'B') {
    act = "BACKWARD";
  } else if (currentCommand == 'L') {
    act = "STRAFE_LEFT";
  } else if (currentCommand == 'R') {
    act = "STRAFE_RIGHT";
  } else if (currentCommand == 'Q') {
    act = "ROTATE_LEFT";
  } else if (currentCommand == 'E') {
    act = "ROTATE_RIGHT";
  }

  Serial.print("DATA:");
  Serial.print(s1 ? '1' : '0');
  Serial.print(s2 ? '1' : '0');
  Serial.print(s3 ? '1' : '0');
  Serial.print(s4 ? '1' : '0');
  Serial.print(s5 ? '1' : '0');
  Serial.print(",");
  Serial.print(act);
  Serial.print(",");
  Serial.println(readBatteryVoltage(), 2);

  Serial.print("SONAR:");
  Serial.print(distF);
  Serial.print(",");
  Serial.print(distB);
  Serial.print(",");
  Serial.print(distL);
  Serial.print(",");
  Serial.println(distR);

  printLineAdc();
}

float readBatteryVoltage() {
  int raw = analogRead(VOLT_PIN);

  if (raw < 30) {
    return 12.4;
  }

  return (float)raw * (5.0 / 1023.0) * 4.0;
}

long readUltrasonicCM(int trigPin, int echoPin) {
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH, 8000);

  if (duration <= 0) {
    return 999;
  }

  return duration * 0.034 / 2;
}

void updateSonar() {
  if (millis() - lastSonarTime < SONAR_SLOT_MS) {
    return;
  }

  lastSonarTime = millis();

  switch (sonarSlot) {
    case 0:
    case 2:
    case 4:
      distF = readUltrasonicCM(TRIG_FRONT, ECHO_FRONT);
      rangeF.cm=distF; rangeF.at=millis();

      if (distF > 3 && distF <= OBSTACLE_CM) {
        if (frontHits < 100) {
          frontHits++;
        }
      } else {
        frontHits = 0;
      }
      break;

    case 1:
      distL = readUltrasonicCM(TRIG_LEFT, ECHO_LEFT);
      rangeL.cm=distL; rangeL.at=millis();
      break;

    case 3:
      distR = readUltrasonicCM(TRIG_RIGHT, ECHO_RIGHT);
      rangeR.cm=distR; rangeR.at=millis();
      break;

    case 5:
      distB = readUltrasonicCM(TRIG_BACK, ECHO_BACK);
      rangeB.cm=distB; rangeB.at=millis();
      break;
  }

  sonarSlot = (sonarSlot + 1) % 6;
}

// DO LINE VA CHUYEN GOC90
void handleLineAndObstacleMode() {
  unsigned long now = millis();

  if (turnState == IDLE_LINE && rangeF.valid(now) && rangeF.cm <= 60) {
    vectorBeginAvoidance(); return;
  }

  if (USE_ULTRASONIC && frontHits >= 2) {
    frontHits = 0;

    if (turnState != IDLE_LINE) {
      cornerFail("OBSTACLE_DURING_CORNER");
      return;
    }

    stopAllMotors();
    vectorBeginAvoidance();
    return;
  }

  bool l2, l1, m, r1, r2;

  if (!REVERSE_SENSOR_ORDER) {
    l2 = digitalRead(PIN_RAW_1) == LINE_DETECTED;
    l1 = digitalRead(PIN_RAW_2) == LINE_DETECTED;
    m  = digitalRead(PIN_RAW_3) == LINE_DETECTED;
    r1 = digitalRead(PIN_RAW_4) == LINE_DETECTED;
    r2 = digitalRead(PIN_RAW_5) == LINE_DETECTED;

  } else {
    l2 = digitalRead(PIN_RAW_5) == LINE_DETECTED;
    l1 = digitalRead(PIN_RAW_4) == LINE_DETECTED;
    m  = digitalRead(PIN_RAW_3) == LINE_DETECTED;
    r1 = digitalRead(PIN_RAW_2) == LINE_DETECTED;
    r2 = digitalRead(PIN_RAW_1) == LINE_DETECTED;
  }

  // TRANG THAI CHUYEN GOC
  if (turnState != IDLE_LINE) {
    if (now - cornerSampleTime < CONTROL_PERIOD_MS) {
      return;
    }

    cornerSampleTime = now;

    logicalLineMask =
        (unsigned int)l2 |
        ((unsigned int)l1 << 1) |
        ((unsigned int)m << 2) |
        ((unsigned int)r1 << 3) |
        ((unsigned int)r2 << 4);

    // CHO BAT LAI LINE SAU LOI TIM LINE
    if (turnState == CORNER_FAULT) {
      stopAllMotors();

      bool center = m && !l2 && !r2;

      bool obstacle =
          frontHits > 0 ||
          (distF > 3 && distF <= OBSTACLE_CM);

      if (cornerAutoResume && center && !obstacle) {
        if (!cornerResumePending) {
          cornerResumePending = true;
          cornerResumeSince = now;
        }

        if (now - cornerResumeSince >= CORNER_RESUME_MS) {
          logCorner("LINE_FOUND_RESUME");
          finishCorner();
        }

      } else {
        cornerResumePending = false;
      }

      return;
    }

    // BUOC1: TIEN BU
    if (turnState == RUNOUT_90) {
      // Ghi nhan da roi line cu ngay trong luc tien bu.
      if (!(l2 || l1 || m || r1 || r2)) {
        if (cornerBlankCount < 2) {
          ++cornerBlankCount;
        }

        if (cornerBlankCount >= 2) {
          cornerBlankSeen = true;
        }

      } else {
        cornerBlankCount = 0;
      }

      unsigned long runout =
          pendingTurnDir == 'E'
          ? RUNOUT_RIGHT_MS
          : RUNOUT_LEFT_MS;

      if (now - turnTimer < runout) {
        steerChassis(RUNOUT_SPEED, RUNOUT_SPEED);

        curL = curR = RUNOUT_SPEED;
        lineTargetL = lineTargetR = RUNOUT_SPEED;
        cruiseSpeed = RUNOUT_SPEED;
        return;
      }

      // Khong chen pha dung/pha xoay cham.
      turnState = TURNING_90;
      turnTimer = now;

      // Giu co da roi line cu tu giai doan tien bu.
      cornerSideSeen = false;
      cornerCenterCount = 0;

      logCorner("SPIN_START");
    }

    // BUOC2: XOAY NHANH, BAT LINE BANG CUM GIUA
    if (turnState == TURNING_90) {
      if (now - turnTimer >= TURN_TIMEOUT_MS) {
        cornerFail("SPIN_TIMEOUT");
        return;
      }

      bool blank = !(l2 || l1 || m || r1 || r2);

      if (blank) {
        if (cornerBlankCount < 2) {
          ++cornerBlankCount;
        }

        if (cornerBlankCount >= 2) {
          cornerBlankSeen = true;
        }

      } else {
        cornerBlankCount = 0;
      }

      bool expectedSide =
          pendingTurnDir == 'E'
          ? (r1 || r2)
          : (l1 || l2);

      // Chi ghi nhan, khong dung lam dieu kien bat buoc.
      if (cornerBlankSeen && expectedSide) {
        cornerSideSeen = true;
      }

      bool center = m && !l2 && !r2;

      // Mot mau cum giua hop le se ngat PWM ngay.
      if (cornerBlankSeen &&
          center &&
          now - turnTimer >= MIN_TURN_MS) {

        cornerCenterCount = 1;

      } else {
        cornerCenterCount = 0;
      }

      if (cornerCenterCount >= 1) {
        stopAllMotors();

        curL = curR = 0;
        lineTargetL = lineTargetR = 0;

        logCorner("CENTER_STOP");

        turnState = SETTLE_90;
        turnTimer = now;
        currentCommand = 'S';
        return;
      }

      int speed =
          pendingTurnDir == 'E'
          ? TURN_RIGHT_SPEED
          : TURN_LEFT_SPEED;

      applyMecanumChassis(pendingTurnDir, speed);

      // L/R co dau khi xoay, duong=tien.
      curL =
          pendingTurnDir == 'E'
          ? speed
          : -speed;

      curR = -curL;
      lineTargetL = curL;
      lineTargetR = curR;

      currentCommand = pendingTurnDir;
      return;
    }

    // BUOC3: KIEM TRA LINE SAU KHI NGAT PWM
    if (turnState == SETTLE_90) {
      stopAllMotors();

      if (now - turnTimer < SETTLE_MS) {
        return;
      }

      if (!(m && !l2 && !r2)) {
        cornerFail("LINE_MOVED_AFTER_STOP");
        return;
      }

      logCorner("LOCK_OK");
      finishCorner();
      return;
    }

    cornerFail("INVALID_STATE");
    return;
  }

  // DO LINE THONG THUONG
  if (now - lastControlTime < CONTROL_PERIOD_MS) {
    return;
  }

  lastControlTime = now;

  // NHAN GOC90
  if (ENABLE_90_TURN) {
    bool enabled =
        now - postAvoidanceBlindTimer > 400 &&
        now - lastCornerFinished > CORNER_LOCK_MS;

    bool rightCorner = m && r1 && r2 && !l2;
    bool leftCorner = m && l1 && l2 && !r2;

    char dir = rightCorner ? 'E' : 'Q';

    if (enabled && (rightCorner || leftCorner)) {
      if (pendingTurnDir != dir) {
        cornerCount = 0;
      }

      pendingTurnDir = dir;

      if (++cornerCount >= 2) {
        cornerCount = 0;
        turnState = RUNOUT_90;
        turnTimer = now;
        cornerSampleTime = now;
        lineZone = 'T';

        cornerBlankSeen = false;
        cornerSideSeen = false;
        cornerBlankCount = 0;
        cornerCenterCount = 0;

        cornerAutoResume = false;
        cornerResumePending = false;

        logCorner("DETECT_RUNOUT");

        steerChassis(RUNOUT_SPEED, RUNOUT_SPEED);

        curL = curR = RUNOUT_SPEED;
        lineTargetL = lineTargetR = RUNOUT_SPEED;
        cruiseSpeed = RUNOUT_SPEED;

        currentCommand = 'F';
        return;
      }

    } else {
      cornerCount = 0;
    }
  }

  logicalLineMask =
      (unsigned int)l2 |
      ((unsigned int)l1 << 1) |
      ((unsigned int)m << 2) |
      ((unsigned int)r1 << 3) |
      ((unsigned int)r2 << 4);

  int cnt =
      (int)l2 +
      (int)l1 +
      (int)m +
      (int)r1 +
      (int)r2;

  int targetL, targetR;
  bool needPulse = false;

  if (cnt > 0) {
    adcHadLine = true;
    lostReported = false;
    lostLineTimer = now;

    float sum =
        -4.0f * l2 -
        2.0f * l1 +
        2.0f * r1 +
        4.0f * r2;

    float err = sum / cnt;
    float a = fabs(err);

    lineAbsError = a;

    const bool edge = l2 || r2;
    const bool ambiguous = l2 && r2;

    const int direction =
        err > 0.01f ? 1 : (err < -0.01f ? -1 : 0);

    // Nhanh bam cua thuong giu theo chuandet.
    if (edge) {
      curveActive = true;
      centerPending = false;

    } else if (curveActive) {
      if (!centerPending) {
        centerPending = true;
        centerSince = now;
      }

      if (now - centerSince >= CURVE_EXIT_MS) {
        curveActive = false;
        centerPending = false;
      }
    }

    if (ambiguous) {
      lineZone = 'X';
      cruiseSpeed = LINE_BASE_SPEED;

      targetL = targetR = LINE_BASE_SPEED;

    } else if (curveActive) {
      lineZone = 'C';
      cruiseSpeed = LINE_BASE_SPEED;

      if (edge) {
        int inner = constrain(
          lerpTbl(INNER_TBL, a, LINE_BASE_SPEED),
          0,
          255
        );

        int outer = min(
          lerpTbl(OUTER_TBL, a, LINE_BASE_SPEED),
          CURVE_OUTER_MAX
        );

        if (direction > 0) {
          targetL = outer;
          targetR = inner;

        } else if (direction < 0) {
          targetL = inner;
          targetR = outer;

        } else {
          targetL = targetR = LINE_BASE_SPEED;
        }

        needPulse = a >= PULSE_MIN_A;

      } else {
        int trim = constrain(
          (int)(a * (STRAIGHT_TRIM_MAX / 2.0f) + 0.5f),
          0,
          STRAIGHT_TRIM_MAX
        );

        targetL =
            LINE_BASE_SPEED -
            (direction < 0 ? trim : 0);

        targetR =
            LINE_BASE_SPEED -
            (direction > 0 ? trim : 0);
      }

    } else {
      lineZone = 'S';
      cruiseSpeed = LINE_FAST_SPEED;

      int trim = constrain(
        (int)(a * (STRAIGHT_TRIM_MAX / 2.0f) + 0.5f),
        0,
        STRAIGHT_TRIM_MAX
      );

      targetL =
          cruiseSpeed -
          (direction < 0 ? trim : 0);

      targetR =
          cruiseSpeed -
          (direction > 0 ? trim : 0);
    }

    lastErr = err;
    lastLeftCmd = targetL;
    lastRightCmd = targetR;

    currentCommand = 'F';

  } else {
    if (adcHadLine) {
      adcHadLine = false;

      Serial.print(">> FIRST_LOSS ");
      printLineAdc();
    }

    unsigned long lost = now - lostLineTimer;

    lineZone = 'L';
    cruiseSpeed = LINE_BASE_SPEED;

    curveActive = true;
    centerPending = false;

    if (lost < HOLD_LAST_MS) {
      targetL = min(lastLeftCmd, LINE_BASE_SPEED);
      targetR = min(lastRightCmd, LINE_BASE_SPEED);

    } else if (lost < SEARCH_MAX_MS) {
      if (lastErr >= 1.5f) {
        targetL = SEARCH_OUTER_SPEED;
        targetR = 0;

      } else if (lastErr <= -1.5f) {
        targetL = 0;
        targetR = SEARCH_OUTER_SPEED;

      } else if (lost < HOLD_LAST_MS + CREEP_MS) {
        targetL = LOST_FORWARD_SPEED;
        targetR = LOST_FORWARD_SPEED;

      } else {
        stopLineLost();
        return;
      }

    } else {
      stopLineLost();
      return;
    }

    needPulse = false;
    currentCommand = 'F';
  }

  lineTargetL = targetL;
  lineTargetR = targetR;

  if (ENABLE_TURN_PULSE && needPulse) {
    if (!wasPulsing) {
      pulseStart = now;
      wasPulsing = true;
    }

    unsigned long ph =
        (now - pulseStart) %
        (TURN_PULSE_ON_MS + TURN_PULSE_OFF_MS);

    if (ph < TURN_PULSE_ON_MS) {
      curL = targetL;
      curR = targetR;

    } else {
      curL = 0;
      curR = 0;
    }

  } else {
    wasPulsing = false;

    curL = slewTo(curL, targetL);
    curR = slewTo(curR, targetR);
  }

  steerChassis(curL, curR);
}

void logCorner(const char* event) {
  Serial.print(">> CORNER ");
  Serial.print(event);

  Serial.print(" dir=");
  Serial.print(pendingTurnDir);

  Serial.print(" at=");
  Serial.print(millis());

  Serial.print(" elapsed=");
  Serial.println(millis() - turnTimer);
}

void finishCorner() {
  unsigned long now = millis();

  turnState = IDLE_LINE;
  lastCornerFinished = now;

  resetLineTracking();
  cruiseSpeed = LINE_BASE_SPEED;

  lastErr = 0;
  lastLeftCmd = lastRightCmd = LINE_BASE_SPEED;

  curL = curR = 0;
  lineTargetL = lineTargetR = 0;

  lostLineTimer = now;
  lastControlTime = now;

  currentCommand = 'F';
  cornerCount = 0;
  lostReported = false;

  cornerAutoResume = false;
  cornerResumePending = false;
}

void cornerFail(const char* reason) {
  stopAllMotors();

  curL = curR = 0;
  lineTargetL = lineTargetR = 0;

  currentCommand = 'S';
  turnState = CORNER_FAULT;
  lineZone = 'F';

  Serial.print(">> CORNER_FAULT: ");
  Serial.println(reason);

  // Chi loi tim line cho phep tu chay lai.
  cornerAutoResume =
      strcmp(reason, "SPIN_TIMEOUT") == 0 ||
      strcmp(reason, "LINE_MOVED_AFTER_STOP") == 0;

  cornerResumePending = false;

  Serial.println(
    cornerAutoResume
      ? ">> Cho cumgiua bat line120ms de tu chay lai; M de huy AUTO."
      : ">> Loi vatcan/trangthai: dung M de thoat AUTO va kiem tra."
  );
}

void resetLineTracking() {
  adcHadLine = false;
  curveActive = false;
  centerPending = false;

  lineZone = 'S';
  lineTargetL = lineTargetR = 0;

  logicalLineMask = 0;
  lineAbsError = 0.0f;
}

int lerpTbl(const int* t, float a, int row0) {
  if (a <= 0.0f) {
    return row0;
  }

  if (a >= 4.0f) {
    return t[4];
  }

  int i = (int)a;
  float f = a - i;
  int v0 = i == 0 ? row0 : t[i];

  return v0 + (int)((t[i + 1] - v0) * f);
}

int slewTo(int cur, int target) {
  if (target > cur + SLEW_STEP) {
    return cur + SLEW_STEP;
  }

  if (target < cur - SLEW_STEP) {
    return cur - SLEW_STEP;
  }

  return target;
}

void stopLineLost() {
  stopAllMotors();

  curL = curR = 0;
  wasPulsing = false;
  cruiseSpeed = LINE_BASE_SPEED;

  resetLineTracking();

  lineZone = 'L';
  currentCommand = 'S';

  if (!lostReported) {
    lostReported = true;

    Serial.println(
      ">> TU HANH: KHONG THAY VACH -> DUNG "
      "(xem DATA:xxxxx, kiem tra LINE_DETECTED/do cao cam bien)"
    );
  }
}

// DIEU KHIEN MOTOR
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
  // Commissioning cap applies to ALL USB-owned motion, including unchanged line/corner targets.
  if(hostOwned){
    int peak=max(max(abs(fl),abs(fr)),max(abs(rl),abs(rr)));
    if(peak>vectorAvoid.cap){fl=(long)fl*vectorAvoid.cap/peak;fr=(long)fr*vectorAvoid.cap/peak;rl=(long)rl*vectorAvoid.cap/peak;rr=(long)rr*vectorAvoid.cap/peak;}
  }
  actualWheels[0]=fl;actualWheels[1]=fr;actualWheels[2]=rl;actualWheels[3]=rr;
  motor(D1_RPWM, D1_LPWM, -fl);
  motor(D2_RPWM, D2_LPWM, fr);
  motor(D3_RPWM, D3_LPWM, -rl);
  motor(D4_RPWM, D4_LPWM, rr);
}

void steerChassis(int speedLeft, int speedRight) {
  speedLeft = constrain(speedLeft, 0, 255);
  speedRight = constrain(speedRight, 0, 255);

  drive(speedLeft, speedRight, speedLeft, speedRight);
}

void steerSigned(int speedLeft, int speedRight) {
  speedLeft = constrain(speedLeft, -255, 255);
  speedRight = constrain(speedRight, -255, 255);

  drive(speedLeft, speedRight, speedLeft, speedRight);
}

void applyMecanumChassis(char cmd, int spd) {
  switch (cmd) {
    case 'F':
      drive(spd, spd, spd, spd);
      break;

    case 'B':
      drive(-spd, -spd, -spd, -spd);
      break;

    case 'L':
      drive(-spd, spd, spd, -spd);
      break;

    case 'R':
      drive(spd, -spd, -spd, spd);
      break;

    case 'Q':
      drive(-spd, spd, -spd, spd);
      break;

    case 'E':
      drive(spd, -spd, spd, -spd);
      break;

    case 'S':
    default:
      stopAllMotors();
      break;
  }
}

void stopAllMotors() {
  for(int i=0;i<4;i++)actualWheels[i]=0;
  analogWrite(D1_RPWM, 0);
  analogWrite(D1_LPWM, 0);
  analogWrite(D2_RPWM, 0);
  analogWrite(D2_LPWM, 0);
  analogWrite(D3_RPWM, 0);
  analogWrite(D3_LPWM, 0);
  analogWrite(D4_RPWM, 0);
  analogWrite(D4_LPWM, 0);
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

    if (c == 'M' || c == 'm' ||
        c == 'S' || c == 's' ||
        c == ' ' || c == 'Z' || c == 'z') {

      toggleMode("NGAT KHAN CAP USB");
      return true;
    }
  }

  while (Serial2.available() > 0) {
    char c = Serial2.read();

    if (c == 'M' || c == 'm' ||
        c == 'S' || c == 's' ||
        c == ' ' || c == 'Z' || c == 'z') {

      toggleMode("NGAT KHAN CAP WIFI");
      return true;
    }
  }

  return false;
}

bool nonBlockingAction(
  char cmd,
  int spd,
  unsigned long durationMs
) {
  unsigned long startT = millis();

  while (millis() - startT < durationMs) {
    if (checkEmergencyAbort()) {
      return false;
    }

    applyMecanumChassis(cmd, spd);
    delay(10);
  }

  return true;
}

// NE VAT CAN: GIU THEO CHUANDET
void executeCorridorAvoidanceReference() {
  isExecutingAvoidance = true;

  stopAllMotors();
  delay(150);

  long distSideLeft =
      readUltrasonicCM(TRIG_LEFT, ECHO_LEFT);

  long distSideRight =
      readUltrasonicCM(TRIG_RIGHT, ECHO_RIGHT);

  servoMove(135, 420);
  long distAngle135 =
      readUltrasonicCM(TRIG_FRONT, ECHO_FRONT);

  servoMove(45, 420);
  long distAngle45 =
      readUltrasonicCM(TRIG_FRONT, ECHO_FRONT);

  servoMove(90, 250);

  if (checkEmergencyAbort()) {
    isExecutingAvoidance = false;
    return;
  }

  if (distSideLeft > 300) {
    distSideLeft = 300;
  }

  if (distSideRight > 300) {
    distSideRight = 300;
  }

  if (distAngle135 > 300) {
    distAngle135 = 300;
  }

  if (distAngle45 > 300) {
    distAngle45 = 300;
  }

  char primaryDir;
  char returnDir;

  if (distSideRight < 35 || distAngle45 < 30) {
    primaryDir = 'L';
    returnDir = 'R';

  } else if (distSideLeft < 35 || distAngle135 < 30) {
    primaryDir = 'R';
    returnDir = 'L';

  } else if (distSideRight >= distSideLeft) {
    primaryDir = 'R';
    returnDir = 'L';

  } else {
    primaryDir = 'L';
    returnDir = 'R';
  }

  // [1] DAT NGANG RA
  Serial.println(">> NE CAN [1/3]: DAT NGANG RA");

  if (!nonBlockingAction(
        primaryDir,
        AVOID_STRAFE_SPD,
        AVOID_OUT_MS)) {

    isExecutingAvoidance = false;
    return;
  }

  stopAllMotors();
  delay(150);

  // [2] TIEN SONG SONG
  Serial.println(">> NE CAN [2/3]: TIEN THANG SONG SONG");

  if (!nonBlockingAction(
        'F',
        AVOID_FORWARD_SPEED,
        AVOID_FORWARD_MS)) {

    isExecutingAvoidance = false;
    return;
  }

  stopAllMotors();
  delay(150);

  // [3] DAT VE LINE
  Serial.println(">> NE CAN [3/3]: DAT NGANG QUAY LAI LINE");

  if (!nonBlockingAction(
        returnDir,
        AVOID_STRAFE_SPD,
        AVOID_BACK_BLIND_MS)) {

    isExecutingAvoidance = false;
    return;
  }

  stopAllMotors();

  const int AVOID_RETURN_SPEED = 150;
  unsigned long t0 = millis();
  bool found = false;

  while (millis() - t0 < AVOID_BACK_SEARCH_MS) {
    if (checkEmergencyAbort()) {
      isExecutingAvoidance = false;
      return;
    }

    applyMecanumChassis(returnDir, AVOID_RETURN_SPEED);

    bool hitM =
        digitalRead(PIN_RAW_3) == LINE_DETECTED;

    bool hitL1 =
        digitalRead(PIN_RAW_2) == LINE_DETECTED;

    bool hitR1 =
        digitalRead(PIN_RAW_4) == LINE_DETECTED;

    if (hitM || hitL1 || hitR1) {
      stopAllMotors();
      found = true;
      break;
    }

    delay(5);
  }

  stopAllMotors();

  Serial.println(
    found
      ? ">> NE CAN: DA BAT DUNG CUM 3 MAT GIUA -> DUNG VA DO LINE"
      : ">> NE CAN: HET THOI GIAN TIM LINE"
  );

  delay(150);

  currentCommand = 'S';
  isExecutingAvoidance = false;
  postAvoidanceBlindTimer = millis();

  lastErr = 0.0f;
  lastLeftCmd = lastRightCmd = LINE_BASE_SPEED;

  curL = curR = 0;
  wasPulsing = false;
  cruiseSpeed = LINE_BASE_SPEED;

  resetLineTracking();

  lostLineTimer = millis();
  frontHits = 0;
}
uint16_t vectorCrc(const char *p){uint16_t c=0xffff;while(*p){c^=(uint8_t)*p++<<8;for(int i=0;i<8;i++)c=c&0x8000?(c<<1)^0x1021:c<<1;}return c;}
void vectorStop(){
 stopAllMotors();vectorManual=false;vectorAvoid.phase=VmAvoid::OFF;
 isExecutingAvoidance=false;isLineTrackingMode=false;turnState=IDLE_LINE;currentCommand='S';
 for(int i=0;i<4;i++)vectorTarget[i]=0;
}
void vectorAck(uint32_t seq,const char *status){Serial.print("ACK:");Serial.print(seq);Serial.print(',');Serial.println(status);}
void vectorFrame(){
 char *star=strchr(frameBuffer,'*');if(!star||strlen(star+1)!=4)return;
 *star=0;char *end=0;unsigned long check=strtoul(star+1,&end,16);
 if(*end||check!=vectorCrc(frameBuffer))return;
 char *items[8];int count=0;char *save=0;
 for(char *t=strtok_r(frameBuffer,",",&save);t;t=strtok_r(0,",",&save)){
  if(count>=8)return;
  items[count++]=t;
 }
 if(count!=8||strcmp(items[0],"V1")||strlen(items[3])!=1)return;
 uint32_t sid=0,seq=0;
 for(int k=1;k<=2;k++){
  uint32_t n=0;const char *p=items[k];if(!*p)return;
  while(*p){if(*p<'0'||*p>'9'||n>429496729UL||(n==429496729UL&&*p>'5'))return;n=n*10+(*p++-'0');}
  if(k==1)sid=n;else seq=n;
 }
 char op=items[3][0];int vals[4];
 for(int k=4;k<8;k++){
  if(strlen(items[k])>5)return;
  char *e=0;long v=strtol(items[k],&e,10);
  if(*e||v < -255||v>350)return;
  vals[k-4]=v;
 }
 int f=vals[0],s=vals[1],r=vals[2],ttl=vals[3];
 uint32_t now=millis();
 if(op=='H'){
  if(!sid||(hostOwned&&sid!=hostSession&&(uint32_t)(now-hostAt)<=700)){vectorAck(seq,"BUSY");return;}
  if(hostOwned&&sid==hostSession&&seq<=hostSequence)return;
  vectorStop();hostOwned=true;hostSession=sid;hostSequence=seq;hostAt=now;vectorAck(seq,"OK");return;
 }
 if(!hostOwned||sid!=hostSession)return;
 if(op=='S'){vectorStop();hostAt=now;if(seq>hostSequence)hostSequence=seq;vectorAck(seq,"OK");return;}
 if(seq<=hostSequence||ttl<100||ttl>350||abs(f)>255||abs(s)>255||abs(r)>255)return;
 if(op!='P'&&op!='D'&&op!='A'&&op!='M'&&op!='E')return;
 hostSequence=seq;hostAt=now;
 if(op=='D'){
  if(isLineTrackingMode||vectorAvoid.phase!=VmAvoid::OFF){vectorAck(seq,"MODE");return;}
  vmMix(f,s,r,vectorAvoid.cap,vectorTarget);vectorManual=true;driveAt=now;currentCommand='V';
 }else if(op=='A'){
  if(!isLineTrackingMode){vectorStop();toggleMode("VECTOR1");}
 }else if(op=='M'){vectorStop();}
 else if(op=='E'){
  if(isLineTrackingMode||vectorManual){vectorAck(seq,"MODE");return;}
  if((f!=0&&f!=1)||s<40||s>255){vectorAck(seq,"RANGE");return;}
  vectorAvoid.enabled=f;vectorAvoid.cap=s;
 }
 vectorAck(seq,"OK");
}
void vectorRead(){
 // Consume all framed USB as frames. Never pass their letters to legacy parsing.
 int budget=96;
 while(Serial.available()&&budget--){char c=Serial.read();
  if(c=='?'){if(!frameActive)Serial.println("AGV:VECTOR1");continue;}
  if(c=='@'){frameActive=true;frameOverflow=false;frameLength=0;continue;}
  if(frameActive){
   if(c=='\n'){if(!frameOverflow){frameBuffer[frameLength]=0;vectorFrame();}frameActive=false;}
   else if(c!='\r'){if(frameLength<sizeof(frameBuffer)-1)frameBuffer[frameLength++]=c;else frameOverflow=true;}
  }else if(c=='Z'||c=='z'){vectorStop();}
 }
 // Old ESP retains single-character operation ONLY before USB claims the session.
 budget=32;while(Serial2.available()&&budget--){char c=Serial2.read();
  if(c=='Z'||c=='S'||c==' '){vectorStop();}
  else if(!hostOwned)parseSingleChar(c,'E');
 }
}
void vectorApply(int f,int s,int rot,int cap){vmMix(f,s,rot,cap,vectorTarget);}
void vectorBeginAvoidance(){
 stopAllMotors();vectorManual=false;isExecutingAvoidance=true;
 vectorAvoid.start(millis());servoAngle=135;scanLeft=scanRight=999;
 scanSideL=rangeL.valid(millis())?rangeL.cm:999;scanSideR=rangeR.valid(millis())?rangeR.cm:999;
 for(int i=0;i<4;i++)vectorTarget[i]=0;
}
void vectorSonar(){
 if(millis()-lastSonarTime<40)return;
 lastSonarTime=millis();
 if(vectorAvoid.phase<VmAvoid::OUT)return;
 switch(sonarSlot++%4){
  case 0:rangeF.cm=distF=readUltrasonicCM(TRIG_FRONT,ECHO_FRONT);rangeF.at=millis();break;
  case 1:rangeL.cm=distL=readUltrasonicCM(TRIG_LEFT,ECHO_LEFT);rangeL.at=millis();break;
  case 2:rangeR.cm=distR=readUltrasonicCM(TRIG_RIGHT,ECHO_RIGHT);rangeR.at=millis();break;
  case 3:rangeB.cm=distB=readUltrasonicCM(TRIG_BACK,ECHO_BACK);rangeB.at=millis();break;
 }
}
void vectorService(){
 uint32_t now=millis();
 if(hostOwned&&(uint32_t)(now-hostAt)>700){vectorStop();return;}
 // Same software servo pulse range as original; one pulse per cycle, no hold loop.
 if(vectorAvoid.phase>=VmAvoid::SCAN_LEFT&&vectorAvoid.phase<=VmAvoid::SCAN_CENTER){
  if((uint32_t)(now-servoAt)>=20){servoAt=now;digitalWrite(SERVO_PIN,HIGH);delayMicroseconds(map(servoAngle,0,180,600,2400));digitalWrite(SERVO_PIN,LOW);}
  if((uint32_t)(now-vectorAvoid.since)>=440){
   if(vectorAvoid.phase==VmAvoid::SCAN_LEFT){scanLeft=readUltrasonicCM(TRIG_FRONT,ECHO_FRONT);servoAngle=45;vectorAvoid.enter(VmAvoid::SCAN_RIGHT,now);}
   else if(vectorAvoid.phase==VmAvoid::SCAN_RIGHT){scanRight=readUltrasonicCM(TRIG_FRONT,ECHO_FRONT);servoAngle=90;vectorAvoid.enter(VmAvoid::SCAN_CENTER,now);}
   else{
    rangeF.cm=distF=readUltrasonicCM(TRIG_FRONT,ECHO_FRONT);rangeF.at=millis();
    rangeL.cm=distL=readUltrasonicCM(TRIG_LEFT,ECHO_LEFT);rangeL.at=millis();
    rangeR.cm=distR=readUltrasonicCM(TRIG_RIGHT,ECHO_RIGHT);rangeR.at=millis();
    rangeB.cm=distB=readUltrasonicCM(TRIG_BACK,ECHO_BACK);rangeB.at=millis();
    vectorAvoid.choose(rangeL.cm,rangeR.cm,scanLeft,scanRight,now);
   }
  }
 }
 if((uint32_t)(now-vectorTickAt)<10)return;
 vectorTickAt=now;
 if(vectorAvoid.phase>=VmAvoid::OUT&&vectorAvoid.phase<=VmAvoid::CENTER){
  int f=0,s=0;vectorAvoid.tick(now,rangeF,rangeB,rangeL,rangeR,digitalRead(A2)==LINE_DETECTED,f,s);
  vectorApply(f,s,0,vectorAvoid.cap);
 }
 if(vectorAvoid.phase==VmAvoid::FAULT){
  const char *why=vectorAvoid.fault;vectorStop();Serial.print("AVOID_FAULT:");Serial.println(why);return;
 }
 if(vectorAvoid.phase==VmAvoid::HANDOFF && abs(actualWheels[0]-actualWheels[1]-actualWheels[2]+actualWheels[3])>48){
  // Finish removing lateral wheel demand before giving the differential line controller ownership.
  vectorAvoid.enter(VmAvoid::CENTER,now);
 }
 if(vectorAvoid.phase==VmAvoid::HANDOFF){
  // A2 was stable for 80 ms. Seed the original controller without an inserted motor stop.
  int l=(actualWheels[0]+actualWheels[2])/2,rr=(actualWheels[1]+actualWheels[3])/2;
  resetLineTracking();curL=l;curR=rr;lastLeftCmd=l;lastRightCmd=rr;
  lastErr=0;lostLineTimer=now;lastControlTime=now;postAvoidanceBlindTimer=now;
  vectorAvoid.phase=VmAvoid::OFF;isExecutingAvoidance=false;currentCommand='F';return;
 }
 if(vectorManual&&(uint32_t)(now-driveAt)>250){vectorStop();return;}
 if(vectorManual||vectorAvoid.active()){
  int out[4];for(int i=0;i<4;i++)out[i]=vmRamp(actualWheels[i],vectorTarget[i],8);
  drive(out[0],out[1],out[2],out[3]);
 }
}
void vectorMotion(){
 uint32_t now=millis();if((uint32_t)(now-motionAt)<80)return;motionAt=now;
 Serial.print("MOTION:");Serial.print(++motionSeq);Serial.print(',');Serial.print(now);
 for(int i=0;i<4;i++){Serial.print(',');Serial.print(actualWheels[i]);}
 Serial.print(',');Serial.print(isLineTrackingMode?1:0);Serial.print(',');Serial.print((int)turnState);
 Serial.print(',');Serial.println(isExecutingAvoidance?1:0);
 Serial.print("VECTOR_STATE:");Serial.print((int)vectorAvoid.phase);Serial.print(',');Serial.print(vectorAvoid.cap);Serial.print(',');Serial.println(vectorAvoid.enabled?1:0);
}
