"""adapters/acts-tracking: why section 7's truth-seeded run loses tracks, read from ACTS's own log (D1 stage 6b brief). A development reading of block 1, tuning, not a gate (K09).

Job 7503215 read the truth-seeded run losing 0.6 % of o3 noise tracks and about 6e-5 of clean ones, more than the finder (D1 stage 6 report, "Results: job 7503215"). Its noise losses
with a missed plane 2 matched a closed form; its losses with every hit kept are not explained, and its records were deleted. This module reads the same block 1 events again:

1. Every stratum (both fixtures, 3,000 events each): the finder, then the truth-seeded run (section 7). Lost particles are found on the scoring side. The truth-seeded run is run again
   on the same files with --trace-file for the lost particles' own starts: all of them on clean and on noise o1, the first 50 by event and particle on noise o2 and o3. Its record must
   equal the first run's byte for byte (the traced CKF has the same configuration and decides the same). For each lost particle it prints ACTS's own VERBOSE lines summarised, every
   branch of its start with hits, owners, chi2 per state and holes, the branch count at each plane, whether a budget or the step limit acted, and how each candidate left.
2. The same events with --reading-start-angle-sigma: NOT section 7, a reading only, for no gate. Its losses are printed beside the closed form.

The truth-seeded records, start files and trace files of every stratum with a loss stay under HEP_ACTS_TRACKING_EVIDENCE/truth-seeded-diagnosis, with the truth files; the data files
too for clean and noise o1 (noise o2 and o3 data files are 175 and 600 MB; the frozen generators remake them). Lines start TS-DIAGNOSIS-. Hypotheses and predictions are in the D1
stage 6b report, fixed before the job. Tests fail only on a traced record that differs from the untraced one, a start asked for and not traced, or a reading record taken as section 7's.
Run from the plugin root: python -m unittest tests.adapters.test_acts_truth_seeded_diagnosis -v
"""
from __future__ import annotations

import concurrent.futures
import math
import os
import re
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import numpy

from tests.adapters import test_acts_finding as finding_tests
from tests.adapters import test_acts_truth_seeded as seeded_tests

finding_record, truth_files, fixture_files = finding_tests.finding_record, finding_tests.truth_files, finding_tests.fixture_files

EVIDENCE_DIR = os.environ.get("HEP_ACTS_TRACKING_EVIDENCE", "")
RUNNABLE = seeded_tests.RUNNABLE and bool(EVIDENCE_DIR)
NOT_RUNNABLE = "needs the T07 build job: HEP_ACTS_TRACKING_BUILD with acts_truth_seeded_run, and HEP_ACTS_TRACKING_EVIDENCE"

TRACE_FORMAT = "acts-tracking-truth-seeded-trace/1"
LABEL = seeded_tests.LABEL
SAMPLE_PER_STRATUM = 50  # noise o2 and o3 (D1 stage 6b brief)
# Not section 7: phi and theta sigma of two hits 50 mm apart, sqrt(2) x 0.020 mm / 50 mm, so the start's direction is as wide as planes 1 and 2 of the track would make it, and its
# plane-2 window about as narrow as a converged track's (D1 stage 6b report). A reading only; it enters no gate and is never the program's default.
READING_ANGLE_SIGMA = math.sqrt(2.0) * 0.020 / 50.0
SECTION_7_ANGLE_SIGMA = 0.01
SECTION_7_LOC_SIGMA_MM = 0.1
SECTION_7_QOP_SHARE = 0.1
HIT_SIGMA_MM = finding_tests.HIT_SIGMA_MM
PLANE_SPACING_MM = 50.0
TURN_PER_GEV_TESLA_MM = 0.299792458e-3
CHI2_CUT = 16.0
NOISE_OF_LEVEL = finding_tests.NOISE_OF_LEVEL
PLANE_AREA_MM2 = finding_tests.PLANE_AREA_MM2
ACTS_LINE_KINDS = {"selected": "Number of selected measurements", "one": "Returning only 1 element", "none": "No measurement candidate", "hole": "Detected hole",
                   "stopped": "has been stopped", "stored": "Storing track", "jump": "Propagation jumps to branch", "navigation-failed": "Navigation initialization failed",
                   "update-failed": "Update step failed", "error": "error "}


# ---- Judges, testable without a build.

def plane_window_variances(angle_sigma: float, q_over_p: float) -> tuple:
    """The variance of the chi2 at plane 2, u and v: the start's predicted variance after the plane-1 update (position from the update of the 0.1 mm prior by a 0.020 mm hit, the
    direction carried 50 mm, and along u the q/p prior, 10 % of |q/p|, turned into a sagitta over 50 mm), plus the hit's own variance, as the CKF's residual covariance
    S = HPH^T + V (track_finding.cpp, WindowedStates). A linear estimate. Correction, stage 6b review m3: the hit variance was left out before the job."""
    position = 1.0 / (1.0 / SECTION_7_LOC_SIGMA_MM ** 2 + 1.0 / HIT_SIGMA_MM ** 2)
    direction = (angle_sigma * PLANE_SPACING_MM) ** 2
    bend = (SECTION_7_QOP_SHARE * TURN_PER_GEV_TESLA_MM * abs(q_over_p) * PLANE_SPACING_MM ** 2 / 2.0) ** 2
    return position + direction + bend + HIT_SIGMA_MM ** 2, position + direction + HIT_SIGMA_MM ** 2


def plane_two_closed_form(truth_events, noise_per_plane: float, angle_sigma: float) -> tuple:
    """Tracks that lost plane 2 alone, and the expected number of them lost: one whose plane-2 window (chi2 < 16) holds another particle's plane-2 crossing is lost, and otherwise one
    with a noise hit in it, Poisson at the plane's density. The rule that read 522, 547, 538 against 530, 537, 550 in job 7503215 (D1 stage 6 report)."""
    density = noise_per_plane / PLANE_AREA_MM2
    count, expected = 0, 0.0
    for truth_event in truth_events:
        tracks = truth_event["tracks"]
        keys, crossings = tracks["hit_keys"], tracks["crossings"]
        for index in range(len(tracks)):
            if tuple(plane + 1 for plane in range(8) if int(keys[index, plane]) == truth_files.NO_HIT_KEY) != (2,):
                continue
            count += 1
            along_u, along_v = plane_window_variances(angle_sigma, float(tracks["q_over_p"][index]))
            others = [other for other in range(len(tracks)) if other != index and int(keys[other, 1]) != truth_files.NO_HIT_KEY]
            distance = (crossings[others, 1, 0] - crossings[index, 1, 0]) ** 2 / along_u + (crossings[others, 1, 1] - crossings[index, 1, 1]) ** 2 / along_v
            area = math.pi * CHI2_CUT * math.sqrt(along_u * along_v)
            expected += 1.0 if bool((distance < CHI2_CUT).any()) else 1.0 - math.exp(-density * area)
    return count, expected


def parse_trace(text: str) -> dict:
    """acts-tracking-truth-seeded-trace/1: the traced searches, {(event, particle): {outcome, result, truncated, extra_branches, log, branches, returned}}, and the ambiguity lines by event."""
    lines = text.split("\n")
    if lines[0] != TRACE_FORMAT or lines[-1] != "":
        raise ValueError(f"not {TRACE_FORMAT}, or not finished")
    body = []
    for line in lines[1:-1]:
        if not line.startswith(LABEL + " "):
            raise ValueError(f"a trace line without its label: {line[:60]}")
        body.append(line[len(LABEL) + 1:])
    searches, ambiguity, position = {}, {}, 0
    while position < len(body):
        tokens = body[position].split(" ")
        if tokens[0] == "end":
            if int(tokens[1]) != len(searches) or position != len(body) - 1:
                raise ValueError("the trace's end record does not count its searches")
            return {"searches": searches, "ambiguity": ambiguity}
        if tokens[0] == "ambiguity":
            count = int(tokens[3])
            ambiguity[int(tokens[1])] = [line[len("log "):] for line in body[position + 1:position + 1 + count]]
            position += 1 + count
            continue
        fields = dict(zip(tokens[0::2], tokens[1::2]))
        log_count, branch_count = int(fields["log_lines"]), int(fields["branch_lines"])
        log = [line[len("log "):] for line in body[position + 1:position + 1 + log_count]]
        branch_lines = [line[len("branch "):] for line in body[position + 1 + log_count:position + 1 + log_count + branch_count]]
        if len(log) != log_count or len(branch_lines) != branch_count:
            raise ValueError("the trace ends inside a search")
        branches, returned = [], []
        for line in branch_lines:
            parts = line.split(" ")
            if parts[0] == "returned":
                returned = [int(part) for part in parts[1:]]
                continue
            states = []
            for item in parts[parts.index("states") + 1:]:
                plane, kind, hit, chi2 = item.split(":")
                states.append((int(plane), kind, None if hit == "-" else int(hit), None if chi2 == "-" else float(chi2)))
            branches.append({"index": int(parts[1]), "measurements": int(parts[3]), "holes": int(parts[5]), "chi2": float(parts[7]), "states": states})
        searches[(int(fields["event"]), int(fields["start"]))] = {"search": int(fields["search"]), "outcome": fields["outcome"], "result": fields["result"],
                                                                  "truncated": fields["truncated"] == "1", "step_limit": fields["step_limit"] == "1",
                                                                  "extra_branches": int(fields["extra_branches"]), "log": log,
                                                                  "branches": branches, "returned": returned}
        position += 1 + log_count + branch_count
    raise ValueError("the trace ends before its end record")


def log_counts(log) -> Counter:
    return Counter(kind for line in log for kind, words in ACTS_LINE_KINDS.items() if words in line)


def branch_count_by_plane(branches) -> dict:
    """How many of the start's branches hold a state on each plane: the forks the CKF made, read from the container."""
    return {plane: sum(any(state[0] == plane for state in branch["states"]) for branch in branches) for plane in range(1, 9)}


def hypotheses_of(search: dict, own_hits: dict) -> dict:
    """The stage 6b hypotheses, for one lost particle's own start. own_hits: plane -> the particle's hit key.
    split-plane-2: its branches hold two or more different plane-2 measurements. budget: a branch budget or the step limit acted. error: ACTS returned an error for the search.
    own-branch: a branch holds the particle's own hit on every plane it reached, and where it ended (its last state's plane and kind, and its holes)."""
    plane_two = {state[2] for branch in search["branches"] for state in branch["states"] if state[0] == 2 and state[1] == "m"}
    own_branches = [branch for branch in search["branches"] if branch["states"]
                    and all(state[1] != "m" or own_hits.get(state[0]) == state[2] for state in branch["states"]) and any(state[1] == "m" for state in branch["states"])]
    longest = max(own_branches, key=lambda branch: (branch["measurements"], -branch["holes"]), default=None)
    return {"split-plane-2": len(plane_two) >= 2, "budget": search["truncated"] or search["step_limit"] or search["outcome"] == "step-limit", "error": search["result"] != "ok",
            "own-branch": None if longest is None else {"measurements": longest["measurements"], "holes": longest["holes"], "last": longest["states"][-1][:2],
                                                        "returned": longest["index"] in search["returned"]}}


def branch_text(branch: dict, owner_of_hit: dict) -> str:
    states = " ".join(f"p{plane}:{kind}" + ("" if hit is None else f":{hit}({owner_of_hit.get(hit, 'noise')}):{chi2:.2f}") for plane, kind, hit, chi2 in branch["states"])
    return f"branch {branch['index']} measurements {branch['measurements']} holes {branch['holes']} chi2 {branch['chi2']:.3f} [{states}]"


# ---- The run.

def lost_particles(seeded: dict, truth_events) -> list:
    """(event, particle, missed planes, category) of every reconstructable particle with no primary in the truth-seeded run, by event then particle."""
    lost = []
    for ordinal, (event, truth_event) in enumerate(zip(seeded["events"], truth_events)):
        particles = finding_tests.particles_of(truth_event)
        scores = finding_tests.scored_event(finding_tests.tracks_of(event), particles)
        for index in sorted(scores["lost"]):
            lost.append((ordinal, index, finding_tests.missed_planes_of(truth_event["tracks"][index]), finding_tests.loss_category(particles[index], event)))
    return lost


def run_seeded(data_file: Path, start_file: Path, name: str, folder: Path, extra=()) -> tuple:
    record, product = folder / f"{name}.record", folder / f"{name}.product"
    finished = finding_tests.run_program([seeded_tests.TRUTH_SEEDED_RUN, "--data-file", data_file, "--start-file", start_file, "--product-id", name, "--product-file", product,
                                          "--record-file", record, "--product-events", 0, *extra])
    product.unlink()
    return record, finished


def stratum_diagnosis(fixture: str, stratum: int, folder: Path, kept: Path) -> dict:
    level = stratum % 3
    label = f"{fixture} stratum {stratum}"
    data_file, truth_file = finding_tests.generate(folder, fixture, stratum, finding_tests.EVENTS_PER_BIN)
    _, finder_record_file, finder_product_file = finding_tests.find(folder, data_file, f"ts-diagnosis-find-{fixture}-{stratum}", 0)
    finder_product_file.unlink()
    truth_events = list(truth_files.iter_truth_events(truth_file))
    start_file = folder / f"truth-seeded-{fixture}-{stratum}.t07starts"
    start_file.write_text(seeded_tests.start_file_text(truth_events, seeded_tests.file_sha256(data_file)), encoding="utf-8")
    name = f"truth-seeded-{fixture}-{stratum}"
    record_file, first = run_seeded(data_file, start_file, name, folder)
    record_text = record_file.read_text(encoding="utf-8")
    seeded = seeded_tests.parse_truth_seeded_record(record_text)
    finder = finding_record.parse_record(finder_record_file.read_text(encoding="utf-8"))
    lost = lost_particles(seeded, truth_events)
    traced = lost if fixture == "clean" or level == 0 else lost[:SAMPLE_PER_STRATUM]
    reading = {"traced": len(traced), "lost": len(lost), "rerun_equal": None, "traced_found": None, "lines": []}
    if traced:
        trace_file = folder / f"{name}.trace"
        rerun_file, _ = run_seeded(data_file, start_file, f"{name}-traced", folder,
                                   ("--trace-file", trace_file, "--trace-starts", ",".join(f"{ordinal}:{particle}" for ordinal, particle, _, _ in traced)))
        reading["rerun_equal"] = rerun_file.read_text(encoding="utf-8") == record_text.replace(f"product_id {name}\n", f"product_id {name}-traced\n", 1)
        rerun_file.unlink()
        trace = parse_trace(trace_file.read_text(encoding="utf-8"))
        reading["traced_found"] = set(trace["searches"]) == {(ordinal, particle) for ordinal, particle, _, _ in traced}
        tally = Counter()
        for ordinal, particle, missed, category in traced:
            search = trace["searches"].get((ordinal, particle))
            if search is None:
                continue
            truth_event = truth_events[ordinal]
            particles = finding_tests.particles_of(truth_event)
            owner_of_hit = {key: index for index, item in enumerate(particles) for key in item["hit_keys"]}
            own_hits = {plane + 1: int(key) for plane, key in enumerate(truth_event["tracks"]["hit_keys"][particle]) if int(key) != truth_files.NO_HIT_KEY}
            hypotheses = hypotheses_of(search, own_hits)
            kind = "all-kept" if not missed else "missed " + "-".join(map(str, missed))
            tally.update(f"{kind} {name_} {value}" for name_, value in hypotheses.items() if name_ != "own-branch")
            own = hypotheses["own-branch"]
            tally[f"{kind} own-branch {'none' if own is None else ('returned' if own['returned'] else 'dropped') + ' ending p' + str(own['last'][0]) + ':' + own['last'][1]}"] += 1
            event = seeded["events"][ordinal]
            start = next(item for item in event["starts"] if item["particle"] == particle)
            left = [f"{item['key']} {item['outcome']} {item['failure_category']}" for item in event["found"][start["first_candidate"]:start["first_candidate"] + start["candidates"]]]
            reading["lines"].append(f"TS-DIAGNOSIS-LOST {label} event {ordinal} particle {particle} {kind} category {category} start {start['outcome']} result {search['result']} "
                                    f"truncated {int(search['truncated'])} step_limit {int(search['step_limit'])} extra_branches {search['extra_branches']} branches {len(search['branches'])} returned {search['returned']} "
                                    f"candidates {start['candidates']} short_branches {start['short_branches']} hypotheses {hypotheses} branch_count_by_plane "
                                    f"{branch_count_by_plane(search['branches'])} acts_lines {dict(log_counts(search['log']))} candidates_left {left}")
            for branch in search["branches"]:
                reading["lines"].append(f"TS-DIAGNOSIS-BRANCH {label} event {ordinal} particle {particle} {branch_text(branch, owner_of_hit)}")
            removals = [line for line in trace["ambiguity"].get(ordinal, []) if "remove track" in line]
            reading["lines"].append(f"TS-DIAGNOSIS-AMBIGUITY {label} event {ordinal} removals {len(removals)}; of this start's candidates: "
                                    + "; ".join(line.split("VERBOSE")[-1].strip() for line in removals
                                                if int(re.search(r"remove track (\d+)", line).group(1)) in range(start["first_candidate"], start["first_candidate"] + start["candidates"])))
        reading["tally"] = tally
    # Item 2: the reading variant, not section 7.
    variant_file, _ = run_seeded(data_file, start_file, f"{name}-reading-only", folder, ("--reading-start-angle-sigma", repr(READING_ANGLE_SIGMA)))
    variant_text = variant_file.read_text(encoding="utf-8")
    try:
        seeded_tests.parse_truth_seeded_record(variant_text)
        reading["variant_refused_as_section_7"] = False
    except seeded_tests.TruthSeededFormatError:
        reading["variant_refused_as_section_7"] = True
    variant = seeded_tests.parse_truth_seeded_record(variant_text, reading=True)
    reading["variant_configuration_differs"] = sorted(key for key, value in variant["configuration"].items() if seeded["configuration"][key] != value)
    variant_lost = lost_particles(variant, truth_events)
    per_event = {"finder": [], "variant": [], "reconstructable": []}
    for event, variant_event, truth_event in zip(finder["events"], variant["events"], truth_events):
        particles = finding_tests.particles_of(truth_event)
        finder_scores = finding_tests.scored_event(finding_tests.tracks_of(event), particles)
        per_event["finder"].append(finder_scores["with_primary"])
        per_event["variant"].append(finding_tests.scored_event(finding_tests.tracks_of(variant_event), particles)["with_primary"])
        per_event["reconstructable"].append(finder_scores["reconstructable"])
    difference, bound, _ = seeded_tests.paired_difference(per_event["finder"], per_event["variant"], per_event["reconstructable"], (finding_tests.FIXTURE_IDS[fixture], finding_tests.TUNING_BLOCK, stratum))
    noise = NOISE_OF_LEVEL[level] if fixture == "noise" else 0.0
    plane_two = {angle: plane_two_closed_form(truth_events, noise, angle) for angle in (SECTION_7_ANGLE_SIGMA, READING_ANGLE_SIGMA)}
    reading.update(label=label, fixture=fixture, stratum=stratum, level=level, events=len(seeded["events"]), stderr=len(first.stderr), lost_classes=Counter((missed, category) for _, _, missed, category in lost),
                   variant_lost=len(variant_lost), variant_classes=Counter((missed, category) for _, _, missed, category in variant_lost), variant_difference=difference, variant_bound=bound,
                   plane_two=plane_two, reconstructable=sum(per_event["reconstructable"]))
    keep = lost or variant_lost
    if keep:
        for path in (record_file, start_file, truth_file, folder / f"{name}.trace", variant_file) + ((data_file,) if fixture == "clean" or level == 0 else ()):
            if path.exists():
                shutil.move(str(path), str(kept / path.name))
    for path in (data_file, truth_file, start_file, record_file, finder_record_file, variant_file, folder / f"{name}.trace"):
        if path.exists():
            path.unlink()
    return reading


def print_stratum(item: dict) -> None:
    label = item["label"]
    print(f"TS-DIAGNOSIS-STRATUM {label}: lost {item['lost']} traced {item['traced']} traced record equal to the untraced {item['rerun_equal']} every asked start traced {item['traced_found']}",
          flush=True)
    print(f"TS-DIAGNOSIS-CLASSES {label} section 7: {dict(sorted(item['lost_classes'].items(), key=str))}", flush=True)
    for line in item["lines"]:
        print(line, flush=True)
    if item.get("tally"):
        print(f"TS-DIAGNOSIS-HYPOTHESES {label} traced lost particles: {dict(sorted(item['tally'].items()))}", flush=True)
    (count_7, expected_7), (count_r, expected_r) = item["plane_two"][SECTION_7_ANGLE_SIGMA], item["plane_two"][READING_ANGLE_SIGMA]
    read_7 = sum(value for (missed, _), value in item["lost_classes"].items() if missed == (2,))
    read_r = sum(value for (missed, _), value in item["variant_classes"].items() if missed == (2,))
    print(f"TS-DIAGNOSIS-CLOSED-FORM {label} tracks missing plane 2 alone {count_7}: section 7 expected {expected_7:.1f} read {read_7}; reading-only angle {READING_ANGLE_SIGMA:.4e} "
          f"expected {expected_r:.1f} read {read_r}", flush=True)
    print(f"TS-DIAGNOSIS-READING-ONLY not section 7, a reading only, no gate: {label} angle sigma {READING_ANGLE_SIGMA:.4e} lost {item['variant_lost']} of {item['reconstructable']} "
          f"(section 7 lost {item['lost']}); finder less this variant {item['variant_difference']:+.6f} (d - 1.645 se {item['variant_bound']:+.6f}); "
          f"classes {dict(sorted(item['variant_classes'].items(), key=str))}", flush=True)


@unittest.skipUnless(RUNNABLE, NOT_RUNNABLE)
class TruthSeededLosses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        kept = Path(EVIDENCE_DIR) / "truth-seeded-diagnosis"
        kept.mkdir(parents=True, exist_ok=True)
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        jobs = [(fixture, stratum) for fixture in ("noise", "clean") for stratum in (11, 8, 5, 2, 10, 7, 4, 1, 9, 6, 3, 0)]
        with concurrent.futures.ThreadPoolExecutor(finding_tests.WORKERS) as pool:
            cls.readings = sorted(pool.map(lambda job: stratum_diagnosis(job[0], job[1], Path(cls.folder.name), kept), jobs), key=lambda item: (item["fixture"], item["stratum"]))
        for item in cls.readings:
            print_stratum(item)

    def test_every_stratum_ran_quietly(self):
        self.assertEqual(len(self.readings), 24)
        self.assertEqual({item["events"] for item in self.readings}, {finding_tests.EVENTS_PER_BIN})
        self.assertEqual({item["stderr"] for item in self.readings}, {0})

    def test_tracing_changes_no_decision(self):
        """The traced run's record is the untraced one's byte for byte, but for its product id, and every start asked for was traced."""
        for item in self.readings:
            if item["traced"]:
                with self.subTest(stratum=item["label"]):
                    self.assertTrue(item["rerun_equal"])
                    self.assertTrue(item["traced_found"])

    def test_the_reading_variant_is_never_section_7(self):
        for item in self.readings:
            with self.subTest(stratum=item["label"]):
                self.assertTrue(item["variant_refused_as_section_7"])
                self.assertEqual(item["variant_configuration_differs"], ["truth_start_sigma_phi", "truth_start_sigma_theta"])


class Judges(unittest.TestCase):
    def test_the_window_variances(self):
        along_u, along_v = plane_window_variances(0.01, 0.0)
        self.assertAlmostEqual(along_v, 1.0 / (100.0 + 2500.0) + 0.25 + 0.020 ** 2, places=12)
        self.assertAlmostEqual(along_u, along_v)
        self.assertGreater(plane_window_variances(0.01, 0.6)[0], along_u)
        self.assertAlmostEqual(plane_window_variances(READING_ANGLE_SIGMA, 0.0)[1], 1.0 / 2600.0 + 3 * 0.020 ** 2, places=12)

    def test_the_closed_form_counts_a_crossing_inside_as_certain(self):
        tracks = numpy.zeros(2, dtype=truth_files.TRACK)
        tracks["hit_keys"] = numpy.arange(16).reshape(2, 8)
        tracks["hit_keys"][0, 1] = truth_files.NO_HIT_KEY
        tracks["crossings"][1, 1, :2] = (0.5, 0.0)
        self.assertEqual(plane_two_closed_form([{"tracks": tracks}], 0.0, 0.01), (1, 1.0))
        self.assertEqual(plane_two_closed_form([{"tracks": tracks}], 0.0, READING_ANGLE_SIGMA), (1, 0.0))
        tracks["crossings"][1, 1, :2] = (50.0, 0.0)
        count, expected = plane_two_closed_form([{"tracks": tracks}], 1000.0, 0.01)
        self.assertEqual(count, 1)
        self.assertAlmostEqual(expected, 1.0 - math.exp(-1000.0 / PLANE_AREA_MM2 * math.pi * CHI2_CUT * plane_window_variances(0.01, 0.0)[0]))

    def honest_trace(self) -> str:
        lines = [TRACE_FORMAT, f"{LABEL} event 3 search 1 start 7 outcome no-candidate result ok truncated 0 step_limit 0 extra_branches 1 log_lines 2 branch_lines 3",
                 f"{LABEL} log 12:00:00 Finder VERBOSE Detected hole after measurement selection on surface x", f"{LABEL} log 12:00:00 Finder VERBOSE Branch on surface x has been stopped",
                 f"{LABEL} branch branch 0 measurements 2 holes 3 chi2 1.5 states 1:m:10:0.2 2:m:11:0.3 3:h:-:- 4:h:-:- 5:h:-:-",
                 f"{LABEL} branch branch 1 measurements 2 holes 3 chi2 9.5 states 1:m:10:0.2 2:m:99:8.1 3:h:-:- 4:h:-:- 5:h:-:-", f"{LABEL} branch returned",
                 f"{LABEL} ambiguity 3 lines 1", f"{LABEL} log 12:00:00 Ambiguity VERBOSE maximum shared measurements 0", f"{LABEL} end 1"]
        return "\n".join(lines) + "\n"

    def test_the_trace_reads_and_refuses(self):
        trace = parse_trace(self.honest_trace())
        search = trace["searches"][(3, 7)]
        self.assertEqual((search["outcome"], len(search["branches"]), search["returned"], len(trace["ambiguity"][3])), ("no-candidate", 2, [], 1))
        self.assertEqual(log_counts(search["log"]), Counter(hole=1, stopped=1))
        self.assertEqual(branch_count_by_plane(search["branches"]), {1: 2, 2: 2, 3: 2, 4: 2, 5: 2, 6: 0, 7: 0, 8: 0})
        for broken in (self.honest_trace().replace("log_lines 2", "log_lines 3"), self.honest_trace().replace(f"{LABEL} end 1", f"{LABEL} end 2"),
                       self.honest_trace().replace(f"{LABEL} log 12:00:00 Finder", "log 12:00:00 Finder", 1)):
            with self.subTest(broken=broken[-30:]):
                with self.assertRaises(ValueError):
                    parse_trace(broken)

    def test_the_hypotheses_of_one_start(self):
        search = parse_trace(self.honest_trace())["searches"][(3, 7)]
        hypotheses = hypotheses_of(search, {1: 10, 2: 11, 3: 12, 4: 13, 5: 14, 6: 15, 7: 16, 8: 17})
        self.assertEqual(hypotheses, {"split-plane-2": True, "budget": False, "error": False, "own-branch": {"measurements": 2, "holes": 3, "last": (5, "h"), "returned": False}})
        self.assertFalse(hypotheses_of(dict(search, branches=search["branches"][:1]), {1: 10, 2: 11})["split-plane-2"])
        self.assertTrue(hypotheses_of(dict(search, truncated=True), {})["budget"])
        self.assertIsNone(hypotheses_of(dict(search, branches=search["branches"][1:]), {1: 10, 2: 11})["own-branch"])

    def test_the_reading_angle_is_two_hits_over_one_spacing(self):
        self.assertAlmostEqual(READING_ANGLE_SIGMA, 5.657e-4, places=7)
        self.assertNotEqual(READING_ANGLE_SIGMA, SECTION_7_ANGLE_SIGMA)


if __name__ == "__main__":
    unittest.main()
