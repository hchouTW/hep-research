"""Conditions payloads of the reconstruction contracts (R32, K07, D2) and CAI-T06-1 to 4 (R37). Interface tests with
synthetic fixtures only: no constant is derived, and nothing here is a calibration or alignment claim."""
import json
import sys
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.conditions import (affected_payloads, check_binding, check_used, check_validation_claim, iov_holds,  # noqa: E402
                                  iov_intersection, reuse_decision)
from contracts.reconstruction import read_sidecar  # noqa: E402
from contracts.schema import validate  # noqa: E402
from tests.contracts.reconstruction_fixtures import (NOMINAL_GEOMETRY, OTHER_GEOMETRY, alignment_payload,  # noqa: E402
                                                     calibration_payload, code_list, consumer, iov, payload_valid_over, sealed,
                                                     used_payload)


class PayloadShape(unittest.TestCase):
    """R32: every field of the payload shape is present and judged."""

    def test_three_kinds_are_accepted(self):
        mask = calibration_payload(kind="channel-mask")
        for payload in (calibration_payload(), alignment_payload(), mask):
            self.assertEqual(code_list(read_sidecar(payload)), [], payload["kind"])

    def test_other_kind_is_refused(self):
        self.assertTrue(code_list(read_sidecar(calibration_payload(kind="beam-spot-guess"))))

    def test_required_fields(self):
        for field in ("kind", "producer", "iov", "parametrization", "frame", "derived_against", "constraints_used",
                      "unconstrained_modes", "origin"):
            payload = calibration_payload()
            del payload[field]
            self.assertTrue(code_list(read_sidecar(payload)), field)

    def test_external_producer_names_its_source(self):
        payload = calibration_payload(producer={"kind": "external"})
        self.assertIn("conditions.producer_incomplete", code_list(read_sidecar(sealed(payload))))
        payload = calibration_payload(producer={"kind": "step"})
        self.assertIn("conditions.producer_incomplete", code_list(read_sidecar(sealed(payload))))

    def test_alignment_states_degrees_of_freedom_and_geometry(self):
        payload = alignment_payload()
        del payload["alignment"]
        self.assertIn("conditions.alignment_incomplete", code_list(read_sidecar(sealed(payload))))
        payload = alignment_payload(derived_against={"upstream_payloads": []})
        self.assertIn("conditions.derivation_missing", code_list(read_sidecar(payload)))

    def test_calibration_states_its_upstream_chain(self):
        self.assertIn("conditions.derivation_missing", code_list(read_sidecar(calibration_payload(derived_against={"geometry_id": NOMINAL_GEOMETRY}))))

    def test_loop_round_and_uncertainty_are_expressible(self):
        payload = calibration_payload(loop={"family": "synthetic-loop", "round": 2},
                                      uncertainty={"representation": "covariance", "reference": "native:uncertainty"})
        self.assertEqual(code_list(read_sidecar(payload)), [])
        self.assertTrue(code_list(read_sidecar(calibration_payload(loop={"family": "synthetic-loop", "round": 0}))))

    def test_derived_subset_has_its_own_identity_and_source(self):
        parent = alignment_payload()
        subset = alignment_payload(content="3", derived_from=parent["payload_id"])
        self.assertNotEqual(parent["payload_id"], subset["payload_id"])
        self.assertEqual(code_list(read_sidecar(subset)), [])

    def test_identity_is_checked(self):
        payload = calibration_payload()
        payload["content_sha256"] = "9" * 64
        self.assertIn("conditions.identity_mismatch", code_list(read_sidecar(payload)))

    def test_required_extension_stops_a_payload_reader(self):
        payload = calibration_payload(required_extensions=["conditions:future-field-v2"])
        self.assertEqual(code_list(read_sidecar(payload)), ["reconstruction.reader.unknown_required_extension"])


class GeometryIdentity(unittest.TestCase):
    """D2, finish-plan C1: geometry_id is checked against the released schema, not a second identity."""

    @staticmethod
    def released_form():
        schema = json.loads((ROOT / "contracts/schemas/ext_computational_run.json").read_text(encoding="utf-8"))
        return schema["properties"]["geometry"]["properties"]["geometry_id"]

    def test_payload_geometry_id_satisfies_the_released_form(self):
        identity = alignment_payload()["derived_against"]["geometry_id"]
        self.assertTrue(validate(identity, self.released_form()).ok)

    def test_both_schemas_refuse_the_same_malformed_identities(self):
        for malformed in ("A" * 64, "a" * 63, "not-an-identity"):
            self.assertFalse(validate(malformed, self.released_form()).ok, malformed)
            self.assertTrue(code_list(read_sidecar(sealed(alignment_payload(geometry=malformed)))), malformed)


class ValidityIntervals(unittest.TestCase):
    """K07: one axis intersects; different coordinates are predicates that must all hold."""

    def test_half_open_boundary(self):
        self.assertTrue(iov_holds(payload_valid_over(iov(0, 5)), {"position-key": 4}))
        self.assertFalse(iov_holds(payload_valid_over(iov(0, 5)), {"position-key": 5}))
        self.assertTrue(iov_holds(payload_valid_over(iov(0, 5, closure="closed")), {"position-key": 5}))

    def test_missing_coordinate_does_not_hold(self):
        self.assertFalse(iov_holds(payload_valid_over(iov(0, 5)), {"run": 4}))

    def test_intersection_on_one_axis(self):
        self.assertEqual(iov_intersection([payload_valid_over(iov(0, 5)), payload_valid_over(iov(3, 9))]), iov(3, 5))
        self.assertIsNone(iov_intersection([payload_valid_over(iov(0, 3)), payload_valid_over(iov(3, 9))]), "disjoint: no common validity")

    def test_different_coordinates_all_hold(self):
        joined = iov_intersection([payload_valid_over(iov(0, 5)), payload_valid_over(iov(100, 200, coordinate="run"))])
        self.assertEqual(len(joined["predicates"]), 2)
        self.assertTrue(iov_holds(payload_valid_over(joined), {"position-key": 1, "run": 150}))
        self.assertFalse(iov_holds(payload_valid_over(joined), {"position-key": 1, "run": 50}))

    def test_mixed_closures_state_no_common_validity(self):
        """Re-review 2 minor 6, Section 9.3: open and closed endpoints follow source rules."""
        self.assertIsNone(iov_intersection([payload_valid_over(iov(0, 10)), payload_valid_over(iov(0, 10, closure="closed"))]))

    def test_no_dependency_gives_no_validity(self):
        self.assertIsNone(iov_intersection([]))

    def test_empty_half_open_interval_is_refused(self):
        self.assertIn("conditions.iov_empty", code_list(read_sidecar(sealed(calibration_payload(iov=iov(3, 3))))))
        self.assertEqual(code_list(read_sidecar(sealed(calibration_payload(iov=iov(3, 3, closure="closed"))))), [])

    def test_reversed_interval_is_refused(self):
        self.assertIn("conditions.iov_reversed", code_list(read_sidecar(sealed(calibration_payload(iov=iov(9, 3))))))


class SameTagNewContent(unittest.TestCase):
    """CAI-T06-1: a payload change under the same tag triggers invalidation (Section 9.9)."""

    def setUp(self):
        self.old, self.changed = calibration_payload("1"), calibration_payload("4")
        self.used = consumer(used_payload(self.old))

    def test_tag_is_the_same_and_identity_differs(self):
        self.assertEqual(self.old["tag"], self.changed["tag"])
        self.assertNotEqual(self.old["payload_id"], self.changed["payload_id"])

    def test_unchanged_identity_may_be_reused(self):
        self.assertTrue(reuse_decision(self.used, {"gain": self.old})["reuse"])

    def test_changed_content_under_one_tag_invalidates(self):
        decision = reuse_decision(self.used, {"gain": self.changed})
        self.assertFalse(decision["reuse"])
        self.assertEqual(decision["changed"], ["gain"])

    def test_stale_stored_identity_does_not_pass_as_fresh(self):
        stale = dict(self.changed, payload_id=self.old["payload_id"])
        self.assertFalse(reuse_decision(self.used, {"gain": stale})["reuse"], "the identity is computed afresh (Section 9.8)")

    def test_missing_slot_invalidates(self):
        self.assertFalse(reuse_decision(self.used, {})["reuse"])

    def test_unknown_dependencies_disable_reuse(self):
        self.assertFalse(reuse_decision(self.used, {"gain": self.old}, unknown_dependencies=True)["reuse"], "K07")

    def test_derived_payloads_follow(self):
        downstream = calibration_payload("5", upstream=[self.old["payload_id"]])
        further = calibration_payload("6", upstream=[downstream["payload_id"]])
        unrelated = calibration_payload("7")
        subset = calibration_payload("8", derived_from=further["payload_id"])
        found = affected_payloads([self.old["payload_id"]], [further, subset, unrelated, downstream])
        self.assertEqual(sorted(found), sorted([downstream["payload_id"], further["payload_id"], subset["payload_id"]]))

    def test_invalidation_takes_each_documented_shape(self):
        """M5."""
        parent = self.old
        child = calibration_payload("5", upstream=[parent["payload_id"]])
        for shape in ([parent, child], (parent, child), {"gain": parent, "child": child}):
            self.assertEqual(affected_payloads([parent["payload_id"]], shape), [child["payload_id"]], type(shape))

    def test_invalidation_never_reads_unknown_input_as_nothing_affected(self):
        """M5, Section 9.4: "conservatively broaden"."""
        parent = self.old
        child = calibration_payload("5", upstream=[parent["payload_id"]])
        self.assertEqual(sorted(affected_payloads(parent["payload_id"], [parent, child])), sorted([parent["payload_id"], child["payload_id"]]), "one id, not a list")
        self.assertIsNone(affected_payloads([parent["payload_id"]], (payload for payload in (parent, child))))
        self.assertIsNone(affected_payloads([parent["payload_id"]], 3))
        self.assertEqual(affected_payloads([], [parent, child]), [], "an empty list stays the answer for no change")

    def test_rounds_are_separable(self):
        """R36: payloads of two rounds differ, so the cached result of round 1 is not reused for round 2."""
        first = calibration_payload("1", loop={"family": "synthetic-loop", "round": 1})
        second = calibration_payload("1", loop={"family": "synthetic-loop", "round": 2})
        self.assertNotEqual(first["payload_id"], second["payload_id"])
        self.assertFalse(reuse_decision(consumer(used_payload(first)), {"gain": second})["reuse"])

    def test_added_dependency_invalidates(self):
        """M6: a slot the cached result never saw is a new dependency, so its identity is not verified."""
        decision = reuse_decision(self.used, {"gain": self.old, "alignment": alignment_payload()})
        self.assertFalse(decision["reuse"])
        self.assertEqual(decision["changed"], ["alignment"])
        self.assertFalse(reuse_decision(consumer(), {"gain": self.old})["reuse"])


class ConsumedRound(unittest.TestCase):
    """B3, R32, R36: every record states the round of the payload it consumed, and the round is checked."""

    def setUp(self):
        self.payload = calibration_payload(loop={"family": "synthetic-loop", "round": 2})

    def test_matching_round_is_accepted(self):
        self.assertEqual(code_list(check_used(consumer(used_payload(self.payload)), [self.payload])), [])

    def test_absent_round_is_refused(self):
        record = used_payload(self.payload)
        record["round"] = None
        self.assertIn("conditions.round_mismatch", code_list(check_used(consumer(record), [self.payload])))

    def test_wrong_round_is_refused(self):
        record = used_payload(self.payload)
        record["round"] = 1
        self.assertIn("conditions.round_mismatch", code_list(check_used(consumer(record), [self.payload])))

    def test_a_round_on_a_payload_outside_any_loop_is_refused(self):
        payload = calibration_payload()
        record = used_payload(payload)
        record["round"] = 1
        self.assertIn("conditions.round_mismatch", code_list(check_used(consumer(record), [payload])))


class StoredIdentities(unittest.TestCase):
    """Minor 11: a stored identity or tag is not trusted."""

    def test_forged_identity_is_refused(self):
        payload = calibration_payload()
        forged = dict(payload, content_sha256="9" * 64)
        self.assertIn("conditions.identity_mismatch", code_list(check_used(consumer(used_payload(payload)), [forged])))

    def test_a_retagged_payload_is_the_same_payload(self):
        """M4, R32: "invalidation compares identities, not tags"; check_used and reuse_decision agree on one record."""
        payload = calibration_payload()
        retagged = sealed(dict(payload, tag="current"))
        self.assertEqual(payload["payload_id"], retagged["payload_id"])
        recorded = consumer(used_payload(payload))
        self.assertEqual(code_list(check_used(recorded, [retagged])), [])
        self.assertTrue(reuse_decision(recorded, {"gain": retagged})["reuse"])


class NominalAndMeasured(unittest.TestCase):
    """CAI-T06-2: nominal and measured payloads are kept apart."""

    def test_same_content_gives_two_identities(self):
        self.assertNotEqual(calibration_payload(origin="nominal")["payload_id"], calibration_payload(origin="measured")["payload_id"])

    def test_nominal_is_refused_where_measured_is_required(self):
        report = check_binding(calibration_payload(origin="nominal"), {"origin": "measured", "upstream_chain": []})
        self.assertIn("conditions.nominal_as_measured", code_list(report))

    def test_nominal_is_accepted_where_nominal_is_declared(self):
        self.assertEqual(code_list(check_binding(calibration_payload(origin="nominal"), {"origin": "nominal", "upstream_chain": []})), [])

    def test_measured_is_refused_where_nominal_is_declared(self):
        report = check_binding(calibration_payload(), {"origin": "nominal", "upstream_chain": []})
        self.assertIn("conditions.measured_as_nominal", code_list(report))

    def test_a_product_cannot_record_nominal_as_measured(self):
        payload = calibration_payload(origin="nominal")
        record = used_payload(payload)
        self.assertEqual(code_list(check_used(consumer(record), [payload])), [])
        record["origin"] = "measured"
        self.assertIn("conditions.nominal_as_measured", code_list(check_used(consumer(record), [payload])))

    def test_measured_recorded_as_nominal_has_its_own_code(self):
        payload = calibration_payload()
        record = dict(used_payload(payload), origin="nominal")
        self.assertEqual(code_list(check_used(consumer(record), [payload])), ["conditions.measured_as_nominal"])

    def test_a_product_records_a_payload_that_exists(self):
        record = used_payload(calibration_payload("8"))
        self.assertIn("conditions.unknown_payload", code_list(check_used(consumer(record), [calibration_payload("1")])))


class ConstraintIsNotValidation(unittest.TestCase):
    """CAI-T06-3 and the P1 part of A37: a constraint used in the derivation is not its independent validation."""

    def test_independent_check_is_accepted(self):
        self.assertEqual(code_list(check_validation_claim(alignment_payload(), "validation.survey")), [])

    def test_used_constraint_is_refused_as_validation(self):
        report = check_validation_claim(alignment_payload(), "constraint.track-straightness")
        self.assertIn("conditions.constraint_as_validation", code_list(report))

    def test_payload_cannot_list_it_either(self):
        payload = alignment_payload(independent_validation=["constraint.track-straightness"])
        self.assertIn("conditions.constraint_as_validation", code_list(read_sidecar(payload)))

    def test_fields_of_the_identifiability_record_are_required(self):
        payload = alignment_payload()
        self.assertEqual(payload["unconstrained_modes"], ["mode.global-shear"])
        del payload["unconstrained_modes"]
        self.assertTrue(code_list(read_sidecar(payload)))


class DerivedAgainst(unittest.TestCase):
    """CAI-T06-4: a payload bound on a different geometry or upstream chain is refused, never silently applied."""

    def test_matching_geometry_is_accepted(self):
        self.assertEqual(code_list(check_binding(alignment_payload(), {"origin": "measured", "geometry_id": NOMINAL_GEOMETRY})), [])

    def test_different_geometry_is_refused(self):
        report = check_binding(alignment_payload(), {"origin": "measured", "geometry_id": OTHER_GEOMETRY})
        self.assertIn("conditions.geometry_mismatch", code_list(report))

    def test_unstated_geometry_is_refused(self):
        self.assertIn("conditions.geometry_mismatch", code_list(check_binding(alignment_payload(), {"origin": "measured"})))

    def test_different_upstream_chain_is_refused(self):
        first, second = calibration_payload("1"), calibration_payload("2")
        payload = calibration_payload("3", upstream=[first["payload_id"], second["payload_id"]])
        matching = {"origin": "measured", "upstream_chain": [first["payload_id"], second["payload_id"]]}
        self.assertEqual(code_list(check_binding(payload, matching)), [])
        swapped = {"origin": "measured", "upstream_chain": [second["payload_id"], first["payload_id"]]}
        self.assertIn("conditions.upstream_chain_mismatch", code_list(check_binding(payload, swapped)), "chain order is part of the definition")
        replaced = {"origin": "measured", "upstream_chain": [first["payload_id"]]}
        self.assertIn("conditions.upstream_chain_mismatch", code_list(check_binding(payload, replaced)))


class UnreadableInvalidation(unittest.TestCase):
    """Re-review 3 N2, Section 9.4: input that holds no payload document is unclear state, never "nothing affected"."""

    def setUp(self):
        self.parent = calibration_payload("1")
        self.child = calibration_payload("5", upstream=[self.parent["payload_id"]])

    def test_input_that_holds_no_document_gives_none(self):
        changed = [self.parent["payload_id"]]
        for payloads in ([self.parent["payload_id"], self.child["payload_id"]], ["a.json"], {"gain": "a.json"}, [None], [[self.parent, self.child]],
                         self.parent, [{"schema": "x"}], [self.parent, self.child["payload_id"]]):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.assertIsNone(affected_payloads(changed, payloads), repr(payloads)[:60])

    def test_a_payload_that_cannot_be_read_broadens_to_every_payload(self):
        forged = dict(self.child, payload_id="f" * 64)
        self.assertEqual(sorted(affected_payloads([self.parent["payload_id"]], [self.parent, forged])), sorted([self.parent["payload_id"], "f" * 64]))

    def test_an_empty_declared_set_has_nothing_to_invalidate(self):
        """Section 9.4 allows precise invalidation when the dependencies are fully declared; an empty set is declared."""
        self.assertEqual(affected_payloads([self.parent["payload_id"]], []), [])
        self.assertEqual(affected_payloads([self.parent["payload_id"]], {}), [])


if __name__ == "__main__":
    unittest.main()
