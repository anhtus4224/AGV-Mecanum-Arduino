from pathlib import Path
import ast
root=Path('/workspace/agv_connection_repair');out=root/'fixed'
s=(root/'normalized_server.py').read_text();tree=ast.parse(s);lines=s.splitlines(True)
replacements={
'serial_worker':'''def serial_worker():
    link.run()
''',
'physics_worker':'''def physics_worker():
    # Khong co encoder: khong mo phong lenh thanh toa do/tocdo 'thuc'.
    while True:
        state['current_speed'] = 0.0
        state['odometry_available'] = False
        time.sleep(0.1)
''',
'fsm_controller_worker':'''def fsm_controller_worker():
    # AUTO do Mega xu ly. Camera chi giam sat, khong co vong dieu khien thu hai.
    while True:
        state['fsm_state'] = 'ARDUINO_AUTO' if state.get('mode') == 'TỰ HÀNH' else 'IDLE'
        time.sleep(0.1)
''',
 'toggle_mode':'''def toggle_mode():
    target = 'MANUAL' if state.get('mode') == 'TỰ HÀNH' else 'AUTO'
    if not link.send('MODE:' + target):
        return jsonify(status='error', msg='Mega chưa kết nối/handshake'), 503
    return jsonify(status='queued', mode=state['mode'])
''',
 'save_tuning':'''def save_tuning():
    return jsonify(status='error', msg='Firmware dùng hằng số. Chưa hỗ trợ nạp CFG qua web; không gửi cấu hình vào cổng motor.'), 501
''',
 'mecanum_control':'''def mecanum_control():
    try:
        drive = int(request.args.get('drive', 0))
        strafe = int(request.args.get('strafe', 0))
        rotate = int(request.args.get('rotate', 0))
    except ValueError:
        return jsonify(status='error', msg='Lệnh không hợp lệ'), 400
    if request.args.get('estop') == '1' or (drive, strafe, rotate) == (0, 0, 0):
        if not link.send('STOP'):
            return jsonify(status='error', msg='Mất kết nối; không xác nhận STOP tới Mega'), 503
        return jsonify(status='queued_stop')
    if state.get('mode') != 'LÁI TAY':
        return jsonify(status='error', msg='Đang AUTO; dùng STOP hoặc đổi sang LÁI TAY trước'), 409
    commands = {(1,0,0):'F',(-1,0,0):'B',(0,-1,0):'L',(0,1,0):'R',(0,0,-1):'Q',(0,0,1):'E'}
    cmd = commands.get((drive,strafe,rotate))
    if cmd is None:
        return jsonify(status='error', msg='Chỉ chấp nhận một hướng mỗi lệnh'), 400
    if not link.send('DRIVE:' + cmd):
        return jsonify(status='error', msg='Mega chưa kết nối/handshake'), 503
    return jsonify(status='queued')
'''}
for n in sorted([n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in replacements],key=lambda n:n.lineno,reverse=True):
 lines[n.lineno-1:n.end_lineno]=[replacements[n.name]+'\n']
s=''.join(lines)
s=s.replace('app = Flask(__name__)', 'from agv_serial_link import SafeMegaLink\n\napp = Flask(__name__)')
s=s.replace('ser = None\nlast_action_receive_time', 'ser = None\nlink = SafeMegaLink(state, serial)\nlast_action_receive_time')
s=s.replace("let showMode = (d.mode === 'LÁI TAY' || d.mode === 'TỰ LÁI') ? 'TỰ HÀNH' : 'TỰ LÁI';", "let showMode = d.mode || 'LÁI TAY';")
s=s.replace("d.x.toFixed(1) + ', ' + d.y.toFixed(1)", "'CHƯA CÓ ODOM'")
s=s.replace("d.angle.toFixed(1) + '°'", "'—'").replace("d.current_speed.toFixed(2) + ' m/s'", "'CHƯA ĐO'").replace("d.total_dist.toFixed(1) + ' m'", "'—'")
s=s.replace('XE: ONLINE (<span id="port_txt">', 'XE: USB (<span id="port_txt">')
s=s.replace("if (e.code === 'KeyX') {", "if (e.code === 'KeyX' && !e.repeat) {")
# STOP on blur must cancel mouse repeat timer too, not just keyboard timer.
s=s.replace("window.addEventListener('blur', () => {\n    stopKeyLoop();", "window.addEventListener('blur', () => {\n    if (activeBtnTimer) { clearInterval(activeBtnTimer); activeBtnTimer = null; }\n    stopKeyLoop();")
(out/'stream_server.py').write_text(s)
# Firmware: USB accepts framed commands ONLY. ESP legacy remains for later isolated test.
s=(root/'original.ino').read_text()
pos=s.index('// KHAI BAO HAM') if '// KHAI BAO HAM' in s else s.index('// Khai')
s=s[:pos]+'''// USB protocol SAFE1; no raw USB byte may drive motors.
char usbFrame[48]; uint8_t usbLength = 0; bool usbCollecting = false;
bool hostSession = false; unsigned long hostSeen = 0;
const unsigned long HOST_TIMEOUT_MS = 1500;
void hostStop();
void hostWatchdog();
void handleHostFrame(const char* frame);

'''+s[pos:]
s=s.replace('  updateSonar();', '  hostWatchdog();\n  updateSonar();',1)
a=s.index('void readSerialCommands() {');b=s.index('void toggleMode(',a)
s=s[:a]+'''void hostStop() {
  stopAllMotors();
  isLineTrackingMode = false; isExecutingAvoidance = false;
  turnState = IDLE_LINE; currentCommand = 'S';
  curL = curR = lineTargetL = lineTargetR = 0;
  cornerAutoResume = false; cornerResumePending = false;
  cornerCount = 0; frontHits = 0;
  resetLineTracking();
}

void hostWatchdog() {
  if (hostSession && millis() - hostSeen > HOST_TIMEOUT_MS) {
    hostStop(); hostSession = false;
    Serial.println(">> HOST_TIMEOUT STOP");
  }
}

void handleHostFrame(const char* frame) {
  if (strcmp(frame, "HELLO") == 0) {
    hostStop(); hostSession = true; hostSeen = millis();
    Serial.println("AGV:SAFE1"); return;
  }
  if (!hostSession) return;
  if (strcmp(frame, "PING") == 0) { hostSeen = millis(); return; }
  if (strcmp(frame, "STOP") == 0 || strcmp(frame, "MODE:MANUAL") == 0) {
    hostSeen = millis(); hostStop();
    Serial.println(strcmp(frame, "STOP") == 0 ? "ACK:STOP" : "ACK:MODE:MANUAL"); return;
  }
  if (strcmp(frame, "MODE:AUTO") == 0) {
    hostSeen = millis();
    if (!isLineTrackingMode) toggleMode("HOST_AUTO");
    Serial.println("ACK:MODE:AUTO"); return;
  }
  if (strncmp(frame, "DRIVE:", 6) == 0 && strlen(frame) == 7 && strchr("FBLRQE", frame[6])) {
    hostSeen = millis(); parseSingleChar(frame[6], 'U'); return;
  }
  Serial.println("ERR:FRAME");
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '@') { usbCollecting = true; usbLength = 0; }
    else if (c == '\\n') {
      if (usbCollecting) { usbFrame[usbLength] = 0; handleHostFrame(usbFrame); }
      usbCollecting = false; usbLength = 0;
    } else if (c != '\\r' && usbCollecting) {
      if (usbLength < sizeof(usbFrame) - 1) usbFrame[usbLength++] = c;
      else { usbCollecting = false; usbLength = 0; }
    }
  }
  while (Serial2.available() > 0) parseSingleChar(Serial2.read(), 'E');
}

'''+s[b:]
a=s.index('bool checkEmergencyAbort() {');b=s.index('bool nonBlockingAction(',a)
s=s[:a]+'''bool checkEmergencyAbort() {
  readSerialCommands();
  hostWatchdog();
  return !isLineTrackingMode;
}

'''+s[b:]
s=s.replace('AGV_CHUANDET_90_V2','AGV_MEGA_SAFE1')
(out/'agv_mega_safe/agv_mega_safe.ino').write_text(s)
