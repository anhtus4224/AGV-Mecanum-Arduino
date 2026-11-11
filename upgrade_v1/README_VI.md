> Bản mới theo yêu cầu chọn hướng khi sonar bên không echo: [DIRECTIONAL_AVOID_V3.md](DIRECTIONAL_AVOID_V3.md). Mặc định80/né tắt; chưa thử xe bản V3.

> Sửa cửa sổ đo/lấy mẫu quét: [AVOID_SCAN_RETRY.md](AVOID_SCAN_RETRY.md). Chưa thử xe bản sửa này.

> Bổ sung chẩn đoán quét: xem [SCAN_DIAGNOSTICS.md](SCAN_DIAGNOSTICS.md). Chưa sửa nguyên nhân NO_CONFIRMED_CORRIDOR trên xe.

# AGV VECTOR1 — bản nâng cấp thử nghiệm, chưa thử trên xe

**Bản sửa 11/11/2026: TOUCH_VECTOR_V2.** Đọc [TOUCH_VECTOR_V2.md](TOUCH_VECTOR_V2.md)
và [TEST_REPORT_TOUCH_V2.md](TEST_REPORT_TOUCH_V2.md) trước khi dùng. Nguồn là
SETPOINT_ACK_V1 tại commit 882daf1; chưa đối chiếu hash Jetson hôm nay.
Dạt ngang mới được kiểm tra phần mềm/thêm chẩn đoán, chưa xác nhận sửa trên xe.

Bản nguồn do người dùng chọn: CUAXOAYNGANG (Mega) + stream_server_reset_v1.py (Jetson/Web). Không dùng STABLE/CHUAN_GOC thay cho file chính. Xem PROVENANCE.json để nhận diện SHA-256. Không chạy script patch cũ.

## Những gì đã đổi

- Giữ các chân, dấu motor, LINE_DETECTED=LOW, A2=OUT3, bảng INNER/OUTER, phần dò line và cua gốc. Điểm vào né hiện là 55 cm, chuyển giao sau né và cơ chế giới hạn đầu ra khi thử.
- Máy trạng thái né mới: dừng/quét xác nhận khoảng hở → tiến chéo ra (~27° danh nghĩa) → vượt → chéo về → A2 liên tục 80 ms → bàn giao dò line. Không thêm STOP giữa các chặng di chuyển đã đủ điều kiện. Quét đầu vẫn dừng; không cố đi mù để giữ độ mượt.
- Mixer giữ quy ước bánh gốc. Trần tối đa 255, slew 8 PWM mỗi lượt mục tiêu 10 ms; hai cặp bánh phải có PWM khác nhau khi chạy chéo. Có qua 0 trước đảo chiều. STOP/watchdog bỏ qua ramp và xuất PWM0; không phải phanh cơ.
- Giao thức VECTOR1 mang đồng thời tiến/ngang/xoay, CRC16-CCITT, phiên, thứ tự, ACK. Dữ liệu MOTION là PWM đã xuất, không phải encoder. Không dùng SAFE1. Bản mới chỉ gửi khung sau khi probe '?' nhận đúng AGV:VECTOR1; '?' không điều khiển firmware gốc được cung cấp.
- Web: W+A/W+D/S+A/S+D; nút chéo; joystick tròn dùng Pointer Events; Q/E riêng để xoay. Giữ/nhả, đổi tab/mất focus và mất quyền bỏ các phím cũ. Một chủ điều khiển; người khác xem. Người xem đã đăng nhập có thể STOP, thao tác này thu hồi chủ hiện tại.
- Đăng nhập bắt buộc, CSRF, cookie phiên; không có mật khẩu mặc định. Không ghi password vào source hoặc GitHub.
- Quyền Web hết hạn sau 800 ms không gia hạn; Mega tự PWM0 nếu thiếu lệnh vector 250 ms hoặc thiếu host 700 ms (kể cả AUTO do host). Các số này là timeout logic, không phải bảo đảm xe cơ khí đứng yên trong đúng số ms đó.
- Không gửi DEF/CFG lên parser ký tự. Endpoint tuning cũ vẫn trả lỗi rõ ràng; cấu hình thử mới chỉ gồm cap và bật/tắt né, có ACK. Không tự đổi hằng số bám line.
- Radar tách raw/không echo/tuổi dữ liệu; không coi timeout 999 là đường trống. Mô hình dùng PWM trả về; mặc định tiến 0,236 m/s là giả định hình học từ 45 RPM/100 mm, ngang 0,18 m/s và xoay 1,5 rad/s vẫn cần đo lại. Lưu hiệu chuẩn trong thư mục mới `~/.local/share/agv-dashboard-vector-v1`, không dùng/sửa cấu hình vẽ bản cũ.

## Giới hạn phải biết trước khi nạp

Đây là bản để kiểm chứng và hiệu chỉnh, KHÔNG chứng nhận né an toàn ở PWM255. Bốn siêu âm không đo được toàn bộ bề rộng vật, mọi góc thân/đuôi hay độ trượt. Thời gian chặng/700 ms vượt tối thiểu chỉ là giới hạn thực nghiệm, không phải bằng chứng đã qua hết vật. Bản mới đòi dấu hiệu cạnh vật từ nhiều mẫu bên **hợp lệ**; không có echo/không đủ khoảng trống sẽ dừng chờ, có thể xảy ra thường xuyên với bình hẹp trong video. Không bỏ kiểm tra đó chỉ để xe tiếp tục chạy.

`VectorMotion.h` dùng số người dùng đo: rộng cả bánh 47 cm (nửa rộng 23,5), nhô trước/sau 17 cm, tổng dài 34 cm gồm thanh line; biên 12 cm giữ nguyên. Chưa đo vị trí gốc/góc mù các đầu siêu âm. Các guard bảo thủ này không chứng minh toàn bộ vùng thân quét trống. Không thể tự xác minh bằng checkbox trên Web; xem TOUCH_VECTOR_V2.md.

Chu kỳ mục tiêu 10 ms không phải chứng nhận thời gian thực cứng. pulseIn vẫn có thể chờ tối đa 8 ms/mẫu; phần mềm servo dùng cùng chân và khoảng xung 600–2400 us, giữ hàm servo gốc nguyên vẹn nhưng quét mới không dùng vòng hold. Telemetry/UART cũng có thể làm trễ; phải đo độ trễ STOP/chu kỳ thực trên Mega.

Bắt lại A2 không chứng minh thân xe thẳng hàng với line. Chỉ bàn giao để thuật toán line cũ tiếp tục chỉnh. Chưa dùng vị trí mô hình để quyết định tránh va chạm.

## Các file cần dùng

Mega: mở `mega_vector_v1/mega_vector_v1.ino` bằng Arduino IDE, giữ `VectorMotion.h` cùng thư mục. Board **Arduino Mega or Mega 2560**, processor **ATmega2560**.

Jetson: phải chép CÙNG thư mục bốn file:

1. stream_server_vector_v1.py
2. agv_vector_gateway.py
3. vector_controls.js
4. run_vector_v1.py

Không đổi tên file cũ, không chạy nhiều server hoặc hai chương trình giữ cùng USB. `requirements.txt` chỉ để tham khảo cài mới khi thật sự thiếu gói; không nâng cấp hàng loạt môi trường Jetson đang ổn. Cần Flask, pyserial, OpenCV, NumPy. Kiểm tra mới chỉ dùng Python 3.12 và cú pháp Python 3.6, chưa chạy trên Python 3.6/Jetson.

## Trình tự thử, cho mô hình dùng chung nguồn motor/Jetson

1. Lưu cặp đang chạy: file .ino được xác nhận và các file Python. Thư mục original_firmware chứa nguyên byte firmware đã gửi; file stream_server_reset_v1.py cũ vẫn ở gốc nhánh repository.
2. Bấm LÁI TAY → DỪNG, xác nhận xe đứng yên. Tắt Jetson bằng `sudo shutdown -h now`, đợi hoàn tất rồi mới ngắt nguồn chung để chuẩn bị. Không rút/cắm dây hở đang mang điện.
3. Chuẩn bị nạp/thử với nguồn motor tách/ngắt và logic được cấp đúng cách. Nếu không có cách tách, dùng giá chắc chắn bánh không chạm sàn làm bước thử không tải; đây không thay thế cách ly nguồn khi thao tác dây/nạp, cần người hiểu đấu nguồn kiểm tra. Không cắm đồng thời nguồn USB/5 V ngoài khi chưa xác nhận cách chống cấp ngược của board.
4. Biên dịch sketch mới trước. Chỉ nạp Mega khi đã chuẩn bị nguồn, board/cổng đúng và bản cũ có thể nạp lại. Không đổi ESP/pin/motor. Không mở Serial Monitor cùng lúc Jetson đang dùng USB.
5. Tải ZIP bản nâng cấp, giải nén trên PC. Chép 4 file Jetson ở trên vào thư mục mới `/home/nguyennhutoan_uav/agv_vector_v1` bằng SSH FS hoặc SCP. Có thể chép cả thư mục `upgrade_v1` và dùng đúng đường dẫn đã chép.
6. Trong terminal Jetson đang chạy server cũ: Ctrl+C. Sau đó chạy từng lệnh:

```bash
sudo systemctl stop agv_server.service
ss -ltnp 'sport = :5000'
```

Chỉ tiếp tục khi không còn LISTEN cổng 5000. Không kill bừa các tiến trình. Chọn một cổng USB chính xác; nếu có nhiều cổng, dùng `/dev/serial/by-id/...` thích hợp.

7. Trong terminal Jetson, giả sử 4 file được chép trực tiếp vào `~/agv_vector_v1`:

```bash
cd "$HOME/agv_vector_v1"
python3 run_vector_v1.py
```

Launcher hỏi tên đăng nhập Web, mật khẩu ít nhất 12 ký tự (không hiện khi gõ) và đường dẫn USB. Không gửi mật khẩu trong chat, không lưu vào code. Giữ terminal mở. Nhận diện VECTOR1 thất bại thì dừng kiểm tra cặp firmware; không đổi sang SAFE1/firmware khác để thử may rủi.

8. Mở `http://192.168.1.71:5000`, Ctrl+F5, đăng nhập. Xem `/telemetry`: server_version phải `VECTOR_AVOID_V1`; có VECTOR_STATE và MOTION mới. Lỗi/mất ACK sẽ đóng liên kết và cần nhận quyền lại. IP có thể đổi sau khởi động.
9. Bấm **Nhận quyền lái**. Mặc định cap80 và né TẮT. Thử DỪNG trước; thử từng bánh/hướng trên giá, rồi W+A/W+D/S+A/S+D và joystick. Nhả, chuyển tab, tắt WiFi trình duyệt, rút USB theo cách an toàn; kiểm chứng PWM0/watchdog. Không thử rút nguồn Jetson nóng để mô phỏng mạng.
10. Người thứ hai đăng nhập chỉ xem, chưa giành được quyền khi chủ còn giữ. Bấm Nhả quyền để bàn giao. Bất kỳ STOP rõ ràng từ người xem sẽ thu hồi chủ; chủ phải nhận quyền lại và giữ phím mới.
11. Trước thử sàn: đo thân, kiểm tra từng mắt/siêu âm và khoảng mù bằng vật khác nhau. Khi motor được cấp lại, giữ khu vực trống, có cách ngắt nguồn khẩn. Thử line/cua ở cap thấp trước, rồi né chậm ở hành lang rộng và vật đủ dễ đo. Khi xe LÁI TAY/STOP, chọn cap, tích xác nhận và tùy chọn bật né thực nghiệm, Áp dụng. Đợi ACK OK. Bật AUTO qua X/nút trên Web, không giữ lệnh lái tay khi AUTO.
12. Tăng cap80 →120 →160 →200 →255 chỉ sau các lượt đủ điều kiện. Cap áp dụng cả đầu ra line/cua khi USB sở hữu; ở cap255 không hạ các hằng số gốc. Ghi lại thời gian phản hồi, khoảng hở nhỏ nhất, lỗi, khả năng quay về A2/cua sau né. Chưa đạt thì quay lại mức thấp, không bỏ timeout/guard.

## Chia sẻ Web và điện thoại

Cùng WiFi/LAN: người khác mở cùng địa chỉ Jetson, đăng nhập rồi xem/nhận quyền khi được bàn giao. Điện thoại có nút và joystick; không có GPS/định vị thật. HTTP trong LAN không mã hóa mật khẩu Basic; chỉ dùng mạng thử tin cậy. Ngoài LAN dùng VPN hoặc reverse proxy HTTPS có cấu hình đúng, không chuyển tiếp trực tiếp cổng Flask 5000 ra Internet. Bản này chưa tự triển khai VPN/HTTPS trên xe.

Sau khi USB VECTOR1 đã nhận phiên, ESP cũ không được đồng thời chạy motor; ESP vẫn được STOP. Muốn vận hành độc lập bằng ESP cũ phải dừng, ngắt Jetson an toàn và khởi động lại Mega để bỏ quyền USB. Không đổi firmware ESP trong gói này. Nút vật lý 31 vẫn giữ chức năng cũ, nhưng AUTO trong phiên USB vẫn chịu watchdog host.

## Quay lại bản cũ

Đây là thay đổi cả giao thức: không chỉ đổi lệnh chạy Python.

1. DỪNG, Ctrl+C server mới, bảo đảm motor/nguồn an toàn như quy trình nạp.
2. Nạp lại firmware nguyên gốc `original_firmware/agv_mecanum_CUAXOAYNGANG/agv_mecanum_CUAXOAYNGANG.ino` hoặc đúng bản cũ bạn xác nhận đang dùng (nếu có sửa khác bản upload thì phải giữ bản đó riêng).
3. Khởi động lại kết nối USB; service vẫn dừng để tránh chạy trùng.
4. Chạy lại `AGV_PORT=/dev/ttyUSB0 python3 -u "$HOME/stream_server_reset_v1.py"` theo đường dẫn cũ, Ctrl+F5 Web.

Không trộn Python VECTOR1 với Mega cũ, SAFE1 với VECTOR1, hoặc chạy script patch_stream_v7.py. Gói này không sửa service/tự khởi động hay môi trường cũ.

## Kiểm chứng

Xem TEST_REPORT.md. Bản này đã build AVR, nhưng chưa nạp board, chưa thử bánh treo/sàn. Chỉ sau khi người vận hành kiểm tra thực tế mới chốt thông số né, cap và hiệu chuẩn. Không có cam kết sai số vị trí ≤1 m hoặc né thành công mọi vật ở tốc độ cao.
