# Worked Examples

## When to read this file

If this session has not read them yet, read the profile's [working rules](../working-rules.md) first.

Read to see the intended behavior on representative requests. Examples use symbols, never invented AMS values.

## Contents

1. [Worked examples](#worked-examples)

## Worked examples

### Example 1: electron/proton separation

Answer structure: (a) the **Tracker** gives charge sign and `|R|`; it cannot separate `e⁻` from `p̄`-like negatives by itself beyond kinematic consistency. (b) The **TRD** separates leptons from hadrons by transition radiation (γ-dependent); not a charge-sign detector. (c) The **ECAL** provides shower-shape and energy; for electrons `E/|p| ≈ 1` within resolution and bremsstrahlung, protons show `E/p < 1` on average with tails. (d) `E/p` combines ECAL energy with the Tracker's `|R|` (`Z = 1`); it is not independent of the ECAL shape. (e) Each handle's efficiency and rejection must be measured on control data with a named selection; **no rejection factor is quoted** because public values depend on efficiency and energy context (see [source-index](../../evidence/index.md)). Reference: [antimatter-and-leptons](../species/antimatter-and-leptons.md#electrons-and-positrons).

### Example 2: 10-500 GV positron flux

First, flag the premise: rigidity (GV) vs energy (GeV). Positron results are published as energy; for `|Z| = 1` leptons, `E ≈ pc = |R|` numerically in GeV/GV to negligible mass corrections, but the ECAL energy and Tracker rigidity are distinct estimators; choose the binning variable and state it. Then: estimand (flux vs fraction); charge sign from the Tracker; **charge confusion** as a tail-dominated `e⁻ → e⁺` migration with a data-driven tail check; proton contamination via TRD/ECAL templates or cuts with finite-template statistics; conditional efficiencies; acceptance and livetime with geomagnetic transmission; migration/unfolding (bremsstrahlung tail); geomagnetic applicability (low-energy lower bound relative to cutoff); systematics with correlations; cross-checks (see the blueprint in [antimatter-and-leptons](../species/antimatter-and-leptons.md#electronpositron-blueprint)). **Missing inputs** to ask: data period/reconstruction version, track configuration, MC production, cutoff model and safety factor, binning, whether public or internal. No counts, rejection numbers, or systematic sizes are supplied.

### Example 3: deuteron/proton separation

`m = |Z||R|/(γβ)` (GeV/c² for `R` in GV). Error: `(δm/m)² = (δR/R)² + (γ²δβ/β)²` (+ cross-term). High `β`: `γ²` amplification; RICH range and ring-quality dependence; `D` from fragmentation of `⁴He` in material as a background; template overlap between `D` and `p` (mass ratio about 2 but resolution and tails); simulated shapes validated on known-mass samples; conversion to `T/A` requires stated `A` (here `A = 2` for the deuteron). Reference: [nuclei-and-isotopes](../species/nuclei-and-isotopes.md#isotope-separation). AMS published a deuteron flux (S13): the main article describes an **unfolding** with rigidity and 1/β resolution functions of the TOF and RICH (not a mass template fit) and a data-driven He → D fragmentation background; further details are in its Supplemental Material and are not invented here.

### Example 4: antihelium status

Classify: (i) publications: no peer-reviewed AMS antihelium paper located in INSPIRE (checked 2026-09-20), only the AMS-01 limit (S22); (ii) conference/talk statements exist (preliminary); (iii) theses/talks (S24-S25), third-party interpretations of "tentative" events (S26); (iv) media/rumor: navigation only. **Never state candidate counts** or call any candidate a discovery. If the user wants "latest": run the currency check in [source-policy](../sources/source-policy.md#currency-checks-latest).

### Example 5: four-iteration Bayesian unfolding

A count of "four iterations" is not a criterion (published AMS flux analyses stop the iteration when successive fluxes agree within 0.1%, S06/S08). Require: nominal and reweighted closure; prior dependence (unfold with several priors); bias-variance versus iteration count on ensembles containing stress-test spectra; toy-based covariance including response fluctuations; boundary/under/overflow treatment; a declared selection criterion determined without optimizing on the final unfolded spectrum. See [inference-and-unfolding](inference-and-unfolding.md#unfolding).

### Example 6: antiproton template likelihood

Symbolic. Reconstructed bins `i` (signed-rigidity-sensitive discriminant per `|R|` bin `r`); components `c ∈ {p̄, p_conf, e⁻}` with templates `t_{c,i}^{(r)}` (normalized) and yields `ν_c^{(r)}`. Expected count: `μ_i^{(r)} = Σ_c ν_c^{(r)} t_{c,i}^{(r)}`. Finite-template statistics: replace `t` by nuisances `τ_{c,i}` with Poisson (Barlow-Beeston or Conway) auxiliary terms. `L = Π_{r,i} Poisson(n_i^{(r)} | μ_i^{(r)}) Π_{c,i,r} Poisson(m_{c,i}^{(r)} | τ_{c,i}^{(r)} ...) × C(η)`. Constraints: charge-confusion yield `ν_{p_conf}` tied to a data-driven tail probability times the proton yield; `e⁻` yield tied to a control region; correlations across `r` from shared nuisances (scale, tail probability). Checks: identifiability (`p̄` vs `p_conf` shape degeneracy), goodness of fit, signal injection, alternative templates, coverage at low counts. Remains symbolic; no invented counts or widths.

### Example 7: multiplying cut efficiencies

`ε_total ≠ ε_A ε_B ε_C` unless independent. Write each factor with its conditional denominator (`ε_B|A` is the fraction passing B among events passing A). Correlations: shared Tracker information, shared ECAL energy, rigidity dependence. Ordering: totals must match under reordering. Validation: data/MC scale factors per factor, joint efficiency measured directly and compared to the product, combined-efficiency closure in MC per bin. See [efficiency-acceptance-backgrounds](efficiency-acceptance-backgrounds.md#conditional-efficiencies).

### Example 8: invalid helium `E/R = 1` premise

Correct first. `p = |Z|R/c`, so helium at `R = 10 GV` has `p = 20 GeV/c`, not 10. ECAL response to helium is species-dependent (hadronic shower with a large partial containment), and it is not an electron: the `E ≈ pc` relation belongs to electrons/positrons where the mass is negligible. `E/R = 1` therefore has no basis for helium; an `E/p` test is electron-specific logic, and for nuclei the standard charge estimators are Tracker, TOF and RICH (see the matrix in [detector-and-observables](../subsystems/detector-and-observables.md#cross-subsystem-matrix)). Ask what the user tried to achieve (`He` identification? `He` vs electron separation?) and propose the appropriate variables.
