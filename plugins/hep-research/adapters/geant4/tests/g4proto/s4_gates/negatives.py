#!/usr/bin/env python3
"""S4 gate 10: each negative test of Section 15.1 as a real change to a scratch copy of the code, which a test must then catch (g4sim plan, Section 19.2).

A test that merely exists proves nothing, so the copy is first run unchanged, and must pass, and then with one change at a time, and must fail.
Usage: negatives.py --work DIR   Prints JSON with a status key. Exit 0 every change caught, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
COPIED = ("core", "contracts", "adapters/geant4/assets/g4sim", "tests/__init__.py", "tests/core/__init__.py", "tests/adapters/__init__.py", "tests/core/test_simulation_rng.py", "tests/core/test_simulation_response.py",
          "tests/adapters/test_g4sim_philox.py", "tests/adapters/test_g4sim_physics_check.py", "adapters/geant4/assets/g4sim_physics_check.py", "adapters/detector-simulation/assets/garfield/gas_table_query.py", "tests/adapters/test_g4sim_split.py", "tests/adapters/test_g4sim_external.py", "tests/adapters/test_simreco_strip.py", "tests/core/test_simulation_hits.py", "adapters/geant4/assets/simreco")
RNG, RESPONSE, HEADER, CHECK = "core/simulation/rng.py", "core/simulation/response.py", "adapters/geant4/assets/g4sim/Philox.hh", "adapters/geant4/assets/g4sim_physics_check.py"
PYTHON_TESTS = ("tests.core.test_simulation_rng", "tests.core.test_simulation_response")
HEADER_TESTS = ("tests.adapters.test_g4sim_philox",)
CHECK_TESTS = ("tests.adapters.test_g4sim_physics_check",)
SPLIT_TESTS = ("tests.adapters.test_g4sim_split",)
HIT_TESTS = ("tests.core.test_simulation_hits",)
EXTERNAL_TESTS = ("tests.adapters.test_g4sim_external",)
STRIP_TESTS = ("tests.adapters.test_simreco_strip",)
CROSSING = "adapters/geant4/assets/g4sim/PlaneCrossing.hh"
HITS, EVENTS, COLUMNS, STRIP = "core/simulation/hits.py", "adapters/geant4/assets/g4sim/ExternalEvents.hh", "adapters/geant4/assets/g4sim/HitColumns.hh", "adapters/geant4/assets/simreco/simreco_strip.cc"
SPLIT = "adapters/geant4/assets/g4sim/ScintillationSplit.hh"
GROUP_WORD = "word3 = self.sub_index << 16 | self.groups_used\n"
SAMPLED_BIN = "stream = rng.SubStream(key, event, volume_id, bin_index)\n        photons = bin_photons("

# Section 15.1 row, change, file, text replaced, replacement, tests that must fail
CHANGES = (
    ("Event range", "the limit on first_event + events removed", RNG, "def check_event_range(first_event: int, events: int) -> None:\n", "def check_event_range(first_event: int, events: int) -> None:\n    return\n", PYTHON_TESTS),
    ("Event range", "the check-spec rule removed", CHECK, "def card_findings(", "def event_range_findings(card):\n    return []\n\n\ndef card_findings(", CHECK_TESTS),
    ("Distinct keys", "two readouts of one name accepted", RESPONSE, "repeated = rng.distinct_keys(keys)", "repeated = []", PYTHON_TESTS),
    ("Determinism", "a stateful generator", RNG, GROUP_WORD, "SubStream.calls = getattr(SubStream, 'calls', 0) + 1\n        word3 = self.sub_index << 16 | (SubStream.calls & 0xFFFF)\n", PYTHON_TESTS),
    ("Determinism", "sequential summation", RNG, "return math.fsum(_check_summands(values))", "return sum(_check_summands(values))", PYTHON_TESTS),
    ("Determinism", "rounding each chunk before merging", RNG, "return exact_sum([value for chunk in chunks for value in chunk])", "return exact_sum([exact_sum(chunk) for chunk in chunks])", PYTHON_TESTS),
    ("Uniform variates", "a formula that can produce 1.0", RNG, "(2 * ((high << 32 | low) >> 12) + 1) * 2.0 ** -53", "(high << 32 | low) * 2.0 ** -64", PYTHON_TESTS),
    ("Uniform variates", "x0 and x1 swapped", RNG, "for high, low in ((x0, x1), (x2, x3))", "for high, low in ((x1, x0), (x3, x2))", PYTHON_TESTS),
    ("Uniform variates", "x0 and x1 swapped in C++", HEADER, "return {UniformOf(words[0], words[1]), UniformOf(words[2], words[3])};", "return {UniformOf(words[1], words[0]), UniformOf(words[3], words[2])};", HEADER_TESTS),
    ("fsum", "the final correction removed in C++", HEADER, "if (n > 0 && ((low < 0.", "if (false && n > 0 && ((low < 0.", HEADER_TESTS),
    ("fsum", "a summand of 1e300 accepted", RNG, "or abs(value) > SUMMAND_LIMIT", "", PYTHON_TESTS),
    ("Volume streams", "channel-stream sampling", RESPONSE, 'key = rng.volume_key(document["run_seed"], stage["name"], document["replica"])\n    channels =', 'key = rng.channel_key(document["run_seed"], ",".join(map_document["channels"]), stage["name"], document["replica"])\n    channels =', PYTHON_TESTS),
    ("Multinomial", "independent Poisson per channel", RESPONSE, 'stream.multinomial(photons, efficiencies(map_document, bin_index))', '[stream.poisson(photons * share) for share in efficiencies(map_document, bin_index)]', PYTHON_TESTS),
    ("Counter word 3", "two draws share an output group", RNG, GROUP_WORD, "word3 = self.sub_index << 16 | self.groups_used >> 1\n", PYTHON_TESTS),
    ("Counter word 3", "the chunk enters the counter", RESPONSE, SAMPLED_BIN, "stream = rng.SubStream(key, event, volume_id, bin_index + len(bins))\n        photons = bin_photons(", PYTHON_TESTS),
    ("Counter word 3", "a sub-index of 2^16 accepted", RNG, "if not 0 <= sub_index < MAXIMUM_SUB_INDEX:", "if not 0 <= sub_index:", PYTHON_TESTS),
    ("Split closure", "a step with mu_s = 10 in E^L", SPLIT, ": mean > kGaussianRegimeMean", ": mean >= kGaussianRegimeMean", SPLIT_TESTS),
    ("Split closure", "a split without a yield accepted", CHECK, 'findings.append(_finding("scintillation-undeclared"', '(lambda *_: None)(_finding("scintillation-undeclared"', CHECK_TESTS),
    ("Independent read", "cells read as floats", HITS, 'return int(row["event_id"]), int(row["cell"]), int(row.get("segment", 0))', 'return int(row["event_id"]), float(row["cell"]), int(row.get("segment", 0))', HIT_TESTS),
    ("Independent read", "the segment left out of a cell", HITS, 'return int(row["event_id"]), int(row["cell"]), int(row.get("segment", 0))', 'return int(row["event_id"]), int(row["cell"]), 0', HIT_TESTS),
    ("Independent read", "the owner taken for the track that made the step", HITS, 'int(row["step_track_id"])', 'int(row["track_id"])', HIT_TESTS),
    ("Independent read", "only track 1 counts as a primary", HITS, 'if int(row["parent_id"]) == 0}', 'if int(row["track_id"]) == 1}', HIT_TESTS),
    ("Independent read", "a cell split wrongly across its columns", COLUMNS, "static_cast<std::uint32_t>(cell >> 32)", "static_cast<std::uint32_t>(cell >> 31)", EXTERNAL_TESTS),
    ("Independent read", "an event allowed twice", EVENTS, 'if (!events.emplace(current, std::vector<ExternalParticle>{}).second) refuse', 'events.emplace(current, std::vector<ExternalParticle>{}); if (false) refuse', EXTERNAL_TESTS),
    ("Independent read", "a line read past its end", EVENTS, " || (particle >> extra)) refuse", ") refuse", EXTERNAL_TESTS),
    ("Independent read", "a negative count accepted", EVENTS, "if (current < 0 || left < 0) refuse", "if (current < 0) refuse", EXTERNAL_TESTS),
    ("Independent read", "a file ending inside an event accepted", EVENTS, 'if (left > 0) refuse("the file ends', 'if (false) refuse("the file ends', EXTERNAL_TESTS),
    ("Independent read", "two rows sharing draws accepted in core", RESPONSE, 'if len(set(keys)) != len(keys):', 'if False:', PYTHON_TESTS),
    ("Independent read", "two rows sharing draws accepted in simreco_strip", STRIP, "if (!seen.insert({event, cell}).second) throw", "seen.insert({event, cell}); if (false) throw", STRIP_TESTS),
    ("Independent read", "a cell of 2^53 or more accepted", STRIP, 'Whole(row, "cell", 9007199254740992.)', 'Whole(row, "cell", 1e30)', STRIP_TESTS),
    ("Independent read", "fsum of -0.0 keeps the sign", HEADER, "if (value != 0.) partials.push_back(value);", "partials.push_back(value);", HEADER_TESTS),
    ("Independent read", "chunks merged by rounding their partials", HEADER, "  return Fsum(all);\n}", "  return RoundPartials(all);\n}", HEADER_TESTS),
    ("Independent read", "a summand out of range accepted in C++", HEADER, "if (!std::isfinite(value) || std::fabs(value) > 1e290) throw", "if (false) throw", HEADER_TESTS),
    ("Independent read", "a zero time bin accepted", CHECK, "if not math.isfinite(width) or width <= 0:", "if width == -2:", CHECK_TESTS),
    ("Independent read", "a nan time bin accepted", CHECK, "if not math.isfinite(width) or width <= 0:", "if width <= 0:", CHECK_TESTS),
    ("Independent read", "a negative energy threshold accepted", CHECK, 'and 0 <= float(rule["energy_above_MeV"]) < math.inf)', ")", CHECK_TESTS),
    ("Independent read", "a plane deposit from the first piece only", HITS, 'math.fsum(deposits[(event, track, cell)])', 'float(row["edep_MeV"])', HIT_TESTS),
    ("Independent read", "a crossing on the chord in a field", CROSSING, "if (!smooth)\n", "if (true)\n", EXTERNAL_TESTS),
    ("Independent read", "a track born on a plane counted as crossing", CROSSING, "before * after < 0. || (after == 0. && before != 0.)", "before * after <= 0.", EXTERNAL_TESTS),
    ("Independent read", "two hit scorers on one template accepted", CHECK, "if template in claimed:", "if False:", CHECK_TESTS),
    ("Independent read", "a readout that cannot encode its cells accepted", CHECK, 'if "problem" in scorer.get("cell_id", {}):', "if False:", CHECK_TESTS),
    ("Independent read", "a rule naming no real region accepted", CHECK, 'if isinstance(rule, dict) and "region" in rule and rule["region"] not in regions:', "if False:", CHECK_TESTS),
    ("External sources", "the calibration workflow takes an external source", CHECK, "def card_findings(", "def calibration_findings(request):\n    return []\n\n\ndef card_findings(", CHECK_TESTS),
    ("Reference planes", "a plane without a frame accepted", CHECK, "def card_findings(", "def plane_findings(request):\n    return []\n\n\ndef card_findings(", CHECK_TESTS),
)


def run_tests(root: Path, modules: tuple) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "unittest", *modules], cwd=root, capture_output=True, text=True, timeout=300, check=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True)
    root = parser.parse_args().work.resolve()
    shutil.rmtree(root, ignore_errors=True)
    for name in COPIED:
        source, target = PLUGIN / name, root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if source.is_dir() else shutil.copy)(source, target)
    baseline = run_tests(root, PYTHON_TESTS + HEADER_TESTS + CHECK_TESTS + SPLIT_TESTS)
    if baseline.returncode:
        print(json.dumps({"status": "failed", "error": "the unchanged copy fails", "detail": baseline.stderr[-600:]}))
        return 1
    rows = []
    for row, change, file_name, before, after, modules in CHANGES:
        path = root / file_name
        original = path.read_text(encoding="utf-8")
        if before not in original:
            rows.append({"row": row, "change": change, "caught": False, "by": ["the text to change was not found"]})
            continue
        path.write_text(original.replace(before, after, 1), encoding="utf-8")
        done = run_tests(root, modules)
        path.write_text(original, encoding="utf-8")
        rows.append({"row": row, "change": change, "caught": done.returncode != 0, "by": re.findall(r"^(?:FAIL|ERROR): (\S+)", done.stderr, re.M)[:4]})
    passed = all(row["caught"] for row in rows)
    print(json.dumps({"status": "ok" if passed else "failed", "changes": len(rows), "caught": sum(row["caught"] for row in rows), "rows": rows}, indent=1))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
