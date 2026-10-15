# Models: heliospheric modulation of galactic cosmic rays

What this profile computes, what it only documents, and what each statement rests on. Claims in brackets are in
`evidence/claims.json`; text marked `unverified` has no source opened for this profile and is context only.

## Force field (computed, by reference)

- **Model** [helmod:C01, C02]: for a spherically symmetric heliosphere with a diffusion coefficient separable in r and
  proportional to rigidity, and negligible radial streaming, the phase-space density is constant along
  T + |Z| phi(r), so J_TOA(T) = p(T)^2 / p(T + |Z| phi)^2 J_LIS(T + |Z| phi) with p^2 = T (T + 2m) = E^2 - m^2.
  Per nucleon the shift is (|Z|/A) phi [helmod:C04]. One parameter, phi, per period (in GV; |Z| phi in GeV).
- **Implementation**: `<plugin root>/skills/hep-measurement/scripts/solar_modulation_force_field.py` (owned by
  hep-measurement; total kinetic energy, kinetic energy per nucleon or rigidity; power-law or tabulated LIS;
  `--demodulate` for one measured point; `--phi-uncertainty`). This profile does not reimplement it: `scripts/predict.py`
  runs it as a separate process and compares it with the closed forms of `scripts/derive.py`.
- **Derivation**: `derivations/derivation-record.md` (analytic derivation under the assumptions above).

## Validity range and known limits

| Limit | Statement | Source |
|---|---|---|
| Low energy | breaks down below about 300 MeV/n for protons and 250 MeV/n for alpha particles (streaming no longer negligible); `predict.py --point` flags such points | [helmod:C03] |
| Rigidity dependence | the force field "does not allow for any rigidity dependent effects" beyond the single shift | [helmod:C05] |
| Time dependence | cannot predict how phi changes with time; one phi per period, fitted | [helmod:C05] |
| Charge sign, drift | absent from the formula; studies use different phi for positive and negative charges | [helmod:C05] |
| Degeneracy | phi is degenerate with the injection and transport parameters that shape the LIS; report it as a degenerate direction | [helmod:C05] |
| Transients | Forbush decreases, solar energetic particle events and other short-timescale changes are outside the steady-state model | script docstring (hep-measurement) |

The closed-form benchmark checks the implementation, not the physics: it includes points below the low-energy limit on
purpose. A prediction there is not a statement about measured fluxes.

## Other models (documented only)

None of the following is implemented, run or verified in this profile or plugin; no source for them was opened for
this profile, so the descriptions are `unverified` context to help a user state which model produced a number.

- **Convection-diffusion (transport) equation.** The force field is the zero-streaming limit of the spherically
  symmetric steady-state transport equation with diffusion, convection by the solar wind and adiabatic energy change
  ([helmod:C01] states only the negligible-streaming condition; the full equation is not quoted here). Solving the full equation (with streaming)
  changes the low-energy spectrum where the force field breaks down.
- **Drift models.** Gradient, curvature and current-sheet drifts make modulation depend on the sign of the charge and
  on the polarity of the solar magnetic field (`unverified`); the force field has no such term [helmod:C05].
- **Numerical heliospheric models, 1D to 3D.** Time-dependent or stochastic-differential-equation solvers in one to three
  spatial dimensions with drifts and a latitude-dependent wind (`unverified`; no code named or run here). A number
  from such a model is reported with its code, version and inputs, as for galactic propagation codes.

## Neutron-monitor link (documented only)

Ground-level neutron-monitor count rates are commonly used to reconstruct a time series of phi through the
instrument's yield function and the geomagnetic cutoff (`unverified`: no reconstruction method or published phi series
was opened for this profile). A phi taken from such a series depends on the LIS assumed in the reconstruction; it is
not interchangeable with a phi fitted against a different LIS (the degeneracy above), so record the LIS and the
reconstruction with the value.

## Fits of phi over several periods

Fitting one phi per period with shared LIS parameters, time-dependent and time-independent systematics, and the
covariance across periods is statistics: follow `<plugin root>/skills/hep-statistics/references/time-series-inference.md`
(section "Joint fits of several periods") and hand the fit to hep-statistics. The force field enters as the model
function; this profile supplies the conventions and the validity range.

## Excluded

Source terms (dark matter, pulsars), galactic propagation, charge-sign dependent and drift modulation, transients,
geomagnetic cutoffs, any detector or measured flux, and any fitted value of phi.
