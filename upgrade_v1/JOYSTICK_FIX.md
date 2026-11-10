# JOYFIX — phiếu lệnh cho bàn phím/joystick, 10/11/2026

## Bằng chứng và thay đổi

Ảnh người dùng báo Vector/thứ tự/thời hạn không hợp lệ. Thông báo cũ gộp nhiều nguyên nhân, nên không chứng minh riêng nguyên nhân trên điện thoại chỉ từ ảnh. Đã tái hiện chính xác thông báo với bản trước (ff23eba): trì hoãn phản hồi telemetry 450 ms trong Chromium cảm ứng, giữ joystick, server từ chối issued_ms và trang bỏ quyền. Vector không cần sai để bị từ chối: cách suy ra giờ server từ telemetry chịu độ trễ phản hồi đó.

Bản này không nới hạn 300 ms. /control/renew cấp một ticket một lần, buộc vào lease/môi trường/generation; /control/vector xác minh tuổi bằng đồng hồ server, tiêu thụ ticket. UI lấy ticket từ phản hồi nhỏ riêng trước khi gửi vector, không lấy timestamp từ luồng telemetry/camera. Gói đến quá 300 ms vẫn bị từ chối, UI xóa giữ lệnh và cố STOP. Phân biệt VECTOR, SEQUENCE, CONTEXT, TICKET, COMMAND_EXPIRED thay vì thông báo gộp. Mạng thật quá chậm vẫn có thể dừng; đây không phải cam kết chịu mọi độ trễ.

Chỉ 2 file runtime thay đổi: agv_vector_gateway.py và vector_controls.js. Phải cập nhật cùng nhau và restart server để HTML nhúng JS mới. Firmware, pin, thuật toán line/cua/né, thời hạn quyền và watchdog Mega không đổi. Có sẵn sửa mô phỏng thiếu Mega từ bản trước.

## Cài

1. Tải AGV_VECTOR1_JOYFIX_2026-11-10.zip, Extract all. Nguồn xe tắt, USB Mega rời trong lượt mô phỏng.
2. Terminal JETSON: Ctrl+C dừng server, rồi từng lệnh:

```bash
cd "$HOME/agv_vector_v1"
cp -n agv_vector_gateway.py agv_vector_gateway.before_joyfix.py
cp -n vector_controls.js vector_controls.before_joyfix.js
```

3. Terminal PC, đầu dòng PS, nếu giải nén mặc định Downloads:

```powershell
scp "$env:USERPROFILE\Downloads\AGV_VECTOR1_JOYFIX_2026-11-10\upgrade_v1\agv_vector_gateway.py" "$env:USERPROFILE\Downloads\AGV_VECTOR1_JOYFIX_2026-11-10\upgrade_v1\vector_controls.js" nguyennhutoan_uav@192.168.1.71:/home/nguyennhutoan_uav/agv_vector_v1/
```

4. Terminal JETSON: `python3 run_vector_v1.py`, nhập tài khoản/mật khẩu/USB như trước. Không cần nạp Mega.
5. Laptop Ctrl+F5; điện thoại tải lại trang (đóng/mở lại tab nếu còn JS cũ), đăng nhập. Laptop Nhả quyền, điện thoại Nhận quyền. Chọn Mô phỏng trên ô ĐIỀU KHIỂN ở đầu khung bản đồ. Giữ joystick 5–10 s, thả để dừng; chuyển ứng dụng phải nhả quyền. Không thử motor với cấu hình nguồn chưa xác minh.
6. Nếu vẫn lỗi, gửi nguyên thông báo mới và đoạn log terminal quanh POST /control/vector. Không gửi mật khẩu hoặc nội dung header lease/ticket.

## Kiểm chứng

18 test Flask gateway qua: thêm ticket một lần, quá hạn 310 ms bị chặn không ghi USB, không phụ thuộc issued_ms từ đồng hồ client. Chromium mô phỏng cảm ứng với telemetry phản hồi chậm 450 ms: bản trước tái hiện từ chối; bản mới giữ quyền, mô hình đi chéo, thả dừng, không vector rejection/pageerror. Kiểm tra simulation USB retry trước vẫn qua. Đây là trình duyệt chạy trên host với phần cứng giả, chưa thử trực tiếp điện thoại người dùng/Jetson.

## Quay lại

Ctrl+C, trên Jetson:

```bash
cd "$HOME/agv_vector_v1"
cp agv_vector_gateway.before_joyfix.py agv_vector_gateway.py
cp vector_controls.before_joyfix.js vector_controls.js
```

Restart launcher và tải lại trang. Phải quay lại cả hai file. Không dùng các ZIP bản trước để lấy một nửa cặp mới.
