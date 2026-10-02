# M2 migration equivalence records

Environment: Python 3.11.15, `.venv-hep` (numpy 2.4.6, scipy 1.17.1). Legacy source `agentic-ai-skills@3e995a4`.

## core/stats (move, 2026-10-02)

| Legacy | Plugin | Change | Evidence |
|---|---|---|---|
| ams-analysis/scripts/{statistical_toys, unfolding_diagnostics, likelihood_limits, template_fit, poisson_diagnostics, validate_covariance, validate_response}.py | core/stats/<same name>.py | Imports packaged (`core.stats.*`), script-mode bootstrap, usage paths, docstrings no longer name AMS. **No numerical code changed.** | Ported tests: 207 run / 207 pass (legacy: 207 tests in these 7 files). Seeds and tolerances are those of the legacy tests, unchanged. CLI `statistical_toys.py boundary --n 12 --b 8 --toys 2000 --seed 1` output byte-identical to legacy (md5). |

## core/kinematics (move, 2026-10-02)

| Legacy | Plugin | Change | Evidence |
|---|---|---|---|
| ams-analysis/scripts/ams_kinematics.py | core/kinematics/relativistic.py | Moved whole: every conversion (rigidity, momentum, energies, kinetic energy per nucleon, bin edges, Jacobians, mass propagation) is generic charged-particle kinematics; it embeds no constants (|Z|, A and mass are caller-supplied, no defaults). Interface change: output note now says "not measured detector performance" instead of naming AMS; one test assertion updated accordingly. No numerical change. | 25/25 ported tests pass (legacy 25). |

AMS-specific interpretation (which variable a given AMS publication reports, isotope mass assumptions) belongs in the `experiment:ams-02` profile modules, not in code.
