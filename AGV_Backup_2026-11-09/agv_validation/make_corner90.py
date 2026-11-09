from pathlib import Path
s=Path('/workspace/agv_smooth/agv_mecanum_smooth/agv_mecanum_smooth.ino').read_text()
s=s.replace('AGV_SMOOTH_250','AGV_CORNER90_V1')
s=s.replace('const int WIFI_MAX_SPEED   = 250;', 'const int WIFI_MAX_SPEED   = 255;')
s=s.replace('const int LINE_FAST_SPEED = 250;', 'const int LINE_FAST_SPEED = 255;')
s=s.replace('const bool ENABLE_90_TURN = false;', 'const bool ENABLE_90_TURN = true;')
a=s.index('const int TURN_90_SPEED');b=s.index('// --- Bộ lọc mất',a)
s=s[:a]+'''// Cac gia tri tiep can tinh tu phep do, CHUA xac nhan tren goc that.
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

'''+s[b:]
s=s.replace('TURNING_90, SETTLE_90 };','TURNING_90, SETTLE_90, CORNER_FAULT };')
s=s.replace('unsigned long sideSince = 0;', '''unsigned long sideSince = 0;
unsigned long lastCornerFinished = 0;
unsigned long cornerSampleTime = 0;
bool cornerBlankSeen = false;
bool cornerSideSeen = false;
uint8_t cornerBlankCount = 0;
uint8_t cornerCenterCount = 0;''')
s=s.replace('void resetLineTracking();', 'void resetLineTracking();\nvoid cornerFail(const char* reason);\nvoid logCorner(const char* event);')
s=s.replace('  Serial.println(" LOW, reverseOrder=0, continuous steering");', '''  Serial.print(" runoutR/L="); Serial.print(RUNOUT_RIGHT_MS); Serial.print('/');
  Serial.print(RUNOUT_LEFT_MS); Serial.println(" ms; corner turn255, LOW, order=0");''')
s=s.replace('    Serial.print(" bits=");', '    Serial.print(" turnState="); Serial.print((int)turnState);\n    Serial.print(" bits=");')
s=s.replace('  if (millis() - lastPacketTime > FAILSAFE_MS) {', '''  unsigned long timeout = (currentCommand == 'E' || currentCommand == 'Q')
      ? MANUAL_TURN_TIMEOUT_MS : FAILSAFE_MS;
  if (millis() - lastPacketTime > timeout) {''')
s=s.replace("      currentCommand = 'S';\n      stopAllMotors();\n    }\n  }\n}\n\n// ADC", "      currentCommand = 'S';\n      stopAllMotors();\n      Serial.println(\">> MANUAL_TIMEOUT: PWM=0 (app khong gui S)\");\n    }\n  }\n}\n\n// ADC")
s=s.replace('  if (USE_ULTRASONIC && turnState == IDLE_LINE && frontHits >= 2) {\n    frontHits = 0;', '''  if (USE_ULTRASONIC && frontHits >= 2) {
    frontHits = 0;
    if (turnState != IDLE_LINE) { cornerFail("OBSTACLE_DURING_CORNER"); return; }''')
a=s.index('  switch (turnState) {',s.index('void handleLineAndObstacleMode() {'));b=s.index('  unsigned long elapsed',a)
s=s[:a]+'''  if (turnState != IDLE_LINE) {
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

'''+s[b:]
a=s.index('  if (ENABLE_90_TURN) {',s.index('void handleLineAndObstacleMode() {'));b=s.index('  logicalLineMask =',a)
s=s[:a]+'''  if (ENABLE_90_TURN) {
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

'''+s[b:]
pos=s.index('void resetLineTracking() {')
s=s[:pos]+'''void logCorner(const char* event) {
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

'''+s[pos:]
s=s.replace('// giu tat: khong quay nguoc khi do line', '// bat goc vuong: Q/E cho phep xoay hai ben nguoc chieu')
s=s.replace('// AGV_CORNER90_V1 - ban thu cua lien tuc, chua thu tren xe.', '// AGV_CORNER90_V1 - ban thu goc vuong, CHUA thu tren xe.\n// Moc runout 1216ms la uoc luong; chua do duoc troi co khi / goc xoay.')
Path('/workspace/agv_corner90/agv_corner90/agv_corner90.ino').write_text(s)
