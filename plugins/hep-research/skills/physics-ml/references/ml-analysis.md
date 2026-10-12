# Machine Learning in Experimental Analysis

The physics entry point of this skill. It covers what makes a classifier or regressor usable inside a measurement:
splits, event weights, analysis metrics, decorrelation, systematic-aware training, simulation-to-data differences,
weak supervision, ML unfolding on the training side, and deployment. Model families and BDT practice are in
[multivariate-analysis-bdt-nn.md](multivariate-analysis-bdt-nn.md); set and jet architectures in
[particle-and-jet-architectures.md](particle-and-jet-architectures.md); space and ground-based astroparticle
detectors in [space-and-astroparticle-ml.md](space-and-astroparticle-ml.md); fast simulation in
[fast-simulation-validation.md](fast-simulation-validation.md); SBI training in [sbi-training.md](sbi-training.md).
Validity of an inference built on a model is hep-statistics'
([ml-assisted-inference.md](../../hep-statistics/references/ml-assisted-inference.md)); sample normalization is
hep-analysis' ([weights-normalization.md](../../hep-analysis/references/weights-normalization.md)).

Citations give arXiv identifiers looked up on INSPIRE-HEP or arXiv on 2026-10-13. They point to the method, not to
a validated recipe for any experiment.

## Splits and leakage

Split by event and production relationships, not merely by random rows. Multiple candidates, systematic variants,
duplicate files, and derived views of an event should remain grouped. Learn preprocessing, feature selection, tuning,
and calibration only from permitted training/validation partitions.

- **Grouping keys that carry correlation:** event (several candidates or jets per event), run or luminosity block,
  detector period or calibration epoch (time-dependent conditions), simulation production and seed, generator
  parameter point (for parameterized networks), and test-beam run.
- **k-fold by event number** (for example `event % k`) is the standard way to use all simulated and data events: each
  event is evaluated by the model that did not see it. Keep the fold assignment deterministic and record it. The same
  rule applies when the classifier is applied to data in a weakly supervised search.
- **Never `random_split` on rows** when a grouping key exists. Build the split from the key, then check it with
  `<plugin root>/skills/physics-ml/scripts/check_split_integrity.py`.

Prevent blinded SR information from leaking through labels, mass windows, normalization, or validation metrics. Weak
supervision and sideband methods require explicit assumptions about contamination and feature independence.

## Event weights

Two kinds of weight have different jobs and must be kept apart:

- **Physics weights** (cross section × luminosity / Σw_gen, generator weights, scale factors, pileup or reweighting
  corrections) define yields, templates and efficiencies. They are always the weights used for evaluation, and their
  signs are kept (hep-analysis owns their bookkeeping).
- **Training weights** decide what the optimizer pays attention to: class balancing, flattening in a kinematic
  variable, handling of negative weights. They change which function is learned, and so the optimality and the
  probabilistic meaning of the output, but they cannot make a frozen selection wrong: any fixed function of the
  inputs is a valid observable, as long as templates and data pass through it identically.

So, **when the score is used as an observable** (a cut or a template variable): training weights affect sensitivity
and calibration; evaluation weights affect correctness. **When the output itself is used as a density ratio** (DCTR
reweighting, OmniFold, likelihood-ratio estimation, a probability entering a likelihood), the training weights define
the estimated quantity: they must be the physics weights, up to a known class-prior factor (see below). Record both
kinds of weight in the `ml-artifact`.

### Class balancing and the prior

Balancing classes to equal Σw is normal and keeps the per-class shapes. The classifier then estimates p(s|x) under
the balanced prior. When the output is used as a probability, undo the prior shift with the odds:
`f_phys = r·f / (r·f + 1 − f)`, where r = (π_s/π_b)_physical / (π_s/π_b)_training. A selection cut needs no
correction; a probability that enters a likelihood or a combination does, and it still needs calibration
([uncertainty-and-calibration.md](uncertainty-and-calibration.md)).

For training, weights are usually normalized so that their mean is about one, keeping the loss scale and learning
rate independent of the luminosity. Steeply falling spectra (pT, rigidity, energy) put most of the weight at
threshold. To learn the full range, either flatten in that variable for training (keeping physics weights for
evaluation), or give the variable as a network input (parameterize) and check performance per bin.

### Negative weights (NLO generators, sWeights, subtraction)

A weighted loss `L = Σ w_i ℓ_i / Σ w_i` with signed weights is still a consistent estimate of the expected loss (a
ratio estimator).
The problem is the optimization. For a flexible model, a negative-weight event rewards making its own loss *large*,
so the model can drive its output to 0 or 1 on that event and the loss becomes unbounded below. A batch, or a
region of feature space, with net negative weight has no minimum at all. Symptoms are a training loss that falls
below zero, diverges or oscillates, and scores that pile up at the edges.

The options, in rough order of preference:

1. **Keep signed weights, make them harmless.** This works when negative weights are a small fraction of the total
   and are spread out. Use large batches (or accumulate gradients) so each batch has clearly positive net weight in
   every class. Normalize by `Σ|w|` rather than `Σw`, which keeps the sign but avoids dividing by a sum near zero
   (it rescales the effective learning rate by Σw/Σ|w| per batch).
   Regularize (weight decay, early stopping on a signed-weight validation loss) so the model cannot isolate
   individual events. Monitor the fraction of batches with `Σw ≤ 0` per class.
2. **Remove the negative weights before training** with a method that preserves the distributions: positive
   resampling (Andersen et al., EPJC 80 (2020) 1007, arXiv:2005.09375), cell resampling (Andersen & Maier, EPJC 82
   (2022) 433, arXiv:2109.07851), or a neural resampler (Nachman & Thaler, PRD 102 (2020) 076004,
   arXiv:2007.11586). Train on the resampled sample; evaluate with the original signed weights.
3. **Train with |w|.** This is simple and stable, but it learns the wrong density ratio wherever negative weights
   cluster (often exactly in the hard-radiation tails). It is acceptable only when you show the effect: compare
   weighted output distributions or the downstream sensitivity against option 1 or 2. Never use |w| for evaluation.
4. **Dropping negative-weight events** biases both training and evaluation; do not.

For likelihood-ratio estimation with signed weights, see Drnevich et al., Mach. Learn. Sci. Tech. 6 (2025) 045023,
arXiv:2410.10216. For sWeighted training data, see Borisyak, J. Phys. Conf. Ser. 1525 (2020) 012088,
arXiv:1912.02590.

Library behavior differs. Since 1.3.0, XGBoost raises a fatal error on negative instance weights instead of training
on them, so it needs one of options 2–3. A PyTorch weighted loss accepts them silently. A starting point is in
`assets/hep_losses.py` (`weighted_bce`).

## Analysis metrics

AUC alone is insufficient for optimization or validation. Use metrics computed with the physics weights at the
working point the analysis will use. `assets/hep_metrics.py` implements these in NumPy, with signed weights:

- **Background rejection at fixed signal efficiency**, 1/ε_B at ε_S = 30 %, 50 % or 70 % (or the analysis working
  point). This is the standard tagger figure of merit. It is far more sensitive than AUC in the region that matters.
- **Weighted ROC with signed weights.** Do not clip it. Local non-monotonicity is information about MC statistics.
- **Statistical uncertainty of a weighted efficiency.** For ε = W_pass/W_tot,
  `Var(ε) ≈ [(1−ε)² Σ_pass w² + ε² Σ_fail w²] / W_tot²`. Quote it next to every efficiency; an efficiency from a few
  high-weight events is noise.
- **Expected significance.** Use the Asimov formula `Z_A = sqrt(2[(s+b) ln(1+s/b) − s])` rather than `s/√b`, which
  overestimates Z unless s ≪ b (by about 7 % at s/b = 0.5). With a background uncertainty, use the version with an
  absolute σ_b. It assumes σ_b comes from an auxiliary Poisson control measurement (b̂ = m/τ, σ_b² = b/τ; G. Cowan,
  "Discovery sensitivity for a counting experiment with background uncertainty", note, 2012). A theory or modeling
  uncertainty is a different assumption; hand it to hep-statistics. Optimizing on observed significance is
  forbidden.
- **Effective MC statistics after selection.** Report `N_eff = (Σw)²/Σw²` per region. A selection that leaves a few
  effective events has an unusable template.
- **Final-result sensitivity.** The expected uncertainty or limit of the full fit (hep-statistics) is the metric
  that matters. Use the cheaper ones above to compare candidates, then confirm the choice on the final quantity.

PR-AUC, F1 and accuracy depend on the class prior; with arbitrary training normalization they carry no physics
meaning. Do not report them for a selection classifier.

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
  scaling variable such as ρ′. Simple and transparent, but one-dimensional (Dolen et al., JHEP 05 (2016) 156,
  arXiv:1603.00027).
- **Planing:** reweight the training samples so signal and background have the same mass distribution. This removes
  mass as a direct discriminant, but does not guarantee independence through correlated features (Chang, Cohen,
  Ostdiek, PRD 97 (2018) 056009, arXiv:1709.10106).
- **Adversarial:** an adversary predicts the mass from the score, and the classifier is penalized for its success
  (Louppe, Kagan, Cranmer, arXiv:1611.01046, NeurIPS 2017). Powerful, but training is unstable and sensitive to the
  adversary's capacity and to λ.
- **DisCo:** add λ·dCor²(score, mass) computed on background events in each batch. It is a differentiable,
  non-adversarial single-objective penalty, typically much more stable than adversarial training (Kasieczka & Shih,
  PRL 125 (2020) 122001, arXiv:2001.05310). Cost is O(B²) per batch, the penalty needs batches of several hundred
  events, and it should be computed in float32 even under mixed precision. Use |w| inside the penalty; distance
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
  one factor. The measurement itself is detector-response's (tag-and-probe, efficiency); the requirement to do it is
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

## Weak supervision and anomaly detection

- **CWoLa (classification without labels):** train on two mixed samples with different signal fractions. If the
  features of signal and background have the same distribution in both mixtures, the optimal mixed-sample classifier
  is optimal for signal versus background (Metodiev, Nachman, Thaler, JHEP 10 (2017) 174, arXiv:1708.02949; see
  also Komiske et al., PRD 98 (2018) 011502, arXiv:1801.10158). The assumption is the method: test it.
- **Resonant searches:**
  - **CWoLa hunting:** signal region against sidebands in mass (Collins, Howe, Nachman, PRL 121 (2018) 241803,
    arXiv:1805.02664). Requires features independent of mass for the background; otherwise it manufactures a bump.
  - **CATHODE:** learns the background density in the sidebands, interpolates it into the signal region, samples
    it, and classifies data against the samples (Hallin et al., PRD 106 (2022) 055006, arXiv:2109.00546).
  - **CURTAINs:** transforms sideband events into the signal region with a conditional flow (Raine et al., Front.
    Big Data 6 (2023) 899345, arXiv:2203.09470).
  - The LHC Olympics 2020 report compares methods on common benchmarks (Kasieczka et al., Rep. Prog. Phys. 84
    (2021) 124201, arXiv:2101.08320).
- **Validation required:**
  - injection tests over a range of signal fractions, including zero (no false bump);
  - k-folding so no event is selected by a model trained on it;
  - background-only closure with the full selection;
  - look-elsewhere treatment, handed to hep-statistics.
- **Autoencoder anomaly scores** reward low complexity: they flag events that are hard to reconstruct, not events
  that are rare, so a simple signal can score as "normal". Define what "anomalous" means against a background model
  before trusting a reconstruction-error cut.

## ML unfolding (training side)

**OmniFold** unfolds in full phase space by iterative classifier reweighting (Andreassen et al., PRL 124 (2020)
182001, arXiv:1911.09107):

- **Step 1:** reweight simulation at detector level to data.
- **Step 2:** pull the step-1 weights back to particle level. Train a particle-level classifier between the
  generator carrying those weights and the generator with the previous iteration's weights; this turns per-event
  weights into a function of particle-level features. Push those weights forward to the next iteration.
- **Iterations:** the number of iterations acts as the regularization.

This skill covers the classifier training, weight clipping and calibration, the ensemble over seeds, and bootstrap
resampling of data for the statistical uncertainty. Choosing the regularization, coverage and bias tests, and the
final binned result belong to hep-statistics.

## Validation

Inspect performance, calibration, overtraining, domain shift, score-tail populations, and nuisance dependence by
process, era, and phase space. Use independent samples or event-level resampling for uncertainty estimates.
Standard unweighted KS p-values may not apply to weighted train/test distributions. Compare weighted empirical CDFs
directly with a weighted KS statistic, or use a permutation or bootstrap test that resamples with the event weights
as importance weights, rather than dropping the overtraining check.

Check mass sculpting after score selections (see above). If the analysis fits a mass spectrum, validate the
background parameterization in each score category.

When the classifier score becomes an observable, propagate systematic changes through features, inference, and
category migration. Preserve preprocessing, feature order, units, model parameters, versions, and inference
checksums. Compare training and deployment scores for identical events.

Device and precision change the numbers too. The same model and seed give slightly different weights and scores on
CPU and GPU, on different GPU types or torch builds, and in fp32 versus mixed precision. Training losses differing at
the 0.1 % level were observed in the plugin's GPU validation runs (`<plugin root>/VALIDATION.md`, entry
TORCH-GPU-RUN). When a score is cut on, events near the cut move
between categories. Either evaluate in the build, device and precision the model was validated in, or measure the
migration on identical events across the deployment environments and treat it as a systematic. Never mix training
and inference environments silently.

## Deployment in experiment software and triggers

- **Offline frameworks:** export the frozen model to a framework the experiment supports, for example ONNX Runtime
  or ROOT's TMVA SOFIE ([export-and-deployment.md](export-and-deployment.md)). Then verify score agreement on
  identical events: the same inputs, preprocessing and feature order must give the same score within a stated
  tolerance.
- **Hardware triggers:**
  - **Constraints:** the latency budget (sub-microsecond to microseconds at a first-level trigger) and the
    resources force small models, fixed-point arithmetic, pruning and quantization-aware training.
  - **hls4ml** translates networks to FPGA firmware (Duarte et al., JINST 13 (2018) P07027, arXiv:1804.06913).
  - **Validation:**
    - compare the bit-accurate emulation with the floating-point model on identical events;
    - measure the trigger efficiency turn-on in data with an orthogonal trigger;
    - treat a firmware/emulation difference as a trigger systematic.

## Further reading

Feickert & Nachman, "A Living Review of Machine Learning for Particle Physics", arXiv:2102.02770 (continuously
updated), is the index to the literature. Check it for newer methods before claiming a method is the current one.
