"""
Risk scoring engine — IT / Technology industry.
Scores JML requests based on system sensitivity, role privilege,
production access, and Segregation of Duties conflicts.
"""

# Production & infrastructure systems — highest sensitivity
CRITICAL_SYSTEMS  = {"AWS_Prod", "AD", "Okta", "SIEM"}

# Elevated but not critical
SENSITIVE_SYSTEMS = {"AWS_Dev", "VPN", "PagerDuty", "MDM", "HR_System"}

# Roles with elevated privilege
PRIVILEGED_ROLES  = {"Engineering Manager", "IT Administrator", "Site Reliability Engineer", "Security Analyst"}

# Segregation of Duties — these combos should not be held by one person
SOD_CONFLICTS = [
    ({"Okta"},     {"SIEM"}),        # Identity management + security monitoring
    ({"AWS_Prod"}, {"Okta"}),        # Prod infra + identity provider
    ({"AD"},       {"HR_System"}),   # Directory + HR records
    ({"AWS_Prod"}, {"SIEM"}),        # Prod access + audit log access
    ({"MDM"},      {"AD"}),          # Device management + directory
]

SYSTEM_DESCRIPTIONS = {
    "GitHub":     "Source code repository",
    "Jira":       "Project & issue tracking",
    "Confluence": "Internal documentation",
    "Slack":      "Team communication",
    "AWS_Dev":    "AWS development environment",
    "AWS_Prod":   "AWS production environment ⚠",
    "PagerDuty":  "Incident alerting & on-call",
    "Datadog":    "Observability & monitoring",
    "Okta":       "Identity provider & SSO ⚠",
    "VPN":        "Corporate VPN access",
    "SIEM":       "Security event monitoring ⚠",
    "HR_System":  "HR records & payroll",
    "MDM":        "Mobile device management",
    "AD":         "Active Directory ⚠"
}


def score_request(request_type, payload, roles_cfg, existing_user=None):
    """
    Returns:
      { score: int, level: str, factors: [str], sod_violation: bool, system_descriptions: dict }
    """
    score   = 0
    factors = []

    role     = payload.get("role") or payload.get("new_role", "")
    role_cfg = roles_cfg.get(role, {})
    systems  = set(role_cfg.get("systems", []))

    existing_sys = set(existing_user.get("systems", [])) if existing_user else set()
    combined_sys = systems | existing_sys

    # ── Scoring rules ─────────────────────────────────────────────────────────

    if request_type == "LEAVER":
        score += 10
        factors.append("Leaver — immediate access revocation required")
        if existing_user:
            sys_count = len(existing_user.get("systems", []))
            if sys_count >= 5:
                score += 20
                factors.append(f"Large access footprint ({sys_count} systems to revoke)")

    if systems & CRITICAL_SYSTEMS:
        score += 40
        hit = systems & CRITICAL_SYSTEMS
        factors.append(f"Critical system access requested: {', '.join(sorted(hit))}")

    if systems & SENSITIVE_SYSTEMS:
        score += 20
        hit = systems & SENSITIVE_SYSTEMS
        factors.append(f"Sensitive system access: {', '.join(sorted(hit))}")

    if role in PRIVILEGED_ROLES:
        score += 25
        factors.append(f"Privileged role: {role}")

    if "AWS_Prod" in systems:
        score += 15
        factors.append("Production environment access (AWS_Prod)")

    if len(systems) >= 7:
        score += 15
        factors.append(f"Broad access scope ({len(systems)} systems)")

    # SoD check
    sod_violation = False
    for set_a, set_b in SOD_CONFLICTS:
        if combined_sys & set_a and combined_sys & set_b:
            sod_violation = True
            score += 30
            conflict_sys = sorted((set_a | set_b) & combined_sys)
            factors.append(f"⚠ SoD conflict: {' + '.join(conflict_sys)} — dual control violation")

    # ── Level ─────────────────────────────────────────────────────────────────
    if score >= 70:
        level = "CRITICAL"
    elif score >= 40:
        level = "HIGH"
    elif score >= 20:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "score": min(score, 100),
        "level": level,
        "factors": factors,
        "sod_violation": sod_violation,
        "system_descriptions": {s: SYSTEM_DESCRIPTIONS.get(s, s) for s in systems}
    }
