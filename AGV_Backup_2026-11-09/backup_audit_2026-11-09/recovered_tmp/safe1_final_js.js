
        // ---------------------------------------------------------------------
        // KHỞI TẠO THREE.JS WEBGL CHUẨN VỚI ORBIT CONTROLS
        // ---------------------------------------------------------------------
        let carGroup = {position: {set() {}}, rotation: {z: 0}};
let addPathPoint = () => {};
let clearLine = () => {};
function resetOrigin() { fetch('/reset_origin').then(() => clearLine()); }
try {
const mapApi = (() => {
const container = document.getElementById('canvas3d-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x020617);

        const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
        camera.position.set(0, -60, 45);
        camera.up.set(0, 0, 1); // Trục Z hướng lên trên

        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.08;
        controls.maxPolarAngle = Math.PI / 2 - 0.05; // Không cho xoay chìm dưới mặt đất

        // Lưới 3D chuẩn màu xanh đậm và xanh ngọc
        const gridHelper = new THREE.GridHelper(120, 30, 0x00e5ff, 0x142038);
        gridHelper.rotation.x = Math.PI / 2;
        scene.add(gridHelper);

        // Ánh sáng
        const ambLight = new THREE.AmbientLight(0xffffff, 0.8);
        scene.add(ambLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
        dirLight.position.set(20, -30, 40);
        scene.add(dirLight);

        // Mô hình xe AGV Mecanum 3D
        const carGroup = new THREE.Group();

        // Khối thân xe màu cam
        const bodyGeo = new THREE.BoxGeometry(7, 11, 3.2);
        const bodyMat = new THREE.MeshLambertMaterial({ color: 0xf59e0b });
        const carBody = new THREE.Mesh(bodyGeo, bodyMat);
        carBody.position.z = 1.6;
        carGroup.add(carBody);

        // Mũi tên chỉ hướng tiến màu xanh ngọc
        const arrowGeo = new THREE.ConeGeometry(1.8, 3.2, 3);
        const arrowMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff });
        const arrowMesh = new THREE.Mesh(arrowGeo, arrowMat);
        arrowMesh.position.set(0, 6.2, 2.2);
        arrowMesh.rotation.z = Math.PI;
        arrowMesh.rotation.x = Math.PI / 2;
        carGroup.add(arrowMesh);

        scene.add(carGroup);

        // Đường vẽ Line lịch sử
        const maxPoints = 3000;
        const lineGeo = new THREE.BufferGeometry();
        const positions = new Float32Array(maxPoints * 3);
        lineGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const lineMat = new THREE.LineBasicMaterial({ 
    color: 0x00ffff,       // Đổi sang màu Cyan sáng rực (xanh dạ quang nổi bật trên nền đen)
    linewidth: 5, 
    transparent: true, 
    opacity: 1.0 
});
        const pathLine = new THREE.Line(lineGeo, lineMat);
        scene.add(pathLine);

        let ptCount = 0;
        function addPathPoint(x, y) {
            if (ptCount < maxPoints) {
                positions[ptCount * 3]     = x;
                positions[ptCount * 3 + 1] = y;
                positions[ptCount * 3 + 2] = 0.2;
                ptCount++;
                lineGeo.setDrawRange(0, ptCount);
                lineGeo.attributes.position.needsUpdate = true;
            }
        }

        function clearLine() {
            ptCount = 0;
            lineGeo.setDrawRange(0, 0);
            lineGeo.attributes.position.needsUpdate = true;
        }

        function resetOrigin() {
            fetch('/reset_origin').then(() => { clearLine(); });
        }

        window.addEventListener('resize', () => {
            camera.aspect = container.clientWidth / container.clientHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(container.clientWidth, container.clientHeight);
        });

        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        animate();

        // ---------------------------------------------------------------------
        // MODAL TUNING POPUP
        // ---------------------------------------------------------------------
        return {carGroup, addPathPoint, clearLine};
})();
carGroup = mapApi.carGroup;
addPathPoint = mapApi.addPathPoint;
clearLine = mapApi.clearLine;
} catch (err) {
document.getElementById('canvas3d-container').innerText = '3D chưa tải được. Điều khiển USB vẫn hoạt động.';
console.warn(err);
}
window.openTuningModal = function() {
            const m = document.getElementById('tuningModal');
            if (m) m.style.display = 'flex';
            fetch('/telemetry').then(r => r.json()).then(d => {
                let t = d.tuning || {};
                if (document.getElementById('cfg_obs'))  document.getElementById('cfg_obs').value  = t.obs_cm || 22;
                if (document.getElementById('cfg_spd'))  document.getElementById('cfg_spd').value  = t.avoid_spd || 160;
                if (document.getElementById('cfg_out'))  document.getElementById('cfg_out').value  = t.avoid_out_ms || 3300;
                if (document.getElementById('cfg_fwd'))  document.getElementById('cfg_fwd').value  = t.avoid_fwd_ms || 5400;
                if (document.getElementById('cfg_back')) document.getElementById('cfg_back').value = t.avoid_back_ms || 2300;
                if (document.getElementById('cfg_fast')) document.getElementById('cfg_fast').value = t.fast_spd || 190;
            }).catch(e => console.log(e));
        };

        window.closeTuningModal = function() {
            const m = document.getElementById('tuningModal');
            if (m) m.style.display = 'none';
        };

        window.saveTuningData = function() {
            let payload = {
                obs_cm: parseInt(document.getElementById('cfg_obs').value),
                avoid_spd: parseInt(document.getElementById('cfg_spd').value),
                avoid_out_ms: parseInt(document.getElementById('cfg_out').value),
                avoid_fwd_ms: parseInt(document.getElementById('cfg_fwd').value),
                avoid_back_ms: parseInt(document.getElementById('cfg_back').value),
                base_spd: 120,
                fast_spd: parseInt(document.getElementById('cfg_fast').value)
            };
            fetch('/save_tuning', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            }).then(r => r.json()).then(res => {
                alert(res.msg);
                closeTuningModal();
            });
        };

        // ---------------------------------------------------------------------
        // TELEMETRY & ĐỒNG BỘ 3D
        // ---------------------------------------------------------------------
        setInterval(() => {
            fetch('/telemetry').then(r => r.json()).then(d => {
                document.getElementById('val_pos').innerText = 'CHƯA CÓ ODOM';
                document.getElementById('val_deg').innerText = '—';
                document.getElementById('val_spd').innerText = 'CHƯA ĐO';
                document.getElementById('val_dist').innerText = '—';
                document.getElementById('val_volt').innerText = d.battery.toFixed(1) + ' V';
                let showMode = d.mode || 'LÁI TAY';
        document.getElementById('val_mode').innerText = showMode;
        document.getElementById('val_act').innerText = d.action;
        document.getElementById('stat_mode').innerText = 'CHẾ ĐỘ: ' + showMode;

                let pEl = document.getElementById('val_port');
                pEl.innerText = d.port;
                pEl.style.color = (d.port !== 'DISCONNECTED') ? '#00ff88' : '#ef4444';
                document.getElementById('port_txt').innerText = d.port;
                document.getElementById('stat_conn').style.color = d.connected ? '#00ff88' : '#ef4444';
                document.getElementById('stat_conn').title = d.serial_error || '';

                let setS = (id, v) => {
                    let el = document.getElementById(id);
                    el.innerText = v + ' cm';
                    el.style.color = (v <= 25) ? '#ff0055' : ((v <= 50) ? '#f59e0b' : '#00ff88');
                };
                setS('snr_f', d.sonar.F);
                setS('snr_b', d.sonar.B);
                setS('snr_l', d.sonar.L);
                setS('snr_r', d.sonar.R);

                let l = d.line || '00000';
                for (let i = 0; i < 5; i++) {
                    let eye = document.getElementById('eye' + i);
                    if (l[i] === '1') eye.classList.add('active');
                    else eye.classList.remove('active');
                }

                // Cập nhật vị trí và góc quay Three.js
                carGroup.position.set(d.x, d.y, 0);
                carGroup.rotation.z = d.angle * Math.PI / 180;

                if (d.current_speed > 0.02 || Math.abs(d.omega) > 0.05) {
                    addPathPoint(d.x, d.y);
                }
            }).catch(() => { document.getElementById('port_txt').innerText = 'SERVER MẤT KẾT NỐI'; document.getElementById('stat_conn').style.color = '#ef4444'; });
        }, 40);

        // ---------------------------------------------------------------------
        // ĐIỀU KHIỂN BÀN PHÍM PHẦN CỨNG & CHUỘT
        // ---------------------------------------------------------------------
        function driveCmd(d, s, r) {
            fetch('/mecanum_control?drive=' + d + '&strafe=' + s + '&rotate=' + r);
        }
        function stopCmd() {
            stopKeyLoop();
            if (activeBtnTimer) { clearInterval(activeBtnTimer); activeBtnTimer = null; }
            fetch('/mecanum_control?drive=0&strafe=0&rotate=0&estop=1');
        }

        // ======================================================================
// CƠ CHẾ REPEATABLE 80MS ĐỒNG BỘ 100% CẤU HÌNH APP ĐIỀU KHIỂN
// ======================================================================
let activeKeyTimer = null;
let currentPressedKey = null;

const KEY_COMMANDS = {
    'KeyW': [1, 0, 0],    // Tiến
    'KeyS': [-1, 0, 0],   // Lùi
    'KeyA': [0, -1, 0],   // Dạt trái
    'KeyD': [0, 1, 0],    // Dạt phải
    'KeyQ': [0, 0, -1],   // Xoay trái
    'KeyE': [0, 0, 1]     // Xoay phải
};

function sendCurrentKey() {
    if (currentPressedKey && KEY_COMMANDS[currentPressedKey]) {
        let [d, s, r] = KEY_COMMANDS[currentPressedKey];
        driveCmd(d, s, r);
    }
}

function stopKeyLoop() {
    if (activeKeyTimer) {
        clearInterval(activeKeyTimer);
        activeKeyTimer = null;
    }
    currentPressedKey = null;
}

// 1. KHI NHẤN GIỮ PHÍM: BẮN GÓI ĐẦU TIÊN TỨC THÌ & LẶP MỖI 80MS ĐỂ NUÔI FAILSAFE
window.addEventListener('keydown', (e) => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
    if (KEY_COMMANDS[e.code] || ['Space', 'KeyZ', 'KeyX'].includes(e.code)) e.preventDefault();
    if (e.code === 'Space' || e.code === 'KeyZ') {
        stopKeyLoop();
        stopCmd();
        return;
    }
    if (e.code === 'KeyX' && !e.repeat) {
        fetch('/toggle_mode');
        return;
    }

    if (KEY_COMMANDS[e.code]) {
        if (currentPressedKey === e.code) return; // Đang giữ phím này rồi thì để timer 80ms tự lo
        
        currentPressedKey = e.code;
        sendCurrentKey(); // Bắn ngay lệnh đầu tiên dưới 5ms

        if (activeKeyTimer) clearInterval(activeKeyTimer);
        activeKeyTimer = setInterval(sendCurrentKey, 80); // Lặp lại đúng chu kỳ 80ms của App
    }
});

// 2. KHI NHẢ TAY KHỎI BÀN PHÍM: HỦY TIMER VÀ PHANH DỪNG XE TỨC KHẮC
window.addEventListener('keyup', (e) => {
    if (KEY_COMMANDS[e.code] && currentPressedKey === e.code) {
        stopKeyLoop();
        stopCmd(); // Gửi lệnh phanh 'S' về Arduino
    }
});

// Chống kẹt phím nếu người dùng click chuột ra ngoài hoặc chuyển tab
window.addEventListener('blur', () => {
    if (activeBtnTimer) { clearInterval(activeBtnTimer); activeBtnTimer = null; }
    stopKeyLoop();
    stopCmd();
});

const BTN_MAP = {
    'W': () => driveCmd(1, 0, 0),     // Tiến
    'B': () => driveCmd(-1, 0, 0),    // Lùi
    'A': () => driveCmd(0, -1, 0),    // Ngang Trái (chuẩn theo data-act="A")
    'D': () => driveCmd(0, 1, 0),     // Ngang Phải (chuẩn theo data-act="D")
    'L': () => driveCmd(0, -1, 0),    // Dự phòng data-act="L"
    'R': () => driveCmd(0, 1, 0),     // Dự phòng data-act="R"
    'Q': () => driveCmd(0, 0, -1),    // Xoay Trái
    'E': () => driveCmd(0, 0, 1)      // Xoay Phải
};

    // ======================================================================
    // BỘ ĐẾM LẶP 80MS CHO NÚT BẤM CHUỘT VÀ CẢM ỨNG ĐIỆN THOẠI
    // ======================================================================
    let activeBtnTimer = null;

    function startBtnHold(act) {
        if (activeBtnTimer) clearInterval(activeBtnTimer);
        if (BTN_MAP[act]) {
            BTN_MAP[act](); // Bắn gói lệnh đầu tiên tức thì
            activeBtnTimer = setInterval(() => {
                BTN_MAP[act](); // Bơm lệnh liên tục mỗi 80ms để duy trì chạy
            }, 80);
        }
    }

    function stopBtnHold() {
        if (activeBtnTimer) {
            clearInterval(activeBtnTimer);
            activeBtnTimer = null;
        }
        stopCmd(); // Gửi lệnh dừng phanh xe ngay khi nhả tay
    }

    document.querySelectorAll('.ctrl-btn').forEach(btn => {
        let act = btn.getAttribute('data-act');
        if (act === 'X') {
            btn.onclick = () => fetch('/toggle_mode');
        } else if (act === 'Z' || act === 'S') {
            btn.onclick = () => stopCmd();
        } else if (BTN_MAP[act]) {
            // Xử lý giữ/nhả chuột trên Máy tính (Laptop)
            btn.onmousedown = (e) => { e.preventDefault(); startBtnHold(act); };
            btn.onmouseup = (e) => { e.preventDefault(); stopBtnHold(); };
            btn.onmouseleave = (e) => { e.preventDefault(); stopBtnHold(); };

            // Xử lý chạm/giữ/nhả bằng ngón tay trên Điện thoại
            btn.ontouchstart = (e) => { e.preventDefault(); startBtnHold(act); };
            btn.ontouchend = (e) => { e.preventDefault(); stopBtnHold(); };
            btn.ontouchcancel = (e) => { e.preventDefault(); stopBtnHold(); };
        }
    });
    