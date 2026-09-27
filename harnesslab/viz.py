"""Rich notebook rendering for HarnessLab.

Every function returns an ``HTML`` object: Jupyter renders it; plain Python prints a text summary.
Styles are inline and colors are translucent, so output reads in light and dark JupyterLab themes.
"""
from __future__ import annotations

import html as _html
import inspect
from enum import Enum

from .vocabulary import Decision, Reversibility

FONT = "font-family: var(--jp-ui-font-family, system-ui, sans-serif); font-size: 13px; line-height: 1.45;"
MUTED = "opacity: .65;"

COLORS = {
    "allow": "#16a34a", "monitor": "#0891b2", "stage": "#d97706", "require_approval": "#7c3aed",
    "deny": "#dc2626", "refused": "#6b7280", "blocked": "#16a34a", "breached": "#dc2626",
    "ok": "#16a34a", "warning": "#d97706", "exhausted": "#dc2626",
    "running": "#16a34a", "paused": "#d97706", "expired": "#dc2626", "escalated": "#7c3aed",
    "terminated": "#dc2626", "starting": "#0891b2", "checkpoint": "#0891b2", "sleeping": "#6b7280",
    "search": "#0891b2", "draft": "#16a34a", "external_message": "#d97706", "production_write": "#dc2626",
}


class HTML:
    def __init__(self, markup: str, text: str = ""):
        self.markup, self.text = markup, text

    def _repr_html_(self) -> str:
        return self.markup

    def __repr__(self) -> str:
        return self.text or "<rendered HTML>"

    def __add__(self, other: "HTML") -> "HTML":
        return HTML(self.markup + other.markup, "\n".join(t for t in (self.text, other.text) if t))


def esc(x) -> str:
    return _html.escape(str(x))


def _key(x) -> str:
    return (x.value if isinstance(x, Enum) else str(x)).split(" ")[0].lower()


def pill(x, label: str | None = None) -> str:
    color = COLORS.get(_key(x), "#6b7280")
    text = label or (x.value if isinstance(x, Enum) else str(x))
    return (f'<span style="display:inline-block;padding:1px 9px;border-radius:999px;font-weight:600;'
            f'font-size:12px;background:{color}26;border:1px solid {color};color:{color};white-space:nowrap">'
            f'{esc(text)}</span>')


def _table(headers: list[str], rows: list[list[str]], title: str = "") -> str:
    head = "".join(f'<th style="text-align:left;padding:6px 10px;border-bottom:2px solid #8884">{esc(h)}</th>'
                   for h in headers)
    body = "".join("<tr>" + "".join(f'<td style="padding:5px 10px;border-bottom:1px solid #8883;'
                                    f'vertical-align:top">{c}</td>' for c in r) + "</tr>" for r in rows)
    cap = f'<div style="font-weight:700;margin:4px 0 6px">{esc(title)}</div>' if title else ""
    return (f'<div style="{FONT}overflow-x:auto;margin:6px 0">{cap}'
            f'<table style="border-collapse:collapse">{head and "<tr>" + head + "</tr>"}{body}</table></div>')


def card(title: str, body: str, accent: str = "#7c3aed") -> HTML:
    return HTML(f'<div style="{FONT}border:1px solid #8885;border-left:4px solid {accent};border-radius:8px;'
                f'padding:10px 14px;margin:8px 0"><div style="font-weight:700;margin-bottom:6px">{esc(title)}</div>'
                f'{body}</div>', title)


# ------------------------------------------------------------------ source

def show_source(*objs) -> HTML:
    """Render the real implementation from harnesslab/, so notebooks never duplicate it."""
    blocks, text = [], []
    for obj in objs:
        src = inspect.getsource(obj)
        where = f"{inspect.getmodule(obj).__name__.replace('.', '/')}.py · {getattr(obj, '__name__', '')}"
        try:
            from pygments import highlight
            from pygments.formatters import HtmlFormatter
            from pygments.lexers import PythonLexer
            code = highlight(src, PythonLexer(), HtmlFormatter(noclasses=True, style="github-dark", nowrap=True))
        except Exception:
            code = esc(src)
        blocks.append(
            f'<div style="margin:8px 0;border-radius:8px;overflow:hidden;border:1px solid #30363d">'
            f'<div style="background:#161b22;color:#8b949e;padding:4px 12px;font:12px ui-monospace,monospace">'
            f'{esc(where)}</div><pre style="margin:0;padding:10px 12px;background:#0d1117;color:#e6edf3;'
            f'overflow-x:auto;font:12.5px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace">{code}</pre></div>')
        text.append(src)
    return HTML("".join(blocks), "\n".join(text))


# --------------------------------------------------------------- journey

LABS = ["Control", "Envelope", "Reversibility", "Approval", "Budgets", "SLOs", "Long horizon", "Contract"]


def journey(current: int) -> HTML:
    """The lab map: where this notebook sits in the chapter."""
    steps = []
    for i, name in enumerate(LABS, 1):
        done, here = i < current, i == current
        color = "#7c3aed" if here else ("#16a34a" if done else "#8888")
        steps.append(f'<div style="flex:1;min-width:84px;text-align:center">'
                     f'<div style="margin:0 auto 4px;width:26px;height:26px;border-radius:50%;line-height:26px;'
                     f'font-weight:700;color:#fff;background:{color}">{"✓" if done else i}</div>'
                     f'<div style="font-size:11px;{"font-weight:700" if here else MUTED}">{esc(name)}</div></div>')
    return HTML(f'<div style="{FONT}display:flex;flex-wrap:wrap;gap:4px;padding:10px;border:1px solid #8884;'
                f'border-radius:10px;margin:6px 0">{"".join(steps)}</div>',
                f"HarnessLab {current}/8 — {LABS[current - 1]}")


# ------------------------------------------------------------- decisions

def decisions(rows: list[tuple], title: str = "") -> HTML:
    """rows of (label, decision, reason?)."""
    body = [[f"<code>{esc(r[0])}</code>", pill(r[1]), esc(r[2]) if len(r) > 2 else ""] for r in rows]
    text = "\n".join(f"{r[0]:28} {_key(r[1])}" for r in rows)
    return HTML(_table(["action", "decision", "why"], body, title), text)


def envelope_view(actions, env, violations_fn, elapsed_seconds: int = 0) -> HTML:
    axes = ["level", "blast_radius", "external", "duration"]
    rows, text = [], []
    for a in actions:
        v = violations_fn(a, env, elapsed_seconds)
        cells = [pill("deny", "✗") if ax in v else pill("allow", "✓") for ax in axes]
        rows.append([f"<code>{esc(a.name)}</code>"] + cells + [pill("allow", "inside") if not v else pill("deny", "outside")])
        text.append(f"{a.name:26} {'inside' if not v else 'OUTSIDE: ' + ', '.join(v)}")
    return HTML(_table(["action", *axes, "verdict"], rows), "\n".join(text))


def risk_matrix(evaluate, highlight: tuple | None = None, max_blast: int = 10) -> HTML:
    """Reversibility × blast radius, colored by the policy's decision."""
    from .vocabulary import Action, AutonomyLevel
    rows = []
    for rev in Reversibility:
        cells = []
        for blast in range(1, max_blast + 1):
            d = evaluate(Action("probe", AutonomyLevel.DRAFT, rev, blast))
            c = COLORS[d.value]
            ring = "outline:3px solid currentColor;outline-offset:-3px;" if highlight == (rev, blast) else ""
            cells.append(f'<td title="{d.value}" style="width:34px;height:26px;background:{c}55;{ring}'
                         f'text-align:center;font-size:10px">{d.value[0].upper()}</td>')
        rows.append(f'<tr><td style="padding-right:10px;white-space:nowrap">{esc(rev.value)}</td>{"".join(cells)}</tr>')
    axis = "".join(f'<td style="text-align:center;font-size:11px;{MUTED}">{b}</td>' for b in range(1, max_blast + 1))
    legend = " ".join(pill(d) for d in Decision if d is not Decision.DENY)
    return HTML(f'<div style="{FONT}margin:6px 0"><table style="border-collapse:separate;border-spacing:2px">'
                f'{"".join(rows)}<tr><td style="{MUTED}text-align:right;padding-right:10px">blast →</td>{axis}</tr>'
                f'</table><div style="margin-top:6px">{legend}</div></div>', "risk matrix")


def packet_card(packet) -> HTML:
    a = packet.action
    rows = [["action", f"<code>{esc(a.name)}</code> {pill(a.reversibility.value.replace('_', ' '))} blast {a.blast_radius}"],
            ["payload", f"<code>{esc(packet.payload)}</code>"],
            ["reason", esc(packet.reason)],
            ["evidence", "<br>".join(f"✓ {esc(e)}" for e in packet.evidence)],
            ["expected effect", esc(packet.expected_effect)],
            ["rollback", esc(packet.rollback_plan) if packet.rollback_plan
             else pill("deny", "NONE — this cannot be undone")]]
    body = "".join(f'<div style="display:flex;gap:12px;margin:3px 0"><div style="width:120px;{MUTED}">{k}</div>'
                   f'<div>{v}</div></div>' for k, v in rows)
    return card("Decision packet — awaiting human review", body)


def checks(rows: list[tuple[str, bool, str]], title: str = "", good: str = "valid", bad: str = "refused") -> HTML:
    body = [[esc(label), pill("allow" if ok else "deny", good if ok else bad), esc(detail)] for label, ok, detail in rows]
    return HTML(_table(["case", "result", "detail"], body, title),
                "\n".join(f"{l:30} {'OK' if ok else 'NO'} {d}" for l, ok, d in rows))


# ---------------------------------------------------------------- budget

def budget_bar(trace, cost: dict, limit: int, warning: int | None = None) -> HTML:
    segs, chips = [], []
    for op, status, mode in trace:
        s = _key(status)
        if s in ("ok", "warning"):
            w = 100 * cost[op] / limit
            segs.append(f'<div title="{esc(op)} ({cost[op]})" style="width:{w}%;background:{COLORS.get(op, "#888")};'
                        f'border-right:2px solid #fff8;color:#fff;font-size:10px;line-height:22px;overflow:hidden;'
                        f'white-space:nowrap;text-overflow:ellipsis;padding-left:4px">{esc(op)}</div>')
        chips.append(f'{pill(s, op)}<span style="{MUTED}font-size:11px"> {esc(mode)}</span>')
    spent = sum(cost[op] for op, st, _ in trace if _key(st) in ("ok", "warning"))
    marker = (f'<div style="position:absolute;left:{100 * warning / limit}%;top:-4px;bottom:-4px;'
              f'border-left:2px dashed #d97706" title="warning"></div>') if warning else ""
    bar = (f'<div style="position:relative;height:22px;border-radius:6px;background:#8882;display:flex;'
           f'overflow:visible;margin:8px 0">{"".join(segs)}{marker}</div>')
    head = (f'<div style="display:flex;justify-content:space-between"><b>spent {spent} / {limit}</b>'
            f'<span style="{MUTED}">dashed = warning at {warning}</span></div>') if warning else f"<b>spent {spent} / {limit}</b>"
    return HTML(f'<div style="{FONT}margin:6px 0">{head}{bar}<div style="display:flex;flex-wrap:wrap;gap:6px">'
                f'{" → ".join(chips)}</div></div>', f"spent {spent}/{limit}")


# ----------------------------------------------------------- SLO & events

def timeline(events) -> HTML:
    chips = []
    for e in events:
        border = "border-bottom:3px solid #d97706;" if e.mode == "draft_only" else ""
        chips.append(f'<span title="{esc(e.action)}: {esc(e.reason)}" style="{border}padding-bottom:2px">'
                     f'{pill(e.decision, e.action.replace("_", " "))}</span>')
    return HTML(f'<div style="{FONT}display:flex;flex-wrap:wrap;gap:5px;margin:6px 0">{"".join(chips)}</div>'
                f'<div style="{FONT}{MUTED}font-size:11px">hover for reasons · amber underline = degraded mode</div>',
                f"{len(events)} events")


def slo_cards(report: dict) -> HTML:
    tiles = []
    for name, (value, target, ok) in report.items():
        c = COLORS["ok" if ok else "deny"]
        shown = f"{value:.0%}" if isinstance(value, float) else value
        tiles.append(f'<div style="flex:1;min-width:150px;border:1px solid {c};background:{c}14;border-radius:10px;'
                     f'padding:10px 12px"><div style="font-size:11px;{MUTED}">{esc(name.replace("_", " "))}</div>'
                     f'<div style="font-size:24px;font-weight:700">{esc(shown)}</div>'
                     f'<div style="font-size:11px">target {esc(target)} · {pill("ok" if ok else "deny", "PASS" if ok else "FAIL")}'
                     f'</div></div>')
    return HTML(f'<div style="{FONT}display:flex;flex-wrap:wrap;gap:8px;margin:6px 0">{"".join(tiles)}</div>',
                "\n".join(f"{k:30} {v[0]!s:6} {'PASS' if v[2] else 'FAIL'}" for k, v in report.items()))


# ------------------------------------------------------------- lifecycle

def state_path(states) -> HTML:
    arrow = f'<span style="{MUTED}"> → </span>'
    return HTML(f'<div style="{FONT}margin:6px 0">{arrow.join(pill(s) for s in states)}</div>',
                " -> ".join(s.value for s in states))


# -------------------------------------------------------------- contract

def diff_view(changes) -> HTML:
    rows = [[f"<code>{esc(s.label())}</code>", f"{pill(d1)} → {pill(d2)}"] for s, d1, d2 in changes]
    return HTML(_table(["scenario", "v1 → v2"], rows, f"{len(changes)} decision(s) changed"),
                "\n".join(f"{s.label()}: {d1.value} -> {d2.value}" for s, d1, d2 in changes))


# --------------------------------------------------------------- gauntlet

def gauntlet_board(*result_sets, title: str = "Red-Team Gauntlet") -> HTML:
    """Side-by-side scoreboard: one column per defense set."""
    names = [rs[0].defenses for rs in result_sets]
    by_attack = {}
    for rs in result_sets:
        for r in rs:
            by_attack.setdefault(r.attack, []).append(r)
    scores = []
    for n, rs in zip(names, result_sets):
        s = sum(r.blocked for r in rs) / len(rs)
        c = COLORS["ok"] if s == 1 else COLORS["warning"] if s >= .5 else COLORS["deny"]
        scores.append(f'<div style="flex:1;min-width:180px"><div style="display:flex;justify-content:space-between">'
                      f'<b>{esc(n)}</b><b style="color:{c}">{sum(r.blocked for r in rs)}/{len(rs)} blocked</b></div>'
                      f'<div style="height:10px;border-radius:5px;background:#8883;margin-top:4px">'
                      f'<div style="width:{100 * s}%;height:100%;border-radius:5px;background:{c}"></div></div></div>')
    rows = []
    for a, rs in by_attack.items():
        cells = [f'{pill("blocked" if r.blocked else "breached", "BLOCKED" if r.blocked else "BREACHED")}'
                 f'<div style="font-size:11px;{MUTED}">{esc(r.detail)}</div>' for r in rs]
        rows.append([f'<span style="{MUTED}">§{esc(a.section)}</span>',
                     f'<b>{esc(a.name)}</b><div style="font-size:11px;{MUTED}">{esc(a.story)}</div>', *cells])
    text = "\n".join(f"{a.name:26} " + "  ".join("BLOCKED " if r.blocked else "BREACHED" for r in rs)
                     for a, rs in by_attack.items())
    return HTML(f'<div style="{FONT}border:1px solid #8885;border-radius:12px;padding:12px 14px;margin:8px 0">'
                f'<div style="font-size:16px;font-weight:800;margin-bottom:8px">⚔ {esc(title)}</div>'
                f'<div style="display:flex;flex-wrap:wrap;gap:16px;margin-bottom:6px">{"".join(scores)}</div>'
                f'{_table(["", "attack", *names], rows)}</div>', text)
