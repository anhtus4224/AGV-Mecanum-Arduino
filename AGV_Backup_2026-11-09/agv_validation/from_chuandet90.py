from pathlib import Path
s=Path('/workspace/agv_validation/reuploaded_chuandet.ino').read_text()
prev=Path('/workspace/agv_corner90/agv_corner90/agv_corner90.ino').read_text()
a=s.index('// ==============================================================================');b=s.index('const int D1_RPWM')
s='''// AGV_CHUANDET_90_V1: dua truc tiep tren ZIP chuandet cua nguoi dung.
// CHUA THU TREN XE / CHUA HIEU CHUAN GOC90.
// Runout1216ms la moc thu, khong phai gia tri da xac nhan tren goc that.

'''+s[b:]
s=s.replace('const int WIFI_MAX_SPEED   = 250;', 'const int WIFI_MAX_SPEED   = 255;')
s=s.replace('const int LINE_FAST_SPEED = 250;', 'const int LINE_FAST_SPEED = 255;')
s=s.replace('const bool ENABLE_90_TURN = false;', 'const bool ENABLE_90_TURN = true;')
a=s.index('const int TURN_90_SPEED');b=s.index('// --- Bộ lọc mất',a)
params=prev[prev.index('const unsigned long MEASURED_80CM_MS'):prev.index('// --- Bộ lọc mất')]
s=s[:a]+params+'\n'+s[b:]
s=s.replace('TURNING_90, SETTLE_90 };','TURNING_90, SETTLE_90, CORNER_FAULT };')
s=s.replace('float lineAbsError = 0.0f;', '''float lineAbsError = 0.0f;
unsigned long lastCornerFinished = 0;
unsigned long cornerSampleTime = 0;
bool cornerBlankSeen = false, cornerSideSeen = false;
uint8_t cornerBlankCount = 0, cornerCenterCount = 0;''')
s=s.replace('void resetLineTracking();', 'void resetLineTracking();\nvoid cornerFail(const char* reason);\nvoid logCorner(const char* event);')
s=s.replace('  Serial.println(">> [AGV_190_LOW_ADC READY] straight=190 trim=20 curveMax=190 pulse=OFF");', '''  Serial.print(">> [AGV_CHUANDET_90_V1 READY] fast="); Serial.print(LINE_FAST_SPEED);
  Serial.print(" wifi="); Serial.print(WIFI_MAX_SPEED);
  Serial.print(" runoutR/L="); Serial.print(RUNOUT_RIGHT_MS); Serial.print('/');
  Serial.print(RUNOUT_LEFT_MS); Serial.println(" ms; spin255; LOW; order=0");''')
s=s.replace('fw=AGV_190_LOW_ADC', 'fw=AGV_CHUANDET_90_V1')
s=s.replace('    Serial.print(" bits=");', '    Serial.print(" turnState="); Serial.print((int)turnState);\n    Serial.print(" bits=");')
a=s.index('void handleManualMode() {');b=s.index('// ADC samples',a)
s=s[:a]+'''void handleManualMode() {
  unsigned long timeout = (currentCommand == 'E' || currentCommand == 'Q')
      ? MANUAL_TURN_TIMEOUT_MS : FAILSAFE_MS;
  if (millis() - lastPacketTime > timeout && currentCommand != 'S') {
    currentCommand = 'S'; stopAllMotors();
    Serial.println(">> MANUAL_TIMEOUT: PWM=0");
  }
}

'''+s[b:]
s=s.replace('  if (USE_ULTRASONIC && turnState == IDLE_LINE && frontHits >= 2) {\n    frontHits = 0;', '''  if (USE_ULTRASONIC && frontHits >= 2) {
    frontHits = 0;
    if (turnState != IDLE_LINE) { cornerFail("OBSTACLE_DURING_CORNER"); return; }''')
a=s.index('  switch (turnState) {',s.index('void handleLineAndObstacleMode() {'));b=s.index('  if (now - lastControlTime',a)
block=prev[prev.index('  if (turnState != IDLE_LINE) {\n    // Chuyen goc'):prev.index('  unsigned long elapsed',prev.index('void handleLineAndObstacleMode() {'))]
block=block.replace('resetLineTracking(); forwardPwm = LINE_BASE_SPEED; curveActive = true;', 'resetLineTracking(); cruiseSpeed = LINE_BASE_SPEED;')
s=s[:a]+block+s[b:]
a=s.index('  if (ENABLE_90_TURN) {',s.index('void handleLineAndObstacleMode() {'));b=s.index('  logicalLineMask =',a)
pa=prev.index('  if (ENABLE_90_TURN) {',prev.index('void handleLineAndObstacleMode() {'));pb=prev.index('  logicalLineMask =',pa)
s=s[:a]+prev[pa:pb]+s[b:]
pos=s.index('void resetLineTracking() {')
helpers=prev[prev.index('void logCorner(const char* event) {'):prev.index('void resetLineTracking() {')]
s=s[:pos]+helpers+s[pos:]
# Compact obsolete headings; keep executable source otherwise untouched.
s=s.replace('// --- Do line: thu 190 truoc; chi doi LINE_FAST_SPEED len 200 sau khi thu xe ---', '// Do line255; nhan gocvuong se chuyen sang may trangthai rieng.')
s=s.replace('// --- Góc vuông 90 độ ---', '// Goc90: runout tinh tu phepdo; MIN/MAX chi la gioihan, KHONG do goc.')
s='\n'.join(l for l in s.splitlines() if not(l.lstrip().startswith('//') and ('=====' in l or '-----' in l)))+'\n'
Path('/workspace/agv_chuandet90/agv_chuandet90/agv_chuandet90.ino').write_text(s)
