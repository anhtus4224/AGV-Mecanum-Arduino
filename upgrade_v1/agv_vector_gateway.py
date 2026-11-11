"""VECTOR1 wire protocol and authenticated single-owner Web gateway. Python 3.6+."""
import binascii
import hmac
import math
import os
import secrets
import threading
import time
from flask import request, jsonify, Response, session
from teach_return import TeachReturn, clearance_problem


def frame(sid, sequence, op, f=0, right=0, rot=0, ttl=250):
    payload='V1,{},{},{},{},{},{},{}'.format(sid,sequence,op,f,right,rot,ttl)
    return ('@{}*{:04X}\n'.format(payload,binascii.crc_hqx(payload.encode('ascii'),0xffff))).encode('ascii')


class Gateway:
    def __init__(self, g):
        self.g=g
        self.lock=g['serial_lock']
        self.sid=secrets.randbelow(0x7ffffffe)+1
        self.seq=0; self.pending={};self.owner=None;self.owner_until=0
        self.user=os.environ.get('AGV_WEB_USER','')
        self.password=os.environ.get('AGV_WEB_PASSWORD','')
        self.last_ping=0;self.last_motion=0;self.stopped=True;self.ready=False
        self.csrf=secrets.token_urlsafe(24)
        self.web_sequence={}
        self.owner_lease=""
        self.tickets={}
        self.link_reason=""
        self.link_events=[]
        self.teach=TeachReturn()
        self.return_start_heading=None

    def write(self,op,f=0,right=0,rot=0):
        with self.lock:
            port=self.g.get('ser')
            if port is None or not port.is_open or (not self.ready and op!='H'):
                return {'status':'error','msg':'Mega VECTOR1 chưa sẵn sàng','sent':False},503
            self.seq+=1
            data=frame(self.sid,self.seq,op,f,right,rot)
            # Register before write: serial RX may observe ACK before write() returns.
            self.pending[self.seq]=(time.monotonic(),op)
            if len(self.pending)>64:self.pending.pop(min(self.pending))
            try:
                if port.write(data)!=len(data): raise IOError('Short write')
            except Exception as exc:
                self.pending.pop(self.seq,None)
                self.link_fault('WRITE_ERROR',str(exc))
                self.ready=False;self.g['clear_link'](self.link_reason);return {'msg':'Lỗi USB','sent':False},503
            if op=='S':
                self.teach.cancel('Đã DỪNG')
                self.teach.command(time.monotonic(),(0,0,0))
                self.stopped=True
            if op=='D' and not self.teach.active:self.teach.command(time.monotonic(),(f,right,rot))
            if op in ('D','A'):self.stopped=False
            if op=='D':
                self.g['state']['last_drive_request']={'sequence':self.seq,'vector_pwm':[f,right,rot],
                    'at_monotonic_ms':round(time.monotonic()*1000)}
            return {'status':'sent','sent':True,'acknowledged':False,'sequence':self.seq,'command':op},200

    def stop(self):
        return self.write('S')

    def legacy_command(self,command):
        if command=='Z':return self.stop()
        if command=='M':return self.write('A' if self.g['state']['mode']!='TỰ HÀNH' else 'M')
        vectors={'F':(255,0,0),'B':(-255,0,0),'L':(0,-255,0),'R':(0,255,0),'Q':(0,0,-255),'E':(0,0,255)}
        if command not in vectors:return {'msg':'Lệnh không hỗ trợ'},400
        return self.write('D',*vectors[command])

    def receive(self,line):
        now=time.monotonic()
        if line.startswith('ACK:'):
            try:
                seq,status=line[4:].split(',');seq=int(seq)
            except ValueError:return
            with self.lock:
                old=self.pending.pop(seq,None)
                if old:
                    ack={'sequence':seq,'status':status,'op':old[1]}
                    self.g['state']['vector_ack']=ack
                    if old[1]=='D':self.g['state']['last_drive_ack']=dict(ack)
                    if old[1]=='H' and status=='OK':self.ready=True;self.g['link_ready']=True
                    if status=='OK':
                        # D is a replaceable setpoint, not a queued motion job.
                        # A newer accepted setpoint/STOP/mode supersedes older D frames.
                        # PING alone never proves a drive/STOP was accepted.
                        stale_ping=[n for n,entry in self.pending.items() if n<seq and entry[1]=='P']
                        stale_drive=[n for n,entry in self.pending.items()
                                     if n<seq and entry[1]=='D' and old[1] in ('D','S','A','M')]
                        for n in stale_ping+stale_drive:self.pending.pop(n,None)
                        if stale_ping:
                            self.g['state']['ping_ack_superseded']=self.g['state'].get('ping_ack_superseded',0)+len(stale_ping)
                        if stale_drive:
                            self.g['state']['drive_ack_superseded']=self.g['state'].get('drive_ack_superseded',0)+len(stale_drive)
                    if status!='OK':
                        returning=self.teach.active
                        self.teach.invalidate('Mega từ chối lệnh: '+status)
                        self.g['state']['serial_error']='Mega từ chối: '+status
                        if returning:self.stop()
            return
        if line=='AGV:VECTOR1':return
        if line.startswith('VECTOR_BUILD:') and line[13:] in ('AVOID_DIRECTIONAL_V3','AVOID_DIRECTIONAL_V4'):
            self.g['state']['firmware_revision']=line[13:];return
        if line.startswith('VECTOR_RANGE:'):
            try:
                values=list(map(int,line[13:].split(',')))
                if (len(values)==9 and 0<=values[0]<=0xffffffff
                        and all(0<=x<=999 for x in values[1:5])
                        and all(0<=x<=0xffffffff for x in values[5:])):
                    self.g['state']['vector_range']={'board_ms':values[0],
                        'raw':dict(zip('FBLR',values[1:5])),
                        'ages_ms':dict(zip('FBLR',values[5:9])),'received':now}
            except ValueError:pass
            return
        if line.startswith('AVOID_GUARD:'):
            try:
                values=list(map(int,line[12:].split(',')))
                if len(values)==11:
                    self.g['state']['avoid_guard']=dict(zip(('board_ms','phase','side','front_cm','back_cm','left_cm','right_cm','front_age_ms','back_age_ms','left_age_ms','right_age_ms'),values))
            except ValueError:pass
            return
        if line.startswith('VECTOR_STATE:'):
            try:
                phase,cap,armed=map(int,line[13:].split(','))
                self.g['state']['vector_status']={'phase':phase,'cap':cap,'armed':bool(armed)}
            except ValueError:pass
            return
        if line.startswith('AVOID_FAULT:'):
            self.g['state']['avoid_fault']=line[12:];return
        if line.startswith('AVOID_POLICY:'):
            try:
                values=list(map(int,line[13:].split(',')))
                if (len(values) in (4,5) and 0<=values[0]<=0xffffffff
                        and values[1] in (0,1,2) and 0<=values[2]<=15 and 40<=values[3]<=255
                        and (len(values)==4 or values[4] in (0,1))):
                    self.g['state']['avoid_policy']={'board_ms':values[0],
                        'selection_mode':values[1], 'candidate_mask':values[2],
                        'profile_cap':values[3],
                        'unknown_selected_side_allowed':bool(values[4]) if len(values)==5 else None}
            except ValueError:pass
            return
        if line.startswith('AVOID_SAMPLES:'):
            try:
                values=list(map(int,line[14:].split(',')))
                if (len(values) in (6,7) and 0<=values[0]<=0xffffffff
                        and 0<=values[2]<=values[1]<=3 and 0<=values[4]<=values[3]<=3
                        and values[5]==24000 and (len(values)==6 or values[6]==24000)):
                    self.g['state']['avoid_samples']={'board_ms':values[0],
                        'left_total':values[1],'left_valid':values[2],
                        'right_total':values[3],'right_valid':values[4],
                        'stationary_timeout_us':values[5],
                        'fixed_range_timeout_us':values[6] if len(values)==7 else None}
            except ValueError:pass
            return
        if line.startswith('AVOID_SCAN:'):
            try:
                values=list(map(int,line[11:].split(',')))
                if (len(values)==7 and 0<=values[0]<=0xffffffff
                        and all(0<=v<=9999 for v in values[1:5])
                        and 0<=values[5]<=9 and values[6] in (-1,0,1)):
                    self.g['state']['avoid_scan']={
                        'board_ms':values[0], 'left_cm':values[1], 'right_cm':values[2],
                        'diag_left_cm':values[3], 'diag_right_cm':values[4],
                        'phase_after_choice':values[5], 'chosen_side':values[6],
                        'received_monotonic_ms':round(now*1000)}
                    if values[5]==4:
                        self.g['state']['avoid_fault']=None
                        self.g['state']['avoid_guard']=None
            except ValueError:pass
            return
        if line.startswith('VECTOR_TARGET:'):
            try:
                values=list(map(int,line[14:].split(',')))
                if len(values)==5 and all(-255<=v<=255 for v in values[1:]):
                    self.g['state']['firmware_target']={'sequence':values[0],'wheels':values[1:],
                        'at_monotonic_ms':round(now*1000)}
            except ValueError:pass
            return
        old_motion=self.g.get('motion_feedback')
        old_sonar=self.g['state'].get('sonar_raw')
        self.g['parse_mega_line'](line)
        current=self.g.get('motion_feedback')
        if current is not None and current is not old_motion:
            self.last_motion=current['received']
            if any(current['wheels']):
                self.g['state']['last_nonzero_pwm']={'wheels':list(current['wheels']),'received':current['received']}
        if self.g['state'].get('sonar_raw') is not old_sonar:self.g['state']['sonar_received_monotonic']=now

    def link_fault(self,code,message,details=None):
        # Persist cause through reconnect; never log credentials, frames, leases or tickets.
        self.link_reason=message
        event={'code':code,'message':message,'at_monotonic_ms':round(time.monotonic()*1000), 'details':details or {}}
        with self.lock:
            self.teach.invalidate('Mất liên kết: '+code)
            self.link_events.append(event);self.link_events=self.link_events[-8:]
            self.g['state']['vector_link_events']=list(self.link_events)

    def serial_worker(self):
        import glob
        serial=self.g['serial']
        while True:
            port=None;was_connected=False;self.link_reason='';self.ready=False;self.g['clear_link']('Chờ Mega VECTOR1; không dùng firmware cũ')
            self.g['state'].pop('firmware_revision',None)
            try:
                if serial is None:raise RuntimeError('Cần python3-serial')
                names=[os.environ['AGV_PORT']] if os.environ.get('AGV_PORT') else sorted(glob.glob('/dev/ttyUSB*')+glob.glob('/dev/ttyACM*'))
                if not names:raise RuntimeError('Chưa có USB')
                # Specify AGV_PORT/by-id if more than one serial device is attached.
                if len(names)!=1:raise RuntimeError('Nhiều USB: đặt AGV_PORT chính xác')
                port=serial.Serial(names[0],115200,timeout=.02,write_timeout=.1,exclusive=True)
                time.sleep(2)
                # '?' is inert in the supplied legacy firmware. Never probe it with @HELLO.
                deadline=time.monotonic()+3;last_probe=0;found=False
                while time.monotonic()<deadline:
                    if time.monotonic()-last_probe>.3:port.write(b'?');last_probe=time.monotonic()
                    line=port.readline(256).decode('ascii',errors='replace').strip()
                    if line=='AGV:VECTOR1':found=True;break
                if not found:raise RuntimeError('Không có VECTOR1: giữ xe dừng, kiểm tra đúng cặp firmware')
                with self.lock:
                    self.g['ser']=port;self.sid=secrets.randbelow(0x7ffffffe)+1;self.seq=0;self.pending.clear()
                    self.g['firmware_seen']=True
                    self.write('H')
                deadline=time.monotonic()+1
                while not self.ready and time.monotonic()<deadline:self.receive(port.readline(256).decode('ascii',errors='replace').strip())
                if not self.ready:raise RuntimeError('Mega không xác nhận HELLO')
                was_connected=True
                self.stopped=True;self.g['state'].update(port=os.path.basename(names[0]),serial_error='')
                self.last_motion=time.monotonic()
                while self.ready:
                    line=port.readline(512).decode('ascii',errors='replace').strip()
                    if line:
                        try:self.receive(line)
                        except (ValueError,TypeError,OverflowError):pass
                    self.watchdog()
            except Exception as exc:
                self.link_fault('SERIAL_EXCEPTION',str(exc))
                self.g['state']['serial_error']=str(exc)
            finally:
                with self.lock:
                    self.ready=False
                    # Failed discovery must not repeatedly revoke a Web lease.
                    # A real established link loss still revokes real-vehicle control.
                    if was_connected and self.g['driving_environment']=='real':
                        self.owner=None;self.owner_until=0
                    if port:
                        try:port.write(b'Z');port.close()
                        except Exception:pass
                    self.g['ser']=None;self.g['clear_link'](self.link_reason or 'VECTOR1 bị ngắt; cần nhận quyền lại')
            time.sleep(1)

    def watchdog(self,now=None):
        now=time.monotonic() if now is None else now
        with self.lock:
            alive=self.owner is not None and now<self.owner_until
            if self.teach.active and (not alive or self.teach.context!=self.teach_context() or self.g['state'].get('mode')!='LÁI TAY' or (self.g['state'].get('vector_status') or {}).get('cap')!=self.teach.cap):
                self.teach.cancel('Quyền lái/chế độ/phiên vẽ đã đổi');self.stop()
            if self.teach.recording and (not alive or self.teach.context!=self.teach_context() or self.g['state'].get('mode')!='LÁI TAY'):
                if not alive:reason='Hết quyền lái trong khi ghi (không nhận gia hạn trong 0,8 giây)'
                elif self.teach.context[0]!=self.g['driving_environment']:reason='Đổi môi trường trong khi ghi'
                elif self.teach.context[1]!=self.g['drive_generation']:reason='Đặt lại phiên vẽ trong khi ghi'
                elif self.teach.context[2]!=self.owner_lease:reason='Quyền lái được cấp lại trong khi ghi'
                else:reason='Chế độ vừa đổi: '+str(self.g['state'].get('mode'))
                self.teach.invalidate(reason)
            if self.g['driving_environment']=='simulation':
                if not alive:
                    self.owner=None;self.g['simulation_vector']=[0.,0.,0.]
                return
            late_ack=any(now-start>.4 for start,op in self.pending.values())
            if not alive or now-self.last_motion>.4 or late_ack:
                if not self.stopped:self.stop()
                if not alive:self.owner=None
                if now-self.last_motion>.4 or late_ack:
                    if late_ack:
                        pending=[{'sequence':n,'op':op,'age_ms':round((now-start)*1000)} for n,(start,op) in self.pending.items() if now-start>.4]
                        self.link_fault('ACK_TIMEOUT','Phần mềm đóng liên kết: quá hạn ACK',{'pending':pending[:8],'last_ack':dict(self.g['state'].get('vector_ack') or {}),'motion_age_ms':round((now-self.last_motion)*1000)})
                    else:
                        self.link_fault('MOTION_TIMEOUT','Phần mềm đóng liên kết: phản hồi PWM quá cũ',{'age_ms':round((now-self.last_motion)*1000)})
                    self.ready=False;self.owner=None;self.owner_until=0
            else:
                if self.teach.active:
                    old_step=self.teach.index
                    vector=self.teach.step(now)
                    if old_step==0 and self.teach.index==1 and self.teach.active:
                        anchor=self.g.get('teach_heading_anchor')
                        if anchor and self.return_start_heading is not None:anchor(self.return_start_heading+180.)
                    if vector is not None:
                        ranges=self.g['state'].get('vector_range') or {}
                        age=now-ranges.get('received',-1e9)
                        problem=clearance_problem(vector,ranges.get('raw',{}),age,ranges.get('ages_ms',{}))
                        if problem:
                            self.teach.cancel(problem);self.stop()
                        elif self.teach.active:self.write('D',*vector)
                        else:self.stop()
                if now-self.last_ping>=.2:
                    self.last_ping=now;self.write('P')

    def teach_context(self):
        return (self.g['driving_environment'],self.g['drive_generation'],self.owner_lease)

    def teach_stopped(self):
        check=self.g.get('drawing_stopped')
        return bool(check and check())

    def issue_ticket(self):
        now=time.monotonic()
        self.tickets={k:v for k,v in self.tickets.items() if now-v[0]<=.3}
        if len(self.tickets)>=8:self.tickets.pop(next(iter(self.tickets)))
        token=secrets.token_urlsafe(24)
        self.tickets[token]=(now,self.owner_lease,self.g['driving_environment'],self.g['drive_generation'])
        return token

    def identity(self):
        client=request.args.get('controller','')
        if not 8<=len(client)<=64 or not client.replace('_','').replace('-','').isalnum():return None
        return (session['viewer'],client)

    def has_lease(self):
        # Recheck inside the endpoint's lock: ownership can change after before_request.
        return (self.identity()==self.owner and time.monotonic()<self.owner_until
                and hmac.compare_digest(request.headers.get('X-AGV-Lease',''),self.owner_lease))

    def install(self,app):
        app.secret_key=secrets.token_bytes(32)
        app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',MAX_CONTENT_LENGTH=16384)
        @app.before_request
        def protect():
            auth=request.authorization
            if not self.user or len(self.password)<12:
                return jsonify(error='Đặt AGV_WEB_USER và AGV_WEB_PASSWORD tối thiểu 12 ký tự trước khi chạy'),503
            if not auth or not hmac.compare_digest((auth.username or '').encode('utf-8'),self.user.encode('utf-8')) or not hmac.compare_digest((auth.password or '').encode('utf-8'),self.password.encode('utf-8')):
                return Response('Cần đăng nhập AGV',401,{'WWW-Authenticate':'Basic realm="AGV"'})
            if 'viewer' not in session:session['viewer']=secrets.token_urlsafe(20)
            path=request.path
            mutation=path not in ('/','/telemetry','/video_feed','/map/export','/control/diagnostics')
            if not mutation:return None
            if not hmac.compare_digest(request.headers.get('X-AGV-CSRF',''),self.csrf):return jsonify(error='Thiếu xác thực thao tác; tải lại trang',msg='CSRF'),403
            who=self.identity()
            with self.lock:
                if path=='/control/claim':return None
                # Any authenticated viewer may explicitly STOP. Other viewers' lifecycle events are suppressed by UI.
                stop=path=='/mecanum_control' and request.args.get('estop')=='1'
                if stop:
                    if request.args.get('scope')=='owner' and not self.has_lease():
                        return jsonify(status='ignored_old_owner')
                    try: seq=int(request.args.get('sequence','0'))
                    except ValueError:return jsonify(msg='Sequence không hợp lệ'),400
                    if who is not None:self.web_sequence[who]=max(seq,self.web_sequence.get(who,0))
                    if who!=self.owner:self.owner=None;self.owner_until=0
                    self.tickets.clear()
                    self.g['simulation_vector']=[0.,0.,0.]
                    # Keep authorization/fencing and the actual STOP atomic with
                    # respect to claim/release/vector on other Flask threads.
                    return app.view_functions[request.endpoint]()
                if who is None or who!=self.owner or time.monotonic()>=self.owner_until or not hmac.compare_digest(request.headers.get('X-AGV-Lease',''),self.owner_lease):
                    return jsonify(error='Bạn chưa có quyền lái hoặc quyền đã hết hạn',msg='Chưa có quyền lái'),409
                if path in ('/toggle_mode','/drive/environment','/drive/reset-estimate','/drive/reset-simulation','/control/profile'):
                    if self.teach.active:self.teach.cancel('Thay đổi chế độ/cấu hình');self.stop()
                    if self.teach.recording:self.teach.invalidate('Thay đổi chế độ/cấu hình trong khi ghi')
                if path=='/toggle_mode':
                    try: seq=int(request.args.get('sequence','0'))
                    except ValueError:return jsonify(msg='Sequence không hợp lệ'),400
                    if seq<=self.web_sequence.get(who,0):return jsonify(status='ignored_stale')
                    self.web_sequence[who]=seq
                self.owner_until=time.monotonic()+.8
        @app.after_request
        def headers(response):
            response.headers['Cache-Control']='no-store'
            response.headers['X-Content-Type-Options']='nosniff'
            response.headers['X-Frame-Options']='DENY'
            return response
        @app.route('/control/diagnostics')
        def diagnostics():
            with self.lock:
                now=time.monotonic();m=self.g.get('motion_feedback')
                wheels=m['wheels'] if m else None
                electrical=[-wheels[0],wheels[1],-wheels[2],wheels[3]] if wheels else None
                return jsonify(gateway_revision='AVOID_DIRECTIONAL_V4',ready=self.ready,port=self.g['state'].get('port'),
                    firmware_revision=self.g['state'].get('firmware_revision'),
                    motion_age_ms=round((now-m['received'])*1000) if m else None,
                    current_pwm=m['wheels'] if m else None,
                    wheel_order=['FL','FR','RL','RR'],
                    requested_vector=self.g['state'].get('last_drive_request'),
                    firmware_target=self.g['state'].get('firmware_target'),
                    driver_pwm=electrical,driver_pwm_source='derived from MOTION and unchanged drive polarity; not measured pins',
                    avoid_fault=self.g['state'].get('avoid_fault'),
                    avoid_scan=self.g['state'].get('avoid_scan'),
                    avoid_samples=self.g['state'].get('avoid_samples'),
                    avoid_policy=self.g['state'].get('avoid_policy'),
                    avoid_guard=self.g['state'].get('avoid_guard'),
                    vector_range=self.g['state'].get('vector_range'),
                    teach_return=self.teach.snapshot(),
                    vector_status=self.g['state'].get('vector_status'),
                    last_drive_ack=self.g['state'].get('last_drive_ack'),
                    last_nonzero_pwm=self.g['state'].get('last_nonzero_pwm'),
                    link_events=list(self.link_events),
                    drawing_lost=self.g.get('visual_sessions',{}).get('real',{}).get('lost'))
        @app.route('/control/claim',methods=['POST'])
        def claim():
            who=self.identity()
            if who is None:return jsonify(msg='Controller không hợp lệ'),400
            with self.lock:
                now=time.monotonic()
                if self.owner is not None and now<self.owner_until and who!=self.owner:return jsonify(msg='Người khác đang lái'),409
                if self.teach.recording:self.teach.invalidate('Nhận quyền lại; ghi đường mới')
                if self.ready:
                    result,code=self.stop()
                    if code!=200:return jsonify(result),code
                self.owner=who;self.owner_until=now+.8;self.web_sequence={};self.owner_lease=secrets.token_urlsafe(24);self.tickets={}
                return jsonify(status='owner',lease=self.owner_lease,msg='Đã nhận quyền; các phím cũ đã được bỏ')
        @app.route('/control/renew',methods=['POST'])
        def renew():
            with self.lock:
                if not self.has_lease():return jsonify(msg='Quyền lái đã hết'),409
                return jsonify(status='owner',ticket=self.issue_ticket(),teach_return=self.teach.snapshot())
        @app.route('/control/release',methods=['POST'])
        def release():
            with self.lock:
                if not self.has_lease():return jsonify(msg='Quyền lái đã hết'),409
                if self.teach.recording:self.teach.invalidate('Đã nhả quyền trong khi ghi')
                self.stop();self.g['simulation_vector']=[0.,0.,0.];self.owner=None;self.owner_until=0;self.tickets.clear()
            return jsonify(status='released')
        @app.route('/control/profile',methods=['POST'])
        def profile():
            body=request.get_json(silent=True) or {}
            if self.g['driving_environment']!='real':return jsonify(msg='Profile motor chỉ dành cho Xe thật'),409
            if not isinstance(body,dict):return jsonify(msg='Cần JSON object'),400
            if body.get('confirmed') is not True:return jsonify(msg='Cần xác nhận khu vực thử và kích thước xe'),400
            cap=body.get('cap');armed=body.get('armed')
            if type(cap) is not int or cap not in (80,120,160,200,255) or type(armed) is not bool:return jsonify(msg='Profile không hợp lệ'),400
            result,code=self.write('E',int(armed),cap,0);return jsonify(result),code
        @app.route('/control/teach',methods=['POST'])
        def teach():
            body=request.get_json(silent=True) or {}
            if not isinstance(body,dict):return jsonify(msg='Cần JSON object'),400
            with self.lock:
                if not self.has_lease():return jsonify(msg='Quyền lái đã hết'),409
                action=body.get('action')
                if action=='status':return jsonify(dict(self.teach.snapshot(),stopped=self.teach_stopped()))
                if action=='cancel':
                    self.teach.cancel('Người lái hủy quay về');self.stop()
                    return jsonify(self.teach.snapshot())
                sequence=body.get('sequence')
                if type(sequence) is not int or not 1<=sequence<=9007199254740991:
                    return jsonify(msg='Thiếu thứ tự thao tác ghi/quay về'),400
                if sequence<=self.web_sequence.get(self.identity(),0):
                    return jsonify(msg='Thao tác cũ đã bị DỪNG hủy'),409
                token=body.get('ticket')
                issued=self.tickets.pop(token,None) if isinstance(token,str) else None
                if (issued is None or issued[1:]!=(self.owner_lease,self.g['driving_environment'],self.g['drive_generation'])
                        or not 0<=time.monotonic()-issued[0]<=.3):
                    return jsonify(msg='Thao tác tới quá chậm / đã bị hủy; thử lại'),409
                self.web_sequence[self.identity()]=sequence
                if self.g['driving_environment']!='real' or not self.teach_stopped():
                    return jsonify(msg='Cần Xe thật, LÁI TAY và phản hồi STOP/PWM 0 mới'),409
                profile=self.g['state'].get('vector_status') or {}
                cap=profile.get('cap')
                if cap not in (80,120,160,200,255):return jsonify(msg='Chưa nhận PWM cap từ Mega'),409
                if action=='begin':
                    self.teach.begin(time.monotonic(),self.teach_context(),cap)
                elif action=='finish':self.teach.finish(time.monotonic())
                elif action=='return':
                    if body.get('calibrated') is not True:
                        return jsonify(msg='Cần đo thời gian quay 180° tại PWM 80 và xác nhận trước'),400
                    if self.g['state'].get('firmware_revision')!='AVOID_DIRECTIONAL_V4':
                        return jsonify(msg='Cần firmware V4 cho phản hồi và gác an toàn cùng phiên bản'),409
                    try:self.teach.start(time.monotonic(),self.teach_context(),cap,body.get('turn_seconds'))
                    except ValueError as exc:return jsonify(msg=str(exc)),400
                    with self.g.get('map_lock',self.lock):
                        self.return_start_heading=self.g.get('visual_sessions',{}).get('real',{}).get('theta')
                    self.tickets.clear()
                else:return jsonify(msg='Thao tác ghi đường không hợp lệ'),400
                return jsonify(self.teach.snapshot())
        @app.route('/control/vector',methods=['POST'])
        def vector():
            body=request.get_json(silent=True) or {}
            if not isinstance(body,dict):return jsonify(msg='Cần JSON object'),400
            try:
                v=[float(body[k]) for k in ('drive','strafe','rotate')]
                if any(type(body[k]) is bool for k in ('drive','strafe','rotate')) or not all(math.isfinite(x) and -1<=x<=1 for x in v):raise ValueError()
                sequence=body['sequence']
                if type(sequence) is not int or not 1<=sequence<=9007199254740991:
                    return jsonify(msg='Thứ tự lệnh không hợp lệ',code='SEQUENCE'),400
            except (ValueError,TypeError,KeyError,OverflowError):
                return jsonify(msg='Vector phải có ba số hữu hạn trong [-1,1]',code='VECTOR'),400
            with self.lock:
                key=self.identity()
                if not self.has_lease():return jsonify(msg='Quyền lái đã hết'),409
                if self.teach.active:return jsonify(msg='Đang quay về; nhấn DỪNG trước khi lái tay'),409
                if self.teach.recording and self.teach.cap!=(self.g['state'].get('vector_status') or {}).get('cap'):
                    self.teach.invalidate('PWM cap đã đổi trong khi ghi')
                old=self.web_sequence
                if sequence<=old.get(key,0):return jsonify(status='ignored_stale')
                if body.get('environment')!=self.g['driving_environment'] or body.get('generation')!=self.g['drive_generation']:
                    return jsonify(msg='Môi trường vừa đổi; nhả điều khiển rồi thử lại',code='CONTEXT'),409
                token=body.get('ticket')
                issued=self.tickets.pop(token,None) if isinstance(token,str) else None
                if issued is None or issued[1:]!=(self.owner_lease,self.g['driving_environment'],self.g['drive_generation']):
                    return jsonify(msg='Phiếu lệnh không hợp lệ; tải lại trang và nhận quyền',code='TICKET'),409
                if not 0<=time.monotonic()-issued[0]<=.3:
                    return jsonify(msg='Gói điều khiển tới quá chậm (>300 ms); đã dừng. Nhận quyền lại khi mạng ổn định',code='COMMAND_EXPIRED',age_ms=round((time.monotonic()-issued[0])*1000)),409
                old[key]=sequence;self.web_sequence={key:sequence}
                if self.g['driving_environment']=='simulation':
                    self.g['simulation_vector']=v;self.g['simulation_vector_at']=time.monotonic()
                    return jsonify(status='simulation',command='VECTOR',ticket=self.issue_ticket())
                if self.g['state']['mode']!='LÁI TAY' or not self.g['auto_or_manual_fresh']():return jsonify(msg='Cần LÁI TAY và dữ liệu Mega mới'),409
                result,code=self.write('D',*[int(round(x*255)) for x in v])
                if code==200:
                    result['ticket']=self.issue_ticket()
                    result['teach_return']=self.teach.snapshot()
                return jsonify(result),code
