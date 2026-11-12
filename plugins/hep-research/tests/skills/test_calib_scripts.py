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
import calibration_g4sim_fixtures as G4  # noqa: E402
import calibration_phase1 as H  # noqa: E402

sys.path.insert(0, str(ROOT))
from core.calibration import data_release as observed  # noqa: E402

S = ROOT / "skills" / "hep-statistics" / "scripts"
FIXTURE_DIR = ROOT / "core" / "calibration" / "data"


def run(script, *args, timeout=120):
    res = subprocess.run([sys.executable, "-I", str(S / script), *map(str, args)], capture_output=True, text=True,
                         timeout=timeout)
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
        cal, val = observed.release_hash(rels[F.CAL]), observed.release_hash(rels[F.VAL])
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

    def test_calib_contract_g4sim_identity(self):
        """Phase 3: calib_contract.py identity recomputes the five items of section 5.1 from the model documents, and
        check --model-documents rejects a contract whose declared items differ from them."""
        files = {"detector_spec": ("detector.json", G4.detector_text()), "simulation_request": ("request.json",
                 G4.request_text()), "alignment_overlay": ("overlay.json", G4.overlay()),
                 "run_card": ("run.json", G4.run_card()), "response_pipeline": ("pipeline.json", G4.pipeline()),
                 "condition_snapshot": ("snapshot.json", G4.snapshot()), "efficiency_map": ("map.json",
                 G4.efficiency_map())}
        entry = {}
        for key, (name, value) in files.items():
            (self.d / name).write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
            entry[key] = name
        entry.update(event_time_rule=G4.EVENT_TIME, build_environment=G4.BUILD)
        docs = self.put("documents.json", {"nominal": entry})
        rels = F.releases()
        args = ["--release", self.put("cal.json", rels[F.CAL]), "--release", self.put("val.json", rels[F.VAL])]
        c = G4.contract()
        c["data"] = {"calibration_releases": [observed.release_hash(rels[F.CAL])],
                     "validation_releases": [observed.release_hash(rels[F.VAL])]}
        rc, out = run("calib_contract.py", "identity", "--contract", self.put("c.json", c), "--model-documents", docs)
        self.assertEqual((rc, out["status"]), (0, "ok"), out)
        c["models"]["enumerated"][0]["identity"] = out["identities"]["nominal"]
        rc, out = run("calib_contract.py", "check", "--contract", self.put("c.json", c), "--model-documents", docs,
                      *args)
        self.assertEqual((rc, out["status"]), (0, "accepted"), out.get("findings"))
        changed = G4.pipeline()
        changed["stages"][2]["parameters"]["excess_noise"]["value"] = 0.2         # a non-theta stage value
        (self.d / "pipeline.json").write_text(json.dumps(changed))
        rc, out = run("calib_contract.py", "check", "--contract", self.d / "c.json", "--model-documents", docs, *args)
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        self.assertEqual({f["code"] for f in out["findings"]}, {"models.identity_mismatch"})
        rc, out = run("calib_chain.py", "candidates", "--contract", self.d / "c.json", "--plan",
                      self.put("plan.json", G4.plan()))
        self.assertEqual((rc, out["status"], out["parameters"]["birks"][0]["method"]), (0, "ok", "rerun"))
        p = G4.plan()
        p["node_binding"]["nodes"]["source"]["recording"] = "moments"
        rc, out = run("calib_chain.py", "candidates", "--contract", self.d / "c.json", "--plan", self.put("p.json", p))
        self.assertEqual((rc, out["without_candidate"]), (1, ["beam_energy"]))

    def test_calib_data_flow(self):
        from core.calibration import validate as V
        led = self.d / "ledger.json"
        self.assertEqual(run("calib_data.py", "init", "--ledger", led)[0], 0)
        self.assertEqual(run("calib_data.py", "init", "--ledger", led)[0], 2)          # never reset
        k1, k2 = F.h("kappa-1"), F.h("kappa-2")
        rx = {"lineage": {"raw_units": ["x1", "x2"]}}
        ry = {"lineage": {"raw_units": ["y1"]}}
        hx, hy = observed.release_hash(rx), observed.release_hash(ry)
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
        hand = self.put("hand.json", {"decisions": [{"kappa": k1, "outcome": "pass"}]})   # a hand-written outcome
        self.assertEqual(run("calib_data.py", "decide", "--ledger", led, "--book", hand, "--kappa", k1)[0], 2)
        bk = V.DecisionBook()
        bk.register({"kappa": k1, "alpha": 0.05})
        ev = V._seal({"kind": "holdout", "kappa": k1, "alpha": 0.05, "T": 20.0, "k": 2, "p": 4.5e-5, "path": "analytic",
                      "status": "ok", "reference": {"kind": "chi2", "k": 2, "sha256": None, "ratio_failed": False},
                      "data_side_check_triggered": False})
        self.assertEqual(bk.decide_computed(ev)["outcome"], "fail")                  # computed from T_v (F4)
        book = self.put("book.json", bk.state)
        self.assertEqual(run("calib_data.py", "decide", "--ledger", led, "--book", book, "--kappa", k1)[1]
                         ["record_status"], "final")
        rc, out = run("calib_data.py", "inputs", "--ledger", led, "--kappa", k2, "--vmode", "cross-validation",
                      "--validation-units", x, "--calibration-units", x)
        self.assertEqual(out["earlier_failure_record"], "final")
        # a holdout whose releases share raw units, or an unmet opening condition: refused, nothing recorded
        rxy = self.put("rxy.json", {"lineage": {"raw_units": ["x2", "y9"]}})
        hxy = observed.release_hash({"lineage": {"raw_units": ["x2", "y9"]}})
        before = json.loads(led.read_text())["seq"]
        rc, out = run("calib_data.py", "open", "--ledger", led, "--kappa", F.h("kappa-3"), "--vmode", "holdout",
                      "--release", relx, "--release", rxy, "--calibration", hx, "--validation", hxy, "--channel", ch1)
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        cond = self.put("cond.json", {c: True for c in observed.OPENING_PRECONDITIONS} | {"p7_not_incomplete": False})
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
        good["data"] = {"calibration_releases": [observed.release_hash(rels[F.CAL])],
                        "validation_releases": [observed.release_hash(rels[F.VAL])]}
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
        plan = self.put("plan.json", {"schema": "calibration-plan/1", "kernels": {}})
        for cmd in ("train", "p6", "ask", "tell"):
            rc, out = run("calib_emulator.py", cmd, "--plan", plan)
            self.assertEqual((rc, out["status"]), (3, "incomplete"))
        rc, out = run("calib_emulator.py", "p6", "--plan", self.d / "absent.json")
        self.assertEqual((rc, out["status"]), (2, "rejected"))

    def test_calib_contract_preflight(self):
        sys.path.insert(0, str(ROOT / "tests" / "core"))
        from test_calibration_preflight import THRESHOLD, linearity_example
        rel = F.release("calibration", ["u1", "u2"], [], {})
        rel["content"] = {"values": linearity_example(0.035)}
        draft = F.contract()
        draft["thresholds"] = {"linearity": THRESHOLD}
        draft["data"] = {"calibration_releases": [observed.release_hash(rel)]}
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


class Phase2Scripts(unittest.TestCase):
    """The phase-2 scripts: JSON with a status and the section 14 exit codes; the decision-record flow through
    calib_validate.py and calib_data.py with real decision records (section 17: retested in phase 2)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.d = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write(self, name, record):
        p = self.d / name
        p.write_text(json.dumps(record))
        return p

    def test_numeric_subcommands(self):
        self.assertEqual(run("calib_fit.py", "kstar", "--n", 60), (0, {"status": "ok", "n": 60, "replacement": True,
                                                                     "k_star": 5}))
        code, out = run("calib_closure.py", "nc", "--d", 3, "--level", "standard")
        self.assertEqual((code, out["N_c"]), (0, 99))
        code, out = run("calib_validate.py", "required-lambda", "--k", 1)
        self.assertAlmostEqual(out["lambda"], 7.849, places=3)
        code, out = run("calib_likelihood.py", "bootstrap-size", "--p", 50)
        self.assertEqual(out["B_min"], 2500)
        code, out = run("calib_interval.py", "total", "--sigma-q", 1, "--shift", "0.3", "--sigma-boot", 0.02,
                        "--w", 0.891)
        self.assertAlmostEqual(out["half_width"], (1 + 0.09 + 0.02 / 0.891) ** 0.5, places=9)
        code, out = run("calib_closure.py", "not-executed", "--reason", "costly")
        self.assertIn("closure-not-tested", out["flags"])

    def test_g7_and_g3(self):
        th = self.write("th.json", [[0.0, 0.0], [0.1, -0.1], [-0.1, 0.05]])
        S = self.write("s.json", [[0.01, 0.0], [0.0, 0.01]])
        code, out = run("calib_fit.py", "g7", "--theta-hats", th, "--sigma-mc", S)
        self.assertEqual((code, out["df"]), (0, 4))
        region = self.write("r.json", {"t": [0.7, 1.3]})
        lim = self.write("l.json", {"feasible": {"t": [0.0, 1.0]}})
        code, out = run("calib_fit.py", "g3", "--region", region, "--limits", lim)
        self.assertEqual((code, out["finding"]), (1, "g3.outside_limits"))

    def test_statistic_and_declaration(self):
        x = self.write("x.json", {"r": [1.0, 0.0], "C_r": [[1.0, 0.0], [0.0, 0.0]], "sigma0": [1.0, 1.0],
                                  "constraints": [[0.0, 1.0]]})
        code, out = run("calib_validate.py", "statistic", "--input", x)
        self.assertEqual((code, out["k"], out["T_v"]), (0, 1, 1.0))
        bad = self.write("b.json", {"C_r0": [[1.0, 1.0], [1.0, 1.0]], "sigma0": [1.0, 1.0], "constraints": []})
        code, out = run("calib_validate.py", "declaration", "--input", bad)
        self.assertEqual((code, out["code"]), (2, "validate.undeclared_exact_constraint"))

    def test_decision_records_with_the_ledger(self):
        """Abandonment makes the failure record final; a passing decision afterwards is rejected (section 15.3.14)."""
        from core.calibration import validate as V
        led, book = self.d / "ledger.json", self.d / "book.json"
        self.assertEqual(run("calib_data.py", "init", "--ledger", led)[0], 0)
        plan = self.write("plan.json", {"p": 1})
        code, k = run("calib_validate.py", "kappa", "--contract-sha256", "a" * 64, "--plan", plan, "--engine", "p2",
                      "--book", book)
        self.assertEqual(code, 0)
        state = json.loads(led.read_text())
        L = observed.Ledger(state)
        L.open_validation(k["kappa"], "v" * 64, ["v1"], ["c1"], {"contract_sha256": "a" * 64})
        led.write_text(json.dumps(L.state))
        self.assertEqual(run("calib_validate.py", "abandon", "--book", book, "--ledger", led, "--kappa",
                             k["kappa"])[0], 0)
        bk = V.DecisionBook(json.loads(book.read_text()))
        ev = V._seal({"kind": "holdout", "kappa": k["kappa"], "alpha": 0.05, "T": 1.0, "k": 2, "p": 0.6,
                      "path": "analytic", "status": "ok", "reference": {"ratio_failed": False}})
        with self.assertRaises(V.ValidationError) as cm:
            bk.decide_computed(ev)
        self.assertEqual(cm.exception.code, "validate.after_abandonment")
        tampered = dict(ev, p=0.001)                                                  # evidence edited after the fact
        with self.assertRaises(V.ValidationError) as cm:
            bk.decide_computed(tampered)
        self.assertEqual(cm.exception.code, "validate.evidence")
        self.assertEqual({r["status"] for r in json.loads(led.read_text())["failure_records"]}, {"final"})

    def test_propagate_and_likelihood(self):
        x = self.write("e.json", {"theta_hat": [0.1], "zeta_hat": [0.0], "Sigma": [[1.0, 0.5], [0.5, 1.0]],
                                  "i_theta": [0], "i_zeta": [1]})
        code, out = run("calib_propagate.py", "export", "--input", x)
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["G_zeta"][0][0], 0.5)
        self.assertAlmostEqual(out["variance"][0][0], 1.0)
        code, out = run("calib_likelihood.py", "layout", "--contract", FIXTURE_DIR / "toy_detector_design.json")
        self.assertEqual(code, 0)
        self.assertEqual(len(out["blocks"]), 26)
        m = self.write("m.json", {"W_P": 30.0, "S_P": 30.0, "W_F": 70.0, "S_F": 70.0})
        code, out = run("calib_likelihood.py", "binomial", "--moments", m)
        self.assertAlmostEqual(out["n_eff"], 100.0)

    def test_fit_scripts_reject_a_non_toy_evaluator(self):
        c = self.write("c.json", {"observables": [], "parameters": [], "exposure": {"a": 1}})
        p = self.write("p.json", {"evaluator": {"kind": "g4sim"}})
        v = self.write("v.json", {})
        for script, sub in (("calib_fit.py", "fit"), ("calib_identify.py", "g5"), ("calib_shift.py", "g9")):
            code, out = run(script, sub, "--contract", c, "--plan", p, "--values", v)
            self.assertEqual(code, 2, (script, out))


class Phase2Wiring(unittest.TestCase):
    """The phase-2 checks reachable from their owning scripts (section 14, review F3) and the exit codes of
    not-decided outcomes (review F6, F7)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.d = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write(self, name, record):
        p = self.d / name
        p.write_text(json.dumps(record))
        return p

    def test_not_decided_exits_3(self):
        code, out = run("calib_closure.py", "not-executed", "--reason", "declared in the plan")
        self.assertEqual((code, out["status"]), (3, "not-decided"))

    def test_g8_full_level_needs_the_95_flags(self):
        pt = {"errors": [[0.1, 0.0]] * 4, "cover68": [[True, True]] * 4}
        r = self.write("r.json", {"level": "full", "names": ["a", "b"], "sigma_design": [1.0, 1.0],
                                  "interior": pt, "boundary": pt})
        code, out = run("calib_closure.py", "decide", "--results", r)
        self.assertEqual((code, out["status"]), (2, "rejected"))
        self.assertIn("cover95", out["error"])

    def test_package_conflicts(self):
        x = self.write("x.json", {"packages": [{"id": "p1", "upstream": "a" * 64, "zeta": {"eta": "v1"}},
                                               {"id": "p2", "upstream": "b" * 64, "zeta": {"eta": "v2"}}],
                                  "upstreams": {}})
        code, out = run("calib_deps.py", "packages", "--input", x)
        self.assertEqual((code, out["findings"][0]["code"]), (1, "deps.version_conflict"))
        x = self.write("y.json", {"packages": [{"id": "p1", "upstream": "a" * 64, "zeta": {"eta": "v1"}},
                                               {"id": "p2", "upstream": "b" * 64, "zeta": {"eta": "v1"}}],
                                  "upstreams": {}})
        self.assertEqual(run("calib_deps.py", "packages", "--input", x)[0], 0)

    def test_design_noise_checks(self):
        plan = self.write("plan.json", {"toys": {"construction": "philox-only"}})
        code, out = run("calib_design.py", "practices", "--plan", plan)
        self.assertEqual((code, out["findings"][0]["code"]), (1, "design.toy_philox_only"))
        uses = self.write("u.json", {"toy_replicas": [[1, 2]], "bootstrap": [[1, 2]]})
        code, out = run("calib_design.py", "seeds", "--uses", uses)
        self.assertEqual((code, out["findings"][0]["code"]), (1, "design.seed_overlap"))
        J, W = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]
        zero = [[[0.0] * 3] * 3] * 2
        pts = self.write("pts.json", [{"J": J, "W": W, "K": zero, "sigma_tot": [1.0, 1.0]}])
        self.assertEqual(run("calib_design.py", "bj", "--points", pts)[0], 0)
        code, out = run("calib_design.py", "bj", "--points", pts, "--bound", 0.2)
        self.assertEqual((code, out["status"]), (2, "rejected"))                 # only tightening (A9)
        for k0, st in ((3, "not-applicable"), (0, "no-testable-direction")):
            x = self.write("p7.json", {"mode": "none" if k0 else "holdout", "k0": k0, "path": "analytic"})
            code, out = run("calib_design.py", "p7", "--input", x)
            self.assertEqual((code, out["status"]), (0, st))

    def test_holdout_decision_is_computed(self):
        """calib_validate.py holdout on the toy detector: the fit, T_v with C_r^+ against chi2_k, and a decision
        record carrying the statistic (no outcome given by hand, review F4)."""
        import numpy as np
        from core.calibration import toy, toy_problem as TP
        cal = ["beam1_e_mean", "beam2_e_mean", "beam4_e_mean", "light_e_mean", "light_e_width", "spe_e_mean"]
        val = ["beam2_e_width", "beam4_e_width"]
        obs = [{"name": n, "role": "calibration", "block": "gaussian", "link": "log"} for n in cal] + \
              [{"name": n, "role": "validation", "block": "gaussian", "link": "log"} for n in val]
        contract = {"observables": obs, "exposure": {"all": 400},
                    "parameters": [{"name": "pde", "role": "theta", "sampling_bounds": [0.2, 0.3],
                                    "physical_bounds": [0.01, 0.99]},
                                   {"name": "gain", "role": "theta", "sampling_bounds": [8, 12],
                                    "physical_bounds": [1, 100]}]}
        plan = {"evaluator": {"kind": "toy-detector-subgraph", "events": 4000}}
        p = TP.ToyProblem(lambda n: toy.build_toy(n, "subgraph"), cal, {"pde": {"bounds": (0.01, 0.99), "prior": (0.2,
                          0.3)}, "gain": {"bounds": (1, 100), "prior": (8, 12)}}, 400, 4000, val_names=val)
        rng = np.random.default_rng(3)
        y = np.exp(p.simulate(np.array([0.25, 10.0]), rng, nominal=False).y_gauss)
        yv = np.exp(p.simulate_val(np.array([0.25, 10.0]), rng, nominal=False))
        c, pl = self.write("c.json", contract), self.write("p.json", plan)
        v, vv = self.write("v.json", dict(zip(cal, y.tolist()))), self.write("vv.json", dict(zip(val, yv.tolist())))
        led, book = self.d / "ledger.json", self.d / "book.json"
        run("calib_data.py", "init", "--ledger", led)
        code, k = run("calib_validate.py", "kappa", "--contract-sha256", "a" * 64, "--plan", pl, "--engine", "p2",
                      "--book", book)
        code, out = run("calib_validate.py", "holdout", "--contract", c, "--plan", pl, "--values", v,
                        "--validation-values", vv, "--kappa", k["kappa"], "--book", book, "--ledger", led,
                        timeout=900)
        self.assertEqual((code, out["status"]), (0, "written"), out)
        rec = out["record"]
        self.assertTrue(rec["computed"])
        self.assertEqual(rec["statistic"]["k"], 2)
        self.assertEqual(rec["outcome"], "pass" if out["evidence"]["p"] > 0.05 else "fail")

    def test_fit_toys_lower_bound(self):
        c = self.write("c.json", {})
        code, out = run("calib_fit.py", "g6", "--contract", c, "--values", c, "--toys", 100)
        self.assertEqual((code, out["status"]), (2, "rejected"))


if __name__ == "__main__":
    unittest.main()
