"""A37 and plan section 9.6 for T10 (t10-timing-stage-plan.md section 6.1, row A37-T10). Scoring side; the recipe never imports it.

- gxe_check: section 9.6's artificial model y = g E for channel gains g_c and event energies E_e, in logarithms. The design has the
  exact null vector (+1 on every ln g, -1 on every ln E), so its rational rank is C + E - 1; (a g, E / a) gives the same amplitudes;
  a least-squares fit converges (sum of squared log residuals <= 1e-20) in two gauges that differ by the scale a; a same-type
  holdout (an event left out, its energy refitted from its own amplitudes with the gains held) fits equally in both gauges; the
  identifiable combinations (gain ratios, products g_c E_e) agree in both (1e-12 relative); only a named external constraint (one
  event of known energy) makes the rank full and the scale unique. So neither convergence nor the holdout identifies the scale (A37).
- witness_check: T07's run record of CAI-T07-4 (job 7546791, cai-refit.log), read, not rerun, its SHA-256 pinned here (T07_LOG_SHA256;
  stage 2 fix round 1, I2: any other text fails on the source, a placeholder included), with its own outcome required (M9): in
  each of its 8 cells (charge -1 and +1, bending bins 0 to 3) the q/p change is at least k = 4.5 per-track sigma while the change in
  mean chi2/ndf is within n = 4.5 of its standard error (R37's self-check at T07's thresholds). A placeholder record never passes.
- card_check: the recipe's method card (timing_recipe.method_card.check).
Planted defects (plant=...): holdout-as-proof (a claim that the holdout identified the scale, judged and refused: fix round 1, M3),
placeholder-witness (a real placeholder text offered as the witness: placeholder_text()), no-constraint, validation-is-constraint (an
item offered both as constraint and as observable, in the card). Each must FAIL its item.
"""
from __future__ import annotations

import copy
import hashlib
import math
import re
from fractions import Fraction

import numpy

GAUGE_TOLERANCE = 1e-12
CONVERGED = 1e-20
K_SIGMA, STANDARD_ERROR_FACTOR = 4.5, 4.5
T07_JOB = 7546791
T07_LOG_SHA256 = "0f60e9ac0ebe9114c0ba1f64369926027b7b130d9c43884ddcd458bf73316a90"   # calibration-alignment-interfaces.md, T10 stage 2
OUTCOME = re.compile(r"^test_cai_t07_4_self_check \(")
CELL = re.compile(r"CAI-T07-4 cell charge ([+-]1) bending bin (\d+) tracks \d+ and \d+ change in q/p ([-+0-9.eE]+) per-track sigmas"
                  r".*?change in mean chi2/ndf ([-+0-9.eE]+) \(se ([-+0-9.eE]+)\)")


def exact_rank(rows: list) -> int:
    """The rank of an integer or rational matrix by exact elimination."""
    matrix = [[Fraction(v) for v in row] for row in rows]
    rank, columns = 0, len(matrix[0]) if matrix else 0
    for column in range(columns):
        pivot = next((r for r in range(rank, len(matrix)) if matrix[r][column] != 0), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        for r in range(len(matrix)):
            if r != rank and matrix[r][column] != 0:
                factor = matrix[r][column] / matrix[rank][column]
                matrix[r] = [a - factor * b for a, b in zip(matrix[r], matrix[rank])]
        rank += 1
    return rank


def gxe_design(channels: int, events: int) -> list:
    """One row per (channel, event): ln A_ce = ln g_c + ln E_e."""
    return [[int(i == c) for i in range(channels)] + [int(j == e) for j in range(events)] for c in range(channels) for e in range(events)]


def _fit(rows, values):
    solution, *_ = numpy.linalg.lstsq(numpy.array(rows, dtype=float), numpy.array(values, dtype=float), rcond=None)
    residual = numpy.array(rows, dtype=float) @ solution - numpy.array(values, dtype=float)
    return solution, float(residual @ residual)


def _relative(a, b) -> float:
    return max(abs(x - y) / max(abs(x), abs(y), 1e-300) for x, y in zip(a, b))


def gxe_check(gains: list, energies: list, gauge: float, reference_event: int, plant: str | None = None, claims: list | None = None) -> dict:
    channels, events = len(gains), len(energies)
    rows = gxe_design(channels, events)
    logs = [math.log(g * e) for g in gains for e in energies]
    parameters = channels + events
    rank_without = exact_rank(rows)
    constraint = [0] * channels + [int(j == reference_event) for j in range(events)]
    rank_with = exact_rank(rows + [constraint])
    items, largest = {}, {}
    items["rank"] = rank_without == parameters - 1 and rank_with == parameters
    y1 = [g * e for g in gains for e in energies]
    y2 = [(gauge * g) * (e / gauge) for g in gains for e in energies]
    largest["gauge"] = _relative(y1, y2)
    items["gauge"] = largest["gauge"] <= GAUGE_TOLERANCE
    # two gauge-fixed fits: ln g_0 = 0 and ln g_0 = ln a
    fix = [1] + [0] * (parameters - 1)
    first, r1 = _fit(rows + [fix], logs + [0.0])
    second, r2 = _fit(rows + [fix], logs + [math.log(gauge)])
    scales_differ = abs((second[0] - first[0]) - math.log(gauge)) <= 1e-12 and abs(math.log(gauge)) > 1e-6
    items["convergence"] = r1 <= CONVERGED and r2 <= CONVERGED and scales_differ
    largest["convergence"] = max(r1, r2)
    # same-type holdout: fit on all events but the last, then refit the last event's energy from its amplitudes, gains held
    held = events - 1
    train_rows = gxe_design(channels, held)
    train_logs = [math.log(g * e) for g in gains for e in energies[:held]]
    holdout = []
    for solution_gauge in (0.0, math.log(gauge)):
        solution, _ = _fit(train_rows + [[1] + [0] * (channels + held - 1)], train_logs + [solution_gauge])
        ln_g = solution[:channels]
        held_out = [math.log(g * energies[-1]) for g in gains]
        ln_e = float(numpy.mean([t - lg for t, lg in zip(held_out, ln_g)]))
        holdout.append(float(sum((lg + ln_e - t) ** 2 for lg, t in zip(ln_g, held_out))))
    items["holdout"] = all(h <= CONVERGED for h in holdout)
    largest["holdout"] = max(holdout)
    # identifiable combinations agree in both gauges
    g1, e1, g2, e2 = numpy.exp(first[:channels]), numpy.exp(first[channels:]), numpy.exp(second[:channels]), numpy.exp(second[channels:])
    ratios = _relative(list(g1 / g1[0]), list(g2 / g2[0]))
    products = _relative([a * b for a in g1 for b in e1], [a * b for a in g2 for b in e2])
    largest["identifiable"] = max(ratios, products)
    items["identifiable"] = largest["identifiable"] <= GAUGE_TOLERANCE
    # the named external constraint: the reference event's energy is known
    fitted, r3 = _fit(rows + [constraint], logs + [math.log(energies[reference_event])])
    recovered = _relative(list(numpy.exp(fitted)), list(gains) + list(energies))
    largest["constraint"] = recovered
    identified_without = rank_without == parameters
    identified_with = rank_with == parameters and r3 <= CONVERGED and recovered <= GAUGE_TOLERANCE
    items["constraint"] = (not identified_without) and identified_with
    # claims are judged: identification by a holdout or by convergence is refused; only a named constraint identifies (A37)
    claims = list(claims or [])
    if plant == "holdout-as-proof":
        claims.append({"claim": "absolute scale identified", "by": "holdout"})
    refused = [c for c in claims if c.get("by") in ("holdout", "convergence") or not str(c.get("by", "")).startswith("constraint.")]
    items["claims"] = not refused
    items = {name: bool(ok) for name, ok in items.items()}
    largest = {name: float(value) for name, value in largest.items()}
    report = {name: {"verdict": "PASS" if ok else "FAIL"} for name, ok in items.items()}
    return {"verdict": "PASS" if all(items.values()) else "FAIL", "plant": plant, "items": report, "largest_relative": largest,
            "rank": {"without": rank_without, "with": rank_with, "parameters": parameters},
            "identified_without_constraint": bool(identified_without), "identified_with_constraint": bool(identified_with),
            "constraint": f"the energy of event {reference_event} is known (an external energy reference)", "gauge": gauge,
            "claims": claims, "claims_refused": refused}


def parse_t07_witness(text: str) -> list:
    cells = []
    for line in text.splitlines():
        match = CELL.search(line)
        if match:
            charge, bin_, qp, chi2, se = match.groups()
            cells.append({"charge": int(charge), "bin": int(bin_), "qp_sigmas": float(qp), "chi2_change": float(chi2), "chi2_se": float(se)})
    return cells


def placeholder_text() -> str:
    """A placeholder offered as the witness: eight valid-looking cell lines and an outcome, but not T07's run record."""
    lines = ["test_cai_t07_4_self_check (placeholder) ... placeholder unconstrained-mode check, no run behind it"]
    lines += [f"CAI-T07-4 cell charge {q:+d} bending bin {b} tracks 1 and 1 change in q/p 9.0000 per-track sigmas (se 0.0100, "
              f"sigma 0.004000 per GeV), 9.0000 stated sigmas; change in mean chi2/ndf +0.00000 (se 0.01000); placeholder"
              for q in (-1, 1) for b in range(4)]
    return "\n".join(lines + ["ok", "", "Ran 1 test in 0.001s", "", "OK"]) + "\n"


def _outcome(text: str) -> bool:
    """The record's own outcome (M9): the self-check test followed by 'ok' before the next test, and the run's final OK."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if OUTCOME.search(line)), None)
    if start is None or not any(line.strip() == "OK" for line in lines[-3:]):
        return False
    for line in lines[start + 1:]:
        if line.startswith("test_"):
            return False
        if line.strip() == "ok":
            return True
    return False


def witness_check(text: str, plant: str | None = None) -> dict:
    if plant == "placeholder-witness":
        text = placeholder_text()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    cells = parse_t07_witness(text)
    keys = sorted((c["charge"], c["bin"]) for c in cells)
    complete = keys == sorted((q, b) for q in (-1, 1) for b in range(4))
    weak = [c["qp_sigmas"] >= K_SIGMA and abs(c["chi2_change"]) <= STANDARD_ERROR_FACTOR * c["chi2_se"] for c in cells]
    items = {"source": digest == T07_LOG_SHA256, "outcome": _outcome(text), "cells": complete, "weak": complete and all(weak)}
    return {"verdict": "PASS" if all(items.values()) else "FAIL", "plant": plant,
            "items": {k: {"verdict": "PASS" if v else "FAIL"} for k, v in items.items()},
            "source": {"sha256": digest, "pinned_sha256": T07_LOG_SHA256, "job": T07_JOB, "item": "CAI-T07-4",
                       "placeholder_fed": plant == "placeholder-witness"},
            "cells": cells, "thresholds": {"k_sigma": K_SIGMA, "n_se": STANDARD_ERROR_FACTOR}}


def card_check(card: dict, plant: str | None = None) -> dict:
    from timing_recipe import method_card
    card = copy.deepcopy(card)
    if plant == "no-constraint":
        card["unconstrained_modes"][0]["constraining_information"] = []
    elif plant == "validation-is-constraint":                  # the same item offered as constraint and as validation (I3)
        mode = card["unconstrained_modes"][2]
        mode["independent_observables"].append(copy.deepcopy(mode["constraining_information"][0]))
    try:
        method_card.check(card)
        verdict, reason = "PASS", None
    except method_card.InputError as exc:
        verdict, reason = "FAIL", str(exc)
    return {"verdict": verdict, "plant": plant, "reason": reason, "modes": [m.get("mode") for m in card.get("unconstrained_modes", [])]}
