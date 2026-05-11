"""
Simulated IAM API layer — mimics calls to AD, CTMS, LIMS, etc.
No production systems are touched.
"""
import uuid
from datetime import datetime

# Simulated system registry
SYSTEMS = ["AD", "CTMS", "EDC", "LIMS", "ELN", "RIM", "SharePoint", "HR_Portal"]

def provision_account(user_id: str, system: str, permissions: list) -> dict:
    """Simulate provisioning a user account in a target system."""
    return {
        "transaction_id": str(uuid.uuid4()),
        "system": system,
        "user_id": user_id,
        "action": "PROVISION",
        "permissions": permissions,
        "status": "SUCCESS",
        "timestamp": datetime.utcnow().isoformat()
    }

def deprovision_account(user_id: str, system: str) -> dict:
    """Simulate revoking a user account from a target system."""
    return {
        "transaction_id": str(uuid.uuid4()),
        "system": system,
        "user_id": user_id,
        "action": "DEPROVISION",
        "status": "SUCCESS",
        "timestamp": datetime.utcnow().isoformat()
    }

def modify_account(user_id: str, system: str, old_permissions: list, new_permissions: list) -> dict:
    """Simulate modifying permissions in a target system."""
    return {
        "transaction_id": str(uuid.uuid4()),
        "system": system,
        "user_id": user_id,
        "action": "MODIFY",
        "removed_permissions": list(set(old_permissions) - set(new_permissions)),
        "added_permissions": list(set(new_permissions) - set(old_permissions)),
        "status": "SUCCESS",
        "timestamp": datetime.utcnow().isoformat()
    }

def get_account_status(user_id: str, system: str) -> dict:
    """Simulate querying account status in a system."""
    return {
        "system": system,
        "user_id": user_id,
        "exists": True,
        "locked": False,
        "last_login": "2026-03-20T09:15:00",
        "timestamp": datetime.utcnow().isoformat()
    }
