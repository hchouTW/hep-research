"""adapters/acts-tracking: R33's outputs for the tracks the finder and the truth-seeded run deliver (plan R33; D1 stage 8 review m1; D1 stage 9 brief, item 3).

Where they live: in each program's product, acts-tracking-product/2 when asked for by --r33-outputs t07-r33/1 (native/r33_product_outputs.hpp). The product is what
already carries a delivered track's states (the first K events, product-events); the record carries candidate summaries of every event and is not touched. The R33
records are the refit's (track_fit_outputs.hpp, t07-r33/1), formed by fitting each delivered hit set again through KalmanRefit::fit with outputs from the q/p the
delivered fit itself assumed; the program stops unless that fit's /1 records equal the delivered ones byte for byte. Without the flag both programs write /1 as before.

Asserted, built (the byte-equality regime of the finder, finding-equal, and of the truth-seeded run, truth-seeded-equal, is kept by not using the flag there):
- the record with the flag equals the record without it, byte for byte;
- the /2 product's /1 records (native_product.version_one_of) give the /1 product without the flag, byte for byte;
- every R33 record is there (the reader refuses otherwise: native_product.r33_defects), and the residual records equal this module's recomputation from the product's own
  states (native_product.residual_record_defects, the tolerances of test_acts_track_outputs.py);
- one track output and one full residual covariance per delivered track, one measurement output and four residuals per state with a hit.
Reported: smoothed and unbiased pull widths of the delivered tracks (noise hits can be taken, so no width is asserted). Clean fixture stratum 0 (o1, 1.5 to 3 GeV) and noise
fixture stratum 1 (o2), block 1, R33_EVENTS events, the first R33_PRODUCT_EVENTS in the product. Development readings otherwise, no gate (K09).

Every built test needs the build job and skips without it; that job counts a skip as a failure. Run from the plugin root: python -m unittest tests.adapters.test_acts_finding_r33 -v
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy

from tests.adapters import test_acts_finding as finding_tests
from tests.adapters import test_acts_track_outputs as outputs_tests
from tests.adapters import test_acts_truth_seeded as truth_seeded_tests

native_product, truth_files = finding_tests.native_product, finding_tests.truth_files
NATIVE = finding_tests.NATIVE
BUILT = truth_seeded_tests.RUNNABLE
NOT_BUILT = "HEP_ACTS_TRACKING_BUILD names no built finder and truth-seeded run: this test needs the T07 build job, which runs it"

R33_FLAG = ["--r33-outputs", "t07-r33/1"]
R33_EVENTS = 600
R33_PRODUCT_EVENTS = 60
R33_STRATA = (("clean", 0), ("noise", 1))


class R33OutputsOfTheFinderInTheSource(unittest.TestCase):
    """The flag is an output of both programs, with the same helper, and the helper refuses outputs of another fit."""

    def test_both_programs_take_the_flag_and_call_the_helper(self):
        finder = (NATIVE / "acts_tracking_finder.cpp").read_text(encoding="utf-8")
        seeded = (NATIVE / "acts_truth_seeded_run.cpp").read_text(encoding="utf-8")
        outputs_source = (NATIVE / "r33_product_outputs.hpp").read_text(encoding="utf-8")
        self.assertIn('optional_outputs{"seed-file", "ambiguity-trace-file", "ambiguity-trace-events", "r33-outputs"}', finder)
        self.assertIn('optional{"trace-file", "trace-starts", "reading-start-angle-sigma", "r33-outputs"}', seeded)
        for source in (finder, seeded):
            self.assertIn('#include "r33_product_outputs.hpp"', source)
            self.assertIn("t07::add_r33_outputs_of(*outputs_fitter, finding, event, document);", source)
            self.assertIn("t07::name_r33_conventions(document);", source)
        self.assertIn("version_one_records_of(document.header, again) != version_one_records_of(document.header, delivered)", outputs_source)
        self.assertIn("hit_set.assumed_q_over_p = delivered.track.assumed_q_over_p;", outputs_source)
        for word in finding_tests.TRUTH_SEEDED_ONLY:
            self.assertNotIn(word, finder)

    def test_a_version_two_product_gives_back_its_version_one_bytes(self):
        document = outputs_tests.sample_r33_document()
        version_one = native_product.version_one_of(document)
        self.assertNotIn("format", version_one)
        text = native_product.format_product(version_one)
        self.assertTrue(text.startswith("acts-tracking-product/1\n"))
        self.assertNotIn("r33_conventions", text)
        self.assertEqual(native_product.format_product(native_product.parse_product(text)), text)
        with self.assertRaises(native_product.ProductFormatError):
            native_product.version_one_of(version_one)


def width_text(document: dict) -> str:
    arrays = outputs_tests.unbiased_arrays(document)
    widths = []
    for state_type in ("smoothed", "unbiased"):
        rows = numpy.concatenate([rows for (kind, _), rows in arrays.items() if kind == state_type])
        for view in (0, 1):
            widths.append(f"{state_type} {('loc0', 'loc1')[view]} {float(numpy.sqrt(numpy.mean(rows[:, view] ** 2 / rows[:, 2 + view]))):.4f}")
    return ", ".join(widths)


def r33_counts_defects(document: dict) -> list:
    with_hits = [state for state in document["states"] if state["kind"] in ("measurement", "outlier")]
    fitted = [track for track in document["tracks"] if track["status"] == "fitted"]
    defects = []
    if len(document["measurement_outputs"]) != len(with_hits) or len(document["residuals"]) != 4 * len(with_hits):
        defects.append("not one measurement output and four residuals per state with a hit")
    if len(document["track_outputs"]) != len(fitted) or len(document["residual_covariances"]) != len(fitted):
        defects.append("not one track output and one residual covariance per fitted track")
    if not fitted:
        defects.append("no delivered track to read")
    return defects + native_product.r33_defects(document) + native_product.residual_record_defects(document, outputs_tests.RECOMPUTE_RELATIVE, outputs_tests.RECOMPUTE_ABSOLUTE_MM)[:5]


class R33CompletenessRule(unittest.TestCase):
    """Fix round 1, m3: the completeness rule the built test applies, on a consistent sample and with one record taken away."""

    def test_the_rule_passes_a_complete_product_and_names_a_missing_record(self):
        document = outputs_tests.sample_r33_document()
        self.assertEqual(r33_counts_defects(document), [])
        for collection in ("residuals", "track_outputs", "measurement_outputs", "residual_covariances"):
            with self.subTest(removed=collection):
                lacking = dict(document, **{collection: document[collection][1:]})
                self.assertTrue(r33_counts_defects(lacking))
        no_track = dict(document, tracks=[track for track in document["tracks"] if track["status"] != "fitted"])
        self.assertIn("no delivered track to read", r33_counts_defects(dict(no_track, states=[], parameters=[], track_outputs=[], residuals=[], measurement_outputs=[],
                                                                            residual_covariances=[])))


@unittest.skipUnless(BUILT, NOT_BUILT)
class R33OutputsOfFoundTracks(unittest.TestCase):
    """The finder and the truth-seeded run, with and without --r33-outputs, on the same data file."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        folder = Path(cls.folder.name)
        cls.results = {}
        for fixture, stratum in R33_STRATA:
            started = time.monotonic()
            data_file, truth_file = finding_tests.generate(folder, fixture, stratum, R33_EVENTS)
            start_file = folder / f"{fixture}-{stratum}.t07starts"
            start_file.write_text(truth_seeded_tests.start_file_text(list(truth_files.iter_truth_events(truth_file)), truth_seeded_tests.file_sha256(data_file)), encoding="utf-8")
            runs = {}
            for program, name in ((finding_tests.FINDER, "finder"), (truth_seeded_tests.TRUTH_SEEDED_RUN, "truth-seeded")):
                for flagged in (False, True):
                    stem = f"{name}-{fixture}-{stratum}-{'r33' if flagged else 'plain'}"
                    record, product = folder / f"{stem}.record", folder / f"{stem}.product"
                    inputs = ["--start-file", start_file] if name == "truth-seeded" else []
                    finished = finding_tests.run_program([program, "--data-file", data_file] + inputs + ["--product-id", f"{name}-{fixture}-{stratum}", "--product-file", product,
                                                          "--record-file", record, "--product-events", R33_PRODUCT_EVENTS] + (R33_FLAG if flagged else []))
                    runs[(name, flagged)] = {"record": record.read_bytes(), "product": product.read_text(encoding="utf-8"), "stderr": finished.stderr}
                    record.unlink()
                    product.unlink()
            cls.results[(fixture, stratum)] = runs
            for path in (data_file, truth_file, start_file):
                path.unlink()
            print(f"R33-FOUND-COST {fixture} stratum {stratum} events {R33_EVENTS} seconds {time.monotonic() - started:.1f}", flush=True)

    def test_the_records_and_the_version_one_records_are_unchanged(self):
        for (fixture, stratum), runs in self.results.items():
            for name in ("finder", "truth-seeded"):
                plain, flagged = runs[(name, False)], runs[(name, True)]
                document = native_product.parse_product(flagged["product"])
                again = native_product.format_product(native_product.version_one_of(document))
                print(f"R33-FOUND {name} {fixture} stratum {stratum} record equal {plain['record'] == flagged['record']}, /1 records equal {again == plain['product']}, "
                      f"tracks {len(document['tracks'])}, stderr bytes {len(plain['stderr'])} and {len(flagged['stderr'])}", flush=True)
                with self.subTest(program=name, fixture=fixture):
                    self.assertTrue(plain["product"].startswith("acts-tracking-product/1\n"))
                    self.assertTrue(flagged["product"].startswith("acts-tracking-product/2\n"))
                    self.assertEqual(plain["record"], flagged["record"])
                    self.assertEqual(again, plain["product"])
                    self.assertEqual(document["header"]["stage"], native_product.parse_product(plain["product"])["header"]["stage"])

    def test_every_r33_field_is_there_and_recomputes(self):
        for (fixture, stratum), runs in self.results.items():
            for name in ("finder", "truth-seeded"):
                document = native_product.parse_product(runs[(name, True)]["product"])
                outputs = native_product.r33_outputs(document)
                missing = [key for key, item in outputs["measurements"].items() if set(native_product.R33_MEASUREMENT_FIELDS) - set(item)]
                missing += [key for key, item in outputs["tracks"].items() if set(native_product.R33_TRACK_FIELDS) - set(item) or item["residual_covariance"] is None]
                print(f"R33-FOUND-FIELDS {name} {fixture} stratum {stratum} measurements {len(outputs['measurements'])} tracks {len(outputs['tracks'])} pull widths "
                      f"{width_text(document)} (a reading)", flush=True)
                with self.subTest(program=name, fixture=fixture):
                    self.assertEqual(r33_counts_defects(document), [])
                    self.assertEqual(missing, [])


# ---- D1 stage 10, built: the wrapper's find with and without --r33-outputs against the finder called directly.
WRAPPER = finding_tests.ADAPTER / "assets" / "acts_tracking.py"
WRAPPER_EVENTS = 200
WRAPPER_PRODUCT_EVENTS = 60
WRAPPER_STRATUM = ("noise", 1)


@unittest.skipUnless(finding_tests.BUILT, finding_tests.NOT_BUILT)
class WrapperFindRun(unittest.TestCase):
    """The wrapper forwards --r33-outputs and changes nothing: its product and record bytes are the finder's, and a wrong value is the finder's own refusal."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.work = Path(cls.folder.name)
        cls.data_file, truth_file = finding_tests.generate(cls.work, *WRAPPER_STRATUM, WRAPPER_EVENTS)
        truth_file.unlink()

    def arguments(self, stem: str, extra: list) -> list:
        return ["--data-file", self.data_file, "--product-id", "wrapper-check", "--product-file", self.work / f"{stem}.product", "--record-file", self.work / f"{stem}.record",
                "--product-events", WRAPPER_PRODUCT_EVENTS] + extra

    def wrapper(self, stem: str, extra: list) -> tuple:
        finished = subprocess.run([sys.executable, str(WRAPPER), "find", *[str(item) for item in self.arguments(stem, extra)], "--build-dir", finding_tests.BUILD_DIR],
                                  capture_output=True, text=True, timeout=3600)
        return finished.returncode, json.loads(finished.stdout)

    def test_the_product_and_the_record_are_the_finders_bytes(self):
        for label, extra, version in (("without", [], "acts-tracking-product/1\n"), ("with", R33_FLAG, "acts-tracking-product/2\n")):
            finished = finding_tests.run_program([finding_tests.FINDER, *self.arguments("direct", extra)])
            exit_code, report = self.wrapper("wrapper", extra)
            outputs = {kind: ((self.work / f"direct.{kind}").read_bytes(), (self.work / f"wrapper.{kind}").read_bytes()) for kind in ("product", "record")}
            first_line = outputs["product"][1].split(b"\n", 1)[0].decode()
            print(f"WRAPPER-FIND {WRAPPER_STRATUM[0]} stratum {WRAPPER_STRATUM[1]} events {WRAPPER_EVENTS} {label} --r33-outputs: wrapper exit {exit_code} status {report['status']}, "
                  f"product bytes equal {outputs['product'][0] == outputs['product'][1]} ({len(outputs['product'][1])} bytes, {first_line}), "
                  f"record bytes equal {outputs['record'][0] == outputs['record'][1]}", flush=True)
            with self.subTest(r33_outputs=label):
                self.assertEqual((exit_code, report["status"], report["program_exit"]), (0, "ok", 0), report.get("reason"))
                self.assertEqual(report["command"], [str(item) for item in [finding_tests.FINDER, *self.arguments("wrapper", extra)]])
                self.assertEqual(report["program_stdout"], finished.stdout)
                self.assertTrue(outputs["product"][1].startswith(version.encode()))
                self.assertEqual(outputs["product"][0], outputs["product"][1])
                self.assertEqual(outputs["record"][0], outputs["record"][1])
            for kind in ("product", "record"):
                for side in ("direct", "wrapper"):
                    (self.work / f"{side}.{kind}").unlink()

    def test_another_conventions_name_is_the_finders_refusal(self):
        extra = ["--r33-outputs", "t07-r33/2"]
        finished = finding_tests.run_program([finding_tests.FINDER, *self.arguments("wrong-direct", extra)], check=False)
        exit_code, report = self.wrapper("wrong-wrapper", extra)
        print(f"WRAPPER-FIND refused t07-r33/2: finder exit {finished.returncode}, wrapper exit {exit_code} status {report['status']}, stderr equal "
              f"{report.get('program_stderr') == finished.stderr}, reason {report['reason'][:120]}", flush=True)
        self.assertEqual(finished.returncode, 2, finished.stderr)
        self.assertEqual((exit_code, report["status"], report["program_exit"]), (2, "rejected", 2))
        self.assertEqual(report["program_stderr"], finished.stderr)
        self.assertEqual(report["reason"], finished.stderr.strip())
        self.assertIn("--r33-outputs", report["reason"])


if __name__ == "__main__":
    unittest.main()
