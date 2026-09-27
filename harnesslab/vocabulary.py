"""Shared vocabulary for every Chapter 2 control."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class AutonomyLevel(IntEnum):
    OBSERVE = 1
    RECOMMEND = 2
    DRAFT = 3
    STAGE = 4
    EXECUTE_REVERSIBLE = 5
    EXECUTE_CONSEQUENTIAL = 6

    @classmethod
    def parse(cls, name: str) -> "AutonomyLevel":
        return cls[name.upper()]


class Reversibility(Enum):
    READ_ONLY = "read_only"
    REVERSIBLE = "reversible"
    COSTLY_REVERSIBLE = "costly_reversible"
    IRREVERSIBLE = "irreversible"


@dataclass(frozen=True)
class Action:
    name: str
    level: AutonomyLevel
    reversibility: Reversibility
    blast_radius: int = 1
    external: bool = False
    budget_cost: int = 1


class Decision(Enum):
    ALLOW = "allow"
    MONITOR = "monitor"
    STAGE = "stage"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


EXECUTES = {Decision.ALLOW, Decision.MONITOR}
