# AGV SAFE1 - sửa cặp Jetson/Mega

Đây là bản sửa dựa trên DOCX Python và ZIP .ino bạn vừa cung cấp. Đã kiểm tra tĩnh/mô phỏng; chưa cài lên Jetson hay chạy trên xe.

## Lỗi xác nhận từ code
- Server gửi CFG ngay khi mở cổng và khi lưu tuning, nhưng firmware nhận từng ký tự USB như lệnh lái. CFG không tương thích, có thể tạo lệnh ngoài ý muốn.
- serial_worker bị thụt dòng ở nhánh SONAR/DATA: `parts` có thể chưa được gán, hoặc tái sử dụng sai. Exception bị bỏ qua, cổng đóng/mở liên tục.
- HTML cố ý đảo tên chế độ; MODE hiển thị không phản ánh Mega. Vị trí/vận tốc 3D được tích phân từ lệnh giả lập, không phải encoder.
- Hai định nghĩa FSM trùng tên. Bản cuối ghi đè bản đầu; FSM cập nhật trạng thái ảo và không phải phản hồi motor thực.
- Chưa thể xác nhận đây là tất cả nguyên nhân bánh quay liên tục: chưa có log đầy đủ khi lỗi, và chưa kiểm tra chương trình ESP hiện tại. Giữ ESP tách khỏi RX2 khi thử.

## Thiết kế bản sửa
- Một quyền AUTO: Mega thực hiện dò line, góc90, né cản như .ino nhận được. Jetson giữ camera/nhận diện để quan sát, không tự phát lệnh tìm line.
- USB chỉ nhận khung @... kết thúc newline. Raw CFG/raw ký tự không được chạy motor. Serial2 ESP giữ giao thức cũ, nhưng chưa nối lại khi kiểm tra.
- HELLO dừng xe, bắt tay AGV:SAFE1; kết nối lại mặc định LÁI TAY/STOP, không tự AUTO.
- MODE:AUTO/MANUAL là đặt chế độ có ACK, không toggle M thiếu đồng bộ. STOP ngắt motor và thoát AUTO.
- Jetson gửi PING300ms; mất PING1500ms -> Mega dừng/thoát AUTO. Trong chu trình né cũng kiểm tra STOP/watchdog.
- PING không nuôi timeout lệnh motor manual. Nhả nút/mất request -> timeout cũ180ms xoay,700ms các hướng khác vẫn tác dụng.
- Server độc quyền cổng, ráp các dòng bị chia nhỏ, log lỗi rõ, chỉ báo kết nối sau handshake. Độc quyền không thay thế việc đóng các tiến trình đã mở cổng trước.
- AUTO trên web: Mega điều khiển bằng cảm biến gầm/siêu âm; camera chỉ quan sát, không tự tránh theo camera trong bản này.
- Tuning web trả lỗi501 có giải thích; không gửi CFG chưa hỗ trợ, không báo lưu/nạp thành công giả. Chỉnh hằng số trong .ino.
- Chưa có encoder: ô vị trí/góc/quãng đường/vận tốc hiện CHƯA CÓ ODOM/CHƯA ĐO thay số mô phỏng thành số đo.

## Triển khai từng bước
1. Giữ nguồn motor OFF. Dừng server: `sudo systemctl stop agv_server.service`.
   Kiểm tra `systemctl is-active agv_server.service` -> inactive.
   Giữ ESP TX tách khỏi Mega RX2/chân17. Đóng Serial Monitor trên máy tính khi chuyển USB về Jetson.
2. Nạp `agv_mega_safe/agv_mega_safe.ino` bằng Arduino IDE, Mega2560, Verify/Upload. Giữ MOTOR_LOCK làm dự phòng.
   Firmware mới không nhận F/M đơn qua USB Monitor; WiFi Serial2 vẫn giao thức cũ.
3. Chép toàn bộ thư mục giải nén sang Jetson, ví dụ `/home/<user>/agv_safe1`.
4. Trên Jetson trong thư mục đó: `python3 install_server.py "$HOME/stream_server.py"`.
   Script tự sao lưu hai file đích nếu có, chép server + helper cùng thư mục. Không khởi động dịch vụ.
   Nếu ExecStart của dịch vụ trỏ nơi khác, dùng đường dẫn đó làm đối số, xem bằng `systemctl cat agv_server.service`.
5. Nối USB Mega-Jetson, service vẫn inactive. `sudo fuser -v /dev/ttyUSB0` không nên có tiến trình giữ cổng.
   `python3 verify_link.py /dev/ttyUSB0` -> AGV:SAFE1, ACK:STOP, DATA:...,STOP,... và PASS.
   Không cần sudo cho Python nếu phép đọc trước đã có quyền. Nếu bận/permission, chẩn đoán thông báo, không chmod777 hoặc kill bừa tiến trình.
6. `sudo systemctl start agv_server.service`
   `sudo journalctl -u agv_server.service -n 60 --no-pager`
   Trình duyệt Ctrl+F5. USB phải hiện cổng; chế độ ban đầu LÁI TAY. Serial_error hiện trong title nhãn USB, log chi tiết ở journal và /telemetry.
   Nếu vẫn MOTOR_LOCK, server sẽ KHÔNG bắt tay/không cho lái: nạp SAFE1 đúng board.
7. Khi liên kết đúng, kê chắc4bánh khỏi sàn, cấp motor và thử giữ/nhả từng nút; Space/Z/STOP phải dừng, MODE chuyển theoACK.
   Chỉ sau đó thử AUTO trên sàn. Không nối lại ESP cho đến khi USB ổn.
8. Thử mất kết nối: với bánh kê chắc, dừng service/rút USB, AUTO phải ngắt sau watchdog; manual theo timeout ngắn hơn.
   Nếu Mega mất cả nguồn khi rút USB thì đây không phải phép thử watchdog độc lập; cần nguồn logic ổn định.

## Giới hạn
- Code từ DOCX đã chuẩn hóa NBSP thành dấu cách. Phần hình ảnh giữ theo tài liệu, chưa kiểm tra camera/GPU/CDN/Flask thực trên Jetson.
- Mô phỏng không kiểm chứng điện áp chân driver hoặc độ trễ vật lý. Serial lỗi ký tự còn có thể do reader thứ hai, dây/nguồn; cần kiểm tra lại log trên máy.
- WiFi ESP là đường điều khiển thứ hai độc lập, không được coi đã sửa khi chưa nhận source/test ESP.
- Không thay hằng số góc90, chân motor hoặc thông số né cản trong firmware bạn gửi.
