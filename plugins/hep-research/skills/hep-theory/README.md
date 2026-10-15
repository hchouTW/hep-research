# hep-theory

Use when the deliverable is a theoretical or phenomenological result: model definition and conventions (units, metric, couplings, schemes, scales), symbolic or analytic derivations, amplitudes, cross sections, decay rates and widths, whether a process or diagram is allowed, approximations and validity domains, theory uncertainties (scale envelopes, truncation, PDFs, model alternatives), event-generation physics, SMEFT conventions, consistency checks, predictions for comparing a model with published data, and recasting a published analysis. Works with no experiment.

**Owns:** models, assumptions, conventions, derivations, predictions, event-generation physics, approximations, validity, theory-uncertainty prescriptions, consistency checks; definitions of units, constants and generic kinematics. Typical artifacts: `theory-spec` (with a Markdown derivation record carrying a JSON header) and `prediction` (JSON plus CSV for grids, explicit units).

**Never:** require experiment, detector, data or blinding fields; claim support for a domain because a tool ran; report numerical agreement as proof.

## Folder map

| Path | Content |
|---|---|
| `SKILL.md` | entry point |
| `references/` | eleven references: mathematical reasoning and proof status, higher-order predictions, PDFs and LHAPDF, SMEFT and EFT conventions, cosmic-ray propagation (guidance only; fits are outside v1), event generation, the recasting toolchain (documented, not run), DIS kinematics, amplitudes and widths (phase space, narrow width, Breit-Wigner), selection rules, regularization and schemes (running masses) |
| `scripts/` | four helpers: DIS kinematics, PDF uncertainty, event weights, EFT truncation |

## Scripts

`dis_kinematics.py` (invariants, beam relations, Jacobians, frames; lepton-mass bounds), `pdf_uncertainty.py` (`+as` alpha_s members, `num_members`), `event_weights.py` (signed weights pass unclipped; selected-event statistics), `eft_truncation.py` (cross-term convention, rescaling check). Each refuses non-finite or ambiguous input with exit 1 and a JSON reason. The SymPy interpreter for derivations is chosen by `skills/hep-computing/scripts/find_python.py`. A HEPData table becomes a dataset record through `adapters/hepdata/assets/hepdata_record.py`. Cosmic-ray kinematics (rigidity, momentum, total and kinetic energy, kinetic energy per nucleon, bin edges and flux Jacobians) is `core/kinematics/relativistic.py` (steward hep-theory), and force-field solar modulation is `skills/hep-measurement/scripts/solar_modulation_force_field.py`; `references/cosmic-ray-propagation.md` states their conventions.

## References

`references/mathematical-reasoning-and-proof.md` gives the proof-status ladder (formal, analytic, perturbative, asymptotic, heuristic, numerical, empirical, conjecture) that every derivation record states; the other files are topic references. Shipped theory-domain profiles are listed in `profiles/registry.json`.

## Handoffs

| Need | Hand to |
|---|---|
| Fit, interval, limit, model comparison | hep-statistics |
| Numerical convergence, symbolic/numeric cross-check code | hep-computing |
| Folding into detector space | hep-detector, then hep-statistics |
| Surrogate of an expensive prediction | hep-ml |
| Paper section or Feynman-diagram rendering | hep-communication |

## Tests and validation

`tests/skills/hep_theory/` (six modules), the `qed-prediction`, `theory-comparison`, `published-comparison` and `recasting` examples under `examples/`, and the theory routing tests under `tests/routing/`. What is and is not validated is listed in `docs/capability-matrix.md`; the evidence is in `VALIDATION.md`.

## How this folder is used

`SKILL.md` is the entry point the host loads (its front matter carries the description that routes a request here; it
stays under 8 KiB). This README is for people browsing the folder. The skill reads the project's profiles only
through the context-resolution steps in `SKILL.md`; it never embeds experiment facts, and durable results are written
as JSON artifacts in the project's `artifacts_dir`, never inside the plugin. Scripts take `--help` and are standard
library first; a successful run is a software check, not scientific validity.
