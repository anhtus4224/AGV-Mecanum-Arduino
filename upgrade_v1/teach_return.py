"""Bounded, volatile manual command recording and experimental timed retracing.

No encoder/heading feedback is available: this replays commands, not positions.
The caller holds its controller lock and supplies a monotonic clock.
"""
import math
import time


TRANSLATION_CLEARANCE_CM = 10
# Body 47 x 34 cm: corner radius ~29 cm. Extra swept reach at an
# edge-mounted head is ~12 cm F/B, ~5.5 cm L/R; add ~8 cm margin.
TURN_CLEARANCE_CM = {'F':20, 'B':20, 'L':14, 'R':14}


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
        self.invalid_reason = None
        self.events = []
        self.turn_space_confirmed = False
        self.last_guard = None

    def snapshot(self):
        return dict(revision="TEACH_RETURN_INDOOR_V2", guard_policy=dict(translation_cm=TRANSLATION_CLEARANCE_CM, turn_cm=dict(TURN_CLEARANCE_CM), unknown_turn_allowed=self.turn_space_confirmed), last_guard=self.last_guard, invalid_reason=self.invalid_reason, events=list(self.events),
                    recording=self.recording, active=self.active, valid=self.valid,
                    segments=len(self.segments), seconds=round(sum(s[0] for s in self.segments), 3),
                    step=self.index, steps=len(self.plan), cap=self.cap, message=self.reason,
                    method='command_time_estimate', measured=False)

    def event(self, kind, message):
        self.events.append(dict(event=kind, message=message, at_monotonic_ms=round(time.monotonic()*1000)))
        self.events=self.events[-8:]

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
        self.event('BEGIN',self.reason)

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
        if not self.valid:
            # finish() must not hide the event that invalidated a partial trace.
            self.reason = self.invalid_reason or ('Chưa bắt đầu ghi đường; bấm Đặt điểm đầu + ghi đường trước khi lái' if self.cap is None else 'Lượt ghi không hợp lệ; cần ghi đường mới')
            self.event('FINISH_REJECTED',self.reason)
            return
        while self.segments and not any(self.segments[-1][1]):
            self.segments.pop()
        while self.segments and not any(self.segments[0][1]):
            self.segments.pop(0)
        self.current = (0, 0, 0)
        if not self.segments:
            self.valid = False
        self.reason = 'Đã chốt đường ước lượng' if self.valid else 'Chưa ghi được đoạn chuyển động nào'
        self.event('FINISH',self.reason)

    def invalidate(self, reason):
        if self.invalid_reason is None:
            self.invalid_reason=reason
        self.event('INVALIDATED',reason)
        self.valid = self.recording = self.active = False
        self.reason = self.invalid_reason
        self.current = (0, 0, 0)

    def cancel(self, reason):
        # After any partial return the robot is no longer at the saved endpoint.
        if self.active:
            self.invalidate(reason + '; cần đưa xe về điểm cuối hoặc ghi đường mới')

    def start(self, now, context, cap, turn_seconds, turn_space_confirmed=False):
        if self.recording or not self.valid or not self.segments:
            raise ValueError(self.invalid_reason or 'Dừng ghi và chốt một đường hợp lệ trước')
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
        self.turn_space_confirmed = turn_space_confirmed is True
        self.last_guard = None
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


def clearance_problem(vector, raw, age, ray_ages=None, margin=TRANSLATION_CLEARANCE_CM, allow_unknown_turn=False):
    """Only commanded directions, plus all four sides during a body rotation.

    A fresh no-return remains unknown, not a numeric free-space measurement.
    Operator confirmation of the swept area permits unknown rays during turns.
    Too-close measured returns, malformed values and stale rays always stop.
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
        limit = TURN_CLEARANCE_CM[direction] if r else margin
        if type(value) is not int or value <= 3 or (value == 999 and r and not allow_unknown_turn) or (value != 999 and not limit < value < 400):
            if value==999:return 'Sonar {} không echo; chưa xác nhận khoảng trống quay'.format(direction)
            return 'Sonar {}: {} cm, cần lớn hơn {} cm'.format(direction,value,limit)
    return None
