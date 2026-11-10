# Kiểm chứng VECTOR1 — 10/11/2026

Nguồn, hash và phạm vi: PROVENANCE.json. Không có kết nối trực tiếp với Jetson, Mega hoặc motor của người dùng.

| Cấp kiểm tra | Kết quả | Giới hạn |
|---|---|---|
| Cú pháp Python | py_compile và grammar Python 3.6 qua | Runtime kiểm thử Python 3.12; chưa chạy Jetson Python 3.6 |
| Gateway Flask | 26 unit test qua | Serial giả; không có thiết bị thật |
| Mixer/FSM C++ | Qua với g++17 -Wall -Wextra -Werror | Kiểm thử logic host, không thay cho AVR |
| Toàn sketch với Arduino stub | Protocol CRC, sai bounds, replay, không cướp phiên, timeout manual/AUTO, reconnect và thời gian mẫu sau pulseIn qua | Stub không phải mô phỏng chính xác thời gian/điện |
| Chromium thực, HTTP Flask loopback | 6 mục qua: W+A, đủ 4 chéo, nhả từng phím, reset, hai chủ, joystick ở viewport điện thoại | USB/camera giả; chưa thử màn cảm ứng hoặc WiFi xe thật |
| ATmega2560 AVR | Build/link ELF và HEX thành công | GCC AVR 5.4.0, avr-libc 2.0, Arduino AVR core 1.8.3 nguyên bản từ Debian; không dùng stub |
| Bộ nhớ AVR | Flash 25.866 byte (9,9%); static RAM 2.424 byte (29,6%) | Chưa đo stack cực đại/độ trễ thực |
| Nạp board | Chưa làm | Chờ quy trình nguồn/backup/thử của người vận hành |
| Bánh treo/sàn | Chưa làm | Chưa xác minh góc chéo, khoảng hở, servo, tốc độ, A2 và cua thực |

Chi tiết gateway: xác thực/CSRF, một chủ, truyền vector, thứ tự, lease cũ sau nhận lại quyền, STOP chặn gói muộn, hết quyền, thiếu PWM mới, thiếu ACK, người xem STOP thu hồi chủ, profile phải xác nhận và CRC.

C++: mixer tiến/ngang/xoay và bão hòa, ramp đảo chiều qua 0, không bật né thì từ chối, hành lang hẹp từ chối, không echo/sonar cũ dừng, chu trình lý tưởng đầy đủ với ba mẫu cạnh hợp lệ, A2 mất thì quay về pha tìm và A2 ổn định mới bàn giao. Không phải phép chứng minh quỹ đạo va chạm cho mọi vật.

Đối chiếu nguồn: 13 hàm bảo vệ giữ nguyên; thân handleLineAndObstacleMode giữ nguyên sau khi loại khối vào né mới và đổi lời gọi né; bảng INNER/OUTER, pin, LOW, tốc độ/thời gian cua giữ nguyên. drive() thêm đo PWM và cap đầu ra lúc USB sở hữu; không đổi mapping dấu motor.

Các chỉnh sửa thiết kế có chủ đích cần thử: kích hoạt né trước 60 cm ở trạng thái line thường; giới hạn thử đầu ra mặc định80 (cả line/cua); né mặc định tắt; chỉ mở trần255 bằng thao tác profile; servo quét mới dùng phát từng xung thay vì vòng hold; USB sở hữu thì ESP không được tranh lệnh chuyển động.

## Chạy lại kiểm tra

```bash
python3 -m unittest discover -s tests -p test_gateway.py -v
g++ -std=c++17 -Wall -Wextra -Werror tests/test_motion.cpp -o /tmp/vector_motion
/tmp/vector_motion
g++ -std=c++17 -Wall -Wextra -Werror -Itests tests/test_firmware.cpp -o /tmp/vector_firmware
/tmp/vector_firmware
```

Với Flask/NumPy/Playwright/Chromium, terminal riêng `python3 tests/serve_ui.py`, rồi `node tests/test_ui.js`. Fixture nghe **127.0.0.1:18766**, USB/camera giả và credentials chỉ dành cho test loopback. Không dùng fixture để điều khiển xe.

Build AVR (không upload):

```bash
python3 tests/build_avr.py /path/to/avr/bin /path/to/arduino/avr /tmp/vector-avr-build
```

Debian Arduino AVR1.8.7 không build được với GCC5.4 do DECIMAL_DIG ở WString; đã dùng core1.8.3 tương thích, không vá core/thay môi trường để che lỗi. Arduino IDE trên PC cần Verify trước khi Upload.

Không xuất ELF/HEX kiểm thử vào gói dùng trên xe; người dùng biên dịch source đúng board/cặp file, kiểm tra và chủ động nạp sau chuẩn bị nguồn.

## Hotfix mô phỏng

Xem SIMULATION_FIX.md. Thêm 3 test quyền khi thiếu USB và hết lease mô phỏng; kiểm tra Chromium với serial_worker thật chạy nền nhưng serial=None, không mở cổng: nhận quyền được giữ qua retry, chọn simulation và W+A làm mô hình chuyển động, không lỗi JavaScript. Firmware giữ nguyên.

## Hotfix joystick

Xem JOYSTICK_FIX.md: thay issued_ms suy từ telemetry bằng ticket server một lần hạn300 ms. 18 test gateway qua; Chromium cảm ứng có telemetry trễ450 ms tái hiện lỗi cũ và bản mới đi chéo/thả dừng, không lỗi JS. Đây là thử host, chưa thử trực tiếp điện thoại/Jetson.

## Hotfix ACK nhanh

Xem ACK_FIX.md. Bản trước mất ACK nếu ACK tới trước khi write trả về; tái hiện bằng fake serial đồng bộ. Bản mới đăng ký pending trước write và khóa xử lý ACK, không đổi ngưỡng timeout. 22 test gateway qua, diagnostic không ghi USB và không xuất credential/lease/ticket. Chưa thử trực tiếp sửa này trên Jetson.

## Hotfix PING cũ

Xem PING_FIX.md. Dữ liệu người dùng chỉ rõ pending P/413 ms gây ACK_TIMEOUT. Khi ACK OK mới hơn tồn tại, chỉ loại PING cũ; không loại ACK lệnh chạy/dừng đang thiếu. 26 test gateway qua; firmware/ngưỡng timeout giữ nguyên; chưa thử trực tiếp trên hardware.
