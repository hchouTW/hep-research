# Secondary antiproton source term profile: routing map

Profile `theory:cr-secondary-antiprotons`: the source term q(T_pbar) of secondary antiprotons from cosmic-ray p and He
on interstellar H and He (channels pp, pHe, Hep, HeHe), with antineutrons and hyperons. It needs no experiment
profile. Paths are relative to this folder. The shipped cross sections are a TOY form with ILLUSTRATIVE values.

| Request | Read |
|---|---|
| Source-term definition, channels, antineutrons, hyperons, what the toy form can and cannot say | `models/source-term-models.md` |
| Closed form of the source integral, checks run and not run | `derivations/derivation-record.md` (run `scripts/derive.py`) |
| Theory-spec artifact (model family, parameters) | `derivations/theory-spec.json` |
| q(T_pbar) per channel and in total, channel fractions | `scripts/predict.py --help`; in Python `predict.source_term(cfg)`, `predict.bin_averaged(cfg, edges)` |
| Stored prediction artifact | `predictions/source-term-benchmark.prediction.json` (regenerate with `scripts/make_artifacts.py`) |
| Benchmark: numerical integration vs the closed form | `scripts/predict.py --benchmark`; settings `benchmarks/source-term-benchmark.json` |
| Cross-section sets (inputs, model alternatives) | `models/xs-toy-A.json`, `models/xs-toy-B.json` |
| External benchmark (B2): published pp source term, di Mauro et al. 2014 Table VI | `scripts/published_benchmark.py`; reference values `benchmarks/published-source-term-dimauro2014.json`; published closed forms `models/xs-dimauro2014-pp.json` |
| References and what is attributed to them (read levels per source) | `evidence/sources.json`, `evidence/claims.json` |

Conventions: `conventions.json`; they follow `skills/hep-theory/references/cosmic-ray-propagation.md`, section
"Secondary antiprotons: source-term conventions". The level `crpb:interstellar-source` is this profile's vocabulary:
validate its artifacts with `contracts/validate.py <artifact> --profiles-from <project config binding the profile>`.
This is a source term, not a propagation model: it cannot drive a propagation-parameter fit, and its theory-spec
needs no `degenerate_directions`. The published pp parametrizations serve the external benchmark only; the prediction
artifact still uses the toy sets. 12 of 15 Table VI entries are reproduced within the paper's errors; the rest are
documented in the benchmark file with the reason.
