# Models: B/C in a weighted slab and in a 1D thin-disc diffusion halo

Two descriptions of a stable secondary-to-primary ratio (boron from carbon and oxygen), with the same inputs except
the transport parameters. Derivation and checks: `../derivations/derivation-record.md`.

| Model | Parameters | Ratio at E/n |
|---|---|---|
| `weighted-slab` (leaky box) | lambda0 (g/cm^2), delta, R0 | sum_j (sigma_js/m_H) r_j / (1/lambda_esc(R_s) + sigma_s/m_H), lambda_esc = lambda0 (R/R0)^-delta |
| `diffusion-1d` | D0 (cm^2/s), L (kpc), delta, R0; inputs h (kpc), n_H (cm^-3) | same with lambda_esc = n_H m_H h c L / D0 (R/R0)^-delta |

r_j = N_j / N_C are observed parent ratios (inputs); R_s is the secondary's rigidity at that E/n.

## Assumptions

- Steady state; free escape at |z| = L; observer at the mid-plane; thin disc (h << L) holding gas and sources.
- Pure diffusion: no convection, reacceleration, energy losses or radioactive decay.
- E/n conserved in fragmentation; masses A u, so every species has the same velocity at fixed E/n.
- Parents are pure primaries; one effective stable secondary; hydrogen target only.
- Cross sections are inputs (effective cumulative production, inelastic), energy independent.

## Degeneracy

In `diffusion-1d` the ratio depends on D0 and L only through D0/L, at every energy: the theory-spec lists
`degenerate_directions: ["D0/L"]`. A fit of B/C alone can quote D0/L, never D0 or L separately. The gas column
h n_H and a global rescaling of the production cross sections are degenerate with it as well; they are fixed inputs.

## Cross sections: inputs and model alternatives

`xs-illustrative-A.json` (nominal) and `xs-illustrative-B.json` (alternative) are **ILLUSTRATIVE** round placeholders,
not taken from any measurement or parametrization. A choice between sets is a `model-alternative` uncertainty
object (stored as the shift of the alternative from the nominal, fully correlated across bins, never Gaussian);
cross-section uncertainty in a fit belongs to hep-statistics (nuisance parameters or the set of alternatives).
Replacing them with a published set needs a new evidence claim and an energy-dependent treatment (excluded here).

## Validity domain

The models are exact for their own assumptions; they are not claimed to describe the Galaxy. Pure diffusion is a
poor description at low energy, where reacceleration, convection, losses and solar modulation act; the prediction
artifact covers 1-1000 GeV/n as a numerical range only. The ratio is local interstellar, before solar modulation.

## Excluded

See `profile.json` `exclusions`: convection, reacceleration, losses, decay (10Be), energy-dependent or published
cross sections, ghost networks and tertiaries, helium in the gas, solar modulation, ratios of bin-averaged fluxes in
rigidity bins, 2D geometry, any comparison with data, any propagation code.
