"""adapters/acts-tracking: section 7's truth-seeded run of recipe reco.track.acts-ckf-planar/1 and the paired comparison of section 8.2, read on block 1 (D1 stage 6 brief).

Sections cited are of t04-values-v4.md. Scoring side: truth is read here, and goes to the program acts_truth_seeded_run as a start file. Everything printed is a development
reading of block 1, tuning, not a gate result: pass or fail waits for K09 (t07-t09-task-sheets.md, Acceptance), and tuning runs feed nothing (section 2.2). The truth-seeded run is a
comparator only, never reported as finding (section 7; sheet, Acceptance: "a truth-seeded fit is never reported as finding"); every line of its record and its product's stage say
truth-seeded, and the finding readers refuse both (TruthSeededIsNeverFinding).

The rules, quoted, with none added:
- Section 7, "Truth-seeded run": "CKF started from the exact truth state at plane 1, with covariance diag(0.1 mm, 0.1 mm, 0.01, 0.01, 0.1 |q/p|) squared, and no seed finder.
  Comparator only, never reported as finding." Everything after the start is the finder's own code path (track_finding.cpp, TrackFinder::search_resolve_fit), so the CKF settings,
  ambiguity resolution with ambiguity_most_shared_hits 2 and the fit are the recipe's by construction; the record's recipe_configuration_sha256 is the finder's configuration_sha256,
  and test_the_recipe_after_the_start_is_the_finders reads it.
- Section 4.1, Fiducial: "All tracks cross all planes, by construction ... No resampling". So every particle has a truth state at plane 1; the generator stops otherwise
  (t07_event_generator.cpp), and the start file is refused below if a particle had none. Every particle of the truth file is started, in its order; section 7 selects none.
- Section 7, "Track match", "Primary, one-to-one rule" and "Efficiency, tracks": scored_event of tests/adapters/test_acts_finding.py, the same judge for both runs.
- Section 8.2, "Efficiency, noise (a)": "Paired against the truth-seeded run of the same recipe (section 7): lower bound of the difference at least -0.01". Section 5.2, "Paired
  comparisons": "Bootstrap over events of the paired difference, one-sided 95 %, B = 1,000." The difference is the finder's efficiency less the truth-seeded run's, per bin (section
  5.1: 12 bins per fixture, by event stratum). The lower bound is the plan's stated form for a bound from a bootstrap se (coordinator's ruling on stage 6 review m1): the
  estimate less 1.645 se, as section 5.2's test rows bound (e - 1.645 se), with se the event bootstrap of the paired difference, B = 1,000, seeded from the bin's identity (section
  5.1, "se in a gate"): (fixture id, block, stratum). The 5 % percentile of the same replicates is printed beside it, labelled "percentile, reading only". Read on the clean fixture
  too, as a check only: section 8.2 gates the clean efficiency by its own row.
- Every particle is started, non-reconstructable ones too (section 7 selects none). How many starts that is per stratum, how many of their candidates are selected, and how many of
  those are fakes or take a hit from a reconstructable particle the run lost, are printed (TRUTH-SEEDED-NON-RECONSTRUCTABLE; stage 6 review m2).

Development sample: all 12 strata of fixtures 7001 and 7002, block 1, 3,000 events each, as the finding module (section 3.2: block 1, any size within approved jobs). The predictions
are in the D1 stage 6 report, fixed before the job. Tolerances below are fixed before the job and do not move after results (sheet, Stop). The built tests need the build job and skip
without it; that job counts a skip as a failure. Run from the plugin root: python -m unittest tests.adapters.test_acts_truth_seeded -v
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import math
import tempfile
import time
import unittest
from collections import Counter
from pathlib import Path

import numpy

from tests.adapters import test_acts_finding as finding_tests

finding_record, native_product, truth_files, fixture_files = finding_tests.finding_record, finding_tests.native_product, finding_tests.truth_files, finding_tests.fixture_files

TRUTH_SEEDED_RUN = Path(finding_tests.BUILD_DIR) / "acts_truth_seeded_run"
RUNNABLE = finding_tests.BUILT and TRUTH_SEEDED_RUN.is_file()
NOT_RUNNABLE = "HEP_ACTS_TRACKING_BUILD names no built acts_truth_seeded_run: this test needs the T07 build job, which runs it"

LABEL = "truth-seeded"
RECORD_FORMAT = "acts-tracking-truth-seeded-record/2"  # stage 6b: a variant line in the header (review m7)
FIRST_RECORD_FORMAT = "acts-tracking-truth-seeded-record/1"  # job 7503215's: no variant line, section 7's run only
START_FILE_FORMAT = "acts-tracking-truth-starts/1"
STAGE, EVIDENCE_CLASS = "truth-seeded-ckf", "truth-assisted"
# D1 stage 6b: acts_truth_seeded_run --reading-start-angle-sigma, NOT section 7, a reading only, for no gate. Its own stage and variant; parse_truth_seeded_record refuses it unless asked.
READING_STAGE, SECTION_7_VARIANT, READING_VARIANT = "truth-seeded-ckf-reading-only", "section-7", "not-section-7-reading-only"
HEADER_FIELDS = ("recipe", "stage", "evidence_class", "variant", "product_id", "data_sha256", "start_sha256", "product_events", "recipe_configuration_sha256", "configuration_sha256")
START_CONFIGURATION = {"truth_start_plane": "1", "truth_start_sigma_loc0_mm": "0.10000000000000001", "truth_start_sigma_loc1_mm": "0.10000000000000001",
                       "truth_start_sigma_phi": "0.01", "truth_start_sigma_theta": "0.01", "truth_start_sigma_qop_share": "0.10000000000000001", "truth_start_sigma_time": "1"}
PAIRED_LIMIT = -0.01         # section 8.2, Efficiency, noise (a)
BOOTSTRAP_REPLICATES = 1000  # section 5.2, Paired comparisons
ONE_SIDED_LEVEL = 0.95
ONE_SIDED_Z = 1.645          # section 5.2's test rows: e - 1.645 se
PRODUCT_EVENTS = 50
# Tolerances of this module, fixed before the job. A reading outside one is a disagreement with a prediction, for finding the cause, not a gate result.
# Plane 1 is the start surface: ACTS's CKF filters it unless skipPrePropagationUpdate is set (CombinatorialKalmanFilter.hpp), and the start sits 0.02 mm from the hit with 0.1 mm of
# prior, so a primary that left out its own plane-1 hit is a start surface skipped, not chance: at most 1 in 1,000 on clean.
PLANE_ONE_HELD_SHARE = 0.999
# Clean, per stratum: lost tracks the truth-seeded run may have, from the close pairs of o3 (event 2169, D1 stage 5e report); none at o1 and o2.
CLEAN_LOST_LIMIT_OF_LEVEL = (0, 0, 3)
LOST_PRINTED_PER_STRATUM = 40


class TruthSeededFormatError(ValueError):
    """The text is not acts-tracking-truth-seeded-record/1, or a line of it is not labelled truth-seeded."""


# ---- The start file and the record. Judges take text and numbers, so each is tested without a build.

def start_file_text(truth_events, data_sha256: str) -> str:
    """acts-tracking-truth-starts/1: each particle's truth state at plane 1 (section 7), loc0, loc1, phi, theta and q/p, at 17 significant digits, which round-trip a double."""
    lines = [START_FILE_FORMAT, "role truth", f"data_sha256 {data_sha256}", f"events {len(truth_events)}"]
    for ordinal, truth_event in enumerate(truth_events):
        tracks = truth_event["tracks"]
        lines.append(f"event {ordinal} {len(tracks)}")
        for particle, track in enumerate(tracks):
            loc0, loc1, phi, theta = (float(value) for value in track["crossings"][0])
            values = (loc0, loc1, phi, theta, float(track["q_over_p"]))
            if not all(math.isfinite(value) for value in values) or values[4] == 0.0:
                raise TruthSeededFormatError(f"event {ordinal} particle {particle} has no truth state at plane 1")
            lines.append("start " + str(particle) + " " + " ".join("%.17g" % value for value in values))
    lines.append(f"end {len(truth_events)}")
    return "\n".join(lines) + "\n"


def parse_truth_seeded_record(text: str, reading: bool = False) -> dict:
    """The whole record, or TruthSeededFormatError. Every line after the format names itself truth-seeded; the rest reads as a finding record's lines do, plus one start line
    per search, so the scoring is the same function for both. A finding record is refused here, as a truth-seeded record is refused by acts_finding_record.parse_record."""
    lines = text.split("\n")
    if lines[-1] != "" or not lines[:-1] or lines[0] not in (RECORD_FORMAT, FIRST_RECORD_FORMAT):
        raise TruthSeededFormatError(f"not {RECORD_FORMAT} or {FIRST_RECORD_FORMAT}, or not finished")
    fields = HEADER_FIELDS if lines[0] == RECORD_FORMAT else tuple(name for name in HEADER_FIELDS if name != "variant")
    body = []
    for line in lines[1:-1]:
        if not line.startswith(LABEL + " "):
            raise TruthSeededFormatError(f"a line without its label: {line[:60]}")
        body.append(line[len(LABEL) + 1:].split(" "))
    header = {}
    for name, tokens in zip(fields, body):
        if len(tokens) != 2 or tokens[0] != name:
            raise TruthSeededFormatError(f"expected {name}, found {' '.join(tokens)}")
        header[name] = tokens[1]
    if len(header) != len(fields):
        raise TruthSeededFormatError("the record ends inside its header")
    header.setdefault("variant", SECTION_7_VARIANT)  # /1 knew section 7's run only
    expected = (READING_STAGE, READING_VARIANT) if reading else (STAGE, SECTION_7_VARIANT)
    if (header["recipe"], header["stage"], header["evidence_class"], header["variant"]) != (finding_record.FINDING_RECIPE, *expected[:1], EVIDENCE_CLASS, expected[1]):
        raise TruthSeededFormatError("not the truth-seeded run of the finding recipe" + (" in its reading variant" if reading else " as section 7 defines it"))
    configuration, events, counted = {}, [], None
    try:
        for tokens in body[len(fields):]:
            if counted is not None:
                raise TruthSeededFormatError("text after the end record")
            if tokens[0] == "configuration" and len(tokens) == 3 and not events:
                configuration[tokens[1]] = tokens[2]
            elif tokens[0] == "event":
                events.append(dict(finding_record._event(tokens), starts=[]))
            elif tokens[0] == "start" and len(tokens) == 6 and events:
                events[-1]["starts"].append({"particle": int(tokens[1]), "outcome": tokens[2], "first_candidate": int(tokens[3]), "candidates": int(tokens[4]), "short_branches": int(tokens[5])})
            elif tokens[0] == "candidate":
                candidate = finding_record._candidate(tokens)
                if not events or events[-1]["ordinal"] != candidate["ordinal"] or not candidate["seed_planes"].startswith("start-"):
                    raise TruthSeededFormatError(f"{candidate['key']} is not under its event and start")
                events[-1]["found"].append(candidate)
            elif tokens[0] == "end" and len(tokens) == 3:
                counted = [int(token) for token in tokens[1:]]
            else:
                raise TruthSeededFormatError(f"unknown record {tokens[0]}")
    except finding_record.RecordFormatError as error:
        raise TruthSeededFormatError(str(error)) from error
    except (IndexError, ValueError) as error:
        if isinstance(error, TruthSeededFormatError):
            raise
        raise TruthSeededFormatError(str(error)) from error
    if counted != [len(events), sum(len(event["found"]) for event in events)]:
        raise TruthSeededFormatError("the end record is missing or counts other numbers than the record holds")
    if list(configuration) != list(finding_record.CONFIGURATION_KEYS) + list(START_CONFIGURATION):
        raise TruthSeededFormatError("the configuration is not the recipe's, then the start's")
    for event in events:
        defects = finding_record.event_defects(event)
        if event["seeds_skipped"] or len(event["starts"]) != event["seeds_found"]:
            defects.append(f"event {event['ordinal']} skips a start or does not list each")
        if defects:
            raise TruthSeededFormatError(defects[0])
    return {"header": header, "configuration": configuration, "events": events}


def recipe_configuration_hash(configuration: dict) -> str:
    """The finder's configuration_sha256, over the recipe's keys of a truth-seeded record: equal to the finder's when the steps after the start are configured as the finder's."""
    return hashlib.sha256("".join(f"configuration {name} {configuration[name]}\n" for name in finding_record.CONFIGURATION_KEYS).encode()).hexdigest()


def paired_difference(finder_with, seeded_with, reconstructable, entropy) -> tuple:
    """Sections 5.1 and 5.2: per event, the finder's and the truth-seeded run's reconstructable particles with a primary, and the reconstructable count. Returns the efficiency
    difference d (finder less truth-seeded), its one-sided 95 % lower bound d - 1.645 se with se the standard deviation (ddof 1) of B = 1,000 event bootstrap differences seeded from
    entropy, and the 5 % percentile of those replicates, a reading only."""
    finder_with, seeded_with, reconstructable = (numpy.asarray(values, float) for values in (finder_with, seeded_with, reconstructable))
    gained = finder_with - seeded_with
    generator = numpy.random.default_rng(numpy.random.SeedSequence(list(entropy)))
    draws = generator.integers(0, len(reconstructable), size=(BOOTSTRAP_REPLICATES, len(reconstructable)))
    differences = gained[draws].sum(axis=1) / reconstructable[draws].sum(axis=1)
    difference = float(gained.sum() / reconstructable.sum())
    return difference, difference - ONE_SIDED_Z * float(numpy.std(differences, ddof=1)), float(numpy.quantile(differences, 1.0 - ONE_SIDED_LEVEL))


def unreconstructable_starts(event: dict, particles: list, lost) -> Counter:
    """Stage 6 review m2: starts of particles with fewer than section 7's 6 hits, their candidates, those selected, the selected ones that are fakes, and the selected ones holding a
    hit of a reconstructable particle this run lost (one that may have cost it its track)."""
    owner = {key: index for index, particle in enumerate(particles) for key in particle["hit_keys"]}
    short = {index for index, particle in enumerate(particles) if len(particle["hit_keys"]) < finding_tests.LEAST_HITS}
    counts = Counter(starts=sum(start["particle"] in short for start in event["starts"]))
    lost_hits = {key for index in lost for key in particles[index]["hit_keys"]}
    for item in event["found"]:
        if int(item["seed_planes"].split("-", 1)[1]) not in short:
            continue
        counts["candidates"] += 1
        if item["outcome"] != "selected":
            continue
        counts["selected"] += 1
        owners = Counter(owner[key] for key in item["hit_keys"] if key in owner)
        counts["fakes"] += not any(2 * count > len(item["hit_keys"]) for count in owners.values())
        counts["takes_from_lost"] += bool(set(item["hit_keys"]) & lost_hits)
    return counts


def plane_one_held(event: dict, primaries: dict, particles_hits_by_plane) -> tuple:
    """Of the primaries whose particle left a plane-1 hit, how many hold it: the start surface was filtered."""
    selected = [item for item in event["found"] if item["outcome"] == "selected"]
    held = total = 0
    for particle, track_index in primaries.items():
        own = particles_hits_by_plane[particle].get(1)
        if own is not None:
            total += 1
            held += own in selected[track_index]["hit_keys"]
    return held, total


# ---- Judges, without a build.

def honest_truth_seeded_text() -> str:
    record = finding_tests.honest_record()
    event = record["events"][0]
    event.update(seeds_found=2, seeds_run=2, seeds_skipped=0)
    for item in event["found"]:
        item["seed_planes"] = "start-0"
    text = finding_record.format_record(dict(record, configuration={name: "1" for name in finding_record.CONFIGURATION_KEYS}))
    lines = text.split("\n")[:-1]
    configuration = [line for line in lines if line.startswith("configuration ")] + [f"configuration {name} {value}" for name, value in START_CONFIGURATION.items()]
    header = [f"recipe {finding_record.FINDING_RECIPE}", f"stage {STAGE}", f"evidence_class {EVIDENCE_CLASS}", f"variant {SECTION_7_VARIANT}", "product_id one", "data_sha256 " + "a" * 64, "start_sha256 " + "c" * 64,
              "product_events 1", "recipe_configuration_sha256 " + "b" * 64, "configuration_sha256 " + "d" * 64]
    events = [line for line in lines if line.startswith(("event ", "candidate "))]
    starts = ["start 0 candidates 0 2 0", "start 1 no-candidate 2 0 1"]
    body = header + configuration + events[:1] + starts + events[1:] + ["end 1 2"]
    return RECORD_FORMAT + "\n" + "".join(f"{LABEL} {line}\n" for line in body)


class TruthSeededRecordReadsAndRefuses(unittest.TestCase):
    def setUp(self):
        self.text = honest_truth_seeded_text()

    def test_honest_record(self):
        parsed = parse_truth_seeded_record(self.text)
        self.assertEqual(len(parsed["events"][0]["found"]), 2)
        self.assertEqual([start["particle"] for start in parsed["events"][0]["starts"]], [0, 1])

    def test_a_line_without_its_label_is_refused(self):
        for line in ("truth-seeded event 0", "truth-seeded start 1"):
            with self.subTest(line=line):
                with self.assertRaises(TruthSeededFormatError):
                    parse_truth_seeded_record(self.text.replace(line, line[len(LABEL) + 1:], 1))

    def test_job_7503215s_format_reads_and_a_mixed_one_does_not(self):
        """Stage 6b review m7: /1 has no variant line and reads as section 7's run; /2 must have it; neither may be mixed."""
        first = self.text.replace(RECORD_FORMAT, FIRST_RECORD_FORMAT, 1).replace(f"{LABEL} variant {SECTION_7_VARIANT}\n", "")
        self.assertEqual(parse_truth_seeded_record(first)["header"]["variant"], SECTION_7_VARIANT)
        for mixed in (self.text.replace(RECORD_FORMAT, FIRST_RECORD_FORMAT, 1), self.text.replace(f"{LABEL} variant {SECTION_7_VARIANT}\n", "")):
            with self.subTest(mixed=mixed[:40]):
                with self.assertRaises(TruthSeededFormatError):
                    parse_truth_seeded_record(mixed)

    def test_a_finding_record_is_not_a_truth_seeded_record(self):
        with self.assertRaises(TruthSeededFormatError):
            parse_truth_seeded_record(finding_record.format_record(finding_tests.honest_record()))

    def test_the_reading_variant_is_not_section_7(self):
        """D1 stage 6b: the reading variant is refused as section 7's run, and read only when asked; section 7's run is refused when the reading variant is asked."""
        reading = self.text.replace(f"{LABEL} stage {STAGE}\n", f"{LABEL} stage {READING_STAGE}\n").replace(f"variant {SECTION_7_VARIANT}", f"variant {READING_VARIANT}")
        with self.assertRaises(TruthSeededFormatError):
            parse_truth_seeded_record(reading)
        self.assertEqual(len(parse_truth_seeded_record(reading, reading=True)["events"]), 1)
        with self.assertRaises(TruthSeededFormatError):
            parse_truth_seeded_record(self.text, reading=True)
        for half in (self.text.replace(f"variant {SECTION_7_VARIANT}", f"variant {READING_VARIANT}"), self.text.replace(f"{LABEL} stage {STAGE}\n", f"{LABEL} stage {READING_STAGE}\n")):
            with self.subTest(half=half[:0]):
                for asked in (False, True):
                    with self.assertRaises(TruthSeededFormatError):
                        parse_truth_seeded_record(half, reading=asked)
        with self.assertRaises(finding_record.RecordFormatError):
            finding_record.parse_record(reading)

    def test_a_skipped_start_or_a_missing_start_line_is_refused(self):
        with self.assertRaises(TruthSeededFormatError):
            parse_truth_seeded_record(self.text.replace("truth-seeded start 1 no-candidate 2 0 1\n", ""))


class TruthSeededIsNeverFinding(unittest.TestCase):
    """D1 stage 6 brief: no reader of finding results may accept the truth-seeded output as finding. Each reader is driven with it."""

    def test_the_finding_record_reader_refuses_the_record(self):
        with self.assertRaises(finding_record.RecordFormatError):
            finding_record.parse_record(honest_truth_seeded_text())

    def test_the_record_unlabelled_is_still_refused_by_its_stage(self):
        """Stage 6 review m4: a truth-seeded record re-headed in finding's own layout, with no start lines and no truth_start_* keys, differs from a finding record in its stage
        alone, so only acts_finding_record's stage guard refuses it. The control: the same text with finding's stage reads."""
        record = finding_tests.honest_record()
        self.assertEqual(len(finding_record.parse_record(finding_record.format_record(record))["events"]), 1)
        record["header"]["stage"] = STAGE
        with self.assertRaisesRegex(finding_record.RecordFormatError, "a refit or a truth-seeded run is not finding"):
            finding_record.parse_record(finding_record.format_record(record))
        record["header"].update(stage=finding_record.FINDING_STAGE, evidence_class=EVIDENCE_CLASS)
        with self.assertRaisesRegex(finding_record.RecordFormatError, "a refit or a truth-seeded run is not finding"):
            finding_record.parse_record(finding_record.format_record(record))

    def test_the_product_is_not_reported_as_finding(self):
        header = {"recipe": finding_record.FINDING_RECIPE, "stage": STAGE, "evidence_class": EVIDENCE_CLASS, "hit_sets_sha256": "c" * 64, "qop_status": "measured"}
        document = {"header": header, "tracks": []}
        self.assertFalse(native_product.fit_summary(document)["reported_as_finding"])
        self.assertEqual(len(finding_tests.finding_product_defects(document)), 4)
        with self.assertRaises(native_product.ProductFormatError):
            native_product.sidecars_for_product(dict(document, states=[], parameters=[], header=dict(header, revision=1, product_id="x")), "x")


class StartFileAndPairing(unittest.TestCase):
    def truth_events(self) -> list:
        tracks = numpy.zeros(2, dtype=truth_files.TRACK)
        tracks["q_over_p"] = (0.5, -0.25)
        tracks["crossings"][:, 0] = ((0.1, -0.2, 1e-3, 1.5), (3.0, 4.0, -2e-3, 1.6))
        return [{"tracks": tracks}]

    def test_the_start_file_holds_plane_one_exactly(self):
        text = start_file_text(self.truth_events(), "a" * 64)
        lines = text.split("\n")
        self.assertEqual(lines[:5], [START_FILE_FORMAT, "role truth", "data_sha256 " + "a" * 64, "events 1", "event 0 2"])
        values = [float(token) for token in lines[5].split()[2:]]
        self.assertEqual(values, [0.1, -0.2, 1e-3, 1.5, 0.5])
        self.assertEqual(lines[-2:], ["end 1", ""])

    def test_a_particle_without_a_plane_one_state_is_refused(self):
        events = self.truth_events()
        events[0]["tracks"]["crossings"][1, 0, 0] = numpy.nan
        with self.assertRaises(TruthSeededFormatError):
            start_file_text(events, "a" * 64)

    def test_the_paired_difference_and_its_bound(self):
        reconstructable = numpy.full(3000, 36)
        self.assertEqual(paired_difference(reconstructable, reconstructable, reconstructable, (7002, 1, 2)), (0.0, 0.0, 0.0))
        losses = numpy.zeros(3000)
        losses[::30] = 1  # 100 lost by the finder alone in 108,000
        difference, bound, percentile = paired_difference(reconstructable - losses, reconstructable, reconstructable, (7002, 1, 2))
        self.assertAlmostEqual(difference, -100 / 108000)
        self.assertLess(bound, difference)
        self.assertAlmostEqual(bound, difference - 1.645 * math.sqrt(100 * (1 - 1 / 30)) / 108000, delta=0.15e-4)  # the binomial se of 100 losses over 3,000 events
        self.assertAlmostEqual(percentile, bound, delta=0.3e-4)
        self.assertEqual(paired_difference(reconstructable - losses, reconstructable, reconstructable, (7002, 1, 2)), (difference, bound, percentile))  # seeded

    def test_the_starts_of_short_particles_are_counted(self):
        particles = [{"hit_keys": [0, 1, 2, 3, 4, 5, 6, 7]}, {"hit_keys": [10, 11, 12, 13, 14]}]
        selected = {"seed_planes": "start-1", "outcome": "selected", "hit_keys": [10, 11, 12, 13, 14, 7]}
        evicted = dict(selected, outcome="evicted")
        fake = dict(selected, hit_keys=[10, 11, 12, 20, 21, 22])
        own = {"seed_planes": "start-0", "outcome": "selected", "hit_keys": [0, 1, 2, 3, 4, 5, 6]}
        event = {"starts": [{"particle": 0}, {"particle": 1}], "found": [own, selected, evicted, fake]}
        self.assertEqual(unreconstructable_starts(event, particles, [0]), Counter(starts=1, candidates=3, selected=2, fakes=1, takes_from_lost=1))
        self.assertEqual(unreconstructable_starts(event, particles, []), Counter(starts=1, candidates=3, selected=2, fakes=1))

    def test_the_recipe_hash_reads_the_recipe_keys_only(self):
        configuration = dict({name: "1" for name in finding_record.CONFIGURATION_KEYS}, **START_CONFIGURATION)
        expected = hashlib.sha256("".join(f"configuration {name} 1\n" for name in finding_record.CONFIGURATION_KEYS).encode()).hexdigest()
        self.assertEqual(recipe_configuration_hash(configuration), expected)
        self.assertEqual(recipe_configuration_hash(dict(configuration, truth_start_plane="2")), expected)


# ---- The built tests.

def file_sha256(path: Path) -> str:
    """In 16 MB pieces: an o3 noise data file is 600 MB, and six strata run at once."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for piece in iter(lambda: stream.read(1 << 24), b""):
            digest.update(piece)
    return digest.hexdigest()


def stratum_reading(fixture: str, stratum: int, folder: Path) -> dict:
    """Generate one stratum, run the finder and the truth-seeded run on the same data file, score both event by event, then delete the files. Truth is read after the finder."""
    started = time.monotonic()
    data_file, truth_file = finding_tests.generate(folder, fixture, stratum, finding_tests.EVENTS_PER_BIN)
    _, finder_record_file, finder_product_file = finding_tests.find(folder, data_file, f"t07-paired-find-{fixture}-{stratum}", 0)
    searched = time.monotonic()
    truth_events = list(truth_files.iter_truth_events(truth_file))
    start_file = folder / f"{fixture}-{stratum}.t07starts"
    start_file.write_text(start_file_text(truth_events, file_sha256(data_file)), encoding="utf-8")
    record_file, product_file = folder / f"truth-seeded-{fixture}-{stratum}.record", folder / f"truth-seeded-{fixture}-{stratum}.product"
    finished = finding_tests.run_program([TRUTH_SEEDED_RUN, "--data-file", data_file, "--start-file", start_file, "--product-id", f"truth-seeded-{fixture}-{stratum}",
                                          "--product-file", product_file, "--record-file", record_file, "--product-events", PRODUCT_EVENTS])
    seeded_seconds = time.monotonic() - searched
    finder = finding_record.parse_record(finder_record_file.read_text(encoding="utf-8"))
    record_text = record_file.read_text(encoding="utf-8")
    seeded = parse_truth_seeded_record(record_text)
    try:
        finding_record.parse_record(record_text)
        finding_reader_refused = False
    except finding_record.RecordFormatError:
        finding_reader_refused = True
    document = native_product.parse_product(product_file.read_text(encoding="utf-8"))
    per_event = {"finder": [], "seeded": [], "reconstructable": []}
    tally = {"finder": Counter(), "seeded": Counter()}
    losses, lost_lines = Counter(), []
    plane_one = [0, 0]
    unreconstructable = Counter()  # stage 6 review m2
    for ordinal, (truth_event, finder_event, seeded_event) in enumerate(zip(truth_events, finder["events"], seeded["events"])):
        particles = finding_tests.particles_of(truth_event)
        finder_scores = finding_tests.scored_event(finding_tests.tracks_of(finder_event), particles)
        seeded_scores = finding_tests.scored_event(finding_tests.tracks_of(seeded_event), particles)
        for name, scores in (("finder", finder_scores), ("seeded", seeded_scores)):
            tally[name].update({key: scores[key] for key in ("reconstructable", "with_primary", "reconstructed", "fakes", "matched", "duplicates")})
        per_event["finder"].append(finder_scores["with_primary"])
        per_event["seeded"].append(seeded_scores["with_primary"])
        per_event["reconstructable"].append(finder_scores["reconstructable"])
        tally["seeded"]["evicted"] += sum(item["outcome"] == "evicted" for item in seeded_event["found"])
        tally["seeded"]["fit_failed"] += sum(item["outcome"] == "fit-failed" for item in seeded_event["found"])
        tally["seeded"]["truncated_events"] += int(seeded_event["seeds_truncated"] > 0 or seeded_event["ambiguity_budget_reached"])
        tally["seeded"]["lost_by_both"] += len(set(seeded_scores["lost"]) & set(finder_scores["lost"]))
        hits_by_plane = [{int(plane + 1): int(key) for plane, key in enumerate(track["hit_keys"]) if int(key) != truth_files.NO_HIT_KEY} for track in truth_event["tracks"]]
        held, total = plane_one_held(seeded_event, seeded_scores["primaries"], hits_by_plane)
        unreconstructable.update(unreconstructable_starts(seeded_event, particles, seeded_scores["lost"]))
        plane_one[0] += held
        plane_one[1] += total
        for index in seeded_scores["lost"]:
            category = finding_tests.loss_category(particles[index], seeded_event)
            missed = finding_tests.missed_planes_of(truth_event["tracks"][index])
            losses[(missed, category, "lost-by-finder-too" if index in finder_scores["lost"] else "kept-by-finder")] += 1
            if len(lost_lines) < LOST_PRINTED_PER_STRATUM:
                owned = set(particles[index]["hit_keys"])
                fates = [f"{item['key']} {item['outcome']} {item['seed_planes']} hits {len(item['hit_keys'])} own {len(owned & set(item['hit_keys']))}" for item in seeded_event["found"]
                         if 2 * len(owned & set(item["hit_keys"])) > len(item["hit_keys"])][:4]
                crossings = truth_event["tracks"]["crossings"][:, 0, :2]
                apart = numpy.hypot(*(crossings - crossings[index]).T)
                apart[index] = numpy.inf
                lost_lines.append(f"{fixture} stratum {stratum} event {ordinal} particle {index} missed {missed} category {category} finder {'lost' if index in finder_scores['lost'] else 'kept'} "
                                  f"nearest at plane 1 mm {apart.min():.3f} q/p {float(truth_event['tracks'][index]['q_over_p']):+.4f} fate {'; '.join(fates) or 'no candidate holds its majority'}")
    level = stratum % 3
    fixture_id = finding_tests.FIXTURE_IDS[fixture]
    difference, bound, percentile = paired_difference(per_event["finder"], per_event["seeded"], per_event["reconstructable"], (fixture_id, finding_tests.TUNING_BLOCK, stratum))
    summary = native_product.fit_summary(document)
    for path in (data_file, truth_file, start_file, finder_record_file, finder_product_file, record_file, product_file):
        path.unlink()
    return {"fixture": fixture, "stratum": stratum, "level": level, "events": len(seeded["events"]), "tally": tally, "losses": losses, "lost_lines": lost_lines, "difference": difference,
            "bound": bound, "percentile": percentile, "plane_one": plane_one, "unreconstructable": unreconstructable, "finder_hash": finder["header"]["configuration_sha256"], "seeded_header": seeded["header"], "seeded_configuration": seeded["configuration"],
            "finder_configuration": finder["configuration"], "finding_reader_refused": finding_reader_refused, "summary": summary, "product_stage": document["header"]["stage"],
            "stderr_bytes": len(finished.stderr), "seconds": time.monotonic() - started, "seeded_seconds": seeded_seconds}


@unittest.skipUnless(RUNNABLE, NOT_RUNNABLE)
class TruthSeededRun(unittest.TestCase):
    """Both fixtures, every stratum, block 1. A test here fails on a broken or mislabelled output, on a finder that accepts truth, or on a disagreement with a tolerance above."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        jobs = [(fixture, stratum) for fixture in ("noise", "clean") for stratum in (11, 8, 5, 2, 10, 7, 4, 1, 9, 6, 3, 0)]  # slowest first
        with concurrent.futures.ThreadPoolExecutor(finding_tests.WORKERS) as pool:
            cls.readings = sorted(pool.map(lambda job: stratum_reading(job[0], job[1], Path(cls.folder.name)), jobs), key=lambda item: (item["fixture"], item["stratum"]))
        first = cls.readings[0]
        print(f"TRUTH-SEEDED-CONFIGURATION configuration_sha256 {first['seeded_header']['configuration_sha256']} recipe_configuration_sha256 "
              f"{first['seeded_header']['recipe_configuration_sha256']} finder configuration_sha256 {first['finder_hash']}", flush=True)
        for name, value in START_CONFIGURATION.items():
            print(f"TRUTH-SEEDED-CONFIGURATION {name} {first['seeded_configuration'][name]}", flush=True)
        for item in cls.readings:
            finder, seeded = item["tally"]["finder"], item["tally"]["seeded"]
            label = f"{item['fixture']} stratum {item['stratum']}"
            print(f"TRUTH-SEEDED-READING development reading, not a gate (K09), comparator only, not finding: {label} events {item['events']} reconstructable {seeded['reconstructable']} "
                  f"with_primary {seeded['with_primary']} efficiency {seeded['with_primary'] / seeded['reconstructable']:.6f} lost {seeded['reconstructable'] - seeded['with_primary']} "
                  f"reconstructed {seeded['reconstructed']} fakes {seeded['fakes']} matched {seeded['matched']} duplicates {seeded['duplicates']} evicted {seeded['evicted']} "
                  f"fit_failed {seeded['fit_failed']} truncated_events {seeded['truncated_events']} lost_by_both {seeded['lost_by_both']}", flush=True)
            print(f"TRUTH-SEEDED-PAIRED development reading, not a gate (K09): {label} finder efficiency {finder['with_primary'] / finder['reconstructable']:.6f} lost "
                  f"{finder['reconstructable'] - finder['with_primary']}; truth-seeded efficiency {seeded['with_primary'] / seeded['reconstructable']:.6f}; difference {item['difference']:+.6f} "
                  f"lower bound (difference - 1.645 se, event bootstrap B {BOOTSTRAP_REPLICATES}) {item['bound']:+.6f} against {PAIRED_LIMIT}: {'at or above' if item['bound'] >= PAIRED_LIMIT else 'below'}; "
                  f"5 % percentile {item['percentile']:+.6f} (percentile, reading only)"
                  f"{'' if item['fixture'] == 'noise' else ' (clean: a check only, section 8.2 gates clean by its own row)'}", flush=True)
            print(f"TRUTH-SEEDED-LOST {label} by missed planes, category and the finder's fate: {dict(sorted(item['losses'].items(), key=str))}", flush=True)
            for line in item["lost_lines"]:
                print(f"TRUTH-SEEDED-LOST-PARTICLE {line}", flush=True)
            counts = item["unreconstructable"]
            print(f"TRUTH-SEEDED-NON-RECONSTRUCTABLE {label} starts {counts['starts']} candidates {counts['candidates']} selected {counts['selected']} selected_fakes {counts['fakes']} "
                  f"selected_holding_a_hit_of_a_lost_reconstructable_particle {counts['takes_from_lost']}", flush=True)
            print(f"TRUTH-SEEDED-START {label} primaries holding their own plane-1 hit {item['plane_one'][0]}/{item['plane_one'][1]}", flush=True)
            print(f"TRUTH-SEEDED-COST {label} seconds {item['seconds']:.1f} truth_seeded_seconds {item['seeded_seconds']:.1f} stderr_bytes {item['stderr_bytes']}", flush=True)

    def test_every_stratum_ran_at_its_size(self):
        self.assertEqual(len(self.readings), 24)
        self.assertEqual({item["events"] for item in self.readings}, {finding_tests.EVENTS_PER_BIN})
        self.assertEqual({item["stderr_bytes"] for item in self.readings}, {0})

    def test_the_recipe_after_the_start_is_the_finders(self):
        """Same recipe by construction (one code path), and by record: the recipe's 25 configuration lines equal the finder's, value for value, so their hash is the finder's."""
        for item in self.readings:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertEqual({name: item["seeded_configuration"][name] for name in finding_record.CONFIGURATION_KEYS}, item["finder_configuration"])
                self.assertEqual(item["seeded_header"]["recipe_configuration_sha256"], item["finder_hash"])
                self.assertEqual(recipe_configuration_hash(item["seeded_configuration"]), item["finder_hash"])
                self.assertEqual({name: item["seeded_configuration"][name] for name in START_CONFIGURATION}, START_CONFIGURATION)

    def test_the_output_is_labelled_and_never_finding(self):
        for item in self.readings:
            with self.subTest(fixture=item["fixture"], stratum=item["stratum"]):
                self.assertTrue(item["finding_reader_refused"])
                self.assertEqual((item["product_stage"], item["summary"]["evidence_class"], item["summary"]["reported_as_finding"]), (STAGE, EVIDENCE_CLASS, False))
                self.assertEqual((item["seeded_header"]["stage"], item["seeded_header"]["evidence_class"]), (STAGE, EVIDENCE_CLASS))

    def test_the_start_surface_is_filtered(self):
        for item in self.readings:
            if item["fixture"] == "clean":
                with self.subTest(stratum=item["stratum"]):
                    held, total = item["plane_one"]
                    self.assertGreaterEqual(held, PLANE_ONE_HELD_SHARE * total)

    def test_clean_losses_within_the_tolerance(self):
        for item in self.readings:
            if item["fixture"] == "clean":
                seeded = item["tally"]["seeded"]
                with self.subTest(stratum=item["stratum"]):
                    self.assertLessEqual(seeded["reconstructable"] - seeded["with_primary"], CLEAN_LOST_LIMIT_OF_LEVEL[item["level"]])


@unittest.skipUnless(RUNNABLE, NOT_RUNNABLE)
class FinderRefusesTruth(unittest.TestCase):
    """The finder must not accept a truth input: neither a start-file flag, nor the start file or a truth file in place of its data file."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        folder = Path(cls.folder.name)
        cls.data_file, cls.truth_file = finding_tests.generate(folder, "clean", finding_tests.NEGATIVE_STRATUM, 5)
        cls.start_file = folder / "five.t07starts"
        cls.start_file.write_text(start_file_text(list(truth_files.iter_truth_events(cls.truth_file)), file_sha256(cls.data_file)), encoding="utf-8")

    def finder(self, *arguments) -> int:
        folder = Path(self.folder.name)
        return finding_tests.run_program([finding_tests.FINDER, *arguments, "--product-id", "refused", "--product-file", folder / "refused.product", "--record-file",
                                          folder / "refused.record", "--product-events", 0], check=False).returncode

    def test_each_truth_route_is_refused(self):
        self.assertEqual(self.finder("--data-file", self.data_file), 0)  # the control: the same call with hits only runs
        for name, arguments in {"a start-file flag": ("--data-file", self.data_file, "--start-file", self.start_file), "the start file as data": ("--data-file", self.start_file),
                                "a truth file as data": ("--data-file", self.truth_file)}.items():
            with self.subTest(route=name):
                self.assertEqual(self.finder(*arguments), 2)

    def test_the_truth_seeded_run_refuses_a_start_file_of_another_data_file(self):
        folder = Path(self.folder.name)
        wrong = folder / "wrong.t07starts"
        text = self.start_file.read_text(encoding="utf-8")
        wrong.write_text(text.replace(file_sha256(self.data_file), "0" * 64, 1), encoding="utf-8")
        finished = finding_tests.run_program([TRUTH_SEEDED_RUN, "--data-file", self.data_file, "--start-file", wrong, "--product-id", "x", "--product-file", folder / "x.product",
                                              "--record-file", folder / "x.record", "--product-events", 0], check=False)
        self.assertEqual(finished.returncode, 2)


if __name__ == "__main__":
    unittest.main()
