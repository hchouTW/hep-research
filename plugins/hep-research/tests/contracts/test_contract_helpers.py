"""Direct tests of contract helpers that were only reached through other entry points (T11): the observable,
convention, finiteness and binned-payload checks, schema loading, the gate's side reduction, the registry's cycle
finder and profile-folder check, and the namespace helpers. Synthetic inputs only."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.comparison.gate import side_from_artifact  # noqa: E402
from contracts.evidence import namespace_of  # noqa: E402
from contracts.registry import check_profile_dir, find_cycles  # noqa: E402
from contracts.schema import Report, load_schema  # noqa: E402
from contracts.validate import check_binned, check_conventions, check_finite, check_observable  # noqa: E402
from contracts.vocab import Vocabulary, declared_namespaces  # noqa: E402

VALID = ROOT / "contracts" / "fixtures" / "artifacts" / "valid"


def codes(rep: Report) -> set:
    return {f.code for f in rep.findings}


class ValidateHelperTests(unittest.TestCase):
    def setUp(self):
        self.vocab = Vocabulary()

    def test_check_conventions(self):
        rep = Report()
        check_conventions({"frame": "center-of-mass", "fx:custom": 1, "made_up": 2}, self.vocab, rep, "$.c")
        self.assertEqual([(f.path, f.code) for f in rep.findings], [("$.c.made_up", "conventions.unknown_key")])

    def test_check_finite_reports_every_path(self):
        rep = Report()
        check_finite({"a": [1.0, float("nan")], "b": {"c": float("-inf")}, "d": 3}, rep)
        self.assertEqual(sorted(f.path for f in rep.errors), ["$.a[1]", "$.b.c"])
        self.assertEqual(codes(rep), {"number.non_finite"})

    def test_check_binned_one_and_two_axes(self):
        obs = {"unit": "pb", "variables": [{"name": "x", "edges": [0.0, 1.0, 2.0]}]}
        rep = Report()
        check_binned({"edges": [0.0, 1.0, 2.0], "values": [1.0, 2.0], "unit": "pb"}, rep, "$.d", obs)
        self.assertEqual(rep.findings, [])
        rep = Report()
        check_binned({"edges": [0.0, 2.0, 1.0], "values": [1.0], "unit": "fb",
                      "uncertainties": [{"name": "stat", "values": [0.1, 0.1, 0.1]}]}, rep, "$.d", obs)
        self.assertEqual(codes(rep), {"binned.edges_not_increasing", "binned.edges_mismatch", "binned.length",
                                      "binned.unit_mismatch", "binned.uncertainty_length"})
        rep = Report()
        check_binned({"edges": [0.0, 1.0, 2.0], "values": [1.0, 2.0], "unit": "fb",
                      "unit_conversion": {"from": "pb", "to": "fb", "factor": 1000.0, "justification": "1 pb = 1000 fb"}},
                     rep, "$.d", obs)
        self.assertEqual(rep.findings, [])
        obs2 = {"unit": "pb", "variables": [{"name": "x", "edges": [0.0, 1.0, 2.0]}, {"name": "y", "edges": [0.0, 1.0, 2.0, 3.0]}]}
        rep = Report()
        check_binned({"edges": [0.0, 1.0, 2.0], "values": [0.0] * 6, "axes": ["x", "y"]}, rep, "$.d", obs2)
        self.assertEqual(rep.findings, [])
        rep = Report()
        check_binned({"edges": [0.0, 1.0, 2.0], "values": [0.0] * 5}, rep, "$.d", obs2)
        self.assertEqual(codes(rep), {"binned.axes_missing", "binned.length"})

    def test_check_observable(self):
        rep = Report()
        check_observable({"variables": [{"name": "x", "edges": [0, 1], "points": [0.5]}], "bin_semantics": "unknown",
                          "normalization": {"kind": "exposure"}, "conventions": {}}, self.vocab, rep, "$.o")
        self.assertEqual(codes(rep), {"observable.edges_and_points", "observable.bin_semantics_missing",
                                      "normalization.value_missing"})
        rep = Report()
        check_observable({"variables": [{"name": "x", "edges": [0, 1]}], "bin_semantics": "point"}, self.vocab, rep, "$.o")
        self.assertEqual(codes(rep), {"observable.point_with_edges"})


class SchemaGateRegistryTests(unittest.TestCase):
    def test_load_schema_is_cached_and_complete(self):
        env = load_schema("envelope.json")
        self.assertIs(env, load_schema("envelope.json"))
        self.assertIn("artifact_type", env["properties"])

    def test_side_from_artifact(self):
        pred = json.loads((VALID / "prediction.json").read_text())
        side = side_from_artifact(pred)
        self.assertEqual(side["artifact_type"], "prediction")
        self.assertEqual(side["observable"], pred["extension"]["observable"])
        meas = json.loads((VALID / "dataset_record.json").read_text())
        mside = side_from_artifact(meas)
        self.assertEqual(mside["covariance"], meas["extension"]["covariance"]["status"])
        self.assertEqual(side_from_artifact({})["corrections"], [])

    def test_find_cycles(self):
        self.assertEqual(find_cycles({"a": {"depends_on": ["b"]}, "b": {"depends_on": []}}), [])
        self.assertEqual(find_cycles({"a": {"depends_on": ["b"]}, "b": {"depends_on": ["a"]}}), [["a", "b", "a"]])
        self.assertEqual(find_cycles({"a": {"depends_on": ["a"]}}), [["a", "a"]])
        self.assertEqual(find_cycles({"a": {"depends_on": ["missing"]}}), [])

    def test_check_profile_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "profiles"
            pdir = root / "p"
            pdir.mkdir(parents=True)
            rep = Report()
            self.assertIsNone(check_profile_dir(pdir, root, rep, "p"))
            self.assertIn("profile.missing_resource", codes(rep))
            rep = Report()
            self.assertIsNone(check_profile_dir(Path(td) / "elsewhere", root, rep, "p"))
            self.assertIn("profile.path_escapes", codes(rep))
            (pdir / "profile.json").write_text("{not json", encoding="utf-8")
            rep = Report()
            self.assertIsNone(check_profile_dir(pdir, root, rep, "p"))
            self.assertIn("profile.unreadable", codes(rep))
        shipped = ROOT / "profiles" / "experiments" / "synthetic-collider"
        rep = Report()
        prof = check_profile_dir(shipped, ROOT / "profiles", rep, "synthetic-collider")
        self.assertIsNotNone(prof)
        self.assertEqual(rep.errors, [])

    def test_namespace_helpers(self):
        self.assertEqual(namespace_of("ams-02:S01"), "ams-02")
        self.assertIsNone(namespace_of("S01"))
        self.assertIsNone(namespace_of("Bad:S01"))
        self.assertEqual(declared_namespaces({"vocabulary_namespaces": ["a", "b"], "evidence_namespace": "c"}), ["a", "b"])
        self.assertEqual(declared_namespaces({"evidence_namespace": "c"}), ["c"])


if __name__ == "__main__":
    unittest.main()
