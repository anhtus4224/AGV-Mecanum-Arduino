# Kiểm chứng TOUCH_VECTOR_V2 — 11/11/2026

Nguồn đối chiếu: 882daf1239ab6a55617726c5eda8e3aefb7bdf9b trên nhánh
fix/vector-setpoint-ack-2026-11-10, đã xác minh GitHub trước sử dụng.
Không SSH Jetson, không mở USB/camera thật; không khởi động launcher hay service
điều khiển. Fixture HTTP chỉ nghe loopback, serial/camera giả. Không upload AVR.

| Cấp kiểm tra | Kết quả trong phiên này | Giới hạn |
|---|---|---|
| Python | Syntax/grammar3.6 qua; runtime Python3.12 | Chưa chạy Python3.6 trên Jetson |
| Unit test Python | 42 qua: 39 gateway + 3 bảo toàn nguồn | Flask/fake serial, không mạng xe |
| C++ motion | Mixer, bão hòa, đảo chiều, FSM/A2/no-echo qua | Host g++17, không mô phỏng cơ khí |
| C++ toàn sketch/stub | CRC/replay/bounds, quyền, manual/AUTO watchdog, reconnect qua | Không phải build Mega |
| C++ PWM pins | 50 tổ hợp10 hướng×5 cap80/120/160/200/255; tám chân PWM, STOP, đảo chiều, watchdog; vào né55 và không vào56 qua | Chỉ các giá trị analogWrite stub |
| C++ bao thân/né | 47×34 cm, hành lang/chéo chật bị chặn, ramp RETURN, no-echo từng hướng qua | Không chứng minh vùng quét vật lý trống |
| Bảo toàn nguồn | 13 hàm giữ byte/hash; toàn line/cua chỉ đổi điểm vào60→55; prefix pin/sensor/speed/corner giữ nguyên | Telemetry mới vẫn có thể ảnh hưởng timing thực |
| Chromium dashboard | 6 mục gốc qua: bàn phím/chéo/nhả/reset/quyền/joystick | Loopback USB/camera giả |
| Chromium touch/handoff | Lượt16 mục qua, max vector gap184 ms với mỗi request trễ giả130 ms; không pageerror/từ chối vector ngoài dự kiến | Chưa thử Safari/iOS/Android hoặc WiFi thực |
| Chromium USB vắng | Claim/lease/simulation qua trong khi worker thử lại USB giả | serial=None, không mở cổng thật |
| Chromium telemetry trễ450 ms | Joystick tiến phải, giữ4 s, giữ quyền, thả speed0, không rejection/pageerror | Fixture mới; không đo vận tốc xe |
| AVR ATmega2560 | ELF/HEX build/link qua, flash26.734 B, static RAM2.490 B | GCC AVR5.4.0, avr-libc2.0, Arduino AVR core1.8.3; chưa đo stack/timing |
| Nạp board/bánh treo/sàn | CHƯA THỰC HIỆN | Dạt ngang, né, PWM200/255, line/cua cần người vận hành kiểm tra lại |

Baseline Chromium cùng kiểu thử130 ms/request: giữ tiến sau laptop STOP/nhả và
điện thoại nhận quyền tạo khoảng cách vector [300,318,320,323] ms, vượt watchdog250 ms.
Đây là bằng chứng khoảng hở phần mềm; fixture không có watchdog vật lý hay xe.
Bản sửa không nới timeout. Lượt16 mục gồm cả lease cũ bị từ chối và STOP request503 làm bỏ quyền. Lượt đạt không bảo đảm mọi độ trễ/tải CPU đều đạt.

Có lượt host bị trễ lịch chạy làm test timing/lease thất bại, đúng với thiết kế
dừng khi mất nhịp; không đổi watchdog/ngưỡng để vượt test. Test joystick cũ
ban đầu chạy nối tiếp test simulation bị fail dấu tọa độ tuyệt đối vì dùng lại
pose đã đi trước đó. Chạy lại trên fixture mới từ gốc thì qua; giữ nguyên assertion.
Các phép kiểm thời gian phải chạy riêng, tránh build/browser khác cùng lúc.

## Chạy lại, không phần cứng

Từ thư mục upgrade_v1, dùng Python có Flask/NumPy/pyserial, Node có Playwright
và Chromium. Không cần launcher, USB, mật khẩu thật hoặc camera.

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
g++ -std=c++17 -Wall -Wextra -Werror tests/test_motion.cpp -o /tmp/agv-motion
/tmp/agv-motion
g++ -std=c++17 -Wall -Wextra -Werror -Itests tests/test_firmware.cpp -o /tmp/agv-firmware
/tmp/agv-firmware
g++ -std=c++17 -Wall -Wextra -Werror -Itests tests/test_wheels.cpp -o /tmp/agv-wheels
/tmp/agv-wheels
g++ -std=c++17 -Wall -Wextra -Werror tests/test_avoid_envelope.cpp -o /tmp/agv-envelope
/tmp/agv-envelope
```

Terminal test riêng: `python3 tests/serve_ui.py` (127.0.0.1:18766, chỉ phần cứng
giả), rồi `node tests/test_ui.js` và `node tests/test_touch_handoff.js` lần lượt.
Tắt đúng fixture đã khởi động sau test. Không chạy hai bản fixture cùng cổng.
Muốn tái hiện baseline, giải nén upgrade_v1 từ commit nguồn vào thư mục tạm,
dùng fixture mới với AGV_TEST_ROOT trỏ vào thư mục đó, AGV_TEST_PORT=18768;
chạy test touch với AGV_TEST_URL=http://127.0.0.1:18768 và AGV_EXPECT_BASELINE=1.
Baseline chỉ xác nhận khoảng hở >250 ms, không áp tiêu chí bản sửa.

Với simulation: `python3 tests/serve_simulation.py` (127.0.0.1:18767), chạy
`node tests/test_simulation_ui.js`. Khởi động lại đúng fixture test với dữ liệu
test mới trước `node tests/test_joystick_latency.js`, vì test này giả định pose gốc.

Build AVR không upload:

```bash
python3 tests/build_avr.py /path/to/avr/bin /path/to/ArduinoCore-avr-1.8.3 /tmp/agv-avr-build
```

Trong phiên này toolchain Debian tải qua metadata APT ký số, giải nén ngoài
checkout; core1.8.3 từ ArduinoCore-avr chính thức qua HTTPS, không vá core hoặc
tắt TLS/checksum. Không đưa ELF/HEX test vào gói nạp xe.

Đọc TOUCH_VECTOR_V2.md để biết giới hạn sonar, chẩn đoán dạt ngang và rollback.
Các kết quả thử xe trước do người dùng báo không được nhập làm PASS hardware
của bản sửa này; chưa đối chiếu hash Jetson hôm nay.
