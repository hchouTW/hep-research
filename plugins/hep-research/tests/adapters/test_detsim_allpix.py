"""Allpix Squared backend of detsim (work item W4A; TASK.md 8.2, 12.2, 16.1 T-AP / T-OUTPUT / T-ENV; card AP-BOOT).

Offline tests use SYNTHETIC inputs only: a configuration shaped like the official example (never the upstream files),
a pinned-hash descriptor patched to those synthetic files, synthetic per-event data in place of a ROOT file, and a
fake `allpix` program (this interpreter writing a placeholder output) launched by the real shared layer. They cover
the descriptor and parameters, check 1 (pinned hashes, overrides), the expected tree set from include / exclude,
checks 3 and 3b with the card's counterexamples (no hit in a detector, charge sign read wrongly, exit 0 with content
missing, an excluded tree present), check 2's comparison, observables rows, probe's missing-dependency answers and
the version refusal. No test needs ROOT; tests that hide it check the missing-dependency path.

Live tests (the real Allpix Squared view, ROOT bindings in this interpreter) run only when HEP_DETSIM_ALLPIX_VIEW
names the environment root (card AP-BOOT: a view folder with allpix/, geant4/, root/, deps/, data/) and
HEP_DETSIM_ALLPIX_EXAMPLES names the folder holding example.conf, example_detector.conf and
example_electric_field.init of the pinned commit; otherwise they are skipped ("not run: no Allpix view").
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT / "adapters" / "detector-simulation" / "assets"
for _entry in (str(ROOT), str(ASSETS), str(HERE)):
    if _entry not in sys.path:
        sys.path.insert(0, _entry)
sys.dont_write_bytecode = True

import detsim  # noqa: E402
import detsim_backend_allpix as allpix  # noqa: E402
import detsim_plan  # noqa: E402
import detsim_profile  # noqa: E402
import detsim_run  # noqa: E402
import detsim_schemas  # noqa: E402
from detsim_plan import DetsimError  # noqa: E402

MACOS = detsim_profile.profile("macos-g0")
REAL_DESCRIPTOR = allpix._descriptor
CONFIG = """[Allpix]
log_level = "INFO"
detectors_file = "example_detector.conf"
number_of_events = 10000

[GeometryBuilderGeant4]

[DepositionGeant4]
physics_list = FTFP_BERT_LIV
particle_type = "Pi+"

[ElectricFieldReader]
model = "mesh"
file_name = "example_electric_field.init"

[GenericPropagation]
temperature = 293K

[PulseTransfer]

[DefaultDigitizer]
threshold = 600e

[DetectorHistogrammer]
name = "detector1"

[DetectorHistogrammer]
name = "detector2"

# replace by [VisualizationGeant4] to run the visualization
[Ignore]
mode = "gui"

[ROOTObjectWriter]
exclude = DepositedCharge, PropagatedCharge
"""
DETECTORS = '[detector1]\ntype = "cmsp1"\nposition = 0 0 0\n\n[detector2]\ntype = "cmsp1"\nposition = 10um 80um 4mm\n'
FIELD = "SYNTHETIC field placeholder (not the official mesh)\n"
NAMES = {"config": "example.conf", "detector": "example_detector.conf", "field": "example_electric_field.init"}
TEXTS = {"config": CONFIG, "detector": DETECTORS, "field": FIELD}
VERSION = "v3.2.0-689-gdf69a6a4"
FAKE_PROGRAM = '''
import os, sys
from pathlib import Path
mode_file = Path(os.environ["G4LEDATA"]).parent.parent / "mode"
mode = mode_file.read_text().strip() if mode_file.is_file() else "ok"
if mode == "exit3":
    sys.exit(3)
if mode != "nooutput":
    Path("output").mkdir(exist_ok=True)
    Path("output/data.root").write_bytes(b"SYNTHETIC placeholder, read through a mocked extractor")
print("fake allpix", " ".join(sys.argv[1:]))
'''


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def synthetic_descriptor() -> dict:
    """The real descriptor with the pinned input hashes replaced by those of the synthetic files above."""
    doc = REAL_DESCRIPTOR()
    for role, name in NAMES.items():
        doc["pinned"]["inputs"][role] = {"name": name, "sha256": sha(TEXTS[role])}
    return doc


def raw_events(n=10, d1=(-20000,), d2=(-15000, -5000), hits=True) -> dict:
    """SYNTHETIC per-event data in the shape read_data_file returns."""
    events = []
    for i in range(n):
        charges = {"detector1": [[26, 40 + k, c - i] for k, c in enumerate(d1)],
                   "detector2": [[26, 39 + k, c] for k, c in enumerate(d2)]}
        hit = {d: [[x, y, repr(abs(c) * 0.99)] for x, y, c in v] for d, v in charges.items()} if hits else {}
        events.append({"entry": i, "id": i + 1, "seed": str(10**18 + i), "pixel_charge": charges, "pixel_hit": hit})
    classes = {"allpix::PixelCharge": {"class_version": 9, "members": ["allpix::Object", "pixel_", "charge_"]},
               "allpix::PixelHit": {"class_version": 7, "members": ["allpix::Object", "pixel_", "signal_"]},
               "allpix::Pixel": {"class_version": 2, "members": ["index_", "type_"]}}
    trees = {"Event": n, "MCParticle": n, "MCTrack": n, "PixelCharge": n, "PixelHit": n}
    return {"trees": trees, "branches": {t: ["detector1", "detector2"] for t in trees}, "classes": classes,
            "configuration": {"number_of_events": "10", "multithreading": "false", "random_seed": "1",
                              "random_seed_core": "2", "version": '"' + VERSION + '"'},
            "events": events, "root_version": "synthetic"}


def manifest(paths=None, hashes=None) -> list:
    paths = paths or {"config": "inputs/example.conf", "detector": "inputs/example_detector.conf",
                      "field": "inputs/example_electric_field.init"}
    hashes = hashes or {r: sha(TEXTS[r]) for r in NAMES}
    return [{"role": r, "path": paths[r], "size": 1, "sha256": hashes[r]} for r in NAMES]


def identity(version=VERSION, datasets=("G4LEDATA", "G4NEUTRONHPDATA")) -> dict:
    return {"backend": "allpix-squared", "kind": "source-build view", "platform": "test",
            "allpix": {"version_string": version, "commit_abbrev": version.rsplit("-g", 1)[-1], "sha256": {},
                       "models_sha256": {}},
            "geant4": {"version": "11.4.3", "cxx_standard": "20",
                       "datasets": [{"name": n, "version": "1", "envvar": n, "content_sha256": "0" * 64,
                                     "n_files": 1} for n in datasets]},
            "root": {"version": "6.40.04"}}


def variables(datasets=("G4LEDATA", "G4NEUTRONHPDATA")) -> dict:
    out = {"PATH": "ENV_ROOT/allpix/bin", allpix.library_variable(): "ENV_ROOT/allpix/lib"}
    out.update({n: f"ENV_ROOT/data/{n.lower()}" for n in datasets})
    return out


def task(env_identity: str, seed=1, **parameters) -> dict:
    params = {"random_seed": seed, "number_of_events": 10, "multithreading": False}
    params.update(parameters)
    return {"schema": "detector-task/1", "capability_id": "allpix.pixel-charge",
            "objective": "SYNTHETIC test of the Allpix backend", "environment_ref": env_identity,
            "inputs": [{"role": r, "path": "inputs/" + NAMES[r]} for r in NAMES], "parameters": params,
            "budget": {"timeout_s": 60, "max_output_bytes": 1048576}}


class Descriptor(unittest.TestCase):
    def test_descriptor_is_valid_and_in_hash_scope(self):
        capability = detsim_plan.capability_of(allpix, "allpix.pixel-charge")
        self.assertEqual((capability["version"], capability["backend"]), ("1.0.0", "allpix-squared"))
        self.assertEqual(capability["pinned"]["version_string"], VERSION)
        self.assertEqual(capability["required_guarantees"], {"inputs_unmodified": "hard", "timeout_kill": "hard",
                                                             "output_size_abort": "soft"})
        self.assertEqual(capability["checks"]["band_e"], {"low": "10687.5", "high": "42750"})
        keys = [k for k, _p in allpix.code_files(capability)]
        self.assertEqual(keys, ["detsim_backend_allpix.py", "allpix/allpix.pixel-charge.json"])

    def test_parameters_fixed_values(self):
        good = task("0" * 64)
        detsim_plan.checked_task(good, allpix)
        for change in ({"multithreading": True}, {"number_of_events": 11}, {"multithreading": 0},
                       {"random_seed": -1}, {"random_seed": "1"}, {"extra": 1}):
            bad = copy.deepcopy(good)
            bad["parameters"].update(change)
            with self.subTest(change=change), self.assertRaises(DetsimError) as ctx:
                detsim_plan.checked_task(bad, allpix)
            self.assertEqual(ctx.exception.error_code, "parameters-invalid")
        missing = copy.deepcopy(good)
        del missing["parameters"]["multithreading"]  # multithreading = false is written explicitly (card)
        with self.assertRaises(DetsimError):
            detsim_plan.checked_task(missing, allpix)


class CheckAndSpec(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(allpix, "_descriptor", synthetic_descriptor)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.capability = allpix.capabilities()["allpix.pixel-charge"]

    def test_pinned_inputs_pass(self):
        self.assertEqual(allpix.check(task("0" * 64), self.capability, manifest()), [])

    def test_replaced_input_is_refused(self):  # counterexample: replaced input (check 1 at plan time)
        hashes = {r: sha(TEXTS[r]) for r in NAMES}
        hashes["config"] = sha(CONFIG + "number_of_events = 5\n")
        issues = allpix.check(task("0" * 64), self.capability, manifest(hashes=hashes))
        self.assertEqual([(i["code"], i["kind"]) for i in issues], [("input-not-pinned", "refused")])

    def test_layout_and_roles(self):
        paths = {"config": "inputs/example.conf", "detector": "other/example_detector.conf",
                 "field": "inputs/example_electric_field.init"}
        issues = allpix.check(task("0" * 64), self.capability, manifest(paths=paths))
        self.assertEqual([i["code"] for i in issues], ["input-layout"])
        two = manifest()[:2]
        self.assertEqual({i["code"] for i in allpix.check(task("0" * 64), self.capability, two)}, {"input-role"})
        extra = manifest() + [{"role": "macro", "path": "inputs/x", "size": 1, "sha256": "0" * 64}]
        self.assertEqual([i["code"] for i in allpix.check(task("0" * 64), self.capability, extra)], ["input-role"])

    def test_build_spec(self):
        env = {"env_identity": "0" * 64, "identity": identity(), "variables": dict(variables(), EXTRA="x")}
        spec = allpix.build_spec(task("0" * 64, seed=42), self.capability, manifest(), env, MACOS)
        self.assertEqual(spec["argv"], ["ENV_ROOT/allpix/bin/allpix", "-c", "INPUT_ROOT/inputs/example.conf",
                                        "-o", "number_of_events=10", "-o", "multithreading=false",
                                        "-o", "random_seed=42"])
        self.assertEqual(sorted(spec["environment"]), sorted(variables()))  # never an extra variable
        self.assertEqual(spec["expected_outputs"], ["ATTEMPT_ROOT/output/data.root"])
        self.assertEqual(spec["files"], [])
        self.assertEqual([k for k, _v in allpix.overrides_of(spec["argv"])],
                         ["number_of_events", "multithreading", "random_seed"])
        self.assertTrue(set(k for k, _v in allpix.overrides_of(spec["argv"])) <= set(allpix.ALLOWED_OVERRIDES))

    def test_wrong_version_is_refused(self):  # counterexample: wrong version
        env = {"env_identity": "0" * 64, "identity": identity(version="v3.3.0"), "variables": variables()}
        with self.assertRaises(DetsimError) as ctx:
            allpix.build_spec(task("0" * 64), self.capability, manifest(), env, MACOS)
        self.assertEqual((ctx.exception.status, ctx.exception.error_code),
                         ("refused", "environment-version-mismatch"))

    def test_missing_dataset_variable_is_refused(self):  # counterexample: missing Geant4 dataset in the record
        env = {"env_identity": "0" * 64, "identity": identity(), "variables": variables(datasets=("G4LEDATA",))}
        with self.assertRaises(DetsimError) as ctx:
            allpix.build_spec(task("0" * 64), self.capability, manifest(), env, MACOS)
        self.assertEqual(ctx.exception.error_code, "environment-variables-missing")


class ArgvWhitelist(unittest.TestCase):  # review m2
    GOOD = ["ENV_ROOT/allpix/bin/allpix", "-c", "INPUT_ROOT/inputs/example.conf", "-o", "number_of_events=10", "-o",
            "multithreading=false", "-o", "random_seed=7"]

    def test_good(self):
        self.assertEqual(allpix.argv_problems(self.GOOD), [])

    def test_anything_else_fails(self):
        cases = {"-j": self.GOOD + ["-j", "4"], "-g": self.GOOD + ["-g", "detector1.type=x"], "-v": self.GOOD + ["-v",
                 "DEBUG"], "second -c": self.GOOD + ["-c", "INPUT_ROOT/other.conf"],
                 "output_directory": self.GOOD + ["-o", "output_directory=raw"],
                 "other value": [a.replace("number_of_events=10", "number_of_events=11") for a in self.GOOD],
                 "multithreading": [a.replace("multithreading=false", "multithreading=true") for a in self.GOOD],
                 "seed twice": self.GOOD + ["-o", "random_seed=8"], "no seed": self.GOOD[:-2],
                 "executable": ["ENV_ROOT/allpix/bin/other"] + self.GOOD[1:], "dangling": self.GOOD + ["-o"],
                 "seed text": [a.replace("random_seed=7", "random_seed=07") for a in self.GOOD]}
        for name, argv in cases.items():
            with self.subTest(case=name):
                self.assertTrue(allpix.argv_problems(argv), argv)


class Libraries(unittest.TestCase):  # review M1: module libraries and resolved Geant4 / ROOT libraries
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="detsim libs é "))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.real = self.root / "real"
        for rel in ("allpix/bin/allpix", "allpix/lib/libAllpixCore.dylib", "allpix/lib/libAllpixModuleA.dylib",
                    "geant4/lib/libG4run.dylib", "root/lib/root/libCore.so"):
            (self.real / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.real / rel).write_text(rel, encoding="utf-8")
        self.view = self.root / "view"
        self.view.mkdir()
        for name in ("allpix", "geant4", "root"):
            (self.view / name).symlink_to(self.real / name)
        g4, rootlib = self.real / "geant4" / "lib", self.real / "root" / "lib" / "root"
        self.commands = {"allpix": ([str(g4), "@loader_path/../lib"], [("@rpath/libAllpixCore.dylib", False),
                                                                       ("@rpath/libG4run.dylib", False),
                                                                       ("/usr/lib/libSystem.B.dylib", False)]),
                         "libAllpixCore.dylib": ([str(rootlib)], [("@rpath/libCore.so", False)]),
                         "libAllpixModuleA.dylib": ([], [("@rpath/libG4run.dylib", False),
                                                         ("@rpath/libMissing.dylib", True)]),
                         "libG4run.dylib": ([], []), "libCore.so": ([], [])}

    def identity(self):
        binaries = [self.view / "allpix" / "bin" / "allpix"] + sorted((self.view / "allpix" / "lib").glob("*.dylib"))
        with mock.patch.object(allpix, "_load_commands", lambda path: self.commands[Path(path).name]), \
                mock.patch.object(allpix.platform_calls, "platform_key", return_value="darwin"):
            linked = allpix.linked_libraries(self.view, binaries)
        return linked, allpix.library_identity(self.view, linked)

    def test_resolution_and_identity(self):
        linked, ident = self.identity()
        self.assertEqual(linked["unresolved"], [])  # the weak libMissing is not required
        self.assertEqual(sorted(ident), ["allpix", "geant4", "root"])
        self.assertEqual(sorted(ident["allpix"]), ["allpix", "libAllpixCore.dylib", "libAllpixModuleA.dylib"])
        self.assertEqual(list(ident["geant4"]), ["libG4run.dylib"])
        self.assertEqual(list(ident["root"]), ["libCore.so"])  # through libAllpixCore's own LC_RPATH
        self.assertNotIn(str(self.root), json.dumps(ident))      # content only, never a path
        before = ident
        (self.real / "allpix" / "lib" / "libAllpixModuleA.dylib").write_text("changed module", encoding="utf-8")
        self.assertNotEqual(self.identity()[1], before)  # a changed module library changes the identity
        (self.real / "allpix" / "lib" / "libAllpixModuleA.dylib").write_text("allpix/lib/libAllpixModuleA.dylib",
                                                                               encoding="utf-8")
        (self.real / "root" / "lib" / "root" / "libCore.so").write_text("other ROOT", encoding="utf-8")
        self.assertNotEqual(self.identity()[1]["root"], before["root"])  # and so does a resolved ROOT library

    def test_unresolved_required_library(self):
        self.commands["libAllpixModuleA.dylib"] = ([], [("@rpath/libGone.dylib", False)])
        linked, _ident = self.identity()
        self.assertEqual(linked["unresolved"], ["@rpath/libGone.dylib (needed by libAllpixModuleA.dylib)"])


class ExpectedTrees(unittest.TestCase):
    def test_module_chain_minus_exclude(self):
        trees, problems = allpix.expected_trees(allpix.parse_config(CONFIG), allpix._descriptor())
        self.assertEqual((trees, problems), (["MCParticle", "MCTrack", "PixelCharge", "PixelHit"], []))

    def test_include_and_unknown_module(self):
        text = CONFIG.replace("exclude = DepositedCharge, PropagatedCharge", 'include = "PixelHit"')
        self.assertEqual(allpix.expected_trees(allpix.parse_config(text), allpix._descriptor())[0], ["PixelHit"])
        text = CONFIG + "\n[CSADigitizer]\n"
        self.assertEqual(len(allpix.expected_trees(allpix.parse_config(text), allpix._descriptor())[1]), 1)

    def test_detectors_and_overrides(self):
        self.assertEqual(allpix.detectors_of(DETECTORS), ["detector1", "detector2"])
        self.assertEqual(allpix.overrides_of(["x", "-o", "a=1", "-o", "b="]), [("a", "1"), ("b", "")])


class Evaluate(unittest.TestCase):
    def result(self, raw, check):
        evidence = allpix.evaluate(raw, CONFIG, ["detector1", "detector2"], allpix._descriptor(), 10)
        return next(e for e in evidence if e["check"] == check)

    def test_good_data_passes_every_check(self):
        evidence = allpix.evaluate(raw_events(), CONFIG, ["detector1", "detector2"], allpix._descriptor(), 10)
        self.assertEqual({e["check"]: e["result"] for e in evidence},
                         {"run-settings": "pass", "event-count": "pass", "expected-trees": "pass", "members": "pass",
                          "hits-per-detector": "pass", "charge-sign": "pass", "plausibility-band": "pass"})
        band = self.result(raw_events(), "plausibility-band")
        self.assertIn("plausibility, not physics validation", band["detail"])
        self.assertIn("2.00045e4 e", band["detail"])  # median of |-20000 - i|, i = 0..9 (exact half-integer)

    def test_no_hit_in_a_detector_fails(self):  # counterexample
        raw = raw_events()
        raw["events"][4]["pixel_hit"]["detector2"] = []
        self.assertEqual(self.result(raw, "hits-per-detector")["result"], "fail")
        self.assertIn("event 5 detector2", self.result(raw, "hits-per-detector")["detail"])

    def test_signed_sum_fails_the_band(self):  # counterexample: charge sign read wrongly
        signed = [sum(c for _x, _y, c in e["pixel_charge"]["detector1"]) for e in raw_events()["events"]]
        self.assertEqual(allpix.plausibility(signed, allpix._descriptor())["result"], "fail")
        absolute = allpix.charge_sums(raw_events()["events"], "detector1")
        self.assertEqual(allpix.plausibility(absolute, allpix._descriptor())["result"], "pass")

    def test_band_edges(self):
        d = allpix._descriptor()
        for values, expected in (([10687.5 * 2 - 10688, 10688], "pass"), ([10687, 10687], "fail"),
                                 ([42750], "pass"), ([42751], "fail"), ([], "fail")):
            with self.subTest(values=values):
                ints = [int(v) for v in values]
                self.assertEqual(allpix.plausibility(ints, d)["result"], expected)
        self.assertEqual(allpix.median([1, 4]), allpix.Fraction(5, 2))

    def test_trees(self):
        raw = raw_events()
        del raw["trees"]["PixelHit"]
        self.assertEqual(self.result(raw, "expected-trees")["result"], "fail")
        raw = raw_events()
        raw["trees"]["DepositedCharge"] = 10  # excluded by configuration but present
        self.assertEqual(self.result(raw, "expected-trees")["result"], "fail")
        raw = raw_events()
        del raw["trees"]["MCTrack"]  # an expected type with no tree: no objects (upstream rule), not a zero fill
        found = self.result(raw, "expected-trees")
        self.assertEqual(found["result"], "pass")
        self.assertIn("no tree for ['MCTrack']", found["detail"])
        raw = raw_events(n=9)
        self.assertEqual(self.result(raw, "event-count")["result"], "fail")

    def test_members(self):
        raw = raw_events()
        raw["classes"]["allpix::PixelCharge"]["members"].remove("charge_")
        self.assertEqual(self.result(raw, "members")["result"], "fail")

    def test_class_versions_are_pinned(self):  # review m3
        self.assertEqual(allpix._descriptor()["class_versions"],
                         {"allpix::PixelCharge": 9, "allpix::PixelHit": 7, "allpix::Pixel": 2})
        raw = raw_events()
        raw["classes"]["allpix::PixelHit"]["class_version"] = 8
        found = self.result(raw, "members")
        self.assertEqual(found["result"], "fail")
        self.assertIn("allpix::PixelHit class version 8 (pinned 7)", found["detail"])

    def test_flipped_sign_fails(self):  # review m1: a file whose charges are positive (sign flipped)
        raw = raw_events(d1=(20000,), d2=(15000, 5000))
        for event in raw["events"]:
            for pixels in event["pixel_charge"].values():
                for pixel in pixels:
                    pixel[2] = abs(pixel[2])
        found = self.result(raw, "charge-sign")
        self.assertEqual(found["result"], "fail")
        self.assertIn("non-negative charge_", found["detail"])
        self.assertEqual(self.result(raw, "plausibility-band")["result"], "pass")  # the band alone cannot see it
        one = raw_events()
        one["events"][6]["pixel_charge"]["detector2"][0][2] = 0
        self.assertEqual(self.result(one, "charge-sign")["result"], "fail")


class Reproducibility(unittest.TestCase):
    def summary(self, raw):
        return allpix.summary_document(raw, "0" * 64, ["detector1", "detector2"], ["PixelCharge"])

    def test_compare(self):
        a, b = self.summary(raw_events()), self.summary(raw_events())
        b["run_configuration"] = {"random_seed": "99"}  # stored configuration is never compared
        b["source_sha256"] = "1" * 64                  # nor the file hash
        found = allpix.compare_summaries(a, b)
        self.assertEqual((found["identical"], found["pixels_compared"]), (True, 60))
        changed = copy.deepcopy(raw_events())
        changed["events"][3]["pixel_charge"]["detector2"][1][2] -= 1
        self.assertFalse(allpix.compare_summaries(a, self.summary(changed))["identical"])
        seeded = copy.deepcopy(raw_events())
        seeded["events"][0]["seed"] = "7"
        self.assertIn("id/seed", allpix.compare_summaries(a, self.summary(seeded))["differences"][0])

    def test_compare_refuses_and_reports_pixels(self):  # review m4
        a = self.summary(raw_events())
        found = allpix.compare_summaries(a, copy.deepcopy(a))
        self.assertEqual(len(found["per_pixel"]), 60)
        first = found["per_pixel"][0]
        self.assertEqual((first["event"], first["detector"], first["kind"], first["index"], first["a"], first["b"],
                          first["same"]), (1, "detector1", "pixel_charge", [26, 40], -20000, -20000, True))
        empty = copy.deepcopy(a)
        empty["events"] = []
        self.assertEqual(allpix.compare_summaries(empty, copy.deepcopy(empty))["identical"], False)
        other = copy.deepcopy(a)
        other["format"] = "something-else/1"
        self.assertIn("is not allpix-pixel-summary/1", allpix.compare_summaries(a, other)["differences"][0])
        fewer = copy.deepcopy(a)
        fewer["detectors"] = ["detector1"]
        self.assertFalse(allpix.compare_summaries(a, fewer)["identical"])
        with tempfile.TemporaryDirectory(prefix="detsim compare é ") as scratch:
            paths = [Path(scratch) / "a.json", Path(scratch) / "b.json"]
            for path in paths:
                path.write_text(json.dumps(a), encoding="utf-8")
            self.assertTrue(allpix.compare_summary_files(*paths)["identical"])

    def test_summary_is_deterministic(self):
        one = json.dumps(self.summary(raw_events()), sort_keys=True)
        self.assertEqual(one, json.dumps(self.summary(raw_events()), sort_keys=True))


class Probe(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="detsim allpix é "))
        self.addCleanup(shutil.rmtree, self.root, True)

    def test_root_missing_is_missing_dependency(self):
        with mock.patch.object(allpix, "import_root", side_effect=allpix.RootUnavailable("hidden")):
            with self.assertRaises(DetsimError) as ctx:
                allpix.probe(self.root)
        self.assertEqual((ctx.exception.status, ctx.exception.details["missing"]), ("missing-dependency", ["ROOT"]))

    def test_programs_libraries_and_datasets(self):
        fake_root = mock.Mock()
        fake_root.gROOT.GetVersion.return_value = "6.40.04"
        with mock.patch.object(allpix, "import_root", return_value=fake_root):
            with self.assertRaises(DetsimError) as ctx:
                allpix.probe(self.root)
            self.assertEqual(ctx.exception.status, "missing-dependency")
            self.assertIn("allpix/bin/allpix", ctx.exception.details["missing"])
            suffix = allpix.library_suffix()
            for rel in ("allpix/bin/allpix", f"allpix/lib/libAllpixCore{suffix}",
                        f"allpix/lib/libAllpixObjects{suffix}", "allpix/share/Allpix/models/cmsp1.conf",
                        "root/bin/root-config"):
                (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
                (self.root / rel).write_text("x", encoding="utf-8")
            (self.root / "deps" / "lib").mkdir(parents=True)
            config = self.root / "geant4" / "bin" / "geant4-config"
            config.parent.mkdir(parents=True)
            config.write_text("#!/bin/sh\necho 'G4EMLOW G4LEDATA /somewhere/G4EMLOW8.8'\n"
                              "echo 'G4NDL G4NEUTRONHPDATA /elsewhere/G4NDL4.7.1'\n", encoding="utf-8")
            config.chmod(0o755)
            (self.root / "data" / "G4EMLOW8.8").mkdir(parents=True)
            (self.root / "data" / "G4EMLOW8.8" / "f").write_text("x", encoding="utf-8")
            with self.assertRaises(DetsimError) as ctx:  # G4NDL folder missing: counterexample
                allpix.probe(self.root)
            self.assertEqual(ctx.exception.status, "missing-dependency")
            self.assertEqual(ctx.exception.details["missing"], ["G4NEUTRONHPDATA (data/G4NDL4.7.1)"])
            (self.root / "data" / "G4NDL4.7.1").mkdir()
            with self.assertRaises(DetsimError) as ctx:  # an empty dataset folder is missing too
                allpix.probe(self.root)
            self.assertEqual(ctx.exception.details["missing"], ["G4NEUTRONHPDATA (data/G4NDL4.7.1)"])
            (self.root / "data" / "G4NDL4.7.1" / "f").write_text("x", encoding="utf-8")
            program = self.root / "allpix" / "bin" / "allpix"
            program.write_text("#!/bin/sh\necho 'Allpix Squared version v3.3.0'\n", encoding="utf-8")
            program.chmod(0o755)
            with self.assertRaises(DetsimError) as ctx:  # wrong version: refused before any record
                allpix.probe(self.root)
            self.assertEqual((ctx.exception.status, ctx.exception.error_code), ("refused", "backend-version-mismatch"))


class _FakeEnvironment(unittest.TestCase):
    """A project with synthetic inputs and an environment root whose allpix is this interpreter (no simulator)."""

    def setUp(self):
        if detsim_profile.host_profile_id() != "macos-g0":
            self.skipTest("not run (platform): runs need a measured runner profile; only macos-g0 is measured")
        patcher = mock.patch.object(allpix, "_descriptor", synthetic_descriptor)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.work = Path(tempfile.mkdtemp(prefix="detsim allpix é "))
        self.addCleanup(shutil.rmtree, self.work, True)
        self.env_root = self.work / "env root"
        program = self.env_root / "allpix" / "bin" / "allpix"
        program.parent.mkdir(parents=True)
        program.write_text(f"#!{sys.executable}\n" + FAKE_PROGRAM, encoding="utf-8")
        program.chmod(0o755)
        for name in ("g4ledata", "g4neutronhpdata"):
            (self.env_root / "data" / name).mkdir(parents=True)
        self.project = self.work / "project é"
        (self.project / "inputs").mkdir(parents=True)
        for role, name in NAMES.items():
            (self.project / "inputs" / name).write_text(TEXTS[role], encoding="utf-8")
        record = detsim_plan.env_record(identity(), variables(), facts={"backend": "test"},
                                        path_record={"env_root": str(self.env_root)})
        path = detsim_plan.env_record_path(detsim_plan.artifacts_root(self.project), record["env_identity"])
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(record), encoding="utf-8")
        self.env_identity = record["env_identity"]
        (self.project / "task.json").write_text(json.dumps(task(self.env_identity)), encoding="utf-8")

    def mode(self, text):
        (self.env_root / "mode").write_text(text, encoding="utf-8")

    def call(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = detsim.main(["--backend", "allpix-squared", *argv], backends={"allpix-squared": allpix})
        return code, json.loads(out.getvalue())

    def run_task(self, replicate="0"):
        code, answer = self.call("prepare", "--workspace", str(self.project), "--task", "task.json")
        self.assertEqual(code, 0, answer)
        plan = self.work / "plan.json"
        plan.write_text(json.dumps(answer), encoding="utf-8")
        return self.call("run", "--workspace", str(self.project), "--plan", str(plan), "--replicate", replicate)


class Runs(_FakeEnvironment):
    def test_complete_run_with_synthetic_data(self):
        with mock.patch.object(allpix, "read_data_file", return_value=raw_events()):
            code, answer = self.run_task()
        self.assertEqual((code, answer["status"]), (0, "ok"), answer)
        folder = detsim_run.store_root(self.project) / answer["folder"]
        completeness = json.loads((folder / "completeness.json").read_text(encoding="utf-8"))
        self.assertEqual(completeness["state"], "complete")
        self.assertEqual(detsim_schemas.check_completeness(completeness), [])
        summary = json.loads((folder / "extract" / "pixel_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["expected_trees"], ["MCParticle", "MCTrack", "PixelCharge", "PixelHit"])
        record = json.loads((folder / "run.computational-run.json").read_text(encoding="utf-8"))
        self.assertIn(f"detector-simulation/{answer['folder']}/extract/pixel_summary.json",
                      record["extension"]["sidecars"])
        self.assertEqual(record["extension"]["seeds"], {"random_seed": 1})
        log = (folder / "logs" / "stdout.txt").read_text(encoding="utf-8")
        self.assertIn("-o number_of_events=10 -o multithreading=false -o random_seed=1", log)
        observables = allpix.observables(folder, json.loads((folder / "plan.canonical.json").read_text(
            encoding="utf-8"))["execution"])
        self.assertEqual(detsim_schemas.check_observables(observables), [])
        kinds = {r["quantity"] for r in observables["rows"]}
        self.assertEqual(kinds, {"event_seed", "pixel_charge_abs_sum", "pixel_charge_count", "pixel_hit_count",
                                 "pixel_charge", "pixel_hit_signal"})
        sums = [r for r in observables["rows"] if r["quantity"] == "pixel_charge_abs_sum"
                and r["detector"] == "detector1"]
        self.assertEqual((sums[0]["value"], sums[0]["unit"], sums[0]["point"]), ("2e4", "e", 1))

    def test_exit_0_without_output_fails(self):  # counterexample: exit 0 with required content missing
        self.mode("nooutput")
        code, answer = self.run_task()
        self.assertEqual((code, answer["status"], answer["completeness"]), (1, "failed", "partial"), answer)
        self.assertEqual(answer["native_exit_code"], 0)

    def test_no_hit_fails_the_run(self):  # counterexample through the shared layer
        raw = raw_events()
        raw["events"][2]["pixel_hit"]["detector1"] = []
        with mock.patch.object(allpix, "read_data_file", return_value=raw):
            code, answer = self.run_task()
        self.assertEqual((code, answer["status"], answer["completeness"]), (1, "failed", "invalid"), answer)
        folder = detsim_run.store_root(self.project) / answer["folder"]
        record = json.loads((folder / "run.computational-run.json").read_text(encoding="utf-8"))
        self.assertIn("failed", record["status"])

    def test_missing_tree_is_partial(self):
        raw = raw_events()
        del raw["trees"]["PixelCharge"]
        with mock.patch.object(allpix, "read_data_file", return_value=raw):
            code, answer = self.run_task()
        self.assertEqual((answer["status"], answer["completeness"]), ("failed", "partial"), answer)

    def test_root_missing_at_collect_fails_with_evidence(self):
        with mock.patch.object(allpix, "import_root", side_effect=allpix.RootUnavailable("hidden")):
            code, answer = self.run_task()
        self.assertEqual((code, answer["status"], answer["completeness"], answer["error_code"]),
                         (1, "failed", "invalid", "missing-dependency"), answer)
        folder = detsim_run.store_root(self.project) / answer["folder"]
        completeness = json.loads((folder / "completeness.json").read_text(encoding="utf-8"))
        found = next(e for e in completeness["evidence"] if e["check"] == "dependency")
        self.assertEqual(found["result"], "fail")
        record = json.loads((folder / "run.computational-run.json").read_text(encoding="utf-8"))
        self.assertEqual(record["extension"]["detsim"]["error_code"], "missing-dependency")
        self.assertIn("missing-dependency", found["detail"])

    def test_backend_failure(self):
        self.mode("exit3")
        code, answer = self.run_task()
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "failed", "backend-failed"), answer)

    def test_replaced_input_after_prepare_is_refused(self):  # counterexample: replaced input -> plan-stale
        code, answer = self.call("prepare", "--workspace", str(self.project), "--task", "task.json")
        plan = self.work / "plan.json"
        plan.write_text(json.dumps(answer), encoding="utf-8")
        (self.project / "inputs" / "example_detector.conf").chmod(0o644)
        (self.project / "inputs" / "example_detector.conf").write_text(DETECTORS + "\n", encoding="utf-8")
        code, answer = self.call("run", "--workspace", str(self.project), "--plan", str(plan))
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "refused", "plan-stale"), answer)

    def test_changed_environment_identity_is_stale(self):  # counterexample: wrong version -> plan-stale
        code, answer = self.call("prepare", "--workspace", str(self.project), "--task", "task.json")
        path = self.work / "plan.json"
        path.write_text(json.dumps(answer), encoding="utf-8")
        record_path = detsim_plan.env_record_path(detsim_plan.artifacts_root(self.project), self.env_identity)
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["identity"]["allpix"]["version_string"] = "v3.3.0"  # the environment changed under the same name
        record_path.write_text(json.dumps(record), encoding="utf-8")
        code, answer = self.call("run", "--workspace", str(self.project), "--plan", str(path))
        self.assertEqual((code, answer["status"], answer["error_code"]), (1, "refused", "plan-stale"), answer)
        self.assertEqual(answer["mismatched_fields"], ["/environment"])
        tampered = json.loads(path.read_text(encoding="utf-8"))["plan"]  # a plan edited by hand: rejected
        tampered["environment"]["identity"]["allpix"]["version_string"] = "v3.3.0"
        path.write_text(json.dumps(tampered), encoding="utf-8")
        code, answer = self.call("run", "--workspace", str(self.project), "--plan", str(path))
        self.assertEqual((code, answer["status"], answer["error_code"]), (2, "rejected", "plan-invalid"), answer)

    def test_program_version_spot_check(self):  # counterexample: a different program behind the same record
        raw = raw_events()
        raw["configuration"]["version"] = "v3.3.0"
        with mock.patch.object(allpix, "read_data_file", return_value=raw):
            code, answer = self.run_task()
        self.assertEqual((code, answer["status"], answer["completeness"]), (1, "failed", "invalid"), answer)

    def test_fidelity_fails_on_a_changed_snapshot(self):
        spec = {"argv": ["ENV_ROOT/allpix/bin/allpix", "-c", "INPUT_ROOT/inputs/example.conf", "-o",
                         "number_of_events=10", "-o", "multithreading=false", "-o", "random_seed=1", "-o",
                         "log_level=DEBUG"], "expected_outputs": ["ATTEMPT_ROOT/output/data.root"]}
        attempt = self.work / "attempt"
        (attempt / "input" / "inputs").mkdir(parents=True)
        for role, name in NAMES.items():
            (attempt / "input" / "inputs" / name).write_text(TEXTS[role], encoding="utf-8")
        evidence, _found = allpix.config_fidelity(attempt, spec, allpix._descriptor())
        self.assertEqual(evidence["result"], "fail")
        self.assertIn("override 'log_level=DEBUG' is not allowed", evidence["detail"])
        spec["argv"] = spec["argv"][:-2]
        self.assertEqual(allpix.config_fidelity(attempt, spec, allpix._descriptor())[0]["result"], "pass")
        (attempt / "input" / "inputs" / "example.conf").write_text(CONFIG.replace("600e", "500e"), encoding="utf-8")
        self.assertIn("config input example.conf is not the pinned file",
                      allpix.config_fidelity(attempt, spec, allpix._descriptor())[0]["detail"])


@unittest.skipUnless(os.environ.get("HEP_DETSIM_ALLPIX_VIEW") and os.environ.get("HEP_DETSIM_ALLPIX_EXAMPLES"),
                     "not run: no Allpix view (set HEP_DETSIM_ALLPIX_VIEW and HEP_DETSIM_ALLPIX_EXAMPLES)")
class Live(unittest.TestCase):
    """The real Allpix Squared view (card AP-BOOT); needs the ROOT Python bindings in this interpreter."""

    def setUp(self):
        try:
            allpix.import_root()
        except allpix.RootUnavailable:
            self.skipTest("not run: no ROOT Python bindings in this interpreter")
        self.view = Path(os.environ["HEP_DETSIM_ALLPIX_VIEW"])
        self.work = Path(tempfile.mkdtemp(prefix="detsim allpix live é "))
        self.addCleanup(shutil.rmtree, self.work, True)
        self.project = self.work / "project"
        (self.project / "inputs").mkdir(parents=True)
        for name in NAMES.values():
            shutil.copyfile(Path(os.environ["HEP_DETSIM_ALLPIX_EXAMPLES"]) / name, self.project / "inputs" / name)

    def call(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = detsim.main(["--backend", "allpix-squared", *argv])
        return code, json.loads(out.getvalue())

    def write_task(self, env_identity, seed):
        doc = dict(task(env_identity, seed=seed), budget={"timeout_s": 120, "max_output_bytes": 67108864})
        (self.project / f"task-{seed}.json").write_text(json.dumps(doc), encoding="utf-8")
        code, prepared = self.call("prepare", "--workspace", str(self.project), "--task", f"task-{seed}.json")
        self.assertEqual(code, 0, prepared)
        plan = self.work / f"plan-{seed}.json"
        plan.write_text(json.dumps(prepared), encoding="utf-8")
        return plan

    def run_plan(self, plan, replicate):
        code, answer = self.call("run", "--workspace", str(self.project), "--plan", str(plan), "--replicate",
                                 replicate)
        self.assertEqual((code, answer["status"]), (0, "ok"), answer)
        return detsim_run.store_root(self.project) / answer["folder"]

    def test_probe_through_a_symlink_and_reproducibility(self):
        code, direct = self.call("check", "--workspace", str(self.project), "--probe", "--env-root", str(self.view))
        self.assertEqual(code, 0, direct)
        link = self.work / "view link"
        link.symlink_to(self.view)
        code, linked = self.call("check", "--workspace", str(self.project), "--probe", "--env-root", str(link))
        self.assertEqual((code, linked["env_identity"]), (0, direct["env_identity"]))
        self.assertIn("libraries_sha256", direct["identity"])
        plan = self.write_task(direct["env_identity"], 3)
        folders = [self.run_plan(plan, r) for r in ("0", "1")]
        summaries = [json.loads((f / "extract" / "pixel_summary.json").read_text(encoding="utf-8")) for f in folders]
        found = allpix.compare_summaries(*summaries)
        self.assertTrue(found["identical"], found["differences"])
        self.assertTrue(found["per_pixel"] and all(r["same"] for r in found["per_pixel"]))
        other = self.run_plan(self.write_task(direct["env_identity"], 4), "0")  # another seed differs somewhere
        other_summary = json.loads((other / "extract" / "pixel_summary.json").read_text(encoding="utf-8"))
        self.assertFalse(allpix.compare_summaries(summaries[0], other_summary)["identical"])
        for folder in folders + [other]:
            evidence = {e["check"]: e for e in json.loads((folder / "completeness.json").read_text(
                encoding="utf-8"))["evidence"]}
            for check in ("config-fidelity", "run-settings", "members", "hits-per-detector", "charge-sign",
                          "plausibility-band"):
                self.assertEqual(evidence[check]["result"], "pass", (check, evidence[check]))
        sums = allpix.charge_sums([{"pixel_charge": {d: v["pixel_charge"] for d, v in e["detectors"].items()}}
                                   for e in summaries[0]["events"]], "detector1")
        self.assertTrue(10687.5 <= float(allpix.median(sums)) <= 42750, sums)
        self.assertTrue(all(e["detectors"][d]["pixel_hit"] for e in summaries[0]["events"]
                            for d in ("detector1", "detector2")))
        self.compare_with_library_accessors(folders[0], summaries[0])

    def compare_with_library_accessors(self, folder, summary):
        """The emulated read equals the values of the Allpix object library's accessors (getCharge, getSignal,
        getPixel().getIndex(), getAbsoluteCharge), read in a separate interpreter that loads libAllpixObjects."""
        script = self.work / "read_typed.py"
        script.write_text(TYPED_READER, encoding="utf-8")
        library = self.view / "allpix" / "lib" / f"libAllpixObjects{allpix.library_suffix()}"
        env = {k: v for k, v in os.environ.items() if k in ("HOME", "PATH", "PYTHONPATH", "TMPDIR")}
        proc = subprocess.run([sys.executable, str(script), str(library), str(folder / "output" / "data.root"),
                               ",".join(summary["detectors"])], capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        typed = json.loads(proc.stdout)
        self.assertEqual(len(typed), len(summary["events"]))
        for event, values in zip(summary["events"], typed):
            for detector in summary["detectors"]:
                mine = event["detectors"][detector]
                self.assertEqual(mine["pixel_charge"], [v[:3] for v in values[detector]["pixel_charge"]])
                self.assertEqual([abs(c) for _x, _y, c in mine["pixel_charge"]],
                                 [v[3] for v in values[detector]["pixel_charge"]])  # getAbsoluteCharge
                self.assertEqual(mine["pixel_hit"], values[detector]["pixel_hit"])


TYPED_READER = """import json, sys
import ROOT
ROOT.gROOT.SetBatch(True)
if ROOT.gSystem.Load(sys.argv[1]) < 0:
    sys.exit("libAllpixObjects did not load")
handle = ROOT.TFile.Open(sys.argv[2])
detectors = sys.argv[3].split(",")
charges, hits = handle.Get("PixelCharge"), handle.Get("PixelHit")
found = []
for entry in range(int(charges.GetEntries())):
    charges.GetEntry(entry)
    hits.GetEntry(entry)
    found.append({d: {"pixel_charge": [[int(p.getPixel().getIndex().x()), int(p.getPixel().getIndex().y()),
                                        int(p.getCharge()), int(p.getAbsoluteCharge())] for p in getattr(charges, d)],
                      "pixel_hit": [[int(h.getPixel().getIndex().x()), int(h.getPixel().getIndex().y()),
                                     repr(float(h.getSignal()))] for h in getattr(hits, d)]} for d in detectors})
print(json.dumps(found))
"""

if __name__ == "__main__":
    unittest.main()
