# Analysis Design, Data Quality, and Blinding

## Write the measurement spec

The skill has one spec format, the JSON `measurement-spec`: copy `<plugin root>/skills/hep-analysis/assets/measurement_spec.template.json` and fill it with the field guide [measurement_spec.template.md](../assets/measurement_spec.template.md). It covers collider, cosmic-ray and neutrino normalization kinds. Start with the estimand in one sentence (quantity, species or process, variable and range, level, frame, what is held fixed), then the observable, period, selections, backgrounds, corrections, systematics and blinding. For signal strength, document the reference cross section and branching ratio. Inference settings (parameter of interest, test statistic, confidence level) are not part of the spec: they belong to hep-statistics. Experiment conventions live in the bound profile (an experiment profile may have its own spec format and auditor).

Keep unknown physical inputs `unknown` or `not-provided` and list them in `unresolved_inputs`. Independent exploration may continue, but reported yields and inference require sourced inputs. Synthetic demonstrations may define arbitrary values if both files and reports label them synthetic.

## Event and object definitions

Physics rules any pipeline must implement (code patterns: [analysis data pipelines](../../hep-computing/references/analysis-data-pipelines.md)):

- **Stable event keys.** Identify events by run, luminosity block (or time) and event number, plus dataset or production identity for simulation; compare outputs by these keys, never by row index.
- **Duplicates across streams.** An event recorded in several data streams is counted once; remove duplicates before any yield.
- **Signed weights.** Keep generator weights signed through every step and normalize with the signed pre-skim sum ([weights and normalization](weights-normalization.md)).

Record run/luminosity-block/event identification, duplicate removal across data streams, data-quality flags, certified run/luminosity selections, and luminosity sources. A repeated event in different streams must not be counted twice. MC event identifiers may not be globally unique: include dataset, file, or production identity as needed.

Specify identification, isolation, kinematic acceptance, overlap removal, primary-vertex selection, pileup mitigation, and trigger matching. Correcting before ordering and ordering before correcting can give different results; follow the formal object definition. Use wrapped differences for azimuthal angles and distinguish pseudorapidity from rapidity. Document energy and momentum units.

Check era-dependent trigger menus, prescales, turn-ons, plateaus, and OR/overlap logic. Do not multiply efficiencies of correlated trigger paths as though they were independent. MC trigger scale factors must match the selection, run period, and object requirements.

## Trigger efficiency from data

- **Orthogonal reference trigger (collider).** Measure the efficiency of the signal trigger on events recorded by a
  trigger that does not depend on the probed quantity (a muon trigger for a jet or missing-energy trigger), with the
  offline selection applied: `eps = N(reference and signal trigger) / N(reference)`, binned in the offline variable.
- **Bootstrap.** For a high threshold, chain the efficiencies: `eps(T2) = eps(T2 | T1) x eps(T1)`, each measured where
  the looser trigger T1 (often prescaled) is itself efficient or measured.
- **Unbiased or prescaled samples (space and fixed-target instruments).** A minimum-bias or unbiased trigger recorded
  with a prescale p gives `eps = N(unbiased and physics) / N(unbiased)` on the recorded events; the prescale cancels in
  the ratio, but every rate or exposure computed from the unbiased stream is multiplied by p, and the unbiased sample's
  own selection (its acceptance, a different detector requirement) must be applied to both numerator and denominator.
- **Trigger-bias checks.** The reference must not bias the probed variable: compare two different references, check the
  efficiency versus variables the reference could correlate with (multiplicity, pileup, time), and use exact binomial
  intervals near 0 or 1 (hep-statistics, or `core/stats/tail_estimation.py`).

Worked example (synthetic): an unbiased stream with prescale 100 records 2000 events, 1900 of which also fire the
physics trigger: eps = 0.950 with a 68% Clopper-Pearson interval of about [0.945, 0.955]; the unbiased stream stands for
200000 triggers. A bootstrap with eps(T2 | T1) = 0.90 and eps(T1) = 0.98 gives eps(T2) = 0.882.

## Regions and categories

Signal regions (SRs) drive signal inference, control regions (CRs) constrain backgrounds, and validation regions (VRs) test extrapolation. A sideband is a specified interval in an observable; it is not automatically background-only. Record region membership and test exclusivity. Events may appear in multiple diagnostic plots, but not in independent Poisson channels without accounting for overlap.

Choose binning using resolution, MC statistics, background stability, systematic uncertainties, and expected sensitivity. Use simulation, independent optimization samples, or Asimov data to set the strategy. Avoid repeatedly changing categories after examining signal-sensitive observations.

## Blinding

Define the mask by region, observable interval, and category. Real data arrive as a released blinded derivative, prepared by the data custodian outside the agent session; the agent never reads the unblinded values. In-code masks are defence in depth on such inputs, and the method for synthetic data: filter at read time, or set blinded bins to NaN before plotting, ratio or pull computation. Drawing a shaded box over plotted data does not blind it, so check the rendered output shows no observed points in the region. Uncertainties, ratios and pulls are computed on the blinded data or withheld, never from the unblinded values. A pre-unblinding check of a blinded region uses simulation, Asimov data, or control and validation regions. Apply it to plots, yield tables, ratios, pulls, debug output, caches, and notebook displays. Store Asimov/expected results separately from observed results. Do not use the actual SR count to optimize the supposedly blinded model.

Under applicable collaboration rules, record the frozen commit, model, diagnostics, and unblinding conditions. Never unblind in the agent session: an authorized person does it outside the session once the applicable requirements are satisfied; do not invent approval requirements for unrelated routine work. If an unblinded input reaches the session, stop, report it, and do not use or optimize against it.

## Completion criteria

Definitions map to configuration or code; the input manifest is complete; units, triggers, luminosity, region overlaps, and masks are verifiable. Explain which conclusion each missing input prevents, rather than giving only generic caveats.
