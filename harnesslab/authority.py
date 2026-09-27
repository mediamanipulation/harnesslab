"""§2.1 — Separate model proposal from execution authority."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProposedAction:
    name: str
    arguments: dict = field(default_factory=dict)


class Tool:
    """A side-effecting tool. It records what it executed so we can prove what happened."""

    def __init__(self):
        self.executed: list[str] = []

    def execute(self, action: ProposedAction) -> str:
        self.executed.append(action.name)
        return f"EXECUTED {action.name}: {action.arguments}"


class Controller:
    """Default deny: only allowlisted actions run without a human."""

    def __init__(self, auto: set[str] = frozenset({"search_reports", "draft_report"})):
        self.auto = set(auto)

    def authorize(self, action: ProposedAction) -> bool:
        return action.name in self.auto


class DenylistController:
    """Anti-pattern kept for comparison: block known-bad names, allow everything else."""

    def __init__(self, blocked: set[str] = frozenset({"publish_report"})):
        self.blocked = set(blocked)

    def authorize(self, action: ProposedAction) -> bool:
        return action.name not in self.blocked


class Harness:
    """The boundary between a proposal and a side effect. Every proposal is audited."""

    def __init__(self, controller, tool: Tool):
        self.controller, self.tool, self.audit = controller, tool, []

    def run(self, action: ProposedAction) -> str:
        allowed = self.controller.authorize(action)
        self.audit.append((action.name, "executed" if allowed else "paused"))
        if allowed:
            return self.tool.execute(action)
        return f"PAUSED: {action.name} has no execution authority"
