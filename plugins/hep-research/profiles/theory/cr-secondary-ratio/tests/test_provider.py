"""theory:cr-secondary-ratio provider (scripts/provider.py, cr-provider/1): conformance PRV-1 and PRV-2 with the core
checks (core/provider/conformance.py) and the contract schema, its values equal to predict.py's closed form, the D0/L
degeneracy through the protocol, components that add up to the prediction, and the declared quadrature tolerance.
A profile test may not import the plugin's tests package (layering), so it runs the same checks as the shared helper
tests/core/provider_conformance.py through core and contracts directly. Inputs are ILLUSTRATIVE."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT.parents[2]
for entry in (str(PLUGIN), str(ROOT / "scripts")):
    if entry not in sys.path:
        sys.path.insert(0, entry)
import predict  # noqa: E402
import provider  # noqa: E402

from contracts.schema import validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.provider.conformance import comparable_hash, run_conformance  # noqa: E402
from core.provider.runner import ProviderRunner  # noqa: E402

PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
CFG = json.loads((ROOT / "benchmarks" / "bc-benchmark.json").read_text(encoding="utf-8"))
EDGES = CFG["energy_bin_edges_gev_per_n"]
PROVIDER_ID = PROFILE["provider"]["id"]


def request(points, want=("lis", "components")) -> dict:
    return {"protocol": "cr-provider/1", "provider": PROVIDER_ID, "provider_version": PROFILE["version"],
            "theory_spec_ref": "derivations/theory-spec.json", "transport": None, "points": points,
            "observables": [{"id": "B/C", "axis": "ekn", "unit": "GeV/n",
                             "bins": [[lo, hi] for lo, hi in zip(EDGES, EDGES[1:])]}],
            "want": list(want), "seed": None}


REQUEST = request([{"D0_cm2_s": 3e28, "L_kpc": 4.0}, {"D0_cm2_s": 2e28, "delta": 0.45, "L_kpc": 6.0,
                                                       "R0_gv": 1.0, "disc_halfwidth_pc": 100.0}])


def write_registry(folder: Path) -> Path:
    path = folder / "registry.json"
    proc = subprocess.run([sys.executable, str(PLUGIN / "tools" / "provider_registry.py"), "--write", str(path)],
                          capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise AssertionError(proc.stdout + proc.stderr)
    return path


@unittest.skipUnless(find_spec("scipy") and find_spec("numpy"), "numpy and scipy are required (requirements-core.txt)")
class ClosedFormProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._workdir = tempfile.TemporaryDirectory()
        cls.registry = write_registry(Path(cls._workdir.name))
        cls.report = run_conformance(cls.registry, PROVIDER_ID, REQUEST, timeout_s=600)

    @classmethod
    def tearDownClass(cls):
        cls._workdir.cleanup()

    def test_conformance_checks_pass(self):
        failed = [c for c in self.report["checks"] if not c["passed"]]
        self.assertEqual(failed, [], json.dumps(failed, indent=1))

    def test_responses_follow_the_schema(self):
        vocab = Vocabulary.with_profiles([PROFILE])
        self.assertTrue(validate(REQUEST, {"$ref": "cr_provider.json#/$defs/request"}, vocab).ok)
        for name, response in self.report["responses"].items():
            with self.subTest(response=name):
                rep = validate(response, {"$ref": "cr_provider.json#/$defs/response"}, vocab)
                self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors][:5])

    def test_single_shot_equals_serve(self):
        checks = {c["id"]: c for c in self.report["checks"]}
        self.assertTrue(checks["prv-2"]["passed"], checks["prv-2"]["detail"])

    def test_declaration_is_the_profile_field(self):
        self.assertEqual(provider.declaration()["version"], PROFILE["version"])
        self.assertTrue(validate(PROFILE, "profile.json").ok)

    def test_values_are_the_closed_form(self):
        res = self.report["responses"]["single-shot"]["results"]
        for point, out in zip(REQUEST["points"], res):
            with self.subTest(point=point):
                want = predict.bin_averaged(dict(CFG, model="diffusion-1d"), EDGES, provider.model_overrides(point))
                self.assertEqual(out["predictions"][0]["values"]["values"], want)
        bench = json.loads((ROOT / "predictions" / "bc-benchmark.prediction.json").read_text(encoding="utf-8"))
        got, pinned = res[0]["predictions"][0]["values"]["values"], bench["extension"]["values"]["values"]
        self.assertEqual(len(got), len(pinned))
        for a, b in zip(got, pinned):   # relative 1e-12: libm differs across platforms in the last digits
            self.assertTrue(math.isclose(a, b, rel_tol=1e-12, abs_tol=0.0), (a, b))

    def test_components_add_up_to_the_prediction(self):
        for out in self.report["responses"]["single-shot"]["results"]:
            total = out["predictions"][0]["values"]["values"]
            comps = [c["values"] for c in out["components"]]
            self.assertEqual({c["id"] for c in out["components"]}, {"C->B", "O->B"})
            for k, value in enumerate(total):
                self.assertAlmostEqual(sum(c[k] for c in comps) / value, 1.0, delta=1e-12)

    def test_d0_over_l_degeneracy_through_the_protocol(self):
        with ProviderRunner(self.registry) as runner:
            out = runner.evaluate(request([{"D0_cm2_s": 3e28, "L_kpc": 4.0}, {"D0_cm2_s": 7.5e28, "L_kpc": 10.0}],
                                          want=("lis",)))
        a, b = (r["predictions"][0]["values"]["values"] for r in out["results"])
        for x, y in zip(a, b):
            self.assertAlmostEqual(y / x, 1.0, delta=1e-12)

    def test_declared_numerical_tolerance_holds(self):
        """8-node Gauss-Legendre bin average against 32 nodes: within the declared numerical_tolerance."""
        cfg = dict(CFG, model="diffusion-1d")
        coarse = predict.bin_averaged(cfg, EDGES, n_nodes=provider.QUADRATURE_NODES)
        fine = predict.bin_averaged(cfg, EDGES, n_nodes=32)
        self.assertLess(max(abs(c / f - 1) for c, f in zip(coarse, fine)), provider.NUMERICAL_TOLERANCE)

    def test_labels_and_no_modulation(self):
        res = self.report["responses"]["single-shot"]["results"][0]
        self.assertEqual(res["labels"], ["synthetic", "unvalidated"])
        self.assertIsNone(res["evaluation"]["computational_run_ref"])
        with ProviderRunner(self.registry) as runner:
            out = runner.evaluate(request([{"L_kpc": 4.0}], want=("lis", "modulated")))
        self.assertEqual(out["reason"], "unsupported-want")

    def test_bins_outside_the_validity_range(self):
        req = request([{"L_kpc": 4.0}], want=("lis",))
        req["observables"][0]["bins"] = [[0.5, 1.0], [1.0, 3.0]]
        with ProviderRunner(self.registry) as runner:
            self.assertEqual(runner.evaluate(req)["reason"], "out-of-domain")
        with ProviderRunner(self.registry, allow_outside=True) as runner:
            out = runner.evaluate(req)
        self.assertIn("outside-validated-range", out["results"][0]["labels"])

    def test_single_shot_equals_runner_serve(self):
        with ProviderRunner(self.registry, session="serve") as runner:
            served = runner.evaluate(REQUEST)
        self.assertEqual(comparable_hash(served), comparable_hash(self.report["responses"]["single-shot"]))

    def test_help(self):
        proc = subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "provider.py"), "--help"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--serve", proc.stdout)


if __name__ == "__main__":
    unittest.main()
