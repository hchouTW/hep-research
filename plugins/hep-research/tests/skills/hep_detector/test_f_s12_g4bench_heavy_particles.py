"""CHK-AT-09-04 evidence: the heavy-particle references refuse electrons and positrons.

geant4_benchmarks.py's stopping-power reference is the Bethe mean rate (RPP eq. 34.5) and its thin-layer-mpv and
thin-layer-width references the Landau-Vavilov Delta_p and xi (eq. 34.12); before the fix the script applied them to
e- and e+ as well (W_max from the heavy-particle kinematics), so a correct Geant4 electron run could fail a reference
benchmark: the transmitted electron's energy loss includes bremsstrahlung, and the collision stopping power of e- and
e+ is a different formula (eqs. 34.23-34.24).

Oracle (published, located): PDG RPP 2024 (the ledger's scifix:S01) states eq. (34.5) for "moderately relativistic
charged heavy particles" (sec. 34.2.3, p. 4; claim scifix:C01), in section 34.2 "Electronic energy loss by heavy
particles", which also holds eq. (34.12) (sec. 34.2.9, pp. 11-13); sec. 34.4.1 (pp. 17-18) says that the stopping power
"differs somewhat for electrons and positrons, and both differ from stopping power for heavy particles" and prints
different minima in silicon (e- 1.50, e+ 1.46, mu 1.66 MeV cm2/g). Expected behaviour from that printed scope: for e-
and e+ the stopping-power, thin-layer-mpv and thin-layer-width benchmarks and the reference command refuse the input
(exit 2, status rejected) instead of returning a heavy-particle number; for heavy particles they still run.

No numerical tolerance: the assertions are exit codes, statuses and the refusal's reason. All inputs are SYNTHETIC.
"""
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPT = PLUGIN / "skills" / "hep-detector" / "scripts" / "geant4_benchmarks.py"
REF = PLUGIN / "examples" / "geant4-thin-silicon" / "refdata" / "pdg-silicon-2024.json"
sys.path.insert(0, str(PLUGIN))
from core.simulation import summary as S  # noqa: E402

LEPTONS = ("e-", "e+")
HEAVY = ("mu-", "proton")
K = 16
COLS = ["event", "primary_eloss_MeV", "edep_Si_MeV", "primary_fate", "primary_end_process", "exit_dx", "exit_dy",
        "exit_dz"]
BINS = {"lo": 0.0, "hi": 0.4, "width": 0.004}
TRANSMITTED = [{"column": "primary_fate", "op": "==", "value": 1},
               {"column": "primary_end_process", "op": "==", "value": "Transportation"}]
DECL = [{"name": "loss_transmitted_MeV", "source_column": "primary_eloss_MeV", "selection": TRANSMITTED, "bins": BINS},
        {"name": "deposit_transmitted_MeV", "source_column": "edep_Si_MeV", "selection": TRANSMITTED, "bins": BINS}]
REFUSAL = "heavy charged particles"


def silicon() -> dict:
    v = json.loads(REF.read_text(encoding="utf-8"))["values"]
    st = dict(v["sternheimer"])
    st.pop("I_eV")
    return {"name": "Si_study", "density_g_cm3": v["density_g_cm3"], "z_over_a": round(14 / 28.0855, 6),
            "mean_excitation_eV": v["mean_excitation_eV"], "sternheimer": st, "reference_origin": "independent",
            "reference_source": "PDG atomic and nuclear properties, silicon, 2024 (test copy)"}


def run(*args) -> tuple[int, dict]:
    p = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                       timeout=600)
    return p.returncode, json.loads(p.stdout)


class HeavyParticleReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._t = tempfile.TemporaryDirectory()
        cls.d = Path(cls._t.name)
        (cls.d / "study.json").write_text(json.dumps({"schema": "geant4-study-spec/1", "materials": [silicon()]}),
                                          encoding="utf-8")
        rng = random.Random(5)
        rows = []
        for i in range(3200):  # a Landau-like loss of about 0.13 MeV in 0.3 mm of silicon, all transmitted
            loss = 0.11 + abs(rng.gauss(0.0, 0.01)) + rng.expovariate(1 / 0.01)
            rows.append(dict(zip(COLS, [i, loss, 0.95 * loss, 1, "Transportation", 1, 0, 0])))
        (cls.d / "run.json").write_text(json.dumps(S.build(rows, DECL, len(rows) // K, K)), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def bench(self, name: str, particle: str) -> dict:
        b = {"benchmark": name, "summary": "run.json", "particle": particle, "energy_MeV": 100.0,
             "material": "Si_study", "slab": "Si", "thickness_mm": 0.3,
             "observable": "deposit_transmitted_MeV" if name == "thin-layer-width" else "loss_transmitted_MeV",
             "tolerance": {"reference_accuracy_relative": 0.03, "k_sigma": 3}}
        if name == "thin-layer-mpv":
            b["binning"] = {"bin_width_MeV": BINS["width"]}
        return b

    def run_config(self, b: dict) -> tuple[int, dict]:
        cfg = self.d / "cfg.json"
        cfg.write_text(json.dumps({"schema": "geant4-benchmarks/1", "study_spec": "study.json", "benchmarks": [b]}),
                       encoding="utf-8")
        return run("run", "--config", cfg)

    def reference(self, particle: str) -> tuple[int, dict]:
        return run("reference", "--study-spec", self.d / "study.json", "--material", "Si_study", "--particle", particle,
                   "--energy-mev", 100.0, "--thickness-mm", 0.3)

    def test_electrons_and_positrons_are_refused_by_the_heavy_particle_references(self):
        for particle in LEPTONS:
            with self.subTest(command="reference", particle=particle):
                code, out = self.reference(particle)
                self.assertEqual((code, out.get("status")), (2, "rejected"), out)
                self.assertIn(REFUSAL, out.get("error", ""))
            for name in ("stopping-power", "thin-layer-mpv", "thin-layer-width"):
                with self.subTest(benchmark=name, particle=particle):
                    code, out = self.run_config(self.bench(name, particle))
                    self.assertEqual((code, out.get("status")), (2, "rejected"), out)
                    self.assertIn(REFUSAL, out.get("error", ""))

    def test_heavy_particles_still_get_a_reference(self):
        for particle in HEAVY:
            with self.subTest(command="reference", particle=particle):
                code, out = self.reference(particle)
                self.assertEqual((code, out.get("status")), (0, "ok"), out)
                self.assertGreater(out["bethe_MeV_cm2_g"], 0)
            with self.subTest(benchmark="stopping-power", particle=particle):
                code, out = self.run_config(self.bench("stopping-power", particle))
                self.assertNotEqual(out.get("status"), "rejected", out)
                self.assertIsInstance(out["benchmarks"][0]["reference_value"], float)


if __name__ == "__main__":
    unittest.main()
