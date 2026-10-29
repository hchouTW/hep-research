# Talk outline: Timing performance of a synthetic MRPC time-of-flight prototype (SYNTHETIC)

> All numbers in this file are synthetic test-beam numbers made up for an exercise. They do not describe any real detector.

Slot: 12 min + 3 min questions. Status: **Preliminary**.

---

## Slide 1 — Title

- "Timing performance of an MRPC time-of-flight prototype for barrel and endcap"
- Labels on slide: **PRELIMINARY**, **Synthetic test-beam data**

## Slide 2 — Setup

- Prototype modules: barrel type (4 modules), endcap type (2 modules), 128 channels in total.
- Test beam: π⁻ at 6 GeV/c; start time T0 from beam counters, σ_T0 = 30 ps (included in all resolutions below).
- For the physics projection we assume a flight path L = 1.5 m.

## Slide 3 — Time-walk correction

- Time-over-threshold based correction, parameters fitted per channel.

## Slide 4 — Timing resolution

- Figure 3: Δt distribution after time-walk correction.
- Caption (Fig. 3): "Δt distribution after time-walk correction with Gaussian fit. Barrel: σ_t = 85 ± 4 ps; endcap: σ_t = 100 ± 5 ps. σ_T0 = 30 ps included. Preliminary, synthetic data."
- Body: barrel σ_t = 85 ± 4 ps, endcap σ_t = 100 ± 5 ps.

## Slide 5 — Efficiency and noise

- Efficiency 98.7 ± 0.3% at the operating voltage (all modules).
- Noise rate 0.8 Hz/cm².

## Slide 6 — PID projection

- π/K time difference at p = 2 GeV/c over L = 1.5 m: Δt = 138 ps.
- Separation at 2 GeV/c: barrel 1.6σ, endcap 1.4σ.
- Figure 5 caption: "Projected π/K separation (Δt/σ_t) vs momentum for σ_t = 85 ps (barrel, solid) and 100 ps (endcap, dashed), L = 1.5 m. The barrel curve crosses 3σ at p ≈ 1.5 GeV/c. Synthetic."

## Slide 7 — Limitations

- Pions only in test beam; PID performance is a projection, not measured.
- Single prototype per type; module-to-module spread not yet measured on a production batch.
- No magnetic field; track-length uncertainty not included in the projection.

## Slide 8 — Summary

- Barrel σ_t = 85 ps meets the 90 ps design target; endcap σ_t = 100 ps.
- Efficiency 97.8%, noise 0.8 Hz/cm².
- π/K separation 1.6σ at 2 GeV/c (barrel); 3σ up to ≈1.5 GeV/c.
- Preliminary; synthetic test-beam data.
- Speaker notes: "The barrel is just under the 90 ps target, a margin of only 5 ps — say that the margin is thin."

---

## Backup B1 — Performance table

| Type | σ_t (ps) | Efficiency (%) | Noise (Hz/cm²) |
|---|---|---|---|
| Barrel | 85 ± 4 | 98.7 ± 0.3 | 0.8 |
| Endcap | 100 ± 5 | 98.7 ± 0.3 | 0.8 |

## Backup B2 — Barrel σ_t per run

| Run | σ_t (ps) |
|---|---|
| 101 | 84 |
| 102 | 86 |
| 103 | 85 |
| 104 | 87 |

---

## UPDATE NOTE (synthetic)

A bug in the time-walk correction for the barrel modules was fixed (wrong time-over-threshold binning). After reprocessing, the barrel resolution is **σ_t = 72 ± 3 ps** (was 85 ± 4 ps). The endcap modules used a different code path and are **not affected** (σ_t = 100 ± 5 ps stays). Efficiency, noise, σ_T0 and the projection assumptions are unchanged. Per-run values have not been redone yet.
