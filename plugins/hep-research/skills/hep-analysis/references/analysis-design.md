# Analysis Design, Data Quality, and Blinding

## Establish the analysis contract

Complete `<plugin root>/skills/hep-analysis/assets/analysis-contract.yaml`. Identify the collision system, energy, era, data format, target process, fiducial phase space, observables, and POI. State the measurement precisely: inclusive/fiducial/differential cross section, branching fraction, mass, coupling, or signal strength. For signal strength, document the reference cross section and branching ratio.

Keep unknown physical inputs null or explicitly unresolved. Independent exploration may continue, but reported yields and inference require sourced inputs. Synthetic demonstrations may define arbitrary values if both files and reports label them synthetic.

## Event and object definitions

Record run/luminosity-block/event identification, duplicate removal across data streams, data-quality flags, certified run/luminosity selections, and luminosity sources. A repeated event in different streams must not be counted twice. MC event identifiers may not be globally unique: include dataset, file, or production identity as needed.

Specify identification, isolation, kinematic acceptance, overlap removal, primary-vertex selection, pileup mitigation, and trigger matching. Correcting before ordering and ordering before correcting can give different results; follow the formal object definition. Use wrapped differences for azimuthal angles and distinguish pseudorapidity from rapidity. Document energy and momentum units.

Check era-dependent trigger menus, prescales, turn-ons, plateaus, and OR/overlap logic. Do not multiply efficiencies of correlated trigger paths as though they were independent. MC trigger scale factors must match the selection, run period, and object requirements.

## Regions and categories

Signal regions (SRs) drive signal inference, control regions (CRs) constrain backgrounds, and validation regions (VRs) test extrapolation. A sideband is a specified interval in an observable; it is not automatically background-only. Record region membership and test exclusivity. Events may appear in multiple diagnostic plots, but not in independent Poisson channels without accounting for overlap.

Choose binning using resolution, MC statistics, background stability, systematic uncertainties, and expected sensitivity. Use simulation, independent optimization samples, or Asimov data to set the strategy. Avoid repeatedly changing categories after examining signal-sensitive observations.

## Blinding

Define the mask by region, observable interval, and category. Real data arrive as a released blinded derivative, prepared by the data custodian outside the agent session; the agent never reads the unblinded values. In-code masks are defence in depth on such inputs, and the method for synthetic data: filter at read time, or set blinded bins to NaN before plotting, ratio or pull computation. Drawing a shaded box over plotted data does not blind it, so check the rendered output shows no observed points in the region. Apply it to plots, yield tables, ratios, pulls, debug output, caches, and notebook displays. Store Asimov/expected results separately from observed results. Do not use the actual SR count to optimize the supposedly blinded model.

Under applicable collaboration rules, record the frozen commit, model, diagnostics, and unblinding conditions. Never unblind in the agent session: an authorized person does it outside the session once the applicable requirements are satisfied; do not invent approval requirements for unrelated routine work. If an unblinded input reaches the session, stop, report it, and do not use or optimize against it.

## Completion criteria

Definitions map to configuration or code; the input manifest is complete; units, triggers, luminosity, region overlaps, and masks are verifiable. Explain which conclusion each missing input prevents, rather than giving only generic caveats.
