# PINGFIX — không giữ PING cũ khi đã ACK lệnh mới hơn

## Bằng chứng từ xe

Diagnostic người dùng: ACK_TIMEOUT, pending op=P tuổi413 ms; last_drive_ack D/OK; last_nonzero_pwm [80,-80,-80,80]; thời điểm đọc ready=true, motion_age_ms=38, current_pwm=[0,0,0,0], drawing_lost=true. Có bằng chứng phần mềm đóng liên kết vì ACK PING chậm rồi nhận lại liên kết; chưa có bằng chứng cáp bị rút hoặc nguyên nhân điện. Last ACK trong snapshot có thể là sau reconnect, không dùng nó để khẳng định chắc ACK mới hơn đã tồn tại trước lần timeout.

## Sửa tối thiểu

Runtime chỉ đổi agv_vector_gateway.py. Khi nhận ACK OK hợp lệ của một bản tin đang chờ, xóa các PING có sequence nhỏ hơn. ACK mới hơn trong cùng sổ chờ chứng minh parser đã tiến qua PING cũ. Tuyệt đối không xóa D/S/A/M/E/H đang thiếu ACK dựa vào ACK khác. ACK bị từ chối không loại PING. Nếu không có ACK mới hơn, PING vẫn timeout400 ms như trước. Mất PWM mới vẫn timeout400 ms; ticket300 ms, watchdog Mega và quyền lái giữ nguyên. Bổ sung last_ack/motion_age ở log ACK_TIMEOUT cho lần chẩn đoán sau.

Không sửa firmware/nguồn, không tự phục hồi tọa độ qua gián đoạn, không nhận dữ liệu PWM thành phép đo encoder. Nếu có mất liên kết thật, mô hình vẫn giữ vị trí cuối và cần người vận hành đặt lại mốc.

## Cài (hệ thống đã có JOYFIX/ACKFIX)

1. DỪNG, xác nhận bánh thật đứng yên, tắt nguồn motor. Ctrl+C trong terminal JETSON.
2. Tải AGV_VECTOR1_PINGFIX_2026-11-10.zip và Extract all trong Downloads.
3. Terminal JETSON:

```bash
cd "$HOME/agv_vector_v1"
cp -n agv_vector_gateway.py agv_vector_gateway.before_pingfix.py
```

4. Terminal PC, đầu dòng PS:

```powershell
scp "$env:USERPROFILE\Downloads\AGV_VECTOR1_PINGFIX_2026-11-10\upgrade_v1\agv_vector_gateway.py" nguyennhutoan_uav@192.168.1.71:/home/nguyennhutoan_uav/agv_vector_v1/agv_vector_gateway.py
```

5. Terminal JETSON: `python3 run_vector_v1.py`; nhập thông tin như trước. Web Ctrl+F5. Không nạp lại Mega.
6. Đặt lại điểm đầu/phiên vẽ khi xe đã dừng và xác nhận mốc. Lượt thử lặp tiến/thả/dạt/thả ở cap80, né TẮT, bánh treo; không bật AUTO hoặc tăng cap trong lượt này.
7. Nếu tiếp tục xám: DỪNG rồi mở `http://192.168.1.71:5000/control/diagnostics`, gửi nội dung. Mở tab khác có thể tự nhả quyền. Chưa có cam kết hết mọi nguyên nhân ngắt liên kết trên hardware.

## Kiểm thử và quay lại

26 unit test gateway qua, gồm 4 test mới: ACK D/S mới loại PING cũ; ACK P mới không loại D đang thiếu; ACK MODE không loại PING. Các test trước vẫn qua. Python3.6 grammar qua; runtime test Python3.12, serial giả. Chưa kiểm chứng trực tiếp bản sửa này trên Jetson/xe người dùng. Không thay ngưỡng để làm test qua.

Quay lại: Ctrl+C, `cp agv_vector_gateway.before_pingfix.py agv_vector_gateway.py`, restart launcher và tải lại trang. Bản gốc và các nhánh trước giữ nguyên.
