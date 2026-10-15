"""ANA-P4-1: each hep-measurement SKILL.md invariant, as validator behaviour on the contracts 2.6.0 fixtures
(contracts/fixtures/artifacts/{invalid,unresolved}/measurement_v26_*.json). Synthetic fixtures."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from contracts.validate import validate_artifact  # noqa: E402

ART = ROOT / 'contracts' / 'fixtures' / 'artifacts'

# invariant (SKILL.md wording, shortened) -> fixtures that break it, with the outcome they must have
INVARIANTS = {
    'estimand in one sentence': ('error', ['estimand_missing', 'estimand_not_a_sentence']),
    'observable spec complete': ('error', ['variable_incomplete', 'phase_space_missing', 'frame_missing']),
    'unknown is never zero, and is listed': ('error', ['zero_normalization', 'zero_correction', 'shape_only_value',
                                                       'unknown_not_listed']),
    'each correction exactly once, normalization kind declared': (
        'error', ['correction_case_variant', 'category_repeated', 'bare_efficiency_with_factor', 'unknown_category',
                  'luminosity_twice', 'included_and_applied']),
    'every selection names its conditional denominator': ('error', ['selections_empty', 'denominator_blank',
                                                                    'misspelled_key']),
    'every background has an estimator and a control region or constraint': (
        'error', ['backgrounds_empty', 'background_estimator_missing', 'background_constraint_missing']),
    'every background has a closure test': ('unresolved', ['closure_missing']),
    'a systematic is evaluated through its physical effect (applied_via)': (
        'error', ['systematics_empty', 'applied_via_blank', 'duplicate_systematic']),
    'blinded regions stay masked; no observed result while blinded': ('error', ['blinded_no_mask', 'blinded_observed']),
    'ratios list their cancellations': ('error', ['ratio_block_missing', 'ratio_self', 'ratio_cancellations_empty']),
    'periods are ordered': ('error', ['period_reversed']),
    'unresolved inputs are listed explicitly': ('unresolved', ['input_listed']),
}


def load(kind, name):
    return json.loads((ART / kind / f'measurement_v26_{name}.json').read_text(encoding='utf-8'))


class InvariantBehaviourTests(unittest.TestCase):
    def test_each_invariant_is_enforced(self):
        for invariant, (outcome, names) in INVARIANTS.items():
            for name in names:
                with self.subTest(invariant=invariant, fixture=name):
                    kind = 'unresolved' if outcome == 'unresolved' else 'invalid'
                    rep = validate_artifact(load(kind, name))
                    severities = {f.severity for f in rep.findings if f.code.startswith('measurement.')}
                    self.assertIn(outcome, severities, rep.as_dict())
                    self.assertEqual(rep.ok, outcome != 'error')

    def test_every_rule_fixture_is_mapped_to_an_invariant(self):
        mapped = {n for _, names in INVARIANTS.values() for n in names}
        shipped = {p.stem.removeprefix('measurement_v26_') for kind in ('invalid', 'unresolved')
                   for p in (ART / kind).glob('measurement_v26_*.json')}
        self.assertEqual(shipped, mapped)

    def test_the_compliant_spec_passes(self):
        rep = validate_artifact(json.loads((ART / 'valid' / 'measurement_v26.json').read_text(encoding='utf-8')))
        self.assertEqual(rep.findings, [])


if __name__ == '__main__':
    unittest.main()
