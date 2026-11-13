# T15b (Task D5): what it needs

Assessment only, 2026-11-13, on branch `gate-d/prep` from 4c08da43. Nothing was built, run or submitted for it.

## What T15b is

- Plan R19: T15b (P2) covers A50, A51 and A53 on the T03 two-candidate domain. Plan 16.1 row T15: prerequisites T06, T14, K16, K17, K18.
- `t03-selection.md`, "Two-candidate domain": two configurations of `simreco` pattern recognition, simulated `element_sim` events only.
- `finish-plan.md` Task D5: "Two `simreco` configurations, paired events, K16 rules. Needs a built `simreco` and an approved job."
- `t05-task-sheets.md`: T15b `blocked-by-decision`, prerequisites T15a, the T03 domain, K16.
- U-K7 (`decisions.md`, 2026-11-11): A01's owner is T15b. `t07-closeout.md` keeps A01 open "unless `simreco` qualifies on the shared domain".

## The decision that blocks it

**K16, and within K16 only one item is still open: the `element_sim` sample spec.**

- K16's proposal is `t04-values-v4.md` section 13: candidates `simreco-pr-a` (window 1 mm, `chi2_per_ndof_cut` 50, minimum 4 hits) and
  `simreco-pr-b` (window 0.5 mm); comparator `simreco` with pattern recognition off on the same events; per bin and candidate the `rho_pull`
  location, width and tail tests, paired efficiency (lower bound at least -0.01), `charge_flip` and fake at `L` 1 %; 96 tests, `alpha`
  1.04e-4; objective lowest total CPU time per event subject to the gates; CPU measured in alternating 100-event chunks, first chunk cold
  and reported apart; tie rule by the paired bootstrap interval, else `simreco-pr-a` as the "qualified default choice"; none passing gives
  "no qualified candidate".
- Section 16's K16 row recommends "Section 13. Name the `element_sim` spec". The user accepted section 16's recommendations on 2026-11-06,
  and `decisions.md` records "The `element_sim` spec for K16 was not named". Freeze A then froze `t04-values-v4.md` by hash (as amended,
  `92f71f56...`, equal to the file at this branch), with section 13 inside it, and listed as outside the freeze "the `element_sim` spec for
  K16, frozen by hash before T15b" (`freeze-a.md`, "Not in this freeze"; `decisions.md`, Freeze A).
- Reading (for the coordinator to confirm with the user, not settled here): K16's gates, objective and tie rule are given (section 13
  inside Freeze A), and the open K16 item is the sample spec. `STATE.md` still lists K16 under `needs_user`, which this reading narrows to
  the spec. If the user does not read section 16's acceptance as giving K16's hard gates (R02), K16 is open as a whole.
- Section 13 also fixes what the spec must satisfy: one shared `element_sim` sample; 4 true-rigidity bins at the generator's
  equal-population quartiles; 12,000 events per bin per charge (96,000 events); no development results enter; `rho_sigma/|rho|` at most 0.1
  at the top bin's upper edge from truth, else that bin is ungated with the obligation open.
- Not blocking: K18's confirmation data (default "no post-selection quality claim", `decisions.md` K18) and K17 (two fixed configurations,
  no search).

## Is there a built `simreco`?

**No built `simreco` usable for T15b exists in the tree or in this task's records.** Searched:

| Where | Found |
| --- | --- |
| The tree: `adapters/geant4/assets/simreco/` | Sources only (`CMakeLists.txt`, `simreco.cc`, `Fit.hh`, schemas). `simreco.cc` SHA-256 `e5ea011e...`, last changed at 2a0b9f29 |
| `adapters`, `tools` (`*.py`) | `geant4_run.py` (`build-sim --program simreco`; `reco`, which needs a built `simreco` and refuses with `missing-dependency` otherwise) and `simreco_spec.py`. No binary |
| Records under `docs/dev`: `detector-reconstruction/` (decisions.md, t03-selection.md, t07-t09-task-sheets.md, coverage.md, t04-values-v*.md, closeouts), `geant4-architecture/` (g4sim task, S4, S5, approvals), `frontend-electronics/` | `simreco` named as a tool and a domain; no build or run of it for this task. `decisions.md` K02 basis: "`simreco` in the tree, simulated events only" |
| `VALIDATION.md` GEANT4-REGISTER (2026-10-30, E5) | `build-sim --configure-with geant4-config ... simreco` ok, and J15 run 200 events. A one-off check of the adapter, in a work folder not recorded; not a build of this branch |
| `<private>` (job and evidence folders), the home folder, the node-local temporary folder | None, except a session's temporary copy (`truesigma/simreco` under a Claude Code job folder in the home folder) whose `simreco.cc` is `db15c31a...` (not this branch's source) |
| The g4sim work area on the group file system (`g4sim-references/g4sim_run-build12` to `-build28`) | 17 binaries named `simreco`, built 2026-11-09 by g4sim sessions; no record ties any of them to this branch's source, and g4sim's S4 changed `simreco`. Not usable: no build record, source unknown; jobs build and run from a checked snapshot |
| The simcal private clone | Plan text and examples only; no build record for this task |

Building it needs no Geant4: `simreco` is C++17 standard library only (`CMakeLists.txt`). The **input** does: the shared sample needs
`element_sim` (Geant4 11.4.3, the conda installation registered in GEANT4-REGISTER) and `simroot` (ROOT) to dump its crossings. No
`element_sim` run at this sample's size is recorded, so its cost is unknown (`k12-targets-draft.md`, "No record").

**A defect found while searching.** Upstream e0a10d44 ("simreco gives a digitized hit the RMS error of its cluster", plugin 0.61.0):
`StripSigma` was 5 % to 72 % too small, about 14 % on J15's bending strips, giving chi2/ndof 1.197 against 1.001. This branch is based on
0.58.0 and has the old `simreco.cc` (`e5ea011e...`; upstream main is `db15c31a...`). With noise-digitization on, section 13's `rho_pull`
width gates would test the known-wrong hit errors. With it off, hits carry the spec's nominal Gaussian errors and the defect does not enter.
The spec has to say which; the choice is part of the sample spec.

## Runnable now, without the user

1. **T15a's widening (code, T2):** the selection record's `role` is fixed to `artificial-witness` and `_quality`'s witness exception must be
   gated on that role when widened (`decisions.md`, T15a readings; `contract-map.md`). Writable and unit-testable now with artificial
   fixtures for A50, A51 and A53 (fastest candidate failing quality; a tie and an undominated pair; candidates on different populations,
   stages or cost boundaries refused).
2. **The K16 scorer on synthetic records:** the 96 tests with section 13's `alpha` and `z1`, the paired efficiency bound, the alternating
   chunk CPU measurement with the cold chunk apart, the bootstrap tie rule, "no qualified candidate". Testable against hand-made records.
3. **A draft of the `element_sim` sample spec** meeting section 13's constraints, for the user's freeze by hash (drafting only).
4. **A build job draft** for `simreco` from the snapshot (`cmake/3.28`), with `tests/adapters/test_simreco.py`, and a 200-event pilot of
   `simreco-pr-a`, `-pr-b` and the comparator on a small development sample (not the shared sample). Its submission falls under the
   coordinator's standing rule for reconstruction jobs, if the coordinator reads it so; every result is a cost and smoke reading only.

## Needs the user

1. **The `element_sim` sample spec, named and frozen by hash** (Freeze A leaves it out; R02). Including noise-digitization on or off.
2. Confirmation of the K16 reading above (section 13 in Freeze A gives the gates and objective), or K16's gates if not.
3. The resources for generating 96,000 `element_sim` events and the paired run (K10, K17: Slurm requests are the user's), after a pilot
   gives a recorded cost.
4. If digitization is wanted: whether the 0.61.0 `simreco` fix comes to this branch first (a rebase or a cherry-pick is a change of the
   candidate's code; the user's call, since it moves the branch's base).

A01 stays open whatever T15b gives: `simreco` has no vertexing and runs only on `element_sim` events, so it cannot be T07's second backend
on T07's domain (`t07-t09-task-sheets.md`, T07 acceptance; U-K7).

## Recommended question for the user

"For T15b, shall I draft the K16 `element_sim` sample spec (section 13: 4 rigidity quartile bins, 12,000 events per bin per charge,
`rho_sigma/|rho|` at most 0.1 at the top edge) for your freeze by hash, with noise-digitization off, since this branch's `simreco` predates
the 0.61.0 strip-error fix? (Recommended: yes.)"
