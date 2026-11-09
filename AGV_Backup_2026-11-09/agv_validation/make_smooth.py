from pathlib import Path
s=Path('/workspace/agv_validation/current250.ino').read_text()
a=s.index('// ==============================================================================');b=s.index('// ------------------------------------------------------------------------------\n// 1.')
s='''// AGV_SMOOTH_250 - ban thu cua lien tuc, chua thu tren xe.
// Giu chan, LOW, chieu cam bien va ne can cua file nguoi dung.
// Thang toi da 250; cua thong thuong hai ben cung tien.
\n'''+s[b:]
a=s.index('// --- Do line:');b=s.index('// --- Góc vuông',a)
s=s[:a]+'''// --- Dieu khien cua lien tuc: cac gia tri nay CAN THU TREN XE ---
const int LINE_BASE_SPEED = 120; // phuc hoi, khong phai toc do cua binh thuong
const int LINE_FAST_SPEED = 250;
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
const bool ENABLE_90_TURN = false; // giu tat: khong quay nguoc khi do line
const unsigned long CONTROL_PERIOD_MS = 10;

'''+s[b:]
s=s.replace('bool wasPulsing = false;\nunsigned long pulseStart = 0;\n','')
s=s.replace('wasPulsing = false; ', '')
s=s.replace('float lineAbsError = 0.0f;', '''float lineAbsError = 0.0f;
float filteredErr = 0.0f;
float forwardPwm = 0.0f;
float steeringPwm = 0.0f;
bool sidePending = false;
int sideSign = 0;
unsigned long sideSince = 0;''')
s=s.replace('int lerpTbl(const int* t, float a, int row0);', 'float moveToward(float value, float target, float step);')
s=s.replace('  Serial.println(">> [AGV_190_LOW_ADC READY] straight=190 trim=20 curveMax=190 pulse=OFF");', '''  Serial.print(">> [AGV_SMOOTH_250 READY] fast="); Serial.print(LINE_FAST_SPEED);
  Serial.print(" curve="); Serial.print(CURVE_SPEED);
  Serial.println(" LOW, reverseOrder=0, continuous steering");''')
s=s.replace('fw=AGV_190_LOW_ADC', 'fw=AGV_SMOOTH_250')
s=s.replace('    Serial.print(" bits=");', '''    Serial.print(" ef="); Serial.print(filteredErr, 2);
    Serial.print(" steer="); Serial.print(steeringPwm, 1);
    Serial.print(" bits=");''')
s=s.replace('  if (now - lastControlTime < CONTROL_PERIOD_MS) return;\n  lastControlTime = now;', '''  unsigned long elapsed = now - lastControlTime;
  if (elapsed < CONTROL_PERIOD_MS) return;
  lastControlTime = now;
  if (elapsed > 30) elapsed = 30; // khong nhay lenh sau mot lan chan lau
  float tickScale = elapsed / 10.0f;''')
s=s.replace('  bool needPulse = false;\n','')
a=s.index('    const bool edge = l2 || r2;');b=s.index('    lastErr = err;',a)
s=s[:a]+'''    const bool edge = l2 || r2;
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
    float trim = min(fabs(steeringPwm), maxTrim);
    int inner = (int)(forwardPwm - trim + 0.5f);
    targetL = (steeringPwm < 0) ? inner : cruiseSpeed;
    targetR = (steeringPwm > 0) ? inner : cruiseSpeed;

'''+s[b:]
s=s.replace('    centerPending = false;\n    if (lost < HOLD_LAST_MS)', '''    centerPending = false;
    sidePending = false;
    filteredErr = lastErr;
    // Dong bo trang thai dieu khien voi muc phuc hoi, khong bat lai len 250.
    forwardPwm = min(forwardPwm, (float)LINE_BASE_SPEED);
    steeringPwm = 0;
    if (lost < HOLD_LAST_MS)''')
s=s.replace('    needPulse = false; // tim line lien tuc, khong phanh theo xung\n','')
a=s.index('  if (ENABLE_TURN_PULSE && needPulse)');b=s.index('  steerChassis(curL, curR);',a)
s=s[:a]+'''  curL = slewTo(curL, targetL);
  curR = slewTo(curR, targetR);
'''+s[b:]
s=s.replace('void resetLineTracking() {\n', '''void resetLineTracking() {
  filteredErr = 0; forwardPwm = 0; steeringPwm = 0;
  sidePending = false; sideSign = 0;
''')
a=s.index('int lerpTbl(const int* t, float a, int row0) {');b=s.index('int slewTo(',a)
s=s[:a]+'''float moveToward(float value, float target, float step) {
  if (target > value + step) return value + step;
  if (target < value - step) return value - step;
  return target;
}

'''+s[b:]
Path('/workspace/agv_smooth/agv_mecanum_smooth/agv_mecanum_smooth.ino').write_text(s)
