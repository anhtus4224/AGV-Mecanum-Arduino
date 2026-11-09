from flask import Flask, Response, render_template_string, request, jsonify
import cv2
import serial
import glob
import threading
import time
import math
import subprocess
import socket
import numpy as np

app = Flask(__name__)

# ------------------------------------------------------------------------------
# 1. CAMERA TỰ ĐỘNG BẮT MỌI CỔNG VIDEO (0 -> 10)
# ------------------------------------------------------------------------------
latest_frame = None
frame_lock = threading.Lock()

def make_fallback_frame(msg="DANG KET NOI CAMERA..."):
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    cv2.putText(img, msg, (260, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 180, 255), 3, cv2.LINE_AA)
    ret, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()

latest_frame = make_fallback_frame("KHOI TAO CAMERA...")

def camera_worker():
    global latest_frame
    cap = None
    while True:
        if cap is None or not cap.isOpened():
            # Quét tất cả các cổng video hiện có trên Jetson
            dev_list = sorted(glob.glob('/dev/video*'))
            found = False
            for dev in dev_list:
                try:
                    idx = int(dev.replace('/dev/video', ''))
                    # Thử mở camera bằng OpenCV chuẩn
                    test_cap = cv2.VideoCapture(idx)
                    if test_cap.isOpened():
                        test_cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                        test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                        test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                        test_cap.set(cv2.CAP_PROP_FPS, 30)
                        test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        ret, frame = test_cap.read()
                        if ret and frame is not None:
                            cap = test_cap
                            found = True
                            print(f"[CAMERA] Da ket noi thanh cong tai /dev/video{idx}")
                            break
                        else:
                            test_cap.release()
                except Exception:
                    pass

            if not found:
                with frame_lock:
                    latest_frame = make_fallback_frame("CAMERA CHUA CAM - DANG QUET CONG...")
                time.sleep(0.8)
                continue

        success, frame = cap.read()
        if success and frame is not None:
            ret, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
            if ret:
                with frame_lock:
                    latest_frame = buf.tobytes()
        else:
            if cap:
                try: cap.release()
                except: pass
            cap = None
            with frame_lock:
                latest_frame = make_fallback_frame("MAT KET NOI CAMERA - DANG TIM LAI...")
            time.sleep(0.5)
            
        time.sleep(0.02)

threading.Thread(target=camera_worker, daemon=True).start()

# ------------------------------------------------------------------------------
# 2. CẤU HÌNH VẬN HÀNH & KẾT NỐI SERIAL ARDUINO MEGA
# ------------------------------------------------------------------------------
config = {
    "max_linear_spd": 0.35,
    "max_strafe_spd": 0.30,
    "max_angular_spd": 1.40,
    "abs_brake_ramp": 0.15,
    "auto_line_speed": 0.30
}

ser = None
serial_lock = threading.Lock()
active_port = "DISCONNECTED"

def auto_connect_serial():
    global ser, active_port
    while True:
        ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        if ports:
            target = ports[0]
            if ser is None or not ser.is_open:
                try:
                    with serial_lock:
                        ser = serial.Serial(target, 115200, timeout=0.05)
                        active_port = target
                        print(f"[SERIAL] Ket noi: {target}")
                except Exception:
                    ser = None
                    active_port = "DISCONNECTED"
        else:
            if ser and ser.is_open:
                try: ser.close()
                except: pass
            ser = None
            active_port = "DISCONNECTED"
        time.sleep(1.0)

threading.Thread(target=auto_connect_serial, daemon=True).start()

# ------------------------------------------------------------------------------
# 3. QUẢN LÝ TỌA ĐỘ 3D: ĐI ĐẾN ĐÂU VẼ ĐẾN ĐÓ
# ------------------------------------------------------------------------------
state = {
    "x": 0.0, "y": 0.0, "angle": 0.0,
    "current_speed": 0.0,
    "target_vx": 0.0, "current_vx": 0.0,
    "target_vy": 0.0, "current_vy": 0.0,
    "target_omega": 0.0, "current_omega": 0.0,
    "line": "00000", "action": "STOP",
    "mode": "LÁI TAY", "total_dist": 0.0,
    "battery_v": 12.4, "battery_pct": 94,
    "jetson_temp": 40.0, "port": "DISCONNECTED",
    "wifi_info": "CHECKING..."
}

current_web_cmd = 'S'
last_action_receive_time = 0

def heartbeat_worker():
    global current_web_cmd
    while True:
        if ser and ser.is_open and current_web_cmd in ['F', 'B', 'L', 'R', 'Q', 'E']:
            try:
                with serial_lock:
                    ser.write(current_web_cmd.encode())
            except Exception: pass
        time.sleep(0.08)

threading.Thread(target=heartbeat_worker, daemon=True).start()

def udp_server_worker():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', 8888))
        while True:
            data, addr = sock.recvfrom(64)
            if data:
                c = data.decode(errors='ignore').strip().upper()
                if ser and ser.is_open:
                    with serial_lock:
                        ser.write(c.encode())
    except Exception:
        pass

threading.Thread(target=udp_server_worker, daemon=True).start()

def physics_and_telemetry_engine():
    global state, last_action_receive_time
    wifi_timer = 0
    while True:
        if ser and ser.is_open:
            try:
                raw = ser.readline().decode('utf-8', errors='ignore').strip()
                if "CHUYEN SANG" in raw:
                    if "TU HANH" in raw: 
                        state["mode"] = "TỰ HÀNH DÒ LINE + NÉ CẢN"
                    else: 
                        state["mode"] = "LÁI TAY"
                elif raw.startswith("DATA:"):
                    parts = raw.replace("DATA:", "").split(",")
                    if len(parts) >= 2:
                        state["line"] = parts[0]
                        act = parts[1]
                        state["action"] = act
                        if act != "STOP":
                            last_action_receive_time = time.time()
                    if len(parts) >= 3:
                        state["battery_v"] = float(parts[2])
            except Exception: pass

        ramp = config["abs_brake_ramp"]
        hw_connected = (ser is not None and ser.is_open)
        mode = state.get("mode", "LÁI TAY")

        if mode == "LÁI TAY":
            if current_web_cmd == 'S':
                state["target_vx"] = 0.0
                state["target_vy"] = 0.0
                state["target_omega"] = 0.0
                state["current_vx"] = 0.0
                state["current_vy"] = 0.0
                state["current_omega"] = 0.0
                state["action"] = "STOP"
        elif "TỰ HÀNH" in mode:
            if not hw_connected:
                state["target_vx"] = 0.0; state["target_vy"] = 0.0; state["target_omega"] = 0.0
                state["current_vx"] = 0.0; state["current_vy"] = 0.0; state["current_omega"] = 0.0
                state["action"] = "CHƯA KẾT NỐI XE (DỪNG)"
            else:
                if time.time() - last_action_receive_time < 0.40:
                    l_code = state.get("line", "00000")
                    if l_code != "00000":
                        state["target_vx"] = config["auto_line_speed"]; state["target_vy"] = 0.0
                        if l_code in ["01000", "01100", "11000"]:
                            state["target_omega"] = -0.50; state["action"] = "BÁM LINE TRÁI"
                        elif l_code in ["00010", "00110", "00011"]:
                            state["target_omega"] = 0.50; state["action"] = "BÁM LINE PHẢI"
                        elif l_code in ["10000"]:
                            state["target_omega"] = -1.10; state["action"] = "BẺ CUA TRÁI 90°"
                        elif l_code in ["00001"]:
                            state["target_omega"] = 1.10; state["action"] = "BẺ CUA PHẢI 90°"
                        else:
                            state["target_omega"] = 0.0; state["action"] = "TIẾN BÁM LINE"
                    else:
                        state["target_vx"] = 0.0; state["target_vy"] = 0.0; state["target_omega"] = 0.0
                        state["action"] = "MẤT LINE (DỪNG)"
                else:
                    state["target_vx"] = 0.0; state["target_vy"] = 0.0; state["target_omega"] = 0.0
                    state["current_vx"] = 0.0; state["current_vy"] = 0.0; state["current_omega"] = 0.0
                    state["action"] = "CHỜ XE THẬT HOẠT ĐỘNG"

        is_moving = (abs(state["current_vx"]) > 0.01 or abs(state["current_vy"]) > 0.01 or abs(state["current_omega"]) > 0.02)
        if is_moving:
            state["angle"] += state["current_omega"] * 0.04
            cos_a = math.cos(state["angle"])
            sin_a = math.sin(state["angle"])
            dx_w = (cos_a * state["current_vx"] - sin_a * state["current_vy"]) * 1.2
            dy_w = (sin_a * state["current_vx"] + cos_a * state["current_vy"]) * 1.2
            delta_step = math.hypot(dx_w, dy_w)
            if delta_step > 0.002 or abs(state["current_omega"]) > 0.02:
                state["x"] += dx_w
                state["y"] += dy_w
                state["total_dist"] += delta_step * 0.05
                state["current_speed"] = math.hypot(state["current_vx"], state["current_vy"])
            else:
                state["current_speed"] = 0.0
        else:
            state["current_speed"] = 0.0

        state["port"] = active_port

        wifi_timer += 1
        if wifi_timer % 50 == 0:
            try:
                state["wifi_info"] = subprocess.check_output("iwgetid -r 2>/dev/null", shell=True).decode().strip() or "MẠNG DÂY (ETH0)"
            except: state["wifi_info"] = "MẠNG DÂY (ETH0)"

        time.sleep(0.04)

threading.Thread(target=physics_and_telemetry_engine, daemon=True).start()

def generate_frames():
    while True:
        with frame_lock:
            frame_bytes = latest_frame
        if frame_bytes is not None:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>AGV Mecanum 3D Dashboard</title>
    <meta charset="utf-8">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Consolas, monospace; background: #080c14; color: #e2e8f0; margin: 0; padding: 10px; }
        header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 8px; border-bottom: 1px solid #1e293b; }
        .nav-tabs { display: flex; gap: 8px; }
        .tab-btn { background: #1e293b; color: #94a3b8; border: 1px solid #334155; padding: 7px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: bold; }
        .tab-btn.active { background: #0284c7; color: #fff; border-color: #38bdf8; }

        .main-layout { display: grid; grid-template-columns: 1fr 1.15fr; gap: 10px; margin-top: 8px; }
        .panel { background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 10px; }
        .panel-title { font-size: 11px; font-weight: bold; color: #94a3b8; margin-bottom: 6px; border-bottom: 1px solid #1f2937; padding-bottom: 3px; display: flex; justify-content: space-between; }
        
        .video-box { width: 100%; height: 260px; min-height: 260px; border-radius: 6px; overflow: hidden; border: 1px solid #334155; background: #000; position: relative; }
        #camera-feed { width: 100%; height: 100%; object-fit: cover; display: block; }
        #viewport-3d { width: 100%; height: 410px; border-radius: 6px; border: 1px solid #334155; position: relative; }

        .sensor-bar { display: flex; justify-content: center; gap: 8px; margin: 6px 0; background: #0b0f17; padding: 6px; border-radius: 5px; border: 1px solid #1e293b; }
        .s-node { width: 16px; height: 16px; border-radius: 50%; background: #1e293b; border: 2px solid #475569; }
        .s-active { background: #10b981; border-color: #34d399; box-shadow: 0 0 10px #10b981; }

        .grid-3x3 { display: grid; grid-template-columns: repeat(3, 95px); gap: 6px; justify-content: center; margin: 8px 0; }
        .pad-btn { height: 50px; font-size: 11px; font-weight: bold; background: #374151; color: #f3f4f6; border: 1px solid #4b5563; border-radius: 6px; cursor: pointer; user-select: none; display: flex; flex-direction: column; align-items: center; justify-content: center; }
        .pad-btn span { font-size: 9px; color: #9ca3af; font-weight: normal; margin-top: 2px; }
        .pad-btn:active, .pad-btn.active { background: #0284c7; border-color: #38bdf8; color: #fff; }
        .btn-stop { background: #991b1b; border-color: #dc2626; }
        .btn-mode-m { background: #1e3a8a; border-color: #3b82f6; }
        .btn-mode-m.auto-active { background: #059669 !important; border-color: #34d399 !important; }

        .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 5px; margin: 6px 0; }
        .metric-box { background: #0b0f17; border: 1px solid #1e293b; padding: 5px 3px; border-radius: 5px; text-align: center; }
        .m-title { font-size: 9px; color: #64748b; text-transform: uppercase; }
        .m-val { font-size: 12px; font-weight: bold; color: #38bdf8; margin-top: 2px; }

        .btn-tool { background: #1e293b; color: #fff; border: 1px solid #334155; padding: 4px 10px; font-size: 11px; border-radius: 4px; cursor: pointer; }
    </style>
</head>
<body>
    <header>
        <div class="nav-tabs">
            <button class="tab-btn active">🖥️ GIÁM SÁT & VẬN HÀNH</button>
        </div>
        <div style="display:flex; gap:6px; font-size:11px;">
            <div id="chip-port" style="background:#0f172a; border:1px solid #059669; padding:3px 8px; border-radius:4px; color:#34d399; font-weight:bold;">XE: ONLINE</div>
            <div id="chip-mode" style="background:#0f172a; border:1px solid #0284c7; padding:3px 8px; border-radius:4px; color:#38bdf8; font-weight:bold;">CHẾ ĐỘ: LÁI TAY</div>
        </div>
    </header>

    <div class="main-layout">
        <div class="panel">
            <div class="panel-title">
                <span>CAMERA HÀNH TRÌNH (HD 720p)</span>
                <span style="color:#10b981;">ONLINE</span>
            </div>
            <div class="video-box">
                <img id="camera-feed" src="/video_feed">
            </div>

            <div class="panel-title" style="margin-top:8px;">5 MẮT CẢM BIẾN DÒ LINE (S1 -> S5)</div>
            <div class="sensor-bar">
                <div id="s0" class="s-node" title="S1"></div>
                <div id="s1" class="s-node" title="S2"></div>
                <div id="s2" class="s-node" title="S3"></div>
                <div id="s3" class="s-node" title="S4"></div>
                <div id="s4" class="s-node" title="S5"></div>
            </div>

            <div class="grid-3x3">
                <button id="btn-Q" class="pad-btn" onmousedown="pressKey('Q')" onmouseup="releaseKey('Q')">XOAY T<span>(Q)</span></button>
                <button id="btn-W" class="pad-btn" onmousedown="pressKey('W')" onmouseup="releaseKey('W')">TIẾN<span>(W)</span></button>
                <button id="btn-E" class="pad-btn" onmousedown="pressKey('E')" onmouseup="releaseKey('E')">XOAY P<span>(E)</span></button>
                
                <button id="btn-A" class="pad-btn" onmousedown="pressKey('A')" onmouseup="releaseKey('A')">NGANG T<span>(A)</span></button>
                <button id="btn-SPACE" class="pad-btn btn-stop" onclick="emergencyStop()">DỪNG<span>(Space)</span></button>
                <button id="btn-D" class="pad-btn" onmousedown="pressKey('D')" onmouseup="releaseKey('D')">NGANG P<span>(D)</span></button>
                
                <button id="btn-Z" class="pad-btn" onclick="sendActionSingle('DEF')">DEF<span>(Z)</span></button>
                <button id="btn-S" class="pad-btn" onmousedown="pressKey('S')" onmouseup="releaseKey('S')">LÙI<span>(S)</span></button>
                <button id="btn-X" class="pad-btn btn-mode-m" onclick="toggleM()">M (MODE)<span>(X)</span></button>
            </div>
        </div>

        <div class="panel">
            <div class="panel-title">
                <span>BẢN ĐỒ QUỸ ĐẠO 3D & TRẠNG THÁI XE</span>
                <span id="txt-action" style="color:#38bdf8; font-weight:bold;">STOP</span>
            </div>
            <div id="viewport-3d"></div>

            <div class="metric-grid">
                <div class="metric-box"><div class="m-title">Tọa độ (X, Y)</div><div id="m-pos" class="m-val">0.0, 0.0</div></div>
                <div class="metric-box"><div class="m-title">Góc Xoay (θ)</div><div id="m-angle" class="m-val">0°</div></div>
                <div class="metric-box"><div class="m-title">Vận Tốc</div><div id="m-speed" class="m-val">0.00 m/s</div></div>
                <div class="metric-box"><div class="m-title">Quãng Đường</div><div id="m-dist" class="m-val">0.0 m</div></div>
                
                <div class="metric-box"><div class="m-title">Điện Áp Pin</div><div id="m-volt" class="m-val" style="color:#10b981;">12.4 V</div></div>
                <div class="metric-box"><div class="m-title">Chế Độ</div><div id="m-mode" class="m-val" style="color:#38bdf8; font-size:11px;">LÁI TAY</div></div>
                <div class="metric-box"><div class="m-title">Hành Động</div><div id="m-act" class="m-val">STOP</div></div>
                <div class="metric-box"><div class="m-title">Cổng USB</div><div id="m-port" class="m-val">USB0</div></div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;">
                <span style="font-size:10px; color:#64748b;">Đi đến đâu tự vẽ line đến đó (Dừng thì ngừng vẽ)</span>
                <div style="display:flex; gap:6px;">
                    <button onclick="resetToCenter()" class="btn-tool" style="background:#0284c7; font-weight:bold;">Về Tâm (0, 0)</button>
                    <button onclick="clearTrajectory()" class="btn-tool">Xóa Vệt Line</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        const container = document.getElementById('viewport-3d');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x050811);
        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
        camera.position.set(0, 160, 210);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(container.clientWidth, container.clientHeight);
        container.appendChild(renderer.domElement);
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        scene.add(new THREE.AmbientLight(0xffffff, 0.8));
        scene.add(new THREE.GridHelper(300, 30, 0x1e293b, 0x0f172a));

        const robot = new THREE.Group();
        const bMesh = new THREE.Mesh(new THREE.BoxGeometry(18, 7, 24), new THREE.MeshStandardMaterial({color: 0xf59e0b}));
        bMesh.position.y = 4;
        robot.add(bMesh);
        const arr = new THREE.Mesh(new THREE.ConeGeometry(3, 7, 4), new THREE.MeshBasicMaterial({color: 0x00ffcc}));
        arr.rotation.x = -Math.PI / 2;
        arr.position.set(0, 8, 9);
        robot.add(arr);
        scene.add(robot);

        const MAX_PTS = 5000;
        const positions = new Float32Array(MAX_PTS * 3);
        const trajGeo = new THREE.BufferGeometry();
        trajGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const trajLine = new THREE.Line(trajGeo, new THREE.LineBasicMaterial({ color: 0x00ffcc, linewidth: 3 }));
        scene.add(trajLine);

        let ptCount = 0;
        let lastPos = {x: 0, z: 0};

        function addTraj(x, z) {
            const dist = Math.hypot(x - lastPos.x, z - lastPos.z);
            if (dist > 0.25) {
                if (ptCount >= MAX_PTS) { 
                    positions.copyWithin(0, 3); 
                    ptCount = MAX_PTS - 1; 
                }
                positions[ptCount * 3] = x;
                positions[ptCount * 3 + 1] = 0.5;
                positions[ptCount * 3 + 2] = z;
                ptCount++;
                lastPos = {x: x, z: z};
                trajGeo.setDrawRange(0, ptCount);
                trajGeo.attributes.position.needsUpdate = true;
            }
        }

        function clearTrajectory() {
            ptCount = 0;
            trajGeo.setDrawRange(0, 0);
            trajGeo.attributes.position.needsUpdate = true;
            fetch('/reset_odometry');
        }

        function resetToCenter() {
            clearTrajectory();
            lastPos = {x: 0, z: 0};
            robot.position.set(0, 0, 0);
            robot.rotation.y = Math.PI / 2;
            camera.position.set(0, 160, 210);
            controls.target.set(0, 0, 0);
        }

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        animate();

        const keysHeld = {'W': false, 'S': false, 'A': false, 'D': false, 'Q': false, 'E': false};

        function syncMotion() {
            let drive = 0, strafe = 0, rotate = 0;
            if (keysHeld['W']) drive += 1;
            if (keysHeld['S']) drive -= 1;
            if (keysHeld['A']) strafe -= 1;
            if (keysHeld['D']) strafe += 1;
            if (keysHeld['Q']) rotate -= 1;
            if (keysHeld['E']) rotate += 1;
            fetch(`/mecanum_control?drive=${drive}&strafe=${strafe}&rotate=${rotate}`);
        }

        function pressKey(k) { keysHeld[k] = true; document.getElementById('btn-' + k)?.classList.add('active'); syncMotion(); }
        function releaseKey(k) { keysHeld[k] = false; document.getElementById('btn-' + k)?.classList.remove('active'); syncMotion(); }
        function toggleM() { fetch('/single_cmd?c=M'); }
        function sendActionSingle(act) { fetch('/single_cmd?c=' + act); }

        function emergencyStop() {
            for (let k in keysHeld) { keysHeld[k] = false; document.getElementById('btn-' + k)?.classList.remove('active'); }
            fetch('/mecanum_control?estop=1');
        }

        window.addEventListener('keydown', (e) => {
            if (e.repeat) return;
            const k = e.key.toUpperCase();
            if (keysHeld.hasOwnProperty(k)) pressKey(k);
            else if (k === 'X') toggleM();
            else if (k === 'Z') sendActionSingle('DEF');
            else if (e.code === 'Space') emergencyStop();
        });

        window.addEventListener('keyup', (e) => {
            const k = e.key.toUpperCase();
            if (keysHeld.hasOwnProperty(k)) releaseKey(k);
        });

        setInterval(() => {
            fetch('/telemetry').then(r => r.json()).then(data => {
                document.getElementById('chip-port').innerText = "XE: ONLINE (" + data.port + ")";
                document.getElementById('chip-mode').innerText = "CHẾ ĐỘ: " + data.mode;
                document.getElementById('m-mode').innerText = data.mode;
                document.getElementById('m-act').innerText = data.action;
                document.getElementById('txt-action').innerText = data.action;
                document.getElementById('m-volt').innerText = data.battery_v + " V";
                document.getElementById('m-port').innerText = data.port;
                document.getElementById('m-pos').innerText = `${data.x.toFixed(1)}, ${data.y.toFixed(1)}`;
                document.getElementById('m-angle').innerText = `${Math.round(data.angle * 180 / Math.PI)}°`;
                document.getElementById('m-speed').innerText = `${data.current_speed.toFixed(2)} m/s`;
                document.getElementById('m-dist').innerText = `${data.total_dist.toFixed(1)} m`;

                const btnM = document.getElementById('btn-X');
                if (data.mode.includes("TỰ HÀNH")) {
                    btnM.classList.add('auto-active');
                    btnM.innerHTML = "M (TỰ HÀNH)<span>(X)</span>";
                } else {
                    btnM.classList.remove('auto-active');
                    btnM.innerHTML = "M (MODE)<span>(X)</span>";
                }

                for (let i = 0; i < 5; i++) {
                    const el = document.getElementById('s' + i);
                    if (data.line[i] === '1') el.classList.add('s-active');
                    else el.classList.remove('s-active');
                }

                robot.position.set(data.x, 0, data.y);
                robot.rotation.y = -data.angle + Math.PI / 2;
                addTraj(data.x, data.y);
            });
        }, 50);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/mecanum_control')
def mecanum_control():
    global current_web_cmd
    drive = int(request.args.get('drive', 0))
    strafe = int(request.args.get('strafe', 0))
    rotate = int(request.args.get('rotate', 0))
    estop = request.args.get('estop', '0')

    if estop == '1' or (drive == 0 and strafe == 0 and rotate == 0):
        current_web_cmd = 'S'
        state["target_vx"] = 0.0
        state["target_vy"] = 0.0
        state["target_omega"] = 0.0
        state["current_vx"] = 0.0
        state["current_vy"] = 0.0
        state["current_omega"] = 0.0
        state["action"] = "STOP"
        if ser and ser.is_open:
            try:
                with serial_lock: ser.write(b"S")
            except: pass
        return jsonify({'status': 'stop'})

    if drive == 1:
        state["target_vx"] = config["max_linear_spd"]; state["target_vy"] = 0.0; state["target_omega"] = 0.0
        current_web_cmd = 'F'; state["action"] = "TIẾN"
    elif drive == -1:
        state["target_vx"] = -config["max_linear_spd"]; state["target_vy"] = 0.0; state["target_omega"] = 0.0
        current_web_cmd = 'B'; state["action"] = "LÙI"
    elif strafe == -1:
        state["target_vx"] = 0.0; state["target_vy"] = -config["max_strafe_spd"]; state["target_omega"] = 0.0
        current_web_cmd = 'L'; state["action"] = "NGANG TRÁI"
    elif strafe == 1:
        state["target_vx"] = 0.0; state["target_vy"] = config["max_strafe_spd"]; state["target_omega"] = 0.0
        current_web_cmd = 'R'; state["action"] = "NGANG PHẢI"
    elif rotate == -1:
        state["target_vx"] = 0.0; state["target_vy"] = 0.0; state["target_omega"] = -config["max_angular_spd"]
        current_web_cmd = 'Q'; state["action"] = "XOAY TRÁI"
    elif rotate == 1:
        state["target_vx"] = 0.0; state["target_vy"] = 0.0; state["target_omega"] = config["max_angular_spd"]
        current_web_cmd = 'E'; state["action"] = "XOAY PHẢI"

    state["current_vx"] = state["target_vx"]
    state["current_vy"] = state["target_vy"]
    state["current_omega"] = state["target_omega"]

    if ser and ser.is_open:
        try:
            with serial_lock: ser.write(current_web_cmd.encode())
        except: pass

    return jsonify({'status': 'ok'})


@app.route('/single_cmd')
def single_cmd():
    c = request.args.get('c', 'M').upper()
    if c == 'M':
        if state["mode"] == "LÁI TAY":
            state["mode"] = "TỰ HÀNH DÒ LINE + NÉ CẢN"
        else:
            state["mode"] = "LÁI TAY"
            state["target_vx"] = 0.0; state["target_vy"] = 0.0; state["target_omega"] = 0.0
            state["action"] = "STOP"
    elif c == 'DEF':
        state["mode"] = "LÁI TAY"
        state["target_vx"] = 0.0; state["target_vy"] = 0.0; state["target_omega"] = 0.0
        state["action"] = "STOP"

    if ser and ser.is_open:
        try:
            with serial_lock: ser.write(c.encode())
        except Exception: pass
    return jsonify({'status': 'ok', 'sent': c})

@app.route('/reset_odometry')
def reset_odometry():
    state["x"] = 0.0; state["y"] = 0.0; state["angle"] = 0.0; state["total_dist"] = 0.0; state["current_speed"] = 0.0
    return jsonify({'status': 'reset'})

@app.route('/telemetry')
def get_telemetry():
    return jsonify(state)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
