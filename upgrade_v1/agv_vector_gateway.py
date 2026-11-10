"""VECTOR1 wire protocol and authenticated single-owner Web gateway. Python 3.6+."""
import binascii
import hmac
import math
import os
import secrets
import threading
import time
from flask import request, jsonify, Response, session


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

    def write(self,op,f=0,right=0,rot=0):
        with self.lock:
            port=self.g.get('ser')
            if port is None or not port.is_open or (not self.ready and op!='H'):
                return {'status':'error','msg':'Mega VECTOR1 chưa sẵn sàng','sent':False},503
            self.seq+=1
            data=frame(self.sid,self.seq,op,f,right,rot)
            try:
                if port.write(data)!=len(data): raise IOError('Short write')
            except Exception:
                self.ready=False;self.g['clear_link']('Lỗi ghi VECTOR1');return {'msg':'Lỗi USB','sent':False},503
            self.pending[self.seq]=(time.monotonic(),op)
            if len(self.pending)>64:self.pending.pop(min(self.pending))
            if op=='S':self.stopped=True
            if op in ('D','A'):self.stopped=False
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
            old=self.pending.pop(seq,None)
            if old:
                self.g['state']['vector_ack']={'sequence':seq,'status':status,'op':old[1]}
                if old[1]=='H' and status=='OK':self.ready=True;self.g['link_ready']=True
                if status!='OK':self.g['state']['serial_error']='Mega từ chối: '+status
            return
        if line=='AGV:VECTOR1':return
        if line.startswith('VECTOR_STATE:'):
            try:
                phase,cap,armed=map(int,line[13:].split(','))
                self.g['state']['vector_status']={'phase':phase,'cap':cap,'armed':bool(armed)}
            except ValueError:pass
            return
        if line.startswith('AVOID_FAULT:'):
            self.g['state']['avoid_fault']=line[12:];return
        old_motion=self.g.get('motion_feedback')
        old_sonar=self.g['state'].get('sonar_raw')
        self.g['parse_mega_line'](line)
        current=self.g.get('motion_feedback')
        if current is not None and current is not old_motion:self.last_motion=current['received']
        if self.g['state'].get('sonar_raw') is not old_sonar:self.g['state']['sonar_received_monotonic']=now

    def serial_worker(self):
        import glob
        serial=self.g['serial']
        while True:
            port=None;was_connected=False;self.ready=False;self.g['clear_link']('Chờ Mega VECTOR1; không dùng firmware cũ')
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
            except Exception as exc:self.g['state']['serial_error']=str(exc)
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
                    self.g['ser']=None;self.g['clear_link']('VECTOR1 bị ngắt; cần nhận quyền lại')
            time.sleep(1)

    def watchdog(self,now=None):
        now=time.monotonic() if now is None else now
        with self.lock:
            alive=self.owner is not None and now<self.owner_until
            if self.g['driving_environment']=='simulation':
                if not alive:
                    self.owner=None;self.g['simulation_vector']=[0.,0.,0.]
                return
            late_ack=any(now-start>.4 for start,op in self.pending.values())
            if not alive or now-self.last_motion>.4 or late_ack:
                if not self.stopped:self.stop()
                if not alive:self.owner=None
                if now-self.last_motion>.4 or late_ack:
                    self.ready=False;self.owner=None;self.owner_until=0
            elif now-self.last_ping>=.2:
                self.last_ping=now;self.write('P')

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
            mutation=path not in ('/','/telemetry','/video_feed','/map/export')
            if not mutation:return None
            if not hmac.compare_digest(request.headers.get('X-AGV-CSRF',''),self.csrf):return jsonify(error='Thiếu xác thực thao tác; tải lại trang',msg='CSRF'),403
            who=self.identity()
            with self.lock:
                if path=='/control/claim':return None
                # Any authenticated viewer may explicitly STOP. Other viewers' lifecycle events are suppressed by UI.
                stop=path=='/mecanum_control' and request.args.get('estop')=='1'
                if stop:
                    try: seq=int(request.args.get('sequence','0'))
                    except ValueError:return jsonify(msg='Sequence không hợp lệ'),400
                    if who is not None:self.web_sequence[who]=max(seq,self.web_sequence.get(who,0))
                    if who!=self.owner:self.owner=None;self.owner_until=0
                    self.g['simulation_vector']=[0.,0.,0.]
                    return None
                if who is None or who!=self.owner or time.monotonic()>=self.owner_until or not hmac.compare_digest(request.headers.get('X-AGV-Lease',''),self.owner_lease):
                    return jsonify(error='Bạn chưa có quyền lái hoặc quyền đã hết hạn',msg='Chưa có quyền lái'),409
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
        @app.route('/control/claim',methods=['POST'])
        def claim():
            who=self.identity()
            if who is None:return jsonify(msg='Controller không hợp lệ'),400
            with self.lock:
                now=time.monotonic()
                if self.owner is not None and now<self.owner_until and who!=self.owner:return jsonify(msg='Người khác đang lái'),409
                if self.ready:
                    result,code=self.stop()
                    if code!=200:return jsonify(result),code
                self.owner=who;self.owner_until=now+.8;self.web_sequence={};self.owner_lease=secrets.token_urlsafe(24);self.tickets={}
                return jsonify(status='owner',lease=self.owner_lease,msg='Đã nhận quyền; các phím cũ đã được bỏ')
        @app.route('/control/renew',methods=['POST'])
        def renew():
            with self.lock:return jsonify(status='owner',ticket=self.issue_ticket())
        @app.route('/control/release',methods=['POST'])
        def release():
            with self.lock:self.stop();self.owner=None;self.owner_until=0
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
                if key!=self.owner or time.monotonic()>=self.owner_until:return jsonify(msg='Quyền lái đã hết'),409
                old=self.web_sequence
                if sequence<=old.get(key,0):return jsonify(status='ignored_stale')
                if body.get('environment')!=self.g['driving_environment'] or body.get('generation')!=self.g['drive_generation']:
                    return jsonify(msg='Môi trường vừa đổi; nhả điều khiển rồi thử lại',code='CONTEXT'),409
                token=body.get('ticket')
                issued=self.tickets.pop(token,None) if isinstance(token,str) else None
                if issued is None or issued[1:]!=(self.owner_lease,self.g['driving_environment'],self.g['drive_generation']):
                    return jsonify(msg='Phiếu lệnh không hợp lệ; tải lại trang và nhận quyền',code='TICKET'),409
                if not 0<=time.monotonic()-issued[0]<=.3:
                    return jsonify(msg='Gói điều khiển tới quá chậm (>300 ms); đã dừng. Nhận quyền lại khi mạng ổn định',code='COMMAND_EXPIRED'),409
                old[key]=sequence;self.web_sequence={key:sequence}
                if self.g['driving_environment']=='simulation':
                    self.g['simulation_vector']=v;self.g['simulation_vector_at']=time.monotonic()
                    return jsonify(status='simulation',command='VECTOR')
                if self.g['state']['mode']!='LÁI TAY' or not self.g['auto_or_manual_fresh']():return jsonify(msg='Cần LÁI TAY và dữ liệu Mega mới'),409
                result,code=self.write('D',*[int(round(x*255)) for x in v]);return jsonify(result),code
