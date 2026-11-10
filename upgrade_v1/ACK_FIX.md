# ACKFIX — ghi nhận ACK nhanh và giữ lý do đóng liên kết

## Bằng chứng

Người dùng xác nhận 4 bánh quay ở trần80, thả thì dừng, nhấn lại bánh quay nhưng mô hình xám/đứng. Đây là bằng chứng thử lái tay trên giá do người dùng báo; chưa chứng minh chạy sàn/né/cua/nguồn đạt.

Ảnh có Mất USB/Ước lượng cũ. Khi phiên vẽ lost=True, mô hình giữ vị trí cũ, không tích phân qua khoảng không biết chuyển động. Không tự phục hồi tọa độ như chưa có gián đoạn.

Đã tái hiện một race trong gateway: port.write() có thể nhường thực thi cho thread nhận; nếu ACK được đọc trước lúc pending[seq] được gán thì ACK bị bỏ, sau400 ms phần mềm tự đóng liên kết. Test port trả ACK ngay bên trong write cho thấy bản trước còn pending và không ghi nhận ACK. Đây là lỗi có thật trong mã, CHƯA chứng minh là nguyên nhân duy nhất trên Jetson người dùng; còn có thể có lỗi USB/nguồn/thiếu phản hồi thực.

## Sửa đổi

Chỉ agv_vector_gateway.py runtime đổi: đăng ký pending trước khi write, ACK xử lý dưới cùng serial_lock RLock, xóa pending nếu write lỗi. Không nới hạn ACK400 ms, PWM400 ms, command300 ms, không bỏ watchdog hoặc thay firmware. Ghi lịch sử tối đa8 sự kiện, giữ lý do ACK_TIMEOUT/MOTION_TIMEOUT/WRITE_ERROR/SERIAL_EXCEPTION thay vì ghi đè bằng thông báo chung sau đóng cổng. Giữ last_drive_ack và last_nonzero_pwm sau STOP để kiểm tra dễ hơn.

GET /control/diagnostics là chỉ đọc, yêu cầu đăng nhập nhưng không đòi quyền lái/CSRF và không ghi USB. Không xuất mật khẩu, session ID, lease hoặc ticket. Có ready, tuổi PWM, PWM hiện tại, ACK D gần nhất, PWM khác0 gần nhất và lịch sử lỗi theo đồng hồ monotonic của server (không phải giờ đồng hồ).

## Cập nhật cho hệ thống đã cài JOYFIX

1. DỪNG, xác nhận bánh thật đứng yên, tắt nguồn motor. Ctrl+C trong terminal JETSON.
2. Tải AGV_VECTOR1_ACKFIX_2026-11-10.zip, Extract all vào Downloads.
3. Terminal JETSON:

```bash
cd "$HOME/agv_vector_v1"
cp -n agv_vector_gateway.py agv_vector_gateway.before_ackfix.py
```

4. Terminal PC (đầu dòng PS):

```powershell
scp "$env:USERPROFILE\Downloads\AGV_VECTOR1_ACKFIX_2026-11-10\upgrade_v1\agv_vector_gateway.py" nguyennhutoan_uav@192.168.1.71:/home/nguyennhutoan_uav/agv_vector_v1/agv_vector_gateway.py
```

5. Terminal JETSON: `python3 run_vector_v1.py`, nhập thông tin như trước. Laptop Ctrl+F5, điện thoại mở lại trang. Không nạp Mega.
6. Trên Web, kiểm tra LÁI TAY, cap80, né TẮT. Đặt lại điểm đầu/phiên vẽ khi xe đã dừng và operator xác nhận mốc hiện tại. Nếu có mất liên kết thật sau đó, mô hình vẫn giữ vị trí cũ có chủ đích; không tự tiếp tục vệt cũ.
7. Chỉ lặp thử ngắn với bánh treo theo điều kiện nguồn đã chuẩn bị; không tăng cap/AUTO. Nếu tiếp tục xám, DỪNG rồi mở `http://192.168.1.71:5000/control/diagnostics` và gửi nội dung. Không cần chạy script Console hay lặp nhiều lần cấp nguồn. Mở tab khác có thể tự nhả quyền, đó là hành vi riêng của Web.

Không đổi dây/cấp nguồn đang mang điện; phần USB/cấp hai nguồn5V chưa được xác minh đầy đủ, bản này không giải quyết mạch điện. Không gọi dữ liệu PWM là encoder hoặc vận tốc thực.

Nếu chưa có JOYFIX phải dùng cả gateway và vector_controls.js trong gói này; riêng người dùng vừa hoàn thành JOYFIX chỉ cần gateway.

## Kiểm chứng

22 test Flask gateway qua, gồm ACK tức thì, write lỗi, giữ nguyên timeout và giữ nguyên nhân timeout, diagnostic chỉ đọc không lộ trường bí mật; 18 test trước vẫn qua. Cú pháp Python3.6 qua; test runtime Python3.12 với fake serial. Không nạp board hoặc điều khiển hardware từ môi trường này.

## Quay lại

Ctrl+C, trong terminal Jetson:

```bash
cd "$HOME/agv_vector_v1"
cp agv_vector_gateway.before_ackfix.py agv_vector_gateway.py
```

Khởi động lại launcher, tải lại Web. Giữ các bản trước, không xóa.
