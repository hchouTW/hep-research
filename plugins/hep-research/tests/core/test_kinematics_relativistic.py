"""Tests for core/kinematics/relativistic.py reference conversions for proton and helium
(literal values computed by hand from p = |Z| R, E = sqrt(p^2 + m^2)), the
inverse round trips, exact Jacobians against finite differences, and rejection of
every missing or unphysical assumption. Run from the skill directory with
`python3 -m unittest discover -s tests -v`. Standard library only."""
import contextlib
import io
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from core.kinematics import relativistic as kin  # noqa: E402
from core.kinematics.relativistic import KinematicsError, Species  # noqa: E402

M_P, M_HE4 = 0.9383, 3.7274  # GeV, user-stated masses for these tests


class ConversionTests(unittest.TestCase):
    def test_proton_rigidity_is_momentum_numerically(self):
        sp = Species(Z=1, A=1, mass=M_P)
        self.assertAlmostEqual(kin.convert(10, "rigidity", "momentum", sp), 10.0, places=12)
        self.assertAlmostEqual(kin.convert(10, "rigidity", "total_energy", sp), 10.043924, places=5)
        self.assertAlmostEqual(kin.convert(10, "rigidity", "kinetic_energy", sp), 9.105624, places=5)

    def test_helium_momentum_is_twice_rigidity(self):
        sp = Species(Z=2, A=4, mass=M_HE4)
        self.assertAlmostEqual(kin.convert(20, "rigidity", "momentum", sp), 40.0, places=12)
        self.assertNotAlmostEqual(kin.convert(20, "rigidity", "momentum", sp), 20.0)
        self.assertAlmostEqual(kin.convert(20, "rigidity", "total_energy", sp), 40.17330, places=4)
        self.assertAlmostEqual(kin.convert(20, "rigidity", "kinetic_energy_per_nucleon", sp), 9.111475, places=4)

    def test_round_trip_through_every_variable(self):
        sp = Species(Z=2, A=4, mass=M_HE4)
        for src in kin.VARIABLES:
            start = kin.convert(7.5, "rigidity", src, sp)
            for dst in kin.VARIABLES:
                back = kin.convert(kin.convert(start, src, dst, sp), dst, "rigidity", sp)
                self.assertAlmostEqual(back, 7.5, places=9, msg=f"{src}->{dst}")

    def test_sign_of_rigidity_is_ignored(self):
        self.assertEqual(kin.rigidity_to_momentum(-12.0, 1), kin.rigidity_to_momentum(12.0, 1))

    def test_mass_from_rigidity_and_beta_round_trip(self):
        m_d = 1.8756
        p = kin.rigidity_to_momentum(10, 1)
        b = kin.beta(p, m_d)
        self.assertAlmostEqual(kin.mass_from_rigidity_beta(10, 1, b), m_d, places=9)

    def test_mass_uncertainty_with_explicit_correlation(self):
        b = 0.9
        g2 = 1 / (1 - b * b)
        c = g2 * 0.001
        self.assertAlmostEqual(kin.mass_relative_uncertainty(0.05, 0.001, b, 0.0),
                               math.sqrt(0.05 ** 2 + c ** 2), places=12)
        self.assertAlmostEqual(kin.mass_relative_uncertainty(0.05, 0.001, b, 1.0), abs(0.05 - c), places=12)

    def test_uncertainty_propagation_matches_finite_difference(self):
        sp = Species(Z=2, A=4, mass=M_HE4)
        h = 1e-6
        slope = (kin.convert(20 + h, "rigidity", "kinetic_energy_per_nucleon", sp)
                 - kin.convert(20 - h, "rigidity", "kinetic_energy_per_nucleon", sp)) / (2 * h)
        self.assertAlmostEqual(kin.propagate(20, 1.0, "rigidity", "kinetic_energy_per_nucleon", sp), slope, places=6)


class JacobianAndBinTests(unittest.TestCase):
    def test_flux_jacobian_matches_numerical_derivative(self):
        sp = Species(Z=1, A=1, mass=M_P)
        x, h = 4.0, 1e-6
        d_dst = (kin.convert(x + h, "rigidity", "kinetic_energy", sp)
                 - kin.convert(x - h, "rigidity", "kinetic_energy", sp)) / (2 * h)
        self.assertAlmostEqual(kin.flux_jacobian(x, "rigidity", "kinetic_energy", sp), 1 / d_dst, places=6)

    def test_bin_average_factor_is_ratio_of_widths(self):
        sp = Species(Z=2, A=4, mass=M_HE4)
        out = kin.convert_bins([2.0, 4.0, 8.0], "rigidity", "kinetic_energy_per_nucleon", sp)
        self.assertEqual(len(out["bins"]), 2)
        for (lo, hi), b in zip([(2.0, 4.0), (4.0, 8.0)], out["bins"]):
            width_new = b["to"][1] - b["to"][0]
            self.assertAlmostEqual(b["bin_average_flux_factor"], (hi - lo) / width_new, places=12)
        self.assertTrue(all(b > a for a, b in zip(out["edges"], out["edges"][1:])))

    def test_point_jacobian_differs_from_bin_average_for_steep_transform(self):
        sp = Species(Z=1, A=1, mass=M_P)
        out = kin.convert_bins([0.5, 2.0], "rigidity", "kinetic_energy", sp)["bins"][0]
        self.assertNotAlmostEqual(out["bin_average_flux_factor"], out["point_jacobian_at_geometric_centre"], places=2)


class RejectionTests(unittest.TestCase):
    def test_missing_Z_is_rejected(self):
        with self.assertRaises(KinematicsError):
            kin.convert(10, "rigidity", "momentum", Species(Z=None))
        with self.assertRaises(KinematicsError):
            kin.rigidity_to_momentum(10, None)

    def test_bad_Z_values_rejected(self):
        for z in (0, -1, 1.5, True):
            with self.assertRaises(KinematicsError, msg=str(z)):
                kin.rigidity_to_momentum(10, z)

    def test_missing_A_for_kinetic_energy_per_nucleon(self):
        with self.assertRaises(KinematicsError):
            kin.convert(10, "rigidity", "kinetic_energy_per_nucleon", Species(Z=2, mass=M_HE4))

    def test_missing_mass_for_energy(self):
        for dst in ("total_energy", "kinetic_energy", "kinetic_energy_per_nucleon"):
            with self.assertRaises(KinematicsError, msg=dst):
                kin.convert(10, "rigidity", dst, Species(Z=2, A=4))

    def test_nonpositive_mass_rejected(self):
        for m in (0.0, -1.0, float("nan")):
            with self.assertRaises(KinematicsError, msg=str(m)):
                kin.total_energy(10, m)

    def test_beta_outside_physical_range_rejected(self):
        for b in (0.0, 1.0, 1.2, -0.3, float("nan")):
            with self.assertRaises(KinematicsError, msg=str(b)):
                kin.gamma(b)
            with self.assertRaises(KinematicsError, msg=str(b)):
                kin.mass_from_rigidity_beta(10, 1, b)

    def test_rigidity_unit_given_for_momentum_is_rejected(self):
        with self.assertRaises(KinematicsError) as ctx:
            kin.convert(20, "momentum", "rigidity", Species(Z=2), unit="GV")
        self.assertIn("rigidity", str(ctx.exception))

    def test_unit_of_another_variable_is_rejected_for_each_variable(self):
        for variable in kin.VARIABLES:
            wrong = next(u for v, u in kin.UNITS.items() if v != variable and u != kin.UNITS[variable])
            with self.assertRaises(KinematicsError, msg=variable):
                kin.check_unit(variable, wrong)

    def test_unknown_variable_rejected(self):
        with self.assertRaises(KinematicsError):
            kin.convert(1, "energy", "momentum", Species(Z=1))

    def test_energy_below_rest_energy_rejected(self):
        with self.assertRaises(KinematicsError):
            kin.momentum_from_total_energy(0.5, M_P)

    def test_bad_bin_edges_rejected(self):
        sp = Species(Z=1, A=1, mass=M_P)
        for edges in ([1.0], [2.0, 1.0], [1.0, 1.0, 2.0], [0.0, 1.0]):
            with self.assertRaises(KinematicsError, msg=str(edges)):
                kin.convert_bins(edges, "rigidity", "kinetic_energy", sp)

    def test_correlation_must_be_stated_and_bounded(self):
        with self.assertRaises(KinematicsError):
            kin.mass_relative_uncertainty(0.05, 0.001, 0.9, None)
        with self.assertRaises(KinematicsError):
            kin.mass_relative_uncertainty(0.05, 0.001, 0.9, 1.5)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = kin.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_convert_success_is_labelled_general_method(self):
        code, out = self.run_cli("convert", "--from", "rigidity", "--to", "momentum", "--value", "20", "--Z", "2")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["output"]["value"], 40.0)
        self.assertEqual(out["label"], "[General method]")
        self.assertIn("not measured detector performance", out["note"])

    def test_missing_Z_exits_2(self):
        code, out = self.run_cli("convert", "--from", "rigidity", "--to", "momentum", "--value", "20")
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "rejected")

    def test_mass_resolution_requires_rho(self):
        code, out = self.run_cli("mass-resolution", "--R", "10", "--beta", "0.9", "--Z", "1",
                                 "--sigma-R-rel", "0.05", "--sigma-beta-rel", "0.001")
        self.assertEqual(code, 2)
        code, out = self.run_cli("mass-resolution", "--R", "10", "--beta", "0.9", "--Z", "1",
                                 "--sigma-R-rel", "0.05", "--sigma-beta-rel", "0.001", "--rho", "0")
        self.assertEqual(code, 0)
        self.assertAlmostEqual(out["relative_mass_uncertainty_first_order"], 0.050277, places=5)


if __name__ == "__main__":
    unittest.main()
