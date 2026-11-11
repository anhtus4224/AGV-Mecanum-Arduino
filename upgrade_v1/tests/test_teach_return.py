import time
import unittest
from teach_return import TeachReturn, clearance_problem
import test_gateway as gateway_fixture


class EngineTests(unittest.TestCase):
    def trace(self):
        t=TeachReturn();t.begin(0,('real',1,'lease'),200)
        now=0
        for vector in [(255,0,0),(0,255,0),(0,-255,0),(0,255,0),(255,0,0)]:
            for i in range(10):
                t.command(now,vector);now+=.1
            t.command(now,(0,0,0))
        t.finish(now)
        return t,now

    def test_example_reverse_order_preserves_body_strafe(self):
        t,now=self.trace();original=list(t.segments)
        t.start(now,('real',1,'lease'),200,2.)
        self.assertEqual([v for dt,v in t.plan[1:]], [v for dt,v in reversed(original)])
        self.assertEqual(t.plan[0][1],(0,0,102))
        self.assertEqual([v for dt,v in t.plan[1:] if any(v)],[(255,0,0),(0,255,0),(0,-255,0),(0,255,0),(255,0,0)])

    def test_rotation_sign_is_reversed(self):
        t=TeachReturn();t.begin(0,'ctx',80);t.command(0,(0,0,-255));t.command(.1,(255,0,0));t.command(.2,(0,0,0));t.finish(.2)
        t.start(.3,'ctx',80,1.)
        self.assertEqual(t.plan[-1][1],(0,0,255))

    def test_expired_setpoint_not_recorded_as_continued_motion(self):
        t=TeachReturn();t.begin(0,'ctx',80);t.command(0,(255,0,0));t.finish(5.)
        self.assertEqual(t.segments,[(.25,(255,0,0))])

    def test_calibration_context_and_cap_required(self):
        t,now=self.trace()
        for ctx,cap,seconds in [('other',200,2),(t.context,80,2),(t.context,200,None),(t.context,200,float('nan')),(t.context,200,True)]:
            with self.assertRaises(ValueError):t.start(now,ctx,cap,seconds)
        self.assertFalse(t.active)

    def test_stall_invalidates_and_does_not_resume(self):
        t,now=self.trace();t.start(now,t.context,200,1.)
        self.assertEqual(t.step(now),(0,0,102))
        self.assertEqual(t.step(now+.21),(0,0,0));self.assertFalse(t.valid)
        self.assertIsNone(t.step(now+.22))

    def test_bound_and_cancel(self):
        t=TeachReturn();t.begin(0,'ctx',80);t.command(601,(255,0,0));self.assertFalse(t.valid)
        t,now=self.trace();t.start(now,t.context,200,1.);t.cancel('STOP');self.assertFalse(t.active or t.valid)

    def test_directional_collision_and_turn_guards(self):
        raw={'F':100,'B':100,'L':999,'R':8}
        self.assertIsNone(clearance_problem((255,-255,0),raw,.1))
        self.assertIsNotNone(clearance_problem((0,255,0),raw,.1))
        self.assertIsNotNone(clearance_problem((0,0,80),raw,.1))
        self.assertIsNotNone(clearance_problem((255,0,0),raw,.36))
        self.assertIsNone(clearance_problem((0,0,0),{},None))
        self.assertIsNotNone(clearance_problem((255,0,0),raw,.1,{'F':300}))
        self.assertIsNone(clearance_problem((255,0,0),raw,.1,{'F':100}))


class IntegrationTests(unittest.TestCase):
    setUp=gateway_fixture.Tests.setUp
    def req(self,client,path,data=None,controller='browser_123'):
        if path=='/control/teach' and data and data.get('action') not in ('status','cancel'):
            data=dict(data,sequence=self.gateway.web_sequence.get(self.gateway.owner,0)+1,ticket=self.gateway.issue_ticket())
        return gateway_fixture.Tests.req(self,client,path,data,controller)
    claim=gateway_fixture.Tests.claim
    vector=gateway_fixture.Tests.vector

    def prepare(self):
        self.claim();self.g['drawing_stopped']=lambda:True
        self.g['state'].update(vector_status={'cap':200},firmware_revision='AVOID_DIRECTIONAL_V4',sonar_raw={'F':100,'B':100,'L':100,'R':100},sonar_received_monotonic=time.monotonic())
        self.g['state']['vector_range']={'raw':self.g['state']['sonar_raw'],'ages_ms':dict.fromkeys('FBLR',0),'received':time.monotonic()}
        self.assertEqual(self.req(self.a,'/control/teach',{'action':'begin'}).status_code,200)
        t=self.gateway.teach;now=time.monotonic()
        t.command(now,(255,0,0));t.command(now+.1,(0,0,0));t.finish(now+.1)
        return self.req(self.a,'/control/teach',{'action':'return','turn_seconds':1.,'calibrated':True})

    def test_start_needs_stop_calibration_and_exclusive_owner(self):
        self.claim()
        self.assertEqual(self.req(self.a,'/control/teach',{'action':'begin'}).status_code,409)
        self.assertEqual(self.prepare().status_code,200)
        before=len(self.port.data)
        self.assertEqual(self.req(self.a,'/control/vector',self.vector(5)).status_code,409)
        self.assertEqual(len(self.port.data),before)
        self.assertEqual(self.req(self.b,'/control/teach',{'action':'return','calibrated':True,'turn_seconds':1}).status_code,409)

    def test_stop_cancels_without_restart(self):
        self.prepare();self.assertTrue(self.gateway.teach.active)
        self.gateway.stop();self.assertFalse(self.gateway.teach.active or self.gateway.teach.valid)
        count=len(self.port.data);self.gateway.watchdog()
        self.assertFalse(any(b',D,' in x for x in self.port.data[count:]))

    def test_lease_generation_cap_link_changes_cancel(self):
        for case in ('lease','generation','cap','link'):
            self.setUp();self.prepare();self.assertTrue(self.gateway.teach.active)
            if case=='lease':self.gateway.owner_until=0
            elif case=='generation':self.g['drive_generation']+=1
            elif case=='cap':self.g['state']['vector_status']['cap']=255
            elif case=='link':self.gateway.link_fault('TEST','test link lost')
            self.gateway.watchdog();self.assertFalse(self.gateway.teach.active or self.gateway.teach.valid)

    def test_clearance_and_scheduler_stream(self):
        self.prepare();now=time.monotonic();self.gateway.watchdog(now)
        self.assertTrue(any(b',D,0,0,102,' in x for x in self.port.data))
        self.g['state']['sonar_raw']['R']=8
        self.gateway.watchdog(now+.09)
        self.assertFalse(self.gateway.teach.active)
        self.assertIn(b',S,',self.port.data[-1])

    def test_stop_fences_a_delayed_return_request(self):
        self.prepare();self.gateway.stop()
        # Restore a valid saved endpoint solely for this request-fencing test.
        t=self.gateway.teach;t.valid=True
        seq=self.gateway.web_sequence.get(self.gateway.owner,0)+1
        body={'action':'return','calibrated':True,'turn_seconds':1.,'sequence':seq,'ticket':self.gateway.issue_ticket()}
        self.a.get('/mecanum_control?estop=1&controller=browser_123&sequence='+str(seq+1),headers=self.auth)
        before=len(self.port.data)
        response=gateway_fixture.Tests.req(self,self.a,'/control/teach',body)
        self.assertEqual(response.status_code,409);self.assertFalse(t.active)
        self.assertEqual(len(self.port.data),before)

    def test_pause_segment_does_not_cancel_return(self):
        self.prepare();t=self.gateway.teach;now=time.monotonic()
        t.plan=[(.1,(0,0,0)),(.1,(255,0,0))];t.index=0;t.deadline=now+.1;t.last_tick=now;t.last_send=-1e9
        self.gateway.watchdog(now)
        self.assertTrue(t.active);self.assertTrue(any(b',D,0,0,0,' in x for x in self.port.data))
        self.gateway.watchdog(now+.11);self.assertTrue(t.active)
        self.assertTrue(any(b',D,255,0,0,' in x for x in self.port.data))

    def test_avoiding_snapshot_at_fault_is_retained(self):
        self.gateway.receive('AVOID_GUARD:123,4,-1,53,49,999,8,10,50,90,20')
        self.gateway.receive('AVOID_FAULT:CLEARANCE')
        self.assertEqual(self.g['state']['avoid_guard']['phase'],4)
        self.assertEqual(self.g['state']['avoid_guard']['right_cm'],8)
