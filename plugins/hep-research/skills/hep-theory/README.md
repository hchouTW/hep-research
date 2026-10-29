# hep-theory

Theoretical and phenomenological results for particle, nuclear and astroparticle physics: models, conventions, derivations with a stated proof status, predictions with typed theory uncertainties, and recasting; works with no experiment.

## Core capabilities

- Model definition and conventions: units, metric, couplings, schemes, scales; definitions of units, constants and generic kinematics.
- Symbolic or analytic derivations, each with a derivation status and a list of the checks run or not run.
- Amplitudes, cross sections, decay rates and widths (phase space, narrow width, Breit-Wigner).
- Whether a process or Feynman diagram is allowed (selection rules); regularization, schemes and running masses.
- Approximations and validity domains.
- Theory uncertainties as distinct objects: scale envelopes, truncation, PDFs, model alternatives.
- Higher-order predictions, PDFs and LHAPDF, SMEFT and EFT conventions and truncation.
- Hadron structure: DIS kinematics and structure functions, polarized DIS, Drell-Yan, nuclear PDFs and nuclear targets, SIDIS and TMDs, fragmentation functions, small-x and saturation, exclusive processes and GPDs, theory inputs of global PDF/nPDF/FF fits.
- Neutrino oscillations, nuclear decays and decay chains, nuclear cross-section conventions.
- Cosmic-ray propagation and phenomenology, solar modulation models, cosmic-ray new physics (dark matter and pulsars without overclaiming), dark-matter phenomenology, light-nuclei coalescence, astroparticle essentials.
- Event-generation physics and event weights.
- Consistency checks and predictions for comparing a model with an experiment's published data, including import of published tables as dataset records.
- Recasting a published analysis (toolchain documented, not run).

## Triggering conditions

Use when:

- the deliverable is a theoretical or phenomenological result in particle, nuclear or astroparticle physics;
- a quick derivation, cross section or recast is asked for;
- conventions, constants, kinematics or a prediction for comparison with published data are needed;
- the topic is outside v1 (lattice QCD and its global analyses, EFT global fits, global cosmic-ray propagation fits that run a propagation code): the skill says what it cannot cover.

Not for:

| Need | Hand to |
|---|---|
| Fit, interval, limit, model comparison | hep-statistics |
| Numerical convergence, symbolic/numeric cross-check code | hep-computing |
| Folding into detector space | hep-detector, then hep-statistics |
| Surrogate of an expensive prediction | hep-ml |
| Paper section or Feynman-diagram rendering | hep-authoring |
| Measurement design | hep-measurement |

## Workspace directory architecture

```text
hep-theory/
├── SKILL.md
├── README.md
├── references/
│   ├── mathematical-reasoning-and-proof.md
│   ├── hadron-structure-essentials.md
│   ├── particle-physics-essentials.md
│   ├── nuclear-physics-essentials.md
│   ├── astroparticle-essentials.md
│   ├── cosmic-ray-propagation.md
│   ├── cosmic-ray-phenomenology.md
│   └── ...
└── scripts/
    ├── physical_data.py
    ├── kinematics.py
    ├── import_published_table.py
    └── ...
```

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | thirty-one references: hadron structure (entry page for DIS, Drell-Yan, nuclear PDFs, SIDIS/TMD, small-x, GPDs and global-fit inputs), theory inputs of global PDF/nPDF/FF fits, small-x physics and saturation (dipole picture, BK/JIMWLK conventions), exclusive processes and GPDs (DVCS kinematics, GPD properties, diffractive DIS), SIDIS and TMDs (Trento conventions, structure functions, Gaussian ansatz, Sivers sign change), fragmentation functions, DIS structure functions and cross sections, polarized DIS (g_1, g_2, asymmetries, sum rules, schemes), Drell-Yan (variables, frames, angular coefficients), nuclear targets (per-nucleon conventions, nuclear PDF sets and ratios), nuclear cross-section conventions, mathematical reasoning and proof status, higher-order predictions, PDFs and LHAPDF, SMEFT and EFT conventions, cosmic-ray propagation (guidance; narrow secondary-ratio, antiproton-source and force-field modulation profiles and a fit to tabulated predictions, synthetic data only), cosmic-ray phenomenology (propagation codes and their parameter conventions, production cross-section sets and nuisances, global-fit nuisance structure), solar modulation models beyond the force field, cosmic-ray new physics (dark-matter and pulsar interpretation without overclaiming), event generation, the recasting toolchain (documented, not run), DIS kinematics, amplitudes and widths (phase space, narrow width, Breit-Wigner), selection rules, regularization and schemes (running masses), neutrino oscillations, particle-physics essentials, nuclear-physics essentials, dark-matter phenomenology conventions, light-nuclei coalescence, astroparticle essentials |
| `scripts/` | twenty-five helpers: DIS kinematics, dipole-model cross sections, exclusive and diffractive kinematics, SIDIS kinematics, Gaussian TMDs, LO DIS structure functions and cross sections, sum-rule integrals, LO Drell-Yan, nuclear combination and ratios, PDF uncertainty, event weights, EFT truncation, physical data, kinematics, published-table import, neutrino oscillations, running coupling, decay chains, lepton energy losses, dark-matter rates and J factors, coalescence, astroparticle secondaries, Bartels rotations, cosmic-ray transport conventions, the naming extractor for parameters and scheme labels |

Entry pages in `references/`:

- `mathematical-reasoning-and-proof.md` gives the proof-status ladder (formal, analytic, perturbative, asymptotic, heuristic, numerical, empirical, conjecture, not derived) that every derivation record states; the other files are topic references.
- `particle-physics-essentials.md`: widths and lifetimes, Breit-Wigner forms, CKM and PMNS conventions, PDG particle codes.
- `hadron-structure-essentials.md`: the hadron-structure entry page.
- `nuclear-physics-essentials.md`: atomic vs nuclear masses, Q values, decay laws, radii, the S factor.
- `astroparticle-essentials.md`: the astroparticle entry page.
- `cosmic-ray-propagation.md` states the conventions of cosmic-ray kinematics and force-field modulation; `cosmic-ray-phenomenology.md` is the second propagation page (codes, cross-section sets and nuisances, global fits) and links `solar-modulation-models.md` and `cosmic-ray-new-physics.md`.

Scripts:

- `dis_kinematics.py`: invariants, beam relations, Jacobians, frames; lepton-mass bounds.
- `pdf_uncertainty.py`: `+as` alpha_s members, `num_members`.
- `event_weights.py`: signed weights pass unclipped; selected-event statistics.
- `eft_truncation.py`: cross-term convention, rescaling check.
- `physical_data.py`: constants, particle and nuclide data, unit conversions and decay Q values from `core/constants`, each with value, uncertainty, unit, source and edition (CODATA 2022, a PDG 2026 subset, AME2020/NUBASE2020); full tables through user-supplied AME/NUBASE files or the optional `pdg` package.
- `kinematics.py`: two-body decays via the Kallen function, Lorentz boosts, invariant masses, Mandelstam variables, fixed-target thresholds, Dalitz boundaries, rapidity and pseudorapidity, width/lifetime/c tau; masses as numbers or bundled particle names; over `core/kinematics/fourvector.py`.
- `import_published_table.py`: a user-downloaded CSV, FITS or HEPData table with declared columns, units, edges and uncertainty breakdown to a dataset-record labelled user-supplied, with a provenance sidecar (sha256, URL, download date, citation request); the breakdown is checked against a declared total; no network access.
- `neutrino_oscillation.py`: three-flavour probabilities in vacuum and constant-density matter, PMNS in the PDG convention, neutrino or antineutrino; every parameter is an input and the conventions block travels with the result.
- `running_coupling.py`: alpha_s in MS-bar at 1-4 loops with heavy-quark threshold matching, from a stated alpha_s(m_Z) and quark masses; stops where alpha_s > 0.5.
- `decay_chain.py`: amounts and activities of a decay chain (Bateman for linear chains, a matrix exponential for branches, production or nearly equal constants; NUBASE2020 half-lives with their edition).
- `lepton_energy_losses.py`: synchrotron and inverse-Compton loss rates of electrons with Thomson or Klein-Nishina factors, the loss time and the diffusion distance.
- `dm_direct_rate.py`: spin-independent recoil rate in the standard halo model with the Helm form factor, J and D factors and indirect-detection flux prefactors (every halo and cross-section input from the user).
- `coalescence.py`: converts between the coalescence momentum p0 and B_A, builds a coalesced invariant yield and gives the Wigner-function weights.
- `secondary_gamma.py`: gamma rays from a pi0 spectrum (exact kinematics), neutrino flavour ratios after averaged oscillations and head-on thresholds on a target photon.
- `structure_functions_lo.py`: LO F_2, xF_3 and NC/CC cross sections from user-supplied parton values with every electroweak and sign convention an input.
- `sum_rules.py`: integrates tabulated PDFs for the momentum, number, Adler and GLS sum rules, with the extrapolations outside the table reported separately.
- `drell_yan_lo.py`: LO Drell-Yan cross section (photon exchange), x_F and rapidity-frame conversions, the Collins-Soper <-> helicity rotation of (lambda, mu, nu) with frame invariants and the Lam-Tung combination.
- `nuclear_combination.py`: combines bound-proton values into nuclear ones by isospin, converts per nucleon <-> per nucleus and forms nuclear ratios member by member with the set's own rule.
- `sidis_kinematics.py`: SIDIS invariants, the Trento angles phi_h and phi_S, the leading-power q_T and a region label against the user's thresholds.
- `tmd_gaussian.py`: Gaussian-ansatz SIDIS and Drell-Yan transverse-momentum shapes and the SIDIS -> Drell-Yan Sivers sign change.
- `dipole_lo.py`: LO photon wave functions and GBW dipole-model sigma_T, sigma_L, F_2, F_L with every model parameter an input and a convergence report.
- `exclusive_kinematics.py`: t_min, the skewness xi, the BMK and Trento azimuths and the diffractive variables x_P and beta.
- `bartels_rotation.py`: converts dates and Bartels rotation numbers (27-day rotations from 1832-02-08) and averages a daily heliospheric input over each rotation with a declared lag and minimum coverage.
- `transport_conventions.py`: converts cosmic-ray diffusion parameters among the GALPROP, USINE and DRAGON2 conventions and the canonical names, marking each result exact, approximate or not-convertible.
- `extract_names.py`: the naming extractor for parameters and scheme labels.

Outside this folder:

- `core/kinematics/relativistic.py` (steward hep-theory): cosmic-ray kinematics (rigidity, momentum, total and kinetic energy, kinetic energy per nucleon, bin edges and flux Jacobians).
- `skills/hep-measurement/scripts/solar_modulation_force_field.py`: force-field solar modulation; its derivation, validity range and a power-law closed-form benchmark are in a theory-domain profile listed in `profiles/registry.json`.
- `adapters/hepdata/assets/hepdata_record.py`: a HEPData table to a dataset record.
- `adapters/crdb/assets/crdb_query.py` (optional, `tested-in-declared-environment`, CRDB V4.2): compiled cosmic-ray data from CRDB (LPSC), a secondary source; HEPData or the paper's tables stay primary, a CRDB value is a cross-check or a fallback labelled secondary; the experiment filter has no default and every row is labelled secondary.
- `profiles/registry.json`: shipped theory-domain profiles.

## Input and output specifications

Inputs:

- Request: model, observable and conventions where known; a theory-domain profile only if one is named or configured.
- Profiles and context: only through the context-resolution steps in `SKILL.md`; no experiment, detector, data or blinding fields are required.
- Files read: user-supplied tables (CSV, FITS, HEPData), user-supplied AME/NUBASE files, tabulated PDFs and parton values, a daily heliospheric series (CSV), dataset records for comparison.

Outputs:

- `theory-spec` with a Markdown derivation record carrying a JSON header (status, conventions block, validity domain, checks run or not run).
- `prediction`: JSON plus CSV for grids, explicit units, uncertainties by type and allowed transformations.
- `computational-run` recording the SymPy interpreter with its Python and SymPy versions, or a user's own computer algebra system (Mathematica, FORM, Maple, ...) with its name, version and input files (`skills/hep-computing/scripts/environment_manifest.py record --inputs ...`), so the derivation can be rerun.
- Dataset records labelled user-supplied, with a provenance sidecar, from `import_published_table.py`.
- Durable results go to the project's `artifacts_dir`, never inside the plugin.

Script CLI contract:

```text
python3 <plugin root>/skills/hep-theory/scripts/<script>.py --help
python3 <plugin root>/contracts/comparison/gate.py <prediction.json> <record.json> [--plan ...]
```

- Every script takes `--help`; output is JSON.
- Exit codes: 0 ok; refused non-finite or ambiguous input gives a non-zero exit with a JSON reason (exit 1 in `dis_kinematics.py`; exit 2 = invalid input or input the tool cannot use in most scripts); exit 3 `incomplete` in `running_coupling.py` (alpha_s above 0.5) and `bartels_rotation.py` (a rotation below `--min-coverage`).
- Comparison gate: exit 1 means declare transformations (`--plan`) or stop.

## Setup requirements

- Python 3.13 or newer; the SymPy interpreter for derivations is chosen by `skills/hep-computing/scripts/find_python.py`; if it reports `failed`, nothing is installed without approval.
- Standard library first.
- Optional packages: NumPy and SciPy (`decay_chain.py`, `dipole_lo.py`), NumPy (`neutrino_oscillation.py`), astropy (FITS input in `import_published_table.py`), `pdg` (full particle tables in `physical_data.py`), SymPy (derivations).
- No environment variables.

## Operational constraints

- Never requires experiment, detector, data or blinding fields.
- Never claims support for a domain because a tool ran; never reports numerical agreement as proof.
- Every result carries a derivation status from the core vocabulary; a status is never upgraded when a result is reused.
- A conventions block travels with every derivation and prediction; the validity domain and what was neglected are stated; inapplicable fields are `not-applicable`.
- Termination of a computation is not convergence.
- Benchmarks cite an authoritative source that was actually read, with its exact location.
- Scale envelopes, truncation estimates and model alternatives are never turned into Gaussians without a stated prescription.
- A request outside the validated theory profiles gets an explicit "no validated domain profile" notice, then general discipline.
- Comparison with data runs the comparison gate first; the chi2 or fit goes to hep-statistics, never computed inline.
- A successful script run is a software check, not scientific validity.
- The authoritative statement of these rules is [SKILL.md](SKILL.md).

## Validation

- `tests/skills/hep_theory/`: thirty-seven test modules.
- The `qed-prediction`, `theory-comparison`, `published-comparison`, `recasting` and `bc-propagation-fit` examples under `examples/`.
- Theory routing tests under `tests/routing/`.
- What is and is not validated: `docs/capability-matrix.md`; the evidence: `VALIDATION.md`.

## Example requests

Request kinds from the Resources table in [SKILL.md](SKILL.md):

- Derivation status, proof, validity and checks of a result.
- An NLO/NNLO prediction with a scale envelope.
- A PDF uncertainty with LHAPDF sets.
- SMEFT/EFT conventions and truncation.
- DIS invariants, Jacobians and frames.
- Constants, masses, lifetimes, nuclides, units and Q values.
- Neutrino oscillation probabilities in vacuum or constant density.
- Whether a process or diagram is allowed.
- A published table (CSV, FITS, HEPData) as a dataset record.
