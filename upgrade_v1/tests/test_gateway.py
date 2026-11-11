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
 def test_new_drive_ack_retires_old_setpoint(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  old,_=self.gateway.write('D',255,0,0);self.gateway.pending[old['sequence']]=(time.monotonic()-.407,'D')
  new,_=self.gateway.write('D',0,255,0);self.gateway.receive('ACK:{},OK'.format(new['sequence']))
  self.gateway.watchdog();self.assertTrue(self.gateway.ready)
  self.assertNotIn(old['sequence'],self.gateway.pending)
 def test_stop_ack_retires_old_drive(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  old,_=self.gateway.write('D',255,0,0);stop,_=self.gateway.stop()
  self.gateway.receive('ACK:{},OK'.format(stop['sequence']))
  self.assertNotIn(old['sequence'],self.gateway.pending)
 def test_new_drive_ack_never_retires_missing_stop(self):
  self.claim();n=self.gateway.seq;self.gateway.pending[n]=(time.monotonic()-.407,'S')
  new,_=self.gateway.write('D',0,255,0);self.gateway.receive('ACK:{},OK'.format(new['sequence']))
  self.gateway.watchdog();self.assertFalse(self.gateway.ready)
  self.assertTrue(any(p['op']=='S' and p['sequence']==n for p in self.gateway.link_events[-1]['details']['pending']))
 def test_rejected_new_drive_does_not_retire_old_drive(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  old,_=self.gateway.write('D',255,0,0);new,_=self.gateway.write('D',0,255,0)
  self.gateway.receive('ACK:{},MODE'.format(new['sequence']))
  self.assertIn(old['sequence'],self.gateway.pending)
 def test_forward_release_strafe_with_dropped_old_ack(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  for f,right in [(255,0)]*8+[(0,0)]+[(0,255)]*8:
   result,_=self.gateway.stop() if not f and not right else self.gateway.write('D',f,right,0)
   if not f and not right or result['sequence']%5!=0:self.gateway.receive('ACK:{},OK'.format(result['sequence']))
  self.assertFalse(self.gateway.pending)
  now=time.monotonic();self.gateway.last_motion=now+.45;self.gateway.watchdog(now+.45)
  self.assertTrue(self.gateway.ready)
 def test_fresh_drive_ack_does_not_hide_stale_pwm(self):
  self.claim();self.gateway.receive('ACK:{},OK'.format(self.gateway.seq))
  drive,_=self.gateway.write('D',255,0,0);self.gateway.receive('ACK:{},OK'.format(drive['sequence']))
  self.gateway.last_motion=time.monotonic()-.5;self.gateway.watchdog()
  self.assertFalse(self.gateway.ready);self.assertEqual(self.gateway.link_events[-1]['code'],'MOTION_TIMEOUT')
 def test_continuous_vectors_use_response_ticket_without_renew(self):
  self.claim();data=self.vector(1)
  for seq in range(1,9):
   data['sequence']=seq;response=self.req(self.a,'/control/vector',data)
   self.assertEqual(response.status_code,200)
   data['ticket']=response.json['ticket']
  self.assertEqual(len(self.gateway.tickets),1)
 def test_response_ticket_still_expires_at_300ms(self):
  self.claim();response=self.req(self.a,'/control/vector',self.vector(1))
  ticket=response.json['ticket'];old=self.gateway.tickets[ticket]
  self.gateway.tickets[ticket]=(time.monotonic()-.301,)+old[1:]
  data=dict(drive=1,strafe=1,rotate=0,sequence=2,ticket=ticket,environment='real',generation=1)
  self.assertEqual(self.req(self.a,'/control/vector',data).json['code'],'COMMAND_EXPIRED')
 def test_stop_invalidates_ticket_even_with_newer_sequence(self):
  self.claim();data=self.vector(9)
  self.a.get('/mecanum_control?estop=1&scope=owner&controller=browser_123&sequence=4',headers=dict(self.auth,**{'X-AGV-Lease':self.gateway.owner_lease}))
  count=len(self.port.data)
  self.assertEqual(self.req(self.a,'/control/vector',data).json['code'],'TICKET')
  self.assertEqual(count,len(self.port.data))
 def test_late_lifecycle_stop_does_not_revoke_phone(self):
  self.claim();old=self.gateway.owner_lease
  self.req(self.a,'/control/release');self.req(self.b,'/control/claim',controller='phone_456')
  owner=self.gateway.owner;count=len(self.port.data)
  response=self.a.get('/mecanum_control?estop=1&scope=owner&controller=browser_123&sequence=99',headers=dict(self.auth,**{'X-AGV-Lease':old}))
  self.assertEqual(response.json['status'],'ignored_old_owner')
  self.assertEqual(owner,self.gateway.owner);self.assertEqual(count,len(self.port.data))
 def test_lease_change_between_auth_and_endpoint_cannot_release(self):
  @self.app.before_request
  def concurrent_reclaim():
   from flask import request
   if request.path=='/control/release':self.gateway.owner_lease='new-lease-for-same-browser'
  self.claim();owner=self.gateway.owner;count=len(self.port.data)
  response=self.req(self.a,'/control/release')
  self.assertEqual(response.status_code,409);self.assertEqual(owner,self.gateway.owner)
  self.assertEqual(count,len(self.port.data))
 def test_diagnostics_link_request_target_and_output(self):
  self.claim();self.req(self.a,'/control/vector',dict(self.vector(1),drive=0,strafe=1))
  self.gateway.receive('VECTOR_TARGET:3,80,-80,-80,80')
  self.g['motion_feedback']={'wheels':[80,-80,-80,80],'received':time.monotonic()}
  count=len(self.port.data);d=self.a.get('/control/diagnostics',headers=self.auth).json
  self.assertEqual(d['requested_vector']['vector_pwm'],[0,255,0])
  self.assertEqual(d['firmware_target']['wheels'],[80,-80,-80,80])
  self.assertEqual(d['driver_pwm'],[-80,-80,80,80]);self.assertEqual(count,len(self.port.data))
 def test_all_web_directions_reach_wire_unchanged(self):
  self.claim()
  for seq,(f,s,r) in enumerate([(1,0,0),(-1,0,0),(0,-1,0),(0,1,0),(1,-1,0),(1,1,0),(-1,-1,0),(-1,1,0),(0,0,-1),(0,0,1)],1):
   data=self.vector(seq);data.update(drive=f,strafe=s,rotate=r)
   self.assertEqual(self.req(self.a,'/control/vector',data).status_code,200)
   self.assertIn((',D,{},{},{},250*'.format(f*255,s*255,r*255)).encode(),self.port.data[-1])
 def test_avoid_scan_snapshot_survives_fault_without_usb_writes(self):
  count=len(self.port.data)
  self.gateway.receive('AVOID_SCAN:1234,71,62,999,999,9,0')
  self.gateway.receive('AVOID_FAULT:NO_CONFIRMED_CORRIDOR')
  self.gateway.receive('VECTOR_STATE:0,80,1')
  d=self.a.get('/control/diagnostics',headers=self.auth).json
  self.assertEqual(d['avoid_scan']['left_cm'],71)
  self.assertEqual(d['avoid_scan']['diag_left_cm'],999)
  self.assertEqual(d['avoid_scan']['phase_after_choice'],9)
  self.assertEqual(d['avoid_fault'],'NO_CONFIRMED_CORRIDOR')
  self.assertEqual(d['vector_status'],{'phase':0,'cap':80,'armed':True})
  self.assertEqual(count,len(self.port.data))
 def test_malformed_scan_preserves_last_snapshot_and_valid_choice_clears_fault(self):
  self.gateway.receive('AVOID_SCAN:1234,71,62,999,999,9,0')
  first=dict(self.g['state']['avoid_scan'])
  for line in ('AVOID_SCAN:x','AVOID_SCAN:1,2,3','AVOID_SCAN:1,71,62,80,80,4,99'):
   self.gateway.receive(line);self.assertEqual(self.g['state']['avoid_scan'],first)
  self.g['state']['avoid_fault']='NO_CONFIRMED_CORRIDOR'
  self.gateway.receive('AVOID_SCAN:2345,71,62,80,80,4,-1')
  self.assertIsNone(self.g['state']['avoid_fault'])
  self.assertEqual(self.g['state']['avoid_scan']['chosen_side'],-1)
 def test_sampling_snapshot_is_bounded_and_read_only(self):
  count=len(self.port.data)
  self.gateway.receive('AVOID_SAMPLES:100,3,2,3,0,24000')
  before=dict(self.g['state']['avoid_samples'])
  self.gateway.receive('AVOID_SAMPLES:101,3,4,3,0,24000')
  self.assertEqual(self.g['state']['avoid_samples'],before)
  d=self.a.get('/control/diagnostics',headers=self.auth).json
  self.assertEqual(d['avoid_samples']['left_valid'],2)
  self.assertEqual(d['avoid_samples']['right_valid'],0)
  self.assertEqual(d['gateway_revision'],'AVOID_SCAN_RETRY_V1')
  self.assertEqual(count,len(self.port.data))
 def test_crc(self):
  data=frame(123,4,'D',255,130,0);body,crc=data[1:].strip().split(b'*')
  self.assertEqual(int(crc,16),binascii.crc_hqx(body,0xffff))
if __name__=='__main__':unittest.main()
