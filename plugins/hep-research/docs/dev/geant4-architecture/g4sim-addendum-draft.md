# g4sim plan: draft addendum after the S3 prototypes

**Status: draft for targeted review (Section 23, step 4). Nothing here is in force, and Part B is unchanged.** Each proposal below is a recommendation. The maintainer decides, and only then are the passages listed under "Passages to modify" changed.

All results are from E5 (Geant4 11.4.3, conda build, serial). A falsification needs one environment; the fixes will need E2 as well. Archived outputs are below `~/AMS/hsinyichou/g4sim-references/s3-prototypes/`: `em/archive-gb11` (with `SHA256SUMS`) and `steps/` (`verdict.json`, `runs/`).

## GB11 and GB12: PAI requests do nothing

**Target behavior:** `AddPAIModel` before initialization makes `ActivatePAI` add PAI to the region (Section 6.2.9).

**Result, falsified.** For 8 ways of writing a request on `FTFP_BERT` and `FTFP_BERT_EMZ`, no particle gets a PAI model in any region, the process keeps its original number of models, and Geant4 prints no warning. `check-spec`'s prediction is wrong for all 16 runs.

**Cause, from the 11.4.3 source.** `ActivatePAI` runs from the EM constructor's `ConstructProcess` and skips any process whose `IsIonisationProcess()` is false (`G4EmModelActivator.cc`). That flag is false by default (`G4VEnergyLossProcess.hh` line 518) and is only set in `PreparePhysicsTable` (`G4VEnergyLossProcess.cc` line 221), which runs later.

**Candidates tested, on the same 16 runs:**

| Form | PAI applied as check-spec predicts | Models outside the region |
| --- | --- | --- |
| As Part B describes | No, nothing applied | Unchanged |
| A: set the flag, run `G4EmModelActivator` again after the EM constructor | Yes, 16 of 16; an `alpha` request gives alpha no PAI; repeated requests stack models | **Changed** for hadrons, muons and ions. A muon request replaces `MuBetheBloch` with `BetheBloch` and `UrbanFluc` with `UniFluc` in the whole detector; alpha's `BraggIon` and `BetheBloch` become `LindhardSorensen` |
| B: g4sim's own constructor adds the region's low-energy model and PAI with `AddEmModel`, and never calls `SetEmModel` or `SetFluctModel` | Yes, 16 of 16, same request semantics | **Unchanged**, by model name in all 16 runs |

**Proposal: B.** It keeps every check-spec rule of Section 6.2.9 and removes the side effect the plan had to work around: the "non-PAI vs PAI" comparison of Section 11 becomes clean. It does not yet show that PAI's physics is right in a run: that is the thin-layer comparison of Section 11, still to run. GB12 is restated as "PAI leaves models outside the region unchanged", judged by the effective config.

**Passages to modify:** 6.2.9 (PAI semantics, the `ActivatePAI` and `SetEmModel` points); 11 (`thin_layer_ionisation` row); 20 M11; the risk row "PAI changes default models outside the region"; 23 GB11, GB12; 19.2 S3 wording. Search hits checked: lines 548, 649, 651, 655, 661, 662, 1289, 1485, 1746, 1763, 1912, 1958, 2021, 2022.

## GB19: an idle fast-simulation hook is not invisible

**Target behavior:** a model that never triggers leaves step sequences and random-number use unchanged.

**Result, falsified.** With `G4FastSimulationHelper::ActivateFastSimulation` on all particles, 6 of 600 events (seed 11) and 8 of 600 (seed 12) differ from the run without a hook, in steps, random state and navigation. `ModelTrigger` ran about 660,000 times and `DoIt` never. `G4FastSimulationManagerProcess` alone, with no model and no region, gives the same 6 events; an inert process of our own gives none. Reproduced independently on a fresh run. The mechanism is not established. Attachment to fewer particles was not tested.

**Proposal.** S8 gate 3 becomes a statistical equivalence test of per-event observables with registered margins, and the bit-identity requirement is dropped. A run with no `fast_sim_envelope` attaches no process at all, so it stays bit-identical to itself. The test model's closure part of gate 3 is unchanged.

**Passages to modify:** 19.2 S8 gate 3; 23 GB19. Search hits checked: lines 1295, 1873, 1880, 2029.

## GB20: replica and parameterised do not reproduce ordinary placements

**Target behavior:** the three implementations give the same navigation, copy numbers and observables.

**Result, falsified for replica and parameterised.**

- **Replica:** physics scorers differ in 62 of 400 events even at a dyadic pitch; at pitch 3.7, 361 of 400 differ and 143 of 4000 geantinos navigate differently.
- **Parameterised:** passes only where the cells fill the mother. Elsewhere steps in the mother differ in safety, multiple scattering chooses differently, and histories diverge (58 of 400 events in a gapped stack). On a 6×6 grid its contiguous copy numbers (i + 6j) contradict the packed numbering (i + 8j), which is the cellID rule of Section 6.2.6.
- **Assembly:** passes on all layouts, given a `SetCopyNo` pass, because `MakeImprint` alone numbers from 1. Removing a level of mothers (module template) changes the copy chain, so it is not equivalent there.

**Proposal.** `placement_impl` keeps `assembly` as equivalent, with the `SetCopyNo` pass. Replica and parameterised are removed, or kept as declared non-equivalent options that change `run_id` and are judged statistically. Section 7.1's "do not change the semantics of cellIDs" is then true only for assembly.

**Passages to modify:** 7.1; 15.1 S8 row; 16 "Placement optimization"; 19.2 S8; 20 D20; 23 GB20; Appendix B rows for `placement_impl`. Search hits checked: lines 1508, 1566, 1872, 1883, 2030, 2130, 2131.

## Readings that need a ruling, not a design change

- **GB21:** the killed-energy and sum identities hold (worst 5.5e-15). "Deposit equals continuous loss" misses 1e-12 on 206 of 4855 steps, because the loss can only be measured as pre minus post kinetic energy, and one rounding of a double exceeds 1e-12 of a very small loss; all 206 are within half an ulp of the pre-step energy. The same bound is 3.3 ulp with along-step secondaries. Proposal: the tolerance applies to the sum, as the parenthesis of Section 23 can be read, and the deposit identity is judged within a stated number of ulps of the kinetic energy.
- **GB17:** every photon of the four `G4XTR*RadModel` classes is born on the envelope's surface, not inside it (trial: 0 inside, 808 to 990 on the surface). Proposal: "inside the envelope" includes its surface, to be decided before the judged run. `G4StrawTubeXTRadiator` has no foil count, so it does not fit the GB17 row or rule 5 of Section 11.
- **GB15:** the design needs its K = 70 and sample sizes registered: `adapters/geant4/tests/g4proto/s3_optics/registered_numbers.json`. Part B does not say whether r = 3 counts in K or what "close to the margin" means; the proposal is stated there. Run cost about 1 core-hour with GB17.

## Other gaps found (S7 and S4, no action in S3)

- `SetActiveVolume` cannot limit optical photons by volume: only `G4GeneralCerenkov` reads it, and that path crashed or produced no light (GB16).
- Outside the optical scope photons die at the boundary by `NoRINDEX`, so the S7 control "booking photons killed by `KillProcess`" has nothing to act on, and a kill after entry costs one zero-length step per photon.
- Section 10.4 names only extra variance for two components, but truncation also shifts the means: -45% and +105% at small yields in the trial.
- `G4OpticalPhysics` attaches `G4EmSaturation` itself, unlike what Section 10.3 says.
