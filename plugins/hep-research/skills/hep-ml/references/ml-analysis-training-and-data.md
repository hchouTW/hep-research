# Training choices: hyperparameters, inputs, training on data, weak supervision, ML unfolding

Part of [ml-analysis.md](ml-analysis.md), the hep-ml entry reference for machine learning in an analysis
(read its splits and metrics first). Citations give arXiv identifiers looked up on INSPIRE-HEP or arXiv on
2026-10-13; they point to the method, not to a validated recipe for any experiment.

## Hyperparameter search

Search with the analysis metric, not the training loss alone, and with folds that respect the grouping key (grouped
k-fold, `make_grouped_splits.py --folds K`): an ungrouped search selects configurations that exploit leakage. When the
selected model's performance is also reported, use nested cross-validation (an inner grouped search inside each outer
grouped fold) or a test split never used in the search. Seed every trial, record all trials, and confirm the winner
with more seeds ([reproducibility.md](reproducibility.md), [ablation-and-design-review.md](ablation-and-design-review.md));
budget-saving strategies are in [training-at-scale.md](training-at-scale.md).

## Validate the inputs before training

Before a simulation-trained model is trained, compare every input feature between data and simulation in a control
region (shapes, correlations between pairs, out-of-range and default values such as -999 or zero-filled missing
objects). A feature the simulation mismodels becomes a model the simulation mismodels, and a domain-shift check after
training cannot say which input caused it. Drop, correct or carry as a nuisance any input that fails, and record the
comparison with the training record.

## Training on data and blinding

Weakly supervised and data-driven methods train on data, so the training itself can unblind. Classification without
labels (CWoLa: a classifier trained to separate two mixed samples, for example a signal region and a sideband;
Metodiev, Nachman & Thaler, JHEP 10 (2017) 174, arXiv:1708.02949, read 2026-10-14) and CATHODE (a density estimator
trained outside the signal region, interpolated into it and used to sample background, then a classifier of data
against those samples; Hallin et al., PRD 106 (2022) 055006, arXiv:2109.00546, read 2026-10-14) both look at
signal-region data; DCTR (a classifier-based full phase-space reweighting, also used to tune simulation to data;
Andreassen & Nachman, PRD 101 (2020) 091901, arXiv:1907.08209, read 2026-10-14) does when it is trained on data.
Before such a training, the blinding policy (hep-measurement) must say which data the training may see, and the training,
selection and test samples must keep the signal region's results hidden until unblinding: k-fold over the signal
region with the score of each event from a model that never saw it, no hyperparameter tuning on the signal region,
and checks run first on sidebands or on simulation with an injected signal. Record what data the model saw in the
training record.

**Freeze before training.** Before the first training run, write a `decision_record`
(`contracts/schemas/decision_record.json`) that fixes the training set-up:

- `category`: `"other"` (the closed list has no ML category);
- `decision`: the labels, the features (and any variable deliberately excluded, such as the resonance mass), the
  training domain (which samples and regions the training may see) and the SHA-256 of the split manifest file;
- `artifacts`: the split manifest as `{ref, sha256}`, with the same file SHA-256;
- `seen`: bound to the analysis's exposure record: `through_seq` = the number of entries that existed at decision
  time, `entries_sha256` = the canonical SHA-256 of exactly those entries.

Check it with `python3 contracts/lineage.py decision <record> --exposure <exposure record>` (exit 0 = the binding holds;
it also prints the exposure at decision time, which should be `unexposed` for a training that must not see the signal
region). Later appends to the exposure record keep the binding; an edited history, a `seen` that leaves out entries
dated before the decision, or a decision dated before entries it counts fail. It also opens each `artifacts[].ref`
(relative to the record's folder, or to `--artifacts-root DIR`) and fails when the file's SHA-256 differs or the file
is missing (`lineage.artifact_mismatch`, `lineage.artifact_missing`). It does not read the `decision` text: check that
the SHA-256 written there is the one in `artifacts`, and refuse a split that no longer matches. A changed split, feature list or training domain is a
new decision record (`supersedes` the old one), not an edit. Example: `assets/pretraining-decision.example.json` with
`assets/pretraining-exposure.example.json` and `assets/pretraining-split.example.json` (synthetic).

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
- **Density-based anomaly detection:** ANODE learns the data density in the sidebands and interpolates it into the
  signal region to form a data-to-background likelihood ratio; its authors report robustness against systematic
  differences between signal region and sidebands (Nachman & Shih, PRD 101 (2020) 075042, arXiv:2001.04990, abstract
  read 2026-10-14). CATHODE (above) samples from such a density and classifies. Every weakly supervised method depends
  on its background-modelling assumption (features independent of the resonant variable, or a correctly
  interpolated density): test it with injection at zero signal and with features correlated with the mass.
- **Unsupervised (background-only) anomaly detection:** train on background or on data dominated by it, score
  departures; validate on background only (no false excess after the full selection) and with injected signals of
  several types and sizes, because sensitivity depends on what the score rewards.
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

- **Unmatched events:** simulated events that pass the particle-level selection but not the detector-level one
  (inefficiency) and the reverse (fakes, events with no particle-level match) must enter the iterations explicitly;
  the unfolded result is otherwise biased by the simulation's efficiency and fake rate. State how they are handled.
- **Prior dependence:** the result depends on the starting simulation at finite iterations; repeat with a reweighted
  or alternative generator as the prior and carry the difference.

This skill covers the classifier training, weight clipping and calibration, the ensemble over seeds, and bootstrap
resampling of data for the statistical uncertainty. Choosing the regularization, coverage and bias tests, and the
final binned result belong to hep-statistics.
