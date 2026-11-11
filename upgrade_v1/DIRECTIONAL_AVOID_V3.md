# AVOID_DIRECTIONAL_V3 — chọn hướng theo dữ liệu từng phía

Ngày11/11/2026. Nguồn fda7c2ec7d767165c17ef4d9e153be67884a2b00
(AVOID_SCAN_RETRY_V1). Nhánh riêng fix/directional-avoid-v3-2026-11-11.
Giữ nguyên main, SCAN_DIAG, SCAN_RETRY và các gói đã xuất bản.

## Dữ liệu và yêu cầu mới

JSON người dùng gửi sau lượt xe dừng:

```json
{"avoid_fault":"NO_CONFIRMED_CORRIDOR","avoid_samples":{"board_ms":351386,"left_total":3,"left_valid":3,"right_total":3,"right_valid":3,"stationary_timeout_us":24000},"avoid_scan":{"board_ms":351386,"chosen_side":0,"diag_left_cm":152,"diag_right_cm":118,"left_cm":999,"phase_after_choice":9,"right_cm":45},"vector_status":{"armed":true,"cap":160,"phase":0}}
```

Đây là dữ liệu thực người dùng cung cấp. Hai tia chéo đã có3/3 mẫu hợp lệ,
nhưng sonar trái999 và phải45 làm cả hai ứng viên bị loại trong mã cũ.
Mã trước mới mở rộng phép đo chéo24 ms, còn sonar cố định vẫn8 ms: phần sửa
đó chưa đồng nhất. 8 ms chỉ đợi được khoảng136 cm; quan sát999 không chứng
minh nguyên nhân duy nhất là timeout, nhưng sự không thống nhất này có thật.

Người dùng xác nhận phía trái thực tế trống, thử đưa tay lại gần thấy số đo,
đưa xa thì mất echo; yêu cầu không loại hướng chỉ do sonar bên mất echo khi
chéo đã xác nhận đủ xa. Người dùng cũng yêu cầu hỗ trợ thử200/255, không
khóa nhánh này ở80. **Đây là thay đổi chính sách thử nghiệm có chủ đích**, khác
với yêu cầu cũ bắt buộc mọi sonar có echo. Vẫn không gọi999 là một số đo xa
hoặc bằng chứng an toàn độc lập; thiếu echo có thể do nhiều nguyên nhân.

Các báo cáo line/cua, dạt trái/phải, tiến/thả, sensor hoạt động thuộc bản trước.
Chưa có kết quả xe thật của V3. Không ghi PASS hardware từ test phần mềm.

## Quy tắc chọn hướng

Giữ bao thân47×34 cm, halfWidth23,5; nhô trước/sau17; margin12; điểm vào55.
Giữ góc servo lệnh135/45/90 và tỷ lệ tiến/ngang255/130 (~27° danh nghĩa),
không coi45° quét là góc xe chạy hoặc góc đã đo/hiệu chuẩn trên xe.

- Mode1: ưu tiên phía có sonar bên hợp lệ >59 cm và chéo >45,84 cm như cũ.
- Mode2: nếu không có ứng viên Mode1, cho xét **một** phía có bên999 khi
  chéo đã xác nhận >sqrt(2)×59 ≈83,44 cm và <400; sonar bên đối diện phải
  có số đo hợp lệ >35,5 cm và <400. Phép chiếu danh nghĩa tia45° cần >59 cm
  trên cả hai trục. Nếu cả hai bên999, không chọn theo nhánh này.
- Số đo bên hợp lệ nhưng gần (ví dụ20 hoặc45 cm) không được đổi thành999 để
  lách ngưỡng. 0..3 cm cũng không phải phía thoáng. Các số chéo0..3 xuất hiện
  trong bộ mẫu sẽ chặn ứng viên, không bị bỏ để lấy hai mẫu xa hơn.
- Phía được chọn có chéo >83,44 ghi unknown_selected_side_allowed=true. Trong cùng lượt né,
  sonar **phía được chọn** có thể tiếp tục999 nếu timeout đó còn mới<350 ms.
  Điều này cũng áp dụng khi lúc chọn bên có số đo, rồi mất echo trong lúc đi.
  Mẫu mới đo được vật gần vẫn dừng. Dữ liệu cũ không được gia hạn giả.
- Sonar trước, sau và bên đối diện vẫn phải có số đo hợp lệ/mới; các guard
  khoảng hở, timeout pha và STOP/watchdog vẫn giữ. Không coi mất echo bên đối
  diện là bằng chứng đã vượt cạnh vật; vẫn cần ba mẫu cạnh hợp lệ như trước.

Với bộ dữ liệu999/45/152/118 nêu trên: ứng viên trái Mode2 được chọn, side=-1.
Nếu dữ liệu trước/sau/bên đối diện không hợp lệ khi bắt đầu di chuyển thì
guard tương ứng vẫn dừng. Không hứa chọn hướng đồng nghĩa sẽ hoàn thành né.

Đây là heuristic với các tia đo rời rạc, **không chứng minh toàn bộ vùng quét
của thân xe trống**. Nó dựa thêm vào việc người vận hành đã kiểm tra vùng thử
và chủ động bật né thực nghiệm. Không có bản đồ vật cản, encoder hay chứng
nhận chống va chạm cho góc mù, kính/vật phản xạ xiên hoặc vật thấp.

## Phạm vi đo và lịch đọc

Mọi tia VECTOR1 (trước/sau/trái/phải, đứng yên, line và đang né) dùng24 ms;
giá trị999 vẫn được lưu nguyên. Giữ quorum2/3 mẫu chéo, lấy số gần nhất.
Các hàm legacy readUltrasonicCM/updateSonar giữ nguyên byte, dùng trước khi
USB sở hữu. Trong USB-owned loop dùng đường đọc VECTOR1 mới.

SCAN_CENTER đọc bốn tia cố định theo từng vòng, không chờ bốn pulseIn liền
nhau. Trong vòng lặp thông thường mỗi lần chỉ đo một tia. Sau mỗi echo wait
đợi tối thiểu40 ms trước tia tiếp theo, nên riêng thời gian ping/gap một vòng
bốn tia tối đa khoảng256 ms nếu không có công việc trễ khác; không phải
bảo đảm thời gian thực. Một pulseIn vẫn có thể chờ24 ms, STOP được đọc giữa
các lần chờ, chưa đo độ trễ thực trên board. Guard350 ms sẽ dừng nếu dữ liệu
quá cũ; không thay ngưỡng để che việc xử lý chậm.

Lịch đọc đã thay đổi so với vòng legacy ưu tiên tia trước. Vì vậy dù thân
line/cua giữ nguyên, cần thử hồi quy ngắn line/cua trên xe trước mở rộng tốc độ.

## PWM và điều giữ nguyên

Mode1/2 đều sử dụng cap người vận hành chọn:80/120/160/200/255 qua Web,
không còn điều kiện khóa Mode2 ở80. Profile vẫn phải áp dụng khi dừng và có
ACK; mặc định sau khởi động là80, né tắt. Không tự nâng cap vì số đo999.
Cap là trần lệnh điện, không phải vận tốc đo được hay tốc độ né đã chứng nhận.

Không đổi pin, dấu motor, thứ tự bánh/mắt line, baudrate, servo, thông số cua.
Giữ các pha OUT/PASS/RETURN/CENTER/HANDOFF, nội suy RETURN400 ms, điều kiện A2
ổn định80 ms và bàn giao line. Không thêm STOP giữa các pha đã đủ điều kiện.
Giữ watchdog manual250/host700 ms, ACK/PWM400 ms, lease800 ms; STOP tức thời
ở cấp lệnh PWM, không có tuyên bố phanh cơ tức thời.

## Chẩn đoán và nhận diện đúng cặp

Mega phát VECTOR_BUILD:AVOID_DIRECTIONAL_V3 khi được probe '?', sau dòng
AGV:VECTOR1. Không thay giao thức, không thêm lệnh điều khiển. Gateway xóa
marker cũ khi bắt đầu kết nối mới để không nhận nhầm firmware trước.
Trong /control/diagnostics, kiểm tra trước lượt thử:

- gateway_revision và firmware_revision đều AVOID_DIRECTIONAL_V3, ready=true.
- avoid_scan: bốn số đo, phía và pha lựa chọn như trước.
- avoid_samples: có thêm fixed_range_timeout_us=24000; board_ms phải khớp
  avoid_scan để đọc cùng lượt. Còn null trước khi quét lần đầu là bình thường.
- avoid_policy: selection_mode0/1/2, profile_cap, unknown_selected_side_allowed và candidate_mask.
  Mask1/2 là ứng viên có đo bên trái/phải; mask4/8 là ứng viên theo chéo trái/phải.
  Metadata này nói về quyết định lúc quét, không phải chứng nhận an toàn hiện tại.
- vector_status.cap là cap đã áp dụng; ô dropdown có thể chưa được áp dụng.

Nếu gateway marker đúng mà firmware_revision thiếu/khác: kiểm tra đúng sketch
và cặp file đã nạp; không coi chỉ restart Python là cập nhật firmware.

## Kiểm chứng

47 test Python gateway/bảo toàn nguồn qua; grammar Python3.6 qua, runtime
Python3.12. Tám bộ C++ g++17 -Wall -Wextra -Werror qua: motion, envelope,
scan_samples, directional_avoid, firmware, scan_firmware, vector_range, wheels.

Mô hình đã tái hiện đúng bộ999/45/152/118 và chọn trái Mode2; kiểm đối xứng
và cả5 cap80/120/160/200/255. Kiểm PWM đúng dấu/giới hạn, cả50 tổ hợp hướng/cap
cũ, finite-close/chéo yếu/cả hai bên999/dữ liệu cũ từ chối, numeric0..3 chặn,
STOP khung VECTOR1 trong nhánh mới và STOP khi đang lấy mẫu. Full-loop stub
xác nhận tối đa một echo wait mỗi vòng trong các ca đã chạy, cả4 tia24 ms,
tuổi mẫu khi chọn, probe marker mới. Không thay assertion cũ để ép PASS;
test scan-center được cập nhật để chạy đủ bốn vòng đọc thay vì một lần gọi.

Các hàm motor/drive,13 hàm bảo vệ, toàn bộ thân line/cua (trừ điểm vào55 đã
được duyệt trước), prefix hằng số và hai hàm đọc legacy giữ nguyên theo
hash/đối chiếu byte. Build/link AVR thực ATmega2560 qua, flash28.332 B,
RAM tĩnh2.595 B, GCC AVR5.4/core1.8.3. Không upload từ cloud, chưa thử xe,
chưa đo stack/timing thực. Các cap200/255 mới được kiểm số học/logic/build.

## Gói, triển khai và quay lại

Gói AGV_VECTOR1_DIRECTIONAL_V3_2026-11-11.zip gồm gateway và cả thư mục sketch
ba file: mega_vector_v1.ino, VectorMotion.h, ScanSamples.h; tài liệu, diff
DIRECTIONAL_AVOID_V3.patch và DIRECTIONAL_V3_SHA256SUMS.txt. Lấy cả3 file
Mega từ gói này, không dùng header SCAN_RETRY cũ. Ba file Jetson còn lại
vector_controls.js, stream_server_vector_v1.py, run_vector_v1.py giữ bộ
TOUCH_VECTOR_V2 hiện dùng. Không chạy script patch cũ hoặc nâng cấp dependency.

Triển khai trong chat theo từng chặng: DỪNG/nhả, backup gateway đang chạy và
giữ nguồn sketch SCAN_RETRY cũ, tải/kiểm ZIP, Verify đúng sketch3 file; Ctrl+C
đúng server, copy gateway qua staging/kiểm hash. Shutdown Jetson, đợi kết nối
đóng+30 s rồi tắt tổng, chuyển USB/nạp theo cấu hình đã thống nhất với người
vận hành. Nối lại Jetson, boot, xác nhận IP/USB, chạy launcher và hai marker.
Không tự SSH, nạp board hoặc điều khiển xe từ cloud.

Đầu tiên cap80: STOP/thả trên giá, rồi line/cua ngắn, sau đó một lượt né ở
khu vực đã kiểm tra khoảng hở. Chỉ sau kết quả thực tế mới thử120→160→200→255,
mỗi lượt dừng và đọc JSON/video; không mặc định bỏ qua mức thấp. Vẫn có thể
dừng vì guard khác; ghi đúng avoid_fault, không ép chạy lặp hoặc reset lỗi để
che mất dữ liệu. Vệt/tọa độ là ước lượng lệnh/PWM, không dùng làm tránh va chạm.

Rollback về nguyên gateway và thư mục sketch3 file SCAN_RETRY đã giữ/backup,
Verify/nạp theo quy trình nguồn/USB; khởi động lại gateway để bỏ marker cũ.
Backup source không phải firmware đọc ngược Mega; không ghép VECTOR1 với
SAFE1 hoặc firmware ký tự gốc. Xem docs/TRIEN_KHAI_TOUCH_VECTOR_V2.md cho
thao tác PC/JETSON và nguồn đã thống nhất.

## Liên kết bản V3

- [AGV_VECTOR1_DIRECTIONAL_V3_2026-11-11.zip](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/directional-avoid-v3-2026-11-11/AGV_VECTOR1_DIRECTIONAL_V3_2026-11-11.zip)
- [upgrade_v1/agv_vector_gateway.py](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/directional-avoid-v3-2026-11-11/upgrade_v1/agv_vector_gateway.py)
- [upgrade_v1/mega_vector_v1/mega_vector_v1.ino](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/directional-avoid-v3-2026-11-11/upgrade_v1/mega_vector_v1/mega_vector_v1.ino)
- [upgrade_v1/mega_vector_v1/VectorMotion.h](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/directional-avoid-v3-2026-11-11/upgrade_v1/mega_vector_v1/VectorMotion.h)
- [upgrade_v1/mega_vector_v1/ScanSamples.h](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/directional-avoid-v3-2026-11-11/upgrade_v1/mega_vector_v1/ScanSamples.h)
- [upgrade_v1/DIRECTIONAL_V3_SHA256SUMS.txt](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/directional-avoid-v3-2026-11-11/upgrade_v1/DIRECTIONAL_V3_SHA256SUMS.txt)
- [upgrade_v1/DIRECTIONAL_AVOID_V3.patch](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/fix/directional-avoid-v3-2026-11-11/upgrade_v1/DIRECTIONAL_AVOID_V3.patch)
