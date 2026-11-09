"""Load the real Flask routes without camera/serial threads or hardware access."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import uuid


class NoHardwareSerial:
    is_open = True

    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)
        raise AssertionError('Reset tests must never write motor/USB commands')


def load_server():
    os.environ['AGV_MAP_DIR'] = tempfile.mkdtemp(prefix='agv-reset-test-')
    fake_serial = types.ModuleType('serial')

    def reject_port(*args, **kwargs):
        raise AssertionError('Opening physical serial ports is forbidden in tests')

    fake_serial.Serial = reject_port
    sys.modules['serial'] = fake_serial
    sys.modules['cv2'] = types.ModuleType('cv2')
    name = 'agv_reset_test_' + uuid.uuid4().hex
    source = Path(__file__).resolve().parents[1] / 'stream_server_reset_v1.py'
    spec = importlib.util.spec_from_file_location(name, str(source))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.app.config.update(TESTING=True)
    return module


def refresh_feedback(module, profile='ready'):
    now = time.monotonic()
    module.rx_time = module.mode_time = module.data_time = now
    module.firmware_seen = module.link_ready = True
    module.state.update(mode='LÁI TAY', action='STOP', mode_pending=False,
                        port='ttyUSB_TEST', line='01000', battery=12.4,
                        telemetry_valid=True, mode_confirmed=True)
    module.motion_feedback = dict(seq=1, board_ms=1000, wheels=[0, 0, 0, 0],
                                  auto=False, corner=0, avoid=False, received=now)
    if profile == 'auto':
        module.state['mode'] = 'TỰ HÀNH'
        module.motion_feedback['auto'] = True
    elif profile == 'moving':
        module.motion_feedback['wheels'] = [255, 255, 255, 255]
    elif profile == 'no_motion':
        module.motion_feedback = None
    elif profile == 'stale':
        module.data_time = now - 2
    elif profile == 'disconnected':
        module.link_ready = False


def seed_server(module):
    module.ser = NoHardwareSerial()
    module.driving_environment = 'real'
    module.drive_generation = 7
    refresh_feedback(module)
    module.plan = module.validated_plan(dict(width=2, height=3))
    module.map_pose = None
    module.map_lost = None
    module.map_markers = []
    module.map_visits = []
    module.map_recording = False
    visual = module.new_visual_session('command_estimate')
    visual.update(x=9.78, y=-.26, theta=119.3, route_heading=119.3,
                  distance=14.88, started=True, completed_corners=4,
                  segment=3, trail_revision=5,
                  corner_pending=dict(direction='E'),
                  geometry_reason='old drawing fault', lost=True,
                  trail=[dict(x=0, y=0, segment=3),
                         dict(x=9.78, y=-.26, segment=3)])
    module.visual_sessions['real'] = visual
    module.visual_sessions['simulation'] = module.new_visual_session('simulation')
    return copy.deepcopy(visual)
