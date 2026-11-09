from pathlib import Path
s=Path('/workspace/agv_chuandet90/agv_chuandet90/agv_chuandet90.ino').read_text()
s=s.replace('AGV_CHUANDET_90_V1','AGV_CHUANDET_90_V2')
s=s.replace('// Runout1216ms la moc thu, khong phai gia tri da xac nhan tren goc that.', '// Runout608ms =1216*15/30 theo phep thu lo thuc te. Van can thu lai.')
a=s.index('const unsigned long MEASURED_80CM_MS');b=s.index('const int RUNOUT_SPEED',a)
s=s[:a]+'''// Hieu chinh tu chay that: front lo30cm, muc tieu15cm.
const unsigned long RUNOUT_RIGHT_MS = 608;
const unsigned long RUNOUT_LEFT_MS = 608;
'''+s[b:]
s=s.replace('const unsigned long TURN_TIMEOUT_MS = 4000;', '''// Rut cua so tim line: video truoc quay gan180 trong khoang4s.
// 2200ms chi la gioi han bao ve ban thu, KHONG phai phep do90do.
const unsigned long TURN_TIMEOUT_MS = 2200;
const unsigned long CORNER_RESUME_MS = 120;''')
s=s.replace('bool cornerBlankSeen = false, cornerSideSeen = false;', '''bool cornerBlankSeen = false, cornerSideSeen = false;
bool cornerAutoResume = false;
bool cornerResumePending = false;
unsigned long cornerResumeSince = 0;''')
s=s.replace('void logCorner(const char* event);', 'void logCorner(const char* event);\nvoid finishCorner();')
s=s.replace('    if (turnState == CORNER_FAULT) { stopAllMotors(); return; }', '''    if (turnState == CORNER_FAULT) {
      stopAllMotors();
      // Chi tu tiep tuc voi loi line. Loi vatcan van can M xac nhan lai.
      bool center = m && !l2 && !r2;
      bool obstacle = frontHits > 0 || (distF > 3 && distF <= OBSTACLE_CM);
      if (cornerAutoResume && center && !obstacle) {
        if (!cornerResumePending) {
          cornerResumePending = true; cornerResumeSince = now;
        }
        if (now - cornerResumeSince >= CORNER_RESUME_MS) {
          logCorner("LINE_FOUND_RESUME"); finishCorner();
        }
      } else { cornerResumePending = false; }
      return;
    }''')
s=s.replace('    if (turnState == RUNOUT_90) {\n      unsigned long runout', '''    if (turnState == RUNOUT_90) {
      // Ghi nhan da roi line cu ngay trong luc tienbu, khong doi toi luc xoay.
      if (!(l2 || l1 || m || r1 || r2)) {
        if (cornerBlankCount < 2) ++cornerBlankCount;
        if (cornerBlankCount >= 2) cornerBlankSeen = true;
      } else { cornerBlankCount = 0; }
      unsigned long runout''')
s=s.replace('      cornerBlankSeen = false; cornerSideSeen = false;\n      cornerBlankCount = cornerCenterCount = 0;', '''      // Giu lai co da roi line cu tu giai doan tien bu.
      cornerSideSeen = false;
      cornerCenterCount = 0;''')
s=s.replace('      if (cornerBlankSeen && cornerSideSeen && center && now - turnTimer >= MIN_TURN_MS) {\n        if (cornerCenterCount < 2) ++cornerCenterCount;', '''      // Khong bat buoc mat ben: co the bo lo mau ben giua hai lan doc.
      // Mot lan doc cumgiua hop le se ngat ngay, sau do xac minh80ms.
      if (cornerBlankSeen && center && now - turnTimer >= MIN_TURN_MS) {
        cornerCenterCount = 1;''')
s=s.replace('      if (cornerCenterCount >= 2) {', '      if (cornerCenterCount >= 1) {')
a=s.index('      turnState = IDLE_LINE; lastCornerFinished = now;',s.index('if (turnState == SETTLE_90)'))
b=s.index('    }\n    cornerFail("INVALID_STATE")',a)
s=s[:a]+'''      finishCorner(); return;
'''+s[b:]
s=s.replace("        cornerSampleTime = now; lineZone = 'T';", '''        cornerSampleTime = now; lineZone = 'T';
        cornerBlankSeen = false; cornerSideSeen = false;
        cornerBlankCount = cornerCenterCount = 0;
        cornerAutoResume = false; cornerResumePending = false;''')
s=s.replace('void cornerFail(const char* reason) {', '''void finishCorner() {
  unsigned long now = millis();
  turnState = IDLE_LINE; lastCornerFinished = now;
  resetLineTracking(); cruiseSpeed = LINE_BASE_SPEED;
  lastErr = 0; lastLeftCmd = lastRightCmd = LINE_BASE_SPEED;
  curL = curR = lineTargetL = lineTargetR = 0;
  lostLineTimer = now; lastControlTime = now;
  currentCommand = 'F'; cornerCount = 0; lostReported = false;
  cornerAutoResume = false; cornerResumePending = false;
}

void cornerFail(const char* reason) {''')
s=s.replace('  Serial.println(">> Kiem tra vi tri xe. Dung M de thoat AUTO; M lan nua de thu lai.");', '''  cornerAutoResume = strcmp(reason, "SPIN_TIMEOUT") == 0 ||
                     strcmp(reason, "LINE_MOVED_AFTER_STOP") == 0;
  cornerResumePending = false;
  Serial.println(cornerAutoResume
    ? ">> Cho cumgiua bat line120ms de tu chay lai; M de huy AUTO."
    : ">> Loi vatcan/trangthai: dung M de thoat AUTO va kiem tra.");''')
p=Path('/workspace/agv_chuandet90_v2/agv_chuandet90_v2/agv_chuandet90_v2.ino');p.write_text(s)
