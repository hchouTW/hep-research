#!/usr/bin/env python3
"""A run of a new specification (g4sim plan, Sections 8, 9.1): resolve the request, check what Geant4 really set, run, merge the workers' files, check closure.

Imported by g4sim_run.py, whose `simulate` command is the entry point. Pure helpers come first, so tests need no Geant4.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
for folder in (str(ROOT), str(Path(__file__).resolve().parent)):
    if folder not in sys.path:
        sys.path.insert(0, folder)

import g4sim_physics_check as physics_check  # noqa: E402

from core.geometry import fieldmap, identity  # noqa: E402
from core.simulation import hits, rng, source_density  # noqa: E402

AXES = {"x": 0, "y": 1, "z": 2}
CLOSURE_ULP = 2.0 ** -52
CLASSES_PER_DECADE, CLASS_OFFSET, CLASSES_PER_KIND = 4, 40, 200
KINDS = ("ionizing", "nonionizing", "photon", "zero_length")
BIRKS_TOLERANCE, EM_TOLERANCE = 1e-12, 1e-9
THREAD_FILES = ("cells", "boundary", "crossings", "primaries", "conservation", "photons")


def _in_world(frame: str, vector: list, frames: dict) -> list:
    """A position in a named frame, in world coordinates. Frames hold an origin in a template; only the world is built so far."""
    if frame == "world":
        return vector
    if frame not in frames:
        raise source_density.SourceError("source-frame", f"frame {frame!r} is not in the IR")
    if frames[frame]["in"] != "world":
        raise source_density.SourceError("source-frame", f"frame {frame!r} lies in {frames[frame]['in']}: only frames in the world are built")
    return [value + float(origin) for value, origin in zip(vector, frames[frame]["origin_mm"])]


def resolved_external(source: dict, folder: Path) -> dict:
    """A text event file by its recorded hash, inside the request's folder, as a position CSV is."""
    base = folder.resolve()
    target = (base / source["path"]).resolve()
    if Path(source["path"]).is_absolute() or not target.is_relative_to(base):
        raise source_density.SourceError("source-path", "an event file lies inside the request's folder")
    if hashlib.sha256(target.read_bytes()).hexdigest() != source["sha256"]:
        raise source_density.SourceError("source-hash", f"{source['path']} does not match its recorded hash")
    return {"density": "external", "external_path": str(target)}


def resolved_source(source: dict, frames: dict, folder: Path | None = None) -> dict:
    if source.get("density") == "external":
        return resolved_external(source, folder or Path("."))
    record = source_density.density(source)
    record["position"]["centre_mm"] = _in_world(record["position"]["frame"], record["position"]["centre_mm"], frames)
    if "point_mm" in record["direction"]:
        record["direction"]["point_mm"] = _in_world(record["direction"]["frame"], record["direction"]["point_mm"], frames)
    return record


def resolved_segmentation(block) -> dict:
    if block in (None, "none"):
        return {"kind": "none"}
    kind, body = next(iter(block.items()))
    if kind == "along_axis":
        return {"kind": kind, "axis": AXES[body["axis"]], "width_mm": [float(body["width_mm"])]}
    if kind == "polar":
        return {"kind": kind, "width_mm": [float(body["width_r_mm"])], "phi_bins": int(body["phi_bins"])}
    return {"kind": kind, "width_mm": [float(value) for value in body["width_mm"]]}


SEGMENT_AXES = {"none": 0, "along_axis": 1, "cartesian_xy": 2, "cartesian_xyz": 3, "polar": 2}


def cell_encoding(scorer: dict, kind: str, ir: dict, templates: list) -> dict:
    """How the program composes a named readout's cellID (Section 6.2.6): what each placed copy adds, as decimal text because a cellID has 64 bits, and the field of each segmentation axis. The table replaces Section 6.2.6's copy number times stride (g4sim-approvals.md), so a bitfield need not follow a grid's packing. A `problem` stops check-spec."""
    name = scorer["readout"]
    readout = ir["physical"].get("readout", {}).get(name)
    if readout is None:
        return {"problem": f"readout {name!r} is not declared by the specification"}
    if kind not in SEGMENT_AXES:
        return {"problem": f"no cellID for a {kind} segmentation"}
    fields = {field["name"]: field for field in readout["fields"]}
    bound = scorer.get("segment_fields", [])
    unbound = sorted(field["name"] for field in readout["fields"] if field["kind"] == "segmentation" and field["name"] not in bound)
    good = len(bound) == SEGMENT_AXES[kind] == len(set(bound)) and all(fields.get(item, {}).get("kind") == "segmentation" for item in bound)
    if not good or unbound:
        return {"problem": f"segment_fields {bound} must name one distinct segmentation field of readout {name!r} per axis of a {kind} segmentation, and every field no placement index fills (unbound: {unbound})"}
    children: dict = {}
    copies: dict = {}
    for placement in ir["physical"]["placements"]:
        children.setdefault(placement["mother"], []).append(placement)
        part = sum(value * fields[index]["stride"] for index, value in placement["index"].items() if index in fields)
        if copies.setdefault(placement["template"], {}).setdefault(str(placement["copy_number"]), part) != part:
            return {"problem": f"template {placement['template']} has two placements of copy {placement['copy_number']} with different indices: the table is by template and copy, so declare two templates"}
    seen: set = {0} if "world" in templates else set()

    def walk(mother: str, total: int, used: frozenset, clash: frozenset) -> str | None:
        for placement in children.get(mother, []):
            named = frozenset(placement["index"]) & set(fields)
            here = total + copies[placement["template"]][str(placement["copy_number"])]
            repeated = clash | (named & used)
            if placement["template"] in templates:
                if repeated:
                    return f"field {sorted(repeated)} is filled at two levels of one volume: the values would add"
                if here in seen:
                    return f"two volumes of template {placement['template']} have one cellID: readout {name!r} needs a field for every level that repeats (Section 19, cellIDs are unique)"
                seen.add(here)
            found = walk(placement["template"], here, used | named, repeated)
            if found:
                return found
        return None

    problem = walk("world", 0, frozenset(), frozenset())
    if problem:
        return {"problem": problem}
    return {"copies": {template: {copy: str(part) for copy, part in parts.items()} for template, parts in copies.items()}, "segments": [{"stride": fields[item]["stride"], "limit": 1 << fields[item]["width"]} for item in bound]}


def resolved_request(request: dict, ir: dict, folder: Path | None = None) -> dict:
    scorers = []
    for scorer in request.get("scorers", []):
        item = {"name": scorer["name"], "quantity": scorer["quantity"], "templates": identity.selected_templates(scorer["select"], ir), "segmentation": resolved_segmentation(scorer.get("segmentation"))}
        if "split" in scorer:
            item["split"] = scorer["split"]
        if "apportion_short_step_fraction" in scorer:
            item["fraction"] = float(scorer["apportion_short_step_fraction"])
        if "chord_min_rigidity_GV" in scorer:
            item["rigidity_GV"] = float(scorer["chord_min_rigidity_GV"])
        if "time_window_ns" in scorer:
            item["window_ns"] = [float(value) for value in scorer["time_window_ns"]]
        if scorer.get("level") == "event_file":
            item["hit_kind"] = scorer.get("hit_kind", "")  # a missing one is a finding of check-spec, which comes next
            item["readout"] = scorer.get("readout", "none")
            if item["readout"] != "none":
                sharing = [template for other in request["scorers"] if other.get("level") == "event_file" and other.get("readout") == item["readout"] for template in identity.selected_templates(other["select"], ir)]  # a bitfield's cells are unique over every scorer on it
                item["cell_id"] = cell_encoding(scorer, item["segmentation"]["kind"], ir, sharing)
        if scorer.get("level") == "moments":
            item["moments"] = True
        if scorer["quantity"] == physics_check.SPLIT_QUANTITY:
            templates, materials = ir["physical"]["templates"], ir["physical"]["materials"]
            item["light_yield_per_MeV"] = {name: float(materials.get(templates[name]["material"], {}).get("scintillation", {}).get("yield_per_MeV", 0)) for name in item["templates"]}
        scorers.append(item)
    out = {"source": resolved_source(request["source"], ir["physical"]["frames"], folder), "scorers": scorers}
    if any(item["quantity"] in physics_check.BIRKS_QUANTITIES for item in scorers):
        out["birks_active"] = True
    planes = request.get("reference_planes", [])
    if planes or "truth" in request or any("hit_kind" in item for item in scorers):
        keep = request.get("truth", {}).get("keep", ["primary"])
        rules = [{"above_MeV": float(rule["energy_above_MeV"]), "region": rule.get("region", "")} for rule in keep if isinstance(rule, dict) and "energy_above_MeV" in rule]
        out["truth"] = {"decay_products": "decay_products" in keep, "all": "all" in keep, "energy_rules": rules, "time_bin_ns": float(request.get("truth", {}).get("time_bin_ns", 1)),
                        "planes_z_mm": [_in_world(plane["frame"], [0.0, 0.0, float(plane["z_mm"])], ir["physical"]["frames"])[2] for plane in planes]}
    return out


def selected_materials(resolved: dict, ir: dict) -> dict:
    templates = ir["physical"]["templates"]
    return {item["name"]: sorted({templates[name]["material"] for name in item["templates"]}) for item in resolved["scorers"]}


def effective_problems(effective: dict, card: dict, ir: dict, resolved: dict) -> list:
    """Sections 8.7, 8.8: what Geant4 read back against the run card and the specification. Any difference refuses the run."""
    problems = []
    materials = ir["physical"]["materials"]
    for name in sorted({m for scorer, names in selected_materials(resolved, ir).items() for m in names
                        if next(item for item in resolved["scorers"] if item["name"] == scorer)["quantity"] in physics_check.BIRKS_QUANTITIES}):
        declared = float(materials[name]["ionisation"]["birks_mm_per_MeV"])
        actual = effective["birks_mm_per_MeV"].get(name)
        if actual is None or abs(actual - declared) > BIRKS_TOLERANCE * max(declared, 1.0):
            problems.append(f"material {name}: Birks constant {actual} mm/MeV in effect, {declared} declared")
    wanted = card.get("physics", {}).get("em_parameters", {})
    for key, group in (("step_function_electron", "e+-"), ("step_function_muon_hadron", "muons/hadrons"), ("step_function_light_ion", "light ions"), ("step_function_ion", "general ions")):
        if key not in wanted:
            continue
        line = next((text for text in effective["step_functions"] if group in text), "")
        ratio, range_mm = line.rsplit("(", 1)[-1].rstrip(") ").replace(" mm", "").split(",") if "(" in line else ("nan", "nan")
        if abs(float(ratio) - float(wanted[key][0])) > EM_TOLERANCE or abs(float(range_mm) - float(wanted[key][1])) > EM_TOLERANCE:
            problems.append(f"{key}: ({ratio}, {range_mm}) in effect, {wanted[key]} set")
    for key in ("msc_range_factor", "msc_muhad_range_factor"):
        if key in wanted and abs(effective[key] - float(wanted[key])) > EM_TOLERANCE:
            problems.append(f"{key}: {effective[key]} in effect, {wanted[key]} set")
    return problems


def outside_differences(with_pai: dict, without_pai: dict, requests: list) -> list:
    """GB12: the models and fluctuation models outside the PAI regions equal those of a run without PAI. A difference is an error (Section 6.2.9)."""
    regions = {request["region"] for request in requests}
    problems = [] if without_pai and with_pai else ["no models were read back, so nothing can be compared"]
    for region, processes in without_pai.items():
        if region in regions:
            continue
        for key, rows in processes.items():
            if with_pai.get(region, {}).get(key) != rows:
                problems.append(f"region {region}, {key}: PAI changed the models outside its region")
    return problems


def missing_pai(models: dict, requests: list, ionisation: dict) -> list:
    """Each process a request maps to really carries a PAI model in its region: Geant4 read back, not check-spec's prediction."""
    problems = []
    for row in physics_check.effective_pai(requests, ionisation):
        found = {key: rows for key, rows in models.get(row["region"], {}).items() if key.startswith(f"{row['process']}/")}
        if not found:
            problems.append(f"region {row['region']}, {row['process']}: nothing read back")
        for key, rows in found.items():
            if not any(item[0].startswith("PAI") for item in rows):
                problems.append(f"region {row['region']}, {key}: no PAI model in effect")
    return problems


def ionisation_table(effective: dict) -> dict:
    return {name: None if value == "none" else value for name, value in effective["ionisation"].items()}


def _rows(path: Path) -> list:
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle) if row and not row[0].startswith("#") and row[0] != "event"]


def merge_threads(work: Path) -> dict:
    """The workers' files as one file each, ordered by event, so the output does not depend on the threads."""
    counts = {}
    for stem in THREAD_FILES:
        rows = []
        header = None
        for path in sorted(work.glob(f"{stem}.thread*.csv")):
            if stem == "conservation" and header is None:
                header = next((line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("event")), None)
            rows += _rows(path)
            path.unlink()
        rows.sort(key=lambda row: (int(row[0]), row[1:]))
        with (work / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
            if header:
                handle.write(header + "\n")
            csv.writer(handle, lineterminator="\n").writerows(rows)
        counts[stem] = len(rows)
    return counts


def merge_moments(work: Path, events: int) -> dict:
    """`moments.csv` from the workers' partial sums, one final rounding per cell, so the result does not depend on the threads.

    Rows: scorer, volume, bin, events run, events with a deposit, sum, sum of squares; bin -1 is the direct sum. A mean is the sum over the events run, which is why they are recorded.
    The bins close on the direct sum within n x 2^-52 x sum |x|, as column rows do (Section 9.1).
    """
    cells: dict = {}
    for path in sorted(work.glob("moments.thread*.csv")):
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.reader(handle):
                count = int(row[6])
                cell = cells.setdefault((row[0], int(row[1]), int(row[2])), {"with_deposit": 0, "summands": 0, "absolute": 0.0, "sum": [], "squares": []})
                cell["with_deposit"] += int(row[3])
                cell["summands"] += int(row[4])
                cell["absolute"] += float.fromhex(row[5])
                cell["sum"].append([float.fromhex(value) for value in row[7:7 + count]])
                cell["squares"].append([float.fromhex(value) for value in row[7 + count:]])
        path.unlink()
    rows = [[*key, events, cell["with_deposit"], repr(rng.merge_partial_sums(cell["sum"])), repr(rng.merge_partial_sums(cell["squares"]))] for key, cell in sorted(cells.items())]
    if rows:
        with (work / "moments.csv").open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerows(rows)
    binned: dict = {}
    for row in rows:
        if row[1] != -1:
            binned.setdefault(row[0], []).append(float(row[5]))
    failing = []
    for row in rows:
        if row[1] == -1:
            cell = cells[(row[0], -1, -1)]
            if abs(math.fsum(binned.get(row[0], [])) - float(row[5])) > cell["summands"] * 2.0 ** -52 * cell["absolute"]:
                failing.append(row[0])
    return {"rows": len(rows), "failing": failing}


def closure_problems(cells: list) -> dict:
    """Section 9.1: per event and scorer, the bins against the direct sum, within n x 2^-52 x sum |x|. Rows: event, scorer, volume, bin, value, n, sum|x|."""
    sums: dict = {}
    direct: dict = {}
    for row in cells:
        key = (row[0], row[1])
        if row[2] == "-1":
            direct[key] = (float(row[4]), int(row[5]), float(row[6]))
        else:
            sums.setdefault(key, []).append(float(row[4]))
    worst, failing = 0.0, 0
    for key, (value, count, absolute) in direct.items():
        residual = abs(math.fsum(sums.get(key, [])) - value)
        limit = count * CLOSURE_ULP * absolute
        worst = max(worst, residual)
        failing += residual > limit
    return {"events_checked": len(direct), "failing": failing, "largest_residual": worst}


def class_x(bin_number: int) -> tuple:
    """A dedx class's kind and its range of x, for reweighting."""
    kind, index = divmod(bin_number, CLASSES_PER_KIND)
    low = 10.0 ** ((index - CLASS_OFFSET) / CLASSES_PER_DECADE)
    return KINDS[kind], low, 10.0 ** ((index + 1 - CLASS_OFFSET) / CLASSES_PER_DECADE)


def reweighted(rows: list, birks: float) -> float:
    """Visible energy from `edep_by_dedx_class` rows (bin, energy), at the classes' geometric centres; a zero-length step keeps its deposit."""
    total = []
    for number, energy in rows:
        kind, low, high = class_x(number)
        total.append(energy if kind == "zero_length" else energy / (1 + birks * math.sqrt(low * high)))
    return math.fsum(total)


def reweighting_bound(rows: list, birks: float) -> float:
    """Section 9.1: the sum over classes of the deposit times k_B (b - a) / (1 + k_B a)."""
    terms = []
    for number, energy in rows:
        kind, low, high = class_x(number)
        terms.append(0.0 if kind == "zero_length" else energy * birks * (high - low) / (1 + birks * low))
    return math.fsum(terms)


def balance_summary(boundary: list) -> dict:
    """Section 9.1: the energy-balance rows of each envelope."""
    rows = [row for row in boundary if row[2] == "balance"]
    values = [abs(float(row[3])) for row in rows]
    incident = [float(row[6]) for row in rows]
    return {"events": len(rows), "largest_MeV": max(values, default=0.0), "mean_incident_MeV": math.fsum(incident) / len(incident) if incident else 0.0}


def conservation_summary(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    residuals = [abs(float(row["residual_MeV"])) for row in rows]
    return {"events": len(rows), "largest_residual_MeV": max(residuals, default=0.0), "accounting_errors": sum(int(row["accounting_errors"]) for row in rows)}


def failure_reason(log: Path) -> str:
    """The line of a run's log that says why Geant4 stopped it."""
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.is_file() else []
    return next((line.strip() for line in reversed(lines) if any(text in line for text in ("the event file", "a segmentation of", "does not fit its readout field", "is not in the readout's table"))), "")


def run_program(program: Path, work: Path, environment=None) -> int:
    with (work / "log.txt").open("a", encoding="utf-8") as log:
        return subprocess.run([str(program), "--new", "ir.json", "run.json", "request.json"], cwd=work, stdout=log, stderr=log, check=False, env=environment).returncode


FIELD_SAMPLE_TOLERANCE_T = 1e-9  # the same grid and interpolation on both sides; only the transform's rounding differs
FIELD_SAMPLES = 64


def _to_mother(placement: dict, point: list) -> list:
    """A point of the daughter's frame in its mother's: the IR holds Geant4's passive rotation P, so p_mother = P^T p + centre."""
    rows = placement["rotation"] or [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    return [sum(float(rows[j][i]) * point[j] for j in range(3)) + float(placement["centre_mm"][i]) for i in range(3)]


def axis_to_world(ir: dict, template: str, vector: list) -> list:
    """A vector along a once-placed template's axes, in world components: the rotations alone, level by level (a field map's B)."""
    placements = ir["physical"]["placements"]
    while template != "world":
        placement = next(item for item in placements if item["template"] == template)
        rows = placement["rotation"] or [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        vector, template = [sum(float(rows[j][i]) * vector[j] for j in range(3)) for i in range(3)], placement["mother"]
    return vector


def _to_world(ir: dict, template: str, point: list) -> list:
    """A point of a template placed once in the tree, in world coordinates (check-spec requires a field map's frame to be placed once)."""
    placements = ir["physical"]["placements"]
    while template != "world":
        placement = next(item for item in placements if item["template"] == template)
        point, template = _to_mother(placement, point), placement["mother"]
    return point


def _chain(ir: dict, template: str) -> list:
    """The placements from the world down to a template placed once in the tree."""
    placements, chain = ir["physical"]["placements"], []
    while template != "world":
        found = [item for item in placements if item["template"] == template]
        if len(found) != 1:
            raise ValueError(f"template {template} is placed {len(found)} times at one level; a frame needs one placement")
        chain.append(found[0])
        template = found[0]["mother"]
    return chain[::-1]


def to_local(ir: dict, template: str, point: list) -> list:
    """A world point in a once-placed template's frame: level by level, p_daughter = P (p_mother - centre)."""
    for placement in _chain(ir, template):
        rows = placement["rotation"] or [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        shifted = [point[i] - float(placement["centre_mm"][i]) for i in range(3)]
        point = [sum(float(rows[i][j]) * shifted[j] for j in range(3)) for i in range(3)]
    return point


def stage_field_maps(checked: dict, work: Path) -> dict:
    """Copies each field map the IR names into the run folder, as field-map.<name>.txt, after hashing the bytes again (Section 6.2.8),
    and lists sample points for the read-back. Returns {field: (map, [(local, global) points])}."""
    for stale in [*work.glob("field-samples.thread*.txt"), work / "field-samples.txt"]:  # a rerun in the same folder never reads an old answer
        stale.unlink(missing_ok=True)
    staged = {}
    lines = []
    for name, path in sorted(checked.get("field_map_files", {}).items()):
        wanted = checked["ir"]["physical"]["fields"][name]["map"]
        map_bytes = Path(path).read_bytes()
        if hashlib.sha256(map_bytes).hexdigest() != wanted["sha256"]:
            raise ValueError(f"field map {name}: {path} changed after check-spec")
        (work / f"field-map.{name}.txt").write_bytes(map_bytes)
        parsed = fieldmap.parse(map_bytes.decode("utf-8"))
        half = [float(value) for value in checked["ir"]["physical"]["templates"][wanted["frame_template"]]["half_mm"]]
        draw = random.Random(wanted["sha256"])  # the points follow the map, so a rerun samples the same points
        local = [[0.0, 0.0, 0.0]] + [[sign * 0.9 * h for sign, h in zip(signs, half)] for signs in
                                     ((x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1))]
        local += [[draw.uniform(-h, h) for h in half] for _ in range(FIELD_SAMPLES - len(local))]
        points = [(point, _to_world(checked["ir"], wanted["frame_template"], point)) for point in local]
        staged[name] = (parsed, points, wanted["frame_template"], checked["ir"])
        lines += [f"{name} {x.hex()} {y.hex()} {z.hex()}" for _, (x, y, z) in points]
    if lines:
        (work / "field-samples.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return staged


def field_sample_problems(staged: dict, work: Path) -> list:
    """The field each thread's manager gave at the sample points against this side's reading of the map: proves the file read, the
    grid and the frame's transform together."""
    if not staged:
        return []
    # the grid holds components along the frame template's axes; Geant4 is handed them in world components
    wanted = [(name, axis_to_world(ir, frame, fieldmap.interpolate(parsed["grid"], parsed["values"], local)))
              for name, (parsed, points, frame, ir) in sorted(staged.items()) for local, _ in points]
    files = sorted(work.glob("field-samples.thread*.txt"))
    if not files:
        return ["no thread wrote the field at the sample points"]
    problems = []
    for path in files:
        rows = [line.split() for line in path.read_text(encoding="utf-8").splitlines()]
        if len(rows) != len(wanted):
            problems.append(f"{path.name}: {len(rows)} samples for {len(wanted)} points")
            continue
        for number, (row, (name, field)) in enumerate(zip(rows, wanted)):
            got = [float.fromhex(value) for value in row[1:4]]
            if row[0] != name or any(abs(a - b) > FIELD_SAMPLE_TOLERANCE_T for a, b in zip(got, field)):
                problems.append(f"{path.name}, field {name}, sample {number}: {got} T, the map gives {field}")
                break
    return problems


def radiator_process_problems(radiators: list, probe: dict) -> list:
    """Each radiator's process, xtr_<envelope> as XtrConstructor.hh names it, read back on the particles the card names (e- and e+ when it
    names none) and on no other."""
    if not probe.get("processes"):
        return ["no process list was read back"]
    problems = []
    for item in radiators:
        process_name = f"xtr_{item['envelope']}"
        wanted = set(item.get("particles") or ("e-", "e+"))
        carrying = {row["particle"] for row in probe["processes"] if process_name in row["registered"]}
        problems += [f"{name}: {'no ' + process_name if name in wanted else process_name + ', which the card does not name'}" for name in sorted(wanted ^ carrying)]
    return problems


def simulate(card: dict, request: dict, checked: dict, program: Path, work: Path, environment=None, folder: Path | None = None) -> dict:
    """Preflight with no events, so a wrong setting is refused before any event; then the run."""
    ir = checked["ir"]
    resolved = resolved_request(request, ir, folder)
    findings = physics_check.card_findings(card, request, requirements=ir["physical"]["physics_requirements"], materials=ir["physical"]["materials"], selected_materials=selected_materials(resolved, ir),
                                          physical=ir["physical"])
    regions = {record["region"] for record in ir["physical"]["templates"].values()} - {"default"}
    findings += physics_check.hit_findings(resolved["scorers"], regions, request.get("truth", {}))
    if findings:
        return {"status": "rejected", "findings": findings}
    work.mkdir(parents=True, exist_ok=True)
    (work / "ir.json").write_text(json.dumps(ir), encoding="utf-8")
    staged = stage_field_maps(checked, work)
    (work / "request.json").write_text(json.dumps(resolved), encoding="utf-8")
    preflight = json.loads(json.dumps(card))
    preflight["run"]["events"] = 0  # the run's own mode: a serial run has built no model tables at this point, and would read back nothing
    requests = card.get("physics", {}).get("pai", [])
    plain_models = None
    if requests:  # the same settings with no PAI, for GB12's comparison
        plain = json.loads(json.dumps(preflight))
        plain["physics"]["pai"] = []
        (work / "run.json").write_text(json.dumps(plain), encoding="utf-8")
        code = run_program(program, work, environment)
        if code != 0:
            return {"status": "failed", "exit_status": code, "stage": "preflight without PAI", "reason": failure_reason(work / "log.txt")}
        plain_models = json.loads((work / "effective-em.json").read_text(encoding="utf-8"))["models"]
    (work / "run.json").write_text(json.dumps(preflight), encoding="utf-8")
    code = run_program(program, work, environment)
    if code != 0:
        return {"status": "failed", "exit_status": code, "stage": "preflight", "reason": failure_reason(work / "log.txt")}
    effective = json.loads((work / "effective-em.json").read_text(encoding="utf-8"))
    problems = effective_problems(effective, card, ir, resolved) + field_sample_problems(staged, work)
    regions = {node["region"] for node in ir["physical"]["templates"].values()}
    findings = physics_check.pai_findings(requests, regions, ionisation_table(effective), ir["physical"]["physics_requirements"]) if requests else []
    if requests and not findings:
        problems += outside_differences(effective["models"], plain_models, requests) + missing_pai(effective["models"], requests, ionisation_table(effective))
    if problems or findings:
        return {"status": "rejected", "problems": problems, "findings": findings}
    (work / "run.json").write_text(json.dumps(card), encoding="utf-8")
    code = run_program(program, work, environment)
    if code != 0:
        return {"status": "failed", "exit_status": code, "stage": "run", "reason": failure_reason(work / "log.txt")}
    counts = merge_threads(work)
    moments = merge_moments(work, card["run"]["events"])
    request_identity = identity.request_id(identity.identified_request(request, ir), checked["geometry_id"])
    cells = _rows(work / "cells.csv")
    closure = closure_problems([row for row in cells if row[1] in {item["name"] for item in resolved["scorers"] if item["quantity"] in physics_check.ADDITIVE}])
    summary = {"status": "failed" if closure["failing"] or moments["failing"] else "ok", "rows": counts, "closure": closure, "moments": moments, "request_id": request_identity, "balance": balance_summary(_rows(work / "boundary.csv")), "conservation": conservation_summary(work / "conservation.csv"),
               "effective": {"birks_mm_per_MeV": effective["birks_mm_per_MeV"], "step_functions": effective["step_functions"], "pai": physics_check.effective_pai(requests, ionisation_table(effective)), "models": effective["models"]},
               "geometry_id": checked["geometry_id"]}
    radiators = card.get("physics", {}).get("xtr", [])
    if radiators:  # S7: each radiator's process on the particles the card names, and on no other (read back by ProbeV2)
        summary["xtr"] = radiator_process_problems(radiators, json.loads((work / "probe-v2.json").read_text(encoding="utf-8")) if (work / "probe-v2.json").is_file() else {})
        if summary["xtr"]:
            summary["status"] = "failed"
    if (work / "hits.root").is_file():
        (work / "simulation-hits.json").write_text(json.dumps({**hits.index(checked["geometry_id"], card, work / "hits.root", request_identity), "scorers": [item["name"] for item in resolved["scorers"]], "readouts": {item["name"]: item["readout"] for item in resolved["scorers"] if "hit_kind" in item}}, indent=1) + "\n", encoding="utf-8")
    (work / "column_map.json").write_text(json.dumps({"scorers": resolved["scorers"], "volume_id": ir["physical"]["volume_id"]}, indent=1) + "\n", encoding="utf-8")
    (work / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    print(json.dumps({"status": "rejected", "message": "a library: run g4sim_run.py simulate"}))
    sys.exit(2)
