"""T07's negative-case input file (D4 build E5; freeze-b-proposal.md, section 2.5): written once from block 1, kept, and frozen by its SHA-256.

t04-values-v4.md section 11: "T07's negative-case inputs are derived from block 1 files of section 4.1's fixtures. Inputs that depend on a recipe
are fixed at Freeze B." Until D4 the cases were built inside tests/adapters/test_acts_finding.py (class NegativeCases) in a temporary folder that
was deleted; this module holds that construction, unchanged, so the same bytes result, and writes them to a kept folder. Scoring side: it reads
truth (each case's meaning is which hits are a track's), so no recipe file may import it (tests/adapters/test_acts_tracking.py,
GENERATOR_SIDE_PYTHON). The finder reads only the case file, a data file like any other.

Source: block 1, clean fixture (7001), stratum 0 (the lowest momentum bin at o1: the widest curvature window), the one event of a file generated
with --first-event 0 --count 1. The cases, in file order, and the recipe constant each depends on (section 2.5 of the proposal):
- honest: the event as generated;
- one-wrong-plane: each track's plane-5 hit moved 1.0 mm along u (finding_chi2_cut 16 at 0.020 mm hits);
- three-wrong-planes: planes 3, 5, 7 moved by +1, -1, +2 mm (finding_most_holes 2, seed_plane_triples);
- branch-explosion: 20 hits 0.002 mm apart beside each true hit on planes 5 and 6 (branch budgets 16 and 32);
- no-triple, two-planes: planes removed so that no seed triple survives (seed_plane_triples);
- seed-budget: 26 hits per plane in a corner of planes 1 to 3, 17,576 triples (finding_most_seeds_per_event 10000);
- lost-i-j for the 28 plane pairs: both planes emptied;
- alone-t-i-j for each track t and pair: track t alone loses its hits on planes i and j, the other tracks keep theirs.
Every event's hits are put on the hit grid and sorted by plane and position, as the fixture writes them (t07_data_file.hpp).

The kept folder holds three files:
- t07-negative-cases-1.t07data: the case file (role reconstruction-input);
- t07-negative-cases-1.json: t07-negative-cases/1, the source's identity and SHA-256 values, the constants, the source event's hits and its
  tracks' hit keys (the truth the assertions use), the case names in file order, and the case file's SHA-256;
- SHA256SUMS: the SHA-256 of the two files, in `sha256sum -c` form.
read() refuses a folder whose sums, format or source differ, and a case file that is not, byte for byte, what the recorded source event builds.
Usage: python t07_negative_cases.py write --data-file D --truth-file T --out FOLDER; python t07_negative_cases.py read FOLDER
Exit codes (core/status.py): 0 written or read; 2 a rejected input.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from pathlib import Path

import t07_fixture_files as fixture_files
import t07_truth_files as truth_files

FORMAT = "t07-negative-cases/1"
RULE = "t04-values-v4 section 11: negative-case inputs derived from block 1 files; those that depend on a recipe are fixed at Freeze B"
CASE_FILE = "t07-negative-cases-1.t07data"
DESCRIPTION_FILE = "t07-negative-cases-1.json"
SUMS_FILE = "SHA256SUMS"
SOURCE_FIXTURE, SOURCE_FIXTURE_ID, SOURCE_BLOCK, SOURCE_STRATUM, SOURCE_FIRST_EVENT, SOURCE_COUNT = "clean", 7001, 1, 0, 0, 1
PLANES = 8
HIT_SIGMA_MM = 0.020
SHIFT_WRONG_HIT_MM = 1.0  # 50 hit sigmas
EXPLOSION_EXTRA_HITS = 20
EXPLOSION_SPACING_MM = 0.002
EXPLOSION_PLANES = (5, 6)
ONE_WRONG = {5: SHIFT_WRONG_HIT_MM}
THREE_WRONG = {3: SHIFT_WRONG_HIT_MM, 5: -SHIFT_WRONG_HIT_MM, 7: 2.0 * SHIFT_WRONG_HIT_MM}
NO_TRIPLE_PLANES_REMOVED = (2, 4, 7)
TWO_PLANES_KEPT = (1, 2)
DENSE_PATCH = {"planes": (1, 2, 3), "hits_per_plane": 26, "step_mm": 0.01, "corner_mm": 100.0}
CONSTANTS = {"hit_sigma_mm": HIT_SIGMA_MM, "shift_wrong_hit_mm": SHIFT_WRONG_HIT_MM, "explosion_extra_hits": EXPLOSION_EXTRA_HITS,
             "explosion_spacing_mm": EXPLOSION_SPACING_MM, "explosion_planes": list(EXPLOSION_PLANES), "one_wrong": {str(k): v for k, v in ONE_WRONG.items()},
             "three_wrong": {str(k): v for k, v in THREE_WRONG.items()}, "no_triple_planes_removed": list(NO_TRIPLE_PLANES_REMOVED),
             "two_planes_kept": list(TWO_PLANES_KEPT), "dense_patch": {key: list(value) if isinstance(value, tuple) else value for key, value in DENSE_PATCH.items()}}


class NegativeCaseError(ValueError):
    """The source is not block 1's clean stratum 0, or a kept folder does not hold what its source builds."""


def sorted_hits(hits) -> list:
    """Hits as the fixture writes them: on the grid, by plane and position (t07_data_file.hpp), key = position."""
    gridded = [(plane, float(fixture_files.on_hit_grid(loc0_mm)), float(fixture_files.on_hit_grid(loc1_mm))) for plane, loc0_mm, loc1_mm in hits]
    return sorted(gridded)


def _shifted(hits, tracks, shifts: dict) -> list:
    """Each track's hit on a plane moved along u: a wrong hit, chi2 far over the cut once the track has converged."""
    moved = list(hits)
    for keys in tracks:
        for key in keys:
            plane, loc0_mm, loc1_mm = moved[key]
            moved[key] = (plane, loc0_mm + shifts.get(plane, 0.0), loc1_mm)
    return moved


def _exploded(hits) -> list:
    """Compatible hits beside each true hit on the planes named: more branches than the limits allow."""
    extra = [(plane, loc0_mm + EXPLOSION_SPACING_MM * (offset + 1), loc1_mm) for plane, loc0_mm, loc1_mm in hits if plane in EXPLOSION_PLANES
             for offset in range(EXPLOSION_EXTRA_HITS)]
    return hits + extra


def _dense_patch() -> list:
    """26 hits per plane in a corner of planes 1 to 3: 17,576 triples, over the seed budget."""
    steps = [DENSE_PATCH["step_mm"] * step for step in range(DENSE_PATCH["hits_per_plane"])]
    return [(plane, DENSE_PATCH["corner_mm"] + step, DENSE_PATCH["corner_mm"] + step) for plane in DENSE_PATCH["planes"] for step in steps]


def cases_of(description: dict) -> dict:
    """names, events (each a sorted hit list), alone (each alone case's kept hits of its track), hits and tracks, from a description's source event."""
    hits = [(int(plane), float(loc0_mm), float(loc1_mm)) for plane, loc0_mm, loc1_mm in description["hits"]]
    tracks = [[int(key) for key in keys] for keys in description["tracks"]]
    events = {"honest": hits, "one-wrong-plane": _shifted(hits, tracks, ONE_WRONG), "three-wrong-planes": _shifted(hits, tracks, THREE_WRONG),
              "branch-explosion": _exploded(hits), "no-triple": [hit for hit in hits if hit[0] not in NO_TRIPLE_PLANES_REMOVED],
              "two-planes": [hit for hit in hits if hit[0] in TWO_PLANES_KEPT], "seed-budget": hits + _dense_patch()}
    pairs = list(itertools.combinations(range(1, PLANES + 1), 2))
    events.update({f"lost-{first}-{second}": [hit for hit in hits if hit[0] not in (first, second)] for first, second in pairs})
    # One track loses two hits and the others keep theirs, as on the noise fixture. The lost-* cases above empty a plane, so they could not see a foreign hit taken in place of a hole.
    alone = {f"alone-{index}-{first}-{second}": [hits[key] for key in keys if hits[key][0] not in (first, second)] for index, keys in enumerate(tracks) for first, second in pairs}
    for name in alone:
        index, first, second = (int(part) for part in name.split("-")[1:])
        dropped = {key for key in tracks[index] if hits[key][0] in (first, second)}
        events[name] = [hit for key, hit in enumerate(hits) if key not in dropped]
    return {"names": list(events), "events": [sorted_hits(event) for event in events.values()], "alone": alone, "hits": hits, "tracks": tracks}


def build(data_file, truth_file) -> tuple:
    """(case file bytes, description) from the source files: a one-event data file of block 1, clean, stratum 0, and its truth file."""
    data_file, truth_file = Path(data_file), Path(truth_file)
    try:
        header = truth_files.read_truth_header(truth_file)
        data_header = fixture_files.read_data_header(data_file)
        data_event = next(fixture_files.iter_data_events(data_file))
        truth_event = next(truth_files.iter_truth_events(truth_file))
    except (OSError, StopIteration, fixture_files.FixtureFileError) as error:
        raise NegativeCaseError(f"the source files do not read: {error}") from error
    identity = (header["fixture_id"], header["block"], header["stratum"], header["event_count"], data_header["event_count"])
    if identity != (SOURCE_FIXTURE_ID, SOURCE_BLOCK, SOURCE_STRATUM, SOURCE_COUNT, SOURCE_COUNT):
        raise NegativeCaseError(f"the source is fixture, block, stratum, events {identity}; section 11 asks block 1, here clean stratum 0, one event")
    data_sha256 = fixture_files.file_sha256(data_file)
    if header["data_sha256"] != data_sha256:
        raise NegativeCaseError(f"the truth file names data {header['data_sha256']}, not this data file's {data_sha256}")
    if data_header["sigma_loc0_mm"] != HIT_SIGMA_MM or data_header["sigma_loc1_mm"] != HIT_SIGMA_MM:
        raise NegativeCaseError("the source's hit sigma is not 0.020 mm (section 4.1)")
    hits = [[int(hit["plane"]), float(hit["loc0_mm"]), float(hit["loc1_mm"])] for hit in data_event["hits"]]
    tracks = [[int(key) for key in track["hit_keys"] if int(key) != truth_files.NO_HIT_KEY] for track in truth_event["tracks"]]
    description = {"format": FORMAT, "rule": RULE,
                   "source": {"fixture": SOURCE_FIXTURE, "fixture_id": SOURCE_FIXTURE_ID, "block": SOURCE_BLOCK, "stratum": SOURCE_STRATUM,
                              "first_event": SOURCE_FIRST_EVENT, "count": SOURCE_COUNT, "event_index": int(truth_event["event_index"]),
                              "generator": header["generator"], "data_sha256": data_sha256, "truth_sha256": fixture_files.file_sha256(truth_file)},
                   "constants": CONSTANTS, "hits": hits, "tracks": tracks}
    cases = cases_of(description)
    case_bytes = fixture_files.encode_data_file(HIT_SIGMA_MM, cases["events"])
    description["names"] = cases["names"]
    description["case_sha256"] = hashlib.sha256(case_bytes).hexdigest()
    return case_bytes, description


def _description_text(description: dict) -> str:
    return json.dumps(description, indent=1, sort_keys=True) + "\n"


def write(folder, data_file, truth_file) -> dict:
    folder = Path(folder)
    case_bytes, description = build(data_file, truth_file)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / CASE_FILE).write_bytes(case_bytes)
    (folder / DESCRIPTION_FILE).write_text(_description_text(description), encoding="utf-8")
    (folder / SUMS_FILE).write_text("".join(f"{fixture_files.file_sha256(folder / name)}  {name}\n" for name in (CASE_FILE, DESCRIPTION_FILE)), encoding="utf-8")
    return description


def read(folder) -> dict:
    """{description, case_file} of a kept folder, or NegativeCaseError."""
    folder = Path(folder)
    try:
        sums = (folder / SUMS_FILE).read_text(encoding="utf-8")
        listed = dict(reversed(line.split("  ", 1)) for line in sums.splitlines())
        if sorted(listed) != sorted((CASE_FILE, DESCRIPTION_FILE)) or len(sums.splitlines()) != 2:
            raise NegativeCaseError(f"{SUMS_FILE} lists {sorted(listed)}")
        for name, digest in listed.items():
            if fixture_files.file_sha256(folder / name) != digest:
                raise NegativeCaseError(f"{name} differs from {SUMS_FILE}")
        text = (folder / DESCRIPTION_FILE).read_text(encoding="utf-8")
        description = json.loads(text)
    except (OSError, ValueError) as error:
        if isinstance(error, NegativeCaseError):
            raise
        raise NegativeCaseError(f"{folder}: {error}") from error
    if description.get("format") != FORMAT or description.get("rule") != RULE or description.get("constants") != json.loads(json.dumps(CONSTANTS)):
        raise NegativeCaseError("the description's format, rule or constants are not this builder's")
    source = description.get("source", {})
    if (source.get("fixture_id"), source.get("block"), source.get("stratum"), source.get("first_event"), source.get("count")) != (
            SOURCE_FIXTURE_ID, SOURCE_BLOCK, SOURCE_STRATUM, SOURCE_FIRST_EVENT, SOURCE_COUNT):
        raise NegativeCaseError(f"the source is not block 1's clean stratum 0, event 0: {source}")
    if text != _description_text(description):
        raise NegativeCaseError("the description is not in its written form")
    cases = cases_of(description)
    case_bytes = fixture_files.encode_data_file(HIT_SIGMA_MM, cases["events"])
    if cases["names"] != description.get("names") or hashlib.sha256(case_bytes).hexdigest() != description.get("case_sha256") \
            or (folder / CASE_FILE).read_bytes() != case_bytes:
        raise NegativeCaseError("the case file is not what its recorded source event builds")
    if fixture_files.data_file_defects(folder / CASE_FILE):
        raise NegativeCaseError(f"the case file is not a clean data file: {fixture_files.data_file_defects(folder / CASE_FILE)}")
    return {"description": description, "case_file": folder / CASE_FILE}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    writer = commands.add_parser("write")
    writer.add_argument("--data-file", required=True)
    writer.add_argument("--truth-file", required=True)
    writer.add_argument("--out", required=True)
    reader = commands.add_parser("read")
    reader.add_argument("folder")
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as stop:
        return 2 if stop.code else 0
    try:
        if arguments.command == "write":
            description = write(arguments.out, arguments.data_file, arguments.truth_file)
        else:
            description = read(arguments.folder)["description"]
    except NegativeCaseError as error:
        print(f"REJECTED {error}")
        return 2
    print(f"NEGATIVE-CASES {arguments.command} {len(description['names'])} cases case_sha256 {description['case_sha256']} source block {description['source']['block']} "
          f"fixture {description['source']['fixture_id']} stratum {description['source']['stratum']} event_index {description['source']['event_index']} "
          f"data_sha256 {description['source']['data_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
