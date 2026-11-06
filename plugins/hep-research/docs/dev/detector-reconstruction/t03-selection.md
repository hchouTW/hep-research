# T03: selection for the three required workflows

State: `blocked-by-decision` (R16, K02, K03). No reconstruction backend is confirmed on this host. Nothing below has run on this host unless marked. Package facts come from read-only `conda search` queries on conda-forge, 2026-11-06, listed at the end; anything else is marked `unverified`. A package existing is not a confirmed backend: that needs an approved job (R02). Costs are not estimated: no recorded times exist.

## Tracking and vertexing (BP03, BP04)

| Rank | Option | Form | Version | Install route | Licence | Data | Limits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | ACTS | Library | `acts-core` 48.2.0, linux-64, built 2026-10-18 | conda-forge into a new environment. CVMFS is not a dependable route (below) | MPL-2.0 | Synthetic, or simulated from the installed Geant4 | The only option here with general finding and vertexing. Depends on Boost and the C++ runtime with no Python dependency, so it appears to be the core library alone: a C++ driver and a geometry would have to be written. Needs K02 |
| 2 | `simreco` pattern recognition | Existing tool, present in the tree | `adapters/geant4` 0.7.0 | None for the code; needs a build and `element_sim` events | Plugin licence | Simulated events only | Plane-by-plane association plus fit. No vertexing. Not a general tracker, so it cannot stand for BP04 |
| 3 | GenFit | Library | Unverified | Not on conda-forge; source build only | Unverified | Needs measurements and seeds | Fitter only: an existing fitter cannot replace finding (T03) |

Toy fallback: `toy_spectrometer.py`, role toy, with the native-integration gap kept open.

## Calorimetry (BP05)

| Rank | Option | Form | Version | Install route | Licence | Data | Limits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Small clustering adapter written in this task, on Geant4 cell output | Development binding | n/a | No new install for the Python side; cell output path unconfirmed | Plugin licence | Simulated | Must stay labelled a development binding, with its own acceptance. Not a native backend, so the native-integration gap stays open |
| 2 | PandoraSDK with its content libraries (S06) | Library | Unverified | Not on conda-forge; source build only, needing network approval | Unverified | Cell hits, synthetic or simulated | Native option, but the hardest to obtain. Needs a cell-hit input path and K02 |

Toy fallback: `simreco`'s calorimeter stage (active deposit over sampling fraction). It does no clustering, so it cannot count as reconstruction.

## Photon likelihood (BP06)

| Rank | Option | Form | Version | Install route | Licence | Data | Limits |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Likelihood written in this task from `photon-likelihood-reconstruction.md`, with expected light from installed Geant4 | Development binding | n/a | No new install expected | Plugin licence | Simulated | No native backend. Live, unhit and dead channels, thresholds and saturation must follow the reference |
| 2 | ctapipe (S27-S30) | Library | 0.32.0, noarch | conda-forge | BSD-3-Clause | Unverified | Image-template variant only; does not cover the all-channel likelihood |

Experiment-native fitters: access unknown, not in the plan's sources. No native option is known to be obtainable, which is a named gap for required delivery.

## Two-candidate domain (T15b)

Recommended: two valid configurations of `simreco` pattern recognition (association window and `chi2_per_ndof_cut`), allowed by T03 as different configs of one backend. It needs no new install, and its scope stays simulated `element_sim` events. Recommended over ACTS for this purpose only because it does not wait on K02.

## Non-hit routing and negative cases

Non-hit routing uses W6 and W7 inputs. Negative cases: an unknown format ends in restricted delivery (A43, A52); a request with no backend is refused without a fabricated command (A52).

## Other findings

- DD4hep 1.38 is on conda-forge (LGPL-3.0-or-later), a possible geometry input for ACTS. EDM4hep and podio are not, under those names.
- CVMFS: job 7470680 on `hpa-wn28` listed `/cvmfs/sft.cern.ch/lcg` in 2 s, but `views` and `releases/acts` both stalled past 240 s. A listing of `views` also stalled on the login node. One node, one run; the cause is not known.

## Queries run

Approval, verbatim: "approve both jobs and the read-only network queries". Each was `conda search --override-channels -c conda-forge NAME --json`, with NAME: `acts`, `genfit`, `pandorasdk`, `lccontent`, `dd4hep`, `edm4hep`, `podio`, `ctapipe`, `*genfit*`, `*pandora*`, `*edm4hep*`. `acts` matched `acts-core`; `*pandora*` matched only an unrelated package, `pandora-geno`.

## Confirming what is unprobed

No backend counts until an approved job has run it (R02). The smallest next steps are in `blockers/T03.md`.
