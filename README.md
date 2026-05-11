# IdentityFlow — Self-Service Identity Lifecycle Automation

<div align="center">

![TechCorp](https://img.shields.io/badge/TechCorp-Identity%20Portal-5b8dee?style=for-the-badge)
![Flask](https://img.shields.io/badge/Flask-Backend-000000?style=for-the-badge&logo=flask)
![JavaScript](https://img.shields.io/badge/JavaScript-Frontend-F7DF1E?style=for-the-badge&logo=javascript)
![Industry](https://img.shields.io/badge/Industry-IT%20%2F%20Technology-10b981?style=for-the-badge)

**Self-Service Identity Lifecycle Automation for IT Teams**

*Manual Joiner-Mover-Leaver processes cause delays, errors, and orphaned accounts. IdentityFlow fixes that.*

</div>

---

## The Problem

In IT companies, onboarding a new engineer means manually requesting access to GitHub, AWS, Jira, Slack, Okta, and more — across multiple teams. Role changes leave behind stale permissions. Offboarding is often forgotten, leaving active accounts for ex-employees. This is a security risk and an operational nightmare.

## The Solution

IdentityFlow is a self-service portal that automates the entire identity lifecycle:

- **Joiners** — one form provisions all role-appropriate tools automatically
- **Movers** — role changes diff old vs new access and update everything
- **Leavers** — offboarding revokes all system access in one click

With multi-level approval workflows, risk scoring, and a full audit trail built in.

---

## Features

| | Feature | Description |
|---|---|---|
| 🔄 | **JML Workflows** | Automated Joiner, Mover, Leaver request processing |
| ✅ | **Multi-Level Approvals** | L1 Manager → L2 IT Security → L3 IT Compliance |
| 🔴 | **Risk Scoring** | Every request scored LOW → CRITICAL with SoD detection |
| ⚡ | **Emergency Override** | Bypass approval chain with full audit trail |
| 🔐 | **RBAC** | 5 portal roles with scoped permissions |
| 📋 | **Audit Log** | Every action logged — actor, timestamp, severity |
| 💬 | **NL Chatbot** | "Onboard Sam Lee as a DevOps Engineer at sam@techcorp.io" |
| ⏱ | **SLA Timers** | Flags approvals pending over 24 hours |
| 🔍 | **Orphan Detection** | Surfaces inactive users with lingering access |
| 🪪 | **Identity Documents** | Verified ID card for every request |
| 📊 | **Analytics Dashboard** | Activity chart, risk breakdown, system coverage |

---

## Systems Simulated

> No production systems are connected — all IAM calls are fully simulated.

`GitHub` · `Jira` · `Confluence` · `Slack` · `AWS Dev` · `AWS Prod` · `PagerDuty` · `Datadog` · `Okta` · `VPN` · `SIEM` · `MDM` · `Active Directory` · `HR System`

---

## Roles Supported

`Software Engineer` · `Senior Software Engineer` · `DevOps Engineer` · `Site Reliability Engineer` · `Security Analyst` · `Engineering Manager` · `IT Administrator` · `Data Engineer` · `Product Manager` · `Intern`

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/chandra23225/IdentityFlow.git
cd IdentityFlow

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Seed demo data
python demo_seed.py

# Start the API server
python app.py
```

Open a second terminal:

```bash
# Serve the frontend
cd frontend
python -m http.server 8080
```

Open **http://localhost:8080** in your browser.

---

## Demo Accounts

| Username | Password | Role | Access Level |
|---|---|---|---|
| `admin001` | `admin123` | IAM Administrator | Full access + emergency override |
| `mgr001` | `manager123` | Engineering Manager | L1 approvals |
| `sec001` | `security123` | IT Security | L2 approvals |
| `comp001` | `itadmin123` | IT Compliance | L3 approvals |
| `hr001` | `hr123` | HR Specialist | Create requests only |

---

## How the Approval Chain Works

```
Request submitted
       │
       ▼
  Risk scored ──── LOW/MEDIUM ──── Auto-approved → IAM provisioned
       │
    HIGH/CRITICAL
       │
       ▼
  L1: Manager Approval
       │
       ▼
  L2: IT Security Review
       │
       ▼
  L3: IT Compliance Sign-off
       │
       ▼
  IAM provisioned across all systems
```

Critical systems like `AWS_Prod`, `Okta`, and `AD` always require all 3 levels.

---

## Project Structure

```
IdentityFlow/
├── backend/
│   ├── app.py              # Flask REST API (15 endpoints)
│   ├── workflows.py        # JML engine + multi-level approval chain
│   ├── iam_simulator.py    # Simulated IAM API calls
│   ├── risk.py             # Risk scoring + SoD conflict detection
│   ├── chatbot.py          # Natural language intent parser
│   ├── demo_seed.py        # Realistic demo data seeder
│   ├── requirements.txt
│   └── data/
│       ├── users.json      # Employee records
│       ├── roles.json      # Role → system mappings
│       ├── requests.json   # JML request history
│       ├── rbac.json       # Portal user accounts
│       └── audit_log.json  # Full audit trail
└── frontend/
    ├── index.html          # Single-page app
    ├── style.css           # Dark theme UI
    ├── app.js              # All frontend logic
    └── config.js           # API URL config
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/rbac/login` | Authenticate portal user |
| `GET` | `/users` | List all employees |
| `GET` | `/roles` | List roles and system mappings |
| `POST` | `/joiner` | Submit onboarding request |
| `POST` | `/mover` | Submit role change request |
| `POST` | `/leaver` | Submit offboarding request |
| `GET` | `/requests` | List all JML requests |
| `POST` | `/requests/:id/approve` | Approve an approval level |
| `POST` | `/requests/:id/reject` | Reject a request |
| `POST` | `/requests/:id/override` | Emergency override |
| `GET` | `/audit` | Full audit log |
| `GET` | `/analytics` | Dashboard analytics data |
| `GET` | `/orphans` | Orphaned account detection |
| `POST` | `/chat` | Natural language chatbot |

---

## Built With

- **Backend** — Python, Flask, Flask-CORS
- **Frontend** — Vanilla HTML/CSS/JavaScript
- **Charts** — Chart.js
- **Data** — JSON flat files (no database required)
- **Deployment** — Render (backend) + Netlify (frontend)

---

<div align="center">
Built for IT teams · Identity & Access Management · Open Source
</div>
