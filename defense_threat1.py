import json
import re
import sys
import time
from datetime import datetime

OPENAI_API_KEY = "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"  # Hardcode here or use env variable
AI_MODEL = "gpt-4o-mini"

UNIVERSITY_INFO = {
    "domain": "ucl.ac.uk",
    "it_email": "isd-support@ucl.ac.uk",
    "name": "University College London",
}

GOOGLE_API_KEY = "AIzaSyCwyVqm3ojBybf916sZ8oUl2yyQPQke9Hg"
SAFE_BROWSING_URL = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
# Layer 1
def rule_based_detect(email_text):
    score = 0
    reasons = []

    keywords = [
        "urgent", "immediately", "suspended", "locked", "verify",
        "compromised", "act now", "expires", "click here",
        "24 hours", "48 hours", "cancelled", "revoked", "warning",
        "do not ignore", "at risk", "plagiarism", "misconduct",
        "formal investigation", "action required",
    ]
    for kw in keywords:
        if kw.lower() in email_text.lower():
            score += 1
            reasons.append(f"Keyword: '{kw}'")

    typos = [r"suspicous", r"immedately", r"permanantly", r"loosing",
             r"loose ", r"you're (payment|student|account)", r"!!!",
             r"immediatly", r"dont ", r"wont "]
    for p in typos:
        if re.search(p, email_text, re.IGNORECASE):
            score += 2
            reasons.append(f"Typo: '{p}'")

    urls = re.findall(r'https?://[^\s<>"]+', email_text)
    for url in urls:
        if UNIVERSITY_INFO["domain"] not in url:
            score += 2
            reasons.append(f"Suspicious URL: {url[:50]}")

    from_match = re.search(r'From:\s*\S+@(\S+)', email_text, re.IGNORECASE)
    if from_match and UNIVERSITY_INFO["domain"] not in from_match.group(1):
        score += 2
        reasons.append(f"Sender mismatch: {from_match.group(1)}")

    if email_text.count("!") >= 3:
        score += 1
        reasons.append("Excessive punctuation")

    return {
        "is_phishing": score >= 4,
        "confidence": min(score / 12, 1.0),
        "score": score,
        "reasons": reasons,
    }
# Layer 2: PhishTank URL Check
def safe_browsing_check(email_text):
    import requests as http_requests

    urls = re.findall(r'https?://[^\s<>"]+', email_text)
    if not urls:
        return {
            "is_phishing": False,
            "confidence": 0.0,
            "reasons": ["No URLs found"]
        }

    flagged = []
    checked = []

    for url in urls[:5]:  # limit to 5 URLs
        if UNIVERSITY_INFO["domain"] in url:
            continue

        try:
            payload = {
                "client": {
                    "clientId": "ucl-phishing-detector",
                    "clientVersion": "1.0"
                },
                "threatInfo": {
                    "threatTypes": [
                        "MALWARE",
                        "SOCIAL_ENGINEERING",
                        "UNWANTED_SOFTWARE"
                    ],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [
                        {"url": url}
                    ]
                }
            }

            resp = http_requests.post(
                f"{SAFE_BROWSING_URL}?key={GOOGLE_API_KEY}",
                json=payload,
                timeout=5
            )

            if resp.status_code == 200:
                data = resp.json()

                if "matches" in data:
                    flagged.append(f"Google Safe Browsing MATCH: {url}")
                else:
                    checked.append(f"Clean (not flagged): {url}")
            else:
                checked.append(f"API error: {url}")

        except Exception:
            checked.append(f"API timeout: {url}")

    return {
        "is_phishing": len(flagged) > 0,
        "confidence": len(flagged) / max(len(urls), 1),
        "reasons": flagged + checked
    }

def phishtank_check(email_text):
    import requests as http_requests

    urls = re.findall(r'https?://[^\s<>"]+', email_text)
    if not urls:
        return {"is_phishing": False, "confidence": 0.0, "reasons": ["No URLs found"]}

    flagged = []
    for url in urls[:5]:
        if UNIVERSITY_INFO["domain"] in url:
            continue
        try:
            resp = http_requests.post(
                PHISHTANK_API,
                data={
                    "url": url,
                    "format": "json",
                    "app_key": PHISHTANK_APP_KEY,
                },
                headers={
                    "User-Agent": "phishtank/ELEC0138-CW-Demo",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("results", {}).get("in_database"):
                    flagged.append(f"PhishTank MATCH: {url[:50]}")
                else:
                    flagged.append(f"Non-university URL (not in PhishTank): {url[:50]}")
            else:
                flagged.append(f"Non-university URL (API error): {url[:50]}")
        except Exception:
            flagged.append(f"Non-university URL (API timeout): {url[:50]}")

    return {
        "is_phishing": len(flagged) > 0,
        "confidence": min(len(flagged) / max(len(urls), 1), 1.0),
        "reasons": flagged if flagged else ["All URLs legitimate"],
    }

# Layer 3: LLM Classifier
def llm_detect(email_text):
    from openai import OpenAI

    if not OPENAI_API_KEY:
        return {
            "is_phishing": False,
            "confidence": 0.0,
            "reasons": ["LLM disabled (no API key)"],
            "reasoning": "SKIPPED",
            "status": "SKIPPED"
        }

    try:
        # ✅ Step 2: 正常调用
        client = OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a university email security system. Analyse for phishing. "
                    "Respond ONLY with valid JSON, no markdown."
                )},
                {"role": "user", "content": f"""Analyse this email:

{email_text}

Legitimate domain: {UNIVERSITY_INFO['domain']}
Legitimate IT email: {UNIVERSITY_INFO['it_email']}

Respond JSON: {{"is_phishing": true/false, "confidence": 0.0-1.0, "indicators": ["..."], "reasoning": "..."}}"""}
            ],
            temperature=0.1,
            max_tokens=400,
        )

        text = response.choices[0].message.content.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        result = json.loads(text)

        return {
            "is_phishing": result.get("is_phishing", False),
            "confidence": result.get("confidence", 0.0),
            "reasons": result.get("indicators", []),
            "reasoning": result.get("reasoning", ""),
            "status": "OK"
        }

    except Exception as e:
        # ❗关键：API失败 ≠ phishing
        return {
            "is_phishing": False,
            "confidence": 0.0,
            "reasons": [f"API error: {e}"],
            "reasoning": "LLM unavailable",
            "status": "ERROR"
        }
# Display single email analysis
def analyse_and_display(email_text, label=""):
    if label:
        print(f"\n  Analysing: {label}")
    print("  " + "-" * 55)

    r1 = rule_based_detect(email_text)
    print(f"  Layer 1 (Rule-based):   {'DETECTED' if r1['is_phishing'] else 'MISSED':<10} "
          f"(score: {r1['score']}, conf: {r1['confidence']:.0%})")
    for r in r1["reasons"][:3]:
        print(f"    - {r}")

    print(f"  Layer 2 (Safe Browsing):", end=" ", flush=True)
    r2 = safe_browsing_check(email_text)
    print(f"{'FLAGGED' if r2['is_phishing'] else 'CLEAR':<10} "
          f"(conf: {r2['confidence']:.0%})")
    for r in r2["reasons"][:2]:
        print(f"    - {r}")

    print(f"  Layer 3 (LLM):          ", end="", flush=True)
    r3 = llm_detect(email_text)

    if r3["status"] == "SKIPPED":
        label = "SKIPPED"
    elif r3["status"] == "ERROR":
        label = "ERROR"
    elif r3["is_phishing"]:
        label = "DETECTED"
    else:
        label = "MISSED"

    print(f"{label:<10} (conf: {r3['confidence']:.0%})")

    if r3.get("reasoning"):
        print(f"    - {r3['reasoning']}")

    valid_layers = [r1, r2, r3]
    detected_count = sum(
        1 for r in valid_layers
        if r.get("is_phishing") and r.get("status", "OK") == "OK"
    )
    print()
    print(f"  VERDICT: {'PHISHING' if detected_count >= 1 else 'LIKELY SAFE'} "
          f"({detected_count}/3 layers triggered)")
    print("  " + "-" * 55)

    return {"rule": r1, "phishtank": r2, "llm": r3, "detected_count": detected_count}

# Interactive mode

def interactive_mode():
    print("=" * 60)
    print("  PHISHING EMAIL DETECTOR — Interactive Mode")
    print("  👉 Paste full email content (multi-line supported)")
    print("  👉 Type 'END' on a new line to analyse")
    print("  👉 Type 'quit' anytime to exit")
    print("=" * 60)
    print()

    while True:
        print("\n  Paste email below:")
        lines = []

        while True:
            try:
                line = input()
            except EOFError:
                print("\n  Input stream closed. Exiting.")
                return

            if line.strip().lower() == "quit":
                print("  Bye!")
                return

            if line.strip().lower() == "end":
                if not lines:
                    print("  ⚠️ No email content detected. Please paste again.")
                    continue
                break

            lines.append(line)

        email_text = "\n".join(lines).strip()

        if not email_text:
            print("  ⚠️ Empty input, skipped.")
            continue

        print("\n  🔍 Analysing email...\n")
        analyse_and_display(email_text)

        print("\n" + "=" * 60)


# Batch mode
def batch_mode(filepath):
    print("=" * 70)
    print("  PHISHING EMAIL DETECTOR — Batch Mode")
    print(f"  Reading: {filepath}")
    print("=" * 70)
    print()

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples = data.get("samples", [])
    if not samples:
        print("  No samples found in file.")
        return

    summary = {
        "ai": {"rule": 0, "phishtank": 0, "llm": 0, "total": 0},
        "trad": {"rule": 0, "phishtank": 0, "llm": 0, "total": 0},
    }

    for i, sample in enumerate(samples, 1):
        target = sample.get("target", "?")
        scenario = sample.get("scenario", "?")

        ai_email = sample.get("ai_email", "")
        if ai_email and not ai_email.startswith("["):
            print(f"  [{i}/{len(samples)}] {target} x {scenario} — AI email")
            result = analyse_and_display(ai_email, f"AI email for {target}")
            summary["ai"]["total"] += 1
            if result["rule"]["is_phishing"]: summary["ai"]["rule"] += 1
            if result["phishtank"]["is_phishing"]: summary["ai"]["phishtank"] += 1
            if result["llm"]["is_phishing"]: summary["ai"]["llm"] += 1
            time.sleep(1)

        trad_email = sample.get("trad_email", "")
        if trad_email:
            print(f"  [{i}/{len(samples)}] {target} x {scenario} — Traditional email")
            result = analyse_and_display(trad_email, f"Traditional email for {target}")
            summary["trad"]["total"] += 1
            if result["rule"]["is_phishing"]: summary["trad"]["rule"] += 1
            if result["phishtank"]["is_phishing"]: summary["trad"]["phishtank"] += 1
            if result["llm"]["is_phishing"]: summary["trad"]["llm"] += 1
            time.sleep(1)

        print()

    at = summary["ai"]["total"] or 1
    tt = summary["trad"]["total"] or 1

    print("=" * 70)
    print("  DETECTION RATE COMPARISON TABLE (for report)")
    print("=" * 70)
    print()
    print(f"  {'Layer':<20} {'vs AI Phishing':<25} {'vs Traditional':<25}")
    print(f"  {'─' * 20} {'─' * 25} {'─' * 25}")
    print(f"  {'Rule-based':<20} "
          f"{summary['ai']['rule']}/{at} ({summary['ai']['rule']/at*100:.0f}%)"
          f"{'':>13}"
          f"{summary['trad']['rule']}/{tt} ({summary['trad']['rule']/tt*100:.0f}%)")
    print(f"  {'PhishTank':<20} "
          f"{summary['ai']['phishtank']}/{at} ({summary['ai']['phishtank']/at*100:.0f}%)"
          f"{'':>13}"
          f"{summary['trad']['phishtank']}/{tt} ({summary['trad']['phishtank']/tt*100:.0f}%)")
    print(f"  {'LLM Classifier':<20} "
          f"{summary['ai']['llm']}/{at} ({summary['ai']['llm']/at*100:.0f}%)"
          f"{'':>13}"
          f"{summary['trad']['llm']}/{tt} ({summary['trad']['llm']/tt*100:.0f}%)")
    print()
    print("  KEY FINDINGS:")
    print(f"  1. Rule-based: {summary['trad']['rule']/tt*100:.0f}% vs traditional, "
          f"{summary['ai']['rule']/at*100:.0f}% vs AI phishing")
    print(f"  2. PhishTank:  catches non-university URLs but not in known DB")
    print(f"  3. LLM:       {summary['ai']['llm']/at*100:.0f}% vs AI phishing — "
          f"best layer against AI-generated attacks")
    print(f"  4. Multi-layer defense needed: no single layer catches everything")
    print("=" * 70)

    # Save
    with open("defense_threat1_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Results saved to defense_threat1_results.json")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--batch":
        batch_mode(sys.argv[2])
    else:
        interactive_mode()
