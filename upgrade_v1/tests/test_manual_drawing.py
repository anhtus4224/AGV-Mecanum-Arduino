import importlib.util
import math
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


class DrawingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.dict(sys.modules,{'cv2':types.ModuleType('cv2'),'serial':types.ModuleType('serial')}), patch.dict(os.environ,{'AGV_MAP_DIR':tempfile.mkdtemp()}):
            spec=importlib.util.spec_from_file_location('manual_drawing_test_server',ROOT/'stream_server_vector_v1.py')
            cls.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.m)

    def setUp(self):
        m=self.m
        m.visual_sessions['real']=m.new_visual_session('command_estimate')
        m.motion_feedback=None;m.firmware_seen=m.link_ready=True;m.driving_environment='real'
        m.state.update(mode='LÁI TAY',mode_pending=False,action='STOP')
        m.gateway.teach.__init__();m.AUTO_LINEAR_MPS=.236;m.AUTO_STRAFE_MPS=.18;m.AUTO_TURN_RADPS=1.5

    def frame(self,seq,board,host,w=(200,200,200,200)):
        self.m.parse_motion_feedback('MOTION:'+','.join(map(str,[seq,board]+list(w)+[0,0,0])),host)

    def test_board_time_does_not_scale_with_host_packet_jitter(self):
        self.frame(1,1000,1.)
        self.frame(2,1080,1.25)
        self.frame(3,1160,1.26)
        v=self.m.visual_sessions['real']
        self.assertAlmostEqual(v['x'],.236*200/255*.16,places=12)
        self.assertEqual(v['y'],0)
        # Reading telemetry/snapshots does not move or add distance.
        before=dict(v)
        for i in range(5):self.m.presentation_snapshot();self.m.visual_tick(1.27+i*.001)
        self.assertEqual(v['x'],before['x']);self.assertEqual(v['distance'],before['distance'])

    def test_duplicate_missing_and_stale_intervals_are_not_invented(self):
        self.frame(1,1000,1.)
        self.frame(1,1000,1.01)
        self.frame(3,1160,1.16)
        v=self.m.visual_sessions['real'];self.assertEqual(v['x'],0)
        self.assertEqual(v['segment'],1)
        self.frame(4,1240,1.24);self.assertGreater(v['x'],0)
        before=v['x'];self.frame(5,1640,1.64)
        self.assertEqual(v['x'],before);self.assertEqual(v['segment'],2)

    def test_calibrated_yaw_gain_is_drawing_only(self):
        m=self.m
        self.assertTrue(m.teach_drawing_calibration(15.65))
        self.assertAlmostEqual(m.AUTO_TURN_RADPS,math.pi*255/(80*15.65))
        self.assertAlmostEqual(m.AUTO_TURN_RADPS*80/255*15.65,math.pi)
        self.assertAlmostEqual(m.AUTO_LINEAR_MPS,.236)
        self.assertAlmostEqual(m.AUTO_STRAFE_MPS,.18)
        for value in (None,True,0,float('nan'),31):self.assertFalse(m.teach_drawing_calibration(value))
        v=m.presentation_snapshot()
        self.assertEqual(v['drawing_revision'],'MEGA_TIME_MAP_V1');self.assertFalse(v['measured'])

    def test_heading_anchor_does_not_reintegrate_pre_anchor_turn_interval(self):
        m=self.m;m.teach_drawing_calibration(.3)
        self.frame(1,1000,1.,(80,-80,80,-80))
        m.teach_heading_anchor(180)
        self.frame(2,1080,1.08,(200,200,200,200))
        v=m.visual_sessions['real']
        self.assertEqual(v['theta'],180);self.assertEqual(v['heading_anchor_gap_ms'],80)
        self.assertEqual(v['x'],0)
        self.frame(3,1160,1.16,(200,200,200,200))
        self.assertLess(v['x'],0);self.assertAlmostEqual(v['y'],0,places=12)
        self.assertEqual(v['theta'],180)

    def test_constant_twist_arc_matches_analytic_curve(self):
        m=self.m;v=m.visual_sessions['real'];m.integrate_visual(v,1,0,math.pi/2,1)
        self.assertAlmostEqual(v['x'],2/math.pi,places=12)
        self.assertAlmostEqual(v['y'],2/math.pi,places=12)
        self.assertAlmostEqual(v['theta'],90,places=12)

    def test_reversed_curved_trace_closes_without_position_snapping(self):
        m=self.m;v=m.visual_sessions['real'];pieces=[(.2,0,0,2),(.1,-.1,-.6,1.4),(.1,0,.2,1.2)]
        for f,s,r,t in pieces:m.integrate_visual(v,f,s,r,t)
        v['theta']=(v['theta']+180)%360
        for f,s,r,t in reversed(pieces):m.integrate_visual(v,f,s,-r,t)
        self.assertAlmostEqual(v['x'],0,places=12);self.assertAlmostEqual(v['y'],0,places=12)
        self.assertAlmostEqual(v['theta'],180,places=12)


if __name__=='__main__':unittest.main()
