"""
MFA Code Receiver — Simulates User's Phone / SMS Inbox
========================================================
EDUCATIONAL PURPOSE ONLY - ELEC0138 Coursework Demonstration

This simulates the user's device that receives MFA verification codes.
In a real scenario, this would be an SMS message or authenticator app
push notification on the user's phone.

The real portal (portal3.py) sends codes here when MFA is triggered.
The dashboard auto-refreshes to show incoming codes with countdown timers.

Usage:
    python mfa_receiver.py
    (Runs on http://127.0.0.1:7000)
"""

from flask import Flask, request, jsonify, render_template_string
import time
from datetime import datetime

app = Flask(__name__)

# Store received codes
received_codes = []
CODE_EXPIRY = 60  # seconds

RECEIVER_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MFA Code Receiver</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; padding: 32px; }
        .container { max-width: 500px; margin: 0 auto; }
        h1 { color: #22d3ee; text-align: center; margin-bottom: 4px; }
        .subtitle { text-align: center; color: #64748b; margin-bottom: 28px; font-size: 14px; }
        .phone {
            background: #1e293b;
            border: 3px solid #334155;
            border-radius: 28px;
            padding: 24px 20px;
            max-width: 380px;
            margin: 0 auto;
        }
        .notch {
            width: 120px; height: 6px;
            background: #334155; border-radius: 3px;
            margin: 0 auto 20px auto;
        }
        .sms {
            background: #0f766e;
            border-radius: 16px 16px 16px 4px;
            padding: 16px;
            margin-bottom: 14px;
        }
        .sms-header {
            font-size: 12px;
            color: #a7f3d0;
            margin-bottom: 8px;
        }
        .sms-code {
            font-size: 36px;
            font-weight: bold;
            color: white;
            letter-spacing: 8px;
            text-align: center;
            margin: 8px 0;
        }
        .sms-footer {
            font-size: 11px;
            color: #a7f3d0;
            margin-top: 8px;
        }
        .expired {
            background: #334155;
            opacity: 0.5;
        }
        .expired .sms-code {
            text-decoration: line-through;
            color: #94a3b8;
        }
        .countdown {
            text-align: center;
            font-size: 13px;
            color: #fbbf24;
        }
        .empty {
            text-align: center;
            color: #475569;
            padding: 40px 0;
        }
        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: bold;
        }
        .tag-active { background: #22d3ee; color: #0f172a; }
        .tag-expired { background: #475569; color: #94a3b8; }
    </style>
    <meta http-equiv="refresh" content="3">
</head>
<body>
    <div class="container">
        <h1>SMS Inbox</h1>
        <div class="subtitle">Simulated phone — MFA verification codes appear here</div>

        <div class="phone">
            <div class="notch"></div>

            {% if codes %}
                {% for c in codes | reverse %}
                <div class="sms {% if c.expired %}expired{% endif %}">
                    <div class="sms-header">
                        University Student Portal
                        {% if c.expired %}
                            <span class="tag tag-expired">EXPIRED</span>
                        {% else %}
                            <span class="tag tag-active">ACTIVE</span>
                        {% endif %}
                    </div>
                    <div class="sms-code">{{ c.code }}</div>
                    <div class="sms-footer">
                        For: {{ c.username }} | {{ c.time }}
                        {% if not c.expired %}
                            | Expires in {{ c.remaining }}s
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty">No verification codes received yet.<br>Log in to the portal to trigger MFA.</div>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""


@app.route("/receive-code", methods=["POST"])
def receive_code():
    """Receive MFA code from the real portal."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "unknown")
    code = data.get("code", "????")
    timestamp = data.get("timestamp", time.time())

    received_codes.append({
        "username": username,
        "code": code,
        "timestamp": timestamp,
        "time": datetime.now().strftime("%H:%M:%S"),
    })

    print(f"  [SMS] Code {code} received for {username}")
    return jsonify({"status": "received"}), 200


@app.route("/")
def inbox():
    """Display received codes with expiry countdown."""
    now = time.time()
    display_codes = []

    for c in received_codes:
        elapsed = now - c["timestamp"]
        expired = elapsed > CODE_EXPIRY
        remaining = max(0, int(CODE_EXPIRY - elapsed))

        display_codes.append({
            "username": c["username"],
            "code": c["code"],
            "time": c["time"],
            "expired": expired,
            "remaining": remaining,
        })

    return render_template_string(RECEIVER_PAGE, codes=display_codes)


@app.route("/api/codes")
def api_codes():
    """API to get all received codes."""
    return jsonify(received_codes)


if __name__ == "__main__":
    print("=" * 55)
    print("  MFA CODE RECEIVER — Simulated Phone SMS Inbox")
    print("=" * 55)
    print()
    app.run(host="0.0.0.0", port=7000, debug=False)
