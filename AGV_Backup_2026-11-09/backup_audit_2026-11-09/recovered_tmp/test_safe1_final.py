import ast
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path('/workspace/agv_web_safe1_final')
sys.path.insert(0,str(ROOT))
from agv_serial_link import SafeMegaLink
class Port:
    is_open=True
    port='/dev/ttyUSB0'
    def __init__(self):self.writes=[]
    def write(self,b):self.writes.append(b)
    def close(self):self.is_open=False
class LinkTest(unittest.TestCase):
    def setUp(self):self.state={};self.link=SafeMegaLink(self.state,None);self.p=Port();self.link.port=self.p
    def connect(self):self.link.consume(b'AGV:SAFE1\n')
    def test_no_motion_on_handshake(self):
        self.assertFalse(self.link.send('DRIVE:E'));self.connect()
        self.assertEqual(self.p.writes,[b'@STOP\n']);self.assertEqual(self.state['mode'],'LÁI TAY')
    def test_partial_and_nontelemetry(self):
        self.connect();self.link.consume(b'>> RX[E]: E\nDATA:001')
        self.assertNotIn('line',self.state);self.link.consume(b'00,STOP,12.5\nSONAR:999,30,40,50\n')
        self.assertEqual(self.state['line'],'00100');self.assertEqual(self.state['sonar']['F'],999)
        self.assertEqual(self.state['battery'],12.5)
    def test_mode_ack(self):
        self.connect();self.link.send('MODE:AUTO');self.assertEqual(self.state['mode'],'LÁI TAY')
        self.link.ingest('ACK:MODE:AUTO');self.assertEqual(self.state['mode'],'TỰ HÀNH')
        self.link.ingest('ACK:STOP');self.assertEqual(self.state['mode'],'LÁI TAY')
    def test_bad_data(self):
        self.connect();self.link.consume(b'DATA:00100,STOP,NaN\nSONAR:999,NaN,2,3\n\xff\n')
        self.assertNotIn('battery',self.state);self.assertNotIn('sonar',self.state)
    def test_disconnect_resets_state(self):
        self.connect();self.link.ingest('ACK:MODE:AUTO');self.link.disconnect('test')
        self.assertEqual(self.state['port'],'DISCONNECTED');self.assertEqual(self.state['mode'],'LÁI TAY')
        self.assertFalse(self.link.send('DRIVE:F'))
    def test_only_framed_commands(self):
        self.connect();self.link.send('DRIVE:F');self.assertEqual(self.p.writes[-1],b'@DRIVE:F\n')
        with self.assertRaises(ValueError):self.link.send('CFG:FAST=255')

# Load real routes without installing camera/GPU/Flask in this workspace.
flask=types.ModuleType('flask')
class FakeFlask:
    def __init__(self,*a,**kw):pass
    def route(self,*a,**kw):return lambda f:f
flask.Flask=FakeFlask
flask.Response=lambda *a,**kw:None
flask.render_template_string=lambda x:x
flask.jsonify=lambda *a,**kw:kw if kw else a[0]
flask.request=types.SimpleNamespace(args={},json={})
sys.modules['flask']=flask
sys.modules['cv2']=types.ModuleType('cv2')
spec=importlib.util.spec_from_file_location('server_under_test',ROOT/'stream_server.py')
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)
class RoutesTest(unittest.TestCase):
    def setUp(self):
        server.state.clear();server.link=SafeMegaLink(server.state,None)
        self.p=Port();server.link.port=self.p;server.link.ingest('AGV:SAFE1')
        flask.request.args={};flask.request.json={}
    def test_manual_and_stop(self):
        flask.request.args={'drive':'1'};server.mecanum_control();self.assertEqual(self.p.writes[-1],b'@DRIVE:F\n')
        flask.request.args={'estop':'1'};server.mecanum_control();self.assertEqual(self.p.writes[-1],b'@STOP\n')
    def test_auto_rejects_manual_commands(self):
        server.link.ingest('ACK:MODE:AUTO');flask.request.args={'rotate':'1'}
        result=server.mecanum_control();self.assertEqual(result[1],409)
        self.assertNotIn(b'@DRIVE:E\n',self.p.writes)
    def test_mode_not_faked(self):
        server.toggle_mode();self.assertEqual(self.p.writes[-1],b'@MODE:AUTO\n')
        self.assertEqual(server.state['mode'],'LÁI TAY')
    def test_cfg_disabled(self):
        flask.request.json={'fast_spd':255};before=list(self.p.writes)
        result=server.save_tuning();self.assertEqual(result[1],501);self.assertEqual(before,self.p.writes)
    def test_disconnected_command_error(self):
        server.link.disconnect('test');flask.request.args={'drive':'1'}
        self.assertEqual(server.mecanum_control()[1],503)
    def test_no_duplicate_fsm_or_raw_writes(self):
        s=(ROOT/'stream_server.py').read_text();a=ast.parse(s)
        self.assertEqual(sum(isinstance(n,ast.FunctionDef) and n.name=='fsm_controller_worker' for n in a.body),1)
        self.assertNotIn('ser.write(',s)
if __name__=='__main__':unittest.main()
