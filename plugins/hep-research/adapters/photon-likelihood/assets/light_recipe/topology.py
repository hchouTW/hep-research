"""The topology step of T09 (D3 stage 4; t07-t09-task-sheets.md, T09: steps "... then topology", non-goal "topology beyond the
required two-hypothesis check"; the reference, "Hypothesis fits" and "Topologies and hypothesis comparison"): the two-source
hypothesis H2 on the joint charge-time likelihood, and the choice between H1 (stage 3's multistart fit) and H2 by t04-values-v4.md
section 7, "Topology hypotheses". Data side: every start comes from the readout and H1's fit alone; no truth, no generator, no
random numbers.

H2 (case O-h2-likelihood of the D3 stage 4 report). Both sources' light is summed per channel: mu_i = mu_1i + mu_2i, m_i = mu_i +
dark. The arrivals at one channel form one Poisson process of intensity

    lambda(t) = mu_1 phi((t - tau_1)/sigma)/sigma + mu_2 phi((t - tau_2)/sigma)/sigma + rho,   tau_ji = t0_j + d_ji / v,

each source with its own emission time t0_j (rebuild, case R-h2-parameters: v4 section 7's 14 parameters, as the frozen
calc-t09-null-h2.py's nll2; the fixture's sources share one t0, which H2 does not assume). Stage 2's joint term (arrival_response) holds for any
intensity (no photon before t, one at t, k after, each photon's charge independent of its time), so the hit term is
lambda(t) e^{-Lambda_<(t)} sum_k Pois(k; Lambda_>(t)) w_{k+1}, the censored term the same with the charge tail, the unhit term
stage 1's no-hit term at m_i: one threshold model for hit and no-hit terms, so the per-channel sum check at H2's mean counts is
the sheet's stop for H2 too. Dead and disabled channels stay out.

Derivatives (case O-h2-derivatives), in the channel variables y = (mu_1, tau_1, mu_2, tau_2): with G(L) = -L + ln A_0(L),
G' = A_1/A_0 - 1, G'' = A_2/A_0 - (A_1/A_0)^2 (arrival_response),

    dl  = grad lambda / lambda - grad Lambda_< + G' grad Lambda_>
    d2l = H_lambda / lambda - grad lambda grad lambda^T / lambda^2 - H_< + G' H_> + G'' grad Lambda_> grad Lambda_>^T,

every product of A_1/A_0 or A_2/A_0 with Q(z_j), mu_j phi_j or phi_j formed in log space, as arrival_response does. They reduce
to stage 2's single-source terms as mu_2 -> 0. The chain to the 14 fit coordinates
p = (x1, y1, z1, a1, b1, E1, t0_1, x2, y2, z2, a2, b2, E2, t0_2), 7 per source, takes each source's dmu/dp and d2mu/dp2 from stage 1's Objective (each
source in its own chart about its own reference direction) and dtau_j/dx_j = -u/v, d2tau_j/dx_j2 = (I - u u^T)/(d v),
dtau_j/dt0_j = 1, as stage 2.

The domain (case O-h2-domain): each vertex and E_vis in stage 1's domain, each t0_j in stage 2's, the total yield sum_i mu_i at most
YIELD_DOMAIN; outside it the objective is total (ln L = -inf, zero gradient, Hessian -I).

The fit (case O-h2-fit): stage 1's and 2's rounds, convergence rule, failure kinds and covariance (fit.py's constants), for two
charts: a round ends at SciPy's status 0 or 2, or (status 99, never convergence) once either chart step exceeds
JOINT_CHART_RADIUS; the fit ends when both chart steps are below CHART_STEP; convergence by the Newton decrement. Every point
recorded carries its ln L. The covariance is 14 x 14 in (x1, y1, z1, u1_1, u2_1, E1, t0_1, x2, y2, z2, u1_2, u2_2, E2, t0_2).

Starts (case R-h2-starts), 8, in a budget file of their own, format light-likelihood-topology/1, recorded by hash (K10). With
r_i = max(q_i - mu_c m_i(H1), 0) on hit channels (the positive residual charge under H1's fit), M(w) stage 1's moment rule on
weights w, E(w; x, d) = sum w / (1000 sum_live s_i(x, d)) and T(x; S) the median over channels in S of t_i - |P_i - x| / v:
- starts 0 to 5 keep source 1 = H1's fit (vertex, direction, E_vis, t0) and build source 2 from the residual:
  "h1 + residual" (x2, d2) = M(r), t0_2 = T(x2; r > 0); "h1 + residual, reversed" (x2, -d2); "h1 + residual, mirrored"
  (-x2, -d2), T(-x2; r > 0); "h1 + residual, turned" (x2, e1(d2)), section 7's frame; "h1 + largest residual" k = argmax r,
  x2 = 0.5 P_k, d2 = P_k / |P_k|, t0_2 = t_k - |P_k - x2| / v; "h1 + mirrored h1" (-x_H1, -d_H1), T(-x_H1; r > 0); each
  E_2 = E(r; x2, d2) at its own point;
- "charge split": the hit channels split by the plane through the charge centroid c normal to the leading eigenvector a of
  sum q_i (P_i - c)(P_i - c)^T (largest-magnitude component positive), half 0 (P_i - c) . a >= 0; each half h gives
  M(q_h), E(q_h; ...), T(x_h; q_h > 0); "charge split, reversed": both directions reversed, E at the reversed directions.
A start that cannot be formed is recorded as failed, kind no-start-point, with no point.

The choice (cases O-h2-anchor, O-h2-report, O-statistic): H2 is fitted only where H1's reported fit converged. H2's reported
point is the start with the highest recorded ln L, converged or not (a tie within the budget's tolerance goes to the lowest
index): any recorded H2 point is a valid lower bound on H2's maximum. lnL_2 = max(that ln L, lnL_1), since H1 is H2's boundary
at zero second yield (section 7). H2 is chosen if and only if 2 (lnL_2 - lnL_1) >= PENALTY, the frozen 30 of section 7.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy
from scipy import linalg, optimize, special

from . import fit, joint, light_model
from .arrival_response import ArrivalResponse
from .charge_response import HALF_LOG_TWO_PI
from .likelihood import YIELD_DOMAIN, Objective as ChargeObjective, _check_model, frame, in_domain, sum_tolerance

PENALTY = 30.0   # t04-values-v4.md section 7, "Topology hypotheses": H2 iff 2(lnL_2 - lnL_1) >= 30; a frozen design choice, never tuned
FORMAT = "light-likelihood-topology/1"
DEFAULT = Path(__file__).resolve().parent.parent / "t09-topology-2.budget.json"
KEYS = {"format", "starts", "tie_tolerance"}
RULES = {
    "h1 + residual": "source 1 H1's fit; source 2 (x2, d2) = M(r), E(r; x2, d2), t0_2 = T(x2; r > 0)",
    "h1 + residual, reversed": "source 1 H1's fit; source 2 (x2, -d2), E(r; x2, -d2), t0_2 = T(x2; r > 0)",
    "h1 + residual, mirrored": "source 1 H1's fit; source 2 (-x2, -d2), E(r; -x2, -d2), t0_2 = T(-x2; r > 0)",
    "h1 + residual, turned": "source 1 H1's fit; source 2 (x2, e1(d2)), section 7's frame at d2, E(r; x2, e1), t0_2 = T(x2; r > 0)",
    "h1 + largest residual": ("source 1 H1's fit; source 2 at 0.5 P_k, direction P_k / |P_k|, k the channel of largest r, "
                              "E(r; ...), t0_2 = t_k - |P_k - x2| / v"),
    "h1 + mirrored h1": "source 1 H1's fit; source 2 (-x_H1, -d_H1), E(r; -x_H1, -d_H1), t0_2 = T(-x_H1; r > 0)",
    "charge split": ("the hit channels split by the plane through the charge centroid normal to the leading eigenvector of the "
                     "charge-weighted scatter (largest-magnitude component positive), half 0 on its positive side; each half h: "
                     "M(q_h), E(q_h; ...), T(x_h; q_h > 0)"),
    "charge split, reversed": "as charge split with both directions reversed, E at the reversed directions",
}
H1_ANCHORED = ("h1 + residual", "h1 + residual, reversed", "h1 + residual, mirrored", "h1 + residual, turned", "h1 + largest residual",
               "h1 + mirrored h1")
NOTATION = ("r_i = max(q_i - mu_c m_i(H1), 0) on hit channels; M(w) stage 1's moment rule on weights w (vertex 0.5 x the w-weighted "
            "sensor centroid, direction the w-weighted sum of unit vectors from it to the sensors); E(w; x, d) = sum w / (1000 "
            "sum_live s_i(x, d)); T(x; S) the median over channels in S of t_i - |P_i - x| / v")
NO_START = "no-start-point"
FAILURES = fit.FAILURES + (NO_START,)
SIZE = 14
BLOCK = 7                     # per source: x, y, z, a, b, E_vis, t0
REPORT_BEST = "highest recorded ln L"
REPORT_TIE = "tie within tolerance, lowest index"
REPORT_NONE = "no H2 point"
FROM_H2 = "h2"
FROM_BOUNDARY = "h1 boundary"
CHOICE_RULE = ("H2 if and only if 2 (lnL_2 - lnL_1) >= 30 (t04-values-v4.md section 7), lnL_1 the multistart H1 fit's, lnL_2 the "
               "larger of H2's reported ln L and lnL_1 (H1 is H2's boundary at zero second yield); otherwise H1")
CHOICE_H1_FAILED = "H1 failed: no choice"
REPORT_TEXT = ("H2's reported point is the start with the highest recorded ln L, converged or not; a tie within tie_tolerance goes to "
               "the lowest index")
FIT_TEXT = ("the joint charge-time likelihood with both sources' light summed per channel, each source its own t0; 14 coordinates "
            "(x1, y1, z1, a1, b1, E1, t0_1, x2, y2, z2, a2, b2, E2, t0_2); stage 1's and 2's rounds, convergence rule, failure kinds "
            "and covariance for two charts; the start notation: " + NOTATION)


class BudgetError(ValueError):
    """The topology budget file is refused."""


@dataclass(frozen=True)
class TopologyBudget:
    format: str
    starts: tuple
    tie_tolerance: float
    sha256: str

    def header(self) -> dict:
        return {"format": self.format, "sha256": self.sha256, "starts": list(self.starts), "tie_tolerance": self.tie_tolerance}


def _refuse_constant(name):
    raise ValueError(f"non-finite number {name}")


def load(path=None) -> TopologyBudget:
    path = Path(path) if path is not None else DEFAULT
    try:
        content = path.read_bytes()
        doc = json.loads(content, parse_constant=_refuse_constant)
    except (OSError, ValueError, RecursionError) as exc:
        raise BudgetError(f"topology budget cannot be read: {exc}") from None
    if not isinstance(doc, dict) or set(doc) != KEYS:
        raise BudgetError(f"topology budget keys must be exactly {sorted(KEYS)}")
    if doc["format"] != FORMAT:
        raise BudgetError(f"topology budget format must be {FORMAT}")
    starts = doc["starts"]
    if not (isinstance(starts, list) and starts and all(isinstance(s, str) for s in starts)):
        raise BudgetError("starts must be a non-empty list of start names")
    unknown = [s for s in starts if s not in RULES]
    if unknown:
        raise BudgetError(f"unknown start names {unknown}; known: {sorted(RULES)}")
    if len(set(starts)) != len(starts):
        raise BudgetError("a start name is repeated")
    tie = doc["tie_tolerance"]
    if isinstance(tie, bool) or not isinstance(tie, (int, float)) or not math.isfinite(tie) or tie <= 0:
        raise BudgetError("tie_tolerance must be a positive finite number")
    return TopologyBudget(doc["format"], tuple(starts), float(tie), hashlib.sha256(content).hexdigest())


# --- the two-source point and its mean counts -------------------------------------------------------------------------------

@dataclass(frozen=True)
class Point:
    vertices: numpy.ndarray       # (2, 3), m
    directions: numpy.ndarray     # (2, 3), unit vectors
    e_vis: numpy.ndarray          # (2,)
    t0: numpy.ndarray             # (2,), ns: each source its own emission time


def signal_means(model, point: Point) -> numpy.ndarray:
    """mu_ji (2, C): the expected signal photons of each source per channel."""
    return numpy.array([model.scale * point.e_vis[j] * light_model.shape(model, point.vertices[j], point.directions[j])
                        for j in range(2)])


def expected_counts(model, point: Point) -> numpy.ndarray:
    """m_i = mu_1i + mu_2i + dark, the mean count per channel in the window."""
    return signal_means(model, point).sum(axis=0) + model.dark


def in_domain_two(model, point: Point, mu=None) -> bool:
    if not all(in_domain(model, point.vertices[j], float(point.e_vis[j])) for j in range(2)):
        return False
    if not all(joint.t0_in_domain(model, float(point.t0[j])) for j in range(2)):
        return False
    if mu is None:
        return True
    return bool(numpy.all(numpy.isfinite(mu)) and mu.sum() <= YIELD_DOMAIN)


def probability_check(model, event, point: Point) -> dict:
    """P(hit) + P(no hit) per live channel at H2's mean counts m_1 + m_2 + dark (likelihood.probability_check's rule)."""
    _check_model(model, event)
    mu = signal_means(model, point)
    if not in_domain_two(model, point, mu):
        raise ValueError("the probability check was asked outside H2's domain")
    m = mu.sum(axis=0) + model.dark
    live = event.live
    p_hit, p_no = model.response.probability_sums(m[live])
    deviation = numpy.abs(p_hit + p_no - 1.0)
    ratio = deviation / sum_tolerance(m[live])
    bad = ~(ratio <= 1.0)
    channels = numpy.flatnonzero(live)
    return {"channels": int(live.sum()), "failures": int(bad.sum()),
            "max_abs_deviation": float(deviation.max()) if deviation.size else 0.0,
            "largest_ratio": float(ratio.max()) if ratio.size else 0.0,
            "failed_channels": [int(c) for c in channels[bad][:10]]}


# --- the per-channel terms --------------------------------------------------------------------------------------------------

def _hit_terms(model, value, t, mu, tau, censored):
    """(l, g (n, 4), h (n, 4, 4)) of hit channels: value the charge (open) or the saturation level (censored)."""
    arrival = model.arrival
    mc, sc = arrival.charge.photon_charge_mean, arrival.charge.photon_charge_sigma
    sigma, rate, window = arrival.time_spread, arrival.rate, arrival.window
    if numpy.any(~numpy.isfinite(mu)) or numpy.any(mu <= 0) or numpy.any(~numpy.isfinite(t)) or numpy.any(~numpy.isfinite(tau)):
        raise ValueError("mu must be positive and finite, t and tau finite")
    value = numpy.broadcast_to(numpy.asarray(value, float), t.shape)
    def tail_weight(n, owner):            # the censored term: P(charge of n photons >= the level)
        return special.log_ndtr((n * mc - value[owner]) / (sc * numpy.sqrt(n)))

    def density_weight(n, owner):         # the open term: the charge density of n photons at q
        s = sc * numpy.sqrt(n)
        z = (value[owner] - n * mc) / s
        return -0.5 * z * z - numpy.log(s) - HALF_LOG_TWO_PI
    weight = tail_weight if censored else density_weight
    z = (t[None, :] - tau) / sigma                                       # (2, n)
    ln_phi = -0.5 * z * z - math.log(sigma) - HALF_LOG_TWO_PI
    ln_mu = numpy.log(mu)
    ln_signal = ln_mu + ln_phi
    in_window = (t >= 0.0) & (t < window)
    ln_rate = numpy.where(in_window, math.log(rate), -numpy.inf)
    ln_lambda = numpy.logaddexp(numpy.logaddexp(ln_signal[0], ln_signal[1]), ln_rate)
    clipped = numpy.clip(t, 0.0, window)
    cdf, sf = special.ndtr(z), special.ndtr(-z)
    before = (mu * cdf).sum(axis=0) + rate * clipped
    dark_after = rate * (window - clipped)
    ln_sf = special.log_ndtr(-z)
    with numpy.errstate(divide="ignore"):
        ln_after = numpy.logaddexp(numpy.logaddexp(ln_mu[0] + ln_sf[0], ln_mu[1] + ln_sf[1]), numpy.log(dark_after))
    ln_a = ArrivalResponse._k_sums(value / mc, ln_after, weight, censored)
    a1, a2 = ln_a[1] - ln_a[0], ln_a[2] - ln_a[0]
    l0 = ln_lambda - before - numpy.exp(ln_after) + ln_a[0]
    # grad Lambda_> in y = (mu_1, tau_1, mu_2, tau_2): (Q_1, s_1, Q_2, s_2), all positive: kept as logs
    ln_x = numpy.array([ln_sf[0], ln_signal[0], ln_sf[1], ln_signal[1]])
    r1 = numpy.exp(a1 + ln_x)                                            # (A_1/A_0) X
    r = numpy.exp(ln_phi - ln_lambda)                                    # phi_j / lambda
    pi = numpy.exp(ln_signal - ln_lambda)                                # the share of source j in lambda
    r1_phi = numpy.exp(a1 + ln_phi)
    n = t.size
    g = numpy.empty((n, 4))
    h = numpy.empty((n, 4, 4))
    lam_grad = numpy.array([r[0], pi[0] * z[0] / sigma, r[1], pi[1] * z[1] / sigma])   # grad lambda / lambda
    for j in range(2):
        g[:, 2 * j] = r[j] - cdf[j] + (r1[2 * j] - sf[j])
        g[:, 2 * j + 1] = pi[j] * z[j] / sigma + r1[2 * j + 1]
    for a in range(4):
        for b in range(a, 4):
            g2 = numpy.exp(a2 + ln_x[a] + ln_x[b]) - r1[a] * r1[b]       # G'' X_a X_b
            ja, jb = a // 2, b // 2
            if ja == jb and a % 2 == 0 and b % 2 == 0:                   # (mu_j, mu_j)
                value_ab = -r[ja] * r[ja] + g2
            elif ja == jb and a % 2 == 0:                                # (mu_j, tau_j)
                value_ab = r[ja] * z[ja] * (1.0 - pi[ja]) / sigma + r1_phi[ja] + g2
            elif ja == jb:                                               # (tau_j, tau_j)
                value_ab = pi[ja] * (z[ja] * z[ja] - 1.0) / sigma ** 2 - (pi[ja] * z[ja] / sigma) ** 2 + r1[b] * z[ja] / sigma + g2
            else:                                                        # across the sources: - (grad lambda / lambda) products
                value_ab = -lam_grad[a] * lam_grad[b] + g2
            h[:, a, b] = value_ab
            h[:, b, a] = value_ab
    return l0, g, h


def channel_terms(model, tev, mu, tau):
    """(l (C,), dl/dy (C, 4), d2l/dy2 (C, 4, 4)) per channel, y = (mu_1, tau_1, mu_2, tau_2); mu, tau (2, C). Zero for dead and
    disabled channels, which do not enter; the time derivatives zero for unhit channels."""
    ev = tev.event
    channels = ev.channels
    mu = numpy.asarray(mu, float)
    tau = numpy.asarray(tau, float)
    l = numpy.zeros(channels)
    g = numpy.zeros((channels, 4))
    h = numpy.zeros((channels, 4, 4))
    if ev.unhit.any():
        sel = ev.unhit
        l0, l1, l2 = model.response.log_no_hit(mu[0, sel] + mu[1, sel] + model.dark)
        l[sel] = l0
        for a in (0, 2):
            g[sel, a] = l1
            for b in (0, 2):
                h[sel, a, b] = l2
    for mask, censored in ((ev.hit & ~ev.saturated, False), (ev.hit & ev.saturated, True)):
        if mask.any():
            value = ev.saturation_charge if censored else ev.charge[mask]
            l[mask], g[mask], h[mask] = _hit_terms(model, value, tev.time[mask], mu[:, mask], tau[:, mask], censored)
    return l, g, h


def log_likelihood(model, tev, point: Point) -> float:
    _check_model(model, tev.event)
    if not in_domain_two(model, point):
        return -math.inf
    mu = signal_means(model, point)
    if not in_domain_two(model, point, mu):
        return -math.inf
    tau = numpy.array([point.t0[j] + joint.arrival_delays(model, point.vertices[j])[0] for j in range(2)])
    return float(channel_terms(model, tev, mu, tau)[0].sum())


# --- the objective in the fit coordinates -----------------------------------------------------------------------------------

class Objective:
    """ln L of H2 in p = (x1, y1, z1, a1, b1, E1, t0_1, x2, y2, z2, a2, b2, E2, t0_2), each source in its chart about d_refs[j],
    with its gradient and Hessian."""

    def __init__(self, model, tev, d_refs):
        self.model = model
        self.tev = tev
        self.charge = [ChargeObjective(model, tev.event, d) for d in d_refs]
        self._value_cache = (None, None)
        self._full_cache = (None, None)

    def direction(self, j: int, a: float, b: float):
        return self.charge[j].direction(a, b)

    def point_of(self, p) -> Point:
        p = numpy.asarray(p, float)
        return Point(numpy.array([p[0:3], p[7:10]]), numpy.array([self.direction(0, p[3], p[4]), self.direction(1, p[10], p[11])]),
                     numpy.array([p[5], p[12]]), numpy.array([p[6], p[13]]))

    def _inside(self, p) -> bool:
        return all(in_domain(self.model, p[b:b + 3], p[b + 5]) and joint.t0_in_domain(self.model, p[b + 6]) for b in (0, BLOCK))

    def _parts(self, p):
        """(mu (2, C), [dmu_j/dp6 (C, 6)], tau (2, C), [(u_j, d_j)]) or None outside the domain."""
        if not self._inside(p):
            return None
        mus, grads = zip(*(self.charge[j]._mu_gradient(p[BLOCK * j:BLOCK * j + 6]) for j in range(2)))
        mu = numpy.array(mus)
        if not (numpy.all(numpy.isfinite(mu)) and mu.sum() <= YIELD_DOMAIN):
            return None
        delays = [joint.arrival_delays(self.model, p[BLOCK * j:BLOCK * j + 3]) for j in range(2)]
        tau = numpy.array([p[BLOCK * j + 6] + delays[j][0] for j in range(2)])
        return mu, list(grads), tau, [(delays[j][1], delays[j][2]) for j in range(2)]

    def value(self, p) -> float:
        p = numpy.asarray(p, float)
        key = p.tobytes()
        if self._value_cache[0] == key:
            return self._value_cache[1]
        parts = self._parts(p)
        out = -math.inf if parts is None else float(channel_terms(self.model, self.tev, parts[0], parts[2])[0].sum())
        self._value_cache = (key, out)
        return out

    def derivatives(self, p):
        """(ln L, gradient (14,), Hessian (14, 14)) at p; outside the domain (-inf, zeros, -I)."""
        p = numpy.asarray(p, float)
        key = p.tobytes()
        if self._full_cache[0] == key:
            return self._full_cache[1]
        parts = self._parts(p)
        if parts is None:
            return (-math.inf, numpy.zeros(SIZE), -numpy.eye(SIZE))
        mu, grads, tau, geometry = parts
        l, gy, hy = channel_terms(self.model, self.tev, mu, tau)
        speed = self.model.cfg.photon_speed_m_per_ns
        channels = mu.shape[1]
        jac = numpy.zeros((channels, 4, SIZE))
        for j in range(2):
            u, _ = geometry[j]
            b = BLOCK * j
            jac[:, 2 * j, b:b + 6] = grads[j]
            jac[:, 2 * j + 1, b:b + 3] = -u / speed
            jac[:, 2 * j + 1, b + 6] = 1.0                               # tau_j = t0_j + d_j / v
        gradient = numpy.einsum("ck,ckp->p", gy, jac)
        hessian = numpy.einsum("ckp,ckq->pq", jac, numpy.einsum("ckl,clq->ckq", hy, jac))
        for j in range(2):
            u, dist = geometry[j]
            b = BLOCK * j
            block = slice(b, b + 6)
            hessian[block, block] += numpy.einsum("c,cab->ab", gy[:, 2 * j], self.charge[j].second_derivatives(p[block], grads[j]))
            second_t = (numpy.eye(3)[None, :, :] - u[:, :, None] * u[:, None, :]) / (dist * speed)[:, None, None]
            hessian[b:b + 3, b:b + 3] += numpy.einsum("c,cab->ab", gy[:, 2 * j + 1], second_t)
        hessian = 0.5 * (hessian + hessian.T)
        out = (float(l.sum()), gradient, hessian)
        self._full_cache = (key, out)
        self._value_cache = (key, out[0])
        return out


# --- the fit ----------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class TwoSourceResult:
    status: str                         # converged | failed
    failure: str | None                 # one of FAILURES, or None
    point: Point | None
    covariance: numpy.ndarray | None    # (14, 14) or None
    uncertainty_status: str             # ok | not-positive-definite | non-finite | not-formed
    ln_likelihood: float | None         # at the point, wherever there is one
    gradient_norm: float | None
    newton_decrement: float | None
    iterations: int
    rounds: int


def _failed(failure, iterations=0, rounds=0, point=None, ln_l=None, grad=None, uncertainty="not-formed", decrement=None):
    return TwoSourceResult("failed", failure, point, None, uncertainty, ln_l, grad, decrement, iterations, rounds)


def _chart_exit(radius):
    def callback(intermediate_result):
        x = intermediate_result.x
        if max(math.hypot(x[3], x[4]), math.hypot(x[10], x[11])) > radius:
            raise StopIteration
    return callback


def _coordinates(point: Point):
    return numpy.r_[point.vertices[0], 0.0, 0.0, point.e_vis[0], point.t0[0], point.vertices[1], 0.0, 0.0, point.e_vis[1], point.t0[1]]


def fit_two_source(model, tev, start: Point) -> TwoSourceResult:
    """H2's fit from one start (case O-h2-fit)."""
    directions = [numpy.asarray(d, float) / numpy.linalg.norm(d) for d in start.directions]
    point = Point(numpy.asarray(start.vertices, float), numpy.array(directions), numpy.asarray(start.e_vis, float),
                  numpy.asarray(start.t0, float))
    iterations = 0
    for rounds in range(1, fit.MAX_ROUNDS + 1):
        objective = Objective(model, tev, point.directions)
        p0 = _coordinates(point)
        if not math.isfinite(objective.value(p0)):
            return _failed("non-finite", iterations, rounds - 1)
        res = optimize.minimize(lambda p: -objective.value(p), p0, method="trust-exact",
                                jac=lambda p: -objective.derivatives(p)[1], hess=lambda p: -objective.derivatives(p)[2],
                                options={"gtol": fit.GTOL, "maxiter": fit.MAX_ITERATIONS}, callback=_chart_exit(fit.JOINT_CHART_RADIUS))
        iterations += int(res.nit)
        if not (numpy.all(numpy.isfinite(res.x)) and math.isfinite(objective.value(res.x))):
            return _failed("non-finite", iterations, rounds)
        point = objective.point_of(res.x)
        ln_l = objective.value(res.x)
        if res.nit >= fit.MAX_ITERATIONS:
            return _failed("iteration-budget", iterations, rounds, point, ln_l)
        chart_exit = res.status == fit.CALLBACK_STOP
        if res.status not in (0, 2) and not chart_exit:
            return _failed("not-converged", iterations, rounds, point, ln_l)
        if max(math.hypot(res.x[3], res.x[4]), math.hypot(res.x[10], res.x[11])) < fit.CHART_STEP and not chart_exit:
            break
    else:
        return _failed("iteration-budget", iterations, fit.MAX_ROUNDS, point, log_likelihood(model, tev, point))
    recentred = Objective(model, tev, point.directions)
    ln_l, gradient, hessian = recentred.derivatives(_coordinates(point))
    grad_norm = float(numpy.linalg.norm(gradient))
    if not (numpy.all(numpy.isfinite(hessian)) and math.isfinite(ln_l)):
        return _failed("no-finite-covariance", iterations, rounds, point, ln_l, grad_norm, "non-finite")
    try:
        factor = linalg.cho_factor(-hessian, lower=True)
    except linalg.LinAlgError:
        return _failed("no-finite-covariance", iterations, rounds, point, ln_l, grad_norm, "not-positive-definite")
    covariance = linalg.cho_solve(factor, numpy.eye(SIZE))
    covariance = 0.5 * (covariance + covariance.T)
    decrement = float(gradient @ covariance @ gradient)
    if not numpy.all(numpy.isfinite(covariance)) or numpy.any(numpy.diag(covariance) <= 0):
        return _failed("no-finite-covariance", iterations, rounds, point, ln_l, grad_norm, "non-finite")
    if not decrement <= fit.DECREMENT_TOL:
        return _failed("not-converged", iterations, rounds, point, ln_l, grad_norm, decrement=decrement)
    return TwoSourceResult("converged", None, point, covariance, "ok", ln_l, grad_norm, decrement, iterations, rounds)


# --- the starts -------------------------------------------------------------------------------------------------------------

def _moment_point(model, weights):
    """M(w): stage 1's moment rule on per-channel weights, (vertex, direction) or None where it cannot be formed."""
    total = float(weights.sum())
    if not total > 0:
        return None
    used = weights > 0
    positions = model.geometry.positions
    vertex = fit.SEED_VERTEX_FACTOR * (weights[:, None] * positions).sum(axis=0) / total
    toward = positions[used] - vertex
    pull = (weights[used][:, None] * toward / numpy.linalg.norm(toward, axis=1)[:, None]).sum(axis=0)
    norm = float(numpy.linalg.norm(pull))
    if not norm > 0:
        return None
    return vertex, pull / norm


def _yield(model, event, weights, vertex, direction) -> float:
    """E(w; x, d) = sum w / (1000 sum_live s_i(x, d))."""
    return float(weights.sum() / (model.scale * light_model.shape(model, vertex, direction)[event.live].sum()))


def _median_t0(model, tev, vertex, weights) -> float:
    """T(x; S): stage 2's median rule over the channels with weight above 0."""
    used = weights > 0
    dist = numpy.linalg.norm(model.geometry.positions[used] - vertex, axis=1)
    return float(numpy.median(tev.time[used] - dist / model.cfg.photon_speed_m_per_ns))


def _residual(model, tev, h1):
    ev = tev.event
    m = light_model.expected(model, h1.vertex, h1.direction, h1.e_vis)
    return numpy.where(ev.hit, numpy.maximum(numpy.nan_to_num(ev.charge) - model.cfg.photon_charge_mean * m, 0.0), 0.0)


def _h1_anchored(model, tev, h1, name, residual):
    """Starts 0 to 5: source 1 is H1's fit, source 2 from the residual (case R-h2-starts)."""
    ev = tev.event
    base = _moment_point(model, residual)
    if base is None:
        return None
    x2, d2 = base
    t_k = None
    if name == "h1 + residual, reversed":
        d2 = -d2
    elif name == "h1 + residual, mirrored":
        x2, d2 = -x2, -d2
    elif name == "h1 + residual, turned":
        d2 = frame(d2)[0]
    elif name == "h1 + largest residual":
        k = int(numpy.argmax(residual))
        position = model.geometry.positions[k]
        x2 = fit.SEED_VERTEX_FACTOR * position
        d2 = position / numpy.linalg.norm(position)
        t_k = float(tev.time[k] - numpy.linalg.norm(position - x2) / model.cfg.photon_speed_m_per_ns)
    elif name == "h1 + mirrored h1":
        x2, d2 = -numpy.asarray(h1.vertex, float), -numpy.asarray(h1.direction, float)
    t0_2 = t_k if t_k is not None else _median_t0(model, tev, x2, residual)
    return Point(numpy.array([h1.vertex, x2], float), numpy.array([h1.direction, d2], float),
                 numpy.array([h1.e_vis, _yield(model, ev, residual, x2, d2)], float), numpy.array([h1.t0, t0_2], float))


def _split(model, tev, sign):
    """Starts 6 and 7: the charge split, directions times sign."""
    ev = tev.event
    q = numpy.where(ev.hit, numpy.nan_to_num(ev.charge), 0.0)
    total = float(q.sum())
    if not total > 0:
        return None
    positions = model.geometry.positions
    centre = (q[:, None] * positions).sum(axis=0) / total
    offset = positions - centre
    scatter = (offset * q[:, None]).T @ offset
    axis = numpy.linalg.eigh(scatter)[1][:, -1]
    axis = axis if axis[int(numpy.argmax(numpy.abs(axis)))] > 0 else -axis
    side = offset @ axis
    halves = [numpy.where(side >= 0, q, 0.0), numpy.where(side < 0, q, 0.0)]
    points = [_moment_point(model, h) for h in halves]
    if any(pt is None for pt in points):
        return None
    vertices = numpy.array([pt[0] for pt in points])
    directions = numpy.array([sign * pt[1] for pt in points])
    return Point(vertices, directions, numpy.array([_yield(model, ev, h, x, d) for h, x, d in zip(halves, vertices, directions)]),
                 numpy.array([_median_t0(model, tev, x, h) for h, x in zip(halves, vertices)]))


def start_points(model, tev, budget, h1) -> list:
    """[(name, Point or None)] in the budget's order, from the readout and H1's fit alone."""
    residual = _residual(model, tev, h1)
    out = []
    for name in budget.starts:
        if name in H1_ANCHORED:
            out.append((name, _h1_anchored(model, tev, h1, name, residual)))
        else:
            out.append((name, _split(model, tev, 1.0 if name == "charge split" else -1.0)))
    return out


# --- the choice -------------------------------------------------------------------------------------------------------------

def report_choice(ln_ls, tie_tolerance: float):
    """(index or None, rule) of H2's reported point from the starts' recorded ln L (None: no point)."""
    candidates = [(i, v) for i, v in enumerate(ln_ls) if v is not None and math.isfinite(v)]
    if not candidates:
        return None, REPORT_NONE
    best = max(v for _, v in candidates)
    tied = [i for i, v in candidates if v >= best - tie_tolerance]
    return min(tied), (REPORT_TIE if len(tied) > 1 else REPORT_BEST)


def statistic(ln_l1: float, ln_l_h2):
    """(lnL_2, where it comes from, 2 (lnL_2 - lnL_1)): lnL_2 = max(H2's reported ln L, lnL_1)."""
    if ln_l_h2 is None or ln_l_h2 < ln_l1:
        return ln_l1, FROM_BOUNDARY, 0.0
    return ln_l_h2, FROM_H2, 2.0 * (ln_l_h2 - ln_l1)


def choose(stat: float) -> str:
    """t04-values-v4.md section 7: H2 if and only if 2 (lnL_2 - lnL_1) >= 30."""
    return "H2" if stat >= PENALTY else "H1"


@dataclass(frozen=True)
class StartRecord:
    name: str
    start: Point | None
    result: TwoSourceResult


@dataclass(frozen=True)
class Topology:
    records: list
    reported: int | None
    report_rule: str | None
    result: TwoSourceResult | None
    ln_likelihood_1: float | None
    ln_likelihood_2: float | None
    ln_likelihood_2_from: str | None
    statistic: float | None
    choice: str | None
    rule: str


def fit_topology(model, tev, budget: TopologyBudget, h1) -> Topology:
    """H2 from the budget's starts and the choice against H1 (h1: the multistart fit's reported FitResult)."""
    if h1 is None or h1.status != "converged":
        return Topology([], None, None, None, None, None, None, None, None, CHOICE_H1_FAILED)
    records = []
    for name, start in start_points(model, tev, budget, h1):
        res = _failed(NO_START) if start is None else fit_two_source(model, tev, start)
        records.append(StartRecord(name, start, res))
    reported, rule = report_choice([r.result.ln_likelihood if r.result.point is not None else None for r in records],
                                   budget.tie_tolerance)
    result = None if reported is None else records[reported].result
    ln_l2, source, stat = statistic(h1.ln_likelihood, None if result is None else result.ln_likelihood)
    return Topology(records, reported, rule, result, h1.ln_likelihood, ln_l2, source, stat, choose(stat), CHOICE_RULE)


def check_at(model, event, topo: Topology):
    """The per-channel check at H2's reported point (m_1 + m_2 + dark), or None without one."""
    if topo.result is None or topo.result.point is None:
        return None
    point = "fit" if topo.result.status == "converged" else "fit-last"
    return {"point": point, **probability_check(model, event, topo.result.point)}
