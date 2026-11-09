# Sửa nút đặt lại điểm đầu — RESET V1

## Nguồn và phạm vi

Bản mới: `stream_server_reset_v1.py`, phiên bản `OXY_DRIVE_V7_RESET_V1`.
Nguồn là `stream_server.py` trên nhánh `backup/jetson-web-stable-2026-11-09`, commit `8d5319579cd4f6eaa80bad5f35852b52a4dd1e8f`.
SHA-256 nguồn: `ee951911931cb8ff9830e5c8a5badaac047634f0dcf3260afb2a4d0c91cb7273`.
Ba file Python gốc trong nhánh này được giữ nguyên byte. Chạy file mới riêng, không chép đè bản ổn định.

Lỗi tái hiện trên Chromium: nút cũ chỉ hiện form ở phía dưới khối hiệu chuẩn dài, ngoài vùng đang nhìn thấy. Người dùng chưa thấy form để xác nhận nên tọa độ chưa được đặt lại. Ngoài ra, server có thể từ chối khi thiếu xác nhận STOP/MOTION; bản mới hiển thị lý do ngay trong hộp thoại.

Bản sửa đưa form vào hộp thoại giữa màn hình; trả ngay trạng thái mới khi đặt lại thành công và chặn phản hồi telemetry cũ phục hồi tọa độ trước đó. Giữ nguyên điều kiện xác nhận dừng, thuật toán điều khiển, xử lý camera và firmware. Endpoint đặt lại không gửi lệnh USB.

Đây là tọa độ **ước lượng theo lệnh**, không phải phép đo vị trí xe. Đặt lại chỉ đổi mô hình; không đưa xe thật về gốc, không ngăn sai số tích lũy khi chạy tiếp. Nút “Về tâm bản đồ” chỉ đổi góc nhìn. Tải lại trình duyệt không xóa phiên đang nằm trên server.

## 1. Chép file mới từ Windows sang Jetson

1. Tải `stream_server_reset_v1.py` từ GitHub vào thư mục **Downloads** trên Windows. Kiểm tra tên file đúng, không có đuôi `.txt` hay `(1)`.
2. Đặt xe trên giá vững, bánh không chạm sàn; nhấn DỪNG và giữ chế độ LÁI TAY. Nguồn motor và Jetson dùng chung công tắc theo mô hình của bạn; không rút nguồn Jetson khi hệ điều hành đang chạy. Chưa thử chạy trên sàn trong bước thay file.
3. Trong VS Code, bấm mũi tên cạnh dấu **+** ở thanh Terminal, chọn **PowerShell** để mở terminal Windows mới. Terminal này phải hiện đầu dòng `PS C:\...>`; giữ nguyên terminal đang chạy web.
4. Chạy lệnh sau trong terminal Windows mới:

```powershell
scp "$env:USERPROFILE\Downloads\stream_server_reset_v1.py" nguyennhutoan_uav@192.168.1.71:/home/nguyennhutoan_uav/stream_server_reset_v1.py
```

Nhập mật khẩu tài khoản Jetson khi được hỏi (không hiện ký tự là bình thường). Lệnh này tạo file mới trong thư mục home; nếu đã có file cùng tên từ lần thử trước, giữ riêng bản đó trước khi chép.

## 2. Dừng bản cũ rồi chạy bản mới

1. Chọn lại terminal SSH đang in các dòng `GET /telemetry ...`. Nhấn **Ctrl+C** một lần để dừng tiến trình Python đang chạy tay. Đợi thấy đầu dòng `nguyennhutoan_uav@...:~$`.
2. Gõ **từng lệnh một** trong terminal Jetson đó:

```bash
sudo systemctl stop agv_server.service
```

Nhập mật khẩu sudo nếu được hỏi, rồi kiểm tra:

```bash
ss -ltnp 'sport = :5000'
```

Chỉ khi kết quả không có dòng `LISTEN` ở cổng 5000 mới chạy bản mới. Nếu vẫn có, dừng ở đây và gửi kết quả để xác định tiến trình; không mở thêm server tranh cổng/USB.

```bash
AGV_PORT=/dev/ttyUSB0 python3 -u "$HOME/stream_server_reset_v1.py"
```

Giữ terminal này mở. Đường dẫn USB dựa trên lần chạy ổn định của bạn; nếu đổi thành cổng khác phải kiểm tra lại. Không bật lại service song song.

3. Mở `http://192.168.1.71:5000`, nhấn **Ctrl+F5**. Có thể mở `http://192.168.1.71:5000/telemetry`, tìm `server_version`; phải là `OXY_DRIVE_V7_RESET_V1`.

## 3. Thử nút đặt lại

1. Đảm bảo xe thật đã đứng yên; chọn LÁI TAY và nhấn DỪNG. Xác nhận dừng trước mọi thử chạy.
2. Bấm **Đặt lại điểm đầu / phiên vẽ**. Hộp thoại phải xuất hiện ngay giữa màn hình.
3. Muốn quy ước vị trí hiện tại làm gốc: nhập X=0, Y=0, hướng=0° (hướng xe đang quay được quy ước là +X). Hoặc nhập mốc/hướng mà bạn đã biết. Đọc thông tin trạng thái trong hộp thoại.
4. Tích xác nhận sau khi kiểm tra xe thực, bấm **Xác nhận và đặt lại phiên**.
5. Khi thành công: X/Y về giá trị đã nhập, hướng theo giá trị đã nhập, quãng đường về 0 và vệt cũ được xóa; tuyến khai báo vẫn được giữ. Xe thật không được yêu cầu chuyển động bởi thao tác reset.
6. Nếu bị từ chối, hộp thoại giữ nguyên và báo lý do. Chụp/gửi nguyên dòng lỗi. Nếu báo thiếu `MOTION`, cần kiểm tra phản hồi firmware đang dùng; không tự ghép firmware khác hoặc bỏ kiểm tra dừng. PWM bằng 0 là trạng thái lệnh điện, không phải chứng minh có phanh cơ hoặc đo vận tốc bằng 0.

Nếu mở form nhưng không xác nhận, hoặc bấm Hủy/Escape, tọa độ không đổi. Khi chạy tiếp, tọa độ ước lượng vẫn có thể tích lũy sai số; bản sửa này không phải hệ thống định vị.

## 4. Quay lại bản đang chạy ổn

Trong terminal đang chạy file mới, nhấn **Ctrl+C**, đợi đầu dòng Jetson rồi chạy:

```bash
AGV_PORT=/dev/ttyUSB0 python3 -u "$HOME/stream_server.py"
```

Mở lại web và Ctrl+F5. File `stream_server.py`, `stream_server_STABLE.py`, `stream_server_CHUAN_GOC.py` không bị thay bởi quy trình này. Không cần nạp lại Mega. Bản mới chưa được cài tự khởi động; service hiện hữu không được sửa.

## 5. Kiểm chứng và giới hạn

- 8 unit test dùng Flask thật với serial/camera giả: reset, tọa độ tùy chọn, dữ liệu sai, các trạng thái không sẵn sàng, thiếu MOTION, chặn lệnh thế hệ cũ và cú pháp Python 3.6.
- 10 kiểm tra Chromium: hộp thoại desktop/điện thoại, hủy, bắt buộc xác nhận, cập nhật ngay, tải lại trang, telemetry cũ, server mới và bốn lý do từ chối. Không có lỗi JavaScript trong các lượt này.
- Endpoint reset không ghi USB trong các kiểm thử. Fixture trình duyệt chỉ mô phỏng STOP của vòng đời trang; không có thiết bị thật, không khởi động worker camera/serial.
- Chưa chạy trên Jetson, chưa thử bánh treo, chưa thử xe trên sàn. Không có build/nạp Arduino trong nhiệm vụ này.

Chạy lại kiểm thử trên máy có Flask, NumPy, Playwright và Chromium:

```bash
python3 -m unittest discover -s tests -p test_reset_origin.py -v
python3 tests/serve_reset_fixture.py
```

Giữ fixture ở terminal riêng rồi chạy `node tests/test_reset_ui.js`. Fixture chỉ nghe loopback cổng 18765, không dùng USB thật. Xem `reset_origin_v1.patch` để rà khác biệt so với nguồn ổn định; không cần áp dụng patch khi dùng file Python mới.
