"""HarnessLab: executable controls for Chapter 2 — one module per section.

    vocabulary     shared levels, reversibility, actions, decisions
    authority      §2.1   proposal vs execution authority
    envelope       §2.2   the autonomy envelope
    reversibility  §2.3   reversibility, blast radius, stage-before-act
    approval       §2.4   payload-bound, expiring approvals
    budget         §2.5   capability budgets and degradation
    slo            §2.6   SLOs computed from event logs
    lifecycle      §2.7   checkpoint, sleep, resume, drift
    contract       §§2.8–2.11  the autonomy contract and controlled hill climbing
    arena          §2.12  the red-team gauntlet
    viz, playground       notebook rendering and interactive widgets

Teaching code: minimal, dependency-free at its core, and not a production framework.
"""
from .vocabulary import EXECUTES, Action, AutonomyLevel, Decision, Reversibility

__all__ = ["Action", "AutonomyLevel", "Decision", "EXECUTES", "Reversibility"]
