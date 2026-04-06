from flask import Flask, request, jsonify, redirect, url_for, session, render_template_string
import sqlite3
import time
import random
import requests as http_requests
from collections import defaultdict, deque
import html
import secrets

app = Flask(__name__)
app.secret_key = "demo_secret_key_change_in_real_project"
app.config["SESSION_COOKIE_HTTPONLY"] = False
app.config["SESSION_COOKIE_SAMESITE"] = None

DB_NAME = "portal.db"
DEFENSE_TOGGLE_URL = "http://127.0.0.1:9100/status"
DEFENSE_TIMEOUT = 0.5

def get_defense_state():
    try:
        r = http_requests.get(DEFENSE_TOGGLE_URL, timeout=DEFENSE_TIMEOUT)
        if r.status_code != 200:
            return {
                "cookie_defense": False,
                "csp_defense": False,
                "csrf_defense": False,
            }
        data = r.json()
        return {
            "cookie_defense": bool(data.get("cookie_defense", False)),
            "csp_defense": bool(data.get("csp_defense", False)),
            "csrf_defense": bool(data.get("csrf_defense", False)),
        }
    except Exception:
        return {
            "cookie_defense": False,
            "csp_defense": False,
            "csrf_defense": False,
        }
    

@app.before_request
def apply_runtime_defenses():
    state = get_defense_state()
    app.config["SESSION_COOKIE_HTTPONLY"] = state["cookie_defense"]


    if "username" in session:
        session.modified = True

@app.after_request
def apply_csp_headers(response):
    state = get_defense_state()
    if state["csp_defense"]:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src * data:; "
            "connect-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "frame-ancestors 'self';"
        )
    return response 

def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 10
request_log = defaultdict(deque)


# HTML templates
LOGIN_PAGE = """
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
        h1 {
            margin: 0 0 8px 0;
            color: #0f172a;
            text-align: center;
        }
        p.subtitle {
            margin: 0 0 24px 0;
            text-align: center;
            color: #475569;
            font-size: 14px;
        }
        label {
            display: block;
            margin-bottom: 6px;
            color: #1e293b;
            font-weight: bold;
            font-size: 14px;
        }
        input {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            margin-bottom: 16px;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            font-size: 14px;
        }
        button {
            width: 100%;
            background: #0f766e;
            color: white;
            border: none;
            padding: 12px;
            border-radius: 10px;
            font-size: 15px;
            cursor: pointer;
        }
        button:hover {
            background: #0d5f59;
        }
        .msg {
            margin-bottom: 16px;
            padding: 10px 12px;
            border-radius: 10px;
            font-size: 14px;
        }
        .error {
            background: #fee2e2;
            color: #991b1b;
        }
        .info {
            background: #e0f2fe;
            color: #075985;
        }
        .demo-box {
            margin-top: 18px;
            padding: 12px;
            background: #f8fafc;
            border-radius: 10px;
            font-size: 13px;
            color: #334155;
        }
        .demo-box code {
            display: block;
            margin-top: 4px;
        }
        .footer {
            margin-top: 14px;
            text-align: center;
            color: #64748b;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>University Student Portal</h1>
        <p class="subtitle">Sign in to access your academic dashboard</p>

        {% if message %}
            <div class="msg {{ message_type }}">{{ message }}</div>
        {% endif %}

        <form method="POST" action="{{ url_for('web_login') }}">
            <label for="username">University Email / Username</label>
            <input id="username" name="username" type="text" placeholder="student@example.edu" required>

            <label for="password">Password</label>
            <input id="password" name="password" type="password" placeholder="Enter password" required>

            <button type="submit">Sign In</button>
        </form>

        <div class="demo-box">
            <strong>Demo accounts:</strong>
            <code>alice@example.com / Password123 (MFA enabled)</code>
            <code>diana@example.com / Welcome1 (MFA enabled)</code>
            <code>bob@example.com / qwerty123 (no MFA — backdoor)</code>
            <code>MFA codes sent to receiver at port 7000</code>
        </div>

        <div class="footer">University Student Portal</div>
    </div>
</body>
</html>
"""

MFA_PAGE = """
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
        .demo-box { margin-top: 18px; padding: 12px; background: #f8fafc;
                     border-radius: 10px; font-size: 13px; color: #334155; }
        .footer { margin-top: 14px; text-align: center; color: #64748b; font-size: 12px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Two-Factor Authentication</h1>
        <p class="subtitle">Enter the 4-digit verification code sent to your device</p>

        {% if message %}
            <div class="msg {{ message_type }}">{{ message }}</div>
        {% endif %}

        <form method="POST" action="/mfa-verify">
            <label for="code">Verification Code</label>
            <input id="code" name="code" type="text" maxlength="4" placeholder="----" required autofocus>
            <button type="submit">Verify</button>
        </form>

        <div class="demo-box">
            <strong>MFA code has been sent to the receiver.</strong>
            Check http://127.0.0.1:7000 to view the code. Code expires in 60 seconds.
        </div>
        <div class="footer">Coursework demonstration environment</div>
    </div>
</body>
</html>
"""

ACCOUNT_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Dashboard</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f1f5f9;
            margin: 0;
            padding: 32px;
        }
        .topbar {
            max-width: 1000px;
            margin: 0 auto 24px auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .topbar h1 {
            margin: 0;
            color: #0f172a;
        }
        .logout {
            text-decoration: none;
            background: #ef4444;
            color: white;
            padding: 10px 14px;
            border-radius: 10px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .nav {
            margin-bottom: 18px;
        }
        .nav a {
            text-decoration: none;
            display: inline-block;
            margin-right: 12px;
            padding: 10px 14px;
            background: white;
            border-radius: 10px;
            color: #0f766e;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 18px;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }
        .label {
            color: #64748b;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .value {
            color: #0f172a;
            font-size: 24px;
            font-weight: bold;
        }
        .section-title {
            margin: 0 0 12px 0;
            color: #0f172a;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            text-align: left;
            padding: 10px;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            color: #475569;
        }
        .small {
            color: #334155;
            font-size: 15px;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="topbar">
        <h1>Welcome, {{ username }}</h1>
        <a class="logout" href="{{ url_for('logout') }}">Logout</a>
    </div>

    <div class="container">
        <div class="nav">
            <a href="{{ url_for('dashboard') }}">Dashboard</a>
            <a href="{{ url_for('forum_home') }}">Discussion Forum</a>
        </div>

        <div class="grid">
            <div class="card">
                <div class="label">Programme</div>
                <div class="value" style="font-size: 20px;">Electronic & Electrical Engineering</div>
            </div>

            <div class="card">
                <div class="label">Current Tuition Balance</div>
                <div class="value">{{ account.balance }} {{ account.currency }}</div>
            </div>

            <div class="card">
                <div class="label">Portal Access Status</div>
                <div class="value" style="font-size: 20px;">Authenticated</div>
            </div>
        </div>

        <div class="card" style="margin-top: 18px;">
            <h2 class="section-title">Registered Modules</h2>
            <table>
                <thead>
                    <tr>
                        <th>Module Code</th>
                        <th>Module Title</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for tx in transactions %}
                    <tr>
                        <td>{{ tx.date }}</td>
                        <td>{{ tx.description }}</td>
                        <td>{{ tx.amount }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>


    </div>
</body>
</html>
"""

FORUM_HOME_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Discussion Forum</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f1f5f9;
            margin: 0;
            padding: 32px;
            color: #0f172a;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
        }
        .top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 18px;
        }
        .title {
            font-size: 28px;
            margin: 0;
        }
        .btn {
            display: inline-block;
            text-decoration: none;
            color: white;
            background: #0f766e;
            padding: 10px 14px;
            border-radius: 10px;
            margin-right: 10px;
        }
        .btn.secondary {
            background: #334155;
        }
        .notice {
            background: #fff7ed;
            color: #9a3412;
            padding: 14px 16px;
            border-radius: 12px;
            margin-bottom: 18px;
        }
        .list {
            display: grid;
            gap: 16px;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }
        .meta {
            color: #64748b;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .post-title {
            margin: 0 0 10px 0;
            font-size: 20px;
        }
        .preview {
            color: #334155;
            line-height: 1.6;
        }
        .links a {
            text-decoration: none;
            color: #0f766e;
            margin-right: 14px;
            font-size: 14px;
        }
        .empty {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            color: #475569;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="top">
            <h1 class="title">Discussion Forum</h1>
            <div>
                <a class="btn" href="{{ url_for('forum_new') }}">New Post</a>
                <a class="btn secondary" href="{{ url_for('dashboard') }}">Back to Dashboard</a>
            </div>
        </div>

        <div class="notice">
            Communication forum post this place
        </div>

        {% if posts %}
        <div class="list">
            {% for post in posts %}
            <div class="card">
                <div class="meta">
                    Author: {{ post.author }} | Created: {{ post.created_at }}
                </div>
                <h2 class="post-title">{{ post.title }}</h2>
                <div class="preview">{{ post.preview }}</div>
                <div class="links" style="margin-top: 12px;">
                    <a href="{{ url_for('forum_view_post', post_id=post.id) }}">View Post</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty">No forum posts yet.</div>
        {% endif %}
    </div>
</body>
</html>
"""

FORUM_NEW_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>New Forum Post</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f1f5f9;
            margin: 0;
            padding: 32px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }
        h1 {
            margin-top: 0;
        }
        label {
            display: block;
            margin-bottom: 6px;
            color: #1e293b;
            font-weight: bold;
            font-size: 14px;
        }
        input, textarea {
            width: 100%;
            box-sizing: border-box;
            padding: 12px;
            margin-bottom: 16px;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            font-size: 14px;
            font-family: Arial, sans-serif;
        }
        textarea {
            min-height: 220px;
            resize: vertical;
        }
        .btn {
            display: inline-block;
            text-decoration: none;
            color: white;
            background: #0f766e;
            padding: 10px 14px;
            border-radius: 10px;
            border: none;
            margin-right: 10px;
            cursor: pointer;
        }
        .btn.secondary {
            background: #334155;
        }
        .notice {
            background: #fff7ed;
            color: #9a3412;
            padding: 14px 16px;
            border-radius: 12px;
            margin-bottom: 18px;
        }
        .hint {
            background: #eff6ff;
            color: #1d4ed8;
            padding: 12px 14px;
            border-radius: 12px;
            margin-top: 18px;
            font-size: 14px;
            line-height: 1.6;
        }
        code {
            background: #f8fafc;
            padding: 2px 6px;
            border-radius: 6px;
        }
        .msg {
            margin-bottom: 16px;
            padding: 10px 12px;
            border-radius: 10px;
            font-size: 14px;
        }
        .error {
            background: #fee2e2;
            color: #991b1b;
        }
        .info {
            background: #e0f2fe;
            color: #075985;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>Create Forum Post</h1>

            <div class="notice">
                The forum please be short.
            </div>

            {% if message %}
                <div class="msg {{ message_type }}">{{ message }}</div>
            {% endif %}

            <form method="POST" action="{{ url_for('forum_new') }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token }}">

                <label for="title">Post Title</label>
                <input id="title" name="title" type="text" placeholder="Week 2 revision discussion" required>

                <label for="content">Post Content</label>
                <textarea id="content" name="content" placeholder="Write your post here..." required></textarea>

                <button class="btn" type="submit">Publish Post</button>
                <a class="btn secondary" href="{{ url_for('forum_home') }}">Cancel</a>
            </form>


        </div>
    </div>
</body>
</html>
"""

FORUM_POST_UNSAFE_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forum Post - Unsafe View</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f1f5f9;
            margin: 0;
            padding: 32px;
            color: #0f172a;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .warn {
            background: #fee2e2;
            color: #991b1b;
            padding: 14px 16px;
            border-radius: 12px;
            margin-bottom: 18px;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }
        .meta {
            color: #64748b;
            font-size: 13px;
            margin-bottom: 10px;
        }
        h1 {
            margin-top: 0;
        }
        .content {
            line-height: 1.7;
            color: #334155;
        }
        .actions {
            margin-top: 18px;
        }
        .btn {
            display: inline-block;
            text-decoration: none;
            color: white;
            background: #0f766e;
            padding: 10px 14px;
            border-radius: 10px;
            margin-right: 10px;
        }
        .btn.secondary {
            background: #334155;
        }
        .demo-box {
            margin-top: 18px;
            background: #fff7ed;
            color: #9a3412;
            padding: 14px 16px;
            border-radius: 12px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">


        <div class="card">
            <div class="meta">Author: {{ post.author }} | Created: {{ post.created_at }}</div>
            <h1>{{ post.title }}</h1>
            <div class="content">{{ unsafe_content | safe }}</div>

            <div style="margin-top: 24px;">
                <h2 style="font-size: 18px; margin-bottom: 12px;">Comments</h2>

                {% if comments %}
                    {% for c in comments %}
                    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 10px;">
                        <div style="color: #64748b; font-size: 12px; margin-bottom: 6px;">{{ c.author }} — {{ c.created_at }}</div>
                        <div>{{ c.content }}</div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="color: #94a3b8; font-size: 14px;">No comments yet.</div>
                {% endif %}

                <form method="POST" style="margin-top: 14px;">
                    <input name="comment" type="text" placeholder="Write a comment..."
                           style="width: 100%; padding: 12px; border: 1px solid #cbd5e1;
                                  border-radius: 10px; box-sizing: border-box; font-size: 14px;">
                    <button type="submit"
                            style="margin-top: 10px; padding: 10px 16px; background: #0f766e;
                                   color: white; border: none; border-radius: 10px; cursor: pointer;">
                        Post Comment
                    </button>
                </form>
            </div>



            <div class="actions">
                <a class="btn secondary" href="{{ url_for('forum_home') }}">Back to Forum</a>   
            </div>
        </div>
    </div>
</body>
</html>
"""

FORUM_POST_SAFE_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forum Post - Safe View</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f1f5f9;
            margin: 0;
            padding: 32px;
            color: #0f172a;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .ok {
            background: #dcfce7;
            color: #166534;
            padding: 14px 16px;
            border-radius: 12px;
            margin-bottom: 18px;
        }
        .card {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
        }
        .meta {
            color: #64748b;
            font-size: 13px;
            margin-bottom: 10px;
        }
        h1 {
            margin-top: 0;
        }
        .content {
            line-height: 1.7;
            color: #334155;
            white-space: pre-wrap;
        }
        .actions {
            margin-top: 18px;
        }
        .btn {
            display: inline-block;
            text-decoration: none;
            color: white;
            background: #0f766e;
            padding: 10px 14px;
            border-radius: 10px;
            margin-right: 10px;
        }
        .btn.secondary {
            background: #334155;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="ok">
            Safe view: post content is escaped before rendering, so embedded markup is displayed as text instead of executing.
        </div>

        <div class="card">
            <div class="meta">Author: {{ post.author }} | Created: {{ post.created_at }}</div>
            <h1>{{ post.title }}</h1>
            <div class="content">{{ safe_content }}</div>

            <div style="margin-top: 24px;">
                <h2 style="font-size: 18px; margin-bottom: 12px;">Comments</h2>

                {% if comments %}
                    {% for c in comments %}
                    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 10px;">
                        <div style="color: #64748b; font-size: 12px; margin-bottom: 6px;">{{ c.author }} — {{ c.created_at }}</div>
                        <div>{{ c.content }}</div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="color: #94a3b8; font-size: 14px;">No comments yet.</div>
                {% endif %}

                <form method="POST" style="margin-top: 14px;">
                    <input name="comment" type="text" placeholder="Write a comment..."
                           style="width: 100%; padding: 12px; border: 1px solid #cbd5e1;
                                  border-radius: 10px; box-sizing: border-box; font-size: 14px;">
                    <button type="submit"
                            style="margin-top: 10px; padding: 10px 16px; background: #0f766e;
                                   color: white; border: none; border-radius: 10px; cursor: pointer;">
                        Post Comment
                    </button>
                </form>
            </div>

            <div class="actions">
                <a class="btn secondary" href="{{ url_for('forum_home') }}">Back to Forum</a>
            </div>
        </div>
    </div>
</body>
</html>
"""


# Database helpers
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        mfa_enabled INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        ip_address TEXT,
        success INTEGER,
        user_agent TEXT,
        timestamp REAL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS forum_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at REAL NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        author TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at REAL NOT NULL
    )
    """)

    demo_users = [
        ("alice@example.com", "Password123", 1),
        ("bob@example.com", "qwerty123", 0),
        ("charlie@example.com", "letmein2024", 1),
        ("diana@example.com", "Welcome1", 1),
        ("eva@example.com", "12345678", 1),
    ]

    for user in demo_users:
        try:
            cur.execute(
                "INSERT INTO users (username, password, mfa_enabled) VALUES (?, ?, ?)",
                user
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()


def get_user(username):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password, mfa_enabled FROM users WHERE username = ?",
        (username,)
    )
    row = cur.fetchone()
    conn.close()
    return row


def get_fake_account(username):
    fake_accounts = {
        "alice@example.com": {
            "balance": 1250.50,
            "currency": "GBP",
            "transactions": [
                {"date": "ELEC0138", "description": "Security and Privacy", "amount": "Enrolled"},
                {"date": "ELEC0149", "description": "Introduction to Machine Learning", "amount": "Enrolled"},
                {"date": "ELEC0078", "description": "Photonics and Sensors", "amount": "Enrolled"},
            ],
        },
        "bob@example.com": {
            "balance": 4820.10,
            "currency": "GBP",
            "transactions": [
                {"date": "COMP001", "description": "Programming Systems", "amount": "Enrolled"},
                {"date": "COMP002", "description": "Data Structures", "amount": "Enrolled"},
                {"date": "MATH101", "description": "Engineering Mathematics", "amount": "Enrolled"},
            ],
        },
        "charlie@example.com": {
            "balance": 999.99,
            "currency": "GBP",
            "transactions": [
                {"date": "STAT201", "description": "Applied Statistics", "amount": "Enrolled"},
                {"date": "EE202", "description": "Signals and Systems", "amount": "Enrolled"},
                {"date": "CS220", "description": "Networks", "amount": "Enrolled"},
            ],
        },
        "diana@example.com": {
            "balance": 210.00,
            "currency": "GBP",
            "transactions": [
                {"date": "ELEC0025", "description": "Photonics II", "amount": "Enrolled"},
                {"date": "ELEC0138", "description": "Security and Privacy", "amount": "Enrolled"},
                {"date": "ELEC0148", "description": "Energy Materials", "amount": "Enrolled"},
            ],
        },
        "eva@example.com": {
            "balance": 7800.30,
            "currency": "GBP",
            "transactions": [
                {"date": "MGMT101", "description": "Project Management", "amount": "Enrolled"},
                {"date": "ENGR300", "description": "Research Methods", "amount": "Enrolled"},
                {"date": "AI301", "description": "Applied AI Systems", "amount": "Enrolled"},
            ],
        },
    }
    return fake_accounts.get(username)


def get_forum_posts():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, author, title, content, created_at
        FROM forum_posts
        ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()

    posts = []
    for r in rows:
        preview = r["content"][:140]
        if len(r["content"]) > 140:
            preview += "..."
        posts.append({
            "id": r["id"],
            "author": r["author"],
            "title": r["title"],
            "content": r["content"],
            "preview": preview,
            "created_at": r["created_at"]
        })
    return posts


def create_forum_post(author, title, content):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO forum_posts (author, title, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (author, title, content, time.time()))
    post_id = cur.lastrowid
    conn.commit()
    conn.close()
    return post_id


def get_forum_post(post_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, author, title, content, created_at
        FROM forum_posts
        WHERE id = ?
    """, (post_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "id": row["id"],
        "author": row["author"],
        "title": row["title"],
        "content": row["content"],
        "created_at": row["created_at"]
    }


def get_comments(post_id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, post_id, author, content, created_at
        FROM comments WHERE post_id = ? ORDER BY id ASC
    """, (post_id,))
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "author": r["author"],
            "content": r["content"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def create_comment(post_id, author, content):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO comments (post_id, author, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (post_id, author, content, time.time()))
    conn.commit()
    conn.close()


def check_rate_limit(ip):
    now = time.time()
    q = request_log[ip]

    while q and now - q[0] > RATE_LIMIT_WINDOW:
        q.popleft()

    if len(q) >= RATE_LIMIT_MAX:
        return False

    q.append(now)
    return True


def log_attempt(username, ip, success, user_agent):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO login_attempts (username, ip_address, success, user_agent, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (username, ip, int(success), user_agent, time.time()))
    conn.commit()
    conn.close()


def authenticate_user(username, password):
    row = get_user(username)
    if row is None:
        return {"ok": False, "reason": "Invalid credentials."}

    user_id, db_username, db_password, mfa_enabled = row

    if password != db_password:
        return {"ok": False, "reason": "Invalid credentials."}

    if mfa_enabled == 1:
        return {"ok": False, "reason": "MFA verification required.", "mfa": True,
                "user": {"id": user_id, "username": db_username}}

    return {
        "ok": True,
        "user": {
            "id": user_id,
            "username": db_username
        }
    }

# Dynamic MFA code system
# Stores active MFA codes
active_mfa_codes = {}
MFA_CODE_EXPIRY = 60  # seconds
MFA_RECEIVER_URL = "http://192.168.1.158:7000/receive-code"


def generate_mfa_code(username):
    """Generate a random 4-digit MFA code and send it to the receiver."""
    # If there's already an active unexpired code, reuse it
    existing = active_mfa_codes.get(username)
    if existing and (time.time() - existing["time"]) < MFA_CODE_EXPIRY:
        print(f"  [MFA] Reusing existing code {existing['code']} for {username}")
        return existing["code"]

    code = str(random.randint(1000, 9999))
    active_mfa_codes[username] = {"code": code, "time": time.time()}
    print(f"  [MFA] Generated code {code} for {username}")

    # Send to the MFA receiver
    try:
        http_requests.post(
            MFA_RECEIVER_URL,
            json={"username": username, "code": code, "timestamp": time.time()},
            timeout=2,
        )
    except Exception:
        print(f"  [MFA] Warning: Could not reach receiver at {MFA_RECEIVER_URL}")

    return code


def verify_mfa_code(username, code):
    """Verify a MFA code — checks value and expiry."""
    entry = active_mfa_codes.get(username)
    if not entry:
        return False

    # Check expiry
    if time.time() - entry["time"] > MFA_CODE_EXPIRY:
        active_mfa_codes.pop(username, None)
        return False

    # Check code
    if entry["code"] == code:
        active_mfa_codes.pop(username, None)
        return True

    return False


# Routes
@app.route("/", methods=["GET"])
def home():
    if session.get("username"):
        return redirect(url_for("dashboard"))
    return render_template_string(LOGIN_PAGE, message=None, message_type="info")


@app.route("/web-login", methods=["POST"])
def web_login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    result = authenticate_user(username, password)

    if not result["ok"] and not result.get("mfa"):
        return render_template_string(
            LOGIN_PAGE,
            message=result["reason"],
            message_type="error"
        )

    if result.get("mfa"):
        # Password correct, MFA required
        session["mfa_pending"] = result["user"]["username"]
        generate_mfa_code(result["user"]["username"])
        return render_template_string(MFA_PAGE, message=None, message_type="info")

    session["username"] = result["user"]["username"]
    return redirect(url_for("dashboard"))


@app.route("/mfa-verify", methods=["POST"])
def mfa_verify():
    pending_user = session.get("mfa_pending")
    if not pending_user:
        return redirect(url_for("home"))

    code = request.form.get("code", "").strip()

    if verify_mfa_code(pending_user, code):
        session.pop("mfa_pending", None)
        session["username"] = pending_user
        return redirect(url_for("dashboard"))
    else:
        return render_template_string(
            MFA_PAGE,
            message="Invalid or expired verification code. Please try again.",
            message_type="error"
        )


@app.route("/dashboard", methods=["GET"])
def dashboard():
    username = session.get("username")
    if not username:
        return redirect(url_for("home"))

    account = get_fake_account(username)
    if not account:
        return redirect(url_for("logout"))

    return render_template_string(
        ACCOUNT_PAGE,
        username=username,
        account=account,
        transactions=account["transactions"]
    )


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/forum", methods=["GET"])
def forum_home():
    username = session.get("username")
    if not username:
        return redirect(url_for("home"))

    posts = get_forum_posts()
    return render_template_string(FORUM_HOME_PAGE, posts=posts)


@app.route("/forum/new", methods=["GET", "POST"])
def forum_new():
    username = session.get("username")
    if not username:
        return redirect(url_for("web_login"))

    state = get_defense_state()

    if request.method == "POST":
        if state["csrf_defense"]:
            submitted_token = request.form.get("csrf_token", "")
            expected_token = session.get("csrf_token", "")
            if not expected_token or submitted_token != expected_token:
                return "CSRF blocked", 403

        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if not title or not content:
            csrf_token = ensure_csrf_token()
            return render_template_string(
                FORUM_NEW_PAGE,
                csrf_token=csrf_token,
                message="Title and content are required.",
                message_type="error"
            )

        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO forum_posts (author, title, content, created_at) VALUES (?, ?, ?, ?)",
            (username, title, content, time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()

        return redirect(url_for("forum_home"))

    csrf_token = ensure_csrf_token()
    return render_template_string(
        FORUM_NEW_PAGE,
        csrf_token=csrf_token,
        message=None,
        message_type="info"
    )


@app.route("/forum/post/<int:post_id>", methods=["GET", "POST"])
def forum_view_post(post_id):
    username = session.get("username")
    if not username:
        return redirect(url_for("web_login"))

    post = get_forum_post(post_id)
    if not post:
        return "Post not found", 404

    if request.method == "POST":
        comment = request.form.get("comment", "").strip()
        if comment:
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO comments (post_id, author, content, created_at) VALUES (?, ?, ?, ?)",
                (post_id, username, comment, time.strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
        return redirect(url_for("forum_view_post", post_id=post_id))

    comments = get_comments(post_id)

    return render_template_string(
        FORUM_POST_UNSAFE_PAGE,
        post=post,
        unsafe_content=post["content"],
        comments=comments
    )



# API routes
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/login", methods=["POST"])
def login_api():
    client_ip = request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "unknown")

    if not check_rate_limit(client_ip):
        return jsonify({
            "status": "blocked",
            "message": "Too many login attempts. Please try again later."
        }), 429

    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        log_attempt(username, client_ip, False, user_agent)
        return jsonify({
            "status": "fail",
            "message": "Username and password are required."
        }), 400

    result = authenticate_user(username, password)

    if not result["ok"] and not result.get("mfa"):
        log_attempt(username, client_ip, False, user_agent)
        return jsonify({
            "status": "fail",
            "message": result["reason"]
        }), 401

    if result.get("mfa"):
        log_attempt(username, client_ip, True, user_agent)
        generate_mfa_code(username)
        return jsonify({
            "status": "mfa_required",
            "message": "Password accepted. MFA verification required.",
            "username": result["user"]["username"]
        }), 200

    log_attempt(username, client_ip, True, user_agent)
    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "user": result["user"]
    }), 200


@app.route("/verify-mfa", methods=["POST"])
def verify_mfa_api():
    """API endpoint for MFA verification (used by portal_fake AiTM proxy)."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    code = data.get("code", "").strip()

    if verify_mfa_code(username, code):
        session["username"] = username
        return jsonify({
            "status": "success",
            "message": "MFA verified. Session established.",
            "session_cookie": request.cookies.get("session", "")
        }), 200
    else:
        return jsonify({
            "status": "fail",
            "message": "Invalid or expired MFA code."
        }), 401


@app.route("/account", methods=["GET"])
def account_api():
    username = request.args.get("username", "").strip()
    account = get_fake_account(username)

    if not account:
        return jsonify({"status": "fail", "message": "Account not found."}), 404

    return jsonify({
        "status": "success",
        "account": account
    }), 200


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)