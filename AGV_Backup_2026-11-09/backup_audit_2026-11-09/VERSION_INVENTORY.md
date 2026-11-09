# Kiểm kê phiên bản AGV — 09/11/2026

Đường dẫn tương đối so với `/workspace`. Đây là kiểm kê dữ liệu hiện hữu, không tạo lại mã nguồn thiếu. Hash đầy đủ có trong `inventory.csv` và `archive_members.json`.

## Mã nguồn Arduino truy cập được

| File | Bytes | SHA-256 (12 ký tự đầu) | Phân loại |
|---|---:|---|---|
| `user_firmware_confirmed.ino` | 33313 | `38bdacb06152` | Bản trích xuất trùng byte với CUAXOAYNGANG người dùng gửi; không suy ra đang nạp trên xe |
| `agv_chuandet90/agv_chuandet90/agv_chuandet90.ino` | 32577 | `64f4ab703d97` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_chuandet90_v2/agv_chuandet90_v2/agv_chuandet90_v2.ino` | 34300 | `7be5615cbe9c` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_connection_repair/original.ino` | 33313 | `38bdacb06152` | Bản trích xuất trùng byte với CUAXOAYNGANG người dùng gửi; không suy ra đang nạp trên xe |
| `agv_connection_repair/chat/agv_mega_safe.ino` | 32744 | `1303975de927` | Bản định dạng để dán chat; không mặc định là bản gốc |
| `agv_connection_repair/fixed/agv_mega_safe/agv_mega_safe.ino` | 34879 | `9796f78671c3` | SAFE1 trước bản final; không trộn giao thức với firmware cũ |
| `agv_corner90/agv_corner90/agv_corner90.ino` | 32817 | `a1ec50313893` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_delivery/agv_mecanum_chuan/agv_mecanum_chuan.ino` | 30241 | `5300c60e5e32` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_delivery_low/agv_mecanum_190_v2_low/agv_mecanum_190_v2_low.ino` | 30666 | `5116af672677` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_delivery_v2/agv_mecanum_190_v2/agv_mecanum_190_v2.ino` | 30621 | `fa3cb7945b71` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_diagnostic/agv_190_diag/agv_190_diag.ino` | 32180 | `1a10771db31b` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_four_sensors/test_4_thanh/test_4_thanh.ino` | 1313 | `37d0925fc688` | Sketch kiểm tra 4 thanh; phương án khảo sát, không phải thuật toán chạy đã chốt |
| `agv_low_adc/agv_190_low_adc/agv_190_low_adc.ino` | 31382 | `a355a24d602f` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_motor_lock/agv_motor_lock/agv_motor_lock.ino` | 819 | `c9aefe198377` | Chỉ khóa PWM; người dùng xác nhận bánh đứng yên khi dùng sketch khóa |
| `agv_smooth/agv_mecanum_smooth/agv_mecanum_smooth.ino` | 28949 | `3d1e361f0693` | Phiên bản lịch sử còn tồn tại; tên file không chứng minh đã chạy thực tế |
| `agv_validation/current250.ino` | 31340 | `7ed792ace011` | Bản phục vụ phân tích/kiểm thử; không mặc định firmware đang triển khai |
| `agv_validation/reuploaded_chuandet.ino` | 31340 | `7ed792ace011` | Bản phục vụ phân tích/kiểm thử; không mặc định firmware đang triển khai |
| `agv_web_safe1_final/agv_mega_safe/agv_mega_safe.ino` | 35226 | `a4d7bcac9b03` | Đề xuất SAFE1 cuối trong workspace; chưa có xác nhận thử xe sau triển khai |

## ZIP và DOCX hiện hữu

| File | Trạng thái cấu trúc/CRC | Mã Arduino bên trong |
|---|---|---|
| `agv_190_diagnostic.zip` | PASS | `agv_190_diag/agv_190_diag.ino` |
| `agv_190_low_adc.zip` | PASS | `agv_190_low_adc/agv_190_low_adc.ino` |
| `agv_chuandet90_v1.zip` | PASS | `agv_chuandet90/agv_chuandet90.ino` |
| `agv_chuandet90_v2.zip` | PASS | `agv_chuandet90_v2/agv_chuandet90_v2.ino` |
| `agv_corner90_v1.zip` | PASS | `agv_corner90/agv_corner90.ino` |
| `agv_mecanum_190_v2.zip` | PASS | `agv_mecanum_190_v2/agv_mecanum_190_v2.ino` |
| `agv_mecanum_190_v2_low.zip` | PASS | `agv_mecanum_190_v2_low/agv_mecanum_190_v2_low.ino` |
| `agv_mecanum_chuan_190_fix.zip` | PASS | `agv_mecanum_chuan/agv_mecanum_chuan.ino` |
| `agv_mecanum_smooth.zip` | PASS | `agv_mecanum_smooth/agv_mecanum_smooth.ino` |
| `agv_motor_lock.zip` | PASS | `agv_motor_lock/agv_motor_lock.ino` |
| `agv_safe1_repair.zip` | PASS | `agv_safe1/agv_mega_safe/agv_mega_safe.ino` |
| `agv_web_safe1_final.zip` | PASS | `agv_web_safe1_final/agv_mega_safe/agv_mega_safe.ino` |
| `attachments/0e46e922-4d28-46f1-bb8e-e23a831fec74/agv_mecanum_CUAXOAYNGANG.zip` | PASS | `agv_mecanum_CUAXOAYNGANG/agv_mecanum_CUAXOAYNGANG.ino` |
| `attachments/37792c73-fe46-4489-a46e-06b7ec446657/dò line.zip` | PASS | Không có .ino; media hoặc tài liệu |
| `attachments/4e5ee266-d085-4b56-bdd9-3bb08cf6dd33/Robot Travels a Magnetic Line by SuperDroid Robots - YouTube - Cốc Cốc 2026-11-02 21-54-55.zip` | PASS | Không có .ino; media hoặc tài liệu |
| `attachments/6fc5d25f-63c8-45fe-9cd9-c2ca1b9b003e/import os.docx` | PASS | Không có .ino; media hoặc tài liệu |
| `attachments/b5273a60-93a9-4910-a234-3976eaa8eef9/agv_mecanum_chuandet.zip` | PASS | `agv_mecanum_chuandet/agv_mecanum_chuandet.ino` |
| `attachments/b6d38020-c321-402a-93d9-965daf2efc39/agv_mecanum_chuandet.zip` | PASS | `agv_mecanum_chuandet/agv_mecanum_chuandet.ino` |
| `attachments/e18214f3-2888-4858-a7f2-e7fa06f2bb1b/agv_mecanum_chuan.zip` | PASS | `agv_mecanum_chuan/agv_mecanum_chuan.ino` |
| `attachments/fedc0c8a-15e0-4f69-96b6-2f0a674579cd/agv_mecanum_CUAXOAYNGANG.zip` | PASS | `agv_mecanum_CUAXOAYNGANG/agv_mecanum_CUAXOAYNGANG.ino` |

## Đối chiếu bản người dùng chốt

SHA-256 của `user_firmware_confirmed.ino`: `38bdacb061529c72d6bff7b62f23e8799bea17d0b20a547583e0b4eaa2a44e2c`.
- Trùng byte với `attachments/0e46e922-4d28-46f1-bb8e-e23a831fec74/agv_mecanum_CUAXOAYNGANG.zip::agv_mecanum_CUAXOAYNGANG/agv_mecanum_CUAXOAYNGANG.ino`.
- Trùng byte với `attachments/fedc0c8a-15e0-4f69-96b6-2f0a674579cd/agv_mecanum_CUAXOAYNGANG.zip::agv_mecanum_CUAXOAYNGANG/agv_mecanum_CUAXOAYNGANG.ino`.

Các bản `agv_chuandet90_v2/...ino`, `CUAXOAYNGANG` và SAFE1 có hash riêng; không tự gọi chúng là cùng một file dù liên quan về thuật toán.

## Chỉ được nhắc trong lịch sử, chưa tìm thấy file độc lập trong workspace

| Tên/đường dẫn được nhắc | Bằng chứng và trạng thái |
|---|---|
| `stream_server_STABLE.py` | Có tên trong ảnh VS Code trước đây; chưa tìm thấy file hay member ZIP cùng tên. |
| `stream_server_CHUAN_GOC.py` | Có tên trong ảnh; chưa tìm thấy file hay member ZIP cùng tên. |
| `stream_server.py.bak` | Có tên trong ảnh; chưa tìm thấy bản này. |
| `agv_mega_controller.ino` trong `agv_workspace/arduino_firmware` | Có trong ảnh Jetson; không tìm thấy cùng tên ở workspace/ZIP. Không coi CUAXOAYNGANG là bản thay thế nguyên gốc. |
| `/etc/systemd/system/agv_server.service` | Chỉ ảnh/trò chuyện cho thấy dịch vụ; chưa có file unit gốc tại workspace. |
| `/home/nguyennhutoan_uav/agv_tuning.json` | Đường dẫn có trong server; chưa có file cấu hình thực tế để sao lưu. |
| Firmware ESP8266 và cấu hình driver thực tế | Có nhắc giao tiếp ESP; chưa tìm thấy nguồn ESP có thể nhận diện chắc chắn. |

## Ngoài khả năng truy cập của lần kiểm kê này

- Bộ nhớ flash đang nạp trên Mega, ổ đĩa Jetson/PC, bản server thực tế đang chạy và các file trong ảnh không được tự động truy cập qua ảnh.
- Mã trong khung chat không tự trở thành file. Các đoạn được gõ lại ở cuối câu trả lời có thể khác file đã ghi trong workspace; chỉ file có hash trong manifest được xem là byte đã sao lưu.
- Không xuất được toàn bộ lịch sử hội thoại/UI hoặc snapshot cấu hình Codex chỉ bằng các file dự án. PROJECT_CONTEXT.md là bản ghi theo bằng chứng, không phải bản chép đầy đủ hội thoại.
- Không có lỗi đọc ở 274 file trong phạm vi đã kiểm kê. Các thư mục `.git`, `.aws`, `.codex`, `.agents` được loại khỏi manifest dữ liệu dự án; không suy ra dữ liệu ẩn trong đó đã được sao lưu.

## Kiểm thử tạm còn truy cập được

Các file `/tmp/test_safe1_final.cpp`, `/tmp/test_safe1_final.py`, `/tmp/safe1_final_js.js` và binary `/tmp/test_safe1_final` đã được chép nguyên byte vào `recovered_tmp/`; xem `tmp_provenance.json`. Đây là bản sao có ghi nguồn, không phải file tái tạo.
