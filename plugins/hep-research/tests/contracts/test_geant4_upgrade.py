"""Contracts 3.1.0, Geant4 phase 2: the study-record upgrade rule (contracts.validate._study_upgrade) and evidence
records (contracts.dependencies, extension.evidence_records).

The J14 re-issued study record (examples/geant4-thin-silicon/output/artifacts/mpv.study-validated.computational-run.json)
is the passing case; tampered copies must fail with the named code. Evidence records are resolved by dependencies.py
without inheriting the unvalidated label of the run records, and a changed, failed or hash-less run record is caught.
Other computational-runs that carry validated-in-scope (no Geant4 study material) keep their 3.0 outcome."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
NAME = "mpv.study-validated.computational-run.json"
_REPLAY = {}


def j14_output() -> Path:
    """The J14 offline replay, written once into a temporary folder (committed example outputs are not assumed:
    tools/check_ams_optional.py runs the suites in a copy without output/ folders)."""
    if "out" not in _REPLAY:
        import contextlib
        import importlib.util
        import io
        spec = importlib.util.spec_from_file_location("j14_run", PLUGIN / "examples" / "geant4-thin-silicon" / "run.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _REPLAY["tmp"] = tempfile.TemporaryDirectory()
        out = Path(_REPLAY["tmp"].name) / "output"
        with contextlib.redirect_stdout(io.StringIO()):
            mod.main(["--out", str(out)])
        _REPLAY["out"] = out
    return _REPLAY["out"]


def tearDownModule():
    """Delete the replay and forget it, so a module that runs later (test_simulated_dataset shares this cache)
    rebuilds it instead of reading a deleted folder (D10)."""
    if "tmp" in _REPLAY:
        _REPLAY["tmp"].cleanup()
    _REPLAY.clear()
from contracts import CONTRACTS_VERSION, KNOWN_CAPABILITIES  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402


def errors(doc):
    return sorted({f.code for f in validate_artifact(doc).errors})


class UpgradeRule(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads((j14_output() / "artifacts" / NAME).read_text(encoding="utf-8"))

    def test_the_reissued_record_passes(self):
        self.assertEqual(self.doc["status"], ["validated-in-scope"])
        self.assertIn("core:evidence-records", KNOWN_CAPABILITIES)
        self.assertEqual(errors(self.doc), [])
        self.assertTrue(validate_artifact(self.doc, strict=True).ok)

    def mutate(self, fn):
        d = copy.deepcopy(self.doc)
        fn(d)
        return errors(d)

    def test_each_missing_piece_has_its_code(self):
        study = lambda d: d["extension"]["study"]  # noqa: E731
        cases = {
            "geant4.upgrade_without_study": lambda d: d["extension"].pop("study"),
            "geant4.upgrade_unconverged": lambda d: study(d)["convergence"].__setitem__("gate", "fail"),
            "geant4.upgrade_without_reference_benchmark": lambda d: [
                b.__setitem__("negative_control", {"status": "not-caught"}) for b in study(d)["benchmarks"]],
            "geant4.upgrade_scope_outside": lambda d: study(d)["declared_scope"].__setitem__(
                "energy_MeV", [1000.0, 10000.0]),
            "evidence.capability_not_declared": lambda d: d.pop("required_capabilities"),
            "geant4.run_record_upgraded": lambda d: d["extension"].__setitem__("simulation", {}),
        }
        for code, fn in cases.items():
            with self.subTest(code=code):
                self.assertIn(code, self.mutate(fn))
        both = self.mutate(lambda d: (d["extension"].pop("evidence_records"), d.pop("required_capabilities")))
        self.assertIn("geant4.upgrade_without_evidence_records", both)

    def test_older_contract_versions_keep_their_outcome(self):
        d = copy.deepcopy(self.doc)
        d["contract_version"] = d["versions"]["contracts"] = "3.0.1"
        d["extension"]["study"]["convergence"]["gate"] = "fail"
        self.assertNotIn("geant4.upgrade_unconverged", errors(d))

    def test_other_computational_runs_are_unaffected(self):
        plain = {"contract_version": CONTRACTS_VERSION, "artifact_id": "conv-study", "artifact_type": "computational-run",
                 "objective": "a convergence study run by run_workflow.py", "bindings": {"experiments": [], "theory": []},
                 "versions": {"plugin": "0.20.0", "contracts": CONTRACTS_VERSION, "profiles": {}},
                 "provenance": {"producer_skill": "hep-computing", "created": "2026-10-21", "evidence_ids": []},
                 "inputs": [], "outputs": [], "unresolved_inputs": [], "status": ["validated-in-scope"],
                 "extension": {"input_manifest": [], "tools": [], "commands": [], "environment": {}, "seeds": {},
                               "tolerances": {}, "exit_status": 0, "output_hashes": {}}}
        self.assertEqual(errors(plain), [])


class EvidenceRecords(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.root = Path(self._t.name)
        shutil.copytree(j14_output(), self.root / "output")
        self.rec = self.root / "output" / "artifacts" / NAME

    def tearDown(self):
        self._t.cleanup()

    def deps(self, path):
        p = subprocess.run([sys.executable, "-B", str(PLUGIN / "contracts" / "dependencies.py"), str(path), "--root",
                            str(self.root)], capture_output=True, text=True, timeout=600)
        return p.returncode, json.loads(p.stdout)

    def test_resolved_without_inheriting_unvalidated(self):
        code, out = self.deps(self.rec)
        self.assertEqual(code, 0, out)
        self.assertTrue(out["dependency_consistency_ok"])

    def test_a_changed_failed_or_hashless_run_is_caught(self):
        doc = json.loads(self.rec.read_text(encoding="utf-8"))
        run = self.root / doc["extension"]["evidence_records"][0]["ref"]
        original = run.read_text(encoding="utf-8")
        run.write_text(original.replace('"exit_status": 0', '"exit_status": 1'), encoding="utf-8")
        code, out = self.deps(self.rec)
        codes = {f["code"] for f in out["findings"]}
        self.assertIn("evidence.hash_mismatch", codes)
        self.assertIn("evidence.run_failed", codes)
        r = json.loads(original)
        r["extension"]["output_hashes"] = {}
        run.write_text(json.dumps(r), encoding="utf-8")
        doc["extension"]["evidence_records"][0]["sha256"] = __import__("hashlib").sha256(run.read_bytes()).hexdigest()
        self.rec.write_text(json.dumps(doc), encoding="utf-8")
        code, out = self.deps(self.rec)
        self.assertIn("evidence.no_output_hashes", {f["code"] for f in out["findings"]})


class LinkedResponse(unittest.TestCase):
    def test_the_j14_response_links_its_run_record(self):
        doc = json.loads((j14_output() / "artifacts" / "response.json").read_text(encoding="utf-8"))
        self.assertEqual(len(doc["inputs"]), 1)
        self.assertEqual(doc["inputs"][0]["status"], ["unvalidated"])
        self.assertIn("unvalidated", doc["status"])
        self.assertEqual(len(doc["inputs"][0]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
