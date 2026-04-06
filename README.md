# phishing-maestro
# ELEC0138 Security & Privacy — Threat Modelling & Attack Simulation

> **UCL Electronic & Electrical Engineering — Coursework 2025**
> Educational demonstration only. All attacks are performed in a controlled local environment.

---

## Overview

This project demonstrates two real-world cybersecurity threats against a simulated university student portal, along with corresponding defence mechanisms. The primary focus is on **AI-assisted phishing** — specifically, how large language models (GPT-4o-mini) can generate highly convincing, personalised spear phishing emails that bypass traditional detection methods and enable complete MFA bypass through an Adversary-in-the-Middle (AiTM) proxy.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PORTAL (port 5000)                        │
│  Flask/SQLite — Auth, MFA, Dashboard, Discussion Forum      │
└──────────┬──────────────────────────────────┬────────────────┘
           │                                  │
     Threat 1: AiTM                    Threat 2: Stored XSS
           │                                  │
┌──────────▼──────────┐          ┌────────────▼───────────────┐
│ portal_fake (6001)  │          │ attack_xss.py              │
│ AI phishing (5001)  │          │ 3 payloads: cookie theft,  │
│ MFA relay + capture │          │ keylogger, session riding   │
└──────────┬──────────┘          └────────────┬───────────────┘
           │                                  │
┌──────────▼──────────┐          ┌────────────▼───────────────┐
│ defense_threat1.py  │          │ defense_threat2.py (9100)  │
│ 3-layer detector:   │          │ Toggle: HttpOnly, CSP,     │
│ Rules + SafeBrowse  │          │ CSRF token validation      │
│ + LLM classifier    │          │                            │
└─────────────────────┘          └────────────────────────────┘
```

## Components

### Target System
| File | Port | Description |
|------|------|-------------|
| `portal.py` | 5000 | University student portal — login, MFA, dashboard, forum |
| `mfa.py` | 7000 | Simulated SMS inbox for MFA verification codes |

### Threat 1: AI-Powered AiTM Phishing
| File | Port | Description |
|------|------|-------------|
| `attack_phishing.py` | 5001 | AI phishing email generator using GPT-4o-mini — produces personalised emails targeting specific students with contextual details (name, department, modules) |
| `portal_fake.py` | 6001 | AiTM phishing proxy — visually identical to the real portal, relays credentials and MFA codes in real time, captures authenticated session cookies |

**Key finding:** The AI-generated emails are contextually appropriate, grammatically fluent, and reference real university structure. Combined with the real-time MFA relay, the entire attack chain — from credential entry to session hijack — completes in approximately **8 seconds**.

### Threat 2: Stored XSS
| File | Port | Description |
|------|------|-------------|
| `attack_xss.py` | — | Injects 3 XSS payloads into the forum as innocuous-looking posts |
| `attacker_server.py` | 8888 | Receives stolen cookies, keystrokes, and CSRF confirmation beacons |

**Three payload variants, each blocked by a different defence:**

| Payload | What it does | Blocked by |
|---------|-------------|------------|
| Cookie Stealer | Exfiltrates `document.cookie` via `Image.src` | HttpOnly flag |
| Keylogger | Captures keystrokes via `fetch()` to attacker | CSP `connect-src 'self'` |
| Session Riding | Creates forum post as victim via `POST /forum/new` | CSRF token validation |

### Defences
| File | Port | Description |
|------|------|-------------|
| `defense_threat1.py` | — | 3-layer phishing email detector: rule-based keyword analysis → Google Safe Browsing URL check → GPT-4o-mini semantic classification |
| `defense_threat2.py` | 9100 | Runtime defence toggle — independently enable/disable HttpOnly cookies, CSP headers, and CSRF token validation |

## Quick Start

### Prerequisites
```bash
pip install flask requests openai
```

### Run the full demo

**Terminal 1 — Portal:**
```bash
python portal.py
```

**Terminal 2 — MFA Receiver:**
```bash
python mfa.py
```

**Terminal 3 — Threat 1 Attack:**
```bash
python portal_fake.py          # AiTM proxy on :6001
python attack_phishing.py      # AI email generator on :5001
```

**Terminal 4 — Threat 2 Attack:**
```bash
python attacker_server.py      # Exfiltration receiver on :8888
python attack_xss.py           # Inject XSS payloads into forum
```

**Terminal 5 — Defences:**
```bash
python defense_threat2.py      # XSS defence toggles on :9100
python defense_threat1.py      # Phishing detector (interactive mode)
```

### Demo Accounts
| Email | Password | MFA |
|-------|----------|-----|
| alice@example.com | Password123 | Enabled |
| diana@example.com | Welcome1 | Enabled |
| bob@example.com | qwerty123 | Disabled (attacker account) |

## Key Dashboards

| URL | What it shows |
|-----|--------------|
| `http://localhost:5000` | Legitimate portal login |
| `http://localhost:6001` | Fake portal (AiTM proxy) |
| `http://localhost:6001/dashboard` | Captured credentials, MFA codes, hijacked sessions |
| `http://localhost:7000` | Simulated phone SMS inbox with MFA codes |
| `http://localhost:8888` | XSS exfiltration dashboard (cookies, keystrokes, CSRF logs) |
| `http://localhost:9100` | Defence toggle panel for Threat 2 |

## Project Structure
```
├── portal.py               # Target university portal
├── mfa.py                  # Simulated MFA SMS receiver
├── portal_fake.py          # AiTM phishing proxy
├── attack_phishing.py      # AI-powered phishing email generator
├── attack_xss.py           # Stored XSS payload injector
├── attacker_server.py      # Exfiltration receiver (cookies/keys/CSRF)
├── defense_threat1.py      # 3-layer phishing email detector
└── defense_threat2.py      # XSS defence toggle service
```

## Disclaimer

This project is developed exclusively for **educational purposes** as part of the ELEC0138 Security and Privacy module at University College London. All attacks are executed within a controlled local environment against a purpose-built demonstration application. No real systems, networks, or user data are targeted. Do not use any of these tools outside of a controlled lab setting.

## License

Academic coursework — not for redistribution or commercial use.
