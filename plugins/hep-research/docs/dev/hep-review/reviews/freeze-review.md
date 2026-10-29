# Independent review: 1dfb15fa (SHA-256 'unavailable') and 0bea7326 (freeze hep-review/1, schema 1.0.0)

Worktree: the hep-review-v9 worktree (plugin root plugins/hep-research).
Tests run: 12 hep-review modules (contracts + skills), 224 tests, all pass. Empirical checks in
a reproduction script in the session scratch folder (rv/check.py, not kept), run
against the pre-freeze kernel (`git show 0bea7326^:.../contracts/hep_review.py`) and the post-freeze kernel.

Counts: blocker 1, major 2, minor 6.

---

## B1 (blocker): layer 1 under validator 0.1.0 is no longer byte-reproducible; historical reports now fail check_historical / render_report

- File: contracts/hep_review.py:1105-1110 (project() base header); also :352-355 (VALIDATOR_RULES keeps "0.1.0").
- Defect: the layer-1 header is built from the module constants `PROTOCOL`/`SCHEMA_VERSION` plus the new
  `experimental` key, not from `validator_version`. So `project(validate(b, "0.1.0"), "0.1.0")` gives different bytes
  for the same bundle and the same validator version before and after this commit (protocol hep-review/0 -> /1,
  schema_version 0.1.0 -> 1.0.0, new key `experimental`). Layer 1 is required to be a pure, byte-reproducible function
  of (bundle, validator version), and the commit message claims 0.x data "stays readable under its own validator
  version".
- Failure scenario (reproduced): build a 0.x context, compute layer 1 with the pre-freeze kernel under "0.1.0"
  (what every report issued before today contained, and what its printed "layer 1 digest" covers). With the new
  kernel, `H.check_historical(old_l1, bundle, "0.1.0")` returns `"mismatch"`, and
  `H.render_report(old_l1, ..., validator_version="0.1.0")` raises `RenderError: layer 1 does not match the projection
  of the bundle`. A user who verifies a pre-freeze g2/g2h/g2x report gets a false tamper signal. The pre-freeze layer 1
  also now fails hep_review_report.json, because `experimental` is required (contracts/schemas/hep_review_report.json:8).
  New layer 1 objects produced "under 0.1.0" are mislabelled: `protocol: hep-review/1, schema_version: 1.0.0,
  validator_version: 0.1.0`.
- Why the tests miss it: test_hep_review_freeze.py `test_0x_bundle_projects_under_its_own_validator_version` only
  checks `experimental` and `validator_version` on the new output. It never compares against bytes produced by the
  0.1.0 code. The "48 g2x exports still project ... with their tiers" claim compares tiers, not bytes.
- Fix: make the header a function of the validator version, e.g. a table
  `LAYER1_HEADER = {"0.1.0": ("hep-review/0", "0.1.0", False), "1.0.0": ("hep-review/1", "1.0.0", True)}`, where the
  third element says whether the `experimental` key is emitted. Under 0.1.0, emit exactly the pre-freeze object (no
  `experimental` key). Under 1.0.0, emit the new one. In the report schema, require `experimental` only when
  `protocol` is hep-review/1 (an if/then, or a separate $defs per line), or drop it from `required`. Add a golden test
  that stores a pre-freeze layer-1 byte string (or its digest) for a fixed 0.x bundle and asserts
  `check_historical(..., "0.1.0") == "match"`. Alternatively, drop "0.1.0" from VALIDATOR_RULES and document that
  historical checks need the 0.1.0 repository tag (the comment at :350-351 already says so). Today the table offers a
  "0.1.0" that does not reproduce 0.1.0.

## M1 (major): check_object raises TypeError on a non-string protocol (regression); validate/project and store admission crash instead of reporting a diagnostic

- File: contracts/hep_review.py:307-313 (`protocol not in SCHEMA_MAJOR`, a dict lookup) and :1109
  (`o.get("protocol") in EXPERIMENTAL_PROTOCOLS`, a frozenset).
- Defect: the old test `committed.get("protocol") not in (None, PROTOCOL)` was a tuple-equality test and handled any
  type. Membership in a dict or frozenset hashes the value, so a list- or dict-valued `protocol` raises
  `TypeError: unhashable type`.
- Failure scenario (reproduced): an object with `"protocol": ["hep-review/1"]` gave
  `['object.header', 'object.protocol']` before the change. Now `H.check_object` raises TypeError. `H.validate` on a
  bundle holding such an object raises TypeError, not a diagnostic or BundleError, and so does `project` through its
  `experimental` scan. In the store, `_admit` (skills/hep-review/scripts/hep_review_support/store.py:288) calls
  check_object before schema validation, so a malformed intent or plan file, or an imported export, ends in an
  uncaught TypeError. review.py:221-230 catches neither TypeError nor this case, so the user gets a traceback, not
  the exit-2 refusal.
- Fix: guard with `isinstance(protocol, str)`, e.g.
  `if protocol is not None and (not isinstance(protocol, str) or protocol not in SCHEMA_MAJOR): ...`, and in project()
  use `isinstance(o.get("protocol"), str) and o["protocol"] in EXPERIMENTAL_PROTOCOLS`. Add a test with list, dict and
  int protocols through check_object, validate and store admission.

## M2 (major): validator "0.1.0" rules changed meaning (version-independent check_object)

- File: contracts/hep_review.py:296-313 together with :353-355.
- Defect: both "1.0.0" and "0.1.0" map to the same `rule_check_object`/`check_object`, and check_object itself
  changed. Under validator "0.1.0", a hep-review/1 object is now admitted (it used to give `object.protocol`), and a
  hep-review/0 object whose schema_version is 1.x is now refused (it used to be admitted). Diagnostics, and so
  `record_integrity` and the summary eligibility in validate()/project() under "0.1.0", can differ from what 0.1.0
  produced. This is the same reproducibility contract as B1, at the diagnostic level.
- Failure scenario (reproduced): `F.header("intent","i")` (hep-review/1, 1.0.0): old 0.1.0 check gives
  `['object.protocol']`, new check gives `[]`. A historical re-check of a bundle under "0.1.0" no longer applies the
  0.1.0 rule set.
- Fix: make the protocol and schema admission depend on the validator version. For example, give "0.1.0" a
  `rule_protocol_0x` (only hep-review/0, and no schema check, as before) and "1.0.0" the new two-line rule. Or, as in
  B1, remove "0.1.0" from the in-tree table and rely on the tag.

## m1 (minor): fresh hep-review/0 writes are still admitted after the freeze

- File: contracts/hep_review.py:307-313; contracts/schemas/hep_review_definitions.json:11-12; store.py:279-300.
- Defect: admission (check_object plus the header schema) accepts new hep-review/0 / 0.x objects. "Freeze" is not
  enforced for new writes. A stale producer, such as a pilot driver from an older checkout or an agent copying a
  0.x example, can keep writing 0.x records into new or 1.x contexts. Each such context then flips to
  `experimental: true`.
- Fix: in `Store._admit` (the I/O layer, so the kernel can still read 0.x), refuse new objects whose protocol is in
  EXPERIMENTAL_PROTOCOLS unless they arrive through fork, migrate or import of historical data.

## m2 (minor): migrate() can strip the experimental label from 0.x review content

- File: skills/hep-review/scripts/hep_review_support/continuity.py:186-206 (docstring still says "An incompatible 0.x
  schema change"); coordinator.py:250-252.
- Defect: `experimental` is computed only from the objects in the head segment's bundle. A migration whose transform
  rewrites the headers to hep-review/1 / 1.0.0 (the natural 0.x -> 1.0 upgrade path) produces a segment with
  `experimental: false`, although its records were written and reviewed under 0.x. The report discloses
  "schema migration" but not "experimental". The spec requires all 0.x data to be labelled experimental.
- Fix: carry the label through the migration. Either set it when the genesis has `migrated_from` a segment that held
  0.x objects (through a field on the committed genesis, so layer 1 stays a function of the bundle), or forbid
  migrate from rewriting `protocol` on carried records. Update the docstring.

## m3 (minor): decide_summary ignores `experimental`, so the no-defect summary and its disclosure list are unlabelled

- File: contracts/hep_review.py:1385-1425; coordinator.py:240-271.
- Defect: only render_report prints the experimental line. `decide_summary` returns `output_summary: True` and a
  `summary_text` with no qualifier or disclosure for 0.x data, and `attestation.output_summary`/`summary_text` and
  `disclosure` in the CLI JSON carry no label. A consumer that reads the summary field and not the text, such as a
  pilot driver (`run_pilot.py:197` copies `output_summary`), presents 0.x results without the label.
- Fix: in decide_summary, `if layer1.get("experimental"): disclosure.append("experimental: 0.x records ...")`. Test it
  with a 0.x bundle that is otherwise summary-eligible.

## m4 (minor): schema_version admission is a bare prefix test

- File: contracts/hep_review.py:310-311.
- Defect: `startswith("1.")` admits "1.0", "1.anything" and future "1.9.0" (reproduced: no diagnostic). The JSON-schema
  pattern only runs in store admission and only for kinds that have a schema file. There is no
  `hep_review_packet.json`, and validate() (the export/import path) runs no schema. So a malformed schema_version is
  admitted in those paths.
- Fix: check with a full regex, e.g. `^1\.0\.\d+$` for hep-review/1 (the frozen version), or
  `^1\.\d+\.\d+$` if forward-compatible minors are intended, and `^0\.\d+\.\d+$` for hep-review/0.

## m5 (minor): the 'unavailable' normalization breaks when the reported line is passed "exactly as reported"

- File: skills/hep-review/scripts/hep_review_support/materials.py:201-208;
  skills/hep-review/references/host-and-trust-boundaries.md:42-44; coordinator.py:51-53.
- Defect: the packet asks the reviewer to reply `SHA256: unavailable`, and the new reference text says "Pass on the
  reviewer's reported digest exactly as reported". A coordinator that passes the whole token, as in
  `review.py ingest --digest "SHA256: unavailable"`, gets `"sha256: unavailable"`, which is neither "" nor
  "unavailable", so the result is `mismatch` and the record is quarantined. That is the exact g2x failure the commit
  meant to fix. The same holds for `SHA256: <hex>` (the prefix was already a problem before). Otherwise the change
  cannot be abused: whitespace-only and mixed case collapse to "no declaration" as intended, a hex value is still
  compared after strip/lower, and a reviewer could already avoid binding by sending nothing. "Empty" moving from
  mismatch to file-transfer is the only other change in fidelity semantics, and it is consistent with the stated
  intent.
- Fix: strip an optional leading `sha256:` (case-insensitive) before comparing, or change the reference to say "pass
  the value after `SHA256:`". Add a test for `"SHA256: unavailable"` and `"SHA256: <hex>"`.

## m6 (minor): stale "experimental / hep-review/0 / no pilot scored" status left in docs the skill or agents read

- Files:
  - skills/hep-review/references/evaluation-and-claims.md:31-32 ("Today hep-review is **experimental**: no pilot has
    been scored"). This contradicts SKILL.md:12 and is loaded by the skill.
  - docs/capability-map.md:86 ("experimental, protocol hep-review/0; G1 record prototype").
  - docs/capability-matrix.md:226 ("no review-capability pilot scored ... G1 record prototype only").
  - README.md:28 ("(experimental)").
  - docs/dev/hep-review/STATE.md:66 (next_action still "freeze hep-review/1 ... as a separate reviewed step").
- Failure scenario: an agent that follows evaluation-and-claims.md reports the capability state as "experimental",
  while SKILL.md says "pilot-checked" for a narrow scope. The claim statements are inconsistent.
- Fix: update these to the frozen status and the pilot-checked scope (state `pilot-checked-scope` in the
  evaluation-and-claims vocabulary), and advance STATE.md.

---

Checked with no defect found:
- The `experimental` key is present on every layer-1 path: it is set in `base`, so the input_error return and the R0
  path (coordinator.r0_report, mode R0) both carry it. The report schema's types match.
- render_report prints the line before the input-error early return.
- export/import/verify and continuity never compare protocol strings. The commit header `protocol`
  (store.py:410, coordinator.py:279) is written but never checked, so mixing /0 and /1 commit headers in one store is
  harmless.
- Mixed protocol and schema_version in one object is refused in both directions (tested).
- The 1dfb15fa packet text and test match.
