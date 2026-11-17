"""CHK-AT-09-03 evidence: the field-propagation benchmark of a g4sim run follows the helix of either field sign.

bench_field_g4sim compares the crossings of positively charged geantinos in a uniform field along z with the analytic
helix. Before the fix a negative field negated the turned angle, which runs the track backwards along its initial
direction and leaves the bend on the same side; a correct propagation in B < 0 failed (about 1.8 m off), so the verdict
of every negative-field study was wrong.

Oracle (no expected value comes from the module under test, and none imports it to compute one): the circle of a
positive charge, derived by hand. The Lorentz force q v x B with B = (0, 0, B) on a velocity of azimuth phi,
v_T (cos phi, sin phi), is q v_T B (sin phi, -cos phi): v_T rotated by -90 degrees for B > 0, so the azimuth turns as
phi = phi0 - s theta with s = sign(B) and theta = (transverse path) / R, R = p_T / (0.299792458 |B|) (mm, MeV/c, T).
Integrating the direction gives
    x = x0 + s R [sin phi0 - sin(phi0 - s theta)],  y = y0 + s R [cos(phi0 - s theta) - cos phi0].
Exhaustive record: every case of the finite domain B in {+1, -1, +2, -0.5} T, phi0 in the 8 azimuths k 45 degrees,
and theta in {pi/2, pi, 3 pi/2} (96 crossings, the turned angle reached through z at u_z = 0.8). A second check
integrates the Lorentz force vector equation by fourth-order Runge-Kutta for both field signs (the turning sense then
comes from the cross product, not from the hand derivation). Negative control: the pre-fix formula, emulated here,
misses the B < 0 crossings by far more than the tolerance.

Tolerance, fixed before the first run and never widened: TOL_UM = 1e-3 um on the benchmark's largest in-plane distance
(its own default verdict tolerance is 0.5 um). Positions are below 1e4 mm, where a double carries about 1e-12 mm
(1e-9 um), and crossings are written with repr; the Runge-Kutta step of 1 mm on radii of 2000 mm and more has a global
error of about L (h / R)^4 < 1e-9 mm. The defect is 1e6 um. All inputs are SYNTHETIC.
"""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN))
sys.path.insert(0, str(PLUGIN / "skills" / "hep-detector" / "scripts"))
import geant4_benchmarks as G  # noqa: E402

TOL_UM = 1e-3
C_LIGHT = 0.299792458  # GeV / (T m), i.e. MeV / (T mm)
ENERGY_MEV = 1000.0  # a massless charged geantino: p = E
START = (5.0, -3.0, -100.0)
U_TRANSVERSE, U_ALONG_FIELD = 0.6, 0.8
FIELDS_T = (1.0, -1.0, 2.0, -0.5)
AZIMUTHS = tuple(k * math.pi / 4 for k in range(8))
TURNS = (math.pi / 2, math.pi, 3 * math.pi / 2)


def radius_mm(field: float) -> float:
    return ENERGY_MEV * U_TRANSVERSE / (C_LIGHT * abs(field))


def z_at_turn(field: float, theta: float) -> float:
    return START[2] + theta * radius_mm(field) / U_TRANSVERSE * U_ALONG_FIELD


def circle(field: float, phi0: float, theta: float) -> tuple[float, float]:
    s, r = math.copysign(1.0, field), radius_mm(field)
    return (START[0] + s * r * (math.sin(phi0) - math.sin(phi0 - s * theta)),
            START[1] + s * r * (math.cos(phi0 - s * theta) - math.cos(phi0)))


def runge_kutta(field: float, phi0: float, z_stop: float, step: float = 1.0) -> tuple[float, float]:
    """Integrate d(pos)/ds = u, du/ds = (C_LIGHT / p) u x B for a +1 charge, B = (0, 0, field), to z = z_stop."""
    k = C_LIGHT / ENERGY_MEV

    def deriv(state):
        _, _, _, ux, uy, uz = state
        return (ux, uy, uz, k * uy * field, -k * ux * field, 0.0)

    state = (*START, U_TRANSVERSE * math.cos(phi0), U_TRANSVERSE * math.sin(phi0), U_ALONG_FIELD)
    length = (z_stop - START[2]) / U_ALONG_FIELD
    n = int(math.ceil(length / step))
    h = length / n
    for _ in range(n):
        k1 = deriv(state)
        k2 = deriv(tuple(a + h / 2 * b for a, b in zip(state, k1)))
        k3 = deriv(tuple(a + h / 2 * b for a, b in zip(state, k2)))
        k4 = deriv(tuple(a + h * b for a, b in zip(state, k3)))
        state = tuple(a + h / 6 * (b1 + 2 * b2 + 2 * b3 + b4) for a, b1, b2, b3, b4 in zip(state, k1, k2, k3, k4))
    return state[0], state[1]


class _Field(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.d = Path(self._t.name)

    def tearDown(self):
        self._t.cleanup()

    def bench(self, field: float, crossings: list[tuple[int, float, float, float]], azimuths) -> dict:
        ir = {"physical": {"fields": {"dipole": {"b_tesla": ["0", "0", repr(field)]}}, "templates": {}}}
        (self.d / "ir.json").write_text(json.dumps(ir), encoding="utf-8")
        (self.d / "primaries.csv").write_text("".join(
            f"{i},{ENERGY_MEV!r},{START[0]!r},{START[1]!r},{START[2]!r},{U_TRANSVERSE * math.cos(a)!r},{U_TRANSVERSE * math.sin(a)!r},"
            f"{U_ALONG_FIELD!r}\n" for i, a in enumerate(azimuths)), encoding="utf-8")
        (self.d / "crossings.csv").write_text("event_id,x_mm,y_mm,z_mm\n" + "".join(
            f"{e},{x!r},{y!r},{z!r}\n" for e, x, y, z in crossings), encoding="utf-8")
        return G.bench_field_g4sim({"ir": "ir.json", "primaries": "primaries.csv", "crossings": "crossings.csv",
                                    "field_tesla": field}, self.d)


class HelixOfEitherFieldSign(_Field):
    def test_every_field_azimuth_and_turn(self):
        for field in FIELDS_T:
            with self.subTest(field=field):
                cross = [(i, *circle(field, a, t), z_at_turn(field, t)) for i, a in enumerate(AZIMUTHS) for t in TURNS]
                out = self.bench(field, cross, AZIMUTHS)
                self.assertEqual(out["compared"], len(AZIMUTHS) * len(TURNS))
                self.assertLess(out["geant4"], TOL_UM, out)
                self.assertEqual(out["verdict"], "pass")

    def test_runge_kutta_lorentz_force_for_both_signs(self):
        phi0 = math.radians(30.0)
        for field in (1.0, -1.0):
            with self.subTest(field=field):
                cross = [(0, *runge_kutta(field, phi0, z), z) for z in (200.0, 600.0, 1200.0)]
                out = self.bench(field, cross, (phi0,))
                self.assertLess(out["geant4"], TOL_UM, out)
                self.assertEqual(out["verdict"], "pass")

    def test_pre_fix_formula_misses_a_negative_field(self):
        """Negative control, emulating the pre-fix propagation in the test: turned negated for B < 0, across always
        -R (1 - cos turned)."""
        field, phi0, theta = -1.0, 0.0, math.pi / 2
        r = radius_mm(field)
        turned = -theta
        along, across = r * math.sin(turned), -r * (1 - math.cos(turned))
        pre_fix = (START[0] + along * math.cos(phi0) - across * math.sin(phi0),
                   START[1] + along * math.sin(phi0) + across * math.cos(phi0))
        x, y = circle(field, phi0, theta)
        self.assertGreater(math.hypot(pre_fix[0] - x, pre_fix[1] - y) * 1000, 1e6 * TOL_UM)


if __name__ == "__main__":
    unittest.main()
