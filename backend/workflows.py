"""
JML workflow engine — multi-level approvals, RBAC checks, audit logging, emergency override.

Approval levels per request sensitivity:
  STANDARD  -> L1 (Manager) only
  SENSITIVE -> L1 (Manager) + L2 (IT Security)
  CRITICAL  -> L1 (Manager) + L2 (IT Security) + L3 (Compliance)
"""
import uuid, json, os
from datetime import datetime, timezone
from iam_simulator import provision_account, deprovision_account, modify_account
import risk as risk_engine

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Systems that trigger higher approval tiers
SENSITIVE_SYSTEMS = {"AWS_Dev", "AWS_Prod", "VPN", "PagerDuty", "MDM"}
CRITICAL_SYSTEMS  = {"AWS_Prod", "Okta", "AD", "SIEM", "HR_System"}

# Which RBAC permission is needed per level
LEVEL_PERMISSION = {"L1": "approve_L1", "L2": "approve_L2", "L3": "approve_L3"}


def _load(f):
    with open(os.path.join(DATA_DIR, f)) as fh:
        return json.load(fh)

def _save(f, data):
    with open(os.path.join(DATA_DIR, f), "w") as fh:
        json.dump(data, fh, indent=2)


# ── Audit ─────────────────────────────────────────────────────────────────────

def write_audit(action, actor, details, request_id=None, severity="INFO"):
    log = _load("audit_log.json")
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor,
        "severity": severity,
        "request_id": request_id,
        "details": details
    }
    log.append(entry)
    _save("audit_log.json", log)
    return entry


# ── RBAC helpers ──────────────────────────────────────────────────────────────

def get_rbac_user(username):
    rbac = _load("rbac.json")
    return rbac["users"].get(username)

def has_permission(username, permission):
    user = get_rbac_user(username)
    if not user:
        return False
    perms = user.get("permissions", [])
    return "approve_any" in perms or permission in perms

def authenticate(username, password):
    user = get_rbac_user(username)
    if user and user.get("password") == password:
        rbac = _load("rbac.json")
        role_def = rbac["role_definitions"].get(user["role"], {})
        return {
            "username": username,
            "name": user["name"],
            "role": user["role"],
            "role_label": role_def.get("label", user["role"]),
            "role_color": role_def.get("color", "#5b8dee"),
            "permissions": user["permissions"]
        }
    return None


# ── Approval chain builder ────────────────────────────────────────────────────

def _build_approval_chain(systems):
    """Return ordered approval levels based on which systems are involved."""
    sys_set = set(systems)
    if sys_set & CRITICAL_SYSTEMS:
        return [
            {"level": "L1", "label": "Manager Approval",    "approver_role": "MANAGER",     "status": "PENDING", "approver": None, "timestamp": None},
            {"level": "L2", "label": "IT Security Review",  "approver_role": "IT_SECURITY",  "status": "WAITING", "approver": None, "timestamp": None},
            {"level": "L3", "label": "Compliance Sign-off", "approver_role": "COMPLIANCE",   "status": "WAITING", "approver": None, "timestamp": None},
        ]
    elif sys_set & SENSITIVE_SYSTEMS:
        return [
            {"level": "L1", "label": "Manager Approval",   "approver_role": "MANAGER",    "status": "PENDING", "approver": None, "timestamp": None},
            {"level": "L2", "label": "IT Security Review", "approver_role": "IT_SECURITY", "status": "WAITING", "approver": None, "timestamp": None},
        ]
    else:
        return []


# ── Create request ────────────────────────────────────────────────────────────

def create_request(request_type, payload, requester, actor="system"):
    roles    = _load("roles.json")
    requests = _load("requests.json")

    # Determine systems involved
    if request_type == "JOINER":
        role_cfg = roles.get(payload.get("role", ""), {})
        systems  = role_cfg.get("systems", [])
    elif request_type == "MOVER":
        users    = _load("users.json")
        emp      = next((u for u in users if u["id"] == payload.get("employee_id")), None)
        old_sys  = set(roles.get(emp["role"] if emp else "", {}).get("systems", []))
        new_sys  = set(roles.get(payload.get("new_role", ""), {}).get("systems", []))
        systems  = list(old_sys | new_sys)
    else:  # LEAVER
        users   = _load("users.json")
        emp     = next((u for u in users if u["id"] == payload.get("employee_id")), None)
        systems = emp.get("systems", []) if emp else []

    chain = _build_approval_chain(systems)

    # Risk scoring
    existing_user = None
    if request_type in ("MOVER", "LEAVER"):
        all_users = _load("users.json")
        existing_user = next((u for u in all_users if u["id"] == payload.get("employee_id")), None)
    risk = risk_engine.score_request(request_type, payload, roles, existing_user)

    now = datetime.now(timezone.utc).isoformat()
    req = {
        "id": str(uuid.uuid4()),
        "type": request_type,
        "payload": payload,
        "requester": requester,
        "status": "PENDING_APPROVAL" if chain else "AUTO_APPROVED",
        "approval_chain": chain,
        "approvals_needed": [s["level"] for s in chain],
        "approvals_received": [],
        "iam_results": [],
        "risk": risk,
        "created_at": now,
        "updated_at": now
    }

    if not chain:
        req = _execute_request(req)

    requests.append(req)
    _save("requests.json", requests)

    write_audit(
        action=f"REQUEST_CREATED_{request_type}",
        actor=actor,
        details={"request_id": req["id"], "type": request_type, "payload_summary": _payload_summary(payload)},
        request_id=req["id"],
        severity="INFO"
    )
    return req


# ── Approve ───────────────────────────────────────────────────────────────────

def approve_request(request_id, approver_username, level):
    requests = _load("requests.json")
    req = next((r for r in requests if r["id"] == request_id), None)

    if not req:
        return {"error": "Request not found"}
    if req["status"] != "PENDING_APPROVAL":
        return {"error": "Request is already " + req["status"]}

    # Find the step in the chain
    chain = req.get("approval_chain", [])
    step  = next((s for s in chain if s["level"] == level), None)

    if not step:
        return {"error": f"Level {level} not in approval chain"}
    if step["status"] == "APPROVED":
        return {"error": f"Level {level} already approved"}
    if step["status"] == "WAITING":
        return {"error": f"Level {level} is waiting — complete prior levels first"}

    # RBAC check
    needed_perm = LEVEL_PERMISSION.get(level, "approve_any")
    if not has_permission(approver_username, needed_perm):
        write_audit("APPROVAL_DENIED_RBAC", approver_username,
                    {"request_id": request_id, "level": level, "reason": "Insufficient permissions"},
                    request_id, severity="WARNING")
        return {"error": f"User '{approver_username}' lacks permission '{needed_perm}'"}

    # Record approval
    step["status"]    = "APPROVED"
    step["approver"]  = approver_username
    step["timestamp"] = datetime.now(timezone.utc).isoformat()
    req["approvals_received"].append(level)
    req["updated_at"] = datetime.now(timezone.utc).isoformat()

    write_audit("APPROVAL_GRANTED", approver_username,
                {"request_id": request_id, "level": level},
                request_id, severity="INFO")

    # Unlock next step
    for s in chain:
        if s["status"] == "WAITING":
            s["status"] = "PENDING"
            break

    # All levels done?
    if all(s["status"] == "APPROVED" for s in chain):
        req["status"] = "APPROVED"
        req = _execute_request(req)

    _save("requests.json", [r if r["id"] != request_id else req for r in requests])
    return req


# ── Reject ────────────────────────────────────────────────────────────────────

def reject_request(request_id, approver_username, reason):
    requests = _load("requests.json")
    req = next((r for r in requests if r["id"] == request_id), None)

    if not req:
        return {"error": "Request not found"}
    if req["status"] not in ("PENDING_APPROVAL",):
        return {"error": "Request is already " + req["status"]}

    if not has_permission(approver_username, "reject_any"):
        return {"error": f"User '{approver_username}' lacks permission to reject"}

    req["status"]           = "REJECTED"
    req["rejection_reason"] = reason
    req["rejected_by"]      = approver_username
    req["updated_at"]       = datetime.now(timezone.utc).isoformat()

    write_audit("REQUEST_REJECTED", approver_username,
                {"request_id": request_id, "reason": reason},
                request_id, severity="WARNING")

    _save("requests.json", [r if r["id"] != request_id else req for r in requests])
    return req


# ── Emergency Override ────────────────────────────────────────────────────────

def emergency_override(request_id, actor_username, justification):
    requests = _load("requests.json")
    req = next((r for r in requests if r["id"] == request_id), None)

    if not req:
        return {"error": "Request not found"}
    if req["status"] == "COMPLETED":
        return {"error": "Request already completed"}

    if not has_permission(actor_username, "override"):
        write_audit("OVERRIDE_DENIED", actor_username,
                    {"request_id": request_id, "reason": "Insufficient permissions"},
                    request_id, severity="CRITICAL")
        return {"error": f"User '{actor_username}' lacks override permission"}

    # Mark all chain steps as bypassed
    for step in req.get("approval_chain", []):
        if step["status"] != "APPROVED":
            step["status"]    = "BYPASSED"
            step["approver"]  = actor_username
            step["timestamp"] = datetime.now(timezone.utc).isoformat()

    req["status"]              = "OVERRIDE"
    req["override_by"]         = actor_username
    req["override_reason"]     = justification
    req["override_timestamp"]  = datetime.now(timezone.utc).isoformat()
    req = _execute_request(req)

    write_audit("EMERGENCY_OVERRIDE", actor_username,
                {"request_id": request_id, "justification": justification},
                request_id, severity="CRITICAL")

    _save("requests.json", [r if r["id"] != request_id else req for r in requests])
    return req


# ── Execute IAM ───────────────────────────────────────────────────────────────

def _execute_request(req):
    roles   = _load("roles.json")
    users   = _load("users.json")
    payload = req["payload"]
    results = []

    if req["type"] == "JOINER":
        role_cfg    = roles.get(payload["role"], {})
        systems     = role_cfg.get("systems", [])
        permissions = role_cfg.get("permissions", [])
        for system in systems:
            results.append(provision_account(payload["employee_id"], system, permissions))
        new_user = {
            "id":         payload["employee_id"],
            "name":       payload["name"],
            "email":      payload["email"],
            "department": payload["department"],
            "role":       payload["role"],
            "status":     "active",
            "systems":    systems,
            "manager":    payload.get("manager"),
            "joined":     datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        users.append(new_user)
        _save("users.json", users)

    elif req["type"] == "MOVER":
        user = next((u for u in users if u["id"] == payload["employee_id"]), None)
        if user:
            old_cfg  = roles.get(user["role"], {})
            new_cfg  = roles.get(payload["new_role"], {})
            old_sys  = set(old_cfg.get("systems", []))
            new_sys  = set(new_cfg.get("systems", []))
            old_perm = old_cfg.get("permissions", [])
            new_perm = new_cfg.get("permissions", [])
            for s in old_sys - new_sys:
                results.append(deprovision_account(user["id"], s))
            for s in new_sys - old_sys:
                results.append(provision_account(user["id"], s, new_perm))
            for s in old_sys & new_sys:
                results.append(modify_account(user["id"], s, old_perm, new_perm))
            user["role"]       = payload["new_role"]
            user["department"] = payload.get("new_department", user["department"])
            user["systems"]    = list(new_sys)
            _save("users.json", users)

    elif req["type"] == "LEAVER":
        user = next((u for u in users if u["id"] == payload["employee_id"]), None)
        if user:
            for s in user.get("systems", []):
                results.append(deprovision_account(user["id"], s))
            user["status"]  = "inactive"
            user["systems"] = []
            _save("users.json", users)

    req["iam_results"] = results
    req["status"]      = "COMPLETED"
    req["updated_at"]  = datetime.now(timezone.utc).isoformat()

    write_audit("IAM_EXECUTED", "system",
                {"request_id": req["id"], "actions": len(results), "type": req["type"]},
                req["id"], severity="INFO")
    return req


def get_sla_status(req):
    """Return hours pending and whether SLA is breached (>24h)."""
    try:
        created = datetime.fromisoformat(req["created_at"].replace("Z",""))
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        hours = (now - created).total_seconds() / 3600
        return {"hours_pending": round(hours, 1), "breached": hours > 24}
    except Exception:
        return {"hours_pending": 0, "breached": False}


def get_orphaned_accounts():
    """Find inactive users who still have systems listed, or active users with no systems."""
    users = _load("users.json")
    orphans = []
    for u in users:
        if u["status"] == "inactive" and u.get("systems"):
            orphans.append({**u, "orphan_reason": "Inactive user with active system access"})
        elif u["status"] == "active" and not u.get("systems"):
            orphans.append({**u, "orphan_reason": "Active user with no system access provisioned"})
    return orphans


def _payload_summary(payload):
    return {k: v for k, v in payload.items() if k not in ("password",)}
