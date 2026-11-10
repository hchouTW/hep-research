"""adapters/acts-tracking, stage 1 of T07 (t07-t09-task-sheets.md): telescope and straight-line case, on synthetic data.

Tests that need the built programs skip with the reason when HEP_ACTS_TRACKING_BUILD does not name them; the build job
(jobs/t07-stage1/build.sh, outside the tree) runs them. With HEP_ACTS_TRACKING_EVIDENCE set, the straight-line product is copied
there. Everything else runs anywhere, with no ACTS. Each check is driven with honest input and with one defect.

Straight-line case. The expectation is fixed here, in closed form, before the first run, and does not read ACTS. A straight track
in zero field with hits z_k, m_k is the least-squares line of plan-independent algebra: slope S_zm / S_zz, intercept
mean(m) - slope mean(z), variance of the slope sigma^2 / S_zz. The Kalman filter on a linear model gives, at plane k, that line of
the first k planes (filtered), of the first k - 1 planes extrapolated (predicted), and of all planes (smoothed). The tolerances
are bounds set from the fit's own approximations, not from a run:

- the prior: 10 mm and 0.1 rad against 0.02 mm and 6e-5 rad, a relative weight below 1e-6;
- the angle parametrization: the filter is linear in (loc, phi, theta), the line in (loc, slope). The gain changes by the slope
  error (at most 6e-4 rad, after two planes) times the largest slope 0.15, about 1e-4 of a correction of at most 0.05 mm, so
  5e-6 mm. LOC_TOLERANCE_MM is 1e-4 mm, a two-hundredth of the hit sigma, and ANGLE_TOLERANCE_RAD 1e-6 rad, a sixtieth of the
  fitted slope's sigma;
- chi2 is stored as a 32-bit float.

At zero field the hits carry no q/p: the fit must return the assumed value and the prior variance, and say so. The refit at 1 T and the
prior on q/p are tests/adapters/test_acts_refit_field.py's.
Run from the plugin root: python -m unittest tests.adapters.test_acts_tracking -v
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import io
import json
import math
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "acts-tracking"
NATIVE = ADAPTER / "assets" / "native"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ADAPTER / "assets" / "fixture_tools"))
sys.path.insert(0, str(ADAPTER / "assets"))

import acts_native_product as native_product  # noqa: E402
import acts_tracking as wrapper  # noqa: E402
import check_t07_generator as generator_check  # noqa: E402
import t07_fixture_files as fixture_files  # noqa: E402
import t07_truth_files as truth_files  # noqa: E402
from contracts import tool_contract  # noqa: E402
from contracts.reconstruction import check_products, dereference, read_sidecar  # noqa: E402

BUILD_DIR = os.environ.get("HEP_ACTS_TRACKING_BUILD", "")
DRIVER = Path(BUILD_DIR) / "acts_tracking_driver"
GENERATOR = Path(BUILD_DIR) / "t07_fixture_generator"
CAI_GENERATOR = Path(BUILD_DIR) / "t07_cai_fixture_generator"
BUILT = bool(BUILD_DIR) and DRIVER.is_file() and GENERATOR.is_file() and CAI_GENERATOR.is_file()
NOT_BUILT = "HEP_ACTS_TRACKING_BUILD names no built program: this test needs the T07 build job, which runs it"

SIGMA_MM = 0.020
PLANE_Z_MM = [50.0 * plane for plane in range(8)]
LOC_TOLERANCE_MM = 1e-4
ANGLE_TOLERANCE_RAD = 1e-6
COVARIANCE_RELATIVE_TOLERANCE = 1e-3
CHI2_RELATIVE_TOLERANCE, CHI2_ABSOLUTE_TOLERANCE = 1e-3, 1e-2
PRIOR_QOP_SIGMA_PER_GEV = 1.0  # kalman_refit.hpp says why
HELIX_TOLERANCE_MM = 1e-4  # acts_tracking_driver.cpp states the budget
MOMENTUM_ALONG_V_TOLERANCE = 1e-8
OFFSETS_U = (1.0, -0.5, -1.0, 0.5, 0.25, -1.5, 1.0, 0.25)
OFFSETS_V = (-0.75, 1.25, 0.5, -1.0, 0.75, 0.25, -1.25, 0.5)
# key, u at z = 0, u slope, v at z = 0, v slope, scale of the offsets, assumed q/p, planes with a hit
STRAIGHT_TRACKS = (("normal", 0.0, 0.0, 0.0, 0.0, 0.0, 1.0 / 3.0, range(1, 9)),
                   ("normal-offsets", 5.0, 0.0, -7.0, 0.0, 1.0, -1.0 / 3.0, range(1, 9)),
                   ("steep", -30.0, 0.15, 20.0, -0.15, 1.0, 0.1, range(1, 9)),
                   ("mixed", 12.5, -0.1, -40.0, 0.05, 2.0, -0.5, range(1, 9)),
                   ("one-view", 0.25, 0.02, 3.0, 0.12, 1.0, 1.0, range(1, 9)),
                   ("hole-at-plane-4", 2.0, 0.07, -2.0, -0.03, 1.0, 0.25, (1, 2, 3, 5, 6, 7, 8)))


def straight_hits(case) -> list:
    """(plane, loc0, loc1) of one straight track."""
    _, u_start, u_slope, v_start, v_slope, scale, _, planes = case
    return [(plane, u_start + u_slope * PLANE_Z_MM[plane - 1] + scale * SIGMA_MM * OFFSETS_U[plane - 1],
             v_start + v_slope * PLANE_Z_MM[plane - 1] + scale * SIGMA_MM * OFFSETS_V[plane - 1]) for plane in planes]


def least_squares_line(z_values, measured) -> tuple:
    """Closed form: intercept at z = 0, slope, and the chi2 of the line at SIGMA_MM."""
    count = len(z_values)
    mean_z, mean_m = sum(z_values) / count, sum(measured) / count
    s_zz = sum((z - mean_z) ** 2 for z in z_values)
    slope = sum((z - mean_z) * (m - mean_m) for z, m in zip(z_values, measured)) / s_zz
    intercept = mean_m - slope * mean_z
    chi2 = sum((m - intercept - slope * z) ** 2 for z, m in zip(z_values, measured)) / SIGMA_MM ** 2
    return intercept, slope, chi2


def line_covariance(z_values, plane_z) -> numpy.ndarray:
    """Covariance of (position at plane_z, slope) of the least-squares line."""
    count = len(z_values)
    mean_z = sum(z_values) / count
    s_zz = sum((z - mean_z) ** 2 for z in z_values)
    arm = plane_z - mean_z
    return SIGMA_MM ** 2 * numpy.array([[1.0 / count + arm ** 2 / s_zz, arm / s_zz], [arm / s_zz, 1.0 / s_zz]])


def bound_covariance(z_values, plane_z, slope_u, slope_v) -> numpy.ndarray:
    """Closed-form covariance of (loc0, loc1, phi, theta) at a plane, from the two independent views."""
    in_slopes = numpy.zeros((4, 4))  # loc0, slope u, loc1, slope v
    in_slopes[0:2, 0:2] = in_slopes[2:4, 2:4] = line_covariance(z_values, plane_z)
    norm_squared = 1.0 + slope_u ** 2 + slope_v ** 2
    root = math.sqrt(1.0 + slope_u ** 2)
    jacobian = numpy.zeros((4, 4))
    jacobian[0, 0] = jacobian[1, 2] = 1.0
    jacobian[2, 1] = 1.0 / (1.0 + slope_u ** 2)
    jacobian[3, 1] = slope_u * slope_v / (norm_squared * root)
    jacobian[3, 3] = -root / norm_squared
    return jacobian @ in_slopes @ jacobian.T


def upper_index(row: int, column: int) -> int:
    """Position of (row, column), row <= column, in the product's upper triangle of a 6 x 6 covariance."""
    return row * 6 - row * (row - 1) // 2 + column - row


def angles_of(slope_u: float, slope_v: float) -> tuple:
    return math.atan(slope_u), math.acos(slope_v / math.sqrt(1.0 + slope_u ** 2 + slope_v ** 2))


def sample_document() -> dict:
    """A small product with a failed track, as the driver writes one."""
    covariance = [0.0] * 21
    covariance[0] = 2.2250738585072014e-308
    header = {"product_id": "refit.alpha", "revision": 1, "recipe": "reco.track.acts-kf-refit/1", "stage": "refit-known-hit-set",
              "evidence_class": "truth-assisted", "data_product": "t07-measurements-0123456789abcdef", "data_sha256": "a" * 64, "hit_sets_sha256": "b" * 64,
              "field_tesla": 0.0, "qop_status": "assumed-not-measured", "material_model": "none", "start_prior": [-50.0, 10.0, 0.1, 0.1, 1.0],
              "acts_version": "48.2.0"}
    tracks = [{"key": key, "event_ordinal": ordinal, "status": status, "failure_category": category, "measurements": measured, "holes": 0, "outliers": 0,
               "chi2": 1.0 / 3.0, "measured_coordinates": 2 * measured, "assumed_q_over_p": -1e-300}
              for key, ordinal, status, category, measured in (("0", 0, "fitted", "none", 2), ("1", 1, "fitted", "none", 1), ("2", 1, "failed", "fit", 0))]
    states = [{"track_key": key, "index": index, "plane": plane, "kind": kind, "hit_key": hit_key, "loc0_mm": 0.1, "loc1_mm": -0.2, "covariance": [4e-4, 0.0, 4e-4],
               "path_length_mm": 50.0, "chi2": 0.5}
              for key, index, plane, kind, hit_key in (("0", 0, 1, "measurement", 3), ("0", 1, 2, "measurement", 7), ("0", 2, 3, "hole", None), ("1", 0, 1, "measurement", 3))]
    parameters = [{"track_key": key, "state_index": index, "state_type": state_type, "parameters": [0.1, -0.2, 1e-17, 1.5707963267948966, 0.33333333333333331, 0.0],
                   "covariance": list(covariance)}
                  for key, index in (("0", 0), ("0", 1), ("1", 0)) for state_type in native_product.STATE_TYPES]
    return {"header": header, "tracks": tracks, "states": states, "parameters": parameters}


def native_includes(source: Path) -> set:
    """Every local header a source reaches, followed through its includes."""
    reached, waiting = set(), [source]
    while waiting:
        for name in re.findall(r'^\s*#include\s+"([^"]+)"', waiting.pop().read_text(encoding="utf-8"), re.M):
            found = source.parent / name
            if name not in reached and found.is_file():
                reached.add(name)
                waiting.append(found)
    return reached


def cmake_text_of(folder: Path) -> str:
    return (folder / "CMakeLists.txt").read_text(encoding="utf-8") + (folder / "t07_generators.cmake").read_text(encoding="utf-8")


def driver_sources(cmake_text: str) -> list:
    """The sources of the data-side programs, the driver, the finder and the CAI probes, and of the common library, from the CMake file."""
    driver = re.search(r"add_executable\(acts_tracking_driver ([^)]*)\)", cmake_text).group(1).split()
    driver += re.search(r"add_executable\(acts_tracking_finder ([^)]*)\)", cmake_text).group(1).split()
    driver += re.search(r"add_executable\(seed_start_probe ([^)]*)\)", cmake_text).group(1).split()
    probe = re.findall(r"add_executable\(cai_\w+_(?:probe|check) ([^)]*)\)", cmake_text)
    probe = " ".join(probe).split()
    common = re.search(r"add_library\(acts_tracking_common STATIC ([^)]*)\)", cmake_text).group(1).split()
    return driver + probe + common


GENERATOR_ONLY_CODE = ("t07_truth_file", "t07_event_generator", "t07_seed_stream", "t07_generation_constants", "t07_cai")


def truth_code_reached(folder: Path) -> list:
    sources = driver_sources(cmake_text_of(folder))
    reached = set(sources)
    for source in sources:
        reached |= native_includes(folder / source)
    return sorted(name for name in reached if name.startswith(GENERATOR_ONLY_CODE))


class CheckLinesAgainstSection18(unittest.TestCase):
    def test_no_line_of_a_good_run_matches_row_1(self):
        """Section 18 row 1 voids a run on a `ran to its end` line, check_generators.py's failure line. This check must not print those words."""
        self.assertNotIn("ran to its end", (ADAPTER / "assets" / "fixture_tools" / "check_t07_generator.py").read_text(encoding="utf-8"))


class DataSideNeverOpensTruth(unittest.TestCase):
    """Sheet, Input: truth goes to a separate file, and the data-side driver never opens it."""

    def test_the_driver_links_no_truth_code(self):
        self.assertEqual(truth_code_reached(NATIVE), [])

    def test_a_driver_that_reached_the_truth_code_would_be_caught(self):
        with tempfile.TemporaryDirectory() as folder:
            copied = Path(folder) / "native"
            shutil.copytree(NATIVE, copied)
            source = copied / "kalman_refit.cpp"
            source.write_text('#include "t07_truth_file.hpp"\n' + source.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertIn("t07_truth_file.hpp", truth_code_reached(copied))

    def test_a_driver_that_reached_the_seed_stream_would_be_caught(self):
        with tempfile.TemporaryDirectory() as folder:
            copied = Path(folder) / "native"
            shutil.copytree(NATIVE, copied)
            source = copied / "acts_tracking_driver.cpp"
            source.write_text('#include "t07_seed_stream.hpp"\n' + source.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertIn("t07_seed_stream.hpp", truth_code_reached(copied))

    def test_a_finder_that_reached_the_truth_code_would_be_caught(self):
        with tempfile.TemporaryDirectory() as folder:
            copied = Path(folder) / "native"
            shutil.copytree(NATIVE, copied)
            source = copied / "track_finding.cpp"
            source.write_text('#include "t07_truth_file.hpp"\n' + source.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertIn("t07_truth_file.hpp", truth_code_reached(copied))

    def test_a_probe_that_reached_the_cai_constants_would_be_caught(self):
        with tempfile.TemporaryDirectory() as folder:
            copied = Path(folder) / "native"
            shutil.copytree(NATIVE, copied)
            source = copied / "payload_geometry.cpp"
            source.write_text('#include "t07_cai_constants.hpp"\n' + source.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertIn("t07_cai_constants.hpp", truth_code_reached(copied))

    def test_what_shapes_a_generator_build_is_in_the_hashed_cmake_file(self):
        """Section 2.1: t07_generators.cmake is hashed and CMakeLists.txt is not, so nothing in the second may reach a generator."""
        outer = (NATIVE / "CMakeLists.txt").read_text(encoding="utf-8")
        self.assertIn("include(t07_generators.cmake)", outer)
        for name in ("add_library", "add_compile_options", "add_definitions", "CMAKE_CXX", "CMAKE_BUILD_TYPE", "find_package", "add_executable(t07_", "target_link_libraries(t07_"):
            self.assertNotIn(name, outer)
        hashed = (NATIVE / "t07_generators.cmake").read_text(encoding="utf-8")
        for name in ("-ffp-contract=off", "CMAKE_CXX_STANDARD 23", "add_executable(t07_fixture_generator", "add_executable(t07_cai_fixture_generator"):
            self.assertIn(name, hashed)

    def test_both_probes_are_counted_as_data_side(self):
        sources = driver_sources(cmake_text_of(NATIVE))
        self.assertIn("cai_payload_probe.cpp", sources)
        self.assertIn("cai_refit_start_probe.cpp", sources)

    def test_the_cai_code_stays_out_of_the_clean_and_noise_targets(self):
        """Amendment 1: t07-telescope-cai/1 is apart, so t07_fixture_generator and the driver build from what they built from."""
        cmake_text = cmake_text_of(NATIVE)
        self.assertIn("add_executable(t07_fixture_generator t07_fixture_generator.cpp t07_event_generator.cpp t07_seed_stream.cpp t07_truth_file.cpp)", cmake_text)
        # D1 stage 9: the driver also compiles the data-side payload reader and the placement route (CAI-T07-3); still no CAI generator code (below, and truth_code_reached).
        self.assertIn("add_executable(acts_tracking_driver acts_tracking_driver.cpp kalman_refit.cpp payload_geometry.cpp alignment_payload.cpp)", cmake_text)
        self.assertIn("add_library(acts_tracking_common STATIC sha256.cpp t07_data_file.cpp native_product.cpp telescope_geometry.cpp plane_propagation.cpp)", cmake_text)
        reached = native_includes(NATIVE / "t07_fixture_generator.cpp") | native_includes(NATIVE / "t07_event_generator.cpp")
        self.assertEqual(sorted(name for name in reached if name.startswith(("t07_cai", "payload_geometry"))), [])

    def test_no_header_the_driver_reaches_holds_a_draw_rule(self):
        reached = set()
        cmake_text = cmake_text_of(NATIVE)
        for source in driver_sources(cmake_text):
            reached |= native_includes(NATIVE / source)
        text = "".join((NATIVE / name).read_text(encoding="utf-8") for name in sorted(reached))
        for name in ("near_event_modulus", "known_blocks", "momentum_bins_gev", "clean_fixture_id", "EventSeedStream", "cai_sagitta_curvature_per_mm", "cai_blocks"):
            self.assertNotIn(name, text)


def seed_attack(raw: bytes, event_limit: int = 64, fixture_ids: tuple = (7001, 7002)) -> list:
    """The attack of the D1 review: enumerate the four integers of section 3.2 and look for the event's seed, or a hash of it, in the
    file. With the seed, the stream gives every vertex and track bit for bit. Returns what it recovered."""
    wanted = {}
    for fixture_id in fixture_ids:
        for block in (1, 2, 3, 4, 5, 6, 11, 12):
            for stratum in range(12):
                for event_index in range(event_limit):
                    digest = generator_check.seed_digest(fixture_id, block, stratum, event_index)
                    wanted[digest] = wanted[hashlib.sha256(digest).digest()] = (fixture_id, block, stratum, event_index)
    return sorted({wanted[raw[start:start + 32]] for start in range(len(raw) - 31) if raw[start:start + 32] in wanted})


class DataFileHoldsNoTruth(unittest.TestCase):
    """A09; t04-prereg.md, "Truth reaches a data-side recipe"; D1 review M1."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "hits.t07data"
        self.raw = fixture_files.encode_data_file(SIGMA_MM, [[(1, 0.5, -0.5), (8, 1.5, 2.5)], [(3, 1.0, 1.0)]])
        self.path.write_bytes(self.raw)

    def test_the_format_holds_only_the_allowed_fields(self):
        self.assertEqual(fixture_files.data_file_defects(self.path), [])
        allowed = fixture_files.ALLOWED_DATA_FIELDS
        self.assertEqual(set(allowed["header"]), {"magic", "role", "event_count", "sigma_loc0_mm", "sigma_loc1_mm"})
        self.assertEqual(set(allowed["event"]), {"hit_count"})
        self.assertEqual(set(allowed["hit"]), {"hit_key", "plane", "loc0_mm", "loc1_mm"})

    def test_a_new_field_fails_until_it_is_allowed(self):
        for name, layout in {"block in the header": {"header_layout": numpy.dtype(fixture_files.DATA_HEADER.descr + [("block", "<u4")])},
                             "digest in the event": {"event_layout": numpy.dtype(fixture_files.DATA_EVENT.descr + [("event_digest", "V32")])},
                             "particle on the hit": {"hit_layout": numpy.dtype(fixture_files.HIT.descr + [("particle_key", "<u4")])}}.items():
            with self.subTest(defect=name):
                self.assertTrue(any("is not allowed" in defect for defect in fixture_files.data_file_defects(self.path, **layout)))

    def test_bytes_outside_the_allowed_fields_fail(self):
        role_end = 8 + len(fixture_files.DATA_ROLE)
        cases = {"role padding used": self.raw[:role_end + 1] + b"\x07" + self.raw[role_end + 2:], "bytes after the last event": self.raw + b"\x07" * 32,
                 "cut short": self.raw[:-1]}
        for name, raw in cases.items():
            with self.subTest(defect=name):
                self.path.write_bytes(raw)
                self.assertNotEqual(fixture_files.data_file_defects(self.path), [])

    def test_the_attack_finds_a_seed_in_a_file_that_holds_one(self):
        """The attack can succeed, so its failure on an honest file means something."""
        digest = generator_check.seed_digest(7002, 6, 1, 17)
        self.assertEqual(seed_attack(self.raw + digest), [(7002, 6, 1, 17)])
        self.assertEqual(seed_attack(self.raw + hashlib.sha256(digest).digest()), [(7002, 6, 1, 17)])

    def test_the_attack_finds_nothing_in_the_format(self):
        self.assertEqual(seed_attack(self.raw), [])


class ProductFormat(unittest.TestCase):
    """Sheet, Output and plan Section 8.3: round trip, reordering, subsetting, merging, on acts-tracking-product/1."""

    def setUp(self):
        self.document = sample_document()
        self.text = native_product.format_product(self.document)

    def test_round_trip_is_byte_exact(self):
        read_back = native_product.parse_product(self.text)
        self.assertEqual(read_back, self.document)
        self.assertEqual(native_product.format_product(read_back), self.text)

    def test_a_double_survives_exactly(self):
        read_back = native_product.parse_product(self.text)
        self.assertEqual(read_back["tracks"][0]["assumed_q_over_p"], -1e-300)
        self.assertEqual(read_back["parameters"][0]["covariance"][0], 2.2250738585072014e-308)

    def test_one_defect_is_refused(self):
        end_at = self.text.rindex("end ")
        defects = {"no end record": self.text[:end_at],
                   "unknown record": self.text[:end_at] + "seed x\n" + self.text[end_at:],
                   "wrong count": self.text[:end_at] + "end 9 9 9\n",
                   "other format": self.text.replace(native_product.PRODUCT_FORMAT, "acts-tracking-product/3", 1),
                   "not finite": self.text.replace("0.33333333333333331", "nan", 1),
                   "unknown state type": self.text.replace(" smoothed ", " unknown ", 1),
                   "failed without a category": self.text.replace(" failed fit ", " failed none ", 1),
                   "text after the end": self.text + "track x\n",
                   "q/p claimed at zero field": self.text.replace("qop_status assumed-not-measured", "qop_status measured", 1),
                   "a hole with a hit": self.text.replace(" hole none ", " hole 4 ", 1),
                   "state of an unknown track": self.text.replace("state 1 0 ", "state 9 0 ", 1),
                   "negative hit key": self.text.replace(" measurement 3 ", " measurement -3 ", 1)}
        for name, text in defects.items():
            with self.subTest(defect=name):
                self.assertNotEqual(text, self.text)
                with self.assertRaises(native_product.ProductFormatError):
                    native_product.parse_product(text)

    def test_reordering_keeps_every_object_by_key(self):
        reordered = native_product.reorder_tracks(self.document, ["2", "1", "0"])
        self.assertEqual(reordered["header"]["product_id"], "refit.alpha")
        self.assertEqual(sorted(track["key"] for track in reordered["tracks"]), ["0", "1", "2"])
        self.assertEqual(native_product.parse_product(native_product.format_product(reordered)), reordered)
        original = {(state["track_key"], state["index"]): state for state in self.document["states"]}
        for state in reordered["states"]:
            self.assertEqual(state, original[(state["track_key"], state["index"])])

    def test_reordering_refuses_a_lost_track(self):
        with self.assertRaises(native_product.ProductFormatError):
            native_product.reorder_tracks(self.document, ["1", "0"])

    def test_subset_takes_its_own_identity_and_keeps_only_its_objects(self):
        subset = native_product.subset_tracks(self.document, ["1"], "refit.alpha.part")
        self.assertEqual([track["key"] for track in subset["tracks"]], ["1"])
        self.assertEqual({state["track_key"] for state in subset["states"]}, {"1"})
        self.assertEqual(native_product.parse_product(native_product.format_product(subset)), subset)
        with self.assertRaises(native_product.ProductFormatError):
            native_product.subset_tracks(self.document, ["1"], "refit.alpha")
        with self.assertRaises(native_product.ProductFormatError):
            native_product.subset_tracks(self.document, ["9"], "refit.alpha.part")

    def test_merge_of_disjoint_products_keeps_both_hit_set_hashes(self):
        first = native_product.subset_tracks(self.document, ["0"], "refit.first")
        second = native_product.subset_tracks(self.document, ["1", "2"], "refit.second")
        second["header"]["hit_sets_sha256"] = "c" * 64
        merged = native_product.merge_products(first, second, "refit.both")
        self.assertEqual([track["key"] for track in merged["tracks"]], ["0", "1", "2"])
        self.assertEqual(merged["header"]["hit_sets_sha256"], "b" * 64 + "+" + "c" * 64)
        self.assertEqual(native_product.parse_product(native_product.format_product(merged)), merged)

    def test_merge_refuses_shared_keys_another_fit_and_a_reused_identity(self):
        first = native_product.subset_tracks(self.document, ["0"], "refit.first")
        same_key = native_product.subset_tracks(self.document, ["0", "1"], "refit.second")
        with self.assertRaises(native_product.ProductFormatError):  # W1: two products may both hold key 0
            native_product.merge_products(first, same_key, "refit.both")
        other_data = native_product.subset_tracks(self.document, ["1"], "refit.third")
        other_data["header"]["data_sha256"] = "d" * 64
        with self.assertRaises(native_product.ProductFormatError):
            native_product.merge_products(first, other_data, "refit.both")
        second = native_product.subset_tracks(self.document, ["1"], "refit.second")
        with self.assertRaises(native_product.ProductFormatError):
            native_product.merge_products(first, second, "refit.first")


class ReconstructionProductMap(unittest.TestCase):
    """The native product under reconstruction-product/1: W1, A08, A09, read by contracts.reconstruction."""

    def setUp(self):
        self.document = sample_document()
        self.tracks, self.states = native_product.sidecars_for_product(self.document, "refit-alpha.product")
        self.measurements = native_product.measurement_sidecar(self.document, "hits.t07data")

    def test_every_sidecar_reads_and_every_link_resolves(self):
        for sidecar in (self.tracks, self.states, self.measurements):
            report = read_sidecar(sidecar)
            self.assertTrue(report.ok, [finding.as_dict() for finding in report.errors])
        report = check_products([self.tracks, self.states, self.measurements])
        self.assertTrue(report.ok, [finding.as_dict() for finding in report.errors])

    def test_a_state_reaches_its_measurement_after_reordering(self):
        reordered = native_product.reorder_tracks(self.document, ["2", "1", "0"])
        _, states = native_product.sidecars_for_product(reordered, "refit-alpha.product")
        found = next(item for item in states["objects"] if item["key"] == native_product.state_key("1", 0, "smoothed"))
        target = dereference(found["source_links"][0], [self.measurements])
        self.assertEqual(target["key"], native_product.measurement_key(1, 3))

    def test_two_tracks_with_one_hit_key_in_two_events_stay_apart(self):
        keys = {item["key"] for item in self.measurements["objects"]}
        self.assertLessEqual({native_product.measurement_key(0, 3), native_product.measurement_key(1, 3)}, keys)

    def test_a_row_across_products_is_caught(self):
        changed = copy.deepcopy(self.states)
        link = next(item for item in changed["objects"] if "source_links" in item)["source_links"][0]
        link.pop("key")
        link["row"] = 0
        report = check_products([self.tracks, changed, self.measurements])
        self.assertIn("reconstruction.reference.row_across_products", [finding.code for finding in report.errors])

    def test_predicted_filtered_and_smoothed_stay_apart(self):
        at_state = [item for item in self.states["objects"] if item["key"].startswith("0/state-0/")]
        self.assertEqual(sorted(item["state_type"] for item in at_state), ["filtered", "predicted", "smoothed"])

    def test_a_failed_track_stays_an_object_with_its_class(self):
        self.assertIn(("2", "track:2:failed:fit"), [(item["key"], item["native_ref"]) for item in self.tracks["objects"]])

    def test_a_track_has_no_state_type(self):
        self.assertFalse([item for item in self.tracks["objects"] if "state_type" in item])

    def test_two_refits_of_one_data_file_read_together(self):
        other = native_product.subset_tracks(self.document, ["1"], "refit.beta")
        other_sidecars = native_product.sidecars_for_product(other, "refit-beta.product")
        everything = [self.tracks, self.states, self.measurements, *other_sidecars, native_product.measurement_sidecar(other, "hits.t07data")]
        report = check_products(everything)
        self.assertTrue(report.ok, [finding.as_dict() for finding in report.errors])

    def test_a_refit_is_never_on_the_data_side_and_never_finding(self):
        self.assertEqual({self.tracks["role"], self.states["role"]}, {"validation"})
        summary = native_product.fit_summary(self.document)
        self.assertEqual((summary["evidence_class"], summary["reported_as_finding"], summary["failed"]), ("truth-assisted", False, 1))
        self.assertEqual(summary["qop_status"], "assumed-not-measured")

    def test_another_stage_is_refused_by_the_map(self):
        self.document["header"]["stage"] = "finding"
        with self.assertRaises(native_product.ProductFormatError):
            native_product.sidecars_for_product(self.document, "refit-alpha.product")


class FixtureFileReaders(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "hits.t07data"
        self.raw = fixture_files.encode_data_file(SIGMA_MM, [[(1, 0.5, -0.5), (8, 1.5, 2.5)]])

    def read_all(self, raw: bytes) -> list:
        self.path.write_bytes(raw)
        return list(fixture_files.iter_data_events(self.path))

    def test_honest_file_reads(self):
        events = self.read_all(self.raw)
        self.assertEqual(events[0]["hits"]["plane"].tolist(), [1, 8])
        self.assertEqual(events[0]["hits"]["loc1_mm"].tolist(), [-0.5, 2.5])

    def test_one_defect_is_refused(self):
        wrong_role = self.raw.replace(fixture_files.DATA_ROLE.encode(), b"truth".ljust(len(fixture_files.DATA_ROLE), b"\0"), 1)
        for name, raw in {"truncated": self.raw[:-1], "extra bytes": self.raw + b"\0", "truth magic": truth_files.TRUTH_MAGIC + self.raw[8:], "wrong role": wrong_role}.items():
            with self.subTest(defect=name), self.assertRaises(fixture_files.FixtureFileError):
                self.read_all(raw)

    def test_layouts_match_the_native_sizes(self):
        self.assertEqual((fixture_files.DATA_HEADER.itemsize, fixture_files.DATA_EVENT.itemsize, fixture_files.HIT.itemsize), (52, 4, 24))
        self.assertEqual((truth_files.TRUTH_HEADER.itemsize, truth_files.TRUTH_EVENT.itemsize, truth_files.VERTEX.itemsize, truth_files.TRACK.itemsize),
                         (128, 96, 24, 336))


def honest_event(fixture: str = "clean", stratum: int = 0, event_index: int = 1) -> tuple:
    """One event that obeys the fixture text, built here with the closed-form helix: (truth, hits)."""
    level, momentum_bin = stratum % 3, stratum // 3
    draws = numpy.random.default_rng([stratum, event_index])
    track_count, vertex_count = generator_check.TRACKS[level], generator_check.VERTICES[level]
    vertices = numpy.zeros(vertex_count, dtype=truth_files.VERTEX)
    vertices["u_mm"], vertices["z_mm"] = draws.uniform(-0.05, 0.05, vertex_count), draws.uniform(-100.2, -99.8, vertex_count)
    step_units = draws.uniform(1.0, 5.0, vertex_count - 1) if event_index % 5 == 0 else draws.uniform(5.0, 25.0, vertex_count - 1)
    vertices["v_mm"] = draws.uniform(-30.0, 30.0) + numpy.concatenate([[0.0], numpy.cumsum(step_units)]) * generator_check.RESOLUTION_UNIT_MM
    tracks = numpy.zeros(track_count, dtype=truth_files.TRACK)
    tracks["particle_key"] = numpy.arange(track_count)
    tracks["vertex_index"] = numpy.arange(track_count) // (track_count // vertex_count)
    tracks["charge"] = draws.permutation(numpy.repeat([1, -1], track_count // 2))
    lower, upper = generator_check.MOMENTUM_BINS_GEV[momentum_bin]
    tracks["momentum_gev"] = numpy.exp(draws.uniform(math.log(lower), math.log(upper), track_count))
    tracks["slope_u"], tracks["slope_v"] = draws.uniform(-0.15, 0.15, track_count), draws.uniform(-0.15, 0.15, track_count)
    tracks["q_over_p"] = tracks["charge"] / tracks["momentum_gev"]
    start = numpy.stack([vertices["z_mm"], vertices["u_mm"], vertices["v_mm"]], axis=1)[tracks["vertex_index"]]
    direction = numpy.stack([numpy.ones(track_count), tracks["slope_u"], tracks["slope_v"]], axis=1)
    loc0, loc1, phi, theta = generator_check.helix_crossings(start, direction, tracks["q_over_p"], generator_check.PLANE_Z_MM)
    tracks["crossings"] = numpy.stack([loc0, loc1, phi, theta], axis=2)
    rows = [(plane + 1, float(fixture_files.on_hit_grid(loc0[track, plane] + draws.normal(0, SIGMA_MM))),
             float(fixture_files.on_hit_grid(loc1[track, plane] + draws.normal(0, SIGMA_MM))), track)
            for track in range(track_count) for plane in range(8)]
    rows.sort()
    hits = numpy.zeros(len(rows), dtype=fixture_files.HIT)
    for hit_key, (plane, first, second, track) in enumerate(rows):
        hits[hit_key] = (hit_key, plane, first, second)
        tracks["hit_keys"][track, plane - 1] = hit_key
    fixture_id = generator_check.FIXTURES[fixture][0]
    truth = {"event_digest": generator_check.seed_digest(fixture_id, generator_check.BLOCK, stratum, event_index), "event_index": numpy.uint64(event_index),
             "momentum_bin": numpy.uint32(momentum_bin), "occupancy_level": numpy.uint32(level), "near_separation": numpy.uint32(event_index % 5 == 0),
             "noise_counts": numpy.zeros(8, dtype=numpy.uint32), "vertices": vertices, "tracks": tracks}
    return truth, hits


class GeneratorCheckCatchesDefects(unittest.TestCase):
    """Section 2.1 adapted: the check must fail on one defect, and pass an honest input."""

    def setUp(self):
        generator_check.failures.clear()
        self.addCleanup(generator_check.failures.clear)

    def quietly(self, action, *arguments):
        with redirect_stdout(io.StringIO()):
            return action(*arguments)

    def test_an_honest_event_has_no_defect(self):
        for stratum, event_index in ((0, 1), (2, 5), (11, 3)):
            with self.subTest(stratum=stratum):
                truth, hits = honest_event(stratum=stratum, event_index=event_index)
                self.assertEqual(generator_check.event_defects(truth, hits, "clean", stratum), [])

    def test_one_event_defect_is_named(self):
        def edit(change):
            truth, hits = honest_event()
            truth["tracks"], truth["vertices"], hits = truth["tracks"].copy(), truth["vertices"].copy(), hits.copy()
            change(truth, hits)
            return generator_check.event_defects(truth, hits, "clean", 0)

        def set_track(field, value):
            return lambda truth, hits: truth["tracks"][field].__setitem__(0, value)

        def swap_two_hits(truth, hits):
            hits[[0, 1]] = hits[[1, 0]]

        def lose_a_hit(truth, hits):
            truth["tracks"]["hit_keys"][0, 3] = truth_files.NO_HIT_KEY

        def wrong_plane(truth, hits):
            keys = truth["tracks"]["hit_keys"]
            keys[0, 0], keys[0, 1] = keys[0, 1], keys[0, 0]

        def off_grid(truth, hits):
            hits["loc0_mm"][0] += 2.0 ** -34

        cases = {"a coordinate is off the hit grid": off_grid,
                 "charges not exactly half and half": set_track("charge", -int(honest_event()[0]["tracks"]["charge"][0])),
                 "momentum outside its bin": set_track("momentum_gev", 3.0),
                 "slope outside its range": set_track("slope_u", 0.16),
                 "a track left the active area": lambda truth, hits: truth["tracks"]["crossings"].__setitem__((0, 7, 0), 150.0),
                 "vertex u or z outside its range": lambda truth, hits: truth["vertices"]["z_mm"].__setitem__(0, -99.7),
                 "first vertex v outside its range": lambda truth, hits: truth["vertices"]["v_mm"].__setitem__(0, 30.5),
                 "vertex step outside its range": lambda truth, hits: truth["vertices"]["v_mm"].__setitem__(1, truth["vertices"]["v_mm"][0] + 26 * 0.0184),
                 "near or far against event_index mod 5": lambda truth, hits: truth.__setitem__("near_separation", numpy.uint32(1)),
                 "seed digest": lambda truth, hits: truth.__setitem__("event_digest", b"\0" * 32),
                 "stratum fields": lambda truth, hits: truth.__setitem__("momentum_bin", numpy.uint32(1)),
                 "hits not in plane and position order": swap_two_hits,
                 "the clean fixture lost a hit or holds noise": lose_a_hit,
                 "a truth hit on the wrong plane": wrong_plane}
        for defect, change in cases.items():
            with self.subTest(defect=defect):
                self.assertIn(defect, edit(change))

    def test_honest_smearing_agrees_and_a_wrong_sigma_or_bias_does_not(self):
        draws = numpy.random.default_rng(20261107)
        kept = numpy.ones((4000, 8), bool)
        honest = draws.normal(0.0, SIGMA_MM, (4000, 8, 2))
        mean_z, variance_z = generator_check.smearing_z(honest, kept)
        self.assertTrue(self.quietly(generator_check.criteria, "honest mean", mean_z))
        self.assertTrue(self.quietly(generator_check.criteria, "honest variance", variance_z))
        self.assertFalse(self.quietly(generator_check.criteria, "wide", generator_check.smearing_z(honest * 1.1, kept)[1]))
        self.assertFalse(self.quietly(generator_check.criteria, "biased", generator_check.smearing_z(honest + 0.002, kept)[0]))

    def test_criteria_fail_on_one_large_z_and_on_too_small_a_sum(self):
        self.assertFalse(self.quietly(generator_check.criteria, "one large", [0.5, -1.0, 5.5, 0.2] * 4))
        self.assertFalse(self.quietly(generator_check.criteria, "too regular", [0.001] * 32))
        self.assertFalse(self.quietly(generator_check.criteria, "not finite", [math.nan, 1.0]))

    def test_helix_check_catches_a_wrong_field_sign_and_a_shift(self):
        truth, _ = honest_event(stratum=2)
        vertices, tracks = truth["vertices"], truth["tracks"]
        start = numpy.stack([vertices["z_mm"], vertices["u_mm"], vertices["v_mm"]], axis=1)[tracks["vertex_index"]]
        self.assertTrue(self.quietly(generator_check.truth_against_helix, "honest", start, tracks))
        flipped = tracks.copy()
        flipped["q_over_p"] = -flipped["q_over_p"]
        self.assertFalse(self.quietly(generator_check.truth_against_helix, "wrong sign", start, flipped))
        shifted = tracks.copy()
        shifted["crossings"][:, 3, 0] += 2e-3
        self.assertFalse(self.quietly(generator_check.truth_against_helix, "shift", start, shifted))

    def test_helix_bends_a_positive_track_towards_negative_u(self):
        """dT/ds = (q k B / p) T x z with T along x and B along z points to -y. Sagitta over 450 mm at 3 GeV, by L^2 / 2R."""
        loc0, loc1, _, _ = generator_check.helix_crossings([[-100.0, 0.0, 0.0]], [[1.0, 0.0, 0.0]], [1.0 / 3.0], generator_check.PLANE_Z_MM)
        self.assertLess(loc0[0, -1], 0.0)
        self.assertAlmostEqual(loc0[0, -1], -(450.0 ** 2) / (2.0 * 3.0 / 0.299792458e-3), delta=0.01)
        self.assertEqual(loc1[0, -1], 0.0)

    def test_uniform_test_catches_a_shifted_range(self):
        draws = numpy.random.default_rng(7).uniform(0.0, 1.0, 5000)
        self.assertTrue(self.quietly(generator_check.uniform_test, "honest", draws, 0.0, 1.0))
        self.assertFalse(self.quietly(generator_check.uniform_test, "shifted", draws * 0.95, 0.0, 1.0))

    def test_seed_digest_is_the_four_words_in_order(self):
        expected = hashlib.sha256(struct.pack("<QQQQ", 7002, 6, 11, 2999)).hexdigest()
        self.assertEqual(generator_check.seed_digest(7002, 6, 11, 2999).hex(), expected)
        self.assertNotEqual(generator_check.seed_digest(6, 7002, 11, 2999).hex(), expected)

    def test_stream_matches_the_published_vector(self):
        """xoshiro256** from the state 1, 2, 3, 4: the first four outputs of its reference implementation."""
        self.assertEqual(generator_check.stream_raw_draws(struct.pack("<4Q", 1, 2, 3, 4), 4), [11520, 0, 1509978240, 1215971899390074240])

    def test_closed_form_constants_round_to_the_fixture_values(self):
        constants = generator_check.closed_form_constants()
        self.assertEqual(round(constants["u_v_mm"], 4), 0.0184)
        self.assertEqual(round(constants["sigma_q_over_p_per_gev"], 5), 0.00412)


# Section 2.1's size: 1,000 events at each of the 4 momentum bins of each occupancy level, the sample the fixture-level tests read.
def honest_cai_event(fixture: str = "cai-clean", stratum: int = 0, event_index: int = 0) -> tuple:
    """One event that obeys section 4.1's text, every draw from the seed stream, with the closed-form helix in place of ACTS: (truth, hits)."""
    fixture_id = generator_check.CAI_FIXTURES[fixture][0]
    digest = generator_check.seed_digest(fixture_id, generator_check.BLOCK, stratum, event_index)
    drawn = generator_check.cai_expected_draws(digest, stratum)
    vertices = numpy.zeros(1, dtype=truth_files.VERTEX)
    vertices["u_mm"], vertices["z_mm"], vertices["v_mm"] = drawn["u_mm"], drawn["z_mm"], drawn["v_mm"]
    tracks = numpy.zeros(1, dtype=truth_files.TRACK)
    tracks["charge"], tracks["momentum_gev"], tracks["slope_u"], tracks["slope_v"] = drawn["charge"], drawn["momentum_gev"], drawn["slope_u"], drawn["slope_v"]
    tracks["q_over_p"] = tracks["charge"] / tracks["momentum_gev"]
    start = numpy.stack([vertices["z_mm"], vertices["u_mm"], vertices["v_mm"]], axis=1)
    direction = numpy.stack([numpy.ones(1), tracks["slope_u"], tracks["slope_v"]], axis=1)
    loc0, loc1, phi, theta = generator_check.helix_crossings(start, direction, tracks["q_over_p"], generator_check.PLANE_Z_MM)
    loc0 = loc0 - generator_check.cai_displacements_mm(fixture)
    tracks["crossings"] = numpy.stack([loc0, loc1, phi, theta], axis=2)
    tracks["hit_keys"] = numpy.arange(8)
    hits = numpy.zeros(8, dtype=fixture_files.HIT)
    hits["hit_key"], hits["plane"] = numpy.arange(8), numpy.arange(1, 9)
    hits["loc0_mm"] = fixture_files.on_hit_grid(loc0[0] + drawn["smear_loc0_mm"])
    hits["loc1_mm"] = fixture_files.on_hit_grid(loc1[0] + drawn["smear_loc1_mm"])
    truth = {"event_digest": digest, "event_index": numpy.uint64(event_index), "momentum_bin": numpy.uint32(stratum), "occupancy_level": numpy.uint32(0),
             "near_separation": numpy.uint32(0), "noise_counts": numpy.zeros(8, dtype=numpy.uint32), "vertices": vertices, "tracks": tracks}
    return truth, hits


def charge_read_from_hits(hits) -> int:
    """The sign of the parabola through loc0 against z: u'' = -k B q/p. Data side only. Holds for both CAI fixtures: the sagitta's rise is at most half of |q/p|."""
    return -1 if numpy.polyfit(numpy.asarray(generator_check.PLANE_Z_MM), hits["loc0_mm"], 2)[0] > 0 else 1


def parity_match(charges_in_file_order, fixture_id: int, block: int, stratum: int) -> float:
    """D1 stage 2 review, C-m1, by SHA-256 alone: a candidate's digest order gives its event_index order, and parity gave the charge. The share that agrees."""
    order = sorted(range(len(charges_in_file_order)), key=lambda index: generator_check.seed_digest(fixture_id, block, stratum, index))
    return float(numpy.mean([charge == (1 if index % 2 == 0 else -1) for charge, index in zip(charges_in_file_order, order)]))


def stream_match(charges_in_file_order, fixture_id: int, block: int, stratum: int) -> float:
    """The accepted search of section 3.2: with the stream as well, the same candidates predict each charge. The share that agrees."""
    digests = sorted(generator_check.seed_digest(fixture_id, block, stratum, index) for index in range(len(charges_in_file_order)))
    return float(numpy.mean([charge == generator_check.cai_expected_draws(digest, stratum)["charge"] for charge, digest in zip(charges_in_file_order, digests)]))


CAI_CANDIDATES = [(fixture_id, block, stratum) for fixture_id in (7003, 7004) for block in (1, 6) for stratum in range(4)]
ATTACK_EVENTS = 300  # one standard deviation of a chance match: 2.9 %


class CaiCheckCatchesDefects(unittest.TestCase):
    """Each rule of the CAI lines fails on one defect in an event that is honest otherwise, and passes the honest event."""

    def setUp(self):
        generator_check.failures.clear()
        self.addCleanup(generator_check.failures.clear)

    def quietly(self, function, *arguments):
        with redirect_stdout(io.StringIO()):
            return function(*arguments)

    def defects_after(self, change, fixture="cai-clean") -> list:
        truth, hits = honest_cai_event(fixture, 1, 3)
        change(truth, hits)
        return generator_check.cai_event_defects(truth, hits, fixture, 1)

    def test_honest_events_have_no_defect(self):
        for fixture in generator_check.CAI_FIXTURES:
            for stratum in range(4):
                for event_index in (0, 1):
                    with self.subTest(fixture=fixture, stratum=stratum, event_index=event_index):
                        truth, hits = honest_cai_event(fixture, stratum, event_index)
                        self.assertEqual(generator_check.cai_event_defects(truth, hits, fixture, stratum), [])

    def test_one_defect_is_named(self):
        def set_field(name, value):
            return lambda truth, hits: truth.__setitem__(name, value)

        def set_track(name, value):
            return lambda truth, hits: truth["tracks"].__setitem__(name, value)

        def swap_hits(truth, hits):
            hits["plane"][[0, 1]] = hits["plane"][[1, 0]]

        def off_grid(truth, hits):
            hits["loc0_mm"][2] += 1e-11

        def vertex_redrawn(truth, hits):
            truth["vertices"]["v_mm"] = truth["vertices"]["v_mm"] + 1e-6

        def noise(truth, hits):
            truth["noise_counts"][3] = 1

        def key_moved(truth, hits):
            truth["tracks"]["hit_keys"][0, 0] = 1

        def flip_charge(truth, hits):
            truth["tracks"]["charge"] = -truth["tracks"]["charge"]

        def slopes_swapped(truth, hits):
            truth["tracks"]["slope_u"], truth["tracks"]["slope_v"] = truth["tracks"]["slope_v"].copy(), truth["tracks"]["slope_u"].copy()

        def smears_swapped(truth, hits):
            crossings = truth["tracks"]["crossings"][0]
            first, second = hits["loc0_mm"] - crossings[:, 0], hits["loc1_mm"] - crossings[:, 1]
            hits["loc0_mm"], hits["loc1_mm"] = fixture_files.on_hit_grid(crossings[:, 0] + second), fixture_files.on_hit_grid(crossings[:, 1] + first)

        cases = {"stratum fields": set_field("momentum_bin", numpy.uint32(2)), "seed digest": set_field("event_index", numpy.uint64(4)),
                 "track keys": set_track("vertex_index", 1), "charge against the stream": flip_charge,
                 "momentum outside its bin": set_track("momentum_gev", 6.5), "slope outside its range": set_track("slope_v", 0.2),
                 "not one hit per plane in plane order": swap_hits, "a coordinate is off the hit grid": off_grid,
                 "vertex against the stream": vertex_redrawn, "noise in a CAI fixture": noise, "truth keys against hits": key_moved,
                 "track against the stream": slopes_swapped, "hit smear against the stream": smears_swapped}
        for name, change in cases.items():
            with self.subTest(defect=name):
                self.assertIn(name, self.defects_after(change))

    def test_a_second_track_or_vertex_is_a_defect(self):
        truth, hits = honest_cai_event()
        truth["tracks"] = numpy.concatenate([truth["tracks"], truth["tracks"]])
        self.assertIn("track count", generator_check.cai_event_defects(truth, hits, "cai-clean", 0))
        truth, hits = honest_cai_event()
        truth["vertices"] = numpy.concatenate([truth["vertices"], truth["vertices"]])
        self.assertIn("vertex count", generator_check.cai_event_defects(truth, hits, "cai-clean", 0))

    def judged(self, fixture: str, change=None, events: int = 400) -> list:
        """The failed lines of one stratum after change(truth, hits) on every event."""
        sample, pool = generator_check.CaiSample(), generator_check.CaiPool()
        for event_index in range(events):
            truth, hits = honest_cai_event(fixture, 0, event_index)
            if change is not None:
                change(truth, hits)
            sample.add(truth, hits, fixture, 0)
        generator_check.failures.clear()
        self.quietly(generator_check.judge_cai_stratum, sample, fixture, 0, events, pool)
        return list(generator_check.failures)

    def test_an_honest_stratum_passes_for_both_fixtures(self):
        self.assertEqual(self.judged("cai-clean"), [])
        self.assertEqual(self.judged("cai-sagitta"), [])

    def test_a_sagitta_fixture_that_shifted_truth_only_fails_agree(self):
        def hits_on_nominal_planes(truth, hits):
            hits["loc0_mm"] = fixture_files.on_hit_grid(hits["loc0_mm"] + generator_check.sagitta_displacements_mm())

        self.assertTrue([line for line in self.judged("cai-sagitta", hits_on_nominal_planes) if line.startswith("AGREE") and "hit mean" in line])

    def test_a_deformation_of_the_wrong_sign_or_none_fails_truth(self):
        def wrong_sign(truth, hits):
            truth["tracks"]["crossings"][0, :, 0] += 2.0 * generator_check.sagitta_displacements_mm()
            hits["loc0_mm"] = fixture_files.on_hit_grid(hits["loc0_mm"] + 2.0 * generator_check.sagitta_displacements_mm())

        def no_deformation(truth, hits):
            truth["tracks"]["crossings"][0, :, 0] += generator_check.sagitta_displacements_mm()
            hits["loc0_mm"] = fixture_files.on_hit_grid(hits["loc0_mm"] + generator_check.sagitta_displacements_mm())

        for change in (wrong_sign, no_deformation):
            with self.subTest(change=change.__name__):
                self.assertTrue([line for line in self.judged("cai-sagitta", change) if line.startswith("TRUTH")])

    def test_a_clean_fixture_with_the_deformation_fails_truth(self):
        def deformed(truth, hits):
            truth["tracks"]["crossings"][0, :, 0] -= generator_check.sagitta_displacements_mm()

        self.assertTrue([line for line in self.judged("cai-clean", deformed) if line.startswith("TRUTH")])

    def test_the_closed_form_lines_pass_and_a_wrong_bias_fails(self):
        self.quietly(generator_check.check_cai_closed_form)
        self.assertEqual(generator_check.failures, [])
        honest = generator_check.SAGITTA_BIAS_IN_SIGMA
        self.addCleanup(setattr, generator_check, "SAGITTA_BIAS_IN_SIGMA", honest)
        generator_check.SAGITTA_BIAS_IN_SIGMA = 4.0
        self.quietly(generator_check.check_cai_closed_form)
        self.assertIn("TRUTH sagitta table of section 4.1", generator_check.failures)

    def test_an_amplitude_off_by_half_a_percent_fails_truth(self):
        """D1 stage 2 review, C-m2: the CAI limit sees 0.19 % of the largest d_k; 1e-3 mm saw only 1.8 %."""
        def scaled(truth, hits):
            truth["tracks"]["crossings"][0, :, 0] -= 0.005 * generator_check.sagitta_displacements_mm()

        self.assertTrue([line for line in self.judged("cai-sagitta", scaled, 40) if line.startswith("TRUTH")])

    def test_sha256_alone_no_longer_names_a_cai_file(self):
        """D1 stage 2 review, C-m1, on events drawn as the generator draws them. Every candidate, the true one included, is at chance."""
        for fixture, fixture_id in (("cai-clean", 7003), ("cai-sagitta", 7004)):
            events = sorted((honest_cai_event(fixture, 0, index) for index in range(ATTACK_EVENTS)), key=lambda event: event[0]["event_digest"])
            charges = [charge_read_from_hits(hits) for _, hits in events]
            self.assertEqual(charges, [int(truth["tracks"]["charge"][0]) for truth, _ in events])
            for candidate in CAI_CANDIDATES:
                with self.subTest(fixture=fixture, candidate=candidate):
                    self.assertLess(abs(parity_match(charges, *candidate) - 0.5), 0.15)
            self.assertEqual(stream_match(charges, fixture_id, generator_check.BLOCK, 0), 1.0)  # the accepted search, which needs the stream

    def test_the_attack_would_have_named_a_file_under_the_parity_rule(self):
        order = sorted(range(ATTACK_EVENTS), key=lambda index: generator_check.seed_digest(7003, 6, 0, index))
        self.assertEqual(parity_match([1 if index % 2 == 0 else -1 for index in order], 7003, 6, 0), 1.0)

    def test_the_family_is_what_the_amendment_states(self):
        """Lines counted as they print, on honest events: two sums per stratum, thirteen tests per fixture. Then the figures of the draft."""
        before = dict(generator_check.family_counts)
        for fixture in generator_check.CAI_FIXTURES:
            pool = generator_check.CaiPool()
            for stratum in range(4):
                sample = generator_check.CaiSample()
                for event_index in range(60):
                    sample.add(*honest_cai_event(fixture, stratum, event_index), fixture, stratum)
                self.quietly(generator_check.judge_cai_stratum, sample, fixture, stratum, 60, pool)
            self.quietly(generator_check.judge_cai_fixture, pool, fixture)
        self.assertEqual(generator_check.family_counts["sums"] - before["sums"], 16)
        self.assertEqual(generator_check.family_counts["tests"] - before["tests"], 26)
        self.assertEqual(round(100.0 * generator_check.false_stop_chance(48, 294), 2), 7.45)
        self.assertEqual(round(100.0 * generator_check.false_stop_chance(16, 26), 2), 1.84)
        self.assertEqual(round(100.0 * generator_check.false_stop_chance(64, 320), 2), 9.16)

    def test_a_cai_fixture_calls_its_own_program(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder)
            for name, code in ((generator_check.GENERATOR_PROGRAM, 1), (generator_check.CAI_GENERATOR_PROGRAM, 0)):
                program = work / name
                program.write_text(f"#!/bin/sh\nexit {code}\n", encoding="utf-8")
                program.chmod(0o755)
            generator_check.run_generator(work, "cai-sagitta", 0, 0, 1, work, "probe")
            with self.assertRaises(subprocess.CalledProcessError):
                generator_check.run_generator(work, "clean", 0, 0, 1, work, "probe")


FULL_SIZE_TRACKS = generator_check.FULL_EVENTS_PER_POINT * sum(generator_check.TRACKS) * len(generator_check.MOMENTUM_BINS_GEV)


class WrongSmearingFailsAtFullSize(unittest.TestCase):
    """D1 review M3, by synthetic injection into the check's own functions: the generator is not changed. Each wrong generator keeps
    mean 0 and variance sigma^2, so the AGREE lines cannot see it; each must fail its own named test here."""

    @classmethod
    def setUpClass(cls):
        draws = numpy.random.default_rng(20261107)
        cls.honest = draws.normal(0.0, SIGMA_MM, (FULL_SIZE_TRACKS, 8, 2))
        cls.uniform = draws.uniform(-math.sqrt(3.0) * SIGMA_MM, math.sqrt(3.0) * SIGMA_MM, (FULL_SIZE_TRACKS, 8, 2))
        cls.kept = numpy.ones((FULL_SIZE_TRACKS, 8), bool)

    def setUp(self):
        generator_check.failures.clear()
        self.addCleanup(generator_check.failures.clear)

    def results_of(self, residuals) -> dict:
        with redirect_stdout(io.StringIO()):
            return generator_check.hit_shape_tests("injected", residuals, self.kept)

    def test_honest_smearing_passes_every_test(self):
        self.assertEqual(self.results_of(self.honest), {"shape loc0": True, "shape loc1": True, "coordinates": True, "planes": True,
                                                        "coordinates squared": True, "planes squared": True})

    def test_uniform_smearing_fails_on_shape_in_each_coordinate(self):
        results = self.results_of(self.uniform)
        self.assertEqual((results["shape loc0"], results["shape loc1"]), (False, False))
        self.assertTrue(results["coordinates"] and results["planes"])

    def test_fully_correlated_coordinates_fail_on_correlation(self):
        correlated = self.honest.copy()
        correlated[:, :, 1] = correlated[:, :, 0]
        results = self.results_of(correlated)
        self.assertFalse(results["coordinates"])
        self.assertTrue(results["shape loc0"] and results["shape loc1"])

    def test_one_smear_shared_by_all_planes_fails_between_planes(self):
        shared = numpy.repeat(self.honest[:, :1, :], 8, axis=1)
        results = self.results_of(shared)
        self.assertFalse(results["planes"])
        self.assertTrue(results["shape loc0"] and results["shape loc1"] and results["coordinates"])

    def radius_shared(self, across_planes: bool) -> numpy.ndarray:
        """One Box-Muller radius reused with an angle of its own for each value: Gaussian in each coordinate, r = 0, and dependent.
        (One radius and one angle, cos and sin, is the honest pair: that is what Box-Muller gives.)"""
        draws = numpy.random.default_rng(29)
        shape = (FULL_SIZE_TRACKS, 1 if across_planes else 8, 1)
        radius = SIGMA_MM * numpy.sqrt(-2.0 * numpy.log(1.0 - draws.uniform(size=shape)))
        return radius * numpy.cos(draws.uniform(0.0, 2.0 * math.pi, (FULL_SIZE_TRACKS, 8, 2)))

    def test_one_radius_for_both_coordinates_fails_on_squares(self):
        results = self.results_of(self.radius_shared(across_planes=False))
        self.assertFalse(results["coordinates squared"])
        self.assertTrue(results["shape loc0"] and results["shape loc1"])  # Gaussian in each coordinate: the marginals cannot see it

    def test_one_radius_for_a_whole_track_fails_on_squares(self):
        results = self.results_of(self.radius_shared(across_planes=True))
        self.assertFalse(results["planes squared"])

    def test_two_planes_sharing_a_smear_are_enough(self):
        shared = self.honest.copy()
        shared[:, 6, :] = shared[:, 2, :]
        self.assertFalse(self.results_of(shared)["planes"])


def decimal_form_tables(noise_values, track_values) -> list:
    """The other representation of a coordinate, the text of the product: the digits of the shortest form, and the last digit of the
    17-digit form the product writes. Per binade and decade, because digit counts follow magnitude, which is the measurement itself."""
    def features(values) -> dict:
        by_binade = {}
        for value in values:
            digits = repr(abs(float(value))).replace(".", "").lstrip("0")
            exact = "%.16e" % abs(float(value))
            decade = int(exact[exact.index("e") + 1:])
            by_binade.setdefault((math.frexp(float(value))[1], decade), []).append((min(len(digits), 18), int(exact[exact.index("e") - 1])))
        return by_binade

    noise_features, track_features = features(noise_values), features(track_values)
    tables = []
    for binade in sorted(set(noise_features) & set(track_features)):
        first, second = numpy.array(noise_features[binade]), numpy.array(track_features[binade])
        if min(len(first), len(second)) >= 320:
            tables.append([numpy.bincount(first[:, 0], minlength=19), numpy.bincount(second[:, 0], minlength=19)])
            tables.append([numpy.bincount(first[:, 1], minlength=10), numpy.bincount(second[:, 1], minlength=10)])
    return tables


def decimal_form_p_value(noise_values, track_values) -> float:
    total, degrees = generator_check.two_sample_chi2(decimal_form_tables(noise_values, track_values))
    return float(generator_check.stats.chi2.sf(total, degrees))


def noise_and_track_positions(rounded: bool) -> tuple:
    """A mixed sample made as the generator makes it: -150 + 300 u, and crossing + smear."""
    draws = numpy.random.default_rng(31)
    noise = -150.0 + 300.0 * draws.random((200000, 2))
    track = draws.uniform(-60.0, 60.0, (40000, 2)) + draws.normal(0.0, SIGMA_MM, (40000, 2))
    return (fixture_files.on_hit_grid(noise), fixture_files.on_hit_grid(track)) if rounded else (noise, track)


class HitBitsSayNothing(unittest.TestCase):
    """D1 re-review N1: the bits of a coordinate must not tell noise from track. A09; t04-prereg.md, "Truth reaches a data-side recipe"."""

    def setUp(self):
        generator_check.failures.clear()
        self.addCleanup(generator_check.failures.clear)

    def bit_results(self, noise, track) -> dict:
        with redirect_stdout(io.StringIO()):
            return generator_check.hit_bit_tests("mixed", noise, track)

    def test_the_attack_works_on_unrounded_hits(self):
        """Positive control: as the review measured, about nine track hits in ten tagged and no noise hit."""
        noise, track = noise_and_track_positions(rounded=False)
        self.assertEqual(int(generator_check.low_bit_attack(noise).sum()), 0)
        self.assertGreater(float(generator_check.low_bit_attack(track).mean()), 0.8)

    def test_the_general_statistic_sees_unrounded_hits(self):
        noise, track = noise_and_track_positions(rounded=False)
        self.assertFalse(self.bit_results(noise, track)["mantissa tail"])

    def test_on_the_grid_the_attack_tags_nothing(self):
        noise, track = noise_and_track_positions(rounded=True)
        self.assertEqual(int(generator_check.low_bit_attack(noise).sum()), 0)
        self.assertEqual(int(generator_check.low_bit_attack(track).sum()), 0)

    def test_on_the_grid_no_bit_statistic_separates_them(self):
        noise, track = noise_and_track_positions(rounded=True)
        self.assertEqual(self.bit_results(noise, track), {"low bits": True, "residues": True, "mantissa tail": True})

    def test_one_kind_on_another_grid_is_seen_by_each_statistic(self):
        noise, track = noise_and_track_positions(rounded=True)
        coarser = numpy.rint(noise * 2.0 ** 29) / 2.0 ** 29  # the lowest grid bit of noise hits always zero
        results = self.bit_results(coarser, track)
        self.assertFalse(results["low bits"])
        self.assertFalse(results["residues"] and results["mantissa tail"])

    def test_the_decimal_form_says_nothing_on_the_grid_and_can_fail(self):
        noise, track = noise_and_track_positions(rounded=True)
        self.assertGreaterEqual(decimal_form_p_value(noise[:60000, 0], track[:, 0]), generator_check.ALPHA)
        self.assertLess(decimal_form_p_value(numpy.round(noise[:60000, 0], 6), track[:, 0]), generator_check.ALPHA)

    def test_the_rounding_favours_no_parity_on_a_tie(self):
        steps = numpy.arange(-1000, 1000) + 0.5
        rounded = fixture_files.on_hit_grid(steps / fixture_files.HIT_GRID_STEPS_PER_MM) * fixture_files.HIT_GRID_STEPS_PER_MM
        self.assertEqual(int((rounded % 2 == 0).sum()), 1000)

    def test_the_grid_is_far_below_sigma_and_moves_no_statistic(self):
        grid_mm = 1.0 / fixture_files.HIT_GRID_STEPS_PER_MM
        self.assertLess(grid_mm, 1e-7 * SIGMA_MM)
        draws = numpy.random.default_rng(37)
        hits = draws.uniform(-150.0, 150.0, 100000)
        self.assertLessEqual(float(numpy.abs(fixture_files.on_hit_grid(hits) - hits).max()), grid_mm / 2)
        self.assertEqual(fixture_files.off_hit_grid(fixture_files.on_hit_grid(hits)), 0)
        self.assertEqual(float(fixture_files.on_hit_grid(numpy.array([-1e-12]))[0]).hex(), "0x0.0p+0")

    def test_an_off_grid_coordinate_fails_the_file_check(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "hits.t07data"
            path.write_bytes(fixture_files.encode_data_file(SIGMA_MM, [[(1, 0.5 + 2.0 ** -34, -0.5)]]))
            self.assertIn("a coordinate is off the hit grid", fixture_files.data_file_defects(path))


GENERATOR_SIDE_PYTHON = {"check_t07_generator", "t07_truth_files"}


def generator_side_imports(source: str) -> list:
    """The generator-side Python modules a source imports."""
    found = []
    for node in ast.walk(ast.parse(source)):
        names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
        found += [name for name in names if name.split(".")[-1] in GENERATOR_SIDE_PYTHON]
    return found


class DataSidePythonImportsNoGeneratorCode(unittest.TestCase):
    """D1 re-review N7: the rule of the C++ test, for Python. Every module of the adapter is data side unless named above, so a new
    recipe module is covered by being there. The wrapper starts the generator as a program and imports none of its code."""

    def test_no_data_side_module_imports_seed_or_truth_code(self):
        modules = [path for path in (ADAPTER / "assets").rglob("*.py") if path.stem not in GENERATOR_SIDE_PYTHON]
        self.assertGreaterEqual(len(modules), 3)
        for module in modules:
            with self.subTest(module=module.name):
                self.assertEqual(generator_side_imports(module.read_text(encoding="utf-8")), [])

    def test_an_import_would_be_caught_in_each_form(self):
        for source in ("import t07_truth_files\n", "from check_t07_generator import seed_digest\n", "import check_t07_generator as anything\n"):
            with self.subTest(source=source):
                self.assertTrue(generator_side_imports(source))
        self.assertEqual(generator_side_imports("import t07_fixture_files\n"), [])


class DrawsAndFilesFailOnOneDefect(unittest.TestCase):
    """D1 review m1 and the rest of M3."""

    def setUp(self):
        generator_check.failures.clear()
        self.addCleanup(generator_check.failures.clear)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)

    def quietly(self, action, *arguments):
        with redirect_stdout(io.StringIO()):
            return action(*arguments)

    def test_hits_per_track_follow_the_binomial(self):
        draws = numpy.random.default_rng(11)
        honest = draws.uniform(size=(100000, 8)) < 0.98
        self.assertTrue(self.quietly(generator_check.hit_count_test, "honest", honest, 0.98))
        self.assertFalse(self.quietly(generator_check.hit_count_test, "wrong rate", draws.uniform(size=(100000, 8)) < 0.97, 0.98))
        whole_track = numpy.repeat(draws.uniform(size=(100000, 1)) < 0.98, 8, axis=1)  # right rate per plane, not independent
        self.assertFalse(self.quietly(generator_check.hit_count_test, "whole tracks lost", whole_track, 0.98))

    def test_draws_the_text_makes_independent_are_tested_together(self):
        draws = numpy.random.default_rng(13)
        first, second = draws.uniform(-0.15, 0.15, 50000), draws.uniform(-0.15, 0.15, 50000)
        self.assertTrue(self.quietly(generator_check.draw_independence_test, "honest", ((first, second),)))
        self.assertFalse(self.quietly(generator_check.draw_independence_test, "slope v = slope u", ((first, first),)))

    def identity_files(self, block: int = 6, stratum: int = 4, generator: str = "t07-telescope-noise/1", sigma_mm: float = SIGMA_MM) -> tuple:
        data_file, truth_file = self.work / "events.t07data", self.work / "events.t07truth"
        data_file.write_bytes(fixture_files.encode_data_file(sigma_mm, [[(1, 0.5, -0.5)], [(2, 0.5, 0.5)]]))
        header = numpy.zeros(1, dtype=truth_files.TRUTH_HEADER)
        header["magic"], header["role"], header["generator"] = truth_files.TRUTH_MAGIC, b"truth", generator.encode()
        header["fixture_id"], header["block"], header["stratum"], header["event_count"] = 7002, block, stratum, 2
        header["sigma_loc0_mm"] = header["sigma_loc1_mm"] = SIGMA_MM
        header["data_sha256"] = numpy.void(bytes.fromhex(fixture_files.file_sha256(data_file)))
        truth_file.write_bytes(header.tobytes())
        return data_file, truth_file

    def test_both_headers_are_checked(self):
        self.assertEqual(generator_check.file_identity_defects(*self.identity_files(), "noise", 4, 2), [])
        self.assertIn("truth header block", generator_check.file_identity_defects(*self.identity_files(block=5), "noise", 4, 2))
        self.assertIn("truth header stratum", generator_check.file_identity_defects(*self.identity_files(stratum=5), "noise", 4, 2))
        self.assertIn("truth header generator", generator_check.file_identity_defects(*self.identity_files(generator="t07-telescope-clean/1"), "noise", 4, 2))
        self.assertIn("data header sigma_loc0_mm", generator_check.file_identity_defects(*self.identity_files(sigma_mm=0.03), "noise", 4, 2))
        data_file, truth_file = self.identity_files()
        data_file.write_bytes(fixture_files.encode_data_file(SIGMA_MM, [[(1, 0.5, -0.5)], [(2, 0.5, 0.75)]]))
        self.assertIn("truth header data_sha256", generator_check.file_identity_defects(data_file, truth_file, "noise", 4, 2))

    def test_every_generator_call_counts_its_stderr(self):
        program = self.work / "t07_fixture_generator"
        program.write_text("#!/bin/sh\necho 'digest 00' ; echo 'an ACTS warning' >&2\n", encoding="utf-8")
        program.chmod(program.stat().st_mode | stat.S_IXUSR)
        before = generator_check.generator_stderr_bytes
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            generator_check.check_seed_rule(self.work)
        self.assertGreater(generator_check.generator_stderr_bytes, before)
        generator_check.generator_stderr_bytes = before

    def test_generator_stderr_reaches_stderr_and_is_counted(self):
        program = self.work / "t07_fixture_generator"
        program.write_text("#!/bin/sh\necho 'an ACTS warning' >&2\n", encoding="utf-8")
        program.chmod(program.stat().st_mode | stat.S_IXUSR)
        before = generator_check.generator_stderr_bytes
        captured = io.StringIO()
        with redirect_stderr(captured):
            generator_check.run_generator(self.work, "clean", 0, 0, 1, self.work, "probe")
        self.assertIn("an ACTS warning", captured.getvalue())
        self.assertGreater(generator_check.generator_stderr_bytes, before)
        generator_check.generator_stderr_bytes = before

    def test_section_4_1_closed_forms_are_recomputed(self):
        with redirect_stdout(io.StringIO()):
            generator_check.check_closed_form()
        self.assertEqual(generator_check.failures, [])


class WrapperForwardsAndReports(unittest.TestCase):
    """docs/adapter-authoring.md, Honesty rules: a missing tool is a failed result with the reason, never a fallback."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.build = Path(self.folder.name)

    def fake_program(self, name: str, exit_code: int, message: str = "") -> None:
        program = self.build / name
        program.write_text(f"#!/bin/sh\necho '{message}' >&2\nexit {exit_code}\n", encoding="utf-8")
        program.chmod(program.stat().st_mode | stat.S_IXUSR)

    def invoke(self, *arguments) -> tuple:
        captured = io.StringIO()
        with redirect_stdout(captured):
            exit_code = wrapper.main(list(arguments))
        return exit_code, json.loads(captured.getvalue())

    def test_a_missing_program_is_reported_and_nothing_runs(self):
        exit_code, report = self.invoke("self-test", "--work-dir", str(self.build), "--build-dir", str(self.build / "absent"))
        self.assertEqual((exit_code, report["status"]), (3, "missing-dependency"))
        self.assertIn("acts_tracking_driver", report["reason"])

    def test_exit_codes_of_the_program_are_kept_apart(self):
        for program_exit, wrapper_exit, status in ((0, 0, "ok"), (2, 2, "rejected"), (3, 1, "failed")):
            with self.subTest(program_exit=program_exit):
                self.fake_program("acts_tracking_driver", program_exit, "reason here")
                exit_code, report = self.invoke("self-test", "--work-dir", str(self.build), "--build-dir", str(self.build))
                self.assertEqual((exit_code, report["status"], report["program_exit"]), (wrapper_exit, status, program_exit))

    def test_a_refit_with_no_track_fitted_is_a_failure(self):
        for summary, exit_code, status in (('{"tracks": 2, "failed": 2}', 1, "failed"), ('{"tracks": 2, "failed": 1}', 0, "ok"), ('{"tracks": 0, "failed": 0}', 0, "ok")):
            with self.subTest(summary=summary):
                program = self.build / "acts_tracking_driver"
                program.write_text(f"#!/bin/sh\necho '{summary}'\n", encoding="utf-8")
                program.chmod(program.stat().st_mode | stat.S_IXUSR)
                (self.build / "in").write_text("x", encoding="utf-8")
                found_exit, report = self.invoke("refit", "--data-file", str(self.build / "in"), "--hit-sets", str(self.build / "in"), "--field-tesla", "0",
                                                 "--product-id", "refit.alpha", "--product-file", str(self.build / "p"), "--build-dir", str(self.build))
                self.assertEqual((found_exit, report["status"]), (exit_code, status))
                self.assertEqual(report["failed_tracks"], json.loads(summary)["failed"])

    def test_a_missing_input_is_refused_before_the_program(self):
        self.fake_program("acts_tracking_driver", 0)
        exit_code, report = self.invoke("refit", "--data-file", str(self.build / "absent"), "--hit-sets", str(self.build / "absent"), "--field-tesla", "0",
                                        "--product-id", "refit.alpha", "--product-file", str(self.build / "p"), "--build-dir", str(self.build))
        self.assertEqual((exit_code, report["status"]), (2, "rejected"))

    def test_the_tool_contract_passes_against_the_command_line(self):
        contract = json.loads((ROOT / "contracts" / "tool_contracts" / "acts_tracking.json").read_text(encoding="utf-8"))
        result = tool_contract.check(contract)
        self.assertEqual(result["status"], "pass", result["findings"])

    def test_the_tool_contract_fails_on_one_undeclared_option(self):
        contract = json.loads((ROOT / "contracts" / "tool_contracts" / "acts_tracking.json").read_text(encoding="utf-8"))
        refit = next(operation for operation in contract["operations"] if operation["operation_id"] == "refit")
        refit["invocation"]["options"] = [option for option in refit["invocation"]["options"] if option["flag"] != "--product-id"]
        refit["inputs"] = [item for item in refit["inputs"] if item["name"] != "product_id"]
        self.assertEqual(tool_contract.check(contract)["status"], "fail")

    def test_the_adapter_claims_nothing_it_has_not_run(self):
        # D1 stage 11 (T07 close-out): the build jobs ran ACTS on synthetic fixtures only, so the claim is demonstrated-on-synthetic-data and no higher
        # (docs/adapter-authoring.md, Honesty rules); the version is the one the driver's self-test asserts and every product header writes, and VALIDATION.md
        # records the run under the adapter's version (Changing an adapter). Before stage 11 this test held the adapter at proposed with no version.
        # Fix round 1 (review M3): adapter.json and VALIDATION.md name one and the same job of record for the declared version, "the D1 stage 11 job" until the
        # coordinator writes its ID after it passes, then "job <ID>"; job 7548207, which ran 0.1.0 (proposed), is cited for that alone.
        declaration = json.loads((ADAPTER / "adapter.json").read_text(encoding="utf-8"))
        self.assertEqual(declaration["status"], "demonstrated-on-synthetic-data")
        self.assertEqual([tool["status"] for tool in declaration["tools"]], ["demonstrated-on-synthetic-data"])
        versions = declaration["tools"][0]["tested_versions"]
        self.assertEqual(len(versions), 1)
        driver = (NATIVE / "acts_tracking_driver.cpp").read_text(encoding="utf-8")
        self.assertIn('test.check("ACTS is 48.2.0", acts_version_text() == "48.2.0");', driver)
        self.assertTrue(versions[0].startswith("acts-core 48.2.0 "), versions[0])
        for word in ("GCC 15.3.0", "CMake 4.4.5", "Python 3.13.18"):
            self.assertIn(word, versions[0])
        self.assertTrue(declaration["status_rule"].split(";")[1].strip().startswith("demonstrated-on-synthetic-data:"), declaration["status_rule"])  # review minor 5
        validation = (ROOT / "VALIDATION.md").read_text(encoding="utf-8")
        section = validation[validation.index("\n## ACTS-TRACKING-T07 "):]
        section = section[:section.index("\n## ", 1)] if "\n## " in section[1:] else section
        version = declaration["version"]
        record_pattern = rf"job of record for adapter {re.escape(version)}: (the D1 stage 11 job|job \d+)"
        in_declaration = re.findall(record_pattern, declaration["environment"] + " " + declaration["status_rule"], flags=re.IGNORECASE)
        in_validation = re.findall(record_pattern, section, flags=re.IGNORECASE)
        self.assertTrue(in_declaration and in_validation, "adapter.json and VALIDATION.md each name the job of record of the declared version")
        self.assertEqual(len(set(job.lower() for job in in_declaration + in_validation)), 1, (in_declaration, in_validation))
        self.assertNotEqual(in_declaration[0].lower(), "job 7548207")
        self.assertIn(f"Adapter {version} ", section)
        for name, text in (("adapter.json", json.dumps(declaration)), ("VALIDATION.md", section)):
            with self.subTest(record=name):
                self.assertEqual(text.count("7548207"), text.count("job 7548207 (adapter 0.1.0, proposed"), f"{name} cites job 7548207 other than for 0.1.0")
                self.assertIn("job 7548207 (adapter 0.1.0, proposed", text)


# D1 stage 10: the wrapper, the manifest and the tool contract carry the driver interfaces of stages 8 and 9, --alignment-payload on refit and
# --r33-outputs on find. The formats each help text names are read from the native sources, so a program that writes another format fails here.
WRAPPER_SOURCE = ADAPTER / "assets" / "acts_tracking.py"
WRAPPER_IMPORTS = {"__future__", "argparse", "json", "os", "subprocess", "sys", "pathlib"}
FORMAT_SOURCES = ("native_product.hpp", "acts_tracking_driver.cpp", "acts_tracking_finder.cpp", "r33_product_outputs.hpp", "alignment_payload.hpp", "track_fit_outputs.hpp")
FINDER_NAMES_R33 = "  if (with_r33_outputs) {\n    t07::name_r33_conventions(document);\n  }\n"


def wrapper_option_helps(parser: argparse.ArgumentParser = None) -> dict:
    """{(operation, flag): help} of the wrapper's subcommands."""
    parser = parser or wrapper.build_parser()
    commands = next(action for action in parser._actions if isinstance(action, argparse._SubParsersAction))
    return {(name, flag): action.help for name, sub in commands.choices.items() for action in sub._actions for flag in action.option_strings if flag.startswith("--")}


def native_constant(text: str, name: str) -> str:
    found = re.search(rf'\b{name}\[\] = "([^"]+)";', text)
    return found.group(1) if found else ""


def format_written(body: str, versions: dict, default: str) -> str:
    found = re.search(r"document\.format_version = (\d);", body)
    return versions.get(found.group(1) if found else default, "")


def wrapper_format_defects(helps: dict, sources: dict) -> list:
    """What each wrapper help text says the programs read or write, against what the native sources say: the product format of the refit and of the finder
    with and without --r33-outputs, the payload format and the R33 conventions name, and that the programs take the two flags."""
    product = sources["native_product.hpp"]
    versions = {"1": native_constant(product, "product_format"), "2": native_constant(product, "product_format_r33")}
    default = re.search(r"int format_version = (\d);", product).group(1)
    driver, finder, outputs = sources["acts_tracking_driver.cpp"], sources["acts_tracking_finder.cpp"], sources["r33_product_outputs.hpp"]
    refit_body = driver[driver.index("int refit("):driver.index("int geometry_id(")]
    finder_run = finder[finder.index("int run("):]
    naming = outputs[outputs.index("inline void name_r33_conventions("):]
    naming = naming[:naming.index("\n}\n")]
    refit_writes, finder_plain, finder_r33 = format_written(refit_body, versions, default), format_written(finder_run, versions, default), format_written(naming, versions, default)
    payload_format = native_constant(sources["alignment_payload.hpp"], "alignment_payload_format")
    conventions = native_constant(sources["track_fit_outputs.hpp"], "r33_conventions_name")
    defects = []
    if not re.search(r'require_only\(flags, \{[^}]*"alignment-payload"', refit_body):
        defects.append("the driver's refit takes no --alignment-payload")
    if not re.search(r'optional_outputs\{[^}]*"r33-outputs"', finder):
        defects.append("the finder takes no --r33-outputs")
    if FINDER_NAMES_R33 not in finder_run:
        defects.append("the finder does not name the R33 conventions only under --r33-outputs")
    refit_product = helps.get(("refit", "--product-file"), "")
    if refit_writes not in refit_product or (versions["1"] if refit_writes == versions["2"] else versions["2"]) in refit_product:
        defects.append(f"refit --product-file does not name what the refit writes, {refit_writes}: {refit_product}")
    # Fix round 1, F3: the payload's header line, and only with the flag that gives it.
    if "alignment_payload" not in refit_product or "--alignment-payload" not in refit_product:
        defects.append(f"refit --product-file does not name the alignment_payload line that --alignment-payload adds: {refit_product}")
    if payload_format not in helps.get(("refit", "--alignment-payload"), ""):
        defects.append(f"refit --alignment-payload does not name {payload_format}")
    # Fix round 1, F3: without the flag the finder writes /1 and with it /2, and the help puts each format with its condition: the plain format before the
    # semicolon, the R33 format after it, beside --r33-outputs.
    if finder_plain != versions["1"] or finder_r33 != versions["2"]:
        defects.append(f"the finder writes {finder_plain} without --r33-outputs and {finder_r33} with it, not {versions['1']} and {versions['2']}")
    find_product = helps.get(("find", "--product-file"), "")
    plain_part, _, flagged_part = find_product.partition(";")
    if finder_plain not in plain_part or finder_r33 in plain_part or finder_r33 not in flagged_part or "--r33-outputs" not in flagged_part:
        defects.append(f"find --product-file does not name {finder_plain}, and then {finder_r33} with --r33-outputs: {find_product}")
    r33_help = helps.get(("find", "--r33-outputs"), "")
    if conventions not in r33_help or finder_r33 not in r33_help:
        defects.append(f"find --r33-outputs does not name {conventions} and {finder_r33}")
    return defects


def wrapper_reader_defects(source: str) -> list:
    """The wrapper forwards and reads no input: it imports only the standard modules it uses and opens no file. A tripwire, not a proof (fix round 1, F9): the
    substring checks would also flag a harmless comment, and would miss a read through a helper module the wrapper imported, which the import check refuses."""
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    defects = [f"the wrapper imports {name}" for name in sorted(imported - WRAPPER_IMPORTS)]
    defects += [f"the wrapper calls {call}" for call in ("open(", "read_text(", "read_bytes(") if call in source]
    return defects


class WrapperCarriesTheStageEightAndNineInterfaces(unittest.TestCase):
    """D1 stage 10: --alignment-payload and --r33-outputs, forwarded exactly and only when given; the contract, the manifest and the help texts name them."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.build = Path(self.folder.name)
        self.sources = {name: (NATIVE / name).read_text(encoding="utf-8") for name in FORMAT_SOURCES}
        self.contract = json.loads((ROOT / "contracts" / "tool_contracts" / "acts_tracking.json").read_text(encoding="utf-8"))
        self.payload_format = native_constant(self.sources["alignment_payload.hpp"], "alignment_payload_format")
        self.conventions = native_constant(self.sources["track_fit_outputs.hpp"], "r33_conventions_name")

    def planned(self, *arguments) -> tuple:
        return wrapper.program_and_arguments(wrapper.build_parser().parse_args(list(arguments)))

    def test_refit_forwards_the_payload_exactly_and_only_when_given(self):
        given = ["refit", "--data-file", "d.t07data", "--hit-sets", "h.hitsets", "--field-tesla", "1", "--product-id", "p", "--product-file", "out.product"]
        plain = ["refit", "--data-file", "d.t07data", "--hit-sets", "h.hitsets", "--field-tesla", "1.0", "--product-id", "p", "--product-file", "out.product"]
        self.assertEqual(self.planned(*given), (wrapper.DRIVER, plain))
        self.assertEqual(self.planned(*given, "--alignment-payload", "a.t07payload"), (wrapper.DRIVER, plain + ["--alignment-payload", "a.t07payload"]))
        self.assertEqual(self.planned("refit", "--alignment-payload", "a.t07payload", *given[1:]), (wrapper.DRIVER, plain + ["--alignment-payload", "a.t07payload"]))
        self.assertEqual(self.planned(*given, "--build-dir", "b"), (wrapper.DRIVER, plain))

    def test_find_forwards_r33_outputs_exactly_and_only_when_given(self):
        given = ["find", "--data-file", "d.t07data", "--product-id", "p", "--product-file", "out.product", "--record-file", "out.record", "--product-events", "60"]
        plain = given[1:]
        self.assertEqual(self.planned(*given), (wrapper.FINDER, plain))
        self.assertEqual(self.planned(*given, "--r33-outputs", "t07-r33/1"), (wrapper.FINDER, plain + ["--r33-outputs", "t07-r33/1"]))
        # The finder is the one judge of the value: another is forwarded as given, and the finder refuses it.
        self.assertEqual(self.planned(*given, "--r33-outputs", "t07-r33/2"), (wrapper.FINDER, plain + ["--r33-outputs", "t07-r33/2"]))

    def test_the_other_operations_forward_as_before(self):
        self.assertEqual(self.planned("self-test", "--work-dir", "w"), (wrapper.DRIVER, ["self-test", "--work-dir", "w"]))
        self.assertEqual(self.planned("generate-fixture", "--fixture", "noise", "--block", "1", "--stratum", "2", "--first-event", "0", "--count", "3", "--data-file", "d",
                                      "--truth-file", "t.t07truth"),
                         (wrapper.GENERATOR, ["generate", "--fixture", "noise", "--block", "1", "--stratum", "2", "--first-event", "0", "--count", "3", "--data-file", "d",
                                              "--truth-file", "t.t07truth"]))

    def recording_program(self, name: str, exit_code: int = 0, message: str = "") -> Path:
        """A stand-in that writes its arguments one per line and a message to stderr."""
        seen = self.build / f"{name}.arguments"
        program = self.build / name
        program.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{seen}'\nprintf '%s\\n' '{message}' >&2\nexit {exit_code}\n", encoding="utf-8")
        program.chmod(program.stat().st_mode | stat.S_IXUSR)
        return seen

    def invoke(self, *arguments) -> tuple:
        captured = io.StringIO()
        with redirect_stdout(captured):
            exit_code = wrapper.main(list(arguments))
        return exit_code, json.loads(captured.getvalue())

    def inputs(self) -> tuple:
        names = [self.build / name for name in ("in.t07data", "in.hitsets", "in.t07payload")]
        for path in names:
            path.write_text("x", encoding="utf-8")
        return tuple(str(path) for path in names)

    def test_the_program_receives_the_flags_as_given(self):
        data_file, hit_sets, payload = self.inputs()
        seen = self.recording_program("acts_tracking_driver")
        exit_code, report = self.invoke("refit", "--data-file", data_file, "--hit-sets", hit_sets, "--field-tesla", "1", "--product-id", "p", "--product-file", "out",
                                        "--alignment-payload", payload, "--build-dir", str(self.build))
        self.assertEqual((exit_code, report["status"]), (0, "ok"))
        expected = ["refit", "--data-file", data_file, "--hit-sets", hit_sets, "--field-tesla", "1.0", "--product-id", "p", "--product-file", "out", "--alignment-payload", payload]
        self.assertEqual(seen.read_text(encoding="utf-8").splitlines(), expected)
        self.assertEqual(report["command"][1:], expected)
        seen = self.recording_program("acts_tracking_finder")
        exit_code, report = self.invoke("find", "--data-file", data_file, "--product-id", "p", "--product-file", "out", "--record-file", "rec", "--product-events", "5",
                                        "--r33-outputs", "t07-r33/1", "--build-dir", str(self.build))
        self.assertEqual(exit_code, 0)
        self.assertEqual(seen.read_text(encoding="utf-8").splitlines(),
                         ["--data-file", data_file, "--product-id", "p", "--product-file", "out", "--record-file", "rec", "--product-events", "5", "--r33-outputs", "t07-r33/1"])

    def test_a_missing_payload_is_refused_before_the_program(self):
        data_file, hit_sets, _ = self.inputs()
        seen = self.recording_program("acts_tracking_driver")
        absent = str(self.build / "absent.t07payload")
        exit_code, report = self.invoke("refit", "--data-file", data_file, "--hit-sets", hit_sets, "--field-tesla", "0", "--product-id", "p", "--product-file", "out",
                                        "--alignment-payload", absent, "--build-dir", str(self.build))
        self.assertEqual((exit_code, report["status"], report["reason"]), (2, "rejected", f"no such input file: {absent}"))
        self.assertFalse(seen.exists())

    def test_the_programs_refusal_comes_back_unchanged(self):
        data_file, hit_sets, payload = self.inputs()
        refusal = "invalid input: refused: the alignment payload names plane 9, and the telescope has planes 1 to 8"
        self.recording_program("acts_tracking_driver", 2, refusal)
        exit_code, report = self.invoke("refit", "--data-file", data_file, "--hit-sets", hit_sets, "--field-tesla", "0", "--product-id", "p", "--product-file", "out",
                                        "--alignment-payload", payload, "--build-dir", str(self.build))
        self.assertEqual((exit_code, report["status"], report["program_exit"], report["reason"], report["program_stderr"]), (2, "rejected", 2, refusal, refusal + "\n"))

    def test_the_help_texts_name_the_formats_the_programs_write(self):
        self.assertEqual(wrapper_format_defects(wrapper_option_helps(), self.sources), [])

    def test_a_help_text_or_a_program_that_disagrees_is_caught(self):
        helps = wrapper_option_helps()
        product_v1, product_v2 = native_constant(self.sources["native_product.hpp"], "product_format"), native_constant(self.sources["native_product.hpp"], "product_format_r33")
        refit_one = {**helps, ("refit", "--product-file"): helps[("refit", "--product-file")].replace(product_v2, product_v1)}
        finder_plain_only = {**helps, ("find", "--product-file"): "acts-tracking-product/1 to write, with the states of the selected tracks"}
        other_payload = {**helps, ("refit", "--alignment-payload"): helps[("refit", "--alignment-payload")].replace(self.payload_format, "t07-alignment-payload/2")}
        no_conventions = {**helps, ("find", "--r33-outputs"): helps[("find", "--r33-outputs")].replace(self.conventions, "the conventions")}
        driver_one = {**self.sources, "acts_tracking_driver.cpp": self.sources["acts_tracking_driver.cpp"].replace("document.format_version = 2;  // R33", "document.format_version = 1;  // R33")}
        finder_always = {**self.sources, "acts_tracking_finder.cpp": self.sources["acts_tracking_finder.cpp"].replace(FINDER_NAMES_R33, "  t07::name_r33_conventions(document);\n")}
        finder_swapped = {**helps, ("find", "--product-file"): "acts-tracking-product/2 to write, with R33's outputs; acts-tracking-product/1 with --r33-outputs"}
        refit_no_line = {**helps, ("refit", "--product-file"): helps[("refit", "--product-file")].replace("alignment_payload", "payload")}
        refit_no_flag = {**helps, ("refit", "--product-file"): helps[("refit", "--product-file")].replace("--alignment-payload", "a payload")}
        finder_always_two = {**self.sources, "acts_tracking_finder.cpp": self.sources["acts_tracking_finder.cpp"].replace(
            "  t07::ProductDocument document;\n", "  t07::ProductDocument document;\n  document.format_version = 2;\n", 1)}
        finder_without = {**self.sources, "acts_tracking_finder.cpp": self.sources["acts_tracking_finder.cpp"].replace('"ambiguity-trace-events", "r33-outputs"}', '"ambiguity-trace-events"}')}
        driver_without = {**self.sources, "acts_tracking_driver.cpp": self.sources["acts_tracking_driver.cpp"].replace('"product-file", "alignment-payload"}', '"product-file"}')}
        for name, (case_helps, case_sources) in {"refit help naming /1": (refit_one, self.sources), "find help without /2": (finder_plain_only, self.sources),
                                                 "another payload format": (other_payload, self.sources), "no conventions name": (no_conventions, self.sources),
                                                 "a refit writing /1": (helps, driver_one), "a finder naming R33 always": (helps, finder_always),
                                                 "a finder without the flag": (helps, finder_without), "a driver without the flag": (helps, driver_without),
                                                 "find help with the formats swapped": (finder_swapped, self.sources), "refit help without the payload line": (refit_no_line, self.sources),
                                                 "refit help without the payload flag": (refit_no_flag, self.sources), "a finder always at /2": (helps, finder_always_two)}.items():
            with self.subTest(case=name):
                self.assertTrue(case_helps != helps or case_sources != self.sources, "the defect was not made")
                self.assertTrue(wrapper_format_defects(case_helps, case_sources))

    def test_a_flag_is_not_taken_from_its_abbreviation(self):
        """fix round 1, F8: allow_abbrev=False, so --alignment is not --alignment-payload and --r33 is not --r33-outputs."""
        for arguments in (["refit", "--data-file", "d", "--hit-sets", "h", "--field-tesla", "0", "--product-id", "p", "--product-file", "o", "--alignment", "a"],
                          ["find", "--data-file", "d", "--product-id", "p", "--product-file", "o", "--record-file", "r", "--product-events", "1", "--r33", "t07-r33/1"]):
            with self.subTest(operation=arguments[0]), redirect_stderr(io.StringIO()):
                self.assertEqual(wrapper.main(arguments), wrapper.EXIT_INVALID)

    def test_the_wrapper_reads_no_input_itself(self):
        source = WRAPPER_SOURCE.read_text(encoding="utf-8")
        self.assertEqual(wrapper_reader_defects(source), [])
        self.assertTrue(wrapper_reader_defects(source + "\nimport t07_alignment_payload\n"))
        self.assertTrue(wrapper_reader_defects(source + "\nPAYLOAD = Path('p').read_text()\n"))

    def test_the_contract_names_the_flags_and_the_formats(self):
        operations = {operation["operation_id"]: operation for operation in self.contract["operations"]}
        for operation_id, flag, name, words in (("refit", "--alignment-payload", "alignment_payload", (self.payload_format, "alignment conditions")),
                                                ("find", "--r33-outputs", "r33_outputs", (self.conventions, "acts-tracking-product/2"))):
            with self.subTest(operation=operation_id):
                operation = operations[operation_id]
                self.assertIn({"flag": flag, "input": name}, operation["invocation"]["options"])
                item = next(item for item in operation["inputs"] if item["name"] == name)
                self.assertFalse(item["required"])
                for word in words:
                    self.assertIn(word, item["constraint"])
        refit_product = next(item for item in operations["refit"]["inputs"] if item["name"] == "product_file")["constraint"]
        find_product = next(item for item in operations["find"]["inputs"] if item["name"] == "product_file")["constraint"]
        self.assertTrue(refit_product.startswith("acts-tracking-product/2 ") and "alignment_payload" in refit_product, refit_product)
        self.assertTrue(find_product.startswith("acts-tracking-product/1 ") and "acts-tracking-product/2" in find_product and "r33_outputs" in find_product, find_product)

    def test_the_manifest_names_the_flags_and_the_formats(self):
        purpose = json.loads((ADAPTER / "adapter.json").read_text(encoding="utf-8"))["purpose"]
        for word in ("--alignment-payload", "--r33-outputs", self.payload_format, self.conventions, "acts-tracking-product/2", "alignment_payload header line"):
            self.assertIn(word, purpose)


def run_driver(*arguments) -> subprocess.CompletedProcess:
    return subprocess.run([str(DRIVER), *arguments], capture_output=True, text=True, timeout=300)


def straight_line_files(folder: Path) -> tuple:
    """One event per straight track. Returns the data file, the hit-set file and {track key: planes, hits by plane}."""
    events, hit_sets = [], []
    for ordinal, case in enumerate(STRAIGHT_TRACKS):
        hits = straight_hits(case)
        events.append(hits)
        hit_sets.append((case[0], ordinal, case[6], list(range(len(hits)))))
    data_file = folder / "straight.t07data"
    data_file.write_bytes(fixture_files.encode_data_file(SIGMA_MM, events))
    hit_sets_file = folder / "straight.hitsets"
    hit_sets_file.write_text(fixture_files.hit_sets_text(fixture_files.file_sha256(data_file), hit_sets), encoding="utf-8")
    return data_file, hit_sets_file


@unittest.skipUnless(BUILT, NOT_BUILT)
class BuiltDriver(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)

    def refit(self, data_file, hit_sets_file, field="0", product="out.product") -> subprocess.CompletedProcess:
        return run_driver("refit", "--data-file", str(data_file), "--hit-sets", str(hit_sets_file), "--field-tesla", field, "--product-id", "straight.line",
                          "--product-file", str(self.work / product))

    def test_self_test_passes(self):
        finished = run_driver("self-test", "--work-dir", str(self.work))
        self.assertEqual(finished.returncode, 0, finished.stdout + finished.stderr)
        self.assertIn("ALL PASS", finished.stdout)
        self.assertNotIn("FAIL ", finished.stdout)

    def test_self_test_shows_the_helix_numbers_within_tolerances_fixed_here(self):
        """The tolerances are the self-test's, derived there from the propagator's accuracy; a pass must show its numbers."""
        stdout = run_driver("self-test", "--work-dir", str(self.work)).stdout
        on_helix = re.search(r"^PASS every crossing is on the helix: worst u (\S+) mm, worst v (\S+) mm, tolerance (\S+) mm$", stdout, re.M)
        self.assertIsNotNone(on_helix, stdout)
        self.assertEqual(float(on_helix.group(3)), HELIX_TOLERANCE_MM)
        self.assertLess(max(float(on_helix.group(1)), float(on_helix.group(2))), HELIX_TOLERANCE_MM)
        along_v = re.search(r"^PASS the momentum along v is conserved: worst change (\S+) of p, tolerance (\S+) of p$", stdout, re.M)
        self.assertIsNotNone(along_v, stdout)
        self.assertEqual(float(along_v.group(2)), MOMENTUM_ALONG_V_TOLERANCE)
        self.assertLess(float(along_v.group(1)), MOMENTUM_ALONG_V_TOLERANCE)
        self.assertRegex(stdout, r"(?m)^PASS the comparison sees a reversed field: smallest miss \S+ mm$")
        self.assertRegex(stdout, r"(?m)^PASS opposite charges split in v by path: measured \S+ mm, helix \S+ mm$")
        self.assertRegex(stdout, r"(?m)^PASS both charges cross eight planes in order$")

    def test_a_truth_file_is_refused_by_name_and_by_content(self):
        data_file, hit_sets_file = straight_line_files(self.work)
        by_name = self.work / "straight.t07truth"
        shutil.copy(data_file, by_name)
        finished = self.refit(by_name, hit_sets_file)
        self.assertEqual(finished.returncode, 2, finished.stderr)
        self.assertIn("never opens truth", finished.stderr)
        by_content = self.work / "disguised.t07data"
        by_content.write_bytes(truth_files.TRUTH_MAGIC + data_file.read_bytes()[8:])
        self.assertEqual(self.refit(by_content, hit_sets_file).returncode, 2)

    def test_one_defect_in_the_inputs_is_refused(self):
        data_file, hit_sets_file = straight_line_files(self.work)
        honest = hit_sets_file.read_text(encoding="utf-8")
        last_line = honest.strip().splitlines()[-1]
        fields = last_line.split(" ")
        two_on_a_plane = " ".join(fields[:5] + ["1"] * (len(fields) - 5))
        unknown_hit = " ".join(fields[:-1] + ["999"])
        defects = {"other data file": honest.replace("data_sha256 ", "data_sha256 0"),
                   "two hits on a plane": honest.replace(last_line, two_on_a_plane),
                   "unknown hit": honest.replace(last_line, unknown_hit),
                   "unknown event": honest.replace(last_line, " ".join(fields[:2] + ["99"] + fields[3:])),
                   "repeated track key": honest + last_line + "\n",
                   "unknown record": honest + "seed 1\n",
                   "another role": honest.replace("role truth-assisted", "role finding"),
                   "q/p of zero": honest.replace(last_line, " ".join(fields[:3] + ["0.0"] + fields[4:]))}
        for name, text in defects.items():
            with self.subTest(defect=name):
                hit_sets_file.write_text(text, encoding="utf-8")
                finished = self.refit(data_file, hit_sets_file, product="defect.product")
                self.assertEqual(finished.returncode, 2, finished.stdout + finished.stderr)
                self.assertFalse((self.work / "defect.product").exists())

    def test_a_truth_path_is_refused_as_any_input(self):
        data_file, hit_sets_file = straight_line_files(self.work)
        as_hit_sets = self.work / "sets.t07truth"
        shutil.copy(hit_sets_file, as_hit_sets)  # an honest hit-set file: only the path check can refuse it
        finished = self.refit(data_file, as_hit_sets)
        self.assertEqual(finished.returncode, 2, finished.stderr)
        self.assertIn("never opens truth", finished.stderr)
        self.assertEqual(self.refit(data_file, hit_sets_file).returncode, 0)
        as_product = self.work / "out.t07truth"
        shutil.copy(self.work / "out.product", as_product)
        finished = run_driver("rewrite-product", "--product-in", str(as_product), "--product-file", str(self.work / "again.product"))
        self.assertEqual(finished.returncode, 2, finished.stderr)
        self.assertIn("never opens truth", finished.stderr)

    def test_a_corrupt_hit_count_is_refused_without_an_allocation(self):
        data_file, hit_sets_file = straight_line_files(self.work)
        raw = bytearray(data_file.read_bytes())
        raw[fixture_files.DATA_HEADER.itemsize:fixture_files.DATA_HEADER.itemsize + 4] = b"\xff\xff\xff\xff"
        data_file.write_bytes(raw)
        text = re.sub(r"data_sha256 \S+", f"data_sha256 {fixture_files.file_sha256(data_file)}", hit_sets_file.read_text(encoding="utf-8"))
        hit_sets_file.write_text(text, encoding="utf-8")
        finished = self.refit(data_file, hit_sets_file)
        self.assertEqual(finished.returncode, 2, finished.stderr)
        self.assertIn("ends inside the hits", finished.stderr)

    def test_an_unknown_flag_and_an_overwritten_input_are_refused(self):
        data_file, hit_sets_file = straight_line_files(self.work)
        unknown = run_driver("refit", "--data-file", str(data_file), "--hit-sets", str(hit_sets_file), "--field-tesla", "0", "--product-id", "straight.line",
                             "--product-file", str(self.work / "p"), "--field-tesls", "1")
        self.assertEqual(unknown.returncode, 2, unknown.stderr)
        overwrite = run_driver("refit", "--data-file", str(data_file), "--hit-sets", str(hit_sets_file), "--field-tesla", "0", "--product-id", "straight.line",
                               "--product-file", str(data_file))
        self.assertEqual(overwrite.returncode, 2, overwrite.stderr)

    def test_the_driver_binary_holds_no_seed_stream(self):
        self.assertNotIn(b"EventSeedStream", DRIVER.read_bytes())
        self.assertNotIn(b"event_seed_digest", DRIVER.read_bytes())
        self.assertIn(b"EventSeedStream", GENERATOR.read_bytes())  # the search can find it where it is

    def test_a_field_past_double_range_is_invalid_input(self):
        data_file, hit_sets_file = straight_line_files(self.work)
        self.assertEqual(self.refit(data_file, hit_sets_file, field="1e999").returncode, 2)

    def test_only_the_fixture_field_opens(self):
        """kalman_refit.hpp: the prior on q/p is settled for section 4.1's 1 T. A weaker field would make it a constraint."""
        data_file, hit_sets_file = straight_line_files(self.work)
        for field in ("0.01", "2", "-1"):
            with self.subTest(field=field):
                self.assertEqual(self.refit(data_file, hit_sets_file, field=field).returncode, 2)
        self.assertEqual(self.refit(data_file, hit_sets_file, field="1").returncode, 0)

    def test_the_driver_and_python_write_the_same_bytes(self):
        data_file, hit_sets_file = straight_line_files(self.work)
        self.assertEqual(self.refit(data_file, hit_sets_file).returncode, 0)
        text = (self.work / "out.product").read_text(encoding="utf-8")
        self.assertEqual(native_product.format_product(native_product.parse_product(text)), text)
        finished = run_driver("rewrite-product", "--product-in", str(self.work / "out.product"), "--product-file", str(self.work / "again.product"))
        self.assertEqual(finished.returncode, 0, finished.stderr)
        self.assertEqual((self.work / "again.product").read_text(encoding="utf-8"), text)
        (self.work / "cut.product").write_text(text[:-20], encoding="utf-8")
        cut = run_driver("rewrite-product", "--product-in", str(self.work / "cut.product"), "--product-file", str(self.work / "never.product"))
        self.assertNotEqual(cut.returncode, 0)


@unittest.skipUnless(BUILT, NOT_BUILT)
class StraightLineCase(unittest.TestCase):
    """Known straight tracks through the telescope at zero field, fitted through the driver, against the closed form above."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        work = Path(cls.folder.name)
        data_file, hit_sets_file = straight_line_files(work)
        product_file = work / "straight.product"
        finished = run_driver("refit", "--data-file", str(data_file), "--hit-sets", str(hit_sets_file), "--field-tesla", "0", "--product-id", "straight.line",
                              "--product-file", str(product_file))
        if finished.returncode != 0:
            raise AssertionError(finished.stdout + finished.stderr)
        cls.document = native_product.parse_product(product_file.read_text(encoding="utf-8"))
        cls.states = {(state["track_key"], state["plane"]): state for state in cls.document["states"]}
        cls.parameters = {(item["track_key"], item["state_index"], item["state_type"]): item for item in cls.document["parameters"]}
        kept = os.environ.get("HEP_ACTS_TRACKING_EVIDENCE")
        if kept:
            shutil.copy(product_file, Path(kept) / "straight-line.product")

    def state_of(self, track_key: str, plane: int, state_type: str) -> dict:
        return self.parameters[(track_key, self.states[(track_key, plane)]["index"], state_type)]

    def fitted_views(self, hits) -> tuple:
        z_values = [PLANE_Z_MM[plane - 1] for plane, _, _ in hits]
        return z_values, least_squares_line(z_values, [hit[1] for hit in hits]), least_squares_line(z_values, [hit[2] for hit in hits])

    def assert_on_line(self, record: dict, plane_z: float, u_line: tuple, v_line: tuple, label: str) -> None:
        values = record["parameters"]
        expected_phi, expected_theta = angles_of(u_line[1], v_line[1])
        self.assertAlmostEqual(values[0], u_line[0] + u_line[1] * plane_z, delta=LOC_TOLERANCE_MM, msg=label)
        self.assertAlmostEqual(values[1], v_line[0] + v_line[1] * plane_z, delta=LOC_TOLERANCE_MM, msg=label)
        self.assertAlmostEqual(values[2], expected_phi, delta=ANGLE_TOLERANCE_RAD, msg=label)
        self.assertAlmostEqual(values[3], expected_theta, delta=ANGLE_TOLERANCE_RAD, msg=label)

    def test_every_track_is_fitted_and_none_is_finding(self):
        self.assertEqual(len(self.document["tracks"]), len(STRAIGHT_TRACKS))
        self.assertEqual([track["status"] for track in self.document["tracks"]], ["fitted"] * len(STRAIGHT_TRACKS))
        summary = native_product.fit_summary(self.document)
        self.assertEqual((summary["evidence_class"], summary["stage"], summary["reported_as_finding"]), ("truth-assisted", "refit-known-hit-set", False))

    def test_measurements_and_holes_are_counted(self):
        for track, case in zip(self.document["tracks"], STRAIGHT_TRACKS):
            with self.subTest(track=case[0]):
                self.assertEqual((track["measurements"], track["measured_coordinates"]), (len(case[7]), 2 * len(case[7])))
                self.assertEqual(track["holes"], 8 - len(case[7]))
        self.assertEqual(self.states[("hole-at-plane-4", 4)]["kind"], "hole")

    def test_smoothed_states_are_the_line_of_all_hits(self):
        for case in STRAIGHT_TRACKS:
            _, u_line, v_line = self.fitted_views(straight_hits(case))
            for plane in case[7]:
                with self.subTest(track=case[0], plane=plane):
                    self.assert_on_line(self.state_of(case[0], plane, "smoothed"), PLANE_Z_MM[plane - 1], u_line, v_line, "smoothed")

    def test_filtered_states_are_the_line_of_the_hits_so_far(self):
        for case in STRAIGHT_TRACKS:
            hits = straight_hits(case)
            for count in range(2, len(hits) + 1):
                _, u_line, v_line = self.fitted_views(hits[:count])
                plane = hits[count - 1][0]
                with self.subTest(track=case[0], plane=plane):
                    self.assert_on_line(self.state_of(case[0], plane, "filtered"), PLANE_Z_MM[plane - 1], u_line, v_line, "filtered")

    def test_predicted_states_are_that_line_before_the_next_hit(self):
        for case in STRAIGHT_TRACKS:
            hits = straight_hits(case)
            for count in range(2, len(hits)):
                _, u_line, v_line = self.fitted_views(hits[:count])
                plane = hits[count][0]
                with self.subTest(track=case[0], plane=plane):
                    self.assert_on_line(self.state_of(case[0], plane, "predicted"), PLANE_Z_MM[plane - 1], u_line, v_line, "predicted")

    def test_the_three_state_types_differ_where_the_hits_say_they_must(self):
        first = {name: self.state_of("mixed", 1, name)["parameters"][0] for name in native_product.STATE_TYPES}
        self.assertGreater(abs(first["filtered"] - first["smoothed"]), 10 * LOC_TOLERANCE_MM)
        last = {name: self.state_of("mixed", 8, name)["parameters"][0] for name in native_product.STATE_TYPES}
        self.assertGreater(abs(last["predicted"] - last["filtered"]), 10 * LOC_TOLERANCE_MM)
        self.assertEqual(last["filtered"], last["smoothed"])

    def test_smoothed_covariance_is_the_closed_form(self):
        indices = [0, 1, 2, 3]
        for case in STRAIGHT_TRACKS:
            hits = straight_hits(case)
            z_values, u_line, v_line = self.fitted_views(hits)
            for plane in (case[7][0], case[7][-1]):
                expected = bound_covariance(z_values, PLANE_Z_MM[plane - 1], u_line[1], v_line[1])
                found = self.state_of(case[0], plane, "smoothed")["covariance"]
                for row in indices:
                    for column in indices[row:]:
                        with self.subTest(track=case[0], plane=plane, row=row, column=column):
                            scale = math.sqrt(expected[row, row] * expected[column, column])
                            self.assertAlmostEqual(found[upper_index(row, column)], expected[row, column], delta=COVARIANCE_RELATIVE_TOLERANCE * scale)

    def test_chi2_is_the_chi2_of_the_line(self):
        for track, case in zip(self.document["tracks"], STRAIGHT_TRACKS):
            _, u_line, v_line = self.fitted_views(straight_hits(case))
            expected = u_line[2] + v_line[2]
            with self.subTest(track=case[0]):
                self.assertAlmostEqual(track["chi2"], expected, delta=CHI2_ABSOLUTE_TOLERANCE + CHI2_RELATIVE_TOLERANCE * expected)

    def test_q_over_p_stays_the_assumption_and_the_product_says_so(self):
        """Unidentifiable quantity reported with precision is a critical false success (t04-prereg.md)."""
        self.assertEqual(self.document["header"]["qop_status"], "assumed-not-measured")
        for case in STRAIGHT_TRACKS:
            record = self.state_of(case[0], case[7][-1], "smoothed")
            prior_variance = PRIOR_QOP_SIGMA_PER_GEV ** 2
            with self.subTest(track=case[0]):
                self.assertAlmostEqual(record["parameters"][4], case[6], delta=1e-6 * abs(case[6]))
                self.assertAlmostEqual(record["covariance"][upper_index(4, 4)], prior_variance, delta=COVARIANCE_RELATIVE_TOLERANCE * prior_variance)

    def test_measurements_stay_apart_from_states_and_keep_their_covariance(self):
        for case in STRAIGHT_TRACKS:
            for plane, loc0, loc1 in straight_hits(case):
                state = self.states[(case[0], plane)]
                with self.subTest(track=case[0], plane=plane):
                    self.assertEqual((state["loc0_mm"], state["loc1_mm"]), (loc0, loc1))
                    self.assertEqual(state["covariance"], [SIGMA_MM ** 2, 0.0, SIGMA_MM ** 2])

    def test_the_product_maps_to_reconstruction_product(self):
        tracks, states = native_product.sidecars_for_product(self.document, "straight.product")
        measurements = native_product.measurement_sidecar(self.document, "straight.t07data")
        for sidecar in (tracks, states, measurements):
            report = read_sidecar(sidecar)
            self.assertTrue(report.ok, [finding.as_dict() for finding in report.errors])
        report = check_products([tracks, states, measurements])
        self.assertTrue(report.ok, [finding.as_dict() for finding in report.errors])


@unittest.skipUnless(BUILT, NOT_BUILT)
class BuiltGenerator(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)

    def generate(self, fixture="noise", block="6", stratum="1", first_event="0", count="3", truth_name="events.t07truth") -> subprocess.CompletedProcess:
        return subprocess.run([str(GENERATOR), "generate", "--fixture", fixture, "--block", block, "--stratum", stratum, "--first-event", first_event, "--count", count,
                               "--data-file", str(self.work / "events.t07data"), "--truth-file", str(self.work / truth_name)], capture_output=True, text=True, timeout=300)

    def test_events_obey_the_fixture_text(self):
        for fixture, stratum in (("clean", "0"), ("noise", "1"), ("noise", "11")):
            with self.subTest(fixture=fixture, stratum=stratum):
                finished = self.generate(fixture=fixture, stratum=stratum)
                self.assertEqual(finished.returncode, 0, finished.stderr)
                truth_events = list(truth_files.iter_truth_events(self.work / "events.t07truth"))
                data_events = list(fixture_files.iter_data_events(self.work / "events.t07data"))
                self.assertEqual(len(truth_events), 3)
                for truth, data_event in zip(truth_events, data_events):
                    self.assertEqual(generator_check.event_defects(truth, data_event["hits"], fixture, int(stratum)), [])

    def test_the_two_files_have_their_roles_and_truth_stays_in_one(self):
        self.assertEqual(self.generate().returncode, 0)
        truth_header = truth_files.read_truth_header(self.work / "events.t07truth")
        self.assertEqual(truth_header["role"], "truth")
        self.assertEqual(truth_header["data_sha256"], fixture_files.file_sha256(self.work / "events.t07data"))
        self.assertEqual(fixture_files.read_data_header(self.work / "events.t07data")["role"], "reconstruction-input")
        self.assertEqual(fixture_files.data_file_defects(self.work / "events.t07data"), [])

    def test_the_review_attack_fails_on_a_real_data_file_and_would_have_worked(self):
        """From the data file alone the attack finds no seed. From the truth side, the same seed does give truth, bit for bit."""
        self.assertEqual(self.generate(fixture="clean", stratum="1", count="10").returncode, 0)
        self.assertEqual(seed_attack((self.work / "events.t07data").read_bytes()), [])
        truth = next(truth_files.iter_truth_events(self.work / "events.t07truth"))
        first_draw = generator_check.stream_raw_draws(truth["event_digest"], 1)[0]
        vertex_u = -0.05 + (0.05 - -0.05) * ((first_draw >> 11) * 2.0 ** -53)
        self.assertEqual(vertex_u, float(truth["vertices"]["u_mm"][0]))

    def test_file_order_does_not_follow_event_index(self):
        """Without the four integers only: sha256 of them gives this order back, under the accepted limit of t07_data_file.hpp."""
        self.assertEqual(self.generate(fixture="clean", stratum="0", count="200").returncode, 0)
        events = list(truth_files.iter_truth_events(self.work / "events.t07truth"))
        digests = [event["event_digest"] for event in events]
        self.assertEqual(digests, sorted(digests))
        indices = [int(event["event_index"]) for event in events]
        self.assertEqual(sorted(indices), list(range(200)))
        near_by_position = sum(1 for position, index in enumerate(indices) if position % 5 == 0 and index % 5 == 0)
        self.assertLess(near_by_position, 30)  # 8 expected by chance; 40 if position kept the near rule

    def test_on_a_real_mixed_file_nothing_low_level_separates_noise_from_track(self):
        """Labels from the truth side score what the data side shows. Stratum 2 at 20 events: 160,000 noise and 5,600 track hits."""
        self.assertEqual(self.generate(fixture="noise", stratum="2", count="20").returncode, 0)
        noise_hits, track_hits, interleaved = [], [], 0
        for data_event, truth in zip(fixture_files.iter_data_events(self.work / "events.t07data"), truth_files.iter_truth_events(self.work / "events.t07truth"), strict=True):
            hits = data_event["hits"]
            keys = truth["tracks"]["hit_keys"]
            is_track = numpy.zeros(len(hits), bool)
            is_track[keys[keys != truth_files.NO_HIT_KEY].astype(numpy.int64)] = True
            positions = numpy.stack([hits["loc0_mm"], hits["loc1_mm"]], axis=1)
            noise_hits.append(positions[~is_track])
            track_hits.append(positions[is_track])
            interleaved += int((is_track[1:] != is_track[:-1]).sum())
        noise, track = numpy.concatenate(noise_hits), numpy.concatenate(track_hits)
        self.assertEqual(int(generator_check.low_bit_attack(numpy.concatenate([noise, track])).sum()), 0)
        with redirect_stdout(io.StringIO()):
            results = generator_check.hit_bit_tests("real file", noise, track)
        self.assertEqual(results, {"low bits": True, "residues": True, "mantissa tail": True})
        self.assertGreaterEqual(decimal_form_p_value(noise[:40000, 0], track[:, 0]), generator_check.ALPHA)
        self.assertGreater(interleaved, track.shape[0])  # track hits lie among the noise, not in a block

    def test_one_bad_argument_is_refused(self):
        self.assertEqual(self.generate(block="7").returncode, 2)
        self.assertEqual(self.generate(stratum="12").returncode, 2)
        self.assertEqual(self.generate(fixture="dirty").returncode, 2)
        self.assertNotEqual(self.generate(truth_name="events.t07data2").returncode, 0)
        self.assertEqual(self.generate(count=str(2 ** 32 + 1)).returncode, 2)
        self.assertEqual(self.generate(block=str(2 ** 32 + 11)).returncode, 2)
        self.assertEqual(self.generate(stratum=str(2 ** 32)).returncode, 2)
        finished = self.generate(count=str(2 ** 64))
        self.assertEqual(finished.returncode, 2, finished.stderr)
        self.assertIn("does not fit 64 bits", finished.stderr)

    def test_one_file_for_both_outputs_is_refused(self):
        path = str(self.work / "both.t07truth")
        finished = subprocess.run([str(GENERATOR), "generate", "--fixture", "clean", "--block", "6", "--stratum", "0", "--first-event", "0", "--count", "1",
                                   "--data-file", path, "--truth-file", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(finished.returncode, 2, finished.stderr)

    def test_an_unknown_flag_is_refused(self):
        finished = subprocess.run([str(GENERATOR), "seed-vector", "--fixture-id", "7001", "--block", "6", "--stratum", "0", "--event-index", "0", "--draws", "1",
                                   "--salt", "1"], capture_output=True, text=True, timeout=60)
        self.assertEqual(finished.returncode, 2, finished.stderr)


@unittest.skipUnless(BUILT, NOT_BUILT)
class BuiltCaiGenerator(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)

    def generate(self, fixture="cai-clean", block="6", stratum="1", first_event="0", count="4", name="events") -> subprocess.CompletedProcess:
        return subprocess.run([str(CAI_GENERATOR), "generate", "--fixture", fixture, "--block", block, "--stratum", stratum, "--first-event", first_event, "--count", count,
                               "--data-file", str(self.work / f"{name}.t07data"), "--truth-file", str(self.work / f"{name}.t07truth")], capture_output=True, text=True, timeout=120)

    def test_events_obey_the_text_and_the_files_keep_their_roles(self):
        for fixture in generator_check.CAI_FIXTURES:
            with self.subTest(fixture=fixture):
                finished = self.generate(fixture=fixture)
                self.assertEqual(finished.returncode, 0, finished.stderr)
                self.assertEqual(generator_check.file_identity_defects(self.work / "events.t07data", self.work / "events.t07truth", fixture, 1, 4), [])
                for truth, data_event in zip(truth_files.iter_truth_events(self.work / "events.t07truth"), fixture_files.iter_data_events(self.work / "events.t07data"), strict=True):
                    self.assertEqual(generator_check.cai_event_defects(truth, data_event["hits"], fixture, 1), [])

    def test_the_data_file_holds_no_seed_and_the_same_grid(self):
        self.assertEqual(self.generate(fixture="cai-sagitta", count="10").returncode, 0)
        self.assertEqual(fixture_files.data_file_defects(self.work / "events.t07data"), [])
        self.assertEqual(seed_attack((self.work / "events.t07data").read_bytes(), fixture_ids=(7003, 7004)), [])

    def test_sha256_alone_does_not_name_a_real_file(self):
        """D1 stage 2 review, C-m1, on the generator's own files, charges read from the data side."""
        for fixture, fixture_id in (("cai-clean", 7003), ("cai-sagitta", 7004)):
            self.assertEqual(self.generate(fixture=fixture, stratum="0", count=str(ATTACK_EVENTS)).returncode, 0)
            charges = [charge_read_from_hits(event["hits"]) for event in fixture_files.iter_data_events(self.work / "events.t07data")]
            self.assertEqual(charges, [int(event["tracks"]["charge"][0]) for event in truth_files.iter_truth_events(self.work / "events.t07truth")])
            matches = {candidate: parity_match(charges, *candidate) for candidate in CAI_CANDIDATES}
            print(f"RECORD parity attack on {fixture}: true candidate {matches[(fixture_id, 6, 0)]:.3f}, all from {min(matches.values()):.3f} to {max(matches.values()):.3f}")
            self.assertLess(max(abs(match - 0.5) for match in matches.values()), 0.15)

    def test_the_two_fixtures_have_their_own_seeds(self):
        self.assertEqual(self.generate(fixture="cai-clean", name="first").returncode, 0)
        self.assertEqual(self.generate(fixture="cai-sagitta", name="second").returncode, 0)
        self.assertNotEqual(fixture_files.file_sha256(self.work / "first.t07data"), fixture_files.file_sha256(self.work / "second.t07data"))

    def test_one_bad_argument_is_refused(self):
        self.assertEqual(self.generate(block="2").returncode, 2)
        self.assertEqual(self.generate(block="11").returncode, 2)
        self.assertEqual(self.generate(stratum="4").returncode, 2)
        self.assertEqual(self.generate(fixture="clean").returncode, 2)
        self.assertEqual(self.generate(count=str(2 ** 32 + 1)).returncode, 2)
        finished = subprocess.run([str(CAI_GENERATOR), "seed-vector", "--fixture-id", "7003"], capture_output=True, text=True, timeout=60)
        self.assertEqual(finished.returncode, 2, finished.stderr)


if __name__ == "__main__":
    unittest.main()
