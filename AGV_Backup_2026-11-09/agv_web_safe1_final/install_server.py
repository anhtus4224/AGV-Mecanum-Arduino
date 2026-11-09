"""Run on Jetson AFTER stopping agv_server.service. Never starts services."""
from pathlib import Path
from datetime import datetime
import shutil
import sys
root = Path(__file__).resolve().parent
target = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.home() / 'stream_server.py'
if not target.is_file():
    raise SystemExit('Không tìm thấy server hiện tại: ' + str(target))
stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
for name, dest in [('stream_server.py', target), ('agv_serial_link.py', target.parent / 'agv_serial_link.py')]:
    if dest.exists():
        backup = dest.with_name(dest.name + '.before_SAFE1_' + stamp)
        shutil.copy2(dest, backup)
        print('BACKUP:', backup)
    shutil.copy2(root / name, dest)
    print('INSTALLED:', dest)
print('Chưa khởi động dịch vụ. Nạp Mega SAFE1 rồi kiểm tra USB trước.')
