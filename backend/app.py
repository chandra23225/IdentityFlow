from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import workflows
import chatbot
import risk as risk_engine

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load(filename):
    with open(os.path.join(DATA_DIR, filename)) as f:
        return json.load(f)

# ── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "Identity Lifecycle API"})

# ── RBAC ───────────────────────────────────────────────────────────────────────
@app.post("/rbac/login")
def rbac_login():
    body = request.json or {}
    result = workflows.authenticate(body.get("username", ""), body.get("password", ""))
    if result:
        workflows.write_audit("LOGIN", body["username"], {"success": True}, severity="INFO")
        return jsonify(result)
    workflows.write_audit("LOGIN_FAILED", body.get("username", "unknown"), {"success": False}, severity="WARNING")
    return jsonify({"error": "Invalid credentials"}), 401

@app.get("/rbac/users")
def rbac_users():
    rbac = load("rbac.json")
    safe = []
    for uname, u in rbac["users"].items():
        safe.append({
            "username": uname,
            "name": u["name"],
            "role": u["role"],
            "permissions": u["permissions"]
        })
    return jsonify({"users": safe, "role_definitions": rbac["role_definitions"]})

# ── Users ──────────────────────────────────────────────────────────────────────
@app.get("/users")
def get_users():
    return jsonify(load("users.json"))

@app.get("/users/<user_id>")
def get_user(user_id):
    users = load("users.json")
    user = next((u for u in users if u["id"] == user_id), None)
    return jsonify(user) if user else (jsonify({"error": "Not found"}), 404)

@app.get("/roles")
def get_roles():
    return jsonify(load("roles.json"))

# ── Requests ───────────────────────────────────────────────────────────────────
@app.get("/requests")
def get_requests():
    status = request.args.get("status")
    reqs = load("requests.json")
    if status:
        reqs = [r for r in reqs if r["status"] == status]
    return jsonify(reqs)

@app.get("/requests/<request_id>")
def get_request(request_id):
    reqs = load("requests.json")
    req = next((r for r in reqs if r["id"] == request_id), None)
    return jsonify(req) if req else (jsonify({"error": "Not found"}), 404)

# ── JML ────────────────────────────────────────────────────────────────────────
@app.post("/joiner")
def joiner():
    body = request.json or {}
    missing = [f for f in ["employee_id", "name", "email", "department", "role"] if f not in body]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    result = workflows.create_request("JOINER", body, body.get("requester", "HR_System"), body.get("actor", "HR_System"))
    return jsonify(result), 201

@app.post("/mover")
def mover():
    body = request.json or {}
    missing = [f for f in ["employee_id", "new_role"] if f not in body]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    result = workflows.create_request("MOVER", body, body.get("requester", "HR_System"), body.get("actor", "HR_System"))
    return jsonify(result), 201

@app.post("/leaver")
def leaver():
    body = request.json or {}
    if "employee_id" not in body:
        return jsonify({"error": "Missing employee_id"}), 400
    result = workflows.create_request("LEAVER", body, body.get("requester", "HR_System"), body.get("actor", "HR_System"))
    return jsonify(result), 201

# ── Approvals ──────────────────────────────────────────────────────────────────
@app.post("/requests/<request_id>/approve")
def approve(request_id):
    body = request.json or {}
    approver = body.get("approver")
    level    = body.get("level")
    if not approver or not level:
        return jsonify({"error": "Missing approver or level"}), 400
    result = workflows.approve_request(request_id, approver, level)
    return jsonify(result)

@app.post("/requests/<request_id>/reject")
def reject(request_id):
    body = request.json or {}
    approver = body.get("approver", "unknown")
    reason   = body.get("reason", "No reason provided")
    result = workflows.reject_request(request_id, approver, reason)
    return jsonify(result)

# ── Emergency Override ─────────────────────────────────────────────────────────
@app.post("/requests/<request_id>/override")
def override(request_id):
    body          = request.json or {}
    actor         = body.get("actor")
    justification = body.get("justification")
    if not actor or not justification:
        return jsonify({"error": "Missing actor or justification"}), 400
    result = workflows.emergency_override(request_id, actor, justification)
    return jsonify(result)

# ── Audit Log ──────────────────────────────────────────────────────────────────
@app.get("/audit")
def audit_log():
    logs = load("audit_log.json")
    severity  = request.args.get("severity")
    action    = request.args.get("action")
    req_id    = request.args.get("request_id")
    if severity:
        logs = [l for l in logs if l.get("severity") == severity]
    if action:
        logs = [l for l in logs if action.upper() in l.get("action", "").upper()]
    if req_id:
        logs = [l for l in logs if l.get("request_id") == req_id]
    return jsonify(sorted(logs, key=lambda x: x["timestamp"], reverse=True))

# ── Chatbot ────────────────────────────────────────────────────────────────────
@app.post("/chat")
def chat():
    body = request.json or {}
    msg  = body.get("message", "").strip()
    user = body.get("actor", "system")
    if not msg:
        return jsonify({"error": "Empty message"}), 400
    result = chatbot.process_message(msg, session_user=user)
    return jsonify(result)

# ── Risk score ─────────────────────────────────────────────────────────────────
@app.post("/risk/score")
def risk_score():
    body = request.json or {}
    roles_cfg = load("roles.json")
    users     = load("users.json")
    emp_id    = body.get("employee_id")
    existing  = next((u for u in users if u["id"] == emp_id), None) if emp_id else None
    result    = risk_engine.score_request(body.get("type","JOINER"), body, roles_cfg, existing)
    return jsonify(result)

# ── Analytics ──────────────────────────────────────────────────────────────────
@app.get("/analytics")
def analytics():
    reqs  = load("requests.json")
    users = load("users.json")

    # Requests by day (last 14 days)
    from collections import defaultdict
    by_day = defaultdict(lambda: {"JOINER":0,"MOVER":0,"LEAVER":0})
    for r in reqs:
        day = r["created_at"][:10]
        by_day[day][r["type"]] = by_day[day].get(r["type"], 0) + 1

    # Status breakdown
    status_counts = defaultdict(int)
    for r in reqs:
        status_counts[r["status"]] += 1

    # Risk breakdown
    risk_counts = {"LOW":0,"MEDIUM":0,"HIGH":0,"CRITICAL":0}
    for r in reqs:
        lvl = r.get("risk", {}).get("level", "LOW")
        risk_counts[lvl] = risk_counts.get(lvl, 0) + 1

    # SLA breaches
    pending = [r for r in reqs if r["status"] == "PENDING_APPROVAL"]
    sla_data = []
    for r in pending:
        sla = workflows.get_sla_status(r)
        p   = r["payload"]
        sla_data.append({
            "id": r["id"],
            "type": r["type"],
            "title": p.get("name") or p.get("employee_id","?"),
            "hours_pending": sla["hours_pending"],
            "breached": sla["breached"]
        })

    return jsonify({
        "by_day": dict(by_day),
        "status_counts": dict(status_counts),
        "risk_counts": risk_counts,
        "sla": sla_data,
        "total_requests": len(reqs),
        "active_employees": len([u for u in users if u["status"] == "active"])
    })

# ── Orphaned accounts ──────────────────────────────────────────────────────────
@app.get("/orphans")
def orphans():
    return jsonify(workflows.get_orphaned_accounts())

# ── SLA check ──────────────────────────────────────────────────────────────────
@app.get("/sla")
def sla():
    reqs = load("requests.json")
    pending = [r for r in reqs if r["status"] == "PENDING_APPROVAL"]
    result = []
    for r in pending:
        sla_info = workflows.get_sla_status(r)
        result.append({**r, "sla": sla_info})
    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
