"""§§2.8–2.11 — The autonomy contract: validate it, enforce all of it, change it narrowly."""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path

from .vocabulary import AutonomyLevel, Decision, Reversibility

DEFAULT_CONTRACT = Path(__file__).resolve().parent.parent / "contracts" / "research_agent.json"
REQUIRED_STOP_CONDITIONS = {"budget_exhausted", "policy_violation", "context_drift", "approval_expired"}


def load_contract(path: str | Path | None = None) -> dict:
    return json.loads(Path(path or DEFAULT_CONTRACT).read_text(encoding="utf-8"))


def validate_contract(c: dict) -> list[str]:
    """Structural invariants every contract must satisfy. Empty list means valid."""
    problems = []
    try:
        AutonomyLevel.parse(c["autonomy"]["max_level"])
    except KeyError:
        problems.append("autonomy.max_level is not a known level")
    for name, spec in c["actions"].items():
        try:
            AutonomyLevel.parse(spec["level"])
            Reversibility(spec["reversibility"])
        except (KeyError, ValueError):
            problems.append(f"{name}: unknown level or reversibility")
            continue
        if spec.get("budget_cost", 0) <= 0:
            problems.append(f"{name}: budget_cost must be positive")
        if spec["reversibility"] == "irreversible" and not spec.get("prohibited") \
                and spec.get("approval") != "required":
            problems.append(f"{name}: irreversible actions must require approval or be prohibited")
        if spec.get("approval") == "not_required" and not spec.get("limits"):
            problems.append(f"{name}: a grant without approval must be bounded by limits")
    budget = c["budget"]
    if not budget["warning"] < budget["hard_limit"] <= budget["total"]:
        problems.append("budget: require warning < hard_limit <= total")
    missing = REQUIRED_STOP_CONDITIONS - set(c.get("stop_conditions", []))
    if missing:
        problems.append(f"stop_conditions missing: {sorted(missing)}")
    if not c.get("checkpoints", {}).get("before_irreversible_action"):
        problems.append("checkpoints.before_irreversible_action must be true")
    return problems


def decide(name: str, c: dict, *, args: dict | None = None, spent: int = 0) -> tuple[Decision, str]:
    """One function enforces the whole contract. Order: hard denials, approval gates, envelope."""
    args = args or {}
    spec = c["actions"].get(name)
    if spec is None:
        return Decision.DENY, "unknown action (default deny)"
    if spec.get("prohibited"):
        return Decision.DENY, "prohibited by contract"
    if spec.get("external") and not c["autonomy"]["external_actions"]:
        return Decision.DENY, "external actions disabled"
    if spent + spec["budget_cost"] > c["budget"]["hard_limit"]:
        return Decision.DENY, "budget hard limit"
    if spec["reversibility"] == "irreversible":
        return Decision.REQUIRE_APPROVAL, "irreversible"
    for key, cap in spec.get("limits", {}).items():
        if args.get(key, 0) > cap:
            return Decision.REQUIRE_APPROVAL, f"{key}={args[key]} exceeds limit {cap}"
    if spec.get("approval") == "required":
        return Decision.REQUIRE_APPROVAL, "approval required by contract"
    level, ceiling = AutonomyLevel.parse(spec["level"]), AutonomyLevel.parse(c["autonomy"]["max_level"])
    if level > ceiling and spec.get("approval") != "not_required":
        return Decision.DENY, "above envelope ceiling"
    reason = "inside envelope" if level <= ceiling else "bounded per-action grant"
    if spent + spec["budget_cost"] > c["budget"]["warning"]:
        return Decision.MONITOR, f"{reason}; above budget warning"
    return Decision.ALLOW, reason


def bounded_notification_grant(v1: dict, max_recipients: int = 10) -> dict:
    """One narrow hill-climbing step: small internal notifications no longer need approval."""
    v2 = copy.deepcopy(v1)
    v2["actions"]["internal_notification"].update(approval="not_required",
                                                  limits={"recipients": max_recipients})
    return v2


@dataclass(frozen=True)
class Scenario:
    action: str
    args: dict = field(default_factory=dict)
    spent: int = 0

    def label(self) -> str:
        extra = ", ".join(f"{k}={v}" for k, v in self.args.items())
        return f"{self.action}({extra})" + (f" @spent={self.spent}" if self.spent else "")


def diff_decisions(v1: dict, v2: dict, scenarios: list[Scenario]) -> list[tuple[Scenario, Decision, Decision]]:
    """The scenarios whose decision changed between two contract versions."""
    changed = []
    for s in scenarios:
        d1, _ = decide(s.action, v1, args=s.args, spent=s.spent)
        d2, _ = decide(s.action, v2, args=s.args, spent=s.spent)
        if d1 is not d2:
            changed.append((s, d1, d2))
    return changed
