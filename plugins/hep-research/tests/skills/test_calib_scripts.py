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

S = ROOT / "skills" / "hep-statistics" / "scripts"
DATA = ROOT / "core" / "calibration" / "data"


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
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

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
            "inputs": inputs(), "upstreams": [{"usages": ["phi-center"], "effective_grade": "failed", "flags": []}]}))
        self.assertEqual((rc, out["determined"], out["effective_grade"]), (0, True, "failed"))
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
            rc, out = run("calib_chain.py", "candidates", "--contract", DATA / f"{name}.json")
            self.assertEqual((rc, out["status"]), (0, "ok"), name)
            rc, out = run("calib_chain.py", "p4", "--contract", DATA / f"{name}.json")
            self.assertEqual((rc, out["status"]), (0, "passed"), name)
        fx = json.loads((DATA / "toy_detector_subgraph.json").read_text())
        fx["contract"]["references"] = [dict(r, enabled=r["id"] == "single_photoelectron")
                                        for r in fx["contract"]["references"]]
        rc, out = run("calib_chain.py", "p4", "--contract", self.put("sub.json", fx))
        self.assertEqual((rc, out["status"], out["remedy_level"]), (1, "failed", "contract"))

    def test_calib_contract(self):
        rels = F.releases()
        args = []
        for h, r in rels.items():
            args += ["--release", self.put(f"{h[:8]}.json", dict(r, release_sha256=h))]
        rc, out = run("calib_contract.py", "check", "--contract", self.put("c.json", F.contract()), *args)
        self.assertEqual((rc, out["status"]), (0, "accepted"), out.get("findings"))
        bad = F.contract()
        bad["models"]["absorbed"] = [{"id": "nominal"}]
        rc, out = run("calib_contract.py", "check", "--contract", self.put("bad.json", bad), *args)
        self.assertEqual((rc, out["status"]), (2, "rejected"))
        rc, out = run("calib_contract.py", "check", "--contract", self.put("shape.json", {"schema": "x"}))
        self.assertEqual((rc, out["stage"]), (2, "schema"))

    def test_calib_data_flow(self):
        led = self.d / "ledger.json"
        self.assertEqual(run("calib_data.py", "init", "--ledger", led)[0], 0)
        self.assertEqual(run("calib_data.py", "init", "--ledger", led)[0], 2)          # never reset
        k1, k2 = F.h("kappa-1"), F.h("kappa-2")
        x, y = self.put("x.json", ["x1", "x2"]), self.put("y.json", ["y1"])
        ch1 = self.put("ch1.json", {"contract_sha256": F.h("c1")})
        ch2 = self.put("ch2.json", {"contract_sha256": F.h("c2")})
        rc, out = run("calib_data.py", "open", "--ledger", led, "--kappa", k1, "--release-hash", F.h("rel-y"),
                      "--validation-units", y, "--calibration-units", x, "--channel", ch1)
        self.assertEqual((rc, out["opening_seq"]), (0, 1))
        run("calib_data.py", "open", "--ledger", led, "--kappa", k2, "--release-hash", F.h("rel-x"),
            "--validation-units", x, "--calibration-units", x, "--channel", ch2)
        rc, out = run("calib_data.py", "inputs", "--ledger", led, "--kappa", k2, "--vmode", "cross-validation",
                      "--validation-units", x, "--calibration-units", x)
        self.assertEqual((rc, out["earlier_failure_record"]), (0, "pending"))
        stub = self.put("dec.json", {"kappa": k1, "outcome": "fail"})                 # hand-written stub (phase 0)
        self.assertEqual(run("calib_data.py", "decide", "--ledger", led, "--decision", stub)[1]["record_status"], "final")
        rc, out = run("calib_data.py", "inputs", "--ledger", led, "--kappa", k2, "--vmode", "cross-validation",
                      "--validation-units", x, "--calibration-units", x)
        self.assertEqual(out["earlier_failure_record"], "final")
        Path(f"{led}.lock").write_text("other writer")
        rc, out = run("calib_data.py", "draft", "--ledger", led, "--series", "s")
        self.assertEqual((rc, out["status"]), (2, "rejected"))                          # single writer
        rc, out = run("calib_data.py", "ingest", "--release", self.put("r.json", {"observables": []}))
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
