"""transport_conventions.py (cr-propagation A1): diffusion conventions of GALPROP, USINE (K0, K10) and DRAGON2, the
reacceleration zone, per-nucleon and total kinetic energy, legacy names, and the harmonized-v1 configuration.

Oracles: the convention table of skills/hep-theory/references/cosmic-ray-phenomenology.md, parsed row by row here (a
row that does not parse fails the test, A1-3; no value of it is typed in); the IAU parsec and Julian year (A1-2:
1 kpc^2/Myr = 3.0172e29 cm^2/s within 1e-4); exact round trips of pure power laws (A1-1); statuses with breaks (A1-4)
and between reacceleration zones (A1-5); r3 5.4 and 5.5 for harmonized-v1 (A1-6). Inputs are SYNTHETIC."""
import itertools
import json
import math
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-theory" / "scripts" / "transport_conventions.py"
REFERENCE = PLUGIN / "skills" / "hep-theory" / "references" / "cosmic-ray-phenomenology.md"
HARMONIZED = PLUGIN / "tests" / "adapters" / "fixtures" / "cr_propagation" / "specs" / "harmonized-v1.json"
DRAGON2_SPEC = PLUGIN / "tests" / "adapters" / "fixtures" / "cr_propagation" / "specs" / "D_X1_R60_UG.json"
sys.path.insert(0, str(SCRIPT.parent))
sys.path.insert(0, str(PLUGIN))
import transport_conventions as tc  # noqa: E402

TABLE_HEADER = "| Source | Form | Normalization |"
UNIT_FACTOR = {"10^28 cm^2/s": 1e28, "cm^2/s": 1.0}  # kpc^2/Myr is compared with the module's derived unit


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *args], capture_output=True, text=True, timeout=120)
    out = json.loads(p.stdout) if p.stdout.strip().startswith("{") else p.stdout
    return p.returncode, out


def parse_convention_table(text: str) -> list[dict]:
    """The rows of the diffusion convention table; raises AssertionError on any row it cannot read."""
    lines = text.splitlines()
    start = lines.index(TABLE_HEADER)  # ValueError if the table is gone
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        assert len(cells) == 3, f"row with {len(cells)} cells: {line}"
        source, form, norm = cells
        code = next((c for c in ("GALPROP", "USINE", "DRAGON2") if source.startswith(c)), None)
        assert code, f"unknown code in row: {line}"
        if "beta^eta" in form:
            eta = None
        elif re.search(r"\bbeta\b", form):
            eta = 1.0
        else:
            eta = 0.0
        ref = re.search(r"at (?:rho0|R0) = (\d+(?:\.\d+)?) GV|at (\d+(?:\.\d+)?) GV", norm)
        unit = re.search(r"in (10\^28 cm\^2/s|kpc\^2/Myr|cm\^2/s)", norm)
        assert ref and unit, f"normalization not parsed: {norm}"
        row = {"code": code, "eta": eta, "reference_gv": float(ref.group(1) or ref.group(2)), "unit": unit.group(1),
               "momentum": "(p/p0)" in form, "breaks": "break" in form, "line": line}
        rows.append(row)
        k = re.search(r"K(\d+) = K0 (\d+)\^delta", norm)
        if k:
            assert k.group(1) == k.group(2), f"K{k.group(1)} relation not parsed: {norm}"
            rows.append(dict(row, code="USINE-K" + k.group(1), reference_gv=float(k.group(1))))
    assert len(rows) >= 3, "fewer than three convention rows parsed"
    return rows


def at_1gv(out) -> float:
    c = out["canonical"]
    return c["D0_cm2_s"] * c["R0_gv"] ** -c["delta"]


def code_name(row) -> str:
    return {"GALPROP": "galprop", "USINE": "usine-k0", "DRAGON2": "dragon2"}.get(row["code"]) or \
        "usine-k" + row["code"].split("-K")[1]


class ConventionTable(unittest.TestCase):
    """A1-3: every row of the reference page's table matches the module's convention."""

    def setUp(self):
        self.text = REFERENCE.read_text(encoding="utf-8")

    def test_every_row_parses_and_matches(self):
        rows = parse_convention_table(self.text)
        self.assertEqual({code_name(r) for r in rows}, {"galprop", "usine-k0", "usine-k10", "dragon2"})
        for row in rows:
            with self.subTest(row=row["code"]):
                conv = tc.CODE_CONVENTIONS[code_name(row)]
                self.assertEqual(conv["eta"], row["eta"])
                self.assertEqual(conv["reference_gv"], row["reference_gv"])
                factor = UNIT_FACTOR.get(row["unit"], tc.KPC2_PER_MYR_CM2_S)
                self.assertEqual(tc.D0_UNIT_CM2_S[conv["d0_unit"]], factor)

    def test_parse_failure_fails(self):
        broken = self.text.replace("at rho0 = 4 GV", "at the usual rigidity")
        with self.assertRaises(AssertionError):
            parse_convention_table(broken)
        with self.assertRaises(ValueError):
            parse_convention_table(self.text.replace(TABLE_HEADER, "| Code | Form | Norm |"))

    def test_page_unit_line_matches_derived_unit(self):
        m = re.search(r"1 kpc\^2/Myr = ([0-9.]+)e(\d+) cm\^2/s", self.text)
        self.assertIsNotNone(m, "unit line not found")
        quoted = float(m.group(1)) * 10 ** int(m.group(2))
        digits = len(m.group(1).replace(".", "")) - 1
        self.assertLess(abs(tc.KPC2_PER_MYR_CM2_S / quoted - 1), 0.5 * 10 ** -digits)


class Units(unittest.TestCase):
    def test_kpc2_per_myr(self):  # A1-2
        self.assertLess(abs(tc.KPC2_PER_MYR_CM2_S / 3.0172e29 - 1), 1e-4)

    def test_iau_definitions(self):
        self.assertEqual(tc.AU_M, 149597870700.0)
        self.assertAlmostEqual(tc.PARSEC_CM / (648000 / math.pi * 1.495978707e13), 1.0, places=14)
        self.assertEqual(tc.MYR_S, 1e6 * 365.25 * 86400)


class PowerLawRoundTrips(unittest.TestCase):
    """A1-1: pure power laws convert exactly; there and back within 1e-12."""

    def test_all_pairs(self):
        groups = {1.0: ["galprop", "usine-k0", "usine-k10", "canonical"],
                  0.0: ["dragon2", "usine-k0", "usine-k10", "canonical"],
                  0.7: ["usine-k0", "usine-k10", "canonical"]}
        for eta, names in groups.items():
            for delta, d0 in ((0.3, 1.2e28), (0.45, 3.0e28), (0.7, 8.5e28)):
                start = {"D0_cm2_s": d0, "R0_gv": 1.0, "delta": delta, "eta": eta}
                for a, b in itertools.permutations(names, 2):
                    with self.subTest(eta=eta, delta=delta, pair=(a, b)):
                        there = tc.convert_diffusion(start, "canonical", a)
                        self.assertEqual(there["conversion_status"], "exact")
                        mid = tc.convert_diffusion(there["result"], a, b)
                        self.assertEqual(mid["conversion_status"], "exact")
                        back = tc.convert_diffusion(mid["result"], b, a)
                        # canonical keeps its input's R0, so compare D at 1 GV of the canonical forms
                        self.assertLess(abs(at_1gv(back) / at_1gv(there) - 1), 1e-12)
                        if a != "canonical":
                            name = tc.CODE_CONVENTIONS[a]["normalization_name"]
                            self.assertLess(abs(back["result"][name] / there["result"][name] - 1), 1e-12)
                        home = tc.convert_diffusion(back["result"], a, "canonical")
                        r0 = home["result"]["R0_gv"]
                        self.assertLess(abs(home["result"]["D0_cm2_s"] / (d0 * r0 ** delta) - 1), 1e-12)

    def test_k10_is_k0_times_ten_to_delta(self):
        out = tc.convert_diffusion({"K0": 0.1, "delta": 0.45, "eta": 1.0}, "usine-k0", "usine-k10")
        self.assertLess(abs(out["result"]["K10"] / (0.1 * 10 ** 0.45) - 1), 1e-14)

    def test_galprop_reference_4gv(self):
        out = tc.convert_diffusion({"D0_cm2_s": 3e28, "R0_gv": 1.0, "delta": 0.5, "eta": 1.0}, "canonical", "galprop")
        self.assertLess(abs(out["result"]["D0"] - 3.0 * 4 ** 0.5), 1e-12)

    def test_eta_mismatch_not_convertible(self):
        out = tc.convert_diffusion({"D0": 3.0, "delta": 0.5}, "galprop", "dragon2")
        self.assertEqual(out["conversion_status"], "not-convertible")
        self.assertIn("eta", out["reason"])

    def test_momentum_reference_refused(self):
        out = tc.convert_diffusion({"D0": 3e28, "delta": 0.5, "reference": "momentum"}, "dragon2", "canonical")
        self.assertEqual(out["conversion_status"], "not-convertible")

    def test_wrong_fixed_reference_rejected(self):
        with self.assertRaises(tc.ConventionError):
            tc.convert_diffusion({"D0": 3.0, "R0_gv": 1.0, "delta": 0.5}, "galprop", "canonical")


class Breaks(unittest.TestCase):
    """A1-4: with breaks, approximate or not-convertible; K0 <-> K10 with a break never exact."""

    BREAK = {"kind": "low", "R_break_gv": 5.0, "delta_below": 0.15, "s": 0.05, "s_convention": "usine"}

    def spec(self, **extra):
        return {"K0": 0.05, "delta": 0.45, "eta": 1.0, "breaks": [dict(self.BREAK, **extra)]}

    def test_k0_k10_with_break_never_exact(self):
        for brk in (self.BREAK, dict(self.BREAK, R_break_gv=1e-3), dict(self.BREAK, s=0.3)):
            for a, b in (("usine-k0", "usine-k10"), ("usine-k10", "usine-k0")):
                with self.subTest(brk=brk, pair=(a, b)):
                    spec = {"K0" if a == "usine-k0" else "K10": 0.05, "delta": 0.45, "eta": 1.0, "breaks": [brk]}
                    out = tc.convert_diffusion(spec, a, b)
                    self.assertIn(out["conversion_status"], ("approximate", "not-convertible"))
                    self.assertNotEqual(out["conversion_status"], "exact")
                    if out["conversion_status"] == "approximate":
                        self.assertGreaterEqual(out["relative_error_bound"], 0.0)

    def test_bound_covers_break_factor_at_reference(self):
        out = tc.convert_diffusion(self.spec(), "usine-k0", "usine-k10")
        self.assertEqual(out["conversion_status"], "approximate")
        f10 = tc.break_factor(10.0, 0.45, [self.BREAK])
        self.assertGreaterEqual(out["relative_error_bound"], abs(f10 - 1) * (1 - 1e-12))

    def test_break_factor_limits(self):
        brk = [self.BREAK]
        hi = tc.break_factor(1e4, 0.45, brk)
        self.assertLess(abs(hi - 1), 1e-6)
        lo1, lo2 = tc.break_factor(0.01, 0.45, brk), tc.break_factor(0.001, 0.45, brk)
        # slope of D = R^delta f(R) well below the break is delta_below
        slope = 0.45 + math.log(lo1 / lo2) / math.log(10.0)
        self.assertLess(abs(slope - 0.15), 1e-6)

    def test_different_smoothness_not_convertible(self):
        out = tc.convert_diffusion(self.spec(), "usine-k0", "usine-k10", target_s_convention="other")
        self.assertEqual(out["conversion_status"], "not-convertible")
        out = tc.convert_diffusion(self.spec(s_convention="unknown"), "usine-k0", "usine-k10")
        self.assertEqual(out["conversion_status"], "not-convertible")

    def test_unevaluated_break_kind_not_convertible(self):
        out = tc.convert_diffusion(self.spec(kind="high"), "usine-k0", "usine-k10")
        self.assertEqual(out["conversion_status"], "not-convertible")

    def test_break_to_galprop_not_exact(self):
        out = tc.convert_diffusion(self.spec(), "usine-k0", "galprop")
        self.assertEqual(out["conversion_status"], "approximate")


class Reacceleration(unittest.TestCase):
    """A1-5: thin disc <-> whole halo is only approximate."""

    def test_zones(self):
        for a, b in (("thin-disc", "whole-halo"), ("whole-halo", "thin-disc")):
            out = tc.convert_alfven_speed(10.0, a, b, 4.0, 100.0)
            self.assertEqual(out["conversion_status"], "approximate")
            self.assertIsNone(out["relative_error_bound"])
        out = tc.convert_alfven_speed(10.0, "whole-halo", "thin-disc", 4.0, 100.0)
        self.assertAlmostEqual(out["result"]["V_A_kms"], 10.0 * math.sqrt(4.0 / 0.1), places=12)
        self.assertEqual(tc.convert_alfven_speed(10.0, "thin-disc", "thin-disc", 4.0, 100.0)["conversion_status"],
                         "exact")

    def test_cli(self):
        code, out = run("reacceleration", "--alfven-speed-km-s", "10", "--from-zone", "whole-halo", "--to-zone",
                        "thin-disc", "--l-kpc", "4", "--disc-halfwidth-pc", "100")
        self.assertEqual(code, 0)
        self.assertEqual(out["conversion"]["conversion_status"], "approximate")


class EnergyAndNames(unittest.TestCase):
    def test_energy(self):
        rows = tc.convert_energy(11, "ek-total", [11.0, 110.0], [2.0, 4.0])
        self.assertEqual(rows[0]["ekn_gev"], 1.0)
        self.assertEqual(rows[1]["flux_per_ekn"], 44.0)
        self.assertEqual(rows[1]["flux_per_ek_total"], 4.0)
        back = tc.convert_energy(11, "ekn", [r["ekn_gev"] for r in rows], [r["flux_per_ekn"] for r in rows])
        for r, b in zip(rows, back):
            self.assertEqual(r["ek_total_gev"], b["ek_total_gev"])
            self.assertEqual(r["flux_per_ek_total"], b["flux_per_ek_total"])

    def test_legacy_names(self):
        out = tc.map_legacy_names({"D0": 3e28, "L": 4.0, "D0_unit": "cm^2 s^-1", "L_unit": "kpc", "delta": 0.5})
        self.assertEqual(out["canonical"], {"D0_cm2_s": 3e28, "L_kpc": 4.0, "delta": 0.5})
        self.assertEqual(out["mapped"], {"D0": "D0_cm2_s", "L": "L_kpc"})
        self.assertEqual(out["unmapped"], [])
        out = tc.map_legacy_names({"D0": 0.1, "D0_unit": "kpc^2/Myr", "L": 400.0, "L_unit": "pc"})
        self.assertAlmostEqual(out["canonical"]["D0_cm2_s"] / (0.1 * tc.KPC2_PER_MYR_CM2_S), 1.0, places=14)
        self.assertAlmostEqual(out["canonical"]["L_kpc"], 0.4, places=14)
        self.assertTrue(all(n in tc.CANONICAL_NAMES for n in tc.map_legacy_names({"D0": 1, "L": 1})["canonical"]))

    def test_dragon2_spec_keys_match_harmonized(self):
        spec = json.loads(DRAGON2_SPEC.read_text(encoding="utf-8"))
        canon = tc.to_canonical(spec["diffusion"], "canonical")
        harm = json.loads(HARMONIZED.read_text(encoding="utf-8"))["transport"]["diffusion"]
        for key in ("D0_cm2_s", "R0_gv", "delta", "eta"):
            self.assertAlmostEqual(canon[key] / harm[key], 1.0, places=12, msg=key)


class Harmonized(unittest.TestCase):
    """A1-6: harmonized-v1 carries every r3 5.5 row in the r3 5.4 transport structure."""

    TRANSPORT_KEYS = {"geometry", "diffusion", "reacceleration", "convection", "losses", "decay", "gas", "sources",
                      "cross_sections", "species", "family", "free"}
    NESTED_KEYS = {"geometry": {"kind", "L_kpc", "radius_kpc", "disc_halfwidth_pc"},
                   "diffusion": {"form", "D0_cm2_s", "R0_gv", "eta", "delta", "breaks"},
                   "reacceleration": {"V_A_kms", "zone", "relation", "w"},
                   "convection": {"V_c_kms", "dVc_dz_kms_per_kpc"},
                   "decay": {"enabled", "lorentz_dilation", "ec_treatment"},
                   "gas": {"model", "He_to_H_number"},
                   "sources": {"spatial", "injection", "abundances"},
                   "cross_sections": {"production_set", "inelastic_set", "ghost_threshold"},
                   "species": {"network_top", "isotopic"}}

    def setUp(self):
        self.doc = json.loads(HARMONIZED.read_text(encoding="utf-8"))
        self.t = self.doc["transport"]

    def test_structure_r3_5_4(self):
        self.assertEqual(set(self.t), self.TRANSPORT_KEYS)
        for block, keys in self.NESTED_KEYS.items():
            self.assertEqual(set(self.t[block]), keys, block)
        self.assertIsInstance(self.t["losses"], list)
        self.assertIsInstance(self.t["free"], list)
        for name in self.t["free"]:
            self.assertIn(name, tc.CANONICAL_NAMES)

    def test_values_r3_5_5(self):
        t = self.t
        self.assertEqual((t["geometry"]["kind"], t["geometry"]["L_kpc"], t["geometry"]["radius_kpc"],
                          t["geometry"]["disc_halfwidth_pc"]), ("cylinder-2d", 4.0, 20.0, 100))
        self.assertRegex(t["gas"]["model"], r"uniform.*n_H = 1 cm\^-3")
        self.assertEqual(t["gas"]["He_to_H_number"], 0.1)
        d = t["diffusion"]
        self.assertEqual((d["eta"], d["R0_gv"], d["delta"], d["breaks"], d["D0_cm2_s"]), (1.0, 1.0, 0.5, [], 3e28))
        self.assertEqual((t["reacceleration"]["V_A_kms"], t["convection"]["V_c_kms"]), (0.0, 0.0))
        self.assertEqual(t["convection"]["dVc_dz_kms_per_kpc"], 0.0)
        self.assertEqual(t["losses"], [])
        self.assertFalse(t["decay"]["enabled"])
        inj = t["sources"]["injection"]
        self.assertEqual([(i["gamma"], i["breaks"]) for i in inj], [(2.3, [])])
        self.assertIn("xs-illustrative", t["cross_sections"]["production_set"])
        self.assertIn("ILLUSTRATIVE", t["cross_sections"]["production_set"])
        self.assertFalse(self.doc["network"]["tertiary_chains"])
        self.assertFalse(self.doc["network"]["ghost_nuclei"])
        xs = json.loads((PLUGIN / "profiles" / "theory" / "cr-secondary-ratio" / "models" /
                         "xs-illustrative-A.json").read_text(encoding="utf-8"))
        parents = sorted({k.split("->")[0] for k in xs["production_mb"]})
        self.assertEqual(sorted(self.doc["network"]["parents"]), parents)
        out = self.doc["output"]
        self.assertEqual((out["quantity"], out["min"], out["max"], out["points_per_decade"], out["unit"]),
                         ("unmodulated LIS", 1.0, 1000.0, 20, "GeV/n"))
        self.assertEqual(t["family"], "SLIM")  # diffusion only: V_A = V_c = 0

    def test_diffusion_block_converts_exactly(self):
        out = tc.convert_diffusion(self.t["diffusion"], "canonical", "galprop")
        self.assertEqual(out["conversion_status"], "exact")

    def test_transport_schema_when_present(self):
        """Schema validation once A2 has added ext_theory_spec.transport; skipped before."""
        from contracts.schema import load_schema, validate
        prop = load_schema("ext_theory_spec.json").get("properties", {}).get("transport")
        if prop is None:
            self.skipTest("ext_theory_spec.transport not defined yet (added by cr-propagation A2)")
        report = validate(self.t, prop, doc_name="ext_theory_spec.json")
        self.assertTrue(report.ok, [f.message for f in report.errors])


class Cli(unittest.TestCase):
    def test_units(self):
        code, out = run("units")
        self.assertEqual((code, out["status"]), (0, "ok"))
        self.assertLess(abs(out["units"]["kpc2_per_myr_cm2_s"] / 3.0172e29 - 1), 1e-4)

    def test_diffusion_exit_codes(self):
        with tempfile.TemporaryDirectory() as work_dir:
            good = Path(work_dir) / "good.json"
            good.write_text(json.dumps({"from": "usine-k0", "to": "galprop",
                                        "diffusion": {"K0": 0.1, "delta": 0.5, "eta": 1.0}}))
            code, out = run("diffusion", "--input", str(good))
            self.assertEqual((code, out["status"], out["conversion"]["conversion_status"]), (0, "ok", "exact"))
            bad = Path(work_dir) / "bad.json"
            bad.write_text(json.dumps({"from": "galprop", "to": "dragon2", "diffusion": {"D0": 3.0, "delta": 0.5}}))
            code, out = run("diffusion", "--input", str(bad))
            self.assertEqual((code, out["status"]), (1, "refused"))
            code, out = run("diffusion", "--input", str(Path(work_dir) / "missing.json"))
            self.assertEqual((code, out["status"]), (2, "rejected"))

    def test_names_and_energy(self):
        with tempfile.TemporaryDirectory() as work_dir:
            f = Path(work_dir) / "p.json"
            f.write_text(json.dumps({"D0": 3e28, "L": 4.0}))
            code, out = run("names", "--input", str(f))
            self.assertEqual(code, 0)
            self.assertEqual(out["names"]["canonical"], {"D0_cm2_s": 3e28, "L_kpc": 4.0})
        code, out = run("energy", "--mass-number", "10", "--from-variable", "ekn", "--values", "1", "--flux-values", "5")
        self.assertEqual((code, out["rows"][0]["ek_total_gev"], out["rows"][0]["flux_per_ek_total"]), (0, 10.0, 0.5))
        code, out = run("energy", "--mass-number", "0", "--from-variable", "ekn", "--values", "1")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
