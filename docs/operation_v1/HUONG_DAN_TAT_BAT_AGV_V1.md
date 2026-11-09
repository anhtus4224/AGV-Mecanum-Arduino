# CHECKLIST TẮT, ĐỔI NGUỒN VÀ KHỞI ĐỘNG AGV — V1

Ngày 09/11/2026 · Dành cho cấu hình người dùng đã xác nhận: Jetson và động cơ dùng chung công tắc; Jetson nhận 5 V qua bộ hạ áp từ ắc quy.

Tài liệu thao tác, không thay đổi code/firmware, pin Arduino, cấu hình dịch vụ hoặc môi trường Codex. Địa chỉ IP và tên cổng USB phải đối chiếu lại sau mỗi lần khởi động.

## 1. Đánh giá ảnh web hiện tại

- Quan sát được: dashboard mở, có khung hình camera, nhãn USB (ttyUSB0). Đây là dấu hiệu server và kết nối USB đã lên; không chứng nhận đầy đủ tính năng điều khiển/dừng hoặc cảm biến trên xe.
- Camera báo OBSTACLE 100% / Risk 40%: các chỉ số xử lý ảnh, không phải phép đo khoảng cách hay độ tin cậy đã hiệu chuẩn. Chưa thể kết luận đó là lỗi từ một ảnh.
- Siêu âm trước và sau hiện “Không có echo”: không nhận được phản hồi ở mẫu đó. Khi LÁI TAY và STOP, thử mặt phẳng phản xạ cách khoảng 20–40 cm, đúng hướng cảm biến. Nếu vẫn luôn không có echo, kiểm tra nguồn/dây/hướng và log; chưa kết luận cảm biến hỏng từ ảnh.
- Năm mắt line đều tắt: tương ứng không thấy vạch theo dữ liệu giao diện. Bình thường nếu thanh đang trên nền trắng; nếu vạch thực nằm dưới mắt mà vẫn tắt thì cần kiểm tra riêng. Camera nhìn thấy line không có nghĩa thanh gầm đang nằm trên line.
- Bản đồ màu xanh dương 2 × 3 m là tuyến khai báo. Vệt, tọa độ, hướng và quãng đường đang được ghi rõ là ước lượng từ lệnh/PWM; không phải vị trí thực đo được. Vận tốc mô hình 0 không đủ để khẳng định motor đang nhận PWM0; phải quan sát bánh thực tế.

## 2. Các quy tắc thao tác nguồn

- Vì dùng chung công tắc, không yêu cầu “tắt riêng động cơ nhưng vẫn giữ Jetson chạy”. Khi hệ thống còn cấp nguồn, động cơ cũng có thể được cấp nguồn; kê xe chắc chắn để bốn bánh không chạm sàn khi kiểm tra kết nối/khởi động.
- Khi tắt bình thường: DỪNG + LÁI TAY, dừng server, shutdown Jetson, chờ, rồi mới tắt công tắc tổng/rút nguồn.
- Khi bật: dây được cắm đúng trong lúc nguồn tắt, kiểm tra không cấp đồng thời adapter và ắc quy, bật tổng với xe được kê, kết nối SSH, kiểm tra server/USB/STOP, rồi mới thử chạy.
- Nguồn ắc quy phải qua bộ hạ áp đúng 5 V, đúng cực tính đầu cắm và đủ dòng theo board Jetson/camera/USB thực tế. Không nối trực tiếp 12 V vào đầu vào 5 V; không tăng điện áp tùy ý để bù sụt áp.
- Không rút/cắm dây nguồn motor, đầu ắc quy trần, hoặc sửa dây khi đang cấp điện. Tránh nguồn USB khác cấp ngược khi tưởng mô hình đã tắt.
- Nếu xe chuyển động ngoài ý muốn và không dừng được bằng điều khiển, ưu tiên cắt công tắc tổng để ngăn chuyển động; đây là dừng khẩn, không phải quy trình shutdown bình thường. Không chờ SSH trong tình huống đó.

## 3. Tắt mô hình đang chạy bằng ắc quy

1. Dừng thao tác giữ phím/nút trên web. Nhấn DỪNG, xác nhận chế độ LÁI TAY và quan sát bánh dừng. Người còn lại cũng phải ngừng điều khiển.
2. Lưu những file thực sự muốn giữ trong VS Code; chờ lưu qua SSH FS hoàn tất. Nếu đang ghi nhật ký trên web, dừng ghi và tải nhật ký cần giữ trước khi tắt server.
3. Tại terminal Jetson đang chạy server thủ công, nhấn Ctrl + C. Chờ trở lại dấu nhắc Linux. Không đóng nguồn chỉ vì web đã ngừng mở được.
4. Trong terminal Jetson chạy lần lượt:

```bash
sudo systemctl stop agv_server.service
systemctl is-active agv_server.service
ss -ltnp 'sport = :5000'
```

Kỳ vọng: dịch vụ inactive, cổng 5000 không có LISTEN. Nếu dịch vụ không tồn tại nhưng server thủ công đã dừng và cổng trống thì có thể tiếp tục. Nếu cổng vẫn LISTEN, xác định terminal/tiến trình đang chạy; không chạy thêm server hay tự kill mọi tiến trình Python.

5. Tắt hệ điều hành bằng:

```bash
sudo shutdown -h now
```

SSH bị đóng và SSH FS báo Not connected là bình thường trong quá trình tắt. Việc SSH ngắt riêng lẻ chưa chứng minh nguồn điện đã tắt.

6. Chờ khoảng 60 giây sau lệnh shutdown. Đèn nguồn có thể vẫn sáng khi 5 V còn được cấp.
7. Tắt công tắc tổng của mô hình. Khi đó cả motor và nguồn qua hạ áp tới Jetson đều ngừng được cấp từ ắc quy.
8. Nếu chỉ cất xe rồi dùng lại cùng bộ dây, có thể giữ các dây đúng vị trí. Nếu cần tháo: khi nguồn đã tắt, rút cáp USB có khả năng cấp điện từ laptop/thiết bị khác; rút USB Jetson–Mega nếu cần; sau đó tháo đầu nguồn 5 V/các đầu nối tháo rời cần thiết. Không tháo dây motor khi còn điện. Không cần tháo camera mỗi lần.

## 4. Đổi từ adapter sang ắc quy 5 V

1. DỪNG + LÁI TAY, dừng server và shutdown Jetson như mục 3; chờ khoảng 60 giây. Công tắc tổng ắc quy phải OFF; không giả định motor có nguồn riêng.
2. Rút USB tới nguồn bên ngoài nếu có, rút USB Jetson–Mega trong lúc đổi nguồn nếu cần tách hai thiết bị. Rút đầu adapter khỏi Jetson; không chỉ rút adapter khỏi ổ điện rồi để đầu cấp nguồn không rõ trạng thái.
3. Kiểm tra đầu ra bộ hạ áp là 5 V đúng cực tính, đúng đầu cắm và đủ dòng. Thực hiện phép đo khi bộ hạ áp chưa nối vào Jetson nếu cần; sau đó ngắt nguồn bộ hạ áp trước khi cắm đầu ra vào Jetson.
4. Khi công tắc tổng OFF và adapter đã tách, cắm đầu ra 5 V vào đúng cổng nguồn đang dùng của Jetson. Cắm chắc USB Mega và camera vào vị trí đã dùng; không tự chuyển sang cấp GPIO hoặc đổi pin phần cứng.
5. Kê xe chắc chắn, bật công tắc tổng và làm mục 5. Không cắm đồng thời adapter và nguồn ắc quy vào Jetson.

Đổi ngược từ ắc quy sang adapter: shutdown, chờ, tắt tổng, tách đầu ra bộ hạ áp khỏi Jetson rồi mới cắm adapter phù hợp. Giữ nguồn motor từ ắc quy OFF trong lần kiểm tra bằng adapter nếu việc đấu nguồn hiện tại cho phép; không tự đấu lại dây để tạo chế độ này.

## 5. Khởi động lại mô hình

1. Công tắc tổng OFF, adapter không còn cấp nguồn. Kiểm tra dây 5 V, USB Mega, camera và các đầu nối đã cắm chắc. Giữ nguyên sơ đồ đang dùng, không chạy patch/nạp lại Arduino chỉ để bật máy.
2. Kê xe để bánh không chạm sàn. Bật công tắc tổng; cả Jetson và motor có thể có nguồn ngay.
3. Chờ khoảng 1–2 phút để Jetson khởi động và vào cùng Wi-Fi với laptop. Nếu tự khởi động lại, mất SSH lặp lại hoặc sụt nguồn khi motor tải, dừng thử và kiểm tra đường nguồn; chưa kết luận chỉ là lỗi phần mềm.
4. Trong PowerShell Windows trên laptop, đăng nhập:

```powershell
ssh nguyennhutoan_uav@192.168.1.71
```

IP 192.168.1.71 là địa chỉ đã hoạt động trong ảnh. Nếu không vào được, có thể thử tên máy sau hoặc kiểm tra IP mới trên router/màn hình Jetson:

```powershell
ssh nguyennhutoan_uav@nhutoan-uav.local
```

5. Sau khi có dấu nhắc Jetson, kiểm tra:

```bash
hostname
whoami
ls -l /dev/serial/by-id/
```

Cần đăng nhập đúng Jetson/tài khoản, Mega hiện cổng USB tương ứng. Không nạp lại firmware nếu chỉ bị đổi tên ttyUSB.

6. Để dùng nhất quán cách chạy thủ công vừa thử thành công, dừng dịch vụ trước rồi kiểm tra cổng:

```bash
sudo systemctl stop agv_server.service
systemctl is-active agv_server.service
ss -ltnp 'sport = :5000'
```

Lệnh stop không disable dịch vụ: lần bật sau nó có thể tự khởi động. Nếu còn deactivating thì chờ; nếu có LISTEN thì xử lý server đang chạy trước, không mở bản thứ hai.

7. Khi cổng trống và Mega đúng là /dev/ttyUSB0, chạy:

```bash
AGV_PORT=/dev/ttyUSB0 python3 -u "$HOME/stream_server.py"
```

Nếu cổng thực tế khác, thay riêng giá trị AGV_PORT cho đúng kết quả kiểm tra. Dùng stream_server.py như lần đã chạy thành công; không chạy nhầm stream_server_CHUAN_GOC.py, stream_server_STABLE.py hay patch_stream_v7.py. Không dùng sudo để chạy server nhằm che lỗi quyền truy cập.

8. Chờ thông báo Flask chạy trên cổng 5000 và “[SERIAL connected]” tới đúng cổng Mega. Giữ terminal mở; Ctrl + C sẽ dừng chương trình. Chỉ thấy Running không chứng minh USB đã kết nối.
9. Trên laptop cùng mạng mở:

```text
http://192.168.1.71:5000/
```

Thay IP nếu Jetson đổi địa chỉ, rồi Ctrl + F5. Nếu muốn trong VS Code: Ctrl + Shift + P → Simple Browser: Show → nhập URL trên. Không dùng 127.0.0.1:15000 nếu chưa tạo đường hầm tương ứng.

10. Trên web kiểm tra Xe thật · USB, USB đã kết nối, LÁI TAY và DỪNG. Nhấn DỪNG một lần; quan sát bánh. Khi xe vẫn được kê, thử giữ/nhả một hướng ngắn rồi DỪNG. Chỉ một người điều khiển.
11. Khi xác minh giữ/nhả/dừng đúng, đặt xe xuống khu vực trống để thử trong phạm vi ngắn theo cấu hình đang có. Không đưa tay vào bánh đang có thể quay. Với AUTO, đặt đúng hướng trên line trước khi đổi chế độ một lần và chờ xác nhận.

SSH FS chỉ phục vụ duyệt/sửa file, không tự khởi động web. Sau khi bật Jetson, nếu SSH thường vào được nhưng SSH FS chưa hiện file: ngắt phiên SSH FS cũ rồi Add as Workspace folder lại cấu hình jetson-agv. Không cần tạo lại chương trình AGV.

## 6. Các lỗi thường gặp

- Web ERR_CONNECTION_REFUSED: kiểm tra server và cổng 5000 trước; SSH vào được không có nghĩa Flask đang chạy.
- Address already in use: cổng đang bị chương trình khác dùng; không khởi động chồng bản thứ hai.
- V4L2 setting property #38 is not supported: một thuộc tính camera không được hỗ trợ. Nếu web vẫn có hình thì thông báo đó chưa chứng minh camera hỏng.
- Flask development server warning: cảnh báo triển khai, không phải lỗi khởi động khi đã hiện Running. Tài liệu này không thay kiến trúc server.
- USB DISCONNECTED: đối chiếu dây USB/cổng và tiến trình đang giữ cổng; không thử phát chuỗi CFG hoặc đổi sang SAFE1 để sửa việc kết nối.
- Bánh không dừng sau STOP hoặc tự chạy ngoài ý muốn: ưu tiên dừng nguồn chuyển động; không khẳng định dừng dịch vụ web sẽ chắc chắn dừng Mega đang AUTO.

## 7. Phạm vi xác minh

Tài liệu được lập từ ảnh và thông tin người dùng cung cấp ngày 09/11/2026. Không đo trực tiếp điện áp/dòng/cực tính, không chạy lệnh trên Jetson của người dùng, không thử điều khiển hoặc dừng xe từ Codex. Đã kiểm tra định dạng tài liệu và nội dung lệnh, không có thay đổi thuật toán/firmware.

Đề xuất phần cứng cho nhiệm vụ riêng: tách được nguồn driver motor khỏi nguồn Jetson và có cơ cấu dừng khẩn phù hợp. Đây là đề xuất, không phải bước tự đấu lại dây trong checklist này.
