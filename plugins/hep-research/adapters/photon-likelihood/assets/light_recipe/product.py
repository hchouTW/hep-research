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
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy

from . import LABEL, LABEL_MEANING, LIKELIHOOD, PARAMETERS, PARAMETER_UNITS, RECIPE, readout
from .fit import FAILURES, SETTINGS, FitResult, Seed
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
LN_L_TOLERANCE = 1e-9
DEVIATION_TOLERANCE = 1e-14
RATIO_TOLERANCE = 1e-3          # the ratio's recomputation, relative: its numerator is a rounding residue


class ProductError(ValueError):
    """The product is refused: the reason names the line and the defect."""


@dataclass(frozen=True)
class Product:
    header: dict
    events: list


def dumps(doc) -> str:
    return json.dumps(doc, sort_keys=True, allow_nan=False)


def _vec(v):
    return None if v is None else [float(c) for c in v]


def header_document(product_id: str, rd, cfg) -> dict:
    return {"format": FORMAT, "recipe": RECIPE, "product_id": product_id, "label": LABEL, "label_meaning": LABEL_MEANING,
            "likelihood": LIKELIHOOD, "hypothesis": HYPOTHESIS,
            "input": {"format": rd.header["format"], "role": rd.header["role"], "sha256": rd.sha256, "events": rd.events,
                      "channels": rd.channels, "threshold": rd.header["threshold"], "saturation_charge": rd.header["saturation_charge"]},
            "configuration": {"format": cfg.format, "sha256": cfg.sha256},
            "parameters": [{"name": n, "unit": PARAMETER_UNITS[n]} for n in PARAMETERS], "frame": FRAME_TEXT,
            "uncertainty": UNCERTAINTY_TEXT, "not_estimated": dict(NOT_ESTIMATED), "fit_settings": dict(SETTINGS),
            "hessian_steps": dict(HESSIAN_STEPS), "probability_check": {**CHECK_HEADER, "rule": CHECK_RULE},
            "channel_states": {LETTERS[k]: readout.STATE_NAMES[k] for k in sorted(LETTERS)}, "retention": dict(RETENTION),
            "events": rd.events}


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
    fit_doc = {"status": res.status, "failure": res.failure, "vertex": _vec(res.vertex), "direction": _vec(res.direction),
               "e_vis": None if res.e_vis is None else float(res.e_vis), "t0": "not-estimated",
               "frame": None if res.e1 is None else {"e1": _vec(res.e1), "e2": _vec(res.e2)},
               "covariance": None if res.covariance is None else [[float(x) for x in row] for row in res.covariance],
               "uncertainty_status": res.uncertainty_status,
               "ln_likelihood": None if res.ln_likelihood is None else float(res.ln_likelihood),
               "gradient_norm": None if res.gradient_norm is None else float(res.gradient_norm),
               "newton_decrement": None if res.newton_decrement is None else float(res.newton_decrement),
               "iterations": int(res.iterations), "rounds": int(res.rounds)}
    return {"event": index, "states": "".join(LETTERS[int(s)] for s in event.state), "hits": hits,
            "counts": _counts(event.state, event.saturated),
            "seed": None if start is None else {"vertex": _vec(start.vertex), "direction": _vec(start.direction),
                                                "e_vis": float(start.e_vis)},
            "fit": fit_doc, "probability_check": check}


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
        stream.write(dumps(header) + "\n")

    def event(self, doc: dict) -> None:
        self.stream.write(dumps(doc) + "\n")
        self.count += 1

    def finish(self) -> None:
        self.stream.write(dumps({"end": FORMAT, "events": self.count}) + "\n")


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


def _check_header(header: dict, cfg) -> None:
    if not isinstance(header, dict) or set(header) != HEADER_KEYS:
        raise ProductError(f"header keys must be exactly {sorted(HEADER_KEYS)}")
    fixed = {"format": FORMAT, "recipe": RECIPE, "label": LABEL, "label_meaning": LABEL_MEANING, "likelihood": LIKELIHOOD,
             "hypothesis": HYPOTHESIS, "frame": FRAME_TEXT, "uncertainty": UNCERTAINTY_TEXT, "not_estimated": NOT_ESTIMATED,
             "fit_settings": SETTINGS, "hessian_steps": HESSIAN_STEPS, "retention": RETENTION,
             "probability_check": {**CHECK_HEADER, "rule": CHECK_RULE},
             "parameters": [{"name": n, "unit": PARAMETER_UNITS[n]} for n in PARAMETERS],
             "channel_states": {LETTERS[k]: readout.STATE_NAMES[k] for k in sorted(LETTERS)}}
    for key, value in fixed.items():
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
    if cfg is not None and (conf["format"] != cfg.format or conf["sha256"] != cfg.sha256):
        raise ProductError("the product was made with another configuration than the one given")


def _event_arrays(doc: dict, source: dict, where: str):
    states, hits = doc["states"], doc["hits"]
    channels = source["channels"]
    if not isinstance(states, str) or len(states) != channels or not set(states) <= set(CODES):
        raise ProductError(f"{where}: states must be {channels} letters of {sorted(CODES)}")
    state = numpy.array([CODES[c] for c in states], numpy.int8)
    charge = numpy.where(state == readout.LIVE_UNHIT, 0.0, numpy.nan)
    saturated = numpy.zeros(channels, bool)
    if not isinstance(hits, list):
        raise ProductError(f"{where}: hits must be a list")
    previous = -1
    for row in hits:
        if not (isinstance(row, list) and len(row) == 3 and _count(row[0]) and _number(row[1]) and row[2] in (0, 1)
                and not isinstance(row[2], bool)):
            raise ProductError(f"{where}: a hit row must be [channel, charge, saturated 0 or 1]")
        if row[0] <= previous or row[0] >= channels:
            raise ProductError(f"{where}: hit rows must be in ascending channel order, inside the channel range")
        previous = row[0]
        charge[row[0]] = row[1]
        saturated[row[0]] = bool(row[2])
    rows = [row[0] for row in hits]
    if rows != [int(c) for c in numpy.flatnonzero(state == readout.LIVE_HIT)]:
        raise ProductError(f"{where}: hit rows do not match the hit channels of the states")
    try:
        event = EventData(state, charge, saturated, source["saturation_charge"], source["threshold"])
    except ValueError as exc:
        raise ProductError(f"{where}: {exc}") from None
    if doc["counts"] != _counts(state, saturated):
        raise ProductError(f"{where}: counts are not the states'")
    return event


def _check_fit(fit_doc, event: EventData, source: dict, where: str) -> None:
    if not isinstance(fit_doc, dict) or set(fit_doc) != FIT_KEYS:
        raise ProductError(f"{where}: fit keys must be exactly {sorted(FIT_KEYS)}")
    if fit_doc["t0"] != "not-estimated":
        raise ProductError(f"{where}: t0 must be not-estimated in a charge-only product")
    status, failure = fit_doc["status"], fit_doc["failure"]
    if status not in ("converged", "failed") or (status == "converged") != (failure is None) or (failure is not None and failure not in FAILURES):
        raise ProductError(f"{where}: status {status!r} and failure {failure!r} do not agree")
    if not (_count(fit_doc["iterations"]) and _count(fit_doc["rounds"])):
        raise ProductError(f"{where}: iterations and rounds must be counts")
    has_point = fit_doc["vertex"] is not None
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
    if status == "converged":
        if fit_doc["uncertainty_status"] != "ok" or fit_doc["ln_likelihood"] is None or fit_doc["gradient_norm"] is None \
                or fit_doc["newton_decrement"] is None or not fit_doc["newton_decrement"] <= SETTINGS["newton_decrement_tolerance"]:
            raise ProductError(f"{where}: a converged fit needs status ok, ln L, the gradient norm and a Newton decrement within "
                               "the tolerance")
        if not (isinstance(cov, list) and len(cov) == 6 and all(isinstance(r, list) and len(r) == 6 and all(_number(x) for x in r) for r in cov)):
            raise ProductError(f"{where}: covariance must be 6 x 6 finite numbers")
        c = numpy.array(cov, float)
        if not numpy.array_equal(c, c.T):
            raise ProductError(f"{where}: covariance is not symmetric")
        try:
            numpy.linalg.cholesky(c)
        except numpy.linalg.LinAlgError:
            raise ProductError(f"{where}: covariance is not positive definite") from None
    elif cov is not None or fit_doc["uncertainty_status"] not in ("not-positive-definite", "non-finite", "not-formed"):
        raise ProductError(f"{where}: a failed fit has no covariance and a status other than ok")


def _verify(doc, event, model, where: str) -> None:
    """Recompute ln L and the probability check from the product; any defect is a ProductError (fix round 1, F2). A stored
    point outside the fit's domain is refused by the probability check (EventError), turned into a ProductError here."""
    fit_doc, check = doc["fit"], doc["probability_check"]
    try:
        if fit_doc["vertex"] is not None:
            args = (numpy.array(fit_doc["vertex"]), numpy.array(fit_doc["direction"]), fit_doc["e_vis"])
            again = {"point": check["point"], **probability_check(model, event, *args)}
            if fit_doc["ln_likelihood"] is not None:
                value = log_likelihood(model, event, *args)
                if not abs(value - fit_doc["ln_likelihood"]) <= LN_L_TOLERANCE * max(1.0, abs(value)):
                    raise ProductError(f"{where}: ln L {fit_doc['ln_likelihood']} does not recompute ({value})")
        else:
            again = {"point": check["point"], **probability_check(model, event)}
    except ValueError as exc:
        if isinstance(exc, ProductError):
            raise
        raise ProductError(f"{where}: cannot be recomputed: {exc}") from None
    if (again["failures"], again["failed_channels"], again["channels"]) != (check["failures"], check["failed_channels"], check["channels"]) \
            or abs(again["max_abs_deviation"] - check["max_abs_deviation"]) > DEVIATION_TOLERANCE \
            or abs(again["largest_ratio"] - check["largest_ratio"]) > RATIO_TOLERANCE * max(1.0, abs(check["largest_ratio"])):
        raise ProductError(f"{where}: the probability check does not recompute")


def _check_event(doc, index: int, header: dict, model) -> None:
    where = f"event line {index + 2}"
    if not isinstance(doc, dict) or set(doc) != EVENT_KEYS:
        raise ProductError(f"{where}: keys must be exactly {sorted(EVENT_KEYS)}")
    if doc["event"] != index:
        raise ProductError(f"{where}: event {doc['event']!r} out of order, {index} expected")
    source = header["input"]
    event = _event_arrays(doc, source, where)
    start = doc["seed"]
    if start is not None:
        if not isinstance(start, dict) or set(start) != {"vertex", "direction", "e_vis"}:
            raise ProductError(f"{where}: seed keys must be vertex, direction, e_vis")
        _vector(start["vertex"], f"{where}: seed vertex")
        _unit(start["direction"], f"{where}: seed direction")
        if not (_number(start["e_vis"]) and start["e_vis"] > 0):
            raise ProductError(f"{where}: seed e_vis must be positive")
    _check_fit(doc["fit"], event, source, where)
    check = doc["probability_check"]
    if not isinstance(check, dict) or set(check) != CHECK_KEYS:
        raise ProductError(f"{where}: probability_check keys must be exactly {sorted(CHECK_KEYS)}")
    want = "dark-only" if doc["fit"]["vertex"] is None else ("fit" if doc["fit"]["status"] == "converged" else "fit-last")
    if check["point"] != want or check["channels"] != int(event.live.sum()) or not _count(check["failures"]) \
            or not _number(check["max_abs_deviation"]) or not _number(check["largest_ratio"]) or not isinstance(check["failed_channels"], list):
        raise ProductError(f"{where}: probability_check malformed or not at the reported point")
    if model is not None:
        _verify(doc, event, model, where)


def read_text(text: str, model=None, cfg=None) -> Product:
    """Read and check a product. model (and cfg) given: ln L and the probability check are recomputed per event."""
    if not text.endswith("\n"):
        raise ProductError("the last line is unfinished")
    lines = text[:-1].split("\n")
    try:
        docs = [json.loads(line, parse_constant=_refuse_constant) for line in lines]
    except ValueError as exc:
        raise ProductError(f"a line is not JSON: {exc}") from None
    if len(docs) < 2:
        raise ProductError("a product needs a header and an end line")
    header = docs[0]
    _check_header(header, cfg)
    if model is not None and header["input"]["channels"] != model.geometry.channels:
        raise ProductError("the product's channels are not the model's")
    end = docs[-1]
    if end != {"end": FORMAT, "events": len(docs) - 2}:
        if isinstance(end, dict) and "end" in end:
            raise ProductError(f"end line {end!r} does not close {len(docs) - 2} events of {FORMAT}")
        raise ProductError("the end line is missing")
    if any(isinstance(d, dict) and "end" in d for d in docs[1:-1]):
        raise ProductError("text after the end line")
    events = docs[1:-1]
    if len(events) != header["events"]:
        raise ProductError(f"{len(events)} events, the header says {header['events']}")
    for i, doc in enumerate(events):
        _check_event(doc, i, header, model)
    return Product(header, events)


def read_product(path, model=None, cfg=None) -> Product:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ProductError(f"product cannot be read: {exc}") from None
    return read_text(text, model, cfg)
