"""T12 stage 2: conditions, invalidation and identity in reprocessing (T12-05 to T12-09, T12-24 to T12-27; plan v9.2 Sections 9.3,
9.4, 9.8, 9.9; A04, A14, A32, A40, A42).

Every expectation is fixed in docs/dev/detector-reconstruction/t12-stage-plan.md ("Stage 2", R1-R9) before the harness was written.
The DAGs are synthetic and run by skills/hep-computing/scripts/run_workflow.py --incremental. The T08 configuration and the T09 budget
are frozen files read by SHA-256 and copied into scratch folders before any change; neither is edited. No quality claim.

Run from the plugin root: python -m unittest tests.contracts.test_t12_reprocessing -v
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "hep-computing" / "scripts"))
sys.path.insert(0, str(ROOT / "adapters" / "calo-cluster" / "assets"))
from calo_recipe import configuration as calo_configuration  # noqa: E402
from contracts.conditions import reuse_decision  # noqa: E402
from control_layer_support import derivation as dv  # noqa: E402
from tests.contracts import t12_reprocessing as rp  # noqa: E402
from tests.contracts.reconstruction_fixtures import calibration_payload, iov  # noqa: E402
from tests._platform import needs  # noqa: E402

T08_CONFIGURATION = ROOT / "adapters" / "calo-cluster" / "assets" / "t08-grid-1.configuration.json"
T09_BUDGET = ROOT / "adapters" / "photon-likelihood" / "assets" / "t09-multistart-1.budget.json"
STEPS = ("calibrate", "pedestal-monitor", "cluster", "response", "report")


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@needs("process_groups")  # run_workflow.py refuses a host without them (missing-dependency, tests/core/test_hostcaps.py)
class Workspace(unittest.TestCase):
    """Each test gets a fresh reprocessing workspace that has run once in full."""

    legacy = False

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.space = rp.Workspace(Path(self._scratch.name), legacy=self.legacy)
        first = self.space.run(incremental=False)
        self.assertEqual(set(first.values()), {False}, first)

    def tearDown(self):
        self._scratch.cleanup()


class FrozenInputs(unittest.TestCase):
    def test_the_frozen_files_are_read_not_written(self):
        """The harness copies the frozen files; their bytes are the Freeze B ones before and after every scenario."""
        self.assertEqual(rp.T08_CONFIGURATION_SHA256, sha(T08_CONFIGURATION.read_bytes()))
        self.assertEqual(rp.T09_BUDGET_SHA256, sha(T09_BUDGET.read_bytes()))


class PayloadChange(Workspace):
    def test_r1_a_same_tag_payload_change_reruns_exactly_the_affected_steps(self):
        old_sidecar = self.space.read_json("conditions/gain.json")
        old_product = self.space.read_json("calibrated.product.json")
        monitor = self.space.read_bytes("monitor.json")
        self.space.change_gain([1.0, 1.1, 0.9, 1.05])
        new_sidecar = self.space.read_json("conditions/gain.json")
        self.assertEqual(new_sidecar["tag"], old_sidecar["tag"])
        self.assertNotEqual(new_sidecar["payload_id"], old_sidecar["payload_id"])
        skipped = self.space.run()
        self.assertEqual(skipped, {"calibrate": False, "pedestal-monitor": True, "cluster": False, "response": False, "report": False})
        self.assertEqual(self.space.read_bytes("monitor.json"), monitor)
        self.assertFalse(reuse_decision(old_product, {"gain": new_sidecar})["reuse"])
        self.assertTrue(reuse_decision(old_product, {"gain": old_sidecar})["reuse"])

    def test_nothing_changed_skips_everything(self):
        self.assertEqual(self.space.run(), {s: True for s in STEPS})


class UnknownClosure(Workspace):
    legacy = True

    def test_r2_a_step_with_unknown_closure_reruns_and_reuse_is_disabled(self):
        skipped = self.space.run()
        self.assertEqual(skipped, {**{s: True for s in STEPS}, "legacy": False})
        product = self.space.read_json("calibrated.product.json")
        sidecar = self.space.read_json("conditions/gain.json")
        self.assertFalse(reuse_decision(product, {"gain": sidecar}, unknown_dependencies=True)["reuse"])


class NativeChange(Workspace):
    def test_r3_a_rebuilt_native_tool_reruns_its_step_and_what_its_output_reaches(self):
        self.space.rebuild_tool(version="2")
        self.assertEqual(self.space.run(), {"calibrate": True, "pedestal-monitor": True, "cluster": False, "response": False,
                                            "report": False})

    def test_r3_a_byte_change_that_keeps_the_output_reruns_only_the_tool_step(self):
        self.space.rebuild_tool(version="1", comment="# rebuilt, same output")
        self.assertEqual(self.space.run(), {"calibrate": True, "pedestal-monitor": True, "cluster": False, "response": True,
                                            "report": True})


class ConfigurationChange(Workspace):
    def test_r4_a_changed_t08_constant_reruns_the_clusters_and_keeps_both_versions(self):
        old_sha = self.space.configuration_sha256()
        old_clusters = self.space.read_bytes(f"products/{old_sha}/clusters.json")
        self.space.change_configuration(seed_threshold_mev=12.0)
        new_sha = self.space.configuration_sha256()
        self.assertNotEqual(new_sha, old_sha)
        self.assertEqual(new_sha, calo_configuration.from_bytes(self.space.read_bytes("config/t08.configuration.json")).sha256)
        skipped = self.space.run()
        self.assertEqual(skipped, {"calibrate": True, "pedestal-monitor": True, "cluster": False, "response": False, "report": False})
        self.assertEqual(self.space.read_bytes(f"products/{old_sha}/clusters.json"), old_clusters, "the old version is kept")
        self.assertTrue(self.space.exists(f"products/{new_sha}/clusters.json"))
        self.assertEqual(self.space.read_json("response.json")["configuration_sha256"], new_sha, "the pairing follows")

    def test_r5_a_title_change_reruns_only_the_report(self):
        science = {name: self.space.read_bytes(name) for name in self.space.scientific_outputs()}
        records = {s: self.space.read_bytes(f"runs/{s}.computational-run.json") for s in STEPS if s != "report"}
        report = self.space.read_bytes("report.md")
        self.space.change_title("T12 reprocessing, retitled")
        self.assertEqual(self.space.run(), {**{s: True for s in STEPS}, "report": False})
        self.assertEqual({name: self.space.read_bytes(name) for name in science}, science)
        self.assertEqual({s: self.space.read_bytes(f"runs/{s}.computational-run.json") for s in records}, records)
        self.assertNotEqual(self.space.read_bytes("report.md"), report)

    def test_r5_finding_a_source_only_edit_changes_the_t08_identity(self):
        """Recorded, not a defect: the T08 identity is the file's SHA-256, so its non-scientific source text is in it (Section 9.4)."""
        old_sha = self.space.configuration_sha256()
        self.space.change_configuration(source="the same constants, another sentence")
        self.assertNotEqual(self.space.configuration_sha256(), old_sha)
        self.assertFalse(self.space.run()["cluster"])


class ConfigurationIdentity(unittest.TestCase):
    """R6 (T12-27): what a configuration change means, and that defaults are always written out."""

    def setUp(self):
        self.t08 = json.loads(T08_CONFIGURATION.read_text())
        self.t09 = json.loads(T09_BUDGET.read_text())

    def test_r6_t08_constants_need_response_revalidation(self):
        for key, value in (("seed_threshold_mev", 12.0), ("sharing_iterations", 31), ("noise_sigma_mev", 0.3)):
            with self.subTest(key=key):
                changed = {**self.t08, key: value}
                self.assertEqual(rp.configuration_change(self.t08, changed), {key: rp.PHYSICS})

    def test_r6_t08_source_text_is_metadata_and_format_is_identity(self):
        self.assertEqual(rp.configuration_change(self.t08, {**self.t08, "source": "other words"}), {"source": rp.METADATA})
        self.assertEqual(rp.configuration_change(self.t08, {**self.t08, "format": "calo-cluster-configuration/2"}),
                         {"format": rp.IDENTITY})

    def test_r6_t09_budget_keys_are_candidate_or_resource_limits(self):
        self.assertEqual(rp.configuration_change(self.t09, {**self.t09, "starts": self.t09["starts"][:-1]}), {"starts": rp.LIMIT})
        self.assertEqual(rp.configuration_change(self.t09, {**self.t09, "tie_tolerance": 1e-5}), {"tie_tolerance": rp.LIMIT})

    def test_r6_an_unknown_key_is_refused(self):
        with self.assertRaises(KeyError):
            rp.configuration_change(self.t08, {**self.t08, "extra": 1})

    def test_r6_a_value_left_to_a_default_is_refused_by_the_recipe(self):
        without = {k: v for k, v in self.t08.items() if k != "sharing_iterations"}
        with self.assertRaises(calo_configuration.ConfigurationError):
            calo_configuration.from_bytes(json.dumps(without).encode())

    def test_r6_an_iteration_limit_change_changes_the_identity(self):
        base = calo_configuration.from_bytes(T08_CONFIGURATION.read_bytes())
        changed = calo_configuration.from_bytes(json.dumps({**self.t08, "sharing_iterations": 31}).encode())
        self.assertNotEqual(base.sha256, changed.sha256)


class QualityReuse(unittest.TestCase):
    """R7 (T12-09): a reused artifact gets no pass under new criteria until the check runs again; old failures stay."""

    def test_r7_a_stricter_criterion_leaves_the_artifact_unchecked_until_it_runs(self):
        state = rp.quality_reuse_probe()
        self.assertEqual(state["label_before"], "ok")
        self.assertEqual(state["label_after_new_criterion"], "unchecked")
        self.assertEqual(state["label_after_reuse"], "unchecked", "a reuse is no check result")
        self.assertEqual(state["label_after_new_check"], "ok")
        self.assertEqual(state["historical_failures"], [[state["old_check"], state["old_criterion"], "fail"]])


class ChunkBinding(unittest.TestCase):
    """R8 (T12-24): a chunk crossing an IOV is subdivided; one payload for the whole chunk is refused."""

    def setUp(self):
        self.low = calibration_payload(content="1", iov=iov(0, 50))
        self.high = calibration_payload(content="2", iov=iov(50, 100))

    def test_r8_a_crossing_chunk_is_subdivided(self):
        binding = rp.bind_chunk(range(40, 60), [self.low, self.high])
        self.assertEqual(binding, [{"keys": [40, 49], "payload_id": self.low["payload_id"]},
                                   {"keys": [50, 59], "payload_id": self.high["payload_id"]}])
        self.assertEqual(rp.check_chunk_binding(binding, [self.low, self.high], range(40, 60)),
                         {"wrong_payload": [], "uncovered": [], "overlapping": []})

    def test_r8_the_first_keys_payload_on_the_whole_chunk_is_refused(self):
        wrong = [{"keys": [40, 59], "payload_id": self.low["payload_id"]}]
        self.assertEqual(rp.check_chunk_binding(wrong, [self.low, self.high], range(40, 60))["wrong_payload"], list(range(50, 60)))

    def test_r8_a_binding_that_leaves_keys_out_or_covers_them_twice_is_refused(self):
        """R8' (fix round 1, M6)."""
        short = [{"keys": [40, 49], "payload_id": self.low["payload_id"]}]
        self.assertEqual(rp.check_chunk_binding(short, [self.low, self.high], range(40, 60))["uncovered"], list(range(50, 60)))
        twice = [{"keys": [40, 49], "payload_id": self.low["payload_id"]}, {"keys": [45, 59], "payload_id": self.high["payload_id"]}]
        found = rp.check_chunk_binding(twice, [self.low, self.high], range(40, 60))
        self.assertEqual(found["overlapping"], list(range(45, 50)))
        self.assertEqual(found["wrong_payload"], list(range(45, 50)))

    def test_r8_each_payload_uses_its_own_coordinate(self):
        timed = calibration_payload(content="4", iov=iov(0, 100, coordinate="time-ns"))
        with self.assertRaisesRegex(ValueError, "no payload holds key 40"):
            rp.bind_chunk(range(40, 42), [timed])

    def test_r8_a_key_with_no_payload_or_two_is_refused(self):
        with self.assertRaisesRegex(ValueError, "no payload holds key 100"):
            rp.bind_chunk(range(95, 101), [self.low, self.high])
        overlap = calibration_payload(content="3", iov=iov(45, 55))
        with self.assertRaisesRegex(ValueError, "2 payloads hold key 45"):
            rp.bind_chunk(range(40, 50), [self.low, overlap])


class SourceScope(unittest.TestCase):
    """R9 (T12-08, A42): imports, working folder and outputs must lie outside every live root."""

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.root = Path(self._scratch.name)
        self.live = self.root / "main-checkout"
        self.live.mkdir()
        (self.live / "livemod.py").write_text("VALUE = 1\n")
        self.worktree = self.root / "worktree"
        self.worktree.mkdir()
        (self.worktree / ".git").write_text("gitdir: elsewhere\n")

    def tearDown(self):
        self._scratch.cleanup()

    def check(self, *extra, env_path=None, cwd=None):
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        if env_path:
            env["PYTHONPATH"] = str(env_path)
        p = subprocess.run([sys.executable, "-B", str(Path(rp.__file__)), "scope-check", "--snapshot", str(ROOT),
                            "--live", str(self.live), *map(str, extra)], capture_output=True, text=True, timeout=120,
                           env=env, cwd=str(cwd or self.root))
        return p.returncode, json.loads(p.stdout.strip().splitlines()[-1])

    def test_r9_a_clean_process_passes(self):
        code, out = self.check("--evidence-path", self.root / "evidence")
        self.assertEqual((code, out["status"]), (0, "ok"), out)

    def test_r9_a_module_imported_from_a_live_root_is_rejected(self):
        code, out = self.check("--import", "livemod", env_path=self.live)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)
        # compared as paths, not as a substring of JSON text: json.dumps escapes a non-ASCII or Windows path
        self.assertIn(str((self.live / "livemod.py").resolve()), [item.get("path") for item in out["offending"]])

    def test_r9_a_live_path_entry_is_rejected_even_unused(self):
        code, out = self.check(env_path=self.live)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)

    def test_r9_an_output_under_a_live_root_is_rejected(self):
        code, out = self.check("--evidence-path", self.live / "results")
        self.assertEqual((code, out["status"]), (2, "rejected"), out)

    def test_r9_a_working_folder_inside_a_live_root_is_rejected(self):
        code, out = self.check(cwd=self.live)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)

    def test_r9_a_namespace_package_under_a_live_root_is_rejected(self):
        """R9' (fix round 1, M7): a package without __init__.py has no __file__; its search locations are checked."""
        (self.live / "livens").mkdir()
        (self.live / "livens" / "part.py").write_text("VALUE = 2\n")
        code, out = self.check("--import", "livens", env_path=self.live)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)
        self.assertIn("livens", json.dumps(out["offending"]))

    def test_r9_an_interpreter_under_a_live_root_is_rejected(self):
        """R9': the running interpreter (as invoked, and resolved) must lie outside every live root."""
        (self.live / "bin").mkdir()
        link = self.live / "bin" / "python3"
        link.symlink_to(sys.executable)
        p = subprocess.run([str(link), "-B", str(Path(rp.__file__)), "scope-check", "--snapshot", str(ROOT), "--live", str(self.live)],
                           capture_output=True, text=True, timeout=120, cwd=str(self.root))
        out = json.loads(p.stdout.strip().splitlines()[-1])
        self.assertEqual((p.returncode, out["status"]), (2, "rejected"), out)
        self.assertIn("interpreter", json.dumps(out["offending"]))

    def test_r9_a_clean_worktree_path_does_not_prove_isolation(self):
        code, out = self.check("--import", "livemod", env_path=self.live, cwd=self.worktree)
        self.assertEqual((code, out["status"]), (2, "rejected"), out)


if __name__ == "__main__":
    unittest.main()
