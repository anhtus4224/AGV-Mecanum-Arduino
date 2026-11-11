"""Loopback-only browser fixture. Fake USB and sensors, never opens a device."""
import os,sys,time,types,importlib.util,tempfile,threading
from pathlib import Path
os.environ['AGV_WEB_USER']='test';os.environ['AGV_WEB_PASSWORD']='test-only-passphrase'
os.environ['AGV_MAP_DIR']=tempfile.mkdtemp()
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
sys.modules['cv2']=types.ModuleType('cv2');sys.modules['serial']=types.ModuleType('serial')
spec=importlib.util.spec_from_file_location('teach_server',r/'stream_server_vector_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Port:
 is_open=True
 def __init__(self):self.wheels=[0]*4;self.auto=False
 def write(self,data):
  parts=data.decode().split('*')[0].split(',');op=parts[3]
  if op=='S':self.wheels=[0]*4;self.auto=False
  if op=='D':
   f,s,c=map(int,parts[4:7]);raw=[f+s+c,f-s-c,f-s+c,f+s-c];peak=max(255,*map(abs,raw));self.wheels=[round(x*200/peak) for x in raw]
  return len(data)
p=Port();m.ser=p;m.link_ready=m.firmware_seen=m.gateway.ready=True
m.state.update(mode='LÁI TAY',mode_pending=False,action='STOP',port='FAKE_USB',line='00100',firmware_revision='AVOID_DIRECTIONAL_V4',vector_status={'cap':200,'phase':0,'armed':False})
def sensor_loop():
 seq=0
 while True:
  with m.serial_lock:
   seq+=1;now=time.monotonic();m.rx_time=m.data_time=m.mode_time=now;m.gateway.last_motion=now;m.gateway.pending.clear()
   m.motion_feedback=dict(seq=seq,board_ms=int(now*1000),wheels=list(p.wheels),auto=False,corner=0,avoid=False,received=now)
   m.state.update(action='MOVE' if any(p.wheels) else 'STOP',sonar_raw={'F':100,'B':100,'L':100,'R':100},sonar_received_monotonic=now)
   if os.environ.get('AGV_TEST_RETURN_UNKNOWN')=='1':m.state['sonar_raw']={'F':999,'B':66,'L':125,'R':73}
   m.state['vector_range']={'raw':dict(m.state['sonar_raw']),'ages_ms':dict.fromkeys('FBLR',0),'received':now}
   m.gateway.watchdog(now)
  time.sleep(.02)
threading.Thread(target=sensor_loop,daemon=True).start()
threading.Thread(target=m.vector_physics_worker,daemon=True).start()
m.app.run(host='127.0.0.1',port=18768,threaded=True)
