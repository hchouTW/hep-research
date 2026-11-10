"""adapters/calo-cluster, D2 stage 1 of T08 (t07-t09-task-sheets.md, T08): the cell chain, section 7.1 clustering and the product
format, on hand-made events only. No fixture event and no Monte Carlo: every grid here is written by hand or is a closed-form
shower image, so the expectation of each test is fixed in the test before the recipe runs.

Expectations come from the text of t04-values-v4.md section 7.1, coded a second time here in plain Python (math.erf, loops) and
not from the recipe's modules: a test that calls the recipe compares it with that second coding. Each rule is driven with an
honest grid and with the defect it must catch. Run from the plugin root: python -m unittest tests.adapters.test_calo_cluster -v
"""
from __future__ import annotations

import ast
import copy
import io
import json
import math
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import numpy

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "calo-cluster"
ASSETS = ADAPTER / "assets"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ASSETS / "fixture_tools"))
sys.path.insert(0, str(ASSETS))

from calo_recipe import ENERGY_KIND, RECIPE, cell_chain, cell_input, clustering, configuration, product, profile  # noqa: E402
import t08_fixture_files  # noqa: E402
import t08_readings  # noqa: E402
from contracts import tool_contract  # noqa: E402

N = 40
Q, SIGMA_N, T_C, T_S, W = 0.2, 0.2, 0.6, 10.0, 1.0     # t04-values-v4.md section 4.2, written here from the text
ITERATIONS = 30                                         # section 7.1
CFG = configuration.load()


# --- a second coding of section 7.1, from its text ----------------------------------------------------------------------

def phi_cdf(u):
    return 0.5 * (1.0 + math.erf(u / math.sqrt(2.0)))


def g_axis(i, c):
    return phi_cdf((i + 1 - c) / W) - phi_cdf((i - c) / W)


def g_cell(ix, iy, x, y):
    return g_axis(ix, x) * g_axis(iy, y)


def image(showers, n=N):
    """Noise-free shower image: E g_c(x, y) summed over showers, as a list of lists."""
    return [[sum(e * g_cell(ix, iy, x, y) for e, x, y in showers) for iy in range(n)] for ix in range(n)]


def as_array(grid):
    return numpy.array(grid, dtype=float)


def text_one_peak(cells, e, ring):
    """Section 7.1, one peak: A, x, y, sigma_A^2, sigma_x^2, sigma_y^2. cells, ring: lists of (ix, iy); e: dict of values."""
    a = sum(e[c] for c in cells)
    x = sum(e[c] * (c[0] + 0.5) for c in cells) / a
    y = sum(e[c] * (c[1] + 0.5) for c in cells) / a
    sa2 = sum(Q * max(e[c], 0.0) + SIGMA_N ** 2 for c in cells)
    sx2 = sy2 = 0.0
    for c in list(cells) + list(ring):
        mu = a * g_cell(c[0], c[1], x, y)
        s = math.sqrt(Q * mu + SIGMA_N ** 2)
        t = (T_C - mu) / s
        upper = 1.0 - phi_cdf(t)
        dens = math.exp(-0.5 * t * t) / math.sqrt(2 * math.pi)
        m1 = mu * upper + s * dens
        m2 = (mu * mu + s * s) * upper + s * (mu + T_C) * dens
        v = m2 - m1 * m1
        sx2 += (c[0] + 0.5 - x) ** 2 * v / a ** 2
        sy2 += (c[1] + 0.5 - y) ** 2 * v / a ** 2
    return a, x, y, sa2, sx2, sy2


def text_two_peaks(cells, e, peaks):
    """Section 7.1, two peaks: 30 iterations of sharing, no early stop. Returns A, centres, fractions of the last iteration."""
    centres = [[p[0] + 0.5, p[1] + 0.5] for p in peaks]
    amps = [e[p] for p in peaks]
    fractions = None
    for _ in range(ITERATIONS):
        fractions = []
        for c in cells:
            w = [amps[k] * g_cell(c[0], c[1], *centres[k]) for k in range(2)]
            fractions.append([w[k] / (w[0] + w[1]) for k in range(2)])
        amps = [sum(fractions[i][k] * e[c] for i, c in enumerate(cells)) for k in range(2)]
        centres = [[sum(fractions[i][k] * e[c] * (c[0] + 0.5) for i, c in enumerate(cells)) / amps[k],
                    sum(fractions[i][k] * e[c] * (c[1] + 0.5) for i, c in enumerate(cells)) / amps[k]] for k in range(2)]
    return amps, centres, fractions


def text_fisher_variances(cells, amps, centres, step=1e-6):
    """Section 7.1, two peaks: the Fisher matrix with derivatives of mu_c by central differences, inverted. theta = (A1, A2, x1, y1, x2, y2)."""
    theta = [amps[0], amps[1], centres[0][0], centres[0][1], centres[1][0], centres[1][1]]

    def mu(th, c):
        return th[0] * g_cell(c[0], c[1], th[2], th[3]) + th[1] * g_cell(c[0], c[1], th[4], th[5])
    grads = []
    for c in cells:
        row = []
        for j in range(6):
            hi, lo = list(theta), list(theta)
            h = step * max(1.0, abs(theta[j]))
            hi[j] += h
            lo[j] -= h
            row.append((mu(hi, c) - mu(lo, c)) / (2 * h))
        grads.append(row)
    info = numpy.zeros((6, 6))
    for c, row in zip(cells, grads):
        v = Q * mu(theta, c) + SIGMA_N ** 2
        info += numpy.outer(row, row) / v
    return numpy.diag(numpy.linalg.inv(info))


def components_of(e, live=None):
    """Kept components by the text: cells >= T_c, 8-connected, kept if one cell >= T_s. Lists of (ix, iy), ascending flat index."""
    n = len(e)
    seen, out = set(), []
    for ix in range(n):
        for iy in range(n):
            if (ix, iy) in seen or e[ix][iy] is None or e[ix][iy] < T_C:
                continue
            stack, comp = [(ix, iy)], []
            seen.add((ix, iy))
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx_, ny_ = cx + dx, cy + dy
                        if 0 <= nx_ < n and 0 <= ny_ < n and (nx_, ny_) not in seen and e[nx_][ny_] is not None and e[nx_][ny_] >= T_C:
                            seen.add((nx_, ny_))
                            stack.append((nx_, ny_))
            if any(e[c[0]][c[1]] >= T_S for c in comp):
                out.append(sorted(comp, key=lambda c: c[0] * n + c[1]))
    return sorted(out, key=lambda comp: comp[0][0] * n + comp[0][1])


def ring_of(comp, e):
    n = len(e)
    own = set(comp)
    ring = set()
    for cx, cy in comp:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                c = (cx + dx, cy + dy)
                if c not in own and 0 <= c[0] < n and 0 <= c[1] < n and e[c[0]][c[1]] is not None:
                    ring.add(c)
    return sorted(ring)


def run(grid, live=None, saturated=None):
    e = as_array([[numpy.nan if v is None else v for v in row] for row in grid])
    live = numpy.isfinite(e) if live is None else live
    saturated = numpy.zeros_like(live) if saturated is None else saturated
    return clustering.cluster_event(e, live, saturated, CFG)


def flat(c):
    return c[0] * N + c[1]


def close(case, a, b, rel=1e-9, msg=None):
    case.assertLessEqual(abs(a - b), rel * max(abs(a), abs(b), 1e-300), msg or f"{a!r} != {b!r}")


# --- payload and readout helpers -----------------------------------------------------------------------------------------

def payloads(pedestal=0.0, gain=1.0, operation="multiply", channels=N * N, against=None):
    ped = cell_input.payload_bytes("pedestal", "subtract", pedestal, channels, "adc", "nominal", "hand-made test constant")
    ped_id = __import__("hashlib").sha256(ped).hexdigest()
    gb = cell_input.payload_bytes("gain", operation, gain, channels, "MeV/adc", "nominal", "hand-made test constant",
                                  derived_against=[ped_id] if against is None else against)
    return ped, gb


class Configuration(unittest.TestCase):
    def test_values_are_version_4s_written_constants(self):
        doc = json.loads((ASSETS / "t08-grid-1.configuration.json").read_text(encoding="utf-8"))
        self.assertEqual(doc["grid"], {"nx": 40, "ny": 40, "cell_width": 1.0})
        self.assertEqual((doc["shower_width_cells"], doc["cell_quantum_mev"], doc["noise_sigma_mev"], doc["cell_threshold_mev"],
                          doc["seed_threshold_mev"], doc["sharing_iterations"], doc["peaks_kept"]), (W, Q, SIGMA_N, T_C, T_S, 30, 2))

    def test_no_place_for_a_constant_derived_from_pulls_or_targets(self):
        """Section 2.2: a scale, offset or inflation from pulls or targets voids the gate. The reader takes exactly the written keys."""
        doc = json.loads((ASSETS / "t08-grid-1.configuration.json").read_text(encoding="utf-8"))
        for key, value in (("energy_scale", 1.003), ("position_uncertainty_inflation", 1.07), ("energy_offset_mev", -2.907)):
            with self.subTest(added=key):
                bad = dict(doc, **{key: value})
                with self.assertRaisesRegex(configuration.ConfigurationError, "not allowed"):
                    configuration.from_bytes(json.dumps(bad).encode())
        with self.assertRaises(configuration.ConfigurationError):
            configuration.from_bytes(json.dumps(dict(doc, peaks_kept=3)).encode())
        with self.assertRaises(configuration.ConfigurationError):
            configuration.from_bytes(json.dumps(dict(doc, cell_threshold_mev=-1)).encode())


class Profile(unittest.TestCase):
    def test_cell_integrated_gaussian_against_the_text(self):
        for x, y in ((20.3, 15.7), (0.5, 20.0), (39.9, 0.1)):
            g = profile.cell_profile(x, y, N, N, W)
            for ix, iy in ((int(x), int(y)), (min(int(x) + 1, 39), int(y)), (min(int(x) + 3, 39), max(int(y) - 2, 0)), (max(int(x) - 2, 0), min(int(y) + 1, 39))):
                close(self, float(g[ix, iy]), g_cell(ix, iy, x, y), 1e-12)
        g = profile.cell_profile(20.3, 15.7, N, N, W)
        close(self, float(g.sum()), 1.0, 1e-12)

    def test_far_cells_keep_their_small_value(self):
        """Above the centre the difference is formed from upper tails: no cancellation to zero at 8 widths."""
        g = profile.axis_profile(10.2, N, W)
        expected = 0.5 * (math.erfc((18 - 10.2) / math.sqrt(2)) - math.erfc((19 - 10.2) / math.sqrt(2)))
        close(self, float(g[18]), expected, 1e-10)
        self.assertGreater(float(g[18]), 0.0)

    def test_derivative_against_finite_differences(self):
        h = 1e-6
        for c in (3.3, 20.0, 37.8):
            d = profile.axis_profile_derivative(c, N, W)
            for i in (int(c) - 1, int(c), int(c) + 1):
                fd = (g_axis(i, c + h) - g_axis(i, c - h)) / (2 * h)
                self.assertLess(abs(float(d[i]) - fd), 1e-8)


class Readout(unittest.TestCase):
    def grid(self, n_events=2):
        raw = numpy.zeros((n_events, N, N))
        live = numpy.ones((n_events, N, N), bool)
        sat = numpy.zeros((n_events, N, N), bool)
        return raw, live, sat

    def test_round_trip(self):
        raw, live, sat = self.grid()
        raw[0, 3, 4] = 12.5
        live[1, 20, 20] = False
        raw[1, 20, 20] = numpy.nan
        sat[0, 3, 4] = True
        content = cell_input.cells_bytes(raw, live, sat)
        back = cell_input.read_cells(content)
        self.assertEqual(back.header["events"], 2)
        self.assertTrue(numpy.array_equal(back.live, live) and numpy.array_equal(back.saturated, sat))
        self.assertEqual(float(back.raw[0, 3, 4]), 12.5)
        self.assertTrue(numpy.isnan(back.raw[1, 20, 20]))

    def test_refusals(self):
        raw, live, sat = self.grid()
        good = cell_input.cells_bytes(raw, live, sat)
        with self.assertRaisesRegex(cell_input.InputError, "readout kind 'digital' refused"):
            cell_input.read_cells(cell_input.cells_bytes(raw, live, sat, readout="digital"))
        dead_zero = live.copy()
        dead_zero[0, 5, 5] = False          # raw stays 0.0: a dead cell carrying a value
        with self.assertRaisesRegex(cell_input.InputError, "never zero"):
            cell_input.read_cells(cell_input.cells_bytes(raw, dead_zero, sat))
        nan_live = raw.copy()
        nan_live[0, 1, 1] = numpy.nan
        with self.assertRaisesRegex(cell_input.InputError, "no finite raw"):
            cell_input.read_cells(cell_input.cells_bytes(nan_live, live, sat))
        sat_dead, live_dead, raw_dead = sat.copy(), live.copy(), raw.copy()
        live_dead[0, 6, 6], raw_dead[0, 6, 6], sat_dead[0, 6, 6] = False, numpy.nan, True
        with self.assertRaisesRegex(cell_input.InputError, "dead cell is flagged saturated"):
            cell_input.read_cells(cell_input.cells_bytes(raw_dead, live_dead, sat_dead))
        with self.assertRaisesRegex(cell_input.InputError, "bytes, expected"):
            cell_input.read_cells(good[:-1])
        with self.assertRaisesRegex(cell_input.InputError, "magic"):
            cell_input.read_cells(b"T07HITS1" + good[8:])
        # A truth field in the header (stratum, a seed) is refused: the header holds exactly its keys.
        length = int.from_bytes(good[8:12], "little")
        header = json.loads(good[12:12 + length])
        for key, value in (("stratum", 3), ("role", "truth")):
            doc = dict(header, **{key: value})
            text = json.dumps(doc, sort_keys=True).encode()
            forged = good[:8] + len(text).to_bytes(4, "little") + text + good[12 + length:]
            with self.subTest(forged=key), self.assertRaises(cell_input.InputError):
                cell_input.read_cells(forged)

    def test_header_holds_no_truth_seed_or_generator_field(self):
        raw, live, sat = self.grid(1)
        content = cell_input.cells_bytes(raw, live, sat)
        length = int.from_bytes(content[8:12], "little")
        self.assertEqual(set(json.loads(content[12:12 + length])), {"format", "role", "readout", "nx", "ny", "events", "raw_unit"})


class Chain(unittest.TestCase):
    """R34: raw beside calibrated, each step's payload in chain order; both gain roles."""

    def payload_pair(self, **kw):
        ped, gain = payloads(**kw)
        return cell_input.read_payload(ped), cell_input.read_payload(gain)

    def test_both_gain_roles(self):
        raw = numpy.full((N, N), 7.0)
        raw[2, 3] = 103.0
        live = numpy.ones((N, N), bool)
        sat = numpy.zeros((N, N), bool)
        for operation, expected in (("multiply", 2.5 * (103.0 - 3.0)), ("divide", (103.0 - 3.0) / 2.5)):
            with self.subTest(gain=operation):
                ped, gain = self.payload_pair(pedestal=3.0, gain=2.5, operation=operation)
                chain = cell_chain.apply(raw, live, sat, ped, gain)
                self.assertEqual(float(chain.raw[2, 3]), 103.0)
                self.assertEqual(float(chain.pedestal[2, 3]), 3.0)
                self.assertEqual(float(chain.after_pedestal[2, 3]), 100.0)
                self.assertEqual(float(chain.gain[2, 3]), 2.5)
                self.assertEqual(float(chain.energy[2, 3]), expected)
                record = cell_chain.chain_record(ped, gain)
                self.assertEqual([s["step"] for s in record], ["pedestal", "gain"])
                self.assertEqual([s["order"] for s in record], [1, 2])
                self.assertEqual([s["payload_id"] for s in record], [ped.identity, gain.identity])
                self.assertEqual(record[1]["operation"], operation)
                self.assertIn(operation[:-1] if operation == "divide" else "multiplies", record[1]["role"])

    def test_per_channel_values_by_flat_index(self):
        gains = [1.0] * (N * N)
        gains[2 * N + 3] = 4.0
        ped, gb = payloads(gain=gains)
        p, g = cell_input.read_payload(ped), cell_input.read_payload(gb)
        raw = numpy.ones((N, N))
        chain = cell_chain.apply(raw, numpy.ones((N, N), bool), numpy.zeros((N, N), bool), p, g)
        self.assertEqual(float(chain.energy[2, 3]), 4.0)
        self.assertEqual(float(chain.energy[3, 2]), 1.0)

    def test_saturation_and_dead_cells(self):
        """The readout's flag passes unchanged and the chain never sets one; a dead cell has no value at any step."""
        ped, gain = self.payload_pair(gain=0.5)
        raw = numpy.full((N, N), 900.0)
        live = numpy.ones((N, N), bool)
        live[20, 20] = False
        raw[20, 20] = numpy.nan
        sat = numpy.zeros((N, N), bool)
        sat[10, 10] = True
        chain = cell_chain.apply(raw, live, sat, ped, gain)
        self.assertEqual(int(chain.saturated.sum()), 1)
        self.assertTrue(bool(chain.saturated[10, 10]))
        self.assertEqual(float(chain.energy[10, 10]), 450.0)     # the clipped value goes on through the gain
        for array in (chain.raw, chain.after_pedestal, chain.energy):
            self.assertTrue(numpy.isnan(array[20, 20]))

    def test_refused_chains(self):
        ped, gain = self.payload_pair()
        other_ped = cell_input.read_payload(payloads(pedestal=1.0)[0])
        with self.assertRaisesRegex(cell_input.InputError, "another upstream chain"):
            cell_chain.chain_record(other_ped, gain)
        with self.assertRaisesRegex(cell_input.InputError, "chain order"):
            cell_chain.chain_record(gain, ped)
        with self.assertRaisesRegex(cell_input.InputError, "positive"):
            cell_input.read_payload(payloads(gain=0.0)[1])
        bad = json.loads(payloads()[1])
        bad["operation"] = "add"
        with self.assertRaises(cell_input.InputError):
            cell_input.read_payload(json.dumps(bad).encode())
        bad = json.loads(payloads()[0])
        bad["value"] = float("nan")
        with self.assertRaises(cell_input.InputError):
            cell_input.read_payload(json.dumps(bad).encode())


class SingleShower(unittest.TestCase):
    def test_one_component_one_object_as_the_text(self):
        grid = image([(2000.0, 20.3, 15.7)])
        comps = components_of(grid)
        self.assertEqual(len(comps), 1)
        e = {c: grid[c[0]][c[1]] for c in comps[0]}
        expected = text_one_peak(comps[0], e, ring_of(comps[0], grid))
        result = run(grid)
        self.assertEqual(len(result.components), 1)
        self.assertEqual(result.components[0].channels, [flat(c) for c in comps[0]])
        self.assertEqual(len(result.objects), 1)
        cluster = result.objects[0]
        self.assertEqual(cluster.kind, "one-peak")
        self.assertEqual(cluster.peak_channel, 20 * N + 15)
        for got, want in zip((cluster.energy, cluster.x, cluster.y, cluster.sigma_energy ** 2, cluster.sigma_x ** 2, cluster.sigma_y ** 2), expected):
            close(self, got, want, 1e-9)
        self.assertEqual({f for _, f in cluster.members}, {1.0})
        close(self, result.event_sum_sigma ** 2, Q * result.clustered_sum + len(comps[0]) * SIGMA_N ** 2, 1e-12)
        self.assertEqual(cluster.energy_bound, "estimate")

    def test_ring_term_is_used(self):
        """The one-peak position variance includes the ring: dropping it (a sum over kept cells alone) gives another number."""
        grid = image([(300.0, 20.3, 15.7)])
        comp = components_of(grid)[0]
        e = {c: grid[c[0]][c[1]] for c in comp}
        with_ring = text_one_peak(comp, e, ring_of(comp, grid))
        without = text_one_peak(comp, e, [])
        cluster = run(grid).objects[0]
        close(self, cluster.sigma_x ** 2, with_ring[4], 1e-9)
        self.assertGreater(abs(cluster.sigma_x ** 2 - without[4]), 1e-6 * with_ring[4])


class TwoOverlappingShowers(unittest.TestCase):
    def setUp(self):
        self.grid = image([(2000.0, 18.4, 20.2), (1500.0, 21.9, 20.6)])
        self.comps = components_of(self.grid)
        self.result = run(self.grid)

    def test_two_peaks_shared_as_the_text(self):
        self.assertEqual(len(self.comps), 1)
        comp = self.comps[0]
        e = {c: self.grid[c[0]][c[1]] for c in comp}
        self.assertEqual(self.result.components[0].peaks, [18 * N + 20, 21 * N + 20])
        amps, centres, fractions = text_two_peaks(comp, e, [(18, 20), (21, 20)])
        objs = self.result.objects
        self.assertEqual([o.kind for o in objs], ["two-peak", "two-peak"])
        for k in range(2):
            close(self, objs[k].energy, amps[k], 1e-9)
            close(self, objs[k].x, centres[k][0], 1e-9)
            close(self, objs[k].y, centres[k][1], 1e-9)
            for i, (channel, f) in enumerate(objs[k].members):
                self.assertEqual(channel, flat(comp[i]))
                self.assertLess(abs(f - fractions[i][k]), 1e-9)

    def test_exactly_thirty_iterations_no_early_stop(self):
        """At d = 2.9 the sharing still moves at iteration 30 (by about 7e-7 in A_1): the recipe equals 30 iterations of the text to
        rounding, and differs from 29 or 31."""
        global ITERATIONS
        grid = image([(2000.0, 18.7, 20.2), (1500.0, 21.6, 20.6)])
        comp = components_of(grid)[0]
        e = {c: grid[c[0]][c[1]] for c in comp}
        result = run(grid)
        peaks = [divmod(p, N) for p in result.components[0].peaks]
        self.assertEqual(len(peaks), 2)
        saved = ITERATIONS
        try:
            by_count = {}
            for count in (29, 30, 31):
                ITERATIONS = count
                by_count[count] = text_two_peaks(comp, e, peaks)[0][0]
        finally:
            ITERATIONS = saved
        close(self, result.objects[0].energy, by_count[30], 1e-12)
        for count in (29, 31):
            self.assertGreater(abs(result.objects[0].energy - by_count[count]), 1e-9 * by_count[30])

    def test_fractions_are_those_of_the_thirtieth_iteration(self):
        """O-last (coordinator's ruling): the kept f are those that gave the final A_k and c_k. They equal the text's iteration-30
        f to 1e-12, and differ by more than 1e-9 from f recomputed once more from the final A and c, the rejected alternative."""
        grid = image([(2000.0, 18.7, 20.2), (1500.0, 21.6, 20.6)])
        comp = components_of(grid)[0]
        e = {c: grid[c[0]][c[1]] for c in comp}
        result = run(grid)
        peaks = [divmod(p, N) for p in result.components[0].peaks]
        amps, centres, fractions = text_two_peaks(comp, e, peaks)
        recomputed = []
        for c in comp:
            w = [amps[k] * g_cell(c[0], c[1], *centres[k]) for k in range(2)]
            recomputed.append(w[0] / (w[0] + w[1]))
        kept = [f for _, f in result.objects[0].members]
        self.assertLess(max(abs(a - b[0]) for a, b in zip(kept, fractions)), 1e-12)
        self.assertGreater(max(abs(a - b) for a, b in zip(kept, recomputed)), 1e-9)

    def test_fractions_sum_to_one_and_energy_is_conserved(self):
        objs = self.result.objects
        for (c0, f0), (c1, f1) in zip(objs[0].members, objs[1].members):
            self.assertEqual(c0, c1)
            self.assertLess(abs(f0 + f1 - 1.0), 1e-12)
        close(self, objs[0].energy + objs[1].energy, self.result.clustered_sum, 1e-12)

    def test_fisher_uncertainty_as_the_text(self):
        comp = self.comps[0]
        objs = self.result.objects
        variances = text_fisher_variances(comp, [o.energy for o in objs], [[o.x, o.y] for o in objs])
        got = [objs[0].sigma_energy ** 2, objs[1].sigma_energy ** 2, objs[0].sigma_x ** 2, objs[0].sigma_y ** 2,
               objs[1].sigma_x ** 2, objs[1].sigma_y ** 2]
        for g, v in zip(got, variances):
            close(self, g, float(v), 1e-5)

    def test_singular_fisher_matrix_is_a_status_not_a_number(self):
        cells_ix, cells_iy = numpy.divmod(numpy.array([flat(c) for c in self.comps[0]]), N)
        status, variances = clustering.fisher_uncertainty(cells_ix, cells_iy, numpy.array([1000.0, 1000.0]),
                                                          numpy.array([20.0, 20.0]), numpy.array([20.0, 20.0]), CFG)
        self.assertEqual((status, variances), ("singular-fisher", None))

    def test_undefined_uncertainty_keeps_neither_object(self):
        """F3 (coordinator's ruling, as the reference clusterer): a singular Fisher matrix, or a non-positive variance of either
        object, keeps neither object; the component records the status for both, its cells stay in the event sum with fractions
        summing to 0, and that is reported apart, not as a double count."""
        from unittest import mock
        for status in ("singular-fisher", "non-positive-variance"):
            with self.subTest(status=status), mock.patch.object(clustering, "fisher_uncertainty", return_value=(status, None)):
                result = run(self.grid)
                self.assertEqual(result.objects, [])
                self.assertEqual(result.components[0].failure, status)
                close(self, result.clustered_sum, sum(self.grid[c[0]][c[1]] for c in self.comps[0]), 1e-12)
                ped, gain = (cell_input.read_payload(b) for b in payloads())
                chain = cell_chain.apply(as_array(self.grid), numpy.ones((N, N), bool), numpy.zeros((N, N), bool), ped, gain)
                doc = product.event_document(0, chain, result, N)
                self.assertEqual(product.double_count_defects(doc), [])
                self.assertEqual(product.failed_components(doc), [(0, status, len(self.comps[0]))])

    def test_non_positive_variance_is_detected(self):
        """The Fisher step itself returns non-positive-variance when an inverse diagonal is not positive: the 6 x 6 matrix of a
        component is replaced, through the profile, by one whose inverse has a negative diagonal entry."""
        from unittest import mock
        cells_ix, cells_iy = numpy.divmod(numpy.array([flat(c) for c in self.comps[0]]), N)
        bad = numpy.eye(6)
        bad[0, 0] = -1.0
        with mock.patch.object(clustering.linalg, "cho_solve", return_value=bad):
            status, variances = clustering.fisher_uncertainty(cells_ix, cells_iy, numpy.array([2000.0, 1500.0]),
                                                              numpy.array([18.4, 21.9]), numpy.array([20.2, 20.6]), CFG)
        self.assertEqual((status, variances), ("non-positive-variance", None))

    def test_zero_denominator_is_a_recorded_failure(self):
        """A cell neither profile reaches (39 widths away underflows to 0) leaves f undefined: no number is made up."""
        cells_ix, cells_iy = numpy.array([0, 0, 39]), numpy.array([0, 1, 39])
        shared = clustering.share_two_peaks(cells_ix, cells_iy, numpy.array([20.0, 20.0, 20.0]), numpy.array([0, 0]), numpy.array([0, 1]), CFG)
        self.assertIsNone(shared)


class Edge(unittest.TestCase):
    def test_shower_at_the_grid_edge(self):
        grid = image([(2000.0, 0.5, 20.3)])
        comp = components_of(grid)[0]
        self.assertEqual(min(c[0] for c in comp), 0)
        e = {c: grid[c[0]][c[1]] for c in comp}
        ring = ring_of(comp, grid)
        self.assertTrue(all(c[0] >= 0 for c in ring))
        expected = text_one_peak(comp, e, ring)
        result = run(grid)
        self.assertEqual(len(result.objects), 1)
        cluster = result.objects[0]
        self.assertEqual(cluster.peak_channel, 0 * N + 20)
        for got, want in zip((cluster.energy, cluster.x, cluster.y, cluster.sigma_energy ** 2, cluster.sigma_x ** 2, cluster.sigma_y ** 2), expected):
            close(self, got, want, 1e-9)
        self.assertLess(cluster.energy, 2000.0 * 0.70)      # E Phi(0.5) = 0.6915 E is all the grid holds


class DeadCellInShower(unittest.TestCase):
    def setUp(self):
        self.grid = image([(2000.0, 20.5, 20.5)])
        self.grid[20][20] = None
        self.result = run(self.grid)

    def test_dead_cell_is_never_in_a_cluster(self):
        dead = 20 * N + 20
        for comp in self.result.components:
            self.assertNotIn(dead, comp.channels)
        for cluster in self.result.objects:
            self.assertNotIn(dead, [c for c, _ in cluster.members])

    def test_dead_cell_in_the_ring_is_left_out(self):
        """One-peak position variance: a dead cell in the ring has no value and is left out (section 7.1); read as zero it would
        enter the ring and change sigma_x. Dead cells are not counted as unclustered cells either."""
        grid = image([(300.0, 20.5, 20.5)])
        comp = components_of(grid)[0]
        ring = ring_of(comp, grid)
        dead = ring[0]
        grid[dead[0]][dead[1]] = None
        comp = components_of(grid)[0]
        e = {c: grid[c[0]][c[1]] for c in comp}
        left_out = text_one_peak(comp, e, ring_of(comp, grid))
        as_zero = text_one_peak(comp, e, ring)
        result = run(grid)
        self.assertEqual(len(result.objects), 1)
        close(self, result.objects[0].sigma_x ** 2, left_out[4], 1e-9)
        close(self, result.objects[0].sigma_y ** 2, left_out[5], 1e-9)
        self.assertGreater(abs(left_out[4] - as_zero[4]) + abs(left_out[5] - as_zero[5]), 1e-9 * left_out[4])
        self.assertEqual(result.unclustered_cells, N * N - 1 - len(comp))

    def test_hole_gives_two_peaks_by_the_rules(self):
        """The four edge neighbours of the hole are local maxima (the dead cell is not compared); in flat order (19,20) is kept,
        (20,19) and (20,21) are adjacent to it and dropped, (21,20) is kept: two peaks, so two objects share the component."""
        comps = components_of(self.grid)
        self.assertEqual(len(comps), 1)
        self.assertEqual(self.result.components[0].candidates, [19 * N + 20, 20 * N + 19, 20 * N + 21, 21 * N + 20])
        self.assertEqual(sorted(self.result.components[0].peaks), [19 * N + 20, 21 * N + 20])
        e = {c: self.grid[c[0]][c[1]] for c in comps[0]}
        amps, centres, _ = text_two_peaks(comps[0], e, [(19, 20), (21, 20)])
        objs = self.result.objects
        self.assertEqual(len(objs), 2)
        close(self, objs[0].energy + objs[1].energy, sum(e.values()), 1e-12)
        close(self, objs[0].energy, amps[0], 1e-9)


class ThresholdsAndPeaks(unittest.TestCase):
    def blank(self):
        return [[0.0] * N for _ in range(N)]

    def test_below_threshold_neighbour_and_seed_threshold(self):
        grid = self.blank()
        grid[10][10] = 12.0
        grid[10][11] = 0.59        # below T_c: not in the component
        grid[11][10] = 0.6         # at T_c: in
        grid[30][30] = 9.99        # a component with no seed: not kept
        grid[30][31] = 5.0
        grid[5][30] = 10.0         # exactly T_s: kept
        result = run(grid)
        self.assertEqual([c.channels for c in result.components], [[5 * N + 30], [10 * N + 10, 11 * N + 10]])
        close(self, result.clustered_sum, 22.6, 1e-12)
        close(self, result.unclustered_sum, 0.59 + 9.99 + 5.0, 1e-12)
        self.assertEqual(result.unclustered_cells, N * N - 3)

    def test_adjacent_tie_is_dropped_in_flat_order(self):
        grid = self.blank()
        grid[10][10] = grid[10][11] = 50.0
        result = run(grid)
        self.assertEqual(result.components[0].candidates, [10 * N + 10, 10 * N + 11])
        self.assertEqual(result.components[0].peaks, [10 * N + 10])
        self.assertEqual([o.kind for o in result.objects], ["one-peak"])

    def test_diagonal_is_adjacent(self):
        grid = self.blank()
        grid[10][10] = grid[11][11] = 50.0
        result = run(grid)
        self.assertEqual([c.channels for c in result.components], [[10 * N + 10, 11 * N + 11]])   # 8-connected: one component
        self.assertEqual(result.components[0].peaks, [10 * N + 10])

    def test_peak_test_reads_all_eight_neighbours(self):
        """F1: (10,10) beats its four edge neighbours but loses to the diagonal (11,11): it is not a candidate. A 4-neighbour peak
        test would make it one."""
        grid = self.blank()
        grid[10][10], grid[11][11] = 50.0, 60.0
        grid[10][11] = grid[11][10] = 5.0
        result = run(grid)
        self.assertEqual(result.components[0].candidates, [11 * N + 11])
        self.assertEqual(result.components[0].peaks, [11 * N + 11])

    def test_two_highest_ties_to_lower_index(self):
        grid = self.blank()
        for ix in range(10, 19):
            grid[ix][10] = 9.0                      # a ridge below T_s joining the peaks into one component
        grid[10][10], grid[14][10], grid[18][10] = 40.0, 60.0, 40.0
        result = run(grid)
        self.assertEqual(result.components[0].candidates, [10 * N + 10, 14 * N + 10, 18 * N + 10])
        self.assertEqual(result.components[0].peaks, [14 * N + 10, 10 * N + 10])
        # Every cell lies in one row with both centres at y = 10.5: d mu/d y is 0 on every cell, so the Fisher matrix is singular
        # and, by the ruled rule (F3), neither object is kept.
        self.assertEqual((len(result.objects), result.components[0].failure), (0, "singular-fisher"))


class NoCellCountedTwice(unittest.TestCase):
    """The sheet's stop: a cell counted twice. Checked on a written and read product, and caught when planted."""

    def event_doc(self):
        grid = image([(2000.0, 10.4, 10.2), (1800.0, 13.6, 10.5), (900.0, 30.2, 30.7)])
        e = as_array(grid)
        ped, gain = (cell_input.read_payload(b) for b in payloads())
        chain = cell_chain.apply(e, numpy.ones((N, N), bool), numpy.zeros((N, N), bool), ped, gain)
        result = clustering.cluster_event(chain.energy, chain.live, chain.saturated, CFG)
        return product.event_document(0, chain, result, N), result

    def test_honest_event_has_no_defect(self):
        doc, result = self.event_doc()
        self.assertEqual(len(result.components), 2)
        self.assertEqual([o.kind for o in result.objects], ["two-peak", "two-peak", "one-peak"])
        self.assertEqual(product.double_count_defects(doc), [])

    def test_planted_double_counts_are_caught(self):
        doc, _ = self.event_doc()
        raised = copy.deepcopy(doc)
        raised["objects"][0]["members"][0][1] += 0.25
        raised["objects"][0]["energy"] += 0.25 * raised["cells"][0][5]    # the object's energy follows, so only the sum can see it
        self.assertTrue(any("fractions sum to" in d for d in product.double_count_defects(raised)))
        twice = copy.deepcopy(doc)
        stolen = twice["objects"][2]["members"][0]
        twice["objects"][0]["members"].append(list(stolen))
        twice["objects"][0]["members"].sort()
        self.assertTrue(any("components" in d for d in product.double_count_defects(twice)))
        object_energy = copy.deepcopy(doc)
        object_energy["objects"][2]["energy"] += 1.0
        self.assertTrue(any("object 2" in d for d in product.double_count_defects(object_energy)))
        moved = copy.deepcopy(doc)
        moved["objects"][0]["energy"] += 1.0
        moved["objects"][1]["energy"] -= 1.0
        found = product.double_count_defects(moved)
        self.assertTrue(any("object 0" in d for d in found) and any("object 1" in d for d in found))
        inflated = copy.deepcopy(doc)
        inflated["event_sum"]["energy"] += 1.0
        self.assertTrue(product.double_count_defects(inflated))


class Saturation(unittest.TestCase):
    def test_clipped_cells_flag_object_and_bound(self):
        grid = image([(8000.0, 20.5, 20.5)])
        e = as_array(grid)
        sat = e >= 400.0
        e = numpy.minimum(e, 400.0)
        self.assertGreater(int(sat.sum()), 0)
        result = clustering.cluster_event(e, numpy.ones((N, N), bool), sat, CFG)
        self.assertTrue(result.event_sum_saturated)
        for cluster in result.objects:
            clipped = any(sat.ravel()[c] and f > 0 for c, f in cluster.members)
            self.assertEqual(cluster.saturated, clipped)
            self.assertEqual(cluster.energy_bound, "lower-bound" if clipped else "estimate")
        self.assertTrue(any(o.saturated for o in result.objects))

    def test_one_peak_object_with_a_clipped_cell(self):
        """3 GeV at a cell centre clips the central cell only (0.1466 E = 440 MeV; neighbours 278 MeV): one peak, flagged."""
        e = as_array(image([(3000.0, 20.5, 20.5)]))
        sat = e >= 400.0
        self.assertEqual(int(sat.sum()), 1)
        result = clustering.cluster_event(numpy.minimum(e, 400.0), numpy.ones((N, N), bool), sat, CFG)
        self.assertEqual([o.kind for o in result.objects], ["one-peak"])
        self.assertTrue(result.objects[0].saturated)
        self.assertEqual(result.objects[0].energy_bound, "lower-bound")
        unflagged = clustering.cluster_event(numpy.minimum(e, 400.0), numpy.ones((N, N), bool), numpy.zeros((N, N), bool), CFG)
        self.assertEqual((unflagged.objects[0].saturated, unflagged.objects[0].energy_bound), (False, "estimate"))


class ProductFormat(unittest.TestCase):
    def make(self, n_events=3):
        rng_free = [image([(2000.0, 12.3, 20.1)]), image([(2000.0, 18.4, 20.2), (1500.0, 21.9, 20.6)]), image([(150.0, 30.5, 8.5)])]
        raw = numpy.array([as_array(g) for g in rng_free[:n_events]])
        live = numpy.ones(raw.shape, bool)
        raw[1, 5, 5] = numpy.nan
        live[1, 5, 5] = False
        sat = numpy.zeros(raw.shape, bool)
        cells = cell_input.read_cells(cell_input.cells_bytes(raw, live, sat))
        ped, gain = (cell_input.read_payload(b) for b in payloads(pedestal=0.0, gain=1.0))
        chain = cell_chain.chain_record(ped, gain)
        header = product.header_document("hand-made-1", N, N, cells.sha256, cells.events, CFG.sha256, chain)
        stream = io.StringIO()
        writer = product.Writer(stream, header)
        for i in range(cells.events):
            c = cell_chain.apply(cells.raw[i], cells.live[i], cells.saturated[i], ped, gain)
            writer.event(product.event_document(i, c, clustering.cluster_event(c.energy, c.live, c.saturated, CFG), N))
        writer.finish()
        return stream.getvalue()

    def test_round_trip_is_byte_equal(self):
        text = self.make()
        read = product.read_text(text)
        self.assertEqual(product.product_text(read), text)
        self.assertEqual(read.header["energy_kind"], ENERGY_KIND)
        self.assertEqual(read.header["recipe"], RECIPE)
        self.assertEqual(read.events[1]["dead_channels"], [5 * N + 5])
        self.assertEqual([len(e["objects"]) for e in read.events], [1, 2, 1])
        for ev in read.events:
            self.assertEqual(product.double_count_defects(ev), [])

    def test_refuses_malformed_or_incomplete(self):
        text = self.make()
        lines = text.split("\n")[:-1]
        header, events, end = json.loads(lines[0]), [json.loads(x) for x in lines[1:-1]], lines[-1]

        def build(h=None, evs=None, tail=None):
            return "\n".join([product.dumps(h or header)] + [product.dumps(e) for e in (evs or events)] + [tail or end]) + "\n"

        cases = {
            "no end line": "\n".join(lines[:-1]) + "\n",
            "unfinished last line": text[:-1],
            "text after the end": text + "{}\n",
            "missing event": "\n".join([lines[0]] + lines[2:]) + "\n",
            "end line with another count": build(tail=product.dumps({"end": product.FORMAT, "events": len(events) - 1})),
            "end line of another format": build(tail=product.dumps({"end": "calo-cluster-product/0", "events": len(events)})),
            "incident energy": build(h=dict(header, energy_kind="incident-energy")),
            "unknown header key": build(h=dict(header, pull_scale=1.01)),
            "chain reordered": build(h=dict(header, chain=list(reversed(header["chain"])))),
            "non-finite number": text.replace('"energy":', '"energy":NaN,"x_":', 1),
        }
        broken = copy.deepcopy(events)
        broken[0]["cells"][0][5] += 1e-6           # e_c no longer follows from raw, pedestal and gain
        cases["chain arithmetic"] = build(evs=broken)
        broken = copy.deepcopy(events)
        broken[1]["objects"][0]["members"][0][1] = 1.5
        cases["fraction above one"] = build(evs=broken)
        broken = copy.deepcopy(events)
        broken[0]["objects"][0]["members"].append([39 * N + 39, 1.0])
        cases["member outside its component"] = build(evs=broken)
        broken = copy.deepcopy(events)
        broken[1]["cells"].append([5 * N + 5, 0.0, 0.0, 0.0, 1.0, 0.0, 0, 0])
        broken[1]["cells"].sort()
        cases["dead cell with a value"] = build(evs=broken)
        broken = copy.deepcopy(events)
        broken[0], broken[1] = broken[1], broken[0]
        cases["events out of order"] = build(evs=broken)
        broken = copy.deepcopy(events)
        broken[0]["objects"][0]["saturated"] = True
        cases["saturation flag without a clipped cell"] = build(evs=broken)
        broken = copy.deepcopy(events)
        broken[0]["event_sum"]["energy"] += 1.0
        cases["event sum not the clustered sum"] = build(evs=broken)
        broken = copy.deepcopy(events)
        broken[0]["unclustered_sum"] += 1.0
        cases["clustered plus unclustered not the input"] = build(evs=broken)
        for name, bad in cases.items():
            with self.subTest(defect=name), self.assertRaises(product.ProductError):
                product.read_text(bad)


class RecipeImportsNoGenerator(unittest.TestCase):
    """Section 3.1 and Freeze A amendment 1: a recipe never links or imports a generator, seed code or truth readers."""
    FORBIDDEN_MODULES = ("gen_t08_grid", "gen_t09_sphere", "check_generators", "t08_fixture_files", "t08_readings", "fixture_tools",
                         "importlib", "numpy.random", "runpy", "subprocess", "pickle", "multiprocessing", "imp", "zipimport")
    FORBIDDEN_CALLS = ("spec_from_file_location", "__import__", "exec", "eval", "compile", "SeedSequence", "default_rng", "read_truth",
                       "run_path", "run_module", "import_module", "system", "popen", "Popen", "execv", "execl", "spawnv")
    FORBIDDEN_NUMPY = ("random", "load", "loadtxt", "fromfile", "genfromtxt")   # numpy.load reads an npz: the truth file's format
    PLANTED = {"import runpy": "import runpy\nrunpy.run_path('gen_t08_grid.py')\n",
               "subprocess": "import subprocess\nsubprocess.run(['python', 'gen_t08_grid.py'])\n",
               "os.system": "import os\nos.system('python gen_t08_grid.py')\n",
               "numpy.load": "import numpy\nnumpy.load('stratum.truth.npz')\n",
               "numpy.load by name": "from numpy import load\nload('stratum.truth.npz')\n",
               "importlib": "import importlib\nimportlib.import_module('gen_t08_grid')\n",
               "__import__": "__import__('gen_t08_grid')\n",
               "exec": "exec(open('gen_t08_grid.py').read())\n",
               "relative import of fixture_tools": "from . import fixture_tools\n",
               "from-import of a generator": "from gen_t08_grid import event\n",
               "pickle": "import pickle\n",
               "multiprocessing": "import multiprocessing\n",
               "numpy.random": "import numpy.random\n",
               "default_rng": "import numpy as np\nnp.random.default_rng(1)\n"}

    def findings_in(self, text):
        tree = ast.parse(text)
        found = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found += [a.name for a in node.names if a.name.startswith(self.FORBIDDEN_MODULES)]
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = [a.name for a in node.names]
                if module.startswith(self.FORBIDDEN_MODULES) or any(n.startswith(self.FORBIDDEN_MODULES) for n in names) \
                        or (module == "numpy" and any(n in self.FORBIDDEN_NUMPY for n in names)):
                    found.append(module or ",".join(names))
            elif isinstance(node, ast.Attribute):
                if node.attr in self.FORBIDDEN_CALLS:
                    found.append(node.attr)
                elif node.attr in self.FORBIDDEN_NUMPY and isinstance(node.value, ast.Name) and node.value.id in ("numpy", "np"):
                    found.append(f"numpy.{node.attr}")
            elif isinstance(node, ast.Name) and node.id in self.FORBIDDEN_CALLS:
                found.append(node.id)
        return found

    def findings(self, path):
        return self.findings_in(path.read_text(encoding="utf-8"))

    def recipe_files(self):
        files = sorted((ASSETS / "calo_recipe").rglob("*.py")) + [ASSETS / "calo_cluster.py"]
        self.assertGreaterEqual(len(files), 8)
        return files

    def test_each_planted_form_is_caught(self):
        """Every form the scan covers fails on a planted case: the scan is a review rule, not a sandbox (decisions.md, T07 stage 1)."""
        for name, text in self.PLANTED.items():
            with self.subTest(planted=name):
                self.assertTrue(self.findings_in(text), name)

    def test_recipe_imports_no_generator_seed_or_truth_code(self):
        for path in self.recipe_files():
            with self.subTest(file=path.name):
                self.assertEqual(self.findings(path), [])

    def test_the_scan_finds_them_where_they_are(self):
        """Control: the scoring-side harness loads the generator by importlib, and the scan sees it there."""
        self.assertIn("spec_from_file_location", self.findings(ASSETS / "fixture_tools" / "t08_fixture_files.py"))
        self.assertIn("t08_fixture_files", self.findings(ASSETS / "fixture_tools" / "t08_readings.py"))

    def test_harness_refuses_a_generator_that_is_not_the_frozen_one(self):
        with tempfile.TemporaryDirectory() as folder:
            fake = Path(folder) / "gen_t08_grid.py"
            fake.write_text("GENERATOR = 't08-grid/1'\n", encoding="utf-8")
            with self.assertRaisesRegex(t08_fixture_files.FixtureError, "not the frozen"):
                t08_fixture_files.load_generator(fake)


class CommandLine(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "calo_cluster.py"), *args], capture_output=True, text=True,
                              timeout=120)

    def test_reconstruct_then_check_product(self):
        raw = numpy.array([as_array(image([(2000.0, 12.3, 20.1)])), as_array(image([(2000.0, 18.4, 20.2), (1500.0, 21.9, 20.6)]))])
        live = numpy.ones(raw.shape, bool)
        sat = numpy.zeros(raw.shape, bool)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "c.cells").write_bytes(cell_input.cells_bytes(raw, live, sat))
            ped, gain = payloads()
            (folder / "p.json").write_bytes(ped)
            (folder / "g.json").write_bytes(gain)
            args = ["reconstruct", "--cells", str(folder / "c.cells"), "--pedestal-payload", str(folder / "p.json"), "--gain-payload",
                    str(folder / "g.json"), "--product", str(folder / "out.jsonl"), "--product-id", "hand-made-cli"]
            p = self.run_cli(*args)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual((out["status"], out["events"], out["objects"], out["energy_kind"]), ("ok", 2, 3, ENERGY_KIND))
            p = self.run_cli("check-product", "--product", str(folder / "out.jsonl"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            self.assertEqual(json.loads(p.stdout)["double_count_defects"], 0)
            # refusals: a digital readout, a gain bound on another pedestal, a missing file; no product written
            (folder / "d.cells").write_bytes(cell_input.cells_bytes(raw, live, sat, readout="digital"))
            (folder / "g2.json").write_bytes(payloads(against=["0" * 64])[1])
            for name, swap in (("digital", ("c.cells", "d.cells")), ("other chain", ("g.json", "g2.json")), ("missing", ("c.cells", "none.cells"))):
                with self.subTest(refused=name):
                    bad = [a.replace(swap[0], swap[1]) if a.endswith(swap[0]) else a for a in args]
                    bad[bad.index("--product") + 1] = str(folder / f"{name}.jsonl")
                    p = self.run_cli(*bad)
                    self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                    self.assertEqual(json.loads(p.stdout)["status"], "rejected")
                    self.assertFalse((folder / f"{name}.jsonl").exists())
            (folder / "cut.jsonl").write_text("\n".join((folder / "out.jsonl").read_text().split("\n")[:-2]) + "\n")
            p = self.run_cli("check-product", "--product", str(folder / "cut.jsonl"))
            self.assertEqual(p.returncode, 2)

    def test_tool_contract_passes(self):
        doc = json.loads((ROOT / "contracts" / "tool_contracts" / "calo_cluster.json").read_text(encoding="utf-8"))
        res = tool_contract.check(doc)
        self.assertEqual(res["status"], "pass", res["findings"])


class ScoringSide(unittest.TestCase):
    """The readings' own arithmetic on hand-made inputs: matching, interpolation, the reference parser."""

    def test_matching_primary_split_merge(self):
        deposit = numpy.zeros((2, N * N))
        deposit[0, 10] = 100.0
        deposit[1, 11] = 100.0
        deposit[1, 12] = 30.0
        event = {"objects": [{"members": [[10, 1.0], [11, 0.4]], "energy": 140.0, "uncertainty_status": "ok"},
                             {"members": [[11, 0.6], [12, 1.0]], "energy": 90.0, "uncertainty_status": "ok"}]}
        m = t08_readings.match_event(event, deposit.reshape(2, N, N), 2)
        self.assertEqual(m["matched"], [[0], [1]])
        self.assertEqual(m["primary"], [0, 1])
        self.assertFalse(m["merged"])
        merged = {"objects": [{"members": [[10, 1.0], [11, 1.0], [12, 1.0]], "energy": 230.0, "uncertainty_status": "ok"}]}
        m = t08_readings.match_event(merged, deposit.reshape(2, N, N), 2)
        self.assertTrue(m["merged"])
        self.assertEqual(m["primary"], [None, 0])        # shower 1 supplies 130 of 230: more than half
        event["objects"][1]["uncertainty_status"] = "singular-fisher"
        self.assertEqual(t08_readings.match_event(event, deposit.reshape(2, N, N), 2)["primary"], [0, None])

    def test_interpolation_is_exact_at_nodes_and_refuses_outside(self):
        table = {(250.0, 3.0): 1.0, (250.0, 4.0): 2.0, (1000.0, 3.0): 3.0, (1000.0, 4.0): 4.0}
        self.assertEqual(t08_readings.bilinear(table, 250.0, 3.0), 1.0)
        close(self, t08_readings.bilinear(table, 500.0, 3.5), 1.5 + 0.5 * 2.0, 1e-12)   # ln 500 is halfway in ln E
        with self.assertRaises(t08_readings.ReadingError):
            t08_readings.bilinear(table, 2000.0, 3.5)

    def test_reference_parser(self):
        text = "\n".join(["pair d  3.00 E     250.0 n 12000 none 0.0 merged 0.0 eff 1.0 closed 1.0 b_near    3.733 se  0.092 sd 1 model 1",
                          "   total: n 1", "   b_far    2.100 se  0.2 sd 1 model 1", "CONST b_iso 2.907", "CONST b_dead 2.855",
                          "CONST b_sat 3.485"] + [f"CONST b_edge({t}) 1.{i}" for i, t in enumerate(("0.5", "1.0", "1.5", "2.0"))])
        ref = t08_readings.parse_reference(text)
        self.assertEqual((ref["iso"], ref["far"][(250.0, 3.0)], ref["near"][(250.0, 3.0)], ref["edge"][2.0]), (2.907, 2.1, 3.733, 1.3))


class HandMadeGenerator:
    """A stand-in with the frozen generator's interface, written here: closed-form images, no random draw. Not t08-grid/1."""
    N_CELLS, GENERATOR, CLIP_MEV = N, "hand-made", 400.0

    def __init__(self, showers_per_event, fixture="main", extra=None, separation=None):
        self.showers_per_event, self.fixture, self.extra, self.separation = showers_per_event, fixture, extra or {}, separation

    @staticmethod
    def cell_profile(x, y):
        return numpy.array([[g_cell(ix, iy, x, y) for iy in range(N)] for ix in range(N)])

    def event(self, fixture, block, stratum, index):
        showers = self.showers_per_event[index]
        deposit = numpy.stack([e * self.cell_profile(x, y) for e, x, y in showers])
        value = deposit.sum(axis=0)
        n = len(showers)
        separation = self.separation or ("iso" if n == 1 else "far")
        d = None if n == 1 else math.dist(showers[0][1:], showers[1][1:])
        return {"data": {"raw": value.copy(), "pedestal": 0.0, "gain": 1.0, "live": numpy.ones((N, N), bool),
                         "saturated": numpy.zeros((N, N), bool)},
                "truth": {"energy_mev": showers[0][0], "energy_bin": 2, "separation": separation,
                          "showers": numpy.array([[x, y] for _, x, y in showers]), "d": d, "azimuth": None if n == 1 else 0.0,
                          "t": self.extra.get("t"), "f_dead": self.extra.get("f_dead"), "deposit": deposit}}


class HarnessAndReadingsOnHandMadeEvents(unittest.TestCase):
    """The scoring-side path of the job, end to end, on hand-made events: harness files, recipe CLI, readings. No generator runs."""
    REF = {"iso": 2.907, "dead": 2.855, "sat": 3.485, "edge": {0.5: 1.5, 1.0: 1.6, 1.5: 1.7, 2.0: 1.9},
           "far": {(e, d): 2.0 for e in (1000.0, 4000.0) for d in (3.0, 8.0)}, "near": {(e, d): 3.5 for e in (1000.0, 4000.0) for d in (1.5, 3.0)}}

    def run_stratum(self, showers, folder, stem, fixture="main", **kw):
        generator = HandMadeGenerator(showers, fixture, **kw)
        files = t08_fixture_files.stratum_files(generator, fixture, 1, 6, len(showers), folder, stem)
        self.assertEqual(set(files), {"cells", "pedestal", "gain", "truth"})
        cells = cell_input.read_file(files["cells"]["path"], cell_input.read_cells, "cells")
        self.assertEqual(set(cells.header), cell_input.HEADER_KEYS)
        gain = cell_input.read_file(files["gain"]["path"], cell_input.read_payload, "gain")
        pedestal = cell_input.read_file(files["pedestal"]["path"], cell_input.read_payload, "pedestal")
        self.assertEqual((gain.operation, gain.derived_against), ("multiply", (pedestal.identity,)))
        out = Path(folder) / f"{stem}.jsonl"
        p = subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "calo_cluster.py"), "reconstruct", "--cells", files["cells"]["path"],
                            "--pedestal-payload", files["pedestal"]["path"], "--gain-payload", files["gain"]["path"], "--product", str(out),
                            "--product-id", stem], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        header, truth = t08_fixture_files.read_truth(files["truth"]["path"])
        self.assertEqual(header["cells_sha256"], cells.sha256)
        with self.assertRaises(t08_fixture_files.FixtureError):
            t08_fixture_files.read_truth(Path(folder) / f"{stem}.pedestal.json")
        return t08_readings.readings(product.read_product(out), header, truth, self.REF, stem)

    def test_iso_and_far_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            lines, defects = self.run_stratum([[(2000.0, 12.3, 20.1)], [(1500.0, 25.6, 14.2)]], folder, "iso")
            self.assertEqual(defects, 0)
            text = "\n".join(lines)
            self.assertIn("efficiency 2/2 = 1.00000 split 0 merge 0/0", text)
            self.assertIn("GATE iso double-count PASS", text)
            self.assertIn("energy pull (event sum, target E - b_iso) n 2", text)
            self.assertIn("position pull x (largest object) n 2", text)
            lines, defects = self.run_stratum([[(2000.0, 15.2, 20.1), (2000.0, 20.4, 20.3)]], folder, "far")
            text = "\n".join(lines)
            self.assertEqual(defects, 0)
            self.assertIn("efficiency 2/2", text)
            self.assertIn("merge 0/1", text)
            self.assertIn("energy pull (primary object, target E - b_far(E, d)) n 2", text)

    def test_every_variant_prints_its_lines(self):
        """F2: near, edge, dead and saturation strata print energy and position pull lines (positions and near per-shower pulls
        reported, not gated), the components-without-objects count, and the gate line."""
        cases = {"near": ([[(2000.0, 19.0, 20.3), (2000.0, 21.2, 20.3)]], "main", {}, "near",
                          ("energy pull (event sum, target 2E - b_near(E, d)) n 1", "per-shower energy, target E pull of primaries")),
                 "edge": ([[(2000.0, 1.0, 20.3)]], "edge", {"t": 1.0}, "iso",
                          ("energy pull t 1.0 (event sum, target E Phi(t) - b_edge(t)) n 1", "position pull x (largest object, reported")),
                 "dead": ([[(2000.0, 12.3, 20.1)]], "dead", {"f_dead": 0.1}, "iso",
                          ("energy pull (event sum, target E (1 - f) - b_dead) n 1", "position pull y (largest object, reported")),
                 "sat": ([[(2000.0, 12.3, 20.1)]], "saturation", {}, "iso",
                          ("energy pull (event sum, target sum min(E g_c, 400) - b_sat", "position pull x (largest object, reported"))}
        ref = dict(self.REF, near={(e, d): 3.5 for e in (1000.0, 4000.0) for d in (1.5, 3.0)})
        with tempfile.TemporaryDirectory() as folder:
            for stem, (showers, fixture, extra, separation, wanted) in cases.items():
                with self.subTest(variant=stem):
                    self.REF = ref
                    lines, defects = self.run_stratum(showers, folder, stem, fixture, extra=extra, separation=separation)
                    text = "\n".join(lines)
                    self.assertEqual(defects, 0)
                    for w in wanted + ("components without objects {}", f"GATE {stem} double-count PASS"):
                        self.assertIn(w, text)

    def test_readings_refuse_a_truth_file_of_other_cells(self):
        with tempfile.TemporaryDirectory() as folder:
            generator = HandMadeGenerator([[(2000.0, 12.3, 20.1)]])
            files = t08_fixture_files.stratum_files(generator, "main", 1, 0, 1, folder, "a")
            header, truth = t08_fixture_files.read_truth(files["truth"]["path"])
            header = dict(header, cells_sha256="0" * 64)
            text = ProductFormat().make(3)
            truth = {k: numpy.concatenate([v, v, v]) for k, v in truth.items()}
            header = dict(header, events=3)
            with self.assertRaisesRegex(t08_readings.ReadingError, "not made from the cells"):
                t08_readings.readings(product.read_text(text), header, truth, self.REF, "a")


class PullValuesPerVariant(unittest.TestCase):
    """F2, F7: each variant's pulls from a hand-made product event and truth, against the formula of v4 4.2 and 9.2, to 1e-12."""
    REF = {"iso": 2.907, "dead": 2.855, "sat": 3.485, "edge": {0.5: 1.503, 1.0: 1.633, 1.5: 1.701, 2.0: 1.967},
           "far": {(e, d): b for e, b0 in ((1000.0, 1.8), (4000.0, 2.2)) for d, b in ((3.0, b0), (8.0, b0 + 1.0))},
           "near": {(e, d): b for e, b0 in ((1000.0, 3.4), (4000.0, 3.8)) for d, b in ((1.5, b0), (3.0, b0 + 0.4))}}

    def event(self, objects, s=2000.0, sigma=20.0, rows=()):
        return {"objects": [dict(energy=a, sigma_energy=sa, x=x, sigma_x=sx, y=y, sigma_y=sy, uncertainty_status="ok", members=[])
                            for a, sa, x, sx, y, sy in objects],
                "event_sum": {"energy": s, "sigma": sigma, "cells": 30}, "cells": [list(r) for r in rows]}

    def truth(self, energy, showers, **extra):
        out = {"energy_mev": numpy.array([energy]), "showers": numpy.full((1, 2, 2), numpy.nan)}
        out["showers"][0, :len(showers)] = showers
        for key, value in extra.items():
            out[key] = numpy.array([value])
        return out

    def pulls(self, ev, fixture, separation, truth, primary):
        return t08_readings.event_pulls(ev, fixture, separation, 0, truth, self.REF, {"primary": primary})

    def test_iso(self):
        ev = self.event([(1990.0, 21.0, 12.4, 0.01, 20.05, 0.02)], s=1993.0, sigma=21.0)
        p = self.pulls(ev, "main", "iso", self.truth(2000.0, [(12.39, 20.07)]), [0])
        close(self, p["energy"][0], (1993.0 - (2000.0 - 2.907)) / 21.0, 1e-12)
        close(self, p["x"][0], (12.4 - 12.39) / 0.01, 1e-12)
        close(self, p["y"][0], (20.05 - 20.07) / 0.02, 1e-12)

    def test_far(self):
        ev = self.event([(1995.0, 21.0, 12.4, 0.01, 20.0, 0.02), (1990.0, 22.0, 17.4, 0.012, 20.0, 0.015)])
        p = self.pulls(ev, "main", "far", self.truth(2000.0, [(12.41, 20.01), (17.38, 19.99)], d=5.5), [0, 1])
        u = math.log(2.0) / math.log(4.0)          # 2 GeV between the 1 and 4 GeV nodes, in ln E
        b = (1 - u) * (1.8 + 0.5) + u * (2.2 + 0.5)  # d = 5.5 is halfway between 3 and 8
        close(self, p["energy"][1], (1990.0 - (2000.0 - b)) / 22.0, 1e-12)
        close(self, p["x"][1], (17.4 - 17.38) / 0.012, 1e-12)
        close(self, p["y"][0], (20.0 - 20.01) / 0.02, 1e-12)

    def test_near_total_and_per_shower(self):
        ev = self.event([(3990.0, 30.0, 14.0, 0.02, 20.0, 0.03)], s=3995.0, sigma=28.0)
        p = self.pulls(ev, "main", "near", self.truth(2000.0, [(13.0, 20.0), (15.0, 20.0)], d=2.25), [0, None])
        u = math.log(2.0) / math.log(4.0)
        b = (1 - u) * (3.4 + 0.2) + u * (3.8 + 0.2)
        close(self, p["energy"][0], (3995.0 - (4000.0 - b)) / 28.0, 1e-12)
        close(self, p["near_shower_energy"][0], (3990.0 - 2000.0) / 30.0, 1e-12)   # no closure meaning: a merge holds both
        close(self, p["near_shower_x"][0], (14.0 - 13.0) / 0.02, 1e-12)
        self.assertEqual(len(p["near_shower_x"]), 1)

    def test_edge(self):
        ev = self.event([(1300.0, 15.0, 1.1, 0.03, 20.0, 0.02)], s=1310.0, sigma=16.0)
        p = self.pulls(ev, "edge", "iso", self.truth(2000.0, [(1.0, 20.01)], t=1.0), [0])
        close(self, p[("edge", 1.0)][0], (1310.0 - (2000.0 * 0.8413447460685429 - 1.633)) / 16.0, 1e-12)
        close(self, p["x"][0], (1.1 - 1.0) / 0.03, 1e-12)

    def test_dead(self):
        ev = self.event([(1700.0, 20.0, 20.6, 0.02, 20.4, 0.02)], s=1702.0, sigma=19.0)
        p = self.pulls(ev, "dead", "iso", self.truth(2000.0, [(20.55, 20.45)], f_dead=0.14), [0])
        close(self, p["energy"][0], (1702.0 - (2000.0 * (1 - 0.14) - 2.855)) / 19.0, 1e-12)
        close(self, p["y"][0], (20.4 - 20.45) / 0.02, 1e-12)

    def test_saturation(self):
        rows = [(0, 0, 0, 0, 1, 400.0, 1, 0), (1, 0, 0, 0, 1, 300.0, 0, 0), (2, 0, 0, 0, 1, 100.0, 0, 0)]
        ev = self.event([(800.0, 9.0, 20.5, 0.01, 20.5, 0.01)], s=800.0, sigma=99.0, rows=rows)
        p = self.pulls(ev, "saturation", "iso", self.truth(5000.0, [(20.5, 20.48)], clip_reference_mev=805.0), [0])
        sigma_u = math.sqrt(0.2 * 400.0 + 2 * 0.2 ** 2)          # unclipped cells only: 300 + 100 MeV, two cells
        close(self, p["energy"][0], (800.0 - (805.0 - 3.485)) / sigma_u, 1e-12)
        close(self, p["y"][0], (20.5 - 20.48) / 0.01, 1e-12)

    def test_no_pull_below_the_gated_range(self):
        ev = self.event([(150.0, 5.0, 12.4, 0.05, 20.0, 0.05)], s=150.0, sigma=5.0)
        self.assertEqual(self.pulls(ev, "main", "iso", self.truth(200.0, [(12.4, 20.0)]), [0]), {})


class Cost(unittest.TestCase):
    def test_cost_on_hand_made_events(self):
        """A reading for the job's estimate: seconds per event of chain and clustering on closed-form images with fixed noise."""
        grids = [as_array(image([(2000.0, 12.3, 20.1)])), as_array(image([(2000.0, 18.4, 20.2), (1500.0, 21.9, 20.6)]))]
        noise = numpy.sin(numpy.arange(N * N).reshape(N, N) * 12.9898) * SIGMA_N      # fixed, not random
        live, sat = numpy.ones((N, N), bool), numpy.zeros((N, N), bool)
        started = time.perf_counter()
        count = 0
        for _ in range(50):
            for g in grids:
                clustering.cluster_event(g + noise, live, sat, CFG)
                count += 1
        print(f"COST hand-made clustering {(time.perf_counter() - started) / count * 1e3:.2f} ms per event over {count} events")
        ped, gain = (cell_input.read_payload(b) for b in payloads())
        chains = [cell_chain.apply(g + noise, live, sat, ped, gain) for g in grids]
        results = [clustering.cluster_event(c.energy, c.live, c.saturated, CFG) for c in chains]
        header = product.header_document("cost", N, N, "0" * 64, 100, CFG.sha256, cell_chain.chain_record(ped, gain))
        started = time.perf_counter()
        stream = io.StringIO()
        writer = product.Writer(stream, header)
        for i in range(100):
            writer.event(product.event_document(i, chains[i % 2], results[i % 2], N))
        writer.finish()
        written = time.perf_counter()
        read = product.read_text(stream.getvalue())
        for ev in read.events:
            product.double_count_defects(ev)
        print(f"COST hand-made product write {(written - started) * 10:.2f} ms, read and double-count check "
              f"{(time.perf_counter() - written) * 10:.2f} ms per event; {len(stream.getvalue()) / 100 / 1e3:.1f} kB per event")


if __name__ == "__main__":
    unittest.main()
