"""Interactive launcher. Credentials stay in this process; never saved to source."""
import getpass
import os
import runpy
from pathlib import Path
if __name__=='__main__':
    if not os.environ.get('AGV_WEB_USER'):os.environ['AGV_WEB_USER']=input('Tên đăng nhập Web: ').strip()
    if not os.environ.get('AGV_WEB_PASSWORD'):os.environ['AGV_WEB_PASSWORD']=getpass.getpass('Mật khẩu Web (ít nhất 12 ký tự, không hiện khi gõ): ')
    if len(os.environ['AGV_WEB_PASSWORD'])<12:raise SystemExit('Mật khẩu quá ngắn')
    if not os.environ.get('AGV_PORT'):os.environ['AGV_PORT']=input('USB Mega (ví dụ /dev/ttyUSB0 hoặc đường dẫn by-id): ').strip()
    if not os.environ['AGV_PORT'].startswith('/dev/'):raise SystemExit('Đường dẫn USB không hợp lệ')
    runpy.run_path(str(Path(__file__).parent/'stream_server_vector_v1.py'),run_name='__main__')
