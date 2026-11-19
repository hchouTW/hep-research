#!/usr/bin/env python3
"""T07 tracking (adapters/acts-tracking): generate, find and refit a few synthetic telescope events through the thin wrapper.

ILLUSTRATIVE and SYNTHETIC. Two events of the frozen fixture t07-telescope-clean/1 (block 1, the tuning block; stratum 0: the lowest
momentum bin, 1.5 to 3 GeV, occupancy o1, six tracks from one vertex, no noise hits) on the eight-plane telescope in 1 T, through
adapters/acts-tracking/assets/acts_tracking.py on ACTS 48.2.0. Names no experiment. Makes no tracking quality claim: the counts below
are what the programs wrote, not an efficiency; T07's evaluation ended failed at attempt 1, final (decisions.md, "T07: final").
- generate-fixture writes a data file (role reconstruction-input: hits only) and a truth file (role truth), apart.
- find (recipe reco.track.acts-ckf-planar/1, data side) reads the data file alone: seeds from hits, CKF, ambiguity resolution and a
  fit per selected track. Its product says finding.
- refit (recipe reco.track.acts-kf-refit/1) fits each particle's own hits, which this script reads from the truth file on the scoring
  side after the finder has finished: truth-assisted, counted apart, never reported as finding (BP03; scenario A39). Its product is
  acts-tracking-product/2 with R33's track-fit outputs.

Modes:
  offline replay (default): reads --recorded (default recorded/: the finder's record and product, the hit sets, the refit's product and
    runs.json, the wrapper's reports with the folders replaced by <build> and <work>), checks the labels and identities below, and writes
    summary.json and report.md to --out (default output/); the result is byte-identical to the committed output/
    (tests/examples/test_reconstruction_tracking.py). Standard library and the adapter's two product readers only.
  live (--live; the built programs from --build-dir or HEP_ACTS_TRACKING_BUILD; NumPy, for the fixture file readers): runs the three
    operations in --work (a temporary folder by default, outside the plugin), rewrites --recorded and replays. Built only by the T07
    build job, so the committed recorded/ comes from such a job (VALIDATION ACTS-TRACKING-T07).

Checks, every one must pass (exit 0, else 1): each wrapper operation ok with exit 0; the finder's command names no truth file; the
record and both products name the same data file (SHA-256), which is the generated one; the record and the finder's product say
recipe reco.track.acts-ckf-planar/1, stage find-ckf, evidence class data-side, reported as finding; the refit's product says recipe
reco.track.acts-kf-refit/1, stage refit-known-hit-set, evidence class truth-assisted, not reported as finding, format
acts-tracking-product/2 with every R33 record; the hit sets say role truth-assisted, and the refit's product names their SHA-256; the
finder's product keeps predicted, filtered and smoothed apart at each measured surface and holds the record's selected tracks of its events.

Expected readings, stated before the first live run and checked by nobody: the finder selects 12 tracks (6 per event), no event is
search-truncated and none fails; the refit fits 12 hit sets of 8 hits, none fails.
A different count is a reading to explain, not a failed check.

Usage (from the plugin root): python3 examples/reconstruction-tracking/run.py [--out DIR] [--recorded DIR]
       python3 examples/reconstruction-tracking/run.py --live [--build-dir DIR] [--work DIR] [--recorded DIR] [--out DIR]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[1]
ASSETS = PLUGIN / "adapters" / "acts-tracking" / "assets"
WRAPPER = ASSETS / "acts_tracking.py"
sys.path.insert(0, str(ASSETS / "fixture_tools"))
import acts_finding_record as finding_record  # noqa: E402
import acts_native_product as native_product  # noqa: E402

FIXTURE, BLOCK, STRATUM, FIRST_EVENT, EVENTS = "clean", 1, 0, 0, 2
FIELD_TESLA = "1"
FIND_ID, REFIT_ID = "example-reconstruction-tracking-find", "example-reconstruction-tracking-refit"
FINDING_RECIPE, REFIT_RECIPE = "reco.track.acts-ckf-planar/1", "reco.track.acts-kf-refit/1"
RECORDED_FILES = ("runs.json", "find.record", "find.product", "refit.hitsets", "refit.product")
REPORT_FIELDS = ("operation", "status", "exit_code", "reason", "program_exit", "program_stderr")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n", encoding="utf-8")


# ---- live: the three operations through the wrapper.

def wrapper_run(arguments: list, build_dir: str, work: Path) -> dict:
    finished = subprocess.run([sys.executable, str(WRAPPER), *arguments, "--build-dir", build_dir], capture_output=True, text=True, timeout=3600)
    try:
        report = json.loads(finished.stdout)
    except ValueError:
        report = {"operation": arguments[0], "status": "failed", "exit_code": finished.returncode, "reason": f"the wrapper wrote no report: {finished.stderr[-500:]}"}
    kept = {name: report[name] for name in REPORT_FIELDS if name in report}
    kept["command"] = [str(token).replace(str(Path(build_dir).resolve()), "<build>").replace(build_dir, "<build>").replace(str(work), "<work>")
                       for token in report.get("command", [])]
    kept["program_stdout"] = json.loads(report["program_stdout"]) if report.get("program_stdout", "").strip().startswith("{") else report.get("program_stdout", "")
    return kept


def live(build_dir: str, work: Path, recorded: Path) -> int:
    import t07_fixture_files as fixture_files  # noqa: E402  NumPy: the live mode only
    import t07_truth_files as truth_files  # noqa: E402  scoring side: read after the finder has finished

    work.mkdir(parents=True, exist_ok=True)
    data_file, truth_file = work / "events.t07data", work / "events.t07truth"
    runs = [wrapper_run(["generate-fixture", "--fixture", FIXTURE, "--block", str(BLOCK), "--stratum", str(STRATUM), "--first-event", str(FIRST_EVENT),
                         "--count", str(EVENTS), "--data-file", str(data_file), "--truth-file", str(truth_file)], build_dir, work)]
    if runs[-1]["exit_code"] != 0:
        print(json.dumps(runs[-1], indent=1))
        return runs[-1]["exit_code"]
    runs.append(wrapper_run(["find", "--data-file", str(data_file), "--product-id", FIND_ID, "--product-file", str(work / "find.product"),
                             "--record-file", str(work / "find.record"), "--product-events", str(EVENTS)], build_dir, work))
    if runs[-1]["exit_code"] != 0:
        print(json.dumps(runs[-1], indent=1))
        return runs[-1]["exit_code"]
    hit_sets = []
    for ordinal, event in enumerate(truth_files.iter_truth_events(truth_file)):
        for track in event["tracks"]:
            keys = [int(key) for key in track["hit_keys"] if int(key) != truth_files.NO_HIT_KEY]
            hit_sets.append((f"event-{ordinal}-particle-{int(track['particle_key'])}", ordinal, float(track["q_over_p"]), keys))
    (work / "refit.hitsets").write_text(fixture_files.hit_sets_text(fixture_files.file_sha256(data_file), hit_sets), encoding="utf-8")
    runs.append(wrapper_run(["refit", "--data-file", str(data_file), "--hit-sets", str(work / "refit.hitsets"), "--field-tesla", FIELD_TESLA,
                             "--product-id", REFIT_ID, "--product-file", str(work / "refit.product")], build_dir, work))
    if runs[-1]["exit_code"] != 0:
        print(json.dumps(runs[-1], indent=1))
        return runs[-1]["exit_code"]
    recorded.mkdir(parents=True, exist_ok=True)
    for name in RECORDED_FILES[1:]:
        shutil.copyfile(work / name, recorded / name)
    write_json(recorded / "runs.json", {"fixture": f"t07-telescope-{FIXTURE}/1", "block": BLOCK, "stratum": STRATUM, "first_event": FIRST_EVENT, "events": EVENTS,
                                        "field_tesla": float(FIELD_TESLA), "data_sha256": sha256_bytes(data_file.read_bytes()),
                                        "truth_sha256": sha256_bytes(truth_file.read_bytes()), "runs": runs})
    return 0


# ---- offline replay.

def replay(recorded: Path) -> tuple:
    runs = json.loads((recorded / "runs.json").read_text(encoding="utf-8"))
    record_text = (recorded / "find.record").read_text(encoding="utf-8")
    record = finding_record.parse_record(record_text)
    found = native_product.parse_product((recorded / "find.product").read_text(encoding="utf-8"))
    hit_sets_text = (recorded / "refit.hitsets").read_text(encoding="utf-8")
    refit = native_product.parse_product((recorded / "refit.product").read_text(encoding="utf-8"))
    by_operation = {run["operation"]: run for run in runs["runs"]}
    found_summary, refit_summary = native_product.fit_summary(found), native_product.fit_summary(refit)
    # At each measured surface a predicted, a filtered and a smoothed record, and the update moved the state (the rule of tests/adapters/test_acts_finding.py).
    parameters = {(item["track_key"], item["state_index"], item["state_type"]): item["parameters"] for item in found["parameters"]}
    measured = [[parameters.get((state["track_key"], state["index"], name)) for name in native_product.STATE_TYPES] for state in found["states"] if state["kind"] == "measurement"]
    selected = {item["key"] for event in record["events"][:record["header"]["product_events"]] for item in event["found"] if item["outcome"] == "selected"}
    checks = [
        ("every wrapper operation is ok with exit 0", [run["operation"] for run in runs["runs"]] == ["generate-fixture", "find", "refit"]
         and all(run["status"] == "ok" and run["exit_code"] == 0 for run in runs["runs"])),
        ("the finder's command names no truth file", not any(token.endswith(".t07truth") for token in by_operation["find"]["command"])),
        ("the record and both products name the generated data file", record["header"]["data_sha256"] == found["header"]["data_sha256"]
         == refit["header"]["data_sha256"] == runs["data_sha256"]),
        ("the record says finding, on the data side", (record["header"]["recipe"], record["header"]["stage"], record["header"]["evidence_class"])
         == (FINDING_RECIPE, finding_record.FINDING_STAGE, finding_record.FINDING_EVIDENCE_CLASS)),
        ("the finder's product says finding, on the data side", (found["header"]["recipe"], found_summary["stage"], found_summary["evidence_class"],
                                                                 found_summary["reported_as_finding"]) == (FINDING_RECIPE, "find-ckf", "data-side", True)),
        ("the refit's product is truth-assisted and never finding", (refit["header"]["recipe"], refit_summary["stage"], refit_summary["evidence_class"],
                                                                     refit_summary["reported_as_finding"]) == (REFIT_RECIPE, "refit-known-hit-set", "truth-assisted", False)),
        ("the refit's product holds every R33 record", refit.get("format") == native_product.PRODUCT_FORMAT_R33 and native_product.r33_defects(refit) == []),
        ("the hit sets are truth-assisted and the refit names them", hit_sets_text.split("\n")[1] == "role truth-assisted"
         and refit["header"]["hit_sets_sha256"] == sha256_bytes(hit_sets_text.encode("utf-8"))),
        ("predicted, filtered and smoothed stay apart in the finder's product", bool(measured) and all(None not in kept and kept[0] != kept[1] for kept in measured)),
        ("the finder's product holds the record's selected tracks", selected == {track["key"] for track in found["tracks"]}),
    ]
    events = [{name: event[name] for name in ("ordinal", "hit_count", "seeds_found", "candidates", "selected", "failure_category")}
              | {"search_truncated": int(event["seeds_truncated"] > 0 or event["seed_budget_reached"] == 1 or event["ambiguity_budget_reached"] == 1)}
              for event in record["events"]]
    summary = {
        "example": "reconstruction-tracking", "data": "synthetic", "quality_claim": "none: counts the programs wrote, not an efficiency (K09 at Freeze B)",
        "fixture": runs["fixture"], "block": runs["block"], "stratum": runs["stratum"], "events": runs["events"], "field_tesla": runs["field_tesla"],
        "data_sha256": runs["data_sha256"], "truth_sha256": runs["truth_sha256"],
        "acts_version": found["header"]["acts_version"],
        "finding": {"recipe": record["header"]["recipe"], "configuration_sha256": record["header"]["configuration_sha256"], "events": events,
                    "selected": sum(event["selected"] for event in events), "product": found_summary},
        "refit": {"recipe": refit["header"]["recipe"], "hit_sets": len(refit["tracks"]), "product": refit_summary},
        "recorded_sha256": {name: sha256_bytes((recorded / name).read_bytes()) for name in RECORDED_FILES},
        "checks": [{"check": name, "passed": bool(passed)} for name, passed in checks],
    }
    return summary, all(passed for _, passed in checks)


def report_text(summary: dict) -> str:
    lines = ["# T07 tracking example: generate, find, refit (synthetic)", "",
             f"Fixture {summary['fixture']}, block {summary['block']} (tuning), stratum {summary['stratum']}, {summary['events']} events, "
             f"{summary['field_tesla']:g} T, ACTS {summary['acts_version']}. Synthetic data only. No tracking quality claim: the counts are what the "
             "programs wrote, not an efficiency; T07's quality verdict waits for K09 at Freeze B.", "",
             "| Event | Hits | Seeds | Candidates | Selected | Search-truncated | Failure category |", "|---|---|---|---|---|---|---|"]
    for event in summary["finding"]["events"]:
        lines.append(f"| {event['ordinal']} | {event['hit_count']} | {event['seeds_found']} | {event['candidates']} | {event['selected']} | "
                     f"{'yes' if event['search_truncated'] else 'no'} | {event['failure_category']} |")
    found, refit = summary["finding"]["product"], summary["refit"]["product"]
    lines += ["", f"Finding ({summary['finding']['recipe']}): {summary['finding']['selected']} tracks selected, evidence class {found['evidence_class']}, "
              f"reported as finding: {'yes' if found['reported_as_finding'] else 'no'}.",
              f"Refit ({summary['refit']['recipe']}): {refit['tracks']} hit sets from the truth file, {refit['tracks'] - refit['failed']} fitted, {refit['failed']} failed, "
              f"evidence class {refit['evidence_class']}, reported as finding: {'yes' if refit['reported_as_finding'] else 'no'}. Counted apart from finding.", "",
              "| Check | Result |", "|---|---|"]
    lines += [f"| {item['check']} | {'pass' if item['passed'] else 'FAIL'} |" for item in summary["checks"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--out", default=str(HERE / "output"))
    parser.add_argument("--recorded", default=str(HERE / "recorded"))
    parser.add_argument("--live", action="store_true", help="run the three operations through the wrapper and rewrite --recorded")
    parser.add_argument("--build-dir", default=os.environ.get("HEP_ACTS_TRACKING_BUILD", ""), help="folder of the built programs (live)")
    parser.add_argument("--work", help="work folder of the live run (default: a temporary folder)")
    arguments = parser.parse_args(argv)
    recorded, out = Path(arguments.recorded), Path(arguments.out)
    if arguments.live:
        if not arguments.build_dir:
            print("the live mode needs the built programs: --build-dir or HEP_ACTS_TRACKING_BUILD", file=sys.stderr)
            return 3
        with tempfile.TemporaryDirectory() as temporary:
            code = live(arguments.build_dir, Path(arguments.work) if arguments.work else Path(temporary), recorded)
        if code != 0:
            return code
    missing = [name for name in RECORDED_FILES if not (recorded / name).is_file()]
    if missing:
        print(f"no recorded run in {recorded}: missing {', '.join(missing)}; the live mode (--live) writes it", file=sys.stderr)
        return 1
    summary, passed = replay(recorded)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "summary.json", summary)
    (out / "report.md").write_text(report_text(summary), encoding="utf-8")
    print(f"{sum(item['passed'] for item in summary['checks'])} of {len(summary['checks'])} checks pass; {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
