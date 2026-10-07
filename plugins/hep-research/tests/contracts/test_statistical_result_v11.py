"""S11: statistical-result additions in contracts 1.1.0 (significance with trials method, expected bands,
uncertainty breakdown, goodness of fit, new construction values) and the two fail-closed rules: a scan without a
global p-value is unresolved (stats.lee_missing); a Bayesian result declaring R-hat above 1.01 with fit_status
'converged' is an error from contract 1.1.0 on and a warning for 1.0.0 artifacts (stats.convergence_mismatch).
All fixtures SYNTHETIC."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from contracts import CONTRACTS_VERSION  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402

ART = ROOT / "contracts" / "fixtures" / "artifacts"


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def codes(rep, severity=None):
    return {f.code for f in rep.findings if severity is None or f.severity == severity}


class StatisticalResultV11(unittest.TestCase):
    def test_version_is_minor_bump(self):
        self.assertEqual(CONTRACTS_VERSION, "2.0.0")

    def test_unresolved_fixtures(self):
        cases = load(ART / "cases.json")["unresolved"]
        self.assertTrue(cases)
        for name, expected in cases.items():
            with self.subTest(name=name):
                rep = validate_artifact(load(ART / "unresolved" / name))
                self.assertTrue(rep.ok)
                self.assertTrue(set(expected) <= codes(rep, "unresolved"), codes(rep))

    def test_scan_with_global_p_is_clean(self):
        rep = validate_artifact(load(ART / "valid" / "statres_scan_global.json"))
        self.assertEqual(codes(rep), set())

    def test_scan_rule_needs_a_scan(self):
        d = load(ART / "unresolved" / "statres_scan_no_global.json")
        del d["extension"]["significance"]["scan"]
        self.assertNotIn("stats.lee_missing", codes(validate_artifact(d)))

    def test_new_construction_values(self):
        base = load(ART / "valid" / "statres_frequentist.json")
        for c in ("berger-boos", "cousins-highland", "toy-calibrated-profile"):
            d = copy.deepcopy(base)
            d["extension"]["construction"] = c
            self.assertTrue(validate_artifact(d).ok, c)

    def test_rhat_rule_by_contract_version(self):
        bad = load(ART / "invalid" / "statres_bayesian_rhat_mismatch.json")
        self.assertIn("stats.convergence_mismatch", codes(validate_artifact(bad), "error"))
        old = copy.deepcopy(bad)
        old["contract_version"] = "1.0.0"
        rep = validate_artifact(old)
        self.assertTrue(rep.ok)                      # a 1.0.0 artifact keeps its outcome
        self.assertIn("stats.convergence_mismatch", codes(rep, "warning"))
        for status in ("converged-with-warnings", "failed"):
            d = copy.deepcopy(bad)
            d["extension"]["fit_status"] = status
            if status == "failed":
                d["status"].append("failed")
            self.assertNotIn("stats.convergence_mismatch", codes(validate_artifact(d)), status)
        d = copy.deepcopy(bad)
        d["extension"]["convergence"] = {"rhat_max": 1.005}
        self.assertNotIn("stats.convergence_mismatch", codes(validate_artifact(d)))

    def test_v100_fixtures_keep_their_outcome(self):
        cases = load(ART / "cases.json")
        for name in cases["valid"]:
            d = load(ART / "valid" / name)
            if d["contract_version"] == "1.0.0":
                self.assertTrue(validate_artifact(d).ok, name)
        for name, expected in cases["invalid"].items():
            d = load(ART / "invalid" / name)
            if d.get("contract_version") == "1.0.0":
                rep = validate_artifact(d)
                self.assertFalse(rep.ok, name)
                self.assertTrue(set(expected) <= codes(rep), name)


if __name__ == "__main__":
    unittest.main()
