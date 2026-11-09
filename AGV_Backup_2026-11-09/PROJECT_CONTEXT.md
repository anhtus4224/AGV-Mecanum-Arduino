# PROJECT_CONTEXT — AGV Mecanum

Ghi ngày 09/11/2026, múi giờ Asia/Saigon. Tài liệu sao lưu, không phải thay đổi thuật toán.
Tên môi trường người dùng muốn giữ: **Thiết lập anh-tu**. Metadata môi trường quan sát được nằm trong `backup_audit_2026-11-09/ENVIRONMENT_METADATA.json`.

## 1. Nguồn sự thật và mức xác nhận

- **File đọc được:** `user_firmware_confirmed.ino`, hai ZIP CUAXOAYNGANG trong `attachments/`, các phiên bản AGV, mã server và bộ SAFE1 hiện có. Đường dẫn và SHA-256 chi tiết: `backup_audit_2026-11-09/inventory.csv`, member ZIP: `archive_members.json`.
- **Người dùng xác nhận trong trò chuyện:** xe đã bám line tốt ở PWM 250; V2 xoay góc chạy tốt; động cơ 4 chiếc JGB37-520 12 V 45 RPM, không encoder; xe khoảng 30 × 30 cm, thanh trước cách tâm khoảng 14–15 cm; sketch MOTOR_LOCK khiến bốn bánh đứng yên.
- **Đề xuất đã ghi thành file, chưa được người dùng xác nhận thử xe:** SAFE1, đặc biệt `agv_web_safe1_final/`. Không gọi bộ này là firmware đã nghiệm thu.
- Các tài liệu cũ ghi “chưa chạy trên xe” là trạng thái khi sinh file; phản hồi người dùng sau đó “V2 chạy tốt” là bằng chứng thử thực tế ở cấp phiên bản, không có flash readback/hash xác nhận chính xác firmware đang nạp.
- Không có kết nối trực tiếp với xe/Jetson trong nhiệm vụ sao lưu. Không xác nhận server nào đang chạy chỉ qua tên file trong workspace.

## 2. Kiến trúc

```text
Trình duyệt web -- HTTP/WiFi --> Jetson, Flask stream_server.py (cổng 5000)
                                  | camera/OpenCV -> ảnh MJPEG/dashboard
                                  | USB serial 115200
                                  v
                             Arduino Mega 2560
                         line + siêu âm + servo + nút
                                  |
                        8 chân PWM -> BTS7960 -> 4 motor mecanum

Nhánh cũ: ESP -> Mega Serial2 9600, nhận ký tự điều khiển.
SAFE1 final: mặc định tắt xử lý lệnh ESP cũ để tránh hai nguồn điều khiển.
```

- Board người dùng: Arduino Mega2560 Pro Embed CH340G. Phần công suất BTS7960 theo bối cảnh dự án; nguồn code xác minh được 8 ngõ RPWM/LPWM, không xác minh riêng đấu chân EN hay dây công suất thực tế.
- Mega thực thi bám line, xoay 90° bắt lại line, né vật cản. Camera trên Jetson xử lý/hiển thị; bộ SAFE1 không dùng camera ra lệnh motor tự hành.
- Cảm biến gầm: một thanh TCRT5000 5 kênh phía trước, mức LOW khi nhìn đen theo kiểm tra người dùng.
- Có 4 siêu âm trước/sau/trái/phải; chỉ siêu âm trước gắn servo theo mô tả. Model cụ thể chưa đủ bằng chứng để chốt.
- Nguồn logic 5 V/GND được người dùng mở thêm hàng cắm. Chưa có sơ đồ nguồn hoàn chỉnh hoặc số đo điện áp pin đã hiệu chuẩn.

## 3. Pin phần cứng đã có trong firmware người dùng chốt

Nguồn: `user_firmware_confirmed.ino` và firmware SAFE1 final; không đổi pin khi sửa giao tiếp.

| Chức năng | Pin Mega |
|---|---|
| Motor D1 RPWM / LPWM | 44 / 3 |
| Motor D2 RPWM / LPWM | 5 / 9 |
| Motor D3 RPWM / LPWM | 7 / 8 |
| Motor D4 RPWM / LPWM | 11 / 12 |
| Servo | 10 |
| Nút đổi chế độ, INPUT_PULLUP | 31 |
| Đo điện áp | A5 |
| Thanh line RAW1..RAW5 | A0, A1, A2, A3, A4 |
| Siêu âm trước TRIG / ECHO | 22 / 23 |
| Siêu âm sau TRIG / ECHO | 24 / 25 |
| Siêu âm trái TRIG / ECHO | 26 / 27 |
| Siêu âm phải TRIG / ECHO | 28 / 29 |
| USB Serial | 115200 baud |
| Serial2 / ESP cũ | 9600 baud; Mega Serial2 TX2=16/RX2=17 theo chuẩn board, chưa đo lại dây |

Hàm `drive(fl, fr, rl, rr)` đảo dấu D1 và D3, giữ dấu D2 và D4. Không tự đảo cực motor hoặc gán lại trái/phải từ ảnh chụp.
Servo phát xung bằng phần mềm, không dùng thư viện Servo trong firmware này. Phân biệt header Arduino giả lập với thư viện thật.

Đo điện áp trong code: `raw * (5.0 / 1023.0) * 4.0`; nếu raw < 30 trả giá trị dự phòng 12.4. Không coi giá trị dự phòng là số đo pin, không suy ra điện áp danh định từ log 18.x V khi chưa hiệu chuẩn.

## 4. Thông số phiên bản người dùng chốt và SAFE1 final

PWM là lệnh 0..255, **không phải tốc độ m/s hoặc RPM đo được**. 255 đã là mức tối đa của analogWrite 8-bit.

| Hằng số | Giá trị |
|---|---:|
| WIFI_MAX_SPEED | 255 |
| LINE_FAST_SPEED | 255 |
| LINE_BASE_SPEED | 120 |
| STRAIGHT_TRIM_MAX | 20 |
| SLEW_STEP | 40 |
| CONTROL_PERIOD_MS | 10 ms |
| CURVE_OUTER_MAX | 190 |
| CURVE_EXIT_MS | 60 ms |
| ENABLE_TURN_PULSE | false |
| RUNOUT_RIGHT_MS / RUNOUT_LEFT_MS | 608 / 608 ms |
| RUNOUT_SPEED | 255 |
| TURN_RIGHT_SPEED / TURN_LEFT_SPEED | 255 / 255 |
| MIN_TURN_MS | 200 ms |
| TURN_TIMEOUT_MS | 2200 ms |
| SETTLE_MS | 80 ms |
| CORNER_RESUME_MS | 120 ms |
| CORNER_LOCK_MS | 1200 ms |
| MANUAL_TURN_TIMEOUT_MS | 180 ms |
| FAILSAFE_MS cho lệnh lái tay khác | 700 ms |
| HOLD_LAST_MS / CREEP_MS / SEARCH_MAX_MS | 150 / 300 / 1200 ms |
| AVOID_STRAFE_SPD | 160 |
| AVOID_FORWARD_SPEED | 200 |
| AVOID_OUT_MS / AVOID_FORWARD_MS | 2900 / 3500 ms |
| AVOID_BACK_BLIND_MS / AVOID_BACK_SEARCH_MS | 2000 / 4500 ms |
| AVOID_RETURN_SPEED (cục bộ) | 150 |
| OBSTACLE_CM / SONAR_SLOT_MS | 18 cm / 40 ms |

Bảng INNER={120,0,0,0,0}; OUTER={120,190,235,255,255}. Giữ nguyên khi chỉ sửa web/USB.
Những giá trị 190/200/210/250, tiến bù 1216 ms và thời gian né khác xuất hiện ở bản cũ; không tự áp chúng vào bản chốt.

## 5. Cảm biến line và các bài thử

- `LINE_DETECTED=LOW`; `REVERSE_SENSOR_ORDER=false` trong bản chốt. Code gán RAW1..5 thành L2,L1,M,R1,R2 khi false; đó là quy ước logic trong code. Góc nhìn ảnh OUT1..OUT5 có thể đảo trái/phải; phải thử từng mắt theo hướng tiến của xe trước khi thay mapping.
- DATA in theo RAW A0..A4. Người dùng từng đo OUT2 trên đen -> 01000, ADC khoảng 970,17,947,968,968; OUT4 -> 00010, khoảng 970,968,969,17,969. Các số chỉ là dữ kiện lần thử đó, không phải ngưỡng analog đã hiệu chuẩn chung.
- Lúc lỗi 00000, ADC đa số khoảng 977..979: người dùng xác nhận có khoảng mù giữa hai mắt. Khoảng cách mắt khoảng 2.5 cm, line ban đầu rộng 1.7 cm. Dán rộng khoảng 3 cm hết khoảng mù theo thử nghiệm người dùng; đã hạ thanh xuống khoảng 2.5 mm.
- Từng có lỗi cua phải thành trái; người dùng cung cấp ảnh thứ tự OUT và sau đó xác nhận xe chạy tốt. Không tự đảo mapping lại khi chưa đo.
- Thử tiến 80 cm: 6.68 s, 6.75 s, 6.69 s, trung bình khoảng 6.707 s. Đây là thử do người dùng báo, không phải vận tốc có encoder; mốc bắt đầu/kết thúc không được xác minh độc lập.
- Ước lượng ban đầu từ 14.5 cm / 80 cm cho tiến bù khoảng 1216 ms; xe sau đó lố khoảng 30 cm ở đầu dò. V2 dùng 608 ms theo tỷ lệ thực nghiệm, không phải bảo đảm tâm xe đúng giao điểm trong mọi điều kiện.

## 6. Bám line và xoay góc

- Sai số có trọng số [-4,-2,0,2,4], chia số mắt thấy line. Đoạn giữa dùng PWM nhanh, giảm nhẹ một bên theo sai số; mắt rìa kích hoạt xử lý cua, giữ trạng thái trong thời gian CURVE_EXIT_MS. Có giới hạn slew.
- Mất line: giữ lệnh giới hạn trong HOLD_LAST_MS, sau đó tìm theo sai số gần nhất hoặc bò ngắn khi chưa rõ hướng; hết giới hạn thì dừng. Không chạy/tìm mù vô hạn. Trở lại line có thể tự chạy tiếp khi vẫn AUTO.
- Phát hiện góc phải: M && R1 && R2 && !L2; trái đối xứng. Cần 2 mẫu, có khóa góc và khoảng sau né cản.
- Trạng thái chính: IDLE_LINE -> RUNOUT_90 -> TURNING_90 -> SETTLE_90 -> IDLE_LINE; lỗi vào CORNER_FAULT. Enum BRAKE_90 còn tồn tại nhưng không phải pha phanh đang được dùng trong luồng này.
- Tiến bù PWM255 trong 608 ms, ghi nhận đã rời line cũ cả trong tiến bù. Xoay một mức PWM255; sau khi đã rời line, đủ MIN_TURN_MS và M thấy line với hai rìa tắt thì chốt PWM0.
- **Ở V2 thực tế trong file, cornerSideSeen chỉ ghi nhận, không phải điều kiện bắt buộc để chốt.** Một số mô tả cũ nói phải thấy mắt bên trước; không lấy mô tả đó thay cho code V2.
- MIN_TURN_MS chống nhận lại quá sớm; TURN_TIMEOUT_MS giới hạn tìm line, không đo chính xác 90°. Không có encoder/IMU xác nhận góc trong code.
- Sau 80 ms kiểm tra line; lỗi SPIN_TIMEOUT / LINE_MOVED_AFTER_STOP có thể tự tiếp tục khi cụm giữa ổn định 120 ms và không có vật cản. Lỗi vật cản/trạng thái không tự khôi phục chỉ vì mắt giữa thấy line.

## 7. Né vật cản

- Siêu âm trước có hai lần phát hiện gần hợp lệ (trong code >3 cm và <=18 cm) kích hoạt né ở trạng thái bám line thường. Trong xoay góc, vật cản gây lỗi dừng.
- Dừng, đọc siêu âm bên, quét servo 135° và 45°, trả 90°, chọn hướng theo khoảng bên và chếch.
- Dạt ra theo AVOID_OUT_MS -> tiến song song theo AVOID_FORWARD_MS -> dạt ngược đoạn mù theo AVOID_BACK_BLIND_MS -> tìm line trong giới hạn AVOID_BACK_SEARCH_MS.
- Pha tìm lại line dừng khi bất kỳ mắt trong cụm RAW2/3/4 thấy đen, rồi trả về bám line. Không phải xác nhận tọa độ toàn cục.
- Đoạn chạy né dùng vòng lặp có kiểm tra hủy, chưa phải toàn bộ thiết kế event-loop không chặn. SAFE1 final thêm phục vụ USB/telemetry trong kiểm tra hủy và quét servo.

## 8. Lỗi giao tiếp và bộ SAFE1

Bằng chứng: server gốc trích từ `attachments/.../import os.docx`, `agv_connection_repair/original_server.py`, `normalized_server.py`; firmware gốc và các bản fixed/final.

- Server cũ gửi `CFG:OBS=...,FWD=...,BACK=...,BASE=...,FAST=...`. Firmware gốc nhận USB từng ký tự, một số chữ là F/B/L/R/E/M... nên có thể bị hiểu thành lệnh chạy hoặc đổi chế độ. Đã xác định không tương thích; không chứng minh đây là nguyên nhân duy nhất mọi lần bánh quay.
- `serial_worker()` cũ thụt dòng sai ở nhánh SONAR/DATA, có khả năng dùng parts chưa gán hoặc dữ liệu cũ; except che lỗi và mở lại cổng.
- UI cũ có đảo nhãn chế độ, quỹ đạo tính từ lệnh lái tay thay vì đo thực tế; hai định nghĩa FSM gây ghi đè hàm.
- Người dùng thử MOTOR_LOCK, log PWM=0 và xác nhận bốn bánh đứng yên. Không từ đó khẳng định mọi driver/dây nguồn đều tốt trong mọi chế độ.

SAFE1 ghép **đúng cặp**:

- Arduino: `agv_web_safe1_final/agv_mega_safe/agv_mega_safe.ino`.
- Jetson: `agv_web_safe1_final/stream_server.py` + `agv_serial_link.py`, cùng thư mục.
- Khung `@HELLO`, phản hồi `AGV:SAFE1`; `@PING`, `@STOP`, `@MODE:AUTO`, `@MODE:MANUAL`, `@DRIVE:F/B/L/R/Q/E`, kết thúc newline.
- USB không có khung không được điều khiển motor; hostStop về MANUAL, xóa trạng thái góc và PWM0. AUTO là yêu cầu rõ chế độ, không đảo mỗi lần gửi lại.
- HOST_TIMEOUT_MS=1500 có tác dụng sau khi đã có hostSession; không phải công tắc cắt nguồn vật lý và không bao quát mọi cách khởi động độc lập. PING không gia hạn timeout lệnh lái tay.
- Python gửi PING khoảng 0.3 s, timeout telemetry 2.5 s, có khóa ghi/exclusive serial, kiểm tra dữ liệu và báo lỗi. Bản final phục vụ telemetry khi né để tránh mất kết nối giả.
- Final đặt ENABLE_LEGACY_ESP=false; SAFE1 trước đó còn nhận ESP cũ. Không nhầm hai bản.
- Final cố gửi STOP khi server dừng bình thường/SIGTERM, watchdog là dự phòng khi không nhận được liên lạc. Đóng tab web và tắt Jetson không phải cùng một tình huống; không mặc định watchdog dừng AUTO chỉ vì trình duyệt đóng tab trong khi backend vẫn PING.
- Nút tuning web không nạp hằng số vào xe; trả lỗi có giải thích và không gửi CFG. Muốn chỉnh thông số phải làm nhiệm vụ riêng có kiểm tra.
- Server final tách khối bản đồ 3D để lỗi CDN không chặn phần điều khiển còn lại. Chưa có kiểm chứng UI/camera trực tiếp trên Jetson của người dùng.
- Không dùng `agv_serial_link.py` SAFE1 với firmware gốc: bản gốc sẽ đọc từng ký tự @HELLO và có thể kích hoạt E/L. Nhiệm vụ hiện tại không nạp firmware hay chạy điều khiển.

## 9. Quỹ đạo, encoder và quyết định không triển khai

- Motor không “gửi PWM về”: PWM là lệnh ra; encoder mới là phản hồi xung vòng quay. Không có encoder thì PWM không cho biết chính xác vị trí/quãng đường.
- Server cũ lái tay gán fwd/omega rồi tích phân, nên vệt là ước lượng lệnh, kể cả khi bánh treo; AUTO trên Mega không đi qua cùng route cập nhật đó.
- SAFE1 đặt current_speed=0, odometry_available=false và hiển thị CHƯA CÓ ODOM/CHƯA ĐO. Không gọi mất vệt AUTO là chỉ do phần cứng hoặc lỗi thuật toán bám line.
- Ước lượng PWM-thời gian, camera trên cao + AprilTag, định vị thị giác/LiDAR, encoder+IMU là phương án đã trao đổi; **chưa triển khai trong file final**. IMU đơn lẻ không bảo đảm vị trí ổn định.
- Phương án thêm 3 thanh 5 mắt và đi ngang qua góc từng được khảo sát; người dùng sau đó chuyển sang một thanh trước và xoay thân tại góc để giữ cảm biến trước theo hướng chạy. `agv_four_sensors/` chỉ là sketch kiểm tra, không coi là cấu hình đã lắp/chạy.

## 10. Trạng thái kiểm thử và triển khai

- Có stub Arduino, test .cpp, test Python và JS check trong workspace. Bài trước báo pass kiểm tra cú pháp g++ với stub và các test mô phỏng; đó không phải biên dịch AVR hay thử xe thật.
- Test final trước đây còn nằm `/tmp`, đã chép nguyên byte vào `backup_audit_2026-11-09/recovered_tmp/` có provenance/hash. Không sửa đường dẫn hay chạy lại test trong nhiệm vụ sao lưu.
- Chưa có xác nhận từ người dùng về việc đã cài SAFE1 final và hoàn tất kiểm tra STOP/watchdog trên xe. Không đánh nhãn final là “đã giải quyết hoàn toàn trên phần cứng”.
- Đường dẫn Jetson trong ảnh: `/home/nguyennhutoan_uav/stream_server.py`, service `agv_server.service`; USB by-id CH340 từng trỏ `/dev/ttyUSB0`; PC từng COM5. Những tên này có thể thay đổi và chưa kiểm tra hiện tại.

## 11. Bảo toàn và bước tiếp theo

- Bản CUAXOAYNGANG người dùng gửi và toàn bộ phiên bản lịch sử phải giữ riêng; không ghi đè bằng SAFE1.
- `/workspace` không phải Git repo hoạt động. `/workspace/anh-tu` có Git nhưng chưa có commit/file tracked; origin là `https://github.com/anhtus4224/anh-tu.git`, khác đích sao lưu.
- Đích người dùng yêu cầu: `https://github.com/anhtus4224/AGV-Mecanum-Arduino` — chưa push. Xem báo cáo backup để biết kiểm tra quyền truy cập và danh sách file dự kiến.
- Không tự thay môi trường, đổi remote, commit, push, reset/clean hoặc xóa file trong nhiệm vụ sao lưu này.
