# Kiểm tra GitHub chỉ đọc — 09/11/2026

Đích: https://github.com/anhtus4224/AGV-Mecanum-Arduino

1. `git ls-remote https://github.com/anhtus4224/AGV-Mecanum-Arduino.git` trong sandbox: thất bại kết nối proxy:8080. Không phải bằng chứng repo không tồn tại.
2. Chạy lại đúng lệnh chỉ đọc bằng quyền mạng được duyệt: exit 0, kết quả:

```text
9745e3798e1aac03fdd48283b6dcdc72ea7deef8 HEAD
9745e3798e1aac03fdd48283b6dcdc72ea7deef8 refs/heads/main
```

3. `gh auth status`: CLI báo token GH_TOKEN không hợp lệ. Không lưu/in giá trị token; không đăng nhập lại hoặc đổi cấu hình.
4. HTTP **GET** `https://github.com/anhtus4224/AGV-Mecanum-Arduino.git/info/refs?service=git-receive-pack`: HTTP 200. Đây chỉ là truy cập được bước công bố giao thức ghi, không gửi commit/pack hay cập nhật ref, không chứng minh tài khoản hiện tại có quyền push.

Kết luận: đọc repo và kết nối endpoint Git được; quyền push chưa xác nhận. Không chạy `git push` kể cả dry-run; không commit/add/fetch/clone, không đổi remote hoặc cấu hình môi trường.
Muốn xác nhận quyền ghi đầy đủ về sau cần kiểm tra danh tính/quyền repository bằng cơ chế xác thực phù hợp; sau khi người dùng chấp thuận riêng mới thực hiện xuất bản.
