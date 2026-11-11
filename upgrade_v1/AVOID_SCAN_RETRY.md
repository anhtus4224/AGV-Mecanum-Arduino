# AVOID_SCAN_RETRY_V1 — lấy mẫu chọn hướng né, 11/11/2026

Nguồn: SCAN_DIAG_V1, commit357199a95d93e33b986258a7ee0a2494ded90c3c,
trên bộ TOUCH_VECTOR_V2 đã triển khai. Nhánh sửa riêng
fix/avoid-scan-sampling-2026-11-11; giữ nguyên main và các bản trước.

## Bằng chứng mới và giới hạn kết luận

Người dùng đã báo tiến/thả dừng, dạt trái/phải, các cảm biến, line/cua tốt;
né dừng dù đầu sonar quay trái/phải/giữa. Ảnh bố trí cho thấy một phía có vẻ
thoáng hơn; ảnh không đo được chính xác bề rộng và toàn bộ vùng thân quét.
JSON SCAN_DIAG sau lỗi đã ghi đúng bộ chọn:

```json
{"avoid_fault":"NO_CONFIRMED_CORRIDOR","avoid_scan":{"board_ms":792152,"chosen_side":0,"diag_left_cm":999,"diag_right_cm":999,"left_cm":71,"phase_after_choice":9,"right_cm":40},"vector_status":{"armed":true,"cap":200,"phase":0}}
```

Đây là số đo thực do người dùng gửi. Trái71 đạt điều kiện bên >59 cm,
phải40 chưa đạt, cả hai chéo999 là không echo hợp lệ. Mã cũ vốn cho phép
chọn chỉ một bên đủ điều kiện, không bắt buộc hai bên đều >59. Lượt này
không chọn trái vì chưa có bằng chứng chéo trái, không phải vì phải chỉ40.

Phát hiện cụ thể trong mã: readUltrasonicCM dùng pulseIn timeout8000 us,
tương đương khoảng136 cm, trong khi choose chấp nhận khoảng đo <400 cm.
Vật phản xạ xa hơn136 cm có thể bị loại thành999 dù còn trong miền dự kiến.
**Chưa chứng minh echo thực của hai lần999 tới sau8 ms**: mất phản xạ do góc,
vật tròn, góc lắp, điện hoặc nhiễu cũng có thể gây999. Bản này sửa hạn chế
cửa sổ đo và lấy một mẫu; không hứa mọi999 trong không gian thoáng sẽ biến mất.

## Thay đổi có giới hạn

1. Chỉ khi xe đã dừng quét, đo chéo bằng cửa sổ24000 us (~408 cm danh nghĩa).
   Giới hạn hợp lệ <400 cm giữ nguyên. Các lần đo line/sonar trong chuyển động
   vẫn dùng hàm8 ms cũ; không sửa hàm đọc gốc.
2. Sau440 ms ổn định servo như cũ, lấy3 mẫu mỗi góc, cách nhau ít nhất60 ms
   sau lần đo trước. Không gom thành vòng chờ3 mẫu; giữa các mẫu vòng lặp vẫn
   đọc lệnh, gửi telemetry và kiểm watchdog. Một pulseIn vẫn có thể chờ24 ms;
   chưa đo độ trễ thực trên board, không chứng nhận thời gian thực cứng.
3. Cần ít nhất2/3 echo hợp lệ. Dùng **giá trị gần nhất trong các echo hợp lệ**,
   không lấy trung bình để bỏ qua vật gần. Một echo gần vẫn chặn hướng nếu
   có đủ quorum. Thiếu quorum trả999/unknown, không tự cho là thoáng.
4. Chỉ cần một bên có side và diagonal đạt tiêu chí. Đã có test bên trái71,
   phải40, chéo trái200 hợp lệ, chéo phải999: chọn trái. Không lấy hướng có999
   làm dự phòng khi cả hai chưa xác định.
5. Gateway giữ avoid_scan và thêm avoid_samples: số mẫu tổng/hợp lệ từng bên,
   stationary_timeout_us=24000 và board_ms để ghép đúng lần quét.
   gateway_revision=AVOID_SCAN_RETRY_V1. Nếu board_ms hai snapshot khác nhau
   thì không kết luận chúng thuộc cùng lần quét.

VectorMotion.h giữ nguyên byte: kích thước47×34 cm, margin12, tiêu chí bên59,
chéo45.84, ngưỡng bắt đầu55, mixer/dấu, các pha OUT/PASS/RETURN/CENTER/HANDOFF
và nội suy RETURN400 ms. Không đổi pin, servo135/45/90, line/cua, baudrate,
watchdog250/700, ACK/PWM400, lease800 ms hoặc logic STOP. Mặc định cap80,
né tắt. Đường đi lý tưởng vẫn ra chéo → vượt → chuyển về dần → A2 ổn định →
bám line; các guard có thể dừng khi không đủ dữ liệu/khoảng hở.

## Chưa giải quyết bằng giả định

- Không tự hạ ngưỡng theo ảnh hoặc coi không echo là đường trống.
- Chưa đo gốc sensor, góc thực servo, góc mù và đường đi cơ khí. Không tuyên
  bố sơ đồ đường cong mong muốn đã được thực hiện trên xe.
- Sonar trước/sau/hai bên lúc chạy vẫn phải hợp lệ theo guard cũ. Vì vậy nếu
  chọn được hướng nhưng sau đó mất echo, có thể dừng với lỗi khác. Phân biệt
  lỗi chọn hướng với SONAR_REAR_UNKNOWN/FRONT_UNKNOWN/SIDE_UNKNOWN khi chạy.
- Chưa sửa guard phía sau hoặc giả định vùng thân quét dựa trên ảnh; cần
  bằng chứng và vị trí lắp sensor trước các thay đổi đó.
- JSON vừa gửi là cap200; lượt kiểm chứng mới bắt đầu80, không tăng cap để
  vượt qua NO_CONFIRMED_CORRIDOR. Chưa chứng nhận né200/255.

## Kiểm chứng

45 test Python gateway/bảo toàn nguồn qua; grammar Python3.6 qua, runtime
Python3.12. C++ với Arduino stub mô hình pulseIn có timeout: tái hiện8 ms
bỏ echo12 ms (204 cm), bản quét24 ms nhận; xác minh khoảng cách mẫu, chọn
một phía, thiếu quorum/all999 từ chối, STOP không tự tiếp tục quét, host
watchdog700 ms trong scan. Các echo12 ms/200 cm trong test là **dữ liệu giả**,
không phải echo đã đo trên xe người dùng. Khi toàn bộ mẫu vẫn999, test vẫn
đòi NO_CONFIRMED_CORRIDOR và PWM0; không sửa assertion để cho xe đi mù.

Các bộ C++ motion, envelope, protocol, wheel50 tổ hợp, scan samples và scan
integration qua. 13 hàm bảo vệ, toàn thân line/cua và prefix hằng số pin/sensor/
cua được kiểm hash như trước. Header FSM/mixer/geometry so byte với357199a
không đổi. Build ATmega2560 thực qua: flash27.538 B, RAM tĩnh2.536 B,
GCC AVR5.4/core1.8.3, không upload. Stub không chứng minh STOP/timing cơ khí.
Chưa nạp hoặc thử xe bản sửa này.

Chạy lại từ upgrade_v1: unittest discover tests/test_*.py; g++17
-Wall -Wextra -Werror các test_scan_samples.cpp, test_scan_firmware.cpp
(thêm -Itests cho firmware), test_firmware.cpp, test_motion.cpp,
test_avoid_envelope.cpp, test_wheels.cpp. Build AVR bằng tests/build_avr.py
như TEST_REPORT_TOUCH_V2.md. Không chạy launcher, mở USB hoặc bật motor trong
test cloud. Không cần chạy lại browser vì không thay JS/HTML hay request API.

## Tệp cần cập nhật và triển khai

Gói AGV_VECTOR1_SCAN_RETRY_2026-11-11.zip chứa gateway và **cả thư mục sketch
gồm3 file**: mega_vector_v1.ino, VectorMotion.h nguyên trạng, **ScanSamples.h
mới bắt buộc**; tài liệu và SCAN_RETRY_SHA256SUMS.txt. Không chỉ lấy riêng.ino.
vector_controls.js, stream_server_vector_v1.py, run_vector_v1.py giữ đúng bộ
TOUCH_VECTOR_V2 đang dùng, không lấy bản main. AVOID_SCAN_RETRY.patch là diff
runtime từ357199a để review, không tự chạy script patch cũ.

Trong chat triển khai: giữ DỪNG/nhả quyền, backup gateway đang dùng và giữ
nguyên nguồn Mega SCAN_DIAG; tải/hash gói mới; dừng đúng server, chép gateway
qua staging và kiểm hash; mở đúng sketch3 file, Verify; shutdown Jetson và
đợi30 s trước tắt tổng, chuyển USB/nạp theo cấu hình nguồn đã xác nhận với
người vận hành. Nối Jetson lại, kiểm IP/USB, chạy launcher. Không tự điều khiển
xe/SSH/nạp board từ cloud. Tài liệu chung: docs/TRIEN_KHAI_TOUCH_VECTOR_V2.md.

Sau khởi động: xác nhận revision, ready và cap80 thực trong vector_status;
thử STOP rồi mới bố trí một lượt né ở khu vực đã kiểm tra khoảng trống.
Nếu lỗi, giữ xe dừng và lấy avoid_scan, avoid_samples, avoid_fault, vector_status
cùng lượt. Không yêu cầu thử lại liên tục, không bỏ guard để ép chuyển động.

Rollback: phục hồi gateway và nguyên bộ sketch2 file SCAN_DIAG đã lưu,
Verify/nạp theo quy trình nguồn/USB người vận hành; bỏ qua ScanSamples.h khi
mở nguyên thư mục nguồn cũ. Backup source không phải đọc ngược firmware Mega.
Không thay bộ đang chạy bằng firmware ký tự gốc/SAFE1.

## Tải đúng bản

- [AGV_VECTOR1_SCAN_RETRY_2026-11-11.zip](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/avoid-scan-sampling-2026-11-11/AGV_VECTOR1_SCAN_RETRY_2026-11-11.zip)
- [upgrade_v1/agv_vector_gateway.py](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/avoid-scan-sampling-2026-11-11/upgrade_v1/agv_vector_gateway.py)
- [upgrade_v1/mega_vector_v1/mega_vector_v1.ino](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/avoid-scan-sampling-2026-11-11/upgrade_v1/mega_vector_v1/mega_vector_v1.ino)
- [upgrade_v1/mega_vector_v1/VectorMotion.h](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/avoid-scan-sampling-2026-11-11/upgrade_v1/mega_vector_v1/VectorMotion.h)
- [upgrade_v1/mega_vector_v1/ScanSamples.h](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/avoid-scan-sampling-2026-11-11/upgrade_v1/mega_vector_v1/ScanSamples.h)
- [upgrade_v1/SCAN_RETRY_SHA256SUMS.txt](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/avoid-scan-sampling-2026-11-11/upgrade_v1/SCAN_RETRY_SHA256SUMS.txt)
- [upgrade_v1/AVOID_SCAN_RETRY.patch](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/avoid-scan-sampling-2026-11-11/upgrade_v1/AVOID_SCAN_RETRY.patch)
