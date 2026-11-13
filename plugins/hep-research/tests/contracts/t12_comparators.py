#!/usr/bin/env python3
"""T12 stage 4, part A: reproducibility comparators declared per recipe (T12-13; plan v9.2 Section 14.1) and quality before speed
(T12-15; A15, A50; Section 16.1 "quality before speed").

A harness for interface tests on synthetic fixtures; frozen files are read by SHA-256. No quality claim: a comparator's pass says two
products agree within the stated tolerance, nothing about either product's quality. Every rule, tolerance and expectation is fixed in
docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 4"). It lives under tests/ because it imports an adapter's recipe modules
(adapters/destriper/assets/destripe_recipe) and the E6 statistics core (tests/adapters/t04_evaluation_core.py with E2's t07_fake_rate.py),
which an adapter or core/ may not (tools/check_layering.py).

- DECLARATIONS: per recipe, the byte, numerical and statistical forms. Tolerances come only from Freeze A/B and T10's frozen replay
  tolerance; where none is fixed the form is `open` with its open item (OPEN_ITEMS), and its comparator answers `incomplete`, never a pass.
  RULINGS holds the coordinator's rulings a pass depends on; every result under a ruling names it.
- compare_bytes: whole-file byte equality, nothing excluded as metadata; T08 has no recorded byte rerun (OI-11): incomplete.
- compare_numerical: reco.scan.destriper/1 against the frozen records adapters/destriper/assets/t10-replay*.tolerance.json, after T10's own
  derivation checks on the reference product's pointing (fix round 1, I1: kappa and G recomputed by t10_comparator.fixture_numbers; OI-8
  ruling: product against product only on the record's pointing); objects matched by key (pixel index; a baseline by the sorted values of
  its samples), associations compared exactly, values as exact binary fractions.
- compare_statistical: the T07 track finding fake rate per noise bin by F2's rule and tau (t04-values-v4.md section 8.3); the event count must
  match (else failed); a lower rate beyond tau or a changed object count is no pass (OI-10: incomplete).
- fixed_gate, quality_before_speed: Freeze A's common gates (section 6) computed by the E6 core, objects without a result (NaN) counted as
  tail failures (v4 5.1); a timing is sealed to one candidate and released only against that candidate's complete gate record, and only for
  a qualified candidate or a declared working point.

Operation:
  compare --recipe R --form byte|numerical|statistical --reference FILE --candidate FILE --out FILE [--quantity Q]
      Status and exit (core/status.py): passed 0; failed 1; rejected 2 (unknown recipe or form, a form not applicable, unreadable input, an
      output that exists (never overwritten) or a missing folder; nothing written); incomplete 3 (an open tolerance, or the comparator could
      not run).
  declarations
      prints the declarations, open items and rulings as JSON; exit 0.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
DESTRIPER_ASSETS = ROOT / "adapters" / "destriper" / "assets"
for _path in (ROOT, DESTRIPER_ASSETS, DESTRIPER_ASSETS / "fixture_tools", ROOT / "adapters" / "acts-tracking" / "assets" / "fixture_tools"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
from core.status import exit_code  # noqa: E402
from destripe_recipe import product as destripe_product  # noqa: E402
from destripe_recipe import solver as destripe_solver  # noqa: E402
from destripe_recipe import timestream as destripe_timestream  # noqa: E402
import t07_fake_rate as fake_rate  # noqa: E402  (E2's rate rule, section 5.2)
import t10_comparator  # noqa: E402  (T10's replay comparator: its derivation checks, fixture_numbers)
import t10_fixture  # noqa: E402  (the synthetic fixture t10-destripe/1, scoring side)
from tests.adapters import t04_evaluation_core as core  # noqa: E402
from tests.adapters import t07_evaluation_scoring as scoring  # noqa: E402  (E6's T07 scoring: the tail and F2 constants, M1)

# Fix round 1, M2: the frozen codings this harness computes with, by SHA-256 as the evaluation manifest jobs/evaluation/SOURCES.sha256
# pins them (and freeze-b.md for the core). t07_evaluation_scoring.py is pinned at this base only: its bytes differ from the evaluation
# manifest's 6102c2ef... (changed after attempt 1, commit 7a98aeff); only its constants are read here.
FROZEN_MODULES = {
    "tests/adapters/t04_evaluation_core.py": "265eb12426f0e16ce3a0cb0caf9925a816cf3114e5cdf7a80f7638241fce3f6f",
    "adapters/acts-tracking/assets/fixture_tools/t07_fake_rate.py": "4b4aa1addaf252e33091fab7c8487b882f2bb1c6718af7dc0efd24c7dbde5b6d",
}
BASE_PINNED_MODULES = {
    "tests/adapters/t07_evaluation_scoring.py": "32d0adc673b484a2eb7d7fb1caba3e948b4590b67b0559b1644770cbbf57fa4b",
}

CARD = DESTRIPER_ASSETS / "destriper.method-card.json"
DESTRIPER = "reco.scan.destriper/1"
TRACK_FINDING = "reco.track.acts-ckf-planar/1"
FAKE_RATE = "fake rate per noise bin"
RECIPES = (TRACK_FINDING, "reco.vertex.acts-amvf/1", "reco.track.acts-kf-refit/1", "reco.calo.cell-cluster/1", "reco.light.channel-likelihood/1",
           "reco.timing.time-chain/1", DESTRIPER)
FORMS = ("byte", "numerical", "statistical")

# The frozen replay tolerance records (decisions.md, "The user's freeze of T10's replay comparator tolerance", 2026-11-12), by stopping value.
TOLERANCE_RECORDS = {
    1e-10: (DESTRIPER_ASSETS / "t10-replay.tolerance.json", "217a38bc40769da9c750ac347228b120476008b0227f025f4fcbc02ce9d3c35e"),
    1e-13: (DESTRIPER_ASSETS / "t10-replay-noiseless.tolerance.json", "12738ebce579ae83057b69d8dca56cd3a626d5c5afe323863a56275de16da698"),
}
F2_TAU = scoring.STABILITY_TOLERANCE    # t04-values-v4.md section 8.3, tau 0.0025, fixed at Freeze A (E6's constant, M1)
F2_CONFIDENCE = fake_rate.CONFIDENCE    # section 8.3, "the 95 % bounds of section 5.2": E2's rate_rule level (K09's 99 % is attempt 2's)

OPEN_ITEMS = {
    "OI-1": "T07 track finding: no numerical reproducibility tolerance is fixed by Freeze B (freeze-b.md; tolerances are Freeze A's, and Freeze A has none for it)",
    "OI-2": "T07 track finding: every statistical quantity but the fake rate per noise bin (F2) has no frozen tolerance",
    "OI-3": "T07 AMVF: no numerical or statistical reproducibility tolerance is fixed by Freeze B",
    "OI-4": "T07 refit: no numerical or statistical reproducibility tolerance is fixed by Freeze B",
    "OI-5": "T08: no numerical or statistical reproducibility tolerance is fixed by Freeze B",
    "OI-6": ("T09: no numerical or statistical reproducibility tolerance is fixed by Freeze B. The T09 close-out replay tolerance "
             "(decisions.md, review I1: ln L 1e-6, statistic 4e-6, parameters 1e-3 sigma, discrete exact) was offered; the user answered "
             "\"Leave open\" (2026-11-13): it stays open"),
    "OI-7": "T10 timing: no numerical or statistical reproducibility tolerance is fixed (T10's one frozen tolerance is the replay's)",
    "OI-9": ("no recipe document declares `reproducibility` (G03); writing it into a recipe changes a Freeze B item (a return to Freeze B), "
             "so this table is the harness's declaration only"),
    "OI-10": ("T07 track finding fake rate: F2 is one-sided as frozen; as a reproducibility rule a lower candidate rate beyond tau (F2 with "
              "the roles exchanged above tau) or a changed object (track) count has no frozen rule: the answer is incomplete, never passed"),
    "OI-11": "T08: no recorded byte rerun of the recipe's products (t08-closeout.md): the byte form is not declared",
}
RULINGS = {
    "OI-8": ("the coordinator, fix round 1 (2026-11-13): T10's frozen replay tolerance holds for a product against a product of the same "
             "recipe only on the same pointing as the record (t10-destripe/1, seed 20260): each is within kappa x eps of the exact solution, "
             "so they differ by at most 2 kappa eps < tau = safety x kappa x eps; enforced by T10's derivation checks on the reference "
             "product's pointing. The 1e-13 record depends on the pointing only, so it applies to noisy products stopped at 1e-13 too"),
}


def _byte(record: str) -> dict:
    return {"state": "declared", "excluded": [], "record": record,
            "rule": "whole-file byte equality, nothing excluded as non-scientific metadata; same node class (U-W7)"}


def _open(item: str) -> dict:
    return {"state": "open", "open_item": item}


DECLARATIONS = {
    TRACK_FINDING: {"byte": _byte("decisions.md 2026-11-08: outputs byte-equal across jobs 7502411, 7503215, 7512409"), "numerical": _open("OI-1"),
          "statistical": {"state": "declared", "open_item": "OI-2", "quantities": {FAKE_RATE: {
              "rule": "F2: (r_c - r_r) + sqrt((U_c - r_c)^2 + (r_r - L_r)^2) <= tau; one-sided as frozen",
              "tau": F2_TAU, "confidence": F2_CONFIDENCE,
              "source": "t04-values-v4.md section 8.3 (Freeze A, 92f71f56...); r_dev record in Freeze B (ebf2aa0e...)"}}}},
    "reco.vertex.acts-amvf/1": {"byte": _byte("decisions.md 2026-11-08 (job 7512409: finder outputs byte-equal; the vertexer runs in the finder)"),
                                "numerical": _open("OI-3"), "statistical": _open("OI-3")},
    "reco.track.acts-kf-refit/1": {"byte": _byte("t07-closeout.md: the example's recording equal in two live runs (job 7551619)"),
                                   "numerical": _open("OI-4"), "statistical": _open("OI-4")},
    "reco.calo.cell-cluster/1": {"byte": _open("OI-11"), "numerical": _open("OI-5"), "statistical": _open("OI-5")},
    "reco.light.channel-likelihood/1": {"byte": _byte("t09-closeout.md, Reproducibility: products byte-equal across nodes and jobs"),
                                        "numerical": _open("OI-6"), "statistical": _open("OI-6")},
    "reco.timing.time-chain/1": {"byte": _byte("t10-closeout.md, Reproducibility: the stage 1 repeat byte-equal (job 7593003)"),
                                 "numerical": _open("OI-7"), "statistical": _open("OI-7")},
    DESTRIPER: {"byte": _byte("this harness, B1: two solves on one timestream byte-equal; t10-closeout.md: replay values bit-identical (7594892, 7596623)"),
                "numerical": {"state": "declared", "ruling": "OI-8",
                              "records": [{"path": str(path.relative_to(ROOT)), "sha256": sha, "stopping": stopping}
                                          for stopping, (path, sha) in TOLERANCE_RECORDS.items()],
                              "matching": ("pixel by index; baseline by the sorted values of its samples; association: the sorted (value, pixel) "
                                           "pairs of each baseline, exact"),
                              "source": "decisions.md, the user's freeze of T10's replay comparator tolerance (2026-11-12)"},
                "statistical": {"state": "not-applicable", "reason": "one-to-one comparison is possible (Section 14.1)"}},
}


class ComparatorInputError(ValueError):
    """An input the comparator cannot use (rejected, exit 2)."""


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _declaration(recipe: str, form: str) -> dict:
    if recipe not in DECLARATIONS:
        raise ComparatorInputError(f"unknown recipe {recipe!r}; declared: {', '.join(RECIPES)}")
    if form not in FORMS:
        raise ComparatorInputError(f"unknown form {form!r}; forms: {', '.join(FORMS)}")
    declaration = DECLARATIONS[recipe][form]
    if declaration["state"] == "not-applicable":
        raise ComparatorInputError(f"{recipe} has no {form} form: {declaration['reason']}")
    return declaration


def _incomplete(recipe: str, form: str, item: str) -> dict:
    return {"status": "incomplete", "form": form, "recipe": recipe, "open_item": item, "reason": OPEN_ITEMS[item]}


def check_frozen_modules() -> None:
    """M2: refuse to compute with a frozen coding whose bytes are not the pinned ones."""
    for relative, expected in {**FROZEN_MODULES, **BASE_PINNED_MODULES}.items():
        found = _sha256((ROOT / relative).read_bytes())
        if found != expected:
            raise ComparatorInputError(f"{relative} is not the pinned file (SHA-256 {found}, expected {expected})")


# ================================================================ byte (B1-B3)

def compare_bytes(recipe: str, reference: bytes, candidate: bytes) -> dict:
    """Whole-file byte equality. A hash is integrity evidence (Section 14.1); it is reported, and the comparison is of the bytes."""
    declaration = _declaration(recipe, "byte")
    first = None
    if reference != candidate:
        first = next((i for i, (a, b) in enumerate(zip(reference, candidate)) if a != b), min(len(reference), len(candidate)))
    readings = {"first_difference": first, "reference_sha256": _sha256(reference), "candidate_sha256": _sha256(candidate),
                "sizes": [len(reference), len(candidate)]}
    if declaration["state"] == "open":
        return _incomplete(recipe, "byte", declaration["open_item"]) | readings
    return {"status": "passed" if first is None else "failed", "form": "byte", "recipe": recipe, "excluded": list(declaration["excluded"]),
            "record": declaration["record"]} | readings


# ================================================================ numerical (N1-N9)

def _record(stopping: float) -> dict:
    if stopping not in TOLERANCE_RECORDS:
        raise ComparatorInputError(f"stopping value {stopping} is in no frozen tolerance record ({sorted(TOLERANCE_RECORDS)})")
    path, expected = TOLERANCE_RECORDS[stopping]
    try:
        content = Path(path).read_bytes()
    except OSError as exc:
        raise ComparatorInputError(f"the tolerance record {path} cannot be read: {exc.strerror}") from exc
    if _sha256(content) != expected:
        raise ComparatorInputError(f"{Path(path).name} is not the frozen record (SHA-256 {_sha256(content)}, expected {expected})")
    record = json.loads(content)
    if not isinstance(record, dict) or set(record) != t10_comparator.KEYS or record["format"] != "t10-replay-tolerance/1" \
            or record["state"] != "frozen" or record["stopping"] != stopping:
        raise ComparatorInputError(f"{Path(path).name} is not a frozen t10-replay-tolerance/1 record for stopping {stopping}")
    return {"record": Path(path).name, "sha256": expected, "stopping": stopping, "tau_baselines": record["tau_baselines"],
            "tau_map": record["tau_map"], "zero_sum_relative": record["zero_sum_relative"], "safety": record["safety"],
            "kappa": record["kappa"], "map_gain": record["map_gain"]}


def _pointing(document: dict) -> dict:
    """The product's pointing as t10_comparator reads a timestream: one pixel per sample, baseline t // L (checked)."""
    model = document["reconstruction_product"]["scan"]["model"]
    pixels, length = len(document["map"]), document["input"]["baseline_length"]
    pixel = []
    for t, row in enumerate(model["design"]):
        if row[pixels + t // length] != 1:
            raise ComparatorInputError(f"sample {t} is not in baseline {t // length}: the design is not baselines of {length} samples")
        pixel.append(row.index(1))
    return {"pixel": pixel, "baseline_length": length, "pixels": pixels}


def derivation(document: dict, tolerance: dict) -> dict:
    """Fix round 1, I1: T10's record checks (t10_comparator._check_record, without the exact reference) on this product's pointing: kappa and G
    recomputed by fixture_numbers within 0.01 and 1e-4 of the record's; safety at least t10_comparator.MINIMUM_SAFETY; kappa x eps at least
    1e3 rounding units; tau_baselines >= safety kappa eps and tau_map >= safety G kappa eps. Any other pointing is rejected (OI-8 ruling)."""
    kappa, gain = t10_comparator.fixture_numbers(_pointing(document))
    eps, safety = tolerance["stopping"], tolerance["safety"]
    if safety < t10_comparator.MINIMUM_SAFETY:
        raise ComparatorInputError(f"the record's safety {safety} is below {t10_comparator.MINIMUM_SAFETY}")
    if abs(tolerance["kappa"] - kappa) > 0.01 or abs(tolerance["map_gain"] - gain) > 1e-4:
        raise ComparatorInputError(f"the record's kappa {tolerance['kappa']} or G {tolerance['map_gain']} is not this pointing's "
                                   f"({kappa:.4f}, {gain:.5f}): the frozen tolerance holds only on the record's pointing (OI-8 ruling)")
    if kappa * eps < 1e3 * t10_comparator.ROUNDING_UNIT:
        raise ComparatorInputError(f"kappa x eps = {kappa * eps:.3e} is below 1e3 rounding units")
    if tolerance["tau_baselines"] < safety * kappa * eps:
        raise ComparatorInputError(f"tau_baselines {tolerance['tau_baselines']} is below safety x kappa x eps = {safety * kappa * eps:.4e}")
    if tolerance["tau_map"] < safety * gain * kappa * eps:
        raise ComparatorInputError(f"tau_map {tolerance['tau_map']} is below safety x G x kappa x eps = {safety * gain * kappa * eps:.4e}")
    return {"kappa": kappa, "map_gain": gain, "two_kappa_eps": 2 * kappa * eps, "two_gain_kappa_eps": 2 * gain * kappa * eps}


def _objects(document: dict) -> dict:
    """Map values by pixel, and per baseline its key (sorted sample values), association (sorted (value, pixel) pairs) and value."""
    try:
        destripe_product.read(document, DESTRIPER_ASSETS)
    except (destripe_product.ProductError, TypeError, KeyError, AttributeError) as exc:
        raise ComparatorInputError(f"not a readable destriper product: {exc}") from exc
    if document["solver"]["constraint"] != "zero-sum":
        raise ComparatorInputError("the frozen tolerance is relative to zero-sum baselines: a product without the constraint is refused")
    model = document["reconstruction_product"]["scan"]["model"]
    names, design, observation = model["parameters"], model["design"], model["observation"]
    pixels = len(document["map"])
    if len(design) != len(observation) or names[:pixels] != [f"map-{p}" for p in range(pixels)]:
        raise ComparatorInputError("the embedded scan model does not have one design row per observation and the map first")
    samples: dict[int, list] = {}
    for row, value in zip(design, observation):
        ones = [i for i, w in enumerate(row) if w == 1]
        if len(ones) != 2 or ones[0] >= pixels or ones[1] < pixels or any(w not in (0, 1) for w in row):
            raise ComparatorInputError("a design row is not one pixel and one baseline")
        samples.setdefault(ones[1] - pixels, []).append((value, ones[0]))
    baselines = {}
    for index, members in samples.items():
        key = tuple(sorted(value for value, _ in members))
        if key in baselines:
            raise ComparatorInputError(f"two baselines hold the same sample values: the matching rule is ambiguous (baseline {index})")
        baselines[key] = {"association": tuple(sorted(members)), "value": document["baselines"][index]}
    return {"map": dict(enumerate(document["map"])), "baselines": baselines, "stopping": document["solver"]["stopping"],
            "iterations": document["solver"]["iterations"]}


def _squared(pairs) -> Fraction:
    return sum(((Fraction(c) - Fraction(r)) ** 2 for r, c in pairs), Fraction(0))


def compare_numerical(recipe: str, reference: dict, candidate: dict) -> dict:
    declaration = _declaration(recipe, "numerical")
    if declaration["state"] == "open":
        return _incomplete(recipe, "numerical", declaration["open_item"])
    ref, cand = _objects(reference), _objects(candidate)
    if ref["stopping"] != cand["stopping"]:
        raise ComparatorInputError(f"the products stopped at {ref['stopping']} and {cand['stopping']}: the tolerance is fixed per stopping value")
    tolerance = _record(ref["stopping"])
    derived = derivation(reference, tolerance)
    common = sorted(set(ref["baselines"]) & set(cand["baselines"]))
    pixels = sorted(set(ref["map"]) & set(cand["map"]))
    size = sum((Fraction(b["value"]) ** 2 for b in ref["baselines"].values()), Fraction(0))
    d_baselines = _squared((ref["baselines"][k]["value"], cand["baselines"][k]["value"]) for k in common)
    d_map = _squared((ref["map"][p], cand["map"][p]) for p in pixels)
    values = [Fraction(b["value"]) for b in cand["baselines"].values()]
    total, magnitude = sum(values, Fraction(0)), sum((abs(v) for v in values), Fraction(0))
    checks = {
        "objects": set(ref["baselines"]) == set(cand["baselines"]) and set(ref["map"]) == set(cand["map"]),
        "association": all(ref["baselines"][k]["association"] == cand["baselines"][k]["association"] for k in common),
        "baselines": d_baselines <= Fraction(tolerance["tau_baselines"]) ** 2 * size,
        "map": d_map <= Fraction(tolerance["tau_map"]) ** 2 * size,
        "zero_sum": abs(total) <= Fraction(tolerance["zero_sum_relative"]) * magnitude,
    }
    norm = math.sqrt(float(size)) or 1.0
    readings = {"baselines_relative": math.sqrt(float(d_baselines)) / norm, "map_relative": math.sqrt(float(d_map)) / norm,
                "zero_sum": float(total), "sum_abs": float(magnitude), "iterations": [ref["iterations"], cand["iterations"]],
                "unmatched_reference": len(set(ref["baselines"]) - set(cand["baselines"])),
                "unmatched_candidate": len(set(cand["baselines"]) - set(ref["baselines"])),
                "association_differences": sum(ref["baselines"][k]["association"] != cand["baselines"][k]["association"] for k in common)}
    failed = sorted(name for name, ok in checks.items() if not ok)
    return {"status": "failed" if failed else "passed", "form": "numerical", "recipe": recipe, "failed": failed, "checks": checks,
            "tolerance": tolerance, "derivation": derived, "readings": readings, "ruling": declaration["ruling"],
            "statement": ("agreement within the frozen tolerance on a synthetic fixture, under the OI-8 ruling (same pointing as the record, "
                          "checked); a candidate on another pointing shows as an association or object difference; no quality claim")}


# ================================================================ statistical (S1-S6)

def _counts(sample: dict) -> tuple:
    try:
        m = numpy.asarray(sample["objects_per_event"])
        y = numpy.asarray(sample["failures_per_event"])
    except (TypeError, KeyError) as exc:
        raise ComparatorInputError("a sample has objects_per_event and failures_per_event") from exc
    if m.ndim != 1 or m.shape != y.shape or m.dtype.kind not in "iu" or y.dtype.kind not in "iu" or (m < 0).any() or (y < 0).any() \
            or (y > m).any() or m.size < 2 or m.sum() < 1:
        raise ComparatorInputError("per-event integer counts, 0 <= y_e <= m_e, at least 2 events and one object")
    return m.astype(numpy.int64), y.astype(numpy.int64)


def rate_bounds(sample: dict) -> dict:
    """r = k/n and section 5.2's 95 % bounds (E2's rate_rule); k = n gives U = 1 and is refused as a reference (no lower bound)."""
    m, y = _counts(sample)
    n, k, events = int(m.sum()), int(y.sum()), int(m.size)
    if k == n:
        return {"r": 1.0, "upper": 1.0, "lower": None, "events": events, "objects": n, "failures": k}
    found = fake_rate.rate_rule(m, y)
    return {"r": found["r_dev"], "upper": found["u_dev"], "lower": found["l_dev"], "events": events, "objects": n, "failures": k}


def compare_statistical(recipe: str, quantity: str, reference: dict, candidate: dict) -> dict:
    check_frozen_modules()
    declaration = _declaration(recipe, "statistical")
    if declaration["state"] == "open" or quantity not in declaration.get("quantities", {}):
        return _incomplete(recipe, "statistical", declaration["open_item"]) | {"quantity": quantity}
    rule = declaration["quantities"][quantity]
    ref, cand = rate_bounds(reference), rate_bounds(candidate)
    if ref["lower"] is None:
        raise ComparatorInputError("every reference object failed: no lower bound, no F2")
    statistic = (cand["r"] - ref["r"]) + math.sqrt((cand["upper"] - cand["r"]) ** 2 + (ref["r"] - ref["lower"]) ** 2)
    candidate_lower = cand["r"] if cand["lower"] is None else cand["lower"]
    mirrored = (ref["r"] - cand["r"]) + math.sqrt((ref["upper"] - ref["r"]) ** 2 + (cand["r"] - candidate_lower) ** 2)
    checks = {"rate": statistic <= rule["tau"], "events": cand["events"] == ref["events"]}
    failed = sorted(name for name, ok in checks.items() if not ok)
    # OI-10: no frozen rule passes a drop beyond tau or a changed object count; they block a pass (incomplete), never a verdict of their own.
    blocking = sorted(name for name, found in (("lower_rate", mirrored > rule["tau"]), ("objects", cand["objects"] != ref["objects"])) if found)
    status = "failed" if failed else ("incomplete" if blocking else "passed")
    result = {"status": status, "form": "statistical", "recipe": recipe, "quantity": quantity, "failed": failed, "blocking": blocking,
              "checks": checks, "statistic": statistic, "mirrored_statistic": mirrored, "tau": rule["tau"], "confidence": rule["confidence"],
              "reference": ref, "candidate": cand, "readings": {"objects": [ref["objects"], cand["objects"]], "events": [ref["events"], cand["events"]]},
              "open_item": "OI-10" if status == "incomplete" else declaration["open_item"],
              "statement": ("F2's rule (one-sided as frozen); a drop beyond tau (F2 with the roles exchanged) or a changed object count blocks a "
                            "pass (OI-10). A statistical comparator sees an association change only through the rate: an association change "
                            "that leaves the rate unchanged is not visible, which is why Section 14.1 allows this form only where one-to-one "
                            "comparison is impossible. The event count must match: data loss is not excused. No quality claim")}
    if status == "incomplete":
        result["reason"] = OPEN_ITEMS["OI-10"]
    return result


# ================================================================ destriper fixtures (synthetic; the real recipe)

def destriper_fixture(variant: str = "noisy", seed: int = 20260) -> dict:
    return t10_fixture.generate(variant, seed)[0]


def solve_destriper(timestream: dict, product_id: str = "t12-stage4", stopping: float = 1e-10) -> dict:
    """reco.scan.destriper/1 on a timestream, in this process, as destriper.py solve writes it (zero-sum constraint)."""
    raw = (json.dumps(timestream, sort_keys=True, separators=(",", ":")) + "\n").encode()
    stream = destripe_timestream.read(timestream)
    solution = destripe_solver.solve(stream, stopping=stopping)
    built = destripe_product.build(stream, solution, constraint="zero-sum", product_id=product_id, input_sha256=_sha256(raw), card_path=CARD)
    return json.loads(destripe_product.dumps(built))


def dumps_product(document: dict) -> bytes:
    return destripe_product.dumps(document).encode("utf-8")


def _segments(timestream: dict) -> list:
    length = timestream["baseline_length"]
    pairs = list(zip(timestream["pixel"], timestream["value"]))
    return [pairs[i:i + length] for i in range(0, len(pairs), length)]


def _with_segments(timestream: dict, segments: list) -> dict:
    changed = copy.deepcopy(timestream)
    changed["pixel"] = [p for segment in segments for p, _ in segment]
    changed["value"] = [v for segment in segments for _, v in segment]
    return changed


def permute_baselines(timestream: dict, seed: int = 7) -> dict:
    segments = _segments(timestream)
    return _with_segments(timestream, [segments[i] for i in numpy.random.default_rng(seed).permutation(len(segments))])


def reverse_within_baselines(timestream: dict) -> dict:
    return _with_segments(timestream, [segment[::-1] for segment in _segments(timestream)])


def exchange_pixels(timestream: dict, baseline: int = 0) -> dict:
    """Two samples of one baseline exchange pixels; every value stays where it was (an association change)."""
    changed = copy.deepcopy(timestream)
    start = baseline * timestream["baseline_length"]
    pixel = changed["pixel"]
    other = next(start + j for j in range(1, timestream["baseline_length"]) if pixel[start + j] != pixel[start])
    pixel[start], pixel[other] = pixel[other], pixel[start]
    return changed


def drop_baseline(timestream: dict, baseline: int) -> dict:
    segments = _segments(timestream)
    return _with_segments(timestream, segments[:baseline] + segments[baseline + 1:])


def resync_reported(document: dict) -> None:
    """Keep a planted zero-sum product consistent: the embedded reported values are the map, then the baselines."""
    for item, value in zip(document["reconstruction_product"]["scan"]["reported"], document["map"] + document["baselines"]):
        item["value"] = value


def plant_design(document: dict) -> dict:
    """The first sample's design row names the next pixel; every number stays (N5)."""
    planted = copy.deepcopy(document)
    pixels = len(planted["map"])
    row = planted["reconstruction_product"]["scan"]["model"]["design"][0]
    current = row.index(1)
    row[current], row[(current + 1) % pixels] = 0, 1
    return planted


def plant_baselines(document: dict, relative: float) -> dict:
    """Baselines 0 and 1 moved by +delta and -delta, delta = relative x ||a||_2 (zero sum kept, map unchanged) (N6)."""
    planted = copy.deepcopy(document)
    delta = relative * math.sqrt(sum(v * v for v in planted["baselines"]))
    planted["baselines"][0] += delta
    planted["baselines"][1] -= delta
    resync_reported(planted)
    return planted


# ================================================================ quality before speed (Q1-Q8)

ATTEMPT_1 = core.level_of_block(11)   # the attempt-1 level object (95 %, z 1.645), from the core; no event of block 11 is used
TAIL_LIMIT, TAIL_PULL = scoring.TAIL_LIMIT, scoring.TAIL_PULL   # t04-values-v4.md section 6, P(|pull| > 3), L = 1 % (E6's constants, M1)
BOOTSTRAP_TAG = 1215                  # this harness's bootstrap rows: SeedSequence([1215]), never the evaluation's 520
GATE_LABEL = "T12 stage 4 synthetic sample (no evaluation bin)"
GATE_CONSTANTS = {"tolerance": core.TOLERANCE, "precision_cap": core.PRECISION_CAP, "tail_limit": TAIL_LIMIT, "tail_pull": TAIL_PULL,
                  "confidence": ATTEMPT_1.confidence}
PLANTED_EVENTS = 12000


def planted_samples() -> tuple:
    """(baseline, faster variant): 12,000 unit-normal pulls; the variant replaces a fraction (draws < 0.02) by normal(0, 5)."""
    baseline = numpy.random.default_rng(20261115).normal(0.0, 1.0, PLANTED_EVENTS)
    rng = numpy.random.default_rng(20261116)
    variant = rng.normal(0.0, 1.0, PLANTED_EVENTS)
    mask = rng.random(PLANTED_EVENTS) < 0.02
    variant[mask] = rng.normal(0.0, 5.0, int(mask.sum()))
    return baseline, variant


def fixed_gate(pulls) -> dict:
    """Freeze A's common gates (section 6) on one object per event: location and width by the pull test on the objects with a result, the
    tail by the rate test over every object, an object without a result (NaN) counted as a failure (v4 5.1, as E6's
    t07_evaluation_scoring._pull_records; fix round 1, I4); attempt-1 level, through the E6 core's own record functions. The gate takes no
    parameter but the sample."""
    check_frozen_modules()
    values = numpy.asarray(pulls, dtype=float).ravel()
    missing = ~numpy.isfinite(values)
    events = core.EventValues.of([numpy.zeros(0) if gone else numpy.array([v]) for v, gone in zip(values, missing)])
    rows = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence([BOOTSTRAP_TAG]))).integers(
        0, values.size, size=(core.BOOTSTRAP_REPLICATES, values.size))
    centre, width = core._pull_records("T12 fixed gate", GATE_LABEL, events, ATTEMPT_1, rows, True)
    failures = (missing | (numpy.abs(numpy.where(missing, 0.0, values)) > TAIL_PULL)).astype(numpy.int64)
    tail = core._rate_record("T12 fixed gate tail", GATE_LABEL, numpy.ones(values.size, dtype=numpy.int64), failures, TAIL_LIMIT, ATTEMPT_1,
                             None, True, "tail")
    words = [record.result for record in (centre, width, tail)]
    word = "fail" if "fail" in words else ("inconclusive" if "inconclusive" in words else "pass")
    return {"centre": centre, "width": width, "tail": tail, "word": word, "passed": word == "pass", "objects": int(values.size),
            "without_result": int(missing.sum())}


class _GateRecord:
    """A gate record (fix round 2, M3): made only by gate_record, which registers it in _ISSUED; release accepts a record only if this very
    object (identity, not equality) was issued, so a dict, a copy or a look-alike releases nothing."""
    __slots__ = ("candidate", "complete", "word", "passed", "__weakref__")

    def __init__(self, candidate, word: str, passed: bool):
        self.candidate, self.complete, self.word, self.passed = candidate, True, word, passed


_ISSUED: dict = {}   # id(record) -> record: the records gate_record made (kept alive, so an id is never reused while registered)


def gate_record(candidate, gate: dict) -> _GateRecord:
    """The record a timing is released against (M3): the candidate object itself and a gate whose three results exist with v4's words."""
    records = [gate.get(key) for key in ("centre", "width", "tail")]
    if any(record is None or record.result not in core.RESULT_WORDS for record in records):
        raise ComparatorInputError(f"the gate of {getattr(candidate, 'name', candidate)!r} is incomplete: no speed number before the quality gate")
    record = _GateRecord(candidate, gate["word"], gate["passed"])
    _ISSUED[id(record)] = record
    return record


class SealedTiming:
    """A timing (synthetic here), bound to one candidate object and released only against a gate record gate_record made for that object,
    and only when the gate passed or the candidate declared a working point (M3, fix round 2)."""

    def __init__(self, value: float, unit: str = "seconds per 1,000 events (synthetic number, not measured)"):
        self._value = value
        self._unit = unit
        self._owner = None

    def _bind(self, candidate) -> None:
        if self._owner is not None:
            raise ComparatorInputError(f"this timing belongs to {self._owner.name!r}; one timing, one candidate")
        self._owner = candidate

    def release(self, record) -> dict:
        if _ISSUED.get(id(record)) is not record:
            raise ComparatorInputError("no speed number before the quality gate: only a gate record made by gate_record releases a timing")
        if self._owner is None or record.candidate is not self._owner:
            raise ComparatorInputError("a gate record of another candidate object cannot release this timing")
        if not (record.passed or self._owner.working_point):
            raise ComparatorInputError(f"{self._owner.name!r} did not pass the fixed gate and declared no working point: its speed is withheld")
        return {"value": self._value, "unit": self._unit}


@dataclass(frozen=True, eq=False)
class Candidate:
    """Name, sample, timing and the working-point declaration, all fixed before any gate runs (N4: frozen)."""
    name: str
    pulls: object
    timing: SealedTiming = field(repr=False)
    working_point: bool = False

    def __post_init__(self):
        self.timing._bind(self)


def _quality(gate: dict) -> dict:
    out = {"word": gate["word"], "objects": gate["objects"], "without_result": gate["without_result"]}
    for name in ("centre", "width", "tail"):
        record = gate[name]
        out[name] = {"statistic": record.statistic, "result": record.result, "step": record.step, "estimate": record.estimate,
                     "standard_error": record.standard_error, "lower": record.lower, "upper": record.upper, "limit": record.limit}
    return out


def quality_before_speed(candidates) -> dict:
    """Each candidate's fixed gate first; then its speed, only if it qualified or is a declared working point; the selected candidate is
    the fastest qualified one (A15, A50). Every candidate does the same scientific work (Section 14.2): the same number of objects."""
    candidates = list(candidates)
    names = [candidate.name for candidate in candidates]
    if len(set(names)) != len(names):
        raise ComparatorInputError(f"duplicate candidate names {sorted({n for n in names if names.count(n) > 1})}: each candidate is named once")
    sizes = {candidate.name: int(numpy.asarray(candidate.pulls).size) for candidate in candidates}
    if len(set(sizes.values())) > 1:
        raise ComparatorInputError(f"the candidates hold different numbers of objects {sizes}: an object without a result is NaN, never dropped")
    entries = []
    for candidate in candidates:
        entry = {"name": candidate.name, "working_point_declared": candidate.working_point}
        gate = fixed_gate(candidate.pulls)
        record = gate_record(candidate, gate)
        entry["quality"] = _quality(gate)
        if gate["passed"]:
            entry["disposition"] = "qualified"
            entry["speed"] = dict(candidate.timing.release(record), label="qualified under the fixed gates")
        elif candidate.working_point:
            entry["disposition"] = "listed as another working point"
            entry["speed"] = dict(candidate.timing.release(record), label="not qualified under the fixed gates; not a replacement")
        else:
            entry["disposition"] = "rejected under the fixed gates" if gate["word"] == "fail" else "not qualified: the gate is inconclusive"
            entry["speed"] = None
        entries.append(entry)
    qualified = [e for e in entries if e["disposition"] == "qualified"]
    selected = min(qualified, key=lambda e: e["speed"]["value"])["name"] if qualified else None
    statement = (f"selected {selected}: the fastest candidate that passed every fixed gate; a cost advantage never compensates a failed gate (A50)"
                 if selected else "no qualified candidate: a cost advantage cannot compensate a failed or inconclusive gate; gates are not lowered (A50)")
    return {"candidates": entries, "selected": selected, "statement": statement + ". Synthetic samples and timings; no quality or speed claim"}


# ================================================================ command line

def _emit(record: dict) -> int:
    print(json.dumps(record, sort_keys=True))
    return exit_code(record["status"])


def _compare(args) -> dict:
    out = Path(args.out)
    if out.exists():
        raise ComparatorInputError(f"{out} exists: a result is never overwritten")
    if not out.parent.is_dir():
        raise ComparatorInputError(f"no such folder: {out.parent}")
    declaration = _declaration(args.recipe, args.form)
    if declaration["state"] == "open" and args.form != "byte":     # N3: an open tolerance answers before any input is parsed
        return _incomplete(args.recipe, args.form, declaration["open_item"])
    if args.form == "statistical" and args.quantity not in declaration.get("quantities", {}):
        return _incomplete(args.recipe, args.form, declaration["open_item"]) | {"quantity": args.quantity}
    try:
        reference, candidate = Path(args.reference).read_bytes(), Path(args.candidate).read_bytes()
    except OSError as exc:
        raise ComparatorInputError(f"an input cannot be read: {exc}") from exc
    if args.form == "byte":
        return compare_bytes(args.recipe, reference, candidate)
    try:
        ref_doc, cand_doc = json.loads(reference), json.loads(candidate)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ComparatorInputError(f"an input is not JSON: {exc}") from exc
    if args.form == "numerical":
        return compare_numerical(args.recipe, ref_doc, cand_doc)
    return compare_statistical(args.recipe, args.quantity, ref_doc, cand_doc)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="operation", required=True)
    compare = sub.add_parser("compare")
    compare.add_argument("--recipe", required=True)
    compare.add_argument("--form", required=True)
    compare.add_argument("--reference", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--out", required=True)
    compare.add_argument("--quantity", default=FAKE_RATE)
    sub.add_parser("declarations")
    args = parser.parse_args(argv)
    if args.operation == "declarations":
        return _emit({"status": "ok", "declarations": DECLARATIONS, "open_items": OPEN_ITEMS, "rulings": RULINGS})
    try:
        result = _compare(args)
    except ComparatorInputError as exc:
        return _emit({"status": "rejected", "reason": str(exc)})
    except Exception as exc:  # noqa: BLE001  (the comparator could not run: incomplete, never a verdict)
        return _emit({"status": "incomplete", "reason": f"{type(exc).__name__}: {exc}"})
    try:
        with open(args.out, "x", encoding="utf-8") as handle:
            json.dump(result, handle, sort_keys=True, indent=1, default=str)
    except OSError as exc:
        return _emit({"status": "incomplete", "reason": f"the result cannot be written: {exc}"})
    # I3, M5: the summary names the open item or the ruling a result stands on, and what blocks a pass.
    return _emit({k: result[k] for k in ("status", "form", "recipe", "open_item", "ruling", "blocking", "reason") if k in result}
                 | {"out": str(args.out), "failed": result.get("failed", [])})


if __name__ == "__main__":
    sys.exit(main())
