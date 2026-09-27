# Chapter 2 HarnessLab — Refined Teaching Edition

A vendor-neutral Jupyter companion for **Chapter 2: Autonomy — Graduated Control and Human Oversight**.

## Learning arc

| Notebook | Chapter alignment | Teaching outcome |
|---|---|---|
| 01 | §2.1 | Separate model proposal from execution authority |
| 02 | §2.2 | Build a graduated autonomy envelope |
| 03 | §2.3 | Encode reversibility, blast radius, and stage-before-act |
| 04 | §2.4 | Bind human approval to immutable action payloads |
| 05 | §2.5 | Budget cumulative operational consequence |
| 06 | §2.6 | Measure autonomy-control reliability with SLOs |
| 07 | §2.7 | Govern checkpoint, sleep, resume, drift, and authority decay |
| 08 | §§2.8–2.14 | Compose an autonomy contract and practice controlled hill climbing |

## Refinements in this edition

Each notebook now includes:
- chapter-aligned teaching prose;
- a "why this matters" section;
- Mermaid architecture/flow diagrams, rendered natively by JupyterLab;
- the real implementation, displayed from `harnesslab/` with syntax highlighting (never copy-pasted);
- runnable expected-behavior or expected-denial assertions, with rendered decision tables, risk
  matrices, budget bars, event timelines, and SLO cards;
- a **red-team round**: the section's attacks run against HarnessLab and against the anti-pattern
  shortcuts the chapter warns about;
- an interactive **playground** (ipywidgets) that drives the real controls live;
- a hands-on challenge.

Notebook 08 ends with the full **Chapter 2 Gauntlet**, 18 attacks across every section, and a
review board that turns a plausible policy change into an evidence-based rollback.

## Package layout

```
harnesslab/              one module per chapter section: the single source of truth
  vocabulary.py          levels, reversibility, actions, decisions
  authority.py           §2.1    envelope.py   §2.2    reversibility.py  §2.3
  approval.py            §2.4    budget.py     §2.5    slo.py            §2.6
  lifecycle.py           §2.7    contract.py   §§2.8–2.11
  arena.py               the red-team gauntlet (attacks + HarnessLab vs Shortcuts defenses)
  viz.py, playground.py  rich notebook rendering and interactive widgets
contracts/research_agent.json      machine-readable teaching contract
notebooks/                         the eight labs
tests/test_chapter2_invariants.py  cross-notebook control invariants
solutions/challenge_notes.md       instructor/reference notes
```

Notebooks contain no function or class definitions; a test enforces this so the implementation cannot
drift between a notebook and the package.

## Running

Requires Python 3.10+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
jupyter lab
```

Start Jupyter from this project root. Open the notebooks in numeric order. Mermaid diagrams need
JupyterLab 4.1 or newer; playgrounds need ipywidgets (both in `requirements.txt`).

To execute every notebook in a real kernel and check every invariant and attack:

```bash
pytest
```

## Extending the gauntlet

Add an attack to `harnesslab/arena.py` with the `@attack(section, notebook, name, story)` decorator.
It receives a `Defenses` object and returns `(blocked, detail)`. The test suite requires HarnessLab to
block every registered attack.

## Design constraint

HarnessLab is intentionally **not** a production framework and is not tied to any proprietary agent SDK. Its job is to make the chapter's design patterns executable and inspectable with minimal Python.

## License

MIT — see [LICENSE](LICENSE).
