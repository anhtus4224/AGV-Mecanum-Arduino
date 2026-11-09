from pathlib import Path
s=Path('/workspace/agv_delivery_v2/agv_mecanum_190_v2/agv_mecanum_190_v2.ino').read_text()
s=s.replace('AGV_190_V2', 'AGV_190_DIAG')
s=s.replace('int lineTargetL = 0, lineTargetR = 0;', '''int lineTargetL = 0, lineTargetR = 0;
// Lenh PWM co dau gui xuong motor, KHONG phai van toc do duoc.
int cmdFL = 0, cmdFR = 0, cmdRL = 0, cmdRR = 0;
const char* lineReason = "WAIT_LINE";
unsigned long straightTicks = 0, edgeTicks = 0, exitTicks = 0;
unsigned long ambiguousTicks = 0, lostTicks = 0;''')
a=s.index('    Serial.print(" cruise=");');b=s.index('\n  }\n\n  // Bắn Telemetry',a)
s=s[:a]+'''    Serial.print(" cmd4="); Serial.print(cmdFL); Serial.print('/');
    Serial.print(cmdFR); Serial.print('/'); Serial.print(cmdRL); Serial.print('/'); Serial.print(cmdRR);
    Serial.print(" raw=");
    Serial.print(digitalRead(PIN_RAW_1)); Serial.print(digitalRead(PIN_RAW_2));
    Serial.print(digitalRead(PIN_RAW_3)); Serial.print(digitalRead(PIN_RAW_4));
    Serial.print(digitalRead(PIN_RAW_5));
    if (isLineTrackingMode) {
      Serial.print(" cruise="); Serial.print(cruiseSpeed);
      Serial.print(" zone="); Serial.print(lineZone);
      Serial.print(" reason="); Serial.print(lineReason);
      Serial.print(" a="); Serial.print(lineAbsError, 2);
      Serial.print(" bits=");
      for (int bit = 0; bit < 5; ++bit) Serial.print((logicalLineMask >> bit) & 1);
      Serial.print(" target="); Serial.print(lineTargetL); Serial.print('/'); Serial.print(lineTargetR);
      Serial.print(" ticks[S,E,H,X,L]=");
      Serial.print(straightTicks); Serial.print('/'); Serial.print(edgeTicks); Serial.print('/');
      Serial.print(exitTicks); Serial.print('/'); Serial.print(ambiguousTicks); Serial.print('/');
      Serial.print(lostTicks);
    } else {
      Serial.print(" line=N/A");
    }
    Serial.println();'''+s[b:]
s=s.replace("      lineZone = 'X';", "      lineZone = 'X';\n      lineReason = \"BOTH_EDGES\"; ++ambiguousTicks;")
s=s.replace('      if (edge) {\n        // Cua thuc:', '      if (edge) {\n        lineReason = "EDGE"; ++edgeTicks;\n        // Cua thuc:')
s=s.replace('        // Cho thoat cua:', '        lineReason = "EXIT_HOLD"; ++exitTicks;\n        // Cho thoat cua:')
s=s.replace("      lineZone = 'S';\n      cruiseSpeed", "      lineZone = 'S';\n      lineReason = \"STRAIGHT\"; ++straightTicks;\n      cruiseSpeed")
s=s.replace("    lineZone = 'L';\n    cruiseSpeed", "    lineZone = 'L';\n    lineReason = \"LOST\"; ++lostTicks;\n    cruiseSpeed")
s=s.replace('  lineTargetL = lineTargetR = 0;\n  logicalLineMask', '  lineTargetL = lineTargetR = 0;\n  lineReason = "WAIT_LINE";\n  straightTicks = edgeTicks = exitTicks = ambiguousTicks = lostTicks = 0;\n  logicalLineMask')
s=s.replace("  lineZone = 'L';\n  currentCommand", "  lineZone = 'L';\n  lineReason = \"LOST_STOP\";\n  currentCommand")
s=s.replace('void drive(int fl, int fr, int rl, int rr) {\n', '''void drive(int fl, int fr, int rl, int rr) {
  cmdFL = constrain(fl, -255, 255); cmdFR = constrain(fr, -255, 255);
  cmdRL = constrain(rl, -255, 255); cmdRR = constrain(rr, -255, 255);
''')
s=s.replace('void stopAllMotors() {\n', 'void stopAllMotors() {\n  cmdFL = cmdFR = cmdRL = cmdRR = 0;\n')
Path('/workspace/agv_diagnostic/agv_190_diag/agv_190_diag.ino').write_text(s)
