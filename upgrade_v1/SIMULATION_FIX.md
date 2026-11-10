# Sửa mất quyền lái khi chưa cắm Mega — 10/11/2026

Lỗi: serial_worker xóa owner mỗi lần dò USB thất bại, kể cả chưa từng kết nối Mega. Watchdog cũng áp dụng điều kiện PWM/ACK thật cho mô phỏng. Chỉnh sửa chỉ ở agv_vector_gateway.py: giữ quyền khi dò thất bại; chỉ thu hồi khi một kết nối thật đã thiết lập bị mất trong Xe thật; watchdog mô phỏng chỉ xét thời hạn quyền, không ghi USB.

Không thay firmware, motor, nguồn, giao thức hoặc thuật toán né. Nhánh VECTOR1 trước giữ nguyên. 15 test gateway và kiểm tra Chromium với worker dò USB thất bại chạy nền đã qua; thử nhận quyền, chờ hơn một lượt retry, chọn simulation và chạy W+A. Không có phần cứng thật.

## Cài trên Jetson

Tải gói AGV_VECTOR1_SIMFIX_2026-11-10.zip ở nhánh sửa này, Extract all. Chỉ cần file upgrade_v1/agv_vector_gateway.py để cập nhật hệ thống đã cài. Gói ZIP AGV_VECTOR1_2026-11-10.zip cũ được giữ nguyên để truy vết, không chứa hotfix này.

1. Trong terminal JETSON đang chạy server, Ctrl+C, đợi đầu dòng Jetson.
2. Giữ bản gateway đang dùng, chạy từng lệnh trên Jetson:

```bash
cd "$HOME/agv_vector_v1"
cp -n agv_vector_gateway.py agv_vector_gateway.before_simfix.py
```

3. Trong terminal PC (đầu dòng PS), cd tới upgrade_v1 vừa giải nén, rồi:

```powershell
scp .\agv_vector_gateway.py nguyennhutoan_uav@192.168.1.71:/home/nguyennhutoan_uav/agv_vector_v1/agv_vector_gateway.py
```

4. Trong terminal JETSON:

```bash
cd "$HOME/agv_vector_v1"
python3 run_vector_v1.py
```

Nhập tài khoản, mật khẩu ít nhất 12 ký tự và /dev/ttyUSB0 như trước. Không cần Mega cho mô phỏng. Giữ nguồn xe tắt và USB Mega rời trong lượt thử mô phỏng.

5. Web Ctrl+F5; đăng nhập lại. Bấm Nhận quyền lái. Ctrl+Home lên đầu trang, khung BẢN ĐỒ OXY bên phải: ngay dưới tiêu đề có hàng ĐIỀU KHIỂN với ô Xe thật · USB. Chọn Mô phỏng. Thử W/A/S/D hoặc joystick; nhả để dừng. Chỉ mô hình chuyển động, không phải xe thật.

Nếu chuyển sang cửa sổ khác, trang có thể tự nhả quyền; trở lại và bấm Nhận quyền lái. Không bật AUTO hoặc bật né cho mô phỏng.

## Quay lại gateway trước

Ctrl+C server, rồi trên Jetson:

```bash
cd "$HOME/agv_vector_v1"
cp agv_vector_gateway.before_simfix.py agv_vector_gateway.py
```

Sau đó chạy lại launcher. File trước vẫn giữ riêng. Lỗi mất quyền ở chế độ không có Mega có thể trở lại với bản cũ.
