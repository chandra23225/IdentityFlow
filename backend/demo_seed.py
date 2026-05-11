"""
Run before your demo to populate realistic TechCorp IT data.
  python demo_seed.py
"""
import json, os, sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(__file__))
import workflows

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def _load(f):
    with open(os.path.join(DATA_DIR, f)) as fh: return json.load(fh)
def _save(f, d):
    with open(os.path.join(DATA_DIR, f), "w") as fh: json.dump(d, fh, indent=2)

def seed():
    print("Seeding TechCorp demo data...")

    _save("requests.json", [])
    _save("audit_log.json", [])
    _save("users.json", [
        {"id":"EMP001","name":"Alice Chen","email":"alice.chen@techcorp.io","department":"Engineering","role":"Senior Software Engineer","status":"active","systems":["GitHub","Jira","Confluence","Slack","AWS_Dev","AWS_Prod"],"manager":"EMP005","joined":"2022-03-14"},
        {"id":"EMP002","name":"Ben Okafor","email":"ben.okafor@techcorp.io","department":"Platform","role":"DevOps Engineer","status":"active","systems":["GitHub","Jira","Confluence","Slack","AWS_Dev","AWS_Prod","PagerDuty","Datadog"],"manager":"EMP005","joined":"2021-07-01"},
        {"id":"EMP003","name":"Clara Reyes","email":"clara.reyes@techcorp.io","department":"Security","role":"Security Analyst","status":"active","systems":["Okta","Jira","Confluence","Slack","Datadog","VPN","SIEM"],"manager":"EMP005","joined":"2023-01-09"},
        {"id":"EMP004","name":"Dan Patel","email":"dan.patel@techcorp.io","department":"IT","role":"IT Administrator","status":"active","systems":["Okta","Jira","Confluence","Slack","VPN","HR_System","MDM","AD"],"manager":"EMP005","joined":"2020-11-15"},
        {"id":"EMP005","name":"Eva Thornton","email":"eva.thornton@techcorp.io","department":"Engineering","role":"Engineering Manager","status":"active","systems":["GitHub","Jira","Confluence","Slack","AWS_Dev","AWS_Prod","PagerDuty","Datadog","Okta","HR_System"],"manager":None,"joined":"2019-06-01"},
        {"id":"EMP006","name":"Frank Liu","email":"frank.liu@techcorp.io","department":"Data","role":"Data Engineer","status":"active","systems":["GitHub","Jira","Confluence","Slack","AWS_Dev","Datadog"],"manager":"EMP005","joined":"2023-08-21"},
        {"id":"EMP007","name":"Grace Kim","email":"grace.kim@techcorp.io","department":"Engineering","role":"Software Engineer","status":"inactive","systems":[],"manager":"EMP005","joined":"2021-04-12"},
    ])

    # Completed joiner — new SRE hire 3 days ago
    j1 = workflows.create_request("JOINER", {
        "employee_id":"EMP008","name":"Hiro Tanaka","email":"hiro.tanaka@techcorp.io",
        "department":"Platform","role":"Site Reliability Engineer","manager":"EMP005","requester":"HR_System"
    }, "HR_System", "hr001")
    _backdate(j1["id"], days=3)

    # Completed mover — engineer promoted to senior 1 day ago
    m1 = workflows.create_request("MOVER", {
        "employee_id":"EMP006","new_role":"Senior Software Engineer","new_department":"Engineering","requester":"HR_System"
    }, "HR_System", "mgr001")
    _backdate(m1["id"], days=1)

    # Pending — DevOps hire, SLA breached (27h ago)
    j2 = workflows.create_request("JOINER", {
        "employee_id":"EMP009","name":"Isla Fernandez","email":"isla.fernandez@techcorp.io",
        "department":"Platform","role":"DevOps Engineer","manager":"EMP005","requester":"HR_System"
    }, "HR_System", "hr001")
    _backdate(j2["id"], hours=27)

    # Pending — IT Admin hire, 3h ago (within SLA)
    j3 = workflows.create_request("JOINER", {
        "employee_id":"EMP010","name":"Jake Morrison","email":"jake.morrison@techcorp.io",
        "department":"IT","role":"IT Administrator","manager":"EMP005","requester":"HR_System"
    }, "HR_System", "hr001")
    _backdate(j3["id"], hours=3)

    # Rejected — Security Analyst with SoD conflict flagged
    j4 = workflows.create_request("JOINER", {
        "employee_id":"EMP099","name":"Kim Rejected","email":"kim@techcorp.io",
        "department":"Security","role":"Security Analyst","manager":"EMP005","requester":"HR_System"
    }, "HR_System", "hr001")
    workflows.reject_request(j4["id"], "mgr001", "SoD conflict — Okta + SIEM dual access violates security policy")
    _backdate(j4["id"], days=2)

    # Leaver — offboarding Grace Kim
    l1 = workflows.create_request("LEAVER", {
        "employee_id":"EMP007","requester":"HR_System"
    }, "HR_System", "hr001")
    _backdate(l1["id"], days=1)

    reqs = _load("requests.json")
    audit = _load("audit_log.json")
    print(f"Done. {len(reqs)} requests · {len(_load('users.json'))} users · {len(audit)} audit entries.")

def _backdate(req_id, days=0, hours=0):
    reqs = _load("requests.json")
    delta = timedelta(days=days, hours=hours)
    for r in reqs:
        if r["id"] == req_id:
            orig = datetime.fromisoformat(r["created_at"].replace("Z","").split("+")[0])
            r["created_at"] = (orig - delta).isoformat()
    _save("requests.json", reqs)

if __name__ == "__main__":
    seed()
