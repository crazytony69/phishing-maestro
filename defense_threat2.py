from flask import Flask, jsonify, redirect, render_template_string, request

app = Flask(__name__)

DEFENSE_STATE = {
    "cookie_defense": False,
    "csp_defense": False,
    "csrf_defense": False
}

PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Threat 2 Defense Toggle</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 32px;
        }
        .container {
            max-width: 700px;
            margin: 0 auto;
        }
        .card {
            background: #1e293b;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
        }
        h1 {
            margin-top: 0;
            color: #22c55e;
        }
        .status {
            font-size: 20px;
            font-weight: bold;
            margin: 16px 0;
        }
        .on {
            color: #22c55e;
        }
        .off {
            color: #ef4444;
        }
        .btn {
            display: inline-block;
            text-decoration: none;
            padding: 10px 16px;
            border-radius: 10px;
            margin-right: 10px;
            color: white;
        }
        .enable {
            background: #16a34a;
        }
        .disable {
            background: #dc2626;
        }
        .meta {
            margin-top: 18px;
            color: #94a3b8;
            font-size: 14px;
            line-height: 1.6;
        }
        code {
            background: #334155;
            padding: 2px 6px;
            border-radius: 6px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>Threat 2 Defense Toggle</h1>


            <div class="status">
                <div>Cookie Defense (HttpOnly):
                    {% if cookie_defense %}
                        <span class="on">ON</span>
                    {% else %}
                        <span class="off">OFF</span>
                    {% endif %}
                </div>

                <div>CSP Defense:
                    {% if csp_defense %}
                        <span class="on">ON</span>
                    {% else %}
                        <span class="off">OFF</span>
                    {% endif %}
                </div>

                <div>CSRF Defense:
                    {% if csrf_defense %}
                        <span class="on">ON</span>
                    {% else %}
                        <span class="off">OFF</span>
                    {% endif %}
                </div>
            </div>

            <p>
                <a class="btn enable" href="/toggle/cookie">Toggle Cookie Defense</a>
                <a class="btn enable" href="/toggle/csp">Toggle CSP Defense</a>
                <a class="btn enable" href="/toggle/csrf">Toggle CSRF Defense</a>
                <a class="btn disable" href="/reset">Reset All</a>
            </p>

            <div class="meta">
                Cookie Defense enables HttpOnly cookies.<br>
                CSP Defense blocks external data exfiltration routes used by some XSS payloads.<br>
                CSRF Defense requires a valid CSRF token for creating forum posts.<br><br>
                Portal polls: <code>/status</code>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(
        PAGE,
        cookie_defense=DEFENSE_STATE["cookie_defense"],
        csp_defense=DEFENSE_STATE["csp_defense"],
        csrf_defense=DEFENSE_STATE["csrf_defense"],
    )

@app.route("/status")
def status():
    return jsonify({
        "cookie_defense": DEFENSE_STATE["cookie_defense"],
        "csp_defense": DEFENSE_STATE["csp_defense"],
        "csrf_defense": DEFENSE_STATE["csrf_defense"]
    })

@app.route("/toggle/cookie")
def toggle_cookie():
    DEFENSE_STATE["cookie_defense"] = not DEFENSE_STATE["cookie_defense"]
    return redirect("/")

@app.route("/toggle/csp")
def toggle_csp():
    DEFENSE_STATE["csp_defense"] = not DEFENSE_STATE["csp_defense"]
    return redirect("/")

@app.route("/toggle/csrf")
def toggle_csrf():
    DEFENSE_STATE["csrf_defense"] = not DEFENSE_STATE["csrf_defense"]
    return redirect("/")

@app.route("/reset")
def reset():
    DEFENSE_STATE["cookie_defense"] = False
    DEFENSE_STATE["csp_defense"] = False
    DEFENSE_STATE["csrf_defense"] = False
    return redirect("/")

if __name__ == "__main__":
    print("[DEFENSE] Threat 2 defense toggle running on http://127.0.0.1:9100")
    app.run(host="127.0.0.1", port=9100, debug=False)