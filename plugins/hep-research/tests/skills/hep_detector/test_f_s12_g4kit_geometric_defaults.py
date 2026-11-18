"""CHK-AT-12-01 (S1): a geometric default named in a design geometry file is the value the detector-spec uses.

A kit's geometric defaults (for example the gap between two scintillator bars) may come from the design geometry file:
g4kit.py's input_values() accepts a field named after one and merges it into the values ("Every input of the kit, from
the design geometry file, or a geometric default"). Before the fix detector_spec() filled the specification's params
from the kit's own default, so the design's value was dropped without a message: a tof design with bar_gap_mm 0.25 got
a bar pitch of width + 0.5 mm, and its derivation record still hashed the design file as if its gap had been used.

Evidence (no oracle imports g4kit.py or its helpers; each test runs g4kit.py derive as a program and reads its files):

- exhaustive (ExhaustiveGeometricDefaults): every geometric default of every shipped kit that has one, the nine names
  of the five kits in DOMAIN, each omitted and each given at three values (the kit's default, twice it, and half
  it), 32 derivations in all. The expected value is the design file's own number (or, when omitted, the kit file's
  default), never the program's output.
- invariant (ExpandedTofGeometry): in the geometry that contracts/geometry.py expands from the derived tof
  specification, every pair of neighbouring bars in a plane is separated by the design's bar_gap_mm (centre distance
  minus one bar width), for three gaps; and two designs that differ only in a geometric default give different
  detector-specs and geometry ids.
- negative control (PreFixEmulation): params built the pre-fix way (every geometric default from the kit file) are
  rejected by the same comparison the exhaustive oracle uses, for a design that gives a value, and accepted when the
  design omits it.

Tolerance: zero, fixed before the first run. Every quantity is a decimal string; g4kit.py writes design values with
decimal formatting, and the geometry contract computes in decimal arithmetic at 34 significant digits (IR numerics
precision 34, half-even). The compared values are sums and products of a few numbers below 1e4 with at most two
decimal places, so they are exact at that precision, and every comparison is equality of decimal.Decimal values.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-detector/scripts/g4kit.py"
GEOMETRY = ROOT / "contracts/geometry.py"
KITS = ROOT / "skills/hep-detector/assets/g4kits"
TIMEOUT = 120
TOLERANCE = Decimal("0")  # exact: decimal arithmetic at 34 digits on short decimals (module docstring)

# The stated finite domain: each shipped kit with geometric defaults, and the names of its defaults.
DOMAIN = {"calorimeter": {"wrap_mm", "tower_gap_mm", "guide_mm", "guide_side_mm", "guide_gap_mm"},
          "endcap-disks": {"disk_margin_mm"},
          "shell-veto": {"readout_gap_mm"},
          "tof": {"bar_gap_mm"},
          "trd": {"straw_gap_mm"}}
# Valid designs of those kits (the fields of tests/skills/hep_detector/test_g4kit.py, copied so this evidence stays fixed).
DESIGNS = {
    "calorimeter": {"layers": 10, "towers_x": 3, "towers_y": 3, "absorber_mm": 2.0, "active_mm": 3.0, "support_mm": 1.0, "support_material": "G4_AIR", "tower_side_mm": 40.0, "absorber_material": "G4_Pb", "active_material": "G4_PLASTIC_SC_VINYLTOLUENE", "wrap_material": "G4_MYLAR", "guide_material": "G4_PLEXIGLASS", "world_material": "G4_AIR"},
    "endcap-disks": {"disks": 3, "disk_pitch_mm": 100.0, "wedges": 12, "inner_apothem_mm": 100.0, "outer_apothem_mm": 300.0, "wedge_inner_width_mm": 52.59, "wedge_outer_width_mm": 159.77, "wedge_thickness_mm": 0.5, "disk_inner_radius_mm": 95.0, "disk_outer_radius_mm": 320.0, "wedge_material": "G4_Si", "world_material": "G4_AIR"},
    "shell-veto": {"shell_inner_radius_mm": 500.0, "shell_thickness_mm": 8.0, "shell_length_mm": 800.0, "readouts": 8, "readout_side_mm": 8.0, "readout_length_mm": 50.0, "shell_material": "G4_PLASTIC_SC_VINYLTOLUENE", "readout_material": "G4_PLEXIGLASS", "world_material": "G4_AIR"},
    "tof": {"planes": 2, "bars": 8, "bar_length_mm": 1000.0, "bar_width_mm": 100.0, "bar_thickness_mm": 10.0, "plane_gap_mm": 50.0, "bar_material": "G4_PLASTIC_SC_VINYLTOLUENE", "world_material": "G4_AIR"},
    "trd": {"layers": 4, "radiator_thickness_mm": 21.5, "module_width_mm": 130.0, "straws": 20, "straw_radius_mm": 3.0, "straw_wall_mm": 0.07, "straw_length_mm": 500.0, "radiator_material": "radiator_mix", "foil_material": "mylar", "gas_material": "air", "drift_gas_material": "G4_Xe", "wall_material": "G4_KAPTON", "world_material": "G4_AIR", "radiator_structure": "regular", "foils": 100, "foil_thickness_um": 15.0, "gap_um": 200.0, "pai_particles": ["e-", "proton"], "materials": {"mylar": {"base": "G4_MYLAR", "density_g_cm3": "1.39"}, "air": {"base": "G4_AIR", "density_g_cm3": "0.00120479"}, "radiator_mix": {"density_g_cm3": "0.0980974790697674418604651162790698", "components": [{"material": "mylar", "mass_fraction": "0.988575293734879183771547978048"}, {"material": "air", "mass_fraction": "0.0114247062651208162284520219517767"}]}}},
}
TOF_GAPS = ("0.25", "1", "2.5")


def kit_of(kind: str) -> dict:
    """The kit file of a geometry kind, read as data."""
    for path in sorted(KITS.glob("*.json")):
        kit = json.loads(path.read_text(encoding="utf-8"))
        if kit["geometry_kind"] == kind:
            return kit
    raise AssertionError(f"no kit file for {kind}")


def variants(default: str) -> tuple:
    """The three given values of one default: the kit's own, twice it, and half it (all legal geometries)."""
    value = Decimal(default)
    return tuple(format(item, "f") for item in (value, 2 * value, value / 2))


def expected_defaults(kit: dict, fields: dict) -> dict:
    """What each geometric default must be: the design's value when it gives one, else the kit's default."""
    return {name: Decimal(str(fields.get(name, default))) for name, default in kit["geometric_defaults"].items()}


def mismatches(params: dict, kit: dict, fields: dict) -> dict:
    """The geometric defaults whose value in params differs from the expected one, by more than TOLERANCE."""
    wanted = expected_defaults(kit, fields)
    return {name: (params.get(name), str(value)) for name, value in wanted.items()
            if name not in params or abs(Decimal(params[name]) - value) > TOLERANCE}


def derive(folder: Path, kind: str, fields: dict) -> tuple:
    """Run g4kit.py derive on a design-geometry/1 file; return (exit code, stdout, detector-spec or None)."""
    geometry = folder / "design.geometry.json"
    detector = folder / "detector.json"
    if detector.exists():
        detector.unlink()
    geometry.write_text(json.dumps({"schema": "design-geometry/1", "geometry": kind, "geometry_kind": kind, "fields": fields}), encoding="utf-8")
    done = subprocess.run([sys.executable, str(SCRIPT), "derive", "--geometry", str(geometry), "--out-detector", str(detector),
                           "--out-derivation", str(folder / "derivation.json")], capture_output=True, text=True, timeout=TIMEOUT, check=False)
    spec = json.loads(detector.read_text(encoding="utf-8")) if done.returncode == 0 else None
    return done.returncode, done.stdout, spec


class _Folder(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.work = Path(self.folder.name)


class ExhaustiveGeometricDefaults(_Folder):
    def test_every_geometric_default_takes_the_design_value(self):
        """Over the whole domain: omitted, the kit's default; given, the design's value; the other defaults unchanged."""
        for kind, names in DOMAIN.items():
            kit = kit_of(kind)
            self.assertEqual(set(kit["geometric_defaults"]), names, kind)
            cases = [{}] + [{name: given} for name in sorted(names) for given in variants(kit["geometric_defaults"][name])]
            for extra in cases:
                with self.subTest(kind=kind, given=extra):
                    fields = {**DESIGNS[kind], **extra}
                    code, out, spec = derive(self.work, kind, fields)
                    self.assertEqual(code, 0, out)
                    self.assertEqual(mismatches(spec["params"], kit, fields), {})


class ExpandedTofGeometry(_Folder):
    def expanded(self, fields: dict) -> dict:
        code, out, _ = derive(self.work, "tof", fields)
        self.assertEqual(code, 0, out)
        ir = self.work / "ir.json"
        done = subprocess.run([sys.executable, str(GEOMETRY), str(self.work / "detector.json"), "--out", str(ir)],
                              capture_output=True, text=True, timeout=TIMEOUT, check=False)
        self.assertEqual(done.returncode, 0, done.stdout)
        return json.loads(ir.read_text(encoding="utf-8"))

    def test_neighbouring_bars_are_separated_by_the_design_gap(self):
        design = DESIGNS["tof"]
        for gap in TOF_GAPS:
            with self.subTest(bar_gap_mm=gap):
                physical = self.expanded({**design, "bar_gap_mm": gap})["physical"]
                width = 2 * Decimal(physical["templates"]["bar"]["half_mm"][1])
                self.assertEqual(width, Decimal(str(design["bar_width_mm"])))
                centres = sorted(Decimal(item["centre_mm"][1]) for item in physical["placements"] if item["template"] == "bar")
                self.assertEqual(len(centres), design["bars"])
                for low, high in zip(centres, centres[1:]):
                    self.assertLessEqual(abs(high - low - width - Decimal(gap)), TOLERANCE, (low, high))
                plane = 2 * Decimal(physical["templates"]["plane"]["half_mm"][1])
                self.assertLessEqual(abs(plane - design["bars"] * (width + Decimal(gap))), TOLERANCE)

    def test_a_geometric_default_in_the_design_changes_the_geometry(self):
        design = DESIGNS["tof"]
        identities = []
        for fields in (design, {**design, "bar_gap_mm": "1"}):
            code, out, _ = derive(self.work, "tof", fields)
            self.assertEqual(code, 0, out)
            identities.append(json.loads(out)["geometry_id"])
        self.assertNotEqual(*identities)


class PreFixEmulation(unittest.TestCase):
    def test_kit_defaults_in_place_of_the_design_value_are_rejected(self):
        """Negative control: the pre-fix params (every geometric default from the kit) fail the exhaustive oracle's
        comparison when the design gives a different value, and pass it when the design gives none."""
        kit = kit_of("tof")
        pre_fix = {name: format(Decimal(value), "f") for name, value in kit["geometric_defaults"].items()}
        self.assertEqual(mismatches(pre_fix, kit, DESIGNS["tof"]), {})
        self.assertEqual(set(mismatches(pre_fix, kit, {**DESIGNS["tof"], "bar_gap_mm": "0.25"})), {"bar_gap_mm"})
        calorimeter = kit_of("calorimeter")
        pre_fix = {name: format(Decimal(value), "f") for name, value in calorimeter["geometric_defaults"].items()}
        self.assertEqual(set(mismatches(pre_fix, calorimeter, {**DESIGNS["calorimeter"], "tower_gap_mm": "0.4", "guide_mm": "21"})),
                         {"tower_gap_mm", "guide_mm"})


if __name__ == "__main__":
    unittest.main()
