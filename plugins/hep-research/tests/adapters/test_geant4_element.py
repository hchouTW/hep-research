"""Geant4 program B1: element_sim, simroot, check-spec, from-geometry, the analytic-helix oracle (geant4 adapter 0.3.0).

Offline tests need no Geant4: the cross-field rules of element_spec.py and geant4_run.py check-spec, the derivation of
an element_sim.spec/1 from a design-geometry/1 file (evaluate_design.py geometry on a J15 candidate built from Example
A's candidate) and the J15 realization profile, core/simulation/helix.py against the numbers of section B Appendix A,
the check values of sections B.4.1 and B.4.2, and the run plumbing of geant4_run.py with a fake element_sim and a fake
simroot. The live tests (HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG with "build_record" and "element_sim", optionally
"element_sim_test_hooks", an element_sim built with -DELEMENT_SIM_TEST_HOOKS=ON; simroot is found next to each) run the
real program on the J15 geometry (SYNTHETIC) and check the B1.10 acceptance items."""
import copy
import hashlib
import json
import math
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
ASSETS = PLUGIN / "adapters" / "geant4" / "assets"
FIX = PLUGIN / "tests" / "adapters" / "fixtures" / "geant4_b1"
EXAMPLE_A = PLUGIN / "examples" / "design-space-spectrometer" / "output" / "artifacts"
EVAL = PLUGIN / "skills" / "hep-detector" / "scripts" / "evaluate_design.py"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(ASSETS))
import element_spec as ES  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from core.simulation import helix as H  # noqa: E402
from core.simulation.seeds import job_seeds, logical_run_seed  # noqa: E402

LIVE = os.environ.get("HEP_GEANT4_LIVE_TEST") == "1" and os.environ.get("HEP_GEANT4_CONFIG")


def run(script, *args, timeout=600, cwd=None):
    p = subprocess.run([sys.executable, "-B", str(script), *map(str, args)], capture_output=True, text=True,
                       timeout=timeout, cwd=cwd)
    try:
        out = json.loads(p.stdout)
    except ValueError:
        out = {"raw": p.stdout[-500:], "stderr": p.stderr[-500:]}
    return p.returncode, out


def j15() -> dict:
    return json.loads((FIX / "j15_nominal.spec.json").read_text(encoding="utf-8"))


def profile() -> dict:
    return json.loads((FIX / "j15.realization.json").read_text(encoding="utf-8"))


def element(spec, name):
    return next(e for e in spec["elements"] if e["name"] == name)


class SpecRules(unittest.TestCase):
    """B1.1, B1.6: the schema and every kind of cross-field error, with check-spec's exit codes."""

    def mutated(self):
        def m(f):
            s = j15()
            f(s)
            return s

        def reseed(s, seed):
            s["run"].update(logical_run_seed=seed)
        return {
            "duplicate name": (m(lambda s: element(s, "Si2").update(name="Si1")), "not unique"),
            "unknown mother": (m(lambda s: element(s, "Si1").update(mother="Nowhere")), "unknown mother"),
            "two levels of nesting": (m(lambda s: element(s, "CaloSc").update(mother="CaloPb")), "placed once"),
            "daughter outside its mother": (m(lambda s: element(s, "Si1").update(centre_mm=[-519.9, 0.0, 0.0])),
                                            "not inside its mother"),
            "outside the world": (m(lambda s: element(s, "TOF1a").update(centre_mm=[-1199.0, 0.0, 0.0])),
                                  "not inside the world"),
            "overlapping siblings": (m(lambda s: element(s, "Si2").update(centre_mm=[-500.1, 0.0, 0.0])), "overlap"),
            "vacuum tracker plane": (m(lambda s: element(s, "Si3").update(material="G4_Galactic")), "not vacuum"),
            "calorimeter layer outside a calorimeter": (
                m(lambda s: element(s, "TOF1a").update(role="calorimeter-active")), "role calorimeter"),
            "two calorimeters": (m(lambda s: element(s, "FieldRegion").update(role="calorimeter")), "at most one"),
            "field on an unknown element": (m(lambda s: s["field"]["regions"].append(
                {"element": "Nowhere", "b_tesla": [0.0, 0.0, 1.0]})), "unknown element"),
            "nested field regions": (m(lambda s: s["field"]["regions"].append(
                {"element": "Si1", "b_tesla": [0.0, 0.0, 1.0]})), "nest"),
            "cut region on an unknown element": (m(lambda s: s["physics"].update(
                regions=[{"name": "R", "elements": ["Nowhere"], "cut_mm": 0.1}])), "unknown element"),
            "element in two cut regions": (m(lambda s: s["physics"].update(
                regions=[{"name": "A", "elements": ["Si1"], "cut_mm": 0.1},
                         {"name": "B", "elements": ["Si1"], "cut_mm": 0.2}])), "two physics regions"),
            "gps source": (m(lambda s: s["source"].update(type="gps")), "interface only"),
            "no energy": (m(lambda s: s["source"].pop("energy_MeV")), "exactly one of energy_MeV"),
            "energy per nucleon of an electron": (m(lambda s: (s["source"].pop("energy_MeV"), s["source"].update(
                particle="e-", ekin_per_nucleon_MeV=10.0))), "light ion"),
            "seeds not the job seeds": (m(lambda s: reseed(s, 12345)), "not the job seeds"),
            "threads without mt": (m(lambda s: s["run"].update(threads=4)), "run_manager mt"),
            "hits above the limit": (m(lambda s: (s["output"]["event_file"].update(level="hits"), s["run"].update(events=101))), "max_events_hits"),
            "observable on an unknown column": (m(lambda s: s["output"].update(
                observables=[{"name": "x", "source_column": "nope", "bins": {"lo": 0, "hi": 1, "width": 0.5}}],
                blocks={"blocks": 2, "block_size": 50})), "not CSV columns"),
            "beamOn in ui_commands": (m(lambda s: s.update(ui_commands=["/run/beamOn 10"])), "may not contain"),
            "unknown key (schema)": (m(lambda s: s.update(colour="red")), "colour"),
            "event numbers past 2^31 - 1": (m(lambda s: s["run"].update(first_event=2000000000, events=2000000000)),
                                            "32-bit"),
            "field on a repeated element": (m(lambda s: s["field"]["regions"].append(
                {"element": "CaloSc", "b_tesla": [0.0, 0.0, 1.0]})), "placed once"),
            "seeding stream (schema)": (m(lambda s: s["run"].update(seeding="stream")), "seeding"),
        }

    def test_j15_spec_passes(self):
        self.assertEqual(ES.check_spec(j15()), [])

    def test_each_error_is_refused_with_its_reason(self):
        for name, (spec, why) in self.mutated().items():
            with self.subTest(case=name):
                problems = ES.check_spec(spec)
                self.assertTrue(problems, name)
                self.assertTrue(any(why in p for p in problems), problems)

    def test_check_spec_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            ok = Path(d) / "ok.json"
            ok.write_text(json.dumps(j15()))
            code, out = run(ASSETS / "geant4_run.py", "check-spec", "--spec", ok)
            self.assertEqual((code, out["ok"], out["problems"]), (0, True, []))
            for name, (spec, why) in list(self.mutated().items())[:6]:
                bad = Path(d) / "bad.json"
                bad.write_text(json.dumps(spec))
                code, out = run(ASSETS / "geant4_run.py", "check-spec", "--spec", bad)
                with self.subTest(case=name):
                    self.assertEqual(code, 2)
                    self.assertFalse(out["ok"])
                    self.assertTrue(any(why in p for p in out["problems"]))

    def test_python_columns_follow_the_cpp_order(self):
        cols = ES.csv_columns(j15())
        names = [e["name"] for e in j15()["elements"]]
        self.assertEqual(cols[:11], ["event", "chunk", "weight", "primary_pdg", "primary_ekin_MeV", "primary_x_mm",
                                     "primary_y_mm", "primary_z_mm", "primary_dx", "primary_dy", "primary_dz"])
        self.assertEqual(cols[11:11 + len(names)], [f"edep_{n}_MeV" for n in names])
        self.assertEqual(cols[-5:], ["edep_world_MeV", "escape_world_MeV", "leak_rear_MeV", "leak_front_MeV",
                                     "leak_lateral_MeV"])
        src = (ASSETS / "element_sim" / "Actions.cc").read_text(encoding="utf-8")
        for c in ("\"edep_world_MeV\"", "\"escape_world_MeV\"", "\"leak_rear_MeV\"", "\"plen_\""):
            self.assertIn(c, src)


class FromGeometry(unittest.TestCase):
    """B1.8: geometry -> from-geometry rebuilds section B.4.1 from the J15 candidate; determinism; refusals."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        art = self.d / "art"
        (art / "candidates").mkdir(parents=True)
        shutil.copy(EXAMPLE_A / "design-spec.v1.json", art / "design-spec.v1.json")
        cand = json.loads((EXAMPLE_A / "candidates" / "cand-S.json").read_text(encoding="utf-8"))
        t = cand["extension"]["subsystems"]["DES-TRK-001"]["parameters"]
        t["layer_positions_m"]["value"] = [0.0, 0.16, 0.32, 0.48, 0.64, 0.8]
        t["layer_x_over_x0"]["value"] = 0.3 / 93.7  # 0.3 mm of G4_Si with the profile's X0 = 93.70 mm
        t["passive_x_over_x0"]["value"] = 0.0
        cand["extension"]["subsystems"]["DES-MAG-001"]["parameters"]["field_T"]["value"] = 0.5
        self.cand = art / "candidates" / "cand-S.json"
        self.cand.write_text(json.dumps(cand, indent=1))
        self.art = art
        self.prof = self.d / "j15.realization.json"
        self.prof.write_text(json.dumps(profile(), indent=1))

    def tearDown(self):
        self._t.cleanup()

    def geometry(self, gid="G1"):
        code, out = run(EVAL, "geometry", "--artifacts", self.art, "--candidate", "ams-like-v1:cand-S",
                        "--figure-of-merit", "momentum-resolution-core", "--denominator", "rigidity_GV=1",
                        "--denominator", "species=proton", "--id", gid, cwd=self.d)
        self.assertEqual(code, 0, out)
        return self.art / "studies" / f"{gid}.geometry.json"

    def derive(self, geom, out_name="G1.element_sim.json", prof=None):
        out = self.d / out_name
        code, doc = run(ASSETS / "geant4_run.py", "from-geometry", "--geometry", geom, "--profile", prof or self.prof,
                        "--out", out, cwd=self.d)
        return code, doc, out

    def test_rebuilds_the_hand_written_j15_element_by_element(self):
        code, doc, out = self.derive(self.geometry())
        self.assertEqual(code, 0, doc)
        got, want = json.loads(out.read_text(encoding="utf-8")), j15()
        self.assertEqual({e["name"]: e for e in got["elements"]}, {e["name"]: e for e in want["elements"]})
        for key in ("world", "field", "physics", "source", "run", "output"):
            self.assertEqual(got[key], want[key], key)
        self.assertEqual(ES.check_spec(got), [])
        prov = got["provenance"]
        geom = self.art / "studies" / "G1.geometry.json"
        self.assertEqual(prov["geometry"]["sha256"], hashlib.sha256(geom.read_bytes()).hexdigest())
        self.assertEqual(prov["realization"]["sha256"], hashlib.sha256(self.prof.read_bytes()).hexdigest())
        self.assertEqual(prov["parameter_digest"], json.loads(geom.read_text())["parameter_digest"])
        self.assertEqual(prov["candidate"], "ams-like-v1:cand-S")

    def test_the_same_inputs_give_a_byte_identical_spec(self):
        geom = self.geometry()
        _, _, a = self.derive(geom, "a.json")
        _, _, b = self.derive(geom, "b.json")
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_one_parameter_changes_only_its_element(self):
        _, _, base = self.derive(self.geometry())
        ref = json.loads(base.read_text())
        cand = json.loads(self.cand.read_text())
        cand["extension"]["subsystems"]["DES-TRK-001"]["parameters"]["layer_positions_m"]["value"][2] = 0.33
        self.cand.write_text(json.dumps(cand, indent=1))
        _, _, moved = self.derive(self.geometry("G2"), "moved.json")
        new = json.loads(moved.read_text())
        changed = [e["name"] for e in new["elements"] if e != element(ref, e["name"])]
        self.assertEqual(changed, ["Si3"])
        self.assertAlmostEqual(element(new, "Si3")["centre_mm"][0], -170.0, places=9)
        cand["extension"]["subsystems"]["DES-MAG-001"]["parameters"]["field_T"]["value"] = 0.4
        cand["extension"]["subsystems"]["DES-TRK-001"]["parameters"]["layer_positions_m"]["value"][2] = 0.32
        self.cand.write_text(json.dumps(cand, indent=1))
        _, _, field = self.derive(self.geometry("G3"), "field.json")
        new = json.loads(field.read_text())
        self.assertEqual(new["elements"], ref["elements"])
        self.assertEqual(new["field"]["regions"][0]["b_tesla"], [0.0, 0.0, 0.4])

    def test_max_track_time_reaches_the_spec(self):
        """Adapter 0.4.1: field.max_track_time_ns (a looper limit in vacuum field regions) is copied from the profile
        and accepted by check-spec; a negative value is refused."""
        p = profile()
        p["field"]["max_track_time_ns"] = 1000.0
        pp = self.d / "p.json"
        pp.write_text(json.dumps(p))
        code, doc, out = self.derive(self.geometry(), "t.json", pp)
        self.assertEqual(code, 0, doc)
        spec = json.loads(out.read_text())
        self.assertEqual(spec["field"]["max_track_time_ns"], 1000.0)
        self.assertEqual(ES.check_spec(spec), [])
        spec["field"]["max_track_time_ns"] = -1.0
        self.assertTrue(ES.check_spec(spec))

    def test_refusals(self):
        geom = self.geometry()
        doc = json.loads(geom.read_text())
        cases = {}
        bad = dict(doc, mapping_version="9.9.9")
        cases["unknown mapping version"] = (bad, None, "mapping version")
        cases["unknown geometry kind"] = (dict(doc, geometry="toroidal-magnet"), None, "geometry kind")
        p = profile()
        p["templates"].pop("bending")
        cases["no template for a role"] = (doc, p, "no template for role bending")
        p = profile()
        p["world"]["half_mm"] = [600.0, 600.0, 600.0]
        cases["derived spec fails check-spec"] = (doc, p, "fails check-spec")
        cases["geometry file not an object"] = ([doc], None, "design-geometry/1")
        for name, (g, prof, why) in cases.items():
            with self.subTest(case=name):
                gp = self.d / "g.json"
                gp.write_text(json.dumps(g))
                pp = None
                if prof is not None:
                    pp = self.d / "p.json"
                    pp.write_text(json.dumps(prof))
                code, out, _ = self.derive(gp, "x.json", pp)
                self.assertEqual(code, 2, out)
                self.assertIn(why, out["error"])


class Mapping11(unittest.TestCase):
    """B2.6 (CV-B2): geometry mapping 1.1.0 adds optional fields (tracker material and transverse size, field-region
    extent, TOF layers and time resolution, calorimeter front face, depth and sampling); a 1.0.0 candidate keeps its
    fields and digest, from-geometry realizes the new fields with a profile that declares 1.1.0 and refuses them
    otherwise; adding an optional parameter later changes the digest (the geometry becomes stale)."""

    setUp, tearDown = FromGeometry.setUp, FromGeometry.tearDown
    geometry, derive = FromGeometry.geometry, FromGeometry.derive
    PB_X0, PVT_X0 = 5.612, 425.4  # PDG 2024 Atomic and Nuclear Properties: lead 0.5612 cm, polyvinyltoluene 42.54 cm

    def par(self, value, unit):
        return {"value": value, "unit": unit, "source": "SYNTHETIC (test)", "status": "proposal"}

    def add_new_parameters(self, layers=40):
        cand = json.loads(self.cand.read_text())
        subs = cand["extension"]["subsystems"]
        subs["DES-TRK-001"]["parameters"]["layer_transverse_half_m"] = self.par([0.09, 0.09], "m")
        subs["DES-TRK-001"]["parameters"]["layer_material"] = self.par("G4_Si", "n/a")
        subs["DES-MAG-001"]["parameters"]["field_extent_m"] = self.par([-0.03, 0.83], "m")
        cal = {"method": "SYNTHETIC (test)", "control_samples": ["cosmic muons"]}
        subs["DES-TOF-001"] = {"role": "tof", "technology": "plastic scintillator", "interfaces": [], "calibration": cal,
                               "parameters": {"layer_positions_m": self.par([-0.305, -0.285, 0.995, 1.015], "m"),
                                              "layer_thickness_m": self.par(0.012, "m"),
                                              "time_resolution_ps": self.par(150.0, "ps")}}
        depth = layers * (2.0 / self.PB_X0 + 5.0 / self.PVT_X0)
        subs["DES-CAL-001"] = {"role": "calorimetry-em", "technology": "Pb/scintillator sampling", "interfaces": [],
                               "calibration": cal,
                               "parameters": {"front_position_m": self.par(1.06, "m"), "depth_x0": self.par(depth, "1"),
                                              "sampling_layers": self.par(layers, "1"),
                                              "passive_material": self.par("G4_Pb", "n/a"),
                                              "passive_thickness_mm": self.par(2.0, "mm"),
                                              "active_material": self.par("G4_PLASTIC_SC_VINYLTOLUENE", "n/a"),
                                              "active_thickness_mm": self.par(5.0, "mm")}}
        self.cand.write_text(json.dumps(cand, indent=1))

    def profile11(self, path="p11.json"):
        p = profile()
        p["mapping_versions"] = ["1.0.0", "1.1.0"]
        p["templates"]["calorimetry-em"] = {"radiation_lengths_mm": {"G4_Pb": self.PB_X0,
                                                                     "G4_PLASTIC_SC_VINYLTOLUENE": self.PVT_X0},
                                            "radiation_length_source": "PDG 2024 Atomic and Nuclear Properties"}
        out = self.d / path
        out.write_text(json.dumps(p, indent=1))
        return out

    def test_a_1_0_0_candidate_keeps_its_fields_refs_and_digest(self):
        geom = json.loads(self.geometry().read_text())
        self.assertEqual(geom["mapping_version"], "1.1.0")
        self.assertEqual(set(geom["fields"]), {"layer_positions_m", "layer_x_over_x0", "passive_x_over_x0",
                                               "point_resolution_um", "field_T"})
        self.assertEqual(len(geom["parameter_refs"]), 5)
        from contracts import design
        mapping = design.load_json(design.GEOMETRY_FILE)
        old = dict(mapping, mapping_version="1.0.0", fields=[f for f in mapping["fields"] if not f.get("optional")])
        proj = design.Project(self.art)
        self.assertEqual(design.geometry_fields(proj, "ams-like-v1:cand-S", old)[2], geom["parameter_digest"])
        code, doc, _ = self.derive(self.geometry("G9"))  # a 1.0.0 profile realizes it
        self.assertEqual(code, 0, doc)

    def test_new_fields_are_realized(self):
        self.add_new_parameters()
        geom = self.geometry()
        g = json.loads(geom.read_text())
        self.assertIn("DES-TOF-001.parameters.time_resolution_ps", g["parameter_refs"])
        code, doc, out = self.derive(geom, prof=self.profile11())
        self.assertEqual(code, 0, doc)
        spec = json.loads(out.read_text())
        self.assertEqual(element(spec, "Si1")["half_mm"][1:], [90.0, 90.0])
        fr = element(spec, "FieldRegion")
        self.assertAlmostEqual(fr["centre_mm"][0] - fr["half_mm"][0], -530.0, places=9)
        self.assertAlmostEqual(fr["centre_mm"][0] + fr["half_mm"][0], 330.0, places=9)
        for name, x in (("TOF1a", -805.0), ("TOF1b", -785.0), ("TOF2a", 495.0), ("TOF2b", 515.0)):
            self.assertAlmostEqual(element(spec, name)["centre_mm"][0], x, places=9)
            self.assertAlmostEqual(element(spec, name)["half_mm"][0], 6.0, places=9)
        calo, pb, sc = (element(spec, n) for n in ("Calo", "CaloPb", "CaloSc"))
        self.assertAlmostEqual(calo["centre_mm"][0] - calo["half_mm"][0], 560.0, places=9)
        self.assertAlmostEqual(calo["half_mm"][0], 140.0, places=9)
        self.assertAlmostEqual(pb["centre_mm"][0], 561.0, places=9)
        self.assertAlmostEqual(sc["centre_mm"][0], 564.5, places=9)  # Pb 560-562, scintillator 562-567
        self.assertEqual(pb["repeat"], {"count": 40, "pitch_mm": [7.0, 0.0, 0.0]})
        self.assertEqual(ES.check_spec(spec), [])
        import simreco_spec as RS
        reco = {"schema": "simreco.spec/1", "point_resolution_um": {"bending": 10.0, "non_bending": 30.0},
                "radiation_length_mm": {"G4_Si": 93.7}, "tof": {"sigma_t_ps": 100.0}}
        eff = RS.effective(reco, spec, 0, {}, None, g["fields"]["tof_time_resolution_ps"])
        self.assertEqual(eff["reco"]["tof"]["sigma_t_ps"], 150.0)

    def test_refusals(self):
        self.add_new_parameters()
        geom = self.geometry()
        code, out, _ = self.derive(geom)  # the 1.0.0 profile cannot realize the 1.1.0 fields
        self.assertEqual(code, 2, out)
        self.assertIn("mapping version", out["error"])
        g = json.loads(geom.read_text())
        cases = {"TOF count": (dict(g["fields"], tof_layer_positions_m=[0.0, 0.1]), "TOF layers"),
                 "depth": (dict(g["fields"], calo_depth_x0=20.0), "calo_depth_x0"),
                 "material": (dict(g["fields"], layer_material="G4_Ge"), "layer_material"),
                 "field extent": (dict(g["fields"], field_extent_m=[0.5, 0.1]), "field_extent_m"),
                 "partial sampling": ({k: v for k, v in g["fields"].items() if k != "calo_active_material"},
                                      "go together")}
        prof = self.profile11()
        for name, (fields, why) in cases.items():
            with self.subTest(case=name):
                gp = self.d / "g.json"
                gp.write_text(json.dumps(dict(g, fields=fields)))
                code, out, _ = self.derive(gp, "x.json", prof)
                self.assertEqual(code, 2, out)
                self.assertIn(why, out["error"])

    def test_adding_an_optional_parameter_changes_the_digest(self):
        before = json.loads(self.geometry().read_text())["parameter_digest"]
        self.add_new_parameters()
        after = json.loads(self.geometry("G2").read_text())["parameter_digest"]
        self.assertNotEqual(before, after)


class HelixOracle(unittest.TestCase):
    """B1.7's reference: core/simulation/helix.py against section B Appendix A and closed forms."""

    BOX = H.FieldBox([-520.0, -150.0, -150.0], [320.0, 150.0, 150.0], [0.0, 0.0, 0.5])

    def ys(self, rig, angle, xs=(-500, -340, -180, -20, 140, 300, 490, 510)):
        t = H.trajectory([-1000.0, 0.0, 0.0], [math.cos(angle), math.sin(angle), 0.0], rig, 1.0, [self.BOX], 5000)
        return [round(H.at_coordinate(t, 0, x)["position_mm"][1], 1) for x in xs]

    def test_appendix_a_field_check_grid(self):
        self.assertEqual(self.ys(0.6, 0.05), [25.0, 29.0, 26.6, 17.8, 2.5, -19.3, -50.0, -53.2])
        self.assertEqual(self.ys(1.0, 0.05), [25.0, 30.6, 32.4, 30.3, 24.4, 14.6, 0.2, -1.4])
        self.assertEqual(self.ys(10.0, 0.05)[-2:], [67.1, 67.9])
        self.assertEqual(self.ys(100.0, 0.05)[-2:], [73.8, 74.8])
        self.assertEqual(self.ys(1000.0, 0.05)[-2:], [74.5, 75.5])
        self.assertEqual(self.ys(0.6, -0.05, (300,)), [-151.2])  # with the bend, 0.6 and 1 GV miss Si6 (|y| > 100)
        self.assertEqual(self.ys(1.0, -0.05, (300,)), [-116.1])
        self.assertEqual(self.ys(0.6, 0.0, (300, 490, 510)), [-84.9, -125.6, -129.9])

    def test_every_grid_track_reaches_every_plane_and_stays_in_the_field_region(self):
        spec = j15()
        planes = [e for e in spec["elements"] if e["role"] in ("tracker-plane", "tof-layer") and e["centre_mm"][0] > -600]
        for rig in (0.6, 1.0, 10.0, 100.0, 1000.0):
            for d in ([1.0, 0.0, 0.0], [math.cos(0.05), math.sin(0.05), 0.0], [math.cos(0.05), 0.0, 0.05],
                      [math.cos(0.05), 0.0, -0.05]):
                t = H.trajectory([-1000.0, 0.0, 0.0], d, rig, 1.0, [self.BOX], 5000)
                region = t["segments"][1]
                self.assertNotEqual(region.kappa, 0.0)
                self.assertAlmostEqual(region.point(region.s1)[0][0], 320.0, places=6)  # leaves through the rear face
                for e in planes:
                    lo = [e["centre_mm"][i] - e["half_mm"][i] for i in range(3)]
                    hi = [e["centre_mm"][i] + e["half_mm"][i] for i in range(3)]
                    with self.subTest(rigidity=rig, direction=d, plane=e["name"]):
                        self.assertIsNotNone(H.first_entry(t, lo, hi))

    def test_radius_straight_line_and_time(self):
        t = H.trajectory([0.0, 0.0, 0.0], [1.0, 0.0, 0.0], 1.0, 1.0,
                         [H.FieldBox([-1e4, -1e4, -1e4], [1e4, 1e4, 1e4], [0.0, 0.0, 1.0])], 1000.0)
        r = 1.0 / (0.299792458e-3 * 1.0)  # mm, 1 GV in 1 T
        x, _ = t["segments"][0].point(math.pi * r / 2)  # a quarter turn: (r, -r) for a positive charge
        self.assertAlmostEqual(x[0], r, places=6)
        self.assertAlmostEqual(x[1], -r, places=6)
        s = H.trajectory([0.0, 0.0, 0.0], [1.0, 1.0, 0.0], 1.0, 1.0, [], 1000.0)
        p = H.at_coordinate(s, 0, 100.0)
        self.assertAlmostEqual(p["position_mm"][1], 100.0, places=9)
        self.assertAlmostEqual(p["time_ns"], math.sqrt(2) * 100.0 / 299.792458, places=12)

    def test_two_regions_are_followed_one_after_the_other(self):
        a = H.FieldBox([0.0, -500.0, -500.0], [100.0, 500.0, 500.0], [0.0, 0.0, 0.5])
        b = H.FieldBox([100.0, -500.0, -500.0], [200.0, 500.0, 500.0], [0.0, 0.0, 0.3])
        t = H.trajectory([-10.0, 0.0, 0.0], [1.0, 0.0, 0.0], 1.0, 1.0, [a, b], 400.0)
        kinds = [round(s.kappa, 9) for s in t["segments"]]
        self.assertEqual(kinds[:4], [0.0, round(0.299792458e-3 * 0.5, 9), round(0.299792458e-3 * 0.3, 9), 0.0])
        for s1, s2 in zip(t["segments"], t["segments"][1:]):
            p1, u1 = s1.point(s1.s1)
            self.assertLess(max(abs(p - q) for p, q in zip(p1, s2.x0)), 1e-9)
            self.assertLess(max(abs(p - q) for p, q in zip(u1, s2.u0)), 1e-12)

    def test_a_thin_plane_is_not_stepped_over(self):
        t = H.trajectory([-1000.0, 0.0, 0.0], [1.0, 0.0, 0.0], 0.6, 1.0, [self.BOX], 5000)
        e = H.first_entry(t, [-180.15, -100.0, -100.0], [-179.85, 100.0, 100.0])
        self.assertIsNotNone(e)
        self.assertAlmostEqual(e["position_mm"][0], -180.15, places=9)


class J15CheckValues(unittest.TestCase):
    """Sections B.4.1 and B.4.2 recomputed from the J15 spec (geometry), closed forms (tracker, TOF) and the helix
    oracle (acceptance). PDG values as in section B Appendix B (read 2026-10-21)."""

    X0_MM = {"G4_Si": 93.70, "G4_PLASTIC_SC_VINYLTOLUENE": 425.4, "G4_Pb": 5.612}

    def test_geometry(self):
        s = j15()
        si = [element(s, f"Si{k}") for k in range(1, 7)]
        f = element(s, "FieldRegion")
        lo, hi = f["centre_mm"][0] - f["half_mm"][0], f["centre_mm"][0] + f["half_mm"][0]
        self.assertEqual((lo, hi), (-520.0, 320.0))
        self.assertAlmostEqual((si[-1]["centre_mm"][0] - si[0]["centre_mm"][0]) / 1000, 0.800, places=12)
        self.assertAlmostEqual(si[0]["centre_mm"][0] - si[0]["half_mm"][0] - lo, 19.85, places=9)
        self.assertAlmostEqual(hi - si[-1]["centre_mm"][0] - si[-1]["half_mm"][0], 19.85, places=9)
        self.assertEqual(si[0]["centre_mm"][0] - lo, 20.0)
        st1 = (element(s, "TOF1a")["centre_mm"][0] + element(s, "TOF1b")["centre_mm"][0]) / 2
        st2 = (element(s, "TOF2a")["centre_mm"][0] + element(s, "TOF2b")["centre_mm"][0]) / 2
        self.assertEqual((st1, st2), (-795.0, 505.0))
        self.assertAlmostEqual((st2 - st1) / 1000, 1.300, places=12)
        tof2b, calo = element(s, "TOF2b"), element(s, "Calo")
        self.assertEqual(calo["centre_mm"][0] - calo["half_mm"][0] - tof2b["centre_mm"][0] - tof2b["half_mm"][0], 30.0)
        tof1a = element(s, "TOF1a")
        self.assertLess(s["source"]["position_mm"][0], tof1a["centre_mm"][0] - tof1a["half_mm"][0])
        self.assertLess(abs(s["source"]["position_mm"][0]), s["world"]["half_mm"][0])
        self.assertLess(calo["centre_mm"][0] + calo["half_mm"][0], s["world"]["half_mm"][0])
        pb = element(s, "CaloPb")
        x0 = pb["repeat"]["count"] * (2 * pb["half_mm"][0] / self.X0_MM["G4_Pb"]
                                      + 2 * element(s, "CaloSc")["half_mm"][0] / self.X0_MM["G4_PLASTIC_SC_VINYLTOLUENE"])
        self.assertAlmostEqual(x0, 18.41, delta=0.01)
        front = sum(2 * element(s, n)["half_mm"][0] / self.X0_MM[element(s, n)["material"]]
                    for n in ("TOF1a", "TOF1b", "TOF2a", "TOF2b", "Si1", "Si2", "Si3", "Si4", "Si5", "Si6"))
        self.assertAlmostEqual(front, 0.1132, delta=0.0002)

    def test_tracker_mdr_and_multiple_scattering(self):
        def exact(n):
            xs = [Fraction(i, n - 1) for i in range(n)]
            m = [[sum(x ** (i + j) for x in xs) for j in range(3)] for i in range(3)]
            det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                   + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
            return float(4 * (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / det)
        for n, want in ((4, 81.0), (6, 66.96), (8, 57.17)):
            self.assertAlmostEqual(exact(n), 720 * (n - 1) ** 3 / ((n - 2) * n * (n + 1) * (n + 2)), places=9)
            self.assertAlmostEqual(exact(n), want, places=2)
        mdr = lambda b, n, c=0.2998: c * b * 0.8 ** 2 / (10e-6 * math.sqrt(exact(n)))  # noqa: E731
        self.assertAlmostEqual(mdr(0.5, 6), 1172, delta=0.6)
        self.assertAlmostEqual(mdr(0.5, 6, 0.3), 1173, delta=0.6)
        for b, n, want in ((0.15, 6, 352), (1.0, 6, 2345), (0.5, 4, 1066), (0.5, 8, 1269)):
            self.assertAlmostEqual(mdr(b, n), want, delta=0.6)
        x = 6 * 0.03 / 9.370
        ms = 0.0136 * math.sqrt(x) * (1 + 0.038 * math.log(x)) / (0.299792458 * 0.5 * 0.8)
        self.assertAlmostEqual(100 * ms, 1.34, places=2)
        res = subprocess.run([sys.executable, "-B", str(PLUGIN / "skills/hep-detector/scripts/tracker_resolution.py"),
                              "--help"], capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 0)

    def test_tof_resolution(self):
        d_m = 1.3
        for ps, want in ((80, 1.8), (100, 2.3), (150, 3.5)):
            self.assertAlmostEqual(100 * ps * 1e-12 * 299792458 / d_m, want, delta=0.05)
        self.assertAlmostEqual(20e-3 / 299792458 * 1e12, 66.7, delta=0.05)  # 20 mm centre to centre at beta = 1

    def test_acceptance_thresholds(self):
        box = HelixOracle.BOX

        def ok(cond):
            lo, hi = 0.05, 100.0
            for _ in range(60):
                mid = (lo + hi) / 2
                lo, hi = (lo, mid) if cond(mid) else (mid, hi)
            return hi

        def y_at(r, x):
            t = H.trajectory([-1000.0, 0.0, 0.0], [1.0, 0.0, 0.0], r, 1.0, [box], 5000)
            p = H.at_coordinate(t, 0, x)
            return math.inf if p is None else abs(p["position_mm"][1])

        def stays(r):
            t = H.trajectory([-1000.0, 0.0, 0.0], [1.0, 0.0, 0.0], r, 1.0, [box], 5000)
            return abs(t["segments"][1].point(t["segments"][1].s1)[0][0] - 320.0) < 1e-6
        rm = 39.5  # effective Moliere radius of the calorimeter mixture (section B Appendix A)
        self.assertAlmostEqual(ok(stays), 0.364, delta=0.001)
        self.assertAlmostEqual(ok(lambda r: y_at(r, 300.0) <= 100.0), 0.511, delta=0.001)
        self.assertAlmostEqual(ok(lambda r: y_at(r, 490.0) <= 200.0), 0.385, delta=0.001)
        self.assertAlmostEqual(ok(lambda r: y_at(r, 520.0) <= 200.0), 0.404, delta=0.001)
        self.assertAlmostEqual(ok(lambda r: y_at(r, 550.0) <= 250.0 - 2 * rm), 0.490, delta=0.001)
        self.assertAlmostEqual(ok(lambda r: y_at(r, 900.0) <= 250.0 - 2 * rm), 0.745, delta=0.001)


FAKE_ELEMENT = r'''#!/usr/bin/env python3
"""Fake element_sim: the real program's file interface with invented events (no Geant4)."""
import json, os, sys, time
sys.path.insert(0, "@ASSETS@")
import element_spec as ES
spec = json.load(open(sys.argv[1]))
ui = spec.get("ui_commands", [])
if "/fake/refuse" in ui:
    print('ELEMENT_SIM_STATUS {"status": "rejected", "error": "UI command refused"}')
    sys.exit(2)
if "/fake/sleep" in ui:
    time.sleep(30)
cols = ES.csv_columns(spec)
first, n = spec["run"].get("first_event", 0), spec["run"]["events"]
with open("events.csv", "w") as fh:
    fh.write("# SIMULATION\n" + ",".join(cols) + "\n")
    for ev in range(first, first + n):
        row = [ev, 0, 1, 2212] + [100.0, -1000, 0, 0, 1, 0, 0] + [0.001 * (1 + ev % 3)] * (len(cols) - 11)
        fh.write(",".join(map(str, row)) + "\n")
json.dump({"materials": []}, open("materials.json", "w"))
json.dump({"geant4_version": "fake", "before_initialization": {},
           "after_run": {k: os.environ[k] for k in ("G4LEDATA",) if k in os.environ}}, open("datapaths.json", "w"))
json.dump({"column_map_version": "simulation-columns/1", "producer": "fake element_sim",
           "columns": [{"semantic": c, "column": c, "unit": "", "definition": "", "file": "csv",
                        "operation": {"kind": "rename"}} for c in cols]}, open("column_map.json", "w"))
hx = lambda v: float(v).hex()
mat = {"name": "G4_Galactic", "density_g_cm3": hx(1e-25), "state": "gas", "temperature_K": hx(2.73),
       "pressure_Pa": hx(3e-18), "mean_excitation_energy_eV": hx(21.8),
       "elements": [{"symbol": "H", "z": hx(1), "a_g_mole": hx(1.008), "mass_fraction": hx(1)}]}
box = lambda h: {"type": "G4Box", "parameters": {"half_x_mm": hx(h[0]), "half_y_mm": hx(h[1]), "half_z_mm": hx(h[2])}}
lvs = [{"id": 0, "name": "World", "solid": box(spec["world"]["half_mm"]), "material": "G4_Galactic", "field": None,
        "user_limits": None, "region": "DefaultRegionForTheWorld"}]
pls = [{"name": "World", "copy_number": 0, "logical": 0, "mother_logical": None, "translation_mm": [hx(0)] * 3,
        "rotation": None, "kind": "placement"}]
ids = {}
for i, e in enumerate(spec["elements"]):
    ids[e["name"]] = i + 1
    lvs.append({"id": i + 1, "name": e["name"], "solid": box(e["half_mm"]), "material": "G4_Galactic", "field": None,
                "user_limits": None, "region": None})
for e in spec["elements"]:
    m = e.get("mother", "world")
    origin = [0.0] * 3 if m == "world" else next(x for x in spec["elements"] if x["name"] == m)["centre_mm"]
    for k, c in enumerate(ES.copies(e)):
        pls.append({"name": e["name"], "copy_number": k, "logical": ids[e["name"]],
                    "mother_logical": 0 if m == "world" else ids[m],
                    "translation_mm": [hx(c[i] - origin[i]) for i in range(3)], "rotation": None, "kind": "placement"})
geometry = {"units": {"length": "mm"}, "logical_volumes": lvs, "placements": pls, "materials": [mat],
            "global_field": None, "gdml_sha256": None}
json.dump({"probe_version": "g4sim-probe/1", "engine": "geant4", "engine_version": "11.4.3", "recorded": True,
           "application_state": "GeomClosed", "couples": 1, "note": "fake", "geometry": geometry,
           "random_state_unchanged": True}, open("probe.json", "w"))
if spec.get("output", {}).get("event_file", {}).get("level", "none") != "none":
    open("events.root", "wb").write(b"fake root file " + str(n).encode())
print('ELEMENT_SIM_STATUS {"status": "ok"}')
'''

FAKE_SIMROOT = r'''#!/usr/bin/env python3
import hashlib, json, sys
data = open(sys.argv[2], "rb").read()
print(json.dumps({"status": "ok", "content_sha256": hashlib.sha256(b"content:" + data).hexdigest(), "files": 1,
                  "level": "crossings", "ntuples": {"events": {"rows": 3, "sha256": "0" * 64}}}))
'''


class RunPlumbing(unittest.TestCase):
    """geant4_run.py run with an element_sim spec (fake program): record, event-file block, seed scheme, sources,
    rejection and interruption."""

    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)
        ds = self.d / "install" / "share" / "Geant4" / "data" / "G4EMLOW8.8"
        ds.mkdir(parents=True)
        (ds / "table.dat").write_text("fake data\n")
        import geant4_build
        digest, nfiles = geant4_build.tree_hash(ds)
        rec = json.loads((PLUGIN / "tests/adapters/fixtures/geant4/records/geant4-build.computational-run.json")
                         .read_text(encoding="utf-8"))
        rec["extension"]["build"].update(install_prefix=str(self.d / "install"), datasets=[
            {"name": "G4EMLOW", "version": "8.8", "envvar": "G4LEDATA", "path": str(ds), "content_sha256": digest,
             "n_files": nfiles, "md5_verified": True}])
        self.build = self.d / "build.json"
        self.build.write_text(json.dumps(rec))
        bld = self.d / "bin"
        bld.mkdir()
        for name, body in (("element_sim", FAKE_ELEMENT.replace("@ASSETS@", str(ASSETS))), ("simroot", FAKE_SIMROOT)):
            f = bld / name
            f.write_text(f"#!{sys.executable}\n" + body.split("\n", 1)[1])
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
        self.exe = bld / "element_sim"

    def tearDown(self):
        self._t.cleanup()

    def go(self, spec, rid="e1", *extra):
        p = self.d / f"{rid}.spec.json"
        p.write_text(json.dumps(spec))
        return run(ASSETS / "geant4_run.py", "run", "--spec", p, "--exe", self.exe, "--build-record", self.build,
                   "--work", self.d / "work", "--run-id", rid, "--record", self.d / "art" / f"{rid}.json",
                   "--created", "2026-10-24", *extra)

    def small(self):
        s = j15()
        s["run"]["events"] = 3
        return s

    def test_record_event_file_and_seed_scheme(self):
        code, out = self.go(self.small())
        self.assertEqual(code, 0, out)
        rec = json.loads((self.d / "art" / "e1.json").read_text())
        self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())
        sim = rec["extension"]["simulation"]
        self.assertEqual(sim["program"]["name"], "element_sim")
        self.assertEqual((sim["seed_scheme"], sim["logical_run_seed"]), ("hash-v1", j15()["run"]["logical_run_seed"]))
        keys = set(sim["program"]["sources_sha256"])
        self.assertTrue({"element_sim/Field.cc", "simroot/simroot.cc", "g4sim/SimProbe.hh"} <= keys)
        self.assertFalse(any(k.startswith("layered_sim/") for k in keys))
        ef = sim["event_file"]
        root = self.d / "work" / "e1" / "events.root"
        self.assertEqual(ef["sha256"], hashlib.sha256(root.read_bytes()).hexdigest())
        self.assertEqual(ef["content_sha256"], hashlib.sha256(b"content:" + root.read_bytes()).hexdigest())
        self.assertFalse(ef["committed"])
        self.assertEqual(sim["effective_config"]["source"], "probe")
        self.assertEqual(sim["source"]["particle"], "proton")
        self.assertIn("element_sim run e1", rec["objective"])

    def test_no_event_file_at_level_none(self):
        s = self.small()
        s["output"] = {}
        code, out = self.go(s)
        self.assertEqual(code, 0, out)
        self.assertNotIn("event_file", json.loads((self.d / "art" / "e1.json").read_text())["extension"]["simulation"])

    def test_an_invalid_spec_is_refused_before_the_run(self):
        s = self.small()
        element(s, "Si2")["centre_mm"] = [-500.1, 0.0, 0.0]
        code, out = self.go(s)
        self.assertEqual(code, 2, out)
        self.assertIn("overlap", out["error"])
        self.assertFalse((self.d / "work" / "e1").exists())

    def test_a_refused_ui_command_and_an_interrupted_run(self):
        s = self.small()
        s["ui_commands"] = ["/fake/refuse"]
        self.assertEqual(self.go(s)[0], 2)
        s["ui_commands"] = ["/fake/sleep"]
        code, out = self.go(s, "e2", "--timeout", "2")
        self.assertEqual((code, out["status"]), (3, "incomplete"), out)
        self.assertFalse((self.d / "art" / "e2.json").exists())

    def test_logical_run_seed_must_be_the_specs(self):
        code, out = self.go(self.small(), "e1", "--logical-run-seed", "77")
        self.assertEqual(code, 2, out)


@unittest.skipUnless(LIVE, "set HEP_GEANT4_LIVE_TEST=1 and HEP_GEANT4_CONFIG to rerun with Geant4")
class Live(unittest.TestCase):
    """B1.10 on the real element_sim (J15, SYNTHETIC)."""

    @classmethod
    def setUpClass(cls):
        cfg = json.loads(Path(os.path.expanduser(os.environ["HEP_GEANT4_CONFIG"])).read_text(encoding="utf-8"))
        if "element_sim" not in cfg:
            raise unittest.SkipTest("HEP_GEANT4_CONFIG has no element_sim")
        cls.build = os.path.expanduser(cfg["build_record"])
        cls.exe = Path(os.path.expanduser(cfg["element_sim"]))
        cls.hooks = Path(os.path.expanduser(cfg["element_sim_test_hooks"])) if cfg.get("element_sim_test_hooks") else None
        cls._t = tempfile.TemporaryDirectory()
        cls.d = Path(cls._t.name)

    @classmethod
    def tearDownClass(cls):
        cls._t.cleanup()

    def go(self, spec, rid, exe=None, timeout=86400):
        p = self.d / f"{rid}.spec.json"
        p.write_text(json.dumps(spec))
        code, out = run(ASSETS / "geant4_run.py", "run", "--spec", p, "--exe", exe or self.exe, "--build-record",
                        self.build, "--work", self.d / "work", "--run-id", rid, "--record",
                        self.d / "records" / f"{rid}.json", "--timeout", timeout, timeout=7200)
        return code, out, self.d / "records" / f"{rid}.json"

    def simroot(self, exe, *args):
        p = subprocess.run([str(Path(exe).parent / "simroot"), *map(str, args)], capture_output=True, text=True,
                           timeout=600)
        return p.returncode, p.stdout

    def spec(self, point, **run_over):
        s = j15()
        S = logical_run_seed("geant4-b1-live", "test", point)
        s["run"].update(logical_run_seed=S, seeds=list(job_seeds(S, run_over.get("first_event", 0))), **run_over)
        return s

    def verify(self, *args):
        return run(ASSETS / "geant4_verify.py", *args)

    def test_j15_overlaps_material_budget_and_x0(self):
        s = self.spec("geantino", events=3)
        s.update(physics={"em_constructor": "G4EmStandardPhysics", "default_cut_mm": 0.7},
                 source={"type": "gun", "particle": "geantino", "energy_MeV": 1000.0,
                         "position_mm": [-1000.0, 0.0, 0.0], "direction": [1.0, 0.0, 0.0]},
                 output={"overlap_test_points": 10000})
        code, out, rec = self.go(s, "geantino")
        self.assertEqual(code, 0, out)
        code, ov = self.verify("overlaps", "--run-record", rec)
        self.assertEqual((code, ov["overlap_reports"]), (0, 0), ov)
        code, bud = self.verify("budget", "--run-record", rec)
        self.assertEqual(code, 0, bud)
        self.assertAlmostEqual(bud["spec_x_over_X0"], 18.41 + 0.1132, delta=0.02)

    def test_energy_balance_and_leakage(self):
        S = logical_run_seed("geant4-b1-live", "test", "balance")
        cal = {"schema": "element_sim.spec/1", "world": {"material": "G4_Galactic", "half_mm": [400.0, 400.0, 400.0]},
               "elements": [
                   {"name": "Calo", "material": "G4_Galactic", "centre_mm": [35.0, 0.0, 0.0],
                    "half_mm": [35.0, 100.0, 100.0], "role": "calorimeter"},
                   {"name": "Pb", "material": "G4_Pb", "centre_mm": [1.0, 0.0, 0.0], "half_mm": [1.0, 100.0, 100.0],
                    "mother": "Calo", "role": "calorimeter-passive", "repeat": {"count": 10, "pitch_mm": [7.0, 0, 0]}},
                   {"name": "Sc", "material": "G4_PLASTIC_SC_VINYLTOLUENE", "centre_mm": [4.5, 0.0, 0.0],
                    "half_mm": [2.5, 100.0, 100.0], "mother": "Calo", "role": "calorimeter-active",
                    "repeat": {"count": 10, "pitch_mm": [7.0, 0.0, 0.0]}}],
               "physics": {"em_constructor": "G4EmStandardPhysics_option4", "default_cut_mm": 0.7},
               "source": {"type": "gun", "particle": "e+", "energy_MeV": 1000.0, "position_mm": [-300.0, 0.0, 0.0],
                          "direction": [1.0, 0.0, 0.0]},
               "run": {"events": 100, "seeds": list(job_seeds(S, 0)), "seeding": "per-event", "logical_run_seed": S},
               "output": {"event_file": {"level": "summary"}}}
        code, out, rec = self.go(cal, "balance")
        self.assertEqual(code, 0, out)
        code, bal = self.verify("balance", "--run-record", rec, "--tolerance-mev", "0.001")
        self.assertEqual((code, bal["closure_test"]), (0, True), bal)
        for inj in ("omit-positron-mass", "double-count-leakage"):
            code, bad = self.verify("balance", "--run-record", rec, "--tolerance-mev", "0.001", "--inject", inj)
            with self.subTest(inject=inj):
                self.assertEqual(code, 1, bad)
        lines = (self.d / "work" / "balance" / "events.csv").read_text().splitlines()
        cols = lines[1].split(",")
        for ln in lines[2:]:
            r = dict(zip(cols, map(float, ln.split(","))))
            res = r["primary_ekin_MeV"] + 1.02199782 - sum(r[f"edep_{n}_MeV"] for n in ("Calo", "Pb", "Sc")) - sum(
                r[f"leak_{f}_MeV"] for f in ("rear", "front", "lateral"))
            self.assertLess(abs(res), 0.001)
        code, txt = self.simroot(self.exe, "dump", self.d / "work" / "balance" / "events.root", "--ntuple", "deposits")
        self.assertEqual(code, 0)
        dep = {}
        dl = txt.splitlines()
        dc = dl[0].split(",")
        for ln in dl[1:]:
            r = dict(zip(dc, ln.split(",")))
            key = (int(r["event_id"]), int(r["volume_id"]))
            dep[key] = dep.get(key, 0.0) + float(r["edep_MeV"])
        names = [e["name"] for e in cal["elements"]]
        for ln in lines[2:]:
            r = dict(zip(cols, map(float, ln.split(","))))
            for k, n in enumerate(names):
                self.assertAlmostEqual(dep.get((int(r["event"]), k), 0.0), r[f"edep_{n}_MeV"],
                                       delta=1e-8 * max(1.0, r[f"edep_{n}_MeV"]))

    def test_field_check_nominal_two_regions_grid_and_control(self):
        a = 0.05
        dirs = [[1.0, 0.0, 0.0], [math.cos(a), math.sin(a), 0.0], [math.cos(a), 0.0, math.sin(a)],
                [math.cos(a), 0.0, -math.sin(a)]]
        cycle = [{"energy_MeV": r * 1000.0, "direction": d} for r in (0.6, 1.0, 10.0, 100.0, 1000.0) for d in dirs]
        base = self.spec("field", events=len(cycle))
        base.update(physics={"em_constructor": "G4EmStandardPhysics", "default_cut_mm": 0.7},
                    source={"type": "gun", "particle": "chargedgeantino", "position_mm": [-1000.0, 0.0, 0.0],
                            "cycle": cycle}, output={"event_file": {"level": "crossings"}})
        nominal = self.d / "field-nominal.json"
        nominal.write_text(json.dumps(base))
        points = {}
        grid = [("delta_intersection_mm", v) for v in (1e-3, 1e-4, 1e-5, 1e-6)] + [
            ("max_step_mm", v) for v in (100.0, 30.0, 10.0, 3.0)]
        for key, v in grid:
            s = copy.deepcopy(base)
            s["field"][key] = v
            rid = f"field-{key}-{v:g}"
            code, out, rec = self.go(s, rid)
            self.assertEqual(code, 0, out)
            code, chk = self.verify("field", "--run-record", rec)
            points[(key, v)] = chk
            if (key, v) != ("delta_intersection_mm", 1e-3):  # every point is reported; 1e-3 mm is not presumed to pass
                with self.subTest(point=rid):
                    self.assertEqual((code, chk["compared"]), (0, 4 * 5 * 10), chk)  # 4 TOF layers and 6 planes
        fine = {(r["event"], r["plane"]): r for r in points[("delta_intersection_mm", 1e-6)]["rows"]}
        rows5 = points[("delta_intersection_mm", 1e-5)]["rows"]
        self.assertTrue(all(r["in_plane_um"] <= 0.5 for r in rows5))
        g4 = self.d / "work"
        x5 = {}
        for rid in ("field-delta_intersection_mm-1e-05", "field-delta_intersection_mm-1e-06"):
            code, txt = self.simroot(self.exe, "dump", g4 / rid / "events.root", "--ntuple", "crossings")
            lines = txt.splitlines()
            c = lines[0].split(",")
            x5[rid] = {(int(r[0]), int(r[1])): (float(r[c.index("y_mm")]), float(r[c.index("z_mm")]))
                       for r in (ln.split(",") for ln in lines[1:]) if int(r[c.index("track_id")]) == 1}
        a5, a6 = x5.values()
        self.assertEqual(set(a5), set(a6))
        self.assertLessEqual(max(1e3 * math.hypot(a5[k][0] - a6[k][0], a5[k][1] - a6[k][1]) for k in a5), 0.2)
        self.assertTrue(fine)
        # two regions with different B
        s = copy.deepcopy(base)
        els = [e for e in s["elements"] if e["name"] != "FieldRegion"]
        for e in els:
            if e.get("mother") == "FieldRegion":
                e["mother"] = "FieldA" if e["centre_mm"][0] < -100 else "FieldB"
        s["elements"] = [{"name": "FieldA", "material": "G4_Galactic", "centre_mm": [-310.0, 0.0, 0.0],
                          "half_mm": [210.0, 150.0, 150.0], "role": "passive"},
                         {"name": "FieldB", "material": "G4_Galactic", "centre_mm": [110.0, 0.0, 0.0],
                          "half_mm": [210.0, 150.0, 150.0], "role": "passive"}] + els
        s["field"]["regions"] = [{"element": "FieldA", "b_tesla": [0.0, 0.0, 0.5]},
                                 {"element": "FieldB", "b_tesla": [0.0, 0.0, 0.3]}]
        code, out, rec = self.go(s, "field-two-regions")
        self.assertEqual(code, 0, out)
        code, chk = self.verify("field", "--run-record", rec)
        self.assertEqual(code, 0, chk)
        # negative control: Geant4-side B x (1 + 1e-4) checked against the nominal field
        s = copy.deepcopy(base)
        s["field"]["regions"][0]["b_tesla"] = [0.0, 0.0, 0.5 * (1 + 1e-4)]
        code, out, rec = self.go(s, "field-control")
        self.assertEqual(code, 0, out)
        code, chk = self.verify("field", "--run-record", rec, "--reference-spec", nominal)
        self.assertEqual(code, 1, chk)
        self.assertGreater(chk["max_in_plane_um"], 0.5)

    def test_probe_records_the_field_and_the_field_counts_in_the_target_hash(self):
        s = self.spec("probe", events=2)
        code, out, rec = self.go(s, "probe-field")
        self.assertEqual(code, 0, out)
        ec = json.loads(Path(rec).read_text())["extension"]["simulation"]["effective_config"]
        tree = ec["geometry"]["tree"]
        lv = next(x for x in tree["logical_volumes"] if x["name"] == "Si1")
        f = lv["field"]
        self.assertEqual([float.fromhex(b) for b in f["b_tesla"]], [0.0, 0.0, 0.5])
        self.assertEqual(float.fromhex(f["delta_intersection_mm"]), 1e-5)
        self.assertEqual(f["stepper"], "G4DormandPrince745")
        self.assertIn("G4InterpolationDriver", f["driver"])
        from contracts.validate import geant4_tree_v1
        with_field = geant4_tree_v1({"geometry": {"tree": tree}}, ["FieldRegion"])["target_geometry_sha256"]
        no_field = copy.deepcopy(tree)
        for x in no_field["logical_volumes"]:
            if x.get("field"):
                x["field"] = None
        without = geant4_tree_v1({"geometry": {"tree": no_field}}, ["FieldRegion"])["target_geometry_sha256"]
        self.assertNotEqual(with_field, without)

    def test_threads_and_jobs_give_the_same_events(self):
        obs = [{"name": "si1", "source_column": "edep_Si1_MeV", "bins": {"lo": 0, "hi": 2, "width": 0.01}}]
        hashes, summaries = {}, {}
        for t in (1, 2, 4):
            s = self.spec("split", events=32, run_manager="mt" if t > 1 else "serial", threads=t)
            s["output"].update(observables=obs, blocks={"blocks": 4, "block_size": 8})
            code, out, rec = self.go(s, f"split-t{t}")
            self.assertEqual(code, 0, out)
            hashes[t] = json.loads(Path(rec).read_text())["extension"]["simulation"]["event_file"]["content_sha256"]
            summaries[t] = json.loads((self.d / "work" / f"split-t{t}" / "summary.json").read_text())["observables"]
        self.assertEqual(len(set(hashes.values())), 1, hashes)
        for t in (2, 4):
            for o1, o2 in zip(summaries[1], summaries[t]):
                for b1, b2 in zip(o1["blocks"], o2["blocks"]):
                    self.assertEqual((b1["n"], b1["hist"]), (b2["n"], b2["hist"]))
                    self.assertAlmostEqual(b1["sum"], b2["sum"], delta=1e-12 * max(1.0, abs(b1["sum"])))
        files = []
        for j in range(4):
            s = self.spec("split", events=8, first_event=8 * j)
            code, out, _ = self.go(s, f"split-j{j}")
            self.assertEqual(code, 0, out)
            files.append(self.d / "work" / f"split-j{j}" / "events.root")
        code, txt = self.simroot(self.exe, "hash", *files)
        self.assertEqual(code, 0, txt)
        self.assertEqual(json.loads(txt)["content_sha256"], hashes[1])
        code, txt = self.simroot(self.exe, "hash", files[0], files[0])
        self.assertEqual(code, 2, txt)  # the same events twice

    def test_simroot_round_trip_levels_and_limits(self):
        for level in ("summary", "crossings", "hits"):
            s = self.spec(f"level-{level}", events=5)
            s["output"]["event_file"] = {"level": level}
            code, out, rec = self.go(s, f"level-{level}")
            self.assertEqual(code, 0, out)
            root = self.d / "work" / f"level-{level}" / "events.root"
            code, txt = self.simroot(self.exe, "info", root)
            info = json.loads(txt)
            want = {"summary": {"processes", "events", "deposits"}, "crossings": {"processes", "events", "deposits",
                                                                                 "crossings"}}.get(level)
            with self.subTest(level=level):
                self.assertEqual(code, 0)
                self.assertEqual(set(info["ntuples"]), want or {"processes", "events", "deposits", "crossings", "hits"})
                self.assertEqual(info["ntuples"]["events"]["rows"], 5)
                run_row = info["run"][0]
                self.assertEqual(run_row["event_file_version"], "element_sim.events/1")
                self.assertEqual((run_row["first_event"], run_row["last_event"]), (0, 4))
                code, txt = self.simroot(self.exe, "dump", root, "--ntuple", "processes")
                names = [ln.split(",")[1] for ln in txt.splitlines()[1:]]
                self.assertEqual(names, sorted(names))
                csv = (self.d / "work" / f"level-{level}" / "events.csv").read_text().splitlines()
                code, txt = self.simroot(self.exe, "dump", root, "--ntuple", "events", "--columns",
                                         "event_id,edep_Si1_MeV")
                got = [ln.split(",") for ln in txt.splitlines()[1:]]
                cc = csv[1].split(",")
                for row_csv, row_root in zip(csv[2:], got):
                    v = row_csv.split(",")
                    self.assertEqual(int(row_root[0]), int(v[0]))
                    self.assertAlmostEqual(float(row_root[1]), float(v[cc.index("edep_Si1_MeV")]),
                                           delta=1e-9 * max(1e-3, abs(float(row_root[1]))))
        s = self.spec("hits-limit", events=200)
        s["output"]["event_file"] = {"level": "hits"}
        code, out, _ = self.go(s, "hits-limit")
        self.assertEqual(code, 2, out)
        s = self.spec("interrupted", events=200000)
        code, out, rec = self.go(s, "interrupted", timeout=3)
        self.assertEqual((code, out["status"]), (3, "incomplete"), out)

    def test_crossings_of_secondaries_and_primary_only(self):
        s = self.spec("crossings", events=30)
        code, out, rec = self.go(s, "crossings")
        self.assertEqual(code, 0, out)
        header = (self.d / "work" / "crossings" / "events.csv").read_text().splitlines()[1].split(",")
        self.assertEqual(header, ES.csv_columns(s))  # the C++ column order is the Python twin's
        sim = json.loads(Path(rec).read_text())["extension"]["simulation"]
        code, txt = self.simroot(self.exe, "info", self.d / "work" / "crossings" / "events.root")
        self.assertEqual(json.loads(txt)["run"][0]["spec_sha256"], sim["spec_sha256"])
        code, txt = self.simroot(self.exe, "dump", self.d / "work" / "crossings" / "events.root", "--ntuple",
                                 "crossings")
        lines = txt.splitlines()
        c = lines[0].split(",")
        rows = [dict(zip(c, ln.split(","))) for ln in lines[1:]]
        sec = [r for r in rows if r["track_id"] != "1"]
        self.assertTrue(sec, "no crossing of a secondary charged track")
        self.assertTrue(all(int(r["parent_id"]) >= 1 for r in sec))
        if self.hooks is None:
            self.skipTest("no element_sim_test_hooks build in HEP_GEANT4_CONFIG")
        s2 = copy.deepcopy(s)
        s2["ui_commands"] = ["/element_sim/test/primaryOnlyCrossings"]
        code, out, _ = self.go(s2, "crossings-primary", self.hooks)
        self.assertEqual(code, 0, out)
        code, txt = self.simroot(self.hooks, "dump", self.d / "work" / "crossings-primary" / "events.root", "--ntuple",
                                 "crossings")
        prim = txt.splitlines()[1:]
        self.assertEqual(prim, [ln for ln in lines[1:] if ln.split(",")[c.index("track_id")] == "1"])

    def test_every_thread_has_its_own_field_manager(self):
        if self.hooks is None:
            self.skipTest("no element_sim_test_hooks build in HEP_GEANT4_CONFIG")
        s = self.spec("threads-field", events=8, run_manager="mt", threads=4)
        s["ui_commands"] = ["/element_sim/test/reportFieldManagers"]
        code, out, _ = self.go(s, "threads-field", self.hooks)
        self.assertEqual(code, 0, out)
        log = (self.d / "work" / "threads-field" / "log.txt").read_text()
        ptrs = [ln.split("ptr=")[1] for ln in log.splitlines() if ln.startswith("ELEMENT_SIM_FIELD_MANAGER")]
        self.assertGreaterEqual(len(ptrs), 5)  # the master and four workers
        self.assertEqual(len(set(ptrs)), len(ptrs))


if __name__ == "__main__":
    unittest.main()
