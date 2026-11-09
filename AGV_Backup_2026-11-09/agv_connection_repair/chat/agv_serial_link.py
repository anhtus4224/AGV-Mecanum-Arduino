"""Serial bridge: framed commands, explicit handshake, one owner, no auto-drive."""
import glob
import math
import os
import threading
import time
class SafeMegaLink:
    def __init__(self, state, serial_module):
        self.state, self.serial_module = state, serial_module
        self.lock = threading.RLock()
        self.port = None
        self.last_rx = 0.0
        self.last_ping = 0.0
        self.buffer = bytearray()
        self.confirmed = False
        self._reset_state()
    def _reset_state(self):
        self.state.update(port="DISCONNECTED", connected=False, mode="LÁI TAY",
                          action="STOP", fwd=0.0, strafe=0.0, omega=0.0,
                          current_speed=0.0, odometry_available=False)
    def disconnect(self, reason):
        with self.lock:
            self.confirmed = False
            if self.port is not None:
                try: self.port.close()
                except Exception: pass
            self.port = None
            self.buffer.clear()
            self._reset_state()
            self.state['serial_error'] = str(reason)
        print('[SERIAL]', reason, flush=True)
    def send(self, command):
        allowed = {'STOP', 'MODE:AUTO', 'MODE:MANUAL'} | {
            'DRIVE:' + c for c in 'FBLRQE'
        }
        if command not in allowed:
            raise ValueError('Unsupported framed command')
        with self.lock:
            if not self.confirmed or self.port is None or not self.port.is_open:
                return False
            try:
                self.port.write(('@' + command + '\n').encode('ascii'))
                return True
            except Exception as exc:
                self.disconnect('write: ' + str(exc))
                return False
    def ingest(self, line):
        now = time.monotonic()
        if line == 'AGV:SAFE1':
            with self.lock:
                self.port.write(b'@STOP\n')
                self.confirmed = True
                self.last_rx = now
                self.state.update(port=os.path.basename(self.port.port), connected=True,
                                  mode='LÁI TAY', action='STOP', serial_error='')
            return
        if not self.confirmed:
            return
        if line.startswith('DATA:'):
            p = line[5:].split(',')
            actions = {'STOP', 'FORWARD', 'BACKWARD', 'STRAFE_LEFT', 'STRAFE_RIGHT',
                       'ROTATE_LEFT', 'ROTATE_RIGHT'}
            if len(p) != 3 or len(p[0]) != 5 or set(p[0]) - {'0', '1'} or p[1] not in actions:
                return
            try: voltage = float(p[2])
            except ValueError: return
            if not math.isfinite(voltage): return
            self.state.update(line=p[0], action=p[1], battery=voltage)
            self.last_rx = now
        elif line.startswith('SONAR:'):
            try: values = [float(v) for v in line[6:].split(',')]
            except ValueError: return
            if len(values) != 4 or not all(math.isfinite(v) and v > 0 for v in values): return
            self.state['sonar'] = dict(zip('FBLR', values))
            self.last_rx = now
        elif line in ('ACK:MODE:AUTO', 'ACK:MODE:MANUAL', 'ACK:STOP'):
            self.state['mode'] = 'TỰ HÀNH' if line == 'ACK:MODE:AUTO' else 'LÁI TAY'
            if line == 'ACK:STOP': self.state['action'] = 'STOP'
            self.last_rx = now
        elif line.startswith('>> HB '):
            if 'mode=AUTO' in line: self.state['mode'] = 'TỰ HÀNH'
            elif 'mode=MANUAL' in line: self.state['mode'] = 'LÁI TAY'
            self.last_rx = now
    def consume(self, data):
        self.buffer.extend(data)
        if len(self.buffer) > 8192:
            self.buffer.clear()
            self.state['serial_error'] = 'Receive buffer overflow'
            return
        while b'\n' in self.buffer:
            raw, _, rest = self.buffer.partition(b'\n')
            self.buffer = bytearray(rest)
            try: line = raw.rstrip(b'\r').decode('ascii')
            except UnicodeDecodeError:
                self.state['serial_error'] = 'Non-ASCII serial data; inspect shared readers/cable/power'
                continue
            self.ingest(line)
    def run(self):
        if self.serial_module is None:
            self.disconnect('pyserial is not installed')
            return
        while True:
            if self.port is None:
                requested = os.environ.get('AGV_SERIAL_PORT')
                candidates = [requested] if requested else sorted(set(
                    glob.glob('/dev/serial/by-id/*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')))
                for candidate in candidates:
                    try:
                        self.buffer.clear()
                        self.port = self.serial_module.Serial(candidate, 115200, timeout=0.1,
                                                               write_timeout=0.5, exclusive=True)
                        start = time.monotonic()
                        last_hello = 0
                        while time.monotonic() - start < 4 and not self.confirmed:
                            if time.monotonic() - last_hello >= 0.5:
                                self.port.write(b'@HELLO\n')
                                last_hello = time.monotonic()
                            self.consume(self.port.read(256))
                        if self.confirmed: break
                        self.disconnect('No SAFE1 handshake on ' + candidate)
                    except Exception as exc:
                        self.disconnect(candidate + ': ' + str(exc))
                if not self.confirmed:
                    time.sleep(1)
                    continue
            try:
                now = time.monotonic()
                with self.lock:
                    if now - self.last_ping >= 0.3:
                        self.port.write(b'@PING\n')
                        self.last_ping = now
                self.consume(self.port.read(256))
                if time.monotonic() - self.last_rx > 2.5:
                    self.disconnect('Telemetry timeout; firmware watchdog will stop motion')
            except Exception as exc:
                self.disconnect('read: ' + str(exc))
                time.sleep(0.3)
