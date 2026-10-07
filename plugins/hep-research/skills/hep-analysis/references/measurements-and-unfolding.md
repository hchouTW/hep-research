# Cross Sections, Unfolding, and Combinations

This file keeps the measurement-design view. The response object and forward folding are detector-response's
([response and forward folding](../../detector-response/references/response-and-forward-folding.md)); unfolding
algorithms, regularization, coverage and combination methods are hep-statistics'
([unfolding](../../hep-statistics/references/unfolding.md)). Ownership: `docs/routing-contract.md`.

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

## Combinations

Prefer joint likelihoods when available, with nonoverlapping events and compatible nuisance definitions. When only estimates and covariance are available, BLUE under linear Gaussian assumptions uses `w=V_inverse*1/(1^T*V_inverse*1)`. Check conditioning, positive semidefiniteness, and correlation sources. Negative BLUE weights alone are not evidence of an error.

Deliver edges, central values, statistical/systematic/total covariance, fiducial definitions, units, response conventions, regularization settings, and machine-readable tables. Explain whether covariance components can be added directly.
