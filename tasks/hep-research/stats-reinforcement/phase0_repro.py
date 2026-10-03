#!/usr/bin/env python3
"""Phase 0 reproduction of findings F1-F11 for the hep-statistics reinforcement (work order TASK.md, r2).

Run from the repository root with NumPy and SciPy:  python3 tasks/hep-research/stats-reinforcement/phase0_repro.py
Prints one JSON line per finding: {"id", "reproduces", "classification", "detail"}. "reproduces": true means the
finding is present in the tree being run. After the work order is done every entry should print false.
"""
import copy
import json
import math
import re
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy import stats

PLUGIN = Path(__file__).resolve().parents[3] / "plugins" / "hep-research"
sys.path.insert(0, str(PLUGIN))

from contracts.validate import validate_artifact  # noqa: E402

STATS = PLUGIN / "skills" / "hep-statistics"
out = []


def rec(i, bad, cls, detail):
    out.append({"id": i, "reproduces": bool(bad), "classification": cls, "detail": detail})


def text(*parts):
    return "\n".join(p.read_text(encoding="utf-8") for p in parts if p.exists())


def tree_text(root, suffixes=(".md", ".py", ".json")):
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in sorted(root.rglob("*"))
                     if p.is_file() and p.suffix in suffixes and "__pycache__" not in p.parts)


# F1: Li & Ma statement and the low-count claim; the three p-values at (4, 2, 0.25).
n_on, n_off, alpha = 4, 2, 0.25
tot = n_on + n_off
lnl = n_on * math.log((1 + alpha) / alpha * n_on / tot) + n_off * math.log((1 + alpha) * n_off / tot)
s_obs = math.sqrt(2 * lnl)
p_asym = stats.norm.sf(s_obs)
p_exact = float(stats.binom.sf(n_on - 1, tot, alpha / (1 + alpha)))
rng = np.random.default_rng(1)
b_hat = tot / (1 + alpha)  # background-only fit: OFF mean b, ON mean alpha*b
on = rng.poisson(alpha * b_hat, 200000)
off = rng.poisson(b_hat, 200000)
t = on + off
with np.errstate(divide="ignore", invalid="ignore"):
    a = np.where(on > 0, on * np.log((1 + alpha) / alpha * on / t), 0.0)
    b = np.where(off > 0, off * np.log((1 + alpha) * off / t), 0.0)
s_toy = np.where(on - alpha * off > 0, np.sqrt(np.clip(2 * (a + b), 0, None)), 0.0)
p_toy = float(np.mean(s_toy >= s_obs - 1e-12))
ref = text(STATS / "references" / "astroparticle-statistics.md")
doc = text(STATS / "scripts" / "li_ma_significance.py")
claims = {
    "sqrt2_equivalence": "sqrt(2) * sqrt(-2 ln(lambda))" in ref,
    "no_large_counts_claim": "does not\n  require large counts" in ref or "does not require large counts" in ref,
    "valid_at_low_counts_docstring": "remains valid at low counts" in doc,
}
rec("F1", any(claims.values()), "scientific error + method-claim gap",
    {"claims_present": claims, "p_asymptotic": round(p_asym, 6), "p_toy_seed1_2e5": round(p_toy, 5),
     "p_exact_conditional": round(p_exact, 6)})

# F2: without the AMS-02 profile, no skill file documents the core/stats subcommands.
subcommands = []
import importlib  # noqa: E402
for mod in ("likelihood_limits", "poisson_diagnostics", "statistical_toys", "template_fit", "unfolding_diagnostics"):
    parser = importlib.import_module(f"core.stats.{mod}").build_parser()
    for action in parser._actions:
        if getattr(action, "choices", None) and isinstance(action.choices, dict):
            subcommands += list(action.choices)
tmp = Path(tempfile.mkdtemp(prefix="stats r0 "))
try:
    shutil.copytree(PLUGIN / "skills", tmp / "skills", ignore=shutil.ignore_patterns("__pycache__"))
    skills_txt = tree_text(tmp / "skills", (".md",))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
documented = sorted(c for c in set(subcommands) if re.search(rf"`{re.escape(c)}\b", skills_txt))
ams = text(PLUGIN / "profiles/experiments/ams-02/modules/methods/statistical-diagnostics.md")
rec("F2", len(documented) < len(set(subcommands)), "layering inversion + stale docs",
    {"subcommands": len(set(subcommands)), "documented_under_skills": documented,
     "ams_stale_exit_code_sentence": "exit 0 (ok) or 2 (rejected input)" in ams})


def absent(fid, cls, root_text, patterns):
    hits = {p: bool(re.search(p, root_text, re.I)) for p in patterns}
    rec(fid, not any(hits.values()), cls, {"pattern_hits": hits})


stats_tree = tree_text(STATS) + tree_text(PLUGIN / "core" / "stats") + tree_text(PLUGIN / "adapters")
absent("F3", "capability gap", stats_tree, [r"def \w*impact", r"impacts? table", r"pulls and constraints",
                                             r"grouped (uncertainty )?breakdown"])
absent("F4", "content gap", stats_tree, [r"interpcode|code 4\b|code-4", r"\blnN\b.*asymmetric", r"one-sided (systematic|variation)"])
absent("F5", "capability gap", tree_text(STATS, (".py",)) + tree_text(PLUGIN / "core" / "stats", (".py",)),
       [r"global_p", r"upcrossing"])
absent("F6", "capability gap", tree_text(STATS), [r"Z_A", r"expected (discovery )?significance", r"Bayes factor"])
absent("F7", "capability gap", tree_text(STATS, (".py",)) + tree_text(PLUGIN / "core" / "stats", (".py",)),
       [r"rhat|r_hat|split.?r", r"effective.sample.size|\bess\b"])
absent("F8", "content gap", tree_text(STATS), [r"sPlot", r"Pivk", r"custom orthogonal weight"])
absent("F9", "ownership-content gap", tree_text(STATS), [r"NSBI|neural simulation-based", r"likelihood.ratio (trick|estimat)",
                                                         r"classifier output"])
absent("F10", "content gap", tree_text(PLUGIN), [r"simplified likelihood", r"patchset"])

# F11: a scan result without a global significance validates.
doc11 = json.loads((PLUGIN / "contracts/fixtures/artifacts/valid/statres_frequentist.json").read_text())
doc11 = copy.deepcopy(doc11)
doc11["extension"]["significance"] = {"local_p": 1e-3, "local_z": 3.09, "scan": {"parameters": ["mass"], "ranges": [[100, 200]]}}
rep = validate_artifact(doc11)
rec("F11", rep.ok and not any(f.code == "stats.lee_missing" for f in rep.findings), "contract gap",
    {"validates_ok": rep.ok, "codes": sorted({f.code for f in rep.findings})})

for row in out:
    print(json.dumps(row))
