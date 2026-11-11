"""examples/reconstruction-photon-likelihood (T09, adapters/photon-likelihood): generate a few synthetic t09-sphere/1 events, fit them
with reco.light.channel-likelihood/1 (the joint charge-time multistart fit, then the topology step) and check the product.

The offline replay of the committed recording must reproduce the committed output/ byte for byte and pass every check of run.py. The
checks are also driven on a recording made here from hand-made events (stage 3's and stage 4's noise-free stand-ins with the
generator's interface, not t09-sphere/1), honest and with one defect each: a recipe command that names a truth file, other readout
bytes than the product names, a topology product made from another multistart product, a product of another configuration, a
topology choice against the frozen rule, a topology product that does not carry its multistart product unchanged, another label, a
hit charge the likelihood does not reproduce, a multistart product in place of the topology product, a recorded probability failure, a
missing operation, a product the recipe would not write (caught by the rerun alone), a missing recording, and the refused live runs. With
HEP_T09_GENERATOR naming the frozen generator, the live run is repeated into a temporary folder and its recorded files must equal the
recording byte for byte. The T09 job points HEP_T09_EXAMPLE_RECORDED and HEP_T09_EXAMPLE_OUTPUT at its own first live run, since the
committed recording is copied from that job; elsewhere they default to the committed folders. Shared-model closure: no
photon-likelihood quality claim (K09 at Freeze B).
Run from the plugin root: python -m unittest tests.examples.test_reconstruction_photon_likelihood -v
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.adapters import test_photon_likelihood_topology as stage4

PLUGIN = Path(__file__).resolve().parents[2]
EXAMPLE = PLUGIN / "examples" / "reconstruction-photon-likelihood"
RECORDED = Path(os.environ.get("HEP_T09_EXAMPLE_RECORDED", EXAMPLE / "recorded"))
EXPECTED_OUTPUT = Path(os.environ.get("HEP_T09_EXAMPLE_OUTPUT", EXAMPLE / "output"))
HOST_PATH = re.compile(r"/ceph|/var/tmp|/tmp/|/dicos|/home/|/sharedfs|hpa-wn")
GENERATOR = os.environ.get("HEP_T09_GENERATOR", "")
RERUN = ("the recipe run again on the recorded readouts reproduces the recorded products: byte for byte on the recording's platform, "
         "else within the stated tolerances")


def load():
    spec = importlib.util.spec_from_file_location("reconstruction_photon_likelihood_run", EXAMPLE / "run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quiet(function, *arguments):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return function(*arguments)


class HandMadeGenerator(stage4.TwoSourceStandIn):
    """The frozen generator's interface, written in the stage 3 and 4 test modules: noise-free one-source events with median
    first-arrival times (main) and a noise-free two-source event of 3,000 and 2,500 photons (two-source). Not t09-sphere/1."""
    GENERATOR = "hand-made"
    PAIRS = [stage4.TwoSourceStandIn.PAIRS[1]]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class OfflineReplay(unittest.TestCase):
    """The committed recording (made by the T09 job with the frozen generator)."""

    @classmethod
    def setUpClass(cls):
        cls.example = load()
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.out = Path(cls.folder.name) / "output"
        cls.code = quiet(cls.example.main, ["--out", str(cls.out), "--recorded", str(RECORDED)])

    def test_the_replay_reproduces_the_committed_output(self):
        self.assertEqual(self.code, 0)
        self.assertEqual(sorted(path.name for path in self.out.iterdir()), sorted(path.name for path in EXPECTED_OUTPUT.iterdir()))
        for path in EXPECTED_OUTPUT.iterdir():
            with self.subTest(file=path.name):
                self.assertEqual((self.out / path.name).read_bytes(), path.read_bytes())

    def test_every_check_passes_and_nothing_is_claimed(self):
        summary = json.loads((self.out / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(len(summary["checks"]), len(self.example.CHECKS))
        self.assertEqual([item["check"] for item in summary["checks"] if not item["passed"]], [])
        self.assertEqual(summary["data"], "synthetic")
        self.assertEqual(summary["label"], "shared-model closure")
        self.assertTrue(summary["quality_claim"].startswith("none"))
        self.assertEqual((summary["generator"], summary["generator_sha256"]), ("t09-sphere/1", self.example.FROZEN_GENERATOR_SHA256))
        self.assertEqual(summary["block"], 1)  # the tuning block only
        self.assertEqual([(s["sample"], s["fixture"], s["stratum"], s["events"]) for s in summary["samples"]],
                         [("main", "main", 7, 2), ("two-source", "two-source", 0, 1)])
        self.assertEqual(summary["recorded_sha256"], {name: sha256(RECORDED / name) for name in self.example.RECORDED_FILES})

    def test_the_recording_and_the_output_hold_no_host_path(self):
        leaks = [f"{folder.name}/{path.name}" for folder in (RECORDED, EXPECTED_OUTPUT) for path in sorted(folder.iterdir())
                 if HOST_PATH.search(path.read_bytes().decode("utf-8", errors="replace"))]
        self.assertEqual(leaks, [])
        self.assertTrue(HOST_PATH.search("<work>/x /ceph/work/y"))  # the pattern finds what it is for


class HandMadeRecording(unittest.TestCase):
    """run.py's live path and every check, on hand-made events, honest and with one defect each."""

    @classmethod
    def setUpClass(cls):
        cls.example = load()
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.recorded = Path(cls.folder.name) / "recorded"
        cls.live_code = quiet(cls.example.live, HandMadeGenerator(), None, Path(cls.folder.name) / "work", cls.recorded)

    def copy_of_recording(self, name: str) -> Path:
        copy = Path(self.folder.name) / name
        shutil.copytree(self.recorded, copy)
        return copy

    def replay_of(self, recorded: Path):
        """(exit code, summary or None) of the replay of a recording."""
        out = recorded.parent / (recorded.name + "-out")
        code = quiet(self.example.main, ["--out", str(out), "--recorded", str(recorded)])
        summary = out / "summary.json"
        return code, (json.loads(summary.read_text(encoding="utf-8")) if summary.is_file() else None)

    def failed_checks(self, recorded: Path) -> list:
        code, summary = self.replay_of(recorded)
        self.assertEqual(code, 1)
        return [item["check"] for item in summary["checks"] if not item["passed"]]

    @staticmethod
    def edit_product(path: Path, edit) -> None:
        docs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        edit(docs)
        path.write_text("".join(json.dumps(doc, sort_keys=True, allow_nan=False) + "\n" for doc in docs), encoding="utf-8")

    def test_the_honest_recording_passes_every_check(self):
        self.assertEqual(self.live_code, 0)
        self.assertEqual(sorted(p.name for p in self.recorded.iterdir()), sorted(self.example.RECORDED_FILES))
        code, summary = self.replay_of(self.recorded)
        self.assertEqual(code, 0)
        self.assertEqual([c["check"] for c in summary["checks"] if not c["passed"]], [])
        self.assertEqual(len(summary["checks"]), len(self.example.CHECKS))
        self.assertEqual(summary["generator"], "hand-made")
        self.assertIsNone(summary["generator_sha256"])
        self.assertEqual([(e["sample"], e["event"], e["fit_status"]) for e in summary["events"]],
                         [("main", 0, "converged"), ("main", 1, "converged"), ("two-source", 0, "converged")])
        self.assertEqual([e["choice"] for e in summary["events"]], ["H1", "H1", "H2"])
        out = self.recorded.parent / (self.recorded.name + "-out")
        leaks = [p.name for p in list(self.recorded.iterdir()) + list(out.iterdir())
                 if HOST_PATH.search(p.read_bytes().decode("utf-8", errors="replace"))]
        self.assertEqual(leaks, [])

    def test_the_recipe_commands_read_the_readout_and_its_own_products_only(self):
        runs = json.loads((self.recorded / "runs.json").read_text(encoding="utf-8"))
        self.assertEqual([(r["sample"], r["operation"]) for r in runs["runs"]],
                         [(s, op) for s in ("main", "two-source") for op in ("generate", "fit", "topology", "check-product")])
        for run in runs["runs"]:
            if run["operation"] == "generate":
                self.assertEqual(run["data_side_files"], [f"{run['sample']}.readout"])
                continue
            with self.subTest(sample=run["sample"], operation=run["operation"]):
                files = [token for token in run["command"] if token.startswith("<work>/")]
                self.assertTrue(files)
                self.assertTrue(all(Path(token).name.startswith(run["sample"] + ".") for token in files), files)
                self.assertFalse([token for token in files if "truth" in token])

    def test_a_recipe_command_that_named_a_truth_file_fails(self):
        copy = self.copy_of_recording("truth-to-recipe")
        runs = json.loads((copy / "runs.json").read_text(encoding="utf-8"))
        run = next(r for r in runs["runs"] if r["operation"] == "topology")
        run["command"] = run["command"] + ["--truth", "<work>/main.truth.npz"]
        (copy / "runs.json").write_text(json.dumps(runs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertIn("the recipe's commands name no truth file", self.failed_checks(copy))

    def test_other_readout_bytes_than_the_product_names_fail(self):
        copy = self.copy_of_recording("other-readout")
        content = bytearray((copy / "main.readout").read_bytes())
        content[-2500] ^= 0x01                  # a byte of the last event's times (2 x 1,000 saturated flags follow)
        (copy / "main.readout").write_bytes(bytes(content))
        self.assertIn("each product names the recorded readout, and the topology product the recorded multistart product",
                      self.failed_checks(copy))

    def test_a_topology_product_of_another_multistart_product_fails(self):
        copy = self.copy_of_recording("other-h1")
        self.edit_product(copy / "two-source.topology.product", lambda docs: docs[0]["h1_product"].update(sha256="0" * 64))
        self.assertIn("each product names the recorded readout, and the topology product the recorded multistart product",
                      self.failed_checks(copy))

    def test_a_product_of_another_configuration_fails(self):
        copy = self.copy_of_recording("other-configuration")
        self.edit_product(copy / "main.multistart.product", lambda docs: docs[0]["configuration"].update(sha256="0" * 64))
        self.assertIn("the products were made with the configuration and budgets beside the recipe", self.failed_checks(copy))

    def test_a_choice_against_the_frozen_rule_fails(self):
        copy = self.copy_of_recording("choice")
        self.edit_product(copy / "main.topology.product", lambda docs: docs[1]["topology"].update(choice="H2"))
        self.assertIn("the topology choice is the frozen rule: H2 if and only if 2 (lnL_2 - lnL_1) >= 30", self.failed_checks(copy))

    def test_a_topology_product_that_changes_h1_fails(self):
        copy = self.copy_of_recording("h1-changed")
        # the prefit's iteration count in the /4 only: the reader accepts it (a count), so only the comparison with the /3 can tell
        self.edit_product(copy / "main.topology.product", lambda docs: docs[2]["prefit"].update(iterations=docs[2]["prefit"]["iterations"] + 1))
        self.assertEqual(self.failed_checks(copy), ["the topology product carries its multistart product unchanged",
                                                    RERUN])

    def test_another_label_fails(self):
        copy = self.copy_of_recording("label")
        self.edit_product(copy / "two-source.multistart.product", lambda docs: docs[0].update(label="validated"))
        self.assertIn("the products read back whole as the recipe's /3 and /4, label shared-model closure, ln L and the "
                      "per-channel check recomputed", self.failed_checks(copy))

    def test_a_product_the_recipe_would_not_write_fails_by_the_rerun(self):
        copy = self.copy_of_recording("not-the-recipe-s")

        def plant(docs):                        # the prefit's iteration count, which the reader checks as a count only
            docs[1]["prefit"]["iterations"] += 1
        self.edit_product(copy / "main.multistart.product", plant)
        self.edit_product(copy / "main.topology.product", plant)
        new_h1 = sha256(copy / "main.multistart.product")
        self.edit_product(copy / "main.topology.product", lambda docs: docs[0]["h1_product"].update(sha256=new_h1))
        failed = self.failed_checks(copy)
        self.assertEqual(failed, [RERUN])

    def test_the_rerun_is_not_run_when_another_check_failed(self):
        copy = self.copy_of_recording("rerun-skipped")
        self.edit_product(copy / "main.multistart.product", lambda docs: docs[0]["configuration"].update(sha256="0" * 64))
        code, summary = self.replay_of(copy)
        self.assertEqual(code, 1)
        rerun = summary["checks"][-1]
        self.assertEqual((rerun["passed"], rerun["run"]), (False, False))

    def test_a_hit_charge_the_likelihood_does_not_reproduce_fails(self):
        copy = self.copy_of_recording("hit-charge")

        def plant(docs):                        # stays above the threshold: only the recomputed ln L can tell
            docs[1]["hits"][0][1] += 0.01
        self.edit_product(copy / "main.multistart.product", plant)
        self.edit_product(copy / "main.topology.product", plant)
        new_h1 = sha256(copy / "main.multistart.product")
        self.edit_product(copy / "main.topology.product", lambda docs: docs[0]["h1_product"].update(sha256=new_h1))
        self.assertIn("the products read back whole as the recipe's /3 and /4, label shared-model closure, ln L and the "
                      "per-channel check recomputed", self.failed_checks(copy))

    def test_a_multistart_product_in_place_of_the_topology_product_fails(self):
        copy = self.copy_of_recording("format")
        shutil.copyfile(copy / "two-source.multistart.product", copy / "two-source.topology.product")
        self.assertIn("the products read back whole as the recipe's /3 and /4, label shared-model closure, ln L and the "
                      "per-channel check recomputed", self.failed_checks(copy))

    def test_a_recorded_probability_failure_fails(self):
        copy = self.copy_of_recording("probability-failure")
        runs = json.loads((copy / "runs.json").read_text(encoding="utf-8"))
        next(r for r in runs["runs"] if r["operation"] == "check-product" and r["sample"] == "two-source")["probability_failures"] = 1
        (copy / "runs.json").write_text(json.dumps(runs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(self.failed_checks(copy), ["no live channel's hit and no-hit probabilities miss one, at H1's or H2's point (the T09 stop)",
                                                    RERUN])

    def test_a_missing_operation_fails(self):
        copy = self.copy_of_recording("missing-operation")
        runs = json.loads((copy / "runs.json").read_text(encoding="utf-8"))
        runs["runs"] = [r for r in runs["runs"] if (r["sample"], r["operation"]) != ("two-source", "check-product")]
        (copy / "runs.json").write_text(json.dumps(runs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertIn("every operation is ok with exit 0", self.failed_checks(copy))

    def test_the_recording_names_its_platform(self):
        runs = json.loads((self.recorded / "runs.json").read_text(encoding="utf-8"))
        self.assertEqual(runs["platform"], self.example.current_platform())
        self.assertEqual(set(runs["platform"]), {"cpu", "machine", "python", "numpy", "scipy"})

    def mode_of(self, recorded: Path) -> str:
        """check 9's mode, as the replay's JSON on stdout names it"""
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(io.StringIO()):
            self.example.main(["--out", str(recorded.parent / (recorded.name + "-mode")), "--recorded", str(recorded)])
        return json.loads(stream.getvalue())["check_9"]

    def test_on_the_recording_s_platform_check_9_is_byte_equality(self):
        self.assertEqual(self.mode_of(self.recorded), "byte for byte")

    def test_on_another_platform_check_9_compares_within_the_tolerances(self):
        copy = self.copy_of_recording("other-platform")
        runs = json.loads((copy / "runs.json").read_text(encoding="utf-8"))
        runs["platform"]["cpu"] = "another CPU"
        (copy / "runs.json").write_text(json.dumps(runs, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        self.assertEqual(self.mode_of(copy), "within the tolerances")
        code, summary = self.replay_of(copy)
        self.assertEqual(code, 0)
        self.assertEqual([c["check"] for c in summary["checks"] if not c["passed"]], [])
        honest_out = self.recorded.parent / (self.recorded.name + "-out")
        if not (honest_out / "summary.json").is_file():
            self.replay_of(self.recorded)
        # the output does not depend on the mode of check 9 (but for the edited runs.json's own hash)
        mine_out = copy.parent / (copy.name + "-out")
        self.assertEqual((mine_out / "report.md").read_bytes(), (honest_out / "report.md").read_bytes())
        mine, honest = (json.loads((folder / "summary.json").read_text(encoding="utf-8")) for folder in (mine_out, honest_out))
        for doc in (mine, honest):
            doc["recorded_sha256"].pop("runs.json")
        self.assertEqual(mine, honest)

    def test_a_harness_refusal_in_the_live_mode_is_rejected(self):
        class Refused(HandMadeGenerator):
            def event(self, fixture, block, stratum, event_index):
                ev = super().event(fixture, block, stratum, event_index)
                ev["data"]["extra"] = ev["data"]["state"]      # a field the harness does not hand out: FixtureError
                return ev
        folder = Path(self.folder.name) / "refused"
        self.assertEqual(quiet(self.example.live, Refused(), None, folder / "work", folder / "recorded"), 2)
        self.assertFalse((folder / "recorded").exists())

    def test_a_missing_recording_is_refused(self):
        empty = Path(self.folder.name) / "empty"
        empty.mkdir()
        code, summary = self.replay_of(empty)
        self.assertEqual((code, summary), (2, None))

    def test_a_live_run_without_the_frozen_generator_is_refused(self):
        folder = Path(self.folder.name)
        self.assertEqual(quiet(self.example.main, ["--live", "--generator", "", "--recorded", str(folder / "r1"), "--out", str(folder / "o1")]), 2)
        stand_in = folder / "gen_t09_sphere.py"
        stand_in.write_text("GENERATOR = 't09-sphere/1'\n", encoding="utf-8")
        self.assertEqual(quiet(self.example.main, ["--live", "--generator", str(stand_in), "--recorded", str(folder / "r2"),
                                                   "--out", str(folder / "o2")]), 2)
        self.assertFalse((folder / "r2").exists())


class ToleranceComparison(unittest.TestCase):
    """Check 9 off the recording's platform: run.compare_products against planted differences, each just inside or outside its
    stated tolerance (run.TOLERANCES), on the hand-made recording's products."""

    @classmethod
    def setUpClass(cls):
        cls.example = load()
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        recorded = Path(cls.folder.name) / "recorded"
        assert quiet(cls.example.live, HandMadeGenerator(), None, Path(cls.folder.name) / "work", recorded) == 0
        cls.text = {kind: (recorded / f"{stem}.{kind}.product").read_text(encoding="utf-8")
                    for stem, kind in (("main", "multistart"), ("two-source", "topology"))}

    def planted(self, kind, edit) -> str:
        docs = [json.loads(line) for line in self.text[kind].splitlines()]
        edit(docs)
        return "".join(json.dumps(doc, sort_keys=True, allow_nan=False) + "\n" for doc in docs)

    def differences(self, kind, edit) -> list:
        return self.example.compare_products(self.text[kind], self.planted(kind, edit))

    def test_the_tolerances_are_the_stated_ones(self):
        # fixed before any run with their reasons (run.py docstring, D3 stage 5 fix round 1); never moved after a result
        self.assertEqual(self.example.TOLERANCES, {"ln_likelihood": 1e-6, "statistic": 4e-6, "parameter_sigmas": 1e-3})

    def test_the_same_products_have_no_difference(self):
        for kind, text in self.text.items():
            with self.subTest(kind=kind):
                self.assertEqual(self.example.compare_products(text, text), [])

    def test_ln_l_inside_and_outside_its_tolerance(self):
        tol = self.example.TOLERANCES["ln_likelihood"]
        self.assertEqual(self.differences("multistart", lambda d: d[1]["fit"].update(ln_likelihood=d[1]["fit"]["ln_likelihood"] + 0.5 * tol)), [])
        self.assertTrue(self.differences("multistart", lambda d: d[1]["fit"].update(ln_likelihood=d[1]["fit"]["ln_likelihood"] + 2 * tol)))
        self.assertTrue(self.differences("topology", lambda d: d[1]["topology"].update(ln_likelihood_2=d[1]["topology"]["ln_likelihood_2"] + 2 * tol)))
        self.assertTrue(self.differences("topology", lambda d: d[1]["topology"]["h2"]["fit"].update(
            ln_likelihood=d[1]["topology"]["h2"]["fit"]["ln_likelihood"] + 2 * tol)))

    def test_the_statistic_inside_and_outside_its_tolerance(self):
        tol = self.example.TOLERANCES["statistic"]
        self.assertEqual(self.differences("topology", lambda d: d[1]["topology"].update(statistic=d[1]["topology"]["statistic"] + 0.5 * tol)), [])
        self.assertTrue(self.differences("topology", lambda d: d[1]["topology"].update(statistic=d[1]["topology"]["statistic"] + 2 * tol)))

    def test_a_parameter_inside_and_outside_its_tolerance_in_its_own_sigma(self):
        k = self.example.TOLERANCES["parameter_sigmas"]

        def shift(by):
            def edit(docs):
                fit = docs[1]["fit"]
                fit["vertex"][0] += by * k * fit["covariance"][0][0] ** 0.5
            return edit
        self.assertEqual(self.differences("multistart", shift(0.5)), [])
        self.assertTrue(self.differences("multistart", shift(2.0)))

        def turn(by):                                   # the direction turned along e1 by `by` tolerances of u1
            def edit(docs):
                fit = docs[1]["fit"]
                step = by * k * fit["covariance"][3][3] ** 0.5
                d = [a + step * b for a, b in zip(fit["direction"], fit["frame"]["e1"])]
                norm = sum(c * c for c in d) ** 0.5
                fit["direction"] = [c / norm for c in d]
            return edit
        self.assertEqual(self.differences("multistart", turn(0.5)), [])
        self.assertTrue(self.differences("multistart", turn(2.0)))

        def shift_h2(by):                               # H2's second source, its t0 (coordinate 13)
            def edit(docs):
                h2 = docs[1]["topology"]["h2"]["fit"]
                h2["sources"][1]["t0"] += by * k * h2["covariance"][13][13] ** 0.5
            return edit
        self.assertEqual(self.differences("topology", shift_h2(0.5)), [])
        self.assertTrue(self.differences("topology", shift_h2(2.0)))

    def test_a_discrete_difference_is_never_within_a_tolerance(self):
        self.assertTrue(self.differences("topology", lambda d: d[1]["topology"].update(choice="H1")))
        self.assertTrue(self.differences("multistart", lambda d: d[1]["fit"].update(status="failed")))
        self.assertTrue(self.differences("multistart", lambda d: d[1]["choice"].update(chosen=d[1]["choice"]["chosen"] + 1)))
        self.assertTrue(self.differences("multistart", lambda d: d.pop(1)))
        self.assertTrue(self.differences("topology", lambda d: d[1]["topology"].update(ln_likelihood_2_from="h1 boundary")))


@unittest.skipUnless(GENERATOR and Path(GENERATOR).is_file(), "HEP_T09_GENERATOR names no frozen t09-sphere/1 generator: the live part runs in the T09 job")
class LiveRun(unittest.TestCase):
    def test_the_live_run_writes_the_recording_again(self):
        run = load()
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            code = quiet(run.main, ["--live", "--generator", GENERATOR, "--work", str(folder / "work"), "--recorded", str(folder / "recorded"),
                                    "--out", str(folder / "output")])
            self.assertEqual(code, 0)
            recorded = json.loads((RECORDED / "runs.json").read_text(encoding="utf-8"))
            if recorded.get("platform") == run.current_platform():   # check 9's rule: bytes on the recording's platform
                for file_name in run.RECORDED_FILES:
                    with self.subTest(file=file_name):
                        self.assertEqual((folder / "recorded" / file_name).read_bytes(), (RECORDED / file_name).read_bytes())
                for path in EXPECTED_OUTPUT.iterdir():
                    with self.subTest(file=path.name):
                        self.assertEqual((folder / "output" / path.name).read_bytes(), path.read_bytes())
            else:                                                     # elsewhere the stated tolerances
                for stem, *_ in run.SAMPLES:
                    for kind in ("multistart", "topology"):
                        with self.subTest(product=f"{stem}.{kind}"):
                            mine = (folder / "recorded" / f"{stem}.{kind}.product").read_text(encoding="utf-8")
                            kept = (RECORDED / f"{stem}.{kind}.product").read_text(encoding="utf-8")
                            self.assertEqual(run.compare_products(kept, mine), [])


if __name__ == "__main__":
    unittest.main()
