# Learned Density Ratios for Reweighting Stored MC

The training side of a classifier-estimated density ratio that reweights stored simulation for one post-hoc
correction node: the likelihood-ratio trick, cross-fitting, probability calibration with the prior-ratio correction,
and the effective sample size of the weights. It is written for the simulator calibration workflow (Part B,
`docs/dev/simulator-calibration/simulator-calibration-v7.37.4-clean-en.md`: §3.6, §6.2, §6.7, §8.2 P0, G4 and G4-L;
the engine is hep-statistics, `../../hep-statistics/scripts/simcal_reweight.py`), and it applies to any classifier
reweighting of stored events (DCTR-style reweighting, BDT reweighting). Weights in training in general:
[ml-analysis-weights.md](ml-analysis-weights.md). Calibration in general:
[uncertainty-and-calibration.md](uncertainty-and-calibration.md). Sources were looked up on INSPIRE-HEP and arXiv on
2026-11-14 and read at abstract level; see the last section.

## What this method is, and what it is not

- **The method.** One node of the simulation chain has a kernel K(y | u, θ) with no usable analytic density (a
  post-hoc correction: a smearing, an efficiency or a response correction applied after the expensive simulation).
  The calibration needs the stored events at θ′ without resimulating, so each event gets the weight
  r(y, u; θ′) = K(y | u, θ′) / K(y | u, θ₀), estimated by a classifier. The classifier may be parameterized in θ′
  (one network for all θ′, with θ′ as an input; Baldi et al.) or trained once per θ′.
- **The boundary** (Part B §19-9, decided by approval A25 on 2026-11-14). In this workflow a learned ratio is used
  only to reweight stored MC events for one post-hoc correction node (§3.6 limits the method to "post-hoc
  correction models"). Every observable stays an MC prediction with its V_MC plus V_learn, and cross-fitting,
  probability calibration, the prior-ratio correction, P0 and G4-L all apply. Learning the likelihood or the
  posterior of θ from the observables (neural ratio, likelihood or posterior estimation; simulation-based
  inference, SBI) is **not** a method of the calibration workflow: the chain offers no candidate for it and a plan
  that declares it is refused, because no gate checks a learned likelihood. SBI outside this workflow:
  [sbi-training.md](sbi-training.md), with its validity in hep-statistics.
- **What a ratio cannot do.** Reweighting moves weight between stored events; it cannot create events where
  K(y | u, θ₀) is zero. If θ′ puts probability where θ₀ has none, no classifier fixes it: the method is not a
  candidate (the support condition of §3.6), and the effective sample size collapses near that boundary first.

## The likelihood-ratio trick

Label events drawn at θ′ as class 1 and at θ₀ as class 0, with class weights summing to W₁ and W₀. A classifier
trained with a proper loss (cross-entropy) approaches s(x) = W₁p₁(x) / (W₁p₁(x) + W₀p₀(x)), so

    r(x) = p₁(x) / p₀(x) = (W₀ / W₁) · s(x) / (1 − s(x)),   log r = logit s − log(W₁ / W₀).

Any monotone function of s keeps the information needed for the ratio, which is why a calibrated classifier
suffices (Cranmer, Pavez, Louppe). HEP uses: full phase-space reweighting and tuning with neural networks
(Andreassen and Nachman, DCTR) and reweighting with boosted decision trees (Rogozhnikov).

- **Condition on the node's inputs.** For a conditional kernel, give the classifier both y and u, and draw both
  classes on the same u (the stored inputs of the node, with K applied at θ′ and at θ₀). Then the joint ratio equals
  the conditional one, and E₀[r | u] = 1 for every u is a check (per bin of u).
- **Physics weights.** Train with the events' physics weights, as the class weights W₀ and W₁ then define. The
  weight that reaches the fit is the event-level product: physics weight × r.
- **Parameterized in θ′.** Draw θ′ for class 1 over the whole prior and record that training domain; a query
  outside it is extrapolation. Hand the classifier θ′ also for class 0 (for example the same θ′ values, assigned at
  random), so that θ′ alone does not separate the classes.

## Cross-fitting

**Why.** A classifier that has seen an event pulls s towards that event's label. Its weight then depends on the
event's own fluctuation: in-sample weights are biased towards the training sample, their spread is too small, and
V_MC from them is too small. A closure test on held-out events does not see this, because the held-out events are
not the ones that were reweighted in-sample. Part B §6.2: "the weights of each fold are computed by a classifier not
trained on that fold"; the G4-L negative test of §15.3.1 is exactly "no cross-fitting".

**How.**

1. Split the stored events into K folds **by group**, not by row: an event, its derived views, its candidates and
   anything sharing its simulation seed or run stay in one fold
   ([ml-analysis.md](ml-analysis.md), "Splits and leakage").
2. For fold k, train the classifier on the other K − 1 folds; inside them, keep a separate part for the calibration
   map (below). Apply the classifier and the map only to fold k.
3. Every event receives exactly one weight, from the classifier of its own fold. Record per fold the event-group
   identifiers, the classifier's hash, the calibration map and the seeds: the result shows structurally that
   training and application folds are disjoint.
4. Repeat the whole procedure with new seeds (and, where possible, new class-1 samples) for the spread part of
   V_learn.

Part B fixes neither K, the classifier family, nor the number of repeated trainings (decision sheet L2): choose them
before seeing results and record them.

**Leakage to avoid:** an event group in two folds; hyperparameters or early stopping tuned on the applied fold; the
calibration map fit on the applied fold; normalization constants or input scalings fit over all folds (fit them on
the training folds); class-1 samples produced with the seeds of the stored events they are compared with.

## Probability calibration

**Why it matters more here than for a cut.** The weight uses s / (1 − s): at s = 0.98, an error of ±0.01 in s doubles
r or lowers it by a third. Modern neural networks are often overconfident (Guo et al.), and boosted trees push scores to the
edges. A classifier that is good at ranking can still give wrong weights.

- **Reliability.** On a sample disjoint from training and from the applied fold, plot the weighted fraction of
  class 1 against the predicted s in bins; report ECE with its finite-sample floor
  ([uncertainty-and-calibration.md](uncertainty-and-calibration.md); `../assets/calibration.py`).
- **Maps.** Platt scaling, sigmoid(a · logit + b), is an affine correction of log r and needs little data;
  temperature scaling is Platt with b = 0. Isotonic regression is monotone and more flexible but needs more data,
  and its steps give a piecewise-constant r with ties. Calibration by density estimation of s under each class,
  r̂ = p̂₁(s) / p̂₀(s), is the construction of Cranmer et al. All of these are monotone in s: they fix the scale of
  the ratio along s, not a direction of x that the classifier missed. Only a closure on the observables (P0, G4-L)
  sees that.
- **Prior-ratio correction.** The factor W₀ / W₁ above is the prior ratio. Apply it exactly once, with the class
  weights of the sample the map was fit on: if the classes were balanced for training, or the calibration sample
  has other class sizes than the training sample, convert with the odds formula of
  [ml-analysis-weights.md](ml-analysis-weights.md), "Class balancing and the prior"
  (`calibration.py --prior-ratio-change`). A Platt offset b fit on an unbalanced sample already holds that sample's
  prior: correcting for it again is the common double-correction bug.
- **Ratio identities.** On held-out events, check E₀[r] = 1 and E₁[1/r] = 1 per fold, with their standard errors
  and the power of the test stated (`../../hep-statistics/scripts/ratio_estimation.py` is a calibratable example).
- **No silent renormalization.** Rescaling the weights so that Σ w·r = Σ w hides a miscalibration. For a
  normalized kernel a significant departure from E₀[r | u] = 1 is a failure to report, not a constant to divide out.

## Effective sample size of the weights

With event-level product weights w_i (physics weight × r), the Kish effective sample size is
N_eff = (Σ w_i)² / Σ w_i², computed per observable over the events that enter it (§6.7). Feasibility (P5) is
N_eff,k ≥ N_req,k at the worst θ′ within the prior, found by a Sobol scan of the prior, not only at its boundary.
Report also the largest-weight fraction and the Pareto k of the weight tail (the `node_diag` of §7.1).

- An estimated ratio gives an estimated N_eff. An overconfident classifier inflates the large weights and lowers
  N_eff; one that is too smooth hides large weights and makes N_eff look better than it is. Read N_eff together
  with the calibration checks.
- Clipping or smoothing the weights biases the prediction. If used, it is part of the method: it is applied in
  every fold and repetition and is seen by P0 and G4-L.
- Whether the stage-D G4 check (ESS and Pareto k) applies to learned weights, or only P5 at design, is an open
  reading (decision sheet L6): Part B applies G4 to "analytic reweighting or step-level reweighting" (§8.1).

## Uncertainty and the checks that judge it

- **V_learn** (§6.2) = the variation between repeated trainings + the square of the closure bias on held-out
  samples. It enters next to V_MC. In the toys (§6.6) each replica is retrained with
  independent training MC and a new seed, and N(0, V_learn^bias) is drawn once and added.
- **G4-L** compares `learned_closure` on held-out folds, propagated to θ, in the same form as P0. **P0** compares,
  at three or more θ′ including the worst-ESS point, the reweighted prediction with `resample` + `evaluate_from`.
- Hand over in the `ml-artifact` (task `reweighting`): the node and its inputs, the training domain in θ′, K and the
  fold assignment by group, the classifier and map hashes per fold, the prior-ratio factor and where it was applied,
  the reliability and ratio-identity results, the repeated-training spread, and N_eff per observable at the worst
  θ′.

## Sources

Looked up on 2026-11-14 with the plugin's literature lookup (INSPIRE-HEP, arXiv); read level abstract+metadata.
Journal details are given only where INSPIRE-HEP or arXiv lists them.

- K. Cranmer, J. Pavez, G. Louppe, "Approximating Likelihood Ratios with Calibrated Discriminative Classifiers",
  arXiv:1506.02169.
- P. Baldi, K. Cranmer, T. Faucett, P. Sadowski, D. Whiteson, "Parameterized neural networks for high-energy
  physics", arXiv:1601.07913, doi:10.1140/epjc/s10052-016-4099-4.
- A. Andreassen, B. Nachman, "Neural Networks for Full Phase-space Reweighting and Parameter Tuning",
  Phys. Rev. D 101 (2020) 091901, arXiv:1907.08209.
- A. Rogozhnikov, "Reweighting with Boosted Decision Trees", J. Phys. Conf. Ser. 762 (2016) 012036,
  arXiv:1608.05806.
- V. Chernozhukov et al., "Double/Debiased Machine Learning for Treatment and Causal Parameters", arXiv:1608.00060
  (the name and the K-fold construction of cross-fitting).
- C. Guo, G. Pleiss, Y. Sun, K. Q. Weinberger, "On Calibration of Modern Neural Networks", arXiv:1706.04599
  (overconfidence of modern networks; temperature scaling).
