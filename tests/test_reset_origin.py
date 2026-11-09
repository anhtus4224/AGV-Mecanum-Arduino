import ast
import copy
import json
from pathlib import Path
import unittest

from reset_fixture import load_server, refresh_feedback, seed_server


class ResetOriginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server()

    def setUp(self):
        self.old_visual = seed_server(self.server)
        self.client = self.server.app.test_client()
        self.body = dict(x=0, y=0, theta=0, confirmed=True)

    def test_reset_clears_only_real_drawing_and_never_writes_usb(self):
        plan = copy.deepcopy(self.server.plan)
        simulation = copy.deepcopy(self.server.visual_sessions['simulation'])
        response = self.client.post('/drive/reset-estimate', json=self.body)
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        visual = result['visualization']
        for key in ('x', 'y', 'theta', 'distance', 'speed', 'completed_corners'):
            self.assertEqual(visual[key], 0, key)
        self.assertEqual(visual['route_heading'], 0)
        self.assertEqual(visual['trail'], [])
        self.assertEqual(visual['command'], 'Z')
        self.assertFalse(visual['moving'])
        self.assertFalse(visual['lost'])
        self.assertFalse(visual['measured'])
        self.assertIsNone(visual['corner_pending'])
        self.assertEqual(visual['geometry_reason'], '')
        self.assertEqual(visual['segment'], self.old_visual['segment'] + 1)
        self.assertEqual(visual['trail_revision'], self.old_visual['trail_revision'] + 1)
        self.assertEqual(visual['generation'], 8)
        self.assertEqual(visual['server_instance'], self.server.visual_server_id)
        self.assertEqual(self.server.plan, plan)
        self.assertEqual(self.server.visual_sessions['simulation'], simulation)
        self.assertEqual(self.server.ser.writes, [])

    def test_custom_pose_and_following_telemetry(self):
        self.body.update(x=1.25, y=-2, theta=-90)
        response = self.client.post('/drive/reset-estimate', json=self.body)
        self.assertEqual(response.status_code, 200)
        result = self.client.get('/telemetry').get_json()['visualization']
        self.assertEqual((result['x'], result['y'], result['theta']), (1.25, -2, 270))
        self.assertEqual(result['distance'], 0)

    def test_rejects_unready_conditions_without_changing_pose(self):
        for profile in ('auto', 'moving', 'no_motion', 'stale', 'disconnected'):
            with self.subTest(profile=profile):
                seed_server(self.server)
                refresh_feedback(self.server, profile)
                before = copy.deepcopy(self.server.visual_sessions['real'])
                response = self.client.post('/drive/reset-estimate', json=self.body)
                self.assertEqual(response.status_code, 409)
                self.assertTrue(response.get_json()['error'])
                self.assertEqual(self.server.visual_sessions['real'], before)
                self.assertEqual(self.server.ser.writes, [])

    def test_missing_motion_is_an_explicit_error(self):
        self.server.motion_feedback = None
        response = self.client.post('/drive/reset-estimate', json=self.body)
        self.assertIn('MOTION', response.get_json()['error'])

    def test_simulation_cannot_reset_real_session(self):
        self.server.driving_environment = 'simulation'
        response = self.client.post('/drive/reset-estimate', json=self.body)
        self.assertEqual(response.status_code, 409)
        self.assertIn('Xe thật', response.get_json()['error'])

    def test_invalid_input_and_confirmation(self):
        bad_bodies = [None, [], {}, dict(self.body, confirmed=False),
                      dict(self.body, x=True), dict(self.body, x=101),
                      dict(self.body, theta=3601), dict(self.body, y='nan'),
                      dict(self.body, x='inf'), dict(self.body, x=10**400),
                      dict(self.body, x=None)]
        for body in bad_bodies:
            with self.subTest(body=str(body)[:50]):
                seed_server(self.server)
                response = self.client.post('/drive/reset-estimate',
                                            data=json.dumps(body),
                                            content_type='application/json')
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.server.visual_sessions['real'], self.old_visual)
                self.assertEqual(self.server.ser.writes, [])

    def test_old_control_generation_is_rejected_after_reset(self):
        old_generation = self.server.drive_generation
        self.assertEqual(self.client.post('/drive/reset-estimate', json=self.body).status_code, 200)
        response = self.client.get('/mecanum_control?drive=1&environment=real&generation=' + str(old_generation))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.server.ser.writes, [])

    def test_python36_syntax(self):
        source = (Path(__file__).resolve().parents[1] / 'stream_server_reset_v1.py').read_text()
        ast.parse(source, feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main()
