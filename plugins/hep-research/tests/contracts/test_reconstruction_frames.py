"""Witness W3 of the reconstruction contracts (plan Section 12, contract-map.md): continuous frames, halos and IOV
crossings. This tests keys and ownership only; a real halo depends on the method. core/partition expresses the cores
and refuses gaps and overlaps; it has no halo, so the sidecar carries it. Synthetic documents only."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.reconstruction import check_frame_conditions, read_sidecar, same_observable_domain  # noqa: E402
from core.partition import engine  # noqa: E402
from tests.contracts.reconstruction_fixtures import (calibration_payload, code_list, frame_payloads, frame_product,  # noqa: E402
                                                     frame_witness, sealed, used_payload)


def payload_list():
    return list(frame_payloads().values())


class Ownership(unittest.TestCase):
    def setUp(self):
        self.frames = frame_witness()

    def refused(self):
        return code_list(read_sidecar(frame_product(self.frames)))

    def test_witness_is_read(self):
        self.assertEqual(self.refused(), [])
        self.assertEqual(code_list(check_frame_conditions(frame_product(self.frames), payload_list())), [])

    def test_halo_key_counted_twice_is_caught(self):
        self.frames["outputs"].append(dict(self.frames["outputs"][5], owner="core-a"))
        self.assertIn("reconstruction.frames.halo_double_count", self.refused())

    def test_boundary_key_five_belongs_to_the_second_core(self):
        self.frames["outputs"][5]["owner"] = "core-a"
        self.assertIn("reconstruction.frames.wrong_owner", self.refused())

    def test_cores_must_tile_the_domain(self):
        self.frames["partitions"][1]["core"] = [6, 10]
        self.assertIn("reconstruction.frames.cores_do_not_tile", self.refused())

    def test_a_huge_domain_is_one_finding_at_once(self):
        """Re-review minor 3: nothing walks a domain the outputs do not account for."""
        for end in (10**5, 10**400):
            self.frames["domain"] = [0, end]
            self.assertEqual(self.refused(), ["reconstruction.frames.key_without_output"], end)

    def test_a_halo_wider_than_the_stream_is_allowed(self):
        """Re-review 2 minor 8: a method's halo may outgrow a short stream; every window is then at an edge."""
        self.frames["partitions"] = [{"partition_id": "core-a", "core": [0, 10], "halo": 7, "halo_keys": []}]
        for key_output in self.frames["outputs"]:
            key_output.update({"owner": "core-a", "window": "edge-incomplete"})
        self.frames["accounts"].update({"edge_incomplete": [key_output["key"] for key_output in self.frames["outputs"]], "gap_adjacent": []})
        self.assertEqual(self.refused(), [])

    def test_a_huge_halo_returns_at_once(self):
        """Re-review minor 3."""
        self.frames["partitions"][0]["halo"] = 10**400
        self.assertIn("reconstruction.frames.halo_mismatch", self.refused())

    def test_many_keys_read_in_linear_time(self):
        """Re-review 2 minor 3."""
        size, frames = 100000, self.frames
        identity = frames["outputs"][0]["payload_id"]
        frames.update({"domain": [0, size], "partitions": [{"partition_id": "core-a", "core": [0, size], "halo": 0, "halo_keys": []}], "missing_keys": [],
                       "outputs": [{"key": key, "owner": "core-a", "payload_id": identity, "window": "complete"} for key in range(size)],
                       "accounts": {"observed": size, "owned": size, "missing": 0, "edge_incomplete": [], "gap_adjacent": []}})
        self.assertEqual(self.refused(), [])

    def test_lost_key_is_caught(self):
        del self.frames["outputs"][3]
        self.assertIn("reconstruction.frames.key_without_output", self.refused())

    def test_accounts_must_agree(self):
        self.frames["accounts"]["owned"] = 10
        self.assertIn("reconstruction.frames.accounts_mismatch", self.refused())

    def test_core_partition_expresses_the_cores(self):
        manifest = engine.make_manifest("frame-witness", 10, 5, 1)
        self.assertEqual([[chunk["start"], chunk["stop"]] for chunk in manifest["chunks"]],
                         [partition["core"] for partition in self.frames["partitions"]])


class ConditionsPerKey(unittest.TestCase):
    def test_first_payload_for_the_whole_chunk_is_caught(self):
        frames = frame_witness()
        first = frames["outputs"][0]["payload_id"]
        for item in frames["outputs"]:
            item["payload_id"] = first
        self.assertIn("reconstruction.frames.payload_outside_iov", code_list(check_frame_conditions(frame_product(frames), payload_list())))

    def test_unknown_payload_is_caught(self):
        frames = frame_witness()
        frames["outputs"][0]["payload_id"] = "f" * 64
        document = frame_product(frames)
        document["conditions_used"].append(dict(document["conditions_used"][0], payload_id="f" * 64))
        self.assertEqual(code_list(check_frame_conditions(document, payload_list())), ["reconstruction.frames.unknown_payload"])

    def test_a_payload_valid_on_two_coordinates(self):
        """Re-review 2 minor 5, Section 9.3: other coordinates of the observation are stated beside the key."""
        predicates = [{"coordinate": "position-key", "start": 0, "end": 10, "closure": "half-open"}, {"coordinate": "run", "start": 1, "end": 9, "closure": "half-open"}]
        payload = calibration_payload("1", iov={"predicates": predicates})
        payload = sealed(payload)
        frames = frame_witness()
        for key_output in frames["outputs"]:
            key_output["payload_id"] = payload["payload_id"]
        document = frame_product(frames)
        document["conditions_used"] = [used_payload(payload)]
        self.assertEqual(code_list(check_frame_conditions(document, [payload])), ["reconstruction.frames.payload_outside_iov"] * 9, "the run is not stated")
        frames["fixed_coordinates"] = {"run": 5}
        self.assertEqual(code_list(check_frame_conditions(document, [payload])), [])
        frames["fixed_coordinates"] = {"run": 50}
        self.assertEqual(code_list(check_frame_conditions(document, [payload])), ["reconstruction.frames.payload_outside_iov"] * 9)

    def test_forged_payload_is_caught(self):
        """Minor 11."""
        payloads = payload_list()
        payloads[0] = dict(payloads[0], content_sha256="9" * 64)
        self.assertIn("conditions.identity_mismatch", code_list(check_frame_conditions(frame_product(), payloads)))

    def test_used_payload_must_be_recorded(self):
        """R32: a key's payload is among the product's recorded conditions."""
        document = frame_product()
        document["conditions_used"].pop()
        self.assertIn("reconstruction.frames.unrecorded_payload", code_list(read_sidecar(document)))


class GapsAndEdges(unittest.TestCase):
    def setUp(self):
        self.frames = frame_witness()

    def refused(self):
        return code_list(read_sidecar(frame_product(self.frames)))

    def test_original_gap_stays_marked(self):
        self.frames["missing_keys"] = []
        self.assertIn("reconstruction.frames.key_without_output", self.refused())

    def test_gap_filled_by_a_halo_is_caught(self):
        self.frames["outputs"].append({"key": 7, "owner": "core-b", "payload_id": self.frames["outputs"][-1]["payload_id"], "window": "complete"})
        self.assertIn("reconstruction.frames.missing_restored", self.refused())

    def test_halo_does_not_restore_a_gap_at_the_core_boundary(self):
        self.frames = frame_witness(gap=5)
        self.assertEqual(self.refused(), [])
        self.frames["partitions"][0]["halo_keys"] = [5]
        self.assertIn("reconstruction.frames.halo_mismatch", self.refused())

    def test_complete_window_at_stream_end_is_caught(self):
        self.frames["outputs"][-1]["window"] = "complete"
        self.assertIn("reconstruction.frames.incomplete_window_claimed", self.refused())

    def test_complete_window_beside_the_gap_is_caught(self):
        self.frames["outputs"][6]["window"] = "complete"
        self.assertIn("reconstruction.frames.incomplete_window_claimed", self.refused())

    def test_window_labels_are_two_way(self):
        """Minor 3: an interior key cannot claim an edge, and a key far from the gap cannot claim one."""
        for index, label, bucket in ((6, "edge-incomplete", "edge_incomplete"), (3, "gap-adjacent", "gap_adjacent")):
            self.frames = frame_witness()
            key_output = self.frames["outputs"][index]
            for name in ("edge_incomplete", "gap_adjacent"):
                self.frames["accounts"][name] = [key for key in self.frames["accounts"][name] if key != key_output["key"]]
            self.frames["accounts"][bucket] = sorted(self.frames["accounts"][bucket] + [key_output["key"]])
            key_output["window"] = label
            self.assertIn("reconstruction.frames.window_mismatch", self.refused())


class ComparisonDomain(unittest.TestCase):
    """W3: whole-stream and partition references are compared over the same observable domain."""

    @staticmethod
    def whole_stream():
        frames = frame_witness()
        frames["partitions"] = [{"partition_id": "whole", "core": [0, 10], "halo": 1, "halo_keys": []}]
        for item in frames["outputs"]:
            item["owner"] = "whole"
        return frames

    def test_whole_stream_is_a_valid_reference(self):
        self.assertEqual(code_list(read_sidecar(frame_product(self.whole_stream()))), [])

    def test_same_domain(self):
        self.assertTrue(same_observable_domain(frame_product(self.whole_stream()), frame_product()))

    def test_edge_exclusion_on_one_side_differs(self):
        partitioned = copy.deepcopy(frame_witness())
        partitioned["outputs"].pop(0)
        self.assertFalse(same_observable_domain(frame_product(self.whole_stream()), frame_product(partitioned)))


if __name__ == "__main__":
    unittest.main()
