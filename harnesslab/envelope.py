"""§2.2 — The autonomy envelope: authority on several independent axes."""
from __future__ import annotations

from dataclasses import dataclass

from .vocabulary import Action, AutonomyLevel


@dataclass(frozen=True)
class Envelope:
    max_level: AutonomyLevel
    max_blast_radius: int
    allow_external: bool
    max_duration_seconds: int


def envelope_violations(action: Action, env: Envelope, elapsed_seconds: int = 0) -> list[str]:
    """Every axis the action violates. Empty means inside; reviewers need the full list, not the first hit."""
    reasons = []
    if action.level > env.max_level:
        reasons.append("level")
    if action.blast_radius > env.max_blast_radius:
        reasons.append("blast_radius")
    if action.external and not env.allow_external:
        reasons.append("external")
    if elapsed_seconds > env.max_duration_seconds:
        reasons.append("duration")
    return reasons
