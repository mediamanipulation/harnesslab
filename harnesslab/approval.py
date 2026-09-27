"""§2.4 — Human approval as a runtime contract over a frozen payload."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta

from .vocabulary import Action


def payload_digest(obj) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def action_digest(action_name: str, payload: dict) -> str:
    """Bind to the action *and* payload so an approval cannot be replayed on a different action."""
    return payload_digest({"action": action_name, "payload": payload})


@dataclass(frozen=True)
class DecisionPacket:
    """What the reviewer sees before deciding."""
    action: Action
    payload: dict
    reason: str
    evidence: tuple[str, ...]
    expected_effect: str
    rollback_plan: str | None


@dataclass(frozen=True)
class Approval:
    digest: str
    approved_by: str
    policy_version: str
    expires_at: datetime


def approve(packet: DecisionPacket, reviewer: str, policy_version: str,
            now: datetime, ttl_minutes: int = 15) -> Approval:
    return Approval(action_digest(packet.action.name, packet.payload), reviewer, policy_version,
                    now + timedelta(minutes=ttl_minutes))


def check_approval(approval: Approval, action_name: str, payload: dict,
                   policy_version: str, now: datetime) -> tuple[bool, str]:
    """Re-derive everything at execution time. Any difference refuses."""
    if now >= approval.expires_at:
        return False, "expired"
    if approval.policy_version != policy_version:
        return False, "policy_version_changed"
    if approval.digest != action_digest(action_name, payload):
        return False, "payload_mismatch"
    return True, "valid"
