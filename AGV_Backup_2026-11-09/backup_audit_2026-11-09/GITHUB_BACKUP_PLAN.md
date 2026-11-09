# Danh sách dự kiến sao lưu lên GitHub — CHƯA THỰC HIỆN

Đích do người dùng yêu cầu: `anhtus4224/AGV-Mecanum-Arduino`.
Danh sách từng file, byte và SHA-256: `GITHUB_FILE_LIST.csv`. P1/P2 là ưu tiên sao lưu, không phải chứng nhận firmware ổn định.

## P1 — tài liệu bối cảnh và các baseline

- `/workspace/PROJECT_CONTEXT.md`, `/workspace/AGENTS.md`.
- `backup_audit_2026-11-09/`: manifest, version inventory, báo cáo Git/kết nối, kế hoạch, provenance và test final lấy từ /tmp. Metadata môi trường chỉ lưu thông tin nhận diện, không chứa secret.
- `user_firmware_confirmed.ino`: baseline CUAXOAYNGANG người dùng gửi; giữ nguyên byte và nguồn ZIP, không ghi đè bởi SAFE1.
- Hai upload `attachments/0e46e922-4d28-46f1-bb8e-e23a831fec74/agv_mecanum_CUAXOAYNGANG.zip` và `attachments/fedc0c8a-15e0-4f69-96b6-2f0a674579cd/agv_mecanum_CUAXOAYNGANG.zip`: dù trùng hash, giữ provenance cả hai.
- `agv_web_safe1_final/`: `agv_serial_link.py`, `stream_server.py`, `agv_mega_safe/agv_mega_safe.ino`, `verify_link.py`, `install_server.py`, `HUONG_DAN.txt`; không đưa __pycache__. Đây là đề xuất mới chưa có xác nhận triển khai, không thay baseline cũ.
- `agv_motor_lock/agv_motor_lock/agv_motor_lock.ino`, test.cpp và `agv_motor_lock.zip` làm bản chẩn đoán dự phòng.

## P2 — lịch sử phát triển và kiểm thử

- Source/tài liệu trong `agv_delivery/`, `agv_delivery_v2/`, `agv_delivery_low/`, `agv_diagnostic/`, `agv_low_adc/`, `agv_smooth/`, `agv_corner90/`, `agv_chuandet90/`, `agv_chuandet90_v2/`.
- `agv_four_sensors/`: chỉ sketch kiểm tra/phương án khảo sát, ghi rõ chưa phải thiết kế cuối.
- Source, stub và script trong `agv_validation/`; source/test/original/fixed/chat trong `agv_connection_repair/`. Phân biệt bản chat với bản gốc; stub có include đường dẫn /workspace cần ghi nhận khi phục hồi, không tự sửa trong nhiệm vụ backup.
- Tất cả ZIP phiên bản AGV cấp workspace. Không tự hợp nhất code giữa các ZIP.
- Upload `agv_mecanum_chuan.zip`, cả hai `agv_mecanum_chuandet.zip`, `import os.docx`, hai `Văn bản đã dán.txt`: giữ local nguyên gốc; rà dữ liệu riêng tư trước khi đưa lên repo, đặc biệt nếu repo công khai.

## Media và file không ưu tiên Git

- Video gốc/phân tích trong `attachments/`, `agv_videos/`, `agv_turn_cal/`, `agv_failure_frames/`: giữ trong archive đầy đủ. Chọn giải pháp lưu video/LFS/Release sau khi duyệt, không tự thay `.gitattributes` hay cấu hình LFS.
- Không đưa `__pycache__`, `.pyc`, binary test host, credential, token, SSH key hoặc config cá nhân lên GitHub. Binary test vẫn có trong backup local để bảo toàn dữ liệu.
- Không đưa toàn bộ archive disaster-recovery khoảng 120 MB dữ liệu đầu vào vào Git như một file source; ưu tiên file nguồn và ZIP phiên bản nhỏ, media tách riêng.

## Tổ chức dự kiến, chưa di chuyển file

Giữ nguyên tên và cây thư mục để đối chiếu hash. Có thể duyệt một commit backup chứa tài liệu ở root và cây phiên bản hiện hữu. Chưa chọn lại remote, branch, hoặc thư mục checkout đích.
Repo hiện có `/workspace/anh-tu` đang trống commit và trỏ `anhtus4224/anh-tu`, không phải repo đích. Không tự tận dụng bằng cách đổi origin.

## Các dữ liệu còn thiếu, cần lấy từ máy thực tế trong nhiệm vụ riêng

- File unit systemd `agv_server.service`, server đang triển khai, `agv_tuning.json`, bản STABLE/CHUAN_GOC/.bak trên Jetson.
- Firmware ESP và sơ đồ dây/nguồn/EN của BTS7960 nếu có.
- Bản firmware thực sự đang nạp, log thử phần cứng và xác nhận version/hash.
- Lịch sử hội thoại đầy đủ/export nếu người dùng cần; PROJECT_CONTEXT không thay được transcript.

Không có file nào được git add/commit/push trong nhiệm vụ này. Danh sách này để người dùng xem trước, không phải lệnh cho phép xuất bản.
