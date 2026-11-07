# g4sim plan: addendum 11.1 after the S3 prototypes

**Status: decided by the maintainer (2026-11-06, "use your recommendations"; 2026-11-07, the same words on the review's findings) and applied to Part B. Targeted review (Section 23, step 4) done by an agent that did not write this; the maintainer's acceptance is recorded in `g4sim-approvals.md`, or is still open if it is not there.**

All results are from E5 (Geant4 11.4.3, conda build, serial). E2 is waived for the S3 prototypes (`g4sim-approvals.md`: "drop the Mac run"): they are confirmed on E5 only, and GB13, GB20 and GB21, which rest on rounding or bit identity, were not tested on arm64. Outputs below `~/AMS/hsinyichou/g4sim-references/s3-prototypes/`: `em/archive-gb11` (with `SHA256SUMS`), `em/logs/judge.out` (the final GB11 to GB14 verdict), `steps/verdict.json` (the falsifying verdict) and `steps/verdict-11.1.json` (the restated one).

## GB11 and GB12: PAI requests do nothing

**Target behavior as first written:** `AddPAIModel` before initialization makes `ActivatePAI` add PAI to the region (Section 6.2.9).

**Result: GB11 falsified.** For 8 ways of writing a request on `FTFP_BERT` and `FTFP_BERT_EMZ`, no particle gets a PAI model in any region, the process keeps its original number of models, and Geant4 prints no warning. check-spec's prediction fails in all 16 runs. GB12 was not itself falsified: the code it describes never runs.

**Cause, from the 11.4.3 source.** `ActivatePAI` runs from the EM constructor's `ConstructProcess` and skips any process whose `IsIonisationProcess()` is false (`G4EmModelActivator.cc`). That flag is false by default (`G4VEnergyLossProcess.hh` line 518) and is set only in `PreparePhysicsTable` (`G4VEnergyLossProcess.cc` line 221), which runs later.

| Form tested, 16 runs each | PAI applied as check-spec predicts | Models outside the region |
| --- | --- | --- |
| As first written | No, nothing applied | Unchanged |
| A: set the flag, run `G4EmModelActivator` again after the EM constructor | Yes; an `alpha` request gives alpha no PAI; repeated requests stack models | **Changed**. A `mu-` request replaces `MuBetheBloch` with `BetheBloch` and `UrbanFluc` with `UniFluc` in the whole detector; a `GenericIon` request replaces alpha's `BraggIon` and `BetheBloch` with `LindhardSorensen`; an `e-` request turns `UrbanFluc` into `UniFluc` |
| B: g4sim's own constructor adds the region's low-energy model and PAI with `AddEmModel`, and never calls `SetEmModel` or `SetFluctModel` | Yes, same request semantics | **Unchanged**, models and fluctuation models |

**Decision: B.** The check-spec rules of Section 6.2.9 stay, with reasons that no longer rest on Geant4 skipping or merging: the constructor has no guard, so check-spec is the only one. GB11 and GB12 are restated, and `g4sim_run` reads the models back in each region, compares them with a run without PAI, and refuses a difference outside the region. What was judged: which particles carry a PAI model in each region, for the accepted forms of request. Whether PAI's physics is right in a run is the thin-layer comparison of Section 11, still to run.

## GB19: an idle fast-simulation hook is not invisible

**Result: falsified as first written.** With `G4FastSimulationHelper::ActivateFastSimulation` on all particles, 6 of 600 events (seed 11) and 8 of 600 (seed 12) differ from the run without a hook, in steps, random state and navigation. `ModelTrigger` ran about 660,000 times and `DoIt` never. `G4FastSimulationManagerProcess` alone, with no model and no region, gives the same 6 events; an inert process of our own gives none. The mechanism is not established, and attachment to fewer particles was not tested.

**Decision.** S8 gate 3 becomes a paired equivalence test: same seeds, per-event differences of each observable grouped as in S3 gate 3, TOST at α = 0.05, margin ln 1.005 of the mean, passing only if all pass. A run with no `fast_sim_envelope` attaches no process. The test model's closure part is unchanged. **Restated result:** 1,200 paired events, mean difference 0.20 ± 0.17 MeV against a margin of 2.99 MeV; a 1% scaling is rejected. This tests the mean of total deposit only.

## GB20: replica and parameterised do not reproduce ordinary placements

**Result: falsified for replica and parameterised.**

- **Replica:** physics scorers differ in 62 of 400 events even at a dyadic pitch; at pitch 3.7, 361 of 400 differ and 143 of 4000 geantinos navigate differently.
- **Parameterised:** passes only where the cells fill the mother. Elsewhere steps in the mother differ in safety, multiple scattering chooses differently, and histories diverge (58 of 400 events in a gapped stack). On a 6×6 grid its contiguous copy numbers (i + 6j) contradict the packed numbering (i + 8j) of Section 6.2.6.
- **Assembly:** passes on all layouts, given a `SetCopyNo` pass, because `MakeImprint` alone numbers from 1. Against a module template with daughters the copy chain differs, because the imprint removes that level.

**Decision.** `placement_impl` keeps `assembly`, with the `SetCopyNo` pass, for a placement whose template has no daughters of its own; check-spec rejects the rest. Replica and parameterised are removed. **Restated result:** assembly bit-identical on all seven layouts.

## GB21 and GB17: readings ruled by the maintainer

- **GB21.** The killed-energy and sum identities hold at 1e-12 (worst 5.5e-15). The deposit identity missed 1e-12 relative to the continuous loss on 206 of 4855 kill steps in run `plain`, 206 of 4945 in `emit` and 26 of 4883 in `pixe`: the loss can only be measured as a difference of kinetic energies. In `plain` and `emit` all are within half an ulp of the pre-step energy; `pixe` reaches 3.26 ulp, several roundings deep, and includes a step with deposit 0. **Decision:** a step's deposit identity passes within 1e-12 or within 4 ulp of the pre-step kinetic energy. The first form, 4 ulp alone, failed on a step 35 ulp away but within 1e-12 of a large loss; the maintainer approved the corrected rule after that failure ("approve the GB21 rule").
- **GB17.** Every photon of the four `G4XTR*RadModel` classes is born on the envelope's surface. **Decision:** "inside the envelope" includes its surface. **Result:** all nine classes meet the criteria in the judged run. `G4StrawTubeXTRadiator` has no foil count and no structure, so check-spec rejects it.
- **GB15** (registered, no change to Part B). K = 70 and the sample sizes are in `adapters/geant4/tests/g4proto/s3_optics/registered_numbers.json`; r = 3 is recorded outside K. Observed cost with GB17: 1.9 core-hours against about 1 estimated.

## Passages of Part B

Changed: lines 6, 522, 548, 649, 651, 655, 657, 658, 659, 661, 662, 663, 664, 698, 807, 1289, 1303, 1485, 1508, 1566, 1742, 1746, 1872, 1880, 1958, 2007, 2021, 2022, 2027, 2029, 2030, 2031, 2105, 2126, 2130, 2131.

Checked, no change needed: lines 1295, 1763, 1873, 1912 (M11), 1938 (D20).

Task cards updated by step 5: S3, S8 (GB19, GB20, gate 3, `placement_impl`, a stated exception to "never loosened"), S7 (the straw class). S4, S6 and S9 do not depend on these GBs, and S5's labels still hold.

`g4sim-task.zh.md` stays frozen at plan version 11; the English text with this addendum governs. The maintainer's decision, 2026-11-07.

## Gaps carried to S4 and S7, no change in S3

Recorded in those cards' execution logs: `SetActiveVolume` cannot limit optical photons by volume; outside the optical scope photons die at the boundary by `NoRINDEX`, so the S7 control on `KillProcess` has nothing to act on; Section 10.4 omits that truncation shifts the means; `G4OpticalPhysics` attaches `G4EmSaturation` itself, unlike Section 10.3.
