# TOUCH_VECTOR_V2 — 11/11/2026

## Nguồn và phạm vi

Nguồn: `anhtus4224/AGV-Mecanum-Arduino`, nhánh
`fix/vector-setpoint-ack-2026-11-10`, commit
`882daf1239ab6a55617726c5eda8e3aefb7bdf9b`. Đã đối chiếu bằng
`git ls-remote` trên GitHub trước khi tạo nhánh sửa
`fix/touch-strafe-avoid-2026-11-11`. Không sửa main hay nhánh nguồn.
Đã đọc AGENTS.md và tài liệu trong upgrade_v1; checkout này không có
PROJECT_CONTEXT.md hoặc inventory. Không chạy script patch cũ.

Người dùng báo đã thử tốt line thẳng, cua/bắt lại line PWM120/160,
STOP/thả tay, năm mắt line (A2/OUT3/S3 giữa), bốn ô sonar và hết lỗi xám
sau SETPOINTFIX. Đây là báo cáo người dùng, không phải các bài thử xe của
phiên này. Chưa SSH/đối chiếu hash Jetson hôm nay; SETPOINT_ACK_V1 mới là
revision triển khai được báo lại.

## Dạt ngang: chưa kết luận nguyên nhân trên xe

Đã đi từ nút A/D → vector strafe −1/+1 → D ±255 → vmMix → vmRamp →
drive → tám analogWrite. Bảng phần mềm hiện có khớp lệnh L/R gốc, không
tái hiện bánh mất PWM trong stub. **Không đảo dấu, đổi pin hoặc sửa mixer
để đoán theo triệu chứng. Chưa xác nhận sửa được dạt ngang trên xe.**

PWM logic theo thứ tự FL, FR, RL, RR, khi đã hết ramp (c = cap):

| Hướng | FL | FR | RL | RR |
|---|---:|---:|---:|---:|
| Tiến | c | c | c | c |
| Lùi | −c | −c | −c | −c |
| Trái | −c | c | c | −c |
| Phải | c | −c | −c | c |
| Tiến trái | 0 | c | c | 0 |
| Tiến phải | c | 0 | 0 | c |
| Lùi trái | −c | 0 | 0 | −c |
| Lùi phải | 0 | −c | −c | 0 |
| Xoay trái | −c | c | −c | c |
| Xoay phải | c | −c | c | −c |

`drive()` giữ cực điện [−FL,+FR,−RL,+RR]. Các cặp RPWM/LPWM giữ nguyên:
FL44/3, FR5/9, RL7/8, RR11/12. Ví dụ phải/cap80: logic
[80,−80,−80,80], driver [−80,−80,80,80], cả bốn kênh có yêu cầu khác 0.
Đó là yêu cầu điện, không phải chiều bánh quan sát hay vận tốc đo được.

Chẩn đoán chỉ đọc `/control/diagnostics`, sau đăng nhập:

- `gateway_revision=TOUCH_VECTOR_V2`.
- `requested_vector`: D vừa ghi USB, sequence, [tiến,phải,xoay] theo PWM.
- `last_drive_ack`: sequence/status ACK gần nhất của D; ghi USB chưa phải ACK.
- `firmware_target`: `VECTOR_TARGET` từ Mega mới, bốn mục tiêu sau mixer/cap;
  sequence là D tạo mục tiêu, không phải PING. Sequence0 dành cho STOP/né/AUTO.
- `current_pwm`, `motion_age_ms`: PWM logic sau ramp/cap từ MOTION.
- `driver_pwm`: suy ra từ MOTION và dấu drive; **không đo trực tiếp chân**.
- `avoid_fault`, `link_events`: sonar/ACK/PWM mất dữ liệu; không chứa lease/ticket.

Nếu dùng Mega cũ, firmware_target có thể chưa có. Khi thay cặp firmware/USB,
khởi động lại gateway để không đọc telemetry cũ từ phiên trước. Muốn phân biệt
lỗi lệnh với đấu dây/driver/kênh PWM, cần ghi đồng thời các trường trên và
video bốn bánh trong bài thử bánh treo có kiểm soát; chưa tự suy ra phần cứng hỏng.

## Cảm ứng, thứ tự request và bàn giao

Tái hiện trên commit nguồn bằng Chromium mobile/touch, laptop STOP → Nhả quyền
→ điện thoại Nhận quyền. Mỗi request điều khiển trễ giả130 ms: luồng cũ phải
renew rồi vector, khoảng cách vector lớn nhất323 ms, vượt watchdog Mega250 ms.
Fixture không có Mega, nên đây là tái hiện khoảng hở lệnh, không phải xe khựng thật.

Vector được chấp nhận trả ticket tiếp theo, một lần, buộc đúng lease/environment/
generation và hạn300 ms như cũ. Khi giữ liên tục chỉ cần một request mỗi lần;
lúc bắt đầu/đang rảnh vẫn renew. Không cache ticket qua thời gian rảnh. Không
nới watchdog250/700 ms, timeout ACK/PWM400 ms hay lease800 ms.

STOP chặn luồng gửi mới cho đến khi request STOP hoàn tất. Phản hồi/lỗi từ
chu kỳ input hoặc quyền đã bỏ không được phục hồi input, lấy ticket cũ hoặc
thu hồi quyền mới. Pointerup rồi lostpointercapture chỉ phát một STOP;
pointercancel vẫn dừng. Giữ touch-action:none, thêm chặn callout/selection
trên nút và con của nút; chưa xác minh Safari/iOS thật.

STOP tự động khi thả/rời trang có scope=owner, bị bỏ nếu lease đã cũ. Nút
DỪNG/Space/Z có scope=all, mọi người xem đã đăng nhập vẫn dừng được và
thu hồi chủ khác. Gateway kiểm tra lại lease dưới lock tại renew/release/vector;
ủy quyền và phát STOP cùng lock với claim/vector. Wrapper fetch giữ lease
đã ghi rõ trong request, không thay nó bằng lease của lần nhận quyền mới.

Mạng chậm, tab bị treo hoặc gói thực sự mất vẫn có thể làm dừng. Không cam kết
mọi điện thoại/WiFi đều mượt; không tự tiếp tục giữ lệnh sau khi bị hủy/quá hạn.

## Né: thay đổi và giới hạn

- Điểm bắt đầu xử lý55 cm thay60, chỉ ở IDLE_LINE, dữ liệu trước hợp lệ.
- Rộng cả bánh47 cm → halfWidth23,5; nhô trước17, sau17 cm; dài34 gồm thanh line.
  Biên12 cm giữ nguyên. Kiểm tra hành lang hiện đòi mẫu bên >59 cm;
  mẫu chéo >sqrt(35,5²+29²), khoảng45,84 cm. Không còn giả định rộng30 cm.
- Quét khi dừng → ra chéo → vượt → trở về → A2 ổn định80 ms → bàn giao line
  như trước. Đầu RETURN nội suy yêu cầu từ [255,0] đến [200,−side×100]
  trong400 ms, vẫn qua ramp bánh8/chu kỳ mục tiêu10 ms. Không STOP giữa
  các pha di chuyển đủ điều kiện. Đây là thông số thử, chưa hiệu chỉnh trên xe.
- Giữ yêu cầu cả trước/sau/hai bên có echo hợp lệ, tuổi <350 ms. Trước bảo vệ
  tiến, phía ngoài bảo vệ dạt ra, phía gần vật bảo vệ vượt/chéo về; sau tiếp tục
  là guard bảo thủ cho đuôi/vùng thân quét. Không bỏ guard sau để tránh khựng.
  Thiếu echo báo SONAR_FRONT_UNKNOWN / SONAR_REAR_UNKNOWN /
  SONAR_SIDE_UNKNOWN rồi PWM0, không coi 999 là trống.
- Vị trí đầu sonar so với tâm/mép thân chưa được đo; bốn tia và quét chéo không
  chứng minh toàn bộ hình chữ nhật thân quét qua đều trống. Ba mẫu cạnh và
  thời gian vượt700 ms giữ nguyên, chưa chứng minh đuôi đã qua vật ở mọi PWM.
  Cần kiểm tra góc mù, vật hẹp/thấp và gốc đo từng sensor trước khi bật né.
- Mặc định cap80, né TẮT. PWM200/255 chỉ được kiểm thử số học/build, chưa
  kiểm chứng né trên xe. Không tăng mặc định hoặc tự bật né.

Mô hình vẽ dùng bao ngoài34×47 cm; chi tiết bánh chỉ minh họa. Vệt/tọa độ/
vận tốc vẫn ước lượng từ lệnh/PWM, không phải đo thực.

## Tệp, kiểm tra và quay lại

Gói mới gồm toàn bộ upgrade_v1; dùng hai file Mega cùng nhau và cùng bộ bốn
file Jetson: agv_vector_gateway.py, vector_controls.js,
stream_server_vector_v1.py, run_vector_v1.py. Launcher không đổi nhưng đi kèm
để tránh thiếu bộ. TOUCH_VECTOR_V2.patch là diff từ commit nguồn, chỉ để
xem, không tự chạy. firmware.patch/jetson.patch cũ là lịch sử.
Xem TEST_REPORT_TOUCH_V2.md và SHA256SUMS.txt trước khi triển khai.

Phiên này không SSH Jetson, không mở USB thật, không chạy launcher/service
điều khiển, không nạp board hay điều khiển motor. Chỉ chạy test loopback với
USB/camera giả và biên dịch không upload. Chưa triển khai gói mới.

Trước triển khai riêng: người vận hành DỪNG, chuẩn bị nguồn motor an toàn,
ghi hash/copy bộ đang chạy vào thư mục backup mới có ngày giờ, giữ đúng .ino/.h
đang nạp và bản HEX nếu đã có. Đường dẫn dự kiến ~/agv_vector_v1,
SSH nguyennhutoan_uav@nhutoan-uav.local, IP được báo gần nhất192.168.1.139
có thể đổi; USB /dev/ttyUSB0 phải kiểm tra lại, chỉ một tiến trình sở hữu.
Không chép đè hoặc tự dừng service theo các dòng này trong phiên sửa mã.

Khi được phép triển khai: Verify Arduino Mega2560 trước, thử DỪNG/cap80/né
TẮT trên giá; đối chiếu từng bánh và diagnostic. Thử thả/pointercancel,
chuyển quyền hai thiết bị, mất mạng và watchdog trước khi thử sàn. Chỉ thử
né khi sensor/góc mù và khoảng trống được kiểm tra. Line/cua120/160 phải được
thử hồi quy lại vì telemetry/timing firmware đã thay dù thuật toán giữ nguyên.

Rollback về **đúng cặp SETPOINT_ACK_V1 tại commit nguồn** hoặc bản đang chạy
đã backup/hash; không dùng firmware ký tự gốc để ghép Python VECTOR1.
Người vận hành dừng an toàn, dừng duy nhất tiến trình mới, phục hồi cả bộ
Jetson và .ino/.h tương ứng nếu đã nạp Mega, biên dịch/nạp theo quy trình nguồn
đã xác minh, tải lại trang để bỏ JS mới và nhận quyền bằng thao tác mới.
Rollback từ Git không chứng minh trùng bản Jetson nếu chưa có hash ban đầu.
