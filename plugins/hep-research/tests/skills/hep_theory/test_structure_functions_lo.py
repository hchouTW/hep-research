"""structure_functions_lo.py (Th14): LO structure functions and NC/CC cross sections against hand calculations.

Tolerances fixed before comparing: relative 1e-12 for algebraic identities and hand-calculated values.
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "skills/hep-theory/scripts/structure_functions_lo.py"
TOL = 1e-12
GEV2_PB = 0.38937937217185936e9
TOY = {"d": 0.31, "u": 0.62, "s": 0.07, "c": 0.03, "b": 0.01,
       "dbar": 0.11, "ubar": 0.09, "sbar": 0.06, "cbar": 0.025, "bbar": 0.008}
EW = ["--sin2w", "0.23", "--mz", "91.19", "--mw", "80.37", "--gf", "1.1664e-5", "--ew-scheme", "toy on-shell inputs"]


def run(partons=TOY, extra=(), target=("--target", "p")):
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "partons.json"
        p.write_text(json.dumps({"representation": "xf", "values": partons}))
        args = [sys.executable, str(SCRIPT), "--x", "0.1", "--Q2", "100", "--s", "101200", "--M", "0.938",
                "--sf-signs", "pdg", "--alpha", "0.0072973525643", "--alpha-label", "alpha(0)",
                "--target-normalization", "per-nucleon", "--target-mass-treatment", "neglected",
                "--heavy-quark-scheme", "ZM-VFNS (toy)", "--partons", str(p), *target, *extra]
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
    return r.returncode, json.loads(r.stdout)


def close(a, b, tol=TOL):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


class StructureFunctionsLO(unittest.TestCase):
    def test_photon_exchange_hand_value(self):
        code, out = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gamma"])
        self.assertEqual(code, 0, out)
        o = out["outputs"]
        f2 = (4 / 9) * (TOY["u"] + TOY["ubar"] + TOY["c"] + TOY["cbar"]) + (1 / 9) * (
            TOY["d"] + TOY["dbar"] + TOY["s"] + TOY["sbar"] + TOY["b"] + TOY["bbar"])
        self.assertTrue(close(o["F2"], f2))
        self.assertEqual(o["xF3"], 0.0)
        self.assertEqual(o["FL"], 0.0)
        self.assertTrue(close(o["two_x_F1"], o["F2"]))  # Callan-Gross
        x, q2, y = 0.1, 100.0, o["y"]
        self.assertTrue(close(y, q2 / (x * (101200 - 0.938 ** 2))))
        yp = 1 + (1 - y) ** 2
        alpha = 0.0072973525643
        hand = 2 * math.pi * alpha ** 2 / (x * q2 ** 2) * yp * f2
        self.assertTrue(close(o["d2sigma_dx_dQ2_GeV4"], hand))
        self.assertTrue(close(o["d2sigma_dx_dQ2_pb_per_GeV2"], hand * GEV2_PB))
        self.assertTrue(close(o["d2sigma_dx_dy_GeV2"], hand * q2 / y))
        self.assertTrue(close(o["sigma_r_NC"], f2))
        self.assertEqual(out["derivation_status"], "analytic-derivation")

    def test_charge_symmetry_includes_antiquarks(self):
        swapped = dict(TOY, u=TOY["d"], d=TOY["u"], ubar=TOY["dbar"], dbar=TOY["ubar"])
        for bosons in (["--bosons", "gamma"], ["--bosons", "gammaZ", *EW]):
            _, on_n = run(extra=["--lepton", "e-", "--polarization", "0", *bosons], target=("--target", "n"))
            _, swapped_p = run(partons=swapped, extra=["--lepton", "e-", "--polarization", "0", *bosons])
            for key in ("F2", "xF3", "d2sigma_dx_dQ2_GeV4"):
                self.assertTrue(close(on_n["outputs"][key], swapped_p["outputs"][key]), (bosons, key))

    def test_xf3_sign_flips_between_e_plus_and_e_minus_unpolarized(self):
        _, em = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gammaZ", *EW])
        _, ep = run(extra=["--lepton", "e+", "--polarization", "0", "--bosons", "gammaZ", *EW])
        a, b = em["outputs"], ep["outputs"]
        self.assertTrue(close(a["F2"], b["F2"]))
        self.assertTrue(close(a["xF3"], b["xF3"]))
        self.assertGreater(a["xF3"], 0.0)  # e- p above e+ p at high Q^2 (u and d valence excess)
        self.assertTrue(close(a["bracket"] - b["bracket"], 2 * a["Y_minus"] * a["xF3"]))
        self.assertGreater(a["d2sigma_dx_dQ2_GeV4"], b["d2sigma_dx_dQ2_GeV4"])

    def test_polarized_nc_depends_on_charge_times_polarization(self):
        # Eqs. (18.11)-(18.12) depend on charge and polarization only through lambda = charge * P_e
        _, em = run(extra=["--lepton", "e-", "--polarization", "-0.3", "--bosons", "gammaZ", *EW])
        _, ep = run(extra=["--lepton", "e+", "--polarization", "0.3", "--bosons", "gammaZ", *EW])
        _, e0 = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gammaZ", *EW])
        self.assertTrue(close(em["outputs"]["F2"], ep["outputs"]["F2"]))
        self.assertTrue(close(em["outputs"]["xF3"], ep["outputs"]["xF3"]))
        self.assertFalse(close(em["outputs"]["F2"], e0["outputs"]["F2"], 1e-9))
        # independent build of F2^NC from the coupling combination (v_e + lambda a_e), lambda = +0.3
        o, p = em["outputs"], em["outputs"]["parts"]
        ve, ae, lam = -0.5 + 2 * 0.23, -0.5, 0.3
        f2 = (p["F2_gamma"] - (ve + lam * ae) * o["eta_gammaZ"] * p["F2_gammaZ"]
              + (ve ** 2 + ae ** 2 + 2 * lam * ve * ae) * o["eta_gammaZ"] ** 2 * p["F2_Z"])
        self.assertTrue(close(o["F2"], f2))

    def test_photon_limit_of_gammaZ(self):
        # eta_gammaZ -> 0 as G_F -> 0: the gammaZ result reduces to photon exchange
        ew = list(EW)
        ew[ew.index("--gf") + 1] = "1e-30"
        _, g = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gamma"])
        _, gz = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gammaZ", *ew])
        self.assertTrue(close(g["outputs"]["F2"], gz["outputs"]["F2"]))
        self.assertTrue(abs(gz["outputs"]["xF3"]) < 1e-20)

    def test_cc_normalization_against_parton_form(self):
        # e+ p CC, unpolarized: d2sigma/dx dQ^2 = G_F^2/(2 pi x) (M_W^2/(Q^2+M_W^2))^2 x[(ubar+cbar) + (1-y)^2 (d+s)]
        _, ep = run(extra=["--lepton", "e+", "--polarization", "0", "--bosons", "CC", "--ckm", "diagonal", *EW])
        o = ep["outputs"]
        x, q2, y, gf, mw = 0.1, 100.0, o["y"], 1.1664e-5, 80.37
        hand = gf ** 2 / (2 * math.pi * x) * (mw ** 2 / (q2 + mw ** 2)) ** 2 * (
            TOY["ubar"] + TOY["cbar"] + (1 - y) ** 2 * (TOY["d"] + TOY["s"]))
        self.assertTrue(close(o["d2sigma_dx_dQ2_GeV4"], hand))
        self.assertEqual(o["boson"], "W+")

    def test_cc_polarization_scaling(self):
        base = ["--bosons", "CC", "--ckm", "diagonal", *EW]
        _, u = run(extra=["--lepton", "e-", "--polarization", "0", *base])
        _, r = run(extra=["--lepton", "e-", "--polarization", "1", *base])
        _, l30 = run(extra=["--lepton", "e-", "--polarization", "-0.3", *base])
        self.assertEqual(r["outputs"]["d2sigma_dx_dQ2_GeV4"], 0.0)  # right-handed e- has no CC
        self.assertTrue(close(l30["outputs"]["d2sigma_dx_dQ2_GeV4"], 1.3 * u["outputs"]["d2sigma_dx_dQ2_GeV4"]))
        self.assertEqual(u["outputs"]["boson"], "W-")

    def test_nucleus_with_one_proton_is_the_proton(self):
        _, p = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gamma"])
        _, a1 = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gamma"], target=("--Z", "1", "--A", "1"))
        self.assertTrue(close(p["outputs"]["F2"], a1["outputs"]["F2"]))
        _, iso = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gamma"], target=("--Z", "6", "--A", "12"))
        _, n = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gamma"], target=("--target", "n"))
        self.assertTrue(close(iso["outputs"]["F2"], 0.5 * (p["outputs"]["F2"] + n["outputs"]["F2"])))

    def test_rejections_exit_2(self):
        ok = ["--lepton", "e-", "--polarization", "0", "--bosons", "gamma"]
        bad_cases = [
            (TOY, ok + ["--x", "1.2"]),                                   # x > 1 for a nucleon
            ({k: v for k, v in TOY.items() if k != "cbar"}, ok),          # missing flavour
            (dict(TOY, u=float("nan")), ok),                              # non-finite (JSON NaN)
            (TOY, ["--lepton", "e-", "--bosons", "gamma"]),               # no polarization for a charged lepton
            (TOY, ["--lepton", "e-", "--polarization", "0", "--bosons", "gammaZ"]),  # missing EW inputs
            (TOY, ["--lepton", "nu", "--bosons", "gamma"]),               # neutrino NC
            (TOY, ["--lepton", "e+", "--polarization", "0", "--bosons", "CC", *EW]),  # CC without --ckm
            (TOY, ok + ["--Q2", "20000"]),                                # y > 1
            # review I2: electroweak inputs out of range
            (TOY, ["--lepton", "e-", "--polarization", "0", "--bosons", "gammaZ", *EW, "--gf=-1.1664e-5"]),
            (TOY, ["--lepton", "e-", "--polarization", "0", "--bosons", "gammaZ", *EW, "--sin2w", "1.7"]),
            (TOY, ["--lepton", "e-", "--polarization", "0", "--bosons", "gammaZ", *EW, "--mz=-91.19"]),
            (TOY, ["--lepton", "e-", "--polarization", "0", "--bosons", "CC", "--ckm", "diagonal", *EW, "--mw", "0"]),
            (TOY, ok + ["--q2-min", "nan"]),
        ]
        for partons, extra in bad_cases:
            code, out = run(partons=partons, extra=extra)
            self.assertEqual(code, 2, (extra, out))
            self.assertEqual(out["status"], "rejected")

    def test_validity_bounds_are_the_users(self):
        _, out = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gamma", "--q2-min", "200"])
        self.assertFalse(out["outputs"]["validity"]["Q2_min"]["inside"])
        _, out = run(extra=["--lepton", "e-", "--polarization", "0", "--bosons", "gamma"])
        self.assertIsInstance(out["outputs"]["validity"], str)


if __name__ == "__main__":
    unittest.main()
