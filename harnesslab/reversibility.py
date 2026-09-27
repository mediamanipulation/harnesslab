"""§2.3 — Reversibility, blast radius, and stage-before-act."""
from __future__ import annotations

from dataclasses import dataclass

from .vocabulary import Action, AutonomyLevel, Decision, Reversibility

STAGE_BLAST_RADIUS = 5


def evaluate(action: Action) -> Decision:
    """Irreversibility dominates; then blast radius; then cost of undoing."""
    if action.reversibility is Reversibility.IRREVERSIBLE:
        return Decision.REQUIRE_APPROVAL
    if action.blast_radius >= STAGE_BLAST_RADIUS:
        return Decision.STAGE
    if action.reversibility is Reversibility.COSTLY_REVERSIBLE:
        return Decision.MONITOR
    return Decision.ALLOW


CATALOG: dict[str, Action] = {a.name: a for a in [
    Action("search",        AutonomyLevel.OBSERVE, Reversibility.READ_ONLY, 1),
    Action("draft",         AutonomyLevel.DRAFT,   Reversibility.REVERSIBLE, 1),
    Action("temp_resource", AutonomyLevel.EXECUTE_REVERSIBLE, Reversibility.COSTLY_REVERSIBLE, 3),
    Action("bulk_retag",    AutonomyLevel.EXECUTE_REVERSIBLE, Reversibility.REVERSIBLE, 7),
    Action("publish",       AutonomyLevel.EXECUTE_CONSEQUENTIAL, Reversibility.IRREVERSIBLE, 8, external=True),
]}


@dataclass(frozen=True)
class StagedArtifact:
    action_name: str
    payload: dict
    decision: Decision


def stage_before_act(name: str, payload: dict, catalog: dict[str, Action] = CATALOG):
    """Risk labels come from the harness catalog, never from the proposal. Unknown names are denied."""
    action = catalog.get(name)
    if action is None:
        return Decision.DENY
    decision = evaluate(action)
    if decision in {Decision.STAGE, Decision.REQUIRE_APPROVAL}:
        return StagedArtifact(name, payload, decision)
    return decision
