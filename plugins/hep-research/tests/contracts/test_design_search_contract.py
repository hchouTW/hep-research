"""Contracts CV-C1 (geant4 program C1.6, section C.4.9): the search_summary of a computational-run
(contracts/schemas/design_search_summary.json and the cross-field rules of contracts/validate.py), gated by
SEARCH_SUMMARY_FROM or strict; contracts/design.py recognises a search run only from that version on; the search spec
schema design_search_spec.json. SYNTHETIC documents."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts import CONTRACTS_VERSION, design  # noqa: E402
from contracts.schema import validate  # noqa: E402
from contracts.validate import SEARCH_SUMMARY_FROM, _at_least, validate_artifact  # noqa: E402

DIGEST = "a" * 64


def point(k: int, violation: float = 0.0) -> dict:
    return {"index": k, "effective_digest": DIGEST, "topology": "DES-TRK-001:tracking[N=6]",
            "genome": {"DES-TRK-001.parameters.layer_positions_m.n": 6}, "proposer": "random",
            "values": {"momentum-resolution-core": {"value": 0.08, "bound": "optimistic"}}, "violation": violation}


def run(version: str = SEARCH_SUMMARY_FROM, **summary_over) -> dict:
    summary = {"search_id": "SEARCH-1", "search_spec_sha256": DIGEST, "points": [point(0), point(1), point(2, 0.5)],
               "front": [0, 1], "finalists": [{"index": 1, "fixed_before": "expand"}], "levels": ["F1"],
               "optimizer": {"name": "nsga2", "implementation": "evaluate_design.py search", "backend": None,
                             "seed": 12345}, "seeds": {"geant4_search": []},
               "note": "search values are not evaluations"}
    summary.update(summary_over)
    return {"contract_version": version, "artifact_id": "demo-SEARCH-1", "artifact_type": "computational-run",
            "objective": "SYNTHETIC search run", "versions": {"plugin": "0.38.0", "contracts": version},
            "provenance": {"producer_skill": "hep-detector", "created": "2026-10-24"}, "inputs": [], "outputs": [],
            "status": ["synthetic", "unvalidated"], "unresolved_inputs": [],
            "extension": {"input_manifest": [], "tools": [], "commands": ["python3 evaluate_design.py search"],
                          "environment": {}, "seeds": {"optimizer": 12345}, "tolerances": {}, "exit_status": 0,
                          "output_hashes": {}, "argv": ["python3", "skills/hep-detector/scripts/evaluate_design.py",
                                                        "search"], "search_summary": summary}}


def codes(doc: dict, strict: bool = False) -> set:
    return {f.code for f in validate_artifact(doc, strict=strict).errors}


class SearchSummary(unittest.TestCase):
    def test_placeholder_version(self):
        """CV-C1 is a minor at or above 3.13.0, the version this reader implements."""
        self.assertTrue(_at_least(SEARCH_SUMMARY_FROM, "3.13.0"))
        self.assertTrue(_at_least(CONTRACTS_VERSION, SEARCH_SUMMARY_FROM))

    def test_valid(self):
        self.assertEqual(codes(run()), set())
        self.assertTrue(design.is_search_run(run()))

    def test_required_fields(self):
        for key in ("search_spec_sha256", "points", "front", "finalists"):
            doc = run()
            del doc["extension"]["search_summary"][key]
            self.assertIn("schema.required", codes(doc), key)

    def test_point_fields(self):
        doc = run()
        del doc["extension"]["search_summary"]["points"][0]["effective_digest"]
        self.assertIn("schema.required", codes(doc))
        doc = run()
        doc["extension"]["search_summary"]["points"][0]["proposer"] = "oracle"
        self.assertTrue(codes(doc))
        doc = run(levels=["F4"])
        self.assertTrue(codes(doc))

    def test_cross_field_rules(self):
        self.assertIn("search.unknown_point", codes(run(front=[0, 7])))
        self.assertIn("search.unknown_point", codes(run(finalists=[{"index": 9, "fixed_before": "expand"}])))
        self.assertIn("search.point_duplicate", codes(run(points=[point(0), point(0), point(1)])))
        self.assertTrue(codes(run(finalists=[{"index": 1, "fixed_before": "report"}])))
        self.assertIn("search.verdict_written", codes(run(ranking=["SEARCH-1 point 1"])))
        doc = run(recommended=1)
        self.assertIn("search.verdict_written", codes(doc))

    def test_points_file(self):
        pf = {"ref": "runs/SEARCH-1.points.jsonl", "sha256": DIGEST, "count": 40}
        doc = run(points_file=pf, front=[0, 35])
        self.assertIn("search.points_file_unlisted", codes(doc))
        doc["extension"]["output_hashes"] = {pf["ref"]: DIGEST}
        self.assertEqual(codes(doc), set())  # front points may live only in the file
        doc = run(points_file=pf, finalists=[{"index": 35, "fixed_before": "expand"}])
        doc["extension"]["output_hashes"] = {pf["ref"]: DIGEST}
        self.assertIn("search.finalist_not_inline", codes(doc))

    def test_gated_by_contract_version(self):
        """R2: a 3.12.0 run keeps its outcome (the field is an unchecked optional object) unless strict."""
        old = run(version="3.12.0", front=[0, 7])
        self.assertNotIn("search.unknown_point", codes(old))
        self.assertIn("search.unknown_point", codes(old, strict=True))
        self.assertFalse(design.is_search_run(old))

    def test_summary_must_be_an_object(self):
        doc = run()
        doc["extension"]["search_summary"] = ["not", "an", "object"]
        self.assertTrue(codes(doc))


class SearchSpecSchema(unittest.TestCase):
    SPEC = {"search_spec_version": 1, "design_spec": {"path": "design-spec.v1.json", "sha256": DIGEST},
            "base_candidate": "demo:cand-S", "objectives": [{"requirement": "REQ-TRK-001"},
                                                             {"figure_of_merit": "mass-budget", "reference_point": 3000}],
            "constraints": [{"requirement": "REQ-MDR-001"}],
            "free_parameters": [{"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions", "n": [4, 8],
                                 "min_spacing_m": 0.05},
                                {"ref": "DES-MAG-001.parameters.field_T", "range": [0.1, 1.0]}],
            "slots": {"tof": [0, 1], "bending": {"range": [0, 1], "ids": ["DES-MAG-001"]}},
            "rules_version": "1.0.0", "materials_version": "1.0.0", "budget": {"evaluations": 20000, "geant4": 0},
            "optimizer": {"name": "nsga2", "population": 200, "generations": 100, "eta_c": 15, "eta_m": 20,
                          "seed": 12345},
            "stopping": {"hypervolume_window": 10, "min_improvement": 0.001, "reference_point": "auto"},
            "finalists": {"max": 5, "distinct_topologies": True},
            "proposals": [{"id": "P1", "reason": "two TOF planes for PID", "enabled": {"tof": True}}]}

    def test_section_c44_sketch_is_valid(self):
        self.assertTrue(validate(self.SPEC, "design_search_spec.json").ok)

    def test_refusals(self):
        bad = []
        for path, value in ((("search_spec_version",), 2), (("optimizer", "name"), "random-walk"),
                            (("budget", "evaluations"), 0), (("base_candidate",), "cand-S"),
                            (("design_spec", "sha256"), "short"), (("free_parameters",), [{"ref": "field_T"}]),
                            (("finalists", "max"), 0), (("stopping", "reference_point"), "ideal"),
                            (("unknown",), 1)):
            doc = copy.deepcopy(self.SPEC)
            node = doc
            for k in path[:-1]:
                node = node[k]
            node[path[-1]] = value
            if not validate(doc, "design_search_spec.json").ok:
                bad.append(path)
        self.assertEqual(len(bad), 9, bad)


if __name__ == "__main__":
    unittest.main()
