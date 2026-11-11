# TEACH_TRACE_FIX1 — giữ lý do hủy lượt ghi

Nhánh `fix/teach-record-status-2026-11-12`, nền V4 commit5516da4858a2cbab15cf979709390dec5358ece7. Chỉ sửa3 file Jetson; firmware Mega/thuật toán né không đổi. Không cần Upload hay tắt nguồn để áp dụng.

Người dùng báo thử né V4 được, sau đó quay về bị chặn. Diagnostics ghi `valid:false`, `segments:1`, `seconds:2.547`, `link_events:[]`; reason chỉ còn “Chưa có đường hợp lệ”. Người dùng xác nhận đã thực hiện ít nhất một thao tác trong nhóm chuyển tab/cửa sổ, Nhả quyền hoặc Áp dụng PWM trong lúc ghi. Không có dữ liệu để phân biệt chính xác thao tác nào đã xảy ra đầu tiên. Link_events rỗng không loại trừ mất quyền/đổi cấu hình.

Lỗi mã xác định được: finish() ghi đè lý do invalidate trước đó. Sửa để giữ nguyên lý do đầu tiên và8 sự kiện gần nhất, có nhãn phiên bản `teach_return.revision=TEACH_TRACE_FIX1`. Chốt khi chưa bắt đầu ghi được báo riêng. Ghi một lượt mới xóa lỗi của lượt trước; không khôi phục đường đã hủy hoặc ép valid=true cho một đường dở.

Gateway phân biệt hết hạn quyền, đổi môi trường, đổi phiên vẽ, đổi lease và đổi chế độ. Snapshot đi kèm phản hồi vector/renew, không thêm lượt request vào vòng điều khiển. Web cập nhật số đoạn/thời gian/trạng thái khi lái hoặc đứng yên, khóa nút quay về nếu chưa chốt đường hợp lệ. Giữ nguyên các điều kiện STOP, lease/ticket/watchdog, cap, sonar và xoay180°; không tự tiếp tục sau hủy. Đây là sửa quan sát lỗi, không biến phép tích phân PWM thành định vị.

Áp dụng nếu muốn có thông báo rõ hơn:

1. DỪNG, Nhả quyền; Ctrl+C terminal server Jetson. Giữ nguồn.
2. Qua SSH FS thay đúng `agv_vector_gateway.py`, `teach_return.py`, `vector_controls.js` trong `/home/nguyennhutoan_uav/agv_vector_v1`. Không đổi tên thêm hàng loạt file. Các bản cũ có thể tải lại từ nhánh V4/commit nền.
3. Kiểm tra và khởi động:

   ```bash
   cd /home/nguyennhutoan_uav/agv_vector_v1
   python3 -m py_compile agv_vector_gateway.py teach_return.py
   python3 run_vector_v1.py
   ```

4. Web Ctrl+F5. Diagnostics có `teach_return.revision` như trên. Khởi động lại server mất đường RAM, phải ghi lượt mới.

Thử ngay bằng V4 cũ cũng được: về trang chính, giữ PWM200/né tắt/thời gian80 đã đo15.65. Hoàn tất Áp dụng và hiệu chuẩn trước lượt ghi. Nhận quyền → Đặt điểm đầu + ghi đường → đợi “Đang ghi…” → lái ngắn, thả/DỪNG → Chốt, đợi “Đã chốt đường ước lượng” → Quay180° và về. Trong cả chuỗi giữ nguyên trang/cửa sổ, quyền và cấu hình. DỪNG khi cần vẫn được; Nhả quyền/chuyển tab khi đang ghi hủy lượt, không thể ghép đường dở thành một lượt hoàn chỉnh. Chỗ xoay vẫn cần bốn tia hữu hạn đủ khoảng hở theo V4. Không dùng nút Bắt đầu ghi nhật ký thay cho Ghi đường lái tay.

Kiểm tra phần mềm:64 unit Python/Flask đạt, node --check đạt. Chromium với USB/cảm biến giả kiểm tra5 thao tác ghi, chốt, quay/lệnh đảo, vệt đỏ/xanh, mô hình gần gốc giả, STOP/blur; thêm ca hủy trong khi ghi, nhận quyền lại, chốt vẫn giữ nguyên lý do, nút quay về khóa. Một lượt browser trong môi trường dùng chung bị hết hạn lease0,8 giây và dừng; log mới giữ đúng lý do. Chạy tách biệt đạt cả ca hồi quy; không nới lease/watchdog để làm đạt. Chưa áp dụng bản vá hoặc thử quay về trên Jetson/xe thật từ Codex. Không rebuild AVR vì firmware nguyên byte so với nền.

## Tải file

- [agv_vector_gateway.py](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-record-status-2026-11-12/upgrade_v1/agv_vector_gateway.py)
- [teach_return.py](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-record-status-2026-11-12/upgrade_v1/teach_return.py)
- [vector_controls.js](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-record-status-2026-11-12/upgrade_v1/vector_controls.js)
- [Gói3 file ZIP](https://raw.githubusercontent.com/anhtus4224/AGV-Mecanum-Arduino/refs/heads/fix/teach-record-status-2026-11-12/AGV_TEACH_TRACE_FIX1_2026-11-12.zip)
- [ZIP toàn nhánh](https://github.com/anhtus4224/AGV-Mecanum-Arduino/archive/refs/heads/fix/teach-record-status-2026-11-12.zip)
