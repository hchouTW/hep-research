# Schema-freeze review: dispositions

An independent, fresh-context, non-author reviewer read commits `1dfb15fa` (packet digest wording) and `0bea7326`
(freeze to hep-review/1, schema 1.0.0). The full findings are in the reviewer's file, copied below in summary. The
reviewer reproduced B1, M1, M2 and m4 with the pre- and post-freeze kernels. Every finding was accepted, and each fix
was written test first (`tests/contracts/test_hep_review_freeze.py`, `test_continuity_export.FrozenSchema`,
`test_materials`).

| ID | Finding | Disposition |
|---|---|---|
| B1 | Layer 1 under validator 0.1.0 no longer matched the pre-freeze bytes: the header came from the current constants, and `experimental` became required, so every pre-freeze report would look tampered with | Fixed. A projection under a 0.x validator keeps its historical header (hep-review/0, 0.1.0) and has no `experimental` key. Under the current validator, `experimental` is present and optional in the schema. Golden bytes written by the pre-freeze kernel are in `contracts/fixtures/hep_review/layer1_v0_1_0.json`; they match, `check_historical` returns `match`, the report renders, and the schema passes |
| M1 | A list or dict protocol raised TypeError in `check_object` and `project` | Fixed: a type check comes before the lookup, so the result is an `object.protocol` diagnostic under every validator |
| M2 | Both validator versions shared the changed `check_object`, so the 0.1.0 rules changed meaning | Fixed: `check_object(obj, validator_version)`. Under 0.1.0 the old rule is kept exactly (its own protocol, no schema-version check); `validate` passes its version through |
| m1 | The store still accepted new hep-review/0 writes | Fixed: store admission refuses a hep-review/0 object unless an identical object is already committed in the context (carried by a fork or a migration) |
| m2 | `migrate()` could relabel 0.x records as 1.0.0 and drop the experimental label | Fixed: hep-review/0 objects must be carried byte for byte; a changed one is refused |
| m3 | `decide_summary` ignored `experimental` | Fixed: the disclosure list starts with the experimental note when layer 1 is a 0.x projection or holds 0.x records |
| m4 | Schema versions were checked by prefix only | Fixed: a full-version pattern per line. The missing packet schema and the absence of a JSON-schema check on import are recorded as known gaps. Import verifies the export's digests and chain first, and packets are never committed |
| m5 | Only the bare word `unavailable` was understood, while the packet asks for `SHA256: unavailable` | Fixed: an optional `SHA256:` label is stripped before comparing, so both the hex and `unavailable` work with or without it |
| m6 | Stale status text in the reference, capability map and matrix, README and STATE | Fixed: those files now state pilot-checked-scope with its limits, and the capability map was regenerated |

No finding was rejected.
