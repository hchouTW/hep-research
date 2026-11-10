"""Data releases, raw-unit lineage, reads and failure records (Part B sections 2.1, 5.1, 9.2, 9.5, Appendix C.1;
owner calib_data.py).

Phase 0 content (section 17): raw-unit lineage; validation-read and fit-read events, including the registration of
read channels and contract drafts; failure records (pending, final, withdrawn) and their state changes from decision
records; the derivation of the reuse and failure-record inputs of Appendix C.1. Also the release-level checks that
read only metadata or totals: ingestion declarations, sealing, holdout sharing, sample containment and the N_decl,s
equality. The locking-stage checks that need model quantities (rounding, N_exp, n_min, block conversion) are phase 2.

The ledger is the single writer of section 9.5: read events and failure records share one increasing sequence number.
A validation configuration is kappa = (contract hash, plan hash, engine version). Standard library only.
"""
from __future__ import annotations

from core.canonical import canonical_sha256


class DataError(ValueError):
    """A release, read or record the workflow refuses; `code` is a stable name. Exit code 2 (contract error) unless
    stated otherwise by the caller."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def kappa_id(contract_sha256: str, plan_sha256: str, engine_version: str) -> str:
    """The validation configuration kappa of section 9.5 as one identifier."""
    return canonical_sha256({"contract_sha256": contract_sha256, "plan_sha256": plan_sha256,
                             "engine_version": engine_version})


# ------------------------------------------------------------------ lineage (section 9.5 "Decision")
def raw_units(release_sha256: str, releases: dict) -> frozenset | None:
    """Raw data units of a release, followed down its lineage. releases maps a release hash to its metadata
    {"lineage": {"raw_units": [...]}} or {"lineage": {"derived_from": [hashes], "raw_units": [...]}}. A derived
    release's units must lie within its parents'. None when the lineage cannot be confirmed (no lineage, an unknown
    parent, units outside the parents): such data are never opened (rule 0)."""
    meta = releases.get(release_sha256)
    lin = (meta or {}).get("lineage")
    if not isinstance(lin, dict) or not isinstance(lin.get("raw_units"), list) or not lin["raw_units"]:
        return None
    units = frozenset(lin["raw_units"])
    parents = lin.get("derived_from") or []
    if parents:
        pool: set = set()
        for p in parents:
            pu = raw_units(p, releases)
            if pu is None:
                return None
            pool |= pu
        if not units <= pool:
            return None
    return units


def holdout_shares_units(calibration: list[str], validation: list[str], releases: dict) -> dict:
    """Section 9.5 "Holdout must not share events": compare by lineage, at lock and before opening. Returns
    {"confirmed": bool, "shared": [units]}; shared units are a contract error (exit 2, remedy level contract)."""
    cal, val = set(), set()
    for r in calibration:
        u = raw_units(r, releases)
        if u is None:
            return {"confirmed": False, "shared": []}
        cal |= u
    for r in validation:
        u = raw_units(r, releases)
        if u is None:
            return {"confirmed": False, "shared": []}
        val |= u
    return {"confirmed": True, "shared": sorted(cal & val)}


def sample_containment(sample_units, calibration_units, validation_units) -> str:
    """Section 2.1 containment rule for an event sample with calibration observables: 'contained' when every event is
    in the calibration release; 'mixed' (rejected) when it holds events only in the validation release; 'outside'
    (rejected) otherwise."""
    s, c = set(sample_units), set(calibration_units)
    if s <= c:
        return "contained"
    return "mixed" if (s - c) & set(validation_units) else "outside"


def entirely_validation(sample_units, validation_units, calibration_units) -> bool:
    """Whether an event sample belongs entirely to the validation data (section 5.2 clause 9 item 9, D27)."""
    s = set(sample_units)
    return bool(s) and s <= set(validation_units) and not (s & set(calibration_units))


def totals_equal(declared: dict, release_totals: dict) -> list[str]:
    """N_decl,s (or a cross-validation N_decl) declared with an observed basis equals the release's totals, reading
    only the totals (section 2.1). Returns the components that differ or are missing."""
    return sorted(k for k in set(declared) | set(release_totals) if declared.get(k) != release_totals.get(k))


# ------------------------------------------------------------------ ingestion and sealing (sections 2.1, 5.1, 5.2)
INGESTION_DECLARATIONS = ("representation_format", "derivation_relations", "uncertainty_sources",
                          "relative_systematic_correlation", "has_value")
UNCERTAINTY_SOURCES = ("observed", "expected", "systematic")
SEALED_COMPONENTS = ("observed", "expected")      # sealed with the values, provided to no script


def ingestion_findings(release: dict) -> list[dict]:
    """Section 5.2 clause 8: a release must declare each item (a missing one rejects ingestion); only that the
    declarations exist is checked, no value is read."""
    out = []
    decl = release.get("declarations") or {}
    for k in INGESTION_DECLARATIONS:
        if k not in decl:
            out.append({"code": f"ingestion.missing_{k}", "path": f"$.declarations.{k}",
                        "message": f"the release does not declare {k.replace('_', ' ')}; ingestion is rejected"})
    obs = [o["name"] for o in release.get("observables", [])]
    for name in obs:
        if name not in (decl.get("uncertainty_sources") or {}):
            out.append({"code": "ingestion.source_missing", "path": f"$.declarations.uncertainty_sources.{name}",
                        "message": f"observable {name!r} has no declared source for its uncertainty components"})
        else:
            comps = decl["uncertainty_sources"][name]           # {component: source}, e.g. statistical: expected
            bad = set(comps.values() if isinstance(comps, dict) else [None]) - set(UNCERTAINTY_SOURCES)
            if bad:
                out.append({"code": "ingestion.source_unknown", "path": f"$.declarations.uncertainty_sources.{name}",
                            "message": f"unknown sources {sorted(bad)}"})
        if name not in (decl.get("has_value") or {}):
            out.append({"code": "ingestion.has_value_missing", "path": f"$.declarations.has_value.{name}",
                        "message": f"observable {name!r} lacks its 'has a value' declaration"})
    if decl.get("uncertainty_sources") and not release.get("submitter"):
        out.append({"code": "ingestion.submitter_missing", "path": "$.submitter",
                    "message": "the submitter of the source labels is recorded (section 2.1)"})
    return out


def only_observed_statistical(release: dict, calibration_observables) -> list[str]:
    """Section 5.2 clause 9 item 1: calibration observables whose statistical error is only `observed` (cannot be
    recomputed): the contract is rejected."""
    src = (release.get("declarations") or {}).get("uncertainty_sources") or {}
    return sorted(o for o in calibration_observables if src.get(o, {}).get("statistical") == "observed")


def provide(release: dict, component: str, opened: bool, role: str) -> object:
    """The one provider of release content to scripts (section 5.1, 2.1): `systematic` is readable; `observed` and
    `expected` components are sealed and provided to no script; validation values only after opening."""
    if component in SEALED_COMPONENTS:
        raise DataError("sealed.component", f"the {component} uncertainty component is sealed with the observed values "
                        "and is provided to no script (section 2.1)")
    if component == "values" and role == "validation" and not opened:
        raise DataError("sealed.not_opened", "validation values are provided only after the contract is locked and "
                        "the validation data are opened")
    return release["content"][component]


# ------------------------------------------------------------------ the ledger (section 9.5)
FAILURE_STATES = ("pending", "final", "withdrawn")
DECISION_OUTCOMES = ("pass", "fail", "abandoned", "no-testable-direction")


class Ledger:
    """Read events, failure records and contract drafts of one installation, written by calib_data alone. State is a
    plain dict (JSON-serialisable): {"seq", "events", "failure_records", "drafts"}."""

    def __init__(self, state: dict | None = None):
        self.state = state or {"schema": "calibration-ledger/1", "seq": 0, "events": [], "failure_records": [],
                               "drafts": {}}

    # -- sequence and channels
    def _next(self) -> int:
        self.state["seq"] += 1
        return self.state["seq"]

    def register_draft(self, series: str) -> dict:
        """Register a new draft of a contract series (calib_data is the sole registrar); returns its read channel."""
        n = self.state["drafts"].get(series, 0) + 1
        self.state["drafts"][series] = n
        return {"series": series, "draft": n}

    def _channel(self, channel: dict) -> dict:
        if set(channel) == {"contract_sha256"}:
            return dict(channel)
        if set(channel) == {"series", "draft"} and channel["draft"] <= self.state["drafts"].get(channel["series"], 0):
            return dict(channel)
        if set(channel) == {"series"}:                 # first provision for a new draft: register it
            return self.register_draft(channel["series"])
        raise DataError("read.channel", "a read goes through a locked contract (its hash) or a registered contract "
                        "draft (series and draft number)")

    # -- reads
    def fit_read(self, release_sha256: str, units, channel: dict, kappa: str | None = None) -> int:
        """Record a fit read (fit, design, A0 preflight or exploration) of a release on its raw units."""
        ch, seq = self._channel(channel), self._next()
        for u in sorted(units):
            self.state["events"].append({"unit": u, "release_sha256": release_sha256, "channel": ch, "kappa": kappa,
                                         "kind": "fit", "seq": seq})
        return seq

    def open_validation(self, kappa: str, release_sha256: str, validation_units, calibration_units,
                        channel: dict) -> int:
        """At opening (holdout) or the first T_cv (cross-validation): at one sequence number, record the validation
        reads on the validation raw units and write pending failure records on every raw unit of the calibration
        data. Refused when the lineage is unconfirmed (units None): the data are not opened."""
        if validation_units is None or calibration_units is None:
            raise DataError("open.lineage_unconfirmed", "lineage not confirmed: the validation data are not opened, "
                            "no read and no record (section 9.5)")
        if any(e["kappa"] == kappa and e["kind"] == "validation" for e in self.state["events"]):
            raise DataError("open.already_opened", "this kappa has already opened its validation data")
        ch, seq = self._channel(channel), self._next()
        for u in sorted(validation_units):
            self.state["events"].append({"unit": u, "release_sha256": release_sha256, "channel": ch, "kappa": kappa,
                                         "kind": "validation", "seq": seq})
        for u in sorted(calibration_units):
            self.state["failure_records"].append({"unit": u, "kappa": kappa, "seq": seq, "status": "pending"})
        return seq

    def apply_decision(self, decision: dict) -> str:
        """Change kappa's pending records from a decision record of calib_validate (a hand-written stub in phase 0):
        pass -> withdrawn; fail -> final; abandoned -> final; no-testable-direction (k = 0) -> withdrawn, or final
        when the data-side constraint check (including "has a value") was triggered. Records only change state, never
        disappear; a record no longer pending is not changed."""
        kappa, outcome = decision["kappa"], decision["outcome"]
        if outcome not in DECISION_OUTCOMES:
            raise DataError("decision.outcome", f"decision outcome must be one of {list(DECISION_OUTCOMES)}")
        triggered = bool(decision.get("data_side_check_triggered"))
        new = "final" if (outcome in ("fail", "abandoned") or triggered) else "withdrawn"
        recs = [r for r in self.state["failure_records"] if r["kappa"] == kappa]
        if not recs:
            raise DataError("decision.no_records", "no failure record for this kappa: it has not opened")
        if any(r["status"] != "pending" for r in recs):
            raise DataError("decision.not_pending", "the records of this kappa are no longer pending; their state does "
                            "not change again")
        for r in recs:
            r["status"] = new
        return new

    # -- derived inputs of Appendix C.1
    def first_validation_read(self, unit: str) -> dict | None:
        reads = [e for e in self.state["events"] if e["unit"] == unit and e["kind"] == "validation"]
        return min(reads, key=lambda e: e["seq"]) if reads else None

    def opening_seq(self, kappa: str) -> int | None:
        s = [e["seq"] for e in self.state["events"] if e["kappa"] == kappa and e["kind"] == "validation"]
        return min(s) if s else None

    def reuse_input(self, kappa: str, validation_units) -> str:
        """The reuse input (Appendix C.1, "Values of the reuse input"): `validation` when for some unit read by
        kappa's validation the first validation read belongs to another kappa; else `fit` when some validation unit
        has a read (any kind, any channel; none is exempt under the current rules) before kappa's first validation
        read (before it opens: any read so far); else `none`. `fit-pending` is unreachable and never derived."""
        at = self.opening_seq(kappa)
        for u in validation_units:
            fv = self.first_validation_read(u)
            if fv is not None and fv["kappa"] != kappa and (at is None or fv["seq"] <= at):
                return "validation"
        for u in validation_units:
            for e in self.state["events"]:
                if e["unit"] == u and (at is None or e["seq"] < at) and not (
                        e["kind"] == "validation" and e["kappa"] == kappa):
                    return "fit"
        return "none"

    def failure_record_input(self, kappa: str, calibration_units) -> str:
        """The failure-record input (Appendix C.1): failure records of other kappas on the calibration raw units that
        are earlier than kappa's first validation read (all existing ones before it; an equal sequence number counts
        as earlier). final if any is final, else pending if any is pending, else none (withdrawn ones do not
        count)."""
        at = self.opening_seq(kappa)
        units = set(calibration_units)
        states = {r["status"] for r in self.state["failure_records"]
                  if r["unit"] in units and r["kappa"] != kappa and (at is None or r["seq"] <= at)}
        return "final" if "final" in states else "pending" if "pending" in states else "none"

    def waiting_records(self, kappa: str, calibration_units) -> list[dict]:
        """The pending records of other kappas this result waits for (unit, kappa, seq; section 10.1)."""
        at = self.opening_seq(kappa)
        units = set(calibration_units)
        return [dict(r) for r in self.state["failure_records"] if r["unit"] in units and r["kappa"] != kappa
                and r["status"] == "pending" and (at is None or r["seq"] <= at)]

    def concurrent_configurations(self, kappa: str, calibration_units) -> list[dict]:
        """Validation configurations with validation reads on the same calibration raw units, with their failure
        records (report only, section 9.5 "Design trade-off")."""
        units = set(calibration_units)
        kappas = sorted({e["kappa"] for e in self.state["events"] if e["kind"] == "validation" and e["unit"] in units
                         and e["kappa"] != kappa} | {r["kappa"] for r in self.state["failure_records"]
                                                     if r["unit"] in units and r["kappa"] != kappa})
        return [{"kappa": k, "failure_records": sorted({r["status"] for r in self.state["failure_records"]
                                                        if r["kappa"] == k and r["unit"] in units})} for k in kappas]

    def c1_inputs(self, kappa: str, vmode: str, validation_units, calibration_units,
                  has_validation_read: bool = True) -> dict:
        """validation_data_reuse and earlier_failure_record for Appendix C. A kappa without a validation read (k0 = 0
        before opening, lineage unconfirmed, outcome already determined, ...) takes none for both (C.1)."""
        if not has_validation_read or vmode == "none":
            return {"validation_data_reuse": "none", "earlier_failure_record": "none"}
        return {"validation_data_reuse": self.reuse_input(kappa, validation_units),
                "earlier_failure_record": self.failure_record_input(kappa, calibration_units)}
