"""The contract checker (Part B section 5.2; owner calib_contract.py check).

Phase 0 content (section 17): the contract rules of section 5.2 that need no model quantity. Decisions on the DAG and
injection-point splitting call core.calibration.chain, upstream roles call core.calibration.deps, and decisions that
read release metadata, lineage or totals call core.calibration.data. The locking-stage checks that need quantities
produced by the model (rounding negligibility, N_exp of absolute count shapes, n_min, block-conversion conditions,
sigma_i^(0) > 0, the standardized SVD of N_d and N_d,c, the N_d,c declaration check) are added in phase 2; the
phase-0 check only confirms that their declarations exist and lists them under "deferred". The g4sim model identity
(the five masked hashes of section 5.1) is added in phase 3 (section 17, g4sim preconditions).

check() returns {"status": "accepted"|"rejected", "findings": [...], "deferred": [...]}; a rejected contract produces
no result (exit 2). Standard library only.
"""
from __future__ import annotations

import math

from core.calibration import data_release as data
from core.calibration import chain, deps
from core.canonical import canonical_sha256

ROLES = ("calibration", "validation", "measurement")
PARAMETER_ROLES = ("theta", "phi", "psi")
VMODES = ("none", "holdout", "cross-validation")
# Section 2.1 "Link functions": the link each range takes (the functional class only gives a default).
LINKS_FOR_RANGE = {"positive": {"log"}, "signed": {"identity"}, "unit-interval": {"logit"},
                   "correlation": {"fisher-z"}, "simplex": {"alr", "ilr"}}
BLOCKS = ("gaussian", "binomial", "poisson")
ENGINE_BLOCKS = frozenset({"gaussian"})       # block types this engine version supports (non-Gaussian: phase 2)
SHAPE_ESTIMATOR = "binned-fractions"           # estimator of a normalized distribution (section 5.2 clause 3)
SUMMARY_ESTIMATORS = ("mean", "efficiency", "ratio", "width", "quantile", "gaussian-summary")
VALUE_CONVENTIONS = ("zero_events", "one_event", "zero_denominator")
PD_KERNELS = frozenset({"squared-exponential", "exponential", "matern-1/2", "matern-3/2", "matern-5/2",
                        "rational-quadratic", "identity"})
FORBIDDEN_KEYS = frozenset({"observed_value", "observed_values", "data_values", "observed_counts", "measured_value",
                            "measured_values", "observed_totals"})
DEFERRED = [
    "clause 9 item 2: rounding negligibility at the evaluation points (phase 2, calib_data.py)",
    "clause 9 item 3: recomputation at the fit point (calib_fit.py, phase 2)",
    "clause 9 item 4: N_exp >= 10 of absolute count validation shapes (phase 2, calib_data.py)",
    "clause 9 item 8: the value conventions satisfy the declared N_d (phase 2)",
    "clause 9 item 12: n_min and block-conversion conditions at the evaluation points (phase 2, calib_data.py)",
    "clause 9 item 13: sigma_i^(0) > 0 (phase 2)",
    "clause 6 item 2 and clause 7 item 4: the N_d,c and N_d decisions in standardized V_G coordinates (phase 2)",
    "clause 1 item 2: the five g4sim model identity items (phase 3)",
]


class _Findings(list):
    def add(self, code, path, message):
        self.append({"code": code, "path": path, "message": message})


def lock_hash(contract: dict) -> str:
    """The contract hash locked before the validation data are opened (section 5.1)."""
    return canonical_sha256(contract)


def _scan_values(value, path, out: _Findings):
    """The contract contains no data values (section 5.1): keys that hold observed values are refused anywhere."""
    if isinstance(value, dict):
        for k, v in value.items():
            if k in FORBIDDEN_KEYS:
                out.add("contract.data_values", f"{path}.{k}", "the contract contains no data values (section 5.1); "
                        "observed values belong to the data release")
            _scan_values(v, f"{path}.{k}", out)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _scan_values(v, f"{path}[{i}]", out)


def _cholesky_ok(m) -> bool:
    n = len(m)
    if any(len(r) != n for r in m) or any(abs(m[i][j] - m[j][i]) > 1e-12 * (1 + abs(m[i][j]))
                                          for i in range(n) for j in range(n)):
        return False
    low = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = m[i][j] - sum(low[i][k] * low[j][k] for k in range(j))
            if i == j:
                if s <= 0 or not math.isfinite(s):
                    return False
                low[i][i] = math.sqrt(s)
            else:
                low[i][j] = s / low[j][j]
    return True


def _parameters(c, out):
    for i, p in enumerate(c.get("parameters", [])):
        path = f"$.parameters[{i}]"
        if p.get("role") not in PARAMETER_ROLES:
            out.add("parameters.role", path, f"parameter role must be one of {list(PARAMETER_ROLES)}")
        if p.get("role") in ("theta", "phi"):
            pb, sb = p.get("physical_bounds"), p.get("sampling_bounds")
            if not (isinstance(pb, list) and len(pb) == 2 and isinstance(sb, list) and len(sb) == 2):
                out.add("parameters.bounds", path, "physical bounds and sampling bounds are declared separately")
        if p.get("role") == "phi" and not p.get("source"):
            out.add("parameters.phi_source", path, "an externally constrained parameter phi carries its source")
        if p.get("role") == "psi" and p.get("uncertainty") != "negligible":
            out.add("parameters.psi_uncertainty", path, "a conditioning parameter psi with a non-negligible (or "
                    "undeclared) uncertainty is listed as phi instead (section 2.2; criterion of D37)")


def _models(c, out):
    m = c.get("models") or {}
    enum = {x["id"] for x in m.get("enumerated", [])}
    absb = {x["id"] for x in m.get("absorbed", [])}
    for both in sorted(enum & absb):
        out.add("models.enumerated_and_absorbed", "$.models", f"model {both!r} is both enumerated and absorbed")
    lists = {x.get("physics_list") for x in m.get("enumerated", []) + m.get("absorbed", [])
             if x.get("physics_list")}
    lists |= {a.get("physics_list") for a in (c.get("validation") or {}).get("alternatives", []) if a.get("physics_list")}
    if len(lists) > 1:
        confirmed = {frozenset(x.get("physics_lists", [])) for x in m.get("physics_list_confirmations", [])
                     if x.get("record")}
        for a in sorted(lists):
            for b in sorted(lists):
                if a < b and frozenset({a, b}) not in confirmed:
                    out.add("models.physics_list_unconfirmed", "$.models.physics_list_confirmations",
                            f"physics lists {a!r} and {b!r} are used as different models without a record that they "
                            "use different models in the relevant particle and energy range (clause 1 item 3)")
    if c.get("simulator") == "g4sim":
        src = (c.get("source") or {}).get("density")
        if src == "external":
            out.add("source.external", "$.source", "an external event source is always rejected (clause 2)")
        elif src != "analytic":
            out.add("source.density", "$.source", "with g4sim the source of node 0 is density: analytic (clause 2)")


def _observables(c, out, samples):
    seen: dict[str, str] = {}
    shapes = {o["name"]: o for o in c.get("observables", []) if o.get("estimator") == SHAPE_ESTIMATOR}
    for i, o in enumerate(c.get("observables", [])):
        path = f"$.observables[{i}]"
        name, role = o.get("name"), o.get("role")
        if name in seen:
            out.add("observables.role_overlap", path, f"observable {name!r} declared twice (roles {seen[name]!r} and "
                    f"{role!r}); calibration, validation and measurement sets are mutually exclusive")
        seen[name] = role
        if role not in ROLES:
            out.add("observables.role", path, f"observable role must be one of {list(ROLES)}")
        if (o.get("binning") or {}).get("variable_level") != "reconstructed":
            out.add("observables.true_binning", path, "binning is in the reconstructed control variable; the "
                    "simulation side must not bin by the true value (section 3.3)")
        block = o.get("block")
        if block not in BLOCKS:
            out.add("observables.block", path, f"block must be one of {list(BLOCKS)}")
        elif block not in ENGINE_BLOCKS:
            out.add("validation.block_unsupported", path, f"a {block} block needs the engine of phase 2; this engine "
                    "version supports only Gaussian blocks (clause 10 item 3, section 6.7)")
        rng, link = o.get("range"), o.get("link")
        if o.get("estimator") == SHAPE_ESTIMATOR:
            _vector(o, path, out, shapes)
        else:
            if o.get("bin_of"):
                out.add("observables.shape_bin_as_scalar", path, "bins of a normalized distribution are not declared "
                        "as scalar observables (clause 3 item 4)")
            if rng not in LINKS_FOR_RANGE or rng == "simplex":
                out.add("observables.range", path, "a scalar observable declares its range (positive, signed, "
                        "unit-interval, correlation)")
            elif link not in LINKS_FOR_RANGE[rng]:
                out.add("observables.link_range", path, f"link {link!r} does not match the range {rng!r} (section "
                        f"2.1: {sorted(LINKS_FOR_RANGE[rng])})")
            if o.get("estimator") in SUMMARY_ESTIMATORS:
                conv = (o.get("value_conventions") or {})
                missing = [k for k in VALUE_CONVENTIONS if k not in conv]
                if missing:
                    out.add("observables.value_conventions", path, f"a summary-statistic estimator states its value "
                            f"conventions for {missing} (clause 9 item 7)")
    # block rules (section 2.1): binomial and Poisson blocks share no events with other observables; observables that
    # share events are Gaussian summary statistics
    by_sample: dict[str, list] = {}
    for o in c.get("observables", []):
        if o.get("sample"):
            by_sample.setdefault(o["sample"], []).append(o)
    for s, obs in sorted(by_sample.items()):
        if len(obs) > 1:
            for o in obs:
                if o.get("block") != "gaussian" or (o.get("estimator") == SHAPE_ESTIMATOR
                                                    and (o.get("vector") or {}).get("data_side") != "gaussian-summary"):
                    out.add("observables.block_rule", f"$.observables[{o['name']}]", f"observables sharing the events of "
                            f"sample {s!r} are converted to Gaussian summary statistics; binomial and Poisson blocks "
                            "share no events (section 2.1 block rules)")
        if s not in samples:
            out.add("observables.sample_undeclared", "$.event_samples", f"sample {s!r} is not declared")


def _vector(o, path, out, shapes):
    v = o.get("vector") or {}
    k, bins = v.get("K"), v.get("bins") or []
    red = o.get("redeclared_from")
    if o.get("link") == "logit":
        out.add("observables.shape_logit", path, "logit on the components of a normalized distribution is rejected; "
                "use alr or ilr (clause 3 item 4)")
    elif o.get("link") not in ("alr", "ilr"):
        out.add("observables.shape_link", path, "a normalized shape takes the vector link alr or ilr")
    if not isinstance(k, int) or len(bins) != k:
        out.add("observables.shape_bins", path, "a vector observable declares K and all K bins (only K-1 bins declared "
                "is rejected, clause 3 item 4)")
    if o.get("link") == "alr" and v.get("reference_category") not in bins:
        out.add("observables.alr_reference", path, "alr declares its reference category among the bins")
    if o.get("link") == "ilr" and not v.get("contrast_basis"):
        out.add("observables.ilr_basis", path, "ilr declares its contrast basis")
    side = v.get("data_side")
    if side not in ("count", "gaussian-summary"):
        out.add("observables.data_side", path, "data-side representation: count likelihood or Gaussian summary")
    elif side == "gaussian-summary" and not v.get("merging_rule"):
        out.add("observables.merging_rule", path, "a Gaussian-summary shape declares its merging rule (section 2.1)")
    elif side == "gaussian-summary" and (v.get("merging_rule") or {}).get("defined_by") == "observed-counts":
        out.add("observables.merging_observed", path, "a merging rule is not defined by observed counts")
    if side == "count" and o.get("block") != "poisson":
        out.add("observables.count_block", path, "a shape entering through the count likelihood is a Poisson block "
                "(section 2.1)")
    cls = o.get("shape_class")
    if red is not None:
        # the sub-shape's class follows its parent (section 9.2, D5): resolve the parent declared in the contract, or
        # the parent class the redeclaration states (the parent may be replaced by the sub-shape); the two must agree
        parent = shapes.get(red.get("shape"))
        p_cls = red.get("parent_shape_class") if parent is None else parent.get("shape_class")
        p_side = red.get("parent_data_side") if parent is None else (parent.get("vector") or {}).get("data_side")
        if parent is not None and red.get("parent_shape_class") not in (None, p_cls):
            out.add("observables.subshape_parent_mismatch", path, "the redeclared parent class differs from the "
                    "declared parent shape")
        if p_cls is None:
            out.add("observables.subshape_parent", path, "a redeclared sub-shape names its parent shape and the "
                    "parent's class (declared, or stated in redeclared_from)")
        elif p_cls == "free-omega" and p_side == "count":
            if cls != "free-omega":
                out.add("observables.subshape_class", path, "the sub-shape of a free-omega count shape is a new "
                        "free-omega shape (D5, approval A6)")
            cls = "free-omega"
        if isinstance(k, int) and k < 2 and cls != "absolute":
            out.add("observables.subshape_k1", path, "a redeclared shape conditioned on the total or in alr/ilr with "
                    "K' = 1 has no link coordinate: leave the whole shape unused (D38)")
    if (o.get("role") == "validation" or red is not None) and cls == "free-omega" and side == "count":
        for code in data.n_decl_findings(o.get("N_decl"), sub_shape=red is not None):
            out.add(code, path, "a free-omega count shape declares N_decl with a recorded basis and N_decl >= 10 "
                    "(section 2.1; clause 9 item 4" + ("; a sub-shape after exclusion is a new free-omega shape, D5"
                                                       if red is not None else "") + ")")


def _samples(c, out, releases):
    out_map = {}
    cal_rel = (c.get("data") or {}).get("calibration_releases", [])
    val_rel = (c.get("data") or {}).get("validation_releases", [])
    cal_units = set().union(*[data.raw_units(r, releases) or set() for r in cal_rel]) if cal_rel else set()
    val_units = set().union(*[data.raw_units(r, releases) or set() for r in val_rel]) if val_rel else set()
    obs_by_sample: dict[str, set] = {}
    for o in c.get("observables", []):
        if o.get("sample"):
            obs_by_sample.setdefault(o["sample"], set()).add(o.get("role"))
    sample_units = {}
    for r in cal_rel + val_rel:
        for sid, s in ((releases.get(r) or {}).get("samples") or {}).items():
            sample_units.setdefault(sid, set()).update(s.get("raw_units", []))
    for i, s in enumerate(c.get("event_samples", [])):
        path = f"$.event_samples[{i}]"
        sid = s.get("id")
        out_map[sid] = s
        roles = obs_by_sample.get(sid, set())
        units = sample_units.get(sid)
        if s.get("normalization") == "absolute":
            if (s.get("sim_absolute_normalization") or {}).get("value") != "yes":
                out.add("samples.sim_absolute_normalization", path, "an absolute count shape enters only when the "
                        "simulation sample has absolute normalization (missing means no; clause 9 item 5)")
        elif s.get("normalization") == "free":
            for j, comp in enumerate(s.get("components", [])):
                if not comp.get("basis") or "N_decl" not in comp:
                    out.add("samples.n_decl_s", f"{path}.components[{j}]", "a free-normalization sample declares "
                            "N_decl,s and its basis for each component (clause 9 item 11)")
        else:
            out.add("samples.normalization", path, "sample normalization is free or absolute")
        if "calibration" in roles:
            if units is None:
                out.add("samples.lineage", path, "the sample's events are not traced to raw units")
            else:
                verdict = data.sample_containment(units, cal_units, val_units)
                if verdict != "contained":
                    out.add("samples.not_contained", path, f"a sample with calibration observables lies entirely in "
                            f"the calibration release ({verdict}; clause 9 item 6)")
            if s.get("normalization") == "free":
                totals = ((releases.get(cal_rel[0]) or {}).get("samples") or {}).get(sid, {}).get("totals") if cal_rel else None
                declared = {comp.get("id"): comp.get("N_decl") for comp in s.get("components", [])
                            if comp.get("basis") == "observed"}
                if declared and totals is not None:
                    diff = data.totals_equal(declared, {k: v for k, v in totals.items() if k in declared})
                    if diff:
                        out.add("samples.n_decl_s_unequal", path, f"N_decl,s with an observed basis differs from the "
                                f"release totals for {diff} (clause 9 item 11)")
        if units is not None and data.entirely_validation(units, val_units, cal_units):
            for rel in (c.get("validation") or {}).get("exact_relations", []):
                if rel.get("sample") == sid:
                    used = {o["name"] for o in c.get("observables", []) if o.get("role") == "validation"}
                    if set(rel["observables"]) <= used:
                        out.add("validation.exact_relation_all_used", path, "all observables of an exact relation "
                                "determined by the observed component totals are used in a sample entirely in the "
                                "validation data (clause 9 item 9, D27)")
    return out_map


def _validation(c, out, releases):
    v = c.get("validation") or {}
    mode = v.get("mode")
    if mode not in VMODES:
        out.add("validation.mode", "$.validation.mode", f"validation mode must be one of {list(VMODES)}")
        return
    for key, needed in (("N_dc", True), ("N_d", mode != "none")):
        if not needed:
            continue
        if not isinstance(v.get(key), list):
            out.add(f"validation.{key}_missing", f"$.validation.{key}", f"{key} is declared (empty when there is "
                    "no such constraint; clauses 6, 7)")
            continue
        for j, item in enumerate(v[key]):
            if "c" not in item or not item.get("construction") or not isinstance(item.get("n"), dict):
                out.add(f"validation.{key}_item", f"$.validation.{key}[{j}]", "each constraint writes n, the constant "
                        "c of n^T y = c and its construction (clause 7 item 3, D66)")
    cal_rel, val_rel = (c.get("data") or {}).get("calibration_releases", []), (c.get("data") or {}).get(
        "validation_releases", [])
    # the release that holds the residuals: the validation release (holdout) or the calibration release (CV)
    reg = val_rel if mode == "holdout" else cal_rel if mode == "cross-validation" else []
    registered: set[str] = set()
    has_value: dict[str, bool] = {}
    for r in reg:
        meta = releases.get(r) or {}
        registered |= {o["name"] for o in meta.get("observables", [])}
        has_value.update((meta.get("declarations") or {}).get("has_value") or {})
    vroles = ("validation",) if mode == "holdout" else ("validation", "calibration")
    used_v = {o["name"] for o in c.get("observables", []) if o.get("role") in vroles}
    if mode != "none":
        unused = v.get("unused")
        for f in data.untestable_findings(used_v, unused if isinstance(unused, list) else [], has_value):
            if f["code"] == "validation.untestable_used":
                out.add(f["code"], "$.observables", f"observable {f['observable']!r} has no value (untestable, section "
                        "9.5) and must be excluded from the observables used for validation (clause 7 item 2)")
            else:
                out.add(f["code"], f"$.validation.unused[{f['index']}]", f"{f['observable']!r} is declared to have a "
                        "value in the release but listed as untestable")
        if not isinstance(unused, list):
            out.add("validation.unused_missing", "$.validation.unused", "the unused-observables list is declared "
                    "(clause 7 item 6)")
        else:
            listed = set()
            for j, u in enumerate(unused):
                listed.add(u.get("observable"))
                if not u.get("reason") or not u.get("clause"):
                    out.add("validation.unused_reason", f"$.validation.unused[{j}]", "each unused observable states "
                            "its reason and the clause it relies on")
            if reg and listed != registered - used_v:
                out.add("validation.unused_mismatch", "$.validation.unused", f"the list must be exactly the registered "
                        f"observables minus those used: missing {sorted(registered - used_v - listed)}, extra "
                        f"{sorted(listed - (registered - used_v))}")
        alts = v.get("alternatives") or []
        if not alts:
            out.add("validation.no_alternative", "$.validation.alternatives", "at least one alternative hypothesis "
                    "when the mode is not none (clause 10 item 2, D32)")
        for j, a in enumerate(alts):
            if a.get("kind") != "simulation-setting":
                out.add("validation.alternative_shift", f"$.validation.alternatives[{j}]", "alternative hypotheses are "
                        "simulation settings only; a parameter-shift form is always rejected (clause 10 item 3)")
    if mode == "holdout" and cal_rel and val_rel:
        sh = data.holdout_shares_units(cal_rel, val_rel, releases)
        if sh["confirmed"] and sh["shared"]:
            out.add("validation.holdout_shares_units", "$.data", f"the calibration and validation releases of a "
                    f"holdout share raw units {sh['shared'][:5]}; switch to cross-validation or to releases that share "
                    "no events (clause 9 item 10)")
    for r in cal_rel:
        cal_obs = [o["name"] for o in c.get("observables", []) if o.get("role") == "calibration"]
        bad = data.only_observed_statistical(releases.get(r) or {}, cal_obs)
        if bad:
            out.add("validation.observed_only", "$.observables", f"calibration observables {bad} have only an "
                    "observed statistical error, which cannot be recomputed (clause 9 item 1)")
    md = c.get("model_discrepancy") or {}
    if md.get("form") == "inferred" and mode != "holdout":
        out.add("model_discrepancy.inferred_mode", "$.model_discrepancy", "the inferred form of V_model is combined "
                "only with holdout validation")
    ker = md.get("kernel")
    if ker is not None:
        if isinstance(ker, dict) and ker.get("type") == "matrix":
            if not _cholesky_ok(ker.get("matrix") or [[]]):
                out.add("model_discrepancy.kernel_not_pd", "$.model_discrepancy.kernel", "the kernel is not positive "
                        "definite")
        elif not (isinstance(ker, dict) and ker.get("type") in PD_KERNELS):
            out.add("model_discrepancy.kernel_not_pd", "$.model_discrepancy.kernel", "the kernel function must be "
                    f"positive definite: a matrix, or one of {sorted(PD_KERNELS)}")
    if (c.get("numerics") or {}).get("precision") != "double":
        out.add("validation.precision", "$.numerics.precision", "predictions are computed in double precision "
                "(clause 10 item 1)")


def _references(c, out):
    phis = {p["name"] for p in c.get("parameters", []) if p.get("role") == "phi"}
    for i, r in enumerate(c.get("references", [])):
        if r.get("type") == "mid-chain-injection":
            conv = r.get("conversion")
            if not isinstance(conv, dict) or not conv.get("relation"):
                out.add("references.conversion_missing", f"$.references[{i}]", "a mid-chain injected reference "
                        "declares its conversion relation to the physical quantity (clause 4 item 1)")
            else:
                for par in conv.get("parameters", []):
                    if par not in phis:
                        out.add("references.conversion_phi", f"$.references[{i}]", f"conversion parameter {par!r} is "
                                "listed as phi with its source")


PSI_BOUND = 0.1                                # D37 (approval A7): the class-discretization bound of section 5.4


def psi_findings(contract: dict, design: dict) -> list[dict]:
    """D37 (approval A7): a conditioning parameter psi whose effect on theta-hat, propagated via the design-stage A
    (design['psi_effect'][psi] = A_theta (d mu / d psi) sigma_psi), exceeds 0.1 sigma_tot^design for some theta_i
    must be listed as phi. A psi with no declared uncertainty (constraint sigma) cannot be judged."""
    out = []
    if not isinstance(design, dict):
        raise ValueError("the design is a JSON object (calib_design.py linearize output)")
    sig = [float(x) for x in design.get("sigma_tot") or []]
    names = list(design.get("theta") or [])
    effects = design.get("psi_effect") or {}
    if not isinstance(effects, dict):
        raise ValueError("design.psi_effect is an object {psi: [effect per theta]}")
    for i, p in enumerate(contract.get("parameters", [])):
        if p.get("role") != "psi":
            continue
        path = f"$.parameters[{i}]"
        if not (p.get("constraint") or {}).get("sigma"):
            out.append({"code": "parameters.psi_sigma", "path": path, "message": f"psi {p['name']!r} declares no "
                        "uncertainty (constraint.sigma): the D37 bound cannot be computed"})
            continue
        eff = effects.get(p["name"])
        if eff is None:
            out.append({"code": "parameters.psi_not_evaluated", "path": path, "message": f"the design gives no "
                        f"effect of psi {p['name']!r} (calib_design.py linearize)"})
            continue
        if not isinstance(eff, list):
            raise ValueError(f"design.psi_effect[{p['name']!r}] is a list, one effect per theta")
        ratios = [abs(float(e)) / float(s) for e, s in zip(eff, sig)]
        worst = max(range(len(ratios)), key=ratios.__getitem__) if ratios else None
        if worst is not None and ratios[worst] > PSI_BOUND:
            out.append({"code": "parameters.psi_not_negligible", "path": path, "message": f"psi {p['name']!r} moves "
                        f"{names[worst]} by {ratios[worst]:.3g} sigma_tot^design > {PSI_BOUND} via A: list it as phi "
                        "(section 2.2; D37, approval A7)"})
    return out


def check(contract: dict, releases: dict | None = None, series_graph: dict | None = None,
          design: dict | None = None) -> dict:
    """Section 5.2 in phase-0 scope, and the D37 rule of phase 1 when the design-stage linearization is given
    (design: theta, sigma_tot, psi_effect, from calib_design.py linearize). releases maps release hashes to their
    metadata (calib_data's view: lineage, samples, observables, declarations, totals); series_graph maps a contract
    series to the series of its upstream results (calib_deps), for the cycle check."""
    out = _Findings()
    releases = releases or {}
    if not isinstance(contract, dict):
        return {"status": "rejected", "findings": [{"code": "contract.shape", "path": "$", "message": "not an object"}],
                "deferred": DEFERRED}
    _scan_values(contract, "$", out)
    for f in chain.check_graph(contract.get("stage_graph")):
        out.append(f)
    if not any(f["code"].startswith("graph.") for f in out):
        for f in chain.check_references(contract["stage_graph"], contract.get("references", [])):
            out.append(f)
        nodes = chain.node_index(contract["stage_graph"])
        for i, p in enumerate(contract.get("parameters", [])):
            bad = [n for n in p.get("nodes", []) if n not in nodes]
            if bad or not p.get("nodes"):
                out.add("parameters.nodes", f"$.parameters[{i}]", f"a parameter acts on declared nodes, not {bad}")
    _references(contract, out)
    _parameters(contract, out)
    _models(contract, out)
    samples = _samples(contract, out, releases)
    _observables(contract, out, samples)
    est = contract.get("estimators") or {}
    if est.get("shared_implementation") is not True:
        out.add("estimators.shared", "$.estimators", "data and simulation share the same estimator implementation")
    if est.get("uses_truth") is not False:
        out.add("estimators.truth", "$.estimators", "estimators must not use true values unavailable in data")
    for f in deps.check_upstream_entries(contract.get("upstream", [])):
        out.append(f)
    if series_graph is not None and contract.get("series"):
        g = {k: list(v) for k, v in series_graph.items()}
        g.setdefault(contract["series"], [])
        cyc = deps.find_cycle(g)
        if cyc:
            out.add("upstream.cycle", "$.upstream", "circular dependency between contract series " + " -> ".join(cyc)
                    + "; merge into one joint fit (section 10.3)")
    _validation(contract, out, releases)
    for k in ("acceptance", "intended_use", "scope"):
        if not contract.get(k):
            out.add(f"contract.{k}_missing", f"$.{k}", f"{k} is declared and locked with the contract hash")
    a0 = contract.get("a0_summary")
    if a0 is not None and set(a0) - {"unreachable_thresholds"}:
        out.add("contract.a0_values", "$.a0_summary", "the A0 summary records only which thresholds are unreachable")
    flags = []
    if (contract.get("validation") or {}).get("mode") == "cross-validation":
        roles: dict[str, set] = {}
        for o in contract.get("observables", []):
            if o.get("sample"):
                roles.setdefault(o["sample"], set()).add(o.get("role"))
        if any({"calibration", "validation"} <= r for r in roles.values()):
            flags.append("cv")       # validation observables share events with calibration ones (section 2.1)
    deferred = list(DEFERRED)
    if design is not None:
        out.extend(psi_findings(contract, design))
    else:
        for i, p in enumerate(contract.get("parameters", [])):
            if p.get("role") == "psi":                 # D37 cannot be decided without A: never accepted unchecked
                out.add("parameters.psi_needs_design", f"$.parameters[{i}]", f"psi {p['name']!r}: the D37 bound needs "
                        "the design-stage A (check --design, from calib_design.py linearize; approval A7)")
    return {"status": "rejected" if out else "accepted", "findings": list(out), "deferred": deferred,
            "result_flags": flags}
