"""adapters/photon-likelihood, D4 build E1 of T09: v4 9.4's two negative checks (t04-values-v4.md section 9.4 and section 11;
t04-prereg.md, "Required negative case").

- E1b, the single-photon-density variant: a whole configuration of its own (its own file and hash, light-likelihood-configuration/1
  never carries it as a flag), in which the hit channel's time term is one photon's arrival density, f(t) = lambda(t) / m (the signal's
  Gaussian plus the dark noise mixture, as the main recipe defines lambda), in place of the first-arrival density. Everything else is the
  main recipe's: the charge density, the no-hit term, the fit, the multistart and the Hessian.
- E1a, dead read as unhit: a scoring-side tool rewrites the dead control's readout with its dead channels as live-unhit; the frozen recipe
  fits it unchanged.
- The two "fires" rules of v4 9.4, read on the scoring side: E1a fires if any of x, y, z, t0 gives |centre| - 1.645 se > 0.10; E1b if the
  t0 centre does. Readings only: no verdict before K09.

Hand-made events only: no fixture event and no Monte Carlo of the frozen generator; the one noisy event is drawn with stage 2's module's own
coding of section 4.3 and its own random numbers. Expectations come from a second coding in plain Python (math), never from the recipe.
Run from the plugin root: python -m unittest tests.adapters.test_photon_likelihood_negative -v
"""
from __future__ import annotations

import ast
import hashlib
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy
from scipy import integrate

from tests.adapters import test_photon_likelihood as stage1
from tests.adapters import test_photon_likelihood_time as stage2

ROOT = stage1.ROOT
ASSETS = stage1.ASSETS
from light_recipe import (arrival_response, configuration, fit, joint, light_model, likelihood, multistart, product, readout,  # noqa: E402
                          single_photon)
import t09_fixture_files  # noqa: E402
import t09_negative_checks as negative  # noqa: E402
import t09_readings  # noqa: E402

SENSORS, DARK, WINDOW, SIGMA_T = stage1.SENSORS, stage1.DARK, stage1.WINDOW, stage1.SIGMA_T
THRESHOLD, CLIP = stage1.THRESHOLD, stage1.CLIP
RATE = DARK / WINDOW
MAIN_CFG, MAIN_MODEL = stage1.CFG, stage1.MODEL
VARIANT_FILE = ASSETS / "t09-sphere-1-single-photon.configuration.json"
MAIN_FILE = ASSETS / "t09-sphere-1.configuration.json"


def variant_model():
    return single_photon.Model(single_photon.load(VARIANT_FILE))


VARIANT = variant_model()
SINGLE = VARIANT.arrival


def text_ln_single(t, mu_s, tau):
    """ln f(t) of one photon, the normalised arrival mixture (stage 2's second coding of lambda / m)."""
    return stage2.text_arrival(t, mu_s, tau)[0]


def one(values):
    return [float(v[0]) for v in values]


def single_density(q, t, mu_s, tau, arrival=SINGLE):
    return one(arrival.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu_s]), numpy.array([tau])))


def single_censored(level, t, mu_s, tau, arrival=SINGLE):
    return one(arrival.log_joint_at_or_above(level, numpy.array([t]), numpy.array([mu_s]), numpy.array([tau])))


def timed_readout_bytes(states, charges, times, saturated=None, saturation_charge=None):
    states = numpy.asarray(states, numpy.int8)
    saturated = numpy.zeros(states.shape, bool) if saturated is None else numpy.asarray(saturated, bool)
    return readout.readout_bytes(states, numpy.asarray(charges, float), numpy.asarray(times, float), saturated, THRESHOLD,
                                 saturation_charge)


def run_cli(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "photon_likelihood.py"), *args], capture_output=True, text=True,
                          timeout=900)


def run_tool(*args):
    return subprocess.run([sys.executable, "-I", "-B", str(ASSETS / "fixture_tools" / "t09_negative_checks.py"), *args],
                          capture_output=True, text=True, timeout=900)


class TimedGenerator(stage1.HandMadeGenerator):
    """Stage 1's hand-made generator with each hit's time at its median first arrival (stage 2's noise-free timed event)."""
    def event(self, fixture, block, stratum, event_index):
        vertex, direction, n_exp = self.TRUTHS[event_index]
        ev = super().event(fixture, block, stratum, event_index)
        ev["data"]["time"] = stage2.noise_free_timed_event(vertex, direction, n_exp, 20.0,
                                                           dead=tuple(self.DEAD_CHANNELS) if fixture == "dead" else ())[2]
        return ev


BRIGHT = ((0.6, -0.9, 1.4), stage1.unit((0.4, 0.8, -0.3)), 1500.0, 21.0)   # vertex, direction, N_exp, t0: a B4-like event at r/R_s 0.36


# --- E1b: the single-photon density -----------------------------------------------------------------------------------------

class SinglePhotonDensity(unittest.TestCase):
    CASES = (("few photons", 0.05, 1.1, 30.0), ("several", 5.0, 4.7, 40.0), ("many", 300.0, 310.0, 60.0),
             ("near the window start", 2.0, 2.2, 3.0), ("near the window end", 2.0, 1.8, 197.0))

    def time_integral(self, mu_s, tau, term):
        cuts = sorted({-400.0, tau - 60.0, tau - 10.0, tau - 3.0, tau, tau + 3.0, tau + 10.0, tau + 60.0, 0.0, WINDOW, 600.0})
        return sum(integrate.quad(lambda t: math.exp(term(t)), a, b, limit=400, epsabs=0.0, epsrel=1e-12)[0]
                   for a, b in zip(cuts[:-1], cuts[1:]))

    def test_the_time_density_integrates_to_one_at_every_charge(self):
        for name, mu_s, q, tau in self.CASES:
            with self.subTest(case=name):
                m = mu_s + DARK
                charge = stage1.text_ln_density(q, m)
                self.assertAlmostEqual(self.time_integral(mu_s, tau, lambda t: single_density(q, t, mu_s, tau)[0] - charge), 1.0, delta=1e-8)
                for level in (CLIP, THRESHOLD):
                    tail = stage1.text_ln_at_or_above(level, m)
                    self.assertAlmostEqual(self.time_integral(mu_s, tau, lambda t: single_censored(level, t, mu_s, tau)[0] - tail), 1.0,
                                           delta=1e-8)

    def test_against_a_hand_computation(self):
        """ln p(q, t) = ln f(q | m) + ln (lambda(t) / m), the charge density times one photon's time density."""
        for mu_s, q, tau, t in ((0.05, 1.1, 30.0, 31.0), (5.0, 4.7, 40.0, 38.5), (300.0, 310.0, 60.0, 56.0), (2.0, 2.2, 3.0, 150.0),
                                (40.0, 3.0, 20.0, 80.0), (0.3, 7.0, 25.0, -2.0), (800.0, 1100.0, 70.0, 66.0)):
            with self.subTest(mu_s=mu_s, q=q, t=t):
                m = mu_s + DARK
                want = stage1.text_ln_density(q, m) + text_ln_single(t, mu_s, tau)
                self.assertAlmostEqual(single_density(q, t, mu_s, tau)[0], want, delta=1e-10 * max(1.0, abs(want)))
                want = stage1.text_ln_at_or_above(CLIP, m) + text_ln_single(t, mu_s, tau)
                self.assertAlmostEqual(single_censored(CLIP, t, mu_s, tau)[0], want, delta=1e-10 * max(1.0, abs(want)))

    def test_agrees_with_the_first_arrival_in_the_one_photon_limit(self):
        """At a mean count m far below one, a hit holds one photon, whose time is its first arrival: the two terms agree to O(m)."""
        for mu_s in (1e-2, 1e-3, 1e-4):
            for q, tau, t in ((1.0, 30.0, 29.0), (0.8, 50.0, 52.5), (1.3, 100.0, 100.0)):
                with self.subTest(mu_s=mu_s, t=t):
                    main = stage2.ARRIVAL.log_joint_density(numpy.array([q]), numpy.array([t]), numpy.array([mu_s]), numpy.array([tau]))
                    single = single_density(q, t, mu_s, tau)
                    self.assertLess(abs(single[0] - float(main[0][0])), 2.0 * (mu_s + DARK))

    def test_differs_from_the_first_arrival_with_many_photons(self):
        """With about 300 photons the first arrival comes several sigma early; one photon's density keeps its peak at tau."""
        mu_s, q, tau = 300.0, 300.0, 60.0
        grid = numpy.linspace(tau - 12.0, tau + 6.0, 1801)
        single = SINGLE.log_joint_density(numpy.full(grid.size, q), grid, numpy.full(grid.size, mu_s), numpy.full(grid.size, tau))[0]
        main = stage2.ARRIVAL.log_joint_density(numpy.full(grid.size, q), grid, numpy.full(grid.size, mu_s), numpy.full(grid.size, tau))[0]
        self.assertAlmostEqual(float(grid[numpy.argmax(single)]), tau, delta=0.02)
        self.assertLess(float(grid[numpy.argmax(main)]), tau - 2.0 * SIGMA_T)
        self.assertGreater(single[numpy.argmin(abs(grid - tau))] - main[numpy.argmin(abs(grid - tau))], 100.0)

    def test_derivatives_in_mu_and_tau(self):
        for kind in ("density", "censored"):
            for mu_s, q, tau, t in ((0.05, 1.1, 30.0, 31.0), (5.0, 4.7, 40.0, 38.5), (300.0, 310.0, 60.0, 56.0), (2.0, 2.2, 30.0, 150.0),
                                    (40.0, 6.0, 20.0, 24.0), (3.0, 2.0, 30.0, 30.0 + 40.0 * SIGMA_T)):
                with self.subTest(kind=kind, mu_s=mu_s, t=t):
                    def term(mu, ta):
                        return single_density(q, t, mu, ta) if kind == "density" else single_censored(CLIP, t, mu, ta)
                    l0, l_m, l_t, l_mm, l_mt, l_tt = term(mu_s, tau)
                    self.assertTrue(all(math.isfinite(v) for v in (l0, l_m, l_t, l_mm, l_mt, l_tt)))
                    hm, ht = 1e-5 * mu_s, 1e-5
                    up_m, dn_m, up_t, dn_t = term(mu_s + hm, tau), term(mu_s - hm, tau), term(mu_s, tau + ht), term(mu_s, tau - ht)
                    for got, fd in ((l_m, (up_m[0] - dn_m[0]) / (2 * hm)), (l_t, (up_t[0] - dn_t[0]) / (2 * ht)),
                                    (l_mm, (up_m[1] - dn_m[1]) / (2 * hm)), (l_mt, (up_t[1] - dn_t[1]) / (2 * ht)),
                                    (l_mt, (up_m[2] - dn_m[2]) / (2 * hm)), (l_tt, (up_t[2] - dn_t[2]) / (2 * ht))):
                        self.assertAlmostEqual(got, fd, delta=1e-6 * max(1.0, abs(fd)))

    def test_refuses_a_mean_that_is_not_positive_and_takes_an_empty_selection(self):
        with self.assertRaises(ValueError):
            SINGLE.log_joint_density(numpy.array([1.0]), numpy.array([10.0]), numpy.array([0.0]), numpy.array([10.0]))
        with self.assertRaises(ValueError):
            SINGLE.log_joint_at_or_above(CLIP, numpy.array([numpy.nan]), numpy.array([1.0]), numpy.array([10.0]))
        self.assertEqual([v.size for v in SINGLE.log_joint_density(numpy.zeros(0), numpy.zeros(0), numpy.zeros(0), numpy.zeros(0))], [0] * 6)


class OnlyTheHitTimeTermDiffers(unittest.TestCase):
    """The one function that differs: the hit channel's joint term (single_photon.SinglePhotonArrival's two methods in place of
    arrival_response.ArrivalResponse's). The main model keeps the main class itself."""

    def test_the_main_model_keeps_the_first_arrival_class_and_the_variant_swaps_only_it(self):
        self.assertIs(type(MAIN_MODEL.arrival), arrival_response.ArrivalResponse)
        self.assertIsInstance(VARIANT.arrival, single_photon.SinglePhotonArrival)
        self.assertIsInstance(VARIANT, likelihood.Model)
        for name in ("time_spread", "dark_mean", "window", "rate"):
            self.assertEqual(getattr(VARIANT.arrival, name), getattr(MAIN_MODEL.arrival, name))
        self.assertEqual(VARIANT.dark, MAIN_MODEL.dark)
        self.assertEqual(VARIANT.scale, MAIN_MODEL.scale)
        self.assertEqual(vars(VARIANT.response), vars(MAIN_MODEL.response))
        numpy.testing.assert_array_equal(VARIANT.geometry.positions, MAIN_MODEL.geometry.positions)
        defined = {name for name, value in vars(single_photon.SinglePhotonArrival).items() if callable(value)}
        self.assertEqual(defined & set(vars(arrival_response.ArrivalResponse)), {"log_joint_density", "log_joint_at_or_above"})

    def test_unhit_and_dead_channels_get_the_same_terms_and_hit_channels_differ(self):
        vertex, direction, n_exp, t0 = BRIGHT
        state, charge, times, e_vis = stage2.noise_free_timed_event(vertex, direction, n_exp, t0, dead=(5, 6, 7))
        tev = stage2.timed(state, charge, times)
        mu = MAIN_MODEL.scale * e_vis * light_model.shape(MAIN_MODEL, numpy.array(vertex), numpy.array(direction))
        delay, _, _ = joint.arrival_delays(MAIN_MODEL, vertex)
        main = joint.channel_terms(MAIN_MODEL, tev, mu, t0 + delay)
        var = joint.channel_terms(VARIANT, tev, mu, t0 + delay)
        hit = tev.event.hit
        for k in range(6):
            numpy.testing.assert_array_equal(main[k][~hit], var[k][~hit])
        self.assertGreater(float(numpy.abs(main[0][hit] - var[0][hit]).max()), 0.1)

    def test_a_bright_noisy_event_fits_t0_early_under_the_single_photon_density(self):
        """The negative check's mechanism on one hand-made noisy event (stage 2's coding, its own random numbers): the recorded
        times are first arrivals, so a fit that reads them as single photons puts t0 early."""
        vertex, direction, n_exp, t0 = BRIGHT
        tev = stage2.noisy_timed_event(numpy.random.Generator(numpy.random.PCG64(20261111)), vertex, direction, n_exp, t0)
        out = {}
        for name, model in (("main", MAIN_MODEL), ("single-photon", VARIANT)):
            start, _, _ = fit.joint_seed(model, tev)
            res = fit.fit_joint_event(model, tev, start)
            self.assertEqual(res.status, "converged", name)
            out[name] = res.t0
        self.assertLess(abs(out["main"] - t0), 0.3)
        self.assertLess(out["single-photon"], out["main"] - 0.2)


class VariantConfiguration(unittest.TestCase):
    def test_the_variant_file_equals_the_main_one_but_for_its_format(self):
        main, var = (json.loads(p.read_text(encoding="utf-8")) for p in (MAIN_FILE, VARIANT_FILE))
        self.assertEqual(var["format"], single_photon.FORMAT)
        self.assertNotEqual(single_photon.FORMAT, configuration.FORMAT)
        self.assertEqual({k: v for k, v in main.items() if k != "format"}, {k: v for k, v in var.items() if k != "format"})
        cfg = single_photon.load(VARIANT_FILE)
        self.assertEqual(cfg.sha256, hashlib.sha256(VARIANT_FILE.read_bytes()).hexdigest())
        self.assertNotEqual(cfg.sha256, MAIN_CFG.sha256)
        self.assertEqual(single_photon.load().sha256, cfg.sha256)

    def test_the_main_reader_refuses_the_variant_file_and_the_variant_reader_the_main_file(self):
        with self.assertRaises(configuration.ConfigurationError):
            configuration.load(VARIANT_FILE)
        with self.assertRaises(configuration.ConfigurationError):
            single_photon.load(MAIN_FILE)
        self.assertEqual(single_photon.load_any(None).sha256, MAIN_CFG.sha256)
        self.assertEqual(single_photon.load_any(MAIN_FILE).format, configuration.FORMAT)
        self.assertEqual(single_photon.load_any(VARIANT_FILE).format, single_photon.FORMAT)

    def test_a_variant_file_with_a_changed_constant_or_key_is_refused(self):
        doc = json.loads(VARIANT_FILE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            for change in ({"time_spread_ns": -1.0}, {"extra": 1}, {"single_photon": True}):
                path = Path(folder) / "c.json"
                path.write_text(json.dumps({**doc, **change}), encoding="utf-8")
                with self.subTest(change=change), self.assertRaises(configuration.ConfigurationError):
                    single_photon.load(path)
            path.write_text(json.dumps({**json.loads(MAIN_FILE.read_text(encoding="utf-8")), "single_photon": True}), encoding="utf-8")
            with self.assertRaises(configuration.ConfigurationError):   # never a flag inside the main configuration
                configuration.load(path)

    def test_each_model_takes_only_its_own_configuration(self):
        self.assertIs(type(single_photon.model_for(MAIN_CFG)), likelihood.Model)
        self.assertIs(type(single_photon.model_for(VARIANT.cfg)), single_photon.Model)
        with self.assertRaises(configuration.ConfigurationError):
            single_photon.Model(MAIN_CFG)


def multistart_product(model, cfg, tev, product_id="hand-made-e1b"):
    """A /3 (or its single-photon twin) of one event, written through the recipe's own writer."""
    budget = multistart.load()
    rd = readout.read_bytes(timed_readout_bytes([tev.event.state], [tev.event.charge], [tev.time]))
    stream = io.StringIO()
    writer = product.Writer(stream, product.header_document(product_id, rd, cfg, likelihood="charge-time", budget=budget))
    ms = multistart.fit_multistart(model, tev, budget)
    writer.event(product.multistart_event_document(0, tev, ms, product.check_at(model, tev.event, ms.anchor, ms.result)))
    writer.finish()
    return stream.getvalue(), budget


class VariantProduct(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        vertex, direction, n_exp, t0 = BRIGHT
        state, charge, times, _ = stage2.noise_free_timed_event(vertex, direction, n_exp, t0)
        cls.tev = stage2.timed(state, charge, times)
        cls.variant_text, cls.budget = multistart_product(VARIANT, VARIANT.cfg, cls.tev)
        cls.main_text, _ = multistart_product(MAIN_MODEL, MAIN_CFG, cls.tev)

    def test_the_header_names_the_variant_and_its_configuration(self):
        head = json.loads(self.variant_text.split("\n")[0])
        self.assertEqual(head["format"], product.FORMAT_SINGLE_PHOTON)
        self.assertEqual(head["likelihood"], single_photon.LIKELIHOOD)
        self.assertEqual(head["configuration"], {"format": single_photon.FORMAT, "sha256": VARIANT.cfg.sha256})
        self.assertEqual(head["retention"]["truth"], "none")
        self.assertEqual(head["fit_settings"], product.SETTINGS_MULTISTART)
        self.assertEqual(head["hessian_steps"], likelihood.HESSIAN_STEPS)
        main_head = json.loads(self.main_text.split("\n")[0])
        self.assertEqual(main_head["format"], product.FORMAT_MULTISTART)
        self.assertEqual(main_head["likelihood"], product.LIKELIHOOD_JOINT)
        differ = sorted(k for k in head if head[k] != main_head[k])
        self.assertEqual(differ, ["configuration", "format", "likelihood"])

    def test_each_reader_takes_its_own_product_and_refuses_the_other(self):
        read = product.read_text(self.variant_text, VARIANT, VARIANT.cfg, self.budget)
        self.assertEqual(read.header["format"], product.FORMAT_SINGLE_PHOTON)
        product.read_text(self.main_text, MAIN_MODEL, MAIN_CFG, self.budget)
        with self.assertRaises(product.ProductError):
            product.read_text(self.variant_text, MAIN_MODEL, MAIN_CFG, self.budget)
        with self.assertRaises(product.ProductError):
            product.read_text(self.main_text, VARIANT, VARIANT.cfg, self.budget)

    def test_a_product_whose_format_and_configuration_disagree_is_refused(self):
        lines = self.variant_text.split("\n")
        head = json.loads(lines[0])
        head["configuration"] = {"format": configuration.FORMAT, "sha256": MAIN_CFG.sha256}
        forged = "\n".join([product.dumps(head)] + lines[1:])
        with self.assertRaises(product.ProductError):
            product.read_text(forged, None, None)
        lines = self.main_text.split("\n")
        head = json.loads(lines[0])
        head["configuration"] = {"format": single_photon.FORMAT, "sha256": VARIANT.cfg.sha256}
        with self.assertRaises(product.ProductError):
            product.read_text("\n".join([product.dumps(head)] + lines[1:]), None, None)

    def test_the_recomputation_uses_the_variant_density(self):
        """Read with the variant's configuration but the main model, the stored ln L does not recompute."""
        with self.assertRaises(product.ProductError):
            product.read_text(self.variant_text, MAIN_MODEL, VARIANT.cfg, self.budget)

    def test_the_writer_refuses_the_variant_outside_the_multistart_fit(self):
        rd = readout.read_bytes(timed_readout_bytes([self.tev.event.state], [self.tev.event.charge], [self.tev.time]))
        for likelihood_kind in ("charge-only", "charge-time"):
            with self.subTest(likelihood=likelihood_kind), self.assertRaises(ValueError):
                product.header_document("x", rd, VARIANT.cfg, likelihood=likelihood_kind)


class VariantCommandLine(unittest.TestCase):
    def test_fit_and_check_product_with_the_variant_configuration(self):
        vertex, direction, n_exp, t0 = BRIGHT
        state, charge, times, _ = stage2.noise_free_timed_event(vertex, direction, n_exp, t0)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            (folder / "r.readout").write_bytes(timed_readout_bytes([state], [charge], [times]))
            common = ["--readout", str(folder / "r.readout"), "--product-id", "hand-made-e1b-cli"]
            p = run_cli("fit", *common, "--product", str(folder / "single.jsonl"), "--configuration", str(VARIANT_FILE),
                        "--likelihood", "charge-time", "--starts", "multistart")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            out = json.loads(p.stdout)
            self.assertEqual(out["configuration_sha256"], VARIANT.cfg.sha256)
            self.assertEqual(product.format_of(folder / "single.jsonl"), product.FORMAT_SINGLE_PHOTON)
            p = run_cli("check-product", "--product", str(folder / "single.jsonl"), "--configuration", str(VARIANT_FILE))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = run_cli("check-product", "--product", str(folder / "single.jsonl"))
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"), p.stdout)
            for extra in (["--likelihood", "charge-time"], ["--likelihood", "charge-only"]):
                with self.subTest(extra=extra):
                    p = run_cli("fit", *common, "--product", str(folder / "no.jsonl"), "--configuration", str(VARIANT_FILE), *extra)
                    self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"), p.stdout)
                    self.assertFalse((folder / "no.jsonl").exists())
            p = run_cli("topology", "--readout", str(folder / "r.readout"), "--h1-product", str(folder / "single.jsonl"), "--product",
                        str(folder / "top.jsonl"), "--product-id", "x", "--configuration", str(VARIANT_FILE))
            self.assertEqual((p.returncode, json.loads(p.stdout)["status"]), (2, "rejected"), p.stdout)


# --- E1a: dead read as unhit ----------------------------------------------------------------------------------------------------

def mixed_readout():
    """Three events with every state: hits (one saturated), unhit, dead (channels 0-9 and, in event 2 only, 500) and disabled."""
    rng = numpy.random.Generator(numpy.random.PCG64(7))
    states = numpy.zeros((3, SENSORS), numpy.int8)
    charges = numpy.zeros((3, SENSORS))
    times = numpy.full((3, SENSORS), numpy.nan)
    saturated = numpy.zeros((3, SENSORS), bool)
    for e in range(3):
        hits = rng.choice(numpy.arange(20, SENSORS), 120, replace=False)
        states[e, hits] = readout.LIVE_HIT
        charges[e, hits] = rng.uniform(0.3, 4.9, hits.size)
        times[e, hits] = rng.uniform(5.0, 150.0, hits.size)
        charges[e, hits[0]], saturated[e, hits[0]] = CLIP, True
        dead = list(range(10)) + ([500] if e == 2 else [])
        states[e, dead], charges[e, dead], times[e, dead] = readout.DEAD, numpy.nan, numpy.nan
        states[e, 15], charges[e, 15], times[e, 15] = readout.DISABLED, numpy.nan, numpy.nan
    return readout.readout_bytes(states, charges, times, saturated, THRESHOLD, CLIP)


class DeadReadAsUnhit(unittest.TestCase):
    def test_every_dead_channel_becomes_live_unhit_and_nothing_else_changes(self):
        before = readout.read_bytes(mixed_readout())
        state, charge, time_, sat, relabelled = negative.relabel_dead(before)
        after = readout.read_bytes(readout.readout_bytes(state, charge, time_, sat, before.header["threshold"],
                                                         before.header["saturation_charge"]))
        dead = before.state == readout.DEAD
        numpy.testing.assert_array_equal(relabelled, dead)
        self.assertTrue(numpy.all(after.state[dead] == readout.LIVE_UNHIT))
        self.assertTrue(numpy.all(after.charge[dead] == 0.0))
        self.assertTrue(numpy.all(numpy.isnan(after.time[dead])))
        self.assertFalse(after.saturated[dead].any())
        self.assertFalse((after.state == readout.DEAD).any())
        numpy.testing.assert_array_equal(after.state[~dead], before.state[~dead])
        numpy.testing.assert_array_equal(after.charge[~dead], before.charge[~dead])          # NaN of disabled channels compares equal
        numpy.testing.assert_array_equal(after.time[~dead], before.time[~dead])
        numpy.testing.assert_array_equal(after.saturated, before.saturated)
        self.assertEqual(after.header, before.header)
        self.assertEqual(int((after.state == readout.DISABLED).sum()), 3)

    def test_the_file_tool_writes_the_readout_and_a_record_that_links_both(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            content = mixed_readout()
            (folder / "dead.readout").write_bytes(content)
            p = run_tool("relabel-dead", "--readout", str(folder / "dead.readout"), "--out", str(folder / "unhit.readout"),
                         "--record", str(folder / "unhit.relabel.json"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            record = json.loads((folder / "unhit.relabel.json").read_text(encoding="utf-8"))
            self.assertEqual(record["format"], negative.RECORD_FORMAT)
            self.assertEqual(record["source_sha256"], hashlib.sha256(content).hexdigest())
            self.assertEqual(record["relabelled_sha256"], hashlib.sha256((folder / "unhit.readout").read_bytes()).hexdigest())
            self.assertEqual(record["events"], 3)
            self.assertEqual(record["relabelled_per_event"], [10, 10, 11])
            self.assertEqual(record["channels_every_event"], list(range(10)))
            p = run_tool("relabel-dead", "--readout", str(folder / "dead.readout"), "--out", str(folder / "unhit.readout"),
                         "--record", str(folder / "again.json"))
            self.assertEqual(p.returncode, 2, "never overwrites")
            live = readout.readout_bytes(numpy.zeros((1, SENSORS), numpy.int8), numpy.zeros((1, SENSORS)), numpy.full((1, SENSORS), numpy.nan),
                                         numpy.zeros((1, SENSORS), bool), THRESHOLD, None)
            (folder / "live.readout").write_bytes(live)
            p = run_tool("relabel-dead", "--readout", str(folder / "live.readout"), "--out", str(folder / "x.readout"), "--record",
                         str(folder / "x.json"))
            self.assertEqual(p.returncode, 2, "a readout with no dead channel is not the dead control")
            self.assertFalse((folder / "x.readout").exists())

    def test_the_frozen_recipe_fits_the_relabelled_readout_unchanged_and_the_dead_gate_sees_it(self):
        gen = TimedGenerator()
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            files = t09_fixture_files.stratum_files(gen, "dead", 1, 0, 1, folder, "dead")
            p = run_tool("relabel-dead", "--readout", files["readout"]["path"], "--out", str(folder / "unhit.readout"), "--record",
                         str(folder / "unhit.relabel.json"))
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            p = run_cli("fit", "--readout", str(folder / "unhit.readout"), "--product", str(folder / "p.jsonl"), "--product-id", "e1a",
                        "--likelihood", "charge-time")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            read = product.read_product(folder / "p.jsonl", MAIN_MODEL, MAIN_CFG)
            self.assertEqual(read.header["configuration"]["sha256"], MAIN_CFG.sha256)
            doc = read.events[0]
            self.assertNotIn("D", doc["states"])
            self.assertEqual(doc["counts"]["dead"], 0)
            _, truth = t09_fixture_files.read_truth(files["truth"]["path"])
            self.assertTrue(all(doc["states"][c] == "U" for c in truth["dead_channels"]))
            self.assertEqual(len(t09_readings.dead_state_defects(read.events, truth["dead_channels"])), 1)


class NoTruthOnTheDataSide(unittest.TestCase):
    def test_the_variant_module_imports_no_generator_seed_code_or_truth_reader(self):
        text = (ASSETS / "light_recipe" / "single_photon.py").read_text(encoding="utf-8")
        self.assertEqual(stage1.RecipeImportsNoGenerator().findings_in(text), [])
        for name in ("t09_", "truth", "fixture_tools"):
            self.assertNotIn(f"import {name}", text)

    def test_no_recipe_file_names_the_negative_check_tool(self):
        for path in sorted((ASSETS / "light_recipe").rglob("*.py")) + [ASSETS / "photon_likelihood.py"]:
            with self.subTest(file=path.name):
                self.assertNotIn("t09_negative_checks", path.read_text(encoding="utf-8"))

    def test_the_relabelling_reads_the_readout_alone(self):
        tree = ast.parse((ASSETS / "fixture_tools" / "t09_negative_checks.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in ("relabel_dead", "relabel_file"):
                names = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | \
                        {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
                with self.subTest(function=node.name):
                    self.assertFalse({"read_truth", "truth", "numpy.load", "load"} & names, names)


# --- the two "fires" rules, as readings ------------------------------------------------------------------------------------------

class FiresRule(unittest.TestCase):
    def test_the_rule_on_hand_made_outcomes(self):
        for centre, se, fires in ((0.30, 0.05, True), (-0.30, 0.05, True), (0.15, 0.04, False), (-0.15, 0.04, False),
                                  (0.10 + 1.645 * 0.02 + 1e-9, 0.02, True), (0.10 + 1.645 * 0.02 - 1e-9, 0.02, False),
                                  (7.0, 0.07, True), (0.0, 0.0, False)):
            with self.subTest(centre=centre, se=se):
                value, fired = negative.fires(centre, se)
                self.assertAlmostEqual(value, abs(centre) - 1.645 * se, delta=1e-15)
                self.assertIs(fired, fires)

    def test_each_check_reads_its_own_parameters(self):
        self.assertEqual(negative.CHECKS["dead-as-unhit"]["parameters"], ("x", "y", "z", "t0"))
        self.assertEqual(negative.CHECKS["single-photon"]["parameters"], ("t0",))
        rng = numpy.random.Generator(numpy.random.PCG64(3))
        base = {name: rng.standard_normal(400) for name in ("x", "y", "z", "u1", "u2", "e_vis", "t0")}
        quiet = negative.reading(base, "dead-as-unhit", (9002, 1, 0))
        self.assertFalse(quiet["fires"])
        for name, check, fires in (("u1", "dead-as-unhit", False), ("e_vis", "dead-as-unhit", False), ("z", "dead-as-unhit", True),
                                   ("t0", "dead-as-unhit", True), ("x", "single-photon", False), ("t0", "single-photon", True)):
            with self.subTest(shifted=name, check=check):
                pulls = {**base, name: base[name] + 0.5}
                out = negative.reading(pulls, check, (9001, 1, 10))
                self.assertIs(out["fires"], fires)
                self.assertEqual([row["name"] for row in out["rows"]], list(negative.CHECKS[check]["parameters"]))

    def test_the_bootstrap_uncertainty_is_seeded_from_the_bin_and_near_the_design_value(self):
        rng = numpy.random.Generator(numpy.random.PCG64(11))
        pulls = {"t0": rng.standard_normal(2000)}
        a = negative.reading(pulls, "single-photon", (9001, 1, 10))["rows"][0]
        b = negative.reading(pulls, "single-photon", (9001, 1, 10))["rows"][0]
        c = negative.reading(pulls, "single-photon", (9001, 1, 9))["rows"][0]
        self.assertEqual(a, b)
        self.assertNotEqual(a["se_bootstrap"], c["se_bootstrap"])
        self.assertAlmostEqual(a["se_design"], 1.03 / math.sqrt(2000), delta=1e-15)
        self.assertAlmostEqual(a["se_bootstrap"] / a["se_design"], 1.0, delta=0.15)
        self.assertEqual(a["centre"], t09_readings.centre(pulls["t0"]))
        self.assertEqual(a["n"], 2000)

    def test_the_closed_form_sensitivities_of_v4(self):
        """v4 9.4 for E1b: at about 1 photon per channel the first arrival is early by 0.28 of the time spread (0.41 ns); at
        3,000 events the rule needs |centre| above 0.10 + 1.645 x 1.03 / sqrt(3000), about 0.131."""
        self.assertAlmostEqual(negative.threshold_at(3000), 0.10 + 1.645 * 1.03 / math.sqrt(3000), delta=1e-15)
        self.assertAlmostEqual(negative.threshold_at(250), 0.2072, delta=5e-4)
        shift = negative.first_arrival_shift(1.0)          # E[min of n] / sigma for n ~ Poisson(1) given n >= 1
        self.assertAlmostEqual(shift, -0.28, delta=0.01)
        self.assertAlmostEqual(-shift * SIGMA_T, 0.41, delta=0.02)


class FiresCommandLine(unittest.TestCase):
    """The fires reading end to end on hand-made files: provenance checks and the refusals."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        folder = Path(cls.folder.name)
        gen = TimedGenerator()
        cls.dead = t09_fixture_files.stratum_files(gen, "dead", 1, 0, 2, folder, "dead")
        p = run_tool("relabel-dead", "--readout", cls.dead["readout"]["path"], "--out", str(folder / "unhit.readout"), "--record",
                     str(folder / "unhit.relabel.json"))
        assert p.returncode == 0, p.stdout + p.stderr
        # A forged pair (review M4): a readout that is not the relabelling of the source (one more hit charge changed) with a record
        # whose hashes name it; only recomputing the relabelling from the source tells it apart.
        rd = readout.read_file(folder / "unhit.readout")
        charge = rd.charge.copy()
        first_hit = numpy.flatnonzero(rd.state[0] == readout.LIVE_HIT)[0]
        charge[0, first_hit] += 0.5
        forged = readout.readout_bytes(rd.state, charge, rd.time, rd.saturated, rd.header["threshold"], rd.header["saturation_charge"])
        (folder / "forged.readout").write_bytes(forged)
        record = json.loads((folder / "unhit.relabel.json").read_text(encoding="utf-8"))
        record["relabelled_sha256"] = hashlib.sha256(forged).hexdigest()
        (folder / "forged.relabel.json").write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        record = json.loads((folder / "unhit.relabel.json").read_text(encoding="utf-8"))
        record["channels_every_event"] = record["channels_every_event"][1:]
        (folder / "short.relabel.json").write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        for name, readout_path in (("e1a", folder / "unhit.readout"), ("masked", Path(cls.dead["readout"]["path"])),
                                   ("forged", folder / "forged.readout")):
            p = run_cli("fit", "--readout", str(readout_path), "--product", str(folder / f"{name}.jsonl"), "--product-id", name,
                        "--likelihood", "charge-time", "--starts", "multistart")
            assert p.returncode == 0, p.stdout + p.stderr

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def path(self, name):
        return str(Path(self.folder.name) / name)

    def test_the_dead_as_unhit_reading_prints_the_rule_and_no_verdict(self):
        p = run_tool("fires", "--check", "dead-as-unhit", "--product", self.path("e1a.jsonl"), "--truth", self.dead["truth"]["path"],
                     "--relabel-record", self.path("unhit.relabel.json"), "--source-readout", self.dead["readout"]["path"],
                     "--baseline", self.path("masked.jsonl"), "--label", "hand")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("READING hand dead-as-unhit pull z centre", p.stdout)
        self.assertIn("READING hand dead-as-unhit baseline (dead masked) pull z centre", p.stdout)
        self.assertRegex(p.stdout, r"READING hand dead-as-unhit fires rule \(any of x, y, z, t0: \|centre\| - 1\.645 se > 0\.10\): "
                                   r"(fires|does not fire) on this reading; no verdict before K09")
        self.assertNotRegex(p.stdout, r"\b(PASS|FAIL)\b")

    def test_a_baseline_of_another_readout_is_refused(self):
        """--baseline must be the main fit of the check's source readout (the masked dead control for E1a)."""
        p = run_tool("fires", "--check", "dead-as-unhit", "--product", self.path("e1a.jsonl"), "--truth", self.dead["truth"]["path"],
                     "--relabel-record", self.path("unhit.relabel.json"), "--source-readout", self.dead["readout"]["path"],
                     "--baseline", self.path("e1a.jsonl"), "--label", "hand")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("the baseline was not made from the check's source readout", p.stdout)

    def test_refusals(self):
        """Each refusal for the reason its name gives (review M3): the message is checked, not only the exit code."""
        source = ["--source-readout", self.dead["readout"]["path"]]
        cases = {
            "the masked product is not the relabelled one": ("dead-as-unhit", "masked.jsonl",
                                                             ["--relabel-record", self.path("unhit.relabel.json"), *source],
                                                             "not the fit of the relabelled readout"),
            "dead-as-unhit needs the relabel record": ("dead-as-unhit", "e1a.jsonl", source, "reads the relabel record and the source"),
            "dead-as-unhit needs the source readout": ("dead-as-unhit", "e1a.jsonl", ["--relabel-record", self.path("unhit.relabel.json")],
                                                       "reads the relabel record and the source"),
            "the source readout is not the truth file's": ("dead-as-unhit", "e1a.jsonl", ["--relabel-record", self.path("unhit.relabel.json"),
                                                                                          "--source-readout", self.path("unhit.readout")],
                                                           "not this truth file's readout"),
            "a forged record and readout": ("dead-as-unhit", "forged.jsonl", ["--relabel-record", self.path("forged.relabel.json"), *source],
                                            "not the relabelling of the source readout"),
            "the relabelled channels are not the fixture's": ("dead-as-unhit", "e1a.jsonl",
                                                              ["--relabel-record", self.path("short.relabel.json"), *source],
                                                              "not the fixture's dead channels"),
            "single-photon needs the variant product": ("single-photon", "e1a.jsonl", [], "the check reads main stratum 10"),
        }
        for name, (check, prod, extra, reason) in cases.items():
            with self.subTest(case=name):
                p = run_tool("fires", "--check", check, "--product", self.path(prod), "--truth", self.dead["truth"]["path"], *extra,
                             "--label", "hand")
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn("REFUSED", p.stdout)
                self.assertIn(reason, p.stdout)

    def test_the_single_photon_reading_refuses_truth_outside_main_b4_and_reads_it_inside(self):
        class B4(TimedGenerator):
            TRUTHS = [((1.2, -1.6, 1.1), stage1.unit((0.3, 0.9, -0.2)), 900.0), ((-2.0, 0.9, -1.5), stage1.unit((0.5, -0.5, 0.7)), 1400.0)]
        folder = Path(self.folder.name)
        for stratum, ok in ((10, True), (9, False)):
            with self.subTest(stratum=stratum):
                files = t09_fixture_files.stratum_files(B4(), "main", 1, stratum, 2, folder / f"s{stratum}", "b4")
                p = run_cli("fit", "--readout", files["readout"]["path"], "--product", str(folder / f"single{stratum}.jsonl"), "--product-id",
                            "single", "--configuration", str(VARIANT_FILE), "--likelihood", "charge-time", "--starts", "multistart")
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                p = run_tool("fires", "--check", "single-photon", "--product", str(folder / f"single{stratum}.jsonl"), "--truth",
                             files["truth"]["path"], "--label", "b4")
                self.assertEqual(p.returncode, 0 if ok else 2, p.stdout + p.stderr)
                if ok:
                    self.assertIn("READING b4 single-photon pull t0 centre", p.stdout)
                    self.assertIn("configuration " + single_photon.load().sha256, p.stdout)
                else:
                    self.assertIn("the check reads main stratum 10", p.stdout)

    def test_the_single_photon_reading_refuses_an_event_outside_the_bin(self):
        """Stratum 10 in the header, but one event's N_exp or radius outside B4, r/R_s [0.4, 0.7) (review M3)."""
        folder = Path(self.folder.name)
        for name, truth in (("N_exp 300", ((1.2, -1.6, 1.1), stage1.unit((0.3, 0.9, -0.2)), 300.0)),
                            ("r/R_s 0.2", ((0.6, -0.5, 0.5), stage1.unit((0.3, 0.9, -0.2)), 900.0))):
            class Outside(TimedGenerator):
                TRUTHS = [truth]
            with self.subTest(case=name):
                files = t09_fixture_files.stratum_files(Outside(), "main", 1, 10, 1, folder / f"out-{name[:5]}", "b4")
                p = run_cli("fit", "--readout", files["readout"]["path"], "--product", str(folder / f"out-{name[:5]}.jsonl"), "--product-id",
                            "x", "--configuration", str(VARIANT_FILE), "--likelihood", "charge-time", "--starts", "multistart")
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
                p = run_tool("fires", "--check", "single-photon", "--product", str(folder / f"out-{name[:5]}.jsonl"), "--truth",
                             files["truth"]["path"], "--label", "b4")
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn("outside main B4", p.stdout)


if __name__ == "__main__":
    unittest.main()
