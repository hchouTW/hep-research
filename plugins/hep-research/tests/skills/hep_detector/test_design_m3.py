"""Detector system design M3 (engineering and review): F5 measurements and their approval (FID-06, FID-07, DEC-06;
T-27, T-28, T-43), the review gates H1-H4 and the review axis (MAT-04..MAT-08, DEC-12, DEC-13, DEC-20; T-39, T-40),
budget coupling between subsystems (CHN-14) and calibratability (CHN-16). Every project is the SYNTHETIC spectrometer
of tests/contracts/design_fixtures.py; decision records are written by the test as a human or an agent would."""
import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "tests" / "contracts"))
from contracts import design  # noqa: E402
from design_fixtures import NS, copy_fixture, decision, derive, edit, entry, matrix, param, sha256  # noqa: E402

EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
_spec = importlib.util.spec_from_file_location("evaluate_design_m3", EVAL)
EV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(EV)
DATASET = json.loads((PLUGIN / "contracts/fixtures/artifacts/valid/dataset_record.json").read_text())


def ev(b, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = EV.main([*map(str, args), "--artifacts", str(b.art)])
    return code, json.loads(buf.getvalue())


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.b = copy_fixture(self.root / "p")

    def tearDown(self):
        self.tmp.cleanup()

    def ok(self, *args):
        code, out = ev(self.b, *args)
        self.assertEqual(code, 0, out)
        return out


class F5(Base):
    def dataset(self, rel, value=0.3, sigma=0.08, field=0.5):
        ext = dict(DATASET["extension"], status="user-supplied", source_evidence_ids=[])
        ext.pop("experiment_profile", None)
        ext["design_measurement"] = {
            "figure_of_merit": "momentum-resolution-core", "denominator": {"rigidity_GV": 1000.0, "species": "proton"},
            "value": value, "uncertainty": {"minus": sigma, "plus": sigma, "coverage": 0.6827, "interval": "central",
                                            "distribution": "gaussian"},
            "configuration": {"DES-MAG-001.parameters.field_T": {"value": field, "unit": "T"},
                              "DES-TRK-001.parameters.point_resolution_um": {"value": 10.0, "unit": "um"}}}
        return self.b.write(rel, self.b.envelope("dataset-record", f"{NS}-beam-test", ext, status=("user-supplied",)))

    def accept(self, name, ds, cand="cand-B", actor="human"):
        cid = f"{NS}:{cand}"
        cfg = sorted(self.b.read(ds)["extension"]["design_measurement"]["configuration"])
        proj = design.Project(self.b.art)
        digest = proj.parameter_digest(cid, cfg)
        arts = [{"ref": ds, "sha256": sha256(self.b.path(ds))},
                {"ref": f"candidates/{cand}.json", "sha256": sha256(self.b.path(f"candidates/{cand}.json")),
                 "binding": "parameters", "parameter_digest": digest}]
        p = decision(self.b, name, "measurement-acceptance", [], actor=actor)
        rec = json.loads(p.read_text())
        rec["artifacts"] = arts
        p.write_text(json.dumps(rec))

    def test_t43_unapproved_then_approved(self):
        """FID-06, AGG-01: an F5 evaluation without measurement-acceptance is evidence.unreviewed; approved by a human
        it decides (row 16 pass, provisional)."""
        ds = self.dataset("data/beam.json")
        self.ok("f5", "--candidate", f"{NS}:cand-B", "--dataset", ds, "--id", "MEAS-B")
        e = entry(derive(self.b), "REQ-TRK-001", "cand-B", "MEAS-B")
        self.assertEqual(e["code"], "evidence.unreviewed")
        self.accept("ma-agent", ds, actor="agent")
        self.assertEqual(entry(derive(self.b), "REQ-TRK-001", "cand-B", "MEAS-B")["code"], "evidence.unreviewed")
        self.accept("ma", ds)
        d = derive(self.b)
        e = entry(d, "REQ-TRK-001", "cand-B", "MEAS-B")
        self.assertEqual((e["row"], e["verdict"]), (16, "pass"))
        m = matrix(d, "REQ-TRK-001", "cand-B")
        self.assertEqual((m["result"], m["provisional"]), ("pass", True))
        self.assertIn("user-supplied", m["maturity"]["status_axis"])  # MAT-09

    def test_t27_configuration_mismatch(self):
        """FID-07: a measurement made with another field than the candidate's is domain.mismatch."""
        ds = self.dataset("data/beam.json", field=0.4)
        self.ok("f5", "--candidate", f"{NS}:cand-B", "--dataset", ds, "--id", "MEAS-B")
        self.accept("ma", ds)
        e = entry(derive(self.b), "REQ-TRK-001", "cand-B", "MEAS-B")
        self.assertEqual(e["code"], "domain.mismatch")
        self.assertTrue(any("FID-07" in r for r in e["reasons"]))

    def test_t28_dataset_change_invalidates_the_approval(self):
        """DEC-06, RUL-02: a changed dataset-record invalidates the approval and makes the bound evaluation stale;
        after the evaluation is rewritten and before re-approval it is evidence.unreviewed."""
        ds = self.dataset("data/beam.json")
        self.ok("f5", "--candidate", f"{NS}:cand-B", "--dataset", ds, "--id", "MEAS-B")
        self.accept("ma", ds)
        self.dataset("data/beam.json", value=0.31)
        d = derive(self.b)
        self.assertEqual(entry(d, "REQ-TRK-001", "cand-B", "MEAS-B")["code"], "evidence.stale")
        self.b.path("evaluations/MEAS-B.json").unlink()
        self.ok("f5", "--candidate", f"{NS}:cand-B", "--dataset", ds, "--id", "MEAS-B")
        self.assertEqual(entry(derive(self.b), "REQ-TRK-001", "cand-B", "MEAS-B")["code"], "evidence.unreviewed")

    def test_other_parameter_change_keeps_the_approval(self):
        """DEC-06 from M2: the approval binds the candidate by its measurement-configuration parameters only."""
        ds = self.dataset("data/beam.json")
        self.ok("f5", "--candidate", f"{NS}:cand-B", "--dataset", ds, "--id", "MEAS-B")
        self.accept("ma", ds)
        edit(self.b, "candidates/cand-B.json", lambda d: d["extension"]["budgets"]["power"]["DES-TRK-001"]
             .update(estimate=130.0))
        self.assertEqual(entry(derive(self.b), "REQ-TRK-001", "cand-B", "MEAS-B")["row"], 16)


class Gates(Base):
    def gates(self):
        for name, cat, arts in (("h1", "design-scope", ["design-spec.v1.json"]),
                                ("h2", "requirements-baseline", ["design-spec.v1.json"]),
                                ("h3", "architecture-selection", ["candidates/cand-A.json", "candidates/cand-B.json"])):
            decision(self.b, name, cat, arts)

    def baseline(self, name="h4", actor="human", drop_eval=False, dispositions=True, report="design-report",
                 gates=True):
        if gates:
            self.gates()
        code, out = ev(self.b, "report", "--decisions", self.b.dec, "--name", report)
        self.assertEqual(code, 0, out)
        full = design.derive(self.b.art, self.b.dec)
        used = sorted({r["file"] for item in full["requirements"] + full["constraints"] for m in item["matrix"]
                       for r in m["used"]})
        if drop_eval:
            used = used[1:]
        disp = [{"requirement": item["id"], "disposition": "next-study", "note": "F3 and F4 studies"}
                for item in full["requirements"] if item["kind"] == "driving"
                and any(m["result"] == "inconclusive" for m in item["matrix"])]
        extra = {"dispositions": disp if dispositions else disp[:-1]}
        return decision(self.b, name, "design-baseline", [out["report"], *used], actor=actor, **extra)

    def test_valid_h4_sets_the_review_axis(self):
        self.baseline()
        d = derive(self.b)
        self.assertTrue(d["review"]["reviewed"], d["review"])
        self.assertEqual(d["baseline"], "baselined")
        self.assertEqual(matrix(d, "REQ-TRK-001", "cand-A")["maturity"]["review_axis"], "reviewed")

    def test_t40_invalid_h4_never_sets_it(self):
        """MAT-04, DEC-20: an agent actor, artifacts[] that is not the report's set, missing dispositions, or a hash
        that changed after approval; also (interpretation, H4 follows H1-H3) a record taken while an earlier gate is
        open."""
        cases = {"agent": dict(actor="agent"), "artifacts": dict(drop_eval=True), "dispositions": dict(dispositions=False),
                 "gates-open": dict(gates=False)}
        for label, kw in cases.items():
            with self.subTest(case=label):
                b = copy_fixture(self.root / f"q-{label}")
                self.b = b
                self.baseline(**kw)
                d = derive(b)
                self.assertFalse(d["review"]["reviewed"], label)
                self.assertEqual(matrix(d, "REQ-TRK-001", "cand-A")["maturity"]["review_axis"], "not-reviewed")
        self.b = copy_fixture(self.root / "q-hash")
        self.baseline()
        self.assertTrue(derive(self.b)["review"]["reviewed"])
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"].update(description="changed"))  # MAT-06
        d = derive(self.b)
        self.assertFalse(d["review"]["reviewed"])

    def test_recomputed_report_must_match(self):
        """MAT-04 (e): a new evaluation after approval changes the recomputed report; the review axis reverts."""
        self.baseline()
        self.ok("budget", "--candidate", f"{NS}:cand-A", "--quantity", "mass", "--id", "CALC-M")
        d = derive(self.b)
        self.assertFalse(d["review"]["reviewed"])
        self.assertTrue(any("recomputed" in r for rec in d["review"]["records"] for r in rec["reasons"]))

    def test_t39_h1_to_h3_clear_flags_only(self):
        """MAT-07: H1-H3 clear their gate flags and leave the review axis unchanged."""
        for name, cat, arts in (("h1", "design-scope", ["design-spec.v1.json"]),
                                ("h2", "requirements-baseline", ["design-spec.v1.json"]),
                                ("h3", "architecture-selection", ["candidates/cand-A.json", "candidates/cand-B.json"])):
            decision(self.b, name, cat, arts)
        d = derive(self.b)
        self.assertEqual(d["gate_flags"], [])
        self.assertFalse(d["review"]["reviewed"])
        self.assertEqual(matrix(d, "REQ-TRK-001", "cand-A")["maturity"]["review_axis"], "not-reviewed")


class EngineeringCoupling(Base):
    def test_chn14_services_couple_subsystems(self):
        """CHN-14: services another subsystem adds enter the tracker material budget; changing them makes that
        evaluation stale, changing an unrelated parameter does not."""
        def add(doc):
            subs = doc["extension"]["subsystems"]
            subs["DES-MAG-001"]["parameters"]["services_x_over_x0"] = param(0.02, "1")
        edit(self.b, "candidates/cand-A.json", add)
        out = self.ok("run", "--candidate", f"{NS}:cand-A", "--figure-of-merit", "material-budget", "--id", "CALC-MAT")
        ext = self.b.read(out["evaluation"])["extension"]
        self.assertAlmostEqual(ext["value"], 0.09 + 0.03 + 0.02)
        self.assertIn("DES-MAG-001.parameters.services_x_over_x0", ext["parameter_refs"])
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["budgets"]["power"]["DES-MAG-001"]
             .update(estimate=1.0))
        self.assertNotIn(f"{NS}:CALC-MAT", derive(self.b)["stale_evaluations"])
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["parameters"]
             ["services_x_over_x0"].update(value=0.05))
        self.assertIn(f"{NS}:CALC-MAT", derive(self.b)["stale_evaluations"])

    def test_chn16_calibration_needs_a_control_sample(self):
        edit(self.b, "candidates/cand-A.json", lambda d: d["extension"]["subsystems"]["DES-MAG-001"]["calibration"]
             .update(control_samples=[]))
        self.assertIn("design.calibration_incomplete", {e["code"] for e in derive(self.b)["errors"]})


if __name__ == "__main__":
    unittest.main()
