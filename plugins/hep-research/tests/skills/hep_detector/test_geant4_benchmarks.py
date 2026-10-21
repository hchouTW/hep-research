"""WP2 E: skills/hep-detector/scripts/geant4_benchmarks.py (independent-reference benchmarks for Geant4 runs).

The Bethe implementation is checked against the PDG muon table for silicon (examples/geant4-thin-silicon/refdata/,
an independent calculation); the benchmark logic on SYNTHETIC CSVs (energy loss at the reference passes, an offset at
the detection limit fails, deposit below loss, inelastic primaries excluded, kappa >= 0.05 not applicable); the
negative-control and reference-input rules; and the output fields. Standard library only."""
import gzip
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "geant4_benchmarks.py"
ASSETS = PLUGIN / "skills" / "hep-detector" / "assets"
REF = PLUGIN / "examples" / "geant4-thin-silicon" / "refdata" / "pdg-silicon-2024.json"
sys.path.insert(0, str(SCRIPT.parent))
import geant4_benchmarks as G  # noqa: E402

COLS = ["event", "primary_eloss_MeV", "edep_Si_MeV", "primary_fate", "primary_end_process", "exit_dx", "exit_dy",
        "exit_dz"]


def silicon(origin="independent"):
    v = json.loads(REF.read_text(encoding="utf-8"))["values"]
    st = dict(v["sternheimer"])
    st.pop("I_eV")
    return {"name": "Si_study", "density_g_cm3": v["density_g_cm3"], "z_over_a": round(14 / 28.0855, 6),
            "mean_excitation_eV": v["mean_excitation_eV"], "sternheimer": st, "reference_origin": origin,
            "reference_source": "PDG atomic and nuclear properties, silicon, 2024 (test copy)"}


def run(*args):
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True, timeout=600)
    return p.returncode, json.loads(p.stdout)


class Reference(unittest.TestCase):
    def test_k_constant_from_core_constants(self):
        self.assertAlmostEqual(G.K_BETHE, 0.307075, delta=2e-6)  # PDG Table 34.1: 0.307 075 MeV mol^-1 cm^2

    def test_bethe_and_density_effect_match_the_pdg_muon_table(self):
        mat = silicon()
        mass, z = G.particle_props("mu-")
        for t, ion, delta in json.loads(REF.read_text(encoding="utf-8"))["muon_ionization_check"]["rows"]:
            with self.subTest(T=t):
                self.assertLess(abs(G.bethe(t, mass, z, mat) / ion - 1), 0.003)
                self.assertAlmostEqual(G.density_effect(G.kinematics(t, mass)[2], mat["sternheimer"]), delta, delta=2e-3)

    def test_landau_mpv_and_kappa(self):
        mass, z = G.particle_props("mu-")
        lv = G.landau_mpv(10000.0, mass, z, silicon(), 0.3)
        self.assertLess(lv["kappa"], 1e-4)
        mp, zp = G.particle_props("proton")
        self.assertGreater(G.landau_mpv(10.0, mp, zp, silicon(), 0.3)["kappa"], 0.05)


class _Cfg(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        (self.d / "study.json").write_text(json.dumps({"schema": "geant4-study-spec/1", "materials": [silicon()]}))

    def tearDown(self):
        self._t.cleanup()

    def csv(self, name, rows, gz=False):
        text = "# SIMULATION\n" + ",".join(COLS) + "\n" + "".join(",".join(map(str, r)) + "\n" for r in rows)
        p = self.d / (name + (".csv.gz" if gz else ".csv"))
        p.write_bytes(gzip.compress(text.encode(), mtime=0)) if gz else p.write_text(text)
        return p.name

    def protons(self, scale=1.0, n=4000, seed=1, deposit=0.95, extra=()):
        mass, z = G.particle_props("proton")
        mean = G.bethe(100.0, mass, z, silicon()) * 2.329 * 0.03 * scale
        rng = random.Random(seed)
        rows = []
        for i in range(n):
            loss = rng.gauss(mean, 0.05 * mean)
            rows.append([i, loss, deposit * loss, 1, "Transportation", 1, 0, 0])
        return rows + list(extra)

    def config(self, benches):
        p = self.d / "cfg.json"
        p.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": "study.json", "benchmarks": benches}))
        return p

    def sp(self, csv, control=None, inj=None):
        b = {"benchmark": "stopping-power", "csv": csv, "particle": "proton", "energy_MeV": 100.0,
             "material": "Si_study", "slab": "Si", "thickness_mm": 0.3, "bootstrap": {"resamples": 40, "seed": 1},
             "tolerance": {"reference_accuracy_relative": 0.03, "k_sigma": 3}}
        if control:
            b["negative_control"] = {"csv": control, "injected": f"density x {1 + inj}", "injected_relative": inj}
        return b


class StoppingPower(_Cfg):
    def test_loss_at_the_reference_passes_and_an_offset_at_the_detection_limit_fails(self):
        code, out = run("run", "--config", self.config([self.sp(self.csv("good", self.protons()))]))
        b = out["benchmarks"][0]
        self.assertEqual(b["verdict"], "pass", b)
        dl = b["detection_limit_relative"]
        bad = self.csv("bad", self.protons(scale=1 + dl, seed=2))
        code, out = run("run", "--config", self.config([self.sp(self.csv("good", self.protons()), bad, round(dl, 4))]))
        self.assertEqual(code, 0, out)
        b = out["benchmarks"][0]
        self.assertEqual(b["negative_control"]["status"], "caught")
        self.assertTrue(b["negative_control"]["at_claimed_detection_limit"])
        self.assertTrue(b["validation_evidence"])
        self.assertIn("detection_limit_relative", b["scope"])

    def test_the_energy_loss_is_used_not_the_deposit(self):
        code, out = run("run", "--config", self.config([self.sp(self.csv("dep", self.protons(deposit=0.8)))]))
        b = out["benchmarks"][0]
        self.assertEqual(b["verdict"], "pass")
        self.assertAlmostEqual(b["mean_deposit_over_mean_loss"], 0.8, places=6)

    def test_inelastic_and_stopped_primaries_are_excluded_and_counted(self):
        extra = [[9000 + i, 99.0, 1.0, 0, "protonInelastic", 0, 0, 0] for i in range(40)]
        code, out = run("run", "--config", self.config([self.sp(self.csv("inel", self.protons(extra=extra), gz=True))]))
        b = out["benchmarks"][0]
        self.assertEqual(b["verdict"], "pass")
        self.assertEqual((b["selection"]["excluded"], b["selection"]["ended_in_hadronic_process"]), (40, 40))

    def test_a_control_that_is_not_caught_is_no_evidence(self):
        good = self.csv("good", self.protons())
        weak = self.csv("weak", self.protons(scale=1.005, seed=3))
        code, out = run("run", "--config", self.config([self.sp(good, weak, 0.005)]))
        self.assertEqual(code, 1, out)
        self.assertEqual(out["benchmarks"][0]["negative_control"]["status"], "not-caught")
        self.assertFalse(out["benchmarks"][0]["validation_evidence"])
        self.assertTrue(any("not caught" in g for g in out["gaps"]))

    def test_no_control_means_no_evidence(self):
        code, out = run("run", "--config", self.config([self.sp(self.csv("good", self.protons()))]))
        self.assertFalse(out["benchmarks"][0]["validation_evidence"])
        self.assertTrue(any("no negative control" in g for g in out["gaps"]))

    def test_reference_inputs_never_come_from_the_material_dump(self):
        good = self.csv("good", self.protons())
        a = run("run", "--config", self.config([self.sp(good)]))[1]["benchmarks"][0]["reference_value"]
        (self.d / "materials.json").write_text(json.dumps({"materials": [{"name": "Si_study", "density_g_cm3": 9.9,
                                                                          "mean_excitation_eV": 1.0}]}))
        b = run("run", "--config", self.config([self.sp(good)]))[1]["benchmarks"][0]["reference_value"]
        self.assertEqual(a, b)
        (self.d / "study.json").write_text(json.dumps({"materials": [silicon("geant4-material-dump")]}))
        code, out = run("run", "--config", self.config([self.sp(good)]))
        self.assertEqual(code, 2, out)
        self.assertIn("material dump", out["error"])

    def test_every_output_field(self):
        b = run("run", "--config", self.config([self.sp(self.csv("good", self.protons()))]))[1]["benchmarks"][0]
        for k in ("benchmark", "grade", "reference", "scope", "statistic", "geant4", "reference_value",
                  "relative_difference", "tolerance", "detection_limit_relative", "verdict", "negative_control",
                  "validation_evidence"):
            self.assertIn(k, b)
        self.assertEqual(set(b["reference"]), {"source", "version", "validity"})
        self.assertEqual(set(b["tolerance"]["parts"]), {"reference_accuracy", "mc_statistics", "k_sigma", "binning"})
        self.assertEqual(set(b["scope"]) - {"detection_limit_relative"},
                         {"particle", "energy_MeV", "material", "thickness_mm", "observable"})


class ThinLayer(_Cfg):
    def muons(self, scale=1.0, n=20000, seed=4):
        mass, z = G.particle_props("mu-")
        lv = G.landau_mpv(10000.0, mass, z, silicon(), 0.3)
        rng = random.Random(seed)
        rows = []
        for i in range(n):  # symmetric around delta_p with width 2 xi: the mode is delta_p
            loss = scale * (lv["delta_p_MeV"] + 2 * lv["xi_MeV"] * rng.gauss(0, 1))
            rows.append([i, loss, loss, 1, "Transportation", 0.9999, 0.003 * rng.gauss(0, 1), 0.003 * rng.gauss(0, 1)])
        return rows

    def mpv(self, csv, **over):
        b = {"benchmark": "thin-layer-mpv", "csv": csv, "particle": "mu-", "energy_MeV": 10000.0,
             "material": "Si_study", "slab": "Si", "thickness_mm": 0.3, "binning": {"bin_width_MeV": 0.002},
             "bootstrap": {"resamples": 30, "seed": 1}, "tolerance": {"reference_accuracy_relative": 0.03}}
        b.update(over)
        return b

    def test_mpv_at_the_reference_passes_and_reports_the_deposit_mpv(self):
        code, out = run("run", "--config", self.config([self.mpv(self.csv("mu", self.muons()))]))
        b = out["benchmarks"][0]
        self.assertEqual(b["verdict"], "pass", b)
        self.assertIn("most_probable_deposit_MeV", b)
        self.assertIn("least-squares parabola", b["estimator"])

    def test_kappa_above_005_is_not_applicable(self):
        rows = [[i, 0.5, 0.5, 1, "Transportation", 1, 0, 0] for i in range(100)]
        code, out = run("run", "--config", self.config([self.mpv(self.csv("p10", rows), particle="proton",
                                                                 energy_MeV=10.0)]))
        self.assertEqual(code, 3, out)
        self.assertEqual(out["benchmarks"][0]["verdict"], "not-applicable")

    def test_width_and_multiple_scattering_are_sanity_grade(self):
        csv = self.csv("mu", self.muons(n=3000))
        (self.d / "stack.json").write_text((ASSETS / "detector-stack.example.json").read_text(encoding="utf-8"))
        code, out = run("run", "--config", self.config([
            {"benchmark": "thin-layer-width", "csv": csv, "particle": "mu-", "energy_MeV": 10000.0,
             "material": "Si_study", "slab": "Si", "thickness_mm": 0.3},
            {"benchmark": "multiple-scattering", "csv": csv, "particle": "mu-", "energy_MeV": 10000.0,
             "highland_stack": "stack.json"}]))
        grades = {b["benchmark"]: b["grade"] for b in out.get("benchmarks", [])}
        self.assertEqual(grades, {"thin-layer-width": "sanity", "multiple-scattering": "sanity"}, out)
        self.assertFalse(any(b["validation_evidence"] for b in out["benchmarks"]))


class Shower(_Cfg):
    def test_an_uncontained_shower_maximum_is_not_applicable_and_a_gap(self):
        cols = ["event"] + [f"edep_copy{i}_MeV" for i in range(4)]
        text = "# SIMULATION\n" + ",".join(cols) + "\n" + "".join(f"{i},5,4,3,2\n" for i in range(20))
        (self.d / "sh.csv").write_text(text)
        code, out = run("run", "--config", self.config([{"benchmark": "em-shower-shape", "csv": "sh.csv",
                                                          "particle": "e-", "energy_MeV": 1000.0, "layer_x0": 0.4,
                                                          "critical_energy_MeV": 10.0}]))
        self.assertEqual(out["benchmarks"][0]["verdict"], "not-applicable", out)
        self.assertTrue(any("not contained" in g for g in out["gaps"]))
        self.assertTrue(any("no reference benchmark" in g for g in out["gaps"]))


if __name__ == "__main__":
    unittest.main()
