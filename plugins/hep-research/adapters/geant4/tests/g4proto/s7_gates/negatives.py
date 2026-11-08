#!/usr/bin/env python3
"""S7 gate 5: each negative test of Section 15.1 for S7 as a real change, which a test or a run must then catch (g4sim plan, Section 19.2).

A test that merely exists proves nothing, so a scratch copy of the code is first run unchanged, and must pass, then with one change at a time,
and must fail. The two rows that live in Geant4 (a wrong refractive index; optical photons killed by KillProcess booked as killed kinetic
energy) are runs of g4sim_run with the builder and accounting controls; the second must break conservation by more than the 1e-6 MeV of S3.
Usage: negatives.py --work DIR [--program PATH]   Prints JSON with a status key. Exit 0 every change caught, 1 otherwise, 2 bad input.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
COPIED = ("core", "contracts", "adapters/geant4/assets", "profiles", "tests/__init__.py", "tests/core", "tests/adapters")
OPTICS, RADIATOR, EXPAND, CHECK, MAP, CONTRACT, DRIVER = ("core/geometry/optics.py", "core/geometry/xtr.py", "core/geometry/expand.py",
                                                    "adapters/geant4/assets/g4sim_physics_check.py", "core/simulation/efficiency_map.py",
                                                    "contracts/geometry.py", "adapters/geant4/assets/g4sim_run.py")
T_OPTICS, T_RADIATOR, T_EXPAND, T_RUN, T_MAP, T_FIELD = ("tests.core.test_geometry_optics",), ("tests.core.test_geometry_xtr",), ("tests.core.test_geometry_expand",), \
    ("tests.adapters.test_g4sim_run",), ("tests.core.test_simulation_efficiency_map",), ("tests.core.test_geometry_fieldmap",)
BALANCE_TOLERANCE_MEV = 1e-6

# Section 15.1 row, change, file, text replaced, replacement, tests that must fail
CHANGES = (
    ("optical_scope", "a material with optical properties outside the scope accepted", OPTICS, "if has_tables(materials.get(node[\"material\"])) and name not in inside:", "if False:", T_OPTICS),
    ("optical_scope", "a spacer within the scope with no material accepted", OPTICS, "if isinstance(item, dict) and \"spacer_mm\" in item and not has_tables(materials.get(nodes[mother][\"material\"])):", "if False:", T_OPTICS),
    ("XTR", "a foil placed inside the envelope accepted", RADIATOR, "        if tree.get(envelope):", "        if False:", T_RADIATOR),
    ("XTR", "a wrong envelope thickness accepted", RADIATOR, "if not CONTEXT.subtract(pitch, g) <= d <= pitch:", "if False:", T_RADIATOR),
    ("XTR", "an irregular requirement with a regular-foil-stack class accepted", CHECK, "elif entry[\"structure\"] != wanted[envelope][\"structure\"]:", "elif False:", T_RUN),
    ("XTR", "a model kind in the detector-spec accepted", RADIATOR, "        if model:", "        if False:", T_RADIATOR),
    ("XTR", "G4StrawTubeXTRadiator accepted (addendum 11.1)", CHECK, "elif entry[\"structure\"] is None:", "elif False:", T_RUN),
    ("Efficiency maps", "two components with different emission spectra sharing one map", MAP, "if not _same_spectrum(components[numbers[0] - 1][\"spectrum\"], components[number - 1][\"spectrum\"]):", "if False:", T_MAP),
    ("Efficiency maps", "a validation run whose RESOLUTIONSCALE differs from r", CHECK, "if scale is None or float(scale) != float(resolution_scale):", "if False:", T_RUN),
    ("Optics", "a wrong refractive index read back as equal", DRIVER, "    return abs(got - value) <= OPTICAL_RELATIVE_TOLERANCE * max(abs(value), 1e-300)", "    return True", T_RUN),
    ("Shapes", "a cone parameter out of range accepted", EXPAND, "        if rmin1 >= rmax1 or rmin2 >= rmax2:", "        if False:", T_EXPAND),
    ("Shapes", "a polyhedra given its circumradius as the apothem", EXPAND, "    factor = rotation.cos_sin(divide(Decimal(phi_span), multiply(Decimal(2), Decimal(sides))))[0]", "    factor = Decimal(1)", T_EXPAND),
    ("Field maps", "a field-map file with a mismatched hash accepted", CONTRACT, "        if hashlib.sha256(map_bytes).hexdigest() != record[\"sha256\"]:", "        if False:", T_FIELD),
    ("Optical physics", "optical physics with no optical-photon class accepted", DRIVER, "        if card.get(\"accounting\") != \"separated\":", "        if False:", T_RUN),
)


def run_tests(root: Path, modules: tuple) -> subprocess.CompletedProcess:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, "-m", "unittest", *modules], cwd=root, capture_output=True, text=True, timeout=1200, check=False, env=environment)


def copy_plugin(work: Path) -> Path:
    root = work / "plugin"
    if root.exists():
        shutil.rmtree(root)
    for name in COPIED:
        source, target = PLUGIN / name, root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if source.is_dir() else shutil.copy2)(source, target)
    return root


def code_changes(work: Path) -> list:
    root = copy_plugin(work)
    modules = tuple(sorted({module for *_, tests in CHANGES for module in tests}))
    baseline = run_tests(root, modules)
    if baseline.returncode != 0:
        raise RuntimeError("the unchanged copy fails its tests: " + baseline.stderr[-800:])
    rows = []
    for row, change, name, old, replacement, tests in CHANGES:
        path = root / name
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            rows.append({"row": row, "change": change, "caught": False, "why": f"the text to change occurs {original.count(old)} times in {name}"})
            continue
        path.write_text(original.replace(old, replacement), encoding="utf-8")
        done = run_tests(root, tests)
        path.write_text(original, encoding="utf-8")
        failed = [line for line in done.stderr.splitlines() if line.startswith(("FAIL:", "ERROR:"))]
        rows.append({"row": row, "change": change, "file": name, "caught": done.returncode != 0, "failing_tests": failed[:4]})
    return rows


def live(work: Path, program: Path) -> list:
    """The two Geant4 rows: the optics write-back with a 1% high RINDEX; photons leaking out of the scope, killed, booked as killed energy."""
    sys.path.insert(0, str(PLUGIN / "adapters/geant4/tests/g4proto/s7_gates"))
    import optics_gates  # noqa: E402
    folder = work / "live"
    optics_gates.setup(folder)
    spec, request = folder / "cherenkov/spec.json", folder / "cherenkov/request.json"
    card = json.loads((folder / "cherenkov/trial.json").read_text(encoding="utf-8"))
    card["run"]["events"] = 5
    (folder / "run.json").write_text(json.dumps(card), encoding="utf-8")
    driver = PLUGIN / "adapters/geant4/assets/g4sim_run.py"

    def go(command: list, controls: dict, out: Path) -> dict:
        shutil.rmtree(out, ignore_errors=True)  # never read a former run's files
        done = subprocess.run([sys.executable, str(driver), *command, "--program", str(program), "--work", str(out)], capture_output=True, text=True, timeout=3000,
                              check=False, env={**os.environ, **controls})
        return json.loads(done.stdout) if done.stdout.strip().startswith("{") else {"status": "error", "stderr": done.stderr[-400:]}

    rows = []
    for controls, label in (({}, "control: as built"), ({"G4SIM_BUILDER_CONTROL": "wrong_rindex"}, "a wrong refractive index")):
        result = go(["geometry-check", "--detector", str(spec), "--run", str(folder / "run.json")], controls, folder / f"geometry-{len(rows)}")
        problems = [item for item in result.get("problems", []) if "RINDEX" in item]
        rows.append({"row": "Optics (Geant4)", "change": label, "caught": bool(problems) if controls else None, "passes_as_built": result.get("status") == "ok" if not controls else None, "problems": problems[:2]})
    for controls, label in (({"G4SIM_BUILDER_CONTROL": "leak_scope"}, "control: photons leaking out of the scope, booked as optical"),
                            ({"G4SIM_BUILDER_CONTROL": "leak_scope", "G4SIM_ACCOUNTING_CONTROL": "optical_as_killed"}, "photons killed by KillProcess booked as killed kinetic energy")):
        out = folder / f"leak-{len(rows)}"
        result = go(["simulate", "--detector", str(spec), "--request", str(request), "--run", str(folder / "run.json")], controls, out)
        conservation = list(csv.DictReader((out / "conservation.csv").open(encoding="utf-8"))) if (out / "conservation.csv").is_file() else []
        largest = max((abs(float(item["residual_MeV"])) for item in conservation), default=None)
        killed = sum(int(item.get("optical_killed_scope", 0)) for item in conservation)
        if result.get("status") != "ok":
            raise RuntimeError(f"the run '{label}' failed: {json.dumps(result)[:300]}")
        breaks = largest is not None and largest > BALANCE_TOLERANCE_MEV
        negative = "G4SIM_ACCOUNTING_CONTROL" in controls
        rows.append({"row": "Optical photons (Geant4)", "change": label, "caught": breaks if negative else None, "conservation_holds": (not breaks) if not negative else None,
                     "largest_residual_MeV": largest, "killed_in_scope_terms": killed, "run_status": result.get("status")})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--program", type=Path)
    args = parser.parse_args(argv)
    try:
        rows = code_changes(args.work) + (live(args.work, args.program.resolve()) if args.program else [])
    except (OSError, RuntimeError, ValueError) as err:
        print(json.dumps({"status": "rejected", "message": str(err)}))
        return 2
    negatives = [row for row in rows if row.get("caught") is not None]
    controls_hold = all(row.get("passes_as_built", True) is not False and row.get("conservation_holds", True) is not False for row in rows)
    status = "ok" if all(row["caught"] for row in negatives) and controls_hold else "failed"
    print(json.dumps({"status": status, "caught": sum(row["caught"] for row in negatives), "of": len(negatives), "rows": rows}, indent=1))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
