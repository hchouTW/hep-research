# Decorrelation, systematic-aware training and simulation-to-data differences

Part of [ml-analysis.md](ml-analysis.md), the hep-ml entry reference for machine learning in an analysis
(read its splits and metrics first). Citations give arXiv identifiers looked up on INSPIRE-HEP or arXiv on
2026-10-13; they point to the method, not to a validated recipe for any experiment.

## Mass sculpting and decorrelation

If the analysis fits a spectrum (mass, or another variable used for background estimation such as an ABCD plane), a
score correlated with that variable sculpts the background after a cut. A smooth falling spectrum can turn into a
peak.

**Diagnose first.** For background events, compare the mass distribution passing and failing a score cut at fixed
ε_S. Report the Jensen–Shannon divergence (`assets/hep_metrics.py`: `mass_sculpting_jsd`) and plot 1/JSD against
1/ε_B. Higher 1/JSD at equal rejection is better. Do this per score category and on independent samples.

The binned JSD is biased upward by statistical fluctuations, increasingly so with more bins and fewer passing events.
At tight working points 1/JSD then measures MC statistics, not sculpting. Compare at fixed binning, and quote the
statistical baseline next to each value: the JSD between two random halves of the failing sample (`baseline=True`).

**Methods**, each a trade-off between rejection and decorrelation:

- **Decorrelated taggers (DDT):** a transformation of a substructure variable that flattens its dependence on a
  scaling variable such as ρ′ (Dolen et al., JHEP 05 (2016) 156, arXiv:1603.00027). Simple and transparent; later
  uses build the correction as a map in (ρ, pT) rather than in one variable (`unverified`: no opened source cited for
  the two-dimensional maps).
- **Planing:** reweight the training samples so signal and background have the same mass distribution. This removes
  mass as a direct discriminant, but does not guarantee independence through correlated features (Chang, Cohen,
  Ostdiek, PRD 97 (2018) 056009, arXiv:1709.10106).
- **Adversarial:** an adversary predicts the mass from the score, and the classifier is penalized for its success
  (Louppe, Kagan, Cranmer, arXiv:1611.01046, NeurIPS 2017). Powerful, but training is unstable and sensitive to the
  adversary's capacity and to λ.
- **DisCo:** add λ·dCor²(score, mass) computed on background events in each batch. It is a differentiable,
  non-adversarial single-objective penalty, typically much more stable than adversarial training (Kasieczka & Shih,
  PRL 125 (2020) 122001, arXiv:2001.05310). Cost is O(B²) per batch, the penalty needs batches of several hundred
  events, and it should be computed in float32 even under mixed precision ([mixed-precision.md](mixed-precision.md)). Use |w| inside the penalty; distance
  correlation is not defined for signed weights. Training on |w| decorrelates the |w|-weighted background, so check
  the sculpting afterwards with the signed weights. Implementation: `assets/hep_losses.py` (`disco_penalty`).
- **Moment decomposition (MoDe):** constrains the score's conditional distribution to a chosen order in mass (flat,
  linear, ...). This allows controlled rather than zero dependence (Kitouni et al., JHEP 04 (2021) 070,
  arXiv:2010.09745).

Validate the background parameterization in each score category after decorrelation. Using an adversarial or DisCo
objective does not itself establish independence; the measured sculpting on independent samples does.

## Parameterized and systematic-aware training

- **Parameterized networks:** feed the physics parameter θ (a mass hypothesis, a coupling) as an input and train over
  a grid of θ. One network then interpolates between grid points (Baldi et al., EPJC 76 (2016) 235,
  arXiv:1601.07913). Background events have no θ: assign each one a θ drawn from the signal training distribution,
  otherwise θ itself identifies the class. Validate at θ points held out from training, and never extrapolate beyond
  the grid (declare it as the training domain).
- **Nuisance-aware training:**
  - **Augmentation:** train on systematic variations so the score is less sensitive to them.
  - **Parameterization:** give the nuisance ν as an input, for later profiling.
  - **Adversarial pivoting:** make the score invariant to ν (the original use case of the Louppe et al. pivot).
  Lower sensitivity to a nuisance is not automatically better, because data can constrain the nuisance in the fit.
  Judge on the expected total uncertainty of the parameter of interest.
- **Inference-aware objectives:** optimize the expected uncertainty of the parameter of interest, nuisances included,
  through a differentiable approximation of the likelihood. Examples are INFERNO (De Castro & Dorigo, CPC 244 (2019)
  170, arXiv:1806.04743) and neos (Simpson & Heinrich, arXiv:2203.05570). The statistical model they approximate
  must match the final one; hand the final evaluation to hep-statistics.

## Simulation-to-data differences

A model trained on simulation is applied to data whose input distributions differ. The robustness questions are in
[robustness-and-distribution-shift.md](robustness-and-distribution-shift.md). The HEP methods are:

- **Measure, don't assume:** compare score distributions in data and simulation in signal-depleted control regions,
  per period and kinematic bin, with the inputs' systematic variations propagated through the frozen network.
- **Scale factors:** measure the efficiency of the working point in data and simulation on a control sample
  (tag-and-probe or a pure selection). Apply the ratio, binned in the variables it depends on, as a correction with
  uncertainty. A continuous score needs a shape calibration (per-score-bin factors or an iterative fit) rather than
  one factor. The measurement itself is hep-detector's (tag-and-probe, efficiency); the requirement to do it is
  this skill's.
- **Classifier reweighting (DCTR-type):** train a classifier between simulation and data (or between two generator
  setups) in a control region, then reweight the simulation with w = f/(1−f) (Andreassen & Nachman, PRD 101 (2020)
  091901, arXiv:1907.08209). That form holds for equal total training weight per class. Otherwise multiply by
  Σw_sim/Σw_data, or apply the odds correction above. Before using it:
  - calibrate f;
  - renormalize the weights, and report any clipping of large weights with its effect;
  - check that signal contamination of the control region is negligible;
  - report the effective sample size after reweighting;
  - state the extrapolation from the control region to the signal region, which is an assumption, not a result.
- **Domain-adversarial training:** makes the representation indistinguishable between simulation and data (Ganin et
  al., arXiv:1505.07818). It can hide a real mismodeling and puts data into the training. It still needs the
  control-region validation above and must respect blinding: no signal-region data in training.
