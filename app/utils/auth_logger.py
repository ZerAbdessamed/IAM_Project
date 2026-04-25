import json
from datetime import datetime
import os

LOG_FILE = "auth_logs.json"


def write_log(event_type, username, status, extra=None):
    """
    event_type: login / create_user / brute_force / password_fail
    status: success / fail / locked / info
    """

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        "username": username,
        "status": status,
        "extra": extra or {}
    }

    # load existing logs
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                logs = json.load(f)
            except:
                logs = []
    else:
        logs = []

    logs.append(log_entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)