"""Contracts 3.2.0: dataset-records with status 'simulated' (contracts.validate._simulated_dataset and
contracts/dependencies.py). The project is the J14 offline replay (examples/geant4-thin-silicon, through
test_geant4_upgrade.j14_output), whose run records and study records come from real Geant4 11.4.3 outputs; the tables
written here are SYNTHETIC."""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PLUGIN))
from contracts.dependencies import validate_dependencies  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from tests.contracts.test_geant4_upgrade import j14_output, tearDownModule  # noqa: E402,F401

FIX = PLUGIN / "contracts" / "fixtures" / "artifacts"
TABLE = json.loads((FIX / "valid" / "dataset_simulated.json").read_text(encoding="utf-8"))
COMMUNICATION = json.loads((FIX / "valid" / "communication.json").read_text(encoding="utf-8"))
RUN = "output/artifacts/runs/sp-nominal.computational-run.json"
STUDY = "output/artifacts/sp.study-validated.computational-run.json"
LITERATURE = "output/artifacts/geant4.literature-record.json"


class SimulatedDataset(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "j14"
        shutil.copytree(j14_output(), self.root / "output")

    def tearDown(self):
        self.tmp.cleanup()

    def entry(self, ref: str) -> dict:
        path = self.root / ref
        src = json.loads(path.read_text(encoding="utf-8"))
        return {"ref": ref, "artifact_type": src["artifact_type"], "artifact_id": src["artifact_id"],
                "version": src["contract_version"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "status": list(src["status"])}

    def table(self, ref: str, status: list[str]) -> Path:
        d = copy.deepcopy(TABLE)
        d["inputs"], d["status"] = [self.entry(ref)], status
        path = self.root / "output" / "artifacts" / "table.dataset-record.json"
        path.write_text(json.dumps(d, indent=1), encoding="utf-8")
        return path

    def codes(self, rep: dict, severity: str) -> set:
        return {f["code"] for f in rep["findings"] if f["severity"] == severity}

    def test_table_from_a_run_record_keeps_unvalidated(self):
        path = self.table(RUN, ["synthetic", "unvalidated"])
        self.assertTrue(validate_artifact(json.loads(path.read_text(encoding="utf-8"))).ok)
        rep = validate_dependencies(path, self.root)
        self.assertNotIn("dataset.simulated_source", self.codes(rep, "error"), rep["findings"])
        self.assertNotIn("dependency.status_not_propagated", self.codes(rep, "error"), rep["findings"])

    def test_dropping_unvalidated_from_a_run_record_table_is_caught(self):
        rep = validate_dependencies(self.table(RUN, ["synthetic"]), self.root)
        self.assertIn("dependency.status_not_propagated", self.codes(rep, "error"))

    def test_table_from_a_validated_study_may_carry_validated_in_scope(self):
        path = self.table(STUDY, ["synthetic", "validated-in-scope"])
        self.assertTrue(validate_artifact(json.loads(path.read_text(encoding="utf-8"))).ok)
        rep = validate_dependencies(path, self.root)
        self.assertNotIn("dataset.simulated_source", self.codes(rep, "error"), rep["findings"])

    def test_an_input_that_is_not_a_simulation_record_is_refused(self):
        rep = validate_dependencies(self.table(LITERATURE, ["synthetic", "unvalidated"]), self.root)
        self.assertIn("dataset.simulated_source", self.codes(rep, "error"))

    def processing(self, name: str, source: str) -> str:
        """A SYNTHETIC processing record (a reconstruction: computational-run without extension.simulation) whose one
        input is `source`."""
        d = json.loads((self.root / RUN).read_text(encoding="utf-8"))
        d["artifact_id"] = f"reco-{name}"
        d["extension"].pop("simulation", None)
        d["extension"]["reconstruction"] = {"program": {"name": "simreco"}, "note": "SYNTHETIC"}
        d["inputs"] = [self.entry(source)]
        ref = f"output/artifacts/{name}.computational-run.json"
        (self.root / ref).write_text(json.dumps(d, indent=1), encoding="utf-8")
        return ref

    def chain_table(self, ref: str, version: str = "3.13.0") -> Path:
        path = self.table(ref, ["synthetic", "unvalidated"])
        d = json.loads(path.read_text(encoding="utf-8"))
        d["contract_version"] = version
        path.write_text(json.dumps(d, indent=1), encoding="utf-8")
        return path

    def test_a_processing_chain_rooted_in_simulation_is_accepted(self):
        """B2.5 (CV-B2): simulation -> reconstruction -> second processing level -> table."""
        reco = self.processing("reco", RUN)
        rep = validate_dependencies(self.chain_table(self.processing("reco2", reco)), self.root)
        self.assertNotIn("dataset.simulated_source", self.codes(rep, "error"), rep["findings"])

    def test_a_chain_whose_root_is_not_a_simulation_run_is_refused(self):
        bare = self.processing("bare", RUN)
        d = json.loads((self.root / bare).read_text(encoding="utf-8"))
        d["inputs"] = []  # a computational-run with neither simulation, study nor inputs: not a simulation root
        (self.root / bare).write_text(json.dumps(d, indent=1), encoding="utf-8")
        for name, src in (("from-bare", bare), ("from-literature", LITERATURE)):
            with self.subTest(root=name):
                rep = validate_dependencies(self.chain_table(self.processing(name, src)), self.root)
                self.assertIn("dataset.simulated_source", self.codes(rep, "error"))

    def test_before_cv_b2_a_chain_is_not_a_simulated_source(self):
        rep = validate_dependencies(self.chain_table(self.processing("reco", RUN), "3.12.0"), self.root)
        self.assertIn("dataset.simulated_source", self.codes(rep, "error"))

    def test_a_communication_using_a_simulated_table_is_warned(self):
        table = self.table(RUN, ["synthetic", "unvalidated"])
        doc = copy.deepcopy(COMMUNICATION)
        doc["inputs"] = [self.entry(str(table.relative_to(self.root)))]
        path = self.root / "output" / "artifacts" / "note.communication.json"
        path.write_text(json.dumps(doc, indent=1), encoding="utf-8")
        rep = validate_dependencies(path, self.root)
        self.assertIn("communication.simulated_source", self.codes(rep, "warning"))


if __name__ == "__main__":
    unittest.main()
