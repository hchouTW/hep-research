# T04 version 4: dispositions of the third review

Source: `<private>/evidence/20261106T102310Z-b3-review/verdict.md`, 22 findings. Sections named are those of t04-values-v4.md.

Round 1 counts: 20 fixed, 0 rejected, 2 left open (15 in part, 20 in part). Where the verdict offered a route and v4 took another, the row says so. Several fixes rest on pending scripts; the last column says which. This table is as of round 1, except where round 2 below changes it: rows 2, 3, 8 and 10 in particular.

| # | Severity | Action | Where in v4 | Remaining doubt |
| --- | --- | --- | --- | --- |
| 1 | Blocker | Fixed. Fixture table with every parameter, version field, objects per event and references. Design numbers rechecked | 4, 4.4 | Retentions are assumptions. `E_ref` and `f_ref` are pending. T08 and T09 values have seen no recipe |
| 2 | Blocker | Fixed, and in round 2 tightened: all edges and all ranges fixed at Freeze A, with no change at any Freeze B. Recipe, configuration and budgets frozen by hash at Freeze B | 2.2, 3.3, 10 | A correct fit failing in E2 or B2 fails the workflow until the user amends (section 16) |
| 3 | Blocker | Fixed. Fixture-derived `f_ref`, absolute cap `C` at Freeze A, two-sample stability test with development uncertainty, stated development size and frozen hash | 8.3 | `f_ref` pending. The closed form is an order-of-magnitude estimate. With `f_ref` tiny, `C` = 0.005 in practice: the fixture justifies that it cannot hurt a correct recipe, not that 0.005 is the right value. The user chooses (section 16) |
| 4 | Blocker | Fixed. Fail defined, result table, ungated mapped to `inconclusive` with `required: no` and obligation open, minimum gated sets | 5.2, 10 | Ungated-as-`inconclusive` next to "inconclusive gives `failed`" needs the `required` field to read correctly. An alternative reading of R11 is noted below |
| 5 | Blocker | Fixed. Definitions table covers every listed item. Event strata remove the overflow case and the vertex-axis conflict | 7, 3.2, 5.1, 5.2 | None on the list. Recipes must be able to output these quantities |
| 6 | Major | Fixed. Cap of 2, declared blocks, return to Freeze B, no top-up, count reported, second attempt at 99 % | 3.4 | Cap is the user's |
| 7 | Major | Fixed by the verdict's first route: cap 0.0108, one value for both statistics, slack stated as a function of `se`. No count minimum | 5.1, 5.3 | Vertices at worst correlation sit at the cap (4.4) |
| 8 | Major | Fixed by the verdict's second route: the fixture table shows generation per charge is unnecessary. Every event has at least 3 tracks of each charge | 4.1, 4.4 | At worst correlation this holds for retention down to about 0.76 |
| 9 | Major | Fixed. `N_min = 30/L` events, `U = max(U_A, U_B)`, one rule for all `k`. The verdict's example form (DEFF floored at small `k`) was tried and rejected: a variant was non-monotonic in 24 of 40 closed-form cases (run while drafting, not kept in the script). Step 1 stops a short gate reading as fail unless the bound is wholly outside | 5.2 | Rate at varying objects per event pending `calc-rate-rule.py`. The 30 is a design choice |
| 10 | Major | Fixed. (a) reconstructable from the fixture; (b) noise floor from `p_w`; (c) references stated or "none exists", with vertex finding on a floor and T08 near on total energy; (d) `delta(R)` frozen at A | 4, 5.2, 7, 8.2, 8.5, 9.1 | The noise floor is a lower limit from a simple argument. Vertex floor 0.95 is judgment, not closure |
| 11 | Major | Fixed. Conditions stated, rate slack table, skew value, decision on development outside conditions | 5.4, 2.3 | Slack is at known DEFF |
| 12 | Major | Fixed. Recipe named per gate; refit gated on clean, 252 tests; noise refit stated as adding nothing, and why | 8.1, 8.2, 16 | User's choice. Also added: 24 noise tests from split gates, 120 angle tests |
| 13 | Major | Fixed. Each item has a rule, or is marked with reason and obligation open. Axes the fixtures do not vary now read "not tested", never "reported". Few photons has a rule | 9.2, 9.4, 10 | Few-photon pulls stay ungated. First-time negative case sensitivity is unshown |
| 14 | Major | Fixed. The verdict's wording adopted. Added the angle slices, which close the hole for slope sign only | 1, 8.2, 17 | Position sign stays open |
| 15 | Major | Part fixed, part open. Gates, bins, comparator, tests and CPU method are listed, for tracking only. Open: no `element_sim` spec exists to name, so the sample cannot yet be frozen | 13 | Read from `simreco.cc` at this base: recheck at T15b. Hard gates are the user's (R02) |
| 16 | Major | Fixed by the edit list below, applied at Freeze A | 2.1, this file | Not applied until Freeze A, by instruction |
| 17 | Minor | Fixed. Fail is tested before the cap | 5.2 | None |
| 18 | Minor | Fixed. Range on the trimmed centre: 80, not 200. Known limits says gates apply where the task is easy | 3.3, 17 | Toy basis |
| 19 | Minor | Fixed. Union `alpha`, one-sided `z`, "10 % cut from each side" | 5.1, 5.3 | None |
| 20 | Minor | Part fixed, part open. Labels added, `sigma_68` 0.962, earlier-rule numbers marked, closed form quoted. Open: the table with the gate's own bootstrap awaits a job | 5.5, 15, 18 | `calc-pull-table.py` uses B = 200, not 1,000 |
| 21 | Minor | Fixed. Alternatives recomputed with M = 1,260; "size" is retained objects, generated shown apart | 16 | None |
| 22 | Minor | Fixed. 50 % stays primary, a disagreement blocks one sentence only. Each freeze by SHA-256 on the user's word | 2, 7 | The 0.005 and 0.02 sensitivity thresholds are design choices |

## Round 2: recheck findings

Source: `<private>/evidence/t04-v4/recheck.md`, 4 blockers, 14 major, 8 minor. Counts: 25 fixed, 0 rejected, 1 left open (R14 in part). "Fixed" means the text or script changed; pending scripts still have to confirm numbers.

| # | Severity | Action | Where in v4 | Remaining doubt |
| --- | --- | --- | --- | --- |
| R1 | Blocker | Fixed, by the ruling. A return leaves ranges final; only hashes and `r_dev` renew | 3.4, 10 | None |
| R2 | Blocker | Fixed by deletion, by the ruling. VR-T08 and VR-T09 gone, ranges fixed at Freeze A, outcome removed from Freeze B, E2 and B2 required. Counts now T08 80 + 21, T09 270 + 63 | 2.2, 3.3, 10, 16 | The frozen-reference route is listed as the alternative |
| R3 | Blocker | Fixed. Full definition: components, peaks, sharing, iterations, start, position, per-object uncertainty, which sums enter, target arguments, interpolation. Script follows it and yields pulls | 7.1, 4.2 | Same author wrote text and script, so a shared mistake is possible |
| R4 | Blocker | Fixed by arithmetic, no tolerance widened. Noise 1 to 0.2 MeV, threshold 3 to 0.6 MeV; sharing 30 iterations with cell-integrated weights; Fisher uncertainty for two peaks; dead target conditioned on truth x, y; edge at four exact `t`. Far stays [3, 8): spread falls from 2.2 to under 0.08 sigma on the expected image | 4.2, 7.1, 5.4 | All checks are on the expected image. Pulls with real fluctuations near `d` = 3 are pending |
| R5 | Major | Fixed. `calc-t08-reference.py` rewritten: every component handled, E from 80 MeV, d nodes as asked, edge boundary on a cell edge, dead by sub-cell | 18 | Not run |
| R6 | Major | Fixed. Decision rule per result, all scripts required | 18 | One rule ("stop") needs judgment by design |
| R7 | Major | Fixed. Way out deleted. Sample, bins, level given. First-time sensitivity shown in closed form: about 7 sigma | 9.4 | Dead case pending, with a stated rule |
| R8 | Major | Fixed. Wilks claim withdrawn, `calc-t09-null-h2.py` added, penalty in 5.4, rule in 18 | 5.4, 7, 18 | 600 events per `N_exp` bound the tail at about 0.5 %. Nelder-Mead stopping early understates it |
| R9 | Major | Fixed. Geometry written. Region is a stratum truth function. Round 3 replaced the `D_bar` requirement by a direct miss-rate test (S1) | 4.3, 7, 9.4 | None |
| R10 | Major | Fixed. E1 ungated by a stated closed-form rule | 3.3 | None |
| R11 | Major | Fixed. Generators frozen at Freeze A, T07's as an addendum before its first development run, plus a deterministic agreement check | 2.1 | T07 exception |
| R12 | Major | Fixed. Text as asked; void counts as fail | 2.2, 10, 1 | How a forbidden constant is found is by reading configuration |
| R13 | Major | Fixed by the fixture: vertices on a line, third beyond second. 0.027 % at o3 | 4.1 | None |
| R14 | Major | Part open. Headers read and confirmed. Vertices now separated along the seeder's z, near one line. No run exists | 4.1, 8.5, 17 | Vertex finding at 0.95 is unproved for this seeder. T07's 1,260 tests cannot shrink |
| R15 | Major | Fixed. "Takes their place" withdrawn; stated in sections 1, 9.1, 17 and the obligation list. The optional [2.5, 3) gate was not added | 1, 9.1, 10, 17 | None |
| R16 | Major | Fixed. All listed items | 7, 5.2, 8.3, 4.3, 10, 3.2 | None |
| R17 | Major | Fixed as tabled, in the script | 18 | Not run |
| R18 | Major | Fixed. `obligations` table in coverage.md, owners named, `done (narrowed claim)`, plan 11.4 dimensions as a user decision | 10, 16 | Most have no owner: the user decides |
| M1 | Minor | Fixed: number replaced; thresholds changed, `b` flat at 3.0 MeV | 4.2 | None |
| M2 | Minor | Fixed: 45,000, controls included; VR samples gone | 3.2 | None |
| M3 | Minor | Fixed: ceiling record deleted | 2.2, 8.3 | None |
| M4 | Minor | Fixed: near is one table; fake result called an extrapolation | 4.2, 8.3 | None |
| M5 | Minor | Fixed: clause (b) tied to gated pulls | 7, 9.3 | None |
| M6 | Minor | Fixed: stated, in 5.4; pair nodes at 12,000; iso pooled | 4.2, 5.4 | Costs 0.011 sigma of slack |
| M7 | Minor | Fixed: new block needs a recorded functional change | 2.2, 3.2 | "Functional" is a reader's judgment |
| M8 | Minor | Fixed: Known limit, and the script runs 9,120 events | 17, 18 | None |

## Round 3: second recheck findings

Source: `<private>/evidence/t04-v4/recheck2.md`, 3 blockers, 10 major, 8 minor, verdict "fixes needed, no further review". Counts: 20 fixed, 1 needing no change (M7, as the recheck says), 0 rejected, 0 left open. R14 from round 2 stays open. S-numbers are that file's findings.

| # | Severity | Action | Where in v4 | Remaining doubt |
| --- | --- | --- | --- | --- |
| S1 | Blocker | Fixed as written. `D_bar` requirement deleted, now a reported figure. Corner block added to `calc-t09-null-h2.py`. Rule has an exit at 0.8 | 7, 9.4, 15, 17, 18 | H2 is started at truth, so the count is a lower limit on the miss rate. The script carries out the raise itself, so the log holds it |
| S2 | Blocker | Fixed as written. Script prints a `POOLED` line; "lower the cap" deleted | 18 | None |
| S3 | Blocker | Fixed as written, with one addition: the script now prints `BIN` lines, so the rule reads printed numbers. Energy nodes changed so that bin edges are nodes. Far position bias added | 5.4, 17, 18 | Bin width from weighted node widths is not the exact width of the mixture. Far position in E2 has 0.01 of margin on coarse numbers, so a raise of far's edge is possible |
| S4 | Major | Fixed. 0.992 reproduced by `calc-t08-closed.py` (60 slices). 0.84, 0.77 written | 3.3, 4.2, 5.2, 9.1, 9.2 | 0.77 is the recheck's Poisson-exact value, not recomputed here |
| S5 | Major | Fixed. Text added, obligation added, disposition row corrected, optional sample in section 16 | 4.2, 10, 16, 17 | None |
| S6 | Major | Fixed. Reason corrected, row in section 16, `b_sat` added to the script so the choice is open | 9.2, 16, 17 | None |
| S7 | Major | Fixed for all three scripts; the others already printed per job | 18 | None |
| S8 | Major | Fixed as written | 2.1 | Comparison code is not written yet |
| S9 | Major | Fixed as written. `PATCH` constant. The script does the doubling. Added an exit for the row at 200 | 18 | None |
| S10 | Major | Fixed as written. The script does both reruns | 18 | None |
| S11 | Major | Fixed, four lines | 4.2, 7, 7.1 | None |
| S12 | Major | Fixed. Trimmed mean in every `b` and pull; far efficiency row; script prints the closed-form value at each pair node | 4.2, 18 | None |
| S13 | Major | Fixed | 9.1, 10, 17 | None |
| M1 | Minor | Fixed. Script already kept this order | 4.2, 7.1 | None |
| M2 | Minor | Fixed | 8.3 | None |
| M3 | Minor | Fixed | Script | None |
| M4 | Minor | Fixed | 18 | None |
| M5 | Minor | Fixed: "about 0.09" | 4.2, 5.4 | None |
| M6 | Minor | Fixed: bound in Known limits | 17 | None |
| M7 | Minor | No change: the recheck accepts it | 18 | 10 % chance of a needless raise |
| M8 | Minor | Fixed: hashes taken last, estimates replaced, jobs regrouped | 18 | None |

Beyond the recheck, each stated here:

- The `fired` rule now reads `3 se + 3/n`, with `se` from the closed-form `p`. With the script's old `se`, nodes where every event fired had a near-zero `se`, and a closed form of 0.99998 would have tripped it.
- `|b - b_iso|` gained a 3 `se` margin, and split and T09's rate rows too, as the coordinator asked for every rule.
- "Stop" now always returns to the user. The T08 row's "the stratum's tests become reported" is deleted, because that was an agent's choice.
- The fake halving has an exit: twice, then stop.
- Jobs regrouped to fit the limit: A holds T08, the T09 fits, pull and rate; B holds the H2 study and fake.

## Changes that go beyond the findings

The user should see these, because they alter v3 scope or a v3 number. All are set before any result.

| Change | Reason | Direction |
| --- | --- | --- |
| T08 near bins: per-shower pulls ungated, total energy gated | A correct recipe merges many near showers, so the per-shower pull has no closure meaning | Narrower than v3's listing. Sharing in near untested. Obligation open |
| T08 merge in E1: reported, not gated (round 2) | There the second seed may not fire; that loss is already in efficiency, and counting it as merge would fail correct code | One test fewer per far E1 bin. T08 total 101. Obligation open |
| T08 saturated energy: reported, by choice | A truth-side target exists, as for dead cells. It is not gated in this version, to keep T08 simple. Deterministic flag check stays. A recipe that drops or wraps clipped cells passes | Narrower. Obligation open. User's choice, section 16 |
| T08 dead and edge: event sum, conditioned on truth | Unconditioned targets fail by arithmetic | Same 6 tests |
| T08 fixture: noise 0.2 MeV, threshold 0.6 MeV (round 2) | Removes a 17 MeV loss and a spread excess | No gate widened, but gates become blind here: an omitted or wrong `sigma_n` passes every gate, and threshold handling is sensed only in E2, to about 1 MeV of `b`. The noise-dominated regime is untested, an open obligation. "Low thresholds" now means seed threshold in E1 |
| E2 and B2: required, ranges fixed (round 2, ruling) | Requiredness may not move after development | Stricter. Risk of `failed` from a method limit, section 16 |
| T07 vertices: along v, near one line (round 2) | Same-z vertices are out of reach of the named seeder by its headers | Fixture narrower in geometry. Known limit |
| T09 mis-ID region: separation at least 0.4 `R_s`, miss rate tested directly with time (round 3) | With a penalty of 30, `D_bar` 10 is missed 65 % of the time, and charge-only `D_bar` is the wrong quantity | Region set by rule. Without a penalty the sheet's "not preferred for raw likelihood" has no rule |
| T09 valid range: 80, not 200 | Finding 18 | More bins gated |
| T08 energy target: `E - b`, from a reference coding | Thresholds move the sum | Depends on an independent coding of the same definition |
| Duplicates on noise: fixed 1 % | The ceiling was v3's self-referential rule | Stricter |

## Alternative reading of R11 for finding 4

R11 says a task is `failed` when "a required check ran and failed or was inconclusive". v4 makes ungated `inconclusive` with `required: no`, so an ungated bin does not fail the task. The other reading would make every ungated bin `failed`. T08 and T09 could then never be `done`, since E1 and B1 pulls are ungated at Freeze A. v4's reading follows Section 11.3.2: narrow the claim, keep the obligation. The recheck found it defensible (R37 precedent). The user may prefer otherwise.

## Edits needed at Freeze A

Not applied. Applied together, in the Freeze A commit, then hashed (section 2.1).

### t04-prereg.md

| Line | Replace | With |
| --- | --- | --- |
| 3 | `No threshold is set here; proposed values are in t04-values-v3.md, not frozen. Entries marked `<freeze>` are the user's (R02); none may be set after seeing results (Section 1.3 item 8).` | `Thresholds are in t04-values-v4.md, frozen at Freeze A by SHA-256. Entries marked `<freeze>` are the user's (R02). None may be set after seeing results (Section 1.3 item 8), with these exceptions only, each bounded by its rule in t04-values-v4.md, section 2.2: recipe, configuration and budget hashes, and `r_dev`.` |
| 9, Calorimetry | `Named energy kind: scale, core, tails; containment, linearity; split and merge rates` | `Named energy kind: scale, core, tails; containment (edge control), linearity (centre per energy bin); merge rate gated; split rate reported` |
| 9, Photon | `Vertex, time, direction, visible energy; topology mis-ID` | `Vertex, time, direction, visible energy; fit failure, wrong minimum, topology mis-ID` |
| 10, Tracking | `Momentum, angle, occupancy, material` | `Momentum, occupancy (bins); angle (pooled slices). Material: not tested, obligation open` |
| 10, Calorimetry | `Energy, particle type, angle, overlap` | `Energy, overlap. Particle type, angle: not tested, obligation open` |
| 10, Photon | `Photon count, position, medium` | `Photon count, position. Medium: not tested, obligation open` |
| 11, Tracking | `Fiducial truth objects for efficiency; reconstructed objects for fakes; resolution on matches only, reported with efficiency` | Same, plus `; duplicates on the reconstructed convention` |
| 12, all | `<freeze>` observable and threshold; ties; one-to-one rule; sensitivity evaluated, and `<freeze>` twice | `t04-values-v4.md, section 7` |
| 15, all | `<freeze>` | `t04-values-v4.md` |
| 23 | `<freeze>` wall time, memory, retries, trial budgets | `Algorithmic budgets frozen by hash at Freeze B; wall time, memory and retries at each job's approval (K10).` |
| 52 | Targets are `<freeze>`. | Unchanged: K12 has no targets yet |

### t07-t09-task-sheets.md

| Line | Replace | With |
| --- | --- | --- |
| 3 | `` `<freeze>` values are the user's and are set before any run (t04-prereg.md). `` | `` `<freeze>` values are the user's. They are frozen at Freeze A, before any development run, except the items in t04-values-v4.md, section 2.2, frozen at Freeze B, before any evaluation sample (t04-prereg.md). `` |
| 35, T07 Acceptance | `Quality: t04-prereg.md; pass or fail only after K09.` | `Quality: t04-values-v4.md and t04-prereg.md; pass or fail only after K09. Refit gated on the clean fixture, truth-assisted, counted apart.` |
| 37, T07 Stop | `Tolerances do not move after results.` | `Tolerances and valid ranges do not move after results.` |
| 44, T08 Input | `synthetic grid events with stated shower profiles` | `synthetic grid events, fixture t08-grid/1 (t04-values-v4.md, section 4.2),` |
| 52, T08 Acceptance | `Quality: t04-prereg.md.` | `Quality: t04-values-v4.md and t04-prereg.md.` |
| 53, T08 Open items | `whether the synthetic profile needs Geant4 tuning.` | `none for fixture t08-grid/1, which has no Geant4 tuning.` Keep the next sentence |
| 62, T09 Input | `events generated from a stated analytic light model` | `events from fixture t09-sphere/1 (t04-values-v4.md, section 4.3), a stated analytic light model` |
| 70, T09 Acceptance | `Quality: t04-prereg.md.` | `Quality: t04-values-v4.md and t04-prereg.md.` |
| New, T08 Steps | Add | `Clustering follows t04-values-v4.md, section 7.1, exactly. Configuration holds no constant derived from pulls or targets.` |

### Other records, at the same time

| File | Edit |
| --- | --- |
| finish-plan.md, D4 step 2 | `Draft bin edges, valid ranges and the noise-fixture fake ceiling, only by the stated rules.` becomes `Run the Freeze-B run; record hashes and r_dev, only by the stated rules. Bin edges and valid ranges are already fixed.` |
| coverage.md | New table `obligations`, from t04-values-v4.md, section 10 |
| finish-plan.md, D4 step 4 | After `A failure stands.` add `A retry follows t04-values-v4.md, section 3.4.` |
| decisions.md | The user's words for Freeze A, and SHA-256 of each frozen file |
| blockers/T04.md | Update on freeze |
| STATE.md | T04 state and `next_action` |

## Section 18 results, jobs 7474461 and 7474462

Both jobs `COMPLETED`, exit `0:0`, all six scripts exit 0, hashes in the receipts match section 18. Evidence: `<private>/evidence/t04-v4/job-a-7474461/`, `job-b-7474462/`. Rules applied as written. **Two stops recorded then; a third was found later, see the T08 row. No number in version 4 has moved, and none moves until the user answers.**

| Script | Rule | Result | Outcome |
| --- | --- | --- | --- |
| T08 | `fired` against closed form | 1 of 30 iso nodes over: E 80, fired 0.83670, closed 0.84327, `dev` 0.00657, limit 0.00640 | **Stop** |
| T08 | Constant `b_iso` | Worst node E 2378.4: 0.0128 sigma, limit 0.0374 sigma | No action |
| T08 | iso, edge, dead, near, far `BIN` limits | Corrected 2026-11-06: this row read "none over", from a comparison of 4-decimal prints. Iso E2 position y is 0.041206 against 0.041154 from the node values, x 0.041019; 153 others are under | **Stop**, found by the full read |
| T08 | Far merge | 21 values, none over, largest ratio to limit 0.021 | No action |
| T08 | Far efficiency | 22 values, none low, largest deficit 0.011 of its limit | No action |
| T08 | Iso split | 0.00000 in E2-E4 | No action |
| T09 | Range, pulls | `theta` and `phi` over limits at `N_exp` 80 and 120 (pooled centre -0.90 and -0.71, width 1.68 and 1.67), and also at 200 (-0.92, 1.60). `N_exp` weight also over at 80 (-0.126) | **Stop** (not clear at 200) |
| T09 | Fit failure, wrong minimum | Fit failure 0, missed better minimum 0 at 80 and above. Any `|pull|` above 5 is 23 %, with Hessian uncertainties, so not clause (b) as defined; it may be the same departure | Follows the stop above |
| T09 | Dead read as unhit | Patch 100 screen 0.120, patch 200 screen 0.486 | Would set `PATCH` to 200. Held: it uses the same fit |
| H2 | Tail above penalty | 30: 3 of 600 at `N_exp` 50, exactly 0.5 %, not above it; 0 of 600 at 1,000 | Penalty 30, no action |
| H2 | Two-source corner | 0 of 600 below the penalty | No action |
| Rate | Pass at `L` | Largest 7.0 % of 132 rows, limit 7.1 % | No action |
| Rate | Pass at slack | Smallest 100.0 % | No action |
| Pull | m = 1, true error 0.10 | Bias 4.0 %, width 4.8 %, limit 7.9 % | No action |
| Pull | `POOLED` | Centre +1.4 %, width +0.9 %, limit 9 % | No action |
| Pull | Fail at state `none` | None | No action |
| Fake | `f_ref` bound | Largest 1.0e-7, limit 1e-3 | `C` = 0.005 |

Coordinator's reading, not a finding. T09: generator and likelihood call the same `shape` and `direction` functions, and no mismatch was seen by reading them. The departure is confined to `theta`, `phi` and, at low `N_exp`, the weight; x, y, z and `t0` stay inside the limits at the pooled level. It does not shrink with `N_exp`, and at the smallest radii the `theta` centre grows with it. `phi` is wrapped before the pull and `theta` is not. Whether the cause is the reference script, its Hessian or the method is not known. T08: the excess is 3.1 standard errors at one of 30 nodes, and only few nodes are off plateau. Chance and a small missing term in the closed form both remain possible.

## Diagnostics for the two stops: reading rules

Requested by the user 2026-11-06. Fixed before any output exists. Scripts `<private>/evidence/t04-v4/diag/diag-t08.py` (`324acd28b16a57b1`), `diag-t09.py` (`2e485d7b3fcb2b8f`), job `<private>/jobs/t04-diag/diag.sh` (`55ffb8b8f7814f55`). Syntax-parsed only, not run, not independently reviewed. **Every outcome goes to the user. No T04 value moves from this output**, and section 18 stays as written.

**T08, node E 80.** Void unless the replay prints 0.83670 and 0.84327 and `gauss grid 6` prints 0.84327.

| Result, 300,000 new events, `3 se + 3/n` | Reading |
| --- | --- |
| Within the limit of `gauss grid 6` | Excess not reproduced; the first reading is compatible with chance |
| Over at `gauss grid 6`, within at `exact grid 96` | The closed form's approximation is the cause. The ladder names the term: position grid, Gaussian cell response, or both |
| Over at every rung | Stop stands. Something the closed form omits, in the fixture or the clusterer. `fired` against the seed-threshold rate says which |

**T09.** Void unless the `RAW` pooled rows at `N_exp` 80, 120, 200 reproduce job 7474461's centre and width to rounding.

| Check, pooled rows | Limit |
| --- | --- |
| D1 likelihood: `SCORE z`, 7 parameters at 4 `N_exp` | Any `|z|` above 3.5 fails. This does not depend on the optimizer or the error estimate |
| D2 fit: theta out of range, or gain above 0.5 | Either above 1 % fails |
| D3 error estimate: theta, phi sigma ratio at either step | Outside 0.9 to 1.1 fails |
| D4 pulls: `POLISHED` centre and width | Section 18's limits, pooled and radial |

| Outcome | Reading |
| --- | --- |
| D1 fails | Generator and likelihood disagree: reference script or fixture text. D2 to D4 are not read |
| D1 passes, D4 clears at 80 and 120 | The departure belongs to the reference script. Which of D2, D3 names the defect |
| D1 passes, D4 clears only at 200 or 1,000 | Method limit at low `N_exp`, against section 18's cap of 200 |
| D1 passes, D4 does not clear at 1,000 | Hessian pulls do not describe these parameters here, or the method fails. `2 dlnL` and the tangent rows are read to separate the two |

## Diagnostics for the two stops: results

Job 7477066, `COMPLETED`, exit `0:0`, 6 min 45 s, both scripts exit 0, empty error logs. Evidence: `<private>/evidence/t04-v4/job-diag-7477066/`. Neither part is void: the T08 replay printed 0.83670 and 0.84327, and the T09 `RAW` rows match job 7474461. **No T04 value has moved.**

**T08: second row of the rules applies.** 300,000 new events give 0.840860, equal to the rate of any cell reaching the seed threshold, so the clusterer loses nothing.

| Closed form | Value | `dev` | Limit | |
| --- | --- | --- | --- | --- |
| Gaussian cell response, grid 6, 24 or 96 | 0.843273 | 0.002413 | 0.002001 | Over |
| Exact, `q x Poisson` + noise, grid 6, 24 or 96 | 0.840203 | 0.000657 | 0.002017 | Within |

The Gaussian approximation is the cause, overstating `p` by 0.0031 at E 80. The position grid is not: all three grids agree to six places. The approximation stands in section 4.2's efficiency row and in `R`; those values at other energies were not recomputed.

**T09: D1 passes, D2 fails, D3 passes, D4 falls outside the outcome table.**

| Check | Result |
| --- | --- |
| D1 score | Largest pooled `|z|` 2.83 of 28, limit 3.5. Variance over curvature within 8 % of 1. `2 dlnL` mean 6.90 to 7.06, chi2 7 gives 7. Generator and likelihood agree |
| D2 fit | Fit `theta` is out of range in 22.6 to 23.7 % of events, equal to the raw `any |pull| > 5` rate at every `N_exp`. Polishing gains nothing: gain above 0.5 is 0, and the truth start is never better by 0.5. The fits are at the minimum, at an equivalent angle pair |
| D3 error estimate | Sigma ratios 1.0 at both steps |
| D4, `N_exp` 80 | Not clear. Pooled: `N` centre -0.126. Radial: `theta` -0.140, `phi` -0.146, `t0` width 1.139, `N` -0.187 |
| D4, `N_exp` 120 | Clear, pooled and radial |
| D4, `N_exp` 200 | Pooled clear. One radial value over: `N` centre -0.123, limit 0.120 |
| D4, `N_exp` 1,000 | Clear, pooled and radial |

The theta and phi departure of the section 18 stop is a defect in `calc-t09-lowmu.py`: it wraps `phi` but compares an out-of-range `theta` with truth. After polishing and range mapping, pooled `theta` and `phi` clear at all four `N_exp`.

The rules did not provide for "clears at 120, not at 80". Neither row is claimed. What remains at 80 is not a direction problem. Coordinator's reading, not a finding: `SCORE z` for `N` at 80 is 2.83 in these same events, which alone implies a mean pull near -0.08, and the one-parameter toy of section 3.3 gives -0.035, together close to the -0.126 seen. So the same draw may explain most of it. The radial limits sit near 2 standard errors at n = 400, so single excesses there are expected. New events would decide; these cannot.

Consequences recorded for the user's decision:

- Corrected 2026-11-06: an earlier version of this line said version 4 does not define how direction enters a pull. That was wrong, from a search on `theta` and `phi`. Section 7 already names two direction components in the tangent plane at the truth direction. The script departed from version 4 in three ways: it gated `theta` and `phi`, its seventh parameter was `N_exp` where section 7 names `E_vis`, and it drew `theta` only from 0.5 to 2.6 where section 4.3 is isotropic. So the `N` excess at 80 above is on a parameter version 4 does not gate. Section 7 still leaves the tangent frame unstated.
- Not affected by the defect: x, y, z, `t0` and `N` pulls, the dead screen (x, y, z, `t0`), fit failure, and the H2 results, which use likelihood values, not angle differences.
- Wrong minimum clause (b) as defined would count the same out-of-range fits unless angles are mapped first.

## Round 4: rule for the user's decisions

Fixed before any output exists. Scripts `<private>/evidence/t04-v4/round4/calc-t08-exact.py` (`038462b5ab04ee49`), `calc-t09-range.py` (`ae61190114225994`), job `<private>/jobs/t04-round4/run.sh` (`aab787a884ccb392`). Syntax-parsed only, not run, not independently reviewed.

`calc-t09-range.py` follows sections 4.3 and 7: isotropic directions; x, y, z, `t0`, two tangent components, `E_vis`; new seed stream; 4,800 events per `N_exp`, 1,600 per radial bin. Limits keep section 18's form, `0.0356 + 1.645 se`, with `se` 1.03 and 0.962 over `sqrt(n)`; section 18's own values follow from it at n = 1,200 and 400.

| Rows | Centre | Width - 1 |
| --- | --- | --- |
| Pooled, n = 4,800 | 0.0601 | 0.0584 |
| Radial, n = 1,600 | 0.0780 | 0.0752 |
| Dead masked, n = 500 | 0.1114 | 0.1064 |

| Result | Action |
| --- | --- |
| `N_exp` 80: pooled and all three radial rows clear | Range stays 80 |
| 80 not clear, 120 clear on the same four rows | Range and the B1/B2 edge become 120 |
| Neither clear | Stop |
| Fit failure above 0.00805, or wrong minimum, clause (a) or (b), above 0.00466, at either `N_exp` (section 18's `0.5 L + 3 se`) | Stop |
| Dead masked, patch 200: any value over | Goes to the user. `PATCH` stays 200 unless the user changes it |
| T08: every `NODE` line within its limit | Section 4.2's values become the exact ones printed |
| T08: any `NODE` line over | Stop |

A row's kept count below its n is fit failure and is read above. A rule not listed leaves version 4 unchanged, and an outcome the table does not cover goes to the user.

## Round 4: results

Job 7477126, `COMPLETED`, exit `0:0`, 9 min 23 s, both scripts exit 0, empty error logs. Evidence: `<private>/evidence/t04-v4/job-round4-7477126/`. Script check line reproduces the diagnostic's 0.843273 and 0.840203.

**T09: second row applies. Range and the B1/B2 edge become 120.**

| Row | n | Over its limit |
| --- | --- | --- |
| `N_exp` 80, pooled | 4,800 | `E_vis` centre -0.062, limit 0.0601 |
| 80, `r/R_s` from 0 | 1,600 | None |
| 80, from 0.4 | 1,600 | `E_vis` centre -0.111, limit 0.0780 |
| 80, from 0.7 | 1,600 | None |
| `N_exp` 120, pooled and three radial | 4,800, 1,600 | None. Pooled `E_vis` centre -0.044 |
| Dead masked, patch 200 | 500 | None. Clause (a), clause (b), reversed: 1 of 500 each; largest pull 9.45 |

Fit failure, clause (a) and clause (b) are 0 at both `N_exp`, 4,800 events each. Tangent components and x, y, z, `t0` clear everywhere. `E_vis` and `N_exp` centres agree within 0.002, so the earlier parameter mismatch did not hide anything.

**T08: every node within its limit.** Section 4.2 takes the exact form. Rounded values do not change: `R(E1)` 0.99239 against 0.99244, `p` 0.8402 against 0.8433, corner 0.7671 against 0.7752, all rounding as quoted, except that 0.84 and 0.77 now round from a different value. Far E1 node mean 0.96006 against 0.96083.

Version 4 updated accordingly (section 18.1). Freeze A edits still to make in t04-prereg.md and the sheets: those listed above, plus the B1/B2 edge at 120, `PATCH` 200, and the exact efficiency form.

## Generators: review and rulings

Written from the text by a fresh author; reviewed by a second fresh reviewer: `<private>/evidence/t04-v4/generators-review.md`. Verdict: fixes needed, 1 blocker, 5 major, 9 minor. No wrong number, distribution, bin edge, seed use or control was found, by reading only: nothing has run. All findings accepted. Version 4 changed: section 2.1 (dark-count reference, new lines, byte-equality rule), 4.2 (saturation flag), 7.1 (cell frame, recipe reads raw values), 18 (four generator-check rows, closing the blocker). The rows are written before the job.

Fix round 1, then a scoped re-review by a third fresh reviewer: `<private>/evidence/t04-v4/generators-rereview.md`. 0 blockers, 2 major, 8 minor, majors both in section 18's new rows. Code ready for the job by hand trace; nothing has run. Section 18's rows rewritten: ordered, first match applies, every printed outcome listed. n1, n4, n5, n7, n8 fixed in version 4 and the sheets. n2 and n3 left: a docstring claim and two control assertions, correct today, and fixing them would change hashes for no present defect.

Added to the Freeze A edit list, after the table above: `t04-prereg.md` title loses "(draft)"; its State sentences now say frozen at Freeze A, K09 and K16 in version 4 except the `element_sim` spec, K12 targets after P2 (U10). Sheets: the T08 Interfaces list names the saturation flag.

## Full read before Freeze A

Fresh reader: `<private>/evidence/t04-v4/freeze-a-read.md`. Fixes needed, 1 blocker, 4 major, 24 minor. All 17 hashes matched. The blocker is the T08 stop above, confirmed by the coordinator's own recomputation. The user chose to find the cause rather than accept it: "I want correct method and right result", then "go ahead with the T08 diagnostic". Fixes for the majors and minors wait for its outcome, in one batch, so the hashes change once.

## T08 width diagnostic: reading rules

Fixed before any output exists. Script `<private>/evidence/t04-v4/diag-t08b/diag-t08-width.py` (`71437bce63bf10a2`), job `<private>/jobs/t04-diag-t08b/diag.sh` (`770ad76e243c4b2d`). Syntax-parsed only, not run, not independently reviewed. **Every outcome goes to the user. No T04 value moves from this output.** Section 18's rule and limit stay as written.

The script draws 60,000 new iso showers at each of the 9 E2 nodes, 540,000 in all, and at 4 nodes in E3 and E4 for the trend. Bin values use the same trapezoid weights. The limit keeps the rule's form, `0.0356 + 3 se` at the new n, about 0.0395.

Void unless `REPLAY` prints job 7474461's node widths: 1.0671, 1.0717 at 250 MeV; 1.0395, 1.0392 at 500 MeV.

| `BIN E2` values, x and y both | Reading |
| --- | --- |
| `raw` within the limit | The excess is not reproduced at this sample size |
| `raw` over, `cross` within | The term is a deterministic sub-cell shift. `closed` says whether the expected image accounts for it. `quad` says whether adding it to sigma would do |
| `raw` and `cross` over, `oracle` within | The term comes from the threshold, through cells entering and leaving, not from a fixed shift |
| `raw`, `cross` and `oracle` over | Cause not found. It is not the threshold; the evidence goes to the user |

An outcome the table does not cover goes to the user. Any fix to section 7.1 needs the user's word and a T08 rerun against the unchanged section 18 rule.

## T08 width diagnostic: results

Job 7478606, `COMPLETED`, exit `0:0`, 38 s, error logs empty. Evidence: `<private>/evidence/t04-v4/job-diag-t08b-7478606/`. `REPLAY` printed job 7474461's four widths exactly, so it is not void. **No T04 value has moved.**

| `BIN E2`, limit 0.039527 | x | y |
| --- | --- | --- |
| `raw` | 0.040374, over | 0.039683, over |
| `cross` | 0.040737, over | 0.039370, within by 0.00016 |
| `closed` | 0.049785 | 0.047645 |
| `quad` | 0.026758 | 0.026066 |
| `oracle` | 0.024994 | 0.025769, with widths below 1 |

The excess is reproduced with twice the events. The table's rows read "x and y both", and `cross` splits, so no row applies as written and the outcome goes to the user. In substance the third row fits best. At every node `cross` equals `raw` within noise, and the measured shift `scurve` is 0 to 0.0008 against about 0.011 needed at 250 MeV, so the coordinator's fixed-shift explanation is refuted. `closed` is worse than `raw`, so the expected-image shift is not present in the data, and `quad` improves the width only by inflating sigma with a term that does not exist. `oracle` removes the excess and overshoots, from 0.954 at 250 MeV to about 1 at 4 GeV.

Coordinator's reading, not a finding: section 7.1's sigma counts only the variance of cells kept, so it omits the variance of cells near `T_c` entering and leaving the sum, each with a long lever arm. `oracle` below 1 suggests a second, smaller effect: `v_c = q max(e_c, 0) + sigma_n^2` overstates the variance of empty cells. Neither is tested.

## T08 position uncertainty: test of the candidate

The user chose option A, verbatim: "go ahead with option A". Fixed before any output exists. Script `<private>/evidence/t04-v4/diag-t08c/test-t08-sigma.py` (`d94308d0d2bffefa`), job `<private>/jobs/t04-diag-t08c/diag.sh` (`d25356e1c5774991`). Syntax-parsed only, not run, not independently reviewed.

Candidate, one-peak objects, nothing fitted, no truth used: `sigma_x^2 = sum_c (x_c - x)^2 Var(T_c) / A^2`, likewise y, over the component and its 8-connected ring. `T_c = e_c 1(e_c >= T_c0)`, with `e_c` Gaussian of mean `mu_c = A g_c(x, y)` and variance `q mu_c + sigma_n^2`. Two-peak objects keep their Fisher uncertainty. The estimator and `sigma_A` do not change.

60,000 new iso showers at each of the 9 E2 nodes and at 1.41, 2, 2.83, 4, 8, 16 GeV. Void unless `REPLAY` prints job 7478606's widths: 1.0721, 1.0717 at 250 MeV; 1.0383, 1.0303 at 500 MeV.

| Result | Reading |
| --- | --- |
| `BIN E2` `new` within 0.039527 for x and y, and every `NODE` line within its limit of 0.0474, on either side of 1 | The candidate passes. It goes to the user for section 7.1, then T08's reference reruns against the unchanged section 18 rule |
| `BIN E2` within, some `NODE` over | It works on average only. Goes to the user |
| `BIN E2` over, on either side of 1 | The candidate fails. Evidence goes to the user; the cause stays open |

An outcome the table does not cover goes to the user. The candidate may not be adjusted after seeing this output and then counted as passed: a changed formula is a new test on new events.

### Result

Job 7478897, `COMPLETED`, exit `0:0`, 42 s, error logs empty. Evidence: `<private>/evidence/t04-v4/job-diag-t08c-7478897/`. `REPLAY` printed job 7478606's four widths exactly. **First row applies: the candidate passes. No T04 value has moved; section 7.1 waits for the user's word.**

| `BIN E2`, limit 0.039527 | Old | New |
| --- | --- | --- |
| x | 0.041533 | 0.008351 |
| y | 0.043113 | 0.009338 |

All 30 `NODE` lines are within 0.0474. New widths run from 0.9988 to 1.0167, and at 250 MeV are 1.0101 and 1.0118 against 1.0655 and 1.0671. Model and true spread agree within 1.5 % at 250 MeV and better above. Tails are 0.24 to 0.33 %, near the Gaussian 0.27 %. Centres are unchanged. All objects were one-peak, so this tests iso only. Edge, dead and saturation objects and the far and near strata have not been tested with it.

## T08 reference rerun: reading rule

Fixed before any output exists. Script `<private>/evidence/t04-v4/round5/calc-t08-reference.py` (`5f096622f3bbe1b3`), job `<private>/jobs/t04-round5/run.sh` (`ca0c6bf33188d7f6`). Syntax-parsed only, not run. It is round 3's script with two changes: section 7.1's uncertainty and the exact form in `p_closed`. Seeds are unchanged, so the events are job 7474461's.

Void, and goes to the user, unless every `CONST` line and every node's `n`, `b`, `se`, `sd`, `model`, `fired` and `E:` values equal job 7474461's. Only x and y lines, closed-form values and what follows from them may differ.

Section 18's T08 rows apply as written, with `closed` now exact. A value within 1e-4 of a limit is recomputed from its node values before it is read, because the prints have 4 decimals. Any stop goes to the user. With no stop, this job's log replaces job 7474461's T08 log in the freeze list, and the target tables, which should be equal, are confirmed.

### Rerun result

Job 7479146, `COMPLETED`, exit `0:0`, 5 min 24 s, error log empty. Evidence: `<private>/evidence/t04-v4/job-round5-7479146/`. Not void: same 764 lines, every `CONST`, `E:`, `total`, `b_far`, `edge`, `dead`, `sat` and `residual` line equal to job 7474461's, and iso and pair lines equal apart from closed-form values. No section 18 row fires: 30 `fired` nodes within, 154 value limits with none over and none within 1e-4, 21 merge values, 22 efficiency values. Iso E2 position `|s68 - 1|` 0.0078 and 0.0080, before 0.0410 and 0.0412. Far E2 from `d` 3: 0.0069 and 0.0097, before 0.0130 and 0.0156. This log replaces job 7474461's T08 log in the freeze list. The target tables are confirmed equal. The third stop is resolved.

## Batch of read fixes

All 28 findings applied by a fresh editor; no gate, limit, tolerance, range, edge, size, count or decision changed. Report: finish-plan workspace, `b4-batch-report.md`. One question it raised, whether the reference error 0.011 sigma covers the far nodes at `d` = 3, was settled from job 7479146's log: yes, 0.0067 at most from the core width, and section 4.2 says why. freeze-a.md's tables regenerated: job 7474461's T08 log stays listed as history.

## Final read, and the far stratum between d 6 and 8

Fresh reader: `<private>/evidence/t04-v4/freeze-a-read2.md`. Fixes needed, text only, 0 blocker, 1 major, 9 minor. Section 7.1 matches the code symbol by symbol, all changed numbers match their logs, all hashes match. Minors applied. The major: the reference grid has no far node between `d` 6 and 8, 2/5 of the gated range, where the new uncertainty takes over; that interval reaches bin values only by interpolation. The reader's rough bound puts the gate out of danger, and proposed narrowing the claim. The coordinator proposes measuring it instead, given the user's standard: "I want correct method and right result".

Fixed before any output exists. Script `<private>/evidence/t04-v4/diag-t08d/test-t08-far-gap.py` (`1031de6ddd3183f0`), job `<private>/jobs/t04-diag-t08d/run.sh` (`4a6d14009264c3df`). Syntax-parsed only, not run, not independently reviewed. Round 5's `pair()`, 12,000 events per node, 7 energies from 0.25 to 16 GeV, `d` 6.5, 7, 7.5.

Void unless each `REPLAY` line equals job 7479146's `BIN far ... from d 3.0` line on the fields it prints.

| Result | Reading |
| --- | --- |
| Every `GAP` line within section 18's far limits, every `NODE` width within its node limit, about 0.054, and `b_far` within 0.02 sigma + 3 `se` of its linear interpolation | The gap is measured and clean. Section 7.1's claim widens to it |
| `GAP` lines within, a `NODE` width over | Works on average only: goes to the user |
| A `GAP` line over, or `b_far` off its interpolation | Stop: goes to the user. Target tables may need these nodes |

An outcome the table does not cover goes to the user.

