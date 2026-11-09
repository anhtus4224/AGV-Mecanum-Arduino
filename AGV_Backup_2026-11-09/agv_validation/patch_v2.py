from pathlib import Path
s=Path('/workspace/agv_delivery/agv_mecanum_chuan/agv_mecanum_chuan.ino').read_text()
s=s.replace('// BAN SUA 190 PWM: tach bam thang / giu cua; chua thu tren xe.', '// AGV_190_V2: cum 3 mat giua dat truc tiep 190 PWM, khong reset do lech nhe.\n// CHUA THU TREN XE. Toc do vat ly can duoc kiem chung tren xe thuc.')
s=s.replace('const int RAMP_UP_STEP = 2; // moi chu ky dieu khien, khong nhay thang len 190\n', '')
s=s.replace('const unsigned long CENTER_HOLD_MS = 120; // chap nhan lech nhe trong cum giua\n', '')
s=s.replace('const float SIDE_CURVE_MIN_A = 1.5f;\n', '')
s=s.replace('const unsigned long SIDE_CURVE_MS = 100; // lech cung phia keo dai -> vao cua\n', '')
s=s.replace('const unsigned long CURVE_EXIT_MS = 100; // ve gan tam on dinh moi thoat cua', 'const unsigned long CURVE_EXIT_MS = 60; // cum giua co line, hai ria sach lien tuc\nconst int CURVE_OUTER_MAX = 190; // gioi han toc banh ngoai trong cua (khong de len 255)')
s=s.replace('unsigned long lastDeviationTime = 0;\n', '')
s=s.replace('bool sidePending = false;\nint sideDirection = 0;\nunsigned long sideSince = 0;\n', '')
s=s.replace('float lineAbsError = 0.0f;', 'unsigned int logicalLineMask = 0; // bit0=L2, bit1=L1, bit2=M, bit3=R1, bit4=R2\nint lineTargetL = 0, lineTargetR = 0;\nfloat lineAbsError = 0.0f;')
s=s.replace('  Serial.println(">> [AGV READY] - DA SUA CHUAN BUOC 3 DAT NGANG HOI QUY VE LINE");', '  Serial.println(">> [AGV_190_V2 READY] straight=190 trim=20 curveMax=190 pulse=OFF");')
s=s.replace('Serial.print(">> HB up=");', 'Serial.print(">> HB fw=AGV_190_V2 up=");')
s=s.replace("    Serial.print(\" L/R=\"); Serial.print(curL); Serial.print('/'); Serial.println(curR);", '''    Serial.print(" bits=");
    for (int bit = 0; bit < 5; ++bit) Serial.print((logicalLineMask >> bit) & 1);
    Serial.print(" target="); Serial.print(lineTargetL); Serial.print('/'); Serial.print(lineTargetR);
    Serial.print(" L/R="); Serial.print(curL); Serial.print('/'); Serial.println(curR);''')
s=s.replace('  int cnt = (int)l2 + (int)l1 + (int)m + (int)r1 + (int)r2;', '''  logicalLineMask = (unsigned int)l2 | ((unsigned int)l1 << 1) |
                    ((unsigned int)m << 2) | ((unsigned int)r1 << 3) |
                    ((unsigned int)r2 << 4);
  int cnt = (int)l2 + (int)l1 + (int)m + (int)r1 + (int)r2;''')
a=s.index('    // Mat ria: vao cua ngay.');b=s.index('    if (ambiguous)',a)
s=s[:a]+'''    // Chi mat ria kich hoat cua. KHONG coi mat 2/4 bat lau la cua:
    // sensor nam lech / vach day cung co the cho a=2 suot doan thang.
    if (edge) {
      curveActive = true;
      centerPending = false;
    } else if (curveActive) {
      // Bat ky mat nao trong cum GIUA cung duoc phep thoat cua.
      // cnt>0 va !edge => chac chan co line trong cum giua, ke ca a=2.
      if (!centerPending) { centerPending = true; centerSince = now; }
      if (now - centerSince >= CURVE_EXIT_MS) {
        curveActive = false;
        centerPending = false;
      }
    }

'''+s[b:]
s=s.replace('      lastDeviationTime = now;\n', '').replace('    lastDeviationTime = now;\n', '')
a=s.index("    } else if (curveActive) {\n      lineZone = 'C';");b=s.index('      int trim = constrain(',a)
s=s[:a]+'''    } else if (curveActive) {
      lineZone = 'C';
      cruiseSpeed = LINE_BASE_SPEED;
      if (edge) {
        // Cua thuc: giu banh trong, banh ngoai toi da 190, khong dao chieu.
        int inner = constrain(lerpTbl(INNER_TBL, a, LINE_BASE_SPEED), 0, 255);
        int outer = min(lerpTbl(OUTER_TBL, a, LINE_BASE_SPEED), CURVE_OUTER_MAX);
        if (direction > 0)      { targetL = outer; targetR = inner; }
        else if (direction < 0) { targetL = inner; targetR = outer; }
        else                   { targetL = targetR = LINE_BASE_SPEED; }
        needPulse = (a >= PULSE_MIN_A);
      } else {
        // Cho thoat cua: bam mem 120/100, khong khoa banh vi mat 2/4.
        int trim = constrain((int)(a * (STRAIGHT_TRIM_MAX / 2.0f) + 0.5f),
                             0, STRAIGHT_TRIM_MAX);
        targetL = LINE_BASE_SPEED - ((direction < 0) ? trim : 0);
        targetR = LINE_BASE_SPEED - ((direction > 0) ? trim : 0);
      }
    } else {
      lineZone = 'S';
      cruiseSpeed = LINE_FAST_SPEED; // TRUC TIEP 190, khong cho tam / tang cruise
'''+s[b:]
s=s.replace('    sidePending = false;\n', '')
s=s.replace('  sidePending = false;\n  sideDirection = 0;\n', '')
s=s.replace('  lastDeviationTime = millis();\n', '')
s=s.replace("  lineZone = 'S';\n  lineAbsError", "  lineZone = 'S';\n  lineTargetL = lineTargetR = 0;\n  logicalLineMask = 0;\n  lineAbsError")
s=s.replace('  if (ENABLE_TURN_PULSE && needPulse) {', '  lineTargetL = targetL;\n  lineTargetR = targetR;\n  if (ENABLE_TURN_PULSE && needPulse) {')
# Clamping at the chassis output is retained in the original steerChassis().
Path('/workspace/agv_delivery_v2/agv_mecanum_190_v2/agv_mecanum_190_v2.ino').write_text(s)
