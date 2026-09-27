"""Interactive playgrounds (ipywidgets). Each one drives the real harnesslab controls live."""
from __future__ import annotations

import json
from datetime import timedelta

from . import viz
from .vocabulary import Action, AutonomyLevel, Decision, Reversibility


def _widgets():
    try:
        import ipywidgets as w
        from IPython.display import display
        return w, display
    except ImportError:
        return None, None


def _unavailable():
    return viz.HTML("<i>Install <code>ipywidgets</code> (see requirements.txt) to use this playground.</i>",
                    "ipywidgets not installed")


def _live(controls: dict, render):
    """Lay out controls and re-render ``render(**values)`` whenever any control changes."""
    w, display = _widgets()
    if w is None:
        return _unavailable()
    out = w.interactive_output(lambda **kw: display(render(**kw)), controls)
    box = w.HBox(list(controls.values()), layout=w.Layout(flex_flow="row wrap", gap="8px"))
    return w.VBox([box, out])


def _style(w, width="260px"):
    return dict(style={"description_width": "initial"}, layout=w.Layout(width=width))


# ------------------------------------------------------------------ 01

def authority_playground():
    w, _ = _widgets()
    if w is None:
        return _unavailable()
    from .authority import Controller, DenylistController, ProposedAction

    def render(name):
        p = ProposedAction(name)
        rows = [("allowlist (default deny)", Decision.ALLOW if Controller().authorize(p) else Decision.DENY),
                ("denylist", Decision.ALLOW if DenylistController().authorize(p) else Decision.DENY)]
        return viz.decisions(rows, f"Who would execute '{name}'?")
    return _live({"name": w.Text(value="Publish_Report", description="proposed action", **_style(w, "340px"))}, render)


# ------------------------------------------------------------------ 02

def envelope_playground(env):
    w, _ = _widgets()
    if w is None:
        return _unavailable()
    from .envelope import envelope_violations

    def render(level, blast, external, minutes):
        a = Action("your_action", level, Reversibility.REVERSIBLE, blast, external)
        return viz.envelope_view([a], env, envelope_violations, minutes * 60)
    return _live({
        "level": w.Dropdown(options=[(l.name.lower(), l) for l in AutonomyLevel], value=AutonomyLevel.DRAFT,
                            description="level", **_style(w)),
        "blast": w.IntSlider(value=1, min=1, max=20, description="blast radius", **_style(w)),
        "external": w.Checkbox(value=False, description="external"),
        "minutes": w.IntSlider(value=10, min=0, max=120, step=5, description="minutes into run", **_style(w)),
    }, render)


# ------------------------------------------------------------------ 03

def reversibility_playground():
    w, _ = _widgets()
    if w is None:
        return _unavailable()
    from .reversibility import evaluate

    def render(rev, blast):
        d = evaluate(Action("probe", AutonomyLevel.DRAFT, rev, blast))
        return viz.HTML(f"<div style='margin:6px 0'>decision: {viz.pill(d)}</div>") + \
            viz.risk_matrix(evaluate, highlight=(rev, blast))
    return _live({
        "rev": w.Dropdown(options=[(r.value, r) for r in Reversibility], value=Reversibility.REVERSIBLE,
                          description="reversibility", **_style(w)),
        "blast": w.IntSlider(value=3, min=1, max=10, description="blast radius", **_style(w)),
    }, render)


# ------------------------------------------------------------------ 04

def approval_playground(approval, now, default_payload: dict):
    w, _ = _widgets()
    if w is None:
        return _unavailable()
    from .approval import check_approval

    def render(action, payload_text, minutes, policy):
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as e:
            return viz.HTML(f"<div>{viz.pill('deny', 'invalid JSON')} {viz.esc(e)}</div>")
        ok, why = check_approval(approval, action, payload, policy, now + timedelta(minutes=minutes))
        return viz.checks([(f"{action} @ +{minutes} min, policy {policy}", ok, why)], good="EXECUTE", bad="REFUSE")
    return _live({
        "action": w.Dropdown(options=["publish_report", "delete_report"], description="action", **_style(w, "240px")),
        "payload_text": w.Textarea(value=json.dumps(default_payload), description="payload",
                                   **_style(w, "360px")),
        "minutes": w.IntSlider(value=0, min=0, max=30, description="minutes later", **_style(w)),
        "policy": w.Dropdown(options=["2.1", "2.2"], description="policy", **_style(w, "160px")),
    }, render)


# ------------------------------------------------------------------ 05

def budget_playground(limit: int = 12, warning: int = 8):
    w, display = _widgets()
    if w is None:
        return _unavailable()
    from .budget import COST, Budget, run_plan

    plan: list[str] = []
    out = w.Output()

    def refresh():
        budget = Budget(limit, warning)
        mode, trace = run_plan(plan, budget)
        out.clear_output(wait=True)
        with out:
            display(viz.budget_bar(trace, COST, limit, warning) +
                    viz.HTML(f"<div>mode: {viz.pill('allow' if mode.value == 'execute' else 'stage', mode.value)}</div>"))

    def add(op):
        def click(_):
            plan.append(op)
            refresh()
        return click

    buttons = []
    for op, cost in COST.items():
        b = w.Button(description=f"{op} ({cost})", layout=w.Layout(width="auto"))
        b.on_click(add(op))
        buttons.append(b)
    reset = w.Button(description="reset", button_style="warning")
    reset.on_click(lambda _: (plan.clear(), refresh()))
    refresh()
    return w.VBox([w.HBox(buttons + [reset], layout=w.Layout(flex_flow="row wrap", gap="6px")), out])


# ------------------------------------------------------------------ 06

def slo_playground(contract):
    w, _ = _widgets()
    if w is None:
        return _unavailable()
    from .contract import decide
    from .slo import DEMO_PROPOSALS, metrics, naive_decide, paranoid_decide, run_controlled, slo_report

    controllers = {"HarnessLab decide": decide, "naive (allow all)": naive_decide,
                   "paranoid (escalate all)": paranoid_decide}

    def render(name):
        events, spent = run_controlled(DEMO_PROPOSALS, contract, controllers[name])
        return viz.timeline(events) + viz.slo_cards(slo_report(metrics(events, spent, contract)))
    return _live({"name": w.ToggleButtons(options=list(controllers), description="controller",
                                          style={"description_width": "initial"})}, render)


# ------------------------------------------------------------------ 07

def lifecycle_playground(cp, lease, now):
    w, _ = _widgets()
    if w is None:
        return _unavailable()
    from dataclasses import replace
    from .lifecycle import RunState, resume

    seal = cp.seal()

    def render(hours, context, forge, budget):
        candidate = replace(cp, budget_remaining=budget)
        if not forge:
            candidate_seal = candidate.seal()  # an honest save re-seals
        else:
            candidate_seal = seal              # an edit after sealing keeps the old seal
        state, why = resume(candidate, candidate_seal, lease, context, now + timedelta(hours=hours))
        return viz.state_path([RunState.CHECKPOINT, RunState.SLEEPING, state]) + \
            viz.HTML(f"<div style='opacity:.7'>{viz.esc(why)}</div>")
    return _live({
        "hours": w.FloatSlider(value=0.5, min=0, max=3, step=0.25, description="hours asleep", **_style(w)),
        "context": w.Dropdown(options=["ctx-v1", "ctx-v2"], description="world on wake", **_style(w, "200px")),
        "forge": w.Checkbox(value=False, description="edit checkpoint after sealing"),
        "budget": w.IntSlider(value=cp.budget_remaining, min=0, max=30, description="budget in checkpoint", **_style(w)),
    }, render)


# ------------------------------------------------------------------ 08

def contract_playground(v1, v2):
    w, _ = _widgets()
    if w is None:
        return _unavailable()
    from .contract import decide

    def render(version, action, spent, recipients):
        c = v1 if version == "v1" else v2
        d, why = decide(action, c, args={"recipients": recipients}, spent=spent)
        return viz.decisions([(f"{action} · {version}", d, why)])
    return _live({
        "version": w.ToggleButtons(options=["v1", "v2"], description="contract", style={"description_width": "initial"}),
        "action": w.Dropdown(options=list(v1["actions"]) + ["wire_transfer"], value="internal_notification",
                             description="action", **_style(w)),
        "spent": w.IntSlider(value=0, min=0, max=30, description="budget spent", **_style(w)),
        "recipients": w.IntSlider(value=3, min=0, max=50, description="recipients", **_style(w)),
    }, render)
