# AGENTS.md — quy tắc dự án AGV Mecanum

## Phạm vi và nguồn sự thật

- Đọc PROJECT_CONTEXT.md và inventory trước khi sửa. Phân biệt bằng chứng trong file, báo cáo người dùng, giả lập và giả thuyết.
- Trong nhiệm vụ SAO LƯU: chỉ đọc code/Git; chỉ tạo tài liệu/manifest/bản sao mới được yêu cầu. Không sửa thuật toán, build/run code AGV, nạp board, điều khiển xe, xóa file hay đổi cấu hình môi trường.
- Không coi tên `final`, `chuandet` hoặc chữ “PASS” là chứng nhận thử trên xe. Không tạo lại file thiếu rồi gọi là bản gốc; ghi rõ nguồn, hash và tình trạng không truy cập.

## Phần cứng và thuật toán

- Không tự ý đổi chân Mega, dấu motor, thứ tự OUT, LINE_DETECTED, baudrate, servo hoặc mapping BTS7960. Chỉ đổi khi có yêu cầu rõ và bằng chứng đấu dây/thử từng kênh.
- Khi chỉ cần sửa giao tiếp/web hoặc một lỗi nhỏ, sửa tối thiểu; không viết lại toàn bộ bám line, xoay góc và né cản. Giữ nguyên thông số đã chốt trừ khi nhiệm vụ cho phép hiệu chỉnh.
- Không ghi đè bản người dùng xác nhận ổn định. Tạo phiên bản/nhánh riêng khi được phép, lưu diff và cách quay lại. Không chạy script sinh/patch cũ một cách tự động.
- Phân biệt firmware ký tự cũ và giao thức SAFE1; không ghép Python SAFE1 với firmware cũ. Kiểm tra cả nhận lệnh trong vòng né/servo và xung đột nhiều nguồn USB/ESP.
- PWM0 là lệnh điện; không khẳng định xe đứng ngay lập tức hoặc có phanh cơ. PWM255 không phải vận tốc đo được. Không công bố tọa độ/quỹ đạo tích phân lệnh là vị trí thực tế.

## Xác minh

- Báo riêng: kiểm tra cú pháp host g++/stub, unit test/mô phỏng, biên dịch Arduino AVR, nạp board, thử bánh treo và thử xe trên sàn.
- Không gọi g++ với Arduino giả lập là build Mega thành công. Không gọi mô phỏng PASS là đã sửa hoàn toàn trên xe.
- Không nạp/chạy motor hoặc khởi động dịch vụ điều khiển khi chưa thuộc phạm vi người dùng yêu cầu. Khi thử thực tế cần trình tự nguồn motor tắt, đúng firmware/giao thức, một tiến trình sở hữu USB, rồi thử dừng trước khi chạy trên sàn.
- Không sửa/xóa test hoặc thay đổi ngưỡng để làm báo cáo PASS. Ghi rõ điều gì chưa kiểm chứng.

## Dữ liệu, Git và môi trường

- Không `git reset`, `git clean`, force push, xóa file, thay thế môi trường hay thay remote nếu không có chỉ dẫn rõ. Trong nhiệm vụ backup hiện tại không add/commit/push/fetch/clone hoặc sửa Git config.
- Không nhầm `/workspace` với repo `/workspace/anh-tu`; kiểm tra pwd/status/remote/branch trước thao tác Git.
- Giữ bản gốc ZIP/DOCX/upload nguyên byte; dùng SHA-256 để nhận diện. Tên giống nhau nhưng hash khác phải giữ phân biệt.
- Không đưa token, mật khẩu, SSH key, file credentials hoặc cấu hình riêng tư lên GitHub; không in giá trị bí mật vào log. Lưu video lớn ở backup riêng/LFS/Release sau khi người dùng quyết định, không tự bật LFS.
- Không tự kết luận có quyền push từ HTTP200 hay git ls-remote. Không push thử để kiểm tra quyền khi người dùng cấm push.
- Không hứa giữ vĩnh viễn môi trường/chats từ một ZIP. Tách backup file dự án, metadata môi trường, dữ liệu Jetson/PC và lịch sử hội thoại.
