"""Detector system design M0: the single-evaluation verdict table (RUL-*), bound combination (CMB-*), chain and
contract checks (FID-*, ART-60..ART-64) of contracts/design.py, on the SYNTHETIC spectrometer project
(tests/contracts/design_fixtures.py). Test ids follow section 8 of the spec (T-xx)."""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts.design import ROWS, Factors, combine_bounds, decide, one_sided_halfwidth  # noqa: E402
from design_fixtures import (attach_cases, NS, copy_fixture, derive, edit, entry, error_codes, fake_contract, fake_eval,  # noqa: E402
                             gauss, matrix, write_contracts)

RES = "momentum-resolution-core"
UP_RES = {"upstream": RES}


def res_contract(tool="syn-res", bound="estimate", fidelity="F3", **kw):
    return fake_contract(tool, RES, bound, fidelity, **kw)


# ---------------------------------------------------------------- the M0 acceptance (section 7, M0)


def case_m0_acceptance_chain(b):
    """PHY -> REQ -> CALC -> VER at F1 only: the probe fails resolution (row 10), the two reasonable candidates are
    inconclusive on resolution and charge confusion (row 11), and the missing F3, F4 and data validation are listed."""
    d = derive(b)
    assert d["status"] == "ok", d["errors"]
    assert matrix(d, "REQ-TRK-001", "cand-P")["result"] == "fail"
    assert matrix(d, "REQ-TRK-001", "cand-P")["codes"] == ["bound.excludes"]
    for c in ("cand-A", "cand-B"):
        for req in ("REQ-TRK-001", "REQ-CC-001"):
            m = matrix(d, req, c)
            assert (m["result"], m["codes"]) == ("inconclusive", ["bound.direction"])
        assert any("F3" in x for x in matrix(d, "REQ-TRK-001", c)["missing_evidence"])
        cc = matrix(d, "REQ-CC-001", c)["missing_evidence"]
        assert any("charge-confusion-rate at F4" in x for x in cc)
        assert any("charge-confusion-data-validation" in x for x in cc)
    assert entry(d, "REQ-TRK-001", "cand-P", "CALC-TRK-P")["row"] == 10
    assert entry(d, "REQ-CC-001", "cand-A", "CALC-CC-A")["row"] == 11


# ---------------------------------------------------------------- TST-EX-01, T-56: row 18 unreachable


def case_t56_row18_unreachable_by_exhaustion():
    """RUL-18, RUL-19: every combination of the factors the table reads reaches a row before 18, under the premise
    that every evaluation except row 1 and F0 carries a value (meets is then defined)."""
    seen = set()
    bools = (False, True)
    for combo in itertools.product(bools, bools, bools, bools, bools, bools, bools, bools,
                                   ("optimistic", "conservative", "estimate", "mixed"), bools, bools, bools,
                                   ("compliant", "noncompliant", "within")):
        row, verdict, code = decide(Factors(*combo))
        assert row != 18, combo
        assert code == ROWS[row][1]
        seen.add(row)
    assert seen == set(range(1, 18))  # rows 1-17 each reachable


def case_t54_each_row_from_factors():
    """TST-01 at the factor level: one factor state per row 1-17 that holds only at that row."""
    base = dict(bound="estimate", uncertainty_ok=True, estimate="compliant")
    probes = {1: dict(unavailable=True), 2: dict(stale=True), 3: dict(unresolved=True), 4: dict(invalid=True),
              5: dict(chain_incomplete=True), 6: dict(budget_incomplete=True), 7: dict(domain_mismatch=True),
              8: dict(below_screening=True), 9: dict(bound="mixed"), 10: dict(bound="optimistic", meets=False),
              11: dict(bound="optimistic", meets=True), 12: dict(below_compliance=True),
              13: dict(bound="conservative", meets=True), 14: dict(bound="conservative", meets=False),
              15: dict(uncertainty_ok=False), 16: dict(), 17: dict(estimate="within")}
    for row, kw in probes.items():
        got = decide(Factors(**{**base, **kw}))
        assert got[0] == row, (row, got)
    assert decide(Factors(**base))[1] == "pass" and decide(Factors(**{**base, "estimate": "noncompliant"}))[1] == "fail"


# ---------------------------------------------------------------- rows 1-4 (T-01, T-02, T-23, T-50)


def case_t01_unavailable_takes_precedence_over_stale(b):
    """RUL-01, RUL-02, RUL-00a: an unavailable evaluation with a stale input is capability.unavailable."""
    b.evaluation("EST-ACC-A", "cand-A", "geometric-acceptance", {"rigidity_GV": 1000.0, "species": "proton",
                 "charge_sign": "positive"}, None, "estimate", fidelity="F3", unavailable=True)
    edit(b, "candidates/cand-A.json", lambda d: d["extension"].update(description="changed"))
    spec = b.read("design-spec.v1.json")
    spec["extension"]["requirements"].append(
        {"id": f"{NS}:REQ-ACC-001", "quantity": "geometric-acceptance", "comparator": ">=", "target": 0.05,
         "unit": "m2 sr", "kind": "derived", "denominator": {"rigidity_GV": {"value": 1000.0, "tolerance": 0},
                                                             "species": {"value": "proton", "tolerance": 0},
                                                             "charge_sign": {"value": "positive", "tolerance": 0}}})
    b.write("design-spec.v1.json", spec)
    d = derive(b)
    e = entry(d, "REQ-ACC-001", "cand-A", "EST-ACC-A")
    assert (e["row"], e["code"]) == (1, "capability.unavailable")
    assert "spectrometer-demo:EST-ACC-A" in d["unavailable"]


def case_t02_stale_unresolved_invalid(b):
    """RUL-02, RUL-03, RUL-04: input hash mismatch; input without hash; an input carrying 'failed'."""
    edit(b, "runs/CALC-TRK-A.computational-run.json", lambda d: d["extension"].update(tolerances={"x": 1}))
    edit(b, "evaluations/CALC-TRK-B.json", lambda d: d["inputs"][0].pop("sha256"))
    d = derive(b)
    assert entry(d, "REQ-TRK-001", "cand-A", "CALC-TRK-A")["code"] == "evidence.stale"
    assert entry(d, "REQ-TRK-001", "cand-B", "CALC-TRK-B")["code"] == "evidence.unresolved"


def case_t02_invalid_failed_upstream(b):
    """RUL-04: an input that carries the sticky 'failed' (declared and propagated) is evidence.invalid."""
    edit(b, "candidates/cand-B.json", lambda d: d.update(status=["synthetic", "failed"]))
    b.rebind("runs/CALC-TRK-B.computational-run.json")
    edit(b, "runs/CALC-TRK-B.computational-run.json", lambda d: d.update(status=["synthetic", "failed"]))
    edit(b, "evaluations/CALC-TRK-B.json", lambda d: d.update(status=["synthetic", "failed"]))
    b.rebind("evaluations/CALC-TRK-B.json")
    d = derive(b)
    assert entry(d, "REQ-TRK-001", "cand-B", "CALC-TRK-B")["code"] == "evidence.invalid"


def case_t23_unavailable_declared_but_contract_exists(b):
    """RUL-01, ART-63: declaring unavailable for a figure of merit a contract computes at that fidelity is an error."""
    b.evaluation("EST-TRK-A", "cand-A", RES, {"rigidity_GV": 1000.0, "species": "proton"}, None, "estimate",
                 unavailable=True)
    d = derive(b)
    assert "design.contract_mismatch" in error_codes(d, "EST-TRK-A")


def case_t50_f0_and_unavailable_not_compared_with_contract(b):
    """ART-63, RUL-01, RUL-08: an F0 estimate is not checked against the F1 contract and falls under row 8; an
    unavailable evaluation (no contract at F4) falls under row 1."""
    b.evaluation("EST-TRK-A0", "cand-A", RES, {"rigidity_GV": 1000.0, "species": "proton"}, 0.4, "estimate",
                 fidelity="F0", derivation="heuristic-argument", uncertainty=gauss(0.2))
    b.evaluation("EST-TRK-A2", "cand-A", RES, {"rigidity_GV": 1000.0, "species": "proton"}, None, "estimate",
                 fidelity="F4", unavailable=True)
    d = derive(b)
    assert not error_codes(d, "EST-TRK-A")
    assert entry(d, "REQ-TRK-001", "cand-A", "EST-TRK-A0")["row"] == 8
    assert entry(d, "REQ-TRK-001", "cand-A", "EST-TRK-A2")["row"] == 1
    assert any("F0 evaluation" in f for c in d["candidates"] if f"{NS}:cand-A" in c["candidates"] for f in c["at_risk"])


# ---------------------------------------------------------------- rows 5-9 (T-03, T-04, T-05, T-06, T-07, T-48)


def case_t03_expected_precision_chain_incomplete(b, tmp_path):
    """RUL-05, FID-11, CHN-07: an expected-precision chain without its charge-confusion evaluation."""
    c = fake_contract("syn-precision", "expected-precision", "estimate", "F1", denominator={},
                      inputs=[("sigma", UP_RES, "order-preserving"), ("conf", {"upstream": "charge-confusion-rate"},
                                                                      "order-preserving")],
                      required=[RES, "charge-confusion-rate"])
    dirs = [write_contracts(tmp_path / "c", c)]
    sigma = b.read("evaluations/CALC-TRK-A.json")["extension"]["value"]
    fake_eval(b, "CALC-EP-A", "cand-A", c, 0.1, {"--sigma": sigma}, denominator={}, bound="optimistic",
              upstream=["evaluations/CALC-TRK-A.json"], uncertainty=gauss(0.02))
    spec = b.read("design-spec.v1.json")
    spec["extension"]["requirements"].append({"id": f"{NS}:REQ-EP-001", "quantity": "expected-precision",
                                              "comparator": "<=", "target": 0.2, "unit": "1", "kind": "derived",
                                              "denominator": {}})
    b.write("design-spec.v1.json", spec)
    d = derive(b, dirs)
    assert entry(d, "REQ-EP-001", "cand-A", "CALC-EP-A")["code"] == "chain.incomplete"


def case_t04_t48_budget_incomplete_and_uncertainty_minimum(b, tmp_path):
    """RUL-06, ART-23, ART-24, CHN-13: a subsystem without a budget row is budget.incomplete; an author-entered
    uncertainty below the adequacy minimum of its basis is a design error."""
    c = fake_contract("syn-budget", "mass-budget", "estimate", "F1", denominator={}, unit="kg")
    dirs = [write_contracts(tmp_path / "c", c)]
    edit(b, "candidates/cand-A.json", lambda d: d["extension"]["budgets"]["mass"].pop("DES-MAG-001"))
    edit(b, "candidates/cand-B.json", lambda d: d["extension"]["budgets"]["mass"]["DES-TRK-001"].update(uncertainty=1.0))
    fake_eval(b, "CALC-MASS-A", "cand-A", c, 400.0, denominator={}, uncertainty=gauss(100.0))
    d = derive(b, dirs)
    assert entry(d, "CON-MASS-001", "cand-A", "CALC-MASS-A")["code"] == "budget.incomplete"
    assert "design.budget_uncertainty_below_minimum" in error_codes(d, "cand-B")


def case_t05_domain_mismatch(b):
    """RUL-07, FID-10, ART-11: outside the contract's validity domain (a curvature offset); different denominator
    fields; a value outside the tolerance."""
    spec = b.read("design-spec.v1.json")
    reqs = spec["extension"]["requirements"]
    reqs.append(dict(reqs[0], id=f"{NS}:REQ-TRK-002", denominator={"rigidity_GV": {"value": 900.0, "tolerance": 50.0},
                                                                    "species": {"value": "proton", "tolerance": 0}}))
    b.write("design-spec.v1.json", spec)
    b.eval_confusion("CALC-CC-A1", "cand-A", "evaluations/CALC-TRK-A.json", offset=1e-5)
    d = derive(b)
    assert entry(d, "REQ-TRK-002", "cand-A", "CALC-TRK-A")["code"] == "domain.mismatch"
    e = entry(d, "REQ-CC-001", "cand-A", "CALC-CC-A1")
    assert e["code"] == "domain.mismatch"
    assert any("curvature offset" in r for r in e["reasons"])
    edit(b, "design-spec.v1.json", lambda s: s["extension"]["requirements"][2]["denominator"].pop("species"))
    d = derive(b)
    assert "design.denominator_incomplete" in error_codes(d)


def case_t06_f0_used_for_screening(b):
    """RUL-08, FID-01: an F0 estimate is below every screening threshold."""
    b.evaluation("EST-CC-B0", "cand-B", "charge-confusion-rate", {"rigidity_GV": 1000.0, "species": "proton",
                 "charge_sign": "positive", "curvature_offset_per_GV": 0.0}, 0.01, "estimate", fidelity="F0",
                 derivation="heuristic-argument")
    d = derive(b)
    e = entry(d, "REQ-CC-001", "cand-B", "EST-CC-B0")
    assert (e["row"], e["code"]) == (8, "fidelity.insufficient")


def case_t07_bound_mixed(b, tmp_path):
    """RUL-09, CMB-02, CMB-04: one optimistic and one conservative input; a non-monotonic combination with an
    optimistic input."""
    cons = res_contract("syn-cons", "conservative", "F3")
    acc = fake_contract("syn-acc", "geometric-acceptance", "conservative", "F2", better="larger",
                        denominator={"rigidity_GV": "number", "species": "string", "charge_sign": "string"})
    mix = fake_contract("syn-mix", "expected-precision", "estimate", "F1", denominator={},
                        inputs=[("sigma", UP_RES, "order-preserving"),
                                ("acc", {"upstream": "geometric-acceptance"}, "order-preserving")],
                        required=[RES, "geometric-acceptance"])
    nonmono = fake_contract("syn-nonmono", "expected-precision", "estimate", "F1", denominator={},
                            inputs=[("sigma", UP_RES, "non-monotonic")], required=[RES])
    dirs = [write_contracts(tmp_path / "c", cons, acc, mix, nonmono)]
    a = fake_eval(b, "SIM-ACC-A", "cand-A", acc, 0.1, denominator={"rigidity_GV": 1000.0, "species": "proton",
                                                                     "charge_sign": "positive"})
    sigma = b.read("evaluations/CALC-TRK-A.json")["extension"]["value"]
    fake_eval(b, "CALC-EP-MIX", "cand-A", mix, 0.1, {"--sigma": sigma, "--acc": 0.1}, denominator={},
              upstream=["evaluations/CALC-TRK-A.json", a], bound="optimistic")
    fake_eval(b, "CALC-EP-NM", "cand-A", nonmono, 0.1, {"--sigma": sigma}, denominator={},
              upstream=["evaluations/CALC-TRK-A.json"], bound="estimate")
    spec = b.read("design-spec.v1.json")
    spec["extension"]["requirements"].append({"id": f"{NS}:REQ-EP-001", "quantity": "expected-precision",
                                              "comparator": "<=", "target": 0.2, "unit": "1", "kind": "derived",
                                              "denominator": {}})
    b.write("design-spec.v1.json", spec)
    d = derive(b, dirs)
    for eid in ("CALC-EP-MIX", "CALC-EP-NM"):
        e = entry(d, "REQ-EP-001", "cand-A", eid)
        assert (e["row"], e["code"]) == (9, "bound.mixed"), e
    assert combine_bounds("estimate", [("optimistic", "order-preserving"), ("conservative", "order-preserving")]) == "mixed"
    assert combine_bounds("estimate", [("optimistic", "non-monotonic")]) == "mixed"
    assert combine_bounds("estimate", [("estimate", "non-monotonic")]) == "estimate"


# ---------------------------------------------------------------- rows 10-17 (T-08..T-14, T-18..T-22)


def case_t08_optimistic_misses_ge_target(b, tmp_path):
    """RUL-10, RUL-00b, PRN-04: an optimistic PID rejection that misses a >= target fails."""
    c = fake_contract("syn-rej", "pid-rejection", "optimistic", "F1", better="larger",
                      denominator={"momentum_GeV": "number", "species": "string", "working_point_efficiency": "number",
                                   "separation_convention": "string"})
    dirs = [write_contracts(tmp_path / "c", c)]
    den = {"momentum_GeV": 10.0, "species": "proton", "working_point_efficiency": 0.9, "separation_convention": "single"}
    fake_eval(b, "CALC-REJ-A", "cand-A", c, 500.0, denominator=den)
    spec = b.read("design-spec.v1.json")
    spec["extension"]["requirements"].append({"id": f"{NS}:REQ-REJ-001", "quantity": "pid-rejection",
                                              "comparator": ">=", "target": 1000.0, "unit": "1", "kind": "driving",
                                              "denominator": {k: {"value": v, "tolerance": 0} for k, v in den.items()}})
    b.write("design-spec.v1.json", spec)
    d = derive(b, dirs)
    assert (entry(d, "REQ-REJ-001", "cand-A", "CALC-REJ-A")["row"], matrix(d, "REQ-REJ-001", "cand-A")["result"]) == (10, "fail")


def case_t09_optimistic_meets(b):
    """RUL-11: F1 charge confusion meets the target: bound.direction."""
    e = entry(derive(b), "REQ-CC-001", "cand-B", "CALC-CC-B")
    assert (e["row"], e["code"]) == (11, "bound.direction")


def case_t11_t12_conservative(b, tmp_path):
    """RUL-13, RUL-14 with a synthetic conservative F3 contract (no existing F1 tool is a conservative bound)."""
    c = res_contract("syn-cons", "conservative", "F3")
    dirs = [write_contracts(tmp_path / "c", c)]
    fake_eval(b, "SIM-TRK-B", "cand-B", c, 0.3)
    fake_eval(b, "SIM-TRK-A", "cand-A", c, 0.7)
    d = derive(b, dirs)
    assert entry(d, "REQ-TRK-001", "cand-B", "SIM-TRK-B")["row"] == 13
    assert matrix(d, "REQ-TRK-001", "cand-B")["result"] == "pass"
    assert matrix(d, "REQ-TRK-001", "cand-B")["provisional"] is True  # OQ-05: table not frozen
    assert (entry(d, "REQ-TRK-001", "cand-A", "SIM-TRK-A")["row"], matrix(d, "REQ-TRK-001", "cand-A")["result"]) == (14, "inconclusive")


def case_t13_estimate_rows(b, tmp_path):
    """RUL-15, RUL-16, RUL-17: no uncertainty; gap larger than the uncertainty (pass and fail); gap within."""
    c = res_contract()
    dirs = [write_contracts(tmp_path / "c", c)]
    fake_eval(b, "SIM-TRK-A", "cand-A", c, 0.3)                                   # no uncertainty
    fake_eval(b, "SIM-TRK-B", "cand-B", c, 0.3, uncertainty=gauss(0.07))          # 0.3 + 1.645*0.07 < 0.6
    fake_eval(b, "SIM-TRK-P", "cand-P", c, 0.95, uncertainty=gauss(0.2))          # 0.95 - 1.645*0.2 > 0.6
    d = derive(b, dirs)
    assert entry(d, "REQ-TRK-001", "cand-A", "SIM-TRK-A")["row"] == 15
    e = entry(d, "REQ-TRK-001", "cand-B", "SIM-TRK-B")
    assert (e["row"], e["verdict"]) == (16, "pass")
    e = entry(d, "REQ-TRK-001", "cand-P", "SIM-TRK-P")
    assert (e["row"], e["verdict"]) == (16, "fail")
    edit(b, "evaluations/SIM-TRK-B.json", lambda x: x["extension"].update(value=0.5, uncertainty=gauss(0.1)))
    d = derive(b, dirs)
    assert entry(d, "REQ-TRK-001", "cand-B", "SIM-TRK-B")["code"] == "design.contract_mismatch"  # value != output
    assert matrix(d, "REQ-TRK-001", "cand-B")["result"] != "pass"


def case_t13_within_uncertainty(b, tmp_path):
    c = res_contract()
    dirs = [write_contracts(tmp_path / "c", c)]
    fake_eval(b, "SIM-TRK-B", "cand-B", c, 0.5, uncertainty=gauss(0.11))          # 0.5 + 0.18 > 0.6
    e = entry(derive(b, dirs), "REQ-TRK-001", "cand-B", "SIM-TRK-B")
    assert (e["row"], e["code"]) == (17, "margin.within_uncertainty")


def case_t10_chain_charge_confusion_only_at_f3(b, tmp_path):
    """RUL-12, ADQ-02, CMB-07: an all-estimate expected-precision chain whose charge confusion is only F3 stays below
    the charge-confusion compliance threshold (F4)."""
    r3 = res_contract("syn-res3")
    cc3 = fake_contract("syn-cc3", "charge-confusion-rate", "estimate", "F3",
                        denominator={"rigidity_GV": "number", "species": "string", "charge_sign": "string",
                                     "curvature_offset_per_GV": "number"})
    ep = fake_contract("syn-ep3", "expected-precision", "estimate", "F3", denominator={},
                       inputs=[("sigma", UP_RES, "order-preserving"), ("conf", {"upstream": "charge-confusion-rate"},
                                                                       "order-preserving")],
                       required=[RES, "charge-confusion-rate"])
    dirs = [write_contracts(tmp_path / "c", r3, cc3, ep)]
    r = fake_eval(b, "SIM-TRK-B", "cand-B", r3, 0.06, uncertainty=gauss(0.015))
    cc = fake_eval(b, "SIM-CC-B", "cand-B", cc3, 1e-4, denominator={"rigidity_GV": 1000.0, "species": "proton",
                   "charge_sign": "positive", "curvature_offset_per_GV": 0.0},
                   uncertainty=gauss(5e-5, 0.95, distribution="exact"))
    fake_eval(b, "SIM-EP-B", "cand-B", ep, 0.05, {"--sigma": 0.06, "--conf": 1e-4}, denominator={},
              upstream=[r, cc], uncertainty=gauss(0.01))
    spec = b.read("design-spec.v1.json")
    spec["extension"]["requirements"].append({"id": f"{NS}:REQ-EP-001", "quantity": "expected-precision",
                                              "comparator": "<=", "target": 0.2, "unit": "1", "kind": "derived",
                                              "denominator": {}})
    b.write("design-spec.v1.json", spec)
    d = derive(b, dirs)
    assert not error_codes(d, "SIM-EP-B"), d["errors"]
    e = entry(d, "REQ-EP-001", "cand-B", "SIM-EP-B")
    assert (e["row"], e["code"], e["bound"]) == (12, "fidelity.insufficient", "estimate")


def case_t14_range_side_swaps_roles(b):
    """RUL-00c: on the side opposite to 'better' an optimistic bound acts as a conservative one, so a resolution
    below the lower end of a range is not a fail; above the upper end it is."""
    def set_range(lo, hi):
        edit(b, "design-spec.v1.json", lambda s: s["extension"]["requirements"][0].update(comparator="range",
                                                                                           target=[lo, hi]))
    set_range(0.55, 0.7)   # cand-A 0.488: upper side optimistic meets (11); lower side conservative misses
    assert matrix(derive(b), "REQ-TRK-001", "cand-A")["result"] == "inconclusive"
    set_range(0.01, 0.3)   # upper side: optimistic misses -> fail
    d = derive(b)
    assert (matrix(d, "REQ-TRK-001", "cand-A")["result"], entry(d, "REQ-TRK-001", "cand-A", "CALC-TRK-A")["row"]) == ("fail", 10)


def _two_input_project(b, tmp_path, up_bound, est_value=0.10, target=0.5, direction="order-preserving", ep_fid="F1"):
    """A composite 'expected-precision' fed by the F1 (optimistic) resolution or a synthetic F3 conservative or
    optimistic one, and by an acceptance estimate; returns (dirs, upstream rel, acceptance estimate, contract)."""
    acc = fake_contract("syn-acc", "geometric-acceptance", "estimate", "F2", better="larger",
                        denominator={"rigidity_GV": "number", "species": "string", "charge_sign": "string"})
    ep = fake_contract("syn-ep", "expected-precision", "estimate", ep_fid, denominator={},
                       inputs=[("sigma", UP_RES, direction), ("acc", {"upstream": "geometric-acceptance"},
                                                              "order-preserving")],
                       required=[RES, "geometric-acceptance"])
    cons = res_contract("syn-cons", "conservative", "F3")
    opt3 = res_contract("syn-opt3", "optimistic", "F3")
    dirs = [write_contracts(tmp_path / "c", acc, ep, cons, opt3)]
    a = fake_eval(b, "SIM-ACC-A", "cand-A", acc, est_value, denominator={"rigidity_GV": 1000.0, "species": "proton",
                                                                           "charge_sign": "positive"},
                  uncertainty=gauss(0.01))
    if up_bound == "conservative":
        up = fake_eval(b, "SIM-TRK-A", "cand-A", cons, 0.48797)
    elif up_bound == "optimistic-f3":
        up = fake_eval(b, "SIM-TRK-A", "cand-A", opt3, 0.48797)
    else:
        up = "evaluations/CALC-TRK-A.json"
    spec = b.read("design-spec.v1.json")
    spec["extension"]["requirements"].append({"id": f"{NS}:REQ-EP-001", "quantity": "expected-precision",
                                              "comparator": "<=", "target": target, "unit": "1", "kind": "derived",
                                              "denominator": {}})
    b.write("design-spec.v1.json", spec)
    return dirs, up, a, ep


def case_t18_optimistic_with_estimate_moved_favorable(b, tmp_path):
    """CMB-05: the acceptance estimate is fed at its favorable one-sided bound (larger, Bonferroni n=1 at 95%); the
    composite is optimistic: missing the target fails (row 10), meeting it is bound.direction (row 11). Feeding the
    central value is a contract mismatch."""
    dirs, up, a, ep = _two_input_project(b, tmp_path, "optimistic")
    sigma = b.read(up)["extension"]["value"]
    favorable = 0.10 + one_sided_halfwidth(gauss(0.01), "plus", 0.95, False)
    fake_eval(b, "CALC-EP-1", "cand-A", ep, 0.7, {"--sigma": sigma, "--acc": favorable}, denominator={},
              upstream=[up, a], bound="optimistic")
    fake_eval(b, "CALC-EP-2", "cand-A", ep, 0.3, {"--sigma": sigma, "--acc": favorable}, denominator={},
              upstream=[up, a], bound="optimistic")
    fake_eval(b, "CALC-EP-3", "cand-A", ep, 0.3, {"--sigma": sigma, "--acc": 0.10}, denominator={},
              upstream=[up, a], bound="optimistic")
    d = derive(b, dirs)
    assert not error_codes(d, "CALC-EP-1") and not error_codes(d, "CALC-EP-2"), d["errors"]
    assert entry(d, "REQ-EP-001", "cand-A", "CALC-EP-1")["row"] == 10
    assert "design.contract_mismatch" in error_codes(d, "CALC-EP-3")
    # a separate requirement view: the meets case alone
    for f in ("evaluations/CALC-EP-1.json", "evaluations/CALC-EP-3.json"):
        b.path(f).unlink()
    for f in ("runs/CALC-EP-1.computational-run.json", "runs/CALC-EP-3.computational-run.json"):
        b.path(f).unlink()
    d = derive(b, dirs)
    assert entry(d, "REQ-EP-001", "cand-A", "CALC-EP-2")["row"] == 11


def case_t19_conservative_with_estimate_moved_unfavorable(b, tmp_path):
    """CMB-06: with a conservative input the acceptance estimate is fed at its unfavorable bound (smaller); the
    composite is conservative: meeting the target passes (row 13), missing it is bound.direction (row 14), never a
    fail."""
    dirs, up, a, ep = _two_input_project(b, tmp_path, "conservative", ep_fid="F3")
    unfav = 0.10 - one_sided_halfwidth(gauss(0.01), "minus", 0.95, False)
    for eid, val in (("CALC-EP-1", 0.3), ("CALC-EP-2", 0.7)):
        fake_eval(b, eid, "cand-A", ep, val, {"--sigma": 0.48797, "--acc": unfav}, denominator={},
                  upstream=[up, a], bound="conservative", uncertainty=gauss(0.01))
    d = derive(b, dirs)
    assert not error_codes(d, "CALC-EP"), d["errors"]
    # both evaluations share the requirement: check rows per evaluation
    rows = {r["evaluation"].split(":")[1]: r["row"] for r in matrix(d, "REQ-EP-001", "cand-A")["used"]}
    assert rows == {"CALC-EP-1": 13, "CALC-EP-2": 14}


def case_t20_reversed_optimistic_input_becomes_conservative(b, tmp_path):
    """CMB-03: a monotonic but reversed optimistic input is swapped to conservative before combining."""
    dirs, up, a, ep = _two_input_project(b, tmp_path, "optimistic-f3", direction="reversed", ep_fid="F3")
    sigma = b.read(up)["extension"]["value"]
    unfav = 0.10 - one_sided_halfwidth(gauss(0.01), "minus", 0.95, False)
    fake_eval(b, "CALC-EP-1", "cand-A", ep, 0.3, {"--sigma": sigma, "--acc": unfav}, denominator={},
              upstream=[up, a], bound="conservative")
    d = derive(b, dirs)
    assert not error_codes(d, "CALC-EP-1"), d["errors"]
    e = entry(d, "REQ-EP-001", "cand-A", "CALC-EP-1")
    assert e["bound"] == "conservative" and e["row"] == 13


def case_t21_uncertainty_below_minimum(b, tmp_path):
    """RUL-15, ADQ-01: an estimate uncertainty below the adequacy-table minimum (20% for the resolution core)."""
    c = res_contract()
    dirs = [write_contracts(tmp_path / "c", c)]
    fake_eval(b, "SIM-TRK-B", "cand-B", c, 0.3, uncertainty=gauss(0.01))
    assert entry(derive(b, dirs), "REQ-TRK-001", "cand-B", "SIM-TRK-B")["row"] == 15


def case_t22_counting_and_coverage_conversion(b, tmp_path):
    """RUL-15, RUL-16: a counting estimate (charge confusion) with only a Gaussian uncertainty, and a non-Gaussian
    estimate whose coverage differs from the table's, are uncertainty.missing."""
    cc = fake_contract("syn-cc4", "charge-confusion-rate", "estimate", "F4",
                       denominator={"rigidity_GV": "number", "species": "string", "charge_sign": "string",
                                    "curvature_offset_per_GV": "number"})
    r = res_contract()
    dirs = [write_contracts(tmp_path / "c", cc, r)]
    den = {"rigidity_GV": 1000.0, "species": "proton", "charge_sign": "positive", "curvature_offset_per_GV": 0.0}
    fake_eval(b, "SIM-CC-B", "cand-B", cc, 0.01, denominator=den, uncertainty=gauss(0.004), fidelity="F3")
    fake_eval(b, "SIM-TRK-B", "cand-B", r, 0.3, uncertainty=gauss(0.1, 0.6827, distribution="non-gaussian"))
    d = derive(b, dirs)
    assert entry(d, "REQ-TRK-001", "cand-B", "SIM-TRK-B")["row"] == 15
    assert one_sided_halfwidth(gauss(0.004), "plus", 0.95, True) is None
    assert one_sided_halfwidth(gauss(0.004, 0.90, distribution="exact"), "plus", 0.95, True) == 0.004


# ---------------------------------------------------------------- contract checks (T-32, T-47, T-34)


T32_MUTATIONS = [
    (lambda e: e["extension"].update(fidelity="F2"), "fidelity"),
    (lambda e: e["extension"].update(bound="estimate"), "bound"),
    (lambda e: e["extension"].update(parameter_refs=e["extension"]["parameter_refs"][:-1]), "parameter_refs"),
    (lambda e: e["extension"].update(value=e["extension"]["value"] * 0.9), "value"),
]


def case_t32_evaluation_contract_mismatch(tmp_path):
    """ART-60, TRC-02, TRC-08: fidelity, bound, parameter_refs or value that does not match the contract or output."""
    for k, (mutation, field) in enumerate(T32_MUTATIONS):
        b = copy_fixture(tmp_path / f"p{k}")
        edit(b, "evaluations/CALC-TRK-B.json", mutation)
        d = derive(b)
        assert "design.contract_mismatch" in error_codes(d, "CALC-TRK-B"), field
        assert matrix(d, "REQ-TRK-001", "cand-B")["result"] != "pass"


def case_t32_argv_not_recomputed_from_candidate(b):
    """ART-61: an argv input that differs from the value recomputed from the candidate (the run is rebound so the
    evaluation is not stale) is a contract mismatch; a stale evaluation is not compared."""
    run = "runs/CALC-TRK-B.computational-run.json"

    def bump(doc):
        argv = doc["extension"]["argv"]
        i = argv.index("--field-tesla")
        argv[i + 1] = "0.6"
    edit(b, run, bump)
    d = derive(b)
    assert entry(d, "REQ-TRK-001", "cand-B", "CALC-TRK-B")["code"] == "evidence.stale"
    assert not error_codes(d, "CALC-TRK-B")
    b.rebind("evaluations/CALC-TRK-B.json")
    d = derive(b)
    assert "design.contract_mismatch" in error_codes(d, "CALC-TRK-B")


def case_t47_below_crossover_labelled_optimistic(b):
    """FID-04, ART-48: an F1 resolution below the crossover rigidity is an estimate; labelled optimistic it is a
    contract mismatch."""
    rel = b.eval_resolution("CALC-TRK-A10", "cand-A", rigidity=10.0)
    assert b.read(rel)["extension"]["bound"] == "estimate"
    d = derive(b)
    assert not error_codes(d, "CALC-TRK-A10")
    edit(b, rel, lambda e: e["extension"].update(bound="optimistic"))
    assert "design.contract_mismatch" in error_codes(derive(b), "CALC-TRK-A10")


def case_t34_requirement_without_denominator_and_quadrature(b):
    """ART-10, ART-12, ART-64: the schema rejects a requirement without a denominator; a quadrature allocation without
    declared independence is a design error."""
    edit(b, "design-spec.v1.json", lambda s: s["extension"]["allocations"][0].pop("independent"))
    assert "design.allocation_dependence" in error_codes(derive(b))
    edit(b, "design-spec.v1.json", lambda s: s["extension"]["requirements"][0].pop("denominator"))
    d = derive(b)
    assert "design.malformed" in error_codes(d)


def case_binding_incomplete(b):
    """ART-21, TRC-02: an evaluation that does not bind its candidate or its run is a design error."""
    edit(b, "evaluations/CALC-TRK-B.json", lambda e: e.update(inputs=[i for i in e["inputs"]
                                                                       if not i["ref"].startswith("runs/")]))
    assert "design.binding_incomplete" in error_codes(derive(b), "CALC-TRK-B")


class DesignVerdictTests(unittest.TestCase):
    pass


attach_cases(DesignVerdictTests, globals())

if __name__ == "__main__":
    unittest.main()
