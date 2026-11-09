from pathlib import Path
s=Path('/tmp/agv_mecanum_chuan_review.ino').read_text()
s=s.replace('// PHIÊN BẢN TỐI ƯU TOÀN DIỆN (ĐÃ FIX TRIỆT ĐỂ TIMER 5 & VI SAI P-D):', '// BAN SUA 190 PWM: tach bam thang / giu cua; chua thu tren xe.\n// PHIÊN BẢN GỐC (giữ chân, WiFi, né cản):')
a=s.index('// --- Dò line vi sai P-D ---'); b=s.index('// --- Góc vuông 90 độ ---',a)
s=s[:a]+'''// --- Do line: thu 190 truoc; chi doi LINE_FAST_SPEED len 200 sau khi thu xe ---
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

'''+s[b:]
s=s.replace('unsigned long lastDeviationTime = 0;', '''unsigned long lastDeviationTime = 0;
bool curveActive = false;
bool sidePending = false;
int sideDirection = 0;
unsigned long sideSince = 0;
bool centerPending = false;
unsigned long centerSince = 0;
char lineZone = 'S'; // S: thang, C: cua, L: mat line, X: hai mat ria cung bat
float lineAbsError = 0.0f;''')
s=s.replace('void stopLineLost();', 'void stopLineLost();\nvoid resetLineTracking();')
# All original lifecycle resets: toggle, turn settle, loss stop, obstacle completion.
s=s.replace('wasPulsing = false; cruiseSpeed = LINE_BASE_SPEED;', 'wasPulsing = false; cruiseSpeed = LINE_BASE_SPEED; resetLineTracking();')
s=s.replace('Serial.print(" last=\'\"); Serial.print(lastRx); Serial.println("\'");', '''Serial.print(" last='"); Serial.print(lastRx); Serial.print("'");
    Serial.print(" cruise="); Serial.print(cruiseSpeed);
    Serial.print(" zone="); Serial.print(lineZone);
    Serial.print(" a="); Serial.print(lineAbsError, 2);
    Serial.print(" L/R="); Serial.print(curL); Serial.print('/'); Serial.println(curR);''')
a=s.index('    needPulse = (a >= PULSE_MIN_A);'); b=s.index("    currentCommand = 'F';",a)
s=s[:a]+'''    lineAbsError = a;
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
'''+s[b:]
a=s.index('    unsigned long lost = now - lostLineTimer;');b=s.index("    currentCommand = 'F';",a)
s=s[:a]+'''    unsigned long lost = now - lostLineTimer;
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
'''+s[b:]
pos=s.index('int lerpTbl(const int* t, float a, int row0) {')
s=s[:pos]+'''void resetLineTracking() {
  curveActive = false;
  sidePending = false;
  sideDirection = 0;
  centerPending = false;
  lastDeviationTime = millis();
  lineZone = 'S';
  lineAbsError = 0.0f;
}

'''+s[pos:]
Path('/workspace/agv_delivery/agv_mecanum_chuan/agv_mecanum_chuan.ino').write_text(s)
