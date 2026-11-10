import sys,os,unittest,time,binascii
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agv_vector_gateway import Gateway,frame
from flask import Flask
import threading
class Port:
 is_open=True
 def __init__(self):self.data=[]
 def write(self,x):self.data.append(x);return len(x)
class Tests(unittest.TestCase):
 def setUp(self):
  os.environ['AGV_WEB_USER']='test';os.environ['AGV_WEB_PASSWORD']='test-only-passphrase'
  self.port=Port();self.g={'serial_lock':threading.RLock(),'ser':self.port,'clear_link':lambda reason:None,'state':{'mode':'LÁI TAY'},'driving_environment':'real','drive_generation':1,'auto_or_manual_fresh':lambda:True}
  self.gateway=Gateway(self.g);self.gateway.ready=True;self.gateway.last_motion=time.monotonic()
  self.app=Flask(__name__);self.gateway.install(self.app)
  self.app.add_url_rule('/telemetry',endpoint='telemetry',view_func=lambda:{'ok':True})
  self.app.add_url_rule('/mecanum_control',endpoint='stop',view_func=lambda:dict(self.gateway.stop()[0]))
  self.a=self.app.test_client();self.b=self.app.test_client()
  self.auth={'Authorization':'Basic dGVzdDp0ZXN0LW9ubHktcGFzc3BocmFzZQ==','X-AGV-CSRF':self.gateway.csrf}
 def req(self,client,path,data=None,controller='browser_123'):
  return client.post(path+'?controller='+controller,json=data or {},headers=dict(self.auth,**{'X-AGV-Lease':self.gateway.owner_lease}))
 def claim(self):return self.req(self.a,'/control/claim')
 def vector(self,seq):return {'drive':1,'strafe':1,'rotate':0,'sequence':seq,'ticket':self.gateway.issue_ticket(),'environment':'real','generation':1}
 def test_auth_csrf(self):
  self.assertEqual(self.a.get('/telemetry').status_code,401)
  self.assertEqual(self.a.post('/control/claim',headers={'Authorization':self.auth['Authorization']}).status_code,403)
 def test_single_owner_and_release(self):
  self.assertEqual(self.claim().status_code,200)
  self.assertEqual(self.req(self.b,'/control/claim').status_code,409)
  self.assertEqual(self.req(self.b,'/control/vector',self.vector(1)).status_code,409)
  self.assertEqual(self.req(self.a,'/control/release').status_code,200)
  self.assertEqual(self.req(self.b,'/control/claim').status_code,200)
 def test_vector_and_order(self):
  self.claim();self.assertEqual(self.req(self.a,'/control/vector',self.vector(1)).status_code,200)
  self.assertIn(b',D,255,255,0,250*',self.port.data[-1])
  count=len(self.port.data);self.req(self.a,'/control/vector',self.vector(1));self.assertEqual(count,len(self.port.data))
 def test_stop_fences_delayed_vector(self):
  self.claim();self.a.get('/mecanum_control?estop=1&controller=browser_123&sequence=4',headers=self.auth)
  count=len(self.port.data);self.req(self.a,'/control/vector',self.vector(3));self.assertEqual(count,len(self.port.data))
 def test_expired_owner_watchdog(self):
  self.claim();self.req(self.a,'/control/vector',self.vector(1));self.gateway.owner_until=time.monotonic()-1
  self.gateway.watchdog();self.assertIn(b',S,',self.port.data[-1]);self.assertIsNone(self.gateway.owner)
 def test_old_ack_and_missing_motion_stop(self):
  self.claim();self.req(self.a,'/control/vector',self.vector(1));self.gateway.last_motion-=1
  self.gateway.watchdog();self.assertIn(b',S,',self.port.data[-1])
 def test_invalid_vector_no_write(self):
  self.claim();count=len(self.port.data)
  for patch in ({'drive':float('nan')},{'drive':True},{'drive':2},{'generation':0},{'ticket':'invalid'}):
   data=self.vector(2);data.update(patch);self.assertEqual(self.req(self.a,'/control/vector',data).status_code,409 if 'generation' in patch or 'ticket' in patch else 400)
  self.assertEqual(count,len(self.port.data))
 def test_viewer_stop_revokes_owner(self):
  self.claim();self.req(self.a,'/control/vector',self.vector(1))
  response=self.b.get('/mecanum_control?estop=1&controller=viewer_456&sequence=1',headers=self.auth)
  self.assertEqual(response.status_code,200);self.assertIsNone(self.gateway.owner)
  self.assertEqual(self.req(self.a,'/control/vector',self.vector(2)).status_code,409)
 def test_ack_failure_stops(self):
  self.claim();self.req(self.a,'/control/vector',self.vector(1))
  self.gateway.watchdog(time.monotonic()+.45)
  self.assertIn(b',S,',self.port.data[-1])
 def test_profile_requires_confirmation(self):
  self.claim();before=len(self.port.data)
  self.assertEqual(self.req(self.a,'/control/profile',{'cap':255,'armed':True}).status_code,400)
  self.assertEqual(len(self.port.data),before)
  self.assertEqual(self.req(self.a,'/control/profile',{'cap':255,'armed':True,'confirmed':True}).status_code,200)
 def test_old_lease_cannot_resume_after_reclaim(self):
  self.claim();old=self.gateway.owner_lease
  self.req(self.a,'/control/release');self.claim()
  response=self.a.post('/control/vector?controller=browser_123',json=self.vector(50),headers=dict(self.auth,**{'X-AGV-Lease':old}))
  self.assertEqual(response.status_code,409)
 def test_simulation_lease_survives_missing_usb(self):
  self.claim();self.g['driving_environment']='simulation';self.gateway.ready=False
  count=len(self.port.data);owner=self.gateway.owner
  self.gateway.last_motion=0;self.gateway.watchdog()
  self.assertEqual(owner,self.gateway.owner);self.assertEqual(count,len(self.port.data))
 def test_simulation_lease_expiry_clears_motion(self):
  self.claim();self.g['driving_environment']='simulation';self.g['simulation_vector']=[1,1,0]
  self.gateway.owner_until=time.monotonic()-1;count=len(self.port.data)
  self.gateway.watchdog();self.assertIsNone(self.gateway.owner)
  self.assertEqual(self.g['simulation_vector'],[0.,0.,0.]);self.assertEqual(count,len(self.port.data))
 def test_failed_discovery_preserves_lease_before_environment_selection(self):
  from unittest.mock import patch
  self.claim();owner=self.gateway.owner;self.g['serial']=None
  with patch('agv_vector_gateway.time.sleep',side_effect=RuntimeError('end fixture loop')):
   with self.assertRaises(RuntimeError):self.gateway.serial_worker()
  self.assertEqual(owner,self.gateway.owner);self.assertFalse(self.gateway.ready)
 def test_ticket_expiration_stops_old_commands(self):
  self.claim();data=self.vector(1);key=data['ticket'];value=self.gateway.tickets[key]
  self.gateway.tickets[key]=(time.monotonic()-.31,)+value[1:]
  count=len(self.port.data);response=self.req(self.a,'/control/vector',data)
  self.assertEqual(response.status_code,409);self.assertEqual(response.json['code'],'COMMAND_EXPIRED')
  self.assertEqual(count,len(self.port.data))
 def test_ticket_is_single_use(self):
  self.claim();data=self.vector(1);self.assertEqual(self.req(self.a,'/control/vector',data).status_code,200)
  data['sequence']=2;self.assertEqual(self.req(self.a,'/control/vector',data).json['code'],'TICKET')
 def test_phone_clock_does_not_affect_ticket(self):
  self.claim();data=self.vector(1);data['issued_ms']=-1e30
  self.assertEqual(self.req(self.a,'/control/vector',data).status_code,200)
 def test_ack_before_write_returns_is_retained(self):
  gateway=self.gateway
  class ImmediateAckPort:
   is_open=True
   def write(self,data):
    sequence=int(data.decode().split(',')[2]);gateway.receive('ACK:{},OK'.format(sequence));return len(data)
  self.g['ser']=ImmediateAckPort();result,code=gateway.write('D',255,0,0)
  self.assertEqual(code,200);self.assertNotIn(result['sequence'],gateway.pending)
  self.assertEqual(self.g['state']['last_drive_ack']['status'],'OK')
 def test_write_failure_removes_pending(self):
  class BadPort:
   is_open=True
   def write(self,data):raise IOError('test disconnected')
  self.g['ser']=BadPort();result,code=self.gateway.write('D',255,0,0)
  self.assertEqual(code,503);self.assertFalse(self.gateway.pending)
  self.assertEqual(self.gateway.link_events[-1]['code'],'WRITE_ERROR')
 def test_diagnostics_read_only_and_private_fields_absent(self):
  count=len(self.port.data)
  response=self.a.get('/control/diagnostics',headers={'Authorization':self.auth['Authorization']})
  self.assertEqual(response.status_code,200);self.assertEqual(count,len(self.port.data))
  for key in ('password','lease','ticket','sid'):self.assertNotIn(key,response.json)
 def test_timeout_cause_is_retained(self):
  self.claim();self.gateway.write('D',255,0,0);self.gateway.watchdog(time.monotonic()+.45)
  self.assertEqual(self.gateway.link_events[-1]['code'],'ACK_TIMEOUT')
 def test_newer_drive_ack_supersedes_old_ping(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  ping,_=self.gateway.write('P');n=ping['sequence'];self.gateway.pending[n]=(time.monotonic()-.413,'P')
  drive,_=self.gateway.write('D',255,0,0);self.gateway.receive('ACK:{},OK'.format(drive['sequence']))
  self.gateway.watchdog();self.assertTrue(self.gateway.ready);self.assertNotIn(n,self.gateway.pending)
 def test_stop_ack_supersedes_old_ping(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  ping,_=self.gateway.write('P');stop,_=self.gateway.stop()
  self.gateway.receive('ACK:{},OK'.format(stop['sequence']))
  self.assertNotIn(ping['sequence'],self.gateway.pending)
 def test_newer_ping_ack_does_not_hide_missing_drive_ack(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  drive,_=self.gateway.write('D',255,0,0);n=drive['sequence'];self.gateway.pending[n]=(time.monotonic()-.413,'D')
  ping,_=self.gateway.write('P');self.gateway.receive('ACK:{},OK'.format(ping['sequence']))
  self.gateway.watchdog();self.assertFalse(self.gateway.ready)
  self.assertEqual(self.gateway.link_events[-1]['code'],'ACK_TIMEOUT')
 def test_rejected_newer_frame_does_not_supersede_ping(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  ping,_=self.gateway.write('P');drive,_=self.gateway.write('D',255,0,0)
  self.gateway.receive('ACK:{},MODE'.format(drive['sequence']))
  self.assertIn(ping['sequence'],self.gateway.pending)
 def test_crc(self):
  data=frame(123,4,'D',255,130,0);body,crc=data[1:].strip().split(b'*')
  self.assertEqual(int(crc,16),binascii.crc_hqx(body,0xffff))
if __name__=='__main__':unittest.main()
