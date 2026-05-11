"""
Natural language chatbot for JML self-service.
Parses plain English into structured JML actions — no LLM required,
uses intent matching + entity extraction with regex and keyword rules.
"""
import re, json, os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def _load(f):
    with open(os.path.join(DATA_DIR, f)) as fh:
        return json.load(fh)

# ── Intent patterns ───────────────────────────────────────────────────────────
INTENTS = [
    ("JOINER",  [r"\bonboard\b", r"\bhire\b", r"\bnew (employee|hire|joiner|staff|user)\b", r"\badd (employee|user)\b", r"\bjoin\b"]),
    ("LEAVER",  [r"\boffboard\b", r"\bterminate\b", r"\bleave\b", r"\bremove (employee|user|access)\b", r"\bdeactivate\b", r"\bresign\b", r"\bleaver\b"]),
    ("MOVER",   [r"\bmove\b", r"\btransfer\b", r"\bpromote\b", r"\brole change\b", r"\bchange role\b", r"\bnew role\b", r"\bswitch role\b"]),
    ("STATUS",  [r"\bstatus\b", r"\bcheck\b", r"\bshow (me )?(pending|requests)\b", r"\blist (pending|requests)\b", r"\bpending\b"]),
    ("HELP",    [r"\bhelp\b", r"\bwhat can you\b", r"\bcommands\b", r"\bhow (do|to)\b"]),
    ("USERS",   [r"\blist (users|employees|staff)\b", r"\bshow (users|employees|staff)\b", r"\bwho (is|are)\b", r"\bdirectory\b"]),
    ("AUDIT",   [r"\baudit\b", r"\blog\b", r"\bhistory\b", r"\bactivity\b"]),
]

ROLES = None
def _get_roles():
    global ROLES
    if ROLES is None:
        ROLES = list(_load("roles.json").keys())
    return ROLES

def _extract_intent(text):
    t = text.lower()
    for intent, patterns in INTENTS:
        for p in patterns:
            if re.search(p, t):
                return intent
    return "UNKNOWN"

def _extract_name(text):
    # "named X", "called X", "for X", or capitalised words after keywords
    m = re.search(r'(?:named?|called|for|onboard|hire)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
    if m: return m.group(1)
    # fallback: two consecutive Title Case words
    m = re.search(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', text)
    return m.group(1) if m else None

def _extract_employee_id(text):
    m = re.search(r'\b(EMP\d{3,})\b', text, re.IGNORECASE)
    return m.group(1).upper() if m else None

def _extract_role(text):
    roles = _get_roles()
    t = text.lower()
    for role in roles:
        if role.lower() in t:
            return role
    # partial match
    for role in roles:
        words = role.lower().split()
        if any(w in t for w in words if len(w) > 4):
            return role
    return None

def _extract_email(text):
    m = re.search(r'[\w.+-]+@[\w-]+\.[a-z]{2,}', text, re.IGNORECASE)
    return m.group(0) if m else None

def _extract_department(text):
    depts = ["engineering", "platform", "security", "it", "data", "product", "devops", "infrastructure", "sre", "operations"]
    t = text.lower()
    for d in depts:
        if d in t:
            return d.title()
    return None

def _extract_manager(text):
    m = re.search(r'(?:manager|reporting to|reports to)\s+(EMP\d+)', text, re.IGNORECASE)
    return m.group(1).upper() if m else None


# ── Response builder ──────────────────────────────────────────────────────────

def process_message(text, session_user="system"):
    intent = _extract_intent(text)

    if intent == "HELP":
        return {
            "intent": "HELP",
            "reply": (
                "Here's what I can do:\n\n"
                "**Onboard** — _\"Onboard Dana Scientist as a Clinical Analyst\"_\n"
                "**Role change** — _\"Move EMP001 to Regulatory Affairs Specialist\"_\n"
                "**Offboard** — _\"Offboard EMP002\"_ or _\"Terminate Bob Researcher\"_\n"
                "**Status** — _\"Show pending requests\"_\n"
                "**Directory** — _\"List all employees\"_\n"
                "**Audit** — _\"Show audit log\"_\n\n"
                "I'll extract the details and submit the request for you."
            ),
            "action": None
        }

    if intent == "STATUS":
        try:
            reqs = _load("requests.json")
            pending = [r for r in reqs if r["status"] == "PENDING_APPROVAL"]
            completed = [r for r in reqs if r["status"] == "COMPLETED"]
            return {
                "intent": "STATUS",
                "reply": f"There are **{len(pending)} pending** approval requests and **{len(completed)} completed** requests in the system.",
                "action": "SHOW_APPROVALS"
            }
        except:
            return {"intent": "STATUS", "reply": "Could not fetch request status.", "action": None}

    if intent == "USERS":
        try:
            users = _load("users.json")
            active = [u for u in users if u["status"] == "active"]
            names = ", ".join(u["name"] for u in active[:5])
            more = f" and {len(active)-5} more" if len(active) > 5 else ""
            return {
                "intent": "USERS",
                "reply": f"There are **{len(active)} active employees**: {names}{more}.",
                "action": "SHOW_DIRECTORY"
            }
        except:
            return {"intent": "USERS", "reply": "Could not fetch employee list.", "action": None}

    if intent == "AUDIT":
        return {
            "intent": "AUDIT",
            "reply": "Opening the audit log for you.",
            "action": "SHOW_AUDIT"
        }

    if intent == "JOINER":
        name   = _extract_name(text)
        role   = _extract_role(text)
        email  = _extract_email(text)
        dept   = _extract_department(text)
        mgr    = _extract_manager(text)

        missing = []
        if not name:  missing.append("full name")
        if not role:  missing.append("role (e.g. Clinical Analyst)")
        if not email: missing.append("email address")

        if missing:
            roles_list = ", ".join(_get_roles())
            return {
                "intent": "JOINER",
                "reply": f"I need a bit more info to onboard someone. Missing: **{', '.join(missing)}**.\n\nAvailable roles: {roles_list}",
                "action": None,
                "partial": {"name": name, "role": role, "email": email}
            }

        # Generate employee ID
        try:
            users = _load("users.json")
            max_id = max((int(u["id"].replace("EMP","")) for u in users if u["id"].startswith("EMP")), default=0)
            emp_id = f"EMP{str(max_id+1).zfill(3)}"
        except:
            emp_id = "EMP999"

        payload = {
            "employee_id": emp_id,
            "name": name,
            "email": email,
            "department": dept or "General",
            "role": role,
            "manager": mgr,
            "requester": "Chatbot",
            "actor": session_user
        }
        return {
            "intent": "JOINER",
            "reply": f"Ready to onboard **{name}** as **{role}** ({emp_id}). Shall I submit this request?",
            "action": "SUBMIT_JOINER",
            "payload": payload
        }

    if intent == "LEAVER":
        emp_id = _extract_employee_id(text)
        name   = _extract_name(text)

        if not emp_id and name:
            try:
                users = _load("users.json")
                match = next((u for u in users if name.lower() in u["name"].lower()), None)
                if match: emp_id = match["id"]
            except: pass

        if not emp_id:
            return {
                "intent": "LEAVER",
                "reply": "Who should I offboard? Please provide an employee ID (e.g. EMP002) or full name.",
                "action": None
            }

        try:
            users = _load("users.json")
            emp = next((u for u in users if u["id"] == emp_id), None)
            emp_name = emp["name"] if emp else emp_id
        except:
            emp_name = emp_id

        payload = {"employee_id": emp_id, "requester": "Chatbot", "actor": session_user}
        return {
            "intent": "LEAVER",
            "reply": f"Ready to offboard **{emp_name}** ({emp_id}) and revoke all system access. Confirm?",
            "action": "SUBMIT_LEAVER",
            "payload": payload
        }

    if intent == "MOVER":
        emp_id = _extract_employee_id(text)
        name   = _extract_name(text)
        role   = _extract_role(text)

        if not emp_id and name:
            try:
                users = _load("users.json")
                match = next((u for u in users if name.lower() in u["name"].lower()), None)
                if match: emp_id = match["id"]
            except: pass

        missing = []
        if not emp_id: missing.append("employee ID or name")
        if not role:   missing.append("new role")

        if missing:
            return {
                "intent": "MOVER",
                "reply": f"To process a role change I need: **{', '.join(missing)}**.",
                "action": None
            }

        payload = {"employee_id": emp_id, "new_role": role, "requester": "Chatbot", "actor": session_user}
        return {
            "intent": "MOVER",
            "reply": f"Ready to move **{emp_id}** to **{role}**. Confirm?",
            "action": "SUBMIT_MOVER",
            "payload": payload
        }

    return {
        "intent": "UNKNOWN",
        "reply": "I didn't quite understand that. Type **help** to see what I can do.",
        "action": None
    }
