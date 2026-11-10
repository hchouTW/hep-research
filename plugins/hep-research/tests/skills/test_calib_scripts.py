"""The phase-0 calib_*.py scripts of the simulator calibration workflow (skills/hep-statistics/scripts): JSON out with a
status, exit codes 0 normal, 1 negative decision, 2 input error, 3 incomplete (Part B section 14 conventions), and an
end-to-end ledger flow through calib_data.py with a decision-record stub (section 17)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "core"))

import calibration_fixtures as F  # noqa: E402
import calibration_phase1 as H  # noqa: E402

sys.path.insert(0, str(ROOT))
from core.calibration import data_release as data  # noqa: E402

S = ROOT / "skills" / "hep-statistics" / "scripts"
FIXTURE_DIR = ROOT / "core" / "calibration" / "data"


def run(script, *args):
    res = subprocess.run([sys.executable, "-I", str(S / script), *map(str, args)], capture_output=True, text=True,
                         timeout=120)
    return res.returncode, json.loads(res.stdout)


def inputs(**kw):
    c = dict(incomplete=False, mandatory_gate_failed=False, real_data=True, vmode="holdout", design_only=False,
             p7_failed=False, v_pass=True, power_ok=True, testable_ok=True, validation_data_reuse="none",
             validation_data_simulated=False, earlier_failure_record="none", own_flags=[])
    c.update(kw)
    return c


class Scripts(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.d = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def put(self, name, value):
        p = self.d / name
        p.write_text(json.dumps(value))
        return p

    def test_calib_use(self):
        rc, out = run("calib_use.py", "judge", "--inputs", self.put("a.json", {"inputs": inputs(), "upstreams": []}))
        self.assertEqual((rc, out["status"], out["effective_grade"]), (0, "ok", "validated-in-scope"))
        rc, out = run("calib_use.py", "judge", "--inputs", self.put("b.json", {
            "inputs": inputs(vmode="cross-validation", earlier_failure_record="pending"), "upstreams": []}))
        self.assertEqual((rc, out["status"], out["own_grade"]), (3, "incomplete", None))
        rc, out = run("calib_use.py", "lookup", "--undecided", "mandatory-gate", "--inputs", self.put("c.json", {
            "inputs": inputs(incomplete=True), "upstreams": [{"usages": ["phi-center"], "effective_grade": "failed", "flags": []}]}))
        self.assertEqual((rc, out["determined"], out["effective_grade"]), (0, True, "failed"))
        rc, out = run("calib_use.py", "lookup", "--undecided", "v", "--inputs", self.put("e.json", {"inputs": inputs()}))
        self.assertEqual((rc, out["status"]), (2, "rejected"))          # undecided without incomplete (review F1)
        rc, out = run("calib_use.py", "judge", "--inputs", self.put("d.json", {"inputs": inputs(vmode="k-fold")}))
        self.assertEqual((rc, out["status"]), (2, "rejected"))

    def test_calib_deps(self):
        rc, out = run("calib_deps.py", "roles", "--contract", self.put("c.json", {"upstream": [
            {"result_sha256": F.h("u"), "usages": ["envelope", "xi"], "role": "variation"}]}))
        self.assertEqual((rc, out["findings"][0]["code"]), (1, "upstream.role_mismatch"))
        rc, out = run("calib_deps.py", "cycles", "--graph", self.put("g.json", {"a": ["b"], "b": ["a"]}))
        self.assertEqual((rc, out["cycle"]), (1, ["a", "b", "a"]))
        payload = {"contract_sha256": F.h("c"), "data_sha256": F.h("d"), "plan_sha256": F.h("p"),
                   "engine_version": "0.1.0", "parent_versions": [], "values": {}}
        rc, v = run("calib_deps.py", "version", "--payload", self.put("p.json", payload))
        self.assertEqual(rc, 0)
        rc, out = run("calib_deps.py", "finalize", "--result", self.put("r.json", {"x": 1}), "--payload",
                      self.d / "p.json", "--out", self.d / "final.json")
        self.assertEqual((rc, out["version_id"]), (0, v["version_id"]))
        self.assertEqual(json.loads((self.d / "final.json").read_text())["result_sha256"], out["result_sha256"])

    def test_calib_chain(self):
        for name in ("ecal", "rich", "tracker"):
            rc, out = run("calib_chain.py", "candidates", "--contract", FIXTURE_DIR / f"{name}.json")
            self.assertEqual((rc, out["status"]), (0, "ok"), name)
            rc, out = run("calib_chain.py", "p4", "--contract", FIXTURE_DIR / f"{name}.json")
            self.assertEqual((rc, out["status"]), (0, "passed"), name)
        fx = json.loads((FIXTURE_DIR / "toy_detector_subgraph.json").read_text())
        fx["contract"]["references"] = [dict(r, enabled=r["id"] == "single_photoelectron")
                                        for r in fx["contract"]["references"]]
        rc, out = run("calib_chain.py", "p4", "--contract", self.put("sub.json", fx))
        self.assertEqual((rc, out["status"], out["remedy_level"]), (1, "failed", "contract"))

    def test_calib_contract(self):
        rels = F.releases()
        cal, val = data.release_hash(rels[F.CAL]), data.release_hash(rels[F.VAL])
        args = ["--release", self.put("cal.json", rels[F.CAL]), "--release", self.put("val.json", rels[F.VAL])]
        good = F.contract()
        good["data"] = {"calibration_releases": [cal], "validation_releases": [val]}
        rc, out = run("calib_contract.py", "check", "--contract", self.put("c.json", good), *args)
        self.assertEqual((rc, out["status"]), (0, "accepted"), out.get("findings"))
        rc, out = run("calib_contract.py", "check", "--contract", self.d / "c.json", "--release",
                      self.put("lie.json", dict(rels[F.CAL], release_sha256=F.h("other"))))
        self.assertEqual((rc, out["status"]), (2, "rejected"))          # a declared hash is verified (review F12)
        bad = dict(good)
        bad["models"] = {"enumerated": [{"id": "nominal"}], "absorbed": [{"id": "nominal"}]}
        rc, out = run("calib_contract.py", "check", "--contract", self.put("bad.json", bad), *args)
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        rc, out = run("calib_contract.py", "check", "--contract", self.put("shape.json", {"schema": "x"}))
        self.assertEqual((rc, out["stage"]), (2, "schema"))

    def test_calib_data_flow(self):
        led = self.d / "ledger.json"
        self.assertEqual(run("calib_data.py", "init", "--ledger", led)[0], 0)
        self.assertEqual(run("calib_data.py", "init", "--ledger", led)[0], 2)          # never reset
        k1, k2 = F.h("kappa-1"), F.h("kappa-2")
        rx = {"lineage": {"raw_units": ["x1", "x2"]}}
        ry = {"lineage": {"raw_units": ["y1"]}}
        hx, hy = data.release_hash(rx), data.release_hash(ry)
        relx, rely = self.put("rx.json", rx), self.put("ry.json", ry)
        x = self.put("x.json", ["x1", "x2"])
        ch1 = self.put("ch1.json", {"contract_sha256": F.h("c1")})
        ch2 = self.put("ch2.json", {"contract_sha256": F.h("c2")})
        rc, out = run("calib_data.py", "open", "--ledger", led, "--kappa", k1, "--vmode", "holdout", "--release", relx,
                      "--release", rely, "--calibration", hx, "--validation", hy, "--channel", ch1)
        self.assertEqual((rc, out["opening_seq"], out["calibration_units"]), (0, 1, 2))
        run("calib_data.py", "open", "--ledger", led, "--kappa", k2, "--vmode", "cross-validation", "--release", relx,
            "--calibration", hx, "--channel", ch2)
        rc, out = run("calib_data.py", "inputs", "--ledger", led, "--kappa", k2, "--vmode", "cross-validation",
                      "--validation-units", x, "--calibration-units", x)
        self.assertEqual((rc, out["earlier_failure_record"]), (0, "pending"))
        stub = self.put("dec.json", {"kappa": k1, "outcome": "fail"})                 # hand-written stub (phase 0)
        self.assertEqual(run("calib_data.py", "decide", "--ledger", led, "--decision", stub)[1]["record_status"], "final")
        rc, out = run("calib_data.py", "inputs", "--ledger", led, "--kappa", k2, "--vmode", "cross-validation",
                      "--validation-units", x, "--calibration-units", x)
        self.assertEqual(out["earlier_failure_record"], "final")
        # a holdout whose releases share raw units, or an unmet opening condition: refused, nothing recorded
        rxy = self.put("rxy.json", {"lineage": {"raw_units": ["x2", "y9"]}})
        hxy = data.release_hash({"lineage": {"raw_units": ["x2", "y9"]}})
        before = json.loads(led.read_text())["seq"]
        rc, out = run("calib_data.py", "open", "--ledger", led, "--kappa", F.h("kappa-3"), "--vmode", "holdout",
                      "--release", relx, "--release", rxy, "--calibration", hx, "--validation", hxy, "--channel", ch1)
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        cond = self.put("cond.json", {c: True for c in data.OPENING_PRECONDITIONS} | {"p7_not_incomplete": False})
        rc, out = run("calib_data.py", "open", "--ledger", led, "--kappa", F.h("kappa-4"), "--vmode", "holdout",
                      "--release", relx, "--release", rely, "--calibration", hx, "--validation", hy, "--channel", ch1,
                      "--conditions", cond)
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        self.assertEqual(json.loads(led.read_text())["seq"], before)
        Path(f"{led}.lock").write_text("other writer")
        rc, out = run("calib_data.py", "draft", "--ledger", led, "--series", "s")
        self.assertEqual((rc, out["status"]), (2, "rejected"))                          # single writer
        rc, out = run("calib_data.py", "ingest", "--release", self.put("r.json", {"observables": []}))
        self.assertEqual(rc, 1)



class Phase1Scripts(unittest.TestCase):
    """The phase-1 scripts (section 17): JSON with a status and the section 14 exit codes."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.d = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def put(self, name, value):
        p = self.d / name
        p.write_text(json.dumps(value))
        return p

    def chain(self, case):
        c, p = case
        return self.put("c.json", c), self.put("p.json", p)

    def test_calib_design(self):
        fx = FIXTURE_DIR / "toy_detector_design.json"
        rc, out = run("calib_design.py", "p2", "--contract", fx)
        self.assertEqual((rc, out["status"], out["ndf"]), (0, "passed", 15))
        rc, out = run("calib_design.py", "points", "--contract", fx, "--n", 8, "--seed", 1, "--held-back", 2)
        self.assertEqual((rc, len(out["training"]), len(out["held_back"])), (0, 6, 2))
        rc, out = run("calib_design.py", "applicability", "--plan", self.put("m.json", {"methods": {"a": "rerun"}}))
        self.assertEqual((rc, out["gates"]["P0"], out["gates"]["G4"]), (0, "applicable", "not-applicable"))
        c, p = self.chain(H.gaussian_chain())
        rc, out = run("calib_design.py", "p5", "--contract", c, "--plan", p, "--items", "ess", "--declared-methods")
        self.assertEqual((rc, out["status"], out["findings"][0]["code"]), (1, "failed", "p5.ess"))
        rc, out = run("calib_design.py", "p5", "--contract", c, "--plan", p, "--items", "ess")    # final method first
        self.assertEqual((rc, out["status"], out["moved_to_next_tier"]), (0, "passed", {"mu": "resimulation"}))
        rc, out = run("calib_design.py", "p5", "--contract", c, "--plan", p, "--items", "bogus")
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        c, p = self.chain(H.poisson_chain())
        rc, out = run("calib_design.py", "methods", "--contract", c, "--plan", p)
        self.assertEqual((rc, out["methods"]), (0, {"rate": "resimulation"}))
        rc, out = run("calib_design.py", "support", "--contract", *self.chain(H.uniform_chain())[:1], "--plan",
                      self.d / "p.json")
        self.assertEqual((rc, out["findings"][0]["code"]), (1, "support.missing"))
        cc, pp = H.gaussian_chain()
        pp["evaluator"] = {"kind": "g4sim"}
        rc, out = run("calib_design.py", "p5", "--contract", self.put("c2.json", cc), "--plan", self.put("p2.json", pp))
        self.assertEqual((rc, out["status"]), (3, "incomplete"))

    def test_calib_design_linearize_and_contract_design(self):
        c, p = H.gaussian_chain(proposal={"nodes": ["x"], "components": [{"theta": {"sigma": 2.5}}]})
        rc, out = run("calib_design.py", "linearize", "--contract", *self.chain((c, p))[:1], "--plan", self.d / "p.json")
        self.assertEqual((rc, out["theta"]), (0, ["mu"]))
        self.assertIn("provisional-thresholds", out["flags"])
        rels = F.releases()
        good = F.contract()
        good["data"] = {"calibration_releases": [data.release_hash(rels[F.CAL])],
                        "validation_releases": [data.release_hash(rels[F.VAL])]}
        rc, out = run("calib_contract.py", "check", "--contract", self.put("fc.json", good), "--release",
                      self.put("cal.json", rels[F.CAL]), "--release", self.put("val.json", rels[F.VAL]), "--design",
                      self.put("d.json", out))
        self.assertEqual((rc, out["status"]), (0, "accepted"), out.get("findings"))

    def test_calib_kernel_check(self):
        pts = self.put("pts.json", [{"theta": 0.5}, {"theta": 0.25}, {"theta": 0.4}])
        c, p = self.chain(H.uniform_chain())
        rc, out = run("calib_kernel_check.py", "p0", "--contract", c, "--plan", p, "--points", pts, "--seed", 11)
        self.assertEqual((rc, out["status"]), (1, "failed"))
        c, p = self.chain(H.uniform_chain({"nodes": ["x"], "components": [{"theta": {"theta": v}} for v in
                                                                           (0.0, 0.5, 1.0)]}))
        rc, out = run("calib_kernel_check.py", "p0", "--contract", c, "--plan", p, "--points", pts, "--seed", 11)
        self.assertEqual((rc, out["status"]), (0, "passed"))

    def test_calib_reweight(self):
        c, p = self.chain(H.gaussian_chain())
        rc, out = run("calib_reweight.py", "weights", "--contract", c, "--plan", p, "--theta", self.put("t.json", {}))
        self.assertEqual((rc, out["runs"]["run"]["max_abs_w_minus_1"]), (0, 0.0))
        rc, out = run("calib_reweight.py", "weights", "--contract", c, "--plan", p, "--theta",
                      self.put("t2.json", {"mu": 0.5}))
        self.assertEqual(rc, 0)
        self.assertLess(out["runs"]["run"]["kish"], 20_000)
        rc, out = run("calib_reweight.py", "weights", "--contract", c, "--plan", p, "--theta",
                      self.put("t3.json", {"nope": 1}))
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        rc, out = run("calib_reweight.py", "weights", "--contract", c, "--plan", p, "--theta",
                      self.put("t4.json", {"mu": "abc"}))
        self.assertEqual((rc, out["status"]), (2, "rejected"))                       # review F10

    def test_calib_emulator_is_a_stub(self):
        for cmd in ("train", "p6", "ask", "tell"):
            rc, out = run("calib_emulator.py", cmd)
            self.assertEqual((rc, out["status"]), (3, "incomplete"))

    def test_calib_contract_preflight(self):
        sys.path.insert(0, str(ROOT / "tests" / "core"))
        from test_calibration_preflight import THRESHOLD, linearity_example
        rel = F.release("calibration", ["u1", "u2"], [], {})
        rel["content"] = {"values": linearity_example(0.035)}
        draft = F.contract()
        draft["thresholds"] = {"linearity": THRESHOLD}
        draft["data"] = {"calibration_releases": [data.release_hash(rel)]}
        led = self.d / "ledger.json"
        self.assertEqual(run("calib_data.py", "init", "--ledger", led)[0], 0)
        rc, out = run("calib_contract.py", "preflight", "--contract", self.put("draft.json", draft), "--release",
                      self.put("rel.json", rel), "--ledger", led, "--write-draft", self.d / "draft2.json")
        self.assertEqual((rc, out["a0_summary"]), (0, {"unreachable_thresholds": ["linearity"]}))
        self.assertNotIn("_quantity", json.dumps(out))
        state = json.loads(led.read_text())
        self.assertEqual({e["kind"] for e in state["events"]}, {"fit"})
        self.assertEqual(json.loads((self.d / "draft2.json").read_text())["a0_summary"],
                         {"unreachable_thresholds": ["linearity"]})
        bad = dict(draft, thresholds={"linearity": dict(THRESHOLD, observables=["absent"] * 8)})
        before = len(json.loads(led.read_text())["events"])
        rc, out = run("calib_contract.py", "preflight", "--contract", self.put("bad.json", bad), "--release",
                      self.d / "rel.json", "--ledger", led)
        self.assertEqual((rc, out["code"]), (2, "a0.no_value"))
        self.assertGreater(len(json.loads(led.read_text())["events"]), before)    # the read is recorded (review F10)
        rc, out = run("calib_contract.py", "check", "--contract", self.d / "draft.json", "--design",
                      self.put("des.json", [1, 2]))
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        other = dict(draft, data={"calibration_releases": [F.h("x")]})
        rc, out = run("calib_contract.py", "preflight", "--contract", self.put("d3.json", other), "--release",
                      self.d / "rel.json", "--ledger", led)
        self.assertEqual((rc, out["status"]), (2, "rejected"))


if __name__ == "__main__":
    unittest.main()
