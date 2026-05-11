# TechCorp — Self-Service Identity Lifecycle Portal

> Hackathon project · IT Industry · Built with Flask + Vanilla JS

Automates the **Joiner-Mover-Leaver (JML)** identity lifecycle for IT/tech companies.
Manual onboarding and offboarding causes delays, orphaned accounts, and security gaps.
This portal replaces that with automated provisioning, multi-level approvals, risk scoring, and a natural language assistant.

---

## Features

| Feature | Description |
|---|---|
| **JML Workflows** | Onboard, transfer, and offboard engineers with one form |
| **Multi-Level Approvals** | L1 Manager → L2 IT Security → L3 IT Compliance based on system sensitivity |
| **Risk Scoring** | Every request scored LOW→CRITICAL with SoD conflict detection |
| **Emergency Override** | IAM Admin can bypass approval chain with full audit trail |
| **RBAC** | 5 portal roles with scoped permissions |
| **Audit Log** | Every action logged with actor, timestamp, severity |
| **NL Chatbot** | Plain English requests — "Onboard Sam as a DevOps Engineer" |
| **SLA Timers** | Flags approvals pending over 24h |
| **Orphan Detection** | Surfaces inactive users with lingering access |
| **Identity Documents** | Click any request type chip to view a verified ID card |
| **Analytics Dashboard** | Activity chart + risk breakdown + system coverage |

---

## Systems Simulated

`GitHub` `Jira` `Confluence` `Slack` `AWS_Dev` `AWS_Prod` `PagerDuty` `Datadog` `Okta` `VPN` `SIEM` `MDM` `AD` `HR_System`

No production systems are connected — all IAM calls are simulated.

---

## Roles

`Software Engineer` · `Senior Software Engineer` · `DevOps Engineer` · `Site Reliability Engineer` · `Security Analyst` · `Engineering Manager` · `IT Administrator` · `Data Engineer` · `Product Manager` · `Intern`

---

## Quick Start

```bash
# 1. Install dependencies
cd identity-lifecycle/backend
pip install -r requirements.txt

# 2. Seed demo data
python demo_seed.py

# 3. Start the API
python app.py

# 4. In a new terminal, serve the frontend
cd identity-lifecycle/frontend
python -m http.server 8080

# 5. Open in browser
http://localhost:8080
```

---

## Demo Accounts

| Username | Password | Role | Can |
|---|---|---|---|
| admin001 | admin123 | IAM Administrator | Everything + override |
| mgr001 | manager123 | Engineering Manager | L1 approvals |
| sec001 | security123 | IT Security | L2 approvals |
| comp001 | itadmin123 | IT Compliance | L3 approvals |
| hr001 | hr123 | HR Specialist | Create requests |

---

## Project Structure

```
identity-lifecycle/
├── backend/
│   ├── app.py            # Flask REST API
│   ├── workflows.py      # JML engine + approval chain
│   ├── iam_simulator.py  # Simulated IAM API calls
│   ├── risk.py           # Risk scoring engine
│   ├── chatbot.py        # NL intent parser
│   ├── demo_seed.py      # Demo data seeder
│   ├── requirements.txt
│   └── data/
│       ├── users.json
│       ├── roles.json
│       ├── requests.json
│       ├── rbac.json
│       └── audit_log.json
└── frontend/
    ├── index.html
    ├── style.css
    ├── app.js
    └── config.js
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | /rbac/login | Authenticate |
| GET | /users | List employees |
| GET | /roles | List roles |
| POST | /joiner | Onboard employee |
| POST | /mover | Role change |
| POST | /leaver | Offboard employee |
| GET | /requests | List JML requests |
| POST | /requests/:id/approve | Approve a level |
| POST | /requests/:id/reject | Reject request |
| POST | /requests/:id/override | Emergency override |
| GET | /audit | Audit log |
| GET | /analytics | Dashboard analytics |
| GET | /orphans | Orphaned accounts |
| POST | /chat | Chatbot |
