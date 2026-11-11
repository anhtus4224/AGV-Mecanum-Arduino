# AGENTS.md — quy tắc dự án AGV Mecanum

## Triển khai có người vận hành (11/11/2026)

- Dùng hướng dẫn `docs/TRIEN_KHAI_TOUCH_VECTOR_V2.md` cho gói dc1092c62572b3ec2ac7c13fde3014ec392b23e0 và ngữ cảnh bàn giao hiện tại.
- Trong chat triển khai: một bước nhỏ mỗi lần, ghi rõ terminal PC/Jetson và chỗ bấm, đợi kết quả/ảnh sau bước quan trọng. Xem dấu nhắc để xác nhận SSH; không coi tên tab JETSON là bằng chứng. Không yêu cầu chạy lại bước đã xác nhận xong.
- Xác minh trạng thái nguồn và xe kê chắc trước hướng dẫn bật/chạy; công tắc tổng cấp cả Jetson/Mega/motor. Áp dụng trình tự shutdown trong hướng dẫn, không tự đổi dây hoặc suy ra nguồn motor đã cách ly. Không yêu cầu bí mật trong chat.

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


## Quy trình xuất thành phẩm lên GitHub cho các nhiệm vụ tiếp theo

Quy tắc này được người dùng yêu cầu lưu ngày 09/11/2026. Đây là hướng dẫn trong file dự án, không phải cam kết ghi nhớ vĩnh viễn hoặc bảo đảm lưu toàn bộ hội thoại.

- Giữ nguyên môi trường Codex “Thiết lập anh-tu”, dữ liệu dự án gốc, các bản sao lưu và firmware ổn định. Không xóa/thay thế môi trường, thao tác xóa hội thoại hoặc tự thay cấu hình môi trường để xuất file. Không khẳng định đã sao lưu hội thoại nếu chưa có bản export có thể kiểm chứng.
- Từ nhiệm vụ tiếp theo, khi người dùng yêu cầu tạo hoặc sửa thành phẩm, mặc định ưu tiên xuất thành phẩm lên repository `anhtus4224/AGV-Mecanum-Arduino`, trừ khi người dùng yêu cầu chỉ làm cục bộ hoặc cấm commit/push trong nhiệm vụ đó. Không tự xuất thêm CUAXOAYNGANG, SAFE1 hoặc phiên bản khác chỉ vì thiết lập quy trình này.
- Lưu thành file thật, đúng cấu trúc định dạng yêu cầu: `.ino`, `.h`, `.cpp`, `.py`, `.zip`, `.docx` và các định dạng phù hợp khác. Không thay file bằng ảnh/chữ trong chat hoặc chỉ đổi phần mở rộng để giả định dạng.
- Dùng nhánh phiên bản mới, có tên phản ánh thành phẩm và phiên bản/ngày. Không ghi đè `main`, nhánh `backup-agv-2026-11-09`, các nhánh phiên bản đã tồn tại hoặc firmware ổn định; không force push. Giữ nguyên bản gốc, thực hiện thay đổi được yêu cầu trong bản làm việc riêng.
- Dùng checkout riêng của repository đích khi cần. Không đổi remote cũ `anhtus4224/anh-tu`; kiểm tra đúng thư mục, repository và nhánh trước thao tác Git. Các hạn chế chỉ đọc ghi ở nhiệm vụ backup ban đầu không tự biến thành lệnh cấm xuất bản cho mọi nhiệm vụ tương lai; vẫn tuân thủ giới hạn cụ thể của nhiệm vụ đang làm.
- Ưu tiên cơ chế xác thực GitHub chính thức/sẵn có của Codex hoặc kết nối GitHub đang hoạt động. Không yêu cầu người dùng gửi token trong chat, không in giá trị credential và không tự thay cấu hình môi trường/remote để vượt lỗi xác thực. Git push và API tạo PR có thể có khả năng truy cập khác nhau; báo đúng lỗi từng kênh.
- Trước commit, rà mật khẩu, token, private key, thông tin đăng nhập WiFi và bí mật Jetson trong phạm vi xuất bản, kể cả nội dung ZIP/DOCX khi có. Kiểm tra kích thước từng file; không commit file vượt 100 MiB bằng Git thông thường. Đề xuất LFS/Release khi cần, không tự cấu hình nếu chưa được phép. Báo rõ file bị loại và lý do; không âm thầm bỏ file hoặc sửa bản gốc để che thông tin.
- Commit/push trên đúng nhánh phiên bản, rồi đọc lại dữ liệu từ GitHub bằng một lần truy cập độc lập. Đối chiếu commit SHA, đường dẫn, số lượng và nội dung/hash file thành phẩm; không coi commit cục bộ hoặc thông báo đã chuẩn bị là xuất bản thành công. Không sửa thuật toán/pin ngoài phạm vi nhiệm vụ để hoàn tất xuất file.
- Sau khi push và xác minh thành công, trả đủ ba loại liên kết GitHub thực tế: **(1)** xem file/thư mục thành phẩm; **(2)** tải từng file thành phẩm trực tiếp; **(3)** tải ZIP toàn bộ nhánh phiên bản. Kèm nhánh và commit SHA. Với nhiều thành phẩm, cung cấp các link tải riêng tương ứng hoặc danh sách rõ ràng; không chỉ đưa link `/workspace` hay `sandbox` làm cách tải duy nhất.
- Nếu người dùng yêu cầu PR thì thử tạo PR riêng, không tự merge. Chỉ gọi là PR đã tạo khi có URL PR thật; liên kết mở form “Create pull request” không phải PR đã tạo. Nếu push thành công nhưng PR bị chặn, báo riêng hai kết quả và cung cấp cách mở form PR trên GitHub.
- Nếu không push được hoặc đọc lại file thất bại, báo lỗi thực tế, bước đã hoàn tất/chưa hoàn tất và cách cấp quyền qua giao diện GitHub/Codex khi phù hợp. Không nói đã hoàn thành xuất bản hoặc cung cấp URL thành phẩm như thể đã xác minh khi chưa làm được.
- Trong lượt thiết lập quy trình ngày 09/11/2026: chỉ bổ sung AGENTS.md cục bộ, không tạo nhánh, không commit/push, không sửa thuật toán. Khi người dùng yêu cầu đồng bộ AGENTS.md về sau, đề xuất/tiến hành theo phạm vi được cấp: nhánh tài liệu mới trên repository đích, chỉ diff quy tắc cần bổ sung, giữ nguyên quy tắc hiện hữu, không thay bản AGENTS.md lưu trong snapshot backup, mở PR nếu được yêu cầu; không tự merge.
