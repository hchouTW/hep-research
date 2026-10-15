"""hep-ml audit (PML-WP0.5: ML-K01, ML-K06): the publication gate of a statistical result built on an ML score
checks the ml-artifact it rests on, and dependencies.py propagates a source's unresolved findings.

Before the fix (0.9.0, source brief A6): J9's statistical result relabelled 'observed' passed the gate (a) with no ML
input at all, (b) with an ML input whose domain-shift check failed, (c) with an ML input whose split-overlap check was
not run; dependencies.py exited 0 for all three. On J9 itself dependencies.py exited 1 because the ml-artifact listed
raw work/ tool outputs as artifact inputs. All artifacts SYNTHETIC; the 'observed' relabelling exists only here.
"""
import contextlib
import copy
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import dependencies, validate  # noqa: E402

J9 = ROOT / "examples" / "ml-classifier-to-inference" / "output"
HAVE_J9 = (J9 / "artifacts" / "ml_artifact.json").is_file()  # a copy without example outputs skips these tests
ML0 = json.loads((J9 / "artifacts" / "ml_artifact.json").read_text()) if HAVE_J9 else {}
ST0 = json.loads((J9 / "artifacts" / "statistical_result.json").read_text()) if HAVE_J9 else {}


def relabel(doc):
    doc["status"] = ["observed"]
    return doc


@unittest.skipUnless(HAVE_J9, "example outputs not present")
class ProvenanceGateTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.dir = Path(self._td.name)
        (self.dir / "artifacts").mkdir()
        self.addCleanup(self._td.cleanup)

    def chain(self, ml_mut=None, st_mut=None):
        ml = relabel(copy.deepcopy(ML0))
        # an 'observed' ml-artifact needs an observed input (PML-WP1.3): the relabelled model says it was checked on data
        ml["inputs"] = [{"ref": "data/control_region.json", "external": True, "status": ["observed"]}]
        if ml_mut:
            ml_mut(ml)
        ml_path = self.dir / "artifacts" / "ml_artifact.json"
        ml_path.write_text(json.dumps(ml))
        st = relabel(copy.deepcopy(ST0))
        for i in st["inputs"]:
            i["status"] = ["observed"]
            i["sha256"] = hashlib.sha256(ml_path.read_bytes()).hexdigest()
        if st_mut:
            st_mut(st)
        st_path = self.dir / "artifacts" / "statistical_result.json"
        st_path.write_text(json.dumps(st))
        return st, st_path

    def gate(self, st, st_path):
        return validate.publication_gate(st, base_dir=st_path.parent)

    def codes(self, g, level):
        return {r["code"] for r in g["reasons"] if r["level"] == level}

    def test_j9_declares_its_observable_source(self):
        self.assertEqual(ST0["extension"]["observable_source"],
                         {"kind": "ml-score", "ml_artifact": "artifacts/ml_artifact.json"})

    def test_a6a_no_ml_input_fails(self):
        st, p = self.chain(st_mut=lambda s: s.update(inputs=[]))
        g = self.gate(st, p)
        self.assertEqual(g["status"], "failed", g)
        self.assertIn("stats.observable_source_unlinked", self.codes(g, "failed"))

    def test_a6b_domain_shift_failed_is_unresolved(self):
        st, p = self.chain(ml_mut=lambda m: m["extension"]["domain_shift"].update(status="failed"))
        g = self.gate(st, p)
        self.assertEqual(g["status"], "unresolved", g)
        self.assertIn("gate.ml_input_unresolved", self.codes(g, "unresolved"))

    def test_a6c_overlap_not_run_is_unresolved(self):
        st, p = self.chain(ml_mut=lambda m: m["extension"]["splits"]["overlap_check"].update(result="not-run"))
        g = self.gate(st, p)
        self.assertEqual(g["status"], "unresolved", g)

    def test_relabelled_clean_chain_passes_and_bad_ml_fails(self):
        st, p = self.chain()
        self.assertEqual(self.gate(st, p)["status"], "passed", self.gate(st, p))
        st, p = self.chain(ml_mut=lambda m: m["extension"].update(model_hash=""))
        g = self.gate(st, p)
        self.assertEqual(g["status"], "failed", g)
        self.assertIn("gate.ml_input_invalid", self.codes(g, "failed"))

    def test_input_of_the_wrong_type_or_hash_fails(self):
        st, p = self.chain(st_mut=lambda s: s["inputs"][0].update(artifact_type="dataset-record"))
        self.assertEqual(self.gate(st, p)["status"], "failed")
        st, p = self.chain(st_mut=lambda s: s["inputs"][0].update(sha256="0" * 64))
        g = self.gate(st, p)
        self.assertEqual(g["status"], "failed", g)
        self.assertIn("gate.ml_input_hash_mismatch", self.codes(g, "failed"))

    def test_without_a_location_the_ml_input_is_unchecked(self):
        st, _ = self.chain()
        g = validate.publication_gate(st)
        self.assertEqual(g["status"], "unresolved", g)
        self.assertIn("gate.ml_input_unchecked", self.codes(g, "unresolved"))

    def test_cli_resolves_relative_to_the_artifact(self):
        st, p = self.chain(ml_mut=lambda m: m["extension"]["domain_shift"].update(status="failed"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = validate.main([str(p), "--strict", "--gate", "publication"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["gate"]["status"], "unresolved")

    def test_dependencies_propagate_unresolved_findings(self):
        st, p = self.chain(ml_mut=lambda m: m["extension"]["domain_shift"].update(status="failed"))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = dependencies.main([str(p), "--root", str(self.dir)])
        rep = json.loads(out.getvalue())
        self.assertEqual(code, 3, rep)
        self.assertIn("dependency.source_unresolved", {f["code"] for f in rep["findings"]})


@unittest.skipUnless(HAVE_J9, "example outputs not present")
class J9ChainTests(unittest.TestCase):
    def test_dependencies_on_the_committed_j9_chain_exit_0(self):
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "output"
            shutil.copytree(J9 / "artifacts", dst / "artifacts")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = dependencies.main([str(dst / "artifacts" / "statistical_result.json"), "--root", str(dst)])
        self.assertEqual(code, 0, out.getvalue())

    def test_ml_artifact_lists_tool_outputs_as_source_files_not_inputs(self):
        self.assertEqual(ML0["inputs"], [])
        refs = {f["ref"] for f in ML0["extension"]["source_files"]}
        self.assertIn("work/run_summary.json", refs)
        self.assertTrue(all(len(f["sha256"]) == 64 for f in ML0["extension"]["source_files"]))


if __name__ == "__main__":
    unittest.main()
