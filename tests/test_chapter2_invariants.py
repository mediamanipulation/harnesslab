"""Cross-notebook control invariants for Chapter 2 HarnessLab.

Three layers:
1. Every notebook executes top to bottom in a real kernel, so its assertions hold.
2. Notebooks stay thin: implementation lives in harnesslab/, never duplicated in a code cell.
3. The controls in harnesslab/ satisfy the chapter's invariants, including the full red-team gauntlet.

Run from the project root:  pytest
"""
import ast
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harnesslab import EXECUTES, AutonomyLevel, Decision  # noqa: E402
from harnesslab.approval import Approval, action_digest, check_approval  # noqa: E402
from harnesslab.arena import ATTACKS, NAIVE, SECURE, run_gauntlet  # noqa: E402
from harnesslab.budget import Budget, BudgetExceeded  # noqa: E402
from harnesslab.contract import (  # noqa: E402
    Scenario, bounded_notification_grant, decide, diff_decisions, load_contract, validate_contract,
)
from harnesslab.lifecycle import Checkpoint, Lease, RunState, resume, transition  # noqa: E402

NOTEBOOKS = sorted((ROOT / "notebooks").glob("*.ipynb"))
NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _cells(path, kind):
    return ["".join(c["source"]) for c in json.loads(path.read_text(encoding="utf-8"))["cells"]
            if c["cell_type"] == kind]


@pytest.fixture
def contract():
    return load_contract()


# ------------------------------------------------------------- notebooks

def test_eight_notebooks_present():
    assert [p.name[:2] for p in NOTEBOOKS] == [f"{i:02d}" for i in range(1, 9)]


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_executes(path):
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    nb = nbformat.read(path, as_version=4)
    nbclient.NotebookClient(nb, timeout=120, kernel_name="python3",
                            resources={"metadata": {"path": str(path.parent)}}).execute()


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebook_has_teaching_structure(path):
    text = "\n".join(_cells(path, "markdown"))
    for heading in ("## Concept", "## Why this matters", "## Diagram", "```mermaid", "## Expected behavior",
                    "Red-team round" if not path.name.startswith("08") else "final gauntlet",
                    "## Playground", "hallenge"):
        assert heading in text, f"{path.name} missing {heading!r}"


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.stem)
def test_notebooks_do_not_duplicate_implementation(path):
    for src in _cells(path, "code"):
        for node in ast.walk(ast.parse(src)):
            assert not isinstance(node, (ast.FunctionDef, ast.ClassDef)), \
                f"{path.name} defines {node.name!r}; move it into harnesslab/ and show_source() it"


# -------------------------------------------------------------- gauntlet

@pytest.mark.parametrize("attack", ATTACKS, ids=lambda a: a.name)
def test_harnesslab_blocks_every_attack(attack):
    blocked, detail = attack.run(SECURE)
    assert blocked, detail


def test_every_section_has_an_attack():
    assert {a.section for a in ATTACKS} == {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8"}


def test_shortcuts_are_mostly_breached():
    """If the anti-patterns start passing, the attacks have stopped testing anything."""
    results = run_gauntlet(NAIVE)
    assert sum(r.blocked for r in results) <= 2


# -------------------------------------------------------------- contract

def test_shipped_contract_is_valid(contract):
    assert validate_contract(contract) == []


def test_unknown_actions_are_denied(contract):
    for name in ["wire_transfer", "Publish_Report", "publish_report_v2", ""]:
        assert decide(name, contract)[0] is Decision.DENY


def test_prohibited_always_denied(contract):
    for spent in (0, 10, 29):
        for args in ({}, {"recipients": 1}):
            assert decide("delete_records", contract, args=args, spent=spent)[0] is Decision.DENY


def test_irreversible_never_executes_autonomously(contract):
    for c in (contract, bounded_notification_grant(contract)):
        for name, spec in c["actions"].items():
            if spec["reversibility"] == "irreversible":
                for spent in range(0, 31, 5):
                    assert decide(name, c, spent=spent)[0] not in EXECUTES


def test_nothing_above_ceiling_executes_without_bounded_grant(contract):
    ceiling = AutonomyLevel.parse(contract["autonomy"]["max_level"])
    for name, spec in contract["actions"].items():
        if AutonomyLevel.parse(spec["level"]) > ceiling and spec.get("approval") != "not_required":
            assert decide(name, contract)[0] not in EXECUTES


def test_hard_limit_never_exceeded(contract):
    hard = contract["budget"]["hard_limit"]
    for name, spec in contract["actions"].items():
        for spent in range(hard + 1):
            if decide(name, contract, spent=spent)[0] in EXECUTES:
                assert spent + spec["budget_cost"] <= hard


def test_external_flag_enforced(contract):
    c = copy.deepcopy(contract)
    c["actions"]["email_customer"] = {"level": "draft", "reversibility": "reversible",
                                      "budget_cost": 1, "external": True}
    assert decide("email_customer", c)[0] is Decision.DENY
    c["autonomy"]["external_actions"] = True
    assert decide("email_customer", c)[0] is Decision.ALLOW


@pytest.mark.parametrize("mutation, expected_fragment", [
    (lambda c: c["actions"]["publish_report"].pop("approval"), "irreversible"),
    (lambda c: c["stop_conditions"].remove("approval_expired"), "stop_conditions"),
    (lambda c: c["budget"].update(warning=31), "budget"),
    (lambda c: c["checkpoints"].update(before_irreversible_action=False), "checkpoints"),
    (lambda c: c["actions"]["search"].update(budget_cost=0), "budget_cost"),
    (lambda c: c["actions"]["internal_notification"].update(approval="not_required"), "bounded"),
    (lambda c: c["autonomy"].update(max_level="godmode"), "max_level"),
])
def test_validator_rejects_weakened_contracts(contract, mutation, expected_fragment):
    c = copy.deepcopy(contract)
    mutation(c)
    assert any(expected_fragment in p for p in validate_contract(c))


def test_hill_climb_is_narrow_and_bounded(contract):
    v2 = bounded_notification_grant(contract)
    assert validate_contract(v2) == []
    assert contract["actions"]["internal_notification"]["approval"] == "required"  # v1 untouched
    scenarios = [Scenario(n, spent=s) for n in contract["actions"] for s in (0, 20, 28)]
    scenarios += [Scenario("internal_notification", {"recipients": r}) for r in (1, 10, 11, 500)]
    changes = diff_decisions(contract, v2, scenarios)
    assert changes
    assert {s.action for s, _, _ in changes} == {"internal_notification"}
    assert all(s.args.get("recipients", 0) <= 10 for s, _, _ in changes)
    assert decide("internal_notification", v2, args={"recipients": 11})[0] is Decision.REQUIRE_APPROVAL


# ------------------------------------------------- approval, budget, lifecycle

def test_approval_binds_payload_action_policy_and_time():
    payload = {"report_id": "R-104"}
    ap = Approval(action_digest("publish_report", payload), "reviewer-1", "2.1", NOW + timedelta(minutes=15))
    assert check_approval(ap, "publish_report", payload, "2.1", NOW) == (True, "valid")
    assert check_approval(ap, "publish_report", {"report_id": "R-999"}, "2.1", NOW)[1] == "payload_mismatch"
    assert check_approval(ap, "delete_records", payload, "2.1", NOW)[1] == "payload_mismatch"
    assert check_approval(ap, "publish_report", payload, "2.2", NOW)[1] == "policy_version_changed"
    assert check_approval(ap, "publish_report", payload, "2.1", NOW + timedelta(minutes=15))[1] == "expired"


def test_budget_never_overspends_or_refunds():
    b = Budget(limit=12, warning=8)
    for cost in [1, 5, 3, 10, 2, 7, 1, 1]:
        try:
            b.consume(cost)
        except BudgetExceeded:
            pass
        assert 0 <= b.spent <= b.limit
    for bad in (0, -5):
        with pytest.raises(ValueError):
            b.consume(bad)


def test_resume_revalidates_everything():
    cp = Checkpoint("brief", ("search",), 12, (), ("sources unchanged",), "ctx-v1")
    seal, lease = cp.seal(), Lease(NOW + timedelta(hours=1))
    assert resume(cp, seal, lease, "ctx-v1", NOW)[0] is RunState.RUNNING
    forged = Checkpoint("brief", ("search",), 999, (), ("sources unchanged",), "ctx-v1")
    assert resume(forged, seal, lease, "ctx-v1", NOW)[0] is RunState.TERMINATED
    assert resume(cp, seal, lease, "ctx-v1", NOW + timedelta(hours=2))[0] is RunState.EXPIRED
    assert resume(cp, seal, lease, "ctx-v2", NOW)[0] is RunState.ESCALATED
    empty = Checkpoint("brief", ("search",), 0, (), (), "ctx-v1")
    assert resume(empty, empty.seal(), lease, "ctx-v1", NOW)[0] is RunState.PAUSED


def test_expired_runs_must_restart():
    with pytest.raises(ValueError):
        transition(RunState.EXPIRED, RunState.RUNNING)
    assert transition(RunState.EXPIRED, RunState.STARTING) is RunState.STARTING
