# Chẩn đoán quét né — SCAN_DIAG_V1, 11/11/2026

Nguồn đang dùng: TOUCH_VECTOR_V2, dc1092c62572b3ec2ac7c13fde3014ec392b23e0.
Nhánh mới debug/avoid-scan-diag-2026-11-11, chỉ thêm bằng chứng chẩn đoán.
Không đổi VectorMotion.h, ngưỡng55 cm, bao thân47×34, pin, dấu motor,
thuật toán line/cua/né, cap mặc định80, né mặc định tắt, watchdog hoặc STOP.

## Bằng chứng trên xe và phần chưa biết

Người dùng báo đã thử tiến/thả dừng, dạt trái/phải đúng, cảm biến, mô hình
vẽ và vào cua. Đây là các báo cáo thử thực tế, không phải test host; chưa có
đủ nhật ký PWM/thời gian/video để chứng nhận mọi điều kiện hoạt động.
Diagnostic từng cho thấy TOUCH_VECTOR_V2, ready=true, PWM0 khi đứng yên.

Lượt né được báo dừng, UI ghi NO_CONFIRMED_CORRIDOR. Ảnh sau dừng:
trước54, sau56, trái71, phải62 cm; cap200, né bật. Người dùng xác nhận
đầu sonar quay trái → phải → giữa. Chuyển động servo chưa chứng minh
đúng góc thực hoặc echo chéo hợp lệ. Chưa biết bốn số lúc chọn hành lang.

choose() đòi ít nhất một bên cùng lúc có side >59 và <400 cm, diag
>sqrt(35.5²+29²) (khoảng45.84) và <400 cm. Không echo999 bị loại.
Sonar bên hữu hạn sau dừng không chứng minh hai mẫu chéo đã hợp lệ lúc quét.
Firmware cũ chỉ lấy một mẫu mỗi góc và không gửi hai mẫu lên gateway;
chưa đủ bằng chứng để sửa ngưỡng, tăng số mẫu hoặc thay thuật toán.

## Nội dung bổ sung

Sau mỗi lần quét hoàn tất và choose() chạy, Mega gửi đúng một dòng:

`AVOID_SCAN:board_ms,left,right,diag_left,diag_right,phase,chosen_side`

Không ping thêm. Snapshot lấy chính các giá trị đưa vào choose(), trước khi
FAULT bị chuyển về OFF/STOP. side=-1 trái, +1 phải, 0 không chọn; phase4
là OUT, phase9 là FAULT. 999 là không echo/không hợp lệ, không phải999 cm trống.
Dòng bổ sung tạo thêm một ít lưu lượng UART tại lúc quét; chưa đo timing
thực trên Mega sau thay đổi này.

Gateway lưu snapshot mới nhất trong /control/diagnostics:

- gateway_revision: TOUCH_VECTOR_V2_SCAN_DIAG_V1.
- avoid_scan: bốn số đo dùng lúc chọn, board_ms, phase, side, thời điểm nhận.
- vector_status: phase/cap/armed gần nhất từ Mega, phân biệt chọn ô trên UI
  với cap đã được firmware báo lại.
- avoid_fault: lý do mới nhất; xóa lỗi né cũ khi nhận snapshot chọn OUT mới
  thành công. Snapshot vẫn tồn tại sau STOP để đọc khi xe đứng yên.

Không có lease/ticket/mật khẩu trong snapshot. Nếu chưa quét sau khi gateway
khởi động, avoid_scan=null là bình thường. Mega cũ không phát dòng này;
gateway mới đơn lẻ không tạo ra số đo chưa được nhận.

## Gói và triển khai theo chặng

Gói AGV_VECTOR1_SCAN_DIAG_2026-11-11.zip chỉ gồm:
agv_vector_gateway.py; mega_vector_v1/mega_vector_v1.ino; VectorMotion.h
nguyên trạng của TOUCH_VECTOR_V2; tài liệu này và SCAN_DIAG_SHA256SUMS.txt.
vector_controls.js, stream_server_vector_v1.py, run_vector_v1.py giữ bản
TOUCH_VECTOR_V2 đã triển khai. Không chạy patch cũ hoặc nâng cấp dependencies.

Trong chat: đưa một chặng mỗi lần rồi đợi kết quả/ảnh. Thứ tự: giữ DỪNG,
backup bộ đang chạy và nguồn Mega hiện có; tải/kiểm hash gói mới; thay gateway
khi server đã dừng; Verify/nạp cặp sketch trong điều kiện nguồn/USB đã chuẩn bị;
nối Jetson lại, xác nhận cổng USB và IP, chạy launcher. Xem hướng dẫn thao tác
Windows/Jetson trong docs/TRIEN_KHAI_TOUCH_VECTOR_V2.md. Mật khẩu nhập cục bộ.

Sau cập nhật, xác nhận revision trên diagnostic, dùng cap80/né tắt thử STOP
trước. Chỉ khi bố trí chỗ thử thoáng, nhận lại quyền, xác nhận cap80 thật trên
vector_status, bật né chủ động và cho một lượt kiểm tra có người vận hành.
Nếu dừng, không lặp AUTO: DỪNG, đọc avoid_scan/avoid_fault khi đã đứng yên.
Chưa dùng PWM200/255 để thử né. Không coi mất echo là trống, không tạo echo giả
hoặc hạ ngưỡng chỉ để test qua. Dữ liệu quyết định bước điều tra kế tiếp.

Rollback: dừng đúng server và chuẩn bị nguồn an toàn; phục hồi gateway và
nguồn .ino/.h TOUCH_VECTOR_V2 đã backup, Verify/nạp theo quy trình người vận
hành. Nguồn backup không phải binary đọc ngược từ Mega. Không tự điều khiển
xe/nạp board/SSH từ cloud; lượt sửa này chỉ kiểm thử cục bộ không phần cứng.

## Kiểm chứng bản chẩn đoán

44 test Python qua (gateway và bảo toàn nguồn), gồm snapshot tồn tại sau lỗi,
không ghi USB từ diagnostics, bỏ frame sai dạng và loại lỗi cũ sau chọn thành
công. C++ toàn sketch/stub qua: phát đúng snapshot khi chọn được và khi hai
mẫu chéo999; nhánh lỗi vẫn STOP/PWM0. Các giá trị999 trong test là dữ liệu giả,
không phải số đo hai hướng chéo trên xe người dùng. Build AVR thực được thực
hiện không upload; flash27.012 byte, RAM tĩnh2.502 byte (GCC AVR5.4.0, core1.8.3). Chưa thử xe.

## Tải đúng bản chẩn đoán

- [AGV_VECTOR1_SCAN_DIAG_2026-11-11.zip](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/debug/avoid-scan-diag-2026-11-11/AGV_VECTOR1_SCAN_DIAG_2026-11-11.zip)
- [upgrade_v1/agv_vector_gateway.py](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/debug/avoid-scan-diag-2026-11-11/upgrade_v1/agv_vector_gateway.py)
- [upgrade_v1/mega_vector_v1/mega_vector_v1.ino](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/debug/avoid-scan-diag-2026-11-11/upgrade_v1/mega_vector_v1/mega_vector_v1.ino)
- [upgrade_v1/mega_vector_v1/VectorMotion.h](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/debug/avoid-scan-diag-2026-11-11/upgrade_v1/mega_vector_v1/VectorMotion.h)
- [upgrade_v1/SCAN_DIAG_SHA256SUMS.txt](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/refs/heads/debug/avoid-scan-diag-2026-11-11/upgrade_v1/SCAN_DIAG_SHA256SUMS.txt)
