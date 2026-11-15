"""adapters/acts-tracking: the finder after stage 6's tidy against job 7502411's records, and ACTS's own ambiguity removal order against the Python copy of the D1 stage 5e
report (D1 stage 6 brief, items 2 and 3). A development reading of block 1, tuning, not a gate reading (K09).

Stage 6 trimmed this module to what still has a reading here. The stage 5e comparison of five finders is of record in job 7502411 (its diagnosis.log and records), and the kept
binaries of job 7496491 and the no-phi build are gone, so their pairs, seed windows, seed fates and intruder counts are no longer read. What is left:

- The finder, on the same block 1 events as job 7502411's diagnosis (clean stratum 2 and the o3 noise strata 2, 5, 8, 11, 3,000 events each), under the same product names, writes
  its record and seed file. Only tidy changes reach it at stage 6 (the no-phi build out, the steps after the start moved into one shared function, an optional trace output), so
  each record and seed file must equal job 7502411's recipe files byte for byte (HEP_ACTS_TRACKING_KEPT_RECORDS, hash-checked by the build job), and the configuration hash stays
  2448d935...3050. Events that differ are counted, so a difference says where.
- ACTS's removal sequence, from libActsCore's own VERBOSE lines in GreedyAmbiguityResolution::resolve ("maximum shared measurements", "remove track ... nMeas ... nShared ...
  chi2 ..."), which the finder writes for named events (--ambiguity-trace-file). For clean stratum 2 event 2169 and noise stratum 11 event 654 it is compared line by line with
  resolve_copy below, the Python copy the stage 5e report used (written then in a scratch file, not tracked; carried here unchanged in its rule: the largest share of shared hits,
  then the fewest hits, then the largest chi2 as a float, ties to the lowest index; stop when the largest shared count is below the limit). The copy's outcome had matched the finder
  in every event checked; this reads the order itself.

Lines start DIAGNOSIS-. Records, seed files and trace files stay under HEP_ACTS_TRACKING_EVIDENCE/diagnosis, and the clean data and truth files too; the noise data files are deleted
(600 MB each; the frozen generators remake them). Truth is read here, after the finder has finished. The predictions are in the D1 stage 6 report, fixed before the job.
Run from the plugin root: python -m unittest tests.adapters.test_acts_finding_diagnosis -v
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import os
import re
import unittest
from collections import Counter, defaultdict
from pathlib import Path

import numpy

from tests.adapters import test_acts_finding as finding_tests

finding_record, truth_files = finding_tests.finding_record, finding_tests.truth_files

EVIDENCE_DIR = os.environ.get("HEP_ACTS_TRACKING_EVIDENCE", "")
KEPT_RECORDS = os.environ.get("HEP_ACTS_TRACKING_KEPT_RECORDS", "")
RUNNABLE = finding_tests.BUILT and bool(EVIDENCE_DIR) and bool(KEPT_RECORDS)
NOT_RUNNABLE = "needs the T07 build job: HEP_ACTS_TRACKING_BUILD, HEP_ACTS_TRACKING_EVIDENCE and HEP_ACTS_TRACKING_KEPT_RECORDS"

DETAILED_CASE = ("clean", 2)
CASES = (DETAILED_CASE, ("noise", 2), ("noise", 5), ("noise", 8), ("noise", 11))  # job 7502411's diagnosis strata, block 1
TRACED_EVENTS = {("clean", 2): 2169, ("noise", 11): 654}  # D1 stage 6 brief: the two fakes of job 7502411, explained from the records in the D1 stage 5e report
LOST_IN_JOB_7502411 = {("clean", 2): 1, ("noise", 2): 106, ("noise", 5): 104, ("noise", 8): 109, ("noise", 11): 118}  # its DIAGNOSIS-READING recipe lines
FAKES_IN_JOB_7502411 = {("clean", 2): 1, ("noise", 2): 0, ("noise", 5): 0, ("noise", 8): 0, ("noise", 11): 1}
# Job 7502411's recipe hash: unchanged at stage 6, since every configuration line stays (D1 stage 6 report, Tidy).
RECIPE_CONFIGURATION_SHA256 = "2448d935fd8a20d8856be6772d7dfbaa774819f74a0a90d139cdc680531a3050"
MAXIMUM_SHARED_HITS = 2  # track_finding.hpp, ambiguity_most_shared_hits; read from the record below
TRACE_FORMAT = "acts-tracking-ambiguity-trace/1"
NOISE_OWNER = -1


# ---- Judges, testable without a build.

def owner_counts(hit_keys, owner_of_hit: dict) -> Counter:
    return Counter(owner_of_hit.get(key, NOISE_OWNER) for key in hit_keys)


def is_fake(hit_keys, owner_of_hit: dict) -> bool:
    """Section 7: no particle holds more than 50 % of the track's measurements. Noise counts in the denominator and owns nothing."""
    return not any(owner != NOISE_OWNER and 2 * count > len(hit_keys) for owner, count in owner_counts(hit_keys, owner_of_hit).items())


def configuration_hash(configuration: dict, keys) -> str:
    """The finder's configuration_sha256, over the lines of the keys named."""
    return hashlib.sha256("".join(f"configuration {name} {configuration[name]}\n" for name in keys).encode()).hexdigest()


def behaviour_of(event: dict) -> list:
    """What a finder decided in one event, leaving out the marks of the record."""
    return [(item["hit_keys"], item["seed_planes"], item["outcome"], item["search_chi2"], item["fit_chi2"]) for item in event["found"]]


def float_text(value: float) -> str:
    """A float as C++'s ostream writes it by default: six significant digits, %g."""
    return "%g" % value


def resolve_copy(candidates, maximum_shared: int, iterations: int = 1000) -> tuple:
    """The D1 stage 5e report's Python copy of GreedyAmbiguityResolution::resolve, on a record's candidates. Returns the tracks left and the lines ACTS would log, in ACTS's words:
    ("maximum", count) for each "maximum shared measurements", ("remove", track, nMeas, nShared, chi2 text) for each "remove track", ("empty",) for "no tracks left". The chi2 is the
    finder's: float(search_chi2) / float(2 n), in single precision (ambiguity_state_of)."""
    hits = [list(item["hit_keys"]) for item in candidates]
    size = [len(item) for item in hits]
    chi2 = [numpy.float32(numpy.float32(item["search_chi2"]) / numpy.float32(2 * item["measurements"])) for item in candidates]
    tracks_of_hit = defaultdict(set)
    for track, held in enumerate(hits):
        for hit in held:
            tracks_of_hit[hit].add(track)
    shared = [sum(len(tracks_of_hit[hit]) > 1 for hit in held) for held in hits]
    selected = list(range(len(candidates)))  # a flat_set: by index
    lines = []
    for _ in range(iterations):
        if not selected:
            lines.append(("empty",))
            break
        top = max(shared[track] for track in selected)
        lines.append(("maximum", top))
        if top < maximum_shared:
            break
        bad = selected[0]  # std::max_element: the first of the largest
        for track in selected[1:]:
            if (shared[bad] / size[bad], -size[bad], chi2[bad]) < (shared[track] / size[track], -size[track], chi2[track]):
                bad = track
        lines.append(("remove", bad, size[bad], shared[bad], float_text(float(chi2[bad]))))
        for hit in hits[bad]:
            tracks_of_hit[hit].discard(bad)
            if len(tracks_of_hit[hit]) == 1:
                (other,) = tracks_of_hit[hit]
                shared[other] -= 1
        selected.remove(bad)
    return set(selected), lines


def acts_lines_of(text: str) -> list:
    """ACTS's VERBOSE lines of one event, as resolve_copy writes them. Decorations (time, name, level) are left out; any other resolver line is kept as unknown."""
    lines = []
    for line in text.splitlines():
        if (found := re.search(r"remove track (\d+) nMeas (\d+) nShared (\d+) chi2 (\S+)\s*$", line)):
            lines.append(("remove", int(found.group(1)), int(found.group(2)), int(found.group(3)), found.group(4)))
        elif (found := re.search(r"maximum shared measurements (\d+)\s*$", line)):
            lines.append(("maximum", int(found.group(1))))
        elif "no tracks left - exit loop" in line:
            lines.append(("empty",))
        elif line.strip():
            lines.append(("unknown", line.strip()))
    return lines


def parse_trace(text: str) -> dict:
    """acts-tracking-ambiguity-trace/1: per event ordinal, its ACTS lines."""
    lines = text.split("\n")
    if lines[0] != TRACE_FORMAT or lines[-1] != "":
        raise ValueError(f"not {TRACE_FORMAT}, or not finished")
    events, position = {}, 1
    while position < len(lines) - 1:
        tokens = lines[position].split()
        if tokens and tokens[0] == "end":
            if len(tokens) != 2 or int(tokens[1]) != len(events) or position != len(lines) - 2:
                raise ValueError("the trace's end record does not count its events")
            return events
        if len(tokens) != 4 or tokens[0] != "event" or tokens[2] != "lines":
            raise ValueError(f"expected an event, found {lines[position]}")
        count = int(tokens[3])
        if position + 1 + count > len(lines) - 1:
            raise ValueError("the trace ends inside an event")
        events[int(tokens[1])] = "\n".join(lines[position + 1:position + 1 + count]) + "\n"
        position += 1 + count
    raise ValueError("the trace ends before its end record")


def line_text(line: tuple) -> str:
    if line[0] == "remove":
        return f"remove track {line[1]} nMeas {line[2]} nShared {line[3]} chi2 {line[4]}"
    if line[0] == "maximum":
        return f"maximum shared measurements {line[1]}"
    return " ".join(str(part) for part in line)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for piece in iter(lambda: stream.read(1 << 24), b""):
            digest.update(piece)
    return digest.hexdigest()


# ---- The run.

def run_case(case: tuple, folder: Path) -> dict:
    """Generate, find with the name job 7502411 used, and keep what the comparison reads."""
    fixture, stratum = case
    data_file, truth_file = finding_tests.generate(folder, fixture, stratum, finding_tests.EVENTS_PER_BIN)
    title = f"diagnosis-{fixture}-{stratum}-recipe"
    record_file, product_file, seed_file = folder / f"{title}.record", folder / f"{title}.product", folder / f"{title}.seeds"
    trace_file = folder / f"{title}.ambiguity-trace"
    arguments = [finding_tests.FINDER, "--data-file", data_file, "--product-id", title, "--product-file", product_file, "--record-file", record_file, "--product-events", 0,
                 "--seed-file", seed_file]
    if case in TRACED_EVENTS:
        arguments += ["--ambiguity-trace-file", trace_file, "--ambiguity-trace-events", TRACED_EVENTS[case]]
    finished = finding_tests.run_program(arguments)
    product_file.unlink()
    return {"case": case, "data_file": data_file, "truth_file": truth_file, "record_file": record_file, "seed_file": seed_file, "trace_file": trace_file if case in TRACED_EVENTS else None,
            "stderr_bytes": len(finished.stderr)}


def analysed_case(run: dict) -> dict:
    fixture, stratum = run["case"]
    kept = Path(KEPT_RECORDS)
    record = finding_record.parse_record(run["record_file"].read_text(encoding="utf-8"))
    earlier = finding_record.parse_record((kept / run["record_file"].name).read_text(encoding="utf-8"))
    changed = sum(behaviour_of(event) != behaviour_of(old) for event, old in zip(record["events"], earlier["events"])) + abs(len(record["events"]) - len(earlier["events"]))
    tally, fakes_at = Counter(), []
    for ordinal, (event, truth_event) in enumerate(zip(record["events"], truth_files.iter_truth_events(run["truth_file"]))):
        particles = finding_tests.particles_of(truth_event)
        scores = finding_tests.scored_event(finding_tests.tracks_of(event), particles)
        tally.update({name: scores[name] for name in ("reconstructable", "with_primary", "reconstructed", "fakes", "matched", "duplicates")})
        tally["hits_on_two_tracks"] += finding_tests.hits_on_two_selected(event)
        if scores["fakes"]:
            owner_of_hit = {key: index for index, particle in enumerate(particles) for key in particle["hit_keys"]}
            fakes_at += [(ordinal, item["key"], dict(owner_counts(item["hit_keys"], owner_of_hit))) for item in event["found"] if item["outcome"] == "selected" and is_fake(item["hit_keys"], owner_of_hit)]
    reading = {"case": run["case"], "label": f"{fixture} stratum {stratum}", "tally": tally, "fakes_at": fakes_at, "changed_events": changed,
               "record_equal": file_sha256(run["record_file"]) == file_sha256(kept / run["record_file"].name),
               "seeds_equal": file_sha256(run["seed_file"]) == file_sha256(kept / run["seed_file"].name), "configuration": record["configuration"],
               "configuration_sha256": record["header"]["configuration_sha256"], "stderr_bytes": run["stderr_bytes"], "resolver": None}
    if run["trace_file"] is not None:
        ordinal = TRACED_EVENTS[run["case"]]
        traced = parse_trace(run["trace_file"].read_text(encoding="utf-8"))
        candidates = record["events"][ordinal]["found"]
        left, copy_lines = resolve_copy(candidates, int(record["configuration"]["ambiguity_most_shared_hits"]), int(record["configuration"]["ambiguity_most_iterations"]))
        acts_lines = acts_lines_of(traced.get(ordinal, ""))
        reading["resolver"] = {"ordinal": ordinal, "events_traced": sorted(traced), "acts": acts_lines, "copy": copy_lines, "candidates": len(candidates),
                               "copy_left": sorted(left), "record_left": sorted(index for index, item in enumerate(candidates) if item["outcome"] != "evicted")}
    if run["case"] != DETAILED_CASE:
        run["data_file"].unlink()
    return reading


def print_case(reading: dict) -> None:
    label, tally = reading["label"], reading["tally"]
    print(f"DIAGNOSIS-READING {label} recipe: reconstructable {tally['reconstructable']} lost {tally['reconstructable'] - tally['with_primary']} reconstructed {tally['reconstructed']} "
          f"fakes {tally['fakes']} matched {tally['matched']} duplicates {tally['duplicates']} hits_on_two_tracks {tally['hits_on_two_tracks']}", flush=True)
    for ordinal, key, owners in reading["fakes_at"]:
        print(f"DIAGNOSIS-FAKE {label} event {ordinal} {key} owners {owners}", flush=True)
    print(f"DIAGNOSIS-SAME {label}: record equal to job 7502411's byte for byte {int(reading['record_equal'])}, seed file equal {int(reading['seeds_equal'])}, "
          f"events decided otherwise {reading['changed_events']}", flush=True)
    resolver = reading["resolver"]
    if resolver is None:
        return
    acts, copy = resolver["acts"], resolver["copy"]
    first_apart = next((index for index, (one, other) in enumerate(zip(acts, copy)) if one != other), None if len(acts) == len(copy) else min(len(acts), len(copy)))
    removals = sum(line[0] == "remove" for line in acts)
    print(f"DIAGNOSIS-RESOLVER {label} event {resolver['ordinal']}: candidates {resolver['candidates']}, ACTS lines {len(acts)} with {removals} removals, copy lines {len(copy)}; "
          f"first line apart {first_apart}; left by the copy {resolver['copy_left']}, in the record {resolver['record_left']}", flush=True)
    for index in range(max(len(acts), len(copy))):
        one = line_text(acts[index]) if index < len(acts) else "none"
        other = line_text(copy[index]) if index < len(copy) else "none"
        print(f"DIAGNOSIS-RESOLVER-LINE {label} event {resolver['ordinal']} {index} acts [{one}] copy [{other}] {'same' if one == other else 'APART'}", flush=True)


@unittest.skipUnless(RUNNABLE, NOT_RUNNABLE)
class FinderAgainstJob7502411(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = Path(EVIDENCE_DIR) / "diagnosis"
        folder.mkdir(parents=True, exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(finding_tests.WORKERS) as pool:
            runs = list(pool.map(lambda case: run_case(case, folder), reversed(CASES)))
        cls.readings = []
        for run in sorted(runs, key=lambda item: CASES.index(item["case"])):
            reading = analysed_case(run)
            print_case(reading)
            cls.readings.append(reading)
        print(f"DIAGNOSIS-CONFIGURATION recipe configuration_sha256 {cls.readings[0]['configuration_sha256']}", flush=True)

    def test_every_case_ran_quietly(self):
        self.assertEqual([reading["case"] for reading in self.readings], list(CASES))
        self.assertEqual({reading["stderr_bytes"] for reading in self.readings}, {0})

    def test_the_finder_decides_as_in_job_7502411(self):
        """D1 stage 6 brief: only tidy changes touch the finder, so its tracks equal job 7502411's on every event. Byte for byte, and event by event to say where if not."""
        for reading in self.readings:
            with self.subTest(case=reading["case"]):
                self.assertEqual(reading["changed_events"], 0)
                self.assertTrue(reading["record_equal"])
                self.assertTrue(reading["seeds_equal"])
                self.assertEqual(reading["tally"]["reconstructable"] - reading["tally"]["with_primary"], LOST_IN_JOB_7502411[reading["case"]])
                self.assertEqual(reading["tally"]["fakes"], FAKES_IN_JOB_7502411[reading["case"]])

    def test_the_configuration_is_job_7502411s(self):
        for reading in self.readings:
            with self.subTest(case=reading["case"]):
                self.assertEqual(reading["configuration_sha256"], RECIPE_CONFIGURATION_SHA256)
                self.assertEqual(configuration_hash(reading["configuration"], finding_record.CONFIGURATION_KEYS), RECIPE_CONFIGURATION_SHA256)
                self.assertEqual(reading["configuration"]["ambiguity_most_shared_hits"], str(MAXIMUM_SHARED_HITS))

    def test_acts_removes_in_the_copys_order(self):
        """D1 stage 6 brief, item 2: ACTS's own sequence, line by line, against the copy; and the copy's survivors are the record's."""
        for reading in self.readings:
            if reading["resolver"] is None:
                continue
            resolver = reading["resolver"]
            with self.subTest(case=reading["case"]):
                self.assertEqual(resolver["events_traced"], [resolver["ordinal"]])
                self.assertNotIn("unknown", {line[0] for line in resolver["acts"]})
                self.assertGreater(len(resolver["acts"]), 1)
                self.assertEqual(resolver["acts"], resolver["copy"])
                self.assertEqual(resolver["copy_left"], resolver["record_left"])


class Judges(unittest.TestCase):
    def test_a_tie_is_fake_and_a_majority_is_not(self):
        owners = {0: 0, 1: 0, 2: 0, 3: 0, 4: 1, 5: 1, 6: 1, 7: 1}
        self.assertTrue(is_fake(list(range(8)), owners))
        self.assertFalse(is_fake([0, 1, 2, 3, 4], owners))
        self.assertTrue(is_fake([0, 1, 2, 100, 101, 102], owners))

    def test_the_recipe_hash_is_job_7502411s(self):
        """The 25 values of the recipe since stage 5e: unchanged at stage 6, so the hash is job 7502411's."""
        values = ("1-2-3,1-2-4,3-4-5,6-7-8", "1.5", "0.25", "0.16", "5", "1.5", "16", "6", "2", "16", "32", "10000", "10000", "2", "1000", "2", "0.050000000000000003", "-50", "10", "0.10000000000000001",
                  "1", "1", "none", "chord", "present")
        configuration = dict(zip(finding_record.CONFIGURATION_KEYS, values))
        self.assertEqual(configuration_hash(configuration, finding_record.CONFIGURATION_KEYS), RECIPE_CONFIGURATION_SHA256)
        for key, other in (("ambiguity_most_shared_hits", "1"), ("seed_slope_along_v", "last-two"), ("seed_covariance_phi_term", "absent")):
            with self.subTest(key=key):
                self.assertNotEqual(configuration_hash(dict(configuration, **{key: other}), finding_record.CONFIGURATION_KEYS), RECIPE_CONFIGURATION_SHA256)

    def test_the_copy_on_a_close_pair(self):
        """Three candidates: two complementary mixtures sharing one hit, and the true one sharing everything. The share rule takes the true one first, then the loop stops at 2."""
        candidates = [{"hit_keys": [0, 1, 2, 3, 14, 15, 16, 17], "search_chi2": 24.8, "measurements": 8},
                      {"hit_keys": [10, 11, 12, 3, 4, 5, 6, 7], "search_chi2": 24.7, "measurements": 8},
                      {"hit_keys": [0, 1, 2, 3, 4, 5, 6, 7], "search_chi2": 13.0, "measurements": 8}]
        left, lines = resolve_copy(candidates, 2)
        self.assertEqual(left, {0, 1})
        self.assertEqual(lines, [("maximum", 8), ("remove", 2, 8, 8, "0.8125"), ("maximum", 1)])
        left, lines = resolve_copy(candidates, 1)
        self.assertEqual(left, {1})
        self.assertEqual(lines[-2:], [("remove", 0, 8, 1, float_text(float(numpy.float32(numpy.float32(24.8) / numpy.float32(16))))), ("maximum", 0)])

    def test_acts_lines_are_read_through_their_decorations(self):
        text = ("22:12:01    Ambiguity      VERBOSE   maximum shared measurements 8\n22:12:01    Ambiguity      VERBOSE   remove track 2 nMeas 8 nShared 8 chi2 0.8125\n"
                "22:12:01    Ambiguity      VERBOSE   maximum shared measurements 1\n")
        self.assertEqual(acts_lines_of(text), [("maximum", 8), ("remove", 2, 8, 8, "0.8125"), ("maximum", 1)])
        self.assertEqual(acts_lines_of("x  VERBOSE   something else\n"), [("unknown", "x  VERBOSE   something else")])

    def test_the_trace_file_reads_and_refuses(self):
        text = f"{TRACE_FORMAT}\nevent 7 lines 2\none\ntwo\nend 1\n"
        self.assertEqual(parse_trace(text), {7: "one\ntwo\n"})
        for broken in (text.replace("end 1", "end 2"), text.replace("lines 2", "lines 3"), text[:-1], "other\n"):
            with self.subTest(broken=broken):
                with self.assertRaises(ValueError):
                    parse_trace(broken)

    def test_float_text_is_cpp_default(self):
        self.assertEqual([float_text(value) for value in (2.2379, 0.8125, 1.0, 1e-05, 123456789.0)], ["2.2379", "0.8125", "1", "1e-05", "1.23457e+08"])


if __name__ == "__main__":
    unittest.main()
