#!/usr/bin/env python3
"""GB19, GB20 and GB21 (g4sim plan, Section 23): judge the runs of run_all.sh. main.cc measures; every verdict is made here.

GB19: per-event output with and without a fast-simulation model that never triggers. GB20: written-back copy numbers and per-event scorer output of
each placement implementation against ordinary placements, plus the navigator's answers. GB21: three identities on every step KillProcess defines,
in exact rational arithmetic from the hex floats, each at relative difference <= 1e-12. Negative controls must be caught by the same comparison.
A first divergence is located by rerunning both sides with a step trace. Nothing here confirms a GB: a verdict covers this host and this build only.

Usage: judge.py PROGRAM FOLDER   Prints JSON with a status key; exit 0 every criterion met and every control caught, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path

TOLERANCE = Fraction(1, 10**12)
DEPOSIT_ULPS = 4  # addendum 11.1
EQUIVALENCE_RATIO, ONE_SIDED_Z = 1.005, 1.6448536269514722  # addendum 11.1: margin ln 1.005, alpha 0.05
TRACE_FIELDS = ("pre_x", "pre_y", "pre_z", "post_x", "post_y", "post_z", "direction_x", "direction_y", "direction_z", "step_length", "deposit", "pre_kinetic", "post_kinetic", "post_time",
                "pre_safety", "post_safety")
COMPARED = ("cells", "navigation", "trace", "random", "random_end", "steps")
# (layout, implementation): every pair judged against ordinary placements of that layout
PLACEMENT_PAIRS = (("linear_exact", "replica"), ("linear_exact", "parameterised"), ("linear_exact", "assembly"), ("linear_decimal", "replica"), ("linear_decimal", "parameterised"),
                   ("linear_decimal", "assembly"), ("gapped", "parameterised"), ("gapped", "assembly"), ("grid8", "parameterised"), ("grid8", "assembly"), ("grid6", "parameterised"),
                   ("grid6", "assembly"), ("ring", "parameterised"), ("ring", "assembly"), ("module", "assembly"))
NOT_COMPARED = {"replica on gapped": "G4PVReplica slices fill the mother: the program refuses it (exit recorded in gb20-gapped-replica.exit)",
                "replica on grid6, grid8": "G4PVReplica is one axis; a two-index grid needs two nested levels, which is another tree than one packed placement",
                "replica on ring": "G4PVReplica in phi needs tube-sector slices of a tube mother; the ring of boxes has no such form",
                "replica on module": "two different logicals per pitch; a replica repeats one logical",
                "assembly against ordinary_module": "an assembly has no mother per module, so it is another tree than a module template: reported under module_template, not as a pair"}


def load(folder: Path, name: str) -> dict:
    return json.loads((folder / name).read_text(encoding="utf-8"))


def compare_events(first: dict, second: dict) -> dict:
    """How many events differ, field by field."""
    pairs = list(zip(first["events"], second["events"]))
    counts = {field: sum(a[field] != b[field] for a, b in pairs) for field in COMPARED}
    differing = [a["event"] for a, b in pairs if any(a[field] != b[field] for field in COMPARED)]
    return {"events": len(pairs), "same_count": len(first["events"]) == len(second["events"]), "events_differing": counts, "first_differing_event": differing[0] if differing else None,
            "differing_event_ids": differing[:20], "identical": not differing and len(first["events"]) == len(second["events"]) and bool(pairs)}


def deposit_differences(first: dict, second: dict) -> dict:
    """The size of what differs in the scorer: largest relative change of one cell's deposit, and of an event's whole deposit."""
    worst_cell, worst_event = 0.0, 0.0
    for a, b in zip(first["events"], second["events"]):
        if a["cells"] == b["cells"]:
            continue
        left, right = ({row[0]: float.fromhex(row[1]) for row in side["cells"]} for side in (a, b))
        for key in set(left) & set(right):
            if max(left[key], right[key]) > 0:
                worst_cell = max(worst_cell, abs(left[key] - right[key]) / max(left[key], right[key]))
        total_left, total_right = math.fsum(left.values()), math.fsum(right.values())
        if max(total_left, total_right) > 0:
            worst_event = max(worst_event, abs(total_left - total_right) / max(total_left, total_right))
    return {"largest_relative_cell_deposit_difference": worst_cell, "largest_relative_event_deposit_difference": worst_event}


def ulps(a: float, b: float) -> float:
    return abs(a - b) / math.ulp(max(abs(a), abs(b))) if max(abs(a), abs(b)) > 0 else 0.0


def first_divergence(program: str, folder: Path, side_a: list, side_b: list, event: int) -> dict:
    """Rerun both sides up to EVENT with a step trace and name the first step that differs. side_*: mode and arguments before the event count."""
    lines = []
    for label, side in (("a", side_a), ("b", side_b)):
        trace = folder / f"trace-{label}.txt"
        subprocess.run([program, side[0], str(folder / f"trace-{label}.json"), *side[1:], str(event + 1), str(event), str(trace)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        lines.append(trace.read_text(encoding="utf-8").splitlines())
    for index, (a, b) in enumerate(zip(*lines)):
        if a == b:
            continue
        left, right = a.split(), b.split()
        report = {"event": event, "step_in_event": index, "steps": [len(lines[0]), len(lines[1])], "track": left[0], "particle": left[1], "process": [left[2], right[2]], "from": [left[3], right[3]],
                  "to": [left[4], right[4]], "step_of_track": left[-2]}
        if left[:2] == right[:2]:
            changed = {}
            for name, x, y in zip(TRACE_FIELDS, left[5:-2], right[5:-2]):
                if x != y:
                    changed[name] = {"a": x, "b": y, "ulps": ulps(float.fromhex(x), float.fromhex(y))}
            report["changed"] = changed
            report["random_state_before_step_same"] = index == 0 or lines[0][index - 1].split()[-1] == lines[1][index - 1].split()[-1]
            report["random_state_after_step_same"] = left[-1] == right[-1]
        return report
    return {"event": event, "step_in_event": None, "steps": [len(lines[0]), len(lines[1])]}


def flipped(run: dict, field: str) -> dict:
    """A copy of a run with the last hex digit of one deposit changed: the comparison must see one bit."""
    copy = json.loads(json.dumps(run))
    for event in copy["events"]:
        for row in event["cells"]:
            if float.fromhex(row[1]) > 0:
                exact = float.fromhex(row[1])
                row[1] = math.nextafter(exact, math.inf).hex()
                return copy
    raise ValueError(f"no deposit to flip in {field}")


def event_totals(run: dict) -> list:
    return [math.fsum(float.fromhex(row[1]) for row in event["cells"]) for event in run["events"]]


def paired_equivalence(first: list, second: list) -> dict:
    """GB19 as restated by addendum 11.1: TOST on the per-event differences, the margin ln 1.005 of the mean; paired, because the seeds are the same."""
    differences = [b - a for a, b in zip(first, second)]
    mean = math.fsum(differences) / len(differences)
    spread = math.sqrt(math.fsum((value - mean) ** 2 for value in differences) / (len(differences) - 1))
    error = spread / math.sqrt(len(differences))
    margin = math.log(EQUIVALENCE_RATIO) * math.fsum(first) / len(first)
    return {"events": len(differences), "mean_difference": mean, "standard_error": error, "margin": margin, "equivalent": abs(mean) + ONE_SIDED_Z * error <= margin}


def judge_hook(program: str, folder: Path) -> dict:
    criterion, live = {}, {}
    for seed in (11, 12):
        plain, hooked = load(folder, f"gb19-none-{seed}.json"), load(folder, f"gb19-idle-{seed}.json")
        comparison = compare_events(plain, hooked)
        if comparison["first_differing_event"] is not None:
            comparison["first_divergence"] = first_divergence(program, folder, ["gb19", "none", str(seed)], ["gb19", "idle", str(seed)], comparison["first_differing_event"])
            comparison.update(deposit_differences(plain, hooked))
        criterion[f"seed_{seed}"] = comparison
        live[f"seed_{seed}"] = {"hook_counts": hooked["hook_counts"], "fast_process_on_every_listed_particle": all("fastSimProcess" in text for text in hooked["processes"].values()),
                                "hook_asked_and_never_acted": hooked["hook_counts"]["trigger"] > 0 and hooked["hook_counts"]["do_it"] == 0}
    plain = load(folder, "gb19-none-11.json")
    repeat = compare_events(plain, load(folder, "gb19-none-11-again.json"))
    controls = {name: compare_events(plain, load(folder, f"gb19-{name}-11.json")) for name in ("consuming", "triggering")}
    other_seed = compare_events(plain, load(folder, "gb19-none-12.json"))
    bit = compare_events(plain, flipped(plain, "gb19"))
    localisation = {name: compare_events(plain, load(folder, f"gb19-{name}-11.json")) for name in ("region_only", "process_only", "inert_process")}
    detected = {"repeat_of_a_run_is_identical": repeat["identical"], "hook_drawing_a_random_number_detected": not controls["consuming"]["identical"], "triggering_model_detected": not controls["triggering"]["identical"],
                "other_seed_detected": not other_seed["identical"], "one_bit_in_one_deposit_detected": not bit["identical"]}
    plain_totals = [value for seed in (11, 12) for value in event_totals(load(folder, f"gb19-none-{seed}.json"))]
    hooked_totals = [value for seed in (11, 12) for value in event_totals(load(folder, f"gb19-idle-{seed}.json"))]
    equivalence = paired_equivalence(plain_totals, hooked_totals)
    detected["deposit_scaled_by_one_percent_rejected"] = not paired_equivalence(plain_totals, [value * 1.01 for value in hooked_totals])["equivalent"]
    met = equivalence["equivalent"]
    ready = all(detected.values()) and all(side["hook_asked_and_never_acted"] and side["fast_process_on_every_listed_particle"] for side in live.values())
    return {"criterion_met": met, "comparison_trustworthy": ready, "equivalence": equivalence, "bit_identical": all(side["identical"] for side in criterion.values()), "with_against_without": criterion, "hook_live": live, "controls": detected, "control_counts": {name: value["events_differing"] for name, value in controls.items()},
            "what_causes_it": {name: {"identical": value["identical"], "differing_event_ids": value["differing_event_ids"]} for name, value in localisation.items()}}


def tree_rows(run: dict) -> dict:
    return {row[0]: row[1:] for row in run["tree"]}


def compare_placements(program: str, folder: Path, layout: str, reference: str, candidate: str) -> dict:
    report = {}
    same = True
    for beam in ("geantino", "physics"):
        first, second = load(folder, f"gb20-{layout}-{reference}-{beam}.json"), load(folder, f"gb20-{layout}-{candidate}-{beam}.json")
        comparison = compare_events(first, second)
        left, right = tree_rows(first), tree_rows(second)
        comparison["written_back_copy_numbers_identical"] = set(left) == set(right) and len(first["tree"]) == len(second["tree"])
        comparison["written_back_rows_differing"] = sum(left[key] != right.get(key) for key in left)
        comparison["scan_points_differing"] = sum(a != b for a, b in zip(first["scan"], second["scan"]))
        comparison["scan_points"] = len(first["scan"])
        comparison["scorer_identical"] = comparison["events_differing"]["cells"] == 0 and comparison["same_count"]
        comparison["navigation_identical"] = comparison["events_differing"]["navigation"] == 0 and comparison["scan_points_differing"] == 0
        comparison.update(deposit_differences(first, second))
        hit = sum(bool(event["cells"]) for event in first["events"])
        comparison["events_with_scorer_entries"] = hit
        if comparison["first_differing_event"] is not None and comparison["written_back_copy_numbers_identical"]:
            arguments = lambda name: ["gb20", layout, name, beam, str(first["seed"])]  # noqa: E731
            comparison["first_divergence"] = first_divergence(program, folder, arguments(reference), arguments(candidate), comparison["first_differing_event"])
        same = same and comparison["written_back_copy_numbers_identical"] and comparison["scorer_identical"] and comparison["navigation_identical"] and hit > 0
        report[beam] = comparison
    report["criterion_met"] = same
    return report


def judge_placements(program: str, folder: Path) -> dict:
    pairs = {f"{layout}/{impl}": compare_placements(program, folder, layout, "ordinary", impl) for layout, impl in PLACEMENT_PAIRS}
    plain = load(folder, "gb20-linear_exact-ordinary-physics.json")
    raw = {layout: compare_placements(program, folder, layout, "ordinary", "assembly_raw") for layout in ("linear_exact",)}["linear_exact"]
    nudged = compare_placements(program, folder, "linear_exact", "ordinary", "ordinary_nudged")
    other_seed = compare_events(plain, load(folder, "gb20-linear_exact-ordinary-physics-seed22.json"))
    detected = {"repeat_of_a_run_is_identical": compare_events(plain, load(folder, "gb20-linear_exact-ordinary-physics-again.json"))["identical"],
                "assembly_without_copy_number_pass_detected": not raw["physics"]["written_back_copy_numbers_identical"] and not raw["physics"]["scorer_identical"],
                "centre_moved_one_ulp_detected": nudged["physics"]["written_back_rows_differing"] > 0 and not nudged["physics"]["scorer_identical"],
                "other_seed_detected": not other_seed["identical"], "one_bit_in_one_deposit_detected": not compare_events(plain, flipped(plain, "gb20"))["identical"]}
    refused = (folder / "gb20-gapped-replica.exit").read_text(encoding="utf-8").strip() == "2"
    module = compare_placements(program, folder, "module", "ordinary_module", "assembly")
    return {"criterion_met": all(pair["criterion_met"] for name, pair in pairs.items() if name.endswith("/assembly")), "comparison_trustworthy": all(detected.values()) and refused, "summary": {name: pair["criterion_met"] for name, pair in pairs.items()},
            "pairs": pairs, "controls": detected, "control_counts": {"assembly_raw": raw["physics"]["events_differing"], "ordinary_nudged": nudged["physics"]["events_differing"]},
            "module_template": {"assembly_against_ordinary_module": {beam: {key: module[beam][key] for key in ("written_back_copy_numbers_identical", "scorer_identical", "events_differing")} for beam in ("geantino", "physics")}},
            "not_compared": NOT_COMPARED, "gapped_replica_refused": refused}


def fractions_of(row: list) -> dict:
    names = ("pre", "entry", "after_probe", "killed", "deposit_at_kill", "deposit", "secondary_along", "secondary_post", "post")
    return dict(zip(names, (Fraction(float.fromhex(text)) for text in row[1:10])))


def relative(a: Fraction, b: Fraction) -> Fraction:
    scale = max(abs(a), abs(b))
    return abs(a - b) / scale if scale else Fraction(0)


def judge_kills(rows: list, ignore_secondaries: bool = False, shift: Fraction = Fraction(0)) -> dict:
    """The three identities on every kill step. Continuous loss = pre-step kinetic energy - kinetic energy left by the along-step processes - along-step secondaries."""
    worst = {"deposit_is_continuous_loss": Fraction(0), "killed_is_kinetic_before_kill": Fraction(0), "sum": Fraction(0)}
    over = Counter()
    resolved_worst, resolved_rows, unresolved_rows, unresolved_over, worst_unresolved_ulps = Fraction(0), 0, 0, 0, 0.0
    both = with_post_secondary = with_along_secondary = both_and_secondary = 0
    particles = Counter()
    bit_exact = 0
    worst_over_ulps = worst_deposit_ulps = 0.0
    over_both = 0
    for row in rows:
        v = fractions_of(row)
        loss = v["pre"] - v["entry"] - v["secondary_along"]
        secondaries = 0 if ignore_secondaries else v["secondary_along"] + v["secondary_post"]
        total = v["deposit"] + v["killed"] + v["pre"] * shift
        checks = {"deposit_is_continuous_loss": relative(v["deposit"], loss), "killed_is_kinetic_before_kill": relative(v["killed"], v["after_probe"]), "sum": relative(total, v["pre"] - secondaries)}
        for name, value in checks.items():
            worst[name] = max(worst[name], value)
            over[name] += value > TOLERANCE
        deposit_ulps = float(abs(v["deposit"] - loss) / Fraction(math.ulp(float(v["pre"]))))
        worst_deposit_ulps = max(worst_deposit_ulps, deposit_ulps)
        over_both += checks["deposit_is_continuous_loss"] > TOLERANCE and deposit_ulps > DEPOSIT_ULPS
        if checks["deposit_is_continuous_loss"] > TOLERANCE:
            worst_over_ulps = max(worst_over_ulps, float(abs(v["deposit"] - loss) / Fraction(math.ulp(float(v["pre"])))))
        has_loss = v["deposit"] > 0 and loss > 0
        both += has_loss
        with_post_secondary += v["secondary_post"] > 0
        with_along_secondary += v["secondary_along"] > 0
        both_and_secondary += has_loss and (v["secondary_post"] > 0 or v["secondary_along"] > 0)
        if has_loss:
            particles[row[0]] += 1
            # a double holding the kinetic energy resolves it to half an ulp; below this loss a 1e-12 comparison of the difference cannot be made
            half_ulp = Fraction(math.ulp(float(v["pre"]))) / 2
            pre, deposit = float(v["pre"]), float(v["deposit"])
            bit_exact += float(v["entry"]) == pre + ((pre - deposit) - pre) or float(v["entry"]) == pre - deposit
            if half_ulp / loss <= TOLERANCE:
                resolved_rows += 1
                resolved_worst = max(resolved_worst, checks["deposit_is_continuous_loss"])
            else:
                unresolved_rows += 1
                unresolved_over += checks["deposit_is_continuous_loss"] > TOLERANCE
                worst_unresolved_ulps = max(worst_unresolved_ulps, float(abs(v["deposit"] - loss) / (2 * half_ulp)))
    return {"kill_steps": len(rows), "with_continuous_loss": both, "with_post_step_secondary": with_post_secondary, "with_along_step_secondary": with_along_secondary, "continuous_loss_and_secondary": both_and_secondary,
            "worst_relative": {name: float(value) for name, value in worst.items()}, "steps_over_tolerance": {name: over[name] for name in worst},
            "resolvable": {"steps": resolved_rows, "worst_deposit_relative": float(resolved_worst), "note": "loss large enough that half an ulp of the kinetic energy is <= 1e-12 of it"},
            "not_resolvable": {"steps": unresolved_rows, "over_tolerance": unresolved_over, "worst_difference_in_ulps_of_pre_kinetic": worst_unresolved_ulps},
            "deposit_worst_ulps_of_pre_kinetic": worst_deposit_ulps, "deposit_over_both_limits": over_both, "over_tolerance_worst_difference_in_ulps_of_pre_kinetic": worst_over_ulps, "kinetic_equals_rounded_pre_minus_deposit_bit_for_bit": bit_exact, "by_particle": dict(particles),
            "deposit_unchanged_by_the_kill": sum(row[5] == row[6] for row in rows), "post_kinetic_zero_and_status_stop_and_kill": sum(row[9] == "0x0p+0" and row[10] == 2 for row in rows)}


def judge_kill_runs(folder: Path) -> dict:
    runs = {name: load(folder, f"gb21-{name}.json") for name in ("plain", "emit", "pixe", "booked_as_deposit", "pre_step_energy")}
    judged = {name: judge_kills(runs[name]["kills"]) for name in ("plain", "emit", "pixe")}
    for name, value in judged.items():
        value["kill_defined_but_track_stopped_first"] = runs[name]["defined_without_do_it"]
    booked, early = judge_kills(runs["booked_as_deposit"]["kills"]), judge_kills(runs["pre_step_energy"]["kills"])
    no_secondaries = judge_kills(runs["emit"]["kills"], ignore_secondaries=True)
    just_over, just_under = judge_kills(runs["plain"]["kills"], shift=Fraction(2, 10**12)), judge_kills(runs["plain"]["kills"], shift=Fraction(1, 2 * 10**12))
    detected = {"kill_booked_as_deposit_fails_deposit_and_sum": booked["steps_over_tolerance"]["deposit_is_continuous_loss"] > 0 and booked["steps_over_tolerance"]["sum"] > 0,
                "pre_step_energy_as_killed_fails_kill_and_sum": early["steps_over_tolerance"]["killed_is_kinetic_before_kill"] > 0 and early["steps_over_tolerance"]["sum"] > 0,
                "sum_without_secondaries_fails": no_secondaries["steps_over_tolerance"]["sum"] > 0, "sum_off_by_2e-12_fails": just_over["steps_over_tolerance"]["sum"] == just_over["kill_steps"],
                "sum_off_by_5e-13_passes": just_under["steps_over_tolerance"]["sum"] == 0}
    sum_and_kill = all(value["steps_over_tolerance"]["sum"] == 0 and value["steps_over_tolerance"]["killed_is_kinetic_before_kill"] == 0 for value in judged.values())
    deposit_literal = all(value["steps_over_tolerance"]["deposit_is_continuous_loss"] == 0 for value in judged.values())
    deposit_in_ulps = all(value["deposit_over_both_limits"] == 0 for value in judged.values())
    detected["kill_booked_as_deposit_exceeds_both_limits"] = booked["deposit_over_both_limits"] > 0
    exercised = judged["plain"]["with_continuous_loss"] > 0 and judged["emit"]["continuous_loss_and_secondary"] > 0 and judged["pixe"]["with_along_step_secondary"] > 0
    return {"criterion_met": sum_and_kill and deposit_in_ulps and exercised, "deposit_within_the_ulp_limit": deposit_in_ulps, "comparison_trustworthy": all(detected.values()) and exercised, "killed_and_sum_identities_met": sum_and_kill, "deposit_identity_met_as_written": deposit_literal,
            "runs": judged, "controls": detected, "control_counts": {"booked_as_deposit": booked["steps_over_tolerance"], "pre_step_energy": early["steps_over_tolerance"], "emit_without_secondaries": no_secondaries["steps_over_tolerance"]}}


def main() -> int:
    if len(sys.argv) != 3 or not Path(sys.argv[2]).is_dir():
        print(json.dumps({"status": "rejected", "message": "usage: judge.py PROGRAM FOLDER"}))
        return 2
    program, folder = sys.argv[1], Path(sys.argv[2])
    try:
        verdicts = {"GB19": judge_hook(program, folder), "GB20": judge_placements(program, folder), "GB21": judge_kill_runs(folder)}
    except (OSError, ValueError, KeyError) as problem:
        print(json.dumps({"status": "rejected", "message": f"{type(problem).__name__}: {problem}"}))
        return 2
    met = all(value["criterion_met"] and value["comparison_trustworthy"] for value in verdicts.values())
    print(json.dumps({"status": "ok" if met else "failed", "scope": "E5 only, one host and build; not a confirmation", **verdicts}, indent=1))
    return 0 if met else 1


if __name__ == "__main__":
    sys.exit(main())
