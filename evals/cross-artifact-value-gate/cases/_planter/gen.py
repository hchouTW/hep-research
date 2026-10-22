#!/usr/bin/env python3
"""Generate the planted cases into the kit's out/ folder."""
import copy
import json
import re
import shutil
import sys
from pathlib import Path

KIT = Path(sys.argv[1])
OUT = KIT / "out"
RUN = (KIT / "run.py").read_text(encoding="utf-8")
RECIPE = json.loads((KIT / "recipe.json").read_text(encoding="utf-8"))
CONTEXT = json.loads((KIT / "context.json").read_text(encoding="utf-8"))
ALL_INST = ["proton-p1", "proton-p2", "helium-p1", "helium-p2"]
ALL_FLUX = ["flux-proton-p1", "flux-proton-p2", "flux-helium-p1", "flux-helium-p2"]
RATIOS = ["ratio-p1", "ratio-p2"]


def edit(text, pairs):
    for old, new in pairs:
        if isinstance(old, re.Pattern):
            text, n = old.subn(new, text)
            assert n > 0, old.pattern
            continue
        n = text.count(old)
        assert n == 1, f"{n} matches for: {old[:80]!r}"
        text = text.replace(old, new)
    return text


def case(cid, kind, category, summary, code_change, description_change, affected, run_edits,
         recipe=None, context=None):
    d = OUT / cid
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "run.py").write_text(edit(RUN, run_edits), encoding="utf-8")
    if recipe is not None:
        r = copy.deepcopy(RECIPE)
        recipe(r)
        (d / "recipe.json").write_text(json.dumps(r, indent=1) + "\n", encoding="utf-8")
    if context is not None:
        c = copy.deepcopy(CONTEXT)
        context(c)
        (d / "context.json").write_text(json.dumps(c, indent=1) + "\n", encoding="utf-8")
    key = {"kind": kind}
    if kind == "error":
        key["category"] = category
    key.update({"planter": "ai", "summary": summary, "code_change": code_change,
                "description_change": description_change, "affected": affected})
    (d / "key.json").write_text(json.dumps(key, indent=1) + "\n", encoding="utf-8")


def steps(r):
    return [s["step_id"] for s in r["steps"]]


def step_index(r, sid):
    return steps(r).index(sid)


def decl(c, corr):
    return next(x for x in c["declarations"] if x["content"]["correction"] == corr)


def binding(c, bid):
    return next(x for x in c["bindings"] if x["binding_id"] == bid)


# frequently edited lines of run.py
L_CALL = '''            res[(sname, pname)] = analyse(counts, sim["trig_hat"][pname], sim["sel_hat"][sname],
                                          st, ss, w["exposure"], w["response"], **extra)'''
L_WORLD = '''            world[sname][pname] = {"truth_flux": integ / WIDTH, "exposure": expo, "selected_truth": selected,
                                   "response": m,'''
L_NORM = '''"convention": "ratio of exposure-normalized fluxes; exposure = acceptance x livetime x cutoff fraction per period"}'''
L_ACC_NOTE = '''"notes": "acceptance enters once, inside the exposure normalization (acceptance x livetime x cutoff fraction)"}'''
L_DENOM = "    denom = eff_trig_hat * eff_sel_hat * expo * WIDTH\n"
L_ANALYSE_CORE = '''    s = np.where(blind, 0.0 if fill is None else fill, n - bkg)
    var = np.where(blind, 0.0, n + tf ** 2 * cr)
    u, cov_u, a = unfold(m, s, var, np.where(blind, s, var))  # the weights only condition the full-rank inverse
'''
L_RATIO_REL = '''    rel = (num["stat"] + num["selection"] + num["background"]) / np.outer(num["flux"], num["flux"]) + \\
          (den["stat"] + den["selection"] + den["background"]) / np.outer(den["flux"], den["flux"])
'''
L_SYS_TRIG = '''{"name": "trigger_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "covariance (fully correlated across bins, shared by species)"}'''
L_SYS_SEL = '''{"name": "selection_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "covariance (per bin, per species)"}'''
L_CANC_TRIG = '''{"effect": "trigger_efficiency", "treatment": "cancels", "correlation_model": "the same per-period estimate divides both species", "verification": "independent linear propagation with the shared component (core.stats ratio_measured) agrees"}'''
L_CANC_SEL = '''{"effect": "selection_efficiency", "treatment": "independent", "correlation_model": "separate control samples per species"}'''
L_BKG_EST = '''"estimator": "charge-sideband extrapolation: B_k = TF x N_sideband,k per reco rigidity bin and "
                                                         "period, TF = tail fraction in the window / in the sideband from the synthetic tail shape",'''
L_RESP_PROV = '''"provenance": "computed analytically from the synthetic resolution model; migration outside "
                                                    "[1.5, 150] GV is kept in explicit underflow/overflow vectors; first and last "
                                                    "bins are buffers",'''
L_BLIND_REGION = '''"regions": ["helium signal region (1.7 <= Q < 2.5) in the bin 60-100 GV, both periods"]'''


def build():
    # ======================================================================== errors
    def r_add_acceptance(r):
        r["steps"].insert(step_index(r, "exposure"), {"step_id": "acceptance", "operator": "correct_efficiency"})
    case("E01", "error", "C01",
         "The acceptance shape (acceptance relative to its plateau) is divided out as an extra per-bin 'geometric efficiency' "
         "although the exposure already contains the full acceptance, so the acceptance energy dependence is corrected twice.",
         "run_analysis multiplies the selection efficiency passed to analyse() by acceptance(sp)/acc_max, while w['exposure'] "
         "still equals acceptance x livetime x cutoff fraction.",
         "recipe.json gains a step 'acceptance' (operator correct_efficiency) before 'exposure'; the spec's acceptance "
         "correction notes now say the acceptance shape is corrected in the estimator and its absolute value enters the exposure.",
         ["acceptance", "efficiency", "exposure"] + ALL_INST + ALL_FLUX,
         [(L_CALL, '''            eff_geo = acceptance(sp) / sp["acc_max"]  # geometric acceptance per bin, relative to the plateau
            res[(sname, pname)] = analyse(counts, sim["trig_hat"][pname], sim["sel_hat"][sname] * eff_geo,
                                          st, ss, w["exposure"], w["response"], **extra)'''),
          (L_ACC_NOTE, '''"notes": "the acceptance shape (relative to its plateau) is corrected per bin in the estimator; the "
                                         "absolute acceptance enters the exposure normalization (acceptance x livetime x cutoff fraction)"}''')],
         recipe=r_add_acceptance)

    def r_unfold_eff(r):
        r["steps"][step_index(r, "unfold")]["operator"] = "unfold_with_efficiency"
    case("E02", "error", "C01",
         "The response given to the unfolding is normalized to generated events (selection inefficiency inside the matrix), "
         "but the unfolded counts are still divided by the selection efficiency, so that efficiency is corrected twice.",
         "build_world stores 'response': m * selection_eff(sp)[None, :] for the analysis (and the matrix files), while the "
         "expected reco counts still come from the selected-normalized m; analyse() keeps dividing by eff_sel_hat.",
         "recipe.json: step 'unfold' now uses operator unfold_with_efficiency, step 'efficiency' kept; response artifacts: "
         "normalization conditional_on_generated, inefficiency inside_matrix, includes migration and selection_efficiency "
         "(applied_separately unchanged).",
         ["unfold", "efficiency", "selection_efficiency", "rigidity_migration"] + ALL_INST + ALL_FLUX,
         [(L_WORLD, '''            world[sname][pname] = {"truth_flux": integ / WIDTH, "exposure": expo, "selected_truth": selected,  # response normalized to generated events
                                   "response": m * selection_eff(sp)[None, :],'''),
          ('''"orientation": "rows_reco_cols_truth", "normalization": "conditional_on_selected",
                                      "inefficiency": "outside_matrix", "acceptance": "outside_matrix", "includes": ["migration"],''',
           '''"orientation": "rows_reco_cols_truth", "normalization": "conditional_on_generated",
                                      "inefficiency": "inside_matrix", "acceptance": "outside_matrix", "includes": ["migration", "selection_efficiency"],''')],
         recipe=r_unfold_eff)

    case("E03", "error", "C02",
         "The exposure used to normalize the flux omits the geomagnetic cutoff livetime fraction (taken to be handled by the "
         "event selection), so low-rigidity bins, where only part of the livetime is above cutoff, are underestimated.",
         "build_world stores 'exposure': acceptance(sp) * per['livetime'] for the analysis instead of exposure(sp, per); the "
         "simulated selected counts still use the full exposure with the cutoff fraction.",
         "measurement spec: normalization convention now 'exposure = acceptance x livetime per period (the cutoff selection "
         "acts on events)'; the ratio cancellation 'livetime_and_cutoff' renamed 'livetime'.",
         ["exposure", "acceptance"] + ALL_INST + ALL_FLUX,
         [(L_WORLD, '''            world[sname][pname] = {"truth_flux": integ / WIDTH, "exposure": acceptance(sp) * per["livetime"], "selected_truth": selected,
                                   "response": m,'''),
          (L_NORM, '''"convention": "ratio of exposure-normalized fluxes; exposure = acceptance x livetime per period (the cutoff selection acts on events)"}'''),
          ('''{"effect": "livetime_and_cutoff", "treatment": "cancels", "correlation_model": "identical livetime and cutoff fraction per period and bin", "verification": "by construction of the exposure"}''',
           '''{"effect": "livetime", "treatment": "cancels", "correlation_model": "identical livetime per period", "verification": "by construction of the exposure"}''')])

    def c_trig_avg(c):
        decl(c, "trigger_efficiency")["basis"]["rationale"] = (
            "the trigger efficiency corrects the per-period fluxes of every species; the period average sums "
            "selection-corrected counts, the trigger term being common to both periods")
    case("E04", "error", "C02",
         "The period-averaged flux sums counts corrected for the selection efficiency only, dropping the trigger efficiency "
         "on the belief that it is common to both periods, although it differs per period (0.93 vs 0.90) and never cancels "
         "in a flux.",
         "run_analysis: the average numerator becomes sum(unfolded) / sel_hat instead of sum(unfolded / (trig_hat[p] * sel_hat)).",
         "context.json: rationale of map-trigger_efficiency says the period average uses selection-corrected counts only.",
         ["trigger_efficiency", "efficiency", "proton-p1", "proton-p2", "helium-p1", "helium-p2"],
         [('''        num = sum(res[(sname, p)]["unfolded"] / (sim["trig_hat"][p] * sim["sel_hat"][sname]) for p in PERIODS)''',
           '''        num = sum(res[(sname, p)]["unfolded"] for p in PERIODS) / sim["sel_hat"][sname]  # trigger common to both periods''')],
         context=c_trig_avg)

    def r_bkg_after(r):
        s = r["steps"].pop(step_index(r, "background"))
        r["steps"].insert(step_index(r, "unfold") + 1, s)
    case("E05", "error", "C03",
         "The charge-tail background, estimated in reco rigidity bins, is subtracted from the unfolded (truth-bin) helium "
         "counts instead of from the reco counts before unfolding, so the background is never migrated consistently.",
         "analyse(): the unfolding input is n (not n - bkg) and bkg is subtracted from u after unfold().",
         "recipe.json: step 'background' moved after 'unfold'; spec background estimator text now says B_k is subtracted from "
         "the unfolded helium counts.",
         ["background", "unfold", "helium-p1", "helium-p2", "flux-helium-p1", "flux-helium-p2"] + RATIOS,
         [(L_ANALYSE_CORE, '''    s = np.where(blind, 0.0 if fill is None else fill, n)
    var = np.where(blind, 0.0, n + tf ** 2 * cr)
    u, cov_u, a = unfold(m, s, var, np.where(blind, s, var))  # the weights only condition the full-rank inverse
    u = u - bkg  # charge-tail background removed from the unfolded helium counts
'''),
          (L_BKG_EST, '''"estimator": "charge-sideband extrapolation: B_k = TF x N_sideband,k per rigidity bin and "
                                                         "period, subtracted from the unfolded helium counts; TF = tail fraction in the window / in the sideband from the synthetic tail shape",''')],
         recipe=r_bkg_after)

    def r_eff_before(r):
        s = r["steps"].pop(step_index(r, "efficiency"))
        r["steps"].insert(step_index(r, "unfold"), s)
    case("E06", "error", "C03",
         "The per-bin selection efficiency, which is a function of true rigidity, is divided out of the reco-binned counts "
         "before unfolding instead of from the unfolded truth-bin counts.",
         "analyse(): s and var are divided by eff_sel_hat (and eff_sel_hat**2) before unfold(); denom no longer contains eff_sel_hat.",
         "recipe.json: step 'efficiency' moved before 'unfold'; response artifacts: correction_space of selection_efficiency "
         "changed to space 'reco'.",
         ["efficiency", "unfold", "selection_efficiency"] + ALL_INST + ALL_FLUX,
         [(L_ANALYSE_CORE + L_DENOM, '''    s = np.where(blind, 0.0 if fill is None else fill, n - bkg) / eff_sel_hat  # selection efficiency per rigidity bin
    var = np.where(blind, 0.0, n + tf ** 2 * cr) / eff_sel_hat ** 2
    u, cov_u, a = unfold(m, s, var, np.where(blind, s, var))  # the weights only condition the full-rank inverse
    denom = eff_trig_hat * expo * WIDTH
'''),
          ('''"selection_efficiency": {"space": "truth", "binned_in": "rigidity"},''',
           '''"selection_efficiency": {"space": "reco", "binned_in": "rigidity"},''')],
         recipe=r_eff_before)

    case("E07", "error", "C04",
         "The flux is divided by a log-centred bin width R_c x dlnR instead of the true bin width dR, so the result is no "
         "longer the bin average it is declared to be (a few-percent bias in the wide bins).",
         "New constant DR = CENTER * diff(log(EDGES)); analyse() denom and the period average use DR instead of WIDTH "
         "(the truth stays integral / WIDTH).",
         "measurement spec: normalization convention text appends 'bin width R_c x dlnR (log-centred)'; bin_semantics still bin-averaged.",
         ["bin-width", "bin_width"] + ALL_INST + ALL_FLUX,
         [('''CENTER = np.sqrt(EDGES[:-1] * EDGES[1:])
''', '''CENTER = np.sqrt(EDGES[:-1] * EDGES[1:])
DR = CENTER * np.diff(np.log(EDGES))  # bin width dR = R dlnR at the (geometric) bin centre
'''),
          (L_DENOM, "    denom = eff_trig_hat * eff_sel_hat * expo * DR\n"),
          ('''        den = sum(world[sname][p]["exposure"] for p in PERIODS) * WIDTH''',
           '''        den = sum(world[sname][p]["exposure"] for p in PERIODS) * DR'''),
          (L_NORM, '''"convention": "ratio of exposure-normalized fluxes; exposure = acceptance x livetime x cutoff fraction per period; bin width R_c x dlnR (log-centred)"}''')])

    case("E08", "error", "C04",
         "The per-period livetimes used in the analysis exposure are typed swapped from the run list (period 1 gets 2.6e6 s, "
         "period 2 gets 1.5e6 s), so each period's flux is normalized by the other period's livetime.",
         "New LIVETIME_S table with swapped values; build_world stores 'exposure': acceptance x LIVETIME_S[pname] x cutoff "
         "fraction for the analysis, while the simulation uses PERIODS livetimes.",
         "measurement spec: normalization convention lists the livetimes as period 1: 2.6e6 s, period 2: 1.5e6 s.",
         ["exposure"] + ALL_INST + ALL_FLUX,
         [('''CUTOFF_FACTOR = 1.2  #''', '''LIVETIME_S = {"synthetic-period-1": 2.6e6, "synthetic-period-2": 1.5e6}  # livetime per period from the run list (s)
CUTOFF_FACTOR = 1.2  #'''),
          (L_WORLD, '''            world[sname][pname] = {"truth_flux": integ / WIDTH, "exposure": acceptance(sp) * LIVETIME_S[pname] * cutoff_fraction(per),
                                   "selected_truth": selected, "response": m,'''),
          (L_NORM, '''"convention": "ratio of exposure-normalized fluxes; exposure = acceptance x livetime (period 1: 2.6e6 s, period 2: 1.5e6 s) x cutoff fraction per period"}''')])

    case("E09", "error", "C04",
         "The acceptance, already a geometric factor in m^2 sr, is treated as a projected area in m^2 and multiplied by pi sr "
         "for an isotropic flux, so every flux is low by a factor pi.",
         "build_world stores 'exposure': expo * math.pi for the analysis.",
         "measurement spec: acceptance correction notes now read 'acceptance (m^2) x pi sr enters once, inside the exposure'.",
         ["acceptance", "exposure"] + ALL_INST + ALL_FLUX,
         [(L_WORLD, '''            world[sname][pname] = {"truth_flux": integ / WIDTH, "exposure": expo * math.pi,  # flat-detector area x pi sr
                                   "selected_truth": selected, "response": m,'''),
          (L_ACC_NOTE, '''"notes": "acceptance (projected area, m^2) x pi sr enters once, inside the exposure normalization (acceptance x pi x livetime x cutoff fraction)"}''')])

    case("E10", "error", "C05",
         "The exposure is converted to cm^2 sr s for the analysis, but the flux roots are still declared and plotted in "
         "1/(m2 sr s GV), so every flux value is 1e4 too small for its declared unit.",
         "build_world stores 'exposure': expo * 1e4 (comment: cm^2 sr s).",
         "measurement spec: normalization convention now 'exposure = acceptance x livetime x cutoff fraction per period, in "
         "cm^2 sr s'; context roots still 1/(m2 sr s GV).",
         ["exposure"] + ALL_INST + ALL_FLUX,
         [(L_WORLD, '''            world[sname][pname] = {"truth_flux": integ / WIDTH, "exposure": expo * 1e4,  # cm^2 sr s, as in the flux tables
                                   "selected_truth": selected, "response": m,'''),
          (L_NORM, '''"convention": "ratio of exposure-normalized fluxes; exposure = acceptance x livetime x cutoff fraction per period, in cm^2 sr s"}''')])

    def c_gevn(c):
        for root in c["roots"]:
            if "helium" in root["root_id"]:
                root["unit"] = "1/(m2 sr s GeV/n)"
    case("E11", "error", "C05",
         "The helium flux is made differential in kinetic energy per nucleon (bin width x Z/A) while its bins stay in "
         "rigidity and the proton flux stays per GV, so the He/p ratio divides fluxes per different variables.",
         "analyse() takes a width argument; run_analysis passes width = WIDTH * abs_Z / A for helium (the period average keeps WIDTH).",
         "context.json: units of flux-helium-p1 and flux-helium-p2 changed to 1/(m2 sr s GeV/n); binning still the rigidity edges.",
         ["bin-width", "bin_width", "helium-p1", "helium-p2", "flux-helium-p1", "flux-helium-p2"] + RATIOS,
         [('''def analyse(counts, eff_trig_hat, eff_sel_hat, sigma_trig, sigma_sel, expo, m, sideband=None, tf=0.0, fill=None):''',
           '''def analyse(counts, eff_trig_hat, eff_sel_hat, sigma_trig, sigma_sel, expo, m, sideband=None, tf=0.0, fill=None, width=WIDTH):'''),
          (L_DENOM, "    denom = eff_trig_hat * eff_sel_hat * expo * width\n"),
          ('''                extra = {"sideband": sim["sideband"][pname], "tf": sim["tf_hat"], "fill": w["expected_reco"]}''',
           '''                extra = {"sideband": sim["sideband"][pname], "tf": sim["tf_hat"], "fill": w["expected_reco"],
                         "width": WIDTH * sp["abs_Z"] / sp["A"]}  # helium per nucleon: dE/n ~ (Z/A) dR''')],
         context=c_gevn)

    case("E12", "error", "C06",
         "The reported range is extended to include the 100-150 GV bin, which is a migration buffer with no truth above it, "
         "but only in the code: the spec edges still stop at 100 GV.",
         "REPORTED = slice(1, len(EDGES) - 1) (was len(EDGES) - 2); EDGES comment says only the first bin is a buffer.",
         "response artifacts: provenance text now says only the first bin is a buffer and 100-150 GV is reported; spec edges unchanged.",
         ["proton-p1", "proton-p2", "flux-proton-p1", "flux-proton-p2", "rigidity_migration"],
         [('''# GV; first and last bins are migration buffers''', '''# GV; the first bin is a migration buffer'''),
          ('''REPORTED = slice(1, len(EDGES) - 2)  # bins 2-3 ... 60-100 GV are reported''',
           '''REPORTED = slice(1, len(EDGES) - 1)  # bins 2-3 ... 100-150 GV are reported'''),
          (L_RESP_PROV, '''"provenance": "computed analytically from the synthetic resolution model; migration outside "
                                                    "[1.5, 150] GV is kept in explicit underflow/overflow vectors; the first "
                                                    "bin is a buffer, 100-150 GV is reported",''')])

    case("E13", "error", "C06",
         "The spec's reported edges are typed from the analysis note with 16 GV instead of 15 GV, so the declared binning "
         "differs from the EDGES the code uses.",
         "artifacts(): edges = a hard-coded list [2, 3, 4.5, 7, 10, 16, 25, 40, 60, 100] instead of EDGES[1:-1].",
         "measurement spec: observable variable edges (written by run.py) now contain 16.0 instead of 15.0.",
         ALL_FLUX + RATIOS,
         [('''    edges = EDGES[1:-1].tolist()
''', '''    edges = [2.0, 3.0, 4.5, 7.0, 10.0, 16.0, 25.0, 40.0, 60.0, 100.0]  # reported edges (GV), as in the analysis note
''')])

    def c_he_uses_p(c):
        for p in ("p1", "p2"):
            binding(c, f"use-helium-{p}")["from"]["item"] = f"response-proton-{p}"
    case("E14", "error", "C07",
         "The helium unfolding uses the proton response on the argument that migration is a curvature effect, but the "
         "response depends on the species' spectral shape inside each bin, so the helium unfolding is biased.",
         "run_analysis passes world['proton'][pname]['response'] to analyse() for both species.",
         "context.json: bindings use-helium-p1 / use-helium-p2 now take response-proton-p1 / response-proton-p2.",
         ["helium-p1", "helium-p2", "flux-helium-p1", "flux-helium-p2", "rigidity_migration", "unfold"] + RATIOS,
         [(L_CALL, '''            res[(sname, pname)] = analyse(counts, sim["trig_hat"][pname], sim["sel_hat"][sname],  # migration is in curvature:
                                          st, ss, w["exposure"], world["proton"][pname]["response"], **extra)  # one response''')],
         context=c_he_uses_p)

    def c_p1_resp(c):
        for sp in ("proton", "helium"):
            binding(c, f"use-{sp}-p2")["from"]["item"] = f"response-{sp}-p1"
    case("E15", "error", "C07",
         "Period 2 is unfolded with the period-1 response of each species ('the response is a detector property'), but the "
         "response depends on the in-bin spectral shape, which differs between periods through solar modulation.",
         "run_analysis passes world[sname][first period]['response'] to analyse() for every period.",
         "context.json: bindings use-proton-p2 and use-helium-p2 now take response-proton-p1 and response-helium-p1.",
         ["proton-p2", "helium-p2", "flux-proton-p2", "flux-helium-p2", "ratio-p2", "rigidity_migration", "unfold"],
         [(L_CALL, '''            ref_period = next(iter(PERIODS))  # the response is a detector property, not a period one
            res[(sname, pname)] = analyse(counts, sim["trig_hat"][pname], sim["sel_hat"][sname],
                                          st, ss, w["exposure"], world[sname][ref_period]["response"], **extra)''')],
         context=c_p1_resp)

    case("E16", "error", "C07",
         "Before unfolding, each truth column of the response is renormalized to unity, so migration out of [1.5, 150] GV "
         "(explicit underflow/overflow) is treated as staying in range and the edge bins are biased.",
         "analyse(): m = m / m.sum(axis=0, keepdims=True) before unfold().",
         "response artifacts: provenance text now says the analysis renormalizes each truth column to unity (underflow_overflow still explicit_bins).",
         ["rigidity_migration", "unfold"] + ALL_INST + ALL_FLUX,
         [(L_ANALYSE_CORE, '''    s = np.where(blind, 0.0 if fill is None else fill, n - bkg)
    var = np.where(blind, 0.0, n + tf ** 2 * cr)
    m = m / m.sum(axis=0, keepdims=True)  # probability-conserving columns
    u, cov_u, a = unfold(m, s, var, np.where(blind, s, var))  # the weights only condition the full-rank inverse
'''),
          (L_RESP_PROV, '''"provenance": "computed analytically from the synthetic resolution model; migration outside "
                                                    "[1.5, 150] GV is kept in explicit underflow/overflow vectors and each truth "
                                                    "column is renormalized to unity before unfolding; first and last bins are buffers",''')])

    case("E17", "error", "C08",
         "The charge-sideband transfer factor is inverted (sideband over window instead of window over sideband), so the "
         "subtracted Z=1 background in the helium window is wrong by the square of the true factor.",
         "TF_SR = tail_fraction(*SIDEBAND) / tail_fraction(*HE_WINDOW).",
         "measurement spec: background estimator text now says TF = tail fraction in the sideband / in the window.",
         ["background", "helium-p1", "helium-p2", "flux-helium-p1", "flux-helium-p2"] + RATIOS,
         [('''TF_SR = tail_fraction(*HE_WINDOW) / tail_fraction(*SIDEBAND)''',
           '''TF_SR = tail_fraction(*SIDEBAND) / tail_fraction(*HE_WINDOW)'''),
          (L_BKG_EST, '''"estimator": "charge-sideband extrapolation: B_k = TF x N_sideband,k per reco rigidity bin and "
                                                         "period, TF = tail fraction in the sideband / in the window from the synthetic tail shape",''')])

    def r_two_bkg(r):
        r["steps"].insert(0, {"step_id": "charge-tail", "operator": "subtract_background"})
    case("E18", "error", "C08",
         "The charge-tail background is removed from the helium signal-region histogram when it is read, and analyse() "
         "subtracts the same TF x sideband estimate again, so the background is subtracted twice.",
         "run_analysis: helium counts = blind_counts(counts - tf_hat * sideband) while the sideband and tf are still passed to analyse().",
         "recipe.json: a step 'charge-tail' (subtract_background) is added before step 'background'.",
         ["background", "helium-p1", "helium-p2", "flux-helium-p1", "flux-helium-p2"] + RATIOS,
         [('''                counts = blind_counts(sim["counts"][(sname, pname)])''',
           '''                counts = blind_counts(sim["counts"][(sname, pname)] - sim["tf_hat"] * sim["sideband"][pname])  # charge tail removed'''),
          ],
         recipe=r_two_bkg)

    case("E19", "error", "C09",
         "The selection efficiency is treated as cancelling in the He/p ratio ('same selection for both species'), but it "
         "is measured from separate per-species control samples, so its uncertainty is dropped from the ratio covariance.",
         "ratio_block(): the selection blocks of numerator and denominator are left out of the relative covariance.",
         "measurement spec: ratio cancellation selection_efficiency now treatment 'cancels', correlation model 'same "
         "selection algorithm applied to both species'.",
         ["selection_efficiency", "ratio-p1", "ratio-p2"],
         [(L_RATIO_REL, '''    rel = (num["stat"] + num["background"]) / np.outer(num["flux"], num["flux"]) + \\
          (den["stat"] + den["background"]) / np.outer(den["flux"], den["flux"])  # trigger and selection cancel
'''),
          (L_CANC_SEL, '''{"effect": "selection_efficiency", "treatment": "cancels", "correlation_model": "same selection algorithm applied to both species"}''')])

    case("E20", "error", "C09",
         "The ratio is computed as proton over helium (arguments of ratio_block and the truth swapped together, so closure "
         "still passes) while the context and objective call it He/p.",
         "run_analysis calls ratio_block(proton, helium); ratio_truth is proton / helium.",
         "measurement spec: ratio numerator 'proton flux', denominator 'helium flux'; context ratio-p1/ratio-p2 still helium over proton.",
         RATIOS,
         [('''        res[("ratio", pname)] = ratio_block(res[("helium", pname)], res[("proton", pname)])''',
           '''        res[("ratio", pname)] = ratio_block(res[("proton", pname)], res[("helium", pname)])'''),
          ('''world["helium"][pname]["truth_flux"] / world["proton"][pname]["truth_flux"]''',
           '''world["proton"][pname]["truth_flux"] / world["helium"][pname]["truth_flux"]'''),
          ('''"ratio": {"numerator": "helium flux", "denominator": "proton flux",''',
           '''"ratio": {"numerator": "proton flux", "denominator": "helium flux",''')])

    case("E21", "error", "C09",
         "The trigger-efficiency term, one per-period estimate shared by both species, is propagated as independent in the "
         "numerator and denominator of the ratio instead of cancelling, overstating the ratio uncertainty.",
         "ratio_block(): the trigger blocks of both species are added to the relative covariance.",
         "measurement spec: ratio cancellation trigger_efficiency now treatment 'independent', correlation model 'trigger "
         "efficiency estimated per species'.",
         ["trigger_efficiency", "ratio-p1", "ratio-p2"],
         [(L_RATIO_REL, '''    rel = (num["stat"] + num["trigger"] + num["selection"] + num["background"]) / np.outer(num["flux"], num["flux"]) + \\
          (den["stat"] + den["trigger"] + den["selection"] + den["background"]) / np.outer(den["flux"], den["flux"])
'''),
          (L_CANC_TRIG, '''{"effect": "trigger_efficiency", "treatment": "independent", "correlation_model": "trigger efficiency estimated per species"}''')])

    def c_sel_proton(c):
        d = decl(c, "selection_efficiency")
        d["content"]["instances"] = ["proton-p1", "proton-p2"]
        d["basis"]["rationale"] = "helium: the selection efficiency is part of the helium acceptance model"
    case("E22", "error", "C10",
         "The selection efficiency is corrected for protons only, on the belief that the helium acceptance model contains "
         "it; it does not, so the helium flux (and He/p) is low by the helium selection efficiency.",
         "run_analysis passes eff_sel_hat = 1.0 for helium (the period average still divides by it).",
         "context.json: map-selection_efficiency now lists proton-p1 and proton-p2 only, with a rationale about the helium acceptance model.",
         ["selection_efficiency", "efficiency", "helium-p1", "helium-p2", "flux-helium-p1", "flux-helium-p2"] + RATIOS,
         [(L_CALL, '''            sel = sim["sel_hat"][sname] if sname == "proton" else 1.0  # helium: inside the acceptance model
            res[(sname, pname)] = analyse(counts, sim["trig_hat"][pname], sel,
                                          st, ss, w["exposure"], w["response"], **extra)''')],
         context=c_sel_proton)

    def c_one_trig(c):
        decl(c, "trigger_efficiency")["basis"]["rationale"] = (
            "one trigger-efficiency estimate (the period-1 control sample) serves every species and period")
    case("E23", "error", "C10",
         "The period-1 trigger-efficiency estimate is used for both periods in the per-period fluxes, although the trigger "
         "efficiency differs by period (0.93 vs 0.90).",
         "run_analysis: trig_hat = sim['trig_hat'][first period] taken before the loop and passed for every period.",
         "context.json: rationale of map-trigger_efficiency now says one period-1 estimate serves every period; spec systematics "
         "trigger_efficiency 'shared by species and periods'.",
         ["trigger_efficiency", "proton-p2", "helium-p2", "flux-proton-p2", "flux-helium-p2"],
         [('''    res = {}
    for pname, per in PERIODS.items():
        st = math.sqrt''', '''    res = {}
    trig_hat = sim["trig_hat"][next(iter(PERIODS))]  # one trigger efficiency for the data set
    for pname, per in PERIODS.items():
        st = math.sqrt'''),
          (L_CALL, '''            res[(sname, pname)] = analyse(counts, trig_hat, sim["sel_hat"][sname],
                                          st, ss, w["exposure"], w["response"], **extra)'''),
          (L_SYS_TRIG, '''{"name": "trigger_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "covariance (fully correlated across bins, shared by species and periods)"}''')],
         context=c_one_trig)

    case("E24", "error", "C11",
         "The dataset records are extended to 100 GV, so the blinded 60-100 GV He/p value (built from the filled expectation "
         "and the open proton count) is released.",
         "artifacts(): pub_edges runs to PUBLISHED.stop + 2 and the record values to PUBLISHED.stop + 1.",
         "dataset records: objective now '2-100 GV' and observable/data edges extend to 100 GV; spec blinding unchanged.",
         RATIOS + ["helium-p1", "helium-p2"],
         [('''    pub_edges = EDGES[PUBLISHED.start:PUBLISHED.stop + 1].tolist()  # the blinded bin is not released''',
           '''    pub_edges = EDGES[PUBLISHED.start:PUBLISHED.stop + 2].tolist()  # up to 100 GV (the blinded bin carries the expectation)'''),
          ('''objective=f"SYNTHETIC He/p ratio, {pname}, unblinded bins",''', '''objective=f"SYNTHETIC He/p ratio, {pname}, 2-100 GV",'''),
          ('''"values": r[PUBLISHED].tolist(),''', '''"values": r[PUBLISHED.start:PUBLISHED.stop + 1].tolist(),''')])

    case("E25", "error", "C11",
         "The custodian masking step is run for period 1 only (period 2 assumed masked upstream); the unmasked period-2 "
         "helium signal-region histogram is then written to results.json, publishing the blinded count.",
         "main(): custodian loop over list(PERIODS)[:1]; observed_counts written as plain float lists for every species and period (so the unmasked period-2 helium array serializes).",
         "measurement spec: blinding mask region text now '60-100 GV, period 1 (period 2 masked upstream)'.",
         ["helium-p2", "flux-helium-p2", "ratio-p2"],
         [('''    for p in PERIODS:
        expected = world["helium"][p]["expected_reco"]''', '''    for p in list(PERIODS)[:1]:  # period 2 arrives masked from the custodian
        expected = world["helium"][p]["expected_reco"]'''),
          ('''        "observed_counts": {f"{s}/{p}": (sim["counts"][(s, p)] if s == "helium" else sim["counts"][(s, p)].tolist())''',
           '''        "observed_counts": {f"{s}/{p}": [None if v is None else float(v) for v in sim["counts"][(s, p)]]'''),
          (L_BLIND_REGION, '''"regions": ["helium signal region (1.7 <= Q < 2.5) in the bin 60-100 GV, period 1 (period 2 masked upstream)"]''')])

    case("E26", "error", "C12",
         "The background transfer-factor block is left out of the helium total covariance (the flux pulls and published "
         "uncertainties lose the 10% TF component) although it is still listed as a systematic.",
         "analyse(): 'total' = stat + trig + sel (bkg_cov no longer added).",
         "ratio result: nuisance 'background transfer factor (helium)' removed; spec systematic background applied_via says "
         "'covariance block reported separately'.",
         ["background", "flux-helium-p1", "flux-helium-p2"],
         [('''            "total": stat + trig + sel + bkg_cov,''', '''            "total": stat + trig + sel,'''),
          ('''                           "nuisances": ["trigger efficiency per period", "selection efficiency per bin and species",
                                         "background transfer factor (helium)"],''',
           '''                           "nuisances": ["trigger efficiency per period", "selection efficiency per bin and species"],'''),
          ('''"applied_via": "covariance (TF x sideband counts, fully correlated across bins, helium only, unfolded)"}''',
           '''"applied_via": "covariance block reported separately (TF x sideband counts, helium only, unfolded)"}''')])

    case("E27", "error", "C12",
         "The selection-efficiency uncertainty, from independent binomial control samples per bin, is propagated as fully "
         "correlated across bins.",
         "analyse(): sel = outer(v, v) with v = flux * sigma_sel / eff_sel_hat instead of diag(v**2).",
         "measurement spec: systematic selection_efficiency applied_via now 'covariance (fully correlated across bins, per species)'.",
         ["selection_efficiency"] + ALL_FLUX + RATIOS,
         [('''    sel = np.diag((flux * sigma_sel / eff_sel_hat) ** 2)  # independent per bin''',
           '''    v_sel = flux * sigma_sel / eff_sel_hat
    sel = np.outer(v_sel, v_sel)  # one selection estimate per species'''),
          (L_SYS_SEL, '''{"name": "selection_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "covariance (fully correlated across bins, per species)"}''')])

    case("E28", "error", "C12",
         "The trigger-efficiency uncertainty is computed with the selection control-sample size (5000) instead of the "
         "unbiased-trigger sample (1000), understating it by sqrt(5).",
         "run_analysis: st = sqrt(eps (1 - eps) / N_CTRL_SELECTION).",
         "measurement spec: systematic trigger_efficiency source now 'control sample (5000 unbiased-trigger events per period)'.",
         ["trigger_efficiency"] + ALL_FLUX,
         [('''        st = math.sqrt(per["trigger"] * (1 - per["trigger"]) / N_CTRL_TRIGGER)''',
           '''        st = math.sqrt(per["trigger"] * (1 - per["trigger"]) / N_CTRL_SELECTION)'''),
          (L_SYS_TRIG, '''{"name": "trigger_efficiency", "source": "control sample (5000 unbiased-trigger events per period)", "effect": "normalization", "applied_via": "covariance (fully correlated across bins, shared by species)"}''')])

    # ======================================================================== refactors
    def r_rename_bw(r):
        r["steps"][step_index(r, "bin-width")]["step_id"] = "divide-bin-width"
    case("R01", "refactor", None,
         "The constant WIDTH is renamed BIN_WIDTH and the recipe step 'bin-width' is renamed 'divide-bin-width'; same values, same operator.",
         "WIDTH -> BIN_WIDTH everywhere.", "recipe.json: step_id bin-width -> divide-bin-width.",
         ["bin-width"],
         [(re.compile(r"\bWIDTH\b"), "BIN_WIDTH")], recipe=r_rename_bw)

    case("R02", "refactor", None,
         "The flux and its Jacobian are computed from one reciprocal of the denominator; the acceptance note is reworded with the same meaning.",
         "analyse(): inv = 1/denom; flux = u * inv; jac = diag(inv).",
         "measurement spec: acceptance correction notes reworded (acceptance once, as a factor of the exposure).",
         ["acceptance", "exposure"],
         [('''    flux = u / denom
    jac = np.diag(1.0 / denom)''', '''    inv = 1.0 / denom
    flux = u * inv
    jac = np.diag(inv)'''),
          (L_ACC_NOTE, '''"notes": "acceptance appears once, as a factor of the exposure (acceptance x livetime x cutoff fraction); it is not divided out separately"}''')])

    def r_eff_expo(r):
        i = step_index(r, "efficiency")
        r["steps"][i:i + 2] = [{"step_id": "effective-exposure", "operator": "divide_effective_exposure"}]
    case("R03", "refactor", None,
         "Efficiency correction and exposure division are merged into one division by the effective exposure (efficiencies x "
         "acceptance x livetime x cutoff fraction); the product is unchanged.",
         "analyse(): eff_expo = eff_trig_hat * eff_sel_hat * expo; denom = eff_expo * WIDTH.",
         "recipe.json: steps 'efficiency' and 'exposure' replaced by one step 'effective-exposure' (divide_effective_exposure).",
         ["efficiency", "exposure"] + ALL_INST,
         [(L_DENOM, '''    eff_expo = eff_trig_hat * eff_sel_hat * expo  # effective exposure: efficiencies x acceptance x livetime x cutoff fraction
    denom = eff_expo * WIDTH
''')],
         recipe=r_eff_expo)

    ren = {"proton-p1": "proton-period1", "proton-p2": "proton-period2", "helium-p1": "helium-period1", "helium-p2": "helium-period2"}

    def c_rename_inst(c):
        for root in c["roots"]:
            root["output"]["instance"] = ren[root["output"]["instance"]]
        for inst in c["recipe_instances"]:
            inst["instance_id"] = ren[inst["instance_id"]]
        for b in c["bindings"]:
            b["to"]["instance"] = ren[b["to"]["instance"]]
        for d in c["declarations"]:
            d["content"]["instances"] = [ren[i] for i in d["content"]["instances"]]
    case("R04", "refactor", None,
         "Recipe instance ids are renamed consistently (proton-p1 -> proton-period1, ...) in roots, instances, bindings and "
         "declarations; in the code the per-cell loop variable is renamed. Nothing changes in the computation.",
         "run_analysis: local w renamed cell.",
         "context.json: instance ids renamed everywhere they appear.",
         ALL_INST,
         [('''            w = world[sname][pname]
            if sname == "helium":
                extra = {"sideband": sim["sideband"][pname], "tf": sim["tf_hat"], "fill": w["expected_reco"]}''',
           '''            cell = world[sname][pname]
            if sname == "helium":
                extra = {"sideband": sim["sideband"][pname], "tf": sim["tf_hat"], "fill": cell["expected_reco"]}'''),
          (L_CALL, '''            res[(sname, pname)] = analyse(counts, sim["trig_hat"][pname], sim["sel_hat"][sname],
                                          st, ss, cell["exposure"], cell["response"], **extra)''')],
         context=c_rename_inst)

    def c_rationale(c):
        for d in c["declarations"]:
            d["basis"]["rationale"] = (f"the {d['content']['correction']} correction of the spec applies to both species "
                                       "in both periods")
    case("R05", "refactor", None,
         "Rationale texts of the four instance-mapping declarations and the analyse() docstring are reworded; the meaning and the code path are unchanged.",
         "analyse() docstring rewritten.", "context.json: basis.rationale of every declaration reworded.",
         ["trigger_efficiency", "selection_efficiency", "acceptance", "rigidity_migration"],
         [('''    """Flux and covariance blocks for one species and period. counts may hold None (a blinded bin, as released by the
    custodian step): that bin takes the simulated expectation fill[k] with no variance. With a sideband, the
    background tf x sideband is subtracted per reco bin; its statistical variance joins the statistical block and the
    transfer-factor uncertainty forms the background block."""''',
           '''    """Flux of one species in one period, with its covariance split into blocks.

    A None in counts marks the blinded bin released by the custodian; it is replaced by the simulated expectation
    fill[k] and carries no variance. If a sideband is given, tf x sideband is subtracted in each reco bin before
    unfolding: the sideband's Poisson variance goes into the statistical block, the transfer-factor uncertainty into
    the background block."""''')],
         context=c_rationale)

    case("R06", "refactor", None,
         "ratio_block computes each species' relative covariance in a helper (still without the cancelling trigger block); "
         "the spec's trigger-cancellation verification text is reworded.",
         "ratio_block(): nested rel_cov(b) helper; same terms summed in the same order.",
         "measurement spec: verification text of the trigger_efficiency cancellation reworded.",
         ["trigger_efficiency", "ratio-p1", "ratio-p2"],
         [(L_RATIO_REL + "    return r, rel * np.outer(r, r)\n", '''
    def rel_cov(b):  # relative covariance without the trigger block, which cancels in the ratio
        return (b["stat"] + b["selection"] + b["background"]) / np.outer(b["flux"], b["flux"])
    return r, (rel_cov(num) + rel_cov(den)) * np.outer(r, r)
'''),
          (L_CANC_TRIG, '''{"effect": "trigger_efficiency", "treatment": "cancels", "correlation_model": "the same per-period estimate divides both species", "verification": "agrees with an independent linear propagation that keeps the shared trigger term (core.stats ratio_measured)"}''')])

    case("R07", "refactor", None,
         "The per-bin selection uncertainty is named before forming the diagonal block; the systematic's description is reworded with the same meaning.",
         "analyse(): sel_sigma = flux * sigma_sel / eff_sel_hat; sel = diag(sel_sigma**2).",
         "measurement spec: systematic selection_efficiency applied_via 'diagonal covariance (bins independent), separate per species'.",
         ["selection_efficiency"],
         [('''    sel = np.diag((flux * sigma_sel / eff_sel_hat) ** 2)  # independent per bin''',
           '''    sel_sigma = flux * sigma_sel / eff_sel_hat
    sel = np.diag(sel_sigma ** 2)  # independent per bin'''),
          (L_SYS_SEL, '''{"name": "selection_efficiency", "source": "control sample", "effect": "normalization", "applied_via": "diagonal covariance (bins independent), separate per species"}''')])

    case("R08", "refactor", None,
         "cutoff_fraction is vectorized with numpy (same criterion: CUTOFF_FACTOR x cutoff < bin lower edge); the geomagnetic selection definition is reworded.",
         "cutoff_fraction(): boolean mask over (bin, cutoff) times weights, summed per bin.",
         "measurement spec: geomagnetic selection definition 'lower edge of the rigidity bin above 1.2 x the maximum cutoff'.",
         ["exposure"] + ALL_INST,
         [('''    return np.array([sum(w for rc, w in period["cutoff_hist"].items() if CUTOFF_FACTOR * rc < EDGES[j]) for j in range(NB)])''',
           '''    rc = np.array(list(period["cutoff_hist"].keys()))
    w = np.array(list(period["cutoff_hist"].values()))
    above = CUTOFF_FACTOR * rc[None, :] < EDGES[:-1, None]  # (bin, cutoff)
    return (above * w[None, :]).sum(axis=1)'''),
          ('''"definition": "bin lower edge > 1.2 x maximum cutoff",''',
           '''"definition": "lower edge of the rigidity bin above 1.2 x the maximum cutoff",''')])

    case("R09", "refactor", None,
         "TF_REL is renamed TF_REL_UNC and the spec's background-uncertainty text is generated from it with reworded, equivalent wording.",
         "TF_REL -> TF_REL_UNC everywhere; uncertainty string built with f'{TF_REL_UNC:.0%}'.",
         "measurement spec: background uncertainty text reworded (10% relative on the transfer factor, fully correlated across bins).",
         ["background"],
         [(re.compile(r"\bTF_REL\b"), "TF_REL_UNC"),
          ('''"uncertainty": "10% on TF, fully correlated (synthetic tail-shape modelling); sideband "
                                                           "counts in the statistical block"}],''',
           '''"uncertainty": f"{TF_REL_UNC:.0%} relative on the transfer factor, fully correlated across bins (synthetic "
                                                           "tail-shape modelling); the sideband counts enter the statistical block"}],''')])

    case("R10", "refactor", None,
         "The period average is computed as the exposure-weighted mean of the per-period fluxes, which equals the sum of "
         "efficiency-corrected counts over the summed exposure x bin width; the spec states the definition.",
         "run_analysis: average = sum(exposure_p * flux_p) / sum(exposure_p).",
         "measurement spec: normalization convention appends 'the period average is the exposure-weighted mean of the per-period fluxes'.",
         ["exposure", "trigger_efficiency", "selection_efficiency"],
         [('''    for sname in SPECIES:  # exposure-weighted average over periods: sum of corrected counts / sum of exposures
        num = sum(res[(sname, p)]["unfolded"] / (sim["trig_hat"][p] * sim["sel_hat"][sname]) for p in PERIODS)
        den = sum(world[sname][p]["exposure"] for p in PERIODS) * WIDTH
        res[(sname, "average")] = num / den''',
           '''    for sname in SPECIES:  # exposure-weighted average over periods: sum of exposure x flux / sum of exposures
        tot = sum(world[sname][p]["exposure"] for p in PERIODS)
        res[(sname, "average")] = sum(world[sname][p]["exposure"] * res[(sname, p)]["flux"] for p in PERIODS) / tot'''),
          (L_NORM, '''"convention": "ratio of exposure-normalized fluxes; exposure = acceptance x livetime x cutoff fraction per period; the period average is the exposure-weighted mean of the per-period fluxes"}''')])

    def r_unfold_name(r):
        r["steps"][step_index(r, "unfold")]["step_id"] = "unfold-tsvd"
    case("R11", "refactor", None,
         "The unfolding function is renamed unfold_tsvd and the recipe step 'unfold' is renamed 'unfold-tsvd'; the operator and the computation are unchanged.",
         "def unfold -> def unfold_tsvd and its call in analyse().",
         "recipe.json: step_id unfold -> unfold-tsvd (operator unfold).",
         ["unfold"],
         [(re.compile(r"\bunfold\("), "unfold_tsvd(")], recipe=r_unfold_name)


if __name__ == "__main__":
    build()
