"""T08 scoring on the statistics core (D4 stage E6c; d4-e6c-brief.md, item 1). Scoring side: the recipe never imports it.

Sections cited are of t04-values-v4.md (Freeze A); decisions are decisions.md's. From one complete bin (the recipe's calo-cluster-product/1
events and the bin's t08-truth/1 file) to the core's typed records, every gate of v4 9.1 and the controls of 9.2:

| Bin | Tests (v4 5.3: 101 in all) | Required (v4 10: 80) |
| --- | --- | --- |
| main iso, E1-E4 (8001, strata 0, 3, 6, 9) | energy, x, y pulls (location, width, tail: 9) + efficiency = 10 | E2-E4 pulls (27), efficiency E1-E4 (4) |
| main far, E1-E4 (8001, strata 1, 4, 7, 10) | the same 10, + merge in E2-E4 (3) | E2-E4 pulls (27), efficiency (4), merge (3) |
| main near, E1-E4 (8001, strata 2, 5, 8, 11) | total energy pulls (3) | E2-E4 (9) |
| edge control, E3 (8002) | event-sum energy pulls, target E Phi(t) - b_edge(t), pooled over the four t (3) | 3 |
| dead control, E3 (8003) | event-sum energy pulls, target E (1 - f) - b_dead (3) | 3 |
| saturation control, E4 (8004) | none (its flag is a deterministic check) | - |

E1 pulls (21 tests) are ungated (v4 3.3: the seed reference p at E1's lower edge is 0.84, below 0.99): each is core.mark_ungated, numbers only,
inconclusive, required no, its obligation open. The near efficiency has no reference (v4 4.2) and E1 merge is reported (v4 9.1): both are
readings, never records, as v4 5.3's count has them.

Definitions, taken from the development readings module (fixture_tools/t08_readings.py, in the Freeze-B run's manifest; imported, not
copied): cluster match at more than 50 % of a shower's energy in the object, primary by share then energy then index, and a primary whose
uncertainty status is not ok leaves the shower without one (v4 7, 7.1); which sum enters (v4 7.1: the event sum in iso, edge, dead and near,
the primary object in far; position of the largest object in iso, of the primary in far); targets from job 7479146's frozen log (v4 4.2):
E - b_iso, E - b_far(E, d) and 2E - b_near(E, d) bilinear in (ln E, d) on the log's nodes, never extrapolated (t08_readings.bilinear; v4 7.1,
"Interpolation of tables"), E Phi(t) - b_edge(t), E (1 - f) - b_dead. Merge: a two-shower event whose showers give their largest energy share
to one object (v4 7); denominator far events.

Efficiency (U-K5): gated on the seed-firing efficiency, the quantity of the closed-form reference: a shower's seed fired when a cell of the
product with read value at or above T_s (10 MeV, v4 4.2) takes its largest truth deposit from that shower (seed_fired; "the far case takes each
shower alone", v4 4.2). Failures: showers whose seed did not fire. The reference R is v4's closed form, the integral over ln E and sub-cell
position (v4 4.2 "Other references"; 18.1, "T08 quoted values"): 0.9924 in E1, 1.000 in E2-E4; the lower limit is R - delta(R), delta 0.01
throughout (v4 5.2). R is a bin constant, not a node interpolation: linear interpolation of the log's `closed` column in ln E gives 0.984 over
E1 (iso nodes) or 0.960 (pair nodes), below the integral by 0.008 and 0.032, the unsafe direction (test_t08_scoring, EfficiencyReference).
The matched-primary-with-ok-uncertainty rate is printed beside it as a reading (U-K5).

Deterministic checks (v4 9.1, 9.2, 11), per sample: conservation (clustered plus unclustered equals the input within 1e-9 relative; fractions
sum to 1 for each cell of a component with objects, and to 0 for a failed component's cells, which the product format records apart); no cell
counted twice (the sheet's stop: product.double_count_defects); a dead cell never in a cluster; in the saturation control every object with a
clipped cell carries the flag and its energy is marked a lower bound, zero exceptions, its clipped cells read against the readout's own flags
when the cells file is given. Negative cases (v4 9.2): digital read as analog (a digital-typed input built here from the sample's own cells:
the recipe's reader must refuse it by type) and deposited energy used as incident (the product's header with energy kind incident-energy: the
recipe's product reader must refuse it by the named-energy check). U-K6: the leakage and threshold failure classes are judged through the
edge control and the efficiency gates only; the claim is narrowed and the obligation listed (FOUND_OBLIGATIONS).
"""
from __future__ import annotations

import dataclasses
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy

from tests.adapters import t04_evaluation_core as core
from tests.adapters.t04_bin_scorer import BinScorer, ScoringError

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "adapters" / "calo-cluster" / "assets"
for _folder in (ASSETS, ASSETS / "fixture_tools"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import t08_readings as readings  # noqa: E402  (the development readings' definitions, reused by import)

WORKFLOW = "T08"
FIXTURE_OF_ID = {8001: "main", 8002: "edge", 8003: "dead", 8004: "saturation"}      # v4 3.2
SEPARATIONS = ("iso", "far", "near")                                                  # v4 4.2: main stratum s is E(s // 3 + 1), separation s % 3
CONTROL_ENERGY_BIN = {"edge": 2, "dead": 2, "saturation": 3}                         # v4 4.2: edge and dead E3, saturation E4 (index from 0)
SEED_THRESHOLD_MEV = 10.0                    # v4 4.2, T_s
GATED_ENERGY_BINS = (1, 2, 3)                # v4 3.3: E2-E4 gated; E1 (index 0) ungated
REFERENCE_EFFICIENCY = {0: 0.9924, 1: 1.000, 2: 1.000, 3: 1.000}   # v4 4.2 and 18.1: R, the integral over ln E and sub-cell position
MERGE_LIMIT = 0.01                           # v4 9.1, merge: L = 1 %
RELATIVE_CONSERVATION = 1e-9                 # v4 9.1, conservation
TESTS_TOTAL, TESTS_REQUIRED = 101, 80        # v4 5.3 and 10
E1_REASON = ("ungated, v4 3.3: the seed reference p is below 0.99 at E1's lower edge (0.84), so a pull is conditional on the cells that fired "
             "the seed; obligation open (v4 10, T08 E1 pulls)")
FOUND_OBLIGATIONS = (core.Obligation("T08 leakage and threshold failure classes", None,
                                     "U-K6: judged through the edge control and the efficiency gates only; claim narrowed and stated"),)
PULLS = ("energy pulls", "position x pulls", "position y pulls")
NEAR_PULLS = ("total energy pulls",)
EDGE_PULLS = ("edge energy pulls",)
DEAD_PULLS = ("dead energy pulls",)


@dataclass(frozen=True)
class BinKind:
    fixture_id: int
    stratum: int
    fixture: str
    separation: str
    energy_bin: int          # 0 to 3: E1 to E4

    @property
    def name(self) -> str:
        if self.fixture == "main":
            return f"main-E{self.energy_bin + 1}-{self.separation}"
        return f"{self.fixture}-E{self.energy_bin + 1}"


def bin_kind(fixture_id: int, stratum: int) -> BinKind:
    fixture = FIXTURE_OF_ID.get(fixture_id)
    if fixture is None:
        raise ScoringError(f"fixture {fixture_id} is not a T08 fixture (v4 3.2: 8001 to 8004)")
    if fixture == "main":
        if not 0 <= stratum < 12:
            raise ScoringError(f"main stratum {stratum} is outside 0 to 11")
        return BinKind(fixture_id, stratum, fixture, SEPARATIONS[stratum % 3], stratum // 3)
    if stratum != 0:
        raise ScoringError(f"the {fixture} control has stratum 0 only, not {stratum}")
    return BinKind(fixture_id, 0, fixture, "iso", CONTROL_ENERGY_BIN[fixture])


ALL_BINS = tuple(bin_kind(8001, s) for s in range(12)) + tuple(bin_kind(f, 0) for f in (8002, 8003, 8004))


def gates_of_bin(kind: BinKind) -> list:
    """The bin's tests, in record order: (gate, statistic, required, reason). The count of section 5.3, by construction of each bin."""
    out = []
    pulls_required = kind.energy_bin in GATED_ENERGY_BINS
    reason = "" if pulls_required else E1_REASON

    def pull(gate):
        out.extend((gate, statistic, pulls_required, reason) for statistic in ("trimmed-centre", "sigma68-width", "tail"))
    if kind.fixture == "main" and kind.separation in ("iso", "far"):
        for gate in PULLS:
            pull(gate)
        out.append(("efficiency", "efficiency", True, ""))
        if kind.separation == "far" and pulls_required:
            out.append(("merge", "rate", True, ""))
    elif kind.fixture == "main":
        pull(NEAR_PULLS[0])
    elif kind.fixture == "edge":
        out.extend((EDGE_PULLS[0], statistic, True, "") for statistic in ("trimmed-centre", "sigma68-width", "tail"))
    elif kind.fixture == "dead":
        out.extend((DEAD_PULLS[0], statistic, True, "") for statistic in ("trimmed-centre", "sigma68-width", "tail"))
    return out


def count_tests() -> dict:
    """v4 5.3's count (101: 40 iso, 43 far, 12 near, 6 controls) and v4 10's required set (80), from gates_of_bin; refuses another count."""
    by = {"iso": 0, "far": 0, "near": 0, "controls": 0}
    required = 0
    for kind in ALL_BINS:
        gates = gates_of_bin(kind)
        by[kind.separation if kind.fixture == "main" else "controls"] += len(gates)
        required += sum(1 for g in gates if g[2])
    total = sum(by.values())
    if (total, required, by) != (TESTS_TOTAL, TESTS_REQUIRED, {"iso": 40, "far": 43, "near": 12, "controls": 6}):
        raise ScoringError(f"T08 has {total} tests ({by}) and {required} required; v4 5.3 and 10 fix 101 (40, 43, 12, 6) and 80")
    return {"total": total, "required": required, **by}


def efficiency_lower_limit(reference: float) -> float:
    """R - delta(R) (v4 5.2). At R = 1.000 (E2-E4) delta's formula gives its floor 0.01 (the core's efficiency_margin takes R in (0, 1))."""
    if reference >= 1.0:
        return reference - core.DELTA_FLOOR
    return core.efficiency_lower_limit(reference)


# ---- per-event definitions

def seed_fired(event: dict, deposit, n_showers: int, threshold: float = SEED_THRESHOLD_MEV) -> list:
    """U-K5: per shower, whether its seed fired: some product cell with e_c >= T_s takes its largest truth deposit from that shower (ties to
    the lower shower index; a cell with no truth deposit belongs to none)."""
    flat = numpy.asarray(deposit, float).reshape(deposit.shape[0], -1)
    fired = [False] * n_showers
    for row in event["cells"]:
        channel, value = row[0], row[5]
        if value < threshold:
            continue
        shares = flat[:n_showers, channel]
        if shares.size and shares.max() > 0:
            fired[int(numpy.argmax(shares))] = True
    return fired


def conservation_defects(event: dict) -> list:
    """v4 9.1: clustered plus unclustered equals the input within 1e-9 relative; fractions sum to 1 for each cell of a component with objects,
    0 for a failed component's cells."""
    defects = []
    total = event["clustered_sum"] + event["unclustered_sum"]
    if abs(total - event["input_sum"]) > RELATIVE_CONSERVATION * max(abs(event["input_sum"]), 1.0):
        defects.append(f"event {event['event']}: clustered {event['clustered_sum']} plus unclustered {event['unclustered_sum']} is not the input "
                       f"{event['input_sum']} within 1e-9 relative")
    shares = {}
    for cluster in event["objects"]:
        for channel, fraction in cluster["members"]:
            shares[channel] = shares.get(channel, 0.0) + fraction
    failed = {c["component"] for c in event["components"] if c["failure"] is not None}
    for row in event["cells"]:
        channel, component = row[0], row[7]
        want = 0.0 if component in failed else 1.0
        if abs(shares.get(channel, 0.0) - want) > RELATIVE_CONSERVATION:
            defects.append(f"event {event['event']}: cell {channel}'s fractions sum to {shares.get(channel, 0.0)}, not {want}")
    return defects


def dead_cell_defects(event: dict) -> list:
    """v4 9.2, dead cells: a dead cell is never in a cluster (neither a kept cell nor a member)."""
    dead = set(event["dead_channels"])
    defects = [f"event {event['event']}: dead cell {row[0]} is a kept cell" for row in event["cells"] if row[0] in dead]
    defects += [f"event {event['event']}: dead cell {c} is a member of object {o['object']}" for o in event["objects"] for c, _ in o["members"] if c in dead]
    return defects


def saturation_defects(event: dict, saturated_cells=None) -> list:
    """v4 9.2, saturation: every object with a clipped cell carries the flag and its energy is marked a lower bound; zero exceptions.
    saturated_cells: the readout's own flags of this event (flat, by channel), when the cells file is given."""
    defects = []
    flag = {row[0]: row[6] for row in event["cells"]}
    if saturated_cells is not None:
        own = numpy.asarray(saturated_cells, bool).ravel()
        flag = {channel: int(own[channel]) for channel in flag}
        for row in event["cells"]:
            if row[6] != int(own[row[0]]):
                defects.append(f"event {event['event']}: cell {row[0]}'s saturated flag {row[6]} is not the readout's {int(own[row[0]])}")
    for cluster in event["objects"]:
        clipped = any(fraction > 0.0 and flag.get(channel) == 1 for channel, fraction in cluster["members"])
        if clipped and (cluster["saturated"] is not True or cluster["energy_bound"] != "lower-bound"):
            defects.append(f"event {event['event']}: object {cluster['object']} holds a clipped cell but is not flagged with a lower bound")
    return defects


# ---- one sample

@dataclass
class SampleScore:
    kind: BinKind
    records: list
    defects: dict
    lines: list = field(default_factory=list)


def _check_truth(identity: core.BinIdentity, kind: BinKind, header: dict, events: list):
    if header.get("fixture") != kind.fixture or int(header.get("stratum", -1)) != kind.stratum or int(header.get("block", -1)) != identity.block:
        raise ScoringError(f"the truth file is {header.get('fixture')} block {header.get('block')} stratum {header.get('stratum')}, not the bin "
                           f"{identity.label}")
    if int(header.get("events", -1)) != len(events):
        raise ScoringError(f"the truth file holds {header.get('events')} events, the products {len(events)}")
    if kind.fixture == "main" and header.get("separation") != kind.separation:
        raise ScoringError(f"the truth file's separation is {header.get('separation')}, the bin's {kind.separation}")


def score_sample(identity: core.BinIdentity, events: list, truth_header: dict, truth: dict, reference: dict, *, saturated=None,
                 products_header: dict | None = None) -> SampleScore:
    """The records of one complete T08 bin, its deterministic defects and its reading lines. events: the bin's product event documents in event
    order (the ranges merged); truth: t08_fixture_files.read_truth's arrays; reference: t08_readings.parse_reference of job 7479146's log;
    saturated: the cells file's saturated flags (events, nx, ny), for the saturation check; products_header: one product header, whose
    configuration must be t08-grid/1's (t08_readings.REFERENCE_CONFIGURATION_SHA256: the targets carry that selection, v4 9.2)."""
    if identity.workflow != WORKFLOW:
        raise ScoringError(f"{identity.label} is not a T08 bin")
    kind = bin_kind(identity.fixture_id, identity.stratum)
    _check_truth(identity, kind, truth_header, events)
    if products_header is not None and products_header["configuration"]["sha256"] != readings.REFERENCE_CONFIGURATION_SHA256:
        raise ScoringError("the product's configuration is not t08-grid/1's, whose selection the reference constants carry (v4 9.2)")
    scorer = BinScorer(identity)
    per = {key: [] for key in ("energy", "x", "y", "near_shower_energy", "near_shower_x", "near_shower_y")}
    edge_by_t = {t: [] for t in (0.5, 1.0, 1.5, 2.0)}
    showers, not_fired, primaries_ok, merged, splits = [], [], [], [], 0
    defects = {"conservation": [], "double-count": [], "dead cell in a cluster": [], "saturation flag": []}
    for i, event in enumerate(events):
        if event["event"] != i:
            raise ScoringError(f"product event {i} carries index {event['event']}: the ranges were not merged in order")
        n_sh = int(truth["n_showers"][i])
        deposit = truth["deposit"][i]
        match = readings.match_event(event, deposit, n_sh)
        fired = seed_fired(event, deposit, n_sh)
        showers.append(n_sh)
        not_fired.append(n_sh - sum(fired))
        primaries_ok.append(sum(p is not None for p in match["primary"]))
        splits += sum(len(m) > 1 for m in match["matched"])
        merged.append(int(bool(match["merged"])))
        found = readings.event_pulls(event, kind.fixture, kind.separation if kind.fixture == "main" else None, i, truth, reference, match)
        for key in per:
            per[key].append(found.get(key, []))
        for t in edge_by_t:
            edge_by_t[t].append(found.get(("edge", t), []))
        defects["conservation"] += conservation_defects(event)
        defects["double-count"] += [f"event {i}: {d}" for d in readings_product().double_count_defects(event)]
        defects["dead cell in a cluster"] += dead_cell_defects(event)
        if kind.fixture == "saturation":
            defects["saturation flag"] += saturation_defects(event, None if saturated is None else saturated[i])
    gated = kind.energy_bin in GATED_ENERGY_BINS
    reason = "" if gated else E1_REASON
    records = []
    lines = []
    if kind.fixture == "main" and kind.separation in ("iso", "far"):
        for gate, key in zip(PULLS, ("energy", "x", "y")):
            records += scorer.pulls(gate, per[key], required=gated, reason=reason)
        reference_r = REFERENCE_EFFICIENCY[kind.energy_bin]
        records.append(scorer.efficiency("efficiency", showers, not_fired, efficiency_lower_limit(reference_r)))
        lines.append(f"READING {scorer.label} efficiency (U-K5): seed fired {sum(showers) - sum(not_fired)} of {sum(showers)} showers against R "
                     f"{reference_r} (lower limit {efficiency_lower_limit(reference_r):.4f}); matched primary with ok uncertainty "
                     f"{sum(primaries_ok)} of {sum(showers)} ({sum(primaries_ok) / max(sum(showers), 1):.5f}), a reading")
        if kind.separation == "far":
            if gated:
                records.append(scorer.rate("merge", [1] * len(events), merged, MERGE_LIMIT))
            else:
                lines.append(f"READING {scorer.label} merge (E1, reported, not gated, v4 9.1): {sum(merged)} of {len(events)} events")
    elif kind.fixture == "main":
        records += scorer.pulls(NEAR_PULLS[0], per["energy"], required=gated, reason=reason)
        for key, what in (("near_shower_energy", "energy, target E"), ("near_shower_x", "x"), ("near_shower_y", "y")):
            lines.append(f"READING {scorer.label} near per-shower {what} pulls of primaries, reported, no closure meaning (v4 9.1): "
                         f"{readings.summary([v for e in per[key] for v in e])}")
        lines.append(f"READING {scorer.label} near efficiency: no reference exists (v4 4.2), reported only: seed fired "
                     f"{sum(showers) - sum(not_fired)} of {sum(showers)}; matched primary with ok uncertainty {sum(primaries_ok)}")
    elif kind.fixture == "edge":
        pooled = [a + b + c + d for a, b, c, d in zip(*(edge_by_t[t] for t in (0.5, 1.0, 1.5, 2.0)))]
        records += scorer.pulls(EDGE_PULLS[0], pooled)
        for t in edge_by_t:
            lines.append(f"READING {scorer.label} edge energy pulls at t {t} (a reading beside the pooled test): "
                         f"{readings.summary([v for e in edge_by_t[t] for v in e])}")
    elif kind.fixture == "dead":
        records += scorer.pulls(DEAD_PULLS[0], per["energy"])
    else:
        lines.append(f"READING {scorer.label} saturated energy, reported, ungated by choice (v4 9.2, 16): "
                     f"{readings.summary([v for e in per['energy'] for v in e])}")
    if kind.fixture != "main":
        for axis in ("x", "y"):
            lines.append(f"READING {scorer.label} position {axis} pulls of the largest object, reported, not gated (v4 9.2): "
                         f"{readings.summary([v for e in per[axis] for v in e])}")
    lines.append(f"READING {scorer.label} split (reported, v4 9.2): {splits} showers with more than one matched cluster")
    want = [(g, s) for g, s, _, _ in gates_of_bin(kind)]
    have = [(r.gate, r.statistic) for r in records]
    if have != want:
        raise ScoringError(f"{identity.label}: the records {have} are not the bin's tests {want}")
    return SampleScore(kind, records, defects, lines)


def readings_product():
    from calo_recipe import product
    return product


# ---- the negative cases (v4 9.2) and the checks

def negative_digital_as_analog(cells_content: bytes) -> tuple:
    """A digital-typed copy of a sample's own cells (the fixture has no digital readout, so the test builds its own): the recipe's reader must
    refuse it by type. (passed, detail)."""
    from calo_recipe import cell_input
    cells = cell_input.read_cells(cells_content)
    digital = cell_input.cells_bytes(cells.raw[:1], cells.live[:1], cells.saturated[:1], readout="digital")
    try:
        cell_input.read_cells(digital)
    except cell_input.InputError as error:
        return "digital" in str(error) and "refused" in str(error), f"typed refusal: {error}"
    return False, "a digital-typed input was read as analog"


def negative_deposited_as_incident(product_text: str) -> tuple:
    """The product's header with energy kind incident-energy: the recipe's product reader must refuse it (the named-energy check)."""
    from calo_recipe import product
    head, _, rest = product_text.partition("\n")
    import json
    header = json.loads(head)
    header["energy_kind"] = "incident-energy"
    try:
        product.read_text(product.dumps(header) + "\n" + rest)
    except product.ProductError as error:
        return "energy_kind" in str(error), f"named-energy refusal: {error}"
    return False, "a product naming incident energy was read"


def sample_checks(score: SampleScore) -> list:
    """The deterministic checks of one sample, as core.CheckResult: a defect fails the check; double counting is the sheet's stop."""
    out = []
    for name, defects in score.defects.items():
        if name == "saturation flag" and score.kind.fixture != "saturation":
            continue
        if name == "dead cell in a cluster" and score.kind.fixture != "dead" and not defects:
            continue
        out.append(core.CheckResult(f"{name} {score.kind.name}", "deterministic", "fail" if defects else "pass", stop=(name == "double-count" and bool(defects))))
    return out


def negative_checks(cells_content: bytes, product_text: str) -> list:
    digital, _ = negative_digital_as_analog(cells_content)
    incident, _ = negative_deposited_as_incident(product_text)
    return [core.CheckResult(NEGATIVE_NAMES[0], "negative", "pass" if digital else "fail"),
            core.CheckResult(NEGATIVE_NAMES[1], "negative", "pass" if incident else "fail")]


NEGATIVE_NAMES = ("digital read as analog", "deposited energy used as incident")
# The checks rerun at evaluation by the T08 checks task (the user, 2026-11-12: "Rerun at evaluation", at the frozen hash, on their own v4 3.2
# block 1): CAI-T08-1 (fixed membership, both gain roles, main E3 iso, far and near) and its planted-fraction control, CAI-T08-2 (full
# re-reconstruction, recorded), and the reference selection (A38.1: the reference clusterer's constants are the configuration's).
CHECK_TASK_NAMES = ("CAI-T08-1", "CAI-T08-2", "reference selection (A38.1)")


def required_checks(missing=()) -> tuple:
    """Every check a T08 outcome needs (v4 9.1, 9.2, 10, 11; fix round 1, review I2): per sample conservation, double count and A38's
    accounting; the dead control's dead-cell check and the saturation control's flag; the two negative cases (made from bin 0's sample); the
    checks task's three. missing: labels of bins the collection marked missing (recipe side), whose own checks cannot exist."""
    names = []
    missing = set(missing)
    for kind in ALL_BINS:
        if kind.name in missing:
            continue
        names += [f"conservation {kind.name}", f"double-count {kind.name}", f"A38 selection and accounting {kind.name}"]
        if kind.fixture == "dead":
            names.append(f"dead cell in a cluster {kind.name}")
        if kind.fixture == "saturation":
            names.append(f"saturation flag {kind.name}")
    return tuple(names) + (() if ALL_BINS[0].name in missing else NEGATIVE_NAMES) + CHECK_TASK_NAMES


def missing_records(identity: core.BinIdentity, why: str) -> list:
    """Section 10's "required output missing" records of every test of an incomplete bin (E1 pulls kept ungated)."""
    kind = bin_kind(identity.fixture_id, identity.stratum)
    scorer = BinScorer(identity)
    return [scorer.missing(gate, statistic, why, required=required, reason=reason) for gate, statistic, required, reason in gates_of_bin(kind)]


def merged_events(products) -> tuple:
    """The events of one bin from its range products (calo_recipe.product.Product), in order of their first event, renumbered from 0; and the
    first header. Every product must have the same configuration and payload chain."""
    products = list(products)
    if not products:
        raise ScoringError("no product")
    header = products[0].header
    events = []
    for p in products:
        if p.header["configuration"] != header["configuration"] or p.header["chain"] != header["chain"]:
            raise ScoringError("the range products differ in configuration or chain")
        for doc in p.events:
            events.append(dict(doc, event=len(events)))
    return events, header
