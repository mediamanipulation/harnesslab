"""§2.7 — Checkpoint, sleep, resume, drift, and authority decay."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .approval import payload_digest


class RunState(Enum):
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    SLEEPING = "sleeping"
    CHECKPOINT = "checkpoint"
    EXPIRED = "expired"
    ESCALATED = "escalated"
    TERMINATED = "terminated"


S = RunState
TRANSITIONS: dict[RunState, set[RunState]] = {
    S.STARTING:   {S.RUNNING, S.TERMINATED},
    S.RUNNING:    {S.PAUSED, S.CHECKPOINT, S.ESCALATED, S.TERMINATED},
    S.PAUSED:     {S.RUNNING, S.TERMINATED},
    S.CHECKPOINT: {S.SLEEPING, S.RUNNING, S.TERMINATED},
    S.SLEEPING:   {S.RUNNING, S.EXPIRED, S.ESCALATED, S.PAUSED, S.TERMINATED},
    S.EXPIRED:    {S.STARTING, S.TERMINATED},  # must be re-authorized from the start
    S.ESCALATED:  {S.RUNNING, S.TERMINATED},
    S.TERMINATED: set(),
}


def transition(current: RunState, new: RunState) -> RunState:
    if new not in TRANSITIONS[current]:
        raise ValueError(f"illegal transition {current.value} -> {new.value}")
    return new


@dataclass(frozen=True)
class Checkpoint:
    objective: str
    actions_taken: tuple[str, ...]
    budget_remaining: int
    pending_risks: tuple[str, ...]
    assumptions: tuple[str, ...]
    context_version: str

    def seal(self) -> str:
        return payload_digest(self.__dict__)


@dataclass(frozen=True)
class Lease:
    expires_at: datetime

    def active(self, now: datetime) -> bool:
        return now < self.expires_at


def resume(cp: Checkpoint, seal: str, lease: Lease, current_context: str,
           now: datetime) -> tuple[RunState, str]:
    """Resuming is a decision, not a default. Returns the state the run moves to, and why."""
    if cp.seal() != seal:
        return S.TERMINATED, "checkpoint tampered; restart from last trusted state"
    if not lease.active(now):
        return S.EXPIRED, "authority expired; reauthorize"
    if cp.context_version != current_context:
        return S.ESCALATED, "context changed; drift review"
    if cp.budget_remaining <= 0:
        return S.PAUSED, "budget exhausted; degrade"
    return S.RUNNING, "resume permitted"
