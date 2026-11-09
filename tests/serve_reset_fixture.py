"""Loopback-only browser fixture. Never starts serial/camera/AGV threads."""
import copy
from wsgiref.simple_server import make_server

from flask import request, jsonify
from reset_fixture import load_server, refresh_feedback, seed_server

server = load_server()
seed_server(server)
server.visual_sessions['real'].update(lost=False, geometry_reason='', corner_pending=None)
profile = {'value': 'ready', 'reset_requests': 0, 'reset_usb_writes': 0}


def allow_only_lifecycle_stop(data):
    # The unchanged pagehide handler can send Z during browser reload/close.
    # This is a fake acknowledgement only; no real serial port exists.
    if data != b'Z':
        raise AssertionError('Browser fixture forbids every directional motor command')
    server.ser.writes.append(data)
    return len(data)


server.ser.write = allow_only_lifecycle_stop


@server.app.before_request
def test_feedback():
    refresh_feedback(server, profile['value'])
    if request.path == '/drive/reset-estimate':
        profile['reset_requests'] += 1
        request.reset_writes_before = len(server.ser.writes)


@server.app.after_request
def test_reset_writes(response):
    if request.path == '/drive/reset-estimate':
        profile['reset_usb_writes'] += len(server.ser.writes) - request.reset_writes_before
    return response


@server.app.route('/__test__/seed', methods=['POST'])
def test_seed():
    body = request.get_json(silent=True) or {}
    seed_server(server)
    server.ser.write = allow_only_lifecycle_stop
    server.visual_sessions['real'].update(lost=False, geometry_reason='', corner_pending=None)
    profile.update(value=body.get('profile', 'ready'), reset_requests=0, reset_usb_writes=0)
    return jsonify(status='seeded')


@server.app.route('/__test__/stats')
def test_stats():
    return jsonify(usb_writes=len(server.ser.writes), reset_usb_writes=profile['reset_usb_writes'], reset_requests=profile['reset_requests'])


@server.app.route('/__test__/stale')
def test_stale():
    data = server.telemetry().get_json()
    data['visualization'].update(x=9.78, y=-.26, theta=119.3, distance=14.88, generation=7)
    return jsonify(data)


if __name__ == '__main__':
    print('TEST FIXTURE ONLY: http://127.0.0.1:18765', flush=True)
    make_server('127.0.0.1', 18765, server.app).serve_forever()
