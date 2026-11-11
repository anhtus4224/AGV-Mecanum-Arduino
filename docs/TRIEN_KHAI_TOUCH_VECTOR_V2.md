# Triển khai TOUCH_VECTOR_V2 cùng người vận hành

Ghi nhận ngày 11/11/2026. Tài liệu tham chiếu cho cuộc trò chuyện hiện tại;
không phải biên bản đã triển khai. Không chứa mật khẩu/token. Không tự chạy
các chặng dưới đây. Trong chat chỉ đưa **một bước nhỏ**, nói rõ chỗ bấm,
terminal và lệnh; sau mỗi bước quan trọng **đợi kết quả/ảnh**, kiểm tra rồi
mới tiếp tục. Ghi nhận bước đã xong để không bắt làm lại.

## Ngữ cảnh và bản được chọn

- Repository: anhtus4224/AGV-Mecanum-Arduino.
- Nhánh phần mềm: `fix/touch-strafe-avoid-2026-11-11`.
- Commit cố định: `dc1092c62572b3ec2ac7c13fde3014ec392b23e0`.
- Gói: `AGV_VECTOR1_TOUCH_V2_2026-11-11.zip`.
- SHA256 ZIP: `7ee2926162c43be42d06692318ee2daccb7c6341aee5e6c8f0e1910950b37254`.
- Bản nguồn trước: SETPOINT_ACK_V1, commit
  `882daf1239ab6a55617726c5eda8e3aefb7bdf9b`. Chưa đối chiếu hash Jetson hôm nay.
- Đọc [thay đổi/giới hạn](../upgrade_v1/TOUCH_VECTOR_V2.md),
  [kiểm chứng](../upgrade_v1/TEST_REPORT_TOUCH_V2.md),
  [bảng PWM](../upgrade_v1/PWM_TABLE_TOUCH_V2.csv) và AGENTS.md trước triển khai.

Các kết quả line thẳng/cua/bắt lại line PWM120/160, STOP/thả tay, cảm biến line
và hết lỗi xám sau SETPOINTFIX là **người dùng báo đã thử trước đây**. Chưa
coi đó là kiểm chứng bản mới. Test phần mềm/build AVR không phải thử xe.
Dạt ngang chưa xác nhận sửa trên xe. Mô hình/vệt/vận tốc chỉ ước lượng từ
lệnh/PWM. Không đổi pin, dấu motor, baudrate, servo, thứ tự cảm biến hay cua.

## Nhận diện thiết bị và terminal

Laptop Windows, VS Code có terminal tên **PC** và **JETSON**. Tên tab không
xác nhận SSH. `PS C:\...>` hoặc `PS F:\...>` là PowerShell trên PC, kể cả khi
tab tên JETSON. Chỉ dấu nhắc `nguyennhutoan_uav@nhutoan-uav:...$` mới là
bằng chứng đang ở shell Jetson. Không gõ PowerShell/scp nguồn Windows vào
shell Jetson hoặc gõ sudo/Linux vào PowerShell.

- SSH từ PowerShell: `ssh nguyennhutoan_uav@nhutoan-uav.local`.
- Nếu tên .local không phân giải, kiểm tra IP/router/kết nối; IP báo gần nhất
  192.168.1.139 không được mặc định còn đúng. Không tự dùng .71.
- Sau đăng nhập Jetson: `hostname -I`, đọc kết quả rồi chọn IP LAN phù hợp.
- Thư mục chạy: `/home/nguyennhutoan_uav/agv_vector_v1`.
- Launcher: `python3 run_vector_v1.py`.
- USB cũ: `/dev/ttyUSB0`, phải kiểm tra lại, không mặc định COM Windows tương đương.
- Chỉ đưa link web cụ thể `http://<IP đã xác nhận>:5000` sau khi biết IP.
- Mật khẩu SSH, mật khẩu web, token chỉ nhập cục bộ khi chương trình hỏi;
  không gửi chat/ảnh hoặc ghi vào tài liệu/lệnh/GitHub.

## Nguồn và điều kiện chuyển chặng

Theo người dùng: một công tắc tổng cấp Jetson, Mega và motor qua các nhánh
đang dùng; ưu tiên ắc quy, adapter Jetson đã rút; USB Jetson–Mega đang dùng.
Không suy ra nguồn motor đã cách ly khi phần mềm STOP. Bật tổng để kiểm tra
thì xe phải kê chắc, tất cả bánh không chạm sàn. Không tự đổi dây/chân/dấu motor.

Tắt bình thường bằng từng thao tác, đợi xác nhận giữa các thao tác:

1. Web **DỪNG**, xác nhận bánh thật dừng; **Nhả quyền**.
2. Đúng terminal đang chạy server trên Jetson: **Ctrl+C**. Nếu server là service
   thì xác định đúng service trước, không giả định Ctrl+C dừng service nền.
3. Shell Jetson: `sudo shutdown -h now`.
4. Đợi SSH/kết nối đóng, **thêm 30 giây**, rồi mới tắt công tắc tổng.

Đây là tắt bình thường; tình huống nguy hiểm thực tế không được chờ quy trình
chat hoặc SSH thay cho cách ngắt khẩn đã chuẩn bị tại xe.

Nạp Mega cần chặng kiểm tra nguồn/USB riêng: phải làm rõ cách cấp logic, cách
giữ motor không được cấp điện và nguy cơ cấp ngược USB. Bánh treo không thay
thế cách ly nguồn khi thao tác dây/nạp. Không mặc định tắt tổng là hết mọi
nguồn nếu PC USB vẫn cấp điện. Không cắm USB PC cùng Jetson vào Mega hoặc
đề xuất cách đấu nguồn khi chưa biết phần cứng. Nếu chưa xác nhận được cách
chuẩn bị nguồn đúng, chỉ Verify ngoại tuyến, dừng trước Upload.

## Chặng 1 — chỉ thu trạng thái, chưa chạy lệnh

Yêu cầu ảnh phần dấu nhắc/nội dung cuối của hai terminal PC và JETSON; che
bí mật nếu có. Hỏi tổng đang bật/tắt, xe đã kê bánh rời sàn chưa, server/web
đang chạy/dừng. Không yêu cầu bật tổng, chạy launcher hay SSH lại nếu đã xong.
Từ phản hồi mới chọn một hành động tiếp theo. Trạng thái vật lý hiện tại chưa
được xác minh chỉ vì tài liệu này mô tả cấu hình nguồn.

## Chặng 2 — tải và giải nén trên Windows

Trong trình duyệt Windows đã đăng nhập GitHub, tải
[ZIP đúng commit](https://github.com/anhtus4224/AGV-Mecanum-Arduino/raw/dc1092c62572b3ec2ac7c13fde3014ec392b23e0/AGV_VECTOR1_TOUCH_V2_2026-11-11.zip).
Không dùng ZIP SETPOINTFIX hoặc ZIP nhánh main. Đợi tải xong và xác định
đường dẫn thật trong Explorer; không đoán ổ C/F hay tên thư mục Downloads.

Ở terminal **PC PowerShell**, sau khi người dùng cung cấp đường dẫn file,
đưa một lệnh `Get-FileHash -Algorithm SHA256 -LiteralPath 'đường dẫn thực'`;
đối chiếu với SHA ở trên. Không đưa chuỗi giữ nguyên chữ 'đường dẫn thực' để chạy.
Đợi kết quả rồi Explorer: chuột phải ZIP → **Extract All… / Giải nén tất cả**
→ chọn thư mục mới → **Extract**. Ghi lại đường dẫn `upgrade_v1` đã giải nén.
Mở thư mục, xác nhận đủ bốn file Jetson và thư mục mega_vector_v1 có .ino/.h.

## Chặng 3 — nhận diện bản đang chạy, dừng và sao lưu

Nếu tab JETSON còn PowerShell và xe đủ điều kiện kiểm tra, hướng dẫn SSH bằng
lệnh đã ghi ở trên; đợi ảnh dấu nhắc. Nếu đã SSH thì không đăng nhập lại.
Nếu server đang chiếm terminal, không gõ lệnh shell vào launcher; chọn phiên
SSH riêng để đọc thông tin, hoặc dừng có kiểm soát tại chặng này.

Sau khi người vận hành đã DỪNG/nhả quyền, xác định tiến trình thực trước khi
thay file. Các lệnh **JETSON** đọc thông tin, đưa từng lệnh rồi đợi kết quả:

```bash
ss -ltnp 'sport = :5000'
```

Nếu cần xác minh service được nhắc trong tài liệu cũ:

```bash
systemctl status agv_server.service --no-pager
```

Không kết luận service tồn tại/đang chạy từ tên cũ. Không kill bừa, không bật
enable/disable service. Server foreground: Ctrl+C trong đúng terminal.
Service thật sự chiếm cổng: chỉ hướng dẫn `sudo systemctl stop agv_server.service`
sau khi đã đối chiếu đúng; rồi kiểm tra lại cổng5000. Chỉ một chủ USB.

Trong thư mục chạy, lấy hash bốn file (không in nội dung code/env/header):

```bash
cd /home/nguyennhutoan_uav/agv_vector_v1
```

```bash
sha256sum agv_vector_gateway.py vector_controls.js stream_server_vector_v1.py run_vector_v1.py
```

Đối chiếu hash với các bản đã xuất bản để ghi rõ: khớp nguồn, khớp bản mới,
hay chưa xác định. Nếu đang chạy, đọc `/control/diagnostics` qua trình duyệt
đã đăng nhập để biết revision; không xem revision là bằng chứng trùng hash.

Tạo thư mục backup mới trên Jetson, tên có thời gian, ví dụ dùng biến riêng:

```bash
agv_backup_dir="$HOME/agv_backup_before_touch_v2_$(date +%Y%m%d_%H%M%S)"
```

```bash
mkdir -- "$agv_backup_dir"
```

Sau khi mkdir thành công, copy đúng bốn file vào thư mục mới bằng `cp -p --`;
đưa lệnh với danh sách bốn file rõ ràng và biến đích ở trên. Lưu SHA256SUMS
của bản copy rồi kiểm tra `sha256sum -c` trong thư mục backup. Ghi lại tên
backup thực và copy backup về PC trước thay đổi; không đưa file có bí mật
lên GitHub. Biến shell có thể mất khi đổi phiên SSH, không dùng lại mù quáng.

Trên PC/Jetson, xác định **nguồn firmware hiện có** (.ino, .h và HEX nếu có),
copy nguyên thư mục vào backup mới, ghi hash và nguồn gốc. Đó là **bản nguồn
đang có, không phải firmware đọc ngược từ Mega**. Nếu không biết nguồn nào
đúng bản đang nạp, ghi 'chưa xác minh', không hứa rollback y hệt. Chưa có
bản quay lại phù hợp thì dừng trước Upload để làm rõ, không tự tạo bản 'gốc'.

## Chặng 4 — xác định bộ cập nhật

Đọc thực tế gói tại commit trên và đối chiếu SHA256SUMS.txt:

| Nơi | Tệp | Xử lý |
|---|---|---|
| Jetson | agv_vector_gateway.py | Cập nhật: ticket nối tiếp, lease/STOP, diagnostics |
| Jetson | vector_controls.js | Cập nhật cùng gateway: giữ/thả, ticket, bàn giao |
| Jetson | stream_server_vector_v1.py | Cập nhật: fetch wrapper, touch, kích thước mô hình |
| Jetson | run_vector_v1.py | Nội dung giữ nguyên so với nguồn; kiểm tra và giữ cùng bộ |
| Mega | mega_vector_v1/mega_vector_v1.ino | Build/nạp mới: điểm vào55 cm và VECTOR_TARGET |
| Mega | mega_vector_v1/VectorMotion.h | Cùng sketch: bao thân47×34 cm, chuyển RETURN |

Triển khai hoàn chỉnh cần bộ Jetson đồng nhất và hai file Mega mới, trong cửa
sổ dừng bảo trì, không chạy xe giữa lúc mới chép một phần. Không nạp .h riêng.
Giao thức vẫn VECTOR1; Mega cũ có thể nhận lệnh gateway mới nhưng thiếu sửa
né/telemetry mới, nên không coi là đã triển khai xong. Không chạy .patch, tests,
original_firmware hoặc cài requirements hàng loạt lên Jetson đang ổn.

## Chặng 5 — chép từ PC, xác minh tại Jetson

Chỉ sau backup và dừng server: tạo thư mục nhận mới ngoài thư mục chạy trên
Jetson. Ghi lại đúng đường dẫn đã tạo. Trong **PC PowerShell**, dùng `scp`
với **đường dẫn Windows đã xác nhận**, đích
`nguyennhutoan_uav@nhutoan-uav.local:<thư mục nhận đã tạo>/`.
Hướng dẫn riêng từng lệnh; không để người dùng chạy placeholder `<...>`.
Mật khẩu SSH chỉ gõ tại prompt cục bộ, không dán chat.

Trên **JETSON**, kiểm tra hash bốn file staging so với manifest gói. Chỉ sau
khớp và xác nhận cổng5000 đã trống mới copy đúng bốn file vào thư mục chạy.
Kiểm tra lại hash sau copy. Không dùng scp ghi đè thẳng thư mục chạy khi
chưa backup/dừng; không chạy server trước khi hoàn tất chặng firmware.

## Chặng 6 — Verify và Upload Mega

Trên **Windows**, hỏi Arduino IDE đã cài và bản nào; mở
mega_vector_v1/mega_vector_v1.ino, giữ VectorMotion.h cùng thư mục.
Chọn **Tools → Board → Arduino AVR Boards → Arduino Mega or Mega 2560**;
processor ATmega2560 nếu menu phiên bản IDE có lựa chọn. Bấm **Verify (✓)**,
đợi kết quả build/ảnh; Verify không upload và không chứng minh motor đúng.

Trước **Upload (→)**: dừng server, giữ backup đã xác minh, làm rõ nguồn và
USB theo phần nguồn ở trên. Nếu phải tắt tổng để chuẩn bị, áp dụng shutdown
Jetson và chờ30 s trước tắt tổng. Không đề xuất đổi cáp lúc đang mang điện
hoặc cấp thêm USB5V khi chưa rõ chống cấp ngược. Không tự đổi dây nguồn.

Chỉ khi cách cấp logic/cách ly motor được xác nhận: xác định đúng **Tools →
Port → COM…** bằng bằng chứng thiết bị Windows, không đoán từ /dev/ttyUSB0.
Đóng Serial Monitor và mọi chủ USB khác. Người vận hành chủ động Upload;
đợi log thành công. Không tự nạp từ môi trường đám mây. Ghi lại file/hash,
board/processor/cổng và kết quả nạp. Chỉ sau đó hướng dẫn khôi phục kết nối
Jetson–Mega và nguồn theo cấu hình đã xác nhận, xe vẫn kê bánh rời sàn.

## Chặng 7 — khởi động và mở web

Nếu tổng đang tắt, chỉ hướng dẫn bật sau xác nhận xe kê chắc và cấu hình nguồn
đúng; đợi Jetson boot, SSH lại nếu cần. **JETSON**, đưa từng lệnh và đợi:

```bash
hostname -I
```

```bash
ls -l /dev/serial/by-id/ /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
```

Nếu không có cổng hoặc nhiều thiết bị, điều tra trước; không đoán hoặc sửa
quyền USB bằng chmod777. Kiểm tra không có service/tiến trình khác giữ USB
hay5000. Vào thư mục chạy nếu chưa ở đó, rồi **JETSON**:

```bash
python3 run_vector_v1.py
```

Người dùng nhập tài khoản/mật khẩu web và đường dẫn USB đã xác nhận cục bộ.
Đợi log nhận VECTOR1 và server nghe5000, không chỉ nhìn có PID. Từ IP LAN
vừa đọc, trợ lý đưa **link chính xác** để mở trên laptop. Đăng nhập, Ctrl+F5;
điện thoại tải lại trang. Nếu lỗi import/USB/probe/ACK thì dừng xử lý lỗi,
không tự ghép SAFE1/firmware ký tự hoặc chạy bản khác thử may rủi.

## Chặng 8 — kiểm tra đầu tiên, cap80, né TẮT

Xác nhận diagnostics revision TOUCH_VECTOR_V2, telemetry mới và có
firmware_target từ Mega mới; nếu chưa có không coi là đủ bộ. Kê bánh treo,
khu vực trống, có người ngắt khẩn. Một chủ USB. Thử từng thao tác riêng:
DỪNG khi đứng yên → Nhận quyền → xác nhận cap80/né TẮT → giữ tiến ngắn →
thả → quan sát bánh thật dừng → DỪNG. Không tăng cap để bù bánh không chạy.
PWM0 không phải bằng chứng phanh cơ tức thời; phải quan sát bánh.

Sau mỗi thao tác đợi ảnh/kết quả. Nếu không dừng đúng thì ngừng thử chuyển
động, xử lý điều kiện an toàn trước. Khi STOP/thả đã đạt, thử riêng lùi,
các nút cảm ứng tiến/lùi/ngang/bốn chéo, rồi bàn giao laptop DỪNG → Nhả quyền
→ điện thoại Nhận quyền. Thử giữ/thả, rời tab/hủy pointer từng ca, không gộp
tất cả thành một lượt. Ghi thiết bị/trình duyệt, lỗi và trạng thái quyền.

## Chặng 9 — chẩn đoán dạt ngang trước kết luận

Mở `http://<IP hiện tại>:5000/control/diagnostics` bằng trình duyệt đã đăng nhập;
trợ lý thay IP thực khi hướng dẫn. Thu riêng trạng thái đứng yên, giữ dạt trái,
giữ dạt phải và sau thả, cap80/né TẮT, cùng video cả bốn bánh trên giá.
Không yêu cầu gửi header/cookie/lease/ticket/mật khẩu.

Đối chiếu requested_vector → last_drive_ack → firmware_target → current_pwm
và tuổi MOTION. driver_pwm chỉ suy ra dấu điện từ MOTION, không đo chân.
Thứ tự FL,FR,RL,RR: phải dự kiến [80,-80,-80,80], trái [-80,80,80,-80] sau
ramp. Nếu bánh khác dù yêu cầu đúng, chưa tự kết luận phần cứng, không đảo
dấu; phân biệt mismatch bản triển khai, lệnh, pin/driver và quan sát bánh bằng
bằng chứng tiếp theo. Gói này chưa có kết quả dạt ngang thực tế.

## Chặng 10 — line/cua rồi mới né

Chỉ sau STOP/lái tay/cảm ứng/bàn giao và dạt ngang đã đánh giá đủ: lập từng
bài thử sàn có kiểm soát, line/cua trước rồi mới né. Giữ mapping, thông số cua
và mắt giữa A2/OUT3/S3. Các mức120/160 từng tốt ở bản cũ vẫn cần hồi quy.
Né chỉ bật chủ động sau kiểm tra gốc đo/góc mù cảm biến, kích thước và khoảng
trống. Điểm vào55 cm, rộng47/dài34 cm; không echo không phải đường trống.
SONAR_REAR_UNKNOWN phải điều tra, không bỏ guard để làm xe mượt.
Không thử né200/255 ngay hoặc coi chuyển động liên tục là bảo đảm an toàn.

## Quay lại và nhật ký

Nếu lỗi: DỪNG và bảo đảm nguồn an toàn, dừng đúng tiến trình mới. Khôi phục
bốn file Jetson từ backup đã kiểm hash; nếu đã Upload Mega thì cần build/nạp
lại đúng nguồn firmware đã lưu theo chặng nguồn/USB. Không ghép Python VECTOR1
với firmware ký tự gốc, không lấy original_firmware làm mặc định rollback.
Tải lại web, nhận quyền mới, thử STOP trước. Chưa xác minh nguồn cũ thì không
hứa khôi phục đúng binary từng chạy trên Mega.

Tài liệu chung chỉ ghi quy trình và dữ kiện không bí mật. Nhật ký tại phiên
triển khai cần ghi: trạng thái nguồn/terminal, đường dẫn giải nén, SHA gói,
hash trước/sau, backup thực, nguồn firmware và tình trạng xác minh, IP/USB
đã xác nhận, Verify/Upload, bài thử đã làm/chưa làm. Không ghi PASS phần cứng
từ test host. Không lưu mật khẩu/token/cookie vào nhật ký hoặc commit.

**Trạng thái lúc lập hướng dẫn:** đã có gói phần mềm xuất bản và kiểm thử
host/AVR; chưa xác nhận trạng thái xe/terminal hiện tại, chưa xác minh hash
Jetson, chưa thực hiện triển khai hoặc thử xe trong cuộc trò chuyện này.
