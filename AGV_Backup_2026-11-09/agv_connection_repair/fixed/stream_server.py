import os, sys, time, glob, math, json, threading
import cv2
import numpy as np
from flask import Flask, Response, render_template_string, jsonify, request

try:
    import serial
except ImportError:
    serial = None

from agv_serial_link import SafeMegaLink

app = Flask(__name__)

# ------------------------------------------------------------------------------
# TRẠNG THÁI HỆ THỐNG
# ------------------------------------------------------------------------------
state = {
    "x": 0.0, "y": 0.0, "angle": 0.0,
    "fwd": 0.0, "strafe": 0.0, "omega": 0.0,
    "current_speed": 0.0, "total_dist": 0.0,
    "mode": "LÁI TAY", "action": "STOP",
    "fsm_state": "IDLE",
    "avoid_step": 0,
    "last_line_time": time.time(),
    "line": "00000", "battery": 12.4, "port": "DISCONNECTED",
    "sonar": {"F": 120, "B": 180, "L": 75, "R": 80},
    "tuning": {
        "obs_cm": 22,
        "avoid_out_ms": 3300,
        "avoid_fwd_ms": 5400,
        "avoid_back_ms": 2300,
        "avoid_spd": 160,
        "base_spd": 120,
        "fast_spd": 190
    }
}

tuning_file = "/home/nguyennhutoan_uav/agv_tuning.json"
if os.path.exists(tuning_file):
    try:
        with open(tuning_file, "r") as f:
            saved = json.load(f)
            state["tuning"].update(saved)
    except Exception: pass

latest_frame = None
frame_lock = threading.Lock()
serial_lock = threading.Lock()
ser = None
link = SafeMegaLink(state, serial)
last_action_receive_time = time.time()

def make_fallback_frame():
    import numpy as np
    img = np.zeros((540, 960, 3), dtype=np.uint8)
    cv2.putText(img, "DANG KHOI DONG CAMERA...", (120, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    _, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return buf.tobytes()

# ==============================================================================
# BỘ DÒ LINE 1/4 ĐÁY KHUNG HÌNH & KẺ HÀNH LANG VÀNG BÁM DÍNH THEO DÁNG LINE
# ==============================================================================
def process_line_tracking(frame):
    if frame is None:
        return frame, False, 0

    h, w = frame.shape[:2]
    frame_center_x = w // 2

    # 1. Giới hạn vùng dò line đúng 1/4 đáy khung hình (từ 75% đến 100% chiều cao)
    roi_top = int(h * 0.75)
    roi_bottom = h
    roi = frame[roi_top:roi_bottom, 0:w]

    line_detected = False
    error_x = 0

    try:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # 2. Bộ lọc tương phản: blockSize = 31, C = 12 (Loại bỏ bóng râm và dây cáp)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 31, 12
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

        cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = cnts[0] if len(cnts) == 2 else cnts[1]

        candidates = []
        if contours:
            for c in contours:
                area = cv2.contourArea(c)
                if area > 400:  # Diện tích vạch tối thiểu
                    rect = cv2.minAreaRect(c)
                    (rx, ry), (rw, rh), angle = rect
                    long_side = max(rw, rh)
                    short_side = min(rw, rh) if min(rw, rh) > 0 else 1.0
                    aspect_ratio = float(long_side) / float(short_side)

                    # Ưu tiên dải vạch dài chạy dọc sàn
                    if aspect_ratio >= 1.6:
                        candidates.append((area, c, rect))

        if candidates:
            # Chọn vạch rõ nét và có diện tích tốt nhất
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_c = candidates[0][1]
            best_rect = candidates[0][2]

            M = cv2.moments(best_c)
            if M["m00"] > 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"]) + roi_top
                error_x = cx - frame_center_x
                line_detected = True

                # 3. KẺ 2 ĐƯỜNG VÀNG ÔM THEO DÁNG VẠCH (CHỈ HIỆN KHI KHÓA ĐƯỢC VẠCH)
                box = cv2.boxPoints(best_rect)
                box = np.int0(box)
                # Dịch tọa độ box từ ROI ra toàn khung hình
                box[:, 1] += roi_top

                # Sắp xếp 4 góc để xác định 2 mép cạnh dài của vạch
                edges = [
                    (box[0], box[1]),
                    (box[1], box[2]),
                    (box[2], box[3]),
                    (box[3], box[0])
                ]
                # Chọn 2 cạnh có chiều dài lớn nhất
                edges.sort(key=lambda e: np.linalg.norm(e[0] - e[1]), reverse=True)
                for pt1, pt2 in edges[:2]:
                    # Vẽ 2 đường viền màu vàng ôm sát hai bên mép vạch
                    cv2.line(frame, tuple(pt1), tuple(pt2), (0, 255, 255), 3)

                # Vẽ tâm vạch màu xanh lá & mũi tên điều hướng
                cv2.circle(frame, (cx, cy), 6, (0, 255, 0), -1)
                cv2.arrowedLine(frame, (frame_center_x, h - 15), (cx, h - 15), (0, 255, 0), 2)

        # 4. Hiển thị thông số (Không khóa được vạch thì hoàn toàn không vẽ vạch vàng)
        if line_detected:
            cv2.putText(frame, f"TRACK LOCKED | Err: {error_x:+d}px", (20, roi_top - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "TRACK SEARCHING...", (20, roi_top - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        # ----------------------------------------------------------------------
        # CHÈN THÊM: QUÉT VẬT CẢN 3/4 TRÊN & DUNG HỢP XÁC SUẤT NÉ CẢN
        # ----------------------------------------------------------------------
        try:
            # 1. Cắt riêng vùng 3/4 trên (từ đỉnh y=0 đến sát mép roi_top)
            roi_obs = frame[0:roi_top, 0:w]
            obs_gray = cv2.cvtColor(roi_obs, cv2.COLOR_BGR2GRAY)
            obs_blur = cv2.GaussianBlur(obs_gray, (5, 5), 0)
            obs_edges = cv2.Canny(obs_blur, 50, 150)
            
            obs_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            obs_dilated = cv2.dilate(obs_edges, obs_kernel, iterations=2)
            
            cnts_obs = cv2.findContours(obs_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours_obs = cnts_obs[0] if len(cnts_obs) == 2 else cnts_obs[1]
            
            max_obs_area = 0
            best_obs_box = None
            if contours_obs:
                for c in contours_obs:
                    c_area = cv2.contourArea(c)
                    # Chỉ bắt các khối vật cản lớn nằm trong hành lang di chuyển (vùng giữa 60% khung hình)
                    if c_area > 4000:
                        ox, oy, ow, oh = cv2.boundingRect(c)
                        center_ox = ox + ow // 2
                        if int(w * 0.20) < center_ox < int(w * 0.80):
                            if c_area > max_obs_area:
                                max_obs_area = c_area
                                best_obs_box = (ox, oy, ow, oh)
                                
            # 2. Tính xác suất vật cản từ Camera (0.0 đến 1.0)
            p_cam = min(1.0, max_obs_area / 22000.0)
            if p_cam < 0.25:
                p_cam = 0.0

            # 3. Đọc dữ liệu siêu âm và dung hợp xác suất
            sonar_f = 120
            is_connected = False
            if 'state' in globals() and isinstance(state, dict):
                sonar_f = state.get("sonar", {}).get("F", 120)
                is_connected = (state.get("port") != "DISCONNECTED")

            if sonar_f <= 20:
                p_sonar = 1.0
            elif sonar_f >= 45:
                p_sonar = 0.0
            else:
                p_sonar = (45.0 - float(sonar_f)) / 25.0

            # Nếu chưa cắm Arduino: Tin tưởng Camera 100% để test trực tiếp trên bàn
            # Khi đã cắm Arduino: Dung hợp 60% Siêu âm + 40% Camera
            if not is_connected:
                p_front_risk = p_cam
            else:
                p_front_risk = round(0.6 * p_sonar + 0.4 * p_cam, 2)

            # Cập nhật kết quả vào state để FSM xử lý
            if 'state' in globals() and isinstance(state, dict):
                state["p_cam_obs"] = p_cam
                state["fusion_risk"] = p_front_risk

            # 4. CHỈ VẼ KHUNG ĐỎ KHI CÓ VẬT CẢN THẬT (Bình thường để thoáng 100%)
            if best_obs_box is not None and p_cam >= 0.35:
                bx, by, bw, bh = best_obs_box
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 0, 255), 2)
                cv2.putText(frame, f"OBSTACLE: {int(p_cam*100)}% | Risk: {int(p_front_risk*100)}%", 
                            (bx, max(25, by - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
        except Exception:
            pass

    except Exception as e:
        cv2.putText(frame, f"ERR: {str(e)[:20]}", (20, roi_top - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    return frame, line_detected, error_x

 # ==============================================================================
# BỘ DUNG HỢP DỰ BÁO CAMERA + PHẢN XẠ 5 MẮT GẦM CUA GẤP 90 ĐỘ (CHUẨN AN TOÀN)
# ==============================================================================
def execute_line_following_fusion(err_x, line_code, far_curve_detected=False):
    """
    err_x: Sai số tâm từ camera 1/4 đáy (-350 đến +350 px)
    line_code: Trạng thái chuỗi 5 mắt gầm (vd: "00100", "10000", "00001", "11111")
    far_curve_detected: Camera nhìn xa phát hiện góc rẽ phía trước
    """
    # Khởi tạo an toàn kiểu dữ liệu
    safe_err_x = float(err_x) if err_x is not None else 0.0
    safe_code = str(line_code) if line_code else "00000"
    
    fwd = 0.45
    strafe = 0.0
    omega = 0.0
    action = "TIEN_BAM_LINE"
    is_corner_marker = False

    # --------------------------------------------------------------------------
    # TẦNG 1: PHẢN XẠ KHẨN CẤP TỪ 5 MẮT GẦM (ƯU TIÊN TUYỆT ĐỐI)
    # --------------------------------------------------------------------------
    # 1.1. Phát hiện Bệ Line (CẢ 5 MẮT CÙNG ĐÈ VẠCH ĐEN "11111") -> Ghi nhận mốc 4 góc
    if safe_code == "11111":
        action = "GHI_NHAN_MOC_GOC_4_CANH"
        fwd = 0.20
        strafe = 0.0
        omega = 0.0
        is_corner_marker = True
        return fwd, strafe, omega, action, is_corner_marker

    # 1.2. Mắt ngoài cùng S1 (Trái) chạm vạch -> Bẻ cua gấp 90 độ sang trái
    if safe_code in ["10000", "11000", "11100"]:
        action = "BE_CUA_TRAI_90_KHAN_CAP"
        fwd = 0.15
        strafe = 0.0
        omega = 0.70
        return fwd, strafe, omega, action, is_corner_marker

    # 1.3. Mắt ngoài cùng S5 (Phải) chạm vạch -> Bẻ cua gấp 90 độ sang phải
    elif safe_code in ["00001", "00011", "00111"]:
        action = "BE_CUA_PHAI_90_KHAN_CAP"
        fwd = 0.15
        strafe = 0.0
        omega = -0.70
        return fwd, strafe, omega, action, is_corner_marker

    # --------------------------------------------------------------------------
    # TẦNG 2: DỰ BÁO TẦM XA TỪ CAMERA (HÃM TỐC & DẠT ĐÓN GÓC)
    # --------------------------------------------------------------------------
    if far_curve_detected:
        fwd = 0.25
        action = "DON_GOC_CUA_TU_XA"

    # --------------------------------------------------------------------------
    # TẦNG 3: BÁM LINE MỊN BẰNG MECANUM (DÙNG ERR_X TỪ CAMERA 1/4 ĐÁY)
    # --------------------------------------------------------------------------
    # Giới hạn dạt ngang và góc xoay trong dải an toàn [-0.6, 0.6]
    calc_strafe = safe_err_x * 0.0025
    calc_omega = safe_err_x * 0.0015
    
    strafe = round(max(-0.6, min(0.6, calc_strafe)), 2)
    omega = round(max(-0.6, min(0.6, calc_omega)), 2)

    return fwd, strafe, omega, action, is_corner_marker
   
# ------------------------------------------------------------------------------
# CAMERA THỜI GIAN THỰC (TRIỆT TIÊU ĐỘ TRỄ)
# ------------------------------------------------------------------------------
def camera_worker():
    global latest_frame
    cap = None
    while True:
        if cap is None or not cap.isOpened():
            dev_list = sorted(glob.glob('/dev/video*'))
            found = False
            for dev in dev_list:
                try:
                    idx = int(dev.replace('/dev/video', ''))
                    test_cap = cv2.VideoCapture(idx)
                    if test_cap.isOpened():
                        test_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
                        test_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
                        test_cap.set(cv2.CAP_PROP_FPS, 30)
                        test_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        ret, frame = test_cap.read()
                        if ret and frame is not None:
                            cap = test_cap
                            found = True
                            break
                        else:
                            test_cap.release()
                except Exception: pass
            if not found:
                with frame_lock: latest_frame = make_fallback_frame()
                time.sleep(1.0)
                continue

        cap.grab()
        ret, frame = cap.read()
        if not ret or frame is None:
            if cap: cap.release()
            cap = None
            time.sleep(0.05)
            continue
# --- XỬ LÝ NHẬN DIỆN LINE AN TOÀN ---
        frame, has_line, err_x = process_line_tracking(frame)
        if 'state' in globals() and isinstance(state, dict):
            state["line_detected"] = has_line
            state["line_error"] = err_x
            # ------------------------------------
        ret, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 45])
        if ret:
            with frame_lock: latest_frame = buf.tobytes()
        time.sleep(0.015)

def generate_frames():
    while True:
        with frame_lock:
            f_data = latest_frame if latest_frame is not None else make_fallback_frame()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + f_data + b'\r\n')
        time.sleep(0.03)

# ----------------------------------------------------------------------
# THUẬT TOÁN ƯỚC LƯỢNG KHOẢNG CÁCH SIÊU ÂM (MEDIAN + EMA FILTER)
# ----------------------------------------------------------------------
from collections import deque

sonar_history = {
    'F': deque(maxlen=5),
    'B': deque(maxlen=5),
    'L': deque(maxlen=5),
    'R': deque(maxlen=5)
}
sonar_estimated = {'F': 120.0, 'B': 180.0, 'L': 75.0, 'R': 80.0}
ALPHA_SONAR = 0.65  # Trọng số thích nghi (khử rung và chống giật)

def estimate_sonar_distance(direction, raw_val):
    global sonar_history, sonar_estimated
    try:
        val = float(raw_val)
    except (ValueError, TypeError):
        return int(sonar_estimated.get(direction, 100))

    # 1. Triệt tiêu số ảo 999cm và khoảng cách âm/bằng 0 (Timeout từ Arduino)
    if val >= 400.0 or val <= 0.0:
        val_clean = 300.0  # Coi như không gian thoáng trong tầm 3 mét
    else:
        val_clean = val

    # 2. Lọc trung vị (Median Filter) qua 5 mẫu gần nhất để khử xung nhọn
    buf = sonar_history.get(direction)
    if buf is not None:
        buf.append(val_clean)
        sorted_buf = sorted(list(buf))
        median_val = sorted_buf[len(sorted_buf) // 2]
    else:
        median_val = val_clean

    # 3. Làm phẳng dao động bằng Exponential Moving Average (EMA)
    last_est = sonar_estimated.get(direction, 100.0)
    est_val = (ALPHA_SONAR * median_val) + ((1.0 - ALPHA_SONAR) * last_est)
    sonar_estimated[direction] = round(est_val, 1)
    
    return int(sonar_estimated[direction])

# ------------------------------------------------------------------------------
# GIAO TIẾP ARDUINO MEGA
# ------------------------------------------------------------------------------
def serial_worker():
    link.run()


# ------------------------------------------------------------------------------
# ĐỘNG HỌC XE 3D MECANUM
# ------------------------------------------------------------------------------
def physics_worker():
    # Khong co encoder: khong mo phong lenh thanh toa do/tocdo 'thuc'.
    while True:
        state['current_speed'] = 0.0
        state['odometry_available'] = False
        time.sleep(0.1)

        
# ------------------------------------------------------------------------------
# API ĐIỀU KHIỂN & CẤU HÌNH
# ------------------------------------------------------------------------------
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetry')
def telemetry():
    return jsonify(state)

@app.route('/toggle_mode')
def toggle_mode():
    target = 'MANUAL' if state.get('mode') == 'TỰ HÀNH' else 'AUTO'
    if not link.send('MODE:' + target):
        return jsonify(status='error', msg='Mega chưa kết nối/handshake'), 503
    return jsonify(status='queued', mode=state['mode'])


@app.route('/reset_origin')
def reset_origin():
    state["x"] = 0.0
    state["y"] = 0.0
    state["angle"] = 0.0
    state["total_dist"] = 0.0
    return jsonify({"status": "ok"})

@app.route('/save_tuning', methods=['POST'])
def save_tuning():
    return jsonify(status='error', msg='Firmware dùng hằng số. Chưa hỗ trợ nạp CFG qua web; không gửi cấu hình vào cổng motor.'), 501


@app.route('/mecanum_control')
def mecanum_control():
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

# ==============================================================================
# BỘ ĐIỀU KHIỂN MÁY TRẠNG THÁI FSM (TỰ HÀNH BÁM LINE & NÉ CẢN MECANUM)
# ==============================================================================


# ------------------------------------------------------------------------------
# GIAO DIỆN WEB: THREE.JS WEBGL PHỐI CẢNH 3D & ORBIT CONTROLS
# ------------------------------------------------------------------------------
HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>AGV Mecanum 3D Dashboard</title>
    <!-- Thư viện Three.js WebGL & OrbitControls chính thức -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; padding: 12px; background: #070d19; color: #fff; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
        .badge-title { background: #0070f3; padding: 6px 14px; border-radius: 6px; font-weight: bold; font-size: 14px; }
        .status-tags { display: flex; gap: 8px; font-size: 13px; font-weight: bold; }
        .tag { padding: 5px 12px; border-radius: 4px; border: 1px solid #1f2d4d; }
        .tag-online { background: #08211b; color: #00e676; border-color: #00e676; }
        .tag-mode { background: #0c1b33; color: #00b0ff; border-color: #00b0ff; }
        .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
        .panel { background: #0f172a; border: 1px solid #1e293b; border-radius: 8px; padding: 12px; }
        .panel-header { display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; color: #94a3b8; margin-bottom: 8px; border-bottom: 1px solid #1e293b; padding-bottom: 6px; }
        .cam-box { width: 100%; height: 260px; background: #000; border-radius: 6px; overflow: hidden; display: flex; align-items: center; justify-content: center; }
        .cam-box img { width: 100%; height: 100%; object-fit: cover; }
        .radar-box { background: #111a2e; border: 1px solid #1f2d4d; border-radius: 8px; padding: 8px 12px; margin: 10px 0; }
        .radar-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center; }
        .radar-card { background: #0b1324; padding: 6px; border-radius: 4px; border: 1px solid #1e293b; }
        .radar-val { font-size: 15px; font-weight: bold; color: #00ff88; }
        .sensor-line { display: flex; justify-content: center; gap: 12px; margin: 10px 0; padding: 8px; background: #111a2e; border-radius: 6px; border: 1px solid #1f2d4d; }
        .sensor-eye { width: 18px; height: 18px; border-radius: 50%; border: 2px solid #475569; background: #0f1f38; }
        .sensor-eye.active { background: #ff0055; border-color: #ff0055; box-shadow: 0 0 10px #ff0055; }
        .btn-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; max-width: 320px; margin: 0 auto; }
        .ctrl-btn { background: #1e293b; color: #fff; border: 1px solid #334155; padding: 10px 0; font-weight: bold; font-size: 12px; border-radius: 6px; cursor: pointer; user-select: none; }
        .ctrl-btn:active { background: #38bdf8; color: #000; }
        .btn-stop { background: #b91c1c; border-color: #ef4444; }
        .btn-mode { background: #1d4ed8; border-color: #3b82f6; }
        #canvas3d-container { width: 100%; height: 320px; background: #020617; border-radius: 6px; border: 1px solid #1e293b; overflow: hidden; position: relative; }
        .telemetry-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 10px; text-align: center; font-size: 12px; }
        .telem-card { background: #0b1324; padding: 6px; border-radius: 4px; border: 1px solid #1e293b; }
        .telem-val { font-size: 14px; font-weight: bold; color: #38bdf8; margin-top: 2px; }
        .telem-action { color: #f59e0b; }
        .telem-batt { color: #10b981; }
        .telem-port { color: #ef4444; }
        .btn-row { display: flex; justify-content: flex-end; gap: 8px; margin-top: 10px; }
        .action-btn { background: #0284c7; color: #fff; border: none; padding: 6px 12px; font-weight: bold; border-radius: 4px; cursor: pointer; font-size: 12px; }
        #tuningModal { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); z-index: 999999; justify-content: center; align-items: center; }
        .modal-card { background: #111a2e; border: 2px solid #00e5ff; border-radius: 10px; width: 500px; padding: 22px; box-shadow: 0 0 25px rgba(0, 229, 255, 0.4); }
        .modal-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; font-size: 13px; margin: 16px 0; }
        .modal-input { width: 100%; background: #070d19; color: #00ff88; border: 1px solid #334155; padding: 8px; border-radius: 4px; margin-top: 5px; font-size: 14px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="badge-title">GIÁM SÁT & VẬN HÀNH</div>
        <div class="status-tags">
            <div id="stat_conn" class="tag tag-online">XE: USB (<span id="port_txt">DISCONNECTED</span>)</div>
            <div id="stat_mode" class="tag tag-mode">CHẾ ĐỘ: LÁI TAY</div>
        </div>
    </div>

    <div class="main-grid">
        <div class="panel">
 <div class="panel-header"><span>CAMERA HÀNH TRÌNH (960x540)</span><span style="color:#00ff88">ONLINE</span></div>
<div class="cam-box" style="height: 420px; width: 100%; border-radius: 8px; overflow: hidden; background: #000;"><img src="/video_feed" alt="Camera Stream" style="width: 100%; height: 100%; object-fit: fill; display: block;"></div>

            <div class="radar-box">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <span style="font-size:12px; font-weight:bold; color:#00e5ff;">RADAR 4 CẢM BIẾN SIÊU ÂM</span>
                    <button id="btnOpenTuning" type="button" onclick="openTuningModal()" style="background:#00e5ff; color:#000; border:none; padding:6px 12px; font-weight:bold; border-radius:4px; cursor:pointer; font-size:11px;">⚙ HIỆU CHỈNH THÔNG SỐ (TUNING)</button>
                </div>
                <div class="radar-grid">
                    <div class="radar-card"><div style="font-size:10px; color:#94a3b8">TRƯỚC (F)</div><div id="snr_f" class="radar-val">-- cm</div></div>
                    <div class="radar-card"><div style="font-size:10px; color:#94a3b8">SAU (B)</div><div id="snr_b" class="radar-val">-- cm</div></div>
                    <div class="radar-card"><div style="font-size:10px; color:#94a3b8">TRÁI (L)</div><div id="snr_l" class="radar-val">-- cm</div></div>
                    <div class="radar-card"><div style="font-size:10px; color:#94a3b8">PHẢI (R)</div><div id="snr_r" class="radar-val">-- cm</div></div>
                </div>
            </div>

            <div style="font-size:11px; font-weight:bold; color:#94a3b8; margin-top:6px;">5 MẮT CẢM BIẾN DÒ LINE (S1 -> S5)</div>
            <div class="sensor-line">
                <div id="eye0" class="sensor-eye"></div>
                <div id="eye1" class="sensor-eye"></div>
                <div id="eye2" class="sensor-eye"></div>
                <div id="eye3" class="sensor-eye"></div>
                <div id="eye4" class="sensor-eye"></div>
            </div>

            <div class="btn-grid">
                <button class="ctrl-btn" data-act="Q">XOAY T<br>(Q)</button>
                <button class="ctrl-btn" data-act="W">TIẾN<br>(W)</button>
                <button class="ctrl-btn" data-act="E">XOAY P<br>(E)</button>
                <button class="ctrl-btn" data-act="A">NGANG T<br>(A)</button>
                <button class="ctrl-btn btn-stop" data-act="S">DỪNG<br>(Space)</button>
                <button class="ctrl-btn" data-act="D">NGANG P<br>(D)</button>
                <button class="ctrl-btn" data-act="Z">DEF<br>(Z)</button>
                <button class="ctrl-btn" data-act="B">LÙI<br>(S)</button>
                <button class="ctrl-btn btn-mode" data-act="X">M (MODE)<br>(X)</button>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header"><span>BẢN ĐỒ QUỸ ĐẠO 3D & TRẠNG THÁI XE</span><span style="color:#38bdf8">TRACKING</span></div>
            <div id="canvas3d-container"></div>

            <div class="telemetry-grid">
                <div class="telem-card"><div>TỌA ĐỘ (X, Y)</div><div id="val_pos" class="telem-val">0.0, 0.0</div></div>
                <div class="telem-card"><div>GÓC XOAY (θ)</div><div id="val_deg" class="telem-val">0.0°</div></div>
                <div class="telem-card"><div>VẬN TỐC</div><div id="val_spd" class="telem-val">0.00 m/s</div></div>
                <div class="telem-card"><div>QUÃNG ĐƯỜNG</div><div id="val_dist" class="telem-val">0.0 m</div></div>
                <div class="telem-card"><div>ĐIỆN ÁP PIN</div><div id="val_volt" class="telem-val telem-batt">12.4 V</div></div>
                <div class="telem-card"><div>CHẾ ĐỘ</div><div id="val_mode" class="telem-val telem-action">LÁI TAY</div></div>
                <div class="telem-card"><div>HÀNH ĐỘNG</div><div id="val_act" class="telem-val telem-action">STOP</div></div>
                <div class="telem-card"><div>CỔNG USB</div><div id="val_port" class="telem-val telem-port">DISCONNECTED</div></div>
            </div>

            <div class="btn-row">
                <button class="action-btn" onclick="resetOrigin()">Về Tâm (0, 0)</button>
                <button class="action-btn" onclick="clearLine()">Xóa Vệt Line</button>
            </div>
        </div>
    </div>

    <!-- MODAL TUNING -->
    <div id="tuningModal" onclick="if(event.target === this) closeTuningModal()">
        <div class="modal-card">
            <h3 style="margin-top:0; color:#00e5ff; border-bottom:1px solid #1e293b; padding-bottom:8px;">BẢNG HIỆU CHỈNH THÔNG SỐ XE (TUNING)</h3>
            <div class="modal-grid">
                <div><label>Khoảng cách né cản (cm):</label><input id="cfg_obs" type="number" class="modal-input"></div>
                <div><label>Tốc độ dạt ngang (PWM):</label><input id="cfg_spd" type="number" class="modal-input"></div>
                <div><label>Dạt ngang ra né (ms):</label><input id="cfg_out" type="number" class="modal-input"></div>
                <div><label>Tiến vượt vật cản (ms):</label><input id="cfg_fwd" type="number" class="modal-input"></div>
                <div><label>Dạt ngược về line (ms):</label><input id="cfg_back" type="number" class="modal-input"></div>
                <div><label>Tốc độ bứt tốc thẳng (PWM):</label><input id="cfg_fast" type="number" class="modal-input"></div>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:15px;">
                <button type="button" onclick="closeTuningModal()" style="background:#475569; color:#fff; border:none; padding:8px 16px; border-radius:4px; cursor:pointer; font-weight:bold;">HỦY</button>
                <button type="button" onclick="saveTuningData()" style="background:#00e676; color:#000; font-weight:bold; border:none; padding:8px 20px; border-radius:4px; cursor:pointer;">💾 LƯU & NẠP VÀO XE</button>
            </div>
        </div>
    </div>

    <script>
        // ---------------------------------------------------------------------
        // KHỞI TẠO THREE.JS WEBGL CHUẨN VỚI ORBIT CONTROLS
        // ---------------------------------------------------------------------
        const container = document.getElementById('canvas3d-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x020617);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
        camera.position.set(0, -60, 45);
        camera.up.set(0, 0, 1); // Trục Z hướng lên trên

        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.08;
        controls.maxPolarAngle = Math.PI / 2 - 0.05; // Không cho xoay chìm dưới mặt đất

        // Lưới 3D chuẩn màu xanh đậm và xanh ngọc
        const gridHelper = new THREE.GridHelper(120, 30, 0x00e5ff, 0x142038);
        gridHelper.rotation.x = Math.PI / 2;
        scene.add(gridHelper);

        // Ánh sáng
        const ambLight = new THREE.AmbientLight(0xffffff, 0.8);
        scene.add(ambLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
        dirLight.position.set(20, -30, 40);
        scene.add(dirLight);

        // Mô hình xe AGV Mecanum 3D
        const carGroup = new THREE.Group();

        // Khối thân xe màu cam
        const bodyGeo = new THREE.BoxGeometry(7, 11, 3.2);
        const bodyMat = new THREE.MeshLambertMaterial({ color: 0xf59e0b });
        const carBody = new THREE.Mesh(bodyGeo, bodyMat);
        carBody.position.z = 1.6;
        carGroup.add(carBody);

        // Mũi tên chỉ hướng tiến màu xanh ngọc
        const arrowGeo = new THREE.ConeGeometry(1.8, 3.2, 3);
        const arrowMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
        const arrowMesh = new THREE.Mesh(arrowGeo, arrowMat);
        arrowMesh.position.set(0, 6.2, 2.2);
        arrowMesh.rotation.z = Math.PI;
        arrowMesh.rotation.x = Math.PI / 2;
        carGroup.add(arrowMesh);

        scene.add(carGroup);

        // Đường vẽ Line lịch sử
        const maxPoints = 3000;
        const lineGeo = new THREE.BufferGeometry();
        const positions = new Float32Array(maxPoints * 3);
        lineGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const lineMat = new THREE.LineBasicMaterial({ 
    color: 0x00ffff,       // Đổi sang màu Cyan sáng rực (xanh dạ quang nổi bật trên nền đen)
    linewidth: 5, 
    transparent: true, 
    opacity: 1.0 
});
        const pathLine = new THREE.Line(lineGeo, lineMat);
        scene.add(pathLine);

        let ptCount = 0;
        function addPathPoint(x, y) {
            if (ptCount < maxPoints) {
                positions[ptCount * 3]     = x;
                positions[ptCount * 3 + 1] = y;
                positions[ptCount * 3 + 2] = 0.2;
                ptCount++;
                lineGeo.setDrawRange(0, ptCount);
                lineGeo.attributes.position.needsUpdate = true;
            }
        }

        function clearLine() {
            ptCount = 0;
            lineGeo.setDrawRange(0, 0);
            lineGeo.attributes.position.needsUpdate = true;
        }

        function resetOrigin() {
            fetch('/reset_origin').then(() => { clearLine(); });
        }

        window.addEventListener('resize', () => {
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        });

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        animate();

        // ---------------------------------------------------------------------
        // MODAL TUNING POPUP
        // ---------------------------------------------------------------------
        window.openTuningModal = function() {
            const m = document.getElementById('tuningModal');
            if (m) m.style.display = 'flex';
            fetch('/telemetry').then(r => r.json()).then(d => {
                let t = d.tuning || {};
                if (document.getElementById('cfg_obs'))  document.getElementById('cfg_obs').value  = t.obs_cm || 22;
                if (document.getElementById('cfg_spd'))  document.getElementById('cfg_spd').value  = t.avoid_spd || 160;
                if (document.getElementById('cfg_out'))  document.getElementById('cfg_out').value  = t.avoid_out_ms || 3300;
                if (document.getElementById('cfg_fwd'))  document.getElementById('cfg_fwd').value  = t.avoid_fwd_ms || 5400;
                if (document.getElementById('cfg_back')) document.getElementById('cfg_back').value = t.avoid_back_ms || 2300;
                if (document.getElementById('cfg_fast')) document.getElementById('cfg_fast').value = t.fast_spd || 190;
            }).catch(e => console.log(e));
        };

        window.closeTuningModal = function() {
            const m = document.getElementById('tuningModal');
            if (m) m.style.display = 'none';
        };

        window.saveTuningData = function() {
            let payload = {
                obs_cm: parseInt(document.getElementById('cfg_obs').value),
                avoid_spd: parseInt(document.getElementById('cfg_spd').value),
                avoid_out_ms: parseInt(document.getElementById('cfg_out').value),
                avoid_fwd_ms: parseInt(document.getElementById('cfg_fwd').value),
                avoid_back_ms: parseInt(document.getElementById('cfg_back').value),
                base_spd: 120,
                fast_spd: parseInt(document.getElementById('cfg_fast').value)
            };
            fetch('/save_tuning', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(res => {
                alert(res.msg);
                closeTuningModal();
            });
        };

        // ---------------------------------------------------------------------
        // TELEMETRY & ĐỒNG BỘ 3D
        // ---------------------------------------------------------------------
        setInterval(() => {
            fetch('/telemetry').then(r => r.json()).then(d => {
                document.getElementById('val_pos').innerText = 'CHƯA CÓ ODOM';
                document.getElementById('val_deg').innerText = '—';
                document.getElementById('val_spd').innerText = 'CHƯA ĐO';
                document.getElementById('val_dist').innerText = '—';
                document.getElementById('val_volt').innerText = d.battery.toFixed(1) + ' V';
                let showMode = d.mode || 'LÁI TAY';
        document.getElementById('val_mode').innerText = showMode;
        document.getElementById('val_act').innerText = d.action;
        document.getElementById('stat_mode').innerText = 'CHẾ ĐỘ: ' + showMode;

                let pEl = document.getElementById('val_port');
                pEl.innerText = d.port;
                pEl.style.color = (d.port !== 'DISCONNECTED') ? '#00ff88' : '#ef4444';
                document.getElementById('port_txt').innerText = d.port;
                document.getElementById('stat_conn').style.color = d.connected ? '#00ff88' : '#ef4444';
                document.getElementById('stat_conn').title = d.serial_error || '';

                let setS = (id, v) => {
                    let el = document.getElementById(id);
                    el.innerText = v + ' cm';
                    el.style.color = (v <= 25) ? '#ff0055' : ((v <= 50) ? '#f59e0b' : '#00ff88');
                };
                setS('snr_f', d.sonar.F);
                setS('snr_b', d.sonar.B);
                setS('snr_l', d.sonar.L);
                setS('snr_r', d.sonar.R);

                let l = d.line || '00000';
                for (let i = 0; i < 5; i++) {
                    let eye = document.getElementById('eye' + i);
                    if (l[i] === '1') eye.classList.add('active');
                    else eye.classList.remove('active');
                }

                // Cập nhật vị trí và góc quay Three.js
                carGroup.position.set(d.x, d.y, 0);
                carGroup.rotation.z = d.angle * Math.PI / 180;

                if (d.current_speed > 0.02 || Math.abs(d.omega) > 0.05) {
                    addPathPoint(d.x, d.y);
                }
            }).catch(()=>{});
        }, 40);

        // ---------------------------------------------------------------------
        // ĐIỀU KHIỂN BÀN PHÍM PHẦN CỨNG & CHUỘT
        // ---------------------------------------------------------------------
        function driveCmd(d, s, r) {
            fetch('/mecanum_control?drive=' + d + '&strafe=' + s + '&rotate=' + r);
        }
        function stopCmd() {
            stopKeyLoop();
            if (activeBtnTimer) { clearInterval(activeBtnTimer); activeBtnTimer = null; }
            fetch('/mecanum_control?drive=0&strafe=0&rotate=0&estop=1');
        }

        // ======================================================================
// CƠ CHẾ REPEATABLE 80MS ĐỒNG BỘ 100% CẤU HÌNH APP ĐIỀU KHIỂN
// ======================================================================
let activeKeyTimer = null;
let currentPressedKey = null;

const KEY_COMMANDS = {
    'KeyW': [1, 0, 0],    // Tiến
    'KeyS': [-1, 0, 0],   // Lùi
    'KeyA': [0, -1, 0],   // Dạt trái
    'KeyD': [0, 1, 0],    // Dạt phải
    'KeyQ': [0, 0, -1],   // Xoay trái
    'KeyE': [0, 0, 1]     // Xoay phải
};

function sendCurrentKey() {
    if (currentPressedKey && KEY_COMMANDS[currentPressedKey]) {
        let [d, s, r] = KEY_COMMANDS[currentPressedKey];
        driveCmd(d, s, r);
    }
}

function stopKeyLoop() {
    if (activeKeyTimer) {
        clearInterval(activeKeyTimer);
        activeKeyTimer = null;
    }
    currentPressedKey = null;
}

// 1. KHI NHẤN GIỮ PHÍM: BẮN GÓI ĐẦU TIÊN TỨC THÌ & LẶP MỖI 80MS ĐỂ NUÔI FAILSAFE
window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' || e.code === 'KeyZ') {
        stopKeyLoop();
        stopCmd();
        return;
    }
    if (e.code === 'KeyX' && !e.repeat) {
        fetch('/toggle_mode');
        return;
    }

    if (KEY_COMMANDS[e.code]) {
        if (currentPressedKey === e.code) return; // Đang giữ phím này rồi thì để timer 80ms tự lo
        
        currentPressedKey = e.code;
        sendCurrentKey(); // Bắn ngay lệnh đầu tiên dưới 5ms

        if (activeKeyTimer) clearInterval(activeKeyTimer);
        activeKeyTimer = setInterval(sendCurrentKey, 80); // Lặp lại đúng chu kỳ 80ms của App
    }
});

// 2. KHI NHẢ TAY KHỎI BÀN PHÍM: HỦY TIMER VÀ PHANH DỪNG XE TỨC KHẮC
window.addEventListener('keyup', (e) => {
    if (KEY_COMMANDS[e.code] && currentPressedKey === e.code) {
        stopKeyLoop();
        stopCmd(); // Gửi lệnh phanh 'S' về Arduino
    }
});

// Chống kẹt phím nếu người dùng click chuột ra ngoài hoặc chuyển tab
window.addEventListener('blur', () => {
    if (activeBtnTimer) { clearInterval(activeBtnTimer); activeBtnTimer = null; }
    stopKeyLoop();
    stopCmd();
});

const BTN_MAP = {
    'W': () => driveCmd(1, 0, 0),     // Tiến
    'B': () => driveCmd(-1, 0, 0),    // Lùi
    'A': () => driveCmd(0, -1, 0),    // Ngang Trái (chuẩn theo data-act="A")
    'D': () => driveCmd(0, 1, 0),     // Ngang Phải (chuẩn theo data-act="D")
    'L': () => driveCmd(0, -1, 0),    // Dự phòng data-act="L"
    'R': () => driveCmd(0, 1, 0),     // Dự phòng data-act="R"
    'Q': () => driveCmd(0, 0, -1),    // Xoay Trái
    'E': () => driveCmd(0, 0, 1)      // Xoay Phải
};

    // ======================================================================
    // BỘ ĐẾM LẶP 80MS CHO NÚT BẤM CHUỘT VÀ CẢM ỨNG ĐIỆN THOẠI
    // ======================================================================
    let activeBtnTimer = null;

    function startBtnHold(act) {
        if (activeBtnTimer) clearInterval(activeBtnTimer);
        if (BTN_MAP[act]) {
            BTN_MAP[act](); // Bắn gói lệnh đầu tiên tức thì
            activeBtnTimer = setInterval(() => {
                BTN_MAP[act](); // Bơm lệnh liên tục mỗi 80ms để duy trì chạy
            }, 80);
        }
    }

    function stopBtnHold() {
        if (activeBtnTimer) {
            clearInterval(activeBtnTimer);
            activeBtnTimer = null;
        }
        stopCmd(); // Gửi lệnh dừng phanh xe ngay khi nhả tay
    }

    document.querySelectorAll('.ctrl-btn').forEach(btn => {
        let act = btn.getAttribute('data-act');
        if (act === 'X') {
            btn.onclick = () => fetch('/toggle_mode');
        } else if (act === 'Z' || act === 'S') {
            btn.onclick = () => stopCmd();
        } else if (BTN_MAP[act]) {
            // Xử lý giữ/nhả chuột trên Máy tính (Laptop)
            btn.onmousedown = (e) => { e.preventDefault(); startBtnHold(act); };
            btn.onmouseup = (e) => { e.preventDefault(); stopBtnHold(); };
            btn.onmouseleave = (e) => { e.preventDefault(); stopBtnHold(); };

            // Xử lý chạm/giữ/nhả bằng ngón tay trên Điện thoại
            btn.ontouchstart = (e) => { e.preventDefault(); startBtnHold(act); };
            btn.ontouchend = (e) => { e.preventDefault(); stopBtnHold(); };
            btn.ontouchcancel = (e) => { e.preventDefault(); stopBtnHold(); };
        }
    });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

# ==============================================================================
# BỘ ĐIỀU KHIỂN MÁY TRẠNG THÁI FSM (TỰ HÀNH BÁM LINE & NÉ CẢN MECANUM)
# ==============================================================================
def fsm_controller_worker():
    # AUTO do Mega xu ly. Camera chi giam sat, khong co vong dieu khien thu hai.
    while True:
        state['fsm_state'] = 'ARDUINO_AUTO' if state.get('mode') == 'TỰ HÀNH' else 'IDLE'
        time.sleep(0.1)


if __name__ == '__main__':
    t_cam = threading.Thread(target=camera_worker, daemon=True)
    t_ser = threading.Thread(target=serial_worker, daemon=True)
    t_phy = threading.Thread(target=physics_worker, daemon=True)
    t_fsm = threading.Thread(target=fsm_controller_worker, daemon=True)
    t_cam.start()
    t_ser.start()
    t_phy.start()
    t_fsm.start()
    app.run(host='0.0.0.0', port=5000, threaded=True)


