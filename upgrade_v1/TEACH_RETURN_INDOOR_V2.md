# Quay về trong nhà — TEACH_RETURN_INDOOR_V2

Nhánh `fix/teach-return-indoor-2026-11-12`. Dùng firmware AVOID_DIRECTIONAL_V4 đã nạp. Chỉ cập nhật3 file Jetson; không cần nạp Mega, đổi dây hoặc tắt nguồn. Gói đã bao gồm sửa giữ lý do hủy của TEACH_TRACE_FIX1 mà người dùng chưa cài.

## Bằng chứng

Người dùng báo3 lượt quay về: lượt đầu quay và đi được một đoạn rồi dừng; lượt hai đi khoảng0,2 giây rồi dừng; lượt ba quay xong không đi tiếp. Ảnh có thông báo `Khoảng hở F chưa đủ / chưa xác nhận … bước0/20`, F không echo, B66/L125/R73. Bước0 là pha quay đầu trong lịch lệnh; không nhất thiết đã qua thời gian quay dù người quan sát thấy thân gần180°. V4 gốc bắt mọi tia hữu hạn >30 cm suốt các đoạn xoay, nên fresh999 ở F cũng hủy lượt. Đó là nguyên nhân xác định được của ảnh này; chưa có snapshot từng lượt để khẳng định cả3 lần cùng nguyên nhân. Thông báo CLEARANCE ở mục né có thể còn từ lần né trước, không thay cho lỗi `teach_return`.

Người dùng cũng mô tả bấm Chốt hai lần. Chốt lặp lại sau một lượt hợp lệ vốn không tự hủy đường: finish() có thể được gọi lại. Lỗi khác đã xác định là chốt đường không hợp lệ làm mất lý do hủy; gói này giữ lý do gốc, không ép đường dở thành hợp lệ.

## Điều chỉnh theo yêu cầu giảm ngưỡng dừng

Các thay đổi sau chỉ dành cho lịch quay về:

- Tịnh tiến/dạt: từ12 cm xuống10 cm, chỉ xét hướng đang đi; số đo bằng ngưỡng vẫn dừng.
- Xoay: từ30 cm mọi phía thành20 cm trước/sau và14 cm trái/phải. Mô hình thân47×34 cm có bán kính góc khoảng29 cm; phần nhô thêm khi xoay từ đầu gắn mép ~12 cm trước/sau, ~5,5 cm hai bên, thêm khoảng8 cm đệm. Đây là giả thiết hình học theo gốc đầu đo ở mép, không có phép đo quãng phanh. Nếu đầu đo lùi vào trong bánh hoặc có vật nhô thêm, phải tăng ngưỡng tương ứng trước khi chạy.
- Giá trị999 mới (không echo) được chấp nhận trong đoạn xoay **chỉ khi người dùng đã tích ô hiệu chuẩn và kiểm tra khoảng trống**. Không thay999 bằng khoảng cách giả. Mặc định hàm guard vẫn từ chối999 lúc xoay khi không có xác nhận; API không cho bắt đầu lượt về khi thiếu xác nhận.
- Vẫn xét cả4 tia khi xoay. Giá trị0–3, giá trị ngoài miền, tia/gói quá cũ, khoảng hở hữu hạn không đủ đều dừng. Giữ ngưỡng tuổi350 ms, watchdog/lease/ticket/STOP, thời gian quayPWM80, cap đã ghi và thứ tự đảo đường. Không thay thuật toán né, bám line, motor hay firmware.

Không echo cũng có thể do vật nghiêng/hấp thụ/lỗi đầu đo, không tự chứng minh an toàn. Việc chấp nhận999 lúc xoay là chính sách thử có người vận hành đã kiểm tra cả vùng thân quét. Vẫn cần vùng xoay đủ rộng, không chỉ một tia nhìn ra xa. Ngưỡng giảm không bảo đảm không va chạm, nhất là khi tốc độ cao hoặc xe trượt. Cảm biến vẫn đo/hiển thị vật xa; thay đổi là ngưỡng dừng, không cắt tầm đo hay timeout sonar.

## Quan sát lỗi

`teach_return.revision=TEACH_RETURN_INDOOR_V2`.

`guard_policy` chứa `translation_cm`, `turn_cm`, `unknown_turn_allowed` (chỉ true sau khi lịch đã được bắt đầu với ô xác nhận). `last_guard` lưu bước, vector lệnh, số đo thô4 hướng, tuổi từng tia, tuổi gói và lý do tại thời điểm hủy do cảm biến. `invalid_reason` cùng8 events gần nhất giữ nguyên lý do đầu tiên. Một hủy do watchdog/lease vẫn được ghi bằng lý do đó, không giả là lỗi sonar. Lượt mới xóa snapshot cũ.

## Cập nhật trực tiếp qua SSH FS

1. DỪNG, Nhả quyền; Ctrl+C terminal Jetson đang chạy launcher. Giữ nguồn và USB.
2. Giải nén gói mới trên PC. Chép đè đúng3 file vào `/home/nguyennhutoan_uav/agv_vector_v1`:

   - `agv_vector_gateway.py`
   - `teach_return.py`
   - `vector_controls.js`

   Chọn Replace/Ghi đè cho3 file đích. Không đổi tên thêm hàng loạt file. Không cần thay `stream_server_vector_v1.py`, launcher hoặc `.ino/.h`. Bản V4 cũ vẫn tải được tại commit5516da4858a2cbab15cf979709390dec5358ece7 để khôi phục.
3. Terminal Jetson:

   ```bash
   cd /home/nguyennhutoan_uav/agv_vector_v1
   python3 -m py_compile agv_vector_gateway.py teach_return.py
   python3 -c "from teach_return import TeachReturn; print(TeachReturn().snapshot()['revision'])"
   python3 run_vector_v1.py
   ```

   Lệnh kiểm tra phải in `TEACH_RETURN_INDOOR_V2`. Nhập tài khoản/mật khẩu web tại máy, USB `/dev/ttyUSB0`. Không gửi mật khẩu vào chat.
4. Web Ctrl+F5, kiểm tra diagnostics có revision mới. Gateway/firmware vẫn ghi AVOID_DIRECTIONAL_V4; đó là đúng vì firmware không đổi.
5. Nhập lại thời gian đã đoPWM80 là15.65, tích ô xác nhận sau khi kiểm tra chỗ quay. Chọn cap muốn ghi, hoàn tất Áp dụng trước khi ghi. Thử lượt ngắnPWM80 trước, sau đó cap200 theo nhu cầu; không đổi cap giữa lượt.
6. Nhận quyền → Đặt điểm đầu + ghi đường → đợi Đang ghi → lái2–3 đoạn ngắn → DỪNG → Chốt, đợi Đã chốt đường → Quay180° và về. Giữ nguyên cửa sổ web/quyền/cấu hình. Lượt trước đã hủy không dùng tiếp được; khởi động lại server cũng xóa đường RAM.
7. Nếu dừng bất thường, giữ xe dừng và server chạy; lấy `teach_return` trong diagnostics, đặc biệt `invalid_reason`, `last_guard`, `events`. Không chỉ chụp số đo dashboard sau dừng rồi coi đó là thời điểm lỗi.

## Kiểm tra

67 bài Python/Flask đạt; bao gồm F999 chưa xác nhận bị chặn, có xác nhận được chấp nhận; từng biên20/14/10 và số đo0/1/3/400/998 vẫn chặn, tuổi tia/gói cũ vẫn chặn, snapshot tại lỗi và API thiếu xác nhận không phát lệnh. Chromium với USB/cảm biến giả dùng F999/B66/L125/R73 kiểm tra ghi5 thao tác, quay/phát đảo lịch, vệt mô hình, STOP và hủy do mất quyền. node --check và git diff --check đạt. Firmware nguyên byte so với V4 nên không rebuild/nạp AVR trong bản sửa này. Chưa áp dụng lên Jetson hoặc thử trên xe thật từ Codex. Đường và góc vẫn là ước lượng lệnh/thời gian, không có odometry/IMU.

## Tải từng file

- [agv_vector_gateway.py](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-return-indoor-2026-11-12/upgrade_v1/agv_vector_gateway.py)
- [teach_return.py](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-return-indoor-2026-11-12/upgrade_v1/teach_return.py)
- [vector_controls.js](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-return-indoor-2026-11-12/upgrade_v1/vector_controls.js)
- [Gói3 file ZIP](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-return-indoor-2026-11-12/AGV_TEACH_RETURN_INDOOR_V2_2026-11-12.zip)
- [ZIP toàn nhánh](https://github.com/anhtus4224/AGV-Mecanum-Arduino/archive/refs/heads/fix/teach-return-indoor-2026-11-12.zip)
