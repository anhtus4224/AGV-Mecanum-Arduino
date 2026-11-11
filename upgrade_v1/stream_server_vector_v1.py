import os, sys, time, glob, math, json, threading
import cv2
import numpy as np
from flask import Flask, Response, render_template_string, jsonify, request

try:
    import serial
except ImportError:
    serial = None

app = Flask(__name__)
SERVER_VERSION = "VECTOR_AVOID_V1"

# ------------------------------------------------------------------------------
# TRẠNG THÁI HỆ THỐNG
# ------------------------------------------------------------------------------
state = {
    "x": 0.0, "y": 0.0, "angle": 0.0,
    "fwd": 0.0, "strafe": 0.0, "omega": 0.0,
    "current_speed": 0.0, "total_dist": 0.0,
    "mode": "CHƯA XÁC NHẬN", "action": "STOP",
    "telemetry_valid": False, "mode_confirmed": False, "mode_pending": False,
    "serial_error": "", "last_tx": "", "odometry_measured": False,
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
serial_lock = threading.RLock()
ser = None
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
                box = box.astype(np.intp)
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
            state["camera_frame_time"] = time.monotonic()
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
    est_val = min(val_clean, (ALPHA_SONAR * median_val) + ((1.0 - ALPHA_SONAR) * last_est)) # React immediately to an approaching object; display filter only
    sonar_estimated[direction] = round(est_val, 1)
    
    return int(sonar_estimated[direction])

# ------------------------------------------------------------------------------
# GIAO TIẾP ARDUINO MEGA
# ------------------------------------------------------------------------------
# Adapter for the ORIGINAL agv_mega_controller.ino (single-character USB protocol).
# This firmware has NO framed handshake, ACK or AUTO host watchdog.
rx_time = 0.0
data_time = 0.0
mode_time = 0.0
last_toggle_request = 0.0
link_ready = False
firmware_seen = False


def clear_link(reason):
    global link_ready, firmware_seen, rx_time, data_time, mode_time, motion_feedback
    motion_feedback = None
    visual_untracked('Mất USB; không biết xe đã di chuyển tới đâu')
    visual_command('Z','real')
    invalidate_map_pose('Mất kết nối Mega; vị trí cuối chỉ để tham khảo')
    link_ready = firmware_seen = False
    rx_time = data_time = mode_time = 0.0
    state.update(port='DISCONNECTED', mode='CHƯA XÁC NHẬN', action='STOP',
                 serial_error=reason, telemetry_valid=False, mode_confirmed=False, mode_pending=False,
                 fwd=0.0, strafe=0.0, omega=0.0, current_speed=0.0)


def parse_mega_line(line):
    global rx_time, data_time, mode_time, firmware_seen, last_action_receive_time
    now = time.monotonic()
    if line.startswith('>> CORNER ') or line.startswith('>> CORNER_FAULT:'):
        corner_feedback_event(line, now)
        return
    if line.startswith('MOTION:'):
        return parse_motion_feedback(line, now)
    if line.startswith('DATA:'):
        parts = line[5:].split(',')
        if len(parts) != 3 or len(parts[0]) != 5 or set(parts[0]) - set('01'):
            return
        volts = float(parts[2])
        if not math.isfinite(volts): return
        if parts[1] != 'STOP': invalidate_map_pose('Mega báo lệnh chuyển động; chưa có phép đo vị trí mới')
        state.update(line=parts[0], battery=volts, action=parts[1])
        data_time = rx_time = now
        last_action_receive_time = time.time()
    elif line.startswith('SONAR:'):
        parts = line[6:].split(',')
        if len(parts) != 4: return
        values = [int(x) for x in parts]
        if not all(0 <= x <= 999 for x in values): return
        state['sonar_raw'] = dict(zip(('F','B','L','R'), values))
        # Retain the original sonar filter, only feed it valid packets.
        state['sonar'] = {k: estimate_sonar_distance(k, v)
                          for k, v in zip(('F','B','L','R'), values)}
        rx_time = now
    elif line.startswith('ADC5:'):
        parts = [int(x) for x in line[5:].split(',')]
        if len(parts) == 5: state['line_adc'] = parts; rx_time = now
    elif line.startswith('>> HB fw=AGV_CHUANDET_90_V2 '):
        firmware_seen = True
        if ' mode=AUTO ' in line:
            state['mode'] = 'TỰ HÀNH'
            if not auto_pwm_fresh(now): visual_untracked('AUTO chờ phản hồi PWM bốn bánh')
            invalidate_map_pose('Mega đang AUTO; chưa có định vị liên tục')
        elif ' mode=MANUAL ' in line: state['mode'] = 'LÁI TAY'
        else: return
        mode_time = rx_time = now
        state['mode_pending'] = False
    elif line.startswith('>> [AGV_CHUANDET_90_V2 READY]'):
        firmware_seen = True; rx_time = now
    elif 'CHUYEN SANG -> TU HANH DO LINE' in line:
        if not auto_pwm_fresh(now): visual_untracked('AUTO chờ phản hồi PWM bốn bánh')
        invalidate_map_pose('Mega xác nhận AUTO; chưa có định vị liên tục')
        state.update(mode='TỰ HÀNH', mode_pending=False); mode_time = rx_time = now
    elif ('CHUYEN SANG -> LAI TAY' in line or line == '>> VE CHE DO LAI TAY'
          or line == '>> PHIM LAI TAY -> THOAT TU HANH, VE LAI TAY'):
        state.update(mode='LÁI TAY', mode_pending=False); mode_time = rx_time = now


def serial_worker():
    global ser, link_ready
    clear_link('Đang tìm Mega gốc; không dùng với SAFE1')
    while True:
        if driving_environment == 'simulation':
            time.sleep(0.5)
            continue
        candidate = None
        try:
            if serial is None: raise RuntimeError('Thiếu python3-serial')
            ports = [os.environ['AGV_PORT']] if os.environ.get('AGV_PORT') else sorted(glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*'))
            for port in ports:
                try:
                    clear_link('Đang nhận diện Mega')
                    candidate = serial.Serial(port, 115200, timeout=0.05,
                                              write_timeout=0.2, exclusive=True)
                    time.sleep(2.0) # opening USB can reset Mega
                    with serial_lock:
                        if driving_environment != 'real': raise RuntimeError('Đã chuyển sang mô phỏng')
                        candidate.write(b'Z') # explicit MANUAL/STOP; never send CFG
                    deadline = time.monotonic() + 3.0
                    while time.monotonic() < deadline:
                        line = candidate.readline(512).decode('utf-8', errors='replace').strip()
                        try: parse_mega_line(line)
                        except (ValueError, TypeError, OverflowError) as exc:
                            print('[SERIAL malformed]', repr(line), str(exc), flush=True)
                        if firmware_seen and data_time and mode_time and state['mode'] == 'LÁI TAY':
                            break
                    else: raise RuntimeError('Không nhận đủ định danh, DATA và chế độ MANUAL của Mega gốc')
                    with serial_lock:
                        if driving_environment != 'real': raise RuntimeError('Đã chuyển sang mô phỏng')
                        ser = candidate; link_ready = True
                        state.update(port=os.path.basename(port), serial_error='')
                    print('[SERIAL connected]', port, flush=True)
                    break
                except Exception as exc:
                    print('[SERIAL open]', port, str(exc), flush=True)
                    if candidate is not None: candidate.close()
                    candidate = None
            if candidate is None: raise RuntimeError('Không tìm thấy Mega tương thích')
            while True:
                line = candidate.readline(512).decode('utf-8', errors='replace').strip()
                if line:
                    try: parse_mega_line(line)
                    except (ValueError, TypeError, OverflowError) as exc:
                        print('[SERIAL malformed]', repr(line), str(exc), flush=True)
                # Old Mega does not send telemetry during blocking avoidance.
                # Do not reset its USB merely because an avoidance cycle is quiet.
                state['telemetry_valid'] = time.monotonic() - data_time < 2.0
                state['mode_confirmed'] = time.monotonic() - mode_time < 2.0
        except Exception as exc:
            print('[SERIAL error]', str(exc), flush=True)
            with serial_lock:
                clear_link(str(exc))
                if candidate is not None:
                    try:
                        if driving_environment == 'real': candidate.write(b'Z')
                    except Exception: pass
                    candidate.close()
                ser = None
            time.sleep(1.0)


def send_mega(command):
    global last_toggle_request
    if command not in ('F','B','L','R','Q','E','Z','M'):
        raise ValueError('Command not allowed')
    with serial_lock:
        if driving_environment != 'real': return {'status':'error','msg':'USB lái bị khóa trong Mô phỏng','sent':False},409
        if not link_ready or ser is None or not ser.is_open:
            return {'status':'error', 'msg':'Mega chưa kết nối/nhận diện', 'sent':False}, 503
        if command != 'Z' and time.monotonic() - rx_time > 2.0:
            return {'status':'error', 'msg':'Dữ liệu Mega đã cũ; vẫn có thể gửi STOP', 'sent':False}, 503
        if command == 'M':
            if state.get('mode_pending') or time.monotonic()-last_toggle_request < 1.0:
                return {'status':'busy', 'msg':'Đang chờ chế độ Mega'}, 409
            if time.monotonic()-mode_time > 2.0:
                return {'status':'error', 'msg':'Chưa xác nhận chế độ Mega'}, 409
        try:
            if ser.write(command.encode('ascii')) != 1: raise IOError('Short serial write')
        except Exception as exc:
            try: ser.close()
            except Exception: pass
            clear_link(str(exc))
            return {'status':'error','msg':str(exc),'sent':False}, 503
        if command == 'M':
            last_toggle_request = time.monotonic(); state['mode_pending'] = True
        if command in ('F','B','L','R','Q','E','M'):
            invalidate_map_pose('Đã gửi lệnh '+command+'; không suy ra tọa độ từ PWM')
        state['last_tx'] = command
        print('[SERIAL TX]', command, flush=True)
        # A successful write is NOT a hardware ACK (legacy protocol has none).
        return {'status':'sent', 'command':command, 'acknowledged':False}, 200


def physics_worker():
    while True:
        visual_tick()
        state.update(current_speed=0.0, fwd=0.0, strafe=0.0, omega=0.0)
        time.sleep(0.04)


# ------------------------------------------------------------------------------
# ĐỘNG HỌC XE 3D MECANUM
# ------------------------------------------------------------------------------
def physics_worker_reference():
    global state, ser
    dt = 0.04
    while True:
        t0 = time.time()
        hw_connected = (ser is not None and hasattr(ser, 'is_open') and ser.is_open)
        current_mode = state.get("mode", "LÁI TAY")

        vf = state.get("fwd", 0.0)
        vs = state.get("strafe", 0.0)
        vo = state.get("omega", 0.0)
        speed = math.hypot(vf, vs)
        state["current_speed"] = round(speed, 2)

        action = state.get("action", "STOP")

        # ----------------------------------------------------------------------
        # ĐIỀU KIỆN ĐỂ XE ẢO CHẠY VÀ VẼ LINE (ĐÚNG YÊU CẦU XE THẬT CHẠY MỚI CHẠY):
        # 1. Nếu LÁI TAY: Chỉ chạy khi có bấm nút/chuột (speed > 0.01 hoặc abs(vo) > 0.01)
        # 2. Nếu TỰ HÀNH: Chỉ chạy khi FSM phát lệnh di chuyển thực tế (Action khác STOP và speed > 0.01)
        # ----------------------------------------------------------------------
        is_moving = False

        if current_mode == "LÁI TAY":
            if speed > 0.01 or abs(vo) > 0.01:
                is_moving = True
        else:  # Chế độ TỰ HÀNH
            # Chỉ khi xe thật có lệnh bám line / né cản (khác STOP) và có vận tốc
            if action != "STOP" and (speed > 0.01 or abs(vo) > 0.01):
                is_moving = True

        if is_moving:
            theta_rad = math.radians(state.get("angle", 0.0))
            # Tích phân chuyển động Mecanum chuẩn tọa độ mặt sàn
            dx = (vs * math.cos(theta_rad) + vf * math.sin(theta_rad)) * dt
            dy = (vf * math.cos(theta_rad) - vs * math.sin(theta_rad)) * dt
            d_angle = math.degrees(vo * dt)

            state["x"] = round(state.get("x", 0.0) + dx, 3)
            state["y"] = round(state.get("y", 0.0) + dy, 3)
            state["angle"] = round((state.get("angle", 0.0) + d_angle) % 360, 1)
            state["total_dist"] = round(state.get("total_dist", 0.0) + speed * dt, 2)
        else:
            # Khi xe thật dừng: Đứng im tuyệt đối, không trôi ảo
            if action == "STOP" or current_mode != "LÁI TAY":
                state["current_speed"] = 0.0

        elapsed = time.time() - t0
        time.sleep(max(0.005, dt - elapsed))
        
# ------------------------------------------------------------------------------
# API ĐIỀU KHIỂN & CẤU HÌNH
# ------------------------------------------------------------------------------
# Map coordinates are in metres. This UI never synthesizes measured odometry.
from pathlib import Path
import copy
import uuid
visual_server_id = uuid.uuid4().hex
map_lock = threading.RLock()
map_dir = Path(os.environ.get('AGV_MAP_DIR', str(Path.home() / '.local/share/agv-dashboard-vector-v1'))).expanduser()
map_error = ''


def validated_plan(body):
    if not isinstance(body, dict): raise ValueError('Cần nhập cấu hình tuyến')
    shape = body.get('shape', 'rectangle')
    if shape not in ('rectangle', 'square', 'parallelogram'): raise ValueError('Hình dạng không hợp lệ')
    def number(key, default, low, high):
        value = body.get(key, default)
        if isinstance(value, bool): raise ValueError('Giá trị số không hợp lệ')
        value = float(value)
        if not math.isfinite(value) or not low <= value <= high:
            raise ValueError('{} phải trong khoảng {}…{} m'.format(key, low, high))
        return round(value, 4)
    width = number('width', 2, 0.2, 50)
    height = width if shape == 'square' else number('height', 3, 0.2, 50)
    skew = number('skew', 0, -25, 25) if shape == 'parallelogram' else 0.0
    points = [{'id': k, 'x': x, 'y': y} for k, x, y in
              [('A', 0.0, 0.0), ('B', width, 0.0), ('C', width+skew, height), ('D', skew, height)]]
    return {'shape': shape, 'width': width, 'height': height, 'skew': skew,
            'points': points, 'unit': 'm', 'perimeter_m': round(2*(width+math.hypot(skew,height)),4)}


plan = None
try:
    if (map_dir/'plan.json').exists():
        plan = validated_plan(json.loads((map_dir/'plan.json').read_text()))
except (OSError, ValueError, TypeError) as exc:
    map_error = 'Không đọc được tuyến đã lưu: ' + str(exc)
# Position is deliberately NOT restored as a current measurement after restart.
map_pose = None
map_lost = None
map_markers = []
map_visits = []
map_recording = False
map_record_file = None
map_record_name = None


def map_event(kind, payload):
    global map_recording, map_error
    if not map_recording or map_record_file is None: return
    try:
        if map_record_file.stat().st_size > 10*1024*1024:
            raise OSError('Nhật ký đạt giới hạn 10 MB; hãy dừng và tải nhật ký')
        event = {'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                 'time_unix': time.time(), 'type': kind, 'data': payload}
        with map_record_file.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False)+'\n')
    except (OSError, ValueError) as exc:
        map_recording = False; map_error = 'Ghi nhật ký thất bại: ' + str(exc)


def invalidate_map_pose(reason):
    global map_pose, map_lost
    with map_lock:
        if map_pose is not None and map_pose['valid']:
            map_pose['valid'] = False
            map_pose['invalid_reason'] = reason
            map_lost = copy.deepcopy(map_pose)
            map_event('position_invalidated', {'reason': reason, 'last_known': map_lost})


def map_snapshot():
    with map_lock:
        pose = copy.deepcopy(map_pose)
        if pose is not None: pose['age_ms'] = max(0, int((time.time()-pose['time_unix'])*1000))
        route = copy.deepcopy(plan)
        last_id = map_markers[-1]['id'] if map_markers else None
        # Manual pose at a corner establishes only a requested next edge, not actual progress.
        segment = None
        if route and pose:
            ids = [p['id'] for p in route['points']]
            idx = ids.index(pose['corner'])
            step = 1 if pose['direction'] == 'forward' else -1
            segment = pose['corner'] + ' → ' + ids[(idx+step) % len(ids)]
        markers = copy.deepcopy(map_markers[-200:])
        for marker in markers: marker['age_ms'] = max(0, int((time.time()-marker['time_unix'])*1000))
        return {'plan': route, 'pose': pose, 'last_known': copy.deepcopy(map_lost),
                'markers': markers, 'visits': copy.deepcopy(map_visits[-500:]),
                'segment': segment, 'segment_source': 'Kế hoạch từ mốc thủ công' if segment else None,
                'progress_m': None, 'cross_track_m': None, 'distance_measured_m': None,
                'speed_measured_mps': None, 'last_marker_id': last_id,
                'recording': map_recording, 'record_name': map_record_name,
                'error': map_error, 'axes': 'X phải, Y lên; θ=0° hướng +X, tăng ngược chiều kim đồng hồ'}


def record_worker():
    while True:
        with map_lock:
            if map_recording:
                map_event('observation', {'position': copy.deepcopy(map_pose),
                    'mode': state.get('mode'), 'action': state.get('action'),
                    'line': state.get('line'), 'sonar_raw': copy.deepcopy(state.get('sonar_raw')),
                    'telemetry_age_ms': int((time.monotonic()-data_time)*1000) if data_time else None,
                    'position_is_measurement': False, 'visualization': {k:v for k,v in presentation_snapshot().items() if k!='trail'}})
        time.sleep(1.0)


def stationary_for_map_edit():
    # Configuration does not command motors; refuse edits when motion is known or mode uncertain on a live link.
    return not link_ready or (state.get('mode') == 'LÁI TAY' and
                             state.get('action') == 'STOP' and not state.get('mode_pending'))


@app.route('/map/config', methods=['POST'])
def map_config():
    global plan, map_pose, map_lost, map_markers, map_visits, map_error
    try:
        new_plan = validated_plan(request.get_json(silent=True))
    except (ValueError, TypeError, OverflowError) as exc:
        return jsonify(error=str(exc)), 400
    with map_lock:
        if not stationary_for_map_edit(): return jsonify(error='Dừng xe ở LÁI TAY trước khi thay tuyến'), 409
        if map_recording: return jsonify(error='Dừng ghi trước khi thay tuyến'), 409
        temporary = map_dir/('plan-'+uuid.uuid4().hex+'.tmp')
        try:
            map_dir.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(new_plan, ensure_ascii=False), encoding='utf-8')
            os.replace(str(temporary), str(map_dir/'plan.json'))
        except OSError as exc:
            try: temporary.unlink()
            except OSError: pass
            return jsonify(error='Không lưu được tuyến: '+str(exc)), 503
        plan = new_plan; map_pose = map_lost = None
        for environment in visual_sessions:
            revision = visual_sessions[environment].get('trail_revision',0)+1
            visual_sessions[environment] = new_visual_session('simulation' if environment=='simulation' else 'command_estimate')
            visual_sessions[environment]['trail_revision'] = revision
        map_markers = []; map_visits = []; map_error = ''
    return jsonify(status='saved', map=map_snapshot())


@app.route('/map/pose', methods=['POST'])
def map_set_pose():
    global map_pose, map_lost
    body = request.get_json(silent=True)
    if not isinstance(body, dict): return jsonify(error='Cần thông tin điểm xuất phát'), 400
    if body.get('confirmed') is not True: return jsonify(error='Cần xác nhận xe thực đang ở mốc đã chọn'), 400
    try:
        if isinstance(body.get('heading'), bool): raise ValueError('Góc không hợp lệ')
        heading = float(body.get('heading', 0))
        if not math.isfinite(heading) or not -3600 <= heading <= 3600: raise ValueError('Góc không hợp lệ')
    except (TypeError, ValueError, OverflowError): return jsonify(error='Góc không hợp lệ'), 400
    direction = body.get('direction', 'forward')
    if direction not in ('forward','reverse'): return jsonify(error='Chiều đi không hợp lệ'), 400
    with map_lock:
        if not stationary_for_map_edit(): return jsonify(error='Dừng xe ở LÁI TAY trước khi xác nhận vị trí'), 409
        if plan is None: return jsonify(error='Khai báo tuyến trước'), 409
        corner = next((p for p in plan['points'] if p['id'] == body.get('corner')), None)
        if corner is None: return jsonify(error='Mốc không tồn tại'), 400
        map_pose = dict(corner, corner=corner['id'], theta=heading % 360,
                        valid=True, source='manual', direction=direction, time_unix=time.time())
        map_lost = None
        visual_anchor(map_pose)
        visit = dict(map_pose)
        map_visits.append(visit)
        del map_visits[:-500]
        map_markers.append({'id': corner['id'], 'time_unix': visit['time_unix'], 'source':'manual'})
        del map_markers[:-200]
        map_event('manual_corner_confirmed', visit)
    return jsonify(status='manual_confirmation', map=map_snapshot())


@app.route('/map/clear-trail', methods=['POST'])
def map_clear_trail():
    body = request.get_json(silent=True)
    if body is None: body = {}
    if not isinstance(body,dict): return jsonify(error='Yêu cầu xóa vệt không hợp lệ'),400
    with map_lock:
        if 'environment' in body or 'generation' in body:
            if (body.get('environment') != driving_environment or
                type(body.get('generation')) is not int or body['generation'] != drive_generation):
                return jsonify(error='Môi trường đã đổi; tải lại dữ liệu trước khi xóa'),409
        v = visual_sessions[driving_environment]
        count = len(v['trail'])
        v['trail'].clear()
        v['segment'] += 1
        v['trail_revision'] = v.get('trail_revision',0)+1
        result = {'status':'cleared', 'cleared_points':count,
                  'visualization':presentation_snapshot(), 'navigation':map_snapshot()}
    return jsonify(result)


@app.route('/map/record', methods=['POST'])
def map_record():
    global map_recording, map_record_file, map_record_name, map_error
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or type(body.get('enabled')) is not bool:
        return jsonify(error='enabled phải là true hoặc false'), 400
    with map_lock:
        if body['enabled'] and not map_recording:
            if plan is None: return jsonify(error='Khai báo tuyến trước khi ghi'), 409
            try:
                map_dir.mkdir(parents=True, exist_ok=True)
                map_record_name = 'observations-'+time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:6]+'.jsonl'
                map_record_file = map_dir/map_record_name
                with map_record_file.open('x', encoding='utf-8'): pass
            except OSError as exc: return jsonify(error='Không tạo được nhật ký: '+str(exc)), 503
            map_recording = True; map_error = ''
            map_event('record_start', {'plan': copy.deepcopy(plan), 'purpose':'Sensor observations; not measured Teach & Repeat'})
        elif not body['enabled']:
            map_event('record_stop', {})
            map_recording = False
        if map_error: return jsonify(error=map_error), 503
    return jsonify(status='ok', map=map_snapshot())


@app.route('/map/export')
def map_export():
    with map_lock:
        if map_record_file is None: return jsonify(error='Chưa có nhật ký trong phiên này'), 404
        try: content = map_record_file.read_text(encoding='utf-8')
        except OSError as exc: return jsonify(error=str(exc)), 503
        name = map_record_name
    return Response(content, mimetype='application/x-ndjson', headers={'Content-Disposition':'attachment; filename="'+name+'"'})



# Presentation motion never becomes measured navigation. USB is isolated in simulation.
driving_environment = 'real'
drive_generation = 0
VISUAL_SPEED_MPS = 0.25
VISUAL_TURN_RADPS = 0.65
visual_last_tick = time.monotonic()


def new_visual_session(source):
    return {'x':0.0, 'y':0.0, 'theta':0.0, 'command':'Z', 'command_time':0.0,
            'moving':False, 'speed':0.0, 'distance':0.0, 'trail':[], 'segment':0,
            'trail_revision':0, 'route_heading':0.0, 'corner_pending':None,
            'completed_corners':0, 'geometry_reason':'', 'source':source, 'frame':'relative', 'started':False, 'lost':False, 'lost_reason':''}


visual_sessions = {'simulation':new_visual_session('simulation'), 'real':new_visual_session('command_estimate')}


def visual_anchor(pose):
    with map_lock:
        v = visual_sessions['real']
        v.update(x=pose['x'], y=pose['y'], theta=pose['theta'], route_heading=pose['theta'],
                 corner_pending=None,geometry_reason='',command='Z',
                 command_time=0.0, moving=False, speed=0.0, distance=0.0,
                 frame='manual_anchor', started=True, lost=False, lost_reason='')
        v['segment'] += 1
        v['trail'].append({'x':v['x'],'y':v['y'],'segment':v['segment']})
        del v['trail'][:-2000]


def visual_untracked(reason):
    with map_lock:
        v = visual_sessions['real']
        v['corner_pending']=None
        if v['started']:
            v.update(lost=True,lost_reason=reason,command='Z',command_time=0.0,moving=False,speed=0.0)


def visual_command(command, environment):
    with map_lock:
        v = visual_sessions[environment]
        if environment=='real' and command in 'FBLRQE' and v['lost']:
            v.update(x=0.0,y=0.0,theta=0.0,distance=0.0,frame='relative',lost=False,lost_reason='')
            v['segment'] += 1;v['trail_revision'] += 1;v['trail'].clear()
            map_event('relative_estimate_restarted', {'measured':False})
        if environment=='real' and command in 'FBLRQE': v['source']='command_estimate'
        v['command'] = command if command in 'FBLRQE' else 'Z'
        v['command_time'] = time.monotonic()
        if command in 'FBLRQE': v['started'] = True
        if v['command'] == 'Z': v['moving']=False;v['speed']=0.0


def visual_tick(now=None):
    global visual_last_tick
    now = time.monotonic() if now is None else now
    with map_lock:
        elapsed = max(0.0, min(0.1, now-visual_last_tick))
        visual_last_tick = now
        for environment, v in visual_sessions.items():
            v['moving'] = False;v['speed'] = 0.0
            if environment != driving_environment or v['lost']: continue
            if environment=='real' and state.get('mode')=='TỰ HÀNH':
                v['moving']=bool(auto_pwm_fresh(now) and not v.get('geometry_reason') and not v['lost'] and any(motion_feedback['wheels']))
                v['speed']=math.hypot(*pwm_velocity(motion_feedback['wheels'])[:2]) if v['moving'] else 0.0
                continue
            command = v['command']
            lease = 0.16 if command in ('Q','E') else 0.25
            age = now-v['command_time']
            allowed = command in 'FBLRQE' and 0 <= age <= lease
            if environment == 'real':
                expected = {'F':'FORWARD','B':'BACKWARD','L':'STRAFE_LEFT','R':'STRAFE_RIGHT','Q':'ROTATE_LEFT','E':'ROTATE_RIGHT'}.get(command)
                # Echo indicates accepted command only, NOT measured wheel motion.
                allowed = bool(allowed and link_ready and ser is not None and ser.is_open
                    and data_time and 0 <= now-data_time < 0.5
                    and mode_time and now-mode_time < 2.0
                    and state.get('mode') == 'LÁI TAY' and not state.get('mode_pending')
                    and state.get('action') == expected)
            if not allowed: continue
            v['moving'] = True
            theta = math.radians(v['theta'])
            fwd = VISUAL_SPEED_MPS * (1 if command=='F' else -1 if command=='B' else 0)
            left = VISUAL_SPEED_MPS * (1 if command=='L' else -1 if command=='R' else 0)
            turn = VISUAL_TURN_RADPS * (1 if command=='Q' else -1 if command=='E' else 0)
            if not v['trail']:
                v['trail'].append({'x':v['x'],'y':v['y'],'segment':v['segment']})
            v['x'] += (fwd*math.cos(theta)-left*math.sin(theta))*elapsed
            v['y'] += (fwd*math.sin(theta)+left*math.cos(theta))*elapsed
            v['theta'] = (v['theta']+math.degrees(turn*elapsed)) % 360
            distance = math.hypot(fwd,left)*elapsed
            v['distance'] += distance;v['speed'] = math.hypot(fwd,left)
            if distance and math.hypot(v['x']-v['trail'][-1]['x'],v['y']-v['trail'][-1]['y']) >= 0.005:
                v['trail'].append({'x':v['x'],'y':v['y'],'segment':v['segment']})
                del v['trail'][:-2000]


def presentation_snapshot():
    with map_lock:
        v = copy.deepcopy(visual_sessions[driving_environment])
        auto = driving_environment == 'real' and state.get('mode') == 'TỰ HÀNH'
        feedback_ok=auto_pwm_fresh()
        if auto:
            v['moving']=bool(feedback_ok and not v.get('geometry_reason') and not v['lost'] and any(motion_feedback['wheels']))
            v['speed']=math.hypot(*pwm_velocity(motion_feedback['wheels'])[:2]) if v['moving'] else 0.0
        return dict(v, environment=driving_environment, generation=drive_generation, server_instance=visual_server_id, snapshot_monotonic_ms=time.monotonic()*1000, measured=False,
                    auto_waiting_measurement=auto and not feedback_ok, auto_pwm_estimate=auto and feedback_ok,
                    drawing_settings=dict(drawing_settings),
                    motion_pwm=copy.deepcopy(motion_feedback), accuracy_target_m=1.0, accuracy_verified=False,
                    model_only=driving_environment=='real' and not v['started'],
                    speed_scale_mps=VISUAL_SPEED_MPS, turn_scale_radps=VISUAL_TURN_RADPS,
                    real_motion_feedback_available=False, pwm_feedback_available=feedback_ok)


# PWM output estimate, not measured odometry. Gains only affect the drawing.
# Calibrate at the actual PWM/battery/load used; a 1 m error limit is unverified.
AUTO_LINEAR_MPS = float(os.environ.get('AGV_AUTO_FULL_PWM_MPS', '0.236'))
AUTO_STRAFE_MPS = float(os.environ.get('AGV_AUTO_FULL_PWM_STRAFE_MPS', '0.18'))
AUTO_TURN_RADPS = float(os.environ.get('AGV_AUTO_FULL_PWM_RADPS', '1.50'))
if not all(math.isfinite(x) and 0 < x <= 10 for x in
           (AUTO_LINEAR_MPS, AUTO_STRAFE_MPS, AUTO_TURN_RADPS)):
    raise ValueError('AUTO drawing calibration must be finite and in (0,10]')
motion_feedback = None


# Drawing configuration only. These values never change Mega motor control.
drawing_defaults = dict(orthogonal=True, forward_mps=AUTO_LINEAR_MPS,
                        strafe_mps=AUTO_STRAFE_MPS, turn_radps=AUTO_TURN_RADPS)
drawing_settings = dict(drawing_defaults)
try:
    saved = json.loads((map_dir/'drawing.json').read_text())
    if isinstance(saved,dict) and isinstance(saved.get('orthogonal'),bool):
        gains=[float(saved[k]) for k in ('forward_mps','strafe_mps','turn_radps')]
        if all(math.isfinite(x) and 0 < x <= 10 for x in gains):
            drawing_settings.update(zip(('forward_mps','strafe_mps','turn_radps'),gains))
            drawing_settings['orthogonal']=saved['orthogonal']
except (OSError,ValueError,TypeError,KeyError): pass
AUTO_LINEAR_MPS=drawing_settings['forward_mps']
AUTO_STRAFE_MPS=drawing_settings['strafe_mps']
AUTO_TURN_RADPS=drawing_settings['turn_radps']


def drawing_stopped():
    now=time.monotonic()
    if driving_environment!='real': return False
    if not (link_ready and ser is not None and ser.is_open and mode_time
            and 0 <= now-mode_time < 2 and data_time and 0 <= now-data_time < .5
            and state.get('mode')=='LÁI TAY' and state.get('action')=='STOP'
            and not state.get('mode_pending')): return False
    return bool(motion_feedback and 0 <= now-motion_feedback['received'] < .3
                and not motion_feedback['auto'] and not any(motion_feedback['wheels']))


def drawing_reset_problem():
    """Explain the existing STOP checks; this function never writes to USB."""
    now = time.monotonic()
    if driving_environment != 'real':
        return 'Chọn Xe thật · USB trước khi đặt lại mô hình xe thật.'
    if not (link_ready and ser is not None and ser.is_open):
        return 'Mega chưa kết nối. Kiểm tra USB trước khi đặt lại.'
    if state.get('mode_pending') or state.get('mode') != 'LÁI TAY':
        return 'Cần LÁI TAY và STOP. Đóng hộp thoại, nhấn DỪNG và chờ Mega xác nhận.'
    if not mode_time or not 0 <= now-mode_time < 2:
        return 'Xác nhận chế độ Mega đã cũ; chờ dữ liệu mới rồi thử lại.'
    if not data_time or not 0 <= now-data_time < .5:
        return 'DATA từ Mega đã cũ; kiểm tra kết nối, không dùng vận tốc mô hình 0 để suy ra xe đã dừng.'
    if state.get('action') != 'STOP':
        return 'Mega chưa báo STOP. Đóng hộp thoại và nhấn DỪNG trước.'
    if not motion_feedback or not 0 <= now-motion_feedback['received'] < .3:
        return 'Thiếu phản hồi MOTION mới từ Mega. Cần PWM bốn bánh bằng 0 để xác nhận; không phải lỗi tải lại trang.'
    if motion_feedback['auto'] or any(motion_feedback['wheels']):
        return 'Phản hồi MOTION còn AUTO hoặc PWM bánh chưa bằng 0. Dừng xe trước khi đặt lại.'
    return 'Trạng thái xe vừa thay đổi; chờ STOP ổn định rồi thử lại.'


def corner_feedback_event(line,now):
    # Original firmware emits LOCK_OK only after a stable post-turn line check.
    with map_lock:
        v=visual_sessions['real']
        if line.startswith('>> CORNER_FAULT:'):
            if v.get('corner_pending'):
                v.update(corner_pending=None,geometry_reason='Mega báo lỗi cua; cần đặt lại điểm đầu',lost=True)
            return
        fields=line.split()
        if len(fields)!=6 or fields[:2]!=['>>','CORNER']: return
        event=fields[2]
        try:
            values=dict(x.split('=',1) for x in fields[3:])
            direction=values['dir'];board_ms=int(values['at'])
        except (ValueError,KeyError): return
        if event not in ('SPIN_START','LOCK_OK') or direction not in ('Q','E') or not 0<=board_ms<=0xffffffff: return
        if not drawing_settings['orthogonal'] or driving_environment!='real' or not auto_pwm_fresh(now): return
        if v.get('geometry_reason') or v['lost'] or motion_feedback['avoid']: return
        board_offset=((board_ms-motion_feedback['board_ms']+0x80000000)&0xffffffff)-0x80000000
        if not -300<=board_offset<=300: return
        pending=v.get('corner_pending')
        if event=='SPIN_START':
            if pending: return
            last_start=v.get('last_corner_start_ms')
            if last_start is not None and not 0<((board_ms-last_start)&0xffffffff)<0x80000000: return
            v['last_corner_start_ms']=board_ms
            v['corner_pending']=dict(board_ms=board_ms,received=now,direction=direction,
                                     heading=v.get('route_heading',v['theta']),observed=False,progress=0.0)
            return
        if not pending or pending['direction']!=direction or not pending['observed']: return
        elapsed=(board_ms-pending['board_ms'])&0xffffffff
        if not (150<=elapsed<=4000 and 0<=now-pending['received']<=4): return
        target=(pending['heading']+(90 if direction=='Q' else -90))%360
        v.update(theta=target,route_heading=target,corner_pending=None,last_corner_lock_ms=board_ms,
                 completed_corners=v.get('completed_corners',0)+1)
        v['geometry_note']='Hướng 90° theo tuyến giả thiết; Mega xác nhận LOCK_OK, chưa phải góc đo'
        map_event('orthogonal_corner_confirmed',dict(direction=direction,theta=target,measured=False))


def integrate_auto_interval(v,old,dt):
    fwd,left,turn=pwm_velocity(old['wheels'])
    if not drawing_settings['orthogonal'] or old['avoid']:
        integrate_visual(v,fwd,left,turn,dt)
        v['route_heading']=v['theta']
        return
    pending=v.get('corner_pending')
    if old['corner']==3:
        if not pending and v.get('last_corner_lock_ms') is not None and ((v['last_corner_lock_ms']-old['board_ms'])&0xffffffff)<=300:
            return  # LOCK_OK already completed the final spin interval
        if not pending:
            v.update(geometry_reason='Thiếu SPIN_START của lần cua; đặt lại phiên để thử lại',lost=True)
            return
        sign=1 if pending['direction']=='Q' else -1
        if turn*sign < -1e-6:
            v.update(geometry_reason='Chiều PWM khác chiều cua Mega; cần kiểm tra',corner_pending=None,lost=True)
            return
        if turn*sign > 1e-6: pending['observed']=True
        integrate_visual(v,fwd,left,turn,dt)
        pending['progress']=min(89.0,pending['progress']+abs(math.degrees(turn*dt)))
        v['theta']=(pending['heading']+sign*pending['progress'])%360
    else:
        # On a declared straight leg, IR steering corrections do not redefine
        # the map's leg heading. This is a visible route assumption, not sensing.
        if not pending: v['theta']=v.get('route_heading',v['theta'])
        integrate_visual(v,fwd,left,0.0,dt)


@app.route('/drive/drawing-config',methods=['POST'])
def configure_drawing():
    global AUTO_LINEAR_MPS,AUTO_STRAFE_MPS,AUTO_TURN_RADPS
    with serial_lock:
        with map_lock:
            if not drawing_stopped(): return jsonify(error='Cần Xe thật, LÁI TAY, STOP và phản hồi PWM mới bằng 0'),409
            body=request.get_json(silent=True)
            if not isinstance(body,dict): return jsonify(error='Cấu hình không hợp lệ'),400
            try:
                if not isinstance(body.get('orthogonal'),bool): raise ValueError('Chọn kiểu tuyến')
                gains=[]
                for key in ('forward_mps','strafe_mps','turn_radps'):
                    if isinstance(body.get(key),bool): raise ValueError('Hệ số không hợp lệ')
                    value=float(body[key])
                    if not math.isfinite(value) or not 0<value<=10: raise ValueError('Hệ số phải trong (0,10]')
                    gains.append(value)
                settings=dict(zip(('forward_mps','strafe_mps','turn_radps'),gains),orthogonal=body['orthogonal'])
                map_dir.mkdir(parents=True,exist_ok=True)
                temporary=map_dir/'drawing.json.tmp';temporary.write_text(json.dumps(settings))
                temporary.replace(map_dir/'drawing.json')
            except (ValueError,TypeError,KeyError) as exc: return jsonify(error=str(exc)),400
            except OSError as exc: return jsonify(error='Không lưu được cấu hình: '+str(exc)),500
            drawing_settings.update(settings)
            AUTO_LINEAR_MPS,AUTO_STRAFE_MPS,AUTO_TURN_RADPS=gains
            v=visual_sessions['real']
            if v['started']:
                v.update(geometry_reason='Đã đổi hệ số/kiểu tuyến; đặt lại điểm đầu trước lượt mới',lost=True,corner_pending=None)
    return jsonify(status='saved',msg='Đã lưu hệ số vẽ. Đặt lại điểm đầu trước khi chạy lượt mới; không đổi PWM motor.')


@app.route('/drive/reset-estimate',methods=['POST'])
def reset_real_estimate():
    global drive_generation
    with serial_lock:
        with map_lock:
            if not drawing_stopped(): return jsonify(error=drawing_reset_problem()),409
            body=request.get_json(silent=True)
            if not isinstance(body,dict) or body.get('confirmed') is not True:
                return jsonify(error='Cần xác nhận vị trí/hướng thực của xe'),400
            try:
                pose={k:float(body[k]) for k in ('x','y','theta')}
                if any(isinstance(body[k],bool) for k in pose) or not all(math.isfinite(x) for x in pose.values()): raise ValueError()
                if abs(pose['x'])>100 or abs(pose['y'])>100 or abs(pose['theta'])>3600: raise ValueError()
            except (ValueError,TypeError,KeyError,OverflowError): return jsonify(error='Tọa độ/hướng không hợp lệ'),400
            previous=visual_sessions['real']
            v=new_visual_session('command_estimate')
            v.update(x=pose['x'],y=pose['y'],theta=pose['theta']%360,
                     route_heading=pose['theta']%360,frame='manual_anchor',started=True,
                     segment=previous['segment']+1,trail_revision=previous['trail_revision']+1)
            visual_sessions['real']=v
            invalidate_map_pose('Đặt lại điểm đầu cho mô hình; không phải phép đo định vị')
            drive_generation+=1
            map_event('drawing_start_reset',dict(pose,measured=False))
            # Return the new session atomically, before another poll/control request.
            result = dict(status='reset',
                          msg='Đã đặt lại điểm đầu, hướng, quãng đường và vệt; không gửi lệnh motor.',
                          visualization=presentation_snapshot(), navigation=map_snapshot(),
                          control_server_time_ms=time.monotonic()*1000)
    return jsonify(result)




def pwm_velocity(wheels):
    fl, fr, rl, rr = [x/255.0 for x in wheels]
    return ((fl+fr+rl+rr)*AUTO_LINEAR_MPS/4,
            (-fl+fr+rl-rr)*AUTO_STRAFE_MPS/4,
            (-fl+fr-rl+rr)*AUTO_TURN_RADPS/4)



def parse_motion_feedback(line, now):
    global motion_feedback, rx_time, mode_time
    fields = line[7:].split(',')
    if len(fields) != 9: return
    seq, board_ms, fl, fr, rl, rr, auto, corner, avoid = [int(x) for x in fields]
    if not (0 <= seq <= 0xffffffff and 0 <= board_ms <= 0xffffffff
            and all(-255 <= x <= 255 for x in (fl,fr,rl,rr))
            and auto in (0,1) and 0 <= corner <= 5 and avoid in (0,1)): return
    with map_lock:
        old = motion_feedback
        seq_delta = ((seq-old['seq']) & 0xffffffff) if old else 1
        board_delta = ((board_ms-old['board_ms']) & 0xffffffff) if old else 0
        if old and (seq_delta == 0 or seq_delta >= 0x80000000):
            # Lower board uptime + sequence indicates a reboot, never bridge it.
            if seq_delta == 0 or board_ms >= old['board_ms']: return
            visual_untracked('Mega khởi động lại; cần xác nhận lại mốc')
            old = None
        fresh = bool(old and 0 <= now-old['received'] <= .30
                     and 0 <= board_delta <= 300 and seq_delta == 1)
        motion_feedback = dict(seq=seq, board_ms=board_ms, wheels=[fl,fr,rl,rr],
                               auto=bool(auto), corner=corner, avoid=bool(avoid), received=now)
        if not firmware_seen: return  # accepted only after recognised firmware banner
        rx_time = mode_time = now
        state.update(mode='TỰ HÀNH' if auto else 'LÁI TAY',mode_pending=False)
        if driving_environment != 'real' or not link_ready: return
        v = visual_sessions['real']
        if not auto:
            if v.get('corner_pending'):
                v.update(corner_pending=None,geometry_reason='Cua bị hủy; cần xác nhận lại điểm đầu',lost=True)
            if v['source'] == 'auto_pwm_estimate':
                v.update(moving=False,speed=0.0)
            return
        if v['source'] != 'auto_pwm_estimate':
            # Keep a valid starting anchor; do not fabricate an absolute position.
            if v['lost']:
                v.update(x=0.0,y=0.0,theta=0.0,distance=0.0,frame='relative')
                v['segment'] += 1; v['trail_revision'] += 1; v['trail'].clear()
            v.update(source='auto_pwm_estimate',lost=False,lost_reason='',route_heading=v['theta'])
        if old and old['auto'] and not fresh:
            if v.get('corner_pending'):
                v.update(corner_pending=None,geometry_reason='Mất dữ liệu trong lúc cua; đặt lại điểm đầu')
            v['segment'] += 1
            v.update(lost=True,lost_reason='Gián đoạn phản hồi PWM; vệt sau khoảng trống chỉ là ước lượng tương đối')
        if drawing_settings['orthogonal'] and corner==5:
            v.update(geometry_reason='Mega báo CORNER_FAULT; cần kiểm tra và đặt lại điểm đầu',corner_pending=None)
        if corner==0 and v.get('corner_pending'):
            v.update(geometry_reason='Cua chưa có LOCK_OK hợp lệ; không tự ép góc 90°',corner_pending=None)
        if avoid and v.get('corner_pending'):
            v.update(geometry_reason='Né cản ngắt quá trình cua; cần xác nhận lại điểm đầu',corner_pending=None)
        if v.get('geometry_reason'):
            v.update(lost=True,moving=False,speed=0.0,lost_reason=v['geometry_reason']);return
        # Once data resumes, continue without integrating through the missing interval.
        if fresh and old['auto']:
            v.update(lost=False,lost_reason='')
            integrate_auto_interval(v,old,board_delta/1000.0)
        if v.get('geometry_reason'):
            v.update(lost=True,moving=False,speed=0.0,lost_reason=v['geometry_reason']);return
        v.update(started=v['started'] or any((fl,fr,rl,rr)),
                 moving=bool(any((fl,fr,rl,rr))),speed=math.hypot(*pwm_velocity((fl,fr,rl,rr))[:2]))

def integrate_visual(v,fwd,left,turn,dt):
    if not v['trail'] or v['trail'][-1]['segment'] != v['segment']:
        v['trail'].append({'x':v['x'],'y':v['y'],'segment':v['segment'],'leg':v.get('trace_leg','manual')})
    # Midpoint yaw improves curved-path integration without changing motor control.
    theta = math.radians(v['theta'])+turn*dt/2
    v['x'] += (fwd*math.cos(theta)-left*math.sin(theta))*dt
    v['y'] += (fwd*math.sin(theta)+left*math.cos(theta))*dt
    v['theta'] = (v['theta']+math.degrees(turn*dt)) % 360
    distance = math.hypot(fwd,left)*dt
    v['distance'] += distance
    if distance and math.hypot(v['x']-v['trail'][-1]['x'],v['y']-v['trail'][-1]['y']) >= .005:
        v['trail'].append({'x':v['x'],'y':v['y'],'segment':v['segment'],'leg':v.get('trace_leg','manual')})
        del v['trail'][:-2000]


def auto_pwm_fresh(now=None):
    now=time.monotonic() if now is None else now
    return bool(motion_feedback and firmware_seen and link_ready and ser is not None and ser.is_open
                and 0 <= now-motion_feedback['received'] < .30 and motion_feedback['auto'])


def dispatch_drive(command, requested_environment=None, requested_generation=None):
    # Serial lock orders environment changes and hardware writes.
    with serial_lock:
        context_ok = (requested_environment == driving_environment and requested_generation == str(drive_generation)) or (requested_environment is None and requested_generation is None and driving_environment=='real' and drive_generation==0)
        if command != 'Z' and not context_ok:
            return {'status':'error','msg':'Môi trường điều khiển đã đổi; tải lại trang','sent':False},409
        if driving_environment == 'simulation':
            if command == 'M':
                return {'status':'error','msg':'AUTO ở đây dành cho xe thật; mô phỏng chỉ lái tay','sent':False},409
            visual_command(command,'simulation')
            return {'status':'simulation','command':command,'sent':False,'acknowledged':False},200
        result, code = send_mega(command)
        if code == 200: visual_command(command,'real')
        return result, code


# Order packets from each browser controller before writing bytes to the legacy USB link.
control_sequences = {}


def ordered_dispatch_drive(command, requested_environment=None, requested_generation=None):
    client = request.args.get('controller')
    raw_sequence = request.args.get('sequence')
    # Preserve the original API for scripts; the new UI always supplies both fields.
    if client is None and raw_sequence is None:
        return dispatch_drive(command, requested_environment, requested_generation)
    if (not client or not 8 <= len(client) <= 64 or
        not client.replace('_','').replace('-','').isalnum() or
        not raw_sequence or len(raw_sequence)>16 or not raw_sequence.isdigit()):
        return {'status':'error','msg':'Định danh/thứ tự lệnh không hợp lệ','sent':False},400
    sequence = int(raw_sequence)
    if sequence > 9007199254740991:
        return {'status':'error','msg':'Thứ tự lệnh quá lớn','sent':False},400
    with serial_lock:
        now = time.monotonic()
        key = (client, requested_environment, requested_generation)
        previous = control_sequences.get(key)
        if previous is not None and sequence <= previous['sequence']:
            return {'status':'ignored_stale','sequence':sequence,'sent':False,'acknowledged':False},200
        if command != 'Z':
            try:
                issued = float(request.args.get('issued_ms', ''))
            except (TypeError, ValueError, OverflowError):
                return {'status':'error','msg':'Chưa có mốc thời gian lệnh từ server','sent':False},400
            age = now*1000-issued
            if not math.isfinite(issued) or not -250 <= age <= 350:
                return {'status':'error','msg':'Gói lệnh quá cũ; nhả phím và thử lại khi kết nối ổn định','sent':False},409
        for expired in [k for k,v in control_sequences.items() if now-v['time']>120]:
            del control_sequences[expired]
        if key not in control_sequences and len(control_sequences)>=64:
            oldest = min(control_sequences,key=lambda k:control_sequences[k]['time'])
            del control_sequences[oldest]
        control_sequences[key] = {'sequence':sequence,'time':now}
        result, code = dispatch_drive(command, requested_environment, requested_generation)
        result['sequence'] = sequence
        return result, code



@app.route('/drive/environment', methods=['POST'])
def drive_environment():
    global driving_environment, visual_last_tick, drive_generation
    body = request.get_json(silent=True)
    if not isinstance(body,dict) or body.get('environment') not in ('real','simulation'):
        return jsonify(error='Chọn Xe thật hoặc Mô phỏng'),400
    target = body['environment']
    with serial_lock:
        if target == driving_environment: return jsonify(status='unchanged',environment=target)
        if link_ready:
            fresh = data_time and mode_time and time.monotonic()-data_time < 2 and time.monotonic()-mode_time < 2
            if not fresh or state.get('mode')!='LÁI TAY' or state.get('action')!='STOP' or state.get('mode_pending'):
                return jsonify(error='Dừng xe thật về LÁI TAY/STOP và chờ dữ liệu mới trước khi đổi môi trường'),409
            try:
                if ser is None or not ser.is_open or ser.write(b'Z')!=1: raise IOError('Không gửi được STOP chuyển môi trường')
            except Exception as exc: return jsonify(error=str(exc)),503
        with map_lock:
            for v in visual_sessions.values(): v.update(command='Z',command_time=0.0,moving=False,speed=0.0)
            driving_environment = target;drive_generation += 1;visual_last_tick=time.monotonic()
            map_event('environment_changed', {'environment':target,'measured':False})
    return jsonify(status='changed',environment=target)


@app.route('/drive/reset-simulation', methods=['POST'])
def reset_simulation():
    global drive_generation
    with serial_lock:
        if driving_environment!='simulation':return jsonify(error='Chỉ đặt lại mô hình trong Mô phỏng'),409
        with map_lock:
            visual_sessions['simulation']=new_visual_session('simulation')
            drive_generation += 1
    return jsonify(status='reset')



@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/telemetry')
def telemetry():
    now = time.monotonic()
    # Check raw validity ages at response time, including when no worker has started yet.
    payload = dict(state)
    with serial_lock:
        payload["teach_return"] = gateway.teach.snapshot()
    sonar_at=state.get('sonar_received_monotonic')
    payload['sonar_age_ms']=int((now-sonar_at)*1000) if sonar_at else None
    payload['server_version'] = SERVER_VERSION
    payload['control_server_time_ms'] = now*1000
    age = int((now-data_time)*1000) if data_time else None
    payload['telemetry_age_ms'] = age
    payload['telemetry_valid'] = bool(link_ready and age is not None and age < 2000)
    payload['mode_confirmed'] = bool(link_ready and mode_time and now-mode_time < 2.0)
    camera_time = state.get('camera_frame_time')
    payload['camera_age_ms'] = int((now-camera_time)*1000) if camera_time else None
    payload['navigation'] = map_snapshot()
    pose = payload['navigation']['pose']
    for name, key in [('x','x'), ('y','y'), ('angle','theta')]:
        payload[name] = pose[key] if pose and pose['valid'] else None
    payload['position_source'] = 'manual' if pose and pose['valid'] else None
    payload['position_is_measurement'] = False
    payload['visualization'] = presentation_snapshot()
    return jsonify(payload)

@app.route('/toggle_mode')
def toggle_mode():
    if driving_environment == 'simulation':
        return jsonify(status='error',msg='AUTO dành cho Xe thật; mô phỏng hiện chỉ lái tay'),409
    command = 'Z' if state.get('mode') == 'TỰ HÀNH' else 'M'
    result, code = ordered_dispatch_drive(command, request.args.get('environment'), request.args.get('generation'))
    return jsonify(result), code

@app.route('/reset_origin')
def reset_origin():
    return jsonify(error='Dùng Xác nhận vị trí tại mốc; đưa bản đồ về tâm chỉ thay góc nhìn'), 409

@app.route('/save_tuning', methods=['POST'])
def save_tuning():
    return jsonify(status='disabled', msg='Firmware gốc không hỗ trợ nạp tuning qua USB. Thông số chạy xe giữ trong Mega.'), 409

@app.route('/mecanum_control')
def mecanum_control():
    if request.args.get('estop') == '1':
        result, code = ordered_dispatch_drive('Z', request.args.get('environment'), request.args.get('generation'))
        return jsonify(result), code
    try:
        vector = tuple(int(request.args.get(k, 0)) for k in ('drive','strafe','rotate'))
    except ValueError:
        return jsonify(status='error', msg='Lệnh không hợp lệ'), 400
    commands = {(0,0,0):'Z',(1,0,0):'F',(-1,0,0):'B',(0,-1,0):'L',
                (0,1,0):'R',(0,0,-1):'Q',(0,0,1):'E'}
    if vector not in commands: return jsonify(status='error', msg='Lệnh không hợp lệ'), 400
    result, code = ordered_dispatch_drive(commands[vector], request.args.get('environment'), request.args.get('generation'))
    return jsonify(result), code

# ==============================================================================
# BỘ ĐIỀU KHIỂN MÁY TRẠNG THÁI FSM (TỰ HÀNH BÁM LINE & NÉ CẢN MECANUM)
# ==============================================================================
def fsm_controller_worker_reference_1():
    global state, ser
    print("[FSM] Bo dieu khien Tu hanh da khoi dong.")
    avoid_timer = 0
    SEARCH_TIMEOUT = 1.0   # Mất line quá 1s chuyển sang xoay tìm line
    OBS_THRESHOLD = 25     # Khoảng cách siêu âm kích hoạt né (cm)
    OBS_CLEAR = 40         # Khoảng cách xác nhận đã cất vật cản đi (cm)

    while True:
        try:
            current_mode = state.get("mode", "LÁI TAY")
            
            # Khi ở chế độ LÁI TAY, FSM trả quyền cho người điều khiển
            if current_mode != "TỰ HÀNH":
                state["fsm_state"] = "IDLE"
                state["avoid_step"] = 0
                time.sleep(0.05)
                continue

            line_detected = state.get("line_detected", False)
            err_x = state.get("line_error", 0)
            sonar_f = state.get("sonar", {}).get("F", 120)
            now = time.time()

            if line_detected:
                state["last_line_time"] = now

            # 1. TRƯỜNG HỢP GẶP CẢN (ƯU TIÊN AN TOÀN CAO NHẤT)
            if sonar_f < OBS_THRESHOLD or state.get("fsm_state") == "AVOID":
                state["fsm_state"] = "AVOID"

                if state["avoid_step"] == 0:
                    avoid_timer = now
                    state["avoid_step"] = 1

                # TỰ PHỤC HỒI: Cất vật cản đi thì hủy chu trình né
                if state["avoid_step"] == 1 and sonar_f > OBS_CLEAR and (now - avoid_timer < 1.0):
                    state["fsm_state"] = "LINE_FOLLOW"
                    state["avoid_step"] = 0
                    state["action"] = "VAT_CAN_DA_CAT_DI"
                    continue

                # BƯỚC 1: Dạt ngang sang phải né cản (3.0 giây)
                if state["avoid_step"] == 1:
                    state["action"] = "DAT_P_NE_CAN"
                    state["fwd"] = 0.0; state["strafe"] = 0.8; state["omega"] = 0.0
                    if now - avoid_timer > 3.0:
                        avoid_timer = now
                        state["avoid_step"] = 2

                # BƯỚC 2: Tiến thẳng vượt cản (4.5 giây)
                elif state["avoid_step"] == 2:
                    state["action"] = "TIEN_VUOT_CAN"
                    state["fwd"] = 0.6; state["strafe"] = 0.0; state["omega"] = 0.0
                    if now - avoid_timer > 4.5:
                        avoid_timer = now
                        state["avoid_step"] = 3

                # BƯỚC 3: Dạt trái tìm lại đường line
                elif state["avoid_step"] == 3:
                    state["action"] = "DAT_T_TIM_LINE"
                    state["fwd"] = 0.2; state["strafe"] = -0.8; state["omega"] = 0.0
                    if line_detected and abs(err_x) < 80:
                        state["fsm_state"] = "LINE_FOLLOW"
                        state["avoid_step"] = 0
                    elif now - avoid_timer > 5.0:
                        state["fsm_state"] = "SEARCH"
                        state["avoid_step"] = 0

            # 2. TRƯỜNG HỢP TỰ ĐỘNG BÁM LINE
            elif line_detected:
                state["fsm_state"] = "LINE_FOLLOW"
                state["avoid_step"] = 0
            # Lấy dữ liệu thực tế từ 5 mắt cảm biến gầm và camera
                line_code = state.get("line", "00000")
                has_far_curve = (state.get("p_cam_obs", 0.0) > 0.5)

                # GỌI BỘ DUNG HỢP 3 TẦNG ĐÃ KHAI BÁO
                fwd, strafe, omega, action, is_marker = execute_line_following_fusion(
                    err_x, line_code, has_far_curve
                )

                # Cập nhật lệnh chấp hành cho xe Mecanum
                state["fwd"] = fwd
                state["strafe"] = strafe
                state["omega"] = omega
                state["action"] = action

                # XỬ LÝ GẶP BỆ LINE (CẢ 5 MẮT CHẠM VẠCH "11111")
                if is_marker and not state.get("marker_latched", False):
                    state["marker_latched"] = True
                    curr_x = state.get("x", 0.0)
                    curr_y = state.get("y", 0.0)
                    # Lưu mốc góc vào danh sách waypoints (tối đa 4 góc)
                    if "waypoints" in state and len(state["waypoints"]) < 4:
                        state["waypoints"].append((curr_x, curr_y))
                        print(f"[MAP] Da danh dau moc goc X{len(state['waypoints'])} tai: ({curr_x}, {curr_y})")
                elif not is_marker:
                    state["marker_latched"] = False

            # 3. TRƯỜNG HỢP MẤT LINE (XE BỊ BƯNG ĐI CHỖ KHÁC)
            else:
                if now - state.get("last_line_time", now) > SEARCH_TIMEOUT:
                    state["fsm_state"] = "SEARCH"
                    state["action"] = "XOAY_360_TIM_LINE"
                    # Xoay chậm tại chỗ tìm line
                    state["fwd"] = 0.0; state["strafe"] = 0.0; state["omega"] = 0.4
                else:
                    state["action"] = "LINE_LOST_WAIT"
                    state["fwd"] = 0.0; state["strafe"] = 0.0; state["omega"] = 0.0

        except Exception as e:
            pass

        time.sleep(0.04) # Chu kỳ 25Hz

# ------------------------------------------------------------------------------
# GIAO DIỆN WEB: THREE.JS WEBGL PHỐI CẢNH 3D & ORBIT CONTROLS
# ------------------------------------------------------------------------------
HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>AGV Mecanum 3D Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
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
        body { color:#dbe6f5; }
        .main-grid { grid-template-columns:minmax(330px,.9fr) minmax(500px,1.25fr); align-items:start; }
        .panel { min-width:0; }
        .cam-box { aspect-ratio:16/9; height:auto !important; }
        .cam-box img { object-fit:cover !important; }
        .map-toolbar,.map-actions,.map-legend,.hardware-strip { display:flex; flex-wrap:wrap; gap:8px; align-items:center; }
        .map-toolbar { justify-content:space-between; margin-bottom:9px; }
        .map-toolbar button,.map-actions button,.map-actions a,.map-form button { background:#18283f; color:#dae8f9; border:1px solid #34465f; border-radius:5px; padding:8px 10px; font-size:12px; cursor:pointer; text-decoration:none; }
        .map-toolbar button.selected { border-color:#38bdf8; background:#063a56; color:#7dd3fc; }
        .view-switch { display:flex; gap:4px; }
        #canvas3d-container { height:390px; background:radial-gradient(ellipse at center,#0c1930,#030919); }
        #oxy_canvas { display:block; width:100%;height:100%; touch-action:none; cursor:grab; }
        .map-overlay { position:absolute; left:10px;top:10px;max-width:85%;font-size:11px;color:#cbd5e1;background:#06101ed9;padding:7px 9px;border:1px solid #293f58;border-radius:5px;pointer-events:none; }
        .map-legend { font-size:10px;color:#94a3b8;margin:9px 0;justify-content:space-between; }
        .legend-plan { color:#38bdf8; }.legend-manual {color:#fbbf24;}.legend-lost {color:#fb7185;}
        .nav-grid { gap:7px; }
        .nav-grid .telem-card {padding:11px 7px; min-height:78px;font-size:10px;text-align:left;}
        .nav-grid .primary { border-top:2px solid #38bdf8;background:linear-gradient(160deg,#11273d,#0a1525);min-height:104px; }
        .nav-grid .telem-val { font-size:14px;margin:9px 0 5px;overflow-wrap:anywhere; }
        .nav-grid .primary .telem-val {font-size:18px;}
        .nav-grid small {display:block;color:#94a3b8;line-height:1.5;font-size:10px;}
        .map-status {color:#fbbf24;font-size:10px;}
        .hardware-strip {justify-content:space-between;padding:12px 2px;color:#94a3b8;font-size:11px;border-bottom:1px solid #27364d;margin-bottom:10px;}
        .hardware-strip b {color:#cbd5e1;}
        .map-actions {gap:6px;}.map-actions button,.map-actions a {font-size:11px;}
        .map-message {font-size:11px;color:#94a3b8;padding-top:10px;line-height:1.5;}
        .map-message.error {color:#fda4af;}
        .map-form {margin-top:12px;border:1px solid #345371;padding:14px;border-radius:7px;background:#0a1525;}
        .map-form h3 {margin:0 0 12px;font-size:14px;}
        .form-fields {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
        .map-form label {font-size:11px;line-height:1.5;display:block;color:#b6c9df;}
        .map-form input:not([type=checkbox]),.map-form select {width:100%;box-sizing:border-box;padding:8px;background:#050e1c;border:1px solid #3b516d;color:#dbeafe;border-radius:4px;margin-top:4px;}
        .map-form input:disabled {opacity:.4;}
        .map-form p {font-size:11px;line-height:1.6;color:#94a3b8;}
        .reset-dialog {width:min(540px,calc(100vw - 32px));max-height:85vh;overflow:auto;box-sizing:border-box;border:1px solid #38bdf8;border-radius:10px;padding:18px;background:#0a1525;color:#e2e8f0;}
        .reset-dialog::backdrop {background:rgba(0,0,0,.7);}
        .reset-dialog .map-form {margin:0;border:0;padding:0;}
        .reset-dialog .reset-status {min-height:1.5em;color:#fda4af;}
        .reset-dialog .reset-status.success {color:#4ade80;}
        .reset-dialog .reset-readiness {color:#fbbf24;}
        .check-label {margin:12px 0;}.map-form [type=checkbox] {vertical-align:middle;}
        button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible {outline:2px solid #7dd3fc;outline-offset:2px;}
        @media(max-width:1100px) {.main-grid {grid-template-columns:1fr;}.nav-grid .primary .telem-val {font-size:17px;}}
        @media(max-width:520px) {.nav-grid {grid-template-columns:repeat(2,minmax(0,1fr));}.header-bar {align-items:flex-start;gap:8px;flex-direction:column;}.status-tags {flex-wrap:wrap;font-size:10px;}#canvas3d-container {height:320px;}.form-fields {grid-template-columns:1fr;}.radar-val {font-size:12px;}}

        .main-grid {grid-template-columns:minmax(0,1fr) minmax(0,1fr);}
        .panel-header {flex-wrap:wrap;gap:8px;}
        .camera-tools {display:flex;align-items:center;gap:9px;flex-wrap:wrap;justify-content:flex-end;}
        #camera_expand {background:#16354c;color:#b9e6fc;border:1px solid #36708a;padding:5px 8px;border-radius:4px;font-size:11px;cursor:pointer;}
        .cam-box {aspect-ratio:16/9;width:100%;height:auto !important;}
        .cam-box img {width:100% !important;height:100% !important;object-fit:cover !important;}
        .camera-panel.expanded .cam-box {position:fixed;inset:0;z-index:10000;width:100vw!important;height:100vh!important;aspect-ratio:auto;background:#000;}
        .camera-panel.expanded #camera_expand {position:fixed;right:20px;top:16px;z-index:10001;background:#102f46;padding:12px;}
        .drive-environment {display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:8px;font-size:11px;}
        .drive-environment label {display:flex;align-items:center;gap:7px;}
        .drive-environment select,.drive-environment button {background:#0b2035;color:#d1e6f8;border:1px solid #3b5877;border-radius:5px;padding:7px;font-size:11px;}
        .ctrl-btn:disabled {opacity:.4;cursor:default;}
        .drive-environment button {cursor:pointer;}.drive-environment button:disabled {opacity:.35;cursor:default;}
        #drive_badge {font-size:10px;color:#fbbf24;font-weight:700;flex:1;}
        .drive-explanation {font-size:11px;color:#9fb2c9;line-height:1.6;margin-bottom:10px;}
        @media(max-width:1100px) {.main-grid {grid-template-columns:1fr;}}

        .camera-panel.show-full-image .cam-box img {object-fit:contain !important;}
        #camera_fit {background:#122b40;color:#b9e6fc;border:1px solid #36708a;border-radius:4px;padding:5px 8px;cursor:pointer;font-size:11px;}
        .camera-panel.expanded #camera_fit {position:fixed;right:180px;top:16px;z-index:10001;padding:12px;}
        .ctrl-btn,.ctrl-btn * {touch-action:none;-webkit-touch-callout:none;-webkit-user-select:none;user-select:none;}
        .ctrl-btn.held {background:#38bdf8;color:#020617;border-color:#7dd3fc;}
        #control_status {font-size:11px;color:#94a3b8;text-align:center;margin-top:10px;min-height:18px;}
        .drive-dock {margin-top:12px;}
        .dock-heading {font-size:11px;color:#9fb2c9;text-align:center;margin-bottom:7px;}
        .drive-shortcut {display:block;font-size:10px;opacity:.8;margin-top:3px;}
        #mobile_tabs,#mobile_environment_slot {display:none;}
        body.driving-mobile {padding:8px 8px calc(250px + env(safe-area-inset-bottom));}
        .driving-mobile .header-bar {position:relative;flex-direction:row;align-items:center;gap:5px;flex-wrap:wrap;margin-bottom:6px;}
        .driving-mobile .badge-title {font-size:10px;padding:5px 7px;}
        .driving-mobile .status-tags {font-size:9px;gap:4px;flex-wrap:wrap;}
        .driving-mobile .tag {padding:4px 5px;max-width:80vw;}
        .driving-mobile #mobile_environment_slot {display:block;}
        .driving-mobile #mobile_environment_slot .drive-environment {margin:0;padding:6px;background:#0d1b2b;border:1px solid #273b54;border-radius:6px;gap:5px;}
        .driving-mobile #drive_badge {font-size:9px;flex-basis:100%;order:3;line-height:1.4;}
        .driving-mobile .drive-environment select {font-size:11px;padding:6px;}
        .driving-mobile #reset_simulation {font-size:10px;padding:6px;}
        .driving-mobile #mobile_tabs {display:flex;gap:5px;padding:6px 0;}
        #mobile_tabs button {flex:1;border:1px solid #375273;border-radius:5px;background:#102338;color:#d6e6f6;min-height:35px;font-size:12px;}
        #mobile_tabs button.active {background:#065077;border-color:#38bdf8;color:#e0f2fe;}
        .driving-mobile .main-grid {display:block;}
        .driving-mobile .panel {padding:8px;}
        .driving-mobile .panel-header {font-size:10px;margin-bottom:6px;gap:4px;}
        .driving-mobile .camera-tools {gap:4px;}
        .driving-mobile #camera_expand,.driving-mobile #camera_fit {font-size:10px;padding:5px;}
        .driving-mobile[data-mobile-view="camera"] .map-panel {display:none;}
        .driving-mobile[data-mobile-view="map"] .camera-panel {display:none;}
        .driving-mobile[data-mobile-view="camera"] #line_sensor_label,.driving-mobile[data-mobile-view="camera"] .sensor-line {display:none;}
        .driving-mobile .radar-box {margin:7px 0 0;padding:7px;}
        .driving-mobile .radar-grid {gap:4px;}
        .driving-mobile .radar-card {padding:5px 2px;}
        .driving-mobile .radar-val {font-size:11px;}
        .driving-mobile #btnOpenTuning {display:none;}
        .driving-mobile .nav-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
        .driving-mobile .nav-grid .primary .telem-val {font-size:16px;}
        .driving-mobile #canvas3d-container {height:280px;}
        .driving-mobile .drive-explanation {font-size:10px;}
        .driving-mobile .map-toolbar button {font-size:10px;padding:7px;}
        .driving-mobile #drive_dock {position:fixed;bottom:0;left:0;right:0;z-index:100;background:#0a1525f5;border-top:1px solid #3b5777;padding:8px 10px calc(8px + env(safe-area-inset-bottom));margin:0;box-sizing:border-box;box-shadow:0 -5px 18px #020617aa;}
        .driving-mobile #drive_dock .btn-grid {max-width:none;gap:6px;width:100%;}
        .driving-mobile #drive_dock .ctrl-btn {min-height:44px;padding:5px;font-size:12px;border-radius:7px;}
        .driving-mobile #drive_dock .btn-stop {background:#cf2028;border-color:#fb7185;font-size:15px;}
        .driving-mobile #drive_dock .drive-shortcut {display:none;}
        .driving-mobile #control_status {margin-top:6px;font-size:10px;min-height:14px;}
        .driving-mobile .dock-heading {font-size:10px;margin-bottom:6px;}
        .driving-mobile[data-mobile-view="details"] .camera-panel > .panel-header,.driving-mobile[data-mobile-view="details"] #camera_view {display:none;}
        .driving-mobile[data-mobile-view="details"] .map-panel > .panel-header,.driving-mobile[data-mobile-view="details"] .map-toolbar,.driving-mobile[data-mobile-view="details"] #canvas3d-container,.driving-mobile[data-mobile-view="details"] .map-legend,.driving-mobile[data-mobile-view="details"] .drive-explanation {display:none;}
        .driving-mobile[data-mobile-view="details"] .map-panel {margin-top:8px;}
        body.driving-landscape {padding-bottom:10px;--dock-width:clamp(230px,34vw,320px);}
        .driving-landscape .header-bar,.driving-landscape #mobile_environment_slot,.driving-landscape #mobile_tabs,.driving-landscape .main-grid {margin-right:calc(var(--dock-width) + 8px);}
        .driving-landscape #mobile_environment_slot .drive-environment {padding:4px;}
        .driving-landscape #drive_badge {flex-basis:100%;font-size:9px;}
        .driving-landscape #reset_simulation {display:none;}
        .driving-landscape #drive_dock {width:var(--dock-width);left:auto;top:0;bottom:0;border-left:1px solid #3b5777;border-top:none;display:flex;flex-direction:column;justify-content:center;padding:8px;}
        .driving-landscape #drive_dock .ctrl-btn {min-height:48px;font-size:11px;}
        .driving-landscape #canvas3d-container {height:240px;}
        .driving-landscape .map-legend {font-size:9px;}
        body.camera-zoomed #drive_dock,body.camera-zoomed #mobile_tabs,body.camera-zoomed #mobile_environment_slot {visibility:hidden;}
        body.camera-zoomed .camera-panel {display:block!important;}
        body.camera-zoomed .camera-panel > .panel-header {display:flex!important;}
        body.camera-zoomed #camera_view {display:flex!important;}
        #mobile_map_tools {display:none;}
        .driving-mobile #mobile_map_tools {display:flex;gap:6px;flex-basis:100%;order:3;}
        .driving-mobile #mobile_map_tools button {flex:1;min-height:34px;font-size:11px;}
        .driving-landscape .badge-title,.driving-landscape #camera_status {display:none;}
        .driving-landscape #camera_view {height:calc(100vh - 190px)!important;height:calc(100dvh - 190px)!important;min-height:130px;max-height:260px;aspect-ratio:auto;}
        body.camera-zoomed #camera_view {height:100vh!important;height:100dvh!important;max-height:none!important;}

        .driving-mobile:not(.driving-landscape) #camera_view {aspect-ratio:4/3;min-height:140px;max-height:calc(100vh - 470px);max-height:calc(100dvh - 470px);}
    #vector_joystick{touch-action:none;-webkit-touch-callout:none;-webkit-user-select:none;user-select:none;width:130px;height:130px;border:2px solid #38bdf8;border-radius:50%;margin:8px auto;text-align:center;display:flex;align-items:center;justify-content:center;background:#12314a;white-space:pre-line;}
.vector-owner{display:flex;flex-wrap:wrap;gap:6px;font-size:11px;align-items:center}.vector-owner button{min-height:32px;}.vector-owner label{max-width:250px;}
.driving-mobile #drive_dock{max-height:58dvh;overflow:auto;} .driving-mobile .vector-owner{font-size:10px;}
</style>
</head>
<body data-mobile-view="camera">
    <div class="header-bar">
        <div class="badge-title">GIÁM SÁT & VẬN HÀNH</div>
        <div class="status-tags">
            <div id="stat_conn" class="tag tag-online">USB: (<span id="port_txt">DISCONNECTED</span>)</div>
            <div id="stat_mode" class="tag tag-mode">CHẾ ĐỘ: LÁI TAY</div>
        </div>
    </div>

    <div id="mobile_environment_slot"></div>
    <nav id="mobile_tabs" aria-label="Chế độ xem điện thoại"><button type="button" data-view="camera" class="active" aria-pressed="true">Camera</button><button type="button" data-view="map" aria-pressed="false">Bản đồ</button><button type="button" data-view="details" aria-pressed="false">Thông số</button></nav>
    <div class="main-grid">
        <div class="panel camera-panel" id="camera_panel">
 <div class="panel-header"><span>CAMERA HÀNH TRÌNH · ĐẦY KHUNG</span><div class="camera-tools"><span id="camera_status" style="color:#fbbf24">ĐANG CHỜ</span><button type="button" id="camera_fit" title="Đầy khung: giữ tỷ lệ và cắt nhẹ mép ảnh. Trọn ảnh: hiện toàn bộ, có thể có viền.">Đầy khung</button><button type="button" id="camera_expand">Phóng lớn camera</button></div></div>
<div class="cam-box" id="camera_view" style="height: 420px; width: 100%; border-radius: 8px; overflow: hidden; background: #000;"><img src="/video_feed" alt="Camera Stream" style="width: 100%; height: 100%; object-fit: fill; display: block;"></div>

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

            <div id="line_sensor_label" style="font-size:11px; font-weight:bold; color:#94a3b8; margin-top:6px;">5 MẮT CẢM BIẾN DÒ LINE (S1 -> S5)</div>
            <div class="sensor-line">
                <div id="eye0" class="sensor-eye"></div>
                <div id="eye1" class="sensor-eye"></div>
                <div id="eye2" class="sensor-eye"></div>
                <div id="eye3" class="sensor-eye"></div>
                <div id="eye4" class="sensor-eye"></div>
            </div>

<div id="dock_home">
            <section id="drive_dock" class="drive-dock"><div class="dock-heading">Giữ để chạy · Thả hết để dừng</div>
            <div class="btn-grid">
                <button class="ctrl-btn" data-act="Q"><span class="drive-label">XOAY TRÁI</span><span class="drive-shortcut">(Q)</span></button>
                <button class="ctrl-btn" data-act="W"><span class="drive-label">TIẾN</span><span class="drive-shortcut">(W)</span></button>
                <button class="ctrl-btn" data-act="E"><span class="drive-label">XOAY PHẢI</span><span class="drive-shortcut">(E)</span></button>
                <button class="ctrl-btn" data-act="A"><span class="drive-label">DẠT TRÁI</span><span class="drive-shortcut">(A)</span></button>
                <button class="ctrl-btn btn-stop" data-act="S"><span class="drive-label">DỪNG</span><span class="drive-shortcut">(Space)</span></button>
                <button class="ctrl-btn" data-act="D"><span class="drive-label">DẠT PHẢI</span><span class="drive-shortcut">(D)</span></button>
                <button class="ctrl-btn" data-act="Z"><span class="drive-label">DỪNG</span><span class="drive-shortcut">(Z)</span></button>
                <button class="ctrl-btn" data-act="B"><span class="drive-label">LÙI</span><span class="drive-shortcut">(S)</span></button>
                <button class="ctrl-btn btn-mode" data-act="X"><span class="drive-label">LÁI TAY ↔ TỰ HÀNH</span><span class="drive-shortcut">(X)</span></button>
            </div>
            <div id="vector_feedback" role="status">VECTOR1 · Chờ dữ liệu Mega</div><div class="vector-owner"><button type="button" id="claim_control">Nhận quyền lái</button><button type="button" id="release_control">Nhả quyền</button>
<label>Mức thử PWM <select id="profile_cap"><option>80</option><option>120</option><option>160</option><option>200</option><option>255</option></select></label>
<label><input type="checkbox" id="profile_armed">Bật né thực nghiệm</label>
<label><input type="checkbox" id="profile_confirm">Đã kiểm tra kích thước thân xe, khoảng trống và xe đã dừng</label><button type="button" id="set_profile">Áp dụng khi dừng</button></div>
<div class="btn-grid"><button class="ctrl-btn" data-act="NW">↖ Tiến trái</button><button class="ctrl-btn" data-act="NE">↗ Tiến phải</button><button class="ctrl-btn" data-act="SW">↙ Lùi trái</button><button class="ctrl-btn" data-act="SE">↘ Lùi phải</button></div><div id="vector_joystick" aria-label="Giữ kéo để tiến/lùi/ngang/chéo">↖ ↑ ↗<br>← GIỮ / KÉO →<br>↙ ↓ ↘</div>
<div id="control_status" role="status">Nhận quyền lái · W+A/W+D/S+A/S+D để chạy chéo · nhả để dừng</div>
            </section>
</div>
        </div>

        <div class="panel map-panel">
            <div class="panel-header"><span>BẢN ĐỒ OXY · ĐƠN VỊ MÉT</span><span id="map_status" class="map-status">CHƯA ĐỊNH VỊ</span></div>
            <div id="environment_home"><div class="drive-environment">
                <label>ĐIỀU KHIỂN <select id="drive_environment"><option value="real">Xe thật · USB</option><option value="simulation">Mô phỏng · chỉ xe 3D</option></select></label>
                <span id="drive_badge">XE THẬT · CHƯA CÓ PHÉP ĐO CHUYỂN ĐỘNG</span>
                <button type="button" id="reset_simulation">Đặt lại mô phỏng</button>
            </div>
            </div>
            <div id="drive_explanation" class="drive-explanation">Lái tay xe thật: vệt xanh nét đứt là ước lượng theo lệnh. AUTO cần firmware gửi PWM bốn bánh.</div>

            <div class="map-toolbar">
                <div class="view-switch"><button type="button" id="view_top" class="selected">Oxy từ trên</button><button type="button" id="view_iso">Phối cảnh 3D</button></div>
                <div id="mobile_map_tools"></div><div><button type="button" id="zoom_out" aria-label="Thu nhỏ">−</button><button type="button" id="zoom_in" aria-label="Phóng to">+</button><button type="button" id="center_map">Về tâm bản đồ</button></div>
            </div>
            <div id="canvas3d-container"><canvas id="oxy_canvas" aria-label="Bản đồ mặt sàn Oxy theo mét"></canvas><div class="map-overlay" id="map_note">Khai báo tuyến để bắt đầu. Chưa có phép đo vị trí.</div></div>
            <div class="map-legend"><span class="legend-plan">━ Tuyến khai báo</span><span class="legend-manual">× Mốc xác nhận thủ công</span><span class="legend-lost">× Vị trí cuối đã biết</span><span style="color:#4ade80">━ Vệt mô phỏng · ┄ Ước lượng lệnh</span><span>θ: 0° = +X · 90° = +Y</span></div>
            <div class="telemetry-grid nav-grid">
                <div class="telem-card primary"><div>TỌA ĐỘ X, Y · m</div><div id="val_pos" class="telem-val">Chưa xác định</div><small id="pos_source">Chưa có nguồn định vị</small></div>
                <div class="telem-card primary"><div>HƯỚNG XE θ · °</div><div id="val_deg" class="telem-val">Chưa xác định</div><small id="heading_source">0° hướng +X; ngược chiều kim đồng hồ</small></div>
                <div class="telem-card primary"><div id="distance_label">QUÃNG ĐƯỜNG THỰC CHẠY</div><div id="val_dist" class="telem-val">Chưa đo</div><small id="distance_source">Không cộng khoảng cách giữa các lần đặt xe</small></div>
                <div class="telem-card primary"><div id="speed_label">VẬN TỐC ĐO</div><div id="val_spd" class="telem-val">Chưa đo</div><small id="speed_source">Chưa có nguồn đo vận tốc</small></div>
                <div class="telem-card"><div>CẠNH DỰ KIẾN</div><div id="nav_segment" class="telem-val">—</div><small id="segment_source">Chưa xác nhận xe đang trên cạnh</small></div>
                <div class="telem-card"><div>TIẾN ĐỘ TRÊN CẠNH</div><div class="telem-val">Chưa xác định</div><small id="route_length">Chưa khai báo tuyến</small></div>
                <div class="telem-card"><div>MỐC CUỐI XÁC NHẬN</div><div id="nav_marker" class="telem-val">—</div><small id="marker_age">Chỉ ghi khi người vận hành xác nhận</small></div>
                <div class="telem-card"><div>LỆCH ĐƯỜNG</div><div id="nav_error" class="telem-val">—</div><small>Sai số camera là px, chưa phải mét</small></div>
                <div class="telem-card"><div>TRẠNG THÁI ĐỊNH VỊ</div><div id="nav_quality" class="telem-val">Chưa xác định</div><small id="quality_source">Chưa có encoder, IMU hoặc mốc định vị</small></div>
                <div class="telem-card"><div>TUỔI GIÁ TRỊ VỊ TRÍ</div><div id="nav_age" class="telem-val">—</div><small id="data_age">Dữ liệu Mega: chưa có</small></div>
                <div class="telem-card"><div>LINE CAMERA / IR</div><div id="nav_line" class="telem-val">—</div><small id="line_detail">Trạng thái cảm biến, không phải tọa độ</small></div>
                <div class="telem-card"><div>CHẾ ĐỘ / HÀNH ĐỘNG</div><div id="val_mode" class="telem-val">Chưa xác nhận</div><small id="val_act">STOP</small></div>
            </div>
            <div class="hardware-strip"><span>USB <b id="val_port">DISCONNECTED</b></span><span>Pin <b id="val_volt">—</b></span><span id="record_state">Chưa ghi nhật ký</span></div>
            <div class="map-actions"><button type="button" id="show_drawing_start">Đặt lại điểm đầu / phiên vẽ</button><button type="button" id="show_route">Khai báo tuyến</button><button type="button" id="show_pose">Xác nhận vị trí tại mốc</button><button type="button" id="clear_trail" title="Xóa vệt xanh, giữ vị trí, quãng đường và các mốc đã xác nhận">Xóa vệt xanh</button><button type="button" id="toggle_plan" aria-pressed="true">Ẩn tuyến khai báo</button><button type="button" id="record_toggle">Bắt đầu ghi nhật ký</button><a href="/map/export" id="export_log">Tải nhật ký</a></div>
            <div class="map-actions" aria-label="Ghi đường lái tay và quay về">
                <button type="button" id="teach_begin">Đặt điểm đầu + ghi đường lái tay</button>
                <button type="button" id="teach_finish">Chốt đường tại điểm dừng</button>
                <button type="button" id="teach_return">Quay 180° và về theo đường đã ghi</button>
                <button type="button" id="teach_cancel">Hủy quay về / DỪNG</button>
            </div>
            <label>Thời gian quay 180° đã đo tại PWM 80 · giây <input id="teach_turn_seconds" type="number" min="0.2" max="30" step="0.01" placeholder="Nhập sau khi đo trên xe"></label>
            <label><input id="teach_calibrated" type="checkbox"> Đã hiệu chuẩn lượt quay và kiểm tra khoảng trống quay xe.</label>
            <p id="teach_status" role="status">Vệt ghi màu đỏ, vệt quay về màu xanh lam. Ghi lệnh/thời gian trong phiên này; quãng đường là ước lượng. DỪNG hoặc nhả quyền sẽ hủy lượt quay về.</p>
            <div id="map_message" class="map-message" role="status" aria-live="polite">Tuyến đã khai báo không phải quỹ đạo xe đo được.</div>

<form id="drawing_form" class="map-form">
  <h3>Ước lượng tuyến và hiệu chuẩn hình vẽ</h3>
  <label><input id="drawing_orthogonal" type="checkbox"> Tuyến thẳng, cua 90° — giả thiết theo tuyến, không phải góc đo</label>
  <div class="form-fields">
    <label>Tiến tại PWM 255 · m/s<input id="drawing_forward" type="number" min="0.001" max="10" step="any" required></label>
    <label>Dạt tại PWM 255 · m/s<input id="drawing_strafe" type="number" min="0.001" max="10" step="any" required></label>
    <label>Quay tại PWM 255 · rad/s<input id="drawing_turn" type="number" min="0.001" max="10" step="any" required></label>
  </div>
  <p>Chỉ thay mô hình vẽ, không đổi PWM motor. Bật tuyến vuông góc sẽ bỏ tích lũy lệch góc do chỉnh lái IR trên đoạn thẳng và chốt ±90° sau LOCK_OK của Mega. Không áp dụng cho tuyến cong.</p>
  <button type="submit">Lưu cấu hình vẽ</button>
  <div class="form-fields">
    <label>Đoạn thẳng thực đã đo · m<input id="calibration_real" type="number" min="0.05" max="100" step="0.01" value="1"></label>
    <label>Quãng đường mô hình của cùng đoạn · m<input id="calibration_model" type="number" min="0.05" max="100" step="0.01"></label>
  </div>
  <button type="button" id="calculate_drawing_gain">Tính hệ số tiến từ đoạn chuẩn</button>
  <p>Đo một đoạn thẳng, không gồm cua/dạt/lùi. Tính hệ số rồi nhấn Lưu cấu hình vẽ; sau đó đặt lại điểm đầu cho lượt mới. Chưa xác nhận sai số ≤1 m.</p>
  <div id="drawing_status" role="status">Đợi phản hồi Mega.</div>
</form>


            <form id="route_form" class="map-form" hidden>
                <h3>Khai báo tuyến đã đo trên sàn</h3>
                <div class="form-fields"><label>Hình dạng<select id="route_shape"><option value="rectangle">Hình chữ nhật</option><option value="square">Hình vuông</option><option value="parallelogram">Hình bình hành</option></select></label><label>Cạnh AB (m)<input id="route_width" type="number" min="0.2" max="50" step="0.01" value="2" required></label><label>Chiều cao vuông góc (m)<input id="route_height" type="number" min="0.2" max="50" step="0.01" value="3" required></label><label>Độ lệch ngang D so với A (m)<input id="route_skew" type="number" min="-25" max="25" step="0.01" value="0" disabled></label></div>
                <p>A = (0,0), B nằm trên +X. Đây là kích thước khai báo; không phải kích thước xe tự đo. Đổi tuyến sẽ xóa mốc/vị trí của phiên hiện tại.</p>
                <button type="submit">Lưu tuyến</button><button type="button" id="close_route">Đóng</button>
            </form>
            <form id="pose_form" class="map-form" hidden>
                <h3>Xác nhận thủ công khi xe đã dừng tại mốc</h3>
                <div class="form-fields"><label>Mốc<select id="pose_corner"><option>A</option><option>B</option><option>C</option><option>D</option></select></label><label>Hướng đầu xe θ (°)<input id="pose_heading" type="number" min="-3600" max="3600" step="0.1" value="0" required></label><label>Chiều tuyến<select id="pose_direction"><option value="forward">A → B → C → D → A</option><option value="reverse">A → D → C → B → A</option></select></label></div>
                <label class="check-label"><input id="pose_confirm" type="checkbox" required> Tôi xác nhận xe thực đang ở mốc và hướng đã chọn.</label>
                <p>Không điều khiển motor. Giá trị bị đánh dấu cũ ngay khi có lệnh di chuyển, AUTO hoặc mất kết nối. Chưa có tự nhận góc hay tự tìm lại vị trí.</p>
                <button type="submit">Xác nhận mốc / vị trí</button><button type="button" id="close_pose">Đóng</button>
            </form>
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

    <dialog id="drawing_start_dialog" class="reset-dialog" aria-labelledby="drawing_start_title">
      <form id="drawing_start_form" class="map-form">
        <h3 id="drawing_start_title">Đặt lại điểm đầu / phiên vẽ</h3>
        <p>Mở hộp này chưa thay tọa độ. Bấm Xác nhận để áp dụng; chỉ thay mô hình, không di chuyển xe thật. Tuyến khai báo được giữ.</p>
        <div class="form-fields">
          <label>X · m<input id="drawing_start_x" type="number" min="-100" max="100" step="0.01" value="0" required></label>
          <label>Y · m<input id="drawing_start_y" type="number" min="-100" max="100" step="0.01" value="0" required></label>
          <label>Hướng θ · ° (0 = +X, 90 = +Y)<input id="drawing_start_theta" type="number" min="-3600" max="3600" step="0.1" value="0" required></label>
        </div>
        <button type="button" id="drawing_start_zero">Điền mốc (0,0), hướng 0°</button>
        <label class="check-label"><input id="drawing_start_confirm" type="checkbox" required> Tôi đã đặt xe thật đúng vị trí và hướng này, đang LÁI TAY và STOP.</label>
        <p id="drawing_start_readiness" class="reset-readiness" role="status"></p>
        <p id="drawing_start_status" class="reset-status" role="alert" aria-live="polite"></p>
        <button type="submit" id="drawing_start_submit">Xác nhận và đặt lại phiên</button>
        <button type="button" id="close_drawing_start">Hủy / Đóng</button>
      </form>
    </dialog>
    <script>
        // ---------------------------------------------------------------------
        // KHỞI TẠO THREE.JS WEBGL CHUẨN VỚI ORBIT CONTROLS
        // ---------------------------------------------------------------------
        // MODAL TUNING POPUP
        // ---------------------------------------------------------------------
        window.openTuningModal = function() { alert('Tuning USB không được firmware Mega gốc hỗ trợ. Giữ thông số trong Arduino.'); return;

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
// Local Canvas renderer: no CDN or WebGL required for map or driving controls.
const byId = id => document.getElementById(id);
let latestTelemetry = null;
// A slow poll from before a reset must not put the old pose back on screen.
let resetFence = null;
let lastServerControlTime=null;
let lastServerControlReceived=0;
let currentMap = null;
let mapView = 'top';
let mapZoom = 1;
let mapPan = {x:0,y:0};
let mapDrag = null;
const mapCanvas = byId('oxy_canvas');
let mapContext = null;
try { mapContext = mapCanvas.getContext('2d'); } catch (error) { console.warn('Map canvas unavailable', error); }
function mapMessage(text, error=false) { byId('map_message').textContent = text; byId('map_message').classList.toggle('error', error); }
let environmentBusy=false;
let cameraExpanded=false;
function cancelDriveHolds(){return clearHeldInputs();}
function setCameraExpanded(expanded){
    if(expanded&&cancelDriveHolds())stopCmd();
    document.body.classList.toggle('camera-zoomed',expanded);
    cameraExpanded=expanded;byId('camera_panel').classList.toggle('expanded',expanded);
    byId('camera_expand').textContent=expanded?'Thu nhỏ · Esc':'Phóng lớn camera';
    byId('camera_expand').setAttribute('aria-expanded',String(expanded));
    document.body.style.overflow=expanded?'hidden':'';
}
let cameraFit='cover';
byId('camera_fit').onclick=()=>{cameraFit=cameraFit==='cover'?'contain':'cover';byId('camera_panel').classList.toggle('show-full-image',cameraFit==='contain');byId('camera_fit').textContent=cameraFit==='cover'?'Đầy khung':'Trọn ảnh';};
byId('camera_expand').onclick=()=>setCameraExpanded(!cameraExpanded);
window.addEventListener('keydown',event=>{if(event.code==='Escape'&&cameraExpanded){event.preventDefault();setCameraExpanded(false);}});
byId('drive_environment').onchange=async()=>{
    const target=byId('drive_environment').value;
    const hadHold=cancelDriveHolds();environmentBusy=true;byId('drive_environment').disabled=true;
    if(hadHold)await controlFetch('/mecanum_control?estop=1');
    await mapRequest('/drive/environment',{environment:target});
    environmentBusy=false;byId('drive_environment').disabled=false;byId('drive_environment').blur();
    await pollTelemetry();
};
byId('reset_simulation').onclick=async()=>{cancelDriveHolds();await mapRequest('/drive/reset-simulation',{});};
function renderDrivePresentation(d){
    const v=d.visualization;if(!v)return;
    renderDrawingSettings(v);
    const sim=v.environment==='simulation',auto=v.auto_waiting_measurement,autoPwm=v.source==='auto_pwm_estimate';
    if(!environmentBusy)byId('drive_environment').value=v.environment;
    byId('reset_simulation').disabled=!sim;
    const modeButton=document.querySelector('.ctrl-btn[data-act="X"]');
    modeButton.disabled=sim;modeButton.title=sim?'AUTO hiện chỉ dành cho Xe thật':'';
    byId('drive_badge').textContent=sim?'MÔ PHỎNG · KHÔNG GỬI LỆNH LÁI USB':autoPwm?(v.drawing_settings.orthogonal?'ƯỚC LƯỢNG AUTO · GIẢ THIẾT 90°':'ƯỚC LƯỢNG AUTO · PWM'):auto?'AUTO · CHỜ PHẢN HỒI PWM':'XE THẬT · MÔ HÌNH ƯỚC LƯỢNG THEO LỆNH';
    byId('drive_badge').style.color=sim?'#4ade80':'#fbbf24';
    byId('drive_explanation').textContent=sim?'Lái xe 3D bằng W/S/A/D/Q/E hoặc giữ nút. Đường xanh là đường mô phỏng, không phải đường xe thật.':autoPwm?'Ước lượng từ PWM. Khi bật tuyến vuông góc, hướng được chốt ±90° sau LOCK_OK của Mega; chưa phải tọa độ/góc đo thực, chưa xác nhận sai số ≤1 m.':auto?'Đang chờ phản hồi PWM mới từ Mega. Mô hình dừng; cần firmware bổ sung MOTION.':'Vệt xanh nét đứt ước lượng theo lệnh đã gửi và echo Mega. Bánh bị kẹt hoặc trượt vẫn làm ước lượng sai; không dùng để tự tìm vị trí.';
    if(sim||(!auto&&v.started&&!v.lost)){
        byId('val_pos').textContent=v.x.toFixed(2)+', '+v.y.toFixed(2)+' m';
        byId('val_deg').textContent=v.theta.toFixed(1)+'°';
        const source=sim?'MÔ PHỎNG':autoPwm?'ƯỚC LƯỢNG AUTO · PWM bốn bánh':v.frame==='manual_anchor'?'ƯỚC LƯỢNG LỆNH · từ mốc thủ công':'ƯỚC LƯỢNG TƯƠNG ĐỐI · chưa gắn sàn';
        byId('pos_source').textContent=source;
        byId('heading_source').textContent=sim?'Hướng mô phỏng':'Hướng ước lượng, chưa đo thực';
        byId('nav_quality').textContent=sim?'Mô phỏng':autoPwm?'Ước lượng AUTO':'Ước lượng theo lệnh';
        byId('quality_source').textContent='Không phải tọa độ định vị đo được';
        byId('map_status').textContent=sim?'MÔ PHỎNG':autoPwm?'ƯỚC LƯỢNG AUTO':'ƯỚC LƯỢNG LỆNH';
        byId('val_pos').style.color=byId('val_deg').style.color=sim?'#4ade80':'#fbbf24';
        byId('distance_label').textContent=sim?'QUÃNG ĐƯỜNG MÔ PHỎNG':'QUÃNG ĐƯỜNG ƯỚC LƯỢNG';
        byId('val_dist').textContent=v.distance.toFixed(2)+' m';
        byId('distance_source').textContent=sim?'Tính trong mô hình, không phải phép đo xe':autoPwm?'Từ PWM; chiều dài cần hiệu chuẩn bằng đoạn đo thực':'Từ lệnh lái; không phải quãng đường đo';
        byId('speed_label').textContent=sim?'VẬN TỐC MÔ PHỎNG':'VẬN TỐC MÔ HÌNH';
        byId('val_spd').textContent=v.speed.toFixed(2)+' m/s';
        byId('speed_source').textContent=autoPwm?'Từ PWM; cần hiệu chuẩn với xe thực': 'Thang minh họa '+v.speed_scale_mps.toFixed(2)+' m/s, không chỉnh PWM';
        byId('nav_age').textContent='Không có phép đo';
        byId('map_note').textContent=source+' · đường xanh không phải bản đồ định vị thực.';
    }else{
        byId('distance_label').textContent='QUÃNG ĐƯỜNG THỰC CHẠY';byId('val_dist').textContent='Chưa đo';
        byId('speed_label').textContent='VẬN TỐC ĐO';byId('val_spd').textContent='Chưa đo';
        byId('distance_source').textContent='Chưa có phản hồi PWM mới để ước lượng';
        byId('speed_source').textContent='Chưa có nguồn đo chuyển động thực';
        if(auto){byId('map_status').textContent='AUTO · CHỜ PHẢN HỒI PWM';byId('map_note').textContent='AUTO: mô hình dừng khi thiếu phản hồi PWM mới.';}
        else if(v.lost){byId('map_status').textContent='ƯỚC LƯỢNG CŨ';byId('map_note').textContent=v.lost_reason;byId('pos_source').textContent='ƯỚC LƯỢNG CŨ — không phải vị trí hiện tại';byId('nav_quality').textContent='Cần định vị lại';}
        else if(v.model_only)byId('map_note').textContent='Mô hình xe tại gốc chỉ để minh họa; chưa biết vị trí thực.';
    }
    if(sim){
        byId('val_mode').textContent='LÁI TAY · MÔ PHỎNG';byId('stat_mode').textContent='CHẾ ĐỘ: LÁI TAY · MÔ PHỎNG';
        byId('val_act').textContent=v.moving?'Mô phỏng lệnh '+v.command:'Mô phỏng STOP';
        byId('nav_segment').textContent='Không bám tuyến tự động';byId('segment_source').textContent='Đang lái mô hình tự do';
    }
}

// Interpolate toward received model positions only; never extrapolate real AUTO movement.
let smoothedVehicle=null;
let vehicleTarget=null;
let vehicleFrame=null;
let vehicleFrameTime=0;
function stopVehicleAnimation(){if(vehicleFrame!==null)cancelAnimationFrame(vehicleFrame);vehicleFrame=null;}
function updateVehicleTarget(v){
    if(!v)return;
    const context=v.environment+':'+v.generation+':'+v.segment;
    vehicleTarget={x:v.x,y:v.y,theta:v.theta,moving:v.moving,context};
    if(!smoothedVehicle||smoothedVehicle.context!==context||!v.moving||v.auto_waiting_measurement||v.lost||v.model_only){
        smoothedVehicle={...vehicleTarget};stopVehicleAnimation();return;
    }
    if(vehicleFrame===null){vehicleFrameTime=performance.now();vehicleFrame=requestAnimationFrame(animateVehicle);}
}
function animateVehicle(now){
    vehicleFrame=null;if(!vehicleTarget||!smoothedVehicle)return;
    const dt=Math.max(0,Math.min(.05,(now-vehicleFrameTime)/1000));vehicleFrameTime=now;
    const weight=1-Math.exp(-dt/.065);
    smoothedVehicle.x+=(vehicleTarget.x-smoothedVehicle.x)*weight;
    smoothedVehicle.y+=(vehicleTarget.y-smoothedVehicle.y)*weight;
    const delta=((vehicleTarget.theta-smoothedVehicle.theta+540)%360)-180;
    smoothedVehicle.theta=(smoothedVehicle.theta+delta*weight+360)%360;
    drawMap();
    if(vehicleTarget.moving)vehicleFrame=requestAnimationFrame(animateVehicle);
}
function renderVehiclePose(v){return v&&smoothedVehicle?{...v,x:smoothedVehicle.x,y:smoothedVehicle.y,theta:smoothedVehicle.theta}:v||{x:0,y:0,theta:0,model_only:true};}

let showDeclaredPlan=true;
try{showDeclaredPlan=localStorage.getItem('agv.showDeclaredPlan')!=='false';}catch{}
const clearedTrailRevisions=new Map();
function visualContext(v){return v?v.environment+':'+v.generation:'';}
function syncPlanButton(){byId('toggle_plan').textContent=showDeclaredPlan?'Ẩn tuyến khai báo':'Hiện tuyến khai báo';byId('toggle_plan').setAttribute('aria-pressed',String(showDeclaredPlan));}
byId('toggle_plan').onclick=()=>{showDeclaredPlan=!showDeclaredPlan;try{localStorage.setItem('agv.showDeclaredPlan',String(showDeclaredPlan));}catch{}syncPlanButton();drawMap();};
syncPlanButton();
function guardClearedTrail(d){
    if(!d.visualization)return;
    const key=visualContext(d.visualization),minimum=clearedTrailRevisions.get(key);
    if(minimum!==undefined&&(d.visualization.trail_revision||0)<minimum){
        if(latestTelemetry&&visualContext(latestTelemetry.visualization)===key)d.visualization=latestTelemetry.visualization;
        else d.visualization.trail=[];
    }
}
async function clearVisibleTrail(){
    const v=latestTelemetry&&latestTelemetry.visualization;
    if(!v){mapMessage('Đợi dữ liệu server trước khi xóa vệt.',true);return;}
    const result=await mapRequest('/map/clear-trail',{environment:v.environment,generation:v.generation},{skipPoll:true});
    if(!result)return;
    const key=visualContext(result.visualization);
    const revision=Math.max(clearedTrailRevisions.get(key)||0,result.visualization.trail_revision);
    clearedTrailRevisions.set(key,revision);
    if(latestTelemetry&&visualContext(latestTelemetry.visualization)===key&&result.visualization.trail_revision>=revision&&
       ((latestTelemetry.visualization.trail_revision||0)<revision||
        (latestTelemetry.visualization.snapshot_monotonic_ms||0)<=(result.visualization.snapshot_monotonic_ms||0))){
        latestTelemetry.visualization=result.visualization;
        latestTelemetry.navigation=result.navigation;
        currentMap=result.navigation;
        updateVehicleTarget(result.visualization);
        drawMap();
    }
    mapMessage('Đã xóa '+result.cleared_points+' điểm vệt xanh. Tuyến xanh dương được giữ; dùng nút Ẩn tuyến để tắt hiển thị.'+(result.visualization.moving?' Xe đang chạy sẽ vẽ vệt mới từ đây.':''));
}

function drawMap() {
    if (!mapContext) return;
    const ctx=mapContext;
    const w=mapCanvas.clientWidth, h=mapCanvas.clientHeight;
    if (!w || !h) return;
    const ratio=Math.min(window.devicePixelRatio||1,2);
    if(mapCanvas.width!==Math.round(w*ratio)||mapCanvas.height!==Math.round(h*ratio)) { mapCanvas.width=Math.round(w*ratio);mapCanvas.height=Math.round(h*ratio); }
    ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);
    const points=currentMap && currentMap.plan ? currentMap.plan.points : [];
    const raw=(x,y,z=0)=>mapView==='top'?[x,-y]:[.76*(x-y),-.38*(x+y)-z];
    const fitting=points.length?points:[{x:-1,y:-1},{x:1,y:1}];
    if(!points.length&&latestTelemetry&&latestTelemetry.visualization){const q=latestTelemetry.visualization;fitting.push({x:q.x-.5,y:q.y-.5},{x:q.x+.5,y:q.y+.5});}
    const projected=fitting.map(p=>raw(p.x,p.y));
    const minx=Math.min(...projected.map(p=>p[0]),0), maxx=Math.max(...projected.map(p=>p[0]),0);
    const miny=Math.min(...projected.map(p=>p[1]),0), maxy=Math.max(...projected.map(p=>p[1]),0);
    const cx=(minx+maxx)/2,cy=(miny+maxy)/2;
    const scale=Math.min((w-110)/Math.max(maxx-minx,1),(h-100)/Math.max(maxy-miny,1))*mapZoom;
    const project=(x,y,z=0)=>{const p=raw(x,y,z);return [w/2+(p[0]-cx)*scale+mapPan.x,h/2+(p[1]-cy)*scale+mapPan.y];};
    const groundRange=Math.min(120,Math.ceil(Math.max(6,...fitting.map(p=>Math.abs(p.x)),...fitting.map(p=>Math.abs(p.y)))+3));
    const baseStep=scale*.1>=7?.1:scale*.5>=7?.5:1;
    function line(a,b,color,width=1,dash=[]) {ctx.beginPath();ctx.strokeStyle=color;ctx.lineWidth=width;ctx.setLineDash(dash);ctx.moveTo(...a);ctx.lineTo(...b);ctx.stroke();ctx.setLineDash([]);}
    function text(value,p,color='#92a8c3',align='center') {ctx.fillStyle=color;ctx.font='11px Segoe UI, sans-serif';ctx.textAlign=align;ctx.fillText(value,p[0],p[1]);}
    const limit=Math.ceil(groundRange/baseStep);
    for(let i=-limit;i<=limit;i++) {
        const v=i*baseStep;const strong=Math.abs(v*2-Math.round(v*2))<.001;
        line(project(v,-groundRange),project(v,groundRange),strong?'#213750':'#122338');
        line(project(-groundRange,v),project(groundRange,v),strong?'#213750':'#122338');
    }
    line(project(-groundRange,0),project(groundRange,0),'#ef6571',1.7);
    line(project(0,-groundRange),project(0,groundRange),'#4ade80',1.7);
    const labelStep=scale>45?1:scale>20?2:5;
    for(let i=-groundRange;i<=groundRange;i++) { if(i===0 || i%labelStep)continue;
        const x=project(i,0), y=project(0,i);
        if(x[0]>18&&x[0]<w-22&&x[1]>20&&x[1]<h-25)text(String(i),[x[0]+3,x[1]+16],'#fda4af');
        if(y[0]>18&&y[0]<w-22&&y[1]>25&&y[1]<h-20)text(String(i),[y[0]-9,y[1]-5],'#86efac','right');
    }
    text('O',project(-.12,-.18),'#e2e8f0');
    function axisArrow(axis,color,label) {
        const start=project(0,0), end=project(axis==='x'?1:0,axis==='y'?1:0);
        const vx=end[0]-start[0],vy=end[1]-start[1],mag=Math.hypot(vx,vy),ux=vx/mag,uy=vy/mag;
        const tx=ux>0?(w-28-start[0])/ux:ux<0?(22-start[0])/ux:Infinity;
        const ty=uy>0?(h-28-start[1])/uy:uy<0?(28-start[1])/uy:Infinity;
        const distance=Math.min(tx,ty);
        if(distance>35) {const tip=[start[0]+ux*distance,start[1]+uy*distance];line([tip[0]-ux*13-uy*5,tip[1]-uy*13+ux*5],tip,color,2);line([tip[0]-ux*13+uy*5,tip[1]-uy*13-ux*5],tip,color,2);text(label,[tip[0]-ux*24-uy*14,tip[1]-uy*24+ux*14-8],color);}
    }
    axisArrow('x','#fda4af','+X (m)');axisArrow('y','#86efac','+Y (m)');
    if(points.length&&showDeclaredPlan) {
        for(let i=0;i<points.length;i++) {const a=points[i],b=points[(i+1)%points.length];line(project(a.x,a.y),project(b.x,b.y),'#38bdf8',3);
            const len=Math.hypot(a.x-b.x,a.y-b.y);text(len.toFixed(2)+' m',[...project((a.x+b.x)/2,(a.y+b.y)/2)].map((v,j)=>v+(j===1?-12:0)),'#7dd3fc');}
        for(const p of points) {const q=project(p.x,p.y),confirmed=currentMap.markers.some(m=>m.id===p.id);line([q[0]-5,q[1]-5],[q[0]+5,q[1]+5],confirmed?'#fbbf24':'#38bdf8',2);line([q[0]-5,q[1]+5],[q[0]+5,q[1]-5],confirmed?'#fbbf24':'#38bdf8',2);text(p.id+' ('+p.x.toFixed(2)+', '+p.y.toFixed(2)+')',[q[0],q[1]+26],confirmed?'#fbbf24':'#cbd5e1');}
    }
    // Discrete manual observations are dots; never join them into a measured trajectory.
    if(currentMap)for(const p of currentMap.visits) {const q=project(p.x,p.y);ctx.beginPath();ctx.arc(q[0],q[1],3,0,2*Math.PI);ctx.fillStyle='#fbbf24';ctx.fill();}
    const v=latestTelemetry&&latestTelemetry.visualization;
    if(v && v.trail.length>1) {
        ctx.save();ctx.strokeStyle='#4dff76';ctx.lineWidth=3.5;ctx.lineJoin='round';ctx.lineCap='round';
        ctx.shadowColor='#39ff78';ctx.shadowBlur=5;ctx.setLineDash(v.environment==='real'?[8,5]:[]);
        let previous=null;
        for(const p of v.trail){
            if(previous&&p.segment===previous.segment){
                const color=p.leg==='return'?'#38bdf8':p.leg==='teach'?'#fb7185':'#4dff76';
                line(project(previous.x,previous.y,.012),project(p.x,p.y,.012),color,3.5,v.environment==='real'?[8,5]:[]);
            }
            previous=p;
        }
        ctx.restore();
    }
    if(currentMap&&currentMap.pose&&!currentMap.pose.valid){const p=currentMap.pose,q=project(p.x,p.y);line([q[0]-7,q[1]-7],[q[0]+7,q[1]+7],'#fb7185',2);line([q[0]-7,q[1]+7],[q[0]+7,q[1]-7],'#fb7185',2);}
    // Measured outer envelope 34 x 47 cm; wheel sizes/placement remain illustrative.
    const p=renderVehiclePose(v);
    const theta=p.theta*Math.PI/180;
    const local=(x,y,z=0)=>project(p.x+x*Math.cos(theta)-y*Math.sin(theta),p.y+x*Math.sin(theta)+y*Math.cos(theta),z);
    function face(vertices,color,stroke='#5f8099'){ctx.beginPath();vertices.forEach((pt,i)=>i?ctx.lineTo(...pt):ctx.moveTo(...pt));ctx.closePath();ctx.fillStyle=color;ctx.fill();ctx.strokeStyle=stroke;ctx.lineWidth=1;ctx.stroke();}
    function box(x,y,sx,sy,z,height,color){
        const pts=[[-sx/2,-sy/2],[sx/2,-sy/2],[sx/2,sy/2],[-sx/2,sy/2]].map(a=>[a[0]+x,a[1]+y]);
        if(mapView==='iso')for(let i=0;i<4;i++){const a=pts[i],b=pts[(i+1)%4];face([local(a[0],a[1],z),local(b[0],b[1],z),local(b[0],b[1],z+height),local(a[0],a[1],z+height)],'#142e40');}
        face(pts.map(a=>local(a[0],a[1],mapView==='iso'?z+height:0)),color);
    }
    for(const x of [-.105,.105])for(const y of [-.205,.205]){
        box(x,y,.095,.06,0,.075,'#172333');
        // Diagonal rollers distinguish all four Mecanum wheels.
        const slant=(x*y>0?1:-1);
        for(let i=-1;i<=1;i++)line(local(x+i*.025-.008,y-.02,mapView==='iso'?.079:0),local(x+i*.025+.008*slant,y+.02,mapView==='iso'?.079:0),'#8bd2dd',1.5);
    }
    box(0,0,.34,.35,.055,.06,p.auto_waiting_measurement||p.lost?'#596678':p.model_only?'#536375':'#d0a524');
    box(-.045,0,.085,.105,.12,.035,'#26546b');
    box(.085,0,.04,.12,.12,.025,'#81c8d8');
    const nose=local(.32,0,.16);line(local(.12,0,.16),nose,'#22d3ee',2.5);line(local(.25,.035,.16),nose,'#22d3ee',2);line(local(.25,-.035,.16),nose,'#22d3ee',2);
    if(p.model_only)text('Mô hình minh họa · chưa định vị',[...project(p.x,p.y)].map((z,i)=>z+(i===1?35:0)),'#94a3b8');

    text('1 đơn vị = 1 m · lưới '+baseStep.toFixed(1)+' m',[12,h-12],'#94a3b8','left');
}
window.addEventListener('resize',drawMap);
mapCanvas.addEventListener('pointerdown',e=>{mapDrag={x:e.clientX,y:e.clientY,px:mapPan.x,py:mapPan.y};mapCanvas.setPointerCapture(e.pointerId);});
mapCanvas.addEventListener('pointermove',e=>{if(mapDrag){mapPan={x:mapDrag.px+e.clientX-mapDrag.x,y:mapDrag.py+e.clientY-mapDrag.y};drawMap();}});
mapCanvas.addEventListener('pointerup',()=>mapDrag=null);mapCanvas.addEventListener('pointercancel',()=>mapDrag=null);
mapCanvas.addEventListener('wheel',e=>{e.preventDefault();mapZoom=Math.max(.3,Math.min(8,mapZoom*(e.deltaY>0?.9:1.1)));drawMap();},{passive:false});
byId('zoom_in').onclick=()=>{mapZoom=Math.min(8,mapZoom*1.2);drawMap();};
byId('zoom_out').onclick=()=>{mapZoom=Math.max(.3,mapZoom/1.2);drawMap();};
byId('center_map').onclick=()=>{mapZoom=1;mapPan={x:0,y:0};drawMap();};
for(const [id,view] of [['view_top','top'],['view_iso','iso']])byId(id).onclick=()=>{mapView=view;mapPan={x:0,y:0};byId('view_top').classList.toggle('selected',view==='top');byId('view_iso').classList.toggle('selected',view==='iso');drawMap();};
function seconds(ageMs){return ageMs===null||ageMs===undefined?'—':ageMs<1000?ageMs+' ms':(ageMs/1000).toFixed(1)+' s';}
function renderTelemetry(d) {
    if(resetFence && d.visualization &&
       d.visualization.server_instance===resetFence.server_instance &&
       d.visualization.generation<resetFence.generation)return;
    guardClearedTrail(d);
    latestTelemetry=d;currentMap=d.navigation;
    lastServerControlTime=d.control_server_time_ms;lastServerControlReceived=performance.now();
    updateVehicleTarget(d.visualization);
    const cameraFresh=d.camera_age_ms!==null&&d.camera_age_ms<2000;
    byId('camera_status').textContent=cameraFresh?'CÓ KHUNG HÌNH':'CHƯA CÓ KHUNG HÌNH MỚI';
    byId('camera_status').style.color=cameraFresh?'#4ade80':'#fbbf24';
    if(!currentMap)throw new Error('Thiếu dữ liệu bản đồ từ server');
    const p=currentMap.pose, valid=p&&p.valid;
    byId('val_pos').textContent=p?p.x.toFixed(2)+', '+p.y.toFixed(2)+' m':'Chưa xác định';
    byId('val_deg').textContent=p?p.theta.toFixed(1)+'°':'Chưa xác định';
    byId('pos_source').textContent=p?(valid?'Xác nhận thủ công tại '+p.corner:'GIÁ TRỊ CŨ — không phải vị trí hiện tại'):'Chưa có nguồn định vị';
    byId('heading_source').textContent=p?(valid?'Hướng do người vận hành nhập':'Hướng cuối đã biết'):'0° hướng +X; ngược chiều kim đồng hồ';
    byId('val_pos').style.color=byId('val_deg').style.color=p&&!valid?'#fb7185':'#7dd3fc';
    byId('nav_quality').textContent=valid?'Xác nhận thủ công':p?'Mất định vị':'Chưa xác định';
    byId('quality_source').textContent=p&&!valid?p.invalid_reason:'Chưa có nguồn tự định vị liên tục';
    byId('map_status').textContent=valid?'VỊ TRÍ THỦ CÔNG':p?'VỊ TRÍ CŨ':'CHƯA ĐỊNH VỊ';
    byId('nav_age').textContent=p?seconds(p.age_ms):'—';
    byId('data_age').textContent='Dữ liệu Mega: '+seconds(d.telemetry_age_ms);
    byId('nav_segment').textContent=currentMap.segment||'—';
    byId('segment_source').textContent=currentMap.segment_source||'Chưa xác nhận xe đang trên cạnh';
    byId('route_length').textContent=currentMap.plan?'Chiều dài tuyến khai báo: '+currentMap.plan.perimeter_m.toFixed(2)+' m':'Chưa khai báo tuyến';
    const last=currentMap.markers.length?currentMap.markers[currentMap.markers.length-1]:null;
    byId('nav_marker').textContent=last?last.id:'—';
    byId('marker_age').textContent=last?'Thủ công · '+seconds(last.age_ms)+' trước':'Chưa xác nhận mốc';
    byId('nav_error').textContent=d.camera_age_ms!==null&&d.camera_age_ms<2000&&d.line_detected?Number(d.line_error||0).toFixed(0)+' px':'—';
    byId('nav_line').textContent=(d.camera_age_ms!==null&&d.camera_age_ms<2000?(d.line_detected?'Có vạch':'Mất vạch'):'Camera chưa có dữ liệu')+' / '+(d.telemetry_valid?d.line:'—');
    byId('line_detail').textContent='IR: 1 = firmware báo nhận vạch; cần hiệu chuẩn trên sàn';
    const mode=d.mode+(d.mode_pending?' (đang chờ)':d.mode_confirmed?'':' (chưa cập nhật)');
    byId('val_mode').textContent=mode;byId('stat_mode').textContent='CHẾ ĐỘ: '+mode;
    byId('val_act').textContent=d.action+(d.mode==='TỰ HÀNH'?' · DATA chưa phản ánh mọi chuyển động AUTO':'');
    byId('val_port').textContent=d.port;byId('port_txt').textContent=d.port+(d.telemetry_valid?'':' · DATA CŨ');
    byId('stat_conn').style.color=d.telemetry_valid?'#4ade80':'#fbbf24';
    byId('val_volt').textContent=d.telemetry_valid?d.battery.toFixed(2)+' V':'—';
    byId('val_volt').style.color=d.battery<5?'#fb7185':'#cbd5e1';
    for(const [key,id] of [['F','snr_f'],['B','snr_b'],['L','snr_l'],['R','snr_r']]){
        const el=byId(id),raw=d.sonar_raw&&d.sonar_raw[key], value=d.sonar[key];
        const echo=d.sonar_age_ms!==null&&d.sonar_age_ms<350&&raw!==undefined&&raw>3&&raw<400;
        el.textContent=!d.telemetry_valid?'—':!echo?'Không có echo':value+' cm';
        el.style.color=!echo?'#fbbf24':value<=25?'#fb7185':'#4ade80';
    }
    for(let i=0;i<5;i++)byId('eye'+i).classList.toggle('active',d.telemetry_valid&&d.line[i]==='1');
    byId('record_state').textContent=currentMap.recording?'● Đang ghi nhật ký cảm biến':currentMap.record_name?'Nhật ký đã dừng':'Chưa ghi nhật ký';
    byId('record_toggle').textContent=currentMap.recording?'Dừng ghi nhật ký':'Bắt đầu ghi nhật ký';
    byId('map_note').textContent=valid?'Vị trí do người vận hành xác nhận; chưa theo dõi chuyển động.':p?'Xe đã mất định vị. Dấu đỏ là vị trí cuối đã biết.':currentMap.plan?'Tuyến đã khai báo. Chưa biết vị trí xe trên tuyến.':'Khai báo tuyến để bắt đầu. Chưa có phép đo vị trí.';
    const vs=d.vector_status,ack=d.vector_ack;
    byId('vector_feedback').textContent='VECTOR1 · '+(vs?'Pha né '+vs.phase+' · trần PWM '+vs.cap+' · '+(vs.armed?'Né thực nghiệm BẬT':'Né thực nghiệm TẮT'):'Chờ Mega')+(ack?' · ACK '+ack.status:'')+(d.avoid_fault?' · Lỗi né: '+d.avoid_fault:'');
    renderDrivePresentation(d);
    if(currentMap.error)mapMessage(currentMap.error,true);
    drawMap();
}
async function mapRequest(path,body,options={}) {
    try {
        const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const result=await response.json();if(!response.ok)throw new Error(result.error||response.status);
        mapMessage(path==='/drive/environment'?'Đã đổi môi trường. STOP được gửi khi chuyển với USB đang nối.':path==='/drive/reset-simulation'?'Đã đặt lại mô phỏng, không gửi USB.':'Đã cập nhật. Thao tác bản đồ không gửi lệnh motor.');
        if(!options.skipPoll)await pollTelemetry();return result;
    }catch(error){mapMessage(error.message,true);return null;}
}
byId('show_route').onclick=()=>{byId('route_form').hidden=!byId('route_form').hidden;if(currentMap&&currentMap.plan){const p=currentMap.plan;byId('route_shape').value=p.shape;byId('route_width').value=p.width;byId('route_height').value=p.height;byId('route_skew').value=p.skew;}syncRouteInputs();};
byId('close_route').onclick=()=>byId('route_form').hidden=true;
byId('show_pose').onclick=()=>{byId('pose_form').hidden=!byId('pose_form').hidden;byId('pose_confirm').checked=false;};
byId('close_pose').onclick=()=>byId('pose_form').hidden=true;
function syncRouteInputs(){const s=byId('route_shape').value;byId('route_height').disabled=s==='square';byId('route_skew').disabled=s!=='parallelogram';}
byId('route_shape').onchange=syncRouteInputs;
byId('route_form').onsubmit=async e=>{e.preventDefault();const result=await mapRequest('/map/config',{shape:byId('route_shape').value,width:Number(byId('route_width').value),height:Number(byId('route_height').value),skew:Number(byId('route_skew').value)});if(result){byId('route_form').hidden=true;mapPan={x:0,y:0};mapZoom=1;drawMap();}};
byId('pose_form').onsubmit=async e=>{e.preventDefault();const result=await mapRequest('/map/pose',{corner:byId('pose_corner').value,heading:Number(byId('pose_heading').value),direction:byId('pose_direction').value,confirmed:byId('pose_confirm').checked});if(result){byId('pose_form').hidden=true;byId('pose_confirm').checked=false;}};
byId('clear_trail').onclick=clearVisibleTrail;
byId('record_toggle').onclick=()=>mapRequest('/map/record',{enabled:!(currentMap&&currentMap.recording)});
let pollBusy=false;
let telemetryFailed=false;
async function pollTelemetry(){
    if(pollBusy)return;pollBusy=true;
    try{const response=await fetch('/telemetry',{cache:'no-store'});if(!response.ok)throw new Error('Telemetry '+response.status);renderTelemetry(await response.json());if(telemetryFailed){mapMessage('Đã kết nối lại server. Kiểm tra nguồn và tuổi giá trị vị trí.');telemetryFailed=false;}}
    catch(error){telemetryFailed=true;stopVehicleAnimation();if(currentMap&&currentMap.pose){currentMap.pose.valid=false;currentMap.pose.invalid_reason='Mất kết nối web';drawMap();}byId('nav_quality').textContent='Dữ liệu vị trí cũ';byId('val_pos').style.color=byId('val_deg').style.color='#fb7185';byId('map_status').textContent='MẤT KẾT NỐI WEB';byId('pos_source').textContent='DỮ LIỆU CŨ — không dùng làm vị trí hiện tại';byId('stat_conn').style.color='#fb7185';mapMessage('Không cập nhật được server: '+error.message,true);}
    finally{pollBusy=false;}
}
setInterval(pollTelemetry,150);
pollTelemetry();
drawMap();


function renderDrawingSettings(v){
    updateDrawingStartReadiness();
    if(!v||!v.drawing_settings)return;
    const settings=v.drawing_settings,form=byId('drawing_form');
    if(!form.contains(document.activeElement)){
        byId('drawing_orthogonal').checked=settings.orthogonal;
        byId('drawing_forward').value=settings.forward_mps;
        byId('drawing_strafe').value=settings.strafe_mps;
        byId('drawing_turn').value=settings.turn_radps;
    }
    byId('drawing_status').textContent=v.geometry_reason||
      (settings.orthogonal?'Giả thiết tuyến vuông góc · ':'PWM tự do · ')+
      'Đã xác nhận '+(v.completed_corners||0)+' lần cua. '+
      (v.corner_pending?'Đang cua, chờ LOCK_OK. ':'')+'Chưa đo tọa độ thực.';
}
const drawingStartDialog=byId('drawing_start_dialog');
let drawingStartBusy=false;
function updateDrawingStartReadiness(){
    const d=latestTelemetry,v=d&&d.visualization;
    let message='Đợi dữ liệu server.';
    if(v){
        const m=v.motion_pwm;
        const age=m?(v.snapshot_monotonic_ms/1000-m.received):Infinity;
        message=v.environment!=='real'?'Cần chọn Xe thật · USB.':
            d.mode!=='LÁI TAY'||d.mode_pending?'Cần LÁI TAY, nhấn DỪNG trước khi đặt lại.':
            !d.mode_confirmed||d.telemetry_age_ms===null||d.telemetry_age_ms>=500?'Dữ liệu Mega đã cũ; chờ cập nhật.':
            d.action!=='STOP'?'Mega chưa báo STOP.':
            !m||age<0||age>=.3?'Chưa có MOTION mới. Server cần phản hồi PWM bốn bánh bằng 0.':
            m.auto||m.wheels.some(x=>x!==0)?'MOTION còn AUTO hoặc PWM bánh chưa bằng 0.':
            'Đã nhận LÁI TAY, STOP và PWM bốn bánh bằng 0. Kiểm tra xe thực rồi xác nhận.';
    }
    byId('drawing_start_readiness').textContent=message;
}
byId('show_drawing_start').onclick=()=>{
    cancelDriveHolds();
    byId('drawing_start_confirm').checked=false;
    byId('drawing_start_status').textContent='';
    updateDrawingStartReadiness();
    if(!drawingStartDialog.open)drawingStartDialog.showModal();
    byId('drawing_start_x').focus({preventScroll:true});
};
byId('close_drawing_start').onclick=()=>drawingStartDialog.close();
byId('drawing_start_zero').onclick=()=>{
    for(const id of ['drawing_start_x','drawing_start_y','drawing_start_theta'])byId(id).value='0';
};
byId('drawing_start_form').onsubmit=async event=>{
    event.preventDefault();
    if(drawingStartBusy)return;
    cancelDriveHolds();
    drawingStartBusy=true;byId('drawing_start_submit').disabled=true;
    byId('drawing_start_status').textContent='Đang gửi yêu cầu đặt lại mô hình…';
    try{
        const response=await fetch('/drive/reset-estimate',{
            method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({x:Number(byId('drawing_start_x').value),
                y:Number(byId('drawing_start_y').value),theta:Number(byId('drawing_start_theta').value),
                confirmed:byId('drawing_start_confirm').checked})
        });
        const result=await response.json();
        if(!response.ok)throw new Error(result.error||'HTTP '+response.status);
        if(!result.visualization||!result.navigation)throw new Error('Server chưa trả phiên vẽ mới; kiểm tra đã khởi động đúng bản RESET_V1.');
        resetFence={server_instance:result.visualization.server_instance,generation:result.visualization.generation};
        stopVehicleAnimation();smoothedVehicle=null;vehicleTarget=null;
        mapPan={x:0,y:0};mapZoom=1;
        renderTelemetry({...latestTelemetry,visualization:result.visualization,navigation:result.navigation,
            control_server_time_ms:result.control_server_time_ms});
        drawingStartDialog.close();byId('drawing_start_confirm').checked=false;
        mapMessage(result.msg);
        byId('canvas3d-container').scrollIntoView({behavior:'smooth',block:'center'});
    }catch(error){
        const message='Chưa đặt lại: '+error.message;
        byId('drawing_start_status').textContent=message;
        mapMessage(message,true);
    }finally{
        drawingStartBusy=false;byId('drawing_start_submit').disabled=false;
    }
};
byId('drawing_form').onsubmit=async event=>{
    event.preventDefault();cancelDriveHolds();
    const result=await mapRequest('/drive/drawing-config',{
        orthogonal:byId('drawing_orthogonal').checked,forward_mps:Number(byId('drawing_forward').value),
        strafe_mps:Number(byId('drawing_strafe').value),turn_radps:Number(byId('drawing_turn').value)
    });
    if(result)mapMessage(result.msg);
};
byId('calculate_drawing_gain').onclick=()=>{
    const actual=Number(byId('calibration_real').value),model=Number(byId('calibration_model').value);
    const current=Number(byId('drawing_forward').value),gain=current*actual/model;
    if(!Number.isFinite(actual)||!Number.isFinite(model)||actual<.05||model<.05||actual>100||model>100||!Number.isFinite(gain)||gain<=0||gain>10){mapMessage('Nhập chiều dài thực và quãng đường mô hình hợp lệ của cùng một đoạn thẳng.',true);return;}
    byId('drawing_forward').value=gain.toFixed(6);byId('drawing_forward').focus();
    mapMessage('Hệ số tiến mới '+gain.toFixed(6)+' m/s tại PWM 255. Nhấn Lưu cấu hình vẽ để áp dụng, rồi đặt lại điểm đầu.');
};


__VECTOR_CONTROLS__
// Move the SAME controls and environment selector; no duplicate command bindings.
const mobileQuery=window.matchMedia('(max-width:700px), (max-width:1100px) and (max-height:600px), (pointer:coarse) and (max-width:1100px)');
const driveDock=byId('drive_dock');
const dockHome=byId('dock_home');
const environmentRow=document.querySelector('.drive-environment');
const environmentHome=byId('environment_home');
const mapActions=document.querySelector('.map-actions');
const clearButton=byId('clear_trail'),planButton=byId('toggle_plan');
let dockLayout=null;
let layoutTimer=null;
function setMobileView(view){
    if(!['camera','map','details'].includes(view))return;
    document.body.dataset.mobileView=view;
    document.querySelectorAll('#mobile_tabs button').forEach(button=>{const active=button.dataset.view===view;button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
    requestAnimationFrame(drawMap);
}
function layoutMobileDock(){
    const mobile=mobileQuery.matches,landscape=mobile&&innerWidth>innerHeight;
    const signature=mobile+':'+landscape;
    if(signature===dockLayout){requestAnimationFrame(drawMap);return;}
    if(dockLayout!==null&&clearHeldInputs())stopCmd();
    dockLayout=signature;
    document.body.classList.toggle('driving-mobile',mobile);
    document.body.classList.toggle('driving-landscape',landscape);
    if(mobile){document.body.appendChild(driveDock);byId('mobile_environment_slot').appendChild(environmentRow);byId('mobile_map_tools').append(clearButton,planButton);}
    else {dockHome.appendChild(driveDock);environmentHome.appendChild(environmentRow);mapActions.insertBefore(clearButton,byId('record_toggle'));mapActions.insertBefore(planButton,byId('record_toggle'));}
    requestAnimationFrame(drawMap);
}
document.querySelectorAll('#mobile_tabs button').forEach(button=>button.onclick=()=>setMobileView(button.dataset.view));
function scheduleDockLayout(){clearTimeout(layoutTimer);layoutTimer=setTimeout(layoutMobileDock,60);}
window.addEventListener('resize',scheduleDockLayout);
window.addEventListener('orientationchange',scheduleDockLayout);
if(mobileQuery.addEventListener)mobileQuery.addEventListener('change',scheduleDockLayout);
else mobileQuery.addListener(scheduleDockLayout);
requestAnimationFrame(layoutMobileDock);

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
def fsm_controller_worker_reference_2():
    global state
    print("[FSM] Bo dieu khien Tu hanh da khoi dong.")
    avoid_timer = 0
    SEARCH_TIMEOUT = 1.0   # Mất line quá 1s chuyển sang xoay tìm line
    OBS_THRESHOLD = 25     # Khoảng cách siêu âm kích hoạt né (cm)
    OBS_CLEAR = 40         # Khoảng cách xác nhận đã cất vật cản đi (cm)

    while True:
        try:
            current_mode = state.get("mode", "LÁI TAY")
            
            # Khi ở chế độ LÁI TAY, FSM nghỉ
            if current_mode != "TỰ HÀNH":
                state["fsm_state"] = "IDLE"
                state["avoid_step"] = 0
                time.sleep(0.05)
                continue

            line_detected = state.get("line_detected", False)
            err_x = state.get("line_error", 0)
            sonar_f = state.get("sonar", {}).get("F", 120)
            now = time.time()

            if line_detected:
                state["last_line_time"] = now

            # 1. TRƯỜNG HỢP GẶP CẢN (ƯU TIÊN AN TOÀN CAO NHẤT)
            if sonar_f < OBS_THRESHOLD or state.get("fsm_state") == "AVOID":
                state["fsm_state"] = "AVOID"

                if state["avoid_step"] == 0:
                    avoid_timer = now
                    state["avoid_step"] = 1

                # TỰ PHỤC HỒI: Cất vật cản đi thì hủy chu trình né
                if state["avoid_step"] == 1 and sonar_f > OBS_CLEAR and (now - avoid_timer < 1.0):
                    state["fsm_state"] = "LINE_FOLLOW"
                    state["avoid_step"] = 0
                    state["action"] = "VAT_CAN_DA_CAT_DI"
                    continue

                # BƯỚC 1: Dạt ngang sang phải né cản (3.0 giây)
                if state["avoid_step"] == 1:
                    state["action"] = "DAT_P_NE_CAN"
                    state["fwd"] = 0.0; state["strafe"] = 0.8; state["omega"] = 0.0
                    if now - avoid_timer > 3.0:
                        avoid_timer = now
                        state["avoid_step"] = 2

                # BƯỚC 2: Tiến thẳng vượt cản (4.5 giây)
                elif state["avoid_step"] == 2:
                    state["action"] = "TIEN_VUOT_CAN"
                    state["fwd"] = 0.6; state["strafe"] = 0.0; state["omega"] = 0.0
                    if now - avoid_timer > 4.5:
                        avoid_timer = now
                        state["avoid_step"] = 3

                # BƯỚC 3: Dạt trái tìm lại đường line
                elif state["avoid_step"] == 3:
                    state["action"] = "DAT_T_TIM_LINE"
                    state["fwd"] = 0.2; state["strafe"] = -0.8; state["omega"] = 0.0
                    if line_detected and abs(err_x) < 80:
                        state["fsm_state"] = "LINE_FOLLOW"
                        state["avoid_step"] = 0
                    elif now - avoid_timer > 5.0:
                        state["fsm_state"] = "SEARCH"
                        state["avoid_step"] = 0

            # 2. TRƯỜNG HỢP TỰ ĐỘNG BÁM LINE
            elif line_detected:
                state["fsm_state"] = "LINE_FOLLOW"
                state["avoid_step"] = 0
                
                # Bù sai số bằng dạt ngang Mecanum (Kp = 0.45)
                kp = 0.45
                vy_cmd = max(-150, min(150, int(err_x * kp)))

                state["fwd"] = 0.6
                state["strafe"] = float(vy_cmd) / 150.0 * 0.7
                state["omega"] = float(err_x) / 300.0 * 0.3

                if abs(err_x) < 30:
                    state["action"] = "BAM_LINE_THANG"
                elif err_x > 0:
                    state["action"] = f"BAM_LINE_DAT_P ({vy_cmd})"
                else:
                    state["action"] = f"BAM_LINE_DAT_T ({vy_cmd})"

            # 3. TRƯỜNG HỢP MẤT LINE (XE BỊ BƯNG ĐI CHỖ KHÁC)
            else:
                if now - state.get("last_line_time", now) > SEARCH_TIMEOUT:
                    state["fsm_state"] = "SEARCH"
                    state["action"] = "XOAY_360_TIM_LINE"
                    state["fwd"] = 0.0; state["strafe"] = 0.0; state["omega"] = 0.4
                else:
                    state["action"] = "LINE_LOST_WAIT"
                    state["fwd"] = 0.0; state["strafe"] = 0.0; state["omega"] = 0.0

        except Exception as e:
            pass

        time.sleep(0.04) # Chu kỳ 25Hz

def shutdown_stop():
    if not serial_lock.acquire(timeout=0.3): return
    try:
        if driving_environment == 'real' and ser is not None and ser.is_open: ser.write(b'Z')
    except Exception: pass
    finally: serial_lock.release()


from agv_vector_gateway import Gateway
gateway = Gateway(globals())
gateway.install(app)
serial_worker = gateway.serial_worker
send_mega = gateway.legacy_command
simulation_vector = [0.,0.,0.]
simulation_vector_at = 0.

def auto_or_manual_fresh():
    return bool(link_ready and motion_feedback and time.monotonic()-motion_feedback['received'] < .3)

def teach_heading_anchor(theta):
    # User-calibrated timed turn, still an assumption rather than measured yaw.
    with map_lock:
        visual_sessions['real']['theta']=theta%360


def vector_physics_worker():
    last=time.monotonic()
    while True:
        now=time.monotonic();dt=min(.1,max(0.,now-last));last=now
        with map_lock:
            v=visual_sessions[driving_environment]
            if driving_environment=='simulation':
                cmd=simulation_vector if now-simulation_vector_at<.25 else [0.,0.,0.]
                integrate_visual(v,cmd[0]*AUTO_LINEAR_MPS,-cmd[1]*AUTO_STRAFE_MPS,-cmd[2]*AUTO_TURN_RADPS,dt)
                v.update(source='simulation',lost=False,started=v['started'] or any(cmd),moving=any(cmd),speed=math.hypot(cmd[0]*AUTO_LINEAR_MPS,cmd[1]*AUTO_STRAFE_MPS))
            elif state.get('mode')=='LÁI TAY':
                v['trace_leg']='return' if gateway.teach.active else 'teach' if gateway.teach.recording else 'manual'
                v['source']='manual_pwm_estimate'
                fresh=auto_or_manual_fresh();v['moving']=bool(fresh and any(motion_feedback['wheels']))
                if v['moving']:v['started']=True
                if fresh and not v['lost']:
                    f,left,turn=pwm_velocity(motion_feedback['wheels'])
                    if gateway.teach.active and gateway.teach.index==0:
                        # Show the timed 180-degree turn using its calibration;
                        # never present the unrelated drawing gain as measured yaw.
                        turn=-math.pi/gateway.teach.plan[0][0]
                    integrate_visual(v,f,left,turn,dt);v['speed']=math.hypot(f,left)
                else:v['speed']=0.
        time.sleep(.02)
physics_worker=vector_physics_worker
# Apply only to this new variant; preserve the supplied source file untouched.
from pathlib import Path as _VectorPath
_controls=(_VectorPath(__file__).parent/'vector_controls.js').read_text(encoding='utf-8')
HTML_PAGE=HTML_PAGE.replace('__VECTOR_CONTROLS__', 'const AGV_CSRF='+json.dumps(gateway.csrf)+';\n'+_controls)
HTML_PAGE=HTML_PAGE.replace('<script>', "<script>\nconst originalFetch=window.fetch.bind(window);\nwindow.fetch=(url,options={})=>{\n const same=typeof url==='string'&&(url.startsWith('/')&&!url.startsWith('//'));\n if(same){options={...options,headers:{'X-AGV-CSRF':__CSRF__,'X-AGV-Lease':ownerLease,...(options.headers||{})}};\n if(!url.startsWith('/video_feed')&&!url.startsWith('/telemetry')&&!url.startsWith('/map/export')&&!new URL(url,location.href).searchParams.has('controller'))url+=(url.includes('?')?'&':'?')+'controller='+encodeURIComponent(controllerId);}\n return originalFetch(url,options);\n};\n".replace('__CSRF__',json.dumps(gateway.csrf)),1)

if __name__ == '__main__':
    if not gateway.user or len(gateway.password)<12:
        raise SystemExit('Đặt AGV_WEB_USER và AGV_WEB_PASSWORD tối thiểu 12 ký tự; không ghi mật khẩu vào code.')
    import atexit, signal
    atexit.register(shutdown_stop)
    def terminate(signum, frame): raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate)
    t_cam = threading.Thread(target=camera_worker, daemon=True)
    t_ser = threading.Thread(target=serial_worker, daemon=True)
    t_phy = threading.Thread(target=physics_worker, daemon=True)
    t_cam.start()
    t_ser.start()
    t_phy.start()
    threading.Thread(target=record_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, threaded=True)

