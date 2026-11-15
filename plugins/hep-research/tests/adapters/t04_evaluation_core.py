"""The statistics core of the T07-T09 evaluation harness (D4 stage E6a; freeze-b-proposal.md section 4, row E6). Scoring side.

Sections cited are of t04-values-v4.md (Freeze A). The core judges nothing by itself in this stage: it is the rule, written and tested before any
evaluation sample exists (plan, T04 preregistration, "Acceptance / Validation"). It is shared by T07, T08 and T09 and imported by no recipe
(section 3.1 and Freeze A amendment 1: a recipe never links or imports a generator, seed code or truth reader; the harness hands out files, so
bins stay on its side; tests/adapters/test_t04_evaluation_core.py, NoRecipeImportsTheCore). It lives in tests/adapters, beside the T07 scoring
modules, because it is shared by three adapters (an adapter may import only core and contracts, tools/check_layering.py), it imports E2's
scorer from adapters/acts-tracking (which core/ may not), and it holds this plan's rules, not experiment-neutral code (core/OWNERS.json).

What it holds:
- the attempt level (section 3.4): attempt 1 at 95 % (`z` 1.645), attempt 2 at 99 % (`z` 2.326) on every test; the attempt comes from the bin's
  block (11 or 12, section 3.2) and nowhere else: every evaluation test takes the bin's identity and derives its level by level_of_block
  (identity.block), so a block-12 bin can never be scored at 95 %; any other block is refused (fix round 1, I1). The frozen codings' replay has
  its own named path (replay_pull_tests, replay_rate_test), with no bin and the attempt as a number, never reachable from evaluation scoring;
- the pull test (section 5.2, steps 1 to 4 in their order) on the trimmed centre (10 % per side) and on `sigma_68 - 1`, with the event
  bootstrap's `se`, mean and RMS reported beside them (sections 5.1, 6);
- the rate test with an upper limit `L` (section 5.2: `DEFF_hat`, `U_A`, `U_B`, `U`, steps 1 to 4, `N_min = 30/L`). Its first part is E2's
  rule, reused by import (adapters/acts-tracking/assets/fixture_tools/t07_fake_rate.py, rate_rule and bounds_of, equal to the frozen
  calc-rate-rule.py with difference 0.0 in all 12 bins, job 7584388). At attempt 1 the bounds are E2's own; at attempt 2 the same expressions at
  the 99 % level (bounds_at), since E2's module fixes 95 % (CONFIDENCE). bounds_at at 0.95 equals bounds_of exactly (RateRule tests), and at
  0.99 equals the frozen coding's bound(cl=0.99) (FrozenCodingAgreement). E2's module is not moved: it is in the Freeze-B run's manifest and
  its job of record's pins, and moving it would renew both;
- the efficiency test (section 5.2): the failure rate on the same rule, lower bound `1 - U`, `L = 1 - lower limit`, `N_min` 3,000 events, and
  `delta(R) = max(0.01, 5.961 sqrt(R(1-R)/10000))` frozen as v4's formula;
- the paired bound (U-K2, decisions.md "The user's answers to the remaining Freeze B, K09 and later items"): estimate - z x the event-bootstrap
  `se` of the paired difference, B = 1,000, `z` of the attempt level; the percentile bound printed as a reading;
- the event bootstrap (section 5.1): B = 1,000 replicates of the bin's events, drawn by numpy's PCG64 from
  SeedSequence([BOOTSTRAP_DOMAIN, fixture_id, block, stratum]), the bin's identity led by a tag of its own (so it is never the generator's
  four-integer state of section 3.2); every test of a bin uses the same replicates. No global random state, no wall clock;
- section 10's mapping from test results to R11 states, every row. Section 10's obligations fixed at Freeze A and U-K7's three are built in
  per workflow and always open, so plain `done` cannot be reached for T07-T09; the required set is counted against section 10's table
  (fix round 1, I2);
- results as typed records (TestResult: gate (the test's name), bin, statistic, estimate, standard_error (the se), bounds, limit, result word, step, level); the words
  v4's: pass, fail, inconclusive, not-applicable.
Constants are v4's and are not tuned here (R12): no constant derives from pulls or targets.
"""
from __future__ import annotations

import dataclasses
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "adapters" / "acts-tracking" / "assets" / "fixture_tools"))
import t07_fake_rate as fake_rate  # noqa: E402  (E2's rate rule, reused by import)

TOLERANCE = 0.10              # section 5.1, "Tolerance": 0.10 on centre and on sigma_68 - 1
PRECISION_CAP = 0.0108        # section 5.1, "Precision cap", centre and width
TRIM_PER_SIDE = 0.10          # section 5.1, "Robust centre": 10 % cut from each side
SIGMA68_PROBABILITIES = (0.158655, 0.841345)  # section 5.1, half the central 68.27 % interval; the frozen coding's probabilities (calc-pull-table.py s68)
BOOTSTRAP_REPLICATES = 1000   # section 5.1, "se in a gate", B = 1,000
BOOTSTRAP_DOMAIN = 520        # the bootstrap's tag (v4 5.2); no fixture_id (section 3.2) is 520, so its entropy never is a generator state
RATE_MINIMUM_FACTOR = 30      # section 5.2, N_min = 30/L events
EFFICIENCY_MINIMUM_EVENTS = 3000  # section 5.2, "Efficiency tests ... N_min is 3,000 events"
DELTA_FLOOR, DELTA_FACTOR, DELTA_EVENTS = 0.01, 5.961, 10000      # section 5.2, delta(R) = max(0.01, 5.961 sqrt(R(1-R)/10000))
FAMILY_TESTS = 1260           # section 5.3: all T07-T09 gates use T07's count, M = 1,260
Z_FAMILY = float(stats.norm.isf(0.01 / FAMILY_TESTS))  # section 5.3, z1 4.316; enters slack only, never a pass rule
ATTEMPT_OF_BLOCK = {11: 1, 12: 2}                    # section 3.2, blocks 11 and 12: evaluation attempts 1 and 2
# The user's answers on the attempt-2 levels (decisions.md, "The user's answers on the attempt-2 levels (K09, 2026-11-12)"): v4 3.4's 99 % moves
# the bounds that decide a pass; the bounds that declare a fail keep 95 %. So step 1 of the pull and rate tests (the fail-first step) is at 95 %
# at both attempts, and the paired bound (a pass bound; U-K2's form) is at z 2.326 at attempt 2 (its percentile reading at 1 %).
STEP1_ALPHA_OF_ATTEMPT = {1: 0.05, 2: 0.05}          # step 1 of the pull and rate tests (v4 5.2): 95 % at both attempts (the user, K09)
PAIRED_ALPHA_OF_ATTEMPT = {1: 0.05, 2: 0.01}         # the paired bound: U-K2's 1.645 at attempt 1, v4 3.4's 2.326 at attempt 2 (the user, K09)
ALPHA_OF_ATTEMPT = {1: 0.05, 2: 0.01}                # section 3.4: 95 %, then 99 % on every test
CONFIDENCE_OF_ATTEMPT = {1: 0.95, 2: 0.99}
RESULT_WORDS = ("pass", "fail", "inconclusive", "not-applicable")  # sections 5.2 and 10
WORKFLOW_FIXTURES = {"T07": (7001, 7002, 7003, 7004), "T08": (8001, 8002, 8003, 8004), "T09": (9001, 9002, 9003, 9004)}  # section 3.2
STRATA_PER_FIXTURE = 12       # section 5.1, 12 bins per fixture (4 x 3); a control has stratum 0
R11_STATES = ("done", "done (narrowed claim)", "failed", "blocked-by-decision", "blocked-by-resource", "in-progress")
REQUIRED_TESTS = {"T07": 1260, "T08": 80, "T09": 270}  # section 10, "Required set", fixed at Freeze A
# Section 10, "Open obligations", rows fixed at Freeze A, and U-K7 (decisions.md): open in every report, never counted as a pass.
FIXED_OBLIGATIONS = {
    "T07": (("T07 material", None, "section 10: the user's decision at Freeze A against plan 11.4"),
            ("T07 particle type, timing, displaced vertices, near vertices", "T07 later pass, or the user", "section 10"),
            ("A01", "T15b", "section 10; U-K7: a second backend cannot run at evaluation")),
    "T08": (("T08 angle and particle type", None, "section 10: the user's decision at Freeze A against plan 11.4"),
            ("T08 E1 pulls, E1 merge, near per-shower pulls and near sharing, saturated energy, split rate, unequal sharing, noise-dominated regime",
             None, "section 10, the user's decision"),
            ("A38.3", None, "U-K7: exposure, no live time in t08-grid/1"),
            ("A15 (b)", None, "U-K7 and U-B14: rejection of the cheap and coarse variants")),
    "T09": (("T09 medium", None, "section 10: the user's decision at Freeze A against plan 11.4"),
            ("T09 B1 pulls", None, "section 10, the user's decision")),
}
REPLAY_LABEL = "frozen-coding replay (no bin; the attempt as a number, no event of any evaluation block)"
CHECK_KINDS = ("deterministic", "negative", "cai")


class CoreError(ValueError):
    """An input the rules do not define, or a record that would break section 10 (an ungated pass, a required not-applicable)."""


# ---- The attempt level (section 3.4).

@dataclass(frozen=True)
class Level:
    """The level of one evaluation attempt. Made by level_of_block; any other combination is refused."""
    block: int
    attempt: int
    confidence: float
    alpha: float
    z: float

    def __post_init__(self):
        attempt = ATTEMPT_OF_BLOCK.get(self.block)
        if attempt is None or (self.attempt, self.confidence, self.alpha) != (attempt, CONFIDENCE_OF_ATTEMPT[attempt], ALPHA_OF_ATTEMPT[attempt]) \
                or self.z != float(stats.norm.isf(ALPHA_OF_ATTEMPT[attempt])):
            raise CoreError(f"no level of section 3.4 has block {self.block}, attempt {self.attempt}, confidence {self.confidence}, z {self.z}")

    @property
    def step1_alpha(self) -> float:
        return STEP1_ALPHA_OF_ATTEMPT[self.attempt]

    @property
    def step1_z(self) -> float:
        return float(stats.norm.isf(self.step1_alpha))

    @property
    def paired_alpha(self) -> float:
        return PAIRED_ALPHA_OF_ATTEMPT[self.attempt]

    @property
    def paired_z(self) -> float:
        return float(stats.norm.isf(self.paired_alpha))


def level_of_block(block: int) -> Level:
    """Section 3.2 and 3.4: block 11 is attempt 1 (95 %), block 12 attempt 2 (99 %); any other block has no evaluation level."""
    if block not in ATTEMPT_OF_BLOCK:
        raise CoreError(f"block {block} is not an evaluation block (section 3.2: 11 and 12)")
    attempt = ATTEMPT_OF_BLOCK[block]
    return Level(block, attempt, CONFIDENCE_OF_ATTEMPT[attempt], ALPHA_OF_ATTEMPT[attempt], float(stats.norm.isf(ALPHA_OF_ATTEMPT[attempt])))


def _replay_level(attempt: int) -> Level:
    """The replay's level: the attempt as a number only (no bin of block 11 or 12 is scored or drawn)."""
    blocks = {a: b for b, a in ATTEMPT_OF_BLOCK.items()}
    if attempt not in blocks:
        raise CoreError(f"attempt {attempt}: at most 2 evaluation attempts (section 3.4)")
    return level_of_block(blocks[attempt])


def slack(se: float, level: Level) -> float:
    """Sections 3.4 and 5.3: slack(se) = 0.10 - (z + z1) se, a reading of the design, never a pass rule."""
    return TOLERANCE - (level.z + Z_FAMILY) * se


# ---- The bin and its bootstrap (section 5.1).

@dataclass(frozen=True)
class BinIdentity:
    workflow: str
    fixture_id: int
    block: int
    stratum: int

    def __post_init__(self):
        if self.fixture_id not in WORKFLOW_FIXTURES.get(self.workflow, ()):
            raise CoreError(f"fixture {self.fixture_id} is not a fixture of {self.workflow} (section 3.2)")
        if not 0 <= self.stratum < STRATA_PER_FIXTURE or self.block < 1:
            raise CoreError(f"stratum {self.stratum} or block {self.block} is outside section 3.2's")

    @property
    def label(self) -> str:
        return f"{self.workflow} fixture {self.fixture_id} block {self.block} stratum {self.stratum}"

    @property
    def level(self) -> Level:
        """The attempt level of this bin, from its block alone (I1): 11 is 95 %, 12 is 99 %, any other block is refused."""
        return level_of_block(self.block)


POOL_STRATUM_BASE = 100       # a pooled bin's stratum field is 100 + its pool index: its entropy is never a bin's (strata 0 to 11)


@dataclass(frozen=True)
class PooledIdentity:
    """A test pooled over bins of one fixture and block (D4 E6c fix round 1, with E6b's O5): T09's mirrored and reversed (v4 9.4, main B2-B4)
    and T07's angle slices (v4 8.2, the 12 bins of a fixture). Its bootstrap entropy is (520, fixture_id, block, 100 + pool), never a bin's or
    another pool's of the same fixture; its level is its block's; it is complete only if every member bin is (layout.check_pool)."""
    workflow: str
    fixture_id: int
    block: int
    pool: int
    members: tuple
    name: str

    def __post_init__(self):
        if self.fixture_id not in WORKFLOW_FIXTURES.get(self.workflow, ()):
            raise CoreError(f"fixture {self.fixture_id} is not a fixture of {self.workflow} (section 3.2)")
        members = tuple(self.members)
        if self.block < 1 or not 0 <= self.pool < STRATA_PER_FIXTURE or len(members) < 2 or len(set(members)) != len(members) \
                or not all(0 <= m < STRATA_PER_FIXTURE for m in members) or not self.name:
            raise CoreError(f"pool {self.pool} of strata {members}, block {self.block}: a pool has a name, 2 or more distinct strata 0 to 11, a pool index 0 to 11")

    @property
    def stratum(self) -> int:
        return POOL_STRATUM_BASE + self.pool

    @property
    def label(self) -> str:
        return f"{self.workflow} fixture {self.fixture_id} block {self.block} pool {self.pool} ({self.name}; strata {', '.join(map(str, self.members))})"

    @property
    def level(self) -> Level:
        return level_of_block(self.block)


def seed_entropy(identity) -> tuple:
    return (BOOTSTRAP_DOMAIN, identity.fixture_id, identity.block, identity.stratum)


def bootstrap_indices(identity: BinIdentity, events: int, replicates: int = BOOTSTRAP_REPLICATES) -> numpy.ndarray:
    """B rows of N_ev event indices, drawn with replacement by PCG64 from SeedSequence(seed_entropy(identity)): the same bin gives the same rows."""
    if events < 1:
        raise CoreError("a bootstrap needs at least one event")
    generator = numpy.random.Generator(numpy.random.PCG64(numpy.random.SeedSequence(list(seed_entropy(identity)))))
    return generator.integers(0, events, size=(replicates, events))


def _checked_indices(indices, events: int) -> numpy.ndarray:
    indices = numpy.asarray(indices)
    if indices.ndim != 2 or indices.shape[1] != events or indices.shape[0] < 2 or indices.dtype.kind not in "iu" \
            or (indices.size and (indices.min() < 0 or indices.max() >= events)):
        raise CoreError(f"bootstrap indices must be B >= 2 rows of {events} event indices in [0, {events})")
    return indices


@dataclass(frozen=True)
class EventValues:
    """Per-event values, ragged: values of all objects in event order, with each event's count and start."""
    values: numpy.ndarray
    counts: numpy.ndarray
    starts: numpy.ndarray

    @classmethod
    def of(cls, per_event) -> "EventValues":
        if isinstance(per_event, numpy.ndarray) and per_event.ndim == 2:
            values = numpy.ascontiguousarray(per_event, dtype=float).ravel()
            counts = numpy.full(per_event.shape[0], per_event.shape[1], dtype=numpy.int64)
        else:
            parts = [numpy.asarray(part, dtype=float).ravel() for part in per_event]
            counts = numpy.array([part.size for part in parts], dtype=numpy.int64)
            values = numpy.concatenate(parts) if parts else numpy.zeros(0)
        if not numpy.isfinite(values).all():
            raise CoreError("a pull is not finite")
        starts = numpy.concatenate(([0], numpy.cumsum(counts)[:-1])).astype(numpy.int64) if counts.size else numpy.zeros(0, dtype=numpy.int64)
        return cls(values, counts, starts)

    @property
    def events(self) -> int:
        return int(self.counts.size)

    @property
    def objects(self) -> int:
        return int(self.values.size)

    def gather(self, rows) -> numpy.ndarray:
        """The objects of the chosen events, in the chosen order (as x[rows].ravel() for a rectangular x)."""
        rows = numpy.asarray(rows)
        counts = self.counts[rows]
        ends = numpy.cumsum(counts)
        return self.values[numpy.repeat(self.starts[rows] - ends + counts, counts) + numpy.arange(int(ends[-1]) if ends.size else 0)]


# ---- Records.

@dataclass(frozen=True)
class TestResult:
    gate: str
    bin: str
    statistic: str
    estimate: float | None
    standard_error: float | None
    lower: float | None
    upper: float | None
    limit: float | None
    result: str
    step: int
    attempt: int
    confidence: float
    replicates: int | None
    required: bool
    reason: str
    readings: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.result not in RESULT_WORDS:
            raise CoreError(f"result {self.result!r} is not one of v4's words {RESULT_WORDS}")


def replace_result(record: TestResult, result: str, step: int, reason: str = "") -> TestResult:
    return dataclasses.replace(record, result=result, step=step, reason=reason or record.reason)


def mark_ungated(record: TestResult, reason: str) -> TestResult:
    """Section 10, "Ungated": the check value is inconclusive, required no, with the reason. The numbers stay, labelled a reading; the computed
    word is dropped, so nothing on the record reads as a pass (coordinator's ruling, E6a fix round 1, O4)."""
    readings = dict(record.readings, label="reading of an ungated bin (section 10): numbers only, no result word")
    return dataclasses.replace(record, result="inconclusive", step=0, required=False, reason=reason, readings=readings)


def missing_output(name: str, identity: BinIdentity, statistic: str, reason: str) -> TestResult:
    """Section 10: a required output missing (or a sample shrunk by resources, K10), so the test cannot be computed: inconclusive."""
    level = identity.level
    return TestResult(name, identity.label, statistic, None, None, None, None, None, "inconclusive", 0, level.attempt, level.confidence, None, True,
                      f"required output missing: {reason}", {})


# ---- Pull tests (sections 5.1, 5.2, 6).

def trimmed_centre(values) -> float:
    x = numpy.sort(numpy.asarray(values, dtype=float), axis=-1)
    cut = int(TRIM_PER_SIDE * x.shape[-1])
    return float(x[..., cut:x.shape[-1] - cut].mean(axis=-1))


def sigma_68(values) -> float:
    low, high = numpy.quantile(numpy.asarray(values, dtype=float), SIGMA68_PROBABILITIES, axis=-1)
    return float((high - low) / 2)


def pull_readings(per_event) -> dict:
    events = per_event if isinstance(per_event, EventValues) else EventValues.of(per_event)
    x = events.values
    return {"objects": events.objects, "events": events.events, "mean": float(x.mean()) if x.size else math.nan,
            "rms": float(math.sqrt((x * x).mean())) if x.size else math.nan}


def pull_step(estimate: float, target: float, se: float, level: Level) -> tuple:
    """Section 5.2, with e = |estimate - target|, in this order: 1 fail if e - z1 se > 0.10 (z1 of STEP1_ALPHA_OF_ATTEMPT); 2 inconclusive if
    se > 0.0108; 3 pass if e + z se <= 0.10; 4 fail otherwise. Returns (word, step)."""
    if not all(math.isfinite(v) for v in (estimate, target, se)) or se < 0:
        raise CoreError(f"the pull rule needs finite numbers and se >= 0: estimate {estimate}, se {se}")
    e = abs(estimate - target)
    if e - level.step1_z * se > TOLERANCE:
        return "fail", 1
    if se > PRECISION_CAP:
        return "inconclusive", 2
    if e + level.z * se <= TOLERANCE:
        return "pass", 3
    return "fail", 4


def _pull_records(name: str, label: str, events: EventValues, level: Level, rows, required: bool) -> tuple:
    readings = pull_readings(events)
    common = dict(gate=name, bin=label, attempt=level.attempt, confidence=level.confidence, required=required, readings=readings)
    if events.objects == 0:
        return tuple(TestResult(statistic=s, estimate=None, standard_error=None, lower=None, upper=None, limit=TOLERANCE, result="inconclusive", step=0,
                                replicates=None, reason="required output missing: no pull in the bin", **common)
                     for s in ("trimmed-centre", "sigma68-width"))
    rows = rows() if callable(rows) else rows
    empty = int((events.counts[rows].sum(axis=1) == 0).sum())
    if empty:
        # A replicate holding no object has no centre or width, so the bootstrap se is undefined (fix round 1; E6b review I4): inconclusive, the
        # reason stated, as step 2 reads an se it cannot bound. The numbers of the bin stay as readings.
        reason = f"required output missing: {empty} of {rows.shape[0]} bootstrap replicates hold no pull, so the se is undefined"
        return tuple(TestResult(statistic=s, estimate=None, standard_error=None, lower=None, upper=None, limit=TOLERANCE, result="inconclusive",
                                step=2, replicates=int(rows.shape[0]), reason=reason, **common) for s in ("trimmed-centre", "sigma68-width"))
    centre_rep, width_rep = numpy.empty(rows.shape[0]), numpy.empty(rows.shape[0])
    for b, row in enumerate(rows):
        replicate = events.gather(row)
        centre_rep[b], width_rep[b] = trimmed_centre(replicate), sigma_68(replicate)
    records = []
    for statistic, estimate, replicates in (("trimmed-centre", trimmed_centre(events.values), centre_rep),
                                            ("sigma68-width", sigma_68(events.values) - 1.0, width_rep)):
        se = float(replicates.std(ddof=1))
        word, step = pull_step(estimate, 0.0, se, level)
        records.append(TestResult(statistic=statistic, estimate=estimate, standard_error=se, lower=estimate - level.z * se, upper=estimate + level.z * se,
                                  limit=TOLERANCE, result=word, step=step, replicates=int(rows.shape[0]), reason="", **common))
    return tuple(records)


def pull_tests(name: str, identity, per_event, *, required: bool = True) -> tuple:
    """The location and width gates of section 6 on one bin: (centre record, width record), with the bin's own B = 1,000 replicates for both and
    the level of the bin's block. No other replicates are accepted (B is v4 5.1's)."""
    level = identity.level
    events = EventValues.of(per_event)
    return _pull_records(name, identity.label, events, level, lambda: bootstrap_indices(identity, events.events), required)


def replay_pull_tests(name: str, per_event, *, attempt: int, indices) -> tuple:
    """The frozen codings' replay only (jobs/d4-e6a, pull-replay): the given bootstrap rows (calc-pull-table.py's own) and the attempt as a number.
    Its records carry REPLAY_LABEL in place of a bin, so they can never pass for a bin's."""
    events = EventValues.of(per_event)
    return _pull_records(name, REPLAY_LABEL, events, _replay_level(attempt), _checked_indices(indices, events.events), False)


# ---- Rate and efficiency tests (section 5.2).

def minimum_events(limit: float) -> int:
    """N_min = 30/L events, as an integer: 3,000 at 1 %, 6,000 at 0.5 % (section 5.2's table)."""
    if not 0 < limit < 1:
        raise CoreError(f"a rate limit must be in (0, 1): {limit}")
    exact = RATE_MINIMUM_FACTOR / limit
    nearest = round(exact)
    return int(nearest) if abs(exact - nearest) < 1e-9 * exact else int(math.ceil(exact))


def bounds_at(k: int, n: int, events: int, deff_hat: float, confidence: float) -> dict:
    """E2's bounds (t07_fake_rate.bounds_of) at a level: U_A, U_B, U and the step 1 lower bound, the same expressions and order."""
    if events < 2 or n < 1 or not 0 <= k < n:
        raise CoreError(f"the rule needs at least 2 events, an object, and 0 <= k < n: k {k} n {n} events {events}")
    d = max(deff_hat, 1.0) if k > 0 else 1.0
    u_a = float(stats.beta.ppf(confidence, k / d + 1, n / d - k / d))
    mbar = n / events
    kb = min(k, fake_rate.K_CAP) / mbar
    u_b = float(stats.beta.ppf(confidence, kb + 1, events - kb))
    lower = float(stats.beta.ppf(1 - confidence, k / d, n / d - k / d + 1)) if k > 0 else 0.0
    return {"u_a": u_a, "u_b": u_b, "u": max(u_a, u_b), "lower": lower, "design_effect": float(d), "objects_per_event": float(mbar)}


def _counts(m, y) -> tuple:
    m = numpy.asarray(m)
    y = numpy.asarray(y)
    if m.ndim != 1 or m.shape != y.shape or m.dtype.kind not in "iub" or y.dtype.kind not in "iub" or (m < 0).any() or (y < 0).any() or (y > m).any():
        raise CoreError("m and y are per-event integer counts, 0 <= y_e <= m_e")
    return m.astype(numpy.int64), y.astype(numpy.int64)


def _rate_record(name: str, label: str, m, y, limit: float, level: Level, min_events, required: bool, statistic: str) -> TestResult:
    m, y = _counts(m, y)
    needed = minimum_events(limit) if min_events is None else int(min_events)
    common = dict(gate=name, bin=label, statistic=statistic, limit=limit, attempt=level.attempt, confidence=level.confidence,
                  replicates=None, required=required)
    n, k, events = int(m.sum()), int(y.sum()), int(m.size)
    if n == 0 or events < 2:
        return TestResult(estimate=None, standard_error=None, lower=None, upper=None, result="inconclusive", step=0,
                          reason=f"required output missing: {n} objects in {events} events", readings={"events": events, "objects": n}, **common)
    if k == n:
        # Every object failed (coordinator's ruling, E6a fix round 1, M2/O3: fail at step 1). DEFF_hat divides by p(1-p) = 0, so set A's
        # bound is undefined; the lower bound takes events as the unit (k_eff = N_ev of N_ev), the step 1 alpha of the attempt; U is 1.
        lower = float((level.step1_alpha) ** (1.0 / events))
        word, step = ("fail", 1) if lower > limit else (("inconclusive", 2) if events < needed else ("fail", 4))
        return TestResult(estimate=1.0, standard_error=None, lower=lower, upper=1.0, result=word, step=step,
                          reason="every object failed (k = n): the lower bound with events as the unit",
                          readings={"events": events, "objects": n, "failures": k, "minimum_events": needed}, **common)
    found = fake_rate.rate_rule(m, y)
    if level.confidence == fake_rate.CONFIDENCE:
        upper, u_a, u_b, d = found["u_dev"], found["u_a"], found["u_b"], found["design_effect"]
    else:
        own = bounds_at(k, n, events, found["deff_hat"], level.confidence)
        upper, u_a, u_b, d = own["u"], own["u_a"], own["u_b"], own["design_effect"]
    if 1 - level.step1_alpha == fake_rate.CONFIDENCE:
        lower = found["l_dev"]
    else:
        lower = bounds_at(k, n, events, found["deff_hat"], 1 - level.step1_alpha)["lower"]
    if lower > limit:
        word, step = "fail", 1
    elif events < needed:
        word, step = "inconclusive", 2
    elif upper <= limit:
        word, step = "pass", 3
    else:
        word, step = "fail", 4
    readings = {"events": events, "objects": n, "failures": k, "objects_per_event": found["objects_per_event"], "deff_hat": found["deff_hat"],
                "design_effect": d, "u_a": u_a, "u_b": u_b, "minimum_events": needed}
    return TestResult(estimate=found["r_dev"], standard_error=None, lower=lower, upper=upper, result=word, step=step, reason="", readings=readings, **common)


def rate_test(name: str, identity, m, y, limit: float, *, min_events: int | None = None, required: bool = True,
              statistic: str = "rate") -> TestResult:
    """Section 5.2 on one bin, at the level of the bin's block: m_e objects and y_e failures per event; steps 1 to 4. E2's rate_rule gives the
    counts and DEFF_hat."""
    return _rate_record(name, identity.label, m, y, limit, identity.level, min_events, required, statistic)


def replay_rate_test(name: str, m, y, limit: float, *, attempt: int, min_events: int | None = None) -> TestResult:
    """The frozen codings' replay only (jobs/d4-e6a): the attempt as a number, REPLAY_LABEL in place of a bin."""
    return _rate_record(name, REPLAY_LABEL, m, y, limit, _replay_level(attempt), min_events, False, "rate")


def efficiency_margin(reference: float) -> float:
    """Section 5.2, frozen as a formula of the reference: delta(R) = max(0.01, 5.961 sqrt(R(1-R)/10000))."""
    if not 0 < reference < 1:
        raise CoreError(f"a reference efficiency is in (0, 1): {reference}")
    return max(DELTA_FLOOR, DELTA_FACTOR * math.sqrt(reference * (1 - reference) / DELTA_EVENTS))


def efficiency_lower_limit(reference: float) -> float:
    return reference - efficiency_margin(reference)


def efficiency_test(name: str, identity: BinIdentity, m, failures, lower_limit: float, *, required: bool = True) -> TestResult:
    """Section 5.2: the failure rate 1 - efficiency on the rate rule with L = 1 - lower_limit and N_min 3,000 events; the lower bound on
    efficiency is 1 - U. lower_limit is R - delta(R) (efficiency_lower_limit), or a floor the gate states (section 8.2, 8.5)."""
    rate = rate_test(name, identity, m, failures, 1 - lower_limit, min_events=EFFICIENCY_MINIMUM_EVENTS, required=required)
    flip = (lambda v: None if v is None else 1 - v)
    return dataclasses.replace(rate, statistic="efficiency", estimate=flip(rate.estimate), lower=flip(rate.upper), upper=flip(rate.lower),
                               limit=lower_limit, readings=dict(rate.readings, failure_rate_limit=1 - lower_limit))


# ---- The paired bound (section 5.2, "Paired comparisons"; U-K2).

def paired_test(name: str, identity: BinIdentity, m, a, b, limit: float, *, required: bool = True,
                min_events: int = EFFICIENCY_MINIMUM_EVENTS) -> TestResult:
    """The paired difference D = (sum a - sum b) / sum m over the same events (section 8.2, "Efficiency, noise (a)": the recipe's found
    objects a_e against the truth-seeded run's b_e, of m_e objects). Bound D - z se, with z of PAIRED_ALPHA_OF_ATTEMPT (1.645 at attempt 1,
    U-K2; 2.326 at attempt 2, v4 3.4: a reading awaiting the user) and se the bin's event bootstrap (B = 1,000). Pass if the bound is at least
    the limit, else fail; fewer than N_min events (3,000, an efficiency gate's) is inconclusive. The percentile bound (the alpha quantile of the
    replicates) is printed as a reading (U-K2)."""
    level = identity.level
    m, a = _counts(m, a)
    _, b = _counts(m, b)
    events, n = int(m.size), int(m.sum())
    common = dict(gate=name, bin=identity.label, statistic="paired-difference", limit=limit, attempt=level.attempt, confidence=level.confidence,
                  required=required)
    if n == 0 or events < 2:
        return TestResult(estimate=None, standard_error=None, lower=None, upper=None, result="inconclusive", step=0, replicates=None,
                          reason=f"required output missing: {n} objects in {events} events", readings={"events": events, "objects": n}, **common)
    estimate = (int(a.sum()) - int(b.sum())) / n
    rows = bootstrap_indices(identity, events)
    replicates = (a[rows].sum(axis=1) - b[rows].sum(axis=1)) / m[rows].sum(axis=1)
    se = float(numpy.std(replicates, ddof=1))
    lower = estimate - level.paired_z * se
    if events < min_events:
        word, step = "inconclusive", 2
    else:
        word, step = ("pass", 3) if lower >= limit else ("fail", 4)
    readings = {"events": events, "objects": n, "percentile_lower": float(numpy.quantile(replicates, level.paired_alpha))}
    return TestResult(estimate=estimate, standard_error=se, lower=lower, upper=None, result=word, step=step, replicates=int(rows.shape[0]), reason="",
                      readings=readings, **common)


# ---- Section 10: from test results to R11 state.

@dataclass(frozen=True)
class CheckResult:
    """A deterministic, negative or CAI check (section 11; R37): pass or fail, a CAI check also 'gap' for a recorded unsupported gap."""
    name: str
    kind: str
    result: str
    stop: bool = False
    recorded_unsupported_gap: bool = False

    def __post_init__(self):
        if self.kind not in CHECK_KINDS or self.result not in ("pass", "fail", "gap") or (self.result == "gap") != self.recorded_unsupported_gap \
                or (self.recorded_unsupported_gap and self.kind != "cai"):
            raise CoreError(f"check {self.name}: kind {self.kind}, result {self.result} is not a section 10 check")


@dataclass(frozen=True)
class Obligation:
    """An open obligation (section 10, R18): listed in every report; it narrows the claim and is never counted as a pass (U-K7)."""
    name: str
    owner: str | None
    reason: str


def fixed_obligations(workflow: str) -> tuple:
    """Section 10's obligations fixed at Freeze A and U-K7's, for one workflow: always open."""
    if workflow not in FIXED_OBLIGATIONS:
        raise CoreError(f"workflow {workflow} has no section 10 obligations table (T07, T08, T09)")
    return tuple(Obligation(*row) for row in FIXED_OBLIGATIONS[workflow])


@dataclass(frozen=True)
class WorkflowOutcome:
    workflow: str
    gate_results: dict
    workflow_result: str
    r11_state: str
    attempt: int
    open_obligations: tuple
    reasons: tuple
    recorded: tuple
    stop: bool
    failure_record: bool


_WORST = {"pass": 0, "inconclusive": 1, "fail": 2}


def workflow_outcome(workflow: str, tests, checks, *, attempt: int, forbidden_constants=(), freeze_b_blocks_used_up: bool = False,
                     critical_false_success=(), evaluation_could_not_run: bool = False, matching_sensitivity_disagrees: bool = False,
                     found_obligations=(), required_checks=None) -> WorkflowOutcome:
    """Every row of section 10's table. A workflow's result is the worst of its gates; a mean over bins never makes up for a failed bin.
    A gate is the set of records with one gate name; inconclusive in a required bin fails the workflow (R11). The required set is intact when
    the required records number section 10's count (REQUIRED_TESTS); the fixed obligations are always merged in, and found_obligations
    (obligations found at run time, if any) beside them, so the state of a passing T07-T09 workflow is `done (narrowed claim)`."""
    if attempt not in (1, 2):
        raise CoreError(f"attempt {attempt}: at most 2 evaluation attempts (section 3.4)")
    tests = list(tests)
    checks = list(checks)
    recorded = ["matching sensitivity disagrees (recorded, no effect)"] if matching_sensitivity_disagrees else []
    obligations = list(fixed_obligations(workflow)) + list(found_obligations)
    if freeze_b_blocks_used_up:
        return WorkflowOutcome(workflow, {}, "not judged", "blocked-by-decision", attempt, tuple(obligations),
                               ("Freeze-B blocks used up: blocked until the user answers (section 3.2)",), tuple(recorded), False, False)
    if evaluation_could_not_run:
        return WorkflowOutcome(workflow, {}, "not judged", "blocked-by-resource", attempt, tuple(obligations),
                               ("resources: the evaluation cannot run at all (K10)",), tuple(recorded), False, False)
    # Fix round 1 (E6c review I2): v4 10's pass row needs the deterministic, negative and CAI checks to pass, so a pass needs every required check
    # present. required_checks: the names the workflow requires (t08_scoring.REQUIRED_CHECKS, t09_scoring.REQUIRED_CHECKS, E6b's for T07). A
    # required check absent, or no list given, is refused (CoreError): the summary reads it as incomplete, never as a pass or a fail.
    if required_checks is None:
        raise CoreError("workflow_outcome needs the workflow's required checks (v4 10: deterministic, negative and CAI checks)")
    absent = sorted(set(required_checks) - {check.name for check in checks})
    if absent:
        raise CoreError(f"required checks absent: {absent}; no outcome is read without them (v4 10)")
    required = [record for record in tests if record.required]
    if len(required) != REQUIRED_TESTS[workflow]:
        return WorkflowOutcome(workflow, {}, "fail", "failed", attempt, tuple(obligations),
                               (f"required set not intact: {len(required)} required tests, section 10 fixes {REQUIRED_TESTS[workflow]}; no gate result",),
                               tuple(recorded), False, True)
    reasons = []
    gates = {}
    for record in tests:
        if record.attempt != attempt:
            raise CoreError(f"{record.gate} {record.bin}: scored at attempt {record.attempt}, the workflow's attempt is {attempt}")
        if record.required:
            if record.result == "not-applicable":
                raise CoreError(f"{record.gate} {record.bin}: a required test is never not-applicable (section 10)")
            gates[record.gate] = max(gates.get(record.gate, "pass"), record.result, key=_WORST.get)
        elif record.result == "inconclusive":
            obligations.append(Obligation(record.gate, None, f"ungated, {record.bin}: {record.reason}"))
        elif record.result != "not-applicable":
            raise CoreError(f"{record.gate} {record.bin}: an ungated bin is inconclusive with required no, never {record.result} (section 10)")
    for name in forbidden_constants:
        gates[name] = "void (read as fail)"
        reasons.append(f"configuration holds a forbidden constant: {name} (section 2.2)")
    for name in critical_false_success:
        gates[name] = "blocked"
        reasons.append(f"critical false success observed: {name} blocked")
    stop = False
    for check in checks:
        if check.result == "fail":
            reasons.append(f"{check.kind} check {check.name} does not pass")
            stop = stop or check.stop
        elif check.result == "gap":
            obligations.append(Obligation(check.name, None, "a recorded unsupported gap (R37)"))
    failing = [name for name, word in gates.items() if word != "pass"]
    if any(word == "inconclusive" for word in gates.values()):
        reasons.append("a required check was inconclusive (R11)")
    if failing or reasons:
        return WorkflowOutcome(workflow, gates, "fail", "failed", attempt, tuple(obligations), tuple(reasons), tuple(recorded), stop, True)
    state = "done (narrowed claim)" if obligations else "done"
    return WorkflowOutcome(workflow, gates, "pass", state, attempt, tuple(obligations), (), tuple(recorded), False, False)


def after_method_change(outcome: WorkflowOutcome, *, recorded: bool) -> WorkflowOutcome:
    """Section 10, "Failed, method changed and recorded": a new attempt (section 3.4), back to in-progress, the attempt count kept. Unrecorded,
    or after attempt 2, failed stands."""
    if outcome.r11_state != "failed" or not recorded or outcome.attempt >= 2:
        return outcome
    return dataclasses.replace(outcome, r11_state="in-progress", reasons=outcome.reasons + ("method changed and recorded: a new attempt (section 3.4)",))
