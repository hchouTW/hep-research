"""Witness W4 of the reconstruction contracts (plan Section 12, contract-map.md): shared candidates and selected
revision, and the contract part of A21 (ordering and escape hypotheses with their own quality). Memory ownership stays a
typed native reference. Passing proves the stated contract behaviour only. Synthetic documents only."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.reconstruction import check_candidate_links, read_sidecar, selected_objects  # noqa: E402
from tests.contracts.reconstruction_fixtures import (candidate_product, candidate_witness, code_list,  # noqa: E402
                                                     collection_witness, hypothesis, product)


class SharedHypotheses(unittest.TestCase):
    def setUp(self):
        self.candidates = candidate_witness()

    def refused(self):
        return code_list(read_sidecar(candidate_product(self.candidates)))

    def test_sharing_is_allowed(self):
        self.assertEqual(self.refused(), [])
        shared = [item for item in self.candidates["hypotheses"] if item["state"] == "committed"]
        self.assertEqual({item["measurements"][0]["key"] for item in shared}, {0})

    def test_counting_follows_the_selected_hypothesis(self):
        self.assertEqual(selected_objects(candidate_product(self.candidates)), [("H1", 2)], "one object, from the selected revision")

    def test_counting_the_unselected_hypothesis_alone_is_caught(self):
        """B1: the policy selects H1, and a consumer counts H2 alone."""
        self.candidates["consumers"] = [{"consumer": "final-count", "hypothesis_id": "H2", "revision": 1, "use": "count"}]
        self.assertIn("reconstruction.candidate.count_not_selected", self.refused())

    def test_counting_with_no_selection_is_caught(self):
        """B1."""
        self.candidates["selection_policy"]["selected"] = {}
        self.assertIn("reconstruction.candidate.count_not_selected", self.refused())

    def test_one_entry_counted_twice_is_caught(self):
        """B1."""
        self.candidates["consumers"].append(dict(self.candidates["consumers"][0]))
        self.assertIn("reconstruction.candidate.counted_twice", self.refused())

    def test_consumer_of_the_old_revision_is_caught(self):
        self.candidates["consumers"][0]["revision"] = 1
        self.assertIn("reconstruction.candidate.stale_revision", self.refused())

    def test_old_and_new_revision_both_held_is_caught(self):
        self.candidates["consumers"].append({"consumer": "final-count", "hypothesis_id": "H1", "revision": 1, "use": "count"})
        self.assertIn("reconstruction.candidate.double_revision", self.refused())

    def test_uncommitted_revision_is_not_read(self):
        self.candidates["hypotheses"][1]["state"] = "open"
        self.assertIn("reconstruction.candidate.uncommitted_revision", self.refused())

    def test_exclusive_hypotheses_are_not_independent_objects(self):
        self.candidates["consumers"].append({"consumer": "final-count", "hypothesis_id": "H2", "revision": 1, "use": "count"})
        self.assertIn("reconstruction.candidate.exclusive_counted", self.refused())

    def test_reading_the_rejected_alternative_is_allowed(self):
        self.candidates["consumers"].append({"consumer": "diagnostic", "hypothesis_id": "H2", "revision": 1, "use": "read"})
        self.assertEqual(self.refused(), [])

    def test_unique_use_flag_cannot_delete_a_valid_hypothesis_early(self):
        self.candidates["pruning"] = [{"rule": "unique-hit-use", "stage": "before-selection", "removed": "H2"}]
        self.assertIn("reconstruction.candidate.premature_unique_use", self.refused())

    def test_declared_pruning_after_selection_is_allowed(self):
        self.candidates["pruning"] = [{"rule": "unique-hit-use", "stage": "after-selection", "removed": "H2"}]
        self.assertEqual(self.refused(), [])

    def test_dangling_consumer_is_caught(self):
        self.candidates["consumers"][0]["hypothesis_id"] = "H9"
        self.assertIn("reconstruction.candidate.dangling", self.refused())

    def test_discarded_hypothesis_leaves_no_reader(self):
        self.candidates["hypotheses"][1]["state"] = "discarded"
        self.assertIn("reconstruction.candidate.dangling", self.refused())

    def test_selected_hypothesis_must_exist_and_be_committed(self):
        self.candidates["selection_policy"]["selected"]["group-1"] = "H9"
        self.assertIn("reconstruction.candidate.selection_unresolved", self.refused())

    def test_two_committed_revisions_are_caught(self):
        self.candidates["hypotheses"][0]["state"] = "committed"
        self.assertEqual(self.refused(), ["reconstruction.candidate.two_committed_revisions"])

    def test_an_open_replacement_beside_a_commit_is_in_flight(self):
        """Re-review 2 minor 7, Section 10.1: consumers keep the committed revision meanwhile."""
        self.candidates["hypotheses"].append(hypothesis("H1", 3, "open", [0]))
        self.assertEqual(self.refused(), [])
        self.assertEqual(selected_objects(candidate_product(self.candidates)), [("H1", 2)])

    def test_duplicate_revision_is_caught(self):
        self.candidates["hypotheses"].append(hypothesis("H2", 1, "superseded", [0]))
        self.assertIn("reconstruction.candidate.duplicate_revision", self.refused())

    def test_memory_owner_is_a_native_reference(self):
        self.assertEqual(set(self.candidates["memory_owner"]), {"type"})
        del self.candidates["memory_owner"]
        self.assertTrue(self.refused(), "memory ownership stays expressible and separate from counting")


class MeasurementLinks(unittest.TestCase):
    def test_links_reach_their_measurements(self):
        self.assertEqual(code_list(check_candidate_links(candidate_product(), list(collection_witness().values()))), [])

    def test_a_link_into_a_native_collection_cannot_be_followed_here(self):
        """M2, A08: explicit, and not dangling."""
        report = check_candidate_links(candidate_product(), [product("product.hits-a")])
        self.assertEqual(code_list(report), [])
        self.assertEqual({finding.code for finding in report.findings}, {"reconstruction.reference.native_only"})

    def test_dangling_association_is_caught(self):
        products = collection_witness()
        products["first"]["objects"].pop(0)
        self.assertIn("reconstruction.candidate.dangling", code_list(check_candidate_links(candidate_product(), list(products.values()))))


class OrderingHypotheses(unittest.TestCase):
    """A21, contract part: each ordering or escape hypothesis keeps its own quality; the method itself is T11 and T10."""

    @staticmethod
    def ordered(**fields):
        details = {"hypothesis_kind": "ordering", "ordering": ["site-b", "site-a"], "escape": "contained",
                   "quality": {"metric": "synthetic-score", "value": 0.5}}
        details.update(fields)
        return details

    def test_two_orderings_stay_traceable(self):
        candidates = candidate_witness()
        candidates["hypotheses"][1].update(self.ordered())
        candidates["hypotheses"][2].update(self.ordered(ordering=["site-a", "site-b"], escape="escaped", quality={"metric": "synthetic-score", "value": 0.25}))
        self.assertEqual(code_list(read_sidecar(candidate_product(candidates))), [])

    def test_ordering_needs_its_escape_and_quality(self):
        candidates = candidate_witness()
        candidates["hypotheses"][1].update({"hypothesis_kind": "ordering", "ordering": ["site-a"]})
        self.assertIn("reconstruction.candidate.ordering_incomplete", code_list(read_sidecar(candidate_product(candidates))))


class NativeMeasurementLinks(unittest.TestCase):
    """Re-review 3 minor 4, W1: a stale revision or a wrong collection is known without the objects."""

    def test_a_stale_or_wrong_link_into_a_native_collection_is_dangling(self):
        for native in (product("product.hits-a", revision=2), product("product.hits-a", collection="clusters")):
            report = check_candidate_links(candidate_product(), [native])
            self.assertIn("reconstruction.candidate.dangling", code_list(report))
            self.assertNotIn("reconstruction.reference.native_only", [finding.code for finding in report.findings])


if __name__ == "__main__":
    unittest.main()
