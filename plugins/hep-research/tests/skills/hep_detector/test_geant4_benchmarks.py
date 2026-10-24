"""WP2 E: skills/hep-detector/scripts/geant4_benchmarks.py (independent-reference benchmarks for Geant4 runs).

The Bethe implementation is checked against the PDG muon table for silicon (examples/geant4-thin-silicon/refdata/,
an independent calculation); the benchmark logic on SYNTHETIC CSVs (energy loss at the reference passes, an offset at
the detection limit fails, deposit below loss, inelastic primaries excluded, kappa >= 0.05 not applicable); the
negative-control and reference-input rules; and the output fields. Standard library only."""
import gzip
import json
import math
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
sys.path.insert(0, str(PLUGIN))
import geant4_benchmarks as G  # noqa: E402
from core.simulation import summary as S  # noqa: E402

COLS = ["event", "primary_eloss_MeV", "edep_Si_MeV", "primary_fate", "primary_end_process", "exit_dx", "exit_dy",
        "exit_dz"]
K = 16
FINE = {"lo": 0.0, "hi": 0.4, "width": 0.004}
# the transmitted selection on layered_sim's CSV columns (the script names it by semantic columns, G.TRANSMITTED)
TRANSMITTED = [{"column": "primary_fate", "op": "==", "value": 1},
               {"column": "primary_end_process", "op": "==", "value": "Transportation"}]
DECL = [{"name": "loss_transmitted_MeV", "source_column": "primary_eloss_MeV", "selection": TRANSMITTED,
         "bins": FINE},
        {"name": "deposit_transmitted_MeV", "source_column": "edep_Si_MeV", "selection": TRANSMITTED, "bins": FINE},
        {"name": "deposit_as_loss_MeV", "source_column": "edep_Si_MeV", "selection": TRANSMITTED, "bins": FINE}]


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


class GradesMatchTheContracts(unittest.TestCase):
    def test_grades_are_the_contracts_table_classes(self):
        """CV-A1 (A1.1): the tool's GRADES name the same benchmarks as contracts.validate.GEANT4_BENCHMARKS and give
        each its class; the contract decides, the tool only reports."""
        sys.path.insert(0, str(PLUGIN))
        from contracts.validate import GEANT4_BENCHMARKS
        self.assertEqual(G.GRADES, {k: v["class"] for k, v in GEANT4_BENCHMARKS.items()})

    def test_study_spec_enums_follow_the_table(self):
        """D8 (A1.12): the study spec's benchmark names and grades are the table's names and classes."""
        sys.path.insert(0, str(PLUGIN))
        from contracts.validate import GEANT4_BENCHMARKS
        schema = json.loads((ASSETS / "geant4-study-spec.schema.json").read_text(encoding="utf-8"))
        item = schema["properties"]["validation_plan"]["properties"]["benchmarks"]["items"]["properties"]
        self.assertEqual(sorted(item["name"]["enum"]), sorted(GEANT4_BENCHMARKS))
        self.assertEqual(sorted(item["grade"]["enum"]), sorted({v["class"] for v in GEANT4_BENCHMARKS.values()}))


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

    def csv(self, name, rows, gz=False, decl=None, cols=COLS):
        """The per-event CSV and, next to it, its block summary (K blocks, simulation-summary/1) as name.json."""
        text = "# SIMULATION\n" + ",".join(cols) + "\n" + "".join(",".join(map(str, r)) + "\n" for r in rows)
        p = self.d / (name + (".csv.gz" if gz else ".csv"))
        p.write_bytes(gzip.compress(text.encode(), mtime=0)) if gz else p.write_text(text)
        dicts = [dict(zip(cols, r)) for r in rows]
        (self.d / f"{name}.json").write_text(json.dumps(S.build(dicts, decl or DECL, len(rows) // K, K)))
        return p.name

    @staticmethod
    def summ(csv):
        return csv.split(".")[0] + ".json"

    def run_record(self, name="run.json", world="G4_Galactic", others=()):
        """A SYNTHETIC layered_sim run record: one 0.3 mm Si slab (plus other slabs), in the given world."""
        slabs = [{"name": "Si", "material": "Si_study", "thickness_mm": 0.3, "sensitive": True}]
        slabs += [{"name": o, "material": "G4_Al", "thickness_mm": 1.0} for o in others]
        sim = {"geometry": {"lateral_mm": 10.0, "layers": [{"repeat": 1, "slabs": slabs}],
                            "world": {"material": world, "scale": 1.2}},
               "materials": [{"name": "Si_study", "z": 14, "a_g_mole": 28.0855, "density_g_cm3": 2.329}]}
        (self.d / name).write_text(json.dumps({"artifact_type": "computational-run", "artifact_id": name[:-5],
                                               "extension": {"simulation": sim}}))
        return name

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

    def sp(self, csv, control=None, inj=None, observable="loss_transmitted_MeV"):
        b = {"benchmark": "stopping-power", "summary": self.summ(csv), "observable": observable, "particle": "proton",
             "energy_MeV": 100.0, "material": "Si_study", "slab": "Si", "thickness_mm": 0.3,
             "tolerance": {"reference_accuracy_relative": 0.03, "k_sigma": 3}, "run_record": self.run_record()}
        if control:
            b["negative_controls"] = [{"summary": self.summ(control), "injected": f"density x {1 + inj}",
                                       "injected_relative": inj}]
        return b


class Configuration(_Cfg):
    """CV-A1 (A1.3): configuration and target hash from the named run record; only an isolated target validates."""

    def good(self, **kw):
        dl = 0.05
        b = self.sp(self.csv("good", self.protons()), self.csv("bad", self.protons(scale=1.2, seed=2)), dl)
        b.update(kw)
        return b

    def test_isolated_target_with_its_hash(self):
        code, out = run("run", "--config", self.config([self.good()]))
        b = out["benchmarks"][0]
        self.assertEqual((b["configuration"], b["hash_scheme"], b["target_slabs"]), ("isolated", "spec-v1", ["Si"]))
        self.assertRegex(b["target_geometry_sha256"], "^[0-9a-f]{64}$")
        self.assertEqual(b["configuration_basis"]["artifact_id"], "run")
        self.assertNotIn("configuration_gap", {k for k, v in b.items() if v})

    def test_embedded_target_or_no_run_record_is_no_evidence(self):
        cases = {"air world": self.good(run_record=self.run_record("air.json", world="G4_AIR")),
                 "other slab": self.good(run_record=self.run_record("two.json", others=("Al",))),
                 "no run record": {k: v for k, v in self.good().items() if k != "run_record"}}
        for name, b in cases.items():
            with self.subTest(name):
                code, out = run("run", "--config", self.config([b]))
                r = out["benchmarks"][0]
                self.assertFalse(r["validation_evidence"])
                self.assertTrue(r["configuration_gap"])
                self.assertTrue(any(r["configuration_gap"] in g for g in out["gaps"]), out["gaps"])

    def test_the_absorber_named_as_target_is_isolated_again(self):
        b = self.good(run_record=self.run_record("two.json", others=("Al",)), target_slabs=["Si", "Al"])
        r = run("run", "--config", self.config([b]))[1]["benchmarks"][0]
        self.assertEqual(r["configuration"], "isolated")


class StoppingPower(_Cfg):
    def test_loss_at_the_reference_passes_and_an_offset_at_the_detection_limit_fails(self):
        code, out = run("run", "--config", self.config([self.sp(self.csv("good", self.protons()))]))
        b = out["benchmarks"][0]
        self.assertEqual(b["verdict"], "pass", b)
        dl = b["detection_limit_relative"]  # planned: a control with the nominal's SE
        bad = self.csv("bad", self.protons(scale=1 + dl, seed=2))
        code, out = run("run", "--config", self.config([self.sp(self.csv("good", self.protons()), bad, round(dl, 4))]))
        self.assertEqual(code, 0, out)
        b = out["benchmarks"][0]
        self.assertEqual(b["negative_control"]["status"], "caught")
        self.assertTrue(b["negative_control"]["at_claimed_detection_limit"], b["negative_control"])
        self.assertEqual(b["scope"]["detection_limit_sign"], "+")  # one direction: the claim is narrowed
        self.assertTrue(any("one direction only" in g for g in out["gaps"]))
        self.assertTrue(b["validation_evidence"])
        self.assertIn("detection_limit_relative", b["scope"])

    def test_both_directions_validate_the_detection_limit(self):
        good = self.csv("good", self.protons())
        dl = run("run", "--config", self.config([self.sp(good)]))[1]["benchmarks"][0]["detection_limit_relative"]
        plus, minus = self.csv("plus", self.protons(scale=1 + dl, seed=2)), self.csv("minus", self.protons(scale=1 - dl, seed=3))
        b = self.sp(good, plus, round(dl, 4))
        b["negative_controls"].append({"summary": self.summ(minus), "injected_relative": -round(dl, 4)})
        out = run("run", "--config", self.config([b]))[1]
        r = out["benchmarks"][0]
        self.assertEqual((r["negative_control"]["status"], r["scope"]["detection_limit_sign"]), ("caught", "+-"), r)
        self.assertEqual([c["sign"] for c in r["negative_control"]["controls"]], ["+", "-"])

    def test_the_energy_loss_is_used_not_the_deposit(self):
        """A summary observable that carries the deposit under the energy-loss benchmark is refused."""
        code, out = run("run", "--config", self.config([self.sp(self.csv("dep", self.protons(deposit=0.8)),
                                                                observable="deposit_as_loss_MeV")]))
        self.assertEqual(code, 2, out)
        self.assertIn("energy loss of transmitted primaries", out["error"])

    def test_inelastic_and_stopped_primaries_are_excluded_and_counted(self):
        extra = [[4000 + i, 99.0, 1.0, 0, "protonInelastic", 0, 0, 0] for i in range(48)]
        code, out = run("run", "--config", self.config([self.sp(self.csv("inel", self.protons(extra=extra), gz=True))]))
        b = out["benchmarks"][0]
        self.assertEqual(b["verdict"], "pass")
        self.assertEqual(b["selection"]["excluded"], 48)

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
        for k in ("benchmark", "grade", "reference", "scope", "statistic", "geant4", "geant4_se", "geant4_dof",
                  "reference_value", "relative_difference", "relative_se", "tolerance", "detection_limit_relative",
                  "verdict", "negative_control", "validation_evidence"):
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
        b = {"benchmark": "thin-layer-mpv", "summary": self.summ(csv), "observable": "loss_transmitted_MeV",
             "particle": "mu-", "energy_MeV": 10000.0, "material": "Si_study", "slab": "Si", "thickness_mm": 0.3,
             "binning": {"bin_width_MeV": FINE["width"]}, "tolerance": {"reference_accuracy_relative": 0.03}}
        b.update(over)
        return b

    def test_mpv_at_the_reference_passes_with_the_block_mode_estimator(self):
        code, out = run("run", "--config", self.config([self.mpv(self.csv("mu", self.muons()))]))
        b = out["benchmarks"][0]
        self.assertEqual(b["verdict"], "pass", b)
        self.assertEqual((b["geant4_dof"], b["mpv_checks"]["fallback_blocks"]), (K - 1, 0))
        self.assertIn("three-point parabola", b["estimator"])

    def test_a_binning_other_than_the_summary_is_refused(self):
        code, out = run("run", "--config", self.config([self.mpv(self.csv("mu", self.muons()),
                                                                 binning={"bin_width_MeV": 0.002})]))
        self.assertEqual(code, 2, out)

    def test_kappa_above_005_is_not_applicable(self):
        rows = [[i, 0.25, 0.25, 1, "Transportation", 1, 0, 0] for i in range(160)]
        code, out = run("run", "--config", self.config([self.mpv(self.csv("p10", rows), particle="proton",
                                                                 energy_MeV=10.0)]))
        self.assertEqual(code, 3, out)
        self.assertEqual(out["benchmarks"][0]["verdict"], "not-applicable")

    def test_width_and_multiple_scattering_are_sanity_grade(self):
        csv = self.csv("mu", self.muons(n=3000))
        (self.d / "stack.json").write_text((ASSETS / "detector-stack.example.json").read_text(encoding="utf-8"))
        code, out = run("run", "--config", self.config([
            {"benchmark": "thin-layer-width", "summary": self.summ(csv), "observable": "deposit_transmitted_MeV",
             "particle": "mu-", "energy_MeV": 10000.0, "material": "Si_study", "slab": "Si", "thickness_mm": 0.3},
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
        self.assertTrue(any("no reference or setup-matched benchmark" in g for g in out["gaps"]))


class Containment(_Cfg):
    def rows(self, leak):
        cols = ["event", "primary_ekin_MeV", "leak_rear_MeV", "leak_front_MeV", "leak_lateral_MeV"]
        return "# SIMULATION\n" + ",".join(cols) + "\n" + "".join(f"{i},1000,{1000 * leak},0.6,0.1\n" for i in range(50))

    def bench(self, csv, **over):
        b = {"benchmark": "shower-containment", "csv": csv, "particle": "e-", "energy_MeV": 1000.0,
             "depth_x0": 20 / 12.65, "critical_energy_MeV": 10.41}
        b.update(over)
        return b

    def test_gamma_p_closed_forms(self):
        self.assertAlmostEqual(G.gamma_p(2.0, 1.0), 1 - 2 * math.exp(-1), places=14)
        self.assertAlmostEqual(G.gamma_p(3.0, 5.0), 1 - math.exp(-5) * (1 + 5 + 12.5), places=14)
        self.assertAlmostEqual(G.gamma_p(0.5, 0.2), math.erf(math.sqrt(0.2)), places=13)

    def test_plausible_implausible_and_outside_the_fit_range(self):
        (self.d / "near.csv").write_text(self.rows(0.95))
        (self.d / "far.csv").write_text(self.rows(0.5))
        out = run("run", "--config", self.config([self.bench("near.csv"), self.bench("far.csv"),
                                                  self.bench("near.csv", energy_MeV=500.0)]))[1]
        v = [b["verdict"] for b in out["benchmarks"]]
        self.assertEqual(v, ["plausible", "implausible", "not-applicable"], out)
        self.assertEqual({b["grade"] for b in out["benchmarks"]}, {"sanity"})
        self.assertIn("EGS4", out["benchmarks"][0]["reference"]["source"])

    def test_sternheimer_is_required_only_where_used(self):
        (self.d / "study.json").write_text(json.dumps({"materials": [{"name": "Si_study", "density_g_cm3": 2.329,
                                                                      "reference_origin": "independent",
                                                                      "reference_source": "PDG"}]}))
        (self.d / "near.csv").write_text(self.rows(0.95))
        self.assertEqual(run("run", "--config", self.config([self.bench("near.csv")]))[0], 0)
        code, out = run("run", "--config", self.config([self.sp(self.csv("good", self.protons()))]))
        self.assertEqual(code, 2, out)
        self.assertIn("z_over_a", out["error"])


if __name__ == "__main__":
    unittest.main()


class LongitudinalProfile(_Cfg):
    """longitudinal-profile: Gamma fit of per-layer means against a published fit (SYNTHETIC profiles)."""
    LAYERS = [t for t in range(1, 21) if t not in (5, 7, 10)]
    PUB = {"alpha": [5.42, 0.11], "beta": [0.50, 0.01], "source": "SYNTHETIC published fit (test)"}

    def rows(self, name, alpha=5.42, beta=0.5, stretch=1.0, n=300, seed=3):
        rng = random.Random(seed)
        cols = ["event"] + [f"edep_copy{t}_MeV" for t in self.LAYERS]
        lines = []
        for i in range(n):
            q = 4000 * rng.gauss(1, 0.05)
            lines.append([i] + [max(q * G.gamma_profile(t / stretch, alpha, beta) * rng.gauss(1, 0.1) + 1.0, 0.0)
                                for t in self.LAYERS])
        (self.d / name).write_text("# SIMULATION\n" + ",".join(cols) + "\n"
                                   + "".join(",".join(map(str, r)) + "\n" for r in lines))
        decl = [{"name": f"layer{t}", "source_column": f"edep_copy{t}_MeV", "bins": {"lo": 0, "hi": 1e6, "width": 1e6}}
                for t in self.LAYERS]
        out = name.split(".")[0] + ".json"
        (self.d / out).write_text(json.dumps(S.build([dict(zip(cols, r)) for r in lines], decl, n // K, K)))
        return out

    def bench(self, csv, **over):
        b = {"benchmark": "longitudinal-profile", "summary": csv, "particle": "e-", "energy_MeV": 100000.0,
             "layers": [{"t": t, "observable": f"layer{t}"} for t in self.LAYERS], "published": self.PUB,
             "systematic_relative": 0.01, "tolerance": {"k_sigma": 3}}
        b.update(over)
        return b

    def config(self, benches):
        p = self.d / "cfg.json"
        p.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": "study.json", "benchmarks": benches}))
        return p

    def test_fit_recovers_a_noiseless_profile(self):
        ts = list(range(1, 21))
        ys = [38000 * G.gamma_profile(t, 5.4, 0.5) + 70 for t in ts]
        fit = G.fit_gamma_profile(ts, ys, [1.0] * len(ts))
        for k, v in (("alpha", 5.4), ("beta", 0.5), ("Q_E", 38000), ("Q0", 70), ("t_max", 8.8)):
            self.assertAlmostEqual(fit[k], v, delta=1e-6 * max(1, v), msg=k)

    def test_pass_and_a_stretched_profile_caught_as_control(self):
        good, bad = self.rows("good.csv"), self.rows("stretched.csv", stretch=1.12, seed=4)
        code, out = run("run", "--config", self.config([self.bench(good, negative_control={
            "summary": bad, "injected": "depth scale x 1.12 (SYNTHETIC)", "injected_relative": 0.12})]))
        r = out["benchmarks"][0]
        self.assertEqual((code, r["grade"], r["verdict"]), (0, "setup-matched", "pass"), out)
        self.assertAlmostEqual(r["reference_value"], 4.42 / 0.5, places=12)
        self.assertAlmostEqual(r["reference_se"], math.hypot(0.11 / 0.5, 4.42 * 0.01 / 0.25), places=12)
        self.assertAlmostEqual(r["tolerance"]["parts"]["reference_accuracy"], r["reference_se"] / r["reference_value"]
                               + 0.01, places=12)
        self.assertEqual(r["negative_control"]["status"], "caught", r)
        self.assertLess(r["detection_limit_relative"], 0.12)

    def test_published_source_and_layers_are_required(self):
        good = self.rows("good.csv")
        for over in ({"published": {"alpha": [5.4, 0.1], "beta": [0.5, 0.01]}}, {"layers": [{"t": 1, "column": "x"}]}):
            with self.subTest(over=sorted(over)):
                code, out = run("run", "--config", self.config([self.bench(good, **over)]))
                self.assertEqual(code, 2, out)
