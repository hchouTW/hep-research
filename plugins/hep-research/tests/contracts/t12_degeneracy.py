#!/usr/bin/env python3
"""T12 stage 6: A37 and plan section 9.6 in T12 (T12-18, the g x E degeneracy; T12-19, the weak-mode witness; R31, R37).

A harness for identifiability tests on synthetic fixtures. It derives no constant from data and claims no calibration or alignment
quality (R31). Every rule, tolerance and expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 6").
It lives under tests/ because it imports the contracts, the control layer, T10's fixture tool and T07's test arithmetic
(tools/check_layering.py: tests import anything). T10's t10_a37.py and T07's test_acts_cai_refit.py are imported, never changed.

- gxe (T12-18): the artificial model y = g E of section 9.6, in logarithms, in T10's fixture form (t10_a37.gxe_design, exact_rank,
  GAUGE_TOLERANCE, CONVERGED): a two-parameter case (one g, one E, six observations of the same type) and T10's C x E form. Without a
  named external constraint the fit reports only the identifiable combinations (gE; gain ratios and products g_c E_e); two gauges
  converge alike; a same-type holdout closes in both and is refused as validation; only constraint.external-energy-reference
  identifies g and E. The fit's payload sidecar (R32) records the unconstrained mode or the constraint used.
- witness (T12-19): CAI-T07-4's fixtures 7003 and 7004 reprocessed inside T12 through the stage-1 loop machinery (the control layer's
  contract, admission, receipts, checks by digest, labels and publish; the identity-keyed cache acted on only through admission; R32
  records checked with check_used), with the frozen T07 binaries at pinned SHA-256. No round family: nothing is derived (R31). The
  witness cells are weak_mode_self_check's (T07's), at T07's k = 4.5 and n = 4.5, and must reproduce T07's record (job 7546791) to its
  printed precision; a chi2-only judge passes while q/p is biased; the reprocessing's method card lists the sagitta-like deformation
  with its named constraint.

Operation:
  gxe [--plant report-absolute|holdout-as-validation|constraint-as-validation|unnamed-constraint] --out FILE
  witness --build DIR --t07-record FILE --work DIR [--plant no-deformation|visible-chi2|card-without-constraint|
          constraint-as-validation|reuse-across-data] --out FILE
      Each writes its record (t12-gxe/1, t12-weak-mode-witness-run/1). Status and exit (core/status.py): ok 0, every expectation holds;
      failed 1, one does not (a planted defect is detected); rejected 2, bad input (unknown plant, an output that exists, a missing
      folder, a work folder that is not empty, a binary or the T07 record not the pinned bytes); incomplete 3, a crash, a native program
      that fails, or a record that cannot be written.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import math
import re
import sys
import types
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
for _path in (ROOT, ROOT / "skills" / "hep-computing" / "scripts", ROOT / "adapters" / "timing-pid" / "assets" / "fixture_tools"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
import t10_a37  # noqa: E402
from contracts.conditions import check_used, check_validation_claim, payload_identity, reuse_decision  # noqa: E402
from contracts.recipe_semantics import canonical_sha256  # noqa: E402
from control_layer_support import derivation as dv  # noqa: E402
from control_layer_support import task_record  # noqa: E402
from core.status import exit_code  # noqa: E402
from tests.adapters import test_acts_cai_refit as t07  # noqa: E402
from tests.contracts.reconstruction_fixtures import calibration_payload, product as product_document, used_payload  # noqa: E402

alignment_payload = t07.alignment_payload

# ================================================================ T12-18: fixed in t12-stage-plan.md, "Stage 6"
GAUGE_TOLERANCE, CONVERGED = t10_a37.GAUGE_TOLERANCE, t10_a37.CONVERGED
TWO_PARAMETER = {"g": 1.25, "E": 2.0, "observations": 6}
GAUGE = 3.0
GAINS = [1.0 + 0.05 * c for c in range(8)]
ENERGIES = [1.0, 2.0, 3.0, 5.0, 8.0]
REFERENCE_EVENT = 2
CONSTRAINT = "constraint.external-energy-reference"
UNNAMED = "the energy is known"
GAIN_MODE = "mode.global-gain-scale"
GAUGE_TEXT = "g -> a g, E -> E / a"
HOLDOUT_STATEMENT = "same-type holdout: not validation (A37)"
IDENTIFIED, VALIDATED = "absolute scale identified", "absolute scale validated"
GXE_PLANTS = ("report-absolute", "holdout-as-validation", "constraint-as-validation", "unnamed-constraint")
GXE_CLAIMS = {"label": "synthetic", "quality": "none", "a37": "g x E degeneracy on exact synthetic inputs (identifiability); no calibration quality"}

# ================================================================ T12-19: fixed in t12-stage-plan.md, "Stage 6"
K_WEAK, WEAK_N_SIGMA = t07.K_WEAK, t07.WEAK_N_SIGMA
RATIO_PRECISION, CHI2_PRECISION = 1e-4, 1e-5
DRIVER_SHA256 = "7556beb828f3a9029a79a34f41c938e7f9ff328281855800d21d655649ece958"       # freeze-b.md, T07 built binary
GENERATOR_SHA256 = "f1c7309a804ba71a8e54a1ff55f16685a4255703142e130624fe290e77888931"    # job 7546791's build (and 7585954's)
T07_RECORD_SHA256 = t10_a37.T07_LOG_SHA256
T07_JOB = t10_a37.T07_JOB
DRIVER, GENERATOR = "acts_tracking_driver", "t07_cai_fixture_generator"
FIXTURES = {"generate-7003": ("cai-clean", t07.outputs_tests.CAI_FIXTURE_ID), "generate-7004": ("cai-sagitta", t07.SAGITTA_FIXTURE_ID)}
REFITS = {"refit-7003": "generate-7003", "refit-7004": "generate-7004"}
ORDER = ("nominal-alignment", "generate-7003", "refit-7003", "generate-7004", "refit-7004", "witness")
NATIVE_STEPS = ("generate-7003", "refit-7003", "generate-7004", "refit-7004")
ALIGNMENT_TAG = "t12_cai_alignment"
APPLIED = "driver nominal geometry, no payload argument"
ZERO_PAYLOAD_LINE = "CAI-T07-3 zero payload through the placement route: /1 records equal"
ZERO_PAYLOAD_EVIDENCE = ("CAI-T07-3, job 7546791 (cai-refit.log): the zero payload through the placement route gives the plain geometry's "
                         "/1 records, so the nominal payload recorded stands for the driver's built-in nominal geometry")
SAGITTA_MODE = "mode.sagitta-like-deformation"
VISIBLE_CHI2 = 0.1
WITNESS_PLANTS = ("no-deformation", "visible-chi2", "card-without-constraint", "constraint-as-validation", "reuse-across-data")
WITNESS_CLAIMS = {"label": "synthetic", "quality": "none",
                  "a37": "weak-mode witness reproduced in a T12 reprocessing (identifiability); no alignment quality",
                  "control_rules": "not qualified (G07, mode M1)"}
CARD_FORMAT = "t12-method-card/1"
CARD_MODE_KEYS = {"mode", "description", "witness", "constraining_information", "independent_observables", "constraints_used",
                  "identifiable_combinations"}
NOT_SATISFYING = ("placeholder", "convergence", "same-type holdout")
CELL_LINE = re.compile(r"CAI-T07-4 cell charge ([+-]1) bending bin (\d+) tracks (\d+) and (\d+) change in q/p ([-+0-9.]+) per-track sigmas "
                       r"\(se [-+0-9.]+, sigma [-+0-9.]+ per GeV\), ([-+0-9.]+) stated sigmas; change in mean chi2/ndf ([-+0-9.]+) \(se ([-+0-9.]+)\)")


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(a, b) -> float:
    return max(abs(x - y) / max(abs(x), abs(y), 1e-300) for x, y in zip(a, b, strict=True))


def _json(value):
    """A JSON round trip: tuples become lists and numpy scalars floats, so the in-memory record is the written one."""
    return json.loads(json.dumps(value, default=float))


# ================================================================ T12-18: the g x E fit

def _lstsq(rows, values):
    a, b = numpy.array(rows, dtype=float), numpy.array(values, dtype=float)
    solution, *_ = numpy.linalg.lstsq(a, b, rcond=None)
    residual = a @ solution - b
    return solution, float(residual @ residual)


def _design(channels, events, repeat):
    return t10_a37.gxe_design(channels, events) * repeat


def _logs(gains, energies, repeat):
    return [math.log(g * e) for g in gains for e in energies] * repeat


def gxe_fit(channels, events, repeat, gains, energies, constraint=None, reference_event=0, gauge_log=0.0, report_absolute=False) -> dict:
    """Least squares of ln y = ln g_c + ln E_e. A named constraint (an identifier constraint.*) fixes the reference event's energy and
    makes the scale unique; anything else fixes only the gauge (ln g_0 = gauge_log) and the fit reports the identifiable combinations."""
    rows, logs = _design(channels, events, repeat), _logs(gains, energies, repeat)
    named = isinstance(constraint, str) and constraint.startswith("constraint.")
    if named:
        extra = [0] * channels + [int(j == reference_event) for j in range(events)]
        solution, residual = _lstsq(rows + [extra], logs + [math.log(energies[reference_event])])
    else:
        solution, residual = _lstsq(rows + [[1] + [0] * (channels + events - 1)], logs + [gauge_log])
    g, e = numpy.exp(solution[:channels]), numpy.exp(solution[channels:])
    products = [[float(a * b) for b in e] for a in g]
    ratios = [float(a / g[0]) for a in g]
    absolute = named or report_absolute
    if channels == 1 and events == 1:
        reported = {"gE": products[0][0]}
        if absolute:
            reported.update(g=float(g[0]), E=float(e[0]))
    else:
        reported = {"ratios": ratios, "products": products}
        if absolute:
            reported.update(g=[float(v) for v in g], E=[float(v) for v in e])
    return {"reported": reported, "unidentified": [] if named else ["g", "E"], "gauge": None if named else GAUGE_TEXT,
            "identified_by": constraint if named else None, "residual": residual, "solution": [float(v) for v in solution]}


def _identifiable(fit) -> list:
    reported = fit["reported"]
    if "gE" in reported:
        return [reported["gE"]]
    return list(reported["ratios"]) + [v for row in reported["products"] for v in row]


def _holdout(channels, events, repeat, gains, energies) -> list:
    """A same-type holdout fitted in both gauges: the last observation (one channel and event) or the last event, its energy refitted
    from its own amplitudes with the gains held (T10's form). Each fit's ln g_0 is recorded (fix round 1, m2): they differ by ln a."""
    residuals, ln_g0 = [], []
    for gauge_log in (0.0, math.log(GAUGE)):
        if channels == 1 and events == 1:
            solution, _ = _lstsq(_design(1, 1, repeat - 1) + [[1, 0]], _logs(gains, energies, repeat - 1) + [gauge_log])
            held = math.log(gains[0] * energies[0])
            residuals.append(float((solution[0] + solution[1] - held) ** 2))
            ln_g0.append(float(solution[0]))
        else:
            held = events - 1
            solution, _ = _lstsq(_design(channels, held, 1) + [[1] + [0] * (channels + held - 1)],
                                 _logs(gains, energies[:held], 1) + [gauge_log])
            ln_g = solution[:channels]
            amplitudes = [math.log(g * energies[-1]) for g in gains]
            ln_e = float(numpy.mean([t - lg for t, lg in zip(amplitudes, ln_g, strict=True)]))
            residuals.append(float(sum((lg + ln_e - t) ** 2 for lg, t in zip(ln_g, amplitudes, strict=True))))
            ln_g0.append(float(ln_g[0]))
    return {"residuals": residuals, "ln_g0": ln_g0}


def gxe_case(channels, events, repeat, gains, energies, reference_event, plant=None) -> dict:
    rows = _design(channels, events, repeat)
    extra = [0] * channels + [int(j == reference_event) for j in range(events)]
    fit = gxe_fit(channels, events, repeat, gains, energies, report_absolute=plant == "report-absolute")
    constrained = gxe_fit(channels, events, repeat, gains, energies, constraint=CONSTRAINT, reference_event=reference_event)
    if plant == "unnamed-constraint":         # the defect: a text, not a constraint.* identifier, recorded as if it identified the scale
        constrained = dict(gxe_fit(channels, events, repeat, gains, energies, report_absolute=True), identified_by=UNNAMED, unidentified=[])
    y1 = [g * e for g in gains for e in energies]
    y2 = [(GAUGE * g) * (e / GAUGE) for g in gains for e in energies]
    first = gxe_fit(channels, events, repeat, gains, energies, gauge_log=0.0)
    second = gxe_fit(channels, events, repeat, gains, energies, gauge_log=math.log(GAUGE))
    return {"channels": channels, "events": events, "observations_per_cell": repeat, "parameters": channels + events,
            "rank": {"without": t10_a37.exact_rank(rows), "with": t10_a37.exact_rank(rows + [extra])},
            "fit": fit, "constrained": constrained,
            "gauges": {"gauge": GAUGE, "largest_relative_y": _relative(y1, y2), "residuals": [first["residual"], second["residual"]],
                       "scale_difference": second["solution"][0] - first["solution"][0],
                       "reported_relative": _relative(_identifiable(first), _identifiable(second))},
            "holdout": _holdout(channels, events, repeat, gains, energies)}


def judge_claims(claims, identified_by, plant=None) -> list:
    """Section 9.6, A37: a same-type holdout and convergence never identify or validate the scale; a named constraint that the fit used
    identifies it, and is never its validation (fix round 1, m1; CAI-T06-3)."""
    judged = []
    for claim in claims:
        by = claim["by"]
        accepted = claim["claim"] == IDENTIFIED and isinstance(by, str) and by.startswith("constraint.") and by == identified_by
        if plant == "holdout-as-validation" and by == "holdout":
            accepted = True
        judged.append(dict(claim, accepted=accepted))
    return judged


def gxe_sidecar(fit, plant=None, constrained=False) -> dict:
    """The R32 sidecar of the fit's (synthetic) payload: a digest of the reported values, never the constants themselves."""
    content = sha256_hex(json.dumps(fit["reported"], sort_keys=True).encode())
    producer = {"kind": "external", "source": "synthetic g x E fixture (T12 stage 6)"}
    if constrained:
        used = [fit["identified_by"]] if fit["identified_by"] else []
        validation = [CONSTRAINT] if plant == "constraint-as-validation" else []
        return calibration_payload(tag="t12_gxe_gain", content_sha256=content, producer=producer, constraints_used=used,
                                   unconstrained_modes=[], independent_validation=validation)
    return calibration_payload(tag="t12_gxe_gain", content_sha256=content, producer=producer, constraints_used=[],
                               unconstrained_modes=[GAIN_MODE], independent_validation=[])


def gxe_run(plant=None) -> dict:
    if plant is not None and plant not in GXE_PLANTS:
        raise ValueError(f"unknown plant {plant!r}")
    two = gxe_case(1, 1, TWO_PARAMETER["observations"], [TWO_PARAMETER["g"]], [TWO_PARAMETER["E"]], 0, plant)
    form = gxe_case(len(GAINS), len(ENERGIES), 1, GAINS, ENERGIES, REFERENCE_EVENT, plant)
    used = two["constrained"]["identified_by"]
    claims = [{"claim": VALIDATED, "by": "holdout"}, {"claim": IDENTIFIED, "by": "convergence"}, {"claim": IDENTIFIED, "by": used},
              {"claim": VALIDATED, "by": used}]
    judged = judge_claims(claims, used if isinstance(used, str) and used.startswith("constraint.") else None, plant)
    unconstrained, constrained = gxe_sidecar(two["fit"], plant), gxe_sidecar(two["constrained"], plant, constrained=True)
    codes = [finding.code for finding in check_validation_claim(constrained, CONSTRAINT).errors]
    return _json({"schema": "t12-gxe/1", "plant": plant, "claims": dict(GXE_CLAIMS), "cases": {"two-parameter": two, "t10-form": form},
                  "claims_judged": judged, "claims_refused": [c for c in judged if not c["accepted"]],
                  "holdout_statement": HOLDOUT_STATEMENT, "sidecars": {"unconstrained": unconstrained, "constrained": constrained},
                  "validation_claim_codes": codes, "tolerances": {"relative": GAUGE_TOLERANCE, "converged": CONVERGED}})


def _close(got, want) -> bool:
    return abs(got - want) <= GAUGE_TOLERANCE * max(abs(got), abs(want), 1e-300)


def _two_reports_truth(rec) -> bool:
    fit = rec["cases"]["two-parameter"]["fit"]
    return set(fit["reported"]) == {"gE"} and _close(fit["reported"]["gE"], TWO_PARAMETER["g"] * TWO_PARAMETER["E"]) \
        and fit["unidentified"] == ["g", "E"] and fit["gauge"] == GAUGE_TEXT and fit["identified_by"] is None


def _form_reports_truth(rec) -> bool:
    fit = rec["cases"]["t10-form"]["fit"]
    return set(fit["reported"]) == {"ratios", "products"} and fit["identified_by"] is None and fit["unidentified"] == ["g", "E"] \
        and all(_close(r, g / GAINS[0]) for r, g in zip(fit["reported"]["ratios"], GAINS, strict=True)) \
        and all(_close(v, g * e) for row, g in zip(fit["reported"]["products"], GAINS, strict=True) for v, e in zip(row, ENERGIES, strict=True))


def _constrained_truth(rec) -> bool:
    two, form = rec["cases"]["two-parameter"]["constrained"], rec["cases"]["t10-form"]["constrained"]
    return two["identified_by"] == CONSTRAINT and form["identified_by"] == CONSTRAINT and two["unidentified"] == [] \
        and _close(two["reported"]["g"], TWO_PARAMETER["g"]) and _close(two["reported"]["E"], TWO_PARAMETER["E"]) \
        and all(_close(a, b) for a, b in zip(form["reported"]["g"], GAINS, strict=True)) \
        and all(_close(a, b) for a, b in zip(form["reported"]["E"], ENERGIES, strict=True))


def _sidecars_hold(rec) -> bool:
    free, bound = rec["sidecars"]["unconstrained"], rec["sidecars"]["constrained"]
    for sidecar in (free, bound):
        if sidecar["payload_id"] != payload_identity(sidecar) or CONSTRAINT in sidecar["independent_validation"] \
                or any("holdout" in item for item in sidecar["independent_validation"]):
            return False
    return free["unconstrained_modes"] == [GAIN_MODE] and free["constraints_used"] == [] and bound["unconstrained_modes"] == [] \
        and bound["constraints_used"] == [CONSTRAINT] and rec["validation_claim_codes"] == ["conditions.constraint_as_validation"]


def assess_gxe(rec) -> list:
    """The G expectations (t12-stage-plan.md, Stage 6) that do not hold. A missing field fails its expectation."""
    def cases():
        return rec["cases"]["two-parameter"], rec["cases"]["t10-form"]

    def by(name, claim=None):
        return [c for c in rec["claims_judged"] if c["by"] == name and (claim is None or c["claim"] == claim)]

    rules = {
        "G1": lambda: rec["cases"]["two-parameter"]["rank"] == {"without": 1, "with": 2} and rec["cases"]["two-parameter"]["parameters"] == 2
        and rec["cases"]["t10-form"]["rank"] == {"without": len(GAINS) + len(ENERGIES) - 1, "with": len(GAINS) + len(ENERGIES)},
        "G2": lambda: _two_reports_truth(rec) and _form_reports_truth(rec),
        "G3": lambda: all(c["gauges"]["gauge"] == GAUGE and c["gauges"]["largest_relative_y"] <= GAUGE_TOLERANCE
                          and len(c["gauges"]["residuals"]) == 2 and all(r <= CONVERGED for r in c["gauges"]["residuals"])
                          and abs(c["gauges"]["scale_difference"] - math.log(GAUGE)) <= GAUGE_TOLERANCE
                          and c["gauges"]["reported_relative"] <= GAUGE_TOLERANCE for c in cases()),
        "G4": lambda: all(len(c["holdout"]["residuals"]) == 2 and all(r <= CONVERGED for r in c["holdout"]["residuals"])
                          and len(c["holdout"]["ln_g0"]) == 2
                          and abs(c["holdout"]["ln_g0"][1] - c["holdout"]["ln_g0"][0] - math.log(GAUGE)) <= GAUGE_TOLERANCE for c in cases())
        and len(by("holdout")) == 1 and len(by("convergence")) == 1 and not by("holdout")[0]["accepted"]
        and not by("convergence")[0]["accepted"] and rec["holdout_statement"] == HOLDOUT_STATEMENT,
        "G5": lambda: rec["cases"]["two-parameter"]["rank"]["with"] == 2 and _constrained_truth(rec)
        and len(by(CONSTRAINT, IDENTIFIED)) == 1 and by(CONSTRAINT, IDENTIFIED)[0]["accepted"]
        and len(by(CONSTRAINT, VALIDATED)) == 1 and not by(CONSTRAINT, VALIDATED)[0]["accepted"],
        "G6": lambda: _sidecars_hold(rec),
    }
    return _failed(rules)


def _failed(rules) -> list:
    failed = []
    for rule_id, rule in rules.items():
        try:
            held = bool(rule())
        except (KeyError, TypeError, IndexError, AttributeError, ValueError):
            held = False
        if not held:
            failed.append(rule_id)
    return failed


# ================================================================ T12-19: the method card of the reprocessing

def method_card() -> dict:
    """The T12 reprocessing's method card (section 9.6): the unconstrained mode, its witness, the named information that constrains it,
    independent observables that can confirm it, and the constraints used (none: nothing is derived, R31)."""
    return {
        "format": CARD_FORMAT, "recipe": "t12.cai-reprocessing/1",
        "scope": "T12 stage 6: CAI-T07-4's fixtures 7003 and 7004 reprocessed inside T12 at nominal geometry with the frozen T07 binaries; "
                 "synthetic data only; no alignment quality claim (plan R31, R37)",
        "sources": ["plan v9.2 section 9.6, A37 and R37 (T07 weak-mode fixture)",
                    "skills/hep-detector/references/calibration-and-alignment.md (alignment and weak modes)",
                    "adapters/timing-pid/assets/timing-method-card.json (mode.curvature-offset: the same mode seen by T10)"],
        "rule": "an item that constrains a mode is never one of its independent observables (section 9.6): the constraint.* and observable.* "
                "identifiers of a mode are disjoint, and constraints_used names constraint identifiers of that mode only",
        "unconstrained_modes": [{
            "mode": SAGITTA_MODE,
            "description": "sagitta-like deformation: plane i displaced along the bending direction by d_i = A ((z_i - 175)^2 - 13125 mm^2) "
                           "(fixture 7004), a curvature offset; q/p is biased equally for both charges while the track chi2/ndf is essentially "
                           "unchanged",
            "witness": "T12 stage 6 reprocessing of fixture 7004 against 7003 (t12_degeneracy.py witness; CAI-T07-4's fixture reused inside "
                       "T12, R31)",
            "constraining_information": [
                {"id": "constraint.vertex-or-beam", "text": "a vertex or beam constraint (R37 names it as constraining the T07 mode)"},
                {"id": "constraint.cosmic-or-halo-halves", "text": "cosmic-ray or halo tracks fitted as two independent halves"},
                {"id": "constraint.field-reversal", "text": "field-reversal or detector-inversion running"}],
            "independent_observables": [
                {"id": "observable.resonance-mass-symmetry", "text": "a resonance mass versus charge, direction and momentum"},
                {"id": "observable.electron-positron-e-over-p", "text": "electron and positron E/p"},
                {"id": "observable.independent-subdetectors", "text": "comparison of independent subdetectors measuring the same track"}],
            "constraints_used": [],
            "identifiable_combinations": ["charge-symmetric quantities insensitive to a curvature offset (at first order)"]}],
        "not_satisfying_a37": ["the placeholder convergence and unconstrained-mode checks of the T12 loop fixture (stage 1)",
                               "convergence of a fit, or an unchanged track chi2/ndf", "closure on a same-type holdout"],
    }


def _card_items(value) -> bool:
    return isinstance(value, list) and all(isinstance(v, dict) and set(v) == {"id", "text"} and isinstance(v["id"], str) and v["id"]
                                           and isinstance(v["text"], str) and v["text"] for v in value)


def card_check(card) -> tuple:
    """The rules of timing_recipe/method_card.py on a t12-method-card/1, and the sagitta-like mode listed: ("pass", None) or ("fail",
    reason)."""
    try:
        if not isinstance(card, dict) or card.get("format") != CARD_FORMAT or not isinstance(card.get("unconstrained_modes"), list) \
                or not card["unconstrained_modes"]:
            return "fail", f"not a {CARD_FORMAT} card with its unconstrained modes"
        seen = set()
        for mode in card["unconstrained_modes"]:
            if not isinstance(mode, dict) or set(mode) != CARD_MODE_KEYS:
                return "fail", "each mode has exactly the keys " + ", ".join(sorted(CARD_MODE_KEYS))
            name = mode["mode"]
            if not isinstance(name, str) or not name or name in seen:
                return "fail", "each mode has a distinct name"
            seen.add(name)
            if not isinstance(mode["witness"], str) or not mode["witness"]:
                return "fail", f"{name} names no witness"
            if not _card_items(mode["constraining_information"]) or not _card_items(mode["independent_observables"]):
                return "fail", f"{name}: constraining information and observables are lists of {{id, text}}"
            if not mode["constraining_information"]:
                return "fail", f"{name} names no external information that constrains it (section 9.6, A37)"
            if not mode["independent_observables"]:
                return "fail", f"{name} names no independent observable that can confirm it (section 9.6)"
            constraints = [item["id"] for item in mode["constraining_information"]]
            observables = [item["id"] for item in mode["independent_observables"]]
            if len(set(constraints)) != len(constraints) or len(set(observables)) != len(observables):
                return "fail", f"{name}: an item identifier is listed twice"
            if set(constraints) & set(observables):
                return "fail", f"{name}: {sorted(set(constraints) & set(observables))} constrain the mode and cannot be its validation"
            if set(mode["constraints_used"]) & set(observables):
                return "fail", f"{name}: a constraint used in the derivation cannot be its independent validation"
            if set(mode["constraints_used"]) - set(constraints):
                return "fail", f"{name}: constraints_used names items that are not this mode's constraints"
        sagitta = [m for m in card["unconstrained_modes"] if m["mode"] == SAGITTA_MODE]
        if not sagitta or "sagitta-like deformation" not in sagitta[0]["description"]:
            return "fail", f"the card does not list {SAGITTA_MODE} (sagitta-like deformation)"
        if not all(any(words in item for item in card.get("not_satisfying_a37", [])) for words in NOT_SATISFYING):
            return "fail", "not_satisfying_a37 must name the loop placeholders, convergence and same-type holdouts"
        return "pass", None
    except (TypeError, KeyError, AttributeError) as error:
        return "fail", f"malformed card: {error}"


# ================================================================ T12-19: the two checks of the witness step (fixed by digest)

def weak_mode_check(witness, k, n_sigma):
    cells = witness["cells"]
    held = len(cells) == 8 and all(c["ratio"] >= k and c["ratio_stated"] >= k and abs(c["chi2_change"]) <= n_sigma * c["chi2_se"]
                                   for c in cells.values()) and abs(witness["overall_chi2_change"]) <= n_sigma * witness["overall_chi2_se"]
    return "pass" if held else "fail"


def method_card_check(witness):
    return card_check(witness["card"])[0]


CRITERIA = {"weak-mode": {"k": K_WEAK, "n_se": WEAK_N_SIGMA}, "card": {"format": CARD_FORMAT, "mode": SAGITTA_MODE}}
CHECKS = {"weak-mode": weak_mode_check, "card": method_card_check}


def check_digests() -> dict:
    """(check digest, criterion digest): the SHA-256 of the check function's source and of its criterion (stage 1's form)."""
    return {name: (canonical_sha256({"source": inspect.getsource(function)}), canonical_sha256(CRITERIA[name]))
            for name, function in CHECKS.items()}


def witness_contract() -> dict:
    digests = check_digests()
    step = dv.StepSpec
    steps = {"nominal-alignment": step(program="t12.nominal-alignment/1")}
    for name, (fixture, _) in FIXTURES.items():
        steps[name] = step(program=f"t12.cai-generate/1 --fixture {fixture}")
    for name, generate in REFITS.items():
        steps[name] = step(program="t12.cai-refit/1", upstream=(generate, "nominal-alignment"))
    steps["witness"] = step(program="t12.weak-mode-witness/1", upstream=("refit-7004", "refit-7003"), checked=True,
                            required=frozenset({digests["weak-mode"], digests["card"]}))
    return {"steps": steps, "deliverables": {"weak-mode-witness": dv.Deliverable(step="witness", target="T2")}, "families": {},
            "samples": {}, "budget": None}


# ================================================================ T12-19: executors (the native programs, or toys for the plumbing)

class ToyExecutor:
    """Gaussian toys of the two fits' outputs (weak_mode_toys of T07's test: a 5 sigma bias, no chi2 change): the plumbing only."""

    kind = "toy"
    identity = {"driver_sha256": None, "generator_sha256": None}

    def __init__(self, seed: int = 61):
        deformed, clean = t07.weak_mode_toys(t07.weak_mode_design(), t07.SAGITTA_BIAS_IN_SIGMA, 0.0, t07.CAI_EVENTS, seed)
        self._arrays = {"cai-sagitta": deformed, "cai-clean": clean}

    def arrays(self, fixture: str) -> dict:
        return self._arrays[fixture]

    def native_identity(self) -> dict:
        return dict(self.identity)

    def geometry_id(self) -> str:
        return alignment_payload.nominal_geometry_id()

    def generate(self, fixture: str, fixture_id: int) -> tuple:
        return {"fixture_id": fixture_id, "block": t07.CAI_BLOCK, "strata": list(t07.CAI_STRATA), "events": t07.CAI_EVENTS, "files": {}}, None

    def refit(self, fixture_doc: dict, values) -> dict:
        arrays = self._arrays[fixture_doc["fixture"]]
        return dict(arrays, failed=[], tracks=int(arrays["charge"].size), alignment_header=[None] * len(t07.CAI_STRATA))


class NativeExecutor:
    """The frozen generator and driver, run exactly as CaiFiles in test_acts_cai_refit.py runs them (block 1, strata 0-3, 3000 events,
    hit sets from truth with the truth q/p assumed, field 1 T, nominal geometry, no payload, no vertex or beam constraint)."""

    kind = "native"

    def __init__(self, build: Path, work: Path):
        self.driver, self.generator, self.work = Path(build) / DRIVER, Path(build) / GENERATOR, Path(work)

    def native_identity(self) -> dict:
        """Hashed afresh at every call, so at every native step and every cache lookup (fix round 1, m4)."""
        return {"driver_sha256": file_sha256(self.driver), "generator_sha256": file_sha256(self.generator)}

    def geometry_id(self) -> str:
        return t07.run_program([self.driver, "geometry-id"]).stdout.strip()

    def generate(self, fixture: str, fixture_id: int) -> tuple:
        files, values, headers, counts = {}, {}, [], []
        for stratum in t07.CAI_STRATA:
            data_file, truth = self.work / f"{fixture}-{stratum}.t07data", self.work / f"{fixture}-{stratum}.t07truth"
            t07.run_program([self.generator, "generate", "--fixture", fixture, "--block", t07.CAI_BLOCK, "--stratum", stratum, "--first-event", 0,
                             "--count", t07.CAI_EVENTS, "--data-file", data_file, "--truth-file", truth])
            header = t07.truth_files.read_truth_header(truth)
            headers.append((header["fixture_id"], header["block"], header["stratum"]))
            hit_sets, charge = [], {}
            for ordinal, event in enumerate(t07.truth_files.iter_truth_events(truth)):
                (track,) = event["tracks"]
                hit_sets.append((f"event-{ordinal}", ordinal, float(track["q_over_p"]), [int(key) for key in track["hit_keys"]]))
                charge[f"event-{ordinal}"] = int(track["charge"])
            counts.append(len(hit_sets))
            files[str(stratum)] = {"data_sha256": file_sha256(data_file), "truth_sha256": file_sha256(truth)}
            values[stratum] = {"data_file": data_file, "hit_sets": hit_sets, "charge": charge,
                               "true_q_over_p": {key: q_over_p for key, _, q_over_p, _ in hit_sets}}
        ids, blocks = sorted({h[0] for h in headers}), sorted({h[1] for h in headers})
        fields = {"fixture_id": ids[0] if len(ids) == 1 else ids, "block": blocks[0] if len(blocks) == 1 else blocks,
                  "strata": [h[2] for h in headers], "events": counts[0] if len(set(counts)) == 1 else counts, "files": files}
        return fields, values

    def refit(self, fixture_doc: dict, values) -> dict:
        columns = {name: [] for name in ("charge", "u_plane_one", "residual", "variance", "chi2_per_ndf")}
        failed, tracks, headers = [], 0, []
        for stratum in t07.CAI_STRATA:
            entry = values[stratum]
            if file_sha256(entry["data_file"]) != fixture_doc["files"][str(stratum)]["data_sha256"]:
                raise RuntimeError(f"the data file of stratum {stratum} is not the one the generate step recorded")
            name = f"{fixture_doc['fixture']}-{stratum}-refit"
            hit_sets_file, product = self.work / f"{name}.hitsets", self.work / f"{name}.product"
            hit_sets_file.write_text(t07.fixture_files.hit_sets_text(t07.fixture_files.file_sha256(entry["data_file"]), entry["hit_sets"]),
                                     encoding="utf-8")
            t07.run_program([self.driver, "refit", "--data-file", entry["data_file"], "--hit-sets", hit_sets_file, "--field-tesla",
                             t07.FIELD_TESLA, "--product-id", name, "--product-file", product])
            document = t07.native_product.parse_product(product.read_text(encoding="utf-8"))
            product.unlink()
            hit_sets_file.unlink()
            arrays = t07.fit_arrays(document, types.SimpleNamespace(true_q_over_p=entry["true_q_over_p"], charge=entry["charge"]))
            for key in columns:
                columns[key].append(arrays[key])
            failed += list(arrays["failed"])
            tracks += len(arrays["keys"])
            headers.append(arrays["payload"])      # the native header's alignment_payload: none, no payload argument (fix round 1, m3)
        return dict({key: numpy.concatenate(parts) for key, parts in columns.items()}, failed=failed, tracks=tracks, alignment_header=headers)


# ================================================================ T12-19: the reprocessing

def parse_t07_record(text: str) -> dict:
    cells = {}
    for match in CELL_LINE.finditer(text):
        charge, bending_bin, deformed, clean, ratio, stated, chi2, se = match.groups()
        cells[f"{int(charge):+d}/{int(bending_bin)}"] = {"tracks": [int(deformed), int(clean)], "ratio": float(ratio),
                                                          "ratio_stated": float(stated), "chi2_change": float(chi2), "chi2_se": float(se)}
    return {"job": T07_JOB, "sha256": sha256_hex(text.encode("utf-8")), "item": "CAI-T07-4", "cells": cells,
            "zero_payload_equal": ZERO_PAYLOAD_LINE in text}


def nominal_sidecar(text: str) -> dict:
    """The R32 sidecar of the zero payload. t07_alignment_payload.payload_sidecar lists only the moved degrees of freedom, so a zero
    payload's sidecar has no alignment section and the R32 reader refuses it (conditions.alignment_incomplete); here the section lists
    every plane's parameters of the parametrization, all at nominal, and the identity is sealed again (a finding, not a T07 change)."""
    sidecar = alignment_payload.payload_sidecar(text, ALIGNMENT_TAG, "nominal geometry: the zero payload, no plane moved (T12 stage 6)")
    if "alignment" not in sidecar:
        count = next(int(line.split()[1]) for line in alignment_payload.nominal_geometry_text().splitlines() if line.startswith("planes "))
        planes = list(range(1, count + 1))           # from the nominal geometry text (fix round 1, n2)
        sidecar["alignment"] = {"degrees_of_freedom": [{"structure": f"plane-{plane}", "parameters": list(alignment_payload.PLANE_PARAMETERS),
                                                        "frame": "local", "level": "sensor"} for plane in planes]}
        sidecar["payload_id"] = payload_identity(sidecar)
    return sidecar


class Reprocessing:
    """One run of the witness contract on a fresh in-memory fact log."""

    def __init__(self, executor, plant=None, t07_record=None):
        if plant is not None and plant not in WITNESS_PLANTS:
            raise ValueError(f"unknown plant {plant!r}")
        self.executor, self.plant, self.t07_record = executor, plant, t07_record
        self.spec = witness_contract()
        self.log = dv.Log()
        self.log.append("session", "C", mode="M1")
        self.log.append("contract", "agent", spec=self.spec)
        self.card = method_card()
        mode = self.card["unconstrained_modes"][0]
        if plant == "card-without-constraint":
            mode["constraining_information"] = []
        elif plant == "constraint-as-validation":
            mode["independent_observables"].append(copy.deepcopy(mode["constraining_information"][0]))
        self.store, self.outputs, self.consumed, self.computed, self.identity, self.order = {}, {}, {}, {}, {}, []
        self.attempts, self.cache, self.checks, self.published, self.refused, self.native = {}, [], {}, {}, {}, {}
        self.admission_refused = None

    def __deepcopy__(self, memo):
        memo[id(self.executor)] = self.executor          # a probe never copies the executor (it holds the native results)
        clone = object.__new__(Reprocessing)
        memo[id(self)] = clone
        for key, value in self.__dict__.items():
            setattr(clone, key, copy.deepcopy(value, memo))
        return clone

    def attempt(self, name: str) -> str:
        self.attempts[name] = self.attempts.get(name, 0) + 1
        return f"{name}:{self.attempts[name]}"

    def cache_lookup(self, step: str) -> list:
        """Section 9.8: every cached product of the same recipe (t12.cai-refit/1) is asked whether its data input is this step's and
        what reuse_decision says with the payload resolved afresh, and whether the native identity read now is the one the cached step
        recorded (fix round 1, m4). A hit needs all three; the plant reuse-across-data ignores the data."""
        current_data = dv.provisional_input(self.log, REFITS[step])
        payload = self.store[dv.provisional_input(self.log, "nominal-alignment")]["doc"]
        hits = []
        for other in REFITS:
            if other not in self.outputs:
                continue
            same_input = self.consumed[other].get(REFITS[other]) == current_data
            same_native = self.native.get(other) == self.executor.native_identity()
            decision = reuse_decision(self.store[self.outputs[other]]["doc"], {"alignment": payload})
            hit = decision["reuse"] and same_native and (same_input or self.plant == "reuse-across-data")
            entry = {"for": step, "cached": other, "same_input": same_input, "conditions_reuse": decision["reuse"], "same_native": same_native,
                     "hit": hit, "acted": None}
            self.cache.append(entry)
            if hit:
                hits.append((entry, self.outputs[other]))
        return hits

    def run_step(self, step: str) -> str:
        """A refit first asks the cache; a hit is acted on only through dv.admit(reuse_source=...), and a refused reuse falls back to a
        computation (stage 1's rule)."""
        if step in REFITS:
            for entry, source in self.cache_lookup(step):
                attempt = self.attempt(step)
                try:
                    intent = dv.admit(self.log, self.log.head, attempt, step, cost=0.0, reuse_source=source)
                except dv.Admission as refusal:
                    entry["acted"] = str(refusal)
                    continue
                entry["acted"] = "reused"
                self.outputs[step], self.consumed[step], self.identity[step] = source, dict(intent.get("inputs")), intent.get("identity")
                return source
        attempt = self.attempt(step)
        intent = dv.admit(self.log, self.log.head, attempt, step, cost=0.0)
        consumed = dict(intent.get("inputs"))
        doc, values = self.produce(step, consumed)
        digest = dv.digest_of(doc)
        self.store.setdefault(digest, {"doc": doc, "values": values, "step": step})
        self.log.append("receipt", "adapter", attempt=attempt, end="success", termination="confirmed", outputs=(digest,))
        self.outputs[step], self.consumed[step], self.identity[step] = digest, consumed, intent.get("identity")
        self.computed[step] = self.computed.get(step, 0) + 1
        self.order.append(step)
        return digest

    def produce(self, step: str, consumed: dict):
        if step == "nominal-alignment":
            text = alignment_payload.encode_payload({}, self.executor.geometry_id(), "nominal")
            return nominal_sidecar(text), {"text": text}
        if step in FIXTURES:
            fixture, fixture_id = FIXTURES[step]
            fields, values = self.executor.generate(fixture, fixture_id)
            self.native[step] = self.executor.native_identity()
            return {"schema": "t12-cai-fixture/1", "fixture": fixture, **fields, "native": self.native[step]}, values
        if step in REFITS:
            generated = self.store[consumed[REFITS[step]]]
            payload = self.store[consumed["nominal-alignment"]]["doc"]
            arrays = self.executor.refit(generated["doc"], generated["values"])
            self.native[step] = self.executor.native_identity()
            content = b"".join(numpy.ascontiguousarray(arrays[key], dtype=float).tobytes()
                               for key in ("charge", "u_plane_one", "residual", "variance", "chi2_per_ndf"))
            doc = product_document(product_id=f"product.t12.{step}", conditions_used=[used_payload(payload, slot="alignment")],
                                   native={"type": "t12::CaiRefitArrays", "location": "sha256:" + sha256_hex(content)})
            return doc, arrays
        clean = self.store[consumed["refit-7003"]]["values"]
        deformed = clean if self.plant == "no-deformation" else self.store[consumed["refit-7004"]]["values"]
        if self.plant == "visible-chi2":
            deformed = dict(deformed, chi2_per_ndf=deformed["chi2_per_ndf"] + VISIBLE_CHI2)
        verdict = t07.weak_mode_self_check(deformed, clean, K_WEAK, WEAK_N_SIGMA)
        cells = {f"{charge:+d}/{bending_bin}": dict(cell) for (charge, bending_bin), cell in verdict["cells"].items()}
        judge = {"result": "pass" if abs(verdict["overall_chi2_change"]) <= WEAK_N_SIGMA * verdict["overall_chi2_se"] else "fail",
                 "chi2_change": verdict["overall_chi2_change"], "chi2_se": verdict["overall_chi2_se"], "n_se": WEAK_N_SIGMA,
                 "form": "the change in mean chi2/ndf over all tracks within n se (a 'residuals converged' check)"}
        doc = _json({"schema": "t12-weak-mode-witness/1", "cells": cells, "most": f"{verdict['most'][0]:+d}/{verdict['most'][1]}",
                     "overall_chi2_change": verdict["overall_chi2_change"], "overall_chi2_se": verdict["overall_chi2_se"],
                     "defects": verdict["defects"], "chi2_judge": judge, "card": self.card, "thresholds": {"k": K_WEAK, "n_se": WEAK_N_SIGMA}})
        return doc, None

    def run_check(self, name: str, target: str) -> dict:
        chk, crit = check_digests()[name]
        attempt = self.attempt(f"check-{name}")
        dv.admit(self.log, self.log.head, attempt, "__check__", cost=0.0, check=(chk, crit, target))
        witness = self.store[target]["doc"]
        result = weak_mode_check(witness, K_WEAK, WEAK_N_SIGMA) if name == "weak-mode" else method_card_check(witness)
        self.log.append_batch([
            ("receipt", "adapter", dict(attempt=attempt, end="success", termination="confirmed", outputs=())),
            ("check_result", "adapter", dict(target=target, check=chk, criteria=crit, check_attempt=attempt, result=result))])
        outcome = {"result": result}
        if name == "card":
            outcome["reason"] = card_check(witness["card"])[1]
        return outcome

    def execute(self) -> dict:
        try:
            for step in ORDER:
                self.run_step(step)
            witness = self.outputs["witness"]
            for name in ("weak-mode", "card"):
                self.checks[name] = self.run_check(name, witness)
        except dv.Admission as refusal:        # the control layer refused a step: the run stops there, and the record says so
            self.admission_refused = str(refusal)
        for did in self.spec["deliverables"]:
            try:
                self.published[did] = dv.publish(self.log, self.log.head, did).get("digest")
            except dv.Admission as refusal:
                self.refused[did] = str(refusal)
        return self.record()

    def probes(self) -> dict:
        """On copies of the log, so the record's own history is untouched (stage 1's form)."""
        found = {}
        if "refit-7004" in self.outputs and "refit-7003" in self.outputs:
            clone = copy.deepcopy(self)
            before = len(clone.cache)
            try:
                clone.run_step("refit-7004")
                outcome = None
            except dv.Admission as refusal:
                outcome = str(refusal)
            own = [d for d in clone.cache[before:] if d["cached"] == "refit-7004"]
            reused = list(clone.log.of("reuse"))
            found["reuse_control"] = {"decision": own[0] if own else {"hit": False, "acted": None},
                                      "source": reused[-1].get("source") if reused else None,
                                      "state": dv.exec_status(clone.log, reused[-1].get("attempt")) if reused else (outcome or "not reused")}
            clone = copy.deepcopy(self)
            try:
                dv.admit(clone.log, clone.log.head, clone.attempt("refit-7004"), "refit-7004", cost=0.0, reuse_source=self.outputs["refit-7003"])
                found["reuse_across_steps"] = "admitted"
            except dv.Admission as refusal:
                found["reuse_across_steps"] = str(refusal)
        return found

    def record(self) -> dict:
        steps = {}
        for step, digest in self.outputs.items():
            steps[step] = {"artifact": digest, "label": dv.label(self.log, digest), "consumed": self.consumed[step],
                           "computed": self.computed.get(step, 0), "identity": self.identity[step]}
            if step in NATIVE_STEPS:
                steps[step]["native"] = self.native.get(step)
        fixtures = {step: {key: value for key, value in self.store[self.outputs[step]]["doc"].items() if key != "schema"}
                    for step in FIXTURES if step in self.outputs}
        payload = self.store[self.outputs["nominal-alignment"]]["doc"] if "nominal-alignment" in self.outputs else None
        products = {}
        for step in REFITS:
            if step in self.outputs:
                entry = self.store[self.outputs[step]]
                products[step] = {"conditions_used": entry["doc"]["conditions_used"], "native": entry["doc"]["native"],
                                  "check_used_errors": [f.code for f in check_used(entry["doc"], [payload]).errors],
                                  "failed": list(entry["values"]["failed"]), "tracks": int(entry["values"]["tracks"]),
                                  "alignment_header": list(entry["values"]["alignment_header"]), "applied": APPLIED,
                                  "nominal_equivalence": ZERO_PAYLOAD_EVIDENCE}
        witness = self.store[self.outputs["witness"]]["doc"] if "witness" in self.outputs else {}
        geometry = payload["derived_against"]["geometry_id"] if payload else None
        return _json({"schema": "t12-weak-mode-witness-run/1", "executor": self.executor.kind, "plant": self.plant,
                      "claims": dict(WITNESS_CLAIMS), "contract_sha256": dv.digest_of(task_record.encode_contract(self.spec)),
                      "derivation": dv.DERIVATION_VERSION, "check_digests": check_digests(), "facts": self.log.head,
                      "native": dict(self.executor.native_identity(), geometry_id=geometry),
                      "order": self.order, "steps": steps, "payload": payload, "fixtures": fixtures, "products": products,
                      "witness": {key: witness.get(key) for key in ("cells", "most", "overall_chi2_change", "overall_chi2_se", "defects")},
                      "chi2_judge": witness.get("chi2_judge"), "card": witness.get("card"), "checks": self.checks, "cache": self.cache,
                      "published": self.published, "publish_refused": self.refused, "admission_refused": self.admission_refused,
                      "t07_record": self.t07_record,
                      "tolerances": {"k": K_WEAK, "n_se": WEAK_N_SIGMA, "ratio": RATIO_PRECISION, "chi2": CHI2_PRECISION},
                      **self.probes()})


# ================================================================ T12-19: the assessment (W1-W8)

def _cells_hold(cells) -> bool:
    return len(cells) == 8 and all(c["ratio"] >= K_WEAK and c["ratio_stated"] >= K_WEAK and abs(c["chi2_change"]) <= WEAK_N_SIGMA * c["chi2_se"]
                                   for c in cells.values())


def _reproduces_t07(rec) -> bool:
    record, cells = rec["t07_record"], rec["witness"]["cells"]
    if record["sha256"] != T07_RECORD_SHA256 or record["zero_payload_equal"] is not True or sorted(record["cells"]) != sorted(cells) \
            or len(cells) != 8:
        return False
    return all(cells[key]["tracks"] == want["tracks"] and abs(cells[key]["ratio"] - want["ratio"]) <= RATIO_PRECISION
               and abs(cells[key]["ratio_stated"] - want["ratio_stated"]) <= RATIO_PRECISION
               and abs(cells[key]["chi2_change"] - want["chi2_change"]) <= CHI2_PRECISION
               and abs(cells[key]["chi2_se"] - want["chi2_se"]) <= CHI2_PRECISION for key, want in record["cells"].items())


def _records_hold(rec) -> bool:
    payload = rec["payload"]
    expected_use = [{"slot": "alignment", "tag": payload["tag"], "payload_id": payload["payload_id"], "origin": "nominal", "round": None}]
    fixtures_ok = all((rec["fixtures"][step]["fixture_id"], rec["fixtures"][step]["block"], rec["fixtures"][step]["strata"],
                       rec["fixtures"][step]["events"]) == (fixture_id, t07.CAI_BLOCK, list(t07.CAI_STRATA), t07.CAI_EVENTS)
                      for step, (_, fixture_id) in FIXTURES.items())
    products_ok = all(rec["products"][step]["conditions_used"] == expected_use and rec["products"][step]["check_used_errors"] == []
                      and rec["products"][step]["failed"] == [] and rec["products"][step]["tracks"] == len(t07.CAI_STRATA) * t07.CAI_EVENTS
                      and rec["products"][step]["alignment_header"] == [None] * len(t07.CAI_STRATA) and rec["products"][step]["applied"] == APPLIED
                      for step in REFITS)
    return rec["order"] == list(ORDER) and set(rec["steps"]) == set(ORDER) and all(s["computed"] == 1 for s in rec["steps"].values()) \
        and payload["origin"] == "nominal" and payload["payload_id"] == payload_identity(payload) and fixtures_ok and products_ok \
        and rec["steps"]["refit-7003"]["consumed"]["nominal-alignment"] == rec["steps"]["refit-7004"]["consumed"]["nominal-alignment"] \
        and rec["steps"]["refit-7003"]["consumed"]["generate-7003"] != rec["steps"]["refit-7004"]["consumed"]["generate-7004"]


def assess_witness(rec) -> list:
    """The W expectations (t12-stage-plan.md, Stage 6) that do not hold. A missing field fails its expectation."""
    native = {"driver_sha256": DRIVER_SHA256, "generator_sha256": GENERATOR_SHA256}

    def sagitta_constraints():
        return [i["id"] for m in rec["card"]["unconstrained_modes"] if m["mode"] == SAGITTA_MODE for i in m["constraining_information"]]

    rules = {
        "W1": lambda: {k: rec["native"][k] for k in native} == native
        and rec["native"]["geometry_id"] == rec["payload"]["derived_against"]["geometry_id"] == alignment_payload.nominal_geometry_id()
        and all(rec["steps"][step]["native"] == native for step in NATIVE_STEPS),
        "W2": lambda: _records_hold(rec),
        "W3": lambda: rec["cache"] == [{"for": "refit-7004", "cached": "refit-7003", "same_input": False, "conditions_reuse": True,
                                        "same_native": True, "hit": False, "acted": None}]
        and rec["reuse_control"]["decision"]["hit"] and rec["reuse_control"]["decision"]["acted"] == "reused"
        and rec["reuse_control"]["state"] == "reused" and rec["reuse_control"]["source"] == rec["steps"]["refit-7004"]["artifact"]
        and "reuse source is not a usable, current output" in rec["reuse_across_steps"],
        "W4": lambda: _cells_hold(rec["witness"]["cells"])
        and abs(rec["witness"]["overall_chi2_change"]) <= WEAK_N_SIGMA * rec["witness"]["overall_chi2_se"],
        "W5": lambda: _reproduces_t07(rec),
        "W6": lambda: rec["chi2_judge"]["result"] == "pass" and abs(rec["chi2_judge"]["chi2_change"]) <= WEAK_N_SIGMA * rec["chi2_judge"]["chi2_se"]
        and len(rec["witness"]["cells"]) == 8 and all(c["ratio"] >= K_WEAK for c in rec["witness"]["cells"].values()),
        "W7": lambda: card_check(rec["card"]) == ("pass", None) and rec["checks"]["card"]["result"] == "pass"
        and "constraint.vertex-or-beam" in sagitta_constraints() and all(m["constraints_used"] == [] for m in rec["card"]["unconstrained_modes"]),
        "W8": lambda: {s: v["label"] for s, v in rec["steps"].items()} == {s: "ok" for s in ORDER}
        and rec["published"] == {"weak-mode-witness": rec["steps"]["witness"]["artifact"]} and rec["publish_refused"] == {}
        and rec["claims"] == WITNESS_CLAIMS,
    }
    return _failed(rules)


# ================================================================ command line

def _emit(status: str, **fields) -> int:
    print(json.dumps({"status": status, **fields}, sort_keys=True))
    return exit_code(status)


def write_record(path: Path, content: bytes) -> None:
    with open(path, "xb") as handle:
        handle.write(content)


def _finish(rec, failed, out: Path, **fields) -> int:
    rec["assessment"] = {"failed": failed}
    content = (json.dumps(rec, sort_keys=True, indent=1) + "\n").encode()
    try:
        write_record(out, content)
    except OSError as error:   # the record was not written: incomplete, never a negative reading
        return _emit("incomplete", reason=f"the record could not be written: {type(error).__name__}: {error}")
    return _emit("ok" if not failed else "failed", failed=failed, out=str(out), sha256=sha256_hex(content), **fields)


def _witness_inputs(args) -> str | None:
    """The refusals before any step (rejected): a reason, or None."""
    build, work, record = Path(args.build), Path(args.work), Path(args.t07_record)
    if not build.is_dir() or not (build / DRIVER).is_file() or not (build / GENERATOR).is_file():
        return f"{build} holds no {DRIVER} and {GENERATOR}"
    for name, pinned in ((DRIVER, DRIVER_SHA256), (GENERATOR, GENERATOR_SHA256)):
        got = file_sha256(build / name)
        if got != pinned:
            return f"{name} has sha256 {got}, not the pinned {pinned}"
    if not record.is_file() or file_sha256(record) != T07_RECORD_SHA256:
        return f"{record} is not T07's record of CAI-T07-4 (job {T07_JOB}, SHA-256 {T07_RECORD_SHA256})"
    if not work.is_dir() or any(work.iterdir()):
        return f"{work} is not an empty folder"
    return None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    gxe = sub.add_parser("gxe", help="the g x E degeneracy (T12-18)")
    gxe.add_argument("--plant")
    gxe.add_argument("--out", required=True, type=Path)
    witness = sub.add_parser("witness", help="the weak-mode witness: 7004 against 7003 reprocessed inside T12 (T12-19)")
    witness.add_argument("--build", required=True)
    witness.add_argument("--t07-record", required=True)
    witness.add_argument("--work", required=True)
    witness.add_argument("--plant")
    witness.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    plants = GXE_PLANTS if args.operation == "gxe" else WITNESS_PLANTS
    if args.plant is not None and args.plant not in plants:
        return _emit("rejected", reason=f"unknown plant {args.plant!r}")
    if args.out.exists() or not args.out.parent.is_dir():
        return _emit("rejected", reason=f"{args.out} exists or its folder does not: a record is never overwritten")
    if args.operation == "gxe":
        try:
            rec = gxe_run(args.plant)
            failed = assess_gxe(rec)
        except Exception as error:  # noqa: BLE001 - any crash is "incomplete", never a negative reading
            return _emit("incomplete", reason=f"{type(error).__name__}: {error}")
        return _finish(rec, failed, args.out, operation="gxe", plant=args.plant)
    reason = _witness_inputs(args)
    if reason:
        return _emit("rejected", reason=reason)
    try:
        t07_record = parse_t07_record(Path(args.t07_record).read_text(encoding="utf-8"))
        rec = Reprocessing(NativeExecutor(Path(args.build), Path(args.work)), args.plant, t07_record).execute()
        failed = assess_witness(rec)
    except Exception as error:  # noqa: BLE001 - a native program that fails, or any crash, is "incomplete"
        return _emit("incomplete", reason=f"{type(error).__name__}: {str(error)[:2000]}")
    return _finish(rec, failed, args.out, operation="witness", plant=args.plant)


if __name__ == "__main__":
    sys.exit(main())
