"""TOF species hypotheses, migration and composition (plan BP07; t10-timing-stage-plan.md section 6.1, rows PID-T10a to d).

From a TOF record (event_time.tof) and a supplied momentum with its source and that source's unconstrained modes, for each species
hypothesis of mass m (particle-identification.md, "The common principle" and "Time of flight"):
    beta_h = p / sqrt(p^2 + m^2),  t_pred = L / (c beta_h),  r = TOF - t_pred,  ln L_h = -r^2 / (2 sigma_t^2) - ln(sigma_t sqrt(2 pi))
with a stated time resolution sigma_t (a fixture choice: the Gaussian form is the stage plan's, not a measured response). For each
hypothesis pair the log-likelihood ratio, labelled "log-likelihood ratio, not a probability", and the separation
|t_pred,a - t_pred,b| / sigma_t against k (within support or not: the momentum ceiling). A probability is written only with stated
priors (the reference: "A likelihood ratio becomes a probability only with a prior"). The working point (select B over A when
ln L_B - ln L_A >= x) is kept with its result. A track without a TOF gives a missing-input record with no numbers, never zeros.

migration() gives P(selected as B | true A) from a labelled population; purity() gives P(true A | selected as B) with the population
composition stated. They are separate quantities and separate fields (BP07). Synthetic inputs only; no PID quality is claimed.
"""
from __future__ import annotations

import math

from .event_time import SPEED_OF_LIGHT_CM_PER_NS
from .timing_payload import InputError

FORMAT = "timing-pid/1"
MIGRATION_FORMAT = "timing-migration/1"
LIKELIHOOD_RATIO_MEANING = "log-likelihood ratio, not a probability"
PROBABILITY_MEANING = "probability given the stated priors"
SUM_TOLERANCE = 1e-12
DEFAULT_K = 3.0


def _finite(value) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _check_inputs(momentum, species, sigma_t_ns, working_point, priors, k):
    if not isinstance(momentum, dict) or set(momentum) != {"value_gev", "source", "unconstrained_modes"} \
            or not _finite(momentum["value_gev"]) or momentum["value_gev"] <= 0 \
            or not isinstance(momentum["source"], str) or not momentum["source"] \
            or not isinstance(momentum["unconstrained_modes"], list) or not momentum["unconstrained_modes"] \
            or not all(isinstance(m, str) and m for m in momentum["unconstrained_modes"]):
        raise InputError("pid: the momentum is {value_gev > 0, source (a name), unconstrained_modes (a non-empty list of names)}: "
                         "the momentum source's unconstrained mode travels with it (A37)")
    names = [s.get("name") for s in species] if isinstance(species, list) else []
    if len(names) < 2 or len(set(names)) != len(names) or not all(_finite(s.get("mass_gev")) and s["mass_gev"] >= 0 for s in species):
        raise InputError("pid: at least two species hypotheses, each {name, mass_gev >= 0}, names distinct")
    if not _finite(sigma_t_ns) or sigma_t_ns <= 0 or not _finite(k) or k <= 0:
        raise InputError("pid: sigma_t and k are positive")
    if not isinstance(working_point, dict) or set(working_point) != {"select", "over", "threshold"} \
            or working_point["select"] not in names or working_point["over"] not in names or not _finite(working_point["threshold"]):
        raise InputError("pid: the working point is {select, over, threshold} over the hypotheses")
    if priors is not None:
        if not isinstance(priors, dict) or set(priors) != set(names) or not all(_finite(v) and v >= 0 for v in priors.values()) \
                or abs(math.fsum(priors.values()) - 1.0) > SUM_TOLERANCE:
            raise InputError("pid: the priors name every hypothesis and sum to 1")
    return names


def _evaluate(tof_ns, path_cm, momentum, species, sigma_t_ns, working_point, priors, k) -> dict:
    p = momentum["value_gev"]
    hypotheses = []
    for s in species:
        beta = p / math.sqrt(p * p + s["mass_gev"] ** 2)
        t_pred = path_cm / (SPEED_OF_LIGHT_CM_PER_NS * beta)
        residual = tof_ns - t_pred
        hypotheses.append({"name": s["name"], "mass_gev": s["mass_gev"], "beta": beta, "t_pred_ns": t_pred, "residual_ns": residual,
                           "log_likelihood": -residual * residual / (2 * sigma_t_ns ** 2) - math.log(sigma_t_ns * math.sqrt(2 * math.pi))})
    by_name = {h["name"]: h for h in hypotheses}
    llr, support = [], []
    for i, a in enumerate(hypotheses):
        for b in hypotheses[i + 1:]:
            llr.append({"a": a["name"], "b": b["name"], "value": a["log_likelihood"] - b["log_likelihood"], "meaning": LIKELIHOOD_RATIO_MEANING})
            separation = abs(a["t_pred_ns"] - b["t_pred_ns"]) / sigma_t_ns
            support.append({"a": a["name"], "b": b["name"], "separation_sigma": separation, "within_support": separation >= k})
    selected = by_name[working_point["select"]]["log_likelihood"] - by_name[working_point["over"]]["log_likelihood"] >= working_point["threshold"]
    pair = {working_point["select"], working_point["over"]}
    within = next(item["within_support"] for item in support if {item["a"], item["b"]} == pair) if len(pair) == 2 else False
    probabilities = None
    if priors is not None:
        top = max(h["log_likelihood"] for h in hypotheses)
        weights = {h["name"]: priors[h["name"]] * math.exp(h["log_likelihood"] - top) for h in hypotheses}
        total = math.fsum(weights.values())
        if not total > 0:
            raise InputError("pid: the priors give no weight to any hypothesis that has likelihood here (fix round 1, N4)")
        probabilities = {name: w / total for name, w in weights.items()}
    return {"hypotheses": hypotheses, "llr": llr, "support": support, "k": k, "selected": selected, "selected_within_support": within,
            "probabilities": probabilities, "probability_meaning": PROBABILITY_MEANING if priors is not None else None}


def hypotheses(tof_record, momentum, species, sigma_t_ns, working_point, priors=None, k=DEFAULT_K) -> dict:
    """The PID record (timing-pid/1) of one TOF record; a missing TOF is missing(), never this."""
    if not isinstance(tof_record, dict) or tof_record.get("format") != "timing-tof/1":
        raise InputError("pid: no timing-tof/1 record: a track without a TOF is a missing-input record (pid.missing), never zeros")
    if not _finite(tof_record.get("tof_ns")) or not _finite(tof_record.get("path_length_cm")) or tof_record["path_length_cm"] <= 0 \
            or tof_record["tof_ns"] <= 0 or not _finite(tof_record.get("beta")):
        raise InputError("pid: the TOF record has no positive TOF, positive path length and beta")
    if tof_record["beta"] != tof_record["path_length_cm"] / (SPEED_OF_LIGHT_CM_PER_NS * tof_record["tof_ns"]):
        raise InputError("pid: the TOF record's beta does not follow from its path length and TOF (fix round 1, M5)")
    _check_inputs(momentum, species, sigma_t_ns, working_point, priors, k)
    record = {"format": FORMAT, "status": "ok", "reason": None, "hit_id": tof_record["hit_id"], "track_id": tof_record["track_id"],
              "tof_ns": tof_record["tof_ns"], "path_length_cm": tof_record["path_length_cm"], "tof_beta": tof_record["beta"],
              "event_time": tof_record["event_time"],
              "momentum": dict(momentum), "species": [dict(s) for s in species], "sigma_t_ns": sigma_t_ns,
              "working_point": dict(working_point), "priors": None if priors is None else dict(priors)}
    record.update(_evaluate(record["tof_ns"], record["path_length_cm"], momentum, species, sigma_t_ns, working_point, priors, k))
    return record


NUMERIC_FIELDS = ("tof_ns", "path_length_cm", "hypotheses", "llr", "support", "selected", "probabilities")
MISSING_KEYS = {"format", "status", "reason", "hit_id", "track_id", *NUMERIC_FIELDS}


def missing(hit_id, track_id, reason: str) -> dict:
    """A track without the input (BP07: a missing subsystem permits only a validated missing-input method, not zeros)."""
    if not isinstance(reason, str) or not reason:
        raise InputError("pid: a missing-input record states its reason")
    return {"format": FORMAT, "status": "missing-input", "reason": reason, "hit_id": hit_id, "track_id": track_id,
            **{field: None for field in NUMERIC_FIELDS}}


def check(record: dict) -> None:
    """Refuses a PID record that labels an LLR as a probability, has a probability without priors, a missing input holding
    numbers, or values that do not follow from its own inputs (raises InputError, never another exception)."""
    try:
        _check(record)
    except InputError:
        raise
    except (TypeError, KeyError, AttributeError, ValueError, IndexError, ZeroDivisionError, StopIteration) as exc:
        raise InputError(f"pid: malformed record ({type(exc).__name__}: {exc})") from None


def _check(record: dict) -> None:
    if not isinstance(record, dict) or record.get("format") != FORMAT:
        raise InputError(f"pid: not a {FORMAT} record")
    if record["status"] == "missing-input":
        if set(record) != MISSING_KEYS or any(record[field] is not None for field in NUMERIC_FIELDS):
            raise InputError("pid: a missing-input record holds exactly its keys and no numbers, not even zeros (fix round 1, M4)")
        if not isinstance(record["reason"], str) or not record["reason"]:
            raise InputError("pid: a missing-input record states its reason")
        return
    if record["status"] != "ok":
        raise InputError("pid: status is ok or missing-input")
    if record["priors"] is None and record["probabilities"] is not None:
        raise InputError("pid: a probability needs stated priors; an LLR or likelihood is never a probability")
    if any(item["meaning"] != LIKELIHOOD_RATIO_MEANING for item in record["llr"]):
        raise InputError(f"pid: every LLR is labelled '{LIKELIHOOD_RATIO_MEANING}'")
    _check_inputs(record["momentum"], record["species"], record["sigma_t_ns"], record["working_point"], record["priors"], record["k"])
    expected = _evaluate(record["tof_ns"], record["path_length_cm"], record["momentum"], record["species"], record["sigma_t_ns"],
                         record["working_point"], record["priors"], record["k"])
    if any(record[key] != value for key, value in expected.items()):
        raise InputError("pid: the record's values do not follow from its own inputs")
    if not _finite(record["tof_beta"]) or record["tof_beta"] != record["path_length_cm"] / (SPEED_OF_LIGHT_CM_PER_NS * record["tof_ns"]):
        raise InputError("pid: the TOF record's beta does not follow from its path length and TOF")


def migration(true_labels: list, selected_labels: list, species: list) -> dict:
    """P(selected as B | true A) from a labelled population: counts n(A -> B) over n(A)."""
    if not isinstance(true_labels, list) or not isinstance(selected_labels, list) or len(true_labels) != len(selected_labels) \
            or not true_labels:
        raise InputError("pid: migration needs one selected label per true label")
    if not set(true_labels) <= set(species) or not set(selected_labels) <= set(species) | {"unselected"}:
        raise InputError("pid: a label is not a stated species (or unselected)")
    outcomes = list(species) + (["unselected"] if "unselected" in selected_labels else [])
    counts = {a: {b: 0 for b in outcomes} for a in species}
    for a, b in zip(true_labels, selected_labels):
        counts[a][b] += 1
    fractions = {a: ({b: n / sum(row.values()) for b, n in row.items()} if sum(row.values()) else None) for a, row in counts.items()}
    return {"format": MIGRATION_FORMAT, "species": list(species), "counts": counts, "p_selected_given_true": fractions,
            "meaning": "P(selected as B | true A): per true species; not P(true A | selected as B)"}


def purity(table: dict, composition: dict) -> dict:
    """P(true A | selected as B) = P(sel B | A) pi_A / sum_A' P(sel B | A') pi_A', with the composition stated (BP07)."""
    species = table["species"]
    if not isinstance(composition, dict) or set(composition) != set(species) or not all(_finite(v) and v >= 0 for v in composition.values()) \
            or abs(math.fsum(composition.values()) - 1.0) > SUM_TOLERANCE:
        raise InputError("pid: the composition names every species and sums to 1")
    efficiency = table["p_selected_given_true"]
    if any(efficiency[a] is None for a in species):
        raise InputError("pid: a species without true entries has no P(selected | true)")
    outcomes = list(next(iter(table["counts"].values())))
    out = {}
    for b in outcomes:
        total = math.fsum(efficiency[a][b] * composition[a] for a in species)
        out[b] = {a: (efficiency[a][b] * composition[a] / total if total > 0 else None) for a in species}
    return {"format": MIGRATION_FORMAT, "composition": dict(composition), "p_true_given_selected": out,
            "meaning": "P(true A | selected as B): depends on the stated composition"}
