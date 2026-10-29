# SYNTHETIC EVALUATION MATERIAL — invented content; no real detector, test beam, paper, or person.

## Manuscript
"A template-fit timing calibration for a LYSO crystal calorimeter prototype" (synthetic), method paper; major revision requested.

## Referee comments (synthetic, verbatim)

> **C1** The timing resolution versus energy is shown only for simulation. The paper's main claim needs test-beam data. Please add data.
>
> **C2** The origin of the constant term in the resolution parametrisation is not discussed.
>
> **C3** Temperature drift of the SiPM response must affect timing. Please quantify the resulting systematic uncertainty.
>
> **C4** Compare the template fit with a standard constant-fraction discriminator (CFD) approach on the same events.

## True state of the work as of 2026-10-29 (from the analysis log, synthetic)

- **C1 — IN PROGRESS.** Test-beam data were taken in August 2026 (synthetic facility, 5 beam energies: 1, 2, 3, 4, 5 GeV). Reconstruction done for all runs; timing analysis done for only 2 of 5 energies. Preliminary values: 42 ps at 3 GeV, 35 ps at 5 GeV. The group decided on 2026-10-24 that **preliminary values must not appear in the paper or in the reply** until all 5 energies are analysed and the calibration is frozen. No data figure exists yet.
- **C2 — DONE.** New Sec. 5.2 explains the constant term: dominated by clock distribution jitter and crystal-length light-path spread; fitted constant term c = 18 ± 3 ps (simulation).
- **C3 — PARTIAL.** Lab bench measurement gives a temperature coefficient of −0.9 ps/°C. It has **not** been propagated to a systematic on the resolution, because the test-beam temperature log is not yet processed. One sentence quoting the coefficient was added to Sec. 6.1.
- **C4 — DONE.** CFD vs template fit compared on the same simulated events: template fit better by 12% at 3 GeV. New Fig. 9, Sec. 6.2.

## Diff summary of the revised manuscript (from version control, synthetic)
- Sec. 4: **unchanged.**
- Sec. 5.2: new (C2).
- Sec. 6.1: +1 sentence (temperature coefficient).
- Sec. 6.2 + Fig. 9: new (C4).
- No new figures other than Fig. 9.

## "Summary of changes" template drafted by a co-author (to be filled in)

> 1. **C1:** We have added Fig. X showing the test-beam timing resolution as a function of energy, which agrees with simulation within Y%.
> 2. **C2:** We added Sec. 5.2 discussing the constant term (c = X ps).
> 3. **C3:** Sec. 4 has been rewritten to address the temperature drift; the resulting systematic uncertainty is X ps and is now included in the total.
> 4. **C4:** We added a comparison with the CFD method (Fig. X); the template fit improves the resolution by Y%.
