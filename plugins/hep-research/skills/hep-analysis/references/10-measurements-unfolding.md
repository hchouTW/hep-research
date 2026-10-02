# Cross Sections, Unfolding, and Combinations

## Cross sections

A simple fiducial estimate is `sigma_fid=(N_obs-N_bkg)/(L*C)`. Define whether C includes reconstruction, selection efficiency, and migration, consistently with the truth-level fiducial region. Extrapolation to a total cross section introduces acceptance and theory dependence. State whether branching fractions are included.

Differential measurements divide by bin widths: `d_sigma/dx_i=sigma_i/delta_x_i`. Normalized distributions carry a sum constraint and generally have nondiagonal, potentially singular covariance. Compare to theory in the constrained subspace or with an appropriate generalized inverse rather than an ordinary inverse of a singular matrix.

## Response matrices

Define `y_reco=R*x_truth+b`. Specify axis orientation, efficiency treatment, missed truth events, out-of-fiducial contributions/reconstruction fakes, and luminosity. Columns normalized to unity generally no longer encode efficiency loss; do not mix that convention with one that includes losses.

Check folding with a small hand-calculable matrix. Document purity/stability denominators and assess conditioning, rank, and identifiable truth bins. Signed MC contributions are not literal transition probabilities and need suitable response-estimation and uncertainty treatment.

## Unfolding methods

Choose forward-folded likelihoods, matrix methods, regularized inversion, or iterative Bayesian unfolding according to the target and project. Regularization and stopping rules trade variance against bias. Use predefined criteria and independent truth variations, not visual smoothness alone.

Validate nominal closure, alternative truth shapes, stress tests, injections, pulls/coverage, response MC statistics, backgrounds, detector/theory effects, and regularization bias. Building the response and testing closure on the same events may be optimistic; split samples or use valid resampling.

Bootstrap at event level, preserving truth/reconstruction pairing and signed weights. Independently resampling matrix cells destroys event correlations. Propagate each systematic consistently through response, background, and efficiency; use the same nuisance variation when one source affects several components.

## Combinations

Prefer joint likelihoods when available, with nonoverlapping events and compatible nuisance definitions. When only estimates and covariance are available, BLUE under linear Gaussian assumptions uses `w=V_inverse*1/(1^T*V_inverse*1)`. Check conditioning, positive semidefiniteness, and correlation sources. Negative BLUE weights alone are not evidence of an error.

Deliver edges, central values, statistical/systematic/total covariance, fiducial definitions, units, response conventions, regularization settings, and machine-readable tables. Explain whether covariance components can be added directly.
