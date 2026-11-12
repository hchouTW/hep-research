"""The product light-likelihood-product/1: JSON Lines with sorted keys and shortest round-trip floats (so a round trip is
byte-equal): one header line, one line per event in input order, one end line. Every result is labelled shared-model closure.

Per event it keeps the readout states of every channel (one letter each: H live-hit, U live-unhit, D dead, X disabled), every
hit channel's charge and saturated flag, the counts, the seed, the fit (status, failure, vertex, direction, E_vis, t0
not-estimated, section 7's frame at the fitted direction, the covariance of (x, y, z, u1, u2, E_vis), its status, ln L, the
gradient norm, the Newton decrement, iterations and chart rounds) and the per-channel probability check at the reported point. Times are not kept
(the charge-only likelihood does not use them); they are reproducible from the input named by its SHA-256.

The reader refuses a malformed or incomplete product: unknown or missing keys, NaN, a states string of the wrong length or
letter, hit rows that do not match the H states, counts that are not the states', a saturated row in a readout without a
saturation value or not at it, a direction that is not a unit vector, a frame that is not section 7's at the fitted direction, a
covariance that is not symmetric and positive definite where its status is ok, t0 given a value, a missing or wrong end line,
text after it, and events out of order. Given the model and configuration, it also recomputes ln L at the fitted point (to 1e-9
relative) and the probability check (failures exact, largest deviation to 1e-14) from the product alone.

light-likelihood-product/2 (D3 stage 2) is the joint charge-time product: the same lines, with the likelihood text of the joint
likelihood, seven parameters (t0 appended, in ns), a 7 x 7 covariance, t0 a number wherever the fit has a point, every hit row
[channel, charge, saturated, time] (the first-arrival time is kept: the joint ln L needs it), the joint seed {vertex, direction,
e_vis, t0, from} and the charge-only prefit {status, failure, iterations, point, ln_likelihood} per event, the seed's from
agreeing with the prefit. Its reader recomputes the
joint ln L. /1 is unchanged.

light-likelihood-product/3 (D3 stage 3) is the multistart joint product: /2's lines, the header's budget {format, sha256,
starts, tie_tolerance} (the multistart budget file, K10), and per event the record of every start (name, start point, status,
failure, ln L, end point, iterations, rounds) and the choice {chosen, rule}; fit is the chosen start's fit, or for all starts
failed the kind all-starts-failed with start 0's last point (multistart.py). Its reader checks the start names against the
budget, start 0 against the seed, the choice against the rule recomputed from the recorded outcomes, and the reported fit
against the chosen start; given the model it recomputes every start point from the anchor and the data, and every start's
ln L at its end point. /1 and /2 are unchanged.

light-likelihood-product/4 (D3 stage 4) is the topology product: /3's header (format /4, a hypothesis text naming H1 and H2)
with the topology budget {format, sha256, starts, tie_tolerance}, the frozen penalty 30 and the rules, and the SHA-256 and
product id of the /3 it was made from; each event line is the /3 event line unchanged plus `topology`: H2's starts (name, start
point, status, failure, ln L, end point, iterations, rounds), its reported point and rule, its fit (both sources, each its own t0, the 14 x 14
covariance where it converged), lnL_1, lnL_2 and where it comes from, the statistic 2 (lnL_2 - lnL_1), the penalty, the choice
and the per-channel check at H2's point (topology.py). Its reader checks every /3 rule, then the topology record: the starts
against the topology budget and H1's fit, the reported point against the rule, the H2 fit against the reported start, the
statistic, lnL_2 and the choice recomputed from the recorded values, the penalty; given the model it recomputes every H2 start
point from H1's fit and the data, every H2 start's ln L at its end point, and the check at H2's point. /1 to /3 are unchanged.

light-likelihood-product/3-single-photon (D4 E1b) is the product of t04-values-v4.md section 9.4's single-photon-density variant
(single_photon.py): /3's lines exactly, but for its format, its likelihood text (single_photon.LIKELIHOOD) and its configuration, which
must be the variant's format (light-likelihood-configuration/1-single-photon). Every format names the configuration format it is made
with, and the reader refuses a header whose configuration is another format's, so a variant product never reads as a main one and the
reverse. Its writer path is /3's (header_document picks the variant from the configuration's format, and only with a multistart
budget and the charge-time likelihood); /1 to /4 are unchanged.

Any structural exception while the reader checks a field (KeyError, TypeError, IndexError, AttributeError, ValueError,
OverflowError) is a ProductError: a malformed field is refused (status rejected), never an internal error (re-review N5). The
recomputation keeps its own rule (a ValueError there is a ProductError; anything else is a defect of the recipe).
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy

from . import LABEL, LABEL_MEANING, LIKELIHOOD, LIKELIHOOD_JOINT, PARAMETERS, PARAMETERS_JOINT, PARAMETER_UNITS, RECIPE, joint, multistart, readout, topology
from . import configuration, single_photon
from .fit import CALLBACK_STOP, FAILURES, JOINT_CHART_RADIUS, JOINT_ORIGINS, SETTINGS, FitResult, JointSeed, Seed
from .likelihood import (EPSILON, HESSIAN_STEPS, TOLERANCE_FACTOR, TOLERANCE_RULE, EventData, frame, log_likelihood,
                         probability_check)

FORMAT = "light-likelihood-product/1"
LETTERS = {readout.LIVE_HIT: "H", readout.LIVE_UNHIT: "U", readout.DEAD: "D", readout.DISABLED: "X"}
CODES = {v: k for k, v in LETTERS.items()}
HEADER_KEYS = {"format", "recipe", "product_id", "label", "label_meaning", "likelihood", "hypothesis", "input", "configuration",
               "parameters", "frame", "uncertainty", "not_estimated", "fit_settings", "hessian_steps", "probability_check",
               "channel_states", "retention", "events"}
INPUT_KEYS = {"format", "role", "sha256", "events", "channels", "threshold", "saturation_charge"}
EVENT_KEYS = {"event", "states", "hits", "counts", "seed", "fit", "probability_check"}
COUNT_KEYS = {"live", "hit", "unhit", "dead", "disabled", "saturated"}
FIT_KEYS = {"status", "failure", "vertex", "direction", "e_vis", "t0", "frame", "covariance", "uncertainty_status",
            "ln_likelihood", "gradient_norm", "newton_decrement", "iterations", "rounds"}
CHECK_KEYS = {"point", "channels", "failures", "max_abs_deviation", "largest_ratio", "failed_channels"}
CHECK_HEADER = {"tolerance": TOLERANCE_RULE, "epsilon": EPSILON, "factor": TOLERANCE_FACTOR}
NOT_ESTIMATED = {"t0": "not estimated: the charge-only likelihood of stage 1 has no time dependence; the time term comes in a "
                       "later stage"}
HYPOTHESIS = "H1: one point source (the topology hypotheses come in a later stage)"
FRAME_TEXT = ("u1, u2: tangent components at the fitted direction d in section 7's frame, e1 = a x d normalised (a the z axis, or "
              "the x axis where |d_z| > 0.9), e2 = d x e1; the scoring side projects onto the frame at the truth direction")
UNCERTAINTY_TEXT = ("inverse of the observed Hessian of -ln L at the fit, in (x, y, z, u1, u2, e_vis); conditional on the fixed light "
                    "model and its constants; validated by no pull here")
CHECK_RULE = ("per live channel at the reported point: |P(hit) + P(no hit) - 1| <= its tolerance (largest_ratio: the largest "
              "deviation over tolerance), P(hit) from the upper tails at the "
              "threshold and P(no hit) from the likelihood's no-hit term; a failure is the T09 sheet's stop")
RETENTION = {"states": "every channel of every event", "charges": "every hit channel's charge and saturated flag",
             "times": "not kept: unused by the charge-only likelihood; reproducible from the input named by its SHA-256",
             "truth": "none"}
FORMAT_JOINT = "light-likelihood-product/2"
NOT_ESTIMATED_JOINT: dict = {}
HYPOTHESIS_JOINT = HYPOTHESIS
UNCERTAINTY_JOINT = ("inverse of the observed Hessian of -ln L at the fit, in (x, y, z, u1, u2, e_vis, t0); conditional on the fixed "
                     "light model and its constants; validated by no pull here")
SETTINGS_JOINT = {**SETTINGS, "t0_domain_windows": list(joint.T0_DOMAIN_WINDOWS),
                  "t0_domain_rule": "t0 in (lo W, hi W), W the configuration's window_ns (200 ns for t09-sphere/1)",
                  "joint_chart_radius": JOINT_CHART_RADIUS, "callback_stop_status": CALLBACK_STOP,
                  "callback_stop_rule": ("a joint round ends once |(a, b)| exceeds joint_chart_radius; SciPy returns callback_stop_status "
                                         "there; the next round re-centres the chart: never convergence, never a failure by itself"),
                  "t0_seed": "median over hit channels of t_i - |P_i - x_start| / v",
                  "prefit": "the charge-only fit of light-likelihood-product/1 from its seed; its point starts the joint fit",
                  "time_domain_ns": joint.TIME_DOMAIN}
RETENTION_JOINT = {"states": "every channel of every event",
                   "charges": "every hit channel's charge, saturated flag and first-arrival time",
                   "times": "every hit channel's first-arrival time (unhit, dead and disabled channels have none)", "truth": "none"}
FORMAT_MULTISTART = "light-likelihood-product/3"
SETTINGS_MULTISTART = {**SETTINGS_JOINT, "seeds": "multistart: the budget's starts, in its order (header budget)",
                       "start_rules": multistart.RULES, "start_values_rule": multistart.VALUES_RULE,
                       "choice_rule": multistart.CHOICE_TEXT}
BUDGET_KEYS = {"format", "sha256", "starts", "tie_tolerance"}
START_KEYS = {"name", "start", "status", "failure", "ln_likelihood", "end", "iterations", "rounds"}
POINT_KEYS = {"vertex", "direction", "e_vis", "t0"}
START_TOLERANCE = 1e-12        # a start point recomputed from the anchor and the data, relative
STRUCTURAL = (KeyError, TypeError, IndexError, AttributeError, ValueError, OverflowError, RecursionError)
LN_L_TOLERANCE = 1e-9
DEVIATION_TOLERANCE = 1e-14
RATIO_TOLERANCE = 1e-3          # the ratio's recomputation, relative: its numerator is a rounding residue
FORMAT_TOPOLOGY = "light-likelihood-product/4"
HYPOTHESIS_TOPOLOGY = ("H1: one point source (the multistart fit); H2: two point sources, each with its own t0; the choice of "
                       "t04-values-v4.md section 7 (the topology record)")
TOPOLOGY_HEADER_KEYS = {"format", "sha256", "starts", "tie_tolerance", "penalty", "rule", "start_rules", "report_rule", "fit"}
TOPOLOGY_KEYS = {"h2", "ln_likelihood_1", "ln_likelihood_2", "ln_likelihood_2_from", "statistic", "penalty", "choice", "rule",
                 "probability_check"}
H2_KEYS = {"starts", "reported", "fit"}
H2_START_KEYS = {"name", "start", "status", "failure", "ln_likelihood", "end", "iterations", "rounds"}
H2_FIT_KEYS = {"status", "failure", "sources", "covariance", "uncertainty_status", "ln_likelihood", "gradient_norm",
               "newton_decrement", "iterations", "rounds"}
FORMAT_SINGLE_PHOTON = "light-likelihood-product/3-single-photon"


class ProductError(ValueError):
    """The product is refused: the reason names the line and the defect."""


@dataclass(frozen=True)
class Variant:
    """What tells the two products apart."""
    format: str
    likelihood: str
    parameters: tuple
    not_estimated: dict
    uncertainty: str
    settings: dict
    retention: dict
    timed: bool
    multistart: bool = False
    failures: tuple = FAILURES
    hypothesis: str = HYPOTHESIS
    topology: bool = False
    configuration_format: str = configuration.FORMAT

    @property
    def header_keys(self) -> set:
        keys = HEADER_KEYS | {"budget"} if self.multistart else HEADER_KEYS
        return keys | {"topology", "h1_product"} if self.topology else keys

    @property
    def size(self) -> int:
        return len(self.parameters)

    def fixed_header(self) -> dict:
        return {"format": self.format, "recipe": RECIPE, "label": LABEL, "label_meaning": LABEL_MEANING, "likelihood": self.likelihood,
                "hypothesis": self.hypothesis, "frame": FRAME_TEXT, "uncertainty": self.uncertainty, "not_estimated": self.not_estimated,
                "fit_settings": self.settings, "hessian_steps": HESSIAN_STEPS, "retention": self.retention,
                "probability_check": {**CHECK_HEADER, "rule": CHECK_RULE},
                "parameters": [{"name": n, "unit": PARAMETER_UNITS[n]} for n in self.parameters],
                "channel_states": {LETTERS[k]: readout.STATE_NAMES[k] for k in sorted(LETTERS)}}


@dataclass(frozen=True)
class Product:
    header: dict
    events: list


def dumps(doc) -> str:
    return json.dumps(doc, sort_keys=True, allow_nan=False)


def _vec(v):
    return None if v is None else [float(c) for c in v]


def header_document(product_id: str, rd, cfg, likelihood: str = "charge-only", budget=None) -> dict:
    """The header line; likelihood charge-only (light-likelihood-product/1, stage 1's) or charge-time (/2); charge-time with a
    multistart budget gives /3, whose header records the budget."""
    if budget is not None and likelihood != "charge-time":
        raise ValueError("multistart needs the charge-time likelihood")
    variant = MULTISTART if budget is not None else BY_LIKELIHOOD[likelihood]
    if cfg.format == single_photon.FORMAT:
        if variant is not MULTISTART:
            raise ValueError("the single-photon variant is written by the multistart charge-time fit only")
        variant = SINGLE_PHOTON
    extra = {} if budget is None else {"budget": budget.header()}
    return {**copy.deepcopy(variant.fixed_header()), **extra, "product_id": product_id,
            "input": {"format": rd.header["format"], "role": rd.header["role"], "sha256": rd.sha256, "events": rd.events,
                      "channels": rd.channels, "threshold": rd.header["threshold"], "saturation_charge": rd.header["saturation_charge"]},
            "configuration": {"format": cfg.format, "sha256": cfg.sha256}, "events": rd.events}


def check_at(model, event: EventData, start: Seed | None, res: FitResult) -> dict:
    """The probability check at the reported point: the fit, the last point of a failed fit, or the dark-only mean."""
    if res.vertex is not None:
        point = "fit" if res.status == "converged" else "fit-last"
        check = probability_check(model, event, res.vertex, res.direction, res.e_vis)
    else:
        point = "dark-only"
        check = probability_check(model, event)
    return {"point": point, **check}


def event_document(index: int, event: EventData, start: Seed | None, res: FitResult, check: dict) -> dict:
    hits = [[int(c), float(event.charge[c]), int(event.saturated[c])] for c in numpy.flatnonzero(event.hit)]
    return {"event": index, "states": "".join(LETTERS[int(s)] for s in event.state), "hits": hits,
            "counts": _counts(event.state, event.saturated),
            "seed": None if start is None else {"vertex": _vec(start.vertex), "direction": _vec(start.direction),
                                                "e_vis": float(start.e_vis)},
            "fit": _fit_document(res, "not-estimated"), "probability_check": check}


def joint_event_document(index: int, tev, start: JointSeed | None, origin: str | None, prefit: FitResult | None, res: FitResult,
                         check: dict) -> dict:
    """An event line of light-likelihood-product/2."""
    event = tev.event
    hits = [[int(c), float(event.charge[c]), int(event.saturated[c]), float(tev.time[c])] for c in numpy.flatnonzero(event.hit)]
    return {"event": index, "states": "".join(LETTERS[int(s)] for s in event.state), "hits": hits,
            "counts": _counts(event.state, event.saturated),
            "seed": None if start is None else {"vertex": _vec(start.vertex), "direction": _vec(start.direction),
                                                "e_vis": float(start.e_vis), "t0": float(start.t0), "from": origin},
            "prefit": None if prefit is None else {"status": prefit.status, "failure": prefit.failure, "iterations": int(prefit.iterations),
                                                   "point": prefit.vertex is not None,
                                                   "ln_likelihood": None if prefit.ln_likelihood is None else float(prefit.ln_likelihood)},
            "fit": _fit_document(res, None if res.t0 is None else float(res.t0)), "probability_check": check}


def _point_document(vertex, direction, e_vis, t0) -> dict:
    return {"vertex": _vec(vertex), "direction": _vec(direction), "e_vis": float(e_vis), "t0": float(t0)}


def multistart_event_document(index: int, tev, ms, check: dict) -> dict:
    """An event line of light-likelihood-product/3: /2's line of the reported fit, every start's record and the choice."""
    doc = joint_event_document(index, tev, ms.anchor, ms.origin, ms.prefit, ms.result, check)
    starts = []
    for rec in ms.starts:
        res = rec.result
        starts.append({"name": rec.name, "start": _point_document(rec.start.vertex, rec.start.direction, rec.start.e_vis, rec.start.t0),
                       "status": res.status, "failure": res.failure,
                       "ln_likelihood": None if res.ln_likelihood is None else float(res.ln_likelihood),
                       "end": None if res.vertex is None else _point_document(res.vertex, res.direction, res.e_vis, res.t0),
                       "iterations": int(res.iterations), "rounds": int(res.rounds)})
    return {**doc, "starts": starts, "choice": {"chosen": ms.chosen, "rule": ms.choice}}


def topology_header_document(h1_header: dict, h1_sha256: str, product_id: str, topology_budget) -> dict:
    """The header of light-likelihood-product/4: the /3 header it was made from, with format /4, the hypothesis text, the
    topology budget, the penalty and the rules, and the /3's SHA-256 and product id."""
    if h1_header.get("format") != FORMAT_MULTISTART:
        raise ValueError("the topology product is made from a light-likelihood-product/3")
    return {**copy.deepcopy(h1_header), "format": FORMAT_TOPOLOGY, "hypothesis": HYPOTHESIS_TOPOLOGY, "product_id": product_id,
            "topology": {**topology_budget.header(), "penalty": topology.PENALTY, "rule": topology.CHOICE_RULE,
                         "start_rules": {name: topology.RULES[name] for name in topology_budget.starts},
                         "report_rule": topology.REPORT_TEXT, "fit": topology.FIT_TEXT},
            "h1_product": {"sha256": h1_sha256, "product_id": h1_header["product_id"]}}


def fit_result_of(fit_doc: dict) -> FitResult:
    """H1's FitResult from a /3 event line's fit, as the topology step reads it."""
    arr = (lambda v: None if v is None else numpy.array(v, float))  # noqa: E731
    frm = fit_doc["frame"]
    return FitResult(fit_doc["status"], fit_doc["failure"], arr(fit_doc["vertex"]), arr(fit_doc["direction"]), fit_doc["e_vis"],
                     arr(fit_doc["covariance"]), fit_doc["uncertainty_status"], fit_doc["ln_likelihood"], fit_doc["gradient_norm"],
                     fit_doc["newton_decrement"], fit_doc["iterations"], fit_doc["rounds"], None if frm is None else arr(frm["e1"]),
                     None if frm is None else arr(frm["e2"]), fit_doc["t0"])


def _two_point_document(point) -> dict:
    return {"sources": [{"vertex": _vec(point.vertices[j]), "direction": _vec(point.directions[j]), "e_vis": float(point.e_vis[j]),
                         "t0": float(point.t0[j])} for j in range(2)]}


def _two_fit_document(res) -> dict:
    sources = None
    if res.point is not None:
        sources = []
        for j in range(2):
            e1, e2 = frame(res.point.directions[j])
            sources.append({"vertex": _vec(res.point.vertices[j]), "direction": _vec(res.point.directions[j]),
                            "e_vis": float(res.point.e_vis[j]), "t0": float(res.point.t0[j]), "frame": {"e1": _vec(e1), "e2": _vec(e2)}})
    return {"status": res.status, "failure": res.failure, "sources": sources,
            "covariance": None if res.covariance is None else [[float(x) for x in row] for row in res.covariance],
            "uncertainty_status": res.uncertainty_status,
            "ln_likelihood": None if res.ln_likelihood is None else float(res.ln_likelihood),
            "gradient_norm": None if res.gradient_norm is None else float(res.gradient_norm),
            "newton_decrement": None if res.newton_decrement is None else float(res.newton_decrement),
            "iterations": int(res.iterations), "rounds": int(res.rounds)}


def topology_document(topo, check) -> dict:
    """The `topology` record of an event line of /4."""
    if topo.choice is None:
        return {"h2": None, "ln_likelihood_1": None, "ln_likelihood_2": None, "ln_likelihood_2_from": None, "statistic": None,
                "penalty": topology.PENALTY, "choice": None, "rule": topo.rule, "probability_check": None}
    starts = []
    for rec in topo.records:
        res = rec.result
        starts.append({"name": rec.name, "start": None if rec.start is None else _two_point_document(rec.start), "status": res.status,
                       "failure": res.failure, "ln_likelihood": None if res.ln_likelihood is None else float(res.ln_likelihood),
                       "end": None if res.point is None else _two_point_document(res.point), "iterations": int(res.iterations),
                       "rounds": int(res.rounds)})
    return {"h2": {"starts": starts, "reported": {"index": topo.reported, "rule": topo.report_rule},
                   "fit": None if topo.result is None else _two_fit_document(topo.result)},
            "ln_likelihood_1": float(topo.ln_likelihood_1), "ln_likelihood_2": float(topo.ln_likelihood_2),
            "ln_likelihood_2_from": topo.ln_likelihood_2_from, "statistic": float(topo.statistic), "penalty": topology.PENALTY,
            "choice": topo.choice, "rule": topo.rule, "probability_check": check}


def topology_event_document(h1_doc: dict, topo, check) -> dict:
    """An event line of /4: the /3 event line unchanged, plus the topology record."""
    return {**copy.deepcopy(h1_doc), "topology": topology_document(topo, check)}


def _fit_document(res: FitResult, t0) -> dict:
    return {"status": res.status, "failure": res.failure, "vertex": _vec(res.vertex), "direction": _vec(res.direction),
               "e_vis": None if res.e_vis is None else float(res.e_vis), "t0": t0,
               "frame": None if res.e1 is None else {"e1": _vec(res.e1), "e2": _vec(res.e2)},
               "covariance": None if res.covariance is None else [[float(x) for x in row] for row in res.covariance],
               "uncertainty_status": res.uncertainty_status,
               "ln_likelihood": None if res.ln_likelihood is None else float(res.ln_likelihood),
               "gradient_norm": None if res.gradient_norm is None else float(res.gradient_norm),
               "newton_decrement": None if res.newton_decrement is None else float(res.newton_decrement),
               "iterations": int(res.iterations), "rounds": int(res.rounds)}


def _counts(state, saturated) -> dict:
    state = numpy.asarray(state)
    return {"live": int(((state == readout.LIVE_HIT) | (state == readout.LIVE_UNHIT)).sum()),
            "hit": int((state == readout.LIVE_HIT).sum()), "unhit": int((state == readout.LIVE_UNHIT).sum()),
            "dead": int((state == readout.DEAD).sum()), "disabled": int((state == readout.DISABLED).sum()),
            "saturated": int(numpy.asarray(saturated).sum())}


class Writer:
    def __init__(self, stream, header: dict):
        self.stream = stream
        self.count = 0
        self.format = header["format"]
        stream.write(dumps(header) + "\n")

    def event(self, doc: dict) -> None:
        self.stream.write(dumps(doc) + "\n")
        self.count += 1

    def finish(self) -> None:
        self.stream.write(dumps({"end": self.format, "events": self.count}) + "\n")


# --- the reader ---------------------------------------------------------------------------------------------------------

def _refuse_constant(name):
    raise ValueError(f"non-finite number {name}")


def _number(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _count(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _vector(value, where):
    if not (isinstance(value, list) and len(value) == 3 and all(_number(c) for c in value)):
        raise ProductError(f"{where}: not a vector of 3 finite numbers")
    return numpy.array(value, float)


def _unit(value, where):
    v = _vector(value, where)
    if abs(numpy.linalg.norm(v) - 1.0) > 1e-12:
        raise ProductError(f"{where}: not a unit vector")
    return v


def _check_header(header: dict, cfg, budget=None, topology_budget=None) -> Variant:
    if not isinstance(header, dict) or "format" not in header:
        raise ProductError(f"header keys must be exactly {sorted(HEADER_KEYS)}")
    variant = VARIANTS.get(header["format"]) if isinstance(header["format"], str) else None
    if variant is None:
        raise ProductError(f"header format must be one of {sorted(VARIANTS)}")
    if set(header) != variant.header_keys:
        raise ProductError(f"header keys must be exactly {sorted(variant.header_keys)}")
    for key, value in variant.fixed_header().items():
        if header[key] != value:
            raise ProductError(f"header {key} is not this recipe's ({value!r})")
    if not isinstance(header["product_id"], str) or not header["product_id"]:
        raise ProductError("header product_id must be a non-empty string")
    source = header["input"]
    if not isinstance(source, dict) or set(source) != INPUT_KEYS or source["format"] != readout.FORMAT or source["role"] != readout.ROLE:
        raise ProductError(f"header input must have exactly {sorted(INPUT_KEYS)}, format {readout.FORMAT}, role {readout.ROLE}")
    if not (_count(source["events"]) and _count(source["channels"]) and source["channels"] > 0 and _number(source["threshold"])):
        raise ProductError("header input events, channels or threshold malformed")
    if source["saturation_charge"] is not None and not _number(source["saturation_charge"]):
        raise ProductError("header input saturation_charge must be null or a number")
    if not _count(header["events"]) or header["events"] != source["events"]:
        raise ProductError("header events must equal the input's events")
    conf = header["configuration"]
    if not isinstance(conf, dict) or set(conf) != {"format", "sha256"}:
        raise ProductError("header configuration must have exactly format and sha256")
    if conf["format"] != variant.configuration_format:
        raise ProductError(f"header configuration format must be {variant.configuration_format} in a {variant.format} product")
    if cfg is not None and (conf["format"] != cfg.format or conf["sha256"] != cfg.sha256):
        raise ProductError("the product was made with another configuration than the one given")
    if variant.multistart:
        _check_budget_header(header["budget"], budget)
    if variant.topology:
        _check_topology_header(header["topology"], header["h1_product"], topology_budget)
    return variant


def _check_topology_header(doc, h1_product, topology_budget) -> None:
    if not isinstance(doc, dict) or set(doc) != TOPOLOGY_HEADER_KEYS or doc["format"] != topology.FORMAT:
        raise ProductError(f"header topology must have exactly {sorted(TOPOLOGY_HEADER_KEYS)}, format {topology.FORMAT}")
    starts, tie = doc["starts"], doc["tie_tolerance"]
    if not (isinstance(starts, list) and starts and all(isinstance(s, str) and s in topology.RULES for s in starts)
            and len(set(starts)) == len(starts)):
        raise ProductError("header topology starts must be distinct known start names")
    if not (_number(tie) and tie > 0) or not isinstance(doc["sha256"], str) or len(doc["sha256"]) != 64:
        raise ProductError("header topology tie_tolerance or sha256 malformed")
    want = {"penalty": topology.PENALTY, "rule": topology.CHOICE_RULE, "start_rules": {n: topology.RULES[n] for n in starts},
            "report_rule": topology.REPORT_TEXT, "fit": topology.FIT_TEXT}
    for key, value in want.items():
        if doc[key] != value or (key == "penalty" and isinstance(doc[key], bool)):
            raise ProductError(f"header topology {key} is not this recipe's ({value!r}; the penalty is t04-values-v4.md section 7's)")
    if topology_budget is not None and {k: doc[k] for k in ("format", "sha256", "starts", "tie_tolerance")} != topology_budget.header():
        raise ProductError("the product was made with another topology budget than the one given")
    if not (isinstance(h1_product, dict) and set(h1_product) == {"sha256", "product_id"} and isinstance(h1_product["sha256"], str)
            and len(h1_product["sha256"]) == 64 and isinstance(h1_product["product_id"], str) and h1_product["product_id"]):
        raise ProductError("header h1_product must have exactly sha256 (64 hex digits) and a non-empty product_id")


def _check_budget_header(doc, budget) -> None:
    if not isinstance(doc, dict) or set(doc) != BUDGET_KEYS or doc["format"] != multistart.FORMAT:
        raise ProductError(f"header budget must have exactly {sorted(BUDGET_KEYS)}, format {multistart.FORMAT}")
    starts, tie = doc["starts"], doc["tie_tolerance"]
    if not (isinstance(starts, list) and starts and all(isinstance(s, str) and s in multistart.RULES for s in starts)
            and len(set(starts)) == len(starts) and starts[0] == multistart.FIRST):
        raise ProductError("header budget starts must be distinct known start names, the first prefit")
    if not (_number(tie) and tie > 0) or not isinstance(doc["sha256"], str) or len(doc["sha256"]) != 64:
        raise ProductError("header budget tie_tolerance or sha256 malformed")
    if budget is not None and doc != budget.header():
        raise ProductError("the product was made with another multistart budget than the one given")


def _event_arrays(doc: dict, source: dict, where: str, variant: Variant):
    """The event's EventData (and for /2 its TimedEvent) from its states and hit rows."""
    states, hits = doc["states"], doc["hits"]
    channels = source["channels"]
    if not isinstance(states, str) or len(states) != channels or not set(states) <= set(CODES):
        raise ProductError(f"{where}: states must be {channels} letters of {sorted(CODES)}")
    state = numpy.array([CODES[c] for c in states], numpy.int8)
    charge = numpy.where(state == readout.LIVE_UNHIT, 0.0, numpy.nan)
    times = numpy.full(channels, numpy.nan)
    saturated = numpy.zeros(channels, bool)
    if not isinstance(hits, list):
        raise ProductError(f"{where}: hits must be a list")
    width = 4 if variant.timed else 3
    previous = -1
    for row in hits:
        if not (isinstance(row, list) and len(row) == width and _count(row[0]) and _number(row[1]) and row[2] in (0, 1)
                and not isinstance(row[2], bool) and (not variant.timed or _number(row[3]))):
            raise ProductError(f"{where}: a hit row must be [channel, charge, saturated 0 or 1{', time' if variant.timed else ''}]")
        if row[0] <= previous or row[0] >= channels:
            raise ProductError(f"{where}: hit rows must be in ascending channel order, inside the channel range")
        previous = row[0]
        charge[row[0]] = row[1]
        saturated[row[0]] = bool(row[2])
        if variant.timed:
            times[row[0]] = row[3]
    rows = [row[0] for row in hits]
    if rows != [int(c) for c in numpy.flatnonzero(state == readout.LIVE_HIT)]:
        raise ProductError(f"{where}: hit rows do not match the hit channels of the states")
    try:
        event = EventData(state, charge, saturated, source["saturation_charge"], source["threshold"])
        tev = joint.TimedEvent(event, times) if variant.timed else None
    except ValueError as exc:
        raise ProductError(f"{where}: {exc}") from None
    if doc["counts"] != _counts(state, saturated):
        raise ProductError(f"{where}: counts are not the states'")
    return event, tev


def _check_fit(fit_doc, event: EventData, source: dict, where: str, variant: Variant) -> None:
    if not isinstance(fit_doc, dict) or set(fit_doc) != FIT_KEYS:
        raise ProductError(f"{where}: fit keys must be exactly {sorted(FIT_KEYS)}")
    has_point = fit_doc["vertex"] is not None
    if not variant.timed and fit_doc["t0"] != "not-estimated":
        raise ProductError(f"{where}: t0 must be not-estimated in a charge-only product")
    if variant.timed and not (_number(fit_doc["t0"]) if has_point else fit_doc["t0"] is None):
        raise ProductError(f"{where}: t0 must be a finite number where the fit has a point, null otherwise")
    status, failure = fit_doc["status"], fit_doc["failure"]
    if status not in ("converged", "failed") or (status == "converged") != (failure is None) or (failure is not None and failure not in variant.failures):
        raise ProductError(f"{where}: status {status!r} and failure {failure!r} do not agree")
    if not (_count(fit_doc["iterations"]) and _count(fit_doc["rounds"])):
        raise ProductError(f"{where}: iterations and rounds must be counts")
    if has_point:
        _vector(fit_doc["vertex"], f"{where}: fit vertex")
        d = _unit(fit_doc["direction"], f"{where}: fit direction")
        if not _number(fit_doc["e_vis"]):
            raise ProductError(f"{where}: fit e_vis must be a finite number")
        frm = fit_doc["frame"]
        if not isinstance(frm, dict) or set(frm) != {"e1", "e2"}:
            raise ProductError(f"{where}: frame must have e1 and e2")
        e1, e2 = frame(d)
        if numpy.abs(_vector(frm["e1"], where) - e1).max() > 1e-12 or numpy.abs(_vector(frm["e2"], where) - e2).max() > 1e-12:
            raise ProductError(f"{where}: frame is not section 7's at the fitted direction")
    elif any(fit_doc[k] is not None for k in ("direction", "e_vis", "frame", "ln_likelihood", "gradient_norm", "newton_decrement")):
        raise ProductError(f"{where}: a fit without a point carries values")
    for key in ("ln_likelihood", "gradient_norm", "newton_decrement"):
        if fit_doc[key] is not None and not _number(fit_doc[key]):
            raise ProductError(f"{where}: {key} must be null or finite")
    cov = fit_doc["covariance"]
    size = variant.size
    if status == "converged":
        if fit_doc["uncertainty_status"] != "ok" or fit_doc["ln_likelihood"] is None or fit_doc["gradient_norm"] is None \
                or fit_doc["newton_decrement"] is None or not fit_doc["newton_decrement"] <= SETTINGS["newton_decrement_tolerance"]:
            raise ProductError(f"{where}: a converged fit needs status ok, ln L, the gradient norm and a Newton decrement within "
                               "the tolerance")
        if not (isinstance(cov, list) and len(cov) == size and all(isinstance(r, list) and len(r) == size and all(_number(x) for x in r) for r in cov)):
            raise ProductError(f"{where}: covariance must be {size} x {size} finite numbers")
        c = numpy.array(cov, float)
        if not numpy.array_equal(c, c.T):
            raise ProductError(f"{where}: covariance is not symmetric")
        try:
            numpy.linalg.cholesky(c)
        except numpy.linalg.LinAlgError:
            raise ProductError(f"{where}: covariance is not positive definite") from None
    elif cov is not None or fit_doc["uncertainty_status"] not in ("not-positive-definite", "non-finite", "not-formed"):
        raise ProductError(f"{where}: a failed fit has no covariance and a status other than ok")


def _check_seed(doc, where: str, variant: Variant) -> None:
    start = doc["seed"]
    if start is not None:
        keys = {"vertex", "direction", "e_vis", "t0", "from"} if variant.timed else {"vertex", "direction", "e_vis"}
        if not isinstance(start, dict) or set(start) != keys:
            raise ProductError(f"{where}: seed keys must be {sorted(keys)}")
        _vector(start["vertex"], f"{where}: seed vertex")
        _unit(start["direction"], f"{where}: seed direction")
        if not (_number(start["e_vis"]) and start["e_vis"] > 0):
            raise ProductError(f"{where}: seed e_vis must be positive")
        if variant.timed and not (_number(start["t0"]) and start["from"] in JOINT_ORIGINS):
            raise ProductError(f"{where}: seed t0 must be a finite number and from one of {JOINT_ORIGINS}")
    if not variant.timed:
        return
    prefit = doc["prefit"]
    if (start is None) != (prefit is None):
        raise ProductError(f"{where}: a joint seed comes with its charge-only prefit, and only then")
    if prefit is not None:
        if not isinstance(prefit, dict) or set(prefit) != {"status", "failure", "iterations", "point", "ln_likelihood"}:
            raise ProductError(f"{where}: prefit keys must be status, failure, iterations, point, ln_likelihood")
        if not isinstance(prefit["point"], bool) or (prefit["status"] == "converged" and not prefit["point"]):
            raise ProductError(f"{where}: prefit point must be true or false, true for a converged prefit")
        # The seed's origin follows from the prefit (review F8): converged; failed with a point; failed without one.
        origin = JOINT_ORIGINS[0] if prefit["status"] == "converged" else JOINT_ORIGINS[1] if prefit["point"] else JOINT_ORIGINS[2]
        if start["from"] != origin:
            raise ProductError(f"{where}: seed from {start['from']!r} does not agree with its prefit ({origin!r} expected)")
        if prefit["status"] not in ("converged", "failed") or (prefit["status"] == "converged") != (prefit["failure"] is None) \
                or (prefit["failure"] is not None and prefit["failure"] not in FAILURES) or not _count(prefit["iterations"]) \
                or not (prefit["ln_likelihood"] is None or _number(prefit["ln_likelihood"])):
            raise ProductError(f"{where}: prefit malformed")


def _point_of(doc, where):
    if not isinstance(doc, dict) or set(doc) != POINT_KEYS:
        raise ProductError(f"{where}: a point must have exactly {sorted(POINT_KEYS)}")
    vertex = _vector(doc["vertex"], where)
    direction = _unit(doc["direction"], where)
    if not (_number(doc["e_vis"]) and _number(doc["t0"])):
        raise ProductError(f"{where}: e_vis and t0 must be finite numbers")
    return vertex, direction, doc["e_vis"], doc["t0"]


def _check_starts(doc, budget_doc, where: str) -> None:
    """Product /3's per-start records against the budget, the seed, the choice rule and the reported fit (no model needed)."""
    starts, choice, fit_doc, seed_doc = doc["starts"], doc["choice"], doc["fit"], doc["seed"]
    if not isinstance(starts, list) or not isinstance(choice, dict) or set(choice) != {"chosen", "rule"}:
        raise ProductError(f"{where}: starts must be a list and choice exactly chosen and rule")
    names = budget_doc["starts"] if seed_doc is not None else []
    if [s.get("name") if isinstance(s, dict) else None for s in starts] != names:
        raise ProductError(f"{where}: the starts must be the budget's {names}, in its order")
    outcomes = []
    for k, s in enumerate(starts):
        at = f"{where}: start {k}"
        if set(s) != START_KEYS:
            raise ProductError(f"{at}: keys must be exactly {sorted(START_KEYS)}")
        _point_of(s["start"], at)
        status, failure = s["status"], s["failure"]
        if status not in ("converged", "failed") or (status == "converged") != (failure is None) or \
                (failure is not None and failure not in FAILURES):
            raise ProductError(f"{at}: status {status!r} and failure {failure!r} do not agree")
        if not (_count(s["iterations"]) and _count(s["rounds"])):
            raise ProductError(f"{at}: iterations and rounds must be counts")
        if s["ln_likelihood"] is not None and not _number(s["ln_likelihood"]):
            raise ProductError(f"{at}: ln_likelihood must be null or finite")
        if s["end"] is not None:
            _point_of(s["end"], at)
        elif s["ln_likelihood"] is not None:
            raise ProductError(f"{at}: an ln L without an end point")
        if status == "converged" and (s["end"] is None or s["ln_likelihood"] is None):
            raise ProductError(f"{at}: a converged start needs its end point and ln L")
        outcomes.append((status, s["ln_likelihood"]))
    if starts and starts[0]["start"] != {k: seed_doc[k] for k in POINT_KEYS}:
        raise ProductError(f"{where}: start 0 is not the seed")
    chosen, rule = multistart.choose(outcomes, budget_doc["tie_tolerance"])
    if choice != {"chosen": chosen, "rule": rule}:
        raise ProductError(f"{where}: choice {choice!r} is not the rule's ({chosen!r}, {rule!r})")
    point = None if fit_doc["vertex"] is None else {"vertex": fit_doc["vertex"], "direction": fit_doc["direction"],
                                                     "e_vis": fit_doc["e_vis"], "t0": fit_doc["t0"]}
    if chosen is not None:
        s = starts[chosen]
        want = (s["status"], s["failure"], s["ln_likelihood"], s["iterations"], s["rounds"], s["end"])
    elif starts:
        s = starts[0]
        want = ("failed", multistart.ALL_FAILED, s["ln_likelihood"], s["iterations"], s["rounds"], s["end"])
    else:
        want = ("failed", "no-hit-channel", None, 0, 0, None)
    got = (fit_doc["status"], fit_doc["failure"], fit_doc["ln_likelihood"], fit_doc["iterations"], fit_doc["rounds"], point)
    if got != want:
        raise ProductError(f"{where}: the reported fit is not the {'chosen start' if chosen is not None else 'rule'}'s")


def _verify_starts(doc, tev, model, header, where: str) -> None:
    """Every start point recomputed from the anchor and the data, and every start's ln L at its end point (product /3)."""
    starts = doc["starts"]
    if not starts:
        return
    b = header["budget"]
    seed_doc = doc["seed"]
    anchor = JointSeed(numpy.array(seed_doc["vertex"], float), numpy.array(seed_doc["direction"], float), seed_doc["e_vis"],
                       seed_doc["t0"])
    budget = multistart.Budget(b["format"], tuple(b["starts"]), b["tie_tolerance"], b["sha256"])
    for k, ((name, start), s) in enumerate(zip(multistart.start_points(model, tev, budget, anchor), starts)):
        stored = s["start"]
        again = numpy.r_[start.vertex, start.direction, start.e_vis, start.t0]
        kept = numpy.r_[stored["vertex"], stored["direction"], stored["e_vis"], stored["t0"]]
        if not numpy.all(numpy.abs(again - kept) <= START_TOLERANCE * numpy.maximum(1.0, numpy.abs(again))):
            raise ProductError(f"{where}: start {k} ({name}) does not recompute from the anchor and the data")
        if s["ln_likelihood"] is not None:
            end = s["end"]
            value = joint.log_likelihood(model, tev, numpy.array(end["vertex"]), numpy.array(end["direction"]), end["e_vis"], end["t0"])
            if not abs(value - s["ln_likelihood"]) <= LN_L_TOLERANCE * max(1.0, abs(value)):
                raise ProductError(f"{where}: start {k} ln L {s['ln_likelihood']} does not recompute ({value})")


SOURCE_KEYS = {"vertex", "direction", "e_vis", "t0"}


def _two_point_of(doc, where):
    if not isinstance(doc, dict) or set(doc) != {"sources"} or not isinstance(doc["sources"], list) or len(doc["sources"]) != 2:
        raise ProductError(f"{where}: a two-source point must have exactly sources (two)")
    vertices, directions, e_vis, t0 = [], [], [], []
    for s in doc["sources"]:
        if not isinstance(s, dict) or set(s) != SOURCE_KEYS:
            raise ProductError(f"{where}: a source must have exactly {sorted(SOURCE_KEYS)}")
        vertices.append(_vector(s["vertex"], where))
        directions.append(_unit(s["direction"], where))
        if not (_number(s["e_vis"]) and s["e_vis"] > 0):
            raise ProductError(f"{where}: a source's e_vis must be a positive finite number")
        if not _number(s["t0"]):
            raise ProductError(f"{where}: a source's t0 must be a finite number")
        e_vis.append(s["e_vis"])
        t0.append(s["t0"])
    return topology.Point(numpy.array(vertices), numpy.array(directions), numpy.array(e_vis, float), numpy.array(t0, float))


def _fit_point_doc(two):
    """The point of an H2 fit document, in the start records' form (the frames left out)."""
    return {"sources": [{k: src[k] for k in SOURCE_KEYS} for src in two["sources"]]}


def _check_two_fit(fit_doc, where: str) -> None:
    if not isinstance(fit_doc, dict) or set(fit_doc) != H2_FIT_KEYS:
        raise ProductError(f"{where}: H2 fit keys must be exactly {sorted(H2_FIT_KEYS)}")
    status, failure = fit_doc["status"], fit_doc["failure"]
    if status not in ("converged", "failed") or (status == "converged") != (failure is None) or \
            (failure is not None and failure not in topology.FAILURES):
        raise ProductError(f"{where}: H2 status {status!r} and failure {failure!r} do not agree")
    if not (_count(fit_doc["iterations"]) and _count(fit_doc["rounds"])):
        raise ProductError(f"{where}: H2 iterations and rounds must be counts")
    for key in ("ln_likelihood", "gradient_norm", "newton_decrement"):
        if fit_doc[key] is not None and not _number(fit_doc[key]):
            raise ProductError(f"{where}: H2 {key} must be null or finite")
    sources = fit_doc["sources"]
    if sources is None:
        if any(fit_doc[k] is not None for k in ("ln_likelihood", "gradient_norm", "newton_decrement", "covariance")):
            raise ProductError(f"{where}: an H2 fit without a point carries values")
    else:
        if not (isinstance(sources, list) and len(sources) == 2):
            raise ProductError(f"{where}: H2 sources must be two")
        for s in sources:
            if not isinstance(s, dict) or set(s) != SOURCE_KEYS | {"frame"}:
                raise ProductError(f"{where}: an H2 source must have exactly vertex, direction, e_vis, t0 and frame")
            if not _number(s["t0"]):
                raise ProductError(f"{where}: an H2 source's t0 must be a finite number")
            _vector(s["vertex"], where)
            d = _unit(s["direction"], where)
            if not (_number(s["e_vis"]) and s["e_vis"] > 0):
                raise ProductError(f"{where}: an H2 source's e_vis must be positive")
            frm = s["frame"]
            if not isinstance(frm, dict) or set(frm) != {"e1", "e2"}:
                raise ProductError(f"{where}: an H2 source's frame must have e1 and e2")
            e1, e2 = frame(d)
            if numpy.abs(_vector(frm["e1"], where) - e1).max() > 1e-12 or numpy.abs(_vector(frm["e2"], where) - e2).max() > 1e-12:
                raise ProductError(f"{where}: an H2 source's frame is not section 7's at its direction")
        if fit_doc["ln_likelihood"] is None:
            raise ProductError(f"{where}: an H2 fit with a point has its ln L")
    cov = fit_doc["covariance"]
    if status == "converged":
        if fit_doc["uncertainty_status"] != "ok" or fit_doc["gradient_norm"] is None or fit_doc["newton_decrement"] is None \
                or not fit_doc["newton_decrement"] <= SETTINGS["newton_decrement_tolerance"] or sources is None:
            raise ProductError(f"{where}: a converged H2 fit needs a point, status ok, the gradient norm and a Newton decrement "
                               "within the tolerance")
        size = topology.SIZE
        if not (isinstance(cov, list) and len(cov) == size and all(isinstance(r, list) and len(r) == size and all(_number(x) for x in r)
                                                                   for r in cov)):
            raise ProductError(f"{where}: the H2 covariance must be {size} x {size} finite numbers")
        c = numpy.array(cov, float)
        if not numpy.array_equal(c, c.T):
            raise ProductError(f"{where}: the H2 covariance is not symmetric")
        try:
            numpy.linalg.cholesky(c)
        except numpy.linalg.LinAlgError:
            raise ProductError(f"{where}: the H2 covariance is not positive definite") from None
    elif cov is not None or fit_doc["uncertainty_status"] not in ("not-positive-definite", "non-finite", "not-formed"):
        raise ProductError(f"{where}: a failed H2 fit has no covariance and a status other than ok")


def _check_topology(doc, head: dict, where: str, event: EventData) -> None:
    """The topology record of a /4 event line (structure; no model needed)."""
    topo, fit_doc = doc["topology"], doc["fit"]
    if not isinstance(topo, dict) or set(topo) != TOPOLOGY_KEYS:
        raise ProductError(f"{where}: topology keys must be exactly {sorted(TOPOLOGY_KEYS)}")
    if topo["penalty"] != topology.PENALTY or isinstance(topo["penalty"], bool):
        raise ProductError(f"{where}: the penalty is t04-values-v4.md section 7's {topology.PENALTY}")
    if fit_doc["status"] != "converged":
        if any(topo[k] is not None for k in TOPOLOGY_KEYS - {"penalty", "rule"}) or topo["rule"] != topology.CHOICE_H1_FAILED:
            raise ProductError(f"{where}: where H1 failed there is no H2 fit and no choice")
        return
    if topo["rule"] != topology.CHOICE_RULE:
        raise ProductError(f"{where}: the choice rule is not this recipe's")
    h2 = topo["h2"]
    if not isinstance(h2, dict) or set(h2) != H2_KEYS:
        raise ProductError(f"{where}: h2 keys must be exactly {sorted(H2_KEYS)}")
    starts, reported = h2["starts"], h2["reported"]
    if not isinstance(starts, list) or [s.get("name") if isinstance(s, dict) else None for s in starts] != head["starts"]:
        raise ProductError(f"{where}: the H2 starts must be the topology budget's {head['starts']}, in its order")
    h1_source = {"vertex": fit_doc["vertex"], "direction": fit_doc["direction"], "e_vis": fit_doc["e_vis"], "t0": fit_doc["t0"]}
    ln_ls = []
    for k, s in enumerate(starts):
        at = f"{where}: H2 start {k}"
        if set(s) != H2_START_KEYS:
            raise ProductError(f"{at}: keys must be exactly {sorted(H2_START_KEYS)}")
        status, failure = s["status"], s["failure"]
        if status not in ("converged", "failed") or (status == "converged") != (failure is None) or \
                (failure is not None and failure not in topology.FAILURES):
            raise ProductError(f"{at}: status {status!r} and failure {failure!r} do not agree")
        if not (_count(s["iterations"]) and _count(s["rounds"])):
            raise ProductError(f"{at}: iterations and rounds must be counts")
        if s["start"] is None:
            if (status, failure, s["end"], s["ln_likelihood"], s["iterations"], s["rounds"]) != ("failed", topology.NO_START, None, None, 0, 0):
                raise ProductError(f"{at}: a start that was not formed is failed, {topology.NO_START}, with nothing else")
        else:
            if failure == topology.NO_START:
                raise ProductError(f"{at}: {topology.NO_START} with a start point")
            _two_point_of(s["start"], at)
            if s["name"] in topology.H1_ANCHORED and s["start"]["sources"][0] != h1_source:
                raise ProductError(f"{at}: source 1 of the start {s['name']!r} is not H1's fit")
        if (s["end"] is None) != (s["ln_likelihood"] is None):
            raise ProductError(f"{at}: an end point comes with its ln L, and only then")
        if s["end"] is not None:
            _two_point_of(s["end"], at)
            if not _number(s["ln_likelihood"]):
                raise ProductError(f"{at}: ln_likelihood must be finite")
        if status == "converged" and s["end"] is None:
            raise ProductError(f"{at}: a converged start needs its end point")
        ln_ls.append(s["ln_likelihood"] if s["end"] is not None else None)
    index, rule = topology.report_choice(ln_ls, head["tie_tolerance"])
    if reported != {"index": index, "rule": rule}:
        raise ProductError(f"{where}: the reported H2 point {reported!r} is not the rule's ({index!r}, {rule!r})")
    two = h2["fit"]
    if index is None:
        if two is not None:
            raise ProductError(f"{where}: no H2 point, but an H2 fit")
    else:
        _check_two_fit(two, where)
        s = starts[index]
        point = None if two["sources"] is None else _fit_point_doc(two)
        if (two["status"], two["failure"], two["ln_likelihood"], two["iterations"], two["rounds"], point) != \
                (s["status"], s["failure"], s["ln_likelihood"], s["iterations"], s["rounds"], s["end"]):
            raise ProductError(f"{where}: the H2 fit is not the reported start's")
    ln_l1 = topo["ln_likelihood_1"]
    if ln_l1 != fit_doc["ln_likelihood"] or not _number(ln_l1):
        raise ProductError(f"{where}: ln_likelihood_1 is not H1's")
    want = topology.statistic(ln_l1, None if two is None else two["ln_likelihood"])
    if (topo["ln_likelihood_2"], topo["ln_likelihood_2_from"], topo["statistic"]) != want or isinstance(topo["statistic"], bool):
        raise ProductError(f"{where}: lnL_2, its origin or the statistic does not recompute ({want!r})")
    if topo["choice"] != topology.choose(want[2]):
        raise ProductError(f"{where}: the choice {topo['choice']!r} is not the rule's ({topology.choose(want[2])!r})")
    check = topo["probability_check"]
    if two is None or two["sources"] is None:
        if check is not None:
            raise ProductError(f"{where}: a check at H2's point without one")
        return
    if not isinstance(check, dict) or set(check) != CHECK_KEYS:
        raise ProductError(f"{where}: the H2 probability_check keys must be exactly {sorted(CHECK_KEYS)}")
    if check["point"] != ("fit" if two["status"] == "converged" else "fit-last") or check["channels"] != int(event.live.sum()) \
            or not _count(check["failures"]) or not _number(check["max_abs_deviation"]) or not _number(check["largest_ratio"]) \
            or not isinstance(check["failed_channels"], list):
        raise ProductError(f"{where}: the H2 probability_check is malformed or not at H2's point")


def _verify_topology(doc, tev, model, header, where: str) -> None:
    """H2's start points from H1's fit and the data, every H2 start's ln L at its end point, and the check at H2's point."""
    topo = doc["topology"]
    if topo["h2"] is None:
        return
    head = header["topology"]
    tb = topology.TopologyBudget(head["format"], tuple(head["starts"]), head["tie_tolerance"], head["sha256"])
    h1 = fit_result_of(doc["fit"])
    for k, ((name, start), s) in enumerate(zip(topology.start_points(model, tev, tb, h1), topo["h2"]["starts"])):
        if (start is None) != (s["start"] is None):
            raise ProductError(f"{where}: H2 start {k} ({name}) is {'not ' if start is None else ''}formed from H1's fit and the data")
        if start is not None:
            stored = _two_point_of(s["start"], where)
            again = numpy.r_[start.vertices.ravel(), start.directions.ravel(), start.e_vis, start.t0]
            kept = numpy.r_[stored.vertices.ravel(), stored.directions.ravel(), stored.e_vis, stored.t0]
            if not numpy.all(numpy.abs(again - kept) <= START_TOLERANCE * numpy.maximum(1.0, numpy.abs(again))):
                raise ProductError(f"{where}: H2 start {k} ({name}) does not recompute from H1's fit and the data")
        if s["ln_likelihood"] is not None:
            value = topology.log_likelihood(model, tev, _two_point_of(s["end"], where))
            if not abs(value - s["ln_likelihood"]) <= LN_L_TOLERANCE * max(1.0, abs(value)):
                raise ProductError(f"{where}: H2 start {k} ln L {s['ln_likelihood']} does not recompute ({value})")
    check = topo["probability_check"]
    if check is not None:
        two = topo["h2"]["fit"]
        point = _two_point_of(_fit_point_doc(two), where)
        again = topology.probability_check(model, tev.event, point)
        if (again["failures"], again["failed_channels"], again["channels"]) != (check["failures"], check["failed_channels"], check["channels"]) \
                or abs(again["max_abs_deviation"] - check["max_abs_deviation"]) > DEVIATION_TOLERANCE \
                or abs(again["largest_ratio"] - check["largest_ratio"]) > RATIO_TOLERANCE * max(1.0, abs(check["largest_ratio"])):
            raise ProductError(f"{where}: the check at H2's point does not recompute")


def _verify(doc, event, tev, model, where: str, header=None) -> None:
    """Recompute ln L (the joint ln L for /2) and the probability check from the product; any defect is a ProductError (fix
    round 1, F2). A stored point outside the fit's domain is refused by the probability check (EventError), turned into a
    ProductError here."""
    fit_doc, check = doc["fit"], doc["probability_check"]
    try:
        if fit_doc["vertex"] is not None:
            args = (numpy.array(fit_doc["vertex"]), numpy.array(fit_doc["direction"]), fit_doc["e_vis"])
            again = {"point": check["point"], **probability_check(model, event, *args)}
            if fit_doc["ln_likelihood"] is not None:
                value = log_likelihood(model, event, *args) if tev is None else joint.log_likelihood(model, tev, *args, fit_doc["t0"])
                if not abs(value - fit_doc["ln_likelihood"]) <= LN_L_TOLERANCE * max(1.0, abs(value)):
                    raise ProductError(f"{where}: ln L {fit_doc['ln_likelihood']} does not recompute ({value})")
        else:
            again = {"point": check["point"], **probability_check(model, event)}
        if header is not None and "starts" in doc:
            _verify_starts(doc, tev, model, header, where)
        if header is not None and "topology" in doc:
            _verify_topology(doc, tev, model, header, where)
    except ValueError as exc:
        if isinstance(exc, ProductError):
            raise
        raise ProductError(f"{where}: cannot be recomputed: {exc}") from None
    if (again["failures"], again["failed_channels"], again["channels"]) != (check["failures"], check["failed_channels"], check["channels"]) \
            or abs(again["max_abs_deviation"] - check["max_abs_deviation"]) > DEVIATION_TOLERANCE \
            or abs(again["largest_ratio"] - check["largest_ratio"]) > RATIO_TOLERANCE * max(1.0, abs(check["largest_ratio"])):
        raise ProductError(f"{where}: the probability check does not recompute")


def _check_event(doc, index: int, header: dict, variant: Variant):
    """Every structural rule of one event line; returns (EventData, TimedEvent or None) for the recomputation."""
    where = f"event line {index + 2}"
    keys = EVENT_KEYS | {"prefit"} if variant.timed else EVENT_KEYS
    if variant.multistart:
        keys = keys | {"starts", "choice"}
    if variant.topology:
        keys = keys | {"topology"}
    if not isinstance(doc, dict) or set(doc) != keys:
        raise ProductError(f"{where}: keys must be exactly {sorted(keys)}")
    if doc["event"] != index or isinstance(doc["event"], bool):
        raise ProductError(f"{where}: event {doc['event']!r} out of order, {index} expected")
    source = header["input"]
    event, tev = _event_arrays(doc, source, where, variant)
    _check_seed(doc, where, variant)
    _check_fit(doc["fit"], event, source, where, variant)
    if variant.multistart:
        _check_starts(doc, header["budget"], where)
    if variant.topology:
        _check_topology(doc, header["topology"], where, event)
    check = doc["probability_check"]
    if not isinstance(check, dict) or set(check) != CHECK_KEYS:
        raise ProductError(f"{where}: probability_check keys must be exactly {sorted(CHECK_KEYS)}")
    want = "dark-only" if doc["fit"]["vertex"] is None else ("fit" if doc["fit"]["status"] == "converged" else "fit-last")
    if check["point"] != want or check["channels"] != int(event.live.sum()) or not _count(check["failures"]) \
            or not _number(check["max_abs_deviation"]) or not _number(check["largest_ratio"]) or not isinstance(check["failed_channels"], list):
        raise ProductError(f"{where}: probability_check malformed or not at the reported point")
    return event, tev


def _structural(where: str, action, *args):
    """Run a structural check; any structural exception is a ProductError (re-review N5)."""
    try:
        return action(*args)
    except ProductError:
        raise
    except STRUCTURAL as exc:
        raise ProductError(f"{where}: malformed field ({type(exc).__name__}: {exc})") from None


def read_text(text: str, model=None, cfg=None, budget=None, topology_budget=None) -> Product:
    """Read and check a product (/1, /2, /3 or /4). model (and cfg) given: ln L and the probability check are recomputed per event
    (for /3 and /4 every start too, for /4 H2's starts and its check); budget given: a /3 or /4 product must have been made with
    it; topology_budget given: a /4 product must have been made with it."""
    if not text.endswith("\n"):
        raise ProductError("the last line is unfinished")
    lines = text[:-1].split("\n")
    try:
        docs = [json.loads(line, parse_constant=_refuse_constant) for line in lines]
    except (ValueError, RecursionError) as exc:      # a line nested too deep is malformed too (review F3)
        raise ProductError(f"a line is not JSON: {exc}") from None
    if len(docs) < 2:
        raise ProductError("a product needs a header and an end line")
    header = docs[0]
    variant = _structural("header", _check_header, header, cfg, budget, topology_budget)
    if model is not None and header["input"]["channels"] != model.geometry.channels:
        raise ProductError("the product's channels are not the model's")
    end = docs[-1]
    if end != {"end": variant.format, "events": len(docs) - 2}:
        if isinstance(end, dict) and "end" in end:
            raise ProductError(f"end line {end!r} does not close {len(docs) - 2} events of {variant.format}")
        raise ProductError("the end line is missing")
    if any(isinstance(d, dict) and "end" in d for d in docs[1:-1]):
        raise ProductError("text after the end line")
    events = docs[1:-1]
    if len(events) != header["events"]:
        raise ProductError(f"{len(events)} events, the header says {header['events']}")
    for i, doc in enumerate(events):
        event, tev = _structural(f"event line {i + 2}", _check_event, doc, i, header, variant)
        if model is not None:
            _verify(doc, event, tev, model, f"event line {i + 2}", header)
    return Product(header, events)


def format_of(path) -> str | None:
    """The format named by a product's first line, or None when it cannot be told (the reader then refuses the file)."""
    try:
        with open(path, encoding="utf-8") as stream:
            doc = json.loads(stream.readline())
    except (OSError, UnicodeDecodeError, ValueError, RecursionError):
        return None
    return doc.get("format") if isinstance(doc, dict) and isinstance(doc.get("format"), str) else None


def read_product(path, model=None, cfg=None, budget=None, topology_budget=None) -> Product:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProductError(f"product cannot be read: {exc}") from None
    return read_text(text, model, cfg, budget, topology_budget)


CHARGE_ONLY = Variant(FORMAT, LIKELIHOOD, PARAMETERS, NOT_ESTIMATED, UNCERTAINTY_TEXT, SETTINGS, RETENTION, False)
CHARGE_TIME = Variant(FORMAT_JOINT, LIKELIHOOD_JOINT, PARAMETERS_JOINT, NOT_ESTIMATED_JOINT, UNCERTAINTY_JOINT, SETTINGS_JOINT,
                      RETENTION_JOINT, True)
MULTISTART = Variant(FORMAT_MULTISTART, LIKELIHOOD_JOINT, PARAMETERS_JOINT, NOT_ESTIMATED_JOINT, UNCERTAINTY_JOINT, SETTINGS_MULTISTART,
                     RETENTION_JOINT, True, True, multistart.FAILURES)
TOPOLOGY = Variant(FORMAT_TOPOLOGY, LIKELIHOOD_JOINT, PARAMETERS_JOINT, NOT_ESTIMATED_JOINT, UNCERTAINTY_JOINT, SETTINGS_MULTISTART,
                   RETENTION_JOINT, True, True, multistart.FAILURES, HYPOTHESIS_TOPOLOGY, True)
SINGLE_PHOTON = Variant(FORMAT_SINGLE_PHOTON, single_photon.LIKELIHOOD, PARAMETERS_JOINT, NOT_ESTIMATED_JOINT, UNCERTAINTY_JOINT,
                        SETTINGS_MULTISTART, RETENTION_JOINT, True, True, multistart.FAILURES, configuration_format=single_photon.FORMAT)
VARIANTS = {v.format: v for v in (CHARGE_ONLY, CHARGE_TIME, MULTISTART, TOPOLOGY, SINGLE_PHOTON)}
BY_LIKELIHOOD = {"charge-only": CHARGE_ONLY, "charge-time": CHARGE_TIME}
