"""§2.5 — Capability budgets: cap cumulative consequence and degrade instead of crashing."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BudgetExceeded(RuntimeError):
    pass


class Mode(Enum):
    EXECUTE = "execute"
    DRAFT_ONLY = "draft_only"
    READ_ONLY = "read_only"
    PAUSED = "paused"


@dataclass
class Budget:
    limit: int
    warning: int | None = None
    spent: int = 0

    @property
    def remaining(self) -> int:
        return self.limit - self.spent

    @property
    def in_warning(self) -> bool:
        return self.warning is not None and self.spent >= self.warning

    def consume(self, cost: int) -> None:
        if cost <= 0:
            raise ValueError(f"cost must be positive, got {cost}")  # no refunds through the back door
        if cost > self.remaining:
            raise BudgetExceeded(f"need={cost}, remaining={self.remaining}")
        self.spent += cost


COST = {"search": 1, "draft": 2, "external_message": 5, "production_write": 10}

ALLOWED_IN = {
    Mode.EXECUTE:    set(COST),
    Mode.DRAFT_ONLY: {"search", "draft"},
    Mode.READ_ONLY:  {"search"},
    Mode.PAUSED:     set(),
}


def run_plan(plan: list[str], budget: Budget, cost: dict = COST, allowed_in: dict = ALLOWED_IN):
    """Execute a plan against a budget. Exhaustion degrades to DRAFT_ONLY; the run keeps doing safe work."""
    mode, trace = Mode.EXECUTE, []
    for op in plan:
        if op not in allowed_in[mode]:
            trace.append((op, "refused", mode.value))
            continue
        try:
            budget.consume(cost[op])
            trace.append((op, "warning" if budget.in_warning else "ok", mode.value))
        except BudgetExceeded as e:
            mode = Mode.DRAFT_ONLY
            trace.append((op, f"exhausted ({e})", mode.value))
    return mode, trace
