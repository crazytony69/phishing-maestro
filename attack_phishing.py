from flask import Flask, request, render_template_string, jsonify, redirect, url_for
import json
import re
import time
import socket
import requests as http_requests
from datetime import datetime
from openai import OpenAI

app = Flask(__name__)
app.secret_key = "phishing_generator_secret"

# Configuration

OPENAI_API_KEY = "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"

AI_MODEL = "gpt-4o-mini"

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

LOCAL_IP = get_local_ip()
FAKE_PORTAL_URL = f"http://{LOCAL_IP}:6001"

UNIVERSITY_INFO = {
    "name": "University College London",
    "short": "UCL",
    "domain": "ucl.ac.uk",
    "it_email": "isd-support@ucl.ac.uk",
    "department": "Information Services Division (ISD)",
}

PUBLIC_CONTEXT_URLS = [
    "https://www.ucl.ac.uk/",
    "https://www.ucl.ac.uk/isd/",
]

# Storage for generated emails
generated_emails = []

# Target students 

TARGET_USERS = {
    "alice": {
        "name": "Alice",
        "email": "alice@example.com",
        "department": "Electronic & Electrical Engineering",
        "modules": ["ELEC0138 Security and Privacy",
                     "ELEC0149 Introduction to Machine Learning"],
        "year": "MSc",
    },
    "diana": {
        "name": "Diana",
        "email": "diana@example.com",
        "department": "Electronic & Electrical Engineering",
        "modules": ["ELEC0025 Photonics II",
                     "ELEC0138 Security and Privacy"],
        "year": "MSc",
    },
    "eva": {
        "name": "Eva",
        "email": "eva@example.com",
        "department": "Engineering Management",
        "modules": ["MGMT101 Project Management",
                     "AI301 Applied AI Systems"],
        "year": "PhD",
    },
    "charlie": {
        "name": "Charlie",
        "email": "charlie@example.com",
        "department": "Electronic & Electrical Engineering",
        "modules": ["STAT201 Applied Statistics",
                     "CS220 Networks"],
        "year": "UG Year 3",
    },
}

SCENARIOS = {
    "academic_misconduct": {
        "label": "Academic Misconduct Investigation",
        "prompt": (
            "The university Academic Integrity Office has flagged a potential "
            "plagiarism match in the student's recent coursework submission. "
            "The student must log in to the portal immediately to review the "
            "case details and submit a response before the deadline, or a "
            "formal investigation will proceed without their input."
        ),
    },
    "tuition_hold": {
        "label": "Tuition Payment Hold",
        "prompt": (
            "The Finance Office has identified an unresolved tuition payment "
            "discrepancy on the student's account. Unless the student verifies "
            "their payment details via the portal within 48 hours, their "
            "module enrolment for the current term may be suspended and exam "
            "eligibility could be affected."
        ),
    },
    "security_breach": {
        "label": "Suspicious Login Activity",
        "prompt": (
            "The university IT Security team has detected multiple failed "
            "login attempts on the student's account from an unrecognised "
            "device in a foreign country. As a precaution, the student must "
            "verify their identity through the portal within 24 hours to "
            "prevent their account from being temporarily locked."
        ),
    },
    "scholarship_review": {
        "label": "Scholarship Eligibility Review",
        "prompt": (
            "The Student Funding Office is conducting an eligibility review "
            "for the student's scholarship or bursary. The student must log "
            "in to confirm their enrolment status and upload updated documents "
            "within 72 hours, or their funding may be suspended pending review."
        ),
    },
}



# HTML Templates

GENERATOR_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Phishing Email Generator</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1e293b; color: #e2e8f0; padding: 32px; }
        .container { max-width: 700px; margin: 0 auto; }
        h1 { color: #f87171; margin-bottom: 6px; }
        .subtitle { color: #94a3b8; margin-bottom: 24px; }
        .card { background: #334155; border-radius: 14px; padding: 24px; margin-bottom: 18px; }
        label { display: block; color: #94a3b8; font-size: 13px; margin-bottom: 6px; margin-top: 14px; }
        select { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid #475569;
                 background: #1e293b; color: #e2e8f0; font-size: 14px; }
        button { margin-top: 18px; width: 100%; padding: 14px; background: #dc2626; color: white;
                 border: none; border-radius: 10px; font-size: 16px; cursor: pointer; font-weight: bold; }
        button:hover { background: #b91c1c; }
        .nav { margin-bottom: 18px; }
        .nav a { color: #22d3ee; margin-right: 16px; text-decoration: none; }
        .info { background: #1e293b; border-radius: 10px; padding: 12px; margin-top: 14px;
                font-size: 13px; color: #94a3b8; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Phishing Email Generator</h1>

        <div class="nav">
            <a href="/">Generator</a>
            <a href="/gallery">Email Gallery ({{ email_count }})</a>
        </div>

        <div class="card">
            <form method="POST" action="/generate">
                <label>Target Student</label>
                <select name="target">
                    {% for key, t in targets.items() %}
                    <option value="{{ key }}">{{ t.name }} — {{ t.department }} ({{ t.year }})</option>
                    {% endfor %}
                </select>

                <label>Phishing Scenario</label>
                <select name="scenario">
                    {% for key, s in scenarios.items() %}
                    <option value="{{ key }}">{{ s.label }}</option>
                    {% endfor %}
                </select>

                <button type="submit">Generate Phishing Email</button>
            </form>

        </div>
    </div>
</body>
</html>
"""

EMAIL_DISPLAY_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Phishing Email</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f1f5f9; padding: 40px; }
        .container { max-width: 760px; margin: 0 auto; }
        .tag { display: inline-block; background: #fee2e2; color: #991b1b; padding: 6px 10px;
               border-radius: 999px; font-size: 12px; margin-bottom: 12px; }
        .card { background: white; border-radius: 18px; padding: 28px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.08); margin-bottom: 18px; }
        h1 { margin-top: 0; color: #0f172a; font-size: 22px; }
        .email-header { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px;
                        padding: 14px; margin-bottom: 14px; }
        .email-header .field { margin-bottom: 6px; font-size: 14px; }
        .email-header .label { color: #64748b; font-weight: bold; }
        .email-header .value { color: #0f172a; }
        .email-body { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px;
                      padding: 20px; line-height: 1.7; color: #334155; white-space: pre-line; }
        .meta { margin-top: 12px; color: #64748b; font-size: 12px; }
        .btn { display: inline-block; margin-top: 16px; text-decoration: none; color: white;
               padding: 10px 14px; border-radius: 10px; margin-right: 10px; }
        .btn-primary { background: #dc2626; }
        .btn-secondary { background: #334155; }
        .btn-green { background: #0f766e; }
        .note { margin-top: 16px; background: #fef3c7; color: #92400e; padding: 12px;
                border-radius: 10px; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="tag">AI-Generated Phishing Email</div>

        <div class="card">
            <h1>{{ scenario_label }}</h1>

            <div class="email-header">
                <div class="field"><span class="label">To: </span><span class="value">{{ target_email }}</span></div>
                <div class="field"><span class="label">Subject: </span><span class="value">{{ email_subject }}</span></div>
            </div>

            <div class="email-body">{{ email_body | replace(fake_url, '<a href="' + fake_url + '">' + fake_url + '</a>') | safe }}</div>

            <div class="meta">
                Target: {{ target_name }} ({{ target_dept }}) |
                Scenario: {{ scenario_id }} |
                Generated: {{ timestamp }} |
                Model: {{ model }}
            </div>
            <a class="btn btn-secondary" href="/">Generate Another</a>
            <a class="btn btn-green" href="/gallery">View All Emails</a>


        </div>
    </div>
</body>
</html>
"""

GALLERY_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phishing Email Gallery</title>
    <style>
        body { font-family: Arial, sans-serif; background: #1e293b; color: #e2e8f0; padding: 32px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #f87171; margin-bottom: 6px; }
        .subtitle { color: #94a3b8; margin-bottom: 24px; }
        .nav { margin-bottom: 18px; }
        .nav a { color: #22d3ee; margin-right: 16px; text-decoration: none; }
        .card { background: #334155; border-radius: 14px; padding: 20px; margin-bottom: 14px; }
        .card h2 { margin: 0 0 6px 0; color: #fbbf24; font-size: 16px; }
        .card .to { color: #94a3b8; font-size: 13px; margin-bottom: 8px; }
        .card .subject { color: #e2e8f0; font-size: 15px; margin-bottom: 8px; }
        .card .preview { color: #94a3b8; font-size: 13px; line-height: 1.5; }
        .card .meta { color: #475569; font-size: 12px; margin-top: 8px; }
        .tag { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 11px;
               font-weight: bold; margin-right: 6px; }
        .tag-misc { background: #7c3aed; color: white; }
        .tag-tuition { background: #ea580c; color: white; }
        .tag-security { background: #dc2626; color: white; }
        .tag-scholarship { background: #0891b2; color: white; }
        .empty { color: #64748b; font-style: italic; padding: 40px 0; text-align: center; }
        .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 24px; }
        .stat { background: #334155; border-radius: 12px; padding: 18px; text-align: center; }
        .stat .label { color: #94a3b8; font-size: 13px; }
        .stat .count { font-size: 36px; font-weight: bold; color: #f87171; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Phishing Email Gallery</h1>
        <div class="subtitle">All AI-generated phishing emails in this session</div>

        <div class="nav">
            <a href="/">Generator</a>
            <a href="/gallery">Gallery ({{ emails | length }})</a>
        </div>

        <div class="stats">
            <div class="stat">
                <div class="label">Emails Generated</div>
                <div class="count">{{ emails | length }}</div>
            </div>
            <div class="stat">
                <div class="label">Unique Targets</div>
                <div class="count">{{ unique_targets }}</div>
            </div>
            <div class="stat">
                <div class="label">Scenarios Used</div>
                <div class="count">{{ unique_scenarios }}</div>
            </div>
        </div>

        {% if emails %}
            {% for e in emails | reverse %}
            <div class="card">
                <span class="tag
                    {% if e.scenario_id == 'academic_misconduct' %}tag-misc
                    {% elif e.scenario_id == 'tuition_hold' %}tag-tuition
                    {% elif e.scenario_id == 'security_breach' %}tag-security
                    {% else %}tag-scholarship{% endif %}
                ">{{ e.scenario_label }}</span>
                <div class="to">To: {{ e.target_email }}</div>
                <div class="subject">Subject: {{ e.subject }}</div>
                <div class="preview">{{ e.body[:200] }}...</div>
                <div class="meta">{{ e.target_name }} | {{ e.timestamp }}</div>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty">No emails generated yet. Go to the Generator to create one.</div>
        {% endif %}
    </div>
</body>
</html>
"""



# Helpers

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def extract_text_from_html(html_text):
    html_text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html_text)
    html_text = re.sub(r"(?is)<style.*?>.*?</style>", " ", html_text)
    html_text = re.sub(r"(?s)<[^>]+>", " ", html_text)
    return clean_text(html_text)


def collect_public_context():
    pages = []
    for url in PUBLIC_CONTEXT_URLS:
        try:
            resp = http_requests.get(url, timeout=10,
                                      headers={"User-Agent": "ELEC0138-CW/1.0"})
            resp.raise_for_status()
            text = extract_text_from_html(resp.text)[:2000]
            pages.append({"url": url, "text": text})
        except Exception:
            continue
    return pages


def build_context_summary(pages):
    return "\n\n".join(f"URL: {p['url']}\nContent: {p['text'][:1200]}" for p in pages)


def get_openai_client():
    if OPENAI_API_KEY:
        return OpenAI(api_key=OPENAI_API_KEY)
    return OpenAI()


def generate_ai_email(target, scenario, context_summary):
    client = get_openai_client()
    modules_str = ", ".join(target["modules"])

    system_prompt = (
        "You are a cybersecurity researcher generating phishing email samples "
        "for an educational university security assessment in a controlled lab. "
        "Generate a realistic phishing email. Return valid JSON only, "
        "no markdown formatting."
    )

    user_prompt = f"""Generate a realistic phishing email.

TARGET (gathered via OSINT):
- Name: {target['name']}
- Email: {target['email']}
- Department: {target['department']}
- Modules: {modules_str}
- Year: {target['year']}

UNIVERSITY: {UNIVERSITY_INFO['name']} ({UNIVERSITY_INFO['short']})
IT Department: {UNIVERSITY_INFO['department']}

SCENARIO:
{scenario['prompt']}

PHISHING LINK (include exactly once):
{FAKE_PORTAL_URL}

PUBLIC CONTEXT:
{context_summary}

REQUIREMENTS:
- Reference the student's specific modules where relevant
- Match real university administrative email tone
- Zero spelling/grammar errors
- Create genuine urgency and anxiety
- Sign off as a believable university department
- Return JSON only: {{"subject": "...", "body": "..."}}
"""

    response = client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=800,
    )

    text = response.choices[0].message.content.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return json.loads(text)



# Routes

@app.route("/", methods=["GET"])
def index():
    return render_template_string(
        GENERATOR_PAGE,
        targets=TARGET_USERS,
        scenarios=SCENARIOS,
        fake_url=FAKE_PORTAL_URL,
        email_count=len(generated_emails),
    )


@app.route("/generate", methods=["POST"])
def generate():
    target_key = request.form.get("target", "alice")
    scenario_key = request.form.get("scenario", "academic_misconduct")

    target = TARGET_USERS.get(target_key, TARGET_USERS["alice"])
    scenario = SCENARIOS.get(scenario_key, SCENARIOS["academic_misconduct"])

    # Collect OSINT context
    pages = collect_public_context()
    context_summary = build_context_summary(pages)

    # Generate email
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        email_data = generate_ai_email(target, scenario, context_summary)
        email_subject = email_data["subject"]
        email_body = email_data["body"]
    except Exception as e:
        email_subject = f"Important: Action required for your {UNIVERSITY_INFO['short']} account"
        email_body = (
            f"Dear {target['name']},\n\n"
            f"{scenario['prompt']}\n\n"
            f"Please verify your account immediately:\n"
            f"{FAKE_PORTAL_URL}\n\n"
            f"{UNIVERSITY_INFO['department']}\n"
            f"{UNIVERSITY_INFO['name']}\n\n"
            f"[Fallback template — AI generation failed: {e}]"
        )

    # Store
    generated_emails.append({
        "target_name": target["name"],
        "target_email": target["email"],
        "target_dept": target["department"],
        "scenario_id": scenario_key,
        "scenario_label": scenario["label"],
        "subject": email_subject,
        "body": email_body,
        "timestamp": timestamp,
    })

    print(f"\n  [EMAIL] Generated for {target['name']} x {scenario['label']}")
    print(f"          Subject: {email_subject}")

    return render_template_string(
        EMAIL_DISPLAY_PAGE,
        target_name=target["name"],
        target_email=target["email"],
        target_dept=target["department"],
        scenario_id=scenario_key,
        scenario_label=scenario["label"],
        email_subject=email_subject,
        email_body=email_body,
        fake_url=FAKE_PORTAL_URL,
        timestamp=timestamp,
        model=AI_MODEL,
    )


@app.route("/gallery", methods=["GET"])
def gallery():
    unique_targets = len(set(e["target_name"] for e in generated_emails))
    unique_scenarios = len(set(e["scenario_id"] for e in generated_emails))

    return render_template_string(
        GALLERY_PAGE,
        emails=generated_emails,
        unique_targets=unique_targets,
        unique_scenarios=unique_scenarios,
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  AI PHISHING EMAIL GENERATOR")
    print("=" * 60)
    print(f"  Generator:    http://{LOCAL_IP}:5001")
    print(f"  Fake portal:  {FAKE_PORTAL_URL}")
    print(f"  Model:        {AI_MODEL}")
    print("=" * 60)
    print()
    app.run(host="0.0.0.0", port=5001, debug=True)
