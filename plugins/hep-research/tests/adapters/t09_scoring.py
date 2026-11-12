"""T09 scoring on the statistics core (D4 stage E6c; d4-e6c-brief.md, item 2). Scoring side: the recipe never imports it.

Sections cited are of t04-values-v4.md (Freeze A); decisions are decisions.md's. From one complete bin (the recipe's products, the scoring-side
truth-start fits and the bin's truth file) to the core's typed records:

| Bin | Tests (v4 5.3: 333) | Required (v4 10: 270) |
| --- | --- | --- |
| main, 12 bins (9001, stratum 3 x N_exp bin + radial bin) | 7 parameters x (location, width, tail) = 21 pull tests + fit failure + wrong minimum + mis-ID (H1 truth) = 24 | B2-B4 pulls (189); every rate (36) |
| dead control (9002), B3 r [0.4, 0.7) | 21 pull tests, dead channels masked | 21 |
| saturation control (9003), B3 r [0.7, 0.9) | 21 pull tests, censored | 21 |
| pooled over main B2-B4 (strata 3 to 11) | mirrored, reversed: 2 rate tests, L = 0.5 % | 2 |
| two-source control (9004) | H2-truth mis-ID, L = 1 %, every event | 1 |

The 7 parameters (v4 7): x, y, z, the two direction components in the tangent plane at the truth direction (u1, u2), E_vis and t0; pulls of
every converged fit (a converged fit has an ok covariance, light_recipe.product), wrong minima included (v4 5.1, "Pull population"), by
t09_readings.event_pulls (imported, not copied). B1 pulls are ungated (v4 3.3: N_exp below 120): core.mark_ungated, obligation open.

- Fit failure (v4 9.3, 7): rate test, L = 1 %, all generated events; a failure is a reported fit that did not converge (no result, no finite
  covariance or the iteration budget reached: the recipe's failure kinds).
- Wrong minimum (v4 7, 9.3): rate test, L = 0.5 %, over events whose reported fit converged. Clause (a), the truth-start fit's ln L at least 0.5
  above the reported fit's, everywhere; clause (b), any of the 7 parameters more than 5 truth-start uncertainties from truth, only where
  pulls are gated (B2-B4); in B1 clause (b) is printed as a reading. Clauses from t09_truth_start (clause_a, clause_b_ratios, clause_b),
  imported. An event whose truth-start fit did not converge is "comparator unavailable" (D3 stage 3): it is a wrong minimum when the failed
  truth-start's last point already shows clause (a) (trust-exact only raises ln L), and otherwise left out of the denominator and printed
  (the open case O-unavailable of the E6c report).
- Mis-ID, H1 truth (v4 7, 9.3): rate test, L = 1 %, all events of each main bin; a mis-ID is H2 chosen. An event with no choice (H1 failed) is
  no mis-ID here; it is a fit failure already.
- Mirrored, reversed (v4 7, 9.4): 2 rate tests, L = 0.5 %, pooled over the main B2-B4 bins, from H1's reported fit (t09_topology_readings'
  definitions, imported): reversed over converged fits (cosine to truth below -0.5); mirrored over converged fits with |x_true| / R_s >= 0.4.
  The pool has no single stratum; its records carry the pool's name as bin and the identity of its first stratum (fixture 9001, stratum 3),
  which a rate test uses for the level only (the open case O-pool: the core's BinIdentity takes strata 0 to 11).
- Two-source, H2 truth (v4 9.4): rate test, L = 1 %, every event of the control; a miss is H1 chosen or, U-K4, an undecided event (H1 failed,
  no H2 fit, no choice).
- Negative checks (v4 9.4, 10 and 11: required, outside the budget; one that does not fire is fail): E1a, dead read as unhit, on the dead
  control's relabelled readout fitted by the frozen recipe: fires if at least one of x, y, z, t0 gives |centre| - z se > 0.10; E1b, the
  single-photon density on main B4 r [0.4, 0.7): fires if the t0 centre gives |centre| - z se > 0.10. The centre and its se are the core's
  (the trimmed centre and the bin's own event bootstrap, B = 1,000, seeded from the bin's identity, v4 5.1); z is FIRES_ALPHA_OF_ATTEMPT's (fix round 1, the user's answer: 1.645 at both attempts):
  1.645 at attempt 1 (v4 9.4, "at 95 %"); 2.326 at attempt 2, read from v4 3.4 ("on every test") as the core reads the paired bound: a
  reading awaiting the user (K09), named apart.
- Deterministic (v4 9.3, 9.4, 11): the per-channel probability sum at every reported point, H1 and H2 (the products' own checks, recomputed
  by check-product before); dead channels excluded, never unhit (t09_readings.dead_state_defects); the topology product carries its
  multistart product unchanged (t09_topology_readings.carry_defects); the likelihood check and the per-channel sum at the 50 fixed points
  of block 6 (t09_fixed_points.py, its three GATE lines), passed in by the evaluation's fixed-point task.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy
from scipy import stats

from tests.adapters import t04_evaluation_core as core
from tests.adapters.t04_bin_scorer import DEVELOPMENT_ATTEMPT, BinScorer, ScoringError

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "photon-likelihood" / "assets"
for _folder in (ROOT, ASSETS, ASSETS / "fixture_tools"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import t09_readings as readings  # noqa: E402
import t09_topology_readings as topology_readings  # noqa: E402
import t09_truth_start as truth_start  # noqa: E402

WORKFLOW = "T09"
FIXTURE_OF_ID = {9001: "main", 9002: "dead", 9003: "saturation", 9004: "two-source"}   # v4 3.2
RADIAL = ("r0.0-0.4", "r0.4-0.7", "r0.7-0.9")
PARAMETERS = readings.PULL_NAMES_JOINT          # x, y, z, u1, u2, e_vis, t0 (v4 7: 7 parameters)
GATED_N_BINS = (1, 2, 3)                        # v4 3.3: B2-B4 gated (index from 0); B1 ungated
FIT_FAILURE_LIMIT = 0.01                        # v4 9.3
WRONG_MINIMUM_LIMIT = 0.005                     # v4 9.3
MISID_LIMIT = 0.01                              # v4 9.3 (H1 truth) and 9.4 (two-source)
MIRROR_REVERSED_LIMIT = 0.005                   # v4 9.4
POOLED_STRATA = tuple(topology_readings.POOLED_STRATA)   # main strata 3 to 11: B2-B4
FIRES_TOLERANCE = 0.10                          # v4 9.4: |centre| - z se > 0.10
# Reading awaiting the user (K09), as the core's PAIRED_ALPHA_OF_ATTEMPT: v4 9.4 says 1.645 ("at 95 %"); v4 3.4 says 99 % "on every test".
# The user's answer (decisions.md, "The user's answers on the attempt-2 levels (K09, 2026-11-12)"): the "fires" rules use 1.645 at both attempts
# (they test that a check sees a known defect, outside the 1,260-test family; v4 9.4's sensitivity-screened value).
FIRES_ALPHA_OF_ATTEMPT = {1: 0.05, 2: 0.05}
# The user's answer (decisions.md, "The user's answers: wrong minimum without a truth-start fit ...", 2026-11-12): an event whose truth-start
# comparator fit failed counts as a wrong minimum (v4 5.1: "Objects with no result count in a failure rate"); the count is printed. Fixed: the
# other reading ("left out unless its last point shows clause (a)") is refused.
WRONG_MINIMUM_WITHOUT_TRUTH_START = "counted"
POOL = core.PooledIdentity  # the pooled bin of mirrored and reversed: pool 0 of fixture 9001, main strata 3 to 11 (v4 9.4)
E1A_PARAMETERS = ("x", "y", "z", "t0")          # v4 9.4
E1B_PARAMETERS = ("t0",)
E1B_STRATUM = 10                                # main B4, r/R_s [0.4, 0.7)
TESTS_TOTAL, TESTS_REQUIRED = 333, 270          # v4 5.3 and 10
B1_REASON = ("ungated, v4 3.3: N_exp below 120 (B1), no result shows a correct fit has unit pulls there; obligation open (v4 10, T09 B1 pulls)")


@dataclass(frozen=True)
class BinKind:
    fixture_id: int
    stratum: int
    fixture: str
    n_bin: int           # 0 to 3: B1 to B4
    radial: int

    @property
    def name(self) -> str:
        if self.fixture == "main":
            return f"main-B{self.n_bin + 1}-{RADIAL[self.radial]}"
        return {"dead": "dead-B3", "saturation": "saturation-B3", "two-source": "two-source"}[self.fixture]


def bin_kind(fixture_id: int, stratum: int) -> BinKind:
    fixture = FIXTURE_OF_ID.get(fixture_id)
    if fixture is None:
        raise ScoringError(f"fixture {fixture_id} is not a T09 fixture (v4 3.2: 9001 to 9004)")
    if fixture == "main":
        if not 0 <= stratum < 12:
            raise ScoringError(f"main stratum {stratum} is outside 0 to 11")
        return BinKind(fixture_id, stratum, fixture, stratum // 3, stratum % 3)
    if stratum != 0:
        raise ScoringError(f"the {fixture} control has stratum 0 only")
    return BinKind(fixture_id, 0, fixture, 2, {"dead": 1, "saturation": 2, "two-source": 0}[fixture])


ALL_BINS = tuple(bin_kind(9001, s) for s in range(12)) + tuple(bin_kind(f, 0) for f in (9002, 9003, 9004))
POOL_NAME = "pooled main B2-B4 (strata 3 to 11)"


def _pull_gates(required: bool, reason: str) -> list:
    return [(f"{name} pulls", statistic, required, reason) for name in PARAMETERS for statistic in ("trimmed-centre", "sigma68-width", "tail")]


def gates_of_bin(kind: BinKind) -> list:
    """The bin's tests in record order: (gate, statistic, required, reason)."""
    if kind.fixture == "main":
        gated = kind.n_bin in GATED_N_BINS
        return _pull_gates(gated, "" if gated else B1_REASON) + [("fit failure", "rate", True, ""), ("wrong minimum", "rate", True, ""),
                                                                 ("mis-ID H1 truth", "rate", True, "")]
    if kind.fixture in ("dead", "saturation"):
        return _pull_gates(True, "")
    return [("mis-ID H2 truth", "rate", True, "")]


POOL_GATES = [("reversed", "rate", True, ""), ("mirrored", "rate", True, "")]


def count_tests() -> dict:
    """v4 5.3's count (333: 288 main, 45 controls) and v4 10's required set (270); refuses another count."""
    main = sum(len(gates_of_bin(k)) for k in ALL_BINS if k.fixture == "main")
    controls = sum(len(gates_of_bin(k)) for k in ALL_BINS if k.fixture != "main") + len(POOL_GATES)
    required = sum(1 for k in ALL_BINS for g in gates_of_bin(k) if g[2]) + len(POOL_GATES)
    if (main, controls, required) != (288, 45, TESTS_REQUIRED) or main + controls != TESTS_TOTAL:
        raise ScoringError(f"T09 has {main} + {controls} tests and {required} required; v4 5.3 and 10 fix 288 + 45 = 333 and 270")
    return {"total": main + controls, "required": required, "main": main, "controls": controls}


# ---- per-event values

def event_parameter_pulls(events: list, truth: dict) -> dict:
    """Per parameter, one list per event: the pull of its converged reported fit, or empty (v4 5.1's population; failures in the rate)."""
    out = {name: [] for name in PARAMETERS}
    for i, doc in enumerate(events):
        fit_doc = doc["fit"]
        if fit_doc["status"] != "converged":
            for name in PARAMETERS:
                out[name].append([])
            continue
        values = readings.event_pulls(fit_doc, truth["vertex"][i], truth["direction"][i], truth["e_vis"][i], float(truth["t0"][i]))
        for name in PARAMETERS:
            out[name].append([values[name]])
    return out


def wrong_minimum_counts(events: list, truth_start_docs: list, truth: dict, clause_b_counted: bool, *,
                         without_truth_start: str = WRONG_MINIMUM_WITHOUT_TRUTH_START) -> dict:
    """Per event: m (1 if the reported fit converged, else 0) and y (wrong); with the reading counts. An event whose truth-start fit failed
    counts as a wrong minimum (the user's answer; WRONG_MINIMUM_WITHOUT_TRUTH_START); any other rule is refused."""
    if without_truth_start != "counted":
        raise ScoringError(f"wrong minimum without a truth-start fit: {without_truth_start!r} is refused; the user's answer is 'counted' (2026-11-12)")
    m, y = [], []
    counts = {"converged": 0, "evaluated": 0, "unavailable": 0, "unavailable_shows_a": 0, "clause_a": 0, "clause_b": 0, "clause_b_reported": 0}
    for i, (doc, ts) in enumerate(zip(events, truth_start_docs)):
        fit_doc = doc["fit"]
        if fit_doc["status"] != "converged":
            m.append(0)
            y.append(0)
            continue
        counts["converged"] += 1
        if ts["status"] != "converged":
            counts["unavailable"] += 1
            shows = ts["ln_likelihood"] is not None and truth_start.clause_a(fit_doc["ln_likelihood"], ts["ln_likelihood"])
            counts["unavailable_shows_a"] += shows
            m.append(1)
            y.append(1)
            continue
        counts["evaluated"] += 1
        t = {"vertex": truth["vertex"][i], "direction": truth["direction"][i], "e_vis": float(truth["e_vis"][i]), "t0": float(truth["t0"][i])}
        a = truth_start.clause_a(fit_doc["ln_likelihood"], ts["ln_likelihood"])
        b = truth_start.clause_b(truth_start.clause_b_ratios(fit_doc, t, ts))
        counts["clause_a"] += a
        counts["clause_b" if clause_b_counted else "clause_b_reported"] += b
        m.append(1)
        y.append(int(a or (b and clause_b_counted)))
    if len(m) != len(events) or len(truth_start_docs) != len(events):
        raise ScoringError("the truth-start fits and the products hold different event counts")
    return {"m": m, "y": y, **counts}


def two_source_misses(events: list) -> list:
    """U-K4: a miss is H1 chosen, or no choice (H1 failed, no H2 fit)."""
    return [int(doc["topology"]["choice"] != "H2") for doc in events]


def fires(centre: core.TestResult, attempt: int) -> tuple:
    """v4 9.4: (|centre| - z se, fires) from the core's centre record; z of FIRES_ALPHA_OF_ATTEMPT."""
    if centre.estimate is None or centre.standard_error is None:
        return None, False
    z = float(stats.norm.isf(FIRES_ALPHA_OF_ATTEMPT[attempt]))
    value = abs(centre.estimate) - z * centre.standard_error
    return value, bool(value > FIRES_TOLERANCE)


def probability_defects(events: list, with_h2: bool = False) -> list:
    """The per-channel probability sum (the T09 stop) at every reported point, from each event's own check record."""
    out = [f"event {d['event']}: {d['probability_check']['failures']} channels" for d in events if d["probability_check"]["failures"]]
    if with_h2:
        out += [f"event {d['event']} H2: {d['topology']['probability_check']['failures']} channels" for d in events
                if d["topology"]["probability_check"] is not None and d["topology"]["probability_check"]["failures"]]
    return out


# ---- one bin

@dataclass
class BinScore:
    kind: BinKind
    records: list
    defects: dict
    lines: list = field(default_factory=list)


def _check_truth(identity, kind, header, count, readout_sha256=None):
    if header.get("fixture") != kind.fixture or int(header.get("stratum", -1)) != kind.stratum or int(header.get("block", -1)) != identity.block:
        raise ScoringError(f"the truth file is {header.get('fixture')} block {header.get('block')} stratum {header.get('stratum')}, not {identity.label}")
    if int(header.get("events", -1)) != count:
        raise ScoringError(f"the truth file holds {header.get('events')} events, the products {count}")
    if readout_sha256 is not None and header.get("readout_sha256") != readout_sha256:
        raise ScoringError("the truth file belongs to another readout")


def score_bin(identity: core.BinIdentity, events: list, truth_header: dict, truth: dict, *, truth_start_docs=None, readout_sha256=None,
              carry_defects=()) -> BinScore:
    """The records of one complete T09 bin. events: the bin's event documents in order (the ranges merged): the topology product's (/4) for a
    main bin and the two-source control, the multistart product's (/3) for the dead and saturation controls; truth_start_docs: the
    truth-start fits of a main bin; readout_sha256: the bin's stratum readout (the truth file must name it); carry_defects: the ranges' /4
    against /3 defects (t09_topology_readings.carry_defects), computed per range by the caller."""
    if identity.workflow != WORKFLOW:
        raise ScoringError(f"{identity.label} is not a T09 bin")
    kind = bin_kind(identity.fixture_id, identity.stratum)
    _check_truth(identity, kind, truth_header, len(events), readout_sha256)
    for i, doc in enumerate(events):
        if doc["event"] != i:
            raise ScoringError(f"event {i} carries index {doc['event']}: the ranges were not merged in order")
    scorer = BinScorer(identity)
    records, lines = [], []
    defects = {"probability sum": probability_defects(events, with_h2=kind.fixture in ("main", "two-source")),
               "dead channels excluded": readings.dead_state_defects(events, truth["dead_channels"]) if kind.fixture != "two-source" else [],
               "topology carries multistart": list(carry_defects)}
    if kind.fixture == "two-source":
        misses = two_source_misses(events)
        undecided = sum(doc["topology"]["choice"] is None for doc in events)
        records.append(scorer.rate("mis-ID H2 truth", [1] * len(events), misses, MISID_LIMIT))
        lines.append(f"READING {scorer.label} H2-truth misses {sum(misses)} of {len(events)}, of which undecided (H1 failed, no H2 fit, no choice; "
                     f"counted as misses, U-K4) {undecided}")
    else:
        pulls = event_parameter_pulls(events, truth)
        gated = kind.fixture != "main" or kind.n_bin in GATED_N_BINS
        for name in PARAMETERS:
            records += scorer.pulls(f"{name} pulls", pulls[name], required=gated, reason="" if gated else B1_REASON)
        failures = [int(doc["fit"]["status"] != "converged") for doc in events]
        kinds = {}
        for doc in events:
            if doc["fit"]["status"] != "converged":
                kinds[doc["fit"]["failure"]] = kinds.get(doc["fit"]["failure"], 0) + 1
        lines.append(f"READING {scorer.label} fit failures {sum(failures)} of {len(events)} by kind {dict(sorted(kinds.items()))}")
        if kind.fixture == "main":
            records.append(scorer.rate("fit failure", [1] * len(events), failures, FIT_FAILURE_LIMIT))
            if truth_start_docs is None:
                records.append(scorer.missing("wrong minimum", "rate", "no truth-start fits for the bin"))
            else:
                counted = kind.n_bin in GATED_N_BINS
                wm = wrong_minimum_counts(events, truth_start_docs, truth, counted)
                records.append(scorer.rate("wrong minimum", wm["m"], wm["y"], WRONG_MINIMUM_LIMIT))
                lines.append(f"READING {scorer.label} wrong minimum: converged {wm['converged']}, evaluated {wm['evaluated']}, clause (a) {wm['clause_a']}, "
                             f"clause (b) {'counted' if counted else 'reported only (B1)'} {wm['clause_b'] if counted else wm['clause_b_reported']}; "
                             f"comparator unavailable (truth-start fit failed) {wm['unavailable']}, each counted as a wrong minimum (the user, 2026-11-12); "
                             f"of them, clause (a) already shown by the failed truth-start's last point {wm['unavailable_shows_a']}")
            misid = [int(doc["topology"]["choice"] == "H2") for doc in events]
            records.append(scorer.rate("mis-ID H1 truth", [1] * len(events), misid, MISID_LIMIT))
            lines.append(f"READING {scorer.label} H1-truth mis-ID {sum(misid)} of {len(events)}; no choice (H1 failed) "
                         f"{sum(doc['topology']['choice'] is None for doc in events)}")
    want = [(g, s) for g, s, _, _ in gates_of_bin(kind)]
    have = [(r.gate, r.statistic) for r in records]
    if have != want:
        raise ScoringError(f"{identity.label}: the records {have} are not the bin's tests {want}")
    return BinScore(kind, records, defects, lines)


def pool_identity(block: int) -> core.PooledIdentity:
    return core.PooledIdentity(WORKFLOW, 9001, block, 0, POOLED_STRATA, POOL_NAME)


def pool_columns(events: list, truth: dict) -> dict:
    """One bin's per-event (m, y) of reversed and mirrored (v4 7, 9.4), from H1's reported fit: what the pool reads (fix round 1, review I3:
    each scoring task writes these, so the pool never holds the bins' documents)."""
    r_s = sphere_radius()
    out = {"reversed_m": [], "reversed_y": [], "mirrored_m": [], "mirrored_y": []}
    for i, doc in enumerate(events):
        f = doc["fit"]
        converged = f["status"] == "converged"
        out["reversed_m"].append(int(converged))
        out["reversed_y"].append(int(converged and topology_readings.reversed_fit(f["direction"], truth["direction"][i])))
        population = converged and topology_readings.in_mirror_population(truth["vertex"][i], r_s)
        out["mirrored_m"].append(int(population))
        out["mirrored_y"].append(int(population and topology_readings.mirrored_fit(f["vertex"], truth["vertex"][i])))
    return {k: numpy.asarray(v, dtype=numpy.int64) for k, v in out.items()}


def score_pool(block: int, columns) -> list:
    """Mirrored and reversed, pooled over the main B2-B4 bins (v4 9.4), on the pooled identity (core.PooledIdentity). columns: {stratum:
    pool_columns(...)} for exactly strata 3 to 11."""
    if sorted(columns) != list(POOLED_STRATA):
        raise ScoringError(f"the pool needs main strata {list(POOLED_STRATA)}, not {sorted(columns)}")
    joined = {k: numpy.concatenate([columns[s][k] for s in POOLED_STRATA]) for k in ("reversed_m", "reversed_y", "mirrored_m", "mirrored_y")}
    scorer = BinScorer(pool_identity(block))
    return [scorer.rate("reversed", joined["reversed_m"], joined["reversed_y"], MIRROR_REVERSED_LIMIT),
            scorer.rate("mirrored", joined["mirrored_m"], joined["mirrored_y"], MIRROR_REVERSED_LIMIT)]


def sphere_radius() -> float:
    from light_recipe import configuration
    return configuration.load().sphere_radius_m


def negative_check(identity: core.BinIdentity, name: str, events: list, truth: dict, parameters) -> tuple:
    """E1a or E1b (v4 9.4): (core.CheckResult, lines). The centres of the named parameters with the bin's own bootstrap; fires if any
    exceeds; a check that does not fire is fail."""
    scorer = BinScorer(identity)
    pulls = event_parameter_pulls(events, truth)
    attempt = DEVELOPMENT_ATTEMPT if scorer.development else identity.level.attempt
    lines, fired = [], False
    for parameter in parameters:
        centre = scorer.pulls(f"{name} {parameter}", pulls[parameter])[0]
        value, hit = fires(centre, attempt)
        fired = fired or hit
        lines.append(f"READING {scorer.label} {name} {parameter}: centre {centre.estimate} se {centre.standard_error} |centre| - z se "
                     f"{value} (z {stats.norm.isf(FIRES_ALPHA_OF_ATTEMPT[attempt]):.4f}): {'fires' if hit else 'does not fire'}")
    return core.CheckResult(name, "negative", "pass" if fired else "fail"), lines


def missing_records(identity: core.BinIdentity, why: str) -> list:
    kind = bin_kind(identity.fixture_id, identity.stratum)
    scorer = BinScorer(identity)
    return [scorer.missing(gate, statistic, why, required=required, reason=reason) for gate, statistic, required, reason in gates_of_bin(kind)]


def missing_pool(block: int, why: str) -> list:
    scorer = BinScorer(pool_identity(block))
    return [scorer.missing(gate, statistic, why) for gate, statistic, _, _ in POOL_GATES]


def bin_checks(score: BinScore) -> list:
    out = []
    for name, defects in score.defects.items():
        if name == "topology carries multistart" and score.kind.fixture not in ("main", "two-source"):
            continue
        out.append(core.CheckResult(f"{name} {score.kind.name}", "deterministic", "fail" if defects else "pass", stop=(name == "probability sum" and bool(defects))))
    return out


E1A_NAME = "dead read as unhit (E1a)"
E1B_NAME = "single-photon density (E1b)"
FIXED_POINTS_NAME = "fixed likelihood points (likelihood check, per-channel sum)"


def required_checks(missing=()) -> tuple:
    """Every check a T09 outcome needs (v4 9.3, 9.4, 10, 11; fix round 1, review I2): per bin the probability sum, the dead channels (not the
    two-source control) and the topology carry (main and two-source); E1a (the dead control's) and E1b (main stratum 10's); the fixed points. T09
    has no CAI check. missing: labels of bins the collection marked missing (recipe side): their own checks cannot exist, and the bin fails
    through its "required output missing" records instead."""
    names = []
    missing = set(missing)
    for kind in ALL_BINS:
        if kind.name in missing:
            continue
        names.append(f"probability sum {kind.name}")
        if kind.fixture != "two-source":
            names.append(f"dead channels excluded {kind.name}")
        if kind.fixture in ("main", "two-source"):
            names.append(f"topology carries multistart {kind.name}")
    names += [n for n, owner in ((E1A_NAME, "dead-B3"), (E1B_NAME, "main-B4-r0.4-0.7")) if owner not in missing]
    return tuple(names) + (FIXED_POINTS_NAME,)


def slim(doc: dict) -> dict:
    """The fields the scoring reads of one event document (fix round 1, review I3: the merged bin keeps these, not the products' documents)."""
    out = {"event": doc["event"], "fit": doc["fit"], "states": doc["states"], "probability_check": {"failures": doc["probability_check"]["failures"]}}
    if "topology" in doc:
        check = doc["topology"]["probability_check"]
        out["topology"] = {"choice": doc["topology"]["choice"], "probability_check": None if check is None else {"failures": check["failures"]}}
    return out


def fixed_point_check(gate_lines) -> core.CheckResult:
    """v4 9.3's likelihood check and per-channel sum at the 50 fixed points: t09_fixed_points.py's three GATE lines, each PASS."""
    lines = [line for line in gate_lines if line.startswith("GATE ")]
    ok = len(lines) == 3 and all(line.endswith("PASS") for line in lines)
    return core.CheckResult(FIXED_POINTS_NAME, "deterministic", "pass" if ok else "fail", stop=not ok)


def merged_events(products) -> list:
    """The event documents of one bin from its range products, in order of their first event, renumbered from 0."""
    out = []
    for p in products:
        for doc in p.events:
            out.append(dict(doc, event=len(out)))
    return out


def merged_docs(range_docs) -> list:
    out = []
    for docs in range_docs:
        for doc in docs:
            out.append(dict(doc, event=len(out)))
    return out

