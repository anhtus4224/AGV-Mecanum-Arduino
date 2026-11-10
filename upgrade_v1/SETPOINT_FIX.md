# SETPOINTFIX — ACK cho luồng đặt vận tốc thay thế nhau

## Bằng chứng và giới hạn kết luận

Diagnostic người dùng: pending D tuổi407 ms, last_ack D sequence133 OK, PWM age64 ms ở sự kiện, last_nonzero [80,-80,-80,80]. Khi đọc lại ready=true, PWM hiện tại0, drawing_lost=true. Phần mềm đóng liên kết vì một ACK D quá hạn, không phải báo lỗi nhận vector. Log trước chưa lưu sequence của D quá hạn nên chưa chứng minh chắc đó là D cũ hơn133; cần giữ phân biệt với lệnh D mới nhất thực sự chưa ACK hoặc lỗi điện/USB.

Lỗi thiết kế được khắc phục: D là setpoint tức thời lặp lại, không phải hàng đợi các đoạn đường. Khi ACK OK của D mới hơn (hoặc STOP/chuyển mode đã chấp nhận) tới, các D có sequence nhỏ hơn đã bị thay thế. Firmware có chặn sequence cũ nên các lệnh đó không thể quay lại ghi đè mục tiêu mới. Bản PINGFIX trước chỉ xóa P cũ nên vẫn có thể đóng cổng do ACK của D đã bị thay thế.

## Quy tắc mới

- ACK OK D/S/A/M mới hơn loại D cũ hơn và giữ bộ đếm drive_ack_superseded.
- ACK PING không xác nhận lệnh chạy, không loại D.
- ACK lỗi MODE/... không loại D.
- ACK bất kỳ không tự loại STOP đang thiếu ACK. Không loại ACK mode/config chưa nhận.
- D mới nhất không có ACK mới hơn phù hợp vẫn timeout400 ms; PWM cũ400 ms vẫn dừng, ticket300 ms và watchdog Mega giữ nguyên.
- Không tự tiếp tục vệt qua khoảng mất dữ liệu. Nếu lỗi liên kết thực tiếp tục, mô hình vẫn giữ vị trí cuối. Chưa chứng minh hết nguyên nhân trên xe.

Chỉ agv_vector_gateway.py runtime đổi, không nạp Mega, không thay chân/dấu/PWM/thuật toán né. Chẩn đoán thêm gateway_revision=SETPOINT_ACK_V1 và sequence ở từng pending quá hạn, giúp xác nhận đúng file và kiểm tra sự cố tiếp theo.

## Cập nhật

1. DỪNG, xác nhận bánh thật đứng yên, tắt nguồn motor. Ctrl+C server trong terminal JETSON.
2. Tải AGV_VECTOR1_SETPOINTFIX_2026-11-10.zip, Extract all trong Downloads.
3. Terminal JETSON:

```bash
cd "$HOME/agv_vector_v1"
cp -n agv_vector_gateway.py agv_vector_gateway.before_setpointfix.py
```

4. Terminal PC (PS):

```powershell
scp "$env:USERPROFILE\Downloads\AGV_VECTOR1_SETPOINTFIX_2026-11-10\upgrade_v1\agv_vector_gateway.py" nguyennhutoan_uav@192.168.1.71:/home/nguyennhutoan_uav/agv_vector_v1/agv_vector_gateway.py
```

5. Terminal JETSON: `python3 run_vector_v1.py`, nhập thông tin như trước. Web Ctrl+F5. Mở `/control/diagnostics` xác nhận gateway_revision SETPOINT_ACK_V1. Tài khoản đăng nhập vẫn bắt buộc.
6. Khi dừng, đặt lại điểm đầu/phiên vẽ một lần và xác nhận mốc theo hướng dẫn. Kiểm tra PWM80, LÁI TAY, né TẮT. Thử ngắn tiến/thả/dạt/thả chỉ khi bánh treo và điều kiện nguồn đã chuẩn bị. Chưa tăng tốc/AUTO.
7. Nếu xám lại: DỪNG, giữ server đang chạy, gửi JSON `/control/diagnostics`. Không dùng việc reset mốc liên tục để che gián đoạn.

Nếu chưa có JOYFIX, phải dùng thêm vector_controls.js tương thích từ gói; hệ thống vừa cài JOYFIX/ACKFIX/PINGFIX chỉ cần gateway. Không chạy hai server hoặc đổi nguồn/đấu dây lúc đang mang điện. Gói phần mềm không xác minh mạch nguồn USB.

## Kiểm chứng và rollback

32 test gateway qua trên host Python3.12/fake serial, syntax Python3.6 qua. Kiểm tra ACK D mới loại D cũ; STOP ACK loại D cũ; D ACK không che STOP mất ACK; PING không che D; ACK MODE không che D; PWM cũ vẫn đóng dù có D ACK; chuỗi tiến/thả/dạt có ACK cũ bị mất vẫn giữ kết nối nếu lệnh mới được xác nhận. Không nới ngưỡng hoặc xóa test cũ để đạt kết quả. Chưa thử trực tiếp bản này trên xe.

Rollback: Ctrl+C, `cp agv_vector_gateway.before_setpointfix.py agv_vector_gateway.py`, restart launcher và tải lại trang. Các bản gốc/nhánh trước được giữ nguyên.
