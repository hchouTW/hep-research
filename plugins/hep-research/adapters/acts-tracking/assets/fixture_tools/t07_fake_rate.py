"""The T07 Freeze-B scorer and runner of the noise-fixture fake rate (D4 build E2; freeze-b-proposal.md, section 4 row E2). Scoring side.

It reads truth, so no recipe file may import it (tests/adapters/test_acts_tracking.py, GENERATOR_SIDE_PYTHON). Sections cited are of
t04-values-v4.md (Freeze A, 92f71f56...).

What it computes, per noise bin (fixture 7002, one stratum, one block):
- Section 7, "Track match": a track matches a particle if more than 50 % of its measurements, noise hits included in the count, come from it;
  "Fake": a reconstructed track matching no particle, over all reconstructed tracks in the bin's events. Reconstructed tracks are the finder's
  delivered (selected) candidates. Per event: m_e tracks, y_e fakes.
- Section 5.2, "Rate tests with an upper limit L": k = sum y_e, n = sum m_e, N_ev events (every generated event of the bin, also one with no
  track), m = n/N_ev; DEFF_hat = var / (p(1-p)/n) with var = N_ev/(N_ev - 1) x sum_e (y_e - p m_e)^2 / n^2, p = k/n, and 1 by definition at
  k = 0; D = max(1, DEFF_hat); U_A the Clopper-Pearson upper bound on (k/D, n/D); U_B the same with N_ev events and k_eff = min(k, 30)/m;
  U = max(U_A, U_B). The lower bound L of step 1 is the Clopper-Pearson lower bound on set A's effective counts (k/D, n/D), 0 at k = 0. Both
  bounds are one-sided at 95 %, the level of the frozen coding (calc-rate-rule.py, `bound(m, y, cl=0.95)`) and of section 8.3 ("the 95 %
  bounds of section 5.2"); Freeze A's closed form of F2 takes them so (t04-v4 calc-closed-form.py lines 194-199: 2.326 = 1.645 x sqrt 2, each
  bound 1.645 sigma from its rate; coordinator's ruling O1, D4 E2 fix round 1). The expressions are the frozen coding's, in its order, so U
  agrees with it exactly. The record counts the events with no delivered track (events_without_tracks), which are in N_ev.
- Section 8.3: r_dev = k/n, L_dev = L, U_dev = U, recorded with k, n, N_ev and DEFF_hat (U-B7, decisions.md, "Freeze B proposal: the user's
  answers to section 5.1"); C(o) = 0.005 at all three levels ("Value at Freeze A"); "If U_dev exceeds C at the Freeze-B run, evaluation does not
  start". U_dev equal to C is within it ("U <= L", step 3). At blocks 2 to 5 (a Freeze-B run) the check also needs all 12 noise bins
  (section 8.3, r_dev per bin): a record of fewer strata refuses, and a block-1 record names the strata it lacks.

The runner (subcommand run) generates each bin with the frozen generator (its own seed rule: block, stratum, first event 0 and the count are
its arguments), runs the finder on the data file alone with the vertex step (the recipes reco.track.acts-ckf-planar/1 and
reco.vertex.acts-amvf/1), scores noise bins, and, with --delete-noise-data, deletes each noise data file only after its SHA-256 equals both
the finding record's data_sha256 and the truth file's (U-B11), in a second pass after every bin passed its checks and the rate record was
written and read back; if any bin fails, no data file is deleted. Truth files, records, products and counts files are kept. Blocks: 1 (tuning)
and 2 to 5 (the Freeze-B runs, section 3.2); 6, 11 and 12 are refused. Default sizes are section 3.2's Freeze-B run sizes: 12,000 events per
noise bin, 3,000 per clean bin.

Outputs, in --out:
- <fixture>-b<block>-s<stratum>.{t07data,t07truth,record,product,stderr} and, for noise, .counts (t07-noise-fake-rate-counts/1: one line
  "event_index m y" per event in file order);
- <fixture>-b<block>.listing (t07-freeze-b-run-listing/1): every file with its SHA-256, bytes and kept or deleted-after-hash-match, and the
  seconds of each step;
- noise-b<block>.rate.record (t07-noise-fake-rate/1), read by parse_rate_record, which refuses a malformed record and recomputes every bound.

Exit codes (core/status.py): 0 ok; 1 refused or failed: a bin with U_dev > C (evaluation does not start), or a check of a bin failed (a hash, a
count, a program's exit), the file then kept; 2 rejected input (arguments, a block outside 1-5, an unreadable record); 3 not used.
Usage, from anywhere:
    python t07_fake_rate.py run --generator G --finder F --fixture noise --block 1 --strata 0-11 [--events-per-bin N] --out DIR
                                [--workers W] [--product-events K] [--delete-noise-data]
    python t07_fake_rate.py check RECORD
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import math
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy
from scipy import stats

import acts_finding_record as finding_record
import t07_truth_files as truth_files

RECORD_FORMAT = "t07-noise-fake-rate/1"
COUNTS_FORMAT = "t07-noise-fake-rate-counts/1"
LISTING_FORMAT = "t07-freeze-b-run-listing/1"
MATCH_RULE = "t04-values-v4 section 7: Track match (more than 50 % of the track's measurements, noise hits included), Fake (matching no particle; denominator all reconstructed tracks in the bin's events)"
RATE_RULE = "t04-values-v4 section 5.2: rate tests, DEFF_hat, U_A, U_B, U = max(U_A, U_B), step 1 lower bound on set A's effective counts; one-sided 95 % on both bounds, as Freeze A's closed form of F2 (t04-v4 calc-closed-form.py lines 194-199: 2.326 = 1.645 x sqrt 2)"
LIMIT_RULE = "t04-values-v4 section 8.3: C(o) 0.005 at Freeze A, U_dev <= C, else evaluation does not start"
CONFIDENCE = 0.95
K_CAP = 30
LIMIT_OF_LEVEL = (0.005, 0.005, 0.005)  # section 8.3, "Value at Freeze A": 0.005 at all three levels (job 7474462)
FIXTURE_IDS = {"clean": 7001, "noise": 7002}
FREEZE_B_EVENTS_PER_BIN = {"noise": 12000, "clean": 3000}  # section 3.2, "Freeze-B run size, events per bin"
RUN_BLOCKS = (1, 2, 3, 4, 5)  # section 3.2: 1 tuning; 2, 3, 4 the Freeze-B runs before attempt 1; 5 before attempt 2
STRATA = tuple(range(12))
PRODUCT_EVENTS = 50  # as the development run (tests/adapters/test_acts_finding.py, PRODUCT_EVENTS)
HEADER_KEYS = ("match_rule", "rate_rule", "limit_rule", "confidence", "k_cap", "recipe", "configuration_sha256", "vertex_configuration_sha256", "fixture_id",
               "block", "events_per_bin")
BIN_FIELDS = ("level", "events", "events_without_tracks", "tracks", "fakes", "objects_per_event", "deff_hat", "design_effect", "u_a", "u_b", "u_dev", "l_dev", "r_dev", "limit",
              "within_limit", "data_sha256", "truth_sha256", "record_sha256", "counts_sha256")
INTEGER_FIELDS = ("level", "events", "events_without_tracks", "tracks", "fakes")
FLOAT_FIELDS = ("objects_per_event", "deff_hat", "design_effect", "u_a", "u_b", "u_dev", "l_dev", "r_dev", "limit")
HASH_FIELDS = ("data_sha256", "truth_sha256", "record_sha256", "counts_sha256")
BOUND_FIELDS = ("objects_per_event", "design_effect", "u_a", "u_b", "u_dev", "l_dev", "r_dev")
SHA256 = re.compile(r"[0-9a-f]{64}")
CHUNK = 1 << 24


class RateRecordError(ValueError):
    """The text is not t07-noise-fake-rate/1 (or its counts file), or a number in it does not follow from its counts."""


# ---- Section 7.

def event_counts(tracks, particles) -> tuple:
    """(m_e, y_e): reconstructed tracks and fakes of one event. tracks: hit-key lists of the delivered tracks; particles: hit-key lists of the truth
    particles (keys of no hit left out). A hit key held by two particles is refused: the fixture gives each hit one owner at most."""
    owner = {}
    for index, keys in enumerate(particles):
        for key in keys:
            if key in owner:
                raise ValueError(f"hit key {key} belongs to particles {owner[key]} and {index}")
            owner[key] = index
    fakes = 0
    for keys in tracks:
        count = Counter(owner[key] for key in keys if key in owner)
        if not any(2 * matched > len(keys) for matched in count.values()):
            fakes += 1
    return len(tracks), fakes


# ---- Section 5.2.

def within_limit(u_dev: float, level: int) -> bool:
    return u_dev <= LIMIT_OF_LEVEL[level]


def bounds_of(k: int, n: int, events: int, deff_hat: float) -> dict:
    """U_A, U_B, U, L, D, m, r from the counts and DEFF_hat, in the frozen coding's expressions and order (calc-rate-rule.py, bound)."""
    if events < 2 or n < 1 or not 0 <= k < n:
        raise ValueError(f"the rule needs at least 2 events, a track, and 0 <= k < n: k {k} n {n} events {events}")
    if k == 0 and deff_hat != 1.0:
        raise ValueError("DEFF_hat is 1 by definition at k = 0")
    d = max(deff_hat, 1.0) if k > 0 else 1.0
    u_a = float(stats.beta.ppf(CONFIDENCE, k / d + 1, n / d - k / d))
    mbar = n / events
    kb = min(k, K_CAP) / mbar
    u_b = float(stats.beta.ppf(CONFIDENCE, kb + 1, events - kb))
    lower = float(stats.beta.ppf(1 - CONFIDENCE, k / d, n / d - k / d + 1)) if k > 0 else 0.0
    return {"objects_per_event": float(mbar), "design_effect": float(d), "u_a": u_a, "u_b": u_b, "u_dev": max(u_a, u_b), "l_dev": lower, "r_dev": k / n}


def rate_rule(m, y) -> dict:
    """Section 5.2 on one bin: m and y per event. The between-event estimator is the frozen coding's, operation for operation."""
    m = numpy.asarray(m, dtype=numpy.int64)
    y = numpy.asarray(y, dtype=numpy.int64)
    if m.ndim != 1 or m.shape != y.shape or (m < 0).any() or (y < 0).any() or (y > m).any():
        raise ValueError("m and y are per-event counts, 0 <= y_e <= m_e")
    nev = m.size
    n = m.sum()
    k = y.sum()
    if nev < 2 or n < 1 or k >= n:
        raise ValueError(f"the rule needs at least 2 events, a track, and k < n: k {k} n {n} events {nev}")
    if k > 0:
        ph = k / n
        resid = y - ph * m
        var_cluster = nev / (nev - 1) * (resid ** 2).sum() / n ** 2
        deff_hat = float(var_cluster / (ph * (1 - ph) / n))
    else:
        deff_hat = 1.0
    found = {"events": int(nev), "events_without_tracks": int((m == 0).sum()), "tracks": int(n), "fakes": int(k), "deff_hat": deff_hat}
    found.update(bounds_of(int(k), int(n), int(nev), deff_hat))
    return found


# ---- Scoring a bin from its files.

def stream_sha256(path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def score_bin(record: dict, truth_path) -> list:
    """[(event_index, m_e, y_e)] in file order, from a parsed finding record and its truth file. Truth is read here, after the finder has finished."""
    header = truth_files.read_truth_header(truth_path)
    if header["data_sha256"] != record["header"]["data_sha256"]:
        raise ValueError(f"the truth file names data {header['data_sha256']}, the record {record['header']['data_sha256']}")
    if header["event_count"] != len(record["events"]):
        raise ValueError(f"the truth file holds {header['event_count']} events, the record {len(record['events'])}")
    rows = []
    for event, truth_event in zip(record["events"], truth_files.iter_truth_events(truth_path)):
        tracks = [item["hit_keys"] for item in event["found"] if item["outcome"] == "selected"]
        particles = [[int(key) for key in track["hit_keys"] if int(key) != truth_files.NO_HIT_KEY] for track in truth_event["tracks"]]
        rows.append((int(truth_event["event_index"]),) + event_counts(tracks, particles))
    return rows


def format_counts(rows) -> str:
    return COUNTS_FORMAT + "\n" + "".join(f"{index} {m} {y}\n" for index, m, y in rows) + f"end {len(rows)}\n"


def parse_counts(text: str) -> list:
    lines = text.split("\n")
    if not lines or lines[0] != COUNTS_FORMAT or lines[-1] != "" or len(lines) < 3:
        raise RateRecordError(f"not {COUNTS_FORMAT}, or not finished")
    body, end = lines[1:-2], lines[-2]
    if end != f"end {len(body)}":
        raise RateRecordError(f"the counts end at {end!r} and hold {len(body)} events")
    rows, seen = [], set()
    for line in body:
        tokens = line.split(" ")
        if len(tokens) != 3 or not all(token.isdigit() for token in tokens):
            raise RateRecordError(f"not a counts line: {line!r}")
        index, m, y = (int(token) for token in tokens)
        if y > m or index in seen:
            raise RateRecordError(f"event {index}: {y} fakes in {m} tracks, or the event twice")
        seen.add(index)
        rows.append((index, m, y))
    return rows


# ---- The record.

def bin_line_values(stratum: int, found: dict, file_hashes: dict) -> dict:
    """One bin of a rate record from rate_rule's result and the bin's file hashes."""
    level = stratum % 3
    values = {"stratum": stratum, "level": level, "limit": LIMIT_OF_LEVEL[level], "within_limit": "yes" if within_limit(found["u_dev"], level) else "no"}
    values.update({name: found[name] for name in ("events", "events_without_tracks", "tracks", "fakes", "deff_hat") + BOUND_FIELDS})
    values.update({name: file_hashes[name] for name in HASH_FIELDS})
    return values


def _value_text(name: str, value) -> str:
    return repr(float(value)) if name in FLOAT_FIELDS else str(value)


def format_rate_record(document: dict) -> str:
    header = dict(document["header"], match_rule=MATCH_RULE, rate_rule=RATE_RULE, limit_rule=LIMIT_RULE, confidence=CONFIDENCE, k_cap=K_CAP)
    lines = [RECORD_FORMAT] + [f"{name} {header[name]}" for name in HEADER_KEYS]
    for item in document["bins"]:
        lines.append(" ".join([f"bin {item['stratum']}"] + [f"{name} {_value_text(name, item[name])}" for name in BIN_FIELDS]))
    beyond = sum(item["within_limit"] == "no" for item in document["bins"])
    lines.append(f"end bins {len(document['bins'])} beyond_limit {beyond}")
    return "\n".join(lines) + "\n"


def _float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise RateRecordError(f"not a finite number: {token}")
    return value


def _bin(line: str, header: dict) -> dict:
    tokens = line.split(" ")
    if len(tokens) != 2 + 2 * len(BIN_FIELDS) or tokens[0] != "bin" or tokens[2::2] != list(BIN_FIELDS):
        raise RateRecordError(f"a bin line holds other fields than {BIN_FIELDS}: {line[:80]}")
    item = {"stratum": int(tokens[1])}
    for name, token in zip(tokens[2::2], tokens[3::2]):
        if name in INTEGER_FIELDS:
            if not token.isdigit():
                raise RateRecordError(f"{name} is not a count: {token}")
            item[name] = int(token)
        elif name in FLOAT_FIELDS:
            item[name] = _float(token)
        elif name in HASH_FIELDS:
            if not SHA256.fullmatch(token):
                raise RateRecordError(f"{name} is not a SHA-256: {token}")
            item[name] = token
        else:
            item[name] = token
    if item["stratum"] not in STRATA or item["level"] != item["stratum"] % 3:
        raise RateRecordError(f"stratum {item['stratum']} with level {item['level']}: stratum = 3 x momentum bin + occupancy level, 0 to 11")
    if item["events"] != header["events_per_bin"]:
        raise RateRecordError(f"stratum {item['stratum']} holds {item['events']} events, the run {header['events_per_bin']} per bin")
    if item["events_without_tracks"] > item["events"]:
        raise RateRecordError(f"stratum {item['stratum']}: {item['events_without_tracks']} events without a track of {item['events']}")
    if item["limit"] != LIMIT_OF_LEVEL[item["level"]]:
        raise RateRecordError(f"stratum {item['stratum']}: limit {item['limit']} is not section 8.3's C {LIMIT_OF_LEVEL[item['level']]}")
    try:
        again = bounds_of(item["fakes"], item["tracks"], item["events"], item["deff_hat"])
    except ValueError as error:
        raise RateRecordError(f"stratum {item['stratum']}: {error}") from error
    for name in BOUND_FIELDS:
        if again[name] != item[name]:
            raise RateRecordError(f"stratum {item['stratum']}: {name} {item[name]!r} does not follow from the counts ({again[name]!r})")
    if item["within_limit"] != ("yes" if within_limit(item["u_dev"], item["level"]) else "no"):
        raise RateRecordError(f"stratum {item['stratum']}: within_limit {item['within_limit']} against U_dev {item['u_dev']!r} and C {item['limit']}")
    return item


def parse_rate_record(text: str) -> dict:
    """A whole t07-noise-fake-rate/1 record, or RateRecordError: its format and rule texts, every header key once, every bin's fields in order,
    every bound recomputed from the bin's k, n, N_ev and DEFF_hat, the limit check, and the end line's counts."""
    lines = text.split("\n")
    if lines[-1] != "":
        raise RateRecordError("the last line is not finished")
    lines = lines[:-1]
    if not lines or lines[0] != RECORD_FORMAT:
        raise RateRecordError(f"not {RECORD_FORMAT}")
    header = {}
    for name, line in zip(HEADER_KEYS, lines[1:]):
        key, _, value = line.partition(" ")
        if key != name or not value:
            raise RateRecordError(f"expected the header key {name}, found {line[:80]}")
        header[name] = value
    if len(header) != len(HEADER_KEYS):
        raise RateRecordError("the record ends inside its header")
    for name, expected in (("match_rule", MATCH_RULE), ("rate_rule", RATE_RULE), ("limit_rule", LIMIT_RULE), ("confidence", str(CONFIDENCE)), ("k_cap", str(K_CAP)),
                           ("recipe", finding_record.FINDING_RECIPE), ("fixture_id", str(FIXTURE_IDS["noise"]))):
        if header[name] != expected:
            raise RateRecordError(f"{name} {header[name]} is not this reader's: {expected}")
    if not SHA256.fullmatch(header["configuration_sha256"]) or not (header["vertex_configuration_sha256"] == "none" or SHA256.fullmatch(header["vertex_configuration_sha256"])):
        raise RateRecordError("a configuration hash is not a SHA-256")
    try:
        header["block"], header["events_per_bin"], header["fixture_id"] = int(header["block"]), int(header["events_per_bin"]), int(header["fixture_id"])
        header["confidence"], header["k_cap"] = float(header["confidence"]), int(header["k_cap"])
    except ValueError as error:
        raise RateRecordError(str(error)) from error
    if header["block"] not in RUN_BLOCKS:
        raise RateRecordError(f"block {header['block']} is not a block of a Freeze-B or tuning run (section 3.2: {RUN_BLOCKS})")
    bins, end = [], None
    for line in lines[1 + len(HEADER_KEYS):]:
        if end is not None:
            raise RateRecordError("text after the end line")
        if line.startswith("bin "):
            try:
                bins.append(_bin(line, header))
            except ValueError as error:
                if isinstance(error, RateRecordError):
                    raise
                raise RateRecordError(str(error)) from error
        elif line.startswith("end "):
            end = line
        else:
            raise RateRecordError(f"unknown line {line[:80]}")
    if end is None:
        raise RateRecordError("the record ends before its end line")
    strata = [item["stratum"] for item in bins]
    if len(set(strata)) != len(strata):
        raise RateRecordError(f"a stratum appears twice: {strata}")
    beyond = sum(item["within_limit"] == "no" for item in bins)
    if end != f"end bins {len(bins)} beyond_limit {beyond}":
        raise RateRecordError(f"the end line {end!r} counts other numbers than {len(bins)} bins and {beyond} beyond the limit")
    for name in ("match_rule", "rate_rule", "limit_rule", "confidence", "k_cap"):
        header.pop(name)
    return {"header": header, "bins": bins}


def evaluation_verdict(document: dict) -> tuple:
    """(True, line) if U_dev <= C in every bin; otherwise (False, the line section 8.3 asks for). No gate verdict follows from either."""
    beyond = [item for item in document["bins"] if item["within_limit"] == "no"]
    missing = sorted(set(STRATA) - {item["stratum"] for item in document["bins"]})
    block = document["header"]["block"]
    lacking = f"; missing strata {missing}" if missing else ""
    if beyond:
        named = ", ".join(f"stratum {item['stratum']} U_dev {item['u_dev']!r} > C {item['limit']}" for item in beyond)
        return False, f"U_dev > C in {len(beyond)} bins ({named}){lacking}: evaluation does not start (t04-values-v4 section 8.3)"
    if missing and block != 1:
        return False, f"U_dev <= C in the {len(document['bins'])} bins held, but not every noise bin of block {block}{lacking}: evaluation does not start (t04-values-v4 section 8.3, r_dev per noise bin)"
    return True, f"U_dev <= C ({LIMIT_OF_LEVEL[0]}) in all {len(document['bins'])} bins of block {block}{lacking}"


# ---- U-B11.

def delete_after_hash_match(path, expected) -> dict:
    """Delete a data file only if its SHA-256 equals every expected value (the finding record's data_sha256 and the truth file's). A truth file is
    never deleted; no expected value, or a malformed one, is refused with the file kept."""
    path = Path(path)
    if path.suffix != ".t07data":
        raise ValueError(f"{path.name}: only a data file (.t07data) is deleted")
    expected = list(expected)
    if not expected or not all(isinstance(value, str) and SHA256.fullmatch(value) for value in expected):
        raise ValueError(f"{path.name}: the expected hashes are not SHA-256 values: {expected}")
    digest = stream_sha256(path)
    differing = [value for value in expected if value != digest]
    if differing:
        return {"deleted": False, "sha256": digest, "reason": f"the file's SHA-256 {digest} differs from {differing[0]}; kept"}
    path.unlink()
    return {"deleted": True, "sha256": digest, "reason": "every expected SHA-256 matched"}


# ---- The runner.

def finder_command(finder: Path, data_file: Path, product_id: str, product_file: Path, record_file: Path, product_events: int) -> list:
    """The finder's command line: the data file alone as input, with the vertex step. A truth file is refused here as the finder refuses it."""
    if Path(data_file).suffix != ".t07data":
        raise ValueError(f"the finder reads a data file (.t07data), not {Path(data_file).name}")
    return [str(finder), "--data-file", str(data_file), "--product-id", product_id, "--product-file", str(product_file), "--record-file", str(record_file),
            "--product-events", str(product_events), "--vertex-recipe", finding_record.VERTEX_RECIPE]


class BinFailure(Exception):
    """A check of one bin failed; its files are kept."""


def run_bin(generator: Path, finder: Path, fixture: str, block: int, stratum: int, events: int, out: Path, product_events: int, delete_data: bool) -> dict:
    name = f"{fixture}-b{block}-s{stratum}"
    data_file, truth_file = out / f"{name}.t07data", out / f"{name}.t07truth"
    record_file, product_file, stderr_file = out / f"{name}.record", out / f"{name}.product", out / f"{name}.stderr"
    seconds = {}
    started = time.monotonic()
    generated = subprocess.run([str(generator), "generate", "--fixture", fixture, "--block", str(block), "--stratum", str(stratum), "--first-event", "0",
                                "--count", str(events), "--data-file", str(data_file), "--truth-file", str(truth_file)], capture_output=True, text=True)
    seconds["generate"] = time.monotonic() - started
    if generated.returncode != 0:
        raise BinFailure(f"{name}: the generator exited {generated.returncode}: {generated.stderr[-500:]}")
    truth_header = truth_files.read_truth_header(truth_file)
    identity = (truth_header["fixture_id"], truth_header["block"], truth_header["stratum"], truth_header["event_count"])
    if identity != (FIXTURE_IDS[fixture], block, stratum, events):
        raise BinFailure(f"{name}: the truth file is of fixture, block, stratum, events {identity}")
    started = time.monotonic()
    with open(stderr_file, "w", encoding="utf-8") as stderr:
        found = subprocess.run(finder_command(finder, data_file, f"t07-freeze-b-{name}", product_file, record_file, product_events), stdout=subprocess.DEVNULL, stderr=stderr)
    seconds["find"] = time.monotonic() - started
    if found.returncode != 0:
        raise BinFailure(f"{name}: the finder exited {found.returncode}")
    started = time.monotonic()
    record_bytes = record_file.read_bytes()
    try:
        record = finding_record.parse_record(record_bytes.decode("utf-8"))
    except finding_record.RecordFormatError as error:
        raise BinFailure(f"{name}: the finding record is refused: {error}") from error
    data_sha256 = stream_sha256(data_file)
    if record["header"]["data_sha256"] != data_sha256 or truth_header["data_sha256"] != data_sha256:
        raise BinFailure(f"{name}: data_sha256 of the record {record['header']['data_sha256']} or of the truth {truth_header['data_sha256']} is not the data file's {data_sha256}; kept")
    if len(record["events"]) != events:
        raise BinFailure(f"{name}: the record holds {len(record['events'])} events, not {events}")
    result = {"name": name, "stratum": stratum, "configuration_sha256": record["header"]["configuration_sha256"],
              "vertex_configuration_sha256": record["header"].get("vertex_configuration_sha256", "none"),
              "hashes": {"data_sha256": data_sha256, "truth_sha256": stream_sha256(truth_file), "record_sha256": hashlib.sha256(record_bytes).hexdigest()}}
    if fixture == "noise":
        try:
            rows = score_bin(record, truth_file)
        except ValueError as error:
            raise BinFailure(f"{name}: {error}") from error
        counts = format_counts(rows)
        (out / f"{name}.counts").write_text(counts, encoding="utf-8")
        result["hashes"]["counts_sha256"] = hashlib.sha256(counts.encode()).hexdigest()
        result["rate"] = rate_rule([row[1] for row in rows], [row[2] for row in rows])
    seconds["score"] = time.monotonic() - started
    known = {data_file: data_sha256, truth_file: result["hashes"]["truth_sha256"], record_file: result["hashes"]["record_sha256"]}
    files = [(path, known.get(path) or stream_sha256(path), path.stat().st_size) for path in (data_file, truth_file, record_file, product_file, stderr_file, out / f"{name}.counts") if path.exists()]
    result["files"] = [(path.name, digest, size, "kept") for path, digest, size in files]
    if delete_data and fixture == "noise":
        result["deletion"] = (data_file, [record["header"]["data_sha256"], truth_header["data_sha256"]])
    result["seconds"] = seconds
    return result


def parse_strata(text: str) -> list:
    strata = []
    for part in text.split(","):
        low, _, high = part.partition("-")
        strata += list(range(int(low), int(high or low) + 1))
    if not strata or len(set(strata)) != len(strata) or not set(strata) <= set(STRATA):
        raise ValueError(f"strata {text}: each of 0 to 11 at most once")
    return strata


def run(arguments) -> int:
    out = Path(arguments.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "run.log", "a", encoding="utf-8") as log:
        def say(line: str) -> None:
            print(line, flush=True)
            log.write(line + "\n")
            log.flush()

        return _run(arguments, out, say)


def _run(arguments, out: Path, say) -> int:
    events = arguments.events_per_bin or FREEZE_B_EVENTS_PER_BIN[arguments.fixture]
    strata = parse_strata(arguments.strata)
    say(f"RUN fixture {arguments.fixture} block {arguments.block} strata {strata} events_per_bin {events} delete_noise_data {int(arguments.delete_noise_data)}")
    results, failures = [], []
    with concurrent.futures.ThreadPoolExecutor(arguments.workers) as pool:
        futures = {pool.submit(run_bin, Path(arguments.generator), Path(arguments.finder), arguments.fixture, arguments.block, stratum, events, out,
                               arguments.product_events, arguments.delete_noise_data): stratum for stratum in strata}
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except (BinFailure, OSError, ValueError) as error:
                failures.append(f"stratum {futures[future]}: {error}")
    results.sort(key=lambda item: item["stratum"])
    for failure in failures:
        say(f"FAIL {failure}")

    def write_listing() -> None:
        listing = [LISTING_FORMAT, f"fixture {arguments.fixture}", f"block {arguments.block}", f"events_per_bin {events}"]
        for item in results:
            listing += [f"file {name} {digest} {size} {state}" for name, digest, size, state in item["files"]]
            listing.append(f"cost {item['name']} " + " ".join(f"{step}_seconds {value:.1f}" for step, value in item["seconds"].items()))
        listing.append(f"end bins {len(results)} failed {len(failures)}")
        (out / f"{arguments.fixture}-b{arguments.block}.listing").write_text("\n".join(listing) + "\n", encoding="utf-8")

    configurations = {(item["configuration_sha256"], item["vertex_configuration_sha256"]) for item in results}
    if failures or len(configurations) != 1:
        write_listing()
        why = f"{len(failures)} of {len(strata)} bins" if failures else f"the bins ran under {len(configurations)} configurations"
        say(f"RESULT failed: {why}; no rate record is written and no data file deleted")
        return 1
    if arguments.fixture != "noise":
        write_listing()
        say(f"RESULT ok: {len(results)} clean bins produced; no rate (r_dev is the noise fixture's, section 8.3)")
        return 0
    configuration, vertex_configuration = configurations.pop()
    header = {"recipe": finding_record.FINDING_RECIPE, "configuration_sha256": configuration, "vertex_configuration_sha256": vertex_configuration,
              "fixture_id": FIXTURE_IDS["noise"], "block": arguments.block, "events_per_bin": events}
    document = {"header": header, "bins": [bin_line_values(item["stratum"], item["rate"], item["hashes"]) for item in results]}
    text = format_rate_record(document)
    record_path = out / f"noise-b{arguments.block}.rate.record"
    record_path.write_text(text, encoding="utf-8")
    parse_rate_record(record_path.read_text(encoding="utf-8"))
    # U-B11, second pass: only now, with every bin checked and the rate record written and read back, are the noise data files deleted.
    kept_back = []
    for item in results:
        if "deletion" not in item:
            continue
        data_file, expected = item["deletion"]
        deletion = delete_after_hash_match(data_file, expected)
        if deletion["deleted"]:
            item["files"] = [(file_name, digest, size, "deleted-after-hash-match" if file_name == data_file.name else state) for file_name, digest, size, state in item["files"]]
        else:
            kept_back.append(f"{item['name']}: {deletion['reason']}")
    write_listing()
    for line in kept_back:
        say(f"FAIL {line}")
    for item in document["bins"]:
        say(f"RATE block {arguments.block} stratum {item['stratum']} events {item['events']} events_without_tracks {item['events_without_tracks']} n {item['tracks']} k {item['fakes']} deff_hat {item['deff_hat']!r} "
            f"r_dev {item['r_dev']!r} l_dev {item['l_dev']!r} u_dev {item['u_dev']!r} C {item['limit']} within {item['within_limit']}")
    passed, line = evaluation_verdict(document)
    if kept_back:
        say(f"RESULT failed: {len(kept_back)} data files kept, their hash differed; {line}")
        return 1
    say(f"RESULT {'ok' if passed else 'refused'}: {line}")
    return 0 if passed else 1


def check(arguments) -> int:
    try:
        document = parse_rate_record(Path(arguments.record).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, RateRecordError) as error:
        print(f"REJECTED {arguments.record}: {error}")
        return 2
    passed, line = evaluation_verdict(document)
    print(("OK " if passed else "REFUSED ") + line)
    return 0 if passed else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run", help="generate, find and score bins of one fixture and block")
    runner.add_argument("--generator", required=True)
    runner.add_argument("--finder", required=True)
    runner.add_argument("--fixture", choices=sorted(FIXTURE_IDS), required=True)
    runner.add_argument("--block", type=int, required=True)
    runner.add_argument("--strata", default="0-11")
    runner.add_argument("--events-per-bin", type=int, default=0, help="default: section 3.2's Freeze-B run size, 12,000 noise, 3,000 clean")
    runner.add_argument("--out", required=True)
    runner.add_argument("--workers", type=int, default=1)
    runner.add_argument("--product-events", type=int, default=PRODUCT_EVENTS)
    runner.add_argument("--delete-noise-data", action="store_true", help="U-B11: delete each noise data file after its SHA-256 matched")
    checker = commands.add_parser("check", help="read a rate record and say whether evaluation may start")
    checker.add_argument("record")
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as stop:
        return 2 if stop.code else 0
    if arguments.command == "check":
        return check(arguments)
    if arguments.block not in RUN_BLOCKS:
        print(f"REJECTED block {arguments.block}: not a tuning or Freeze-B block (section 3.2: {RUN_BLOCKS})")
        return 2
    try:
        parse_strata(arguments.strata)
    except ValueError as error:
        print(f"REJECTED {error}")
        return 2
    if arguments.events_per_bin < 0 or arguments.workers < 1 or arguments.product_events < 0:
        print("REJECTED events per bin, workers and product events are counts")
        return 2
    return run(arguments)


if __name__ == "__main__":
    sys.exit(main())
