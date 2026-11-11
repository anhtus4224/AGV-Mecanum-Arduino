# TEACH_MAP_FIX1 — sửa vẽ lượt đi/về, giữ lệnh motor

Nhánh `fix/teach-map-timing-calibration-2026-11-12`, nền INDOOR_V2 commit9f431dd68926129f131ee1acb8b581df84abef2b.

Người dùng báo xe thật lượt đi/về đúng theo quan sát, vị trí về gần điểm xuất phát, nhưng bản đồ lệch. Đây là báo cáo của người vận hành, chưa có đo encoder/IMU. Ảnh mô hình về lệch khoảng0,73 m và hướng208°. Bản này sửa mô hình vẽ, không sửa phần chạy đã thử được.

## Phần sửa

- Nhận thời gian quay180° tại PWM80 trong thao tác Bắt đầu ghi, nếu ô hiệu chuẩn đã tích. Hệ số vẽ quay là pi*255/(80*T). T=15.65 s cho khoảng0.640 rad/s ngoại suy tại PWM255, khác giá trị giả thiết1.5 cũ. Đây là ngoại suy tuyến tính theo PWM, chưa phải đo tốc độ ởPWM255 hay200. Hai hệ số tiến0.236/dạt0.18 m/s vẫn giữ nguyên; vẫn cần hiệu chuẩn riêng nếu thang mét sai. Cấu hình vẽ này chỉ cập nhật trong phiên, không thay cap/thời gian quay/lịch lệnh.
- Tích phân lái tay từ hai khung MOTION liên tiếp theo thời gian board_ms của Mega. Không lấy số lần thread/camera/HTTP chạy để quyết định quãng đường. Frame trùng bỏ qua; khoảng mất dữ liệu không được bịa thành chuyển động, vệt ngắt đoạn thay vì nối qua khoảng trống.
- Chỉ một nơi tích phân xe thật. physics worker và visual_tick/đọc telemetry không cộng thêm lần nữa. Simulation vẫn dùng vòng thời gian riêng; AUTO vẫn dùng nhánh phản hồi/line/corner cũ.
- Cung chuyển động với vận tốc thân không đổi dùng công thức tích phân chính xác thay cho xấp xỉ midpoint.
- Sau khi chốt hướng mô hình+180° cuối lượt quay, không cộng lại khoảng PWM đã bắt đầu trước mốc chốt. Lưu độ dài khoảng bị bỏ vì không biết chính xác phần trước/sau mốc trong `heading_anchor_gap_ms`. Đây không phải phép đo góc; không ép điểm cuối vào gốc và không ép mọi điểm quay về trùng vệt đi.
- Tách rõ màu đỏ lượt ghi, xanh lam lượt về, bỏ glow xanh lá che màu. Bản đồ tiếp tục ghi là ước lượng PWM theo thời gian Mega, không phải định vị đo.

`visualization.drawing_revision=MEGA_TIME_MAP_V1`. `visualization.turn_calibration` ghi thời gian80 và hệ số vẽ dùng trong phiên. Gateway/firmware vẫn ghi AVOID_DIRECTIONAL_V4, teach_return vẫn TEACH_RETURN_INDOOR_V2; đó là đúng vì điều khiển/guard không đổi.

## Cập nhật2 file qua SSH FS

1. DỪNG → Nhả quyền → Ctrl+C terminal Jetson. Giữ nguồn/USB.
2. Giải nén gói mới trên PC, chép đè đúng2 file vào `/home/nguyennhutoan_uav/agv_vector_v1`, chọn Replace:
   - `agv_vector_gateway.py`
   - `stream_server_vector_v1.py`
3. Giữ nguyên `teach_return.py`, `vector_controls.js`, launcher, firmware và các file còn lại từ INDOOR_V2. Không cần nạp Mega hoặc tắt nguồn.
4. Terminal Jetson:

   ```bash
   cd /home/nguyennhutoan_uav/agv_vector_v1
   python3 -m py_compile agv_vector_gateway.py stream_server_vector_v1.py
   python3 run_vector_v1.py
   ```

5. Web Ctrl+F5. **Điền15.65 và tích xác nhận trước khi bấm Bắt đầu ghi**, để cùng hệ số vẽ được dùng ngay từ đầu cả lượt đi và về. Hoàn tất chọn cap/Áp dụng trước khi ghi. Giữ cap/quyền/trang như các lần thử được. Lượt mới đặt lại điểm đầu; không dùng vệt cũ vẽ bằng hệ số1.5 để đánh giá bản sửa.
6. Nhận quyền → Đặt điểm đầu + ghi đường → lái → DỪNG → Chốt → Quay180° và về. Lệnh phát xuống motor vẫn như INDOOR_V2. Khởi động lại server mất đường trong RAM, cần ghi một lượt mới.
7. Nếu còn lệch, giữ ảnh cả vệt và metadata `visualization` từ `/telemetry` sau khi lượt đã xong. Nhãn `turn_calibration` phải có15.65. Nếu mất khung MOTION, vệt có thể ngắt; không coi đường mô hình là vị trí thực hay tự chỉnh lệnh motor theo sai số này.

## Xác minh

74 bài Python/Flask đạt: thời gian Mega so với nhịp host không đều, đọc snapshot không di chuyển mô hình, khung trùng/mất/quá cũ không cộng khoảng bịa, gain15.65 cho pi ởPWM80, cung tròn khớp công thức, đường cong đảo đóng trong mô hình lý tưởng không snap vị trí, khoảng trước mốc180° không cộng lần hai; callback hiệu chuẩn không phát D hoặc đổi cap. Chromium USB giả kiểm tra ghi5 thao tác/vệt/quay về/STOP/blur và lỗi ghi, gồm cấu hình F999 được xác nhận. Test với thời gian quay ngắn kiểm tra sai số ngay mốc chuyển, và với15.65 s giống người dùng. Mô phỏng không chứng nhận sai số trên sàn.

Nguồn write/watchdog/receive/STOP/legacy_command của Gateway được so AST với nền: không đổi. teach_return.py, vector_controls.js và toàn bộ sketch Mega nguyên byte. Không rebuild AVR vì firmware không đổi. Chưa áp dụng gói này trên Jetson/xe thật từ Codex.

Sai số do PWM không tuyến tính, pin/tải/bánh trượt, gain tiến/dạt chưa đo và khoảng thiếu MOTION vẫn tồn tại. Bản sửa không bảo đảm hai vệt trùng tuyệt đối hoặc về đúng từng cm, và không giấu sai số bằng cách vẽ theo polyline định sẵn.

## Tải riêng

- [agv_vector_gateway.py](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-map-timing-calibration-2026-11-12/upgrade_v1/agv_vector_gateway.py)
- [stream_server_vector_v1.py](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-map-timing-calibration-2026-11-12/upgrade_v1/stream_server_vector_v1.py)
- [Gói2 file ZIP](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-map-timing-calibration-2026-11-12/AGV_TEACH_MAP_FIX1_2026-11-12.zip)
- [ZIP toàn nhánh](https://github.com/anhtus4224/AGV-Mecanum-Arduino/archive/refs/heads/fix/teach-map-timing-calibration-2026-11-12.zip)
