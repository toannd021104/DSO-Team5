"""Small, observe-only GuardDuty EventBridge handler for the learning lab."""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, _context):
    """Validate the expected envelope and log a compact incident summary."""
    if event.get("source") != "aws.guardduty":
        raise ValueError("Unexpected event source")

    if event.get("detail-type") != "GuardDuty Finding":
        raise ValueError("Unexpected detail-type")

    detail = event.get("detail") or {}
    finding_id = detail.get("id")
    finding_type = detail.get("type")

    if not finding_id or not finding_type:
        raise ValueError("GuardDuty finding is missing id or type")

    summary = {
        "project": os.environ.get("PROJECT_NAME", "guarduty"),
        "mode": os.environ.get("RESPONSE_MODE", "observe-only"),
        "finding_id": finding_id,
        "finding_type": finding_type,
        "severity": detail.get("severity"),
        "account_id": event.get("account"),
        "region": event.get("region"),
        "resources": detail.get("resources", []),
        "created_at": detail.get("createdAt"),
    }

    # Do not include full finding evidence or perform a Kubernetes/AWS mutation here.
    logger.info("GuardDuty incident received: %s", json.dumps(summary, separators=(",", ":")))

    return {"accepted": True, "finding_id": finding_id, "mode": summary["mode"]}
