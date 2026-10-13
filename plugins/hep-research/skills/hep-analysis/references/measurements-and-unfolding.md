# Cross Sections, Unfolding, and Combinations

This file keeps the measurement-design view. The response object and forward folding are detector-response's
([response and forward folding](../../detector-response/references/response-and-forward-folding.md)); unfolding
algorithms, regularization, coverage and combination methods are hep-statistics'
([unfolding](../../hep-statistics/references/unfolding.md)). Ownership: `docs/routing-contract.md`.

## Estimand and fiducial definition

Write the estimand in one sentence before the selection: quantity, species or process, variable and range, level,
frame, and what is held fixed. It goes in the spec's `estimand` field, and the validator refuses a spec without one.

**Truth-level objects (collider).** Define the objects on stable final-state particles (a lifetime cut such as
c tau > 10 mm is the usual convention; state the one used). Leptons are *dressed* (photons within a stated Delta R
added back), *bare* (after final-state radiation) or *Born* (before it); dressed leptons are the least model-dependent
and match what the detector sees. *Prompt* means not from a hadron or tau decay; say how taus are treated. Jets are
clustered from stable particles with neutrinos either included or excluded, stated.

**Fiducial cuts, Rivet-style.** The fiducial region applies to the truth objects the cuts that mirror the reconstructed
selection (thresholds, |eta| ranges, isolation on stable particles), never cuts on partons, the boson's mass before
radiation, or invisible particles that the measurement cannot see. Then the extrapolation from the fiducial region to
the full phase space, if wanted, is a separate, model-dependent step with its own uncertainty. Publish the definition as
code (a Rivet routine or equivalent) so a prediction can be computed in the same region.

**Result levels (cosmic rays).** Top of instrument: corrected for the detector, still including interactions in the
material above it if any. Top of atmosphere: corrected for the overburden of a balloon or ground instrument. Local
interstellar: additionally corrected for solar modulation, which needs a model (for example the force field,
`solar_modulation_force_field.py`) and its epoch; a modulated or demodulated flux is model-dependent and is labelled
so. A profile may define its own levels (for example a top-of-instrument term in its vocabulary).

One-sentence estimands (synthetic examples):

- Collider: "The differential cross section d sigma / d pT of the leading dressed muon in pp -> Z/gamma* -> mu mu, for
  pT from 20 to 200 GeV, at particle level in the fiducial region of two prompt muons with pT > 20 GeV and |eta| < 2.4,
  per bin of 10 GeV."
- Cosmic ray: "The helium flux per rigidity bin from 2 to 100 GV at top of instrument, averaged over each Bartels
  rotation of the period, for particles above the geomagnetic cutoff selection."
- Neutrino: "The flux-averaged charged-current muon-neutrino cross section per nucleon on the target nucleus, in bins
  of muon momentum and angle, at particle level, for the stated neutrino flux."

## Cross sections

A simple fiducial estimate is `sigma_fid=(N_obs-N_bkg)/(L*C)`. Define whether C includes reconstruction, selection efficiency, and migration, consistently with the truth-level fiducial region. Extrapolation to a total cross section introduces acceptance and theory dependence. State whether branching fractions are included.

Differential measurements divide by bin widths: `d_sigma/dx_i=sigma_i/delta_x_i`. Normalized distributions carry a sum constraint and generally have nondiagonal, potentially singular covariance. Compare to theory in the constrained subspace or with an appropriate generalized inverse rather than an ordinary inverse of a singular matrix.

## Design checklist for a corrected measurement

- Level of the result: detector level with a published response, or a truth-level (unfolded) spectrum. Decide it
  before unblinding, with the consumers of the result in mind.
- Fiducial region at truth level, and which corrections (efficiency, acceptance, migration, fakes) the response
  carries versus which are applied outside it; each correction is counted once.
- Binning chosen with the resolution in view (bin widths not much below the resolution at that point).
- Where the response comes from (simulation, data-driven corrections), and which sample tests the closure; closure on
  the events that built the response is optimistic.
- Which systematics move the response, and that each is propagated through response, background and efficiency
  with one nuisance.
- The method, regularization criterion and coverage test are fixed in the plan and executed by hep-statistics.

## Steeply falling spectra and spillover

With finite resolution, a steeply falling spectrum feeds more events from lower true values into a bin than it loses to
higher ones (spillover), so the measured spectrum sits above the true one, more so where the resolution degrades, as
near the maximum detectable rigidity of a spectrometer. For a power law of index gamma and a Gaussian resolution of
relative width s in log E, the measured-to-true ratio is about `exp((gamma - 1)^2 s^2 / 2)`.

- **Forward-fold or unfold.** When the result will be compared with models, forward-folding a parametrized spectrum
  through the response keeps the statistics simple and avoids regularization; unfold when a model-independent
  truth-level spectrum is the deliverable, with the regularization and coverage fixed in advance. Either way the
  computation belongs to hep-statistics ([astroparticle statistics](../../hep-statistics/references/astroparticle-statistics.md),
  [unfolding](../../hep-statistics/references/unfolding.md)) and the response to detector-response.
- **Binning.** Bin widths of about one to two resolution sigma; check the purity (fraction of reconstructed events in a
  bin that come from the same true bin) and the stability (fraction of true events reconstructed in their own bin),
  both well above one half, and merge bins where they are not.
- **Resolution tails.** Non-Gaussian tails (charge or momentum mismeasurement, interactions) dominate the spillover at
  the highest bins: measure the tail on data where possible, vary it as a systematic, and report the highest bin with
  the tail treatment stated.

Worked example (synthetic): gamma = 2.7 with s = 0.10 gives a 1.5% excess; with s = 0.30 (a bin near the maximum
detectable rigidity) about 14%, far above a few-percent statistical error.

## Combinations

Prefer joint likelihoods when available, with nonoverlapping events and compatible nuisance definitions. When only estimates and covariance are available, BLUE under linear Gaussian assumptions uses `w=V_inverse*1/(1^T*V_inverse*1)`. Check conditioning, positive semidefiniteness, and correlation sources. Negative BLUE weights alone are not evidence of an error. Relative (multiplicative) errors scaled with the measured values bias BLUE low (Peelle's Pertinent Puzzle): iterate with the errors rescaled to the combined value; hep-statistics has the diagnostics (`covariance_fit.py`, [core statistics guide](../../hep-statistics/references/core-stats-guide.md)).

Deliver edges, central values, statistical/systematic/total covariance, fiducial definitions, units, response conventions, regularization settings, and machine-readable tables. Explain whether covariance components can be added directly.
