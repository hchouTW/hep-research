# cr-propagation r4: H0 decision record

Answered once by the maintainer on 2026-10-26, before P0 (`workflow-r4.md` §9). From here to H1 every agent acts only
on this record; anything it does not cover goes to `escalations.md`, never to a mid-run question.

| # | Decision | Answer (2026-10-26) | Basis |
|---|---|---|---|
| D0 | The companion manifest `crprop-workflow.json` was not supplied | The orchestrator derives `workflow.json` from r4 §6–§7 and the r3 cards; every value r4 and r3 do not state is marked `derived` in its `source` field | maintainer, H0 |
| D1 | Location of the source repo | The maintainer's checkout of the `hep-research` repo on the E2 host (`$HOME/hep-research`); integration worktree `.claude/worktrees/crprop-integration`, branch `worktree-crprop-integration` from `origin/main` 8fcbb826 (0.42.0) | maintainer, H0 |
| D2 | Execution host | Environment E2 (the macOS arm64 workstation of `VALIDATION.md`) through Claude Code. Probed at H0: ROOT 6.38.04, GSL 2.8, CFITSIO 4.6.4, gfortran, cmake, Homebrew, the DRAGON2 cd588707 build from WP13; no Slurm or HTCondor client; github.com and pypi.org reachable from the agent sandbox; `lpsc.in2p3.fr`, `gitlab.in2p3.fr`, `galprop.stanford.edu` time out from the sandbox | maintainer, H0 |
| D3 | Standing grant | Granted, limited to: installing build dependencies with Homebrew or into a venv outside the repo; cloning DRAGON2 from github.com; building and running DRAGON2, USINE and GALPROP outside the repo (builds under `$HOME/hep-work/crprop-build/`, run outputs under `CRPROP_OUT` = `$HOME/hep-work/crprop-out/`); commits and merges on the integration branch and `worktree-crprop-*` branches; the unreleased contracts minor bump `CV-CRPROP` and the `CORE_VERSION` minor bump of C1. Not granted: push, pull requests, any `gh` write, any change to `main`, `--force`, a paid live routing run, any change to the v1 scope outside F3's conditional preparation (D11) | suggested default |
| D4 | USINE source and version | V3.5, from a tarball the maintainer places in `CRPROP_SOURCES` = `$HOME/hep-work/crprop-sources/`. Until it is there, `net-sources` and `env-usine` are `absent`, and B1, B3, C2U and F1 wait (`waiting-capability`) | maintainer, H0 |
| D5 | GALPROP | Included, v57, from a tarball in `CRPROP_SOURCES`; if the licence is unclear, no fixtures are committed. Without the tarball D2 takes its fallback (`unavailable`) | suggested default |
| D6 | Batch site and consent per round | No batch client on E2: E1 runs through `skills/hep-computing/scripts/local_partition.py` on E2; every E1 round within the D7 caps counts as consented | maintainer, H0 |
| D7 | Compute budget | At most 5000 provider evaluations in total, 200 core-hours, 6 weeks of wall time for the campaign; reaching a cap stops the affected work packages and escalates | maintainer, H0 |
| D8 | F1 target and fallback | Génolini et al. 2019 (arXiv:1904.08917, Table II) with USINE; if USINE is unavailable, a cross-code reproduction with DRAGON2, marked insufficient for v1 | suggested default |
| D9 | F1 tolerance | The best-fit δ and K10 lie within the original paper's 1σ, for all three model families (BIG, SLIM, QUAINT) | suggested default, confirmed |
| D10 | Base exception (§P.10.2) | Accepted: work packages branch from the integration HEAD; each records the exception in its `VALIDATION.md` environment field; RC rebases onto the latest `main` and reruns every check before H1 | suggested default |
| D11 | Conditional consent for F3 | Yes: if F1 passes, F3 prepares the v1 changes on integration; the paid live routing run is left to H1 | suggested default |
| D12 | Notification | Notify the maintainer on each critical escalation and when RC completes; everything else is reported at H1 | suggested default |

Acceptance defaults: the r3 "suggested defaults" (B3, C2, D1–D3, E1–E2) are adopted as the frozen tolerances
(r3 Q8); F1's tolerance is D9. Open Questions of r3 take their defaults: Q3 one shared `adapters/cr-propagation`;
Q4 force field by subprocess through the new tool contract; Q5 as D8; Q6 as D2 and D6; Q7 public data only;
Q9 N₀ = 10 × number of free parameters rounded up to a power of 2, k = N₀/10, within D7.

## Differences between the language versions (reported, not chosen)

- `workflow-r4.zh.md` §3, item 2: "GALPROP（D2 為 yes 時）"; `workflow-r4.md` §3: "GALPROP (when D5 is yes)". D5 is the
  GALPROP decision and D2 the execution host, so the English reading is the consistent one; the orchestrator follows
  D5 and leaves the wording to the maintainer at H1.
- No other difference in identifiers, numbers or paths between `workflow-r4.md` and `workflow-r4.zh.md`, or between
  `cr-propagation-plan.md` and `cr-propagation-plan.zh.md` (token comparison at P0).
