"""tests/core/provider_conformance.ProviderConformance, the shared PRV-1/PRV-2 test of provider work packages: it passes
for a conforming provider and fails for a missing or broken one, also through subclasses of subclasses and in either
run order (each class judges its own provider; no report is inherited from a parent class)."""
from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.core.provider_conformance import ProviderConformance  # noqa: E402

PROFILE = json.loads((ROOT / "profiles" / "theory" / "cr-secondary-ratio" / "profile.json").read_text(encoding="utf-8"))
GOOD_ID = PROFILE["provider"]["id"]


def request(provider: str, version: str) -> dict:
    return {"protocol": "cr-provider/1", "provider": provider, "provider_version": version,
            "points": [{"D0_cm2_s": 3e28, "L_kpc": 4.0}],
            "observables": [{"id": "B/C", "axis": "ekn", "unit": "GeV/n", "bins": [[1.0, 10.0], [10.0, 100.0]]}],
            "want": ["lis", "components"], "seed": None}


GARBAGE = textwrap.dedent('''\
    import sys
    from pathlib import Path
    if "--response" in sys.argv:
        Path(sys.argv[sys.argv.index("--response") + 1]).write_text('{"hello": 1}')
    else:
        for line in sys.stdin:
            print('{"hello": 1}', flush=True)
''')


def make_classes(folder: Path) -> dict[str, type]:
    """Fresh test classes (fresh caches) for one run order."""
    entry = folder / "garbage.py"
    entry.write_text(GARBAGE, encoding="utf-8")
    decl = folder / "garbage.json"
    decl.write_text(json.dumps({"id": "user-garbage", "entrypoint": "garbage.py", "protocol": "cr-provider/1",
                                "version": "0.0.1", "domain": {"L_kpc": {"min": 1, "max": 10}},
                                "observables": ["B/C"], "axes": ["ekn"], "decomposable": True,
                                "deterministic": True, "output_units": {"ratio": "1"}}), encoding="utf-8")

    class Good(ProviderConformance, unittest.TestCase):
        PROVIDER_ID = GOOD_ID
        REQUEST = request(GOOD_ID, PROFILE["version"])
        VOCAB_PROFILES = (ROOT / "profiles" / "theory" / "cr-secondary-ratio" / "profile.json",)

    class Missing(Good):
        PROVIDER_ID = "nonexistent"
        REQUEST = request("nonexistent", "1.0.0")

    class MissingChild(Missing):
        pass

    class GoodGrandchild(MissingChild):
        PROVIDER_ID = GOOD_ID
        REQUEST = request(GOOD_ID, PROFILE["version"])

    class UserGarbage(Good):
        PROVIDER_ID = "user-garbage"
        REQUEST = request("user-garbage", "0.0.1")
        USER_PROVIDERS = (decl,)

    return {c.__name__: c for c in (Good, Missing, MissingChild, GoodGrandchild, UserGarbage)}


EXPECT_PASS = {"Good": True, "Missing": False, "MissingChild": False, "GoodGrandchild": True, "UserGarbage": False}


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "the closed-form provider needs numpy and scipy")
class MixinVerdicts(unittest.TestCase):
    def run_order(self, names: list[str]) -> dict[str, bool]:
        with tempfile.TemporaryDirectory() as workdir:
            classes = make_classes(Path(workdir))
            verdicts = {}
            for name in names:
                suite = unittest.defaultTestLoader.loadTestsFromTestCase(classes[name])
                outcome = unittest.TestResult()
                suite.run(outcome)
                verdicts[name] = outcome.wasSuccessful() and outcome.testsRun == 4 and not outcome.skipped
            return verdicts

    def test_both_run_orders(self):
        order = list(EXPECT_PASS)
        for names in (order, list(reversed(order))):
            with self.subTest(order=names):
                self.assertEqual(self.run_order(names), {n: EXPECT_PASS[n] for n in names})

    def test_subclass_does_not_inherit_a_parent_report(self):
        with tempfile.TemporaryDirectory() as workdir:
            classes = make_classes(Path(workdir))
            good, missing = classes["Good"](), classes["Missing"]()
            self.assertEqual(good._conformance()["status"], "pass")
            self.assertEqual(missing._conformance()["status"], "fail")
            self.assertNotIn("_conformance_reports", classes["MissingChild"].__dict__)


if __name__ == "__main__":
    unittest.main()
