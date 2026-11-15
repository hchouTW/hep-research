"""The single-photon-density variant of reco.light.channel-likelihood/1 (D4 build E1b; t04-values-v4.md section 9.4, "First-time
under a single-photon density": a negative check [R7], main B4 events at r/R_s [0.4, 0.7), "refit with a single-photon density in
place of first-arrival"; t04-prereg.md, "Required negative case"). The reference names this the misuse the check must catch: "Single-
photon time density used for bright channels, biasing the vertex and time" (the hep-detector skill's photon-likelihood reference,
"Several photons on one channel" and its list of misuses).

A whole configuration, never a flag: the variant runs only from its own configuration file, format FORMAT (light-likelihood-configuration/1
-single-photon), whose constants are the main file's; the main reader (configuration.load) refuses it by its format, and this module's
reader refuses the main file. Its products are light-likelihood-product/3-single-photon (product.py), whose header names this
likelihood and this configuration.

What differs, and only that: the joint term of a hit channel. The main recipe (arrival_response.ArrivalResponse) uses the density of
the first of the channel's photons given its charge,

    p(q, t) = sum_{n>=1} Pois(n; m) N(q; n mu_c, n sigma_c^2) n f(t) (1 - F(t))^{n-1};

this variant (SinglePhotonArrival) reads the recorded time as if it were one photon's,

    p(q, t) = f(q | m) f(t),    f(t) = lambda(t) / m,    lambda(t) = mu_s phi((t - tau) / sigma) / sigma + rho [0 <= t < W],

with f(q | m) stage 1's charge density (charge_response.ChargeResponse.log_hit_density) and lambda the main recipe's intensity (signal
plus the dark noise mixture, m = mu_s + dark its integral over the real line, so f integrates to one). A saturated channel takes
P(q >= C | m) f(t) (charge_response.ChargeResponse.log_at_or_above). The two agree when a hit holds one photon (n = 1, m << 1) and
part where many photons arrive (the first comes early). The unhit term, the charge model, the light model, the fit, the multistart
starts and budget, the Hessian and the per-channel probability check are the main recipe's objects, used unchanged: Model swaps the
model's `arrival` attribute and nothing else, so joint.channel_terms and everything above it run the same code.

Derivatives in (mu_s, tau), with z = (t - tau)/sigma, phi_s = phi(z)/sigma, pi_s = mu_s phi_s / lambda, r = phi_s / lambda and (c, c',
c'') the charge term and its derivatives in m:

    l        = c + ln lambda - ln m
    l_mu     = c' + r - 1/m
    l_tau    = pi_s z / sigma
    l_mumu   = c'' - r^2 + 1/m^2
    l_mutau  = r z (1 - pi_s) / sigma
    l_tautau = pi_s (z^2 - 1)/sigma^2 - (pi_s z / sigma)^2

The main recipe's code path does not pass through this module: configuration.load, likelihood.Model and arrival_response are those of
the main recipe, and photon_likelihood.py builds this Model only for a configuration of FORMAT.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy

from . import configuration, likelihood
from .arrival_response import ArrivalResponse
from .charge_response import HALF_LOG_TWO_PI

FORMAT = "light-likelihood-configuration/1-single-photon"
DEFAULT = Path(__file__).resolve().parent.parent / "t09-sphere-1-single-photon.configuration.json"
LIKELIHOOD = ("charge and time jointly, the hit channel's time read as one photon's arrival density (signal and dark noise) in place of "
              "the first arrival: t04-values-v4.md section 9.4's negative-check variant, all live channels (D4 E1b)")


class SinglePhotonArrival(ArrivalResponse):
    """The main recipe's arrival model with the two hit terms replaced: charge density times one photon's time density."""

    def log_joint_density(self, q, t, mu_s, tau):
        """ln f(q | m) + ln f(t) of a hit channel, per unit charge and per ns, and its derivatives in (mu_s, tau)."""
        q = numpy.asarray(q, float)
        return self._single(t, mu_s, tau, lambda m: self.charge.log_hit_density(q, m))

    def log_joint_at_or_above(self, level, t, mu_s, tau):
        """ln P(q >= level | m) + ln f(t) (the censored term of a saturated channel), and its derivatives in (mu_s, tau)."""
        t = numpy.asarray(t, float)
        level = numpy.broadcast_to(numpy.asarray(level, float), t.shape)
        if numpy.any(level <= 0):
            raise ValueError("level must be positive")
        return self._single(t, mu_s, tau, lambda m: self.charge.log_at_or_above(level, m))

    def _single(self, t, mu_s, tau, charge_term):
        t = numpy.asarray(t, float)
        mu_s = numpy.asarray(mu_s, float)
        tau = numpy.asarray(tau, float)
        if t.size == 0:
            return tuple(numpy.zeros(0) for _ in range(6))
        if numpy.any(~numpy.isfinite(mu_s)) or numpy.any(mu_s <= 0) or numpy.any(~numpy.isfinite(t)) \
                or numpy.any(~numpy.isfinite(tau)):
            raise ValueError("mu_s must be positive and finite, t and tau finite")
        sigma = self.time_spread
        m = mu_s + self.dark_mean
        c0, c1, c2 = charge_term(m)
        z = (t - tau) / sigma
        ln_phi = -0.5 * z * z - math.log(sigma) - HALF_LOG_TWO_PI
        ln_signal = numpy.log(mu_s) + ln_phi
        in_window = (t >= 0.0) & (t < self.window)
        ln_lambda = numpy.logaddexp(ln_signal, numpy.where(in_window, math.log(self.rate), -numpy.inf))
        pi_s = numpy.exp(ln_signal - ln_lambda)
        r = numpy.exp(ln_phi - ln_lambda)
        l0 = c0 + ln_lambda - numpy.log(m)
        l_mu = c1 + r - 1.0 / m
        l_tau = pi_s * z / sigma
        l_mumu = c2 - r * r + 1.0 / (m * m)
        l_mutau = r * z * (1.0 - pi_s) / sigma
        l_tautau = pi_s * (z * z - 1.0) / sigma ** 2 - (pi_s * z / sigma) ** 2
        return l0, l_mu, l_tau, l_mumu, l_mutau, l_tautau


class Model(likelihood.Model):
    """likelihood.Model for a configuration of FORMAT, its arrival model SinglePhotonArrival; every other part the main one."""

    def __init__(self, cfg: configuration.Configuration, geometry=None):
        if cfg.format != FORMAT:
            raise configuration.ConfigurationError(f"the single-photon model needs a configuration of format {FORMAT}")
        super().__init__(cfg, geometry)
        self.arrival = SinglePhotonArrival(self.response, cfg.time_spread_ns, cfg.dark_mean_per_window, cfg.window_ns)


def load(path=None) -> configuration.Configuration:
    """The variant's configuration: the main reader's rules, with this format (the main file is refused)."""
    return configuration.load(DEFAULT if path is None else path, FORMAT)


def load_any(path=None) -> configuration.Configuration:
    """A configuration for the CLI: a file of FORMAT is this variant's; anything else goes to the main reader unchanged (no path:
    the main default), which refuses what it refuses."""
    if path is not None:
        try:
            doc = json.loads(Path(path).read_bytes())
        except (OSError, ValueError):
            doc = None
        if isinstance(doc, dict) and doc.get("format") == FORMAT:
            return load(path)
    return configuration.load(path)


def model_for(cfg: configuration.Configuration) -> likelihood.Model:
    """The main model for the main configuration, this variant's for its own; any other format is refused."""
    if cfg.format == configuration.FORMAT:
        return likelihood.Model(cfg)
    if cfg.format == FORMAT:
        return Model(cfg)
    raise configuration.ConfigurationError(f"configuration format {cfg.format!r} is neither {configuration.FORMAT} nor {FORMAT}")
