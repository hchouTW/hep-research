"""Detector system design M0: per-requirement aggregation (AGG-*), maturity (MAT-*), invalidation (TRC-*), gate flags
(DEC-02, DEC-07..DEC-09, DEC-12 for H1-H3), decision record 1.1.0 and the not-applicable marker (DEC-03..DEC-16) of
contracts/design.py and contracts/lineage.py, on the SYNTHETIC spectrometer project. Test ids follow section 8 (T-xx)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from contracts.design import main as design_main  # noqa: E402
from contracts.lineage import check_decision, main as lineage_main  # noqa: E402
from design_fixtures import (attach_cases, NS, OUT, decision, derive, edit, entry, fake_contract,  # noqa: E402
                             fake_eval, gauss, magnet_subsystem, matrix, sha256, write_contracts)

RES = "momentum-resolution-core"


def contracts(tmp_path, *docs):
    return [write_contracts(tmp_path / "c", *docs)]


# ---------------------------------------------------------------- aggregation steps (T-55 and the T-xx cases)


def case_t15_conflict_row10_fail_and_row13_pass(b, tmp_path):
    """AGG-02, RPT-04: a row-10 fail and a row-13 pass of the same requirement are evidence.conflict, with both
    contracts marked for inspection."""
    c = fake_contract("syn-cons", RES, "conservative", "F3")
    dirs = contracts(tmp_path, c)
    fake_eval(b, "SIM-TRK-P", "cand-P", c, 0.5)
    m = matrix(derive(b, dirs), "REQ-TRK-001", "cand-P")
    assert (m["result"], m["codes"]) == ("inconclusive", ["evidence.conflict"])
    assert {x["contract"] for x in m["conflict_inspect"]} == {"tracker-resolution:momentum", "syn-cons:run"}
    assert m["maturity"]["fidelity_axis"] == "undetermined"


def case_t16_row10_fail_without_pass(b):
    """AGG-03: a row-10 fail and no pass: the requirement fails; maturity is the deciding evaluation's vector."""
    m = matrix(derive(b), "REQ-TRK-001", "cand-P")
    assert m["result"] == "fail"
    assert m["maturity"]["lowest_chain_fidelity"] == "F1"
    assert m["maturity"]["fidelity_axis"][0]["fidelity_vector"][0]["fidelity"] == "F1"


def case_t17_orphan_run(b):
    """AGG-08: deleting an F1 fail evaluation and keeping its run leaves an orphan run; the requirement for that
    candidate and figure of merit is at most inconclusive, evidence.orphan_run."""
    b.path("evaluations/CALC-TRK-P.json").unlink()
    d = derive(b)
    assert [o["run"] for o in d["orphan_runs"]] == ["runs/CALC-TRK-P.computational-run.json"]
    m = matrix(d, "REQ-TRK-001", "cand-P")
    assert m["result"] == "inconclusive" and "evidence.orphan_run" in m["codes"]
    assert m["maturity"]["fidelity_axis"] == "undetermined"


def case_t24_copies_aggregated_together(b):
    """AGG-00: a copy of a candidate with the same parameters and another id is the same effective candidate."""
    doc = b.read("candidates/cand-A.json")
    doc["artifact_id"] = f"{NS}-cand-A2"
    doc["extension"]["candidate_id"] = f"{NS}:cand-A2"
    b.write("candidates/cand-A2.json", doc)
    b.eval_resolution("CALC-TRK-A2", "cand-A2")
    d = derive(b)
    m = matrix(d, "REQ-TRK-001", "cand-A")
    assert m["candidates"] == [f"{NS}:cand-A", f"{NS}:cand-A2"]
    assert {r["evaluation"] for r in m["used"]} == {f"{NS}:CALC-TRK-A", f"{NS}:CALC-TRK-A2"}


def case_t25_highest_fidelity_decides(b, tmp_path):
    """AGG-04: an F3 estimate pass and an F1 optimistic bound that meets the target: the F3 level decides (pass)."""
    c = fake_contract("syn-res", RES, "estimate", "F3")
    dirs = contracts(tmp_path, c)
    fake_eval(b, "SIM-TRK-B", "cand-B", c, 0.3, uncertainty=gauss(0.07))
    m = matrix(derive(b, dirs), "REQ-TRK-001", "cand-B")
    assert (m["result"], m["provisional"]) == ("pass", True)
    assert m["maturity"]["lowest_chain_fidelity"] == "F3"


def case_t29_same_level_contradiction(b, tmp_path):
    """AGG-04: two F3 estimates of the same level, one pass and one fail: evidence.conflict."""
    c1 = fake_contract("syn-res", RES, "estimate", "F3")
    c2 = fake_contract("syn-res2", RES, "estimate", "F3")
    dirs = contracts(tmp_path, c1, c2)
    fake_eval(b, "SIM-TRK-B", "cand-B", c1, 0.3, uncertainty=gauss(0.07))
    fake_eval(b, "SIM-TRK-B2", "cand-B", c2, 0.95, uncertainty=gauss(0.2))
    m = matrix(derive(b, dirs), "REQ-TRK-001", "cand-B")
    assert (m["result"], m["codes"]) == ("inconclusive", ["evidence.conflict"])


def case_t30_all_inconclusive_lists_codes(b, tmp_path):
    """AGG-04: all evaluations at the top level inconclusive: every reason code is listed; AGG-05 when every
    evaluation is excluded."""
    c = fake_contract("syn-res1", RES, "estimate", "F1")
    dirs = contracts(tmp_path, c)
    fake_eval(b, "CALC-TRK-A1", "cand-A", c, 0.45, uncertainty=gauss(0.1))   # F1 estimate: row 12
    m = matrix(derive(b, dirs), "REQ-TRK-001", "cand-A")
    assert (m["result"], m["codes"]) == ("inconclusive", ["bound.direction", "fidelity.insufficient"])
    edit(b, "candidates/cand-B.json", lambda d: d["extension"].update(description="changed"))
    m = matrix(derive(b), "REQ-TRK-001", "cand-B")
    assert (m["result"], m["codes"]) == ("inconclusive", ["evidence.stale"])  # AGG-05: all excluded


def case_t44_excluded_adverse(b, tmp_path):
    """AGG-01, TRC-09: a stale evaluation whose value is on the non-compliant side blocks a pass of the others."""
    c = fake_contract("syn-cons", RES, "conservative", "F3")
    dirs = contracts(tmp_path, c)
    edit(b, "runs/CALC-TRK-P.computational-run.json", lambda d: d["extension"].update(tolerances={"x": 1}))
    fake_eval(b, "SIM-TRK-P", "cand-P", c, 0.5)
    m = matrix(derive(b, dirs), "REQ-TRK-001", "cand-P")
    assert m["result"] == "inconclusive"
    assert "evidence.excluded_adverse" in m["codes"]
    assert any(r["code"] == "evidence.stale" for r in m["skipped"])  # AGG-06: listed with its reason


def case_t45_optimistic_fail_and_estimate_pass(b, tmp_path):
    """AGG-02, CMB-05: an optimistic-bound fail together with an estimate pass is evidence.conflict."""
    c = fake_contract("syn-res", RES, "estimate", "F3")
    dirs = contracts(tmp_path, c)
    fake_eval(b, "SIM-TRK-P", "cand-P", c, 0.3, uncertainty=gauss(0.07))
    m = matrix(derive(b, dirs), "REQ-TRK-001", "cand-P")
    assert (m["result"], m["codes"]) == ("inconclusive", ["evidence.conflict"])


def case_t55_step5_no_evaluations(b):
    """AGG-05: a requirement without evaluations is inconclusive and status lists it as missing evaluations."""
    d = derive(b)
    m = matrix(d, "CON-MASS-001", "cand-A")
    assert (m["result"], m["missing_evaluations"]) == ("inconclusive", True)
    out = []
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = design_main(["status", "--artifacts", str(b.art), "--decisions", str(b.dec)])
    out = json.loads(buf.getvalue())
    assert rc == 0
    assert any(x["id"].endswith("CON-MASS-001") for x in out["missing_evaluations"])
    assert out["screened_out"] == [[f"{NS}:cand-P"]]


def case_t38_status_axis_carries_sticky_statuses(b):
    """MAT-09, RPT-09: the compliance matrix carries the sources' sticky statuses (synthetic, user-supplied)."""
    m = matrix(derive(b), "REQ-TRK-001", "cand-A")
    assert m["maturity"]["status_axis"] == ["synthetic"]
    b.candidate("cand-U", {"DES-TRK-001": b.read("candidates/cand-B.json")["extension"]["subsystems"]["DES-TRK-001"],
                           "DES-MAG-001": magnet_subsystem(0.45)}, None, status=("synthetic", "user-supplied"))
    b.eval_resolution("CALC-TRK-U", "cand-U")
    m = matrix(derive(b), "REQ-TRK-001", "cand-U")
    assert m["maturity"]["status_axis"] == ["synthetic", "user-supplied"]


def case_report_cannot_choose_evaluations(b, tmp_path):
    """AGG-06, AGG-07: every evaluation of the figure of merit and effective candidate is listed as used or skipped."""
    d = derive(b)
    for c in ("A", "B", "P"):
        m = matrix(d, "REQ-TRK-001", f"cand-{c}")
        assert {r["evaluation"] for r in m["used"] + m["skipped"]} == {f"{NS}:CALC-TRK-{c}"}


# ---------------------------------------------------------------- invalidation (T-26, T-36, T-37)


def case_t26_staleness_propagates(b):
    """RUL-02, TRC-09: the upstream tracking evaluation stale (its run changed), the downstream charge-confusion
    evaluation file unchanged: the downstream is stale too."""
    edit(b, "runs/CALC-TRK-A.computational-run.json", lambda d: d["extension"].update(tolerances={"x": 1}))
    d = derive(b)
    assert entry(d, "REQ-CC-001", "cand-A", "CALC-CC-A")["code"] == "evidence.stale"
    assert f"{NS}:CALC-CC-A" in d["stale_evaluations"]


def case_t36_base_change_stales_variants(b):
    """ART-21, TRC-03 (M0): changing the base candidate makes every evaluation of its variants stale."""
    b.candidate("cand-A-v", None, None, derived_from="cand-A",
                overrides={"DES-TRK-001": {"parameters": {"point_resolution_um": {"value": 8.0, "unit": "um",
                                                                                  "source": "variant", "status": "proposal"}}}})
    b.eval_resolution("CALC-TRK-Av", "cand-A-v")
    d = derive(b)
    assert not d["errors"], d["errors"]
    assert entry(d, "REQ-TRK-001", "cand-A-v", "CALC-TRK-Av")["row"] == 11
    edit(b, "candidates/cand-A.json", lambda d: d["extension"]["budgets"]["power"]["DES-TRK-001"].update(estimate=300.0))
    d = derive(b)
    assert entry(d, "REQ-TRK-001", "cand-A-v", "CALC-TRK-Av")["code"] == "evidence.stale"


def case_t37_field_change_stales_all_candidate_evaluations(b):
    """TRC-10, TRC-03 (M0): changing the B field makes all evaluations of that candidate stale."""
    edit(b, "candidates/cand-B.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["parameters"]["field_T"]
         .update(value=0.6))
    d = derive(b)
    assert set(d["stale_evaluations"]) == {f"{NS}:CALC-TRK-B", f"{NS}:CALC-CC-B"}


# ---------------------------------------------------------------- gates (T-49, DEC-02, DEC-12)


def case_gate_flags_and_h1_h2(b):
    """DEC-02, DEC-12: missing gates are flags that never block computation; valid human H1 and H2 records that list
    exactly the current design-spec clear them; an agent record does not (DEC-05)."""
    d = derive(b)
    assert d["gate_flags"] == ["gate.H1_missing", "gate.H2_missing", "gate.H3_missing"]
    decision(b, "h1", "design-scope", ["design-spec.v1.json"], actor="agent")
    assert "gate.H1_missing" in derive(b)["gate_flags"]
    decision(b, "h1", "design-scope", ["design-spec.v1.json"])
    decision(b, "h2", "requirements-baseline", ["design-spec.v1.json"])
    assert derive(b)["gate_flags"] == ["gate.H3_missing"]
    decision(b, "h2", "requirements-baseline", ["design-spec.v1.json", "candidates/cand-A.json"])  # not exact
    assert "gate.H2_missing" in derive(b)["gate_flags"]


def case_h3_architecture_selection(b):
    """DEC-12: H3 lists the candidates entering convergence; each needs a screening-level evaluation per requirement
    and must not be screened out."""
    decision(b, "h3", "architecture-selection", ["candidates/cand-A.json", "candidates/cand-B.json"])
    assert "gate.H3_missing" not in derive(b)["gate_flags"]
    decision(b, "h3", "architecture-selection", ["candidates/cand-A.json", "candidates/cand-P.json"])
    assert "gate.H3_missing" in derive(b)["gate_flags"]  # cand-P is screened out


def case_t49_new_spec_version(b):
    """DEC-07..DEC-09, ART-14: a new design-spec version without a requirement-change record is flagged; with one it
    becomes current and the H1 and H2 records of the old version no longer cover it."""
    decision(b, "h1", "design-scope", ["design-spec.v1.json"])
    decision(b, "h2", "requirements-baseline", ["design-spec.v1.json"])
    assert {"gate.H1_missing", "gate.H2_missing"}.isdisjoint(derive(b)["gate_flags"])
    b.spec(2, created="2026-10-25", resolution_target=0.5)
    d = derive(b)
    assert "gate.requirement_change_missing" in d["gate_flags"] and d["spec_version"] == 1
    decision(b, "rc1", "requirement-change", ["design-spec.v1.json", "design-spec.v2.json"])
    d = derive(b)
    assert d["spec_version"] == 2 and "gate.requirement_change_missing" not in d["gate_flags"]
    assert {"gate.H1_missing", "gate.H2_missing"} <= set(d["gate_flags"])


# ---------------------------------------------------------------- decision record 1.1.0 (T-41, T-42, T-59)


def _record(b, artifacts, category="design-baseline", **kw):
    rec = {"record_version": "1.1.0", "decision_id": "d1", "analysis": NS, "decision": "synthetic",
           "category": category, "actor": {"kind": "human", "id": "fixture-reviewer"}, "time": "2026-10-24T12:00:00Z",
           "seen": {"state": "not-applicable"},
           "artifacts": [{"ref": r, "sha256": sha256(b.path(r))} for r in artifacts]}
    rec.update(kw)
    return rec


def _dataset(b, rel, status, envelope_status=("unvalidated",)):
    ext = json.loads((ROOT / "contracts/fixtures/artifacts/valid/dataset_record.json").read_text())["extension"]
    ext = dict(ext, status=status, source_evidence_ids=["synthetic:src-1"] if status in ("published", "preliminary") else [])
    ext.pop("experiment_profile", None)
    doc = b.envelope("dataset-record", f"{NS}-ds-{status}", ext, status=envelope_status)
    return b.write(rel, doc)


def case_t41_not_applicable_refused_on_experimental_or_external_data(b):
    """DEC-14, DEC-15, TRC-11: the marker is refused when the closure holds a published or preliminary dataset, an
    observed artifact, an external input, or a protected input."""
    from contracts.validate import validate_artifact
    rel = "evaluations/CALC-TRK-A.json"
    assert check_decision(_record(b, [rel]), None, b.art).ok
    for status in ("published", "preliminary"):
        ds = _dataset(b, f"data/{status}.json", status)
        assert validate_artifact(b.read(ds)).ok, [f.code for f in validate_artifact(b.read(ds)).errors]
        if True:
            edit(b, rel, lambda d: d["inputs"].append(b.inp(ds)))
            rep = check_decision(_record(b, [rel]), None, b.art)
            assert "lineage.not_applicable_refused" in {f.code for f in rep.errors}, status
            edit(b, rel, lambda d: d["inputs"].pop())
    edit(b, rel, lambda d: d["inputs"].append({"ref": "hepdata:ins123/t1", "external": True}))
    assert "lineage.not_applicable_refused" in {f.code for f in check_decision(_record(b, [rel]), None, b.art).errors}
    edit(b, rel, lambda d: d["inputs"].pop())
    (b.root / "hep-research.project.json").write_text(json.dumps({"agent_policy": {"protected_paths": ["artifacts/candidates"]}}))
    assert "lineage.not_applicable_refused" in {f.code for f in check_decision(_record(b, [rel]), None, b.art).errors}
    (b.root / "hep-research.project.json").unlink()
    assert "lineage.closure_unchecked" in {f.code for f in check_decision(_record(b, [rel]), None, None).errors}


def case_t42_user_supplied_f5_accepted(b):
    """DEC-15: an H4 record covering user-supplied F5 data with the marker is accepted."""
    from contracts.validate import validate_artifact
    ds = _dataset(b, "data/prototype.json", "user-supplied", ("user-supplied",))
    assert validate_artifact(b.read(ds)).ok, [f.code for f in validate_artifact(b.read(ds)).errors]
    rep = check_decision(_record(b, [ds, "evaluations/CALC-TRK-A.json"]), None, b.art)
    assert rep.ok, [f.as_dict() for f in rep.findings]


def case_t59_decision_record_versions(b):
    """DEC-04, DEC-11, DEC-13, DEC-14: 1.0.0 records keep validating; 1.1.0 additions need 1.1.0 and a design
    category; a design record lists at least one artifact."""
    from contracts.schema import validate
    old = {"record_version": "1.0.0", "decision_id": "x", "analysis": "a", "decision": "d", "category": "binning",
           "actor": {"kind": "human", "id": "p"}, "time": "2026-10-24T12:00:00Z",
           "seen": {"through_seq": 0, "entries_sha256": "0" * 64}, "artifacts": []}
    assert validate(old, "decision_record.json").ok
    codes = {f.code for f in check_decision(dict(old, category="design-scope"), None, None).errors}
    assert "lineage.needs_1_1_0" in codes
    codes = {f.code for f in check_decision(_record(b, [], category="binning", record_version="1.1.0"), None, b.art).errors}
    assert "lineage.not_applicable_not_design" in codes
    assert "lineage.design_no_artifacts" in {f.code for f in check_decision(_record(b, []), None, b.art).errors}


def case_lineage_cli_marker_needs_no_exposure(b, tmp_path):
    """DEC-16: lineage.py decision accepts the marker without --exposure; other records still need it."""
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(_record(b, ["design-spec.v1.json"], category="design-scope")))
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        assert lineage_main(["decision", str(p), "--artifacts-root", str(b.art)]) == 0
    old = _record(b, ["design-spec.v1.json"], category="design-scope", seen={"through_seq": 0, "entries_sha256": "0" * 64})
    p.write_text(json.dumps(old))
    with contextlib.redirect_stdout(io.StringIO()):
        assert lineage_main(["decision", str(p), "--artifacts-root", str(b.art)]) == 2


def case_committed_fixture_is_current():
    """The committed project derives without errors (regenerate with tests/contracts/design_fixtures.py)."""
    from contracts.design import derive as _derive
    d = _derive(OUT / "artifacts", OUT / "decisions")
    assert d["status"] == "ok", d["errors"]
    assert not shutil.which("nonexistent-binary")


class DesignAggregationTests(unittest.TestCase):
    pass


attach_cases(DesignAggregationTests, globals())

if __name__ == "__main__":
    unittest.main()
