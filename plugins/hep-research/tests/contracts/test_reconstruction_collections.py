"""Witness W1 of the reconstruction contracts (plan Section 12, contract-map.md): collections, source links and state;
scenarios A06 (empty, absent, invalid, not-applicable), A08 (reordering, subset, persistence) and A09 (truth-assisted
fixture). Passing proves the stated contract behaviour only. Synthetic documents only."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.reconstruction import check_connection, check_products, dereference, object_count, read_sidecar  # noqa: E402
from tests.contracts.reconstruction_fixtures import (code_list, collection_witness, measurement, port, product,  # noqa: E402
                                                     reference)


class SourceLinks(unittest.TestCase):
    def setUp(self):
        self.witness = collection_witness()
        self.products = list(self.witness.values())

    def test_witness_is_read(self):
        for document in self.products:
            self.assertEqual(code_list(read_sidecar(document)), [])
        self.assertEqual(code_list(check_products(self.products)), [])

    def test_key_zero_in_two_products_stays_two_objects(self):
        first = dereference(reference("product.hits-a", key=0), self.products)
        second = dereference(reference("product.hits-b", key=0), self.products)
        self.assertEqual((first["surface"], first["state_type"]), ("surface:plane-1", "measured"))
        self.assertEqual((second["surface"], second["state_type"]), ("surface:plane-2", "filtered"))

    def test_reordered_subset_reaches_the_original_measurement(self):
        subset_row_zero = dereference(reference("product.hits-a-subset", row=0), self.products)
        self.assertEqual(subset_row_zero["key"], 2, "row 0 of the subset is key 2, not key 0")
        original = dereference(subset_row_zero["source_links"][0], self.products)
        self.assertEqual(original["native_ref"], "native:2")

    def test_row_index_across_products_is_detected(self):
        self.witness["subset"]["objects"][0]["source_links"] = [reference("product.hits-a", row=0)]
        self.assertIn("reconstruction.reference.row_across_products", code_list(check_products(self.products)))

    def test_reference_without_a_product_identity_is_refused(self):
        self.witness["subset"]["objects"][0]["source_links"] = [{"collection": "measurements", "revision": 1, "row": 0}]
        self.assertTrue(code_list(read_sidecar(self.witness["subset"])))

    def test_dropped_target_is_explicit(self):
        self.witness["first"]["objects"].pop(0)
        self.assertIn("reconstruction.reference.dangling", code_list(check_products(self.products)))
        self.assertIsNone(dereference(reference("product.hits-a", key=0), self.products),
                          "inability to dereference is explicit, never another object")

    def test_reference_to_another_revision_is_refused(self):
        self.witness["first"]["revision"] = 2
        self.assertIn("reconstruction.reference.stale_revision", code_list(check_products(self.products)))
        self.assertIsNone(dereference(reference("product.hits-a", key=0, revision=1), self.products))

    def test_persisted_copy_keeps_the_mapping(self):
        import json
        restored = json.loads(json.dumps(self.products))
        self.assertEqual(code_list(check_products(restored)), [])
        self.assertEqual(dereference(reference("product.hits-a-subset", key=2), restored)["source_links"][0]["key"], 2)

    def test_duplicate_key_or_product_is_refused(self):
        self.witness["first"]["objects"].append(measurement(0))
        self.assertIn("reconstruction.product.duplicate_key", code_list(read_sidecar(self.witness["first"])))
        self.assertIn("reconstruction.product.duplicate_identity",
                      code_list(check_products([self.witness["second"], self.witness["second"]])))


class Presence(unittest.TestCase):
    """A06: the four states without objects stay distinct, and only a valid empty collection counts zero objects."""

    def test_valid_empty_counts_zero(self):
        document = product(objects=[], presence="valid-empty")
        self.assertEqual(code_list(read_sidecar(document)), [])
        self.assertEqual(object_count(document), 0)

    def test_other_states_have_no_count(self):
        for state in ("absent", "invalid", "not-applicable"):
            document = product(presence=state)
            self.assertEqual(code_list(read_sidecar(document)), [], state)
            self.assertIsNone(object_count(document), state)

    def test_absent_treated_as_empty_is_refused(self):
        for state in ("absent", "invalid", "not-applicable"):
            self.assertIn("reconstruction.presence.objects_without_presence",
                          code_list(read_sidecar(product(objects=[], presence=state))), state)

    def test_a_sidecar_need_not_list_a_native_collection(self):
        """M2: W1 marks the native object a typed native reference, and Section 8.2 asks no listing."""
        document = product(presence="present")
        self.assertEqual(code_list(read_sidecar(document)), [])
        self.assertIsNone(object_count(document), "no count is known here; not zero")

    def test_a_link_into_a_native_collection_cannot_be_followed_here(self):
        """M2, A08: inability to dereference is explicit, and it is not a dangling link."""
        native = product("product.native")
        holder = product("product.reco", [measurement(0, links=[reference("product.native", key=0)])])
        report = check_products([native, holder])
        self.assertEqual(code_list(report), [])
        self.assertEqual([f.code for f in report.findings], ["reconstruction.reference.native_only"])
        self.assertIsNone(dereference(reference("product.native", key=0), [native]))

    def test_empty_needs_an_empty_list_and_present_needs_objects(self):
        self.assertIn("reconstruction.presence.empty_without_objects", code_list(read_sidecar(product(presence="valid-empty"))))
        self.assertIn("reconstruction.presence.empty_with_objects",
                      code_list(read_sidecar(product(objects=[measurement(0)], presence="valid-empty"))))
        self.assertIn("reconstruction.presence.present_without_objects", code_list(read_sidecar(product(objects=[]))))

    def test_absent_cannot_feed_a_port_that_expects_a_collection(self):
        source = port(presence=["present", "absent"])
        self.assertIn("reconstruction.connect.presence_not_accepted", code_list(check_connection(source, port("input"))))


class TruthRole(unittest.TestCase):
    """A09: a truth-assisted path is claimed as that path only; the data side does not read truth."""

    def test_truth_cannot_feed_a_data_side_port(self):
        report = check_connection(port(role="truth-reference"), port("input"))
        self.assertIn("reconstruction.connect.truth_on_data_side", code_list(report))

    def test_truth_may_feed_a_truth_port(self):
        self.assertEqual(code_list(check_connection(port(role="truth-reference"), port("input", role="truth-reference"))), [])

    def test_truth_may_feed_validation_and_training(self):
        """Minor 10: Section 8.4 keeps data-side ports free of truth; validation against truth is a normal role."""
        for role in ("validation", "training-calibration"):
            self.assertEqual(code_list(check_connection(port(role="truth-reference"), port("input", role=role))), [], role)

    def test_a_validation_product_may_link_truth(self):
        """Minor 10."""
        truth = product("product.truth", [measurement(0)], role="truth-reference")
        derived = product("product.reco", [measurement(0, links=[reference("product.truth", key=0)])], role="validation")
        self.assertEqual(code_list(check_products([truth, derived])), [])

    def test_truth_cannot_feed_a_conditions_port(self):
        self.assertIn("reconstruction.connect.truth_on_data_side", code_list(check_connection(port(role="truth-reference"), port("input", role="conditions"))))

    def test_reconstruction_output_may_feed_validation_and_calibration(self):
        """M3: Section 8.4 check 3 asks that roles be explicit, not equal; R33-R35 exist for calibration from reconstructed objects."""
        for role in ("validation", "training-calibration"):
            self.assertEqual(code_list(check_connection(port(), port("input", role=role))), [], role)

    def test_truth_is_decided_by_the_data_side_rule(self):
        """M3: Section 8.4 check 3, "data-side ports do not depend on truth", decides truth into each role, none by accident."""
        for role, found in (("reconstruction-input", ["reconstruction.connect.truth_on_data_side"]), ("conditions", ["reconstruction.connect.truth_on_data_side"]),
                            ("validation", []), ("training-calibration", []), ("truth-reference", [])):
            self.assertEqual(code_list(check_connection(port(role="truth-reference"), port("input", role=role))), found, role)

    def test_validation_and_training_roles_stay_apart(self):
        """K08: sample roles stay separate, in both directions."""
        for source, target in (("training-calibration", "validation"), ("validation", "training-calibration")):
            self.assertEqual(code_list(check_connection(port(role=source), port("input", role=target))), ["reconstruction.connect.role_mismatch"])

    def test_truth_derived_object_in_a_data_product_is_refused(self):
        truth = product("product.truth", [measurement(0)], role="truth-reference")
        derived = product("product.reco", [measurement(0, links=[reference("product.truth", key=0)])])
        self.assertIn("reconstruction.product.truth_on_data_side", code_list(check_products([truth, derived])))
        derived["role"] = "truth-reference"
        self.assertEqual(code_list(check_products([truth, derived])), [], "the truth-assisted path is allowed when it says so")


class NativeLinks(unittest.TestCase):
    """Re-review 3 minor 4, W1: revision and collection are known without the objects, so a wrong one is detected before
    the link is left to the native side."""

    def test_a_wrong_collection_into_a_native_collection_is_dangling(self):
        native = product("product.native")
        holder = product("product.reco", [measurement(0, links=[reference("product.native", key=0, collection="clusters")])])
        self.assertEqual(code_list(check_products([native, holder])), ["reconstruction.reference.dangling"])

    def test_a_stale_revision_into_a_native_collection_is_stale(self):
        native = product("product.native", revision=2)
        holder = product("product.reco", [measurement(0, links=[reference("product.native", key=0)])])
        self.assertEqual(code_list(check_products([native, holder])), ["reconstruction.reference.stale_revision"])


if __name__ == "__main__":
    unittest.main()
