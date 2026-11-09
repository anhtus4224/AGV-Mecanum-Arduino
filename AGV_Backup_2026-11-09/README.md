# AGV Backup — 09/11/2026

Bản sao từ workspace Codex “Thiết lập anh-tu”, không sửa thuật toán, pin hoặc dữ liệu gốc.

## Tải trên Windows

Trên trang repository chọn nhánh **backup-agv-2026-11-09**, chọn **Code → Download ZIP**, giải nén và mở thư mục `AGV_Backup_2026-11-09`.
Các `.ino`, `.cpp`, `.h`, `.py` và tài liệu được lưu thành file riêng, không chỉ nằm trong ZIP.

## Bản cần phân biệt

- `user_firmware_confirmed.ino`: baseline CUAXOAYNGANG người dùng gửi; giữ nguyên byte.
- `attachments/.../agv_mecanum_CUAXOAYNGANG.zip`: các upload nguyên gốc, vẫn giữ riêng provenance.
- `agv_web_safe1_final/`: bộ sửa giao tiếp SAFE1 đề xuất; **chưa có xác nhận nghiệm thu trên xe**. Không trộn Python SAFE1 với firmware ký tự cũ.
- `agv_motor_lock/`: sketch chỉ khóa motor, không phải firmware chạy tuyến.
- `PROJECT_CONTEXT.md`, `AGENTS.md`: bối cảnh và quy tắc bảo vệ dự án.
- `backup_audit_2026-11-09/VERSION_INVENTORY.md`, `BACKUP_REPORT.md`, `GITHUB_BACKUP_PLAN.md`: báo cáo lịch sử ở thời điểm trước nhiệm vụ publish này; câu “chưa push” trong các báo cáo đó là trạng thái lúc lập báo cáo, không phải trạng thái nhánh hiện tại.

## Kiểm chứng nguồn và các file không đưa lên

ZIP local gốc gồm 315 file, SHA-256 `dc86e66f00da8d0081f0b2d89ddb2e3b528e5677074e4bf0b2561bc64fca33c9`.
`FILE_MANIFEST.csv` liệt kê **cả 315 file**, byte, hash, INCLUDE/OMIT và lý do. Mọi file INCLUDE giữ nguyên byte. Không tự tái tạo file thiếu hoặc sửa code để ẩn bí mật.

Không publish `.git` của repo cũ, ID cấu hình runtime nội bộ, cache .pyc và binary ELF kiểm thử. Source tương ứng vẫn có. ZIP tổng 103,627,299 byte (~98.83 MiB) giữ local nguyên vẹn, không upload trùng vì chứa các mục đã loại và lặp dữ liệu; các ZIP phiên bản gốc phù hợp vẫn được đưa lên riêng.
Không có file được chọn vượt 100 MiB. Ảnh/video và các ZIP media được sao lưu nguyên byte; nội dung media chỉ là bằng chứng thử, không tự chứng minh code đã chạy thành công.
Không tự bật Git LFS hoặc tạo Release. Nếu bổ sung file >100 MiB trong tương lai, cần dùng LFS/Release thay vì commit thông thường.

`SECRET_SCAN_SUMMARY.json` ghi phạm vi rà credential/private key; không có literal credential được phát hiện. Không coi kiểm tra regex là bằng chứng tuyệt đối đối với mọi bí mật trong hình/video.
Receipt/SHA của ZIP tổng được giữ kèm để nhận diện nguồn, nhưng ZIP tổng không nằm trong bản Git này.

Đây là bản sao file dự án, không phải snapshot toàn bộ máy Codex, firmware đang nạp hoặc ổ đĩa Jetson/PC.
