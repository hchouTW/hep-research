#!/usr/bin/env python3
"""Build a pyhf workspace from a statistical model card, and check simultaneous signal/control-region fits with
Asimov closure (hep-statistics audit T15).

A model card (contracts/schemas/statistical_model.json) lists channels with their role and observed counts, samples
with their modifiers (poi, free-normalization, constrained-normalization with hi/lo factors), constraints with the
auxiliary measurement each encodes (aux_id) and the toy ensemble. The card is validated first
(contracts.validate.check_model_card): an auxiliary measurement used twice, a prior in a frequentist model or an
undefined parameter is refused before any fit. A constrained-normalization parameter shared by samples in several
channels (a luminosity, a transfer factor's uncertainty) becomes one pyhf normsys parameter, so its auxiliary
measurement enters once.

asimov_closure(card, truth) fits the card's model to the Asimov data of a truth model (expected counts, nuisances at
nominal): the fitted poi must equal the true one within CLOSURE_TOL. When the truth has signal in a control region and
the card omits it, the background normalization absorbs it and the poi is biased: the closure check detects it.

Usage: model_card.py --card CARD.json [--truth TRUTH.json] [--out REPORT.json]
Exit codes: 0 the card is valid, its fit converged and (with --truth) the closure passes; 1 the closure fails or a fit
fails; 2 the card is refused or pyhf is not installed. Needs pyhf (tested with 0.7.6) and NumPy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
sys.path.insert(0, str(PLUGIN))

from contracts.schema import Report, validate  # noqa: E402
from contracts.validate import check_model_card  # noqa: E402

CLOSURE_TOL = 1e-3  # |mu_hat - mu_true| <= CLOSURE_TOL * max(1, |mu_true|) on Asimov data (optimizer tolerance 1e-10)


class CardRefused(ValueError):
    """The card does not validate or uses a feature this converter does not map."""


def check(card: dict, paradigm: str = "frequentist") -> None:
    rep = validate(card, "statistical_model.json")
    if rep.ok:
        check_model_card(card, paradigm, rep, "$")
    errors = [f"{f.code}: {f.message}" for f in rep.findings if f.severity == "error"]
    if errors:
        raise CardRefused("; ".join(errors))


WIDTH_TOL = 1e-9  # a constraint width must equal the modifier's hi - 1 and 1 - lo when both are given


def fitted_channels(card: dict) -> list[dict]:
    """Channels that enter the likelihood: signal and control regions. A validation region is a check of the fitted
    model, never part of the fit (STH-T3.12: before, its counts pulled the fit)."""
    return [ch for ch in card["channels"] if ch.get("role") != "validation-region"]


def _normsys(m: dict, c: dict) -> dict:
    """hi/lo of a constrained normalization: as given, or from the constraint width (1 +- width); refused when both
    are given and disagree (the card would describe two different constraints)."""
    w = c.get("width")
    if "hi" in m and "lo" in m:
        if w is not None and (abs(m["hi"] - 1.0 - w) > WIDTH_TOL or abs(1.0 - m["lo"] - w) > WIDTH_TOL):
            raise CardRefused(f"'{m['parameter']}': constraint width {w} disagrees with the modifier's hi/lo "
                              f"({m['hi']}, {m['lo']}); give one consistent description")
        return {"hi": m["hi"], "lo": m["lo"]}
    if w is None:
        raise CardRefused(f"'{m['parameter']}' needs hi/lo on the modifier or a width on its constraint")
    if not 0 < w < 1:
        raise CardRefused(f"'{m['parameter']}': width {w} must lie in (0, 1) to map to hi/lo = 1 +- width")
    return {"hi": 1.0 + w, "lo": 1.0 - w}


def to_pyhf(card: dict, observed: dict | None = None) -> dict:
    """pyhf workspace spec of the card; observed overrides the card's counts per channel (for Asimov data).
    Validation-region channels are left out of the likelihood; constraint widths reach the normsys hi/lo."""
    check(card)
    cons = {c["parameter"]: c for c in card["constraints"]}
    channels = []
    for ch in fitted_channels(card):
        samples = []
        for s in card["samples"]:
            if s["channel"] != ch["name"]:
                continue
            mods = []
            for m in s["modifiers"]:
                if m["type"] in ("poi", "free-normalization"):
                    mods.append({"name": m["parameter"], "type": "normfactor", "data": None})
                else:
                    c = cons[m["parameter"]]
                    if c["form"] != "gaussian":
                        raise CardRefused(f"constraint form {c['form']} of '{m['parameter']}' is not mapped (gaussian only)")
                    mods.append({"name": m["parameter"], "type": "normsys", "data": _normsys(m, c)})
            samples.append({"name": s["name"], "data": list(map(float, s["yields"])), "modifiers": mods})
        channels.append({"name": ch["name"], "samples": samples})
    fitted = {ch["name"] for ch in fitted_channels(card)}
    obs = {k: v for k, v in (observed or {ch["name"]: ch["observed"] for ch in card["channels"]}).items() if k in fitted}
    params = [{"name": card["poi"], "bounds": [[-10.0, 50.0]]}]
    free = {m["parameter"] for s in card["samples"] if s["channel"] in fitted for m in s["modifiers"]
            if m["type"] == "free-normalization"}
    params += [{"name": p, "bounds": [[0.0, 50.0]]} for p in sorted(free)]
    return {"channels": channels, "observations": [{"name": k, "data": [float(x) for x in v]} for k, v in obs.items()],
            "measurements": [{"name": "card", "config": {"poi": card["poi"], "parameters": params}}], "version": "1.0.0"}


def expected_counts(card: dict, values: dict | None = None) -> dict:
    """Expected counts per channel at the given parameter values (poi and free normalizations; nuisances nominal)."""
    values = values or {}
    out = {ch["name"]: [0.0] * len(ch["observed"]) for ch in card["channels"]}
    for s in card["samples"]:
        f = 1.0
        for m in s["modifiers"]:
            if m["type"] in ("poi", "free-normalization"):
                f *= values.get(m["parameter"], 1.0)
        out[s["channel"]] = [a + f * y for a, y in zip(out[s["channel"]], s["yields"])]
    return out


def fit(card: dict, observed: dict | None = None) -> dict:
    import numpy as np
    import pyhf
    spec = to_pyhf(card, observed)
    pyhf.set_backend("numpy", pyhf.optimize.scipy_optimizer(tolerance=1e-10))
    try:
        ws = pyhf.Workspace(spec)
        model = ws.model(modifier_settings={"normsys": {"interpcode": "code4"}})
        data = ws.data(model)
        pars, twice_nll = pyhf.infer.mle.fit(data, model, return_fitted_val=True)
        init = np.asarray(model.config.suggested_init())
        pulls = {}
        for name in model.config.par_order:
            if model.config.param_set(name).constrained:
                sl = model.config.par_slice(name)
                pulls[name] = float(pars[sl][0] - init[sl][0])
        values = {n: float(pars[model.config.par_slice(n)][0]) for n in model.config.par_order}
    finally:
        pyhf.set_backend("numpy", "scipy")
    return {"values": values, "poi_hat": values[card["poi"]], "twice_nll": float(twice_nll), "pulls": pulls,
            "validation_regions_excluded": [ch["name"] for ch in card["channels"] if ch.get("role") == "validation-region"],
            "ensemble": card.get("ensemble"),
            "ensemble_note": "recorded from the card, not used here: this converter fits once and generates no toys"}


def asimov_closure(card: dict, truth: dict, truth_values: dict) -> dict:
    """Fit the card's model to the Asimov data of the truth card at truth_values; closure passes when the fitted poi
    equals the truth's within CLOSURE_TOL (relative to max(1, |mu|)) and no constrained nuisance is pulled by more than
    CLOSURE_TOL."""
    asimov = expected_counts(truth, truth_values)
    r = fit(card, asimov)
    mu = truth_values.get(truth["poi"], 1.0)
    bias = r["poi_hat"] - mu
    ok = abs(bias) <= CLOSURE_TOL * max(1.0, abs(mu)) and all(abs(p) <= CLOSURE_TOL for p in r["pulls"].values())
    return {"status": "pass" if ok else "fail", "mu_true": mu, "mu_hat": r["poi_hat"], "bias": bias,
            "pulls": r["pulls"], "fitted": r["values"], "tolerance": CLOSURE_TOL, "asimov": asimov}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--card", required=True)
    ap.add_argument("--truth", help="truth card for the Asimov closure (default: the card itself)")
    ap.add_argument("--truth-values", default="{}", help="JSON object of poi and free-normalization values of the truth")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        import pyhf  # noqa: F401
    except ImportError:
        print(json.dumps({"status": "refused", "reason": "pyhf is not installed"}))
        return 2
    try:
        card = json.loads(Path(a.card).read_text())
        truth = json.loads(Path(a.truth).read_text()) if a.truth else card
        check(card)
        check(truth)
        tv = json.loads(a.truth_values)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}))
        return 2
    rep = {"fit": fit(card), "closure": asimov_closure(card, truth, tv)}
    text = json.dumps(rep, indent=1)
    if a.out:
        Path(a.out).write_text(text + "\n")
    print(text)
    return 0 if rep["closure"]["status"] == "pass" else 1


_ = Report  # re-exported for callers that build reports themselves
if __name__ == "__main__":
    sys.exit(main())
