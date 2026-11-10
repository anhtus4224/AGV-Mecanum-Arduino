"""Loopback fixture reproducing absent Mega and background USB retries."""
import os,sys,time,types,importlib.util,tempfile,threading
from pathlib import Path
os.environ['AGV_WEB_USER']='test';os.environ['AGV_WEB_PASSWORD']='test-only-passphrase'
os.environ['AGV_MAP_DIR']=tempfile.mkdtemp()
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r))
sys.modules['cv2']=types.ModuleType('cv2');sys.modules['serial']=types.ModuleType('serial')
spec=importlib.util.spec_from_file_location('simulation_fixture',r/'stream_server_vector_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.serial=None # Failed discovery is real gateway behavior; never opens physical ports.
threading.Thread(target=m.gateway.serial_worker,daemon=True).start()
threading.Thread(target=m.vector_physics_worker,daemon=True).start()
m.app.run(host='127.0.0.1',port=18767,threaded=True)
