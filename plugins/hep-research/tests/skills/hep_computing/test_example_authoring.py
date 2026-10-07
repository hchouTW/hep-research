"""Behavioral tests for the example-authoring helper scripts.

Purpose: cover `generate_skill_example.py` (scaffold), `validate_skill_example.py`
(structural + placeholder checks), and `check_example_diversity.py` across all
eight archetypes (contrast, trajectory, gated-pipeline, decision-tree,
elicitation, adversarial-audit, test-first, postmortem) - the tooling behind
references/example-authoring.md.

Usage: run from the skill directory with
`python3 -m unittest discover -s tests -v`. Standard library only; no external
services or dependencies are needed.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3] / "skills" / "hep-computing"
sys.path.insert(0, str(ROOT / "scripts"))

import check_example_diversity  # noqa: E402
import generate_skill_example  # noqa: E402
import validate_skill_example  # noqa: E402


GOOD_CONTRAST = """---
role: Staff Software Engineer
skill: agile-development
archetype: contrast
use_case: scoping a discount-code bug fix
---

## Scenario

A customer reports the cart total is wrong when a discount code is applied
alongside a shipping promotion. The team must scope and fix the bug.

## Common Weak Approach

```python
def apply_discount(total, code):
    return total * 0.9
```

This ignores stacking rules entirely.

## Expert-Level Best Practice

```python
def apply_discount(total, code, promotions):
    for promo in promotions:
        total = promo.apply(total)
    return total
```

This composes promotions explicitly and is covered by a regression test.

## Key Takeaways

- Reproduce the bug with a failing test before writing a fix.
- Model discount stacking as an explicit, ordered list rather than a single multiplier.
- Add a regression test that encodes the specific reported combination.
"""

LEGACY_CONTRAST_NO_ARCHETYPE_FIELD = """---
role: Staff Software Engineer
skill: agile-development
use_case: scoping a discount-code bug fix
---

## Scenario

A customer reports the cart total is wrong. The team must scope and fix it.

## Common Weak Approach

Patches the one reported case with no test.

## Expert-Level Best Practice

Writes a failing test first, then fixes the underlying stacking contract.

## Key Takeaways

- Reproduce the bug with a failing test before writing a fix.
- Model discount stacking as an explicit, ordered list rather than a single multiplier.
- Add a regression test that encodes the specific reported combination.
"""

GOOD_TRAJECTORY = """---
role: Senior Software Engineer
skill: agile-development
archetype: trajectory
problem_input: a bug report that the cart total is wrong with a discount code
---

## 1. Task Input & Context

A customer reports the cart total is wrong when a 10% code and a $5 flat code
are both applied. This is the fourth report against the same code path.

## 2. Root-Cause Triage & Action Plan

Reproducing the report shows the flat discount is applied before the
percentage discount, halving its effect. Plan: reorder to percentage-then-flat
and add a regression test for this exact combination.

## 3. Surgical Execution

```diff
-    total = apply_flat(total, flat_code)
-    total = apply_percent(total, percent_code)
+    total = apply_percent(total, percent_code)
+    total = apply_flat(total, flat_code)
```

## 4. Verification Evidence

```
$ python3 -m pytest tests/test_discounts.py -k stacking
1 passed in 0.04s
```

## 5. Final Deliverable Summary

Reordered discount application and added a regression test covering the
percent-then-flat stacking case; the reported total now matches expectations.
"""

GOOD_GATED_PIPELINE = """---
role: Principal Software Engineer
skill: agile-development
archetype: gated-pipeline
high_stakes_task: drafting an RFC for a feature-flagged checkout rollout
---

## Phase 1: Input Extraction & Gap Formulation

Extracted the rollout requirements from the checkout team and identified that
the rollback trigger and metric thresholds were not yet defined.

**Gate:** proceed only once rollback trigger and success metrics are named.

## Phase 2: Draft Synthesis

Drafted the RFC aligning to `references/design-and-estimation.md`'s
feature-flag rollout checklist, naming the specific staged-rollout percentages
and the metric dashboard used to gate each stage.

**Gate:** proceed only once the draft cites that checklist section by name.

## Phase 3: Red-Team Review & Final Artifact Packaging

Stress-tested the assumption that the flag system fails closed; a review
found it actually fails open under a config-fetch timeout, so the RFC was
revised to require a fail-closed default before rollout.

**Gate:** merge only once the fail-closed default is implemented and tested.
"""

GOOD_DECISION_TREE = """---
role: Engineering Lead
skill: agile-development
archetype: decision-tree
scenario: triaging an incident page for a checkout outage with unclear cause
---

## Triage Matrix

| Trigger | Resolution Strategy |
|---|---|
| Error rate spike immediately after a deploy | Roll back the deploy first |
| Error rate spike with no recent deploy | Check upstream dependency status pages |
| Elevated latency only, no errors | Check database connection pool saturation |
| Page with no corresponding dashboard signal | Treat as a possible false alarm; page secondary on-call to confirm |

## Selected Branch

The page fired one minute after a deploy completed, so the first row applies:
roll back the deploy first.

## End-to-End Execution Script

Run `deploy rollback checkout-service --to-previous`, confirm the error rate
returns to baseline within two minutes, then post in #incidents: "Rolled back
checkout-service to the prior release; error rate recovering, investigating
root cause of the regression before re-attempting the deploy."

## Fallback Safeguards

If the rollback does not restore baseline error rates within five minutes,
escalate to the database on-call in parallel and assume a coincident second
cause rather than continuing to wait on the rollback alone.
"""


GOOD_ELICITATION = """---
role: Staff Software Engineer
skill: agile-development
archetype: elicitation
user_request: can you make the checkout faster?
---

## 1. Raw Ambiguous Input

"Can you make the checkout faster?" - no target latency, no named step, no
traffic profile given.

## 2. Missing Constraint Analysis

No baseline latency, no target threshold, no identification of which step
(cart, payment, confirmation) is slow, and no traffic profile (peak vs.
average) was named.

## 3. Socratic Clarification Round

1. Which checkout step is slow?
   a) Cart summary load
   b) Payment authorization
   c) Order confirmation
   d) The whole flow end-to-end
2. What is the current p95 latency, and what is the target?
   a) Unknown baseline, target under 2s
   b) ~4s baseline, target under 1s
   c) ~6s baseline, target under 3s
3. Is this under normal load or peak traffic?
   a) Normal traffic only
   b) Peak traffic (e.g. flash sale)
   c) Both

## 4. User Feedback Integration

The user answered: payment authorization (b), current p95 is ~4s with a
target under 1s (a partial match with option b), and this happens under peak
traffic (b).

## 5. Final Mutually-Agreed Specification Document

Reduce payment-authorization p95 latency from ~4s to under 1s under peak
traffic, without regressing cart or confirmation step latency.
"""

GOOD_ADVERSARIAL_AUDIT = """---
role: Staff Machine Learning Engineer
skill: deep-learning
archetype: adversarial-audit
candidate_artifact: a training writeup claiming 95% accuracy, SOTA
---

## 1. Initial Candidate Artifact

The writeup reports 95% test accuracy on a binary classifier, trained with a
single fixed random seed and a train/test split performed after feature
normalization was fit on the full dataset.

## 2. Attack Vectors & Stress-Tests

Attack Vector 1: Normalization was fit on the full dataset (train + test)
before splitting, leaking test-set statistics into the training features.

Attack Vector 2: Only one random seed was reported; no variance across seeds
or folds is shown, so the 95% figure could be a favorable outlier.

## 3. Concrete Counter-Example / Exploit Proof

```python
mean, std = full_dataset.mean(), full_dataset.std()  # leak: fit before split
X = (full_dataset - mean) / std
X_train, X_test = split(X)  # test statistics already baked into X_train
```
Re-running with normalization fit only on `X_train` drops accuracy to 81%.

## 4. Hardened Architectural Patch

```diff
-mean, std = full_dataset.mean(), full_dataset.std()
-X = (full_dataset - mean) / std
-X_train, X_test = split(X)
+X_train_raw, X_test_raw = split(full_dataset)
+mean, std = X_train_raw.mean(), X_train_raw.std()
+X_train = (X_train_raw - mean) / std
+X_test = (X_test_raw - mean) / std
```

## 5. Proof of Robustness Post-Fix

Re-running the corrected pipeline across 5 seeds gives 81.4% +/- 1.1%
accuracy, with no leakage path from test to train statistics.
"""

GOOD_TEST_FIRST = """---
role: Staff Machine Learning Engineer
skill: deep-learning
archetype: test-first
target: DataLoader must sustain >= 500 samples/sec without starving the GPU
---

## 1. Acceptance Invariants & Boundary Constraints

Throughput must be >= 500 samples/sec sustained over 1000 batches, and GPU
utilization must stay >= 90% during that window.

## 2. Executable Failing Test (Red)

```python
def test_dataloader_sustains_throughput():
    throughput, gpu_util = measure_loader(loader, batches=1000)
    assert throughput >= 500, f"{throughput} samples/sec"
    assert gpu_util >= 0.90, f"{gpu_util} util"
```
```
$ python3 -m pytest tests/test_loader_throughput.py
FAILED tests/test_loader_throughput.py::test_dataloader_sustains_throughput
AssertionError: 212 samples/sec
```

## 3. Minimal Code Implementation

```python
loader = DataLoader(dataset, batch_size=256, num_workers=8,
                     pin_memory=True, persistent_workers=True,
                     prefetch_factor=4)
```

## 4. Verified Passing Execution (Green)

```
$ python3 -m pytest tests/test_loader_throughput.py
1 passed in 12.3s
throughput=612 samples/sec, gpu_util=93%
```

## 5. Regression Guard Summary

This test now guards against a regression to single-worker, non-pinned
loading, which previously silently starved the GPU to 40% utilization.
"""

GOOD_POSTMORTEM = """---
role: Site Reliability Engineer
skill: agile-development
archetype: postmortem
incident: production API outage (500s spike) after a bad deploy
---

## 1. Incident Symptom & Alert Payload

```
ALERT: api-5xx-rate > 5% for 5m
service=checkout-api region=us-east-1 rate=18.4% started=2026-03-01T14:02:00Z
```

## 2. Immediate Triage & Blast-Radius Mitigation

Rolled back `checkout-api` to the prior release with `deploy rollback
checkout-api --to-previous`; error rate returned to baseline within 90
seconds.

## 3. 5-Whys Root Cause Deep-Dive

1. Why did the 5xx rate spike? Because the new deploy crashed on startup
   for a subset of pods.
2. Why did it crash on startup? Because it read a config key that did not
   exist in the production config map.
3. Why did it read a missing key? Because a new required field was added to
   the config schema without a default value.
4. Why was there no default value? Because the schema-validation step in CI
   does not check for backward-compatible defaults on new required fields.
5. Why does CI not check that? Because the config-schema linter was scoped
   to type checks only when it was introduced, and was never extended to
   cover default-value compatibility.

## 4. Permanent Surgical Fix (Diff)

```diff
-  new_field: str
+  new_field: str = "legacy-default"
```

## 5. Blameless Postmortem & Preventative Monitoring Rules

No individual is at fault; the config-schema linter had a coverage gap.
Added a monitoring rule: alert and automatically rollback if `api-5xx-rate`
exceeds 2% for 2 consecutive minutes within 10 minutes of a deploy.
"""


def _scaffold_args(**overrides) -> argparse.Namespace:
    defaults = dict(
        archetype="contrast",
        skill="agile-development",
        role="Staff Software Engineer",
        use_case="scoping a bug fix",
        problem_input=None,
        high_stakes_task=None,
        scenario=None,
        user_request=None,
        candidate_artifact=None,
        target=None,
        incident=None,
        takeaways=4,
        output=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class GenerateSkillExampleTests(unittest.TestCase):
    def test_contrast_skeleton_has_frontmatter_and_all_sections_in_order(self):
        skeleton = generate_skill_example.build_skeleton(_scaffold_args())
        self.assertIn("role: Staff Software Engineer", skeleton)
        self.assertIn("skill: agile-development", skeleton)
        self.assertIn("archetype: contrast", skeleton)
        self.assertIn("use_case: scoping a bug fix", skeleton)
        sections = ["## Scenario", "## Common Weak Approach",
                    "## Expert-Level Best Practice", "## Key Takeaways"]
        positions = [skeleton.index(s) for s in sections]
        self.assertEqual(positions, sorted(positions))

    def test_takeaway_count_matches_requested_number(self):
        skeleton = generate_skill_example.build_skeleton(_scaffold_args(takeaways=6))
        self.assertEqual(skeleton.count("<!-- Takeaway"), 6)

    def test_trajectory_skeleton_has_five_sections_in_order(self):
        args = _scaffold_args(archetype="trajectory", use_case=None, problem_input="a raw bug report", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertIn("archetype: trajectory", skeleton)
        self.assertIn("problem_input: a raw bug report", skeleton)
        sections = [
            "## 1. Task Input & Context",
            "## 2. Root-Cause Triage & Action Plan",
            "## 3. Surgical Execution",
            "## 4. Verification Evidence",
            "## 5. Final Deliverable Summary",
        ]
        positions = [skeleton.index(s) for s in sections]
        self.assertEqual(positions, sorted(positions))

    def test_gated_pipeline_skeleton_has_three_phases_with_gate_placeholders(self):
        args = _scaffold_args(archetype="gated-pipeline", use_case=None, high_stakes_task="a rollout RFC", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertIn("archetype: gated-pipeline", skeleton)
        sections = [
            "## Phase 1: Input Extraction & Gap Formulation",
            "## Phase 2: Draft Synthesis",
            "## Phase 3: Red-Team Review & Final Artifact Packaging",
        ]
        positions = [skeleton.index(s) for s in sections]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(skeleton.count("**Gate:**"), 3)

    def test_decision_tree_skeleton_has_matrix_and_fixed_sections(self):
        args = _scaffold_args(archetype="decision-tree", use_case=None, scenario="an ambiguous incident page", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertIn("archetype: decision-tree", skeleton)
        sections = [
            "## Triage Matrix",
            "## Selected Branch",
            "## End-to-End Execution Script",
            "## Fallback Safeguards",
        ]
        positions = [skeleton.index(s) for s in sections]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("| Trigger | Resolution Strategy |", skeleton)

    def test_elicitation_skeleton_has_five_sections_in_order(self):
        args = _scaffold_args(archetype="elicitation", use_case=None, user_request="make it faster", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertIn("archetype: elicitation", skeleton)
        self.assertIn("user_request: make it faster", skeleton)
        sections = [
            "## 1. Raw Ambiguous Input",
            "## 2. Missing Constraint Analysis",
            "## 3. Socratic Clarification Round",
            "## 4. User Feedback Integration",
            "## 5. Final Mutually-Agreed Specification Document",
        ]
        positions = [skeleton.index(s) for s in sections]
        self.assertEqual(positions, sorted(positions))

    def test_adversarial_audit_skeleton_has_five_sections_in_order(self):
        args = _scaffold_args(
            archetype="adversarial-audit", use_case=None, candidate_artifact="a training writeup", takeaways=None
        )
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertIn("archetype: adversarial-audit", skeleton)
        sections = [
            "## 1. Initial Candidate Artifact",
            "## 2. Attack Vectors & Stress-Tests",
            "## 3. Concrete Counter-Example / Exploit Proof",
            "## 4. Hardened Architectural Patch",
            "## 5. Proof of Robustness Post-Fix",
        ]
        positions = [skeleton.index(s) for s in sections]
        self.assertEqual(positions, sorted(positions))

    def test_test_first_skeleton_has_five_sections_in_order(self):
        args = _scaffold_args(archetype="test-first", use_case=None, target="a throughput invariant", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertIn("archetype: test-first", skeleton)
        sections = [
            "## 1. Acceptance Invariants & Boundary Constraints",
            "## 2. Executable Failing Test (Red)",
            "## 3. Minimal Code Implementation",
            "## 4. Verified Passing Execution (Green)",
            "## 5. Regression Guard Summary",
        ]
        positions = [skeleton.index(s) for s in sections]
        self.assertEqual(positions, sorted(positions))

    def test_postmortem_skeleton_has_five_sections_in_order(self):
        args = _scaffold_args(archetype="postmortem", use_case=None, incident="an outage", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertIn("archetype: postmortem", skeleton)
        sections = [
            "## 1. Incident Symptom & Alert Payload",
            "## 2. Immediate Triage & Blast-Radius Mitigation",
            "## 3. 5-Whys Root Cause Deep-Dive",
            "## 4. Permanent Surgical Fix (Diff)",
            "## 5. Blameless Postmortem & Preventative Monitoring Rules",
        ]
        positions = [skeleton.index(s) for s in sections]
        self.assertEqual(positions, sorted(positions))

    def test_cli_rejects_takeaways_out_of_range(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_skill_example.py"),
             "--archetype", "contrast", "--skill", "agile-development", "--role", "X",
             "--use-case", "Y", "--takeaways", "10"],
            capture_output=True, text=True, timeout=600
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--takeaways must be between", result.stderr)

    def test_cli_rejects_takeaways_for_non_contrast_archetype(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_skill_example.py"),
             "--archetype", "trajectory", "--skill", "agile-development", "--role", "X",
             "--problem-input", "Y", "--takeaways", "4"],
            capture_output=True, text=True, timeout=600
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--takeaways is only valid with --archetype contrast", result.stderr)

    def test_cli_missing_required_flag_fails_with_usage(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_skill_example.py"), "--skill", "x"],
            capture_output=True, text=True, timeout=600
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage:", result.stderr)

    def test_cli_missing_scenario_flag_for_archetype_fails(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_skill_example.py"),
             "--archetype", "decision-tree", "--skill", "agile-development", "--role", "X"],
            capture_output=True, text=True, timeout=600
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--archetype decision-tree requires --scenario", result.stderr)

    def test_cli_rejects_wrong_scenario_flag_for_archetype(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/generate_skill_example.py"),
             "--archetype", "contrast", "--skill", "agile-development", "--role", "X",
             "--use-case", "Y", "--scenario", "Z"],
            capture_output=True, text=True, timeout=600
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--scenario is only valid with --archetype decision-tree", result.stderr)

    def test_cli_writes_to_output_path(self):
        out_path = TESTS_DIR / "_scratch_scaffold.md"
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/generate_skill_example.py"),
                 "--archetype", "contrast", "--skill", "agile-development", "--role", "X",
                 "--use-case", "Y", "--output", str(out_path)],
                capture_output=True, text=True, timeout=600
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out_path.exists())
            self.assertIn("## Scenario", out_path.read_text(encoding="utf-8"))
        finally:
            out_path.unlink(missing_ok=True)


class ValidateContrastTests(unittest.TestCase):
    def test_valid_example_passes(self):
        self.assertEqual(validate_skill_example.validate(GOOD_CONTRAST), [])

    def test_legacy_example_without_archetype_field_defaults_to_contrast(self):
        self.assertEqual(validate_skill_example.validate(LEGACY_CONTRAST_NO_ARCHETYPE_FIELD), [])

    def test_missing_frontmatter_field_is_reported(self):
        broken = GOOD_CONTRAST.replace("skill: agile-development\n", "")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("skill" in p for p in problems))

    def test_missing_frontmatter_block_is_reported(self):
        no_frontmatter = GOOD_CONTRAST.split("---\n", 2)[-1]
        problems = validate_skill_example.validate(no_frontmatter)
        self.assertTrue(any("missing frontmatter" in p for p in problems))

    def test_unknown_archetype_value_is_reported(self):
        broken = GOOD_CONTRAST.replace("archetype: contrast", "archetype: bogus")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("unknown archetype" in p for p in problems))

    def test_missing_section_is_reported(self):
        broken = GOOD_CONTRAST.replace("## Key Takeaways", "## Something Else")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Key Takeaways" in p for p in problems))

    def test_out_of_order_sections_are_reported(self):
        scenario = "## Scenario\n\nSome scenario text.\n\n"
        weak = "## Common Weak Approach\n\nweak\n\n"
        expert = "## Expert-Level Best Practice\n\nexpert\n\n"
        takeaways = "## Key Takeaways\n\n- a\n- b\n- c\n"
        frontmatter = "---\nrole: X\nskill: agile-development\narchetype: contrast\nuse_case: Y\n---\n\n"
        reordered = frontmatter + weak + scenario + expert + takeaways
        problems = validate_skill_example.validate(reordered)
        self.assertTrue(any("out of order" in p for p in problems))

    def test_too_few_takeaways_is_reported(self):
        broken = GOOD_CONTRAST.replace(
            "- Add a regression test that encodes the specific reported combination.\n", "")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Key Takeaways has 2 bullet item(s)" in p for p in problems))

    def test_too_many_takeaways_is_reported(self):
        extra = GOOD_CONTRAST + "- A seventh takeaway.\n- An eighth takeaway.\n- A ninth takeaway.\n- A tenth.\n"
        problems = validate_skill_example.validate(extra)
        self.assertTrue(any("bullet item(s), expected 3-6" in p for p in problems))

    def test_todo_marker_is_flagged(self):
        broken = GOOD_CONTRAST.replace("This ignores stacking rules entirely.", "TODO: explain this")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("placeholder marker" in p for p in problems))

    def test_lorem_ipsum_is_flagged(self):
        broken = GOOD_CONTRAST.replace("This ignores stacking rules entirely.", "Lorem ipsum dolor sit amet.")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Lorem ipsum" in p for p in problems))

    def test_bracketed_stand_in_is_flagged(self):
        broken = GOOD_CONTRAST.replace("This ignores stacking rules entirely.", "[Your explanation here]")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("bracketed stand-in" in p for p in problems))

    def test_leftover_scaffold_comment_is_flagged(self):
        broken = GOOD_CONTRAST + "\n<!-- fill this in -->\n"
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("leftover scaffold comment" in p for p in problems))

    def test_standalone_ellipsis_line_is_flagged(self):
        broken = GOOD_CONTRAST.replace(
            "This composes promotions explicitly and is covered by a regression test.",
            "This composes promotions explicitly.\n\n...\n")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("standalone '...' line" in p for p in problems))

    def test_generated_scaffold_fails_validation_until_filled_in(self):
        skeleton = generate_skill_example.build_skeleton(_scaffold_args())
        self.assertNotEqual(validate_skill_example.validate(skeleton), [])

    def test_cli_ok_on_valid_file(self):
        path = TESTS_DIR / "_scratch_valid.md"
        path.write_text(GOOD_CONTRAST, encoding="utf-8")
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/validate_skill_example.py"), str(path)],
                capture_output=True, text=True, timeout=600
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn(": ok", result.stdout)
        finally:
            path.unlink(missing_ok=True)

    def test_cli_missing_file_fails_cleanly_not_with_traceback(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_skill_example.py"),
             str(TESTS_DIR / "does-not-exist.md")],
            capture_output=True, text=True, timeout=600
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("file not found", result.stdout)
        self.assertNotIn("Traceback", result.stderr)


class ValidateTrajectoryTests(unittest.TestCase):
    def test_valid_example_passes(self):
        self.assertEqual(validate_skill_example.validate(GOOD_TRAJECTORY), [])

    def test_missing_section_is_reported(self):
        broken = GOOD_TRAJECTORY.replace("## 5. Final Deliverable Summary", "## Something Else")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("5. Final Deliverable Summary" in p for p in problems))

    def test_missing_code_fence_in_execution_section_is_reported(self):
        broken = GOOD_TRAJECTORY.replace(
            "```diff\n-    total = apply_flat(total, flat_code)\n"
            "-    total = apply_percent(total, percent_code)\n"
            "+    total = apply_percent(total, percent_code)\n"
            "+    total = apply_flat(total, flat_code)\n```",
            "Reordered the two calls.",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("3. Surgical Execution" in p and "fenced code block" in p for p in problems))

    def test_missing_code_fence_in_verification_section_is_reported(self):
        broken = GOOD_TRAJECTORY.replace(
            "```\n$ python3 -m pytest tests/test_discounts.py -k stacking\n1 passed in 0.04s\n```",
            "The test suite passed.",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("4. Verification Evidence" in p and "fenced code block" in p for p in problems))

    def test_generated_scaffold_fails_validation_until_filled_in(self):
        args = _scaffold_args(archetype="trajectory", use_case=None, problem_input="a raw bug report", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertNotEqual(validate_skill_example.validate(skeleton), [])


class ValidateGatedPipelineTests(unittest.TestCase):
    def test_valid_example_passes(self):
        self.assertEqual(validate_skill_example.validate(GOOD_GATED_PIPELINE), [])

    def test_missing_gate_line_is_reported(self):
        broken = GOOD_GATED_PIPELINE.replace(
            "**Gate:** proceed only once rollback trigger and success metrics are named.\n", "")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Phase 1" in p and "Gate" in p for p in problems))

    def test_phase_three_without_assumption_language_is_reported(self):
        broken = GOOD_GATED_PIPELINE.replace(
            "Stress-tested the assumption that the flag system fails closed; a review\n"
            "found it actually fails open under a config-fetch timeout, so the RFC was\n"
            "revised to require a fail-closed default before rollout.",
            "Reviewed the draft once more and polished the wording.",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Phase 3" in p and "assumption" in p for p in problems))

    def test_generated_scaffold_fails_validation_until_filled_in(self):
        args = _scaffold_args(archetype="gated-pipeline", use_case=None, high_stakes_task="a rollout RFC", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertNotEqual(validate_skill_example.validate(skeleton), [])


class ValidateDecisionTreeTests(unittest.TestCase):
    def test_valid_example_passes(self):
        self.assertEqual(validate_skill_example.validate(GOOD_DECISION_TREE), [])

    def test_too_few_matrix_rows_is_reported(self):
        broken = GOOD_DECISION_TREE.replace(
            "| Elevated latency only, no errors | Check database connection pool saturation |\n"
            "| Page with no corresponding dashboard signal | Treat as a possible false "
            "alarm; page secondary on-call to confirm |\n", "")
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Triage Matrix" in p and "data row" in p for p in problems))

    def test_missing_table_is_reported(self):
        broken = GOOD_DECISION_TREE.replace(
            "| Trigger | Resolution Strategy |\n"
            "|---|---|\n"
            "| Error rate spike immediately after a deploy | Roll back the deploy first |\n"
            "| Error rate spike with no recent deploy | Check upstream dependency status pages |\n"
            "| Elevated latency only, no errors | Check database connection pool saturation |\n"
            "| Page with no corresponding dashboard signal | Treat as a possible false "
            "alarm; page secondary on-call to confirm |\n",
            "A prose description of the triage logic instead of a table.\n",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("missing a markdown table" in p for p in problems))

    def test_generated_scaffold_fails_validation_until_filled_in(self):
        args = _scaffold_args(archetype="decision-tree", use_case=None, scenario="an ambiguous incident page", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertNotEqual(validate_skill_example.validate(skeleton), [])


class ValidateElicitationTests(unittest.TestCase):
    def test_valid_example_passes(self):
        self.assertEqual(validate_skill_example.validate(GOOD_ELICITATION), [])

    def test_wrong_question_count_is_reported(self):
        broken = GOOD_ELICITATION.replace(
            "3. Is this under normal load or peak traffic?\n"
            "   a) Normal traffic only\n"
            "   b) Peak traffic (e.g. flash sale)\n"
            "   c) Both\n",
            "",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("has 2 question(s), expected 3-4" in p for p in problems))

    def test_question_without_options_is_reported(self):
        broken = GOOD_ELICITATION.replace(
            "1. Which checkout step is slow?\n"
            "   a) Cart summary load\n"
            "   b) Payment authorization\n"
            "   c) Order confirmation\n"
            "   d) The whole flow end-to-end\n",
            "1. Which checkout step is slow?\n",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("no lettered multiple-choice options" in p for p in problems))

    def test_generated_scaffold_fails_validation_until_filled_in(self):
        args = _scaffold_args(archetype="elicitation", use_case=None, user_request="make it faster", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertNotEqual(validate_skill_example.validate(skeleton), [])


class ValidateAdversarialAuditTests(unittest.TestCase):
    def test_valid_example_passes(self):
        self.assertEqual(validate_skill_example.validate(GOOD_ADVERSARIAL_AUDIT), [])

    def test_single_attack_vector_is_reported(self):
        broken = GOOD_ADVERSARIAL_AUDIT.replace(
            "Attack Vector 2: Only one random seed was reported; no variance across seeds\n"
            "or folds is shown, so the 95% figure could be a favorable outlier.\n",
            "",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("at least 2 distinct" in p for p in problems))

    def test_prose_only_patch_is_reported(self):
        broken = GOOD_ADVERSARIAL_AUDIT.replace(
            "```diff\n"
            "-mean, std = full_dataset.mean(), full_dataset.std()\n"
            "-X = (full_dataset - mean) / std\n"
            "-X_train, X_test = split(X)\n"
            "+X_train_raw, X_test_raw = split(full_dataset)\n"
            "+mean, std = X_train_raw.mean(), X_train_raw.std()\n"
            "+X_train = (X_train_raw - mean) / std\n"
            "+X_test = (X_test_raw - mean) / std\n"
            "```",
            "Fit normalization on the training split only, after splitting.",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Hardened Architectural Patch" in p and "diff" in p for p in problems))

    def test_generated_scaffold_fails_validation_until_filled_in(self):
        args = _scaffold_args(
            archetype="adversarial-audit", use_case=None, candidate_artifact="a training writeup", takeaways=None
        )
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertNotEqual(validate_skill_example.validate(skeleton), [])


class ValidateTestFirstTests(unittest.TestCase):
    def test_valid_example_passes(self):
        self.assertEqual(validate_skill_example.validate(GOOD_TEST_FIRST), [])

    def test_red_section_without_failure_marker_is_reported(self):
        broken = GOOD_TEST_FIRST.replace(
            "```\n$ python3 -m pytest tests/test_loader_throughput.py\n"
            "FAILED tests/test_loader_throughput.py::test_dataloader_sustains_throughput\n"
            "AssertionError: 212 samples/sec\n```",
            "```\n$ python3 -m pytest tests/test_loader_throughput.py\nran the suite\n```",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Executable Failing Test (Red)" in p and "raw failure" in p for p in problems))

    def test_green_section_without_metric_is_reported(self):
        broken = GOOD_TEST_FIRST.replace(
            "```\n$ python3 -m pytest tests/test_loader_throughput.py\n"
            "1 passed in 12.3s\nthroughput=612 samples/sec, gpu_util=93%\n```",
            "```\n$ python3 -m pytest tests/test_loader_throughput.py\n1 passed\n```",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Verified Passing Execution (Green)" in p and "numeric metric" in p for p in problems))

    def test_failure_marker_only_in_prose_is_reported(self):
        broken = GOOD_TEST_FIRST.replace(
            "```\n$ python3 -m pytest tests/test_loader_throughput.py\n"
            "FAILED tests/test_loader_throughput.py::test_dataloader_sustains_throughput\n"
            "AssertionError: 212 samples/sec\n```",
            "The run hit an error and FAILED as expected.\n\n"
            "```\n$ python3 -m pytest tests/test_loader_throughput.py\nran the suite\n```",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Executable Failing Test (Red)" in p and "raw failure" in p for p in problems))

    def test_green_metric_only_in_prose_is_reported(self):
        broken = GOOD_TEST_FIRST.replace(
            "```\n$ python3 -m pytest tests/test_loader_throughput.py\n"
            "1 passed in 12.3s\nthroughput=612 samples/sec, gpu_util=93%\n```",
            "Throughput reached 612 samples/sec.\n\n"
            "```\n$ python3 -m pytest tests/test_loader_throughput.py\n1 passed\n```",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("Verified Passing Execution (Green)" in p and "numeric metric" in p for p in problems))

    def test_fenced_blocks_helper_ignores_prose_and_unclosed_fence(self):
        text = "prose\n```\na\n```\nmore\n```py\nb\n```\ntail\n```\nopen"
        self.assertEqual([b.strip() for b in validate_skill_example.fenced_blocks(text)], ["a", "b"])

    def test_generated_scaffold_fails_validation_until_filled_in(self):
        args = _scaffold_args(archetype="test-first", use_case=None, target="a throughput invariant", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertNotEqual(validate_skill_example.validate(skeleton), [])


class ValidatePostmortemTests(unittest.TestCase):
    def test_valid_example_passes(self):
        self.assertEqual(validate_skill_example.validate(GOOD_POSTMORTEM), [])

    def test_wrong_why_step_count_is_reported(self):
        broken = GOOD_POSTMORTEM.replace(
            "5. Why does CI not check that? Because the config-schema linter was scoped\n"
            "   to type checks only when it was introduced, and was never extended to\n"
            "   cover default-value compatibility.\n",
            "",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("expected exactly 5" in p for p in problems))

    def test_human_error_stopping_point_is_reported(self):
        broken = GOOD_POSTMORTEM.replace(
            "5. Why does CI not check that? Because the config-schema linter was scoped\n"
            "   to type checks only when it was introduced, and was never extended to\n"
            "   cover default-value compatibility.",
            "5. Why does CI not check that? Because of human error during setup.",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any('stops at "human error"' in p for p in problems))

    def test_monitoring_section_without_metric_is_reported(self):
        broken = GOOD_POSTMORTEM.replace(
            "Added a monitoring rule: alert and automatically rollback if `api-5xx-rate`\n"
            "exceeds 2% for 2 consecutive minutes within 10 minutes of a deploy.",
            "We will add more monitoring going forward.",
        )
        problems = validate_skill_example.validate(broken)
        self.assertTrue(any("must name a concrete monitoring rule" in p for p in problems))

    def test_generated_scaffold_fails_validation_until_filled_in(self):
        args = _scaffold_args(archetype="postmortem", use_case=None, incident="an outage", takeaways=None)
        skeleton = generate_skill_example.build_skeleton(args)
        self.assertNotEqual(validate_skill_example.validate(skeleton), [])


class DiversityCheckerTests(unittest.TestCase):
    def _write(self, tmp_dir: Path, name: str, content: str) -> Path:
        path = tmp_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_no_violation_across_different_skills(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            a = self._write(tmp_path, "a.md", GOOD_ADVERSARIAL_AUDIT)  # skill: deep-learning
            b = self._write(
                tmp_path, "b.md", GOOD_ADVERSARIAL_AUDIT.replace("skill: deep-learning", "skill: hep-analysis")
            )
            violations = check_example_diversity.find_violations([a, b])
            self.assertEqual(violations, [])

    def test_violation_when_same_archetype_and_skill_repeat(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            a = self._write(tmp_path, "a.md", GOOD_ADVERSARIAL_AUDIT)
            b = self._write(tmp_path, "b.md", GOOD_ADVERSARIAL_AUDIT)
            violations = check_example_diversity.find_violations([a, b])
            self.assertEqual(len(violations), 1)
            self.assertIn("adversarial-audit", violations[0])
            self.assertIn("deep-learning", violations[0])

    def test_cli_ok_on_diverse_set(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            a = self._write(tmp_path, "a.md", GOOD_ADVERSARIAL_AUDIT)
            b = self._write(
                tmp_path, "b.md", GOOD_ADVERSARIAL_AUDIT.replace("skill: deep-learning", "skill: hep-analysis")
            )
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/check_example_diversity.py"), str(a), str(b)],
                capture_output=True, text=True, timeout=600
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn("ok: no diversity violations", result.stdout)

    def test_cli_fails_on_violation(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            a = self._write(tmp_path, "a.md", GOOD_ADVERSARIAL_AUDIT)
            b = self._write(tmp_path, "b.md", GOOD_ADVERSARIAL_AUDIT)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/check_example_diversity.py"), str(a), str(b)],
                capture_output=True, text=True, timeout=600
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("diversity violation(s) found", result.stdout)


class MetricRegexTests(unittest.TestCase):
    """Units a real log or monitoring rule uses must count as a concrete metric (found 2026-10-02)."""

    def test_percent_word_and_hyphenated_units_match(self):
        for text in ("loss rose 0.5 percent", "a 2,000-step window", "p99 latency 85 ms", "error rate 0.5%"):
            self.assertIsNotNone(validate_skill_example.METRIC_RE.search(text), text)

    def test_plain_numbers_do_not_match(self):
        for text in ("step 3 of the plan", "version 12"):
            self.assertIsNone(validate_skill_example.METRIC_RE.search(text), text)


if __name__ == "__main__":
    unittest.main()
