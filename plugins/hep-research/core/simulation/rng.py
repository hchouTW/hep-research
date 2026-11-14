"""Random numbers of the response pipeline (g4sim plan, Section 10.2): Philox4x32-10, channel and volume streams, uniform variates, sampling and exact sums.

Python is normative. Philox is Salmon, Moraes, Dror and Shaw, SC11 (2011), doi:10.1145/2063384.2063405, checked against the known-answer vectors of the Random123
distribution. PTRS is Hormann, Insurance: Mathematics and Economics 12 (1993) 39, doi:10.1016/0167-6687(93)90997-4; BTPE is Kachitvichyanukul and Schmeiser, CACM 31 (1988)
216, doi:10.1145/42372.42381; Gamma is Marsaglia and Tsang, ACM TOMS 26 (2000) 363, doi:10.1145/358407.358414. These papers were checked at metadata level; the constants of PTRS and BTPE were read from
NumPy's `distributions.c`, including its correction of the sign of two error terms in the 1988 paper's final test.

A sub-stream is (key, event, channel or volume, sub-index): 2^16 output groups of two uniform variates. Each draw, and each attempt of a rejection sampler, starts a new output
group, so a draw depends only on its sub-stream and the draws before it there. Chunks enter neither the key nor the counter.
"""
from __future__ import annotations

import hashlib
import math

from core.canonical import canonical_json

MASK32 = 0xFFFFFFFF
MULTIPLIER_0, MULTIPLIER_1 = 0xD2511F53, 0xCD9E8D57
WEYL_0, WEYL_1 = 0x9E3779B9, 0xBB67AE85
ROUNDS = 10
GROUPS_PER_SUB_STREAM = 2 ** 16
MAXIMUM_SUB_INDEX = 2 ** 16
EVENT_LIMIT = 2 ** 32
SUMMAND_LIMIT = 1e290
SUMMAND_COUNT_LIMIT = 2 ** 48
INVERSE_LIMIT = 30  # below this mean, Poisson and binomial use the inverse transform
# Section 10.2, across platforms: continuous values within these ulps; measured on 200,000 draws, E2 against E5, at 3, 1 and 7 (S4 task card)
CROSS_PLATFORM_ULPS = {"gaussian": 8, "exponential": 4, "gamma": 32}
BOUNDARY_DISTANCE = 2.0 ** -40  # a discrete value may differ only if a uniform variate lies this close to a decision boundary
CHANNEL_PREFIX = "g4sim-rng/1\0channel"
VOLUME_PREFIX = "g4sim-rng/1\0volume"


class RngError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def philox4x32_10(counter: tuple, key: tuple) -> tuple:
    """Philox4x32 with 10 rounds: four 32-bit counter words and two key words to four output words."""
    x0, x1, x2, x3 = counter
    k0, k1 = key
    for at in range(ROUNDS):
        if at:
            k0, k1 = (k0 + WEYL_0) & MASK32, (k1 + WEYL_1) & MASK32
        first, second = MULTIPLIER_0 * x0, MULTIPLIER_1 * x2
        x0, x1, x2, x3 = ((second >> 32) ^ x1 ^ k0, second & MASK32, (first >> 32) ^ x3 ^ k1, first & MASK32)
    return x0, x1, x2, x3


def uniforms_of(words: tuple) -> tuple:
    """Two variates of one output group: the high 52 bits of a = x0 2^32 + x1 and of b, as (k + 0.5) 2^-52, strictly inside (0, 1)."""
    x0, x1, x2, x3 = words
    return tuple((2 * ((high << 32 | low) >> 12) + 1) * 2.0 ** -53 for high, low in ((x0, x1), (x2, x3)))


def _key(*parts) -> tuple:
    digest = hashlib.sha256(canonical_json(list(parts)).encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big"), int.from_bytes(digest[4:8], "big")


def channel_key(run_seed: int, readout: str, stage: str, replica: int) -> tuple:
    return _key(CHANNEL_PREFIX, run_seed, readout, stage, replica)


def volume_key(run_seed: int, stage: str, replica: int) -> tuple:
    return _key(VOLUME_PREFIX, run_seed, stage, replica)


def distinct_keys(keys: list) -> list:
    """The keys that coincide: 64 bits can collide, and the response checks refuse a study where any do."""
    seen, repeated = set(), []
    for key in keys:
        if key in seen:
            repeated.append(key)
        seen.add(key)
    return repeated


def check_event_range(first_event: int, events: int) -> None:
    if first_event < 0 or events < 0 or first_event + events > EVENT_LIMIT:
        raise RngError("event-range", f"first_event {first_event} + events {events} exceeds 2^32")


class SubStream:
    """One sub-stream. Word 0 is the event, words 1 and 2 the cellID or volume ID, word 3 the sub-index and the output group."""

    def __init__(self, key: tuple, event: int, identity: int, sub_index: int = 0):
        if not 0 <= event < EVENT_LIMIT:
            raise RngError("event-range", f"event {event} is outside 2^32")
        if not 0 <= sub_index < MAXIMUM_SUB_INDEX:
            raise RngError("sub-index", f"sub-index {sub_index} needs more than 16 bits")
        if not 0 <= identity < 2 ** 64:
            raise RngError("identity-range", f"identity {identity} is outside 64 bits")
        self.key, self.event, self.identity, self.sub_index = key, event, identity, sub_index
        self.groups_used = 0

    def group(self) -> tuple:
        """The next output group's two variates; a used group is never shared with another draw."""
        if self.groups_used >= GROUPS_PER_SUB_STREAM:
            raise RngError("sub-stream-exhausted", "the output-group index reached 2^16")
        word3 = self.sub_index << 16 | self.groups_used
        self.groups_used += 1
        return uniforms_of(philox4x32_10((self.event, self.identity & MASK32, self.identity >> 32, word3), self.key))

    def gaussian(self, mean: float = 0.0, sigma: float = 1.0) -> float:
        """Box-Muller, using only one of its two outputs."""
        first, second = self.group()
        return mean + sigma * math.sqrt(-2.0 * math.log(first)) * math.cos(2.0 * math.pi * second)

    def exponential(self) -> float:
        return -math.log(self.group()[0])

    def poisson(self, mean: float) -> int:
        if mean < 0 or math.isinf(mean) or math.isnan(mean):
            raise RngError("poisson-mean", f"mean {mean}")
        if mean == 0:
            return 0
        return _poisson_inverse(self, mean) if mean < INVERSE_LIMIT else _poisson_ptrs(self, mean)

    def binomial(self, trials: int, probability: float) -> int:
        if trials < 0 or not 0.0 <= probability <= 1.0:
            raise RngError("binomial-parameters", f"{trials}, {probability}")
        if trials == 0 or probability == 0.0:
            return 0
        if probability == 1.0:
            return trials
        low = min(probability, 1.0 - probability)
        count = _binomial_inverse(self, trials, low) if trials * low < INVERSE_LIMIT else _binomial_btpe(self, trials, low)
        return trials - count if probability > 0.5 else count

    def multinomial(self, trials: int, probabilities: list) -> list:
        """Successive conditional binomials in channel order; what is left over is the last entry, `not detected`."""
        total = math.fsum(probabilities)
        if any(value < 0 for value in probabilities) or total > 1.0 + 1e-12:
            raise RngError("multinomial-parameters", f"probabilities sum to {total}")
        counts, left, remaining = [], trials, 1.0
        for value in probabilities:
            share = min(value / remaining, 1.0) if remaining > 0.0 else 0.0
            drawn = self.binomial(left, share)
            counts.append(drawn)
            left -= drawn
            remaining -= value
        return [*counts, left]

    def gamma(self, shape: float) -> float:
        """Marsaglia-Tsang with scale 1; each attempt takes two consecutive output groups. The yield factor is Gamma(k, 1/k), with k >= 1."""
        if shape < 1.0:
            raise RngError("gamma-shape", f"shape {shape} is below 1")
        d = shape - 1.0 / 3.0
        c = 1.0 / math.sqrt(9.0 * d)
        while True:
            first, second = self.group()
            third = self.group()[0]
            x = math.sqrt(-2.0 * math.log(first)) * math.cos(2.0 * math.pi * second)
            v = (1.0 + c * x) ** 3
            if v > 0.0 and math.log(third) < 0.5 * x * x + d - d * v + d * math.log(v):
                return d * v


def _poisson_inverse(stream: SubStream, mean: float) -> int:
    u = stream.group()[0]
    term = math.exp(-mean)
    total, count = term, 0
    while u > total and term > 0.0:
        count += 1
        term *= mean / count
        total += term
    return count


def _poisson_ptrs(stream: SubStream, mean: float) -> int:
    root, log_mean = math.sqrt(mean), math.log(mean)
    b = 0.931 + 2.53 * root
    a = -0.059 + 0.02483 * b
    inverse_alpha = 1.1239 + 1.1328 / (b - 3.4)
    v_limit = 0.9277 - 3.6224 / (b - 2.0)
    while True:
        first, v = stream.group()
        u = first - 0.5
        us = 0.5 - abs(u)
        count = math.floor((2.0 * a / us + b) * u + mean + 0.43)
        if us >= 0.07 and v <= v_limit:
            return count
        if count < 0 or (us < 0.013 and v > us):
            continue
        if math.log(v) + math.log(inverse_alpha) - math.log(a / (us * us) + b) <= -mean + count * log_mean - math.lgamma(count + 1.0):
            return count


def _binomial_inverse(stream: SubStream, trials: int, probability: float) -> int:
    u = stream.group()[0]
    term = math.exp(trials * math.log1p(-probability))
    ratio = probability / (1.0 - probability)
    total, count = term, 0
    while u > total and count < trials and term > 0.0:
        count += 1
        term *= ratio * (trials - count + 1) / count
        total += term
    return count


def _stirling_tail(value: float) -> float:
    square = value * value
    return (13860.0 - (462.0 - (132.0 - (99.0 - 140.0 / square) / square) / square) / square) / value / 166320.0


def _binomial_btpe(stream: SubStream, n: int, r: float) -> int:
    """BTPE for probability r <= 0.5, with the sign correction of the final test; steps as in the paper."""
    q = 1.0 - r
    fm = n * r + r
    m = math.floor(fm)
    nrq = n * r * q
    p1 = math.floor(2.195 * math.sqrt(nrq) - 4.6 * q) + 0.5
    xm = m + 0.5
    xl, xr = xm - p1, xm + p1
    c = 0.134 + 20.5 / (15.3 + m)
    a = (fm - xl) / (fm - xl * r)
    left = a * (1.0 + a / 2.0)
    a = (xr - fm) / (xr * q)
    right = a * (1.0 + a / 2.0)
    p2 = p1 * (1.0 + 2.0 * c)
    p3 = p2 + c / left
    p4 = p3 + c / right
    while True:
        first, v = stream.group()
        u = first * p4
        if u <= p1:
            return math.floor(xm - p1 * v + u)
        if u <= p2:
            x = xl + (u - p1) / c
            v = v * c + 1.0 - abs(m - x + 0.5) / p1
            if v > 1.0:
                continue
            y = math.floor(x)
        elif u <= p3:
            y = math.floor(xl + math.log(v) / left)
            if y < 0:
                continue
            v = v * (u - p2) * left
        else:
            y = math.floor(xr - math.log(v) / right)
            if y > n:
                continue
            v = v * (u - p3) * right
        k = abs(y - m)
        if k <= 20 or k >= nrq / 2.0 - 1.0:
            s = r / q
            a = s * (n + 1)
            f = 1.0
            for i in range(m + 1, y + 1):
                f *= a / i - s
            for i in range(y + 1, m + 1):
                f /= a / i - s
            if v <= f:
                return y
            continue
        rho = (k / nrq) * ((k * (k / 3.0 + 0.625) + 0.16666666666666666) / nrq + 0.5)
        t = -k * k / (2.0 * nrq)
        log_v = math.log(v)
        if log_v < t - rho:
            return y
        if log_v > t + rho:
            continue
        x1, f1, z, w = y + 1.0, m + 1.0, n + 1.0 - m, n - y + 1.0
        limit = (xm * math.log(f1 / x1) + (n - m + 0.5) * math.log(z / w) + (y - m) * math.log(w * r / (x1 * q))
                 + _stirling_tail(f1) + _stirling_tail(z) - _stirling_tail(x1) - _stirling_tail(w))
        if log_v <= limit:
            return y


def _check_summands(values) -> list:
    numbers = [float(value) for value in values]
    if len(numbers) > SUMMAND_COUNT_LIMIT:
        raise RngError("sum-range", "more than 2^48 summands")
    for value in numbers:
        if not math.isfinite(value) or abs(value) > SUMMAND_LIMIT:
            raise RngError("sum-range", f"summand {value} is outside the range of Section 10.2")
    return numbers


def exact_sum(values) -> float:
    """The correctly rounded sum: CPython's math.fsum, within the range that keeps it independent of order."""
    return math.fsum(_check_summands(values))


def partial_sums(values) -> list:
    """Shewchuk partial sums: an exact representation of a chunk's sum, which is what a chunk hands over, never a rounded double."""
    partials: list = []
    for value in _check_summands(values):
        kept = []
        for other in partials:
            if abs(value) < abs(other):
                value, other = other, value
            high = value + other
            low = other - (high - value)
            if low:
                kept.append(low)
            value = high
        kept.append(value)
        partials = kept
    return partials


def merge_partial_sums(chunks: list) -> float:
    """One final rounding over every chunk's partial sums, so the result equals a single run's."""
    return exact_sum([value for chunk in chunks for value in chunk])
