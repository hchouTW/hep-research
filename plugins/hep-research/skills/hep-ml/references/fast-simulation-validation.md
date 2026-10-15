# Generative Fast Simulation: Training and Validation

Learned surrogates of detector simulation (calorimeter showers, full events, detector response) and of event
generation. Generic generative-model mechanics are in [generative-models.md](generative-models.md). Validation
against the full simulation as a statement about the detector is hep-detector's
([detector-simulation.md](../../hep-detector/references/detector-simulation.md)). This file covers the
model-side choices and the evidence the ML side must deliver. Citations were looked up on INSPIRE-HEP or arXiv on
2026-10-13.

## Families in use

- **GANs:** CaloGAN (Paganini, de Oliveira, Nachman, PRL 120 (2018) 042003, arXiv:1705.02355) started the line.
  Fast to sample, but mode collapse and training instability make the tails unreliable.
- **Normalizing flows:** CaloFlow (Krause & Shih, PRD 107 (2023) 113003, arXiv:2106.05285). Exact likelihood, stable
  training, and a usable density for diagnostics. Sampling cost depends on the architecture: autoregressive flows are
  slow in one direction, and distillation is the usual fix.
- **Diffusion and flow matching** (Lipman et al., arXiv:2210.02747, for flow matching): currently the highest
  fidelity in community comparisons, at the price of many network evaluations per sample. Distillation or
  consistency methods trade fidelity for speed; measure both.
- **Point-cloud generators:** for sparse, high-granularity calorimeters, generating hits as a set avoids the cost of
  mostly empty voxel grids.

The CaloChallenge 2022 report (Krause et al., arXiv:2410.21611; the Rep. Prog. Phys. 88 (2025) 116201 details are
`unverified`: not on the arXiv page) compares these
families on common datasets and metrics. Use its datasets and metrics as the baseline vocabulary.

## Conditioning and the training domain

Fast simulation is conditional:

- **Conditions:** incident energy, angle, position, particle type, and sometimes detector conditions.
- **Training domain:** the conditioning range is the training domain. Record it in the `ml-artifact`. Flag requests
  outside it; extrapolating in energy is the most common silent failure.
- **Steep spectra:** sample the conditions log-uniformly (or flat in the variable that matters) for training, so the
  high-energy end is not starved.
- **Per-condition validation:** validate every metric below per condition bin, not only integrated.

## Physics constraints to check

- **Energy:** total deposited energy against the incident energy (sampling fraction, leakage). Check the response
  and resolution per energy bin, not only the mean.
- **Positivity and sparsity:** fraction of empty cells, the distribution of cell energies near the readout
  threshold, and no negative energies. Many models need an explicit treatment of the threshold.
- **Shower shape:**
  - longitudinal and lateral profiles and their moments (centroid, width) per layer;
  - layer energy fractions;
  - correlations between layers. Independent per-layer agreement is not enough.
- **Tails and rare topologies:** late or punch-through showers, early conversions, leakage. These matter for
  resolution tails and for fake rates, and generative models under-populate them.

## Metrics

No single number validates a fast simulation. Report a set:

1. **High-level feature histograms** (energies, shower moments, layer fractions), each with a separation power or χ²
   against the full simulation, using reference samples independent of the training.
2. **Classifier two-sample test.** Train a classifier to separate generated from full-simulation showers, on low-level
   inputs (cells) and on high-level features. AUC = 0.5 means indistinguishable. It is one of the most sensitive
   CaloChallenge metrics, reported alongside the others; no single metric suffices.
   - **Calibrate the test:** report the AUC of the same classifier on two independent full-simulation samples, so
     the 0.5 floor includes finite-sample noise.
   - **Report its power.** An AUC of 0.5 alone shows nothing: a weak classifier or a small sample also gives 0.5.
     Inject a known distortion into a full-simulation sample (a few percent on a layer energy, a shifted shower
     depth), rerun the same test, and report the smallest distortion it detects. Classifier two-sample tests:
     Lopez-Paz & Oquab, arXiv:1610.06545 (abstract read 2026-10-14).
   - **Find where it fails:** inspect which events the classifier finds easiest to separate.
3. **Fréchet and kernel physics distances (FPD, KPD)** on high-level features. These are sample-based metrics with
   defined uncertainties, preferred to image-based FID for physics (Kansal et al., PRD 107 (2023) 076017,
   arXiv:2211.10295).
4. **Downstream closure.** Run the experiment's reconstruction and a representative analysis selection on generated
   and full-simulation samples. Compare reconstructed energy scale and resolution, identification efficiencies, and
   the analysis observable. This is the metric that decides use, and it needs hep-detector.
5. **Timing and resources:** per shower, on the target hardware, at the batch size the production would use, against
   the full simulation. A speed-up that disappears at production batch size is not a speed-up.

## Statistical meaning of generated samples

A generator trained on N events does not create N′ ≫ N independent events' worth of information. Its samples can
interpolate and smooth, and in some regimes estimate a distribution better than the raw training histogram (Butter
et al., "GANplifying Event Samples", SciPost Phys. 10 (2021) 139, arXiv:2008.06545). But the gain is bounded and
model-dependent.

- **Estimate the effective statistical power.** For example, compare to histograms built from training subsets of
  increasing size.
- **Carry a model uncertainty.** Use an ensemble of generators, or the difference to the full simulation in the
  closure, as a systematic.
- **Never treat the generator as an independent sample** of the full simulation.

## Deliverables

- the `ml-artifact` with the conditioning range, training samples and their simulation version, and model hash;
- metric set 1–5 per condition bin, with the reference-sample sizes;
- the list of known failures (tails, edges, rare particle types) and the regions where the fast simulation must not
  be used;
- handoff to hep-detector for the detector-level validation statement.
