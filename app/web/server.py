import os
import json
import base64
import threading
from flask import Flask, request, jsonify, render_template_string
from ..database.models import SpecimenModel, ColumnDefinition
from ..database.auth import AuthManager


LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign In — Biobank</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa; min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
            padding: 16px;
        }
        .login-card {
            background: white; border-radius: 16px; padding: 32px 28px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 100%; max-width: 380px;
        }
        h1 { font-size: 1.4rem; color: #1a73e8; text-align: center; margin-bottom: 4px; }
        p.sub { color: #666; text-align: center; font-size: 0.9rem; margin-bottom: 24px; }
        input {
            width: 100%; padding: 12px 14px; border: 2px solid #ddd;
            border-radius: 8px; font-size: 1rem; outline: none;
            margin-bottom: 12px; transition: border-color 0.2s;
        }
        input:focus { border-color: #1a73e8; }
        button {
            width: 100%; padding: 12px; background: #1a73e8; color: white;
            border: none; border-radius: 8px; font-size: 1rem; font-weight: 600;
            cursor: pointer; transition: background 0.2s;
        }
        button:hover { background: #1557b0; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .error { color: #e74c3c; font-size: 0.85rem; text-align: center; margin-top: 8px; display: none; }
        .error.visible { display: block; }
        .switch-btn {
            background: none; border: none; color: #1a73e8;
            font-size: 0.85rem; text-decoration: underline;
            cursor: pointer; display: block; margin: 12px auto 0;
            padding: 4px;
        }
        .switch-btn:hover { color: #1557b0; }
        .page { display: none; }
        .page.active { display: block; }
    </style>
</head>
<body>
    <div class="login-card">
        <h1>NUBRI Biobank</h1>
        <p class="sub" id="subtitle">Sign in to access specimen data</p>

        <div id="login-page" class="page active">
            <input type="email" id="email" placeholder="Email" autocomplete="email">
            <input type="password" id="password" placeholder="Password" autocomplete="current-password">
            <button id="login-btn" onclick="webLogin()">Sign In</button>
            <button class="switch-btn" onclick="showSignup()">Create an account</button>
            <div class="error" id="login-error">Invalid credentials</div>
        </div>

        <div id="signup-page" class="page">
            <input type="text" id="signup-name" placeholder="Full name (optional)">
            <input type="email" id="signup-email" placeholder="Email">
            <input type="password" id="signup-password" placeholder="Password (min 4 characters)">
            <input type="password" id="signup-confirm" placeholder="Confirm password">
            <button id="signup-btn" onclick="webSignup()">Create Account</button>
            <button class="switch-btn" onclick="showLogin()">Already have an account? Sign in</button>
            <div class="error" id="signup-error">Error</div>
        </div>
    </div>
    <script>
        function showSignup() {
            document.getElementById('login-page').classList.remove('active');
            document.getElementById('signup-page').classList.add('active');
            document.getElementById('subtitle').textContent = 'Create a new account';
        }
        function showLogin() {
            document.getElementById('signup-page').classList.remove('active');
            document.getElementById('login-page').classList.add('active');
            document.getElementById('subtitle').textContent = 'Sign in to access specimen data';
        }

        document.getElementById('password').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') webLogin();
        });
        document.getElementById('signup-confirm').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') webSignup();
        });

        function webLogin() {
            const btn = document.getElementById('login-btn');
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const errEl = document.getElementById('login-error');
            if (!email || !password) { errEl.textContent = 'Please fill in all fields.'; errEl.classList.add('visible'); return; }
            btn.disabled = true; btn.textContent = 'Signing in...'; errEl.classList.remove('visible');
            fetch('/api/web-login', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            }).then(r => r.json()).then(data => {
                if (data.token) {
                    localStorage.setItem('session_token', data.token);
                    localStorage.setItem('session_user', JSON.stringify(data.user));
                    window.location.href = '/';
                } else { errEl.textContent = data.error || 'Login failed'; errEl.classList.add('visible'); btn.disabled = false; btn.textContent = 'Sign In'; }
            }).catch(() => { errEl.textContent = 'Connection error'; errEl.classList.add('visible'); btn.disabled = false; btn.textContent = 'Sign In'; });
        }

        function webSignup() {
            const btn = document.getElementById('signup-btn');
            const name = document.getElementById('signup-name').value.trim();
            const email = document.getElementById('signup-email').value.trim();
            const password = document.getElementById('signup-password').value;
            const confirm = document.getElementById('signup-confirm').value;
            const errEl = document.getElementById('signup-error');
            if (!email || !password) { errEl.textContent = 'Email and password required.'; errEl.classList.add('visible'); return; }
            if (password !== confirm) { errEl.textContent = 'Passwords do not match.'; errEl.classList.add('visible'); return; }
            btn.disabled = true; btn.textContent = 'Creating account...'; errEl.classList.remove('visible');
            fetch('/api/web-signup', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, name })
            }).then(r => r.json()).then(data => {
                if (data.token) {
                    localStorage.setItem('session_token', data.token);
                    localStorage.setItem('session_user', JSON.stringify(data.user));
                    window.location.href = '/';
                } else { errEl.textContent = data.error || 'Signup failed'; errEl.classList.add('visible'); btn.disabled = false; btn.textContent = 'Create Account'; }
            }).catch(() => { errEl.textContent = 'Connection error'; errEl.classList.add('visible'); btn.disabled = false; btn.textContent = 'Create Account'; });
        }
    </script>
</body>
</html>
"""

SPECIMEN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Biobank Barcode Lookup</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa; color: #333; padding: 16px; min-height: 100vh;
        }
        .container { max-width: 600px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        h1 { font-size: 1.5rem; color: #1a73e8; }
        .signout-btn { background: none; border: 1px solid #ddd; padding: 6px 14px; border-radius: 6px; color: #666; cursor: pointer; font-size: 0.85rem; }
        .signout-btn:hover { background: #f0f0f0; }
        .scan-area { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 16px; }
        #qr-video { width: 100%; max-width: 400px; display: block; margin: 0 auto 12px; border-radius: 8px; background: #000; }
        #scan-btn { display: block; width: 100%; padding: 14px; background: #1a73e8; color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; margin-bottom: 12px; }
        #scan-btn:disabled { opacity: 0.5; }
        #scan-btn.scanning { background: #e74c3c; }
        input[type="text"] { width: 100%; padding: 12px 16px; border: 2px solid #ddd; border-radius: 8px; font-size: 1rem; outline: none; }
        input[type="text"]:focus { border-color: #1a73e8; }
        .result-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); display: none; }
        .result-card.visible { display: block; }
        .result-card h2 { font-size: 1.1rem; color: #1a73e8; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid #e8f0fe; }
        .field { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }
        .field:last-child { border-bottom: none; }
        .field-label { color: #666; font-size: 0.9rem; }
        .field-value { font-weight: 600; text-align: right; max-width: 60%; word-break: break-word; }
        .not-found { background: #fff3f3; color: #c0392b; padding: 20px; border-radius: 8px; text-align: center; display: none; }
        .not-found.visible { display: block; }
        .loading { text-align: center; padding: 20px; color: #666; display: none; }
        .loading.visible { display: block; }
        .spinner { border: 3px solid #f3f3f3; border-top: 3px solid #1a73e8; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Biobank Barcode Lookup</h1>
            <button class="signout-btn" onclick="signOut()">Sign Out</button>
        </div>
        <div class="scan-area">
            <video id="qr-video" autoplay muted playsinline></video>
            <button id="scan-btn" onclick="toggleScanner()">Open Camera Scanner</button>
            <input type="text" id="qr-input" placeholder="Scan barcode or enter ID manually..." onkeydown="if(event.key==='Enter')lookup()">
        </div>
        <div class="loading" id="loading"><div class="spinner"></div>Looking up specimen...</div>
        <div class="not-found" id="not-found">Specimen not found.</div>
        <div class="result-card" id="result">
            <h2 id="specimen-header">Specimen Details</h2>
            <div id="fields-container"></div>
        </div>
    </div>
    <script>
        function getToken() { return localStorage.getItem('session_token'); }

        function authFetch(url, opts) {
            opts = opts || {};
            opts.headers = opts.headers || {};
            opts.headers['Authorization'] = 'Bearer ' + getToken();
            return fetch(url, opts).then(r => {
                if (r.status === 401) { localStorage.removeItem('session_token'); localStorage.removeItem('session_user'); window.location.href = '/login'; throw new Error('Unauthorized'); }
                return r;
            });
        }

        function signOut() {
            const token = getToken();
            if (token) fetch('/api/logout', { method: 'POST', headers: { 'Authorization': 'Bearer ' + token } });
            localStorage.removeItem('session_token');
            localStorage.removeItem('session_user');
            window.location.href = '/login';
        }

        if (!getToken()) { window.location.href = '/login'; }

        let scannerActive = false, videoStream = null;

        async function toggleScanner() {
            const btn = document.getElementById('scan-btn');
            const video = document.getElementById('qr-video');
            if (scannerActive) { stopScanner(); return; }
            try {
                videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
                video.srcObject = videoStream; await video.play();
                scannerActive = true; btn.textContent = 'Stop Scanner'; btn.classList.add('scanning');
                scanQR();
            } catch(e) { alert('Camera access denied. Enter QR code manually.'); }
        }

        function stopScanner() {
            const btn = document.getElementById('scan-btn');
            const video = document.getElementById('qr-video');
            if (videoStream) { videoStream.getTracks().forEach(t => t.stop()); videoStream = null; }
            video.srcObject = null; scannerActive = false;
            btn.textContent = 'Open Camera Scanner'; btn.classList.remove('scanning');
        }

        function scanQR() {
            if (!scannerActive) return;
            const video = document.getElementById('qr-video');
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth; canvas.height = video.videoHeight;
                canvas.getContext('2d').drawImage(video, 0, 0);
                authFetch('/api/decode-qr', {
                    method: 'POST', body: JSON.stringify({ image: canvas.toDataURL('image/png') }),
                    headers: { 'Content-Type': 'application/json' }
                }).then(r => r.json()).then(data => {
                    if (data.qr_code) { stopScanner(); document.getElementById('qr-input').value = data.qr_code; lookup(); }
                }).catch(() => {});
            }
            requestAnimationFrame(scanQR);
        }

        function showLoading() {
            document.getElementById('loading').classList.add('visible');
            document.getElementById('result').classList.remove('visible');
            document.getElementById('not-found').classList.remove('visible');
        }

        function lookup() {
            const qrCode = document.getElementById('qr-input').value.trim();
            if (!qrCode) return;
            showLoading();
            authFetch('/api/lookup?qr=' + encodeURIComponent(qrCode))
                .then(r => r.json()).then(data => {
                    document.getElementById('loading').classList.remove('visible');
                    if (data.error) { document.getElementById('not-found').classList.add('visible'); document.getElementById('result').classList.remove('visible'); return; }
                    document.getElementById('not-found').classList.remove('visible');
                    document.getElementById('specimen-header').textContent = 'Specimen: ' + qrCode;
                    const container = document.getElementById('fields-container');
                    container.innerHTML = '';
                    data.fields.forEach(f => {
                        const div = document.createElement('div');
                        div.className = 'field';
                        div.innerHTML = '<span class="field-label">' + f.name + '</span><span class="field-value">' + (f.value || '-') + '</span>';
                        container.appendChild(div);
                    });
                    const meta = document.createElement('div');
                    meta.style.marginTop = '12px'; meta.style.paddingTop = '8px';
                    meta.style.borderTop = '2px solid #e8f0fe'; meta.style.fontSize = '0.8rem'; meta.style.color = '#999';
                    meta.innerHTML = 'Created: ' + data.created_at;
                    container.appendChild(meta);
                    document.getElementById('result').classList.add('visible');
                }).catch(() => {});
        }
    </script>
</body>
</html>
"""


class WebServer:
    def __init__(self, db=None, port=5000, auth=None):
        self.db = db
        self.port = port
        self.auth = auth  # AuthManager instance (from desktop login)
        self.auth_manager = AuthManager(db)
        self.app = Flask(__name__)
        self._setup_routes()
        self.server_thread = None

    def _require_auth(self):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        if not token:
            return None
        return self.auth_manager.validate_session(token)

    def _setup_routes(self):
        app = self.app
        specimen_model = SpecimenModel(self.db)
        column_def = ColumnDefinition(self.db)

        @app.route("/")
        def index():
            return render_template_string(SPECIMEN_TEMPLATE)

        @app.route("/login")
        def login_page():
            return render_template_string(LOGIN_TEMPLATE)

        @app.route("/api/web-login", methods=["POST"])
        def web_login():
            data = request.get_json() or {}
            email = data.get("email", "").strip()
            password = data.get("password", "")

            try:
                user = self.auth_manager.login(email, password)
                if not user:
                    return jsonify({"error": "Invalid credentials"}), 401
                token = self.auth_manager.create_session(user["id"])
                return jsonify({
                    "token": token,
                    "user": {"id": user["id"], "email": user["email"]}
                })
            except PermissionError as e:
                return jsonify({"error": str(e)}), 401
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/web-signup", methods=["POST"])
        def web_signup():
            data = request.get_json() or {}
            email = data.get("email", "").strip()
            password = data.get("password", "")
            name = data.get("name", "")

            try:
                user = self.auth_manager.signup(email, password, name)
                if not user:
                    return jsonify({"error": "Signup failed"}), 500
                token = self.auth_manager.create_session(user["id"])
                return jsonify({
                    "token": token,
                    "user": {"id": user["id"], "email": user["email"]}
                })
            except (ValueError, PermissionError) as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/logout", methods=["POST"])
        def web_logout():
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                self.auth_manager.delete_session(auth_header[7:])
            return jsonify({"ok": True})

        @app.route("/api/lookup")
        def api_lookup():
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            qr_code = request.args.get("qr", "")
            if not qr_code:
                return jsonify({"error": "No QR code provided"}), 400

            specimen = specimen_model.get_by_qr(qr_code)
            if not specimen:
                results = specimen_model.search(qr_code, column_name="Sample ID")
                specimen = results[0] if results else None
            if not specimen:
                return jsonify({"error": "Not found"}), 404

            columns = column_def.get_all()
            fields = [{"name": c["column_name"], "value": specimen["custom_fields"].get(c["column_name"], "")} for c in columns]

            return jsonify({
                "id": specimen["id"],
                "qr_code": specimen["qr_code"],
                "fields": fields,
                "created_at": specimen["created_at"],
                "updated_at": specimen["updated_at"]
            })

        @app.route("/api/decode-qr", methods=["POST"])
        def api_decode_qr():
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            try:
                from PIL import Image
                from pyzbar.pyzbar import decode as pyzbar_decode
                import io
                data = request.get_json()
                if not data or "image" not in data:
                    return jsonify({"error": "No image data"}), 400
                img_data = base64.b64decode(data["image"].split(",")[1])
                img = Image.open(io.BytesIO(img_data))
                results = pyzbar_decode(img)
                if results:
                    return jsonify({"qr_code": results[0].data.decode("utf-8")})
                return jsonify({"qr_code": None})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/me")
        def api_me():
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            return jsonify(user)

    def start(self):
        def run():
            self.app.run(host="0.0.0.0", port=self.port, debug=False, use_reloader=False)

        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()

    def stop(self):
        try:
            import requests
            requests.get(f"http://127.0.0.1:{self.port}/shutdown", timeout=2)
        except Exception:
            pass
