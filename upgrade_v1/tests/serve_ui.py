import os,sys,time,types,importlib.util,tempfile
from pathlib import Path
os.environ['AGV_WEB_USER']='test'
os.environ['AGV_WEB_PASSWORD']='test-only-passphrase'
os.environ['AGV_MAP_DIR']=tempfile.mkdtemp()
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
sys.modules['cv2']=types.ModuleType('cv2');sys.modules['serial']=types.ModuleType('serial')
spec=importlib.util.spec_from_file_location('vector_server',r/'stream_server_vector_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Port:
 is_open=True
 def __init__(self):self.data=[]
 def write(self,x):self.data.append(x.decode());return len(x)
p=Port();m.ser=p;m.link_ready=m.firmware_seen=m.gateway.ready=True
m.state.update(mode='LÁI TAY',mode_pending=False,action='STOP',port='FAKE_USB',line='00100')
@m.app.before_request
def fake_sensor_snapshot():
 now=time.monotonic();m.rx_time=m.data_time=m.mode_time=now;m.gateway.last_motion=now
 m.motion_feedback=dict(seq=1,board_ms=1000,wheels=[0,0,0,0],auto=False,corner=0,avoid=False,received=now)
# The only hardware is the fake above; no worker threads started.
m.app.run(host='127.0.0.1',port=18766,threaded=True)
