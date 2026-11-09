"""Read-only/STOP link verification; motor power OFF, server service stopped."""
import sys, time
import serial
port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
ready = False
count = 0
with serial.Serial(port,115200,timeout=0.2,write_timeout=0.5,exclusive=True) as ser:
    start = time.monotonic(); last_ping = 0; buf = bytearray()
    try:
        while time.monotonic() - start < 8:
            now = time.monotonic()
            if now - last_ping >= 0.4:
                ser.write(b'@PING\n' if ready else b'@HELLO\n'); last_ping = now
            buf.extend(ser.read(256))
            while b'\n' in buf:
                raw, _, tail = buf.partition(b'\n'); buf = bytearray(tail)
                line = raw.rstrip(b'\r').decode('ascii',errors='replace')
                if line == 'AGV:SAFE1':
                    ready = True; ser.write(b'@STOP\n'); print(line)
                elif line.startswith(('ACK:', '>> HOST_', '>> HB ')):
                    print(line)
                elif line.startswith('DATA:'):
                    count += 1
                    if count <= 3: print(line)
        print('PASS handshake + telemetry' if ready and count else 'FAIL: cần Mega SAFE1, đúng cổng, đúng115200')
    finally:
        if ready: ser.write(b'@STOP\n')
