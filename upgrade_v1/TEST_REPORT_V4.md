# Kiểm tra V4 — 11/11/2026

Phạm vi: sửa điều kiện/chuyển pha né VECTOR1 và thêm ghi/quay về đường lái tay thử nghiệm. Bản nền V3:195a15d65fa2c8f09ecce0dfd75e4dfa709afd82. Không sửa pin, polarity, góc servo, baud hoặc thuật toán line/corner cũ.

| Lớp kiểm tra | Kết quả / giới hạn |
|---|---|
| Python3 / Flask unit | 61 bài đạt; gồm kiểm tra bảo toàn nguồn cũ, lease/ticket/thứ tự lệnh, API, giới hạn ghi, đảo thứ tự và dấu quay, pause không hủy lượt về, STOP hủy request chạy về đến trễ, mất kết nối/chế độ/cap/phiên, guard theo hướng/tuổi từng tia |
| Cú pháp | py_compile3 module Python, node --check JS, git diff --check đạt |
| C++ host stub | 8 chương trình đạt với g++17, Wall/Wextra/Werror; không phải build Mega. Chọn trái/mirror tại5 cap, phía đối diện25 cm, bên chọn999 và chéo hợp lệ, dạt PWM0 chưa được sang PASS, khoảng hở/inset, cạnh/thời gian thân, RETURN/IR, serial STOP/watchdog, sonar24 ms, 50 case chiều/cap và8 chânPWM |
| Chromium + USB/cảm biến giả | 6 kiểm tra điều khiển cơ bản đạt; bài ghi5 thao tác W/D/A/D/W, chốt, quay theo thời gian, đảo đường, vệt đỏ/xanh lam, mô hình về gần gốc giả, chặn chen lệnh tay và blur hủy đạt; không phải xe thực |
| Chromium giả lập độ trễ mạng | Lượt chạy tách biệt đạt16 kiểm tra, không lỗi JS/không vector bị từ chối ngoài tình huống hủy chủ động; khoảng giữa vector lớn nhất247 ms. Hai lượt trước có gói quá hạn304/510 ms và đóng điều khiển đúng ngưỡng300 ms; không nới watchdog/ticket để làm đạt. Bản nền V3 cũng được đối chiếu riêng, đạt16 kiểm tra trong lượt đó. Mạng/CPU thực có thể làm dừng khi quá hạn |
| Arduino AVR thật | AVR core1.8.3, avr-g++/ATmega2560, không dùng Arduino stub. ELF/HEX tạo được; flash30620 byte, RAM tĩnh2655 byte. IDE có thể khác kích thước theo toolchain/LTO |
| Nạp Mega / thử bánh / thử sàn V4 | Chưa thực hiện. Không truy cập cổng USB, không điều khiển motor hoặc khởi động server điều khiển xe thật từ Codex |

Các test FSM cũ được cập nhật vì yêu cầu thay đổi: không còn kỳ vọng chuyển PASS ngay sau một tia nền xa hoặc dừng do rear999 khi xe chỉ tiến/dạt. Các kiểm tra mixer không đổi; kiểm tra FSM đầy đủ nằm trong test_directional_avoid.cpp, chạy cả hai phía ở cả5 cap.

Chưa hiệu chuẩn trên xe: inset từng đầu bên, gain dạt18 cm/s và tiến23,6 cm/s ở PWM255, thời gian quay180° tạiPWM80, mức trượt/tải/pin, vùng mù/bề rộng vật cản. Các giá trị quãng đường và hướng chốt sau quay là ước lượng. Không có encoder/IMU trong mã hiện tại. Điểm cuối phải có chỗ xoay; đoạn quay yêu cầu4 tia hữu hạn đủ khoảng hở, tịnh tiến dùng guard theo hướng đang đi.

Đường ghi lưu trong RAM, giới hạn10 phút/6000 đoạn; không tự tiếp tục sau hủy/khởi động lại. Một lượt phát hết lệnh không chứng minh đã về đúng điểm trên sàn. Các sensor rời rạc không chứng minh toàn bộ vùng quét thân xe trống.

PROJECT_CONTEXT.md và inventory không có trong checkout; không tái tạo rồi gọi là dữ liệu gốc. Cấu hình phần cứng dựa trên nguồn và các xác nhận người dùng, ghi trong DIRECTIONAL_AVOID_TEACH_V4.md.
