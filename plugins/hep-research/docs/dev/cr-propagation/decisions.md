# cr-propagation r4: H0 decision record

Answered once by the maintainer on 2026-10-26, before P0 (`workflow-r4.md` §9). From here to H1 every agent acts only
on this record; anything it does not cover goes to `escalations.md`, never to a mid-run question.

| # | Decision | Answer (2026-10-26) | Basis |
|---|---|---|---|
| D0 | The companion manifest `crprop-workflow.json` was not supplied | The orchestrator derives `workflow.json` from r4 §6–§7 and the r3 cards; every value r4 and r3 do not state is marked `derived` in its `source` field | maintainer, H0 |
| D1 | Location of the source repo | The maintainer's checkout of the `hep-research` repo on the E2 host (`$HOME/hep-research`); integration worktree `.claude/worktrees/crprop-integration`, branch `worktree-crprop-integration` from `origin/main` 8fcbb826 (0.42.0) | maintainer, H0 |
| D2 | Execution host | Environment E2 (the macOS arm64 workstation of `VALIDATION.md`) through Claude Code. Probed at H0: ROOT 6.38.04, GSL 2.8, CFITSIO 4.6.4, gfortran, cmake, Homebrew, the DRAGON2 cd588707 build from WP13; no Slurm or HTCondor client; github.com and pypi.org reachable from the agent sandbox; `lpsc.in2p3.fr`, `gitlab.in2p3.fr`, `galprop.stanford.edu` time out from the sandbox | maintainer, H0 |
| D3 | Standing grant | Granted, limited to: installing build dependencies with Homebrew or into a venv outside the repo; cloning DRAGON2 from github.com; the read-only `adapters/hepdata` and `adapters/crdb` queries of F1 (r3 §0.6, §F1); building and running DRAGON2, USINE and GALPROP outside the repo (builds under `$HOME/hep-work/crprop-build/`, run outputs under `CRPROP_OUT` = `$HOME/hep-work/crprop-out/`); commits and merges on the integration branch and `worktree-crprop-*` branches; the unreleased contracts minor bump `CV-CRPROP` and the `CORE_VERSION` minor bump of C1. Not granted: push, pull requests, any `gh` write, any change to `main`, `--force`, a paid live routing run, any change to the v1 scope outside F3's conditional preparation (D11) | suggested default |
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
- `cr-propagation-plan.md` line 64 places the placeholders `CV-A2`/`CV-C1` in "(Technical Approach §0.4)";
  `cr-propagation-plan.zh.md` line 64 says §0.5. The rule is in §0.5 (line 243), so the Chinese reference is the
  consistent one.
- `cr-propagation-plan.md` line 257 has the code-span status `BLOCKED: environment E2 required`;
  `cr-propagation-plan.zh.md` line 257 has `BLOCKED: 需要環境 E2`. An identifier in a code span differs; workers emit
  the English form (the plan's stated rule keeps identifiers unchanged across languages).
- `workflow-r4.md` Deliverables (line 242): this document is committed as `workflow-r4.md` "together with its Chinese
  original"; `workflow-r4.zh.md` (line 241) says the (Chinese) document is committed as `workflow-r4.md` and does not
  mention the English version. The orchestrator follows the English: `workflow-r4.md` (English) and
  `workflow-r4.zh.md` (Chinese), as for the r3 pair.
- `workflow-r4.md` Open Questions (line 281) instructs running `review.py` "during P0"; `workflow-r4.zh.md` line 280
  says it is "suggested" (建議) at P0. Either way it is deferred (see Orchestrator notes).
- `cr-propagation-plan.zh.md` line 7 (Language row) names the English file `hep-research-cr-propagation-plan.en.md`
  (not its committed name `cr-propagation-plan.md`) and adds a sentence on the headings and `lint_task.py`; the English
  row has neither.
- Found by the two P0 verifiers; the second compared r4 zh in full and r3 by tokens (code spans, numbers, §
  references, identifiers). Wording-only variants are not listed. The maintainer resolves the texts at H1.

## Orchestrator notes recorded at P0 (for H1)

- r3 Q10 / r4 Open Questions, formal independent review with `skills/hep-authoring/scripts/review.py`: not run at P0.
  The isolation precondition of `docs/dev/independent-review-spec.md` §A7 (`CLAUDE_CODE_FORK_SUBAGENT=0` in settings
  with a host restart, or `Agent(fork)` in `permissions.deny`) is a host-settings change outside the D3 grant, so the
  review moves to before H1 as r4 allows.
- D7's 6-week wall-time cap is below r4 §7's 13–15-week estimate; reaching it is a `budget` escalation, not a stop
  of unaffected work packages.
- The checker `workflow_check.py` and `workflow.json` are trusted only from the integration branch; verifiers run the
  integration copy with `--plugin-root` set to the branch under test (P0 rework).

## H0 amendment A1 (2026-10-27, maintainer)

| # | Amends | Answer | Basis |
|---|---|---|---|
| A1.1 | D3, D4 | The maintainer allows installing USINE. Source: the official repository `https://gitlab.com/dmaurin/USINE.git`, tag `V3.5` (tag object 7197ddc1, commit fb53006d; seen with a read-only `git ls-remote` on 2026-10-27). ENV is re-dispatched to clone that tag into `$HOME/hep-work/crprop-build/usine/`, read its licence before any fixture is committed, build it against ROOT 6.38.04 on E2, and record the build; `gitlab.com/dmaurin/USINE` joins the D3 network list | maintainer, 2026-10-27 |
| A1.2 | D5 | GALPROP stays optional: no source host is reachable, so unless the maintainer supplies a v57 tarball, D2 takes its fallback (`unavailable`) at RC | orchestrator recommendation |
| A1.3 | §4 limits | Host and plan: the maintainer runs the next session on Claude Max (x20). Concurrency: at most 3 workers at once and at most 2 full `run_all_checks` runs at once (`--jobs 4`); verifiers of mechanical WPs (P0, ENV, A2, A3, C1, A4) may use Sonnet, physics-heavy ones (A1, B2, B3, C2, C2U, D1, D3, F1) use Opus. Reason: the first run hit the usage limit twice and host load reached ~212, giving a false 600 s timeout | orchestrator recommendation; confirmed by the maintainer at resume, 2026-10-28 |
| A1.4 | §1, §4 (ALL-3 execution) | From the next dispatch on, workers run only `run_all_checks --part static --jobs 4` plus the impacted tests before reporting; the verifier alone runs ALL-3 (full `run_all_checks` and `check_relocation`, through the 2-slot wrapper). ALL-3 itself is unchanged; its evidence is the verifier's own run, so independence is kept. Agents already running finish under the old brief | maintainer, 2026-10-28 (orchestrator recommendation B) |
| A1.5 | §2, §4, ALL-3 execution (supersedes A1.4) | Workers and verifiers run only `run_all_checks --part static --jobs 4` plus the impacted tests (and the other per-WP checks). ALL-3 (full `run_all_checks` + `check_relocation`) is run by the orchestrator once per wave on the integration HEAD after that wave's merges, through the 2-slot wrapper; its record is the ALL-3 evidence for every WP merged in that wave. On a failure not present on the wave's start commit, the orchestrator finds the responsible merge (rerun the failing module on each merge commit of the wave), reverts it and returns that WP to REWORK. WF-4 (static + impacted after every merge) and WF-10 (full run at RC) are unchanged | maintainer, 2026-10-28 (orchestrator recommendation: per wave, not only at the end) |
| A1.6 | §4 limits (P0 rework rounds), escalation 4 | One extra P0 round (round 3) is authorized, limited to adding `--no-renames` to the `git diff --name-only` call in `workflow_check.py` `check_diff` plus a regression test inside `docs/dev/cr-propagation/` (a rename into allowed paths must be reported). Done by a worker in worktree `crprop-p0fix`, verified by an independent verifier, merged by the orchestrator. The verifier-brief mitigation stays until the merge | maintainer, 2026-10-28 |
| A1.7 | §6 (WP set), escalation 8 | Add one small WP (working id `B1X`) after B1 merges and before C2U/F1: (1) a contracts addition so `extension.transport` can express a high break (slope above it), inside the unreleased CV-CRPROP 3.14.0 and gated by CRPROP_FROM; (2) usine_translate.py reads USINE's own cross-section files with data-normalised abundances, not only the ILLUSTRATIVE sets (GPL-2.0: those files are read in place, never committed). C2U and F1 gain `B1X` as a dependency. The orchestrator adds the WP to workflow.json and its entries to acceptance.json (additions only, r4 §5) when it dispatches it | maintainer, 2026-10-28 (orchestrator recommendation) |
| A1.8 | D7, escalation 7 | The 5000-evaluation cap counts evaluations of external codes only (DRAGON2, USINE, GALPROP); closed-form provider evaluations do not count. All CPU time, benchmarks included, counts toward the 200 core-hours. Tally at decision: about 1.2 core-hours (A4), about 130 USINE (B1) and about 22 DRAGON2 (D1) evaluations, plus verifier reruns | maintainer, 2026-10-28 (orchestrator recommendation) |
| A1.9 | escalations 5, 6, 9; D1-1 (frozen); §6 (WP set) | (1) D1-1 is superseded for D1's verdict by D1-1a (each item's effect, ratio with the item over ratio without it, agrees with the reference within the same 3%) and D1-1b (absolute offsets reported and attributed, no tolerance); D1-1 stays in acceptance.json unchanged and is listed in the campaign report as a criterion changed by the maintainer. (2) DRAGON2 energy losses: a bounded diagnosis (at most 6 DRAGON2 runs) rules out a spec/config error; if still unphysical, the dragon2 provider refuses requests with losses on, adapter.json records it, the losses item is excluded from D1 and D3, and an upstream issue is drafted outside the repo for the maintainer to post (entry D1-L). (3) New WP A1R (hep-theory): fix the DRAGON2 row of the convention table (escalation 6) and state the thin-disc/whole-halo V_A conversion and the DRAGON2 vs USINE momentum-diffusion normalisations from their sources; D1 depends on it. (4) D1 is not merged with D1-1 failed (WF-3): after A1R merges, D1 gets dispatch 2 (rerun reacceleration under the agreed convention, losses rule, D1-1a/b), then a verifier. Planned: when D3 is dispatched the orchestrator adds an entry for a level-1 comparison with USINE configured to DRAGON2's He target and gas column (addition only, r4 §5) | maintainer, 2026-10-28 (orchestrator recommendations) |
