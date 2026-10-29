# hep-review

Recorded, tiered review of physics work: review obligations, assurance tiers R0-R3, an append-only commit log with
checkpoints, and a two-layer report computed from the records. Protocol hep-review/1, schema 1.0.0 (0.x records are
labelled experimental). Review capability is pilot-checked only for single-page statistical analyses at R2.

## What is in this folder

| Path | Holds |
|---|---|
| `SKILL.md` | the entry point Claude reads first |
| `references/` | 7 reference pages and 3 domain cards loaded on demand: workflow and tiers, evidence and adjudication, host and trust boundaries, storage and continuity, evaluation and claims, support matrix, `domains/` |
| `assets/` | `registry.json` (domain packs, method cards, readers, host adapter), `host_profile.json` (measured host capabilities) and `claims.json` (capability claims, written through the claim lifecycle) |
| `scripts/` | `review.py` (the CLI) and `hep_review_support/` (controlled reading, store, continuity, export, coordinator, evaluation) |

The pure kernel (validation, projection, tiers, closures) is `contracts/hep_review.py`; its schemas are
`contracts/schemas/hep_review_*.json`. Development records (task state, spike, host measurements, reviews) are in
`docs/dev/hep-review/`.

## What it does not do

It certifies nothing as physically or statistically correct; it does not fix the reviewed code; it does not enforce
reviewer isolation on a shared-filesystem host; R3 is not reachable on the measured host.
