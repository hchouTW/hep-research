"""Geant4 program B2.1-B2.3: simreco (adapters/geant4/assets/simreco/, C++17, no Geant4) on toy events generated from
the analytic helix (core/simulation/helix.py) in the J15 geometry (SYNTHETIC), built here with the system C++ compiler
(-ffp-contract=off); skipped without one unless HEP_SIMRECO_REQUIRED=1 (the CI job "simreco", where a skip fails).

- The fitter (B2.1): on protons at 300 GV without multiple scattering, the spread of the relative inverse-rigidity
  residual equals tracker_resolution.py's measurement term within the toy's MC error, and the pull width is 1 within
  3 sigma_MC.
- Determinism: the same input gives byte-identical outputs.
- Tail sources (B2.2): noise-digitization alone and pattern-recognition alone widen the resolution and raise charge
  confusion; alignment and calibration-non-uniformity with 20 replicas widen the replica-mean core and give a replica
  spread > 0; the global field scale moves the core's mean and leaves its width and the charge signs unchanged;
  tail_sources_simulated lists only the stages on; the effect of curvature_offset_per_GV on charge confusion agrees
  with the Gaussian-core expression.
- The run summary simreco writes equals core/simulation/summary.py recomputed from its result CSV (A2.9's method).
- The result columns equal simreco_spec.RESULT_COLUMNS; the gaussian-core estimator and the F4 result helpers."""
import hashlib
import json
import math
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2]
ASSETS = PLUGIN / "adapters" / "geant4" / "assets"
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(ASSETS))
import simreco_spec as RS  # noqa: E402
from contracts.validate import validate_artifact  # noqa: E402
from core.simulation import estimates as E, helix as H, summary as S  # noqa: E402

CXX = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
REQUIRED = os.environ.get("HEP_SIMRECO_REQUIRED") == "1"
MP = 0.93827208943  # GeV, the proton mass of the particle table (core/constants, PDG 2026)
J15 = json.loads((PLUGIN / "tests/adapters/fixtures/geant4_b1/j15_nominal.spec.json").read_text(encoding="utf-8"))
BOX = H.FieldBox([-520.0, -150.0, -150.0], [320.0, 150.0, 150.0], [0.0, 0.0, 0.5])
ALL_TAILS = ("alignment", "calibration-non-uniformity", "noise-digitization", "pattern-recognition")


def entries(rigidity: float, charge: float = 1.0) -> list[tuple]:
    """(plane id, position, direction, time) of the exact helix's first entry into every J15 plane."""
    t = H.trajectory([-1000.0, 0.0, 0.0], [1.0, 0.0, 0.0], rigidity, charge, [BOX], 5000, MP)
    idx = {e["name"]: i for i, e in enumerate(J15["elements"])}
    out = []
    for e in J15["elements"]:
        if e["role"] not in ("tracker-plane", "tof-layer"):
            continue
        lo = [e["centre_mm"][k] - e["half_mm"][k] for k in range(3)]
        hi = [e["centre_mm"][k] + e["half_mm"][k] for k in range(3)]
        a = H.first_entry(t, lo, hi)
        out.append((idx[e["name"]], a["position_mm"], a["direction"], a["time_ns"]))
    return out


def write_toy(d: Path, rigidity: float, n: int, secondaries: bool = False, pdg: int = 2212) -> None:
    """Toy events: the exact helix entries, each event shifted transversely by its own offset (|dy|, |dz| <= 20 mm, a
    translation of the whole track: exact inside the field box, which is uniform in y and z)."""
    import random
    rng = random.Random(7)
    ek = (math.hypot(rigidity, MP) - MP) * 1000
    base = entries(rigidity, 1.0 if pdg > 0 else -1.0)
    with open(d / "events.csv", "w") as fe, open(d / "crossings.csv", "w") as fc:
        fe.write("# SIMULATION\nevent,primary_pdg,primary_ekin_MeV,edep_CaloSc_MeV\n")
        fc.write("event_id,plane_id,copy,track_id,parent_id,pdg,x_mm,y_mm,z_mm,dx,dy,dz,ekin_MeV,t_ns,edep_MeV\n")
        for ev in range(n):
            fe.write(f"{ev},{pdg},{ek!r},0\n")
            oy, oz = rng.uniform(-20, 20), rng.uniform(-20, 20)
            rows = [(pid, [x[0], x[1] + oy, x[2] + oz], u, tt) for pid, x, u, tt in base]
            for pid, x, u, tt in rows:
                # secondaries: in every third event the primary's entry into plane 6 (Si4, near the middle) is missing
                # and a delta electron 50 um away (about twice the 500 GV sagitta) is there instead: the only candidate
                # in the window, a wrong association that passes the fit and bends the track the other way
                if not (secondaries and pid == 6 and ev % 3 == 0):
                    fc.write(f"{ev},{pid},0,1,0,{pdg},{x[0]!r},{x[1]!r},{x[2]!r},{u[0]!r},{u[1]!r},{u[2]!r},{ek!r},"
                             f"{tt!r},0.1\n")
                if secondaries and pid == 6 and ev % 3 == 0:
                    fc.write(f"{ev},{pid},0,{ev + 2},1,11,{x[0]!r},{x[1] - 0.05!r},{x[2]!r},1,0,0,1.0,{tt!r},0.05\n")


def reco(extra: dict | None = None) -> dict:
    out = {"schema": "simreco.spec/1", "point_resolution_um": {"bending": 10.0, "non_bending": 30.0},
           "radiation_length_mm": {"G4_Si": 93.7}, "tof": {"sigma_t_ps": 100.0}, "fit": {"multiple_scattering": False},
           "output": {"observables": [
               {"name": "res", "source_column": "inv_rig_res", "bins": {"lo": -5, "hi": 5, "width": 0.001},
                "estimator": "gaussian-core", "selection": [{"column": "selected", "op": "==", "value": 1}]},
               {"name": "flip", "source_column": "charge_flip", "bins": {"lo": 0, "hi": 2, "width": 1},
                "thresholds": [0.5], "estimator": "proportion",
                "selection": [{"column": "selected", "op": "==", "value": 1}]},
               {"name": "pull", "source_column": "rho_pull", "bins": {"lo": -10, "hi": 10, "width": 0.01},
                "selection": [{"column": "selected", "op": "==", "value": 1}]}],
               "blocks": {"blocks": 16, "block_size": 250}}}
    out.update(extra or {})
    return out


@unittest.skipUnless(CXX or REQUIRED, "no C++ compiler: the simreco tests are optional here (required in CI job simreco)")
class Simreco(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not CXX:
            raise AssertionError("HEP_SIMRECO_REQUIRED=1 but no C++ compiler was found")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.exe = Path(cls.tmp.name) / "simreco"
        p = subprocess.run([CXX, "-std=c++17", "-O2", "-ffp-contract=off", "-I", str(ASSETS / "g4sim"),
                            str(ASSETS / "simreco" / "simreco.cc"), "-o", str(cls.exe)], capture_output=True, text=True,
                           timeout=600)
        if p.returncode:
            raise AssertionError(p.stderr[-2000:])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_reco(self, d: Path, spec: dict, replica: int = 0, tag: str = "r") -> tuple[list[dict], dict | None]:
        self.assertEqual(RS.check(spec, J15), [], RS.check(spec, J15))
        eff = RS.effective(spec, J15, replica, {"crossings": str(d / "crossings.csv"), "events": str(d / "events.csv"),
                                                "out_csv": str(d / f"{tag}.csv"), "out_summary": str(d / f"{tag}.json")})
        (d / f"{tag}.eff.json").write_text(json.dumps(eff))
        p = subprocess.run([str(self.exe), str(d / f"{tag}.eff.json")], capture_output=True, text=True, timeout=600)
        self.assertEqual(p.returncode, 0, p.stdout[-500:])
        lines = (d / f"{tag}.csv").read_text().splitlines()
        self.assertEqual(lines[0], "# RECONSTRUCTION")
        cols = lines[1].split(",")
        rows = [dict(zip(cols, map(float, ln.split(",")))) for ln in lines[2:]]
        summ = json.loads((d / f"{tag}.json").read_text()) if (d / f"{tag}.json").is_file() else None
        return rows, summ

    def toy(self, rigidity, n=4000, **kw) -> Path:
        d = Path(tempfile.mkdtemp(dir=self.tmp.name))
        write_toy(d, rigidity, n, **kw)
        return d

    def test_fitter_against_the_measurement_term(self):
        d = self.toy(300.0)
        rows, _ = self.run_reco(d, reco())
        ok = [r for r in rows if r["selected"] == 1]
        self.assertEqual(len(ok), len(rows))
        res = [r["inv_rig_res"] for r in ok]
        pulls = [r["rho_pull"] for r in ok]
        tr = subprocess.run([sys.executable, "-B", str(PLUGIN / "skills/hep-detector/scripts/tracker_resolution.py"),
                             "momentum", "--positions-m", "0", "0.16", "0.32", "0.48", "0.64", "0.8",
                             "--point-resolution-um", "10", "--field-tesla", "0.5", "--x-over-x0", "0", "--charge", "1",
                             "--mass-gev", str(MP), "--pt", "300"], capture_output=True, text=True, timeout=120)
        want = json.loads(tr.stdout)["intrinsic"]["slope_per_gev"] * 300
        sd = statistics.stdev(res)
        self.assertLess(abs(sd - want), 3 * want / math.sqrt(2 * len(res)), (sd, want))
        self.assertLess(abs(statistics.stdev(pulls) - 1), 3 / math.sqrt(2 * len(pulls)))
        self.assertLess(abs(statistics.fmean(res)), 3 * sd / math.sqrt(len(res)))

    def test_columns_and_determinism(self):
        d = self.toy(10.0, n=200)
        spec = reco({"output": {}})
        self.run_reco(d, spec, tag="a")
        self.run_reco(d, spec, tag="b")
        self.assertEqual((d / "a.csv").read_bytes(), (d / "b.csv").read_bytes())
        self.assertEqual((d / "a.csv").read_text().splitlines()[1].split(","), list(RS.RESULT_COLUMNS))

    def test_summary_equals_python_from_the_csv(self):
        d = self.toy(100.0)
        spec = reco()
        rows, summ = self.run_reco(d, spec)
        py = S.build(rows, spec["output"]["observables"], 250, 16, 0, {"seeding": "per-event"},
                     {"name": "python", "version": "-"})
        for oc, op in zip(summ["observables"], py["observables"]):
            for bc, bp in zip(oc["blocks"], op["blocks"]):
                for k in ("n", "underflow", "overflow", "hist", "count_if"):
                    self.assertEqual(bc[k], bp[k], (oc["name"], k))
                for k in ("sum", "sumsq"):
                    self.assertAlmostEqual(bc[k], bp[k], delta=1e-12 * max(1.0, abs(bp[k])))
        self.assertEqual(summ["run"]["tail_sources_simulated"], [])

    def test_values_equal_python_from_the_csv(self):
        """Adapter 0.5.0 (C2.1): an observable declared with values keeps each block's values in event order, as the
        Python builder does from the same CSV; the empirical quantile estimator then reads them."""
        d = self.toy(100.0)
        spec = reco()
        spec["output"]["observables"][0]["values"] = True
        rows, summ = self.run_reco(d, spec)
        py = S.build(rows, spec["output"]["observables"], 250, 16, 0, {"seeding": "per-event"},
                     {"name": "python", "version": "-"})
        oc, op = summ["observables"][0], py["observables"][0]
        self.assertEqual([b["values"] for b in oc["blocks"]], [b["values"] for b in op["blocks"]])
        self.assertEqual(oc["quantile_method"], "hyndman-fan-7")
        self.assertNotIn("values", summ["observables"][1]["blocks"][0])
        q = E.estimate(summ, {"name": "res", "estimator": "quantile", "quantile": 0.84})
        self.assertEqual(q["quantile_method"], "hyndman-fan-7")

    def width_and_flips(self, d, spec, replicas=1):
        widths, flips, sel = [], 0, 0
        for m in range(replicas):
            rows, summ = self.run_reco(d, spec, m, tag=f"r{m}")
            ok = [r for r in rows if r["selected"] == 1]
            res = sorted(r["inv_rig_res"] for r in ok)
            widths.append((res[int(0.8413 * len(res))] - res[int(0.1587 * len(res))]) / 2)
            flips += sum(r["charge_flip"] for r in ok)
            sel += len(ok)
        return widths, flips / sel, summ

    def test_digitization_and_pattern_recognition_widen_and_raise_confusion(self):
        d = self.toy(500.0, secondaries=True)
        base_w, base_f, _ = self.width_and_flips(d, reco())
        digi = reco({"tail_sources": {"noise-digitization": {"on": True, "pitch_y_um": 80, "pitch_z_um": 200,
                                                             "sharing_um": 2, "threshold": 0.3, "efficiency": 1.0}}})
        w, f, summ = self.width_and_flips(d, digi)
        self.assertGreater(w[0], 1.3 * base_w[0])
        self.assertGreater(f, base_f)
        self.assertEqual(summ["run"]["tail_sources_simulated"], ["noise-digitization"])
        pr = reco({"tail_sources": {"pattern-recognition": {"on": True, "window_mm": 1.0, "chi2_per_ndof_cut": 1e6,
                                                             "min_hits": 4}}})
        w, f, summ = self.width_and_flips(d, pr)
        self.assertGreater(w[0], 1.05 * base_w[0])
        self.assertGreater(f, base_f)
        self.assertEqual(summ["run"]["tail_sources_simulated"], ["pattern-recognition"])

    def test_replica_tail_sources_widen_and_spread(self):
        """Within one replica a misalignment or field error is fixed: for tracks of one rigidity it mainly shifts the
        mean (B2.2), so the broadening comes from between replicas: the resolution combined over the replicas
        (replica-mean width (+) spread of the replica means) widens and the replica spread is > 0; the rotation residual
        of alignment also widens each replica (tracks at different z). A position-dependent field error with the
        common mean removed acts only at second order on J15's symmetric layout (the first-order change of the
        measured curvature cancels between the halves), so for it only the replica spread is asserted."""
        d = self.toy(500.0, n=4000)
        base_w, _, _ = self.width_and_flips(d, reco())
        for name, params in (("alignment", {"residual_sigma_y_um": 8.0, "residual_sigma_z_um": 10.0,
                                            "residual_sigma_rot_urad": 200.0, "method": "SYNTHETIC test"}),
                             ("calibration-non-uniformity", {"sigma": 0.0, "gradient_sigma": 0.2})):
            spec = reco({"replicas": 20, "tail_sources": {name: {"on": True, **params}}})
            widths, _, summ = self.width_and_flips(d, spec, replicas=20)
            means = []
            for m in range(20):
                rows = [ln for ln in (d / f"r{m}.csv").read_text().splitlines()[2:]]
                means.append(statistics.fmean(float(ln.split(",")[RS.RESULT_COLUMNS.index("inv_rig_res")])
                                              for ln in rows))
            with self.subTest(source=name):
                self.assertGreater(statistics.stdev(means), 0)
                if name == "alignment":
                    self.assertGreater(statistics.fmean(widths), base_w[0])
                    self.assertGreater(math.hypot(statistics.fmean(widths), statistics.stdev(means)), base_w[0])
                self.assertEqual(summ["run"]["tail_sources_simulated"], [name])
        self.assertTrue(RS.check(reco({"tail_sources": {"alignment": {"on": True}}}), J15))  # 20 replicas needed

    def test_a_tail_source_that_does_nothing_is_refused(self):
        """A stage switched on with zero widths would be listed as simulated and make an F4 value an estimate."""
        cases = {"alignment": ({"on": True, "method": "m"}, "every width zero"),
                 "calibration-non-uniformity": ({"on": True, "sigma": 0.01}, "two field regions"),
                 "noise-digitization": ({"on": True, "efficiency": 0.99}, "pitch_y_um"),
                 "pattern-recognition": ({"on": True}, "window_mm")}
        # a strip pitch whose pitch / sqrt 12 is finer than the declared 10 um would improve the measurement (J15)
        problems = RS.check(reco({"tail_sources": {"noise-digitization": {"on": True, "pitch_y_um": 36,
                                                                          "pitch_z_um": 116, "sharing_um": 8}}}), J15)
        self.assertTrue(any("finer than the declared" in p for p in problems), problems)
        for name, (params, why) in cases.items():
            with self.subTest(source=name):
                problems = RS.check(reco({"replicas": 20, "tail_sources": {name: params}}), J15)
                self.assertTrue(any(why in p for p in problems), problems)
        ok = reco({"replicas": 20, "tail_sources": {"calibration-non-uniformity": {"on": True, "gradient_sigma": 0.01}}})
        self.assertEqual(RS.check(ok, J15), [])

    def test_global_field_scale_moves_the_mean_only(self):
        d = self.toy(50.0)
        rows0, _ = self.run_reco(d, reco(), tag="g0")
        rows1, s1 = self.run_reco(d, reco({"field_scale_global": 0.01}), tag="g1")
        r0 = [r["inv_rig_res"] for r in rows0]
        r1 = [r["inv_rig_res"] for r in rows1]
        self.assertAlmostEqual(statistics.fmean(r1) - statistics.fmean(r0), -0.01 / 1.01, delta=2e-4)
        self.assertAlmostEqual(statistics.stdev(r1) / statistics.stdev(r0), 1 / 1.01, delta=0.002)
        self.assertEqual([r["charge_reco"] for r in rows0], [r["charge_reco"] for r in rows1])
        self.assertEqual(s1["run"]["tail_sources_simulated"], [])

    def test_curvature_offset_follows_the_gaussian_core(self):
        d = self.toy(1000.0, n=4000)
        rows0, _ = self.run_reco(d, reco(), tag="o0")
        sig = statistics.stdev(r["inv_rig_res"] for r in rows0) / 1000.0  # sigma of rho (1/GV)
        offset = -0.0005  # 1/GV, toward the other charge
        rows1, _ = self.run_reco(d, reco({"curvature_offset_per_GV": offset}), tag="o1")
        flips = statistics.fmean(r["charge_flip"] for r in rows1)
        want = statistics.NormalDist().cdf(-(1 / 1000.0 + offset) / sig)
        self.assertLess(abs(flips - want), 3 * math.sqrt(want * (1 - want) / len(rows1)) + 0.01, (flips, want))


class Estimators(unittest.TestCase):
    """B2.3: the gaussian-core estimator and the F4 result helpers (no compiler needed)."""

    def summary(self, values, width=0.001, blocks=16):
        obs = [{"name": "res", "source_column": "x", "bins": {"lo": -1, "hi": 1, "width": width},
                "estimator": "gaussian-core"}]
        rows = [{"event": i, "x": v} for i, v in enumerate(values)]
        return S.build(rows, obs, len(values) // blocks, blocks, 0, {"seeding": "per-event"},
                       {"name": "t", "version": "-"}), obs[0]

    def test_core_width_of_a_gaussian_with_tails(self):
        import random
        rng = random.Random(3)
        vals = [rng.gauss(0, 0.02) if rng.random() > 0.05 else rng.gauss(0, 0.2) for _ in range(32000)]
        doc, decl = self.summary(vals)
        r = E.estimate(doc, decl)
        self.assertEqual(r["status"], "ok")
        self.assertAlmostEqual(r["value"], 0.02, delta=0.02 * 0.05)
        sd = statistics.stdev(vals)
        self.assertGreater(sd, 1.5 * r["value"])  # the plain SD is pulled up by the tails, the core is not

    def test_too_coarse_bins_are_incomplete(self):
        import random
        rng = random.Random(4)
        doc, decl = self.summary([rng.gauss(0, 0.002) for _ in range(1600)], width=0.01)
        self.assertEqual(E.estimate(doc, decl)["status"], "incomplete")

    def test_fom_result_counting_is_exact_and_combines_the_replica_spread(self):
        import random
        sums = []
        for m in range(3):
            rng = random.Random(m)
            rows = [{"event": i, "selected": 1.0, "charge_flip": 1.0 if rng.random() < 0.01 else 0.0}
                    for i in range(1600)]
            obs = [{"name": "flip", "source_column": "charge_flip", "bins": {"lo": 0, "hi": 2, "width": 1},
                    "thresholds": [0.5], "estimator": "proportion", "selection": [RS.SELECTED]}]
            sums.append(S.build(rows, obs, 100, 16, 0, {"seeding": "per-event"}, {"name": "t", "version": "-"}))
        r = RS.fom_result("charge-confusion-rate", sums, obs[0], {"rigidity_GV": 1000.0})
        self.assertEqual(r["uncertainty"]["distribution"], "exact")
        self.assertEqual(r["uncertainty"]["coverage"], 0.90)
        self.assertGreater(r["replica_spread"], 0)
        self.assertGreater(r["uncertainty"]["plus"], r["uncertainty_components"]["statistical"]["plus"])
        self.assertNotIn("statistical_uncertainty", r)
        self.assertLessEqual(r["uncertainty"]["minus"], r["value"])  # a proportion stops at zero
        with self.assertRaises(Exception):
            RS.fom_result("momentum-resolution-core", sums, obs[0], {})  # needs the gaussian-core estimator
        lo, hi = r["counts"]["interval"]
        p0 = r["counts"]["k"] / r["counts"]["n"]
        self.assertAlmostEqual(r["uncertainty_components"]["statistical"]["plus"], hi - p0)  # centred on the mean
        with self.assertRaises(Exception):  # the observable must select the fitted tracks
            RS.fom_result("charge-confusion-rate", sums, dict(obs[0], selection=[]), {})
        with self.assertRaises(Exception):  # and read the figure of merit's column
            RS.fom_result("charge-confusion-rate", sums, dict(obs[0], source_column="selected"), {})

    def test_the_denominator_is_the_simulated_source(self):
        ek = (math.hypot(1.0, MP) - MP) * 1000
        self.assertEqual(RS.check_denominator({"rigidity_GV": 1.0, "species": "proton"},
                                              {"particle": "proton", "energy_MeV": ek}), [])
        bad = RS.check_denominator({"rigidity_GV": 300.0, "species": "e-"}, {"particle": "proton", "energy_MeV": ek})
        self.assertEqual(len(bad), 2, bad)


FAKE_SIMROOT_DUMP = r'''#!/usr/bin/env python3
import hashlib, json, pathlib, sys
cmd, path = sys.argv[1], sys.argv[2]
if cmd == "dump":  # the toy crossings next to the event file stand in for the ntuple
    sys.stdout.write((pathlib.Path(path).parent / "toy_crossings.csv").read_text())
    sys.exit(0)
data = open(path, "rb").read()
print(json.dumps({"status": "ok", "content_sha256": hashlib.sha256(b"content:" + data).hexdigest(), "files": 1,
                  "level": "crossings", "ntuples": {"events": {"rows": 3, "sha256": "0" * 64}}}))
'''


@unittest.skipUnless(CXX or REQUIRED, "no C++ compiler: the simreco tests are optional here (required in CI job simreco)")
class RecoTablePlumbing(unittest.TestCase):
    """B2.4-B2.6: geant4_run.py reco and table around the real simreco, on a fake element_sim run (the B1 test's fake
    program) whose event file a fake simroot dumps as toy crossings: the reco record (input hashes, replicas, tail
    sources, the completed summary), a changed event file refused, the simulated dataset-record and its processing
    chain (dependencies.py, B2.5), and the f4-results/1 file with the geometry and a model envelope."""

    @classmethod
    def setUpClass(cls):
        Simreco.setUpClass.__func__(cls)
        cls.simreco = cls.exe  # setUp sets self.exe to the fake element_sim

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        import tests.adapters.test_geant4_element as B1
        B1.RunPlumbing.setUp(self)
        self.cleanup = B1.RunPlumbing.tearDown
        simroot = self.d / "bin" / "simroot"
        simroot.write_text(f"#!{sys.executable}\n" + FAKE_SIMROOT_DUMP.split("\n", 1)[1])
        spec = B1.j15()
        spec["run"]["events"] = 3
        (self.d / "e1.spec.json").write_text(json.dumps(spec))
        code, out = B1.run(ASSETS / "geant4_run.py", "run", "--spec", self.d / "e1.spec.json", "--exe", self.exe,
                           "--build-record", self.build, "--work", self.d / "work", "--run-id", "e1", "--record",
                           self.d / "runs" / "e1.json", "--created", "2026-10-24")
        self.assertEqual(code, 0, out)
        run_dir = self.d / "work" / "e1"
        write_toy(run_dir, 1.0, 400)
        (run_dir / "crossings.csv").rename(run_dir / "toy_crossings.csv")
        self.run_tool = B1.run

    def tearDown(self):
        self.cleanup(self)

    def reco(self, spec, rid="r1", *extra):
        sp = self.d / f"{rid}.reco.json"
        sp.write_text(json.dumps(spec))
        return self.run_tool(ASSETS / "geant4_run.py", "reco", "--run-record", self.d / "runs" / "e1.json",
                             "--reco-spec", sp, "--simreco", self.simreco, "--work-out", self.d / "work", "--reco-id", rid,
                             "--record", self.d / "runs" / f"{rid}.json", "--project-root", self.d,
                             "--created", "2026-10-24", *extra)

    def spec(self, **extra):
        s = reco(extra)
        s["output"]["blocks"] = {"blocks": 16, "block_size": 25}
        s["output"]["observables"][0]["bins"] = {"lo": -0.05, "hi": 0.05, "width": 0.0001}  # toy: no scattering
        return s

    def test_reco_record_and_summary(self):
        code, out = self.reco(self.spec())
        self.assertEqual(code, 0, out)
        rec = json.loads((self.d / "runs" / "r1.json").read_text())
        self.assertTrue(validate_artifact(rec).ok, validate_artifact(rec).as_dict())
        rx = rec["extension"]["reconstruction"]
        self.assertEqual((rx["replicas"], rx["tail_sources_simulated"]), (1, []))
        self.assertEqual(rx["reco_spec_sha256"], hashlib.sha256((self.d / "r1.reco.json").read_bytes()).hexdigest())
        self.assertEqual(rx["run_record"]["sha256"], hashlib.sha256((self.d / "runs" / "e1.json").read_bytes()).hexdigest())
        self.assertFalse(rx["dumped"]["kept"])
        self.assertEqual(rec["inputs"][0]["ref"], "runs/e1.json")
        summ = json.loads((self.d / "work" / "r1" / "summary_r000.json").read_text())
        self.assertEqual(summ["run"]["completed_by"]["name"], "geant4_run.py reco")
        self.assertEqual(summ["run"]["simulation_run_record"]["artifact_id"], rec["inputs"][0]["artifact_id"])
        self.assertEqual(summ["run"]["tail_sources_simulated"], [])
        self.assertFalse((self.d / "work" / "r1" / "crossings.csv").exists())

    def test_replicas_and_a_changed_event_file(self):
        code, out = self.reco(self.spec(replicas=20, tail_sources={"alignment": {
            "on": True, "residual_sigma_y_um": 5, "residual_sigma_z_um": 10, "residual_sigma_rot_urad": 20,
            "method": "SYNTHETIC"}}))
        self.assertEqual(code, 0, out)
        self.assertEqual((out["replicas"], out["tail_sources_simulated"]), (20, ["alignment"]))
        self.assertTrue((self.d / "work" / "r1" / "summary_r019.json").is_file())
        with open(self.d / "work" / "e1" / "events.root", "ab") as fh:
            fh.write(b"changed")
        code, out = self.reco(self.spec(), "r2")
        self.assertEqual(code, 2, out)
        self.assertIn("content_sha256", out["error"])

    def test_table_dataset_chain_and_f4_results(self):
        self.assertEqual(self.reco(self.spec())[0], 0)
        self.assertEqual(self.reco(self.spec(), "r-var")[0], 0)
        geom = self.d / "g.geometry.json"
        geom.write_text(json.dumps({"schema": "design-geometry/1", "fields": {}}))
        code, out = self.run_tool(ASSETS / "geant4_run.py", "table", "--reco-record", self.d / "runs" / "r1.json",
                                  "--figure-of-merit", "momentum-resolution-core", "--observable", "res",
                                  "--denominator", "rigidity_GV=1", "--denominator", "species=proton",
                                  "--out", self.d / "tables" / "t.json", "--id", "t1", "--f4-results",
                                  self.d / "f4.json", "--geometry", geom, "--variation",
                                  f"other={self.d / 'runs' / 'r-var.json'}", "--project-root", self.d,
                                  "--created", "2026-10-24")
        self.assertEqual(code, 0, out)
        table = json.loads((self.d / "tables" / "t.json").read_text())
        rep = validate_artifact(table)
        self.assertTrue(rep.ok, rep.as_dict())
        from contracts.dependencies import validate_dependencies
        deps = validate_dependencies(self.d / "tables" / "t.json", self.d)
        self.assertNotIn("dataset.simulated_source", {f["code"] for f in deps["findings"]}, deps["findings"])
        f4 = json.loads((self.d / "f4.json").read_text())
        r = f4["results"]["momentum-resolution-core"]
        self.assertEqual(f4["geometry"]["sha256"], hashlib.sha256(geom.read_bytes()).hexdigest())
        self.assertEqual(r["uncertainty"]["coverage"], 0.9)
        self.assertEqual(len(r["model_envelope"]), 2)
        self.assertEqual(f4["tail_sources_simulated"], [])
        code, out = self.run_tool(ASSETS / "geant4_run.py", "table", "--reco-record", self.d / "runs" / "r1.json",
                                  "--figure-of-merit", "charge-confusion-rate", "--observable", "res",
                                  "--out", self.d / "tables" / "bad.json", "--id", "bad")
        self.assertEqual(code, 2, out)  # charge confusion needs a proportion observable, not the core


if __name__ == "__main__":
    unittest.main()
