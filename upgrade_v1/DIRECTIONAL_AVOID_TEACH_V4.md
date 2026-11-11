# V4 — né một phía, ghi đường lái tay và quay về thử nghiệm

Bản nền: V3, commit `195a15d65fa2c8f09ecce0dfd75e4dfa709afd82`.
Nhánh riêng: `feat/directional-avoid-teach-return-v4-2026-11-11`.
Chưa nạp/thử V4 trên xe thật từ môi trường Codex.

## Bằng chứng và phần sửa né

Người dùng xác nhận có **4 đầu siêu âm**: F trên servo, B/L/R cố định.
Khoảng 24 cm là từ đầu F giữa thanh trước tới bánh theo chiều ngang; không phải khoảng lùi đầu đo.
F ở mép trước, nhô tối đa khoảng 2 cm. Thân gồm bánh 47 × 34 cm.
Người dùng báo sau scan xe chỉ tiến thẳng rồi dừng. Snapshot V3 chọn trái
(`chosen_side=-1`, diag trái173, bên trái90), sau đó `CLEARANCE`; ảnh sau dừng bên phải25.
Ảnh sau dừng không phải số đo tại thời điểm lỗi.

Hai vấn đề trong mã cũ:

- OUT có thể chuyển PASS ngay vì sonar trước thấy nền xa, trước khi bánh tạo dạt đáng kể.
- Guard lấy `halfWidth+margin=35,5 cm` cho số đo từ đầu bên ở mép xe; như vậy một bên đối diện25 cm cũng làm dừng dù xe đang dạt ra xa bên đó.

V4 chọn từng hướng độc lập. Trái đủ điều kiện thì không cần phải có một hành lang bên phải đủ rộng cho cả xe đi qua. Mode1 giữ yêu cầu bên được chọn >59 cm và quét chéo hữu hạn đủ xa. Mode2 cho bên được chọn999 khi chéo cùng bên có ít nhất2/3 mẫu hợp lệ và khoảng cách >83,44 cm; bên đối diện chỉ cần không có số đo sát dưới guard mép. Hai bên999 chỉ được chọn nếu có chéo hữu hạn xác nhận. Đường chéo999 không tự được coi là đã xác nhận.

`999` là **không nhận echo**, không phải phép đo không gian trống. Theo yêu cầu thử nghiệm của người vận hành, V4 chấp nhận fresh999 ở bên được chọn khi có bằng chứng chéo; không biến999 thành một khoảng cách giả. Số đo0–3 hoặc quá cũ vẫn dừng. Một tường nghiêng, mặt hấp thụ, dây hỏng cũng có thể không echo; chính sách thử này không bảo đảm cả vùng quét của thân xe trống.

Guard khoảng hở từ đầu đo: `margin12 + inset`. `leftInset/rightInset/frontInset` mặc định0 cm theo mô tả sát mép; nếu mặt đầu bên lùi vào trong mép ngoài bánh, nhập đúng số cm lùi trong `VectorMotion.h`. Không tự giảm margin12. Khoảng lùi B không là điều kiện bắt buộc của quỹ đạo chỉ tiến/dạt; né này không phát lệnh lùi hay xoay thân.

OUT phát `f120,s±255`, qua mixer và ramp cũ. Chỉ sang PASS sau khi tích lũy **PWM đã phát** tương đương dạt tối thiểu35,5 cm và ba lần đọc trước mới thông thoáng. Đây là ước lượng dựa trên `strafeCmPerSecond=18` tại PWM255, không phải odometry. PASS cần ước lượng tiến ít nhất46 cm và ba mẫu cạnh mới sau khi từng đo vật gần ở phía trong. Không echo phía trong có thể tính như cạnh chỉ sau bằng chứng vật gần đó. Nếu không có bằng chứng cạnh, hết giới hạn pha thì dừng; không tự bịa là đã qua vật.

RETURN trộn lệnh trong400 ms, tiến120/dạt ngược255 ở cuối blend; không nhận IR giữa quá sớm trước khi đã ước lượng trả ít nhất60% độ dạt. Giới hạn tìm lại line:1,5 lần độ dạt ra +12 cm. Các pha giới hạn30 s để cap80 không bị cùng thời hạn quá ngắn với cap255. Các hệ số18/23,6 cm/s kế thừa giả thiết vẽ trước đó, **chưa hiệu chuẩn trên xe**. Tải, pin, trượt bánh làm sai ước lượng. V4 giữ pin, cực motor, baud, góc servo135/45/90, bám line và cua cũ.

`VECTOR_RANGE` gửi số đo thô và tuổi riêng F/B/L/R để lượt quay về kiểm tra cả tuổi từng tia, không dùng tuổi gói tổng thay cho tuổi số đo. `AVOID_GUARD` chụp pha trước lỗi, hướng đã chọn, F/B/L/R và tuổi từng số đo **trước khi xóa trạng thái lỗi**; motor được gửi STOP trước khi in snapshot. `/control/diagnostics` có `avoid_guard`, `avoid_fault`, `avoid_scan`, `avoid_policy`.

## Ghi đường và quay về

Bốn nút mới cạnh bản đồ:

1. **Đặt điểm đầu + ghi đường lái tay**: cần nhận quyền, Xe thật/LÁI TAY, phản hồi STOP và PWM0 mới. Đặt mô hình0,0,0 ở vị trí hiện tại, bắt đầu lưu lệnh.
2. Lái bằng phím/nút/joystick; thả là STOP như cũ. Vệt ghi màu đỏ, tích phân phản hồi PWM theo hệ số vẽ. Khoảng cách trên bản đồ là ước lượng.
3. **Chốt đường tại điểm dừng**: thả phím/DỪNG, nút chờ phản hồi STOP rồi chốt. Giữ nguyên xe ở điểm cuối và giữ nguyên cap.
4. **Quay180° và về theo đường đã ghi**: nhập thời gian quay180° đã đo tại PWM80, tích ô đã hiệu chuẩn và kiểm tra chỗ quay. Sau lượt quay, phát ngược thứ tự đoạn; giữ dấu tiến/dạt theo thân đã quay, đảo dấu tốc độ xoay của các đoạn quay đã ghi. Vệt quay về màu xanh lam. Mô hình dùng thời gian quay đã khai báo và chốt hướng ước lượng +180° khi kết thúc đoạn quay; đây là giả thiết theo hiệu chuẩn, không phải IMU đo góc.

Ví dụ F80/R70/L150/R80/F50 cm theo thân lúc đi: sau xoay180°, thứ tự đúng theo thân mới là F50/R80/L150/R70/F80. Đây là đảo đường từ cuối về đầu; không phải phát lại thứ tự ban đầu. Bản này lưu vector/thời gian, không suy ra những số cm ấy từ sonar. Các đoạn xoay được đảo dấu khi đảo thời gian.

Quay đầu dùng độ lớn PWM xấp xỉ80 dù cap đã ghi là80/120/160/200/255. **Không có thời gian quay180° mặc định**. Đo thời gian bằng thao tác xoay tay tại cap80, ở vùng đủ chỗ, căn hướng thực/đồng hồ; thả để dừng. Điền số đã đo trước khi ghi lượt thử. Ban đầu thử một đường ngắn ở cap80; chỉ tăng cap sau khi kiểm tra STOP và các hướng trên xe. Không tuyên bố thời gian này tạo góc180° chính xác khi chưa có IMU/encoder.

Giới hạn và hủy:

- Lưu trong RAM, tối đa10 phút/6000 đoạn; khởi động lại server mất đường. Không tự chạy lại sau mất kết nối, không lưu tác vụ chạy motor chờ khởi động.
- Dùng cùng cap, cùng quyền điều khiển và cùng phiên vẽ/môi trường. Đổi cap/chế độ/phiên hoặc mất quyền khi ghi làm lượt ghi không hợp lệ. Nhả quyền sau chốt rồi nhận lại cần ghi đường mới vì lease đã đổi.
- Lượt về cần cả4 số đo hữu hạn >30 cm lúc xoay đầu để gác thân xoay;999 trong lượt xoay là chưa xác nhận. Lúc tịnh tiến chỉ xét hướng đang đi, fresh999 có thể được chấp nhận theo chính sách thử; số đo thật quá gần hoặc dữ liệu cũ dừng. Đầu đo rời rạc không phủ toàn bộ thân.
- DỪNG/Space, nhả quyền, mất focus/rời trang, mất USB/MOTION/ACK, nhịp điều khiển gián đoạn>200 ms, đổi chế độ/cap/phiên đều hủy. Muốn lái tay trong lượt về: nhấn DỪNG trước. Sau hủy giữa chừng phải ghi đường mới; không tự tiếp tục từ chỗ dở.
- Các request chạy về có ticket một lần≤300 ms và thứ tự lệnh, nên request cũ đến sau STOP không khởi động lại xe. Phím lái không chen vào lịch quay về.
- Sai số PWM/thời gian, độ trễ, bánh trượt và quay đầu chưa đúng sẽ tích lũy; đây là quay về **ước lượng**, không bảo đảm về đúng từng cm/đúng tâm line. Sonar gác vật gần không định vị lại điểm đầu. Mô hình minh họa có thể sai ngay cả khi lệnh đã ACK.

## Sửa trực tiếp bằng VS Code, không tắt nguồn cho Python/JS

Cửa sổ trong ảnh có workspace `Program C` của PC và terminal SSH riêng. Terminal đã SSH không có nghĩa tab editor đang sửa file Jetson. Không sửa `stream_server.py` hoặc `stream_server_CHUAN_GOC.py` cũ để áp dụng V4.

1. Giữ xe DỪNG, nhả quyền. Ở terminal đang chạy server, Ctrl+C.
2. Trong VS Code PC: F1 → **Remote-SSH: Connect to Host…** → `nguyennhutoan_uav@192.168.1.139`. Chọn Linux, nhập mật khẩu tại VS Code khi hỏi, không gửi vào chat.
3. Cửa sổ mới phải hiện `SSH: 192.168.1.139` ở góc dưới trái. **File → Open Folder…** → `/home/nguyennhutoan_uav/agv_vector_v1`.
4. Trong Explorer, tạo bản sao dự phòng của các file hiện hữu trước lần sửa đầu, ví dụ `agv_vector_gateway_before_v4.py`. Giữ nguyên file cấu hình dữ liệu/bản đồ.
5. Mở bản Raw tương ứng từ `DOWNLOADS_V4.md`, copy toàn bộ nội dung. Trong file đúng ở cửa sổ SSH: Ctrl+A → paste → Ctrl+S. Cập nhật **4 file trong cùng thư mục runtime**:

   - `agv_vector_gateway.py`
   - `teach_return.py` — tạo New File tên này nếu chưa có
   - `stream_server_vector_v1.py`
   - `vector_controls.js`

6. Không để file Python thiếu module trong lúc chương trình đang chạy. Sau khi lưu đủ4 file, mở terminal trong cửa sổ SSH. Kiểm tra cú pháp, rồi khởi động launcher cũ:

   ```bash
   cd /home/nguyennhutoan_uav/agv_vector_v1
   python3 -m py_compile agv_vector_gateway.py teach_return.py stream_server_vector_v1.py
   python3 run_vector_v1.py
   ```

   Nhập tài khoản/mật khẩu web tại terminal, USB `/dev/ttyUSB0`. Giữ một tiến trình sở hữu USB. Không cần thay launcher nếu launcher cũ đang chạy đúng VECTOR1.
7. Trình duyệt Ctrl+F5. Diagnostics cần `gateway_revision` và `firmware_revision` đều `AVOID_DIRECTIONAL_V4`. Nếu firmware vẫnV3, chưa thử phần néV4/quay về.

Nếu Remote-SSH báo Jetson/VS Code Server không hỗ trợ thư viện hệ thống, dùng **SSH FS** đã cài: mở mục SSH FS ở thanh bên, **Add configuration**, đặt label `JETSON`, host `.139`, username `nguyennhutoan_uav`, root `/home/nguyennhutoan_uav/agv_vector_v1`; nhập mật khẩu qua prompt của extension hoặc dùng key có sẵn. Không lưu mật khẩu vào file settings để chia sẻ. Connect rồi mở file dưới cây SSH FS, Ctrl+S ghi lên Jetson; dùng terminal SSH hiện có để Ctrl+C/khởi động lại launcher. Tên lệnh có thể khác theo phiên bản extension. Nếu Save báo lỗi thì chưa áp dụng, không coi tab đóng là đã lưu thành công.

Những lần chỉnh Python/JS sau cũng chỉ cần DỪNG/nhả quyền → Ctrl+C → sửa/lưu file tại chỗ → launcher → Ctrl+F5. Không cần tạo ZIP hay tắt/mở nguồn mỗi lần.

## Riêng firmware Mega vẫn phải Upload

V4 sửa `mega_vector_v1.ino` và `VectorMotion.h`; giữ `ScanSamples.h` cùng thư mục sketch. Sửa `.ino` qua SSH chỉ sửa văn bản, không nạp Mega. Với kết nối USB hiện tại, dùng trình tự nguồn/USB đã chốt trong `docs/TRIEN_KHAI_TOUCH_VECTOR_V2.md`: shutdown Jetson đúng cách trước khi tắt công tắc tổng, đưa Mega sang PC rồi Upload từ Arduino IDE; sau Done uploading đưa USB về Jetson và bật nguồn lại. Không đổi pin hay cấp nguồn chồng để rút ngắn bước này.

Lần đầu triển khai V4 cần đủ firmware và4 file runtime. Sau đó sửa riêng Python/JS không cần nạp Mega. V3 vẫn nằm trên nhánh cũ để quay lại; phải khôi phục cả firmware và runtime tương ứng nếu quay lại.

## Xác minh phần mềm

Báo cáo chi tiết: `TEST_REPORT_V4.md`. Có test hướng trái/mirror, cap80/120/160/200/255, hẹp phía đối diện, noecho có/không có bằng chứng, PWM dạt chưa phát thì không sang PASS, guard sát mép, cạnh vật/thân xe, STOP/watchdog. Test Python/Flask và Chromium dùng USB/cảm biến giả. AVR build tạo ELF/HEX cho ATmega2560, không upload. Chưa có phép đo tốc độ, góc quay, quãng đường hay thử sàn V4.
