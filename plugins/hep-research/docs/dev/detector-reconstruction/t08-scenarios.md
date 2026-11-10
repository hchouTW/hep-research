# T08 scenarios A15, A32 and A38 (D2 stage 4)

T08 is calorimetry (BP05), recipe `reco.calo.cell-cluster/1`, a development binding in Python on fixture t08-grid/1. Its sheet
(`t07-t09-task-sheets.md`) names scenarios A15, A32 and A38 (plan section 13), and `t05-task-sheets.md` maps them: A15 to T08 and
T12, A32 to T08, T12 and T11's design, A38 to T08. This file covers T08's part only. The full T08 close-out against its sheet
is `t08-closeout.md` (D2 stage 5). Paths are relative to `plugins/hep-research/`.

**Not judged here.** No quality or performance claim. Whether a variant is worse is K09's question at Freeze B, and whether it
is faster is K12's, which has no targets yet. Nothing here pre-judges either.

**Status words** (as `t07-closeout.md`): `met`, the evidence shows the item; `met with readings`, met, with a limit stated beside
it; `open`, work or a decision is still owed. One status per scenario. **Pending job t08-stage4** marks a scenario whose evidence
includes a step of that job: it stayed pending until the job passed; the coordinator set the final status after job 7557963. The status
the login evidence alone would support is named beside it.

**Evidence.** On login, hand-made events only: `tests/adapters/test_calo_scenarios.py` (23 tests: red first, then green; D2
stage 4 report and its fix round 1). Each test reruns in the stage 4 job (`jobs/t08-stage4/`, step `unit-tests-scenarios`). On
the fixture, the job's steps `a38-accounting`, `reference-selection`, `scenario-variants` and `example` (block 1).

## What the stage changed

- `t08_readings.py` read any product. They now refuse a product made with another configuration file than t08-grid/1's
  (`REFERENCE_CONFIGURATION_SHA256`). This was a defect: job 7479146's constants `b`, against which the readings form every
  target, carry t08-grid/1's selection. A product with another `T_c` was scored against them without a word.
- `t08_cai.py` took its `T_c` (the 2 `T_c` rule) from `--configuration`, whatever configuration the product was made with. It now
  refuses a product of another configuration file.
- `calo_cluster.py reconstruct` refuses payloads whose units are not those of the readout's raw values (`cell_chain.check_units`).
  Before, an already-calibrated readout (raw unit MeV) with an ADC pedestal and gain was calibrated again without a word.
- The product reader refuses an event whose kept, unclustered and dead cells do not add up to the grid's channels.
- New: `fixture_tools/t08_scenarios.py`.
  - `accounting` checks a product's kept cells against its input, payloads and own configuration: the 8-connected components
    of {live, `e_c` >= `T_c`} are formed from the input, and the kept cells must be exactly the seeded ones, each product
    component one of them (fix round 1, review F1), with the hit and unhit counts and sums.
  - `reference-selection` checks the reference clusterer's constants against the configuration's.
- Two stage 3 tests paired an ADC readout with MeV identity payloads, which the unit rule now refuses. Their readouts now
  declare MeV. Their intent and their test IDs are unchanged.

## Scenarios

| Scenario | Meaning for this binding, and its parts | Evidence | Status | What would close it, and the readings |
| --- | --- | --- | --- | --- |
| A15 | The plan: a faster but worse variant is rejected under fixed quality gates, or listed as a separate working point. Parts: (a) the variant is kept apart: a cheaper configuration (10 sharing iterations instead of 30; `T_c` 1.2 MeV instead of 0.6) is a whole configuration file whose SHA-256 every product records (no flag sets a single constant), and the consumers that hold t08-grid/1's references refuse its products; (b) rejection under the fixed gates, or listing as a working point | (a), mechanism shown on login: `A15WorkingPoints`: no reconstruct flag besides the six inputs; the product names its own file's SHA-256, unlike the frozen one; the 10-iteration product's two-peak event differs; the readings refuse both variants; CAI-T08-1 refuses a variant product. Job: `scenario-variants` (main E3 far). (b): none. The variant is refused before any gate, but no gate has run (K09) and no speed is measured against a target (K12) | open | (b): rejection under the gates needs K09 at Freeze B and T12 (quality before speed); listing needs a named working point in the configuration and the product (a format change, not made here), or T12's design. Reading on (a): the working point is identified by the configuration's SHA-256 only; the recipe name stays `reco.calo.cell-cluster/1` for any configuration |
| A32 | A changed threshold, cleaning or configuration changes the product's configuration identity. A consumer that holds a response, reference or check made with one configuration refuses a product of another, and the frozen selection applied to the changed product finds the change. T08 has no IRF: its consumers of that kind are the readings (job 7479146's constants `b`), the CAI checks and the accounting | `A32ConfigurationChange`: `T_c` 1.2 and 0.3 products break the frozen selection in both hand-made events, and pass under their own configuration; `accounting` refuses another configuration; CAI-T08-2 refuses two products of different configurations (existing check, D2 stage 2), and two products of one other configuration under the default one (review F4); CAI-T08-1 refuses a product made with another configuration than `--configuration`, whose thresholds it would use; multiplicity (`peaks_kept` 3) and model changes (null `q`) are refused in a t08-grid/1 configuration (existing). The readings refusal is shared with A15. Job: `scenario-variants` (the coarse variant must show the frozen selection's defects, the cheap one none) | met, T08's part (job 7557963, steps scenario-variants and a38-accounting) | T11's design and T12's runtime part of A32 are theirs |
| A38 | The plan: trigger, ROI or quality selection; shape, counts/exposure, hit/unhit and efficiency handled consistently; an unselected model or a repeated correction cannot pass. Here the selection is section 7.1's (`T_c`, `T_s`, kept components). Its seven parts are listed below the table, inside this row's status | See the parts below | open: part A38.3 (exposure) is open; the other six parts (A38.1, A38.2, A38.4 to A38.7) are shown in job 7557963 (a38-accounting: 0 defects in 15 strata; reference-selection; scenario-variants), A38.1, A38.4 and A38.7 with readings | See the parts below |

A38's parts. They carry no status of their own; the A38 row's status covers them.

- **A38.1, same selection.** The kept cells are exactly section 7.1's selection of the input under the configuration the product names; the reference clusterer's constants are that configuration's; the readings score only that configuration.
  - Evidence: `selection_defects` forms the 8-connected components of {live, `e_c` ≥ `T_c`} from the input and requires the kept set to be the seeded ones, each product component exactly one of them, and the dead channels the readout's. Tests: honest events give none; a seedless component under a seeded label (the review's probe), two labels on one component, one label over two components, other dead channels, a seed left out and an adjacent cell left out are each caught. `reference_selection_defects` catches each changed constant; the readings hold the frozen configuration's identity, `q` and `sigma_n`. Job: `reference-selection`, `a38-accounting` (all 15 development products against their regenerated inputs).
  - Reading: `reference-selection` compares six literals (`W`, `SN`, `Q`, `TC`, `TS`, `ITERS`). The script's window (`HALF` 16, a 33 × 33 window), `CLIP` 400 and its 8-connectivity and two kept peaks are read from its text, not compared. `selection_defects` checks the cell selection and components, not peaks, sharing, positions or uncertainties.
- **A38.2, counts and hit/unhit.** Every input event is in the product, in order, selected or not; every live cell is kept or unclustered; dead cells have no value; counts and sums account for the input.
  - Evidence: The reader refuses a product that does not cover every input event, in order, with its end count (existing); `test_counts_every_input_event_is_in_the_product_selected_or_not`: an event with no kept component is an event with no object and every live cell unclustered, and a product short of an event is refused; the reader's grid identity (kept + unclustered + dead = channels); `selection_defects`: the counts and the input, clustered and unclustered sums against the readout (1e-9 relative). Job: `a38-accounting`.
- **A38.3, exposure.** Live time, trigger or exposure.
  - Evidence: none. t08-grid/1 has no live time, trigger or exposure, so no exposure enters any T08 quantity, and no T08 test can show its handling.
  - Status of this part: open (the plan: a missing implementation is never "not applicable"). What would close it: a fixture with a trigger or live time and a test that counts and exposure follow the same selection (T12's design).
- **A38.4, shape.** The shape of a response is formed under the same selection as the targets.
  - Evidence: Every input event is kept with its event sum, objects and unclustered sum, selected or not (A38.2), so any distribution of them is formed over all events under one selection; the readings form pulls only against the targets of the same configuration (A38.1).
  - Reading: T08 builds no response histogram or IRF, so a response shape is not formed here; its gate is K09's. Closing it fully needs a response product (T12 or the C&A plan).
- **A38.5, efficiency reference.** The efficiency reference uses the exact cell response, with the same seed threshold.
  - Evidence: `reference-selection` (job) compares `TS` 10.0 MeV and the configuration's `q`, `sigma_n`. `t04-values-v4.md` line 901 and the script's `p_closed`: exact `q x Poisson` plus Gaussian noise up to 250 MeV, Gaussian above, where both give 1 to six places; cells with mean deposit under 1 MeV are left out of the exact product.
  - Readings: the reference is the probability that a seed fires; the readings' efficiency also needs a matched primary with uncertainty status ok. Comparing the two is the gate's (v4 9.1, K09).
- **A38.6, unselected model.** A product of another selection cannot pass.
  - Evidence: The readings refuse it (A15); `accounting` refuses another configuration.
- **A38.7, repeated correction.** A correction applied twice, or to values it was not made for, cannot pass.
  - Evidence: `test_a_correction_is_never_applied_to_values_it_was_not_made_for`: a calibrated readout with ADC payloads, an ADC readout with a gain for calibrated values, and a dividing gain in a multiplying unit are each refused, with nothing written; `test_a_gain_is_never_applied_twice_through_the_cai_checks`: CAI-T08-1 on a product that already consumed the derived gain is refused (existing check, D2 stage 2). Job: `scenario-variants`.
  - Reading: units cannot show a correction whose unit matches the values it is applied to again: a second gain in MeV/MeV on a readout that is already calibrated, or a second pedestal in adc on an ADC readout that is already pedestal-subtracted. The only MeV readout is the labelled zdcsim identity readout. Closing it needs a readout that records its own calibration state (a format change).

Summary: A15 open; A38 open (part A38.3, exposure), its other parts shown in job 7557963; A32 met, T08's part (job 7557963).

## The example

`examples/reconstruction-calorimetry/` meets the sheet's proposed file, on `examples/reconstruction-tracking/`'s pattern.

- **What it runs.** It generates 2 events of t08-grid/1 (block 1, main stratum 7: E3, far) through the harness and the frozen
  generator. The recipe reconstructs them in its own process, then `check-product` checks the product. Its offline replay runs 8
  checks: identities, labels, no truth on the data side, the double-count stop, A38's selection and accounting, and a rerun that
  must write the same bytes.
- **Tests.** `tests/examples/test_reconstruction_calorimetry.py` drives each check with one defect on a hand-made recording.
- **Status: met (job 7557963, step `example`).** Two live runs wrote the same bytes; the coordinator copied `recorded/` and `output/` from the job's evidence after the PASS (no host path, checked); the committed-recording tests pass on login.

## Also open, outside these rows

- Job of record 7557963 (hpa-wn34, 14 min 03 s, PASS). Earlier runs: 7557508 PASS, superseded (the example recording then failed the packaging scan on its .jsonl name); 7557888 FAIL in the example step (a missed rename in build.sh).
- The T08 close-out table is `t08-closeout.md`; the adapter record (0.2.0, `VALIDATION.md` CALO-CLUSTER-T08) is D2 stage 5's.
