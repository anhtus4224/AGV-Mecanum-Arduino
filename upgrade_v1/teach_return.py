"""Bounded, volatile manual command recording and experimental timed retracing.

No encoder/heading feedback is available: this replays commands, not positions.
The caller holds its controller lock and supplies a monotonic clock.
"""
import math


class TeachReturn:
    MAX_SECONDS = 600.
    MAX_SEGMENTS = 6000

    def __init__(self):
        self.segments = []
        self.recording = False
        self.active = False
        self.reason = 'Chưa ghi đường'
        self.context = None
        self.cap = None
        self.current = (0, 0, 0)
        self.at = 0.
        self.last_command = 0.
        self.plan = []
        self.index = 0
        self.deadline = 0.
        self.last_tick = 0.
        self.last_send = 0.
        self.valid = False

    def snapshot(self):
        return dict(recording=self.recording, active=self.active, valid=self.valid,
                    segments=len(self.segments), seconds=round(sum(s[0] for s in self.segments), 3),
                    step=self.index, steps=len(self.plan), cap=self.cap, message=self.reason,
                    method='command_time_estimate', measured=False)

    def _append(self, duration, vector):
        if duration <= 0:
            return
        if self.segments and self.segments[-1][1] == vector:
            self.segments[-1] = (self.segments[-1][0] + duration, vector)
        else:
            self.segments.append((duration, vector))
        if len(self.segments) > self.MAX_SEGMENTS or sum(s[0] for s in self.segments) > self.MAX_SECONDS:
            self.invalidate('Đường vượt giới hạn 10 phút / 6000 đoạn; ghi lượt ngắn hơn')

    def _close(self, now):
        # Firmware expires a D setpoint after 250 ms. Never record a network
        # gap as continued driving. STOP intervals between gestures are retained.
        if any(self.current):
            end = min(now, self.last_command + .25)
            self._append(max(0., end-self.at), self.current)
            if now > end:
                self._append(now-end, (0, 0, 0))
        else:
            self._append(max(0., now-self.at), self.current)
        self.at = now

    def begin(self, now, context, cap):
        self.__init__()
        self.context = context
        self.cap = cap
        self.recording = self.valid = True
        self.at = self.last_command = now
        self.reason = 'Đang ghi lệnh lái tay; vệt và khoảng cách là ước lượng'

    def command(self, now, vector):
        if not self.recording:
            return
        self._close(now)
        self.current = tuple(vector)
        self.last_command = now

    def finish(self, now):
        if self.recording:
            self._close(now)
        self.recording = False
        while self.segments and not any(self.segments[-1][1]):
            self.segments.pop()
        while self.segments and not any(self.segments[0][1]):
            self.segments.pop(0)
        self.current = (0, 0, 0)
        if not self.segments:
            self.valid = False
        self.reason = 'Đã chốt đường ước lượng' if self.valid else 'Chưa có đường hợp lệ'

    def invalidate(self, reason):
        self.valid = self.recording = self.active = False
        self.reason = reason
        self.current = (0, 0, 0)

    def cancel(self, reason):
        # After any partial return the robot is no longer at the saved endpoint.
        if self.active:
            self.invalidate(reason + '; cần đưa xe về điểm cuối hoặc ghi đường mới')

    def start(self, now, context, cap, turn_seconds):
        if self.recording or not self.valid or not self.segments:
            raise ValueError('Dừng ghi và chốt một đường hợp lệ trước')
        if context != self.context or cap != self.cap:
            raise ValueError('Điểm đầu/môi trường/PWM đã đổi; cần ghi đường mới')
        if type(turn_seconds) not in (int, float) or not math.isfinite(turn_seconds) or not .2 <= turn_seconds <= 30:
            raise ValueError('Nhập thời gian quay 180° đã đo tại PWM 80 (0,2–30 giây)')
        # Use PWM 80 for the initial turn independently of the recorded cap.
        turn = min(255, int(round(80.*255/cap)))
        self.plan = [(float(turn_seconds), (0, 0, turn))]
        # Rotating the BODY frame by pi preserves translation signs when time
        # is reversed; angular velocity changes sign. Do not negate strafe.
        self.plan += [(dt, (f, s, -r)) for dt, (f, s, r) in reversed(self.segments)]
        self.active = True
        self.index = 0
        self.deadline = now + self.plan[0][0]
        self.last_tick = now
        self.last_send = -1e9
        self.reason = 'Đang quay về theo lệnh/thời gian; chưa có định vị đo'

    def step(self, now):
        if not self.active:
            return None
        if now-self.last_tick > .2 or now < self.last_tick:
            self.cancel('Nhịp điều khiển bị gián đoạn')
            return (0, 0, 0)
        self.last_tick = now
        if now >= self.deadline:
            # Never skip a whole short segment to catch up after a stall.
            self.index += 1
            if self.index >= len(self.plan):
                self.active = self.valid = False
                self.reason = 'Đã phát hết lệnh quay về; kiểm tra vị trí thực trước lượt mới'
                return (0, 0, 0)
            self.deadline = now + self.plan[self.index][0]
            self.last_send = -1e9
        if now-self.last_send < .08:
            return None
        self.last_send = now
        return self.plan[self.index][1]


def clearance_problem(vector, raw, age, ray_ages=None, margin=12):
    """Only commanded directions, plus all four sides during a body rotation.

    Fresh no-return is unknown, not a numeric distance. This experimental policy
    accepts it for a translational ray; a turn requires four finite clear rays
    because the entire rectangular footprint sweeps around its center.
    """
    if not any(vector):
        return None
    if age is None or not 0 <= age < .35:
        return 'Dữ liệu sonar quá cũ'
    f, s, r = vector
    directions = list('FBLR') if r else (['F' if f > 0 else 'B'] if f else []) + (['R' if s > 0 else 'L'] if s else [])
    for direction in directions:
        if ray_ages is not None:
            ray_age=ray_ages.get(direction)
            if type(ray_age) is not int or ray_age<0 or age+ray_age/1000. >= .35:
                return 'Số đo {} quá cũ'.format(direction)
        value = raw.get(direction)
        limit = 30 if r else margin
        if type(value) is not int or value <= 3 or (value == 999 and r) or (value != 999 and not limit < value < 400):
            return 'Khoảng hở {} chưa đủ / chưa xác nhận'.format(direction)
    return None
