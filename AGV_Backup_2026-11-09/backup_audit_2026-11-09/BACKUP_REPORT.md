# Báo cáo sao lưu AGV — 09/11/2026 (Asia/Saigon)

## Kết quả kiểm kê

- Workspace `/workspace` còn đọc được, môi trường đang running/connected đúng environment_id đã được chọn. Không thay/restart môi trường hoặc cập nhật cấu hình.
- 274 file dự án đầu vào, 120,008,365 byte (~114.45 MiB), không có lỗi đọc hoặc symlink trong phạm vi kiểm kê.
- 18 `.ino`, 3 `.h`, 0 `.c`, 11 `.cpp`, 23 `.py`, 19 `.zip`, 1 `.docx`, 10 `.txt`, 1 `.md` có trước nhiệm vụ; còn ảnh/video, JS, cache và binary.
- 19 ZIP và 1 DOCX kiểm tra đọc/CRC PASS. PASS CRC chỉ là nguyên vẹn container, không chứng minh thuật toán chạy đúng hoặc code biên dịch được.
- Xem VERSION_INVENTORY.md để phân biệt file có thật, chỉ có trong lịch sử và ngoài phạm vi truy cập. Không tạo lại source thiếu.
- CUAXOAYNGANG trích xuất trong `user_firmware_confirmed.ino` trùng SHA-256 với member `.ino` trong cả hai upload CUAXOAYNGANG.
- Giữ riêng baseline người dùng và đề xuất SAFE1; không đánh dấu SAFE1 đã thử xe.

## Tài liệu đã tạo

- `/workspace/PROJECT_CONTEXT.md`: kiến trúc, phần cứng/pin, thông số, bám line/xoay góc/né cản, lỗi và quyết định, nguồn bằng chứng và trạng thái kiểm thử.
- `/workspace/AGENTS.md`: quy tắc sửa tối thiểu, không đổi pin/ghi đè bản ổn định, phân biệt build/mô phỏng/xe thật và bảo toàn dữ liệu.
- `inventory.json`, `inventory.csv`, `SHA256SUMS.txt`: đường dẫn, kích thước, hash, thời gian sửa file theo UTC (không đồng nghĩa thời điểm triển khai).
- `archive_members.json`: danh sách member và kết quả kiểm tra các ZIP/DOCX hiện hữu.
- `VERSION_INVENTORY.md`, `GITHUB_BACKUP_PLAN.md`, `GITHUB_FILE_LIST.csv`.
- `git_readonly_checks.json`, `GITHUB_CONNECTIVITY.md`, `ENVIRONMENT_METADATA.json`.
- `recovered_tmp/` và `tmp_provenance.json`: chép nguyên byte 4 artifact kiểm thử final còn trong /tmp, không tái tạo source, không chạy chúng.
- `SOURCE_UNCHANGED_VERIFICATION.json`: so sánh byte nguồn và Git metadata trước khi đóng gói. Kết quả đối chiếu archive hoàn chỉnh ghi ở file receipt nằm cạnh ZIP.

## Git và khả năng push

- `/workspace`: không phải repository Git hoạt động (có thư mục `.git` bảo vệ nhưng các lệnh Git trả fatal).
- `/workspace/anh-tu`: branch unborn `work`, chưa có commit, không có file tracked/staged; `git branch -a` không in ref vì chưa có commit.
- Origin hiện tại: `https://github.com/anhtus4224/anh-tu.git`, khác repository đích `anhtus4224/AGV-Mecanum-Arduino`.
- `git ls-remote` repo đích thành công khi được phép dùng mạng ngoài sandbox; nhánh `main`/HEAD = `9745e3798e1aac03fdd48283b6dcdc72ea7deef8` tại lúc kiểm tra. Không fetch nội dung repo.
- GitHub CLI báo GH_TOKEN không hợp lệ; GET receive-pack discovery HTTP200 chỉ là truy cập endpoint, chưa đủ xác nhận quyền cập nhật ref/push.
- Không chạy git push (kể cả dry-run), add, commit, fetch, clone, reset, clean, đổi remote hay cấu hình. Không yêu cầu nhập token vào chat.

## Bản sao local và phạm vi

Bản sao đầy đủ được tạo mới dưới `/workspace/AGV_Mecanum_backup_2026-11-09.zip`; dữ liệu dùng cây `workspace/` trong ZIP. Receipt kết quả kiểm tra và SHA-256 của ZIP ở `/workspace/AGV_Mecanum_backup_2026-11-09.receipt.json` và `.sha256`.

Phạm vi: 274 file dự án có hash trước nhiệm vụ, hai tài liệu root mới, thư mục báo cáo/provenance mới và metadata repository `/workspace/anh-tu/.git` đọc được. Bao gồm video, ảnh và binary/cache để không làm mất dữ liệu local, dù không khuyến nghị đưa mọi thứ lên Git.

Không bao gồm các thư mục dành cho credentials/runtime được bảo vệ ở `.aws`, `.codex`, `.agents`, mount `.git` cấp workspace; không có snapshot OS, package/cache toàn hệ thống, thiết lập bí mật, export hội thoại hoàn chỉnh hay dữ liệu Jetson/PC/flash Mega. Không hứa giữ vĩnh viễn môi trường từ file ZIP này. Không thay đổi cấu hình môi trường để tạo snapshot.

## Rủi ro cần người dùng xem trước

1. **Chưa có bản sao ngoài môi trường:** code nằm ngoài repo và repo hiện tại không có commit. Archive local vẫn có thể mất cùng workspace nếu môi trường bị thu hồi/reset; cần tải ZIP về máy và lưu bản độc lập. Chưa push theo yêu cầu.
2. **Git nhầm repo:** đổi nhầm origin hoặc push từ thư mục sai có thể đưa dữ liệu sang anh-tu thay vì AGV-Mecanum-Arduino; chưa thực hiện.
3. **Nhầm “bản ổn định” với “bản mới”:** SAFE1 là đề xuất chưa nghiệm thu trên xe; phải giữ CUAXOAYNGANG và cả nguồn upload. Chat cuối có thể khác byte file đã ghi; không thay archive bằng mã gõ lại mà không diff.
4. **Thiếu file đang triển khai:** STABLE/CHUAN_GOC/.bak, systemd unit, tuning JSON và firmware ESP chưa truy cập; ảnh chụp không chứa toàn bộ file. Bản đang chạy trên Jetson/Mega cần backup riêng trong nhiệm vụ khác.
5. **Quyền push chưa xác nhận:** repo đọc được không đồng nghĩa được ghi. Không sửa token/cấu hình khi chưa được yêu cầu.
6. **Media và dữ liệu riêng tư:** video thử nghiệm có người/không gian riêng; DOCX/text/code có thể có IP/đường dẫn cá nhân. Không tự công khai. Video, ZIP tổng và cache không phù hợp đưa tràn vào lịch sử Git; cân nhắc media store/LFS/Release sau duyệt.
7. **Mất context:** PROJECT_CONTEXT là tóm tắt có nguồn, không thay toàn bộ cuộc trò chuyện. Metadata cấu hình chỉ nhận diện được môi trường, không bảo đảm có thể tái tạo đầy đủ runtime.
8. **Kiểm thử:** nhiệm vụ sao lưu không build/nạp/chạy xe. Dữ liệu test cũ không chứng minh sửa thành công trên phần cứng; code watchdog phụ thuộc phiên USB đúng và không thay nút cắt nguồn vật lý.

## Hành động thực tế trong nhiệm vụ này

Chỉ đọc dữ liệu/code/Git/kết nối, tạo tài liệu/manifest và bản sao mới. Không xóa file, không chỉnh thuật toán hay thông số, không nạp motor/board, không khởi động dịch vụ, không đổi môi trường hoặc push.
