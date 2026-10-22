# Decision record: cross-artifact check architecture (DR-1 to DR-15)

Status: **decided 2026-10-22 on the maintainer's instruction in the session** (see each Decision). Written 2026-10-22
for the final architecture `cross-artifact-check-architecture.en.md` (and `.zh.md`, which prevails if they differ),
section 7. Replaces the `decision-hardening.md` that plan v3.1 proposed. Labels: **Confirmed**, **Inferred**,
**Unresolved**.

## Analysis question

Which of the architecture's decision items are adopted, in which wording, so that Phase 0 (release R1) may start and
the later phases know what is decided? Phase 0 needs DR-9, DR-11, DR-12 and DR-13 decided (section 9.1); its item 11
needs DR-15.

## Items

| DR | Adopted content (architecture section 7.2) | Post-review revision | DR-11 split |
| --- | --- | --- | --- |
| DR-1 | Trust is judged by custody; `asserted_by.kind` has no effect on trust | Only files outside the project, referenced by digest, can be protected; judged against a named analyst account; `check-report` re-judges itself | Always flag G8 and A3 in plane A; custody judgement moves to plane B |
| DR-2 | check-context 1.1.0 removes `required`; deferral only through exceptions | A subject under a 1.0.0 suite first meets the version guard | — |
| DR-3 | Observation identity = source identity + pointer; values are never compared | Without an envelope, use the canonical digest; a copy with one added key stays undetected (known limitation) | — |
| DR-4 | Forgery is addressed only by a custodian rerun; `require_recheck` | `recheck_record.json`; a forged `state.json` is not covered | Moves to B |
| DR-5 | Snapshots on by default; old rules reproduced by rerunning their release | Definitions in a snapshot must be released definitions | Default snapshots, version guard and P6 stay in A; released-definitions index, custodian copies and release reruns move to B |
| DR-6 | Tolerance derived from declared significant digits | The undeclared default stays 1e-9; check the values' actual digits; replace k with Σ\|power\| | — |
| DR-7 | Blinding judged by lineage; `simulated` may be permitted | No data leaf → `lineage_no_data`; label only → unverified; dataset and envelope status vocabularies kept apart | The "custodian-approved derivative" row moves to B |
| DR-8 | Add `r-real.undescribed` | No root coverage (→ DR-10); only a non-empty `backgrounds` block describes a background; `no_backgrounds_reason` with an applied background → `description_contradicted`; class matches limited to the members the spec lists | — |
| DR-9 | — | — | Join key between the project's `blinded` list and a spec: the spec's `artifact_id` |
| DR-10 | — | — | Root-coverage subject set: deferred to coverage extension |
| DR-11 | — | — | Two planes: diagnostic plane A now, assurance plane B design only |
| DR-12 | — | — | Bounded spike as in section 12 (3–4 sessions, stop at the cap, no operators from argv) |
| DR-13 | — | — | Value gate as in section 10; thresholds pre-registered in `decision-value-gate.md` before any measurement |
| DR-14 | — | — | Build the entry path only if the value gate passes, as specified in section 11 |
| DR-15 | — | — | Rename the code-name identifiers with the mapping and safety rules of section 8.3, as Phase 0 item 11 |

## Evidence (Confirmed)

- Gaps G1–G22: probes in `tests/contracts/test_cross_artifact_check_gap_probes.py` (rebuilt 2026-10-22 from the gap
  register; the architecture review's original probe file is not in this repository). Phase 0 gaps pass; Phase 2
  gaps are expected failures that each fail for the stated reason (checked with the decorator removed).
- G21: `g21-classification.md`.
- Old releases: every release from 0.3.0 has a `hep-research--v<version>` tag except 0.4.0 (manifest only);
  `git archive hep-research--v0.21.0 plugins/hep-research` extracted into an empty folder verifies as release 0.21.0
  through `core.protected.identity.plugin_release()` (digest `96e14c12…`). The checker exists from 0.12.0.

## Owner

hchouTW (programme owner named in `decision-enforce.md`).

## Decision

**2026-10-22, maintainer instruction in the session.** DR-1 to DR-8 were adopted earlier the same day ("the
maintainer's instruction in the session was to follow the recommendation"). Asked to decide DR-9 to DR-15 and the
post-review revisions, the maintainer replied "answer questions", which the implementer took as an instruction to
adopt its recommendations, the same way. Adopted:

- the post-review revisions of DR-1 to DR-8, as in the table, with the DR-11 split;
- DR-9: the spec's `artifact_id`;
- DR-10: deferred to coverage extension;
- DR-11: adopt the two-plane split;
- DR-12: the spike as in section 12 (optional);
- DR-13: the value gate as in section 10; its numeric thresholds are proposed in `decision-value-gate.md` and need
  the maintainer's confirmation there **before** any measurement (section 9.2);
- DR-14: conditional on the value gate passing; decided again from the cost data of section 10 step 7;
- DR-15: adopt, as Phase 0 item 11.

The maintainer may change any of these with a new dated section; this section is not rewritten.
