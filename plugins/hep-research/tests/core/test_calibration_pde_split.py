"""core/calibration/pde_split (simulator calibration phase 3, WP-E): the PDE split of Part B section 6.7 (decided by the
author 2026-11-10): routes 2_1, 3 and 1, the route-3 replicas and their energy grid, the split check with its nested pair
of mapping runs, the contract rules (calib_contract.py) and the plan rules (calib_design.py) of sections 14 and 15.3.19,
the candidate methods (section 11.4 Table 2) and the PDE(E) part of the model identity (section 5.1).

Synthetic: per-photon optics in calibration_pde_fixtures (Geant4 transport NOT run; the section 15.2 items that need it are
listed in Geant4Items and skipped). Each negative test has a positive control that the same check passes."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_g4sim_fixtures as G  # noqa: E402
import calibration_pde_fixtures as P  # noqa: E402
from contracts.geometry import field_types  # noqa: E402
from core.calibration import chain, design_g4sim as DG, model_identity as mi, pde_split as S  # noqa: E402
from core.canonical import canonical_sha256  # noqa: E402
from core.simulation import digitize, efficiency_map as em, rng  # noqa: E402

E2 = ["1.5", "4.0"]


def optical_spec(reflectivity="0", efficiency="0.25") -> dict:
    """A detector-spec/1 with one sensor optical surface (as in tests/core/test_geometry_optics.py)."""
    return {"schema": "detector-spec/1", "params": {},
            "materials": {"glass_optical": {"base": "G4_GLASS_PLATE", "optical": {
                "rindex": {"energy_eV": E2, "value": ["1.5", "1.52"]},
                "absorption_length_mm": {"energy_eV": E2, "value": ["1000", "1000"]}}},
                "AIR_optical": {"base": "G4_AIR", "optical": {"rindex": {"energy_eV": E2, "value": ["1.0003", "1.0003"]}}}},
            "templates": {"radiator": {"solid": {"box": {"size_mm": ["100", "100", "10"]}}, "material": "glass_optical",
                                       "tags": ["optical"]},
                          "sensor": {"solid": {"box": {"size_mm": ["100", "100", "1"]}}, "material": "G4_Si",
                                     "tags": ["optical"]},
                          "box": {"solid": {"box": {"size_mm": ["100", "100", "31"]}}, "material": "AIR_optical",
                                  "tags": ["optical"], "children": [{"placement": {"stack": {
                                      "axis": "z", "from": "-z", "sequence": [
                                          "radiator", {"spacer_mm": "10", "material": "AIR_optical"}, "sensor",
                                          {"spacer_mm": "10"}]}}}]}},
            "world": {"material": "G4_AIR", "size_mm": ["1000", "1000", "1000"], "children": [
                {"template": "box", "placement": {"single": {"centre_mm": ["0", "0", "0"]}}}]},
            "physics_requirements": [{"need": "optical_scope", "select": {"tags": ["optical"]}}],
            "optical_surfaces": {"photocathode": {
                "skin": "sensor", "model": "unified", "finish": "polished", "type": "dielectric_metal",
                "reflectivity": {"energy_eV": E2, "value": [reflectivity, reflectivity]},
                "efficiency": {"energy_eV": E2, "value": [efficiency, efficiency]}}}}


def declaration(**kw) -> dict:
    d = {"parameters": ["pde"], "model": "scale", "angle_dependent": False, "ties": [],
         "sensor_surfaces": ["photocathode"], "map_mode": "fixed"}
    d.update(kw)
    return d


def contract(role="theta", **kw) -> dict:
    c = G.contract()
    c["parameters"].append(G.parameter("pde", role, "pde", "evaluator", "/pde", physical_bounds=[0.0, 1.0],
                                       sampling_bounds=[0.2, 0.6]))
    c["pde_split"] = declaration(**kw)
    return c


def codes(findings):
    return {f["code"] for f in findings}


class Runs:
    """The synthetic mapping runs shared by the tests (built once)."""
    _cache: dict = {}

    @classmethod
    def get(cls, key, photons=20000, **kw):
        if key not in cls._cache:
            cls._cache[key] = P.run(photons, **kw)
        return cls._cache[key]

    @classmethod
    def one(cls):
        ph, pr, emitted, detected = cls.get("one")
        m = P.build_map(emitted, detected)
        return m, S.binned(m, S.read_photons(ph), S.read_primaries(pr), P.CENTRE), ph, pr


def job_at(m, efficiencies=None, run_seed=31, timing=False):
    pipe = G.pipeline()
    if timing:
        pipe["stages"][0]["parameters"]["decay_ns"] = {"value": 20.0}
    j = DG.job_from_documents(pipe, m, "ecal", range(4), run_seed)
    if efficiencies is not None:
        j["efficiencies"] = efficiencies
    return j


class Routes(unittest.TestCase):
    def test_pde_interpolated_as_geant4(self):
        t = {"energy_eV": [2.0, 3.0], "value": [0.2, 0.4]}
        self.assertTrue(np.allclose(S.pde_at(t, [1.0, 2.0, 2.5, 3.0, 9.0]), [0.2, 0.2, 0.3, 0.4, 0.4]))
        self.assertAlmostEqual(S.cell_mean(t, 2.0, 3.0), 0.3)
        self.assertAlmostEqual(S.cell_mean(t, 1.0, 2.0), 0.2)          # the edge value outside the table
        with self.assertRaises(S.SplitError):
            S.pde_at({"energy_eV": [3.0, 2.0], "value": [0.2, 0.4]}, [2.5])

    def test_route21_and_route1_agree_in_law_and_route1_is_nested(self):
        """Route 2_1 (job efficiencies p eps) against route 1 (per-photon thinning by p at the efficiency-1 map): the
        same photoelectron law; route 1's kept set is nested in p (control: a thinning drawn from another stream at
        the larger p is not, so the nesting test detects a non-nested path)."""
        m, _, _, _ = Runs.one()
        rows = P.bins_rows(300)
        j1 = job_at(m)
        p = 0.4
        r21 = digitize.digitize(S.route21_job(j1, p), rows)[0]
        r1 = S.digitize_route1(j1, rows, p, 1)[0]
        for c in (0, 1):
            a = np.array([r[3] for r in r21 if r[2] == c], float)
            b = np.array([r[3] for r in r1 if r[2] == c], float)
            se = np.sqrt(a.var() / len(a) + b.var() / len(b))
            self.assertLess(abs(a.mean() - b.mean()), 4 * se, c)
            self.assertLess(abs(np.log(a.var() / b.var())), 4 * np.sqrt(2 / len(a)) * 1.5, c)
        lo, hi = S.digitize_route1(j1, rows, 0.3, 1)[0], S.digitize_route1(j1, rows, 0.5, 1)[0]
        self.assertTrue(all(x[3] <= y[3] for x, y in zip(lo, hi)))
        other = S.digitize_route1(j1, rows, 0.5, 2)[0]                  # control: a thinning from another stream
        self.assertFalse(all(x[3] <= y[3] for x, y in zip(lo, other)))

    def test_route1_keeps_photon_times_and_never_scales_charge(self):
        m, _, _, _ = Runs.one()
        j = job_at(m, timing=True)
        rows = P.bins_rows(20)
        ch, times = S.digitize_route1(j, rows, 0.5, 1)
        self.assertEqual(sum(r[3] for r in ch), len(times))           # one time per kept photoelectron
        full = digitize.digitize(j, rows)[1]
        self.assertTrue(set(times) <= set(full))                        # the kept photons' times are a subset
        self.assertEqual(S.route1_findings({"stage": "scintillation", "component": 1}), [])
        self.assertEqual(codes(S.route1_findings({"stage": "scintillation", "component": 1,
                                                  "position": "after-dark-counts"})), {"pde_split.route1_position"})
        self.assertEqual(codes(S.route1_findings({"stage": "scintillation", "component": 1, "applies_to": "charge"})),
                         {"pde_split.route1_scale"})
        self.assertEqual(codes(S.route1_findings({"stage": "scintillation", "component": 1,
                                                  "stream": "efficiency_map/1"})), {"pde_split.route1_stream"})

    def test_route21_law_against_a_mapping_run_at_p(self):
        """eps(p) = p eps(1) in law: the map of a mapping run at efficiency p against p times the efficiency-1 map."""
        m1, _, _, _ = Runs.one()
        _, _, emitted, detected = Runs.get("p04", efficiency=0.4)
        mp = P.build_map(emitted, detected)
        z2 = []
        for b in range(4):
            n = m1["form"]["bins"][b]["emitted"]
            for c in range(2):
                k1 = m1["form"]["bins"][b]["detected"][c]
                kp = mp["form"]["bins"][b]["detected"][c]
                z2.append((kp - 0.4 * k1) ** 2 / (0.4 * 0.6 * k1))
            self.assertEqual(n, mp["form"]["bins"][b]["emitted"])
        from scipy import stats
        self.assertGreater(stats.chi2.sf(sum(z2), len(z2)), 0.01)

    def test_linear_observable_u_scales_with_p(self):
        """For an observable linear in eps, mu(p) = mu_0 + p (mu(1) - mu_0) and U(p) = p U(1) exactly."""
        m, _, _, _ = Runs.one()
        reps = [S.map_efficiencies(m, r) for r in range(1, 21)]

        def mu(eff, p):                                   # expected photoelectrons: linear in eps
            return 5.0 + 100.0 * sum(sum(v) for v in S.route21_efficiencies(eff, p).values())
        for p in (0.3, 0.7):
            u1 = np.array([mu(e, 1.0) for e in reps])
            up = np.array([mu(e, p) for e in reps])
            self.assertTrue(np.allclose(up - up.mean(), p * (u1 - u1.mean())))

    def test_route3_efficiencies_transit_and_job(self):
        m, run, _, _ = Runs.one()
        t = P.pde_table()
        r3 = S.route3(m, run, t)
        b0 = [d for d in run["detections"] if d[0] == 0 and d[1] == "sipm/0"]
        self.assertAlmostEqual(r3["efficiencies"]["0"][0], float(np.sum(S.pde_at(t, [d[3] for d in b0])))
                               / m["form"]["bins"][0]["emitted"])
        for counts in r3["transit"]["counts"].values():               # scaled to 10^6, then rounded per cell
            self.assertLessEqual(abs(sum(counts) - S.TRANSIT_TOTAL), len(counts) / 2)
        self.assertLessEqual(r3["rounding"], 5e-7)
        job = S.route3_job(job_at(m, timing=True), r3)
        digitize.check_job(job)                                         # integer transit counts: g4sim accepts it
        self.assertEqual(S.integerise([0.0, 0.0]), ([0, 0], 0.0))

    def test_route3_against_a_mapping_run_at_the_pde_table(self):
        """Route 3 against a mapping run at PDE(E): the split check's chi-square of the efficiencies and transit means."""
        m, run, ph1, pr = Runs.one()
        php, _, _, _ = Runs.get("table", efficiency=P.pde_table())
        rp = S.binned(m, S.read_photons(php), S.read_primaries(pr), P.CENTRE)
        r = S.split_check(m, run, rp, {"table": P.pde_table()}, (S.read_photons(ph1), S.read_photons(php)))
        self.assertEqual(r["status"], "passed", r["findings"])

    def test_photons_csv_equals_the_map(self):
        m, run, ph, pr = Runs.one()
        self.assertEqual(S.photons_findings(m, run), [])
        lines = ph.splitlines()
        cut = S.binned(m, S.read_photons("\n".join(lines[:1] + lines[2:])), S.read_primaries(pr), P.CENTRE)
        self.assertIn("pde_split.photons_counts", codes(S.photons_findings(m, cut)))
        self.assertEqual(S.photons_sha256(b"x"), "2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881")


class Replicas(unittest.TestCase):
    """Route-3 replicas: their covariance against the analytic Dirichlet and the multinomial covariance over several
    grid sizes (small sizes; section 8.7 row 2009 runs the calibration on the ZDC fixture with optics)."""

    def setUp(self):
        ph, pr, emitted, detected = Runs.get("small", photons=8000, seed=9)
        self.m = P.build_map(emitted, detected)
        self.run = S.binned(self.m, S.read_photons(ph), S.read_primaries(pr), P.CENTRE)
        self.t = P.pde_table()
        self.msha, self.psha = em.map_sha256(self.m), S.photons_sha256(ph.encode())

    def test_covariance_against_analytic_over_grid_sizes(self):
        R = 300
        for grid in ([2.0, 3.5], [2.0, 2.5, 3.0, 3.5], list(np.linspace(2.0, 3.5, 7))):
            cat = S.route3_categories(self.m, self.run, self.t, grid)
            draws = [S.route3_replica(cat, S.replica_key(self.msha, self.psha, 1, r)) for r in range(1, R + 1)]
            for b in (0, 3):
                x = np.array([d[str(b)] for d in draws])
                emp = np.cov(x.T)
                ana = S.dirichlet_covariance(cat, b)
                mult = S.multinomial_covariance(cat, b)
                for c in (0, 1):
                    self.assertLess(abs(emp[c, c] / ana[c, c] - 1), 0.35, (grid, b, c))
                    self.assertLess(abs(ana[c, c] / mult[c, c] - 1), 0.08, (grid, b, c))
                self.assertLess(abs(np.corrcoef(x.T)[0, 1] - ana[0, 1] / np.sqrt(ana[0, 0] * ana[1, 1])), 0.25)
                centre = S.route3(self.m, self.run, self.t)["efficiencies"][str(b)]
                self.assertTrue(np.allclose(x.mean(0), centre, rtol=0.1))

    def test_replica_keys_and_registration(self):
        cat = S.route3_categories(self.m, self.run, self.t)
        k1 = S.replica_key(self.msha, self.psha, 1, 1)
        self.assertEqual(S.route3_replica(cat, k1), S.route3_replica(cat, k1))
        self.assertNotEqual(k1, S.replica_key(self.msha, self.psha, 1, 2))
        self.assertEqual(k1, rng._key("calib-map-pde/1", self.msha, self.psha, 1, 1))
        reg = S.registration_key(self.msha, self.psha, 1, cat, 100, S.default_grid(self.t))
        self.assertEqual((reg["key"], reg["R"], len(reg["coordinates"])), ("calib-map-pde/1", 100, 6))
        self.assertTrue(np.allclose(reg["centre"]["1"], S.route3(self.m, self.run, self.t)["efficiencies"]["1"]))

    def test_grid_pseudo_mass_and_variance(self):
        ok = S.grid_check(self.m, self.run, [self.t])
        self.assertEqual(ok["status"], "passed", ok["findings"])
        fine = S.grid_check(self.m, self.run, [self.t], list(np.linspace(2.0, 3.5, 60)))
        self.assertIn("pde_split.grid_pseudo_mass", codes(fine["findings"]))
        steep = {"energy_eV": [2.0, 2.75, 2.76, 3.5], "value": [0.02, 0.02, 0.95, 0.95]}
        coarse = S.grid_check(self.m, self.run, [steep], [2.0, 3.5])
        self.assertIn("pde_split.grid_variance", codes(coarse["findings"]))
        self.assertEqual(S.grid_check(self.m, self.run, [steep], [2.0, 2.75, 2.76, 3.5])["status"], "passed")
        self.assertIn("provisional-thresholds", ok["flags"])


class SplitCheck(unittest.TestCase):
    """The mandatory split check (section 6.7; section 15.3.19): exact split passes, a reflectance tied to the PDE is
    detected (not nested, chi-square, d theta)."""

    def pair(self, key, **kw):
        m, run, ph1, pr = Runs.one()
        php, _, _, _ = Runs.get(key, **kw)
        rp = S.binned(m, S.read_photons(php), S.read_primaries(pr), P.CENTRE)
        return m, run, rp, (S.read_photons(ph1), S.read_photons(php))

    def propagation(self, m, sigma):
        """The total efficiency as the observable, theta = p: d theta = d(sum eps)/sum eps(1)."""
        cells = len(m["form"]["bins"]) * len(m["channels"])
        total = sum(sum(em.efficiencies(m, b)) for b in range(len(m["form"]["bins"])))
        return {"J": [[1.0] * cells], "A": [[1.0 / total]], "sigma_tot_design": [sigma]}

    def test_exact_split_passes(self):
        m, r1, rp, lines = self.pair("p04", efficiency=0.4)
        r = S.split_check(m, r1, rp, {"p": 0.4}, lines, self.propagation(m, 0.4))
        self.assertEqual((r["status"], r["nesting"]["nested"]), ("passed", True), r["findings"])
        self.assertTrue(r["sizing"]["sized"])
        self.assertIn("provisional-thresholds", r["flags"])

    def test_tied_reflectance_is_detected(self):
        m, r1, rp, lines = self.pair("tied", efficiency=0.4, rho=0.25)
        r = S.split_check(m, r1, rp, {"p": 0.4}, lines, self.propagation(m, 0.4))
        self.assertEqual(r["status"], "failed")
        self.assertTrue({"pde_split.not_nested", "pde_split.chi2", "pde_split.dtheta"} <= codes(r["findings"]))
        self.assertEqual(r["remedy"], "route-0")
        self.assertIsNotNone(r["nesting"]["first_event"])
        r = S.split_check(m, r1, rp, {"p": 0.4}, None, self.propagation(m, 0.4))     # without the rows: chi2 alone
        self.assertIn("pde_split.chi2", codes(r["findings"]))

    def test_undersized_pair_fails_through_the_spread_only(self):
        m, r1, rp, lines = self.pair("p04", efficiency=0.4)
        r = S.split_check(m, r1, rp, {"p": 0.4}, lines, self.propagation(m, 0.12))
        self.assertEqual((r["status"], r["remedy"]), ("failed", "larger-pair"), r)
        self.assertFalse(r["sizing"]["sized"])
        self.assertGreater(r["sizing"]["photon_factor"], 1)

    def test_delta_mu_from_both_maps_digitized_with_one_run_seed(self):
        """delta mu automated: the nominal-PDE run and the split digitized with one run_seed (digitization and
        thinning noise in the covariance); the exact split passes, the tied reflectance fails on d theta."""
        m, r1, rp, lines = self.pair("p04", efficiency=0.4)
        rows = P.bins_rows(200)
        job = job_at(m)
        obs = [{"quantity": "photoelectrons"}]
        mu1 = np.mean([r[3] for r in digitize.digitize(job, rows)[0]]) * 2           # per-event sum, 2 channels
        prop = S.digitized_propagation(m, r1, rp, {"p": 0.4}, job, rows, obs, [[1.0 / mu1]], [0.4])
        self.assertGreater(np.array(prop["cov_delta_mu"])[0, 0], np.array(prop["digitization_cov"])[0, 0])
        r = S.split_check(m, r1, rp, {"p": 0.4}, lines, prop)
        self.assertEqual(r["status"], "passed", r["findings"])
        m, r1, rt, lines = self.pair("tied", efficiency=0.4, rho=0.25)
        prop = S.digitized_propagation(m, r1, rt, {"p": 0.4}, job, rows, obs, [[1.0 / mu1]], [0.4])
        self.assertIn("pde_split.dtheta", codes(S.split_check(m, r1, rt, {"p": 0.4}, None, prop)["findings"]))
        with self.assertRaises(S.SplitError):
            S.digitized_propagation(m, r1, rp, {"p": 0.4}, job, rows, [{"quantity": "code"}], [[1.0]], [0.4])

    def test_pair_seeding_and_interval_reuse(self):
        def ev(run_id, seed, first, **kw):
            return {"run_id": run_id, "use": "pde-split-pair", "logical_run_seed": seed, "first_event": first,
                    "events": 5000, "pair": "p", **kw}
        good = {"evaluations": [ev("one", 22, 0, efficiency_one=True), ev("nom", 22, 0)]}
        self.assertEqual(S.pair_findings(good), [])
        self.assertEqual(DG.interval_findings(good)["status"], "passed")        # the sharing is not an overlap (6.6)
        bad = {"evaluations": [ev("one", 22, 0, efficiency_one=True), ev("nom", 23, 0)]}
        self.assertEqual(codes(S.pair_findings(bad)), {"pde_split.pair_seeding"})
        bad = {"evaluations": [ev("one", 22, 0, efficiency_one=True), ev("nom", 22, 100)]}
        self.assertEqual(codes(S.pair_findings(bad)), {"pde_split.pair_seeding"})
        bad = {"evaluations": [ev("one", 22, 0), ev("nom", 22, 0)]}
        self.assertEqual(codes(S.pair_findings(bad)), {"pde_split.pair_form"})

    def test_pair_size_and_record(self):
        self.assertAlmostEqual(S.pair_size_total(0.4, 0.01), (2 + 1.959964) ** 2 * 0.6 / (0.4 * 1e-4), delta=10)
        self.assertGreater(S.pair_size_total(0.4, 0.01, d=3), S.pair_size_total(0.4, 0.01))
        m, _, _, _ = Runs.one()
        h = m["form"]["hashes"]
        rec = {"status": "passed", "geant4_version": "11.2.1", "materials_sha256": h["materials_sha256"],
               "surfaces_sha256": h["surfaces_sha256"]}
        self.assertEqual(S.record_findings(rec, "11.2.1", m), [])
        self.assertEqual(codes(S.record_findings(rec, "11.3.0", m)), {"pde_split.check_stale"})
        self.assertEqual(codes(S.record_findings(None, "11.2.1", m)), {"pde_split.check_missing"})


class ContractRules(unittest.TestCase):
    """Section 6.7 "Rejected" (calib_contract.py, contract error) and section 15.3.19."""

    def test_valid_declaration(self):
        self.assertEqual(S.contract_findings(contract()), [])
        from core.calibration import contract as cc
        self.assertFalse({f["code"] for f in cc.check(contract())["findings"]} & {
            "pde_split.tied_property", "pde_split.undeclared"})

    def test_rejections(self):
        c = contract()
        c["parameters"][-1]["bindings"].append({"document": "detector-spec",
                                                "pointer": "/optical_surfaces/photocathode/reflectivity/value/0"})
        self.assertIn("pde_split.tied_property", codes(S.contract_findings(c)))
        self.assertIn("pde_split.tied_property", codes(S.contract_findings(contract(ties=["reflectivity = 1 - PDE"]))))
        self.assertIn("pde_split.angle_dependent", codes(S.contract_findings(contract(angle_dependent=True))))
        t = contract(model="table", table=P.pde_table(), applied_as="scale")
        self.assertIn("pde_split.table_as_scale", codes(S.contract_findings(t)))
        self.assertEqual(S.contract_findings(contract(model="table", table=P.pde_table())), [])     # control
        c = contract()
        del c["pde_split"]
        self.assertIn("pde_split.undeclared", codes(S.contract_findings(c)))
        from core.calibration import contract as cc
        self.assertIn("pde_split.undeclared", {f["code"] for f in cc.check(c)["findings"]})

    def test_efficiency_one_surfaces(self):
        text = json.dumps(optical_spec()).encode()
        prod, one = S.mapping_surfaces(text, field_types(), ["photocathode"])
        good = P.build_map(*Runs.get("one")[2:], surfaces_sha256=canonical_sha256(one))
        self.assertEqual(S.surfaces_findings(good, prod, ["photocathode"], one), [])
        stale = P.build_map(*Runs.get("one")[2:], surfaces_sha256=canonical_sha256(prod))   # map built at the PDE
        self.assertEqual(codes(S.surfaces_findings(stale, prod, ["photocathode"], one)), {"pde_split.surfaces_hash"})
        self.assertIn("pde_split.sensor_not_one", codes(S.surfaces_findings(good, prod, ["photocathode"], prod)))
        _, other = S.mapping_surfaces(json.dumps(optical_spec(reflectivity="0.1")).encode(), field_types(),
                                      ["photocathode"])
        self.assertIn("pde_split.surfaces_differ", codes(S.surfaces_findings(good, prod, ["photocathode"], other)))
        c = contract()
        self.assertEqual(S.document_findings(c, text, field_types(), good), [])
        self.assertEqual(codes(S.document_findings(c, text, field_types(), stale)), {"pde_split.surfaces_hash"})

    def test_efficiency_test_surfaces(self):
        """A PDE(E) that is 0 at an emitted energy on a surface model with the EFFICIENCY > 0 test (synthetic surface
        declaration): rejected; the same PDE(E) on dielectric_metal, or a PDE(E) > 0, passes."""
        zero = {"energy_eV": [2.0, 2.5, 3.5], "value": [0.0, 0.3, 0.4]}
        davis = {"photocathode": {"type": "dielectric_LUTDAVIS", "model": "DAVIS"}}
        metal = {"photocathode": {"type": "dielectric_metal", "model": "unified"}}
        d = declaration(model="table", table=zero)
        self.assertEqual(codes(S.efficiency_test_findings(d, davis, 2.0, 3.5)), {"pde_split.efficiency_zero"})
        self.assertEqual(S.efficiency_test_findings(d, metal, 2.0, 3.5), [])
        self.assertEqual(S.efficiency_test_findings(declaration(model="table", table=P.pde_table()), davis, 2.0, 3.5),
                         [])
        self.assertEqual(S.efficiency_test_findings(d, davis, 2.6, 3.5), [])        # 0 outside the emitted range
        # design: over the prior range, p = 0 included (remedy plan)
        self.assertEqual(codes(S.efficiency_test_findings(declaration(), davis, 2.0, 3.5, [0.0, 1.0], design=True)),
                         {"pde_split.efficiency_zero"})
        self.assertEqual(S.efficiency_test_findings(declaration(), davis, 2.0, 3.5, [0.1, 1.0], design=True), [])


class DesignRules(unittest.TestCase):
    """calib_design.py (remedy level plan): routes, keys, route 3 without photons."""

    def test_route1_where_p_is_theta_and_not_linear(self):
        c = contract()
        bad = {"readouts": {"ecal": {"route": "2_1", "observables": {"charge_mean": True, "pe_width": False}}}}
        self.assertEqual(codes(S.route_findings(c, bad)), {"pde_split.route_nonlinear"})
        good = {"readouts": {"ecal": {"route": "1", "observables": {"charge_mean": True, "pe_width": False}}}}
        self.assertEqual(S.route_findings(c, good), [])
        self.assertEqual(S.route_findings(contract(role="psi"), bad), [])           # p not theta: 2_1 allowed
        lin = {"readouts": {"ecal": {"route": "2_1", "observables": {"charge_mean": True}}}}
        self.assertEqual(S.route_findings(c, lin), [])
        t = contract(model="table", table=P.pde_table())
        self.assertEqual(codes(S.route_findings(t, {"readouts": {"ecal": {"route": "3"}}})),
                         {"pde_split.route3_photons"})
        self.assertEqual(S.route_findings(t, {"readouts": {"ecal": {"route": "3"}}, "photons": "one"}), [])
        self.assertEqual(codes(S.route_findings(t, lin)), {"pde_split.route_model"})

    def test_key_distinctness(self):
        pipe = G.pipeline()
        keys = {"route-1": S.route1_key(11, "scintillation", 1), "pde r=1": S.replica_key("a" * 64, "b" * 64, 1, 1)}
        self.assertEqual(S.key_findings(keys, [(pipe, ["ecal"])]), [])
        clash = {**keys, "joint": rng.volume_key(11, "scintillation", 0)}
        self.assertEqual(codes(S.key_findings(clash, [(pipe, ["ecal"])])), {"pde_split.key_collision"})
        twice = {**keys, "joint": keys["pde r=1"]}
        self.assertEqual(codes(S.key_findings(twice, [(pipe, ["ecal"])])), {"pde_split.key_collision"})

    def test_design_findings_end_to_end(self):
        m, run, ph1, pr = Runs.one()
        php, _, _, _ = Runs.get("p04", efficiency=0.4)
        h = m["form"]["hashes"]
        docs = {"maps": {"one": m}, "photons": {"one": ph1, "nom": php}, "primaries": {"one": pr},
                "pipelines": [G.pipeline()], "readouts": ["ecal"], "build_environment": dict(G.BUILD)}
        plan = {"pde_split": {"map": "one", "centre_mm": P.CENTRE,
                              "readouts": {"ecal": {"route": "1", "observables": {"pe_width": False}}},
                              "route1": {"stage": "scintillation", "component": 1},
                              "record": {"status": "passed", "geant4_version": "11.2.1",
                                         "materials_sha256": h["materials_sha256"],
                                         "surfaces_sha256": h["surfaces_sha256"]},
                              "split_check": {"one": "one", "p": "nom", "nominal": {"p": 0.4}}}}
        r = S.design_findings(contract(), plan, docs)
        self.assertEqual(r["status"], "passed", r["findings"])
        dg = copy.deepcopy(plan)                    # delta mu from both maps digitized with the pipeline's run_seed
        dg["pde_split"]["split_check"]["digitize"] = {"rows": "r", "readout": "ecal", "A": [[0.015]],
                                                      "sigma_tot_design": [0.4],
                                                      "observables": [{"quantity": "photoelectrons"}]}
        r = S.design_findings(contract(), dg, {**docs, "rows": {"r": [list(x) for x in P.bins_rows(100)]}})
        self.assertEqual(r["status"], "passed", r["findings"])
        self.assertEqual(len(r["split_check"]["dtheta"]), 1)
        bad = copy.deepcopy(plan)
        bad["pde_split"]["readouts"]["ecal"]["route"] = "2_1"
        bad["pde_split"]["route1"]["stream"] = "efficiency_map/1"
        r = S.design_findings(contract(), bad, docs)
        self.assertEqual(codes(r["findings"]), {"pde_split.route_nonlinear", "pde_split.route1_stream"})
        self.assertTrue(all(f["remedy"] == "plan" for f in r["findings"]))


class Binding(unittest.TestCase):
    """Section 11.4 Table 2: the PDE-split row replaces WP-C's `incomplete`."""

    def test_candidates(self):
        r = chain.candidate_methods(contract(), G.plan())
        self.assertEqual(r["status"], "ok", r["findings"])
        e = r["parameters"]["pde"]
        self.assertEqual([x["method"] for x in e], ["rerun"])
        self.assertIn("route 2_1", e[0]["form"])
        self.assertIn("route 3", chain.candidate_methods(contract(model="table", table=P.pde_table()),
                                                         G.plan())["parameters"]["pde"][0]["form"])
        self.assertIn("resimulation", [x["method"] for x in r["excluded"]["pde"]])   # route 0, by rebinding
        p = G.plan()
        p["node_binding"]["nodes"]["pde"]["stored"] = ["hits"]
        self.assertEqual(chain.candidate_methods(contract(), p)["parameters"]["pde"], [])
        self.assertEqual(chain.candidate_methods(contract(ties=["reflectivity"]), G.plan())["parameters"]["pde"], [])


class Identity(unittest.TestCase):
    """Section 5.1: the PDE(E) part of item 4 through model_identity.response_hash(..., pde_part=)."""

    def test_pde_part(self):
        part = S.identity_part({"route": "3", "photons_sha256": "c" * 64, "table": P.pde_table()})
        self.assertEqual(part["photons_sha256"], "c" * 64)
        self.assertIsNone(S.identity_part({"route": "2_1"}))
        a = mi.response_hash("d" * 64, None, None, part)
        b = mi.response_hash("d" * 64, None, None, S.identity_part({"route": "3", "photons_sha256": "e" * 64,
                                                                    "table": P.pde_table()}))
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, mi.response_hash("d" * 64, None, None, None))
        masked = S.identity_part({"route": "3", "photons_sha256": "c" * 64, "table": P.pde_table()}, masked=True)
        self.assertEqual(masked["table"], "calib-masked/1")
        with self.assertRaises(S.SplitError):
            S.identity_part({"route": "3", "table": P.pde_table()})
        c = contract(model="table", table=P.pde_table())
        c["parameters"][-1]["bindings"] = [{"document": "evaluator", "pointer": "/pde/table/value/0"}]
        self.assertTrue(S.table_masked(c))
        self.assertFalse(S.table_masked(contract()))


class Evaluator(unittest.TestCase):
    """g4sim_calib_eval.py writes p eps_c into the job's efficiencies (route 2_1) or thins per photon (route 1)."""

    def make(self, route):
        sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))
        import calibration_g4sim_eval_fixtures as GE
        import g4sim_calib_eval  # noqa: F401  (registers the g4sim evaluator kind)
        from core.calibration import evaluator
        plan = GE.plan({"nominal": GE.batch(101, 0, 60, use="fit")})
        plan["evaluator"]["pde"] = {"parameter": "pde", "route": route, "component": 1, "nominal": 1.0}
        return evaluator.make(plan)

    def test_routes_in_the_evaluator(self):
        for route in ("2_1", "1"):
            e = self.make(route)
            r1, rp = e.evaluate({}), e.evaluate({"pde": 0.4})
            k = r1["names"].index("pe_mean")
            self.assertLess(abs(rp["pred"][k] / r1["pred"][k] - 0.4), 0.08, route)
            self.assertEqual(rp["seeds"], r1["seeds"])                      # common random numbers
            self.assertEqual(e.default_method("pde"), "re-digitization")
        with self.assertRaises(Exception):
            self.make("4")

    def test_route3_in_the_evaluator(self):
        """Route 3 reads the efficiency-1 mapping run's photons.csv: a constant PDE(E) = 0.4 gives exactly the
        prediction of route 2_1 at p = 0.4, and a theta on a table value moves it."""
        sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))
        import calibration_g4sim_eval_fixtures as GE
        import g4sim_calib_eval  # noqa: F401
        from core.calibration import evaluator
        ph, pr, emitted, detected = Runs.get("one")

        def make(pde):
            plan = GE.plan({"nominal": GE.batch(101, 0, 40, use="fit")})
            plan["evaluator"]["documents"]["maps"]["light"] = P.build_map(emitted, detected)
            plan["evaluator"]["pde"] = pde
            return evaluator.make(plan)
        flat = {"energy_eV": [2.0, 3.5], "value": [0.4, 0.4]}
        r3 = make({"route": "3", "photons": ph, "primaries": pr, "centre_mm": P.CENTRE, "table": flat}).evaluate({})
        r21 = make({"parameter": "pde", "route": "2_1", "nominal": 1.0}).evaluate({"pde": 0.4})
        np.testing.assert_allclose(r3["pred"], r21["pred"])
        e = make({"route": "3", "photons": ph, "primaries": pr, "centre_mm": P.CENTRE, "table": P.pde_table(),
                  "parameter": "pde", "pointer": "/pde/table/value/3"})
        k = e.evaluate({})["names"].index("pe_mean")
        self.assertAlmostEqual(e.nominal_theta["pde"], 0.5)
        self.assertGreater(e.evaluate({"pde": 0.9})["pred"][k], e.evaluate({})["pred"][k])


class Geant4Items(unittest.TestCase):
    def test_items_needing_geant4(self):
        self.skipTest("Geant4 not run for the PDE-split evidence (section 15.2): the split check on the ZDC fixture "
                      "with optics and its nested pair from G4OpBoundaryProcess; route 2_1 against a Geant4 mapping run "
                      "at efficiency p; route 3 against a Geant4 mapping run at PDE(E); the section 8.7 row 2009 "
                      "calibration (false-rejection rate, power against a tied reflectance)")


if __name__ == "__main__":
    unittest.main()
