# Detector atlas (reference profile)

Sourced facts on large experiments' detectors. Every number is a claim in `evidence/claims.json` with its source,
location, read level and an `atlas` block: experiment, subsystem, quantity, value, unit, `kind` (design, achieved,
operating) and `valid_for` (the configuration). Read it with
`python3 <plugin root>/skills/hep-detector/scripts/detector_atlas.py query ...`; quote the claim id with every number.

## Coverage (v1 and the batch D expansion, 2026-10-17)

| Experiment | Claims | Source |
|---|---|---|
| ATLAS | 11 | detector paper, JINST 3 (2008) S08003 |
| CMS | 9 | detector paper, JINST 3 (2008) S08004 |
| LHCb | 10 | LHCb Upgrade I, arXiv:2305.10515 (original and upgraded configurations) |
| IceCube | 10 | instrumentation paper, arXiv:1612.05093 |
| Super-Kamiokande | 10 | calibration paper, arXiv:1307.0162 (phases SK-I to SK-IV) |
| Fermi-LAT | 10 | instrument paper, arXiv:0902.1089 (pre-flight estimates) |
| Belle II | 12 | technical design report, arXiv:1011.0352 (2010 design values) |
| ALICE | 11 | LS2 upgrades paper, arXiv:2302.01238 (ALICE 1 and ALICE 2 configurations) |
| DUNE | 10 | far detector TDR volume I, arXiv:2002.02967 (2020 design) |
| JUNO | 10 | physics and detector paper, arXiv:2104.02565 (design before data taking) |
| XENONnT | 10 | detector paper, arXiv:2402.10446 (as built; first science run) |
| Pierre Auger Observatory | 10 | observatory paper, arXiv:1502.01323 (as completed in 2008) |

Further experiments are added by demand, with the same rules (open question 11 of the upgrade work order).
AMS-02: use its experiment profile (`experiment:ams-02`); this atlas holds no AMS-02 claim.

## Rules

- A number not in the ledger is `unknown`: never fill it from memory.
- Design, achieved and operating values are different claims; `valid_for` separates configurations (an upgrade, a
  data-taking phase). Quote the configuration with the number.
- Read levels: `full-text` means the cited passage was read in the full text (here: the overview chapter or section
  and each cited passage; the long detector papers were not read cover to cover). See `evidence/index.md`.
- A user atlas (`--user-atlas`) is user-supplied; packaged as a local profile its custody is `unknown`
  (`contracts/custody.py`).

Conventions: [conventions.json](conventions.json). Evidence: [evidence index](evidence/index.md).
