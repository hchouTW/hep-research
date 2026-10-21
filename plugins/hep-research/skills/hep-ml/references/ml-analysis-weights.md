# Event weights in ML training

Part of [ml-analysis.md](ml-analysis.md), the hep-ml entry reference for machine learning in an analysis
(read its splits and metrics first). Citations give arXiv identifiers looked up on INSPIRE-HEP or arXiv on
2026-10-13; they point to the method, not to a validated recipe for any experiment.

## Event weights

Two kinds of weight have different jobs and must be kept apart:

- **Physics weights** (cross section × luminosity / Σw_gen, generator weights, scale factors, pileup or reweighting
  corrections) define yields, templates and efficiencies. They are always the weights used for evaluation, and their
  signs are kept (hep-measurement owns their bookkeeping).
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
4. **Drop negative-weight events from training only.** The classifier then learns the positive-weight density
   instead of the signed (positive minus negative) one, the same kind of distortion as option 3, which learns positive
   plus negative. It is acceptable only under option 3's condition: show the effect against option 1 or 2. Never drop
   them from evaluation: that biases every yield, efficiency and working point.

For likelihood-ratio estimation with signed weights, see Drnevich, Jiggins, Katzy, Cranmer, arXiv:2410.10216 (the
arXiv page, read 2026-10-14, gives no journal reference; the Mach. Learn. Sci. Tech. 6 (2025) 045023 details are
`unverified`). For sWeighted training data, see Borisyak & Kazeev, J. Phys. Conf. Ser. 1525 (2020) 012088,
arXiv:1912.02590.

Library behavior differs (documentation read 2026-10-14):

- **XGBoost:** since 1.3.0 a fatal error on negative instance weights; it needs option 2 or 3.
- **LightGBM:** its parameter documentation says weights "should be non-negative" and does not say what happens
  otherwise; treat negative weights as unsupported (option 2 or 3).
- **TMVA BDT:** the `MethodBDT` class reference lists treatments that ignore negative-weight events in training (both
  are option 4 in effect), boost them with the inverse boost weight, or pair negative- with positive-weight events and
  "annihilate" them; check the option strings (`NegWeightTreatment`) in the TMVA user guide before use (`unverified`:
  the mapping of class members to option strings was not read).
- **PyTorch:** a weighted loss accepts them silently; `assets/hep_losses.py` (`weighted_bce`) is a starting point, and
  `assets/train_classifier.py --negative-weights resample` applies cell resampling.
