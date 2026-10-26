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
- Pure diffusion (the two models above): no convection, reacceleration, energy losses or radioactive decay; the
  closed forms with convection and decay are the section below.
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

## Convection and radioactive decay (closed forms, B2)

`scripts/convection_decay.py` (derivation `../derivations/convection-decay-record.md`) extends `diffusion-1d` with a
constant convective speed V_c (`V_c_kms`, conservative form, adiabatic energy change neglected) and with the decay
of unstable secondaries at rate 1/(gamma tau_0), half-lives from `core.constants.physical` (NUBASE2020), keeping
the daughter's gain (10Be -> 10B). At the mid-plane N_s(0) = 2 h q_s / (K_s + 2 h n_H v sigma_s) with
K = V_c + D S coth(S L/2), S = sqrt(V_c^2/D^2 + 4 Gamma/D); K = 2D/L recovers pure diffusion. Fully stripped 7Be
is propagated as stable (recorded `stable_assumption`). Settings: `../benchmarks/convection-decay-benchmark.json`
with the ILLUSTRATIVE isotopic set `xs-illustrative-decay.json`; observables are isotope sums at equal E/n (B/C,
Be/B, 10Be/9Be). With V_c or decay the ratio no longer depends on D0/L alone (the escape term is not a function of
D/L), so the D0/L degeneracy of pure diffusion is broken only through these terms; this profile does not quantify
it (work package A3). Reacceleration has no closed form and is excluded.

## Excluded

See `profile.json` `exclusions`: reacceleration, losses, energy-dependent or published
cross sections, ghost networks and tertiaries, helium in the gas, solar modulation, ratios of bin-averaged fluxes in
rigidity bins, 2D geometry, any comparison with data, any propagation code.
