"""Reusable conformance tests of a cr-provider/1 provider (PRV-1, PRV-2 of the cosmic-ray propagation plan).

A provider work package (B1, D1, D2, E2: USINE, DRAGON2, GALPROP, emulator) adds to its own test module:

    from tests.core.provider_conformance import ProviderConformance

    class UsineProviderConformance(ProviderConformance, unittest.TestCase):
        PROVIDER_ID = "usine"                      # the id in its adapter.json 'provider' field
        REQUEST = {...}                            # one small in-domain request (protocol, provider, provider_version,
                                                   # points, observables, want); the version is the registered one
        OUTSIDE_POINT = None                       # optional: a point outside the declared domain
        VOCAB_PROFILES = ()                        # profile.json paths whose namespaced terms the predictions use

        def unavailable_reason(self):              # optional: why the provider cannot run here (skip), else None
            return None if os.environ.get("HEP_USINE_BIN") else "USINE not installed (HEP_USINE_BIN unset)"

It writes a fresh registry with tools/provider_registry.py --write into a temporary folder, runs
core/provider/conformance.py (direct single-shot and --serve calls, the refusals, the runner) and validates every
response against contracts/schemas/cr_provider.json (#/$defs/response), with the vocabulary of VOCAB_PROFILES. The
same checks run from the command line: python3 core/provider/conformance.py --provider-registry R --provider ID
--request REQUEST.json. ProviderConformance is a mixin, not a TestCase, so importing it collects no test by itself.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from contracts.schema import validate  # noqa: E402
from contracts.vocab import Vocabulary  # noqa: E402
from core.provider.conformance import run_conformance  # noqa: E402

RESPONSE_SCHEMA = {"$ref": "cr_provider.json#/$defs/response"}
REQUEST_SCHEMA = {"$ref": "cr_provider.json#/$defs/request"}


def write_registry(folder: Path, user_providers=()) -> Path:
    """tools/provider_registry.py --write into `folder`; the registry path."""
    path = Path(folder) / "registry.json"
    argv = [sys.executable, str(ROOT / "tools" / "provider_registry.py"), "--write", str(path)]
    for decl in user_providers:
        argv += ["--user-provider", str(decl)]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        raise AssertionError(f"provider_registry.py --write failed: {proc.stdout}{proc.stderr}")
    return path


def vocabulary(profile_paths=()) -> Vocabulary:
    return Vocabulary.with_profiles([json.loads(Path(p).read_text(encoding="utf-8")) for p in profile_paths])


class ProviderConformance:
    PROVIDER_ID: str = ""
    REQUEST: dict = {}
    OUTSIDE_POINT: dict | None = None
    VOCAB_PROFILES: tuple = ()
    USER_PROVIDERS: tuple = ()  # user-supplied declaration files to add to the registry
    TIMEOUT_S: float = 600.0

    def unavailable_reason(self) -> str | None:
        return None

    def _conformance(self) -> dict:
        reason = self.unavailable_reason()
        if reason:
            self.skipTest(reason)
        cached = getattr(type(self), "_conformance_report", None)
        if cached is None:
            with tempfile.TemporaryDirectory() as workdir:
                registry = write_registry(Path(workdir), self.USER_PROVIDERS)
                cached = run_conformance(registry, self.PROVIDER_ID, self.REQUEST, self.OUTSIDE_POINT, self.TIMEOUT_S)
            type(self)._conformance_report = cached
        return cached

    def test_provider_request_follows_the_schema(self):
        rep = validate(self.REQUEST, REQUEST_SCHEMA, Vocabulary())
        self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors])

    def test_provider_conformance_checks_pass(self):
        report = self._conformance()
        failed = [c for c in report["checks"] if not c["passed"]]
        self.assertEqual(failed, [], json.dumps(failed, indent=1))
        self.assertEqual(report["status"], "pass")

    def test_provider_responses_follow_the_schema(self):
        report = self._conformance()
        vocab = vocabulary(self.VOCAB_PROFILES)
        self.assertTrue(report["responses"])
        for name, response in report["responses"].items():
            with self.subTest(response=name):
                rep = validate(response, RESPONSE_SCHEMA, vocab)
                self.assertTrue(rep.ok, [f.as_dict() for f in rep.errors][:5])

    def test_provider_single_shot_equals_serve(self):
        checks = {c["id"]: c for c in self._conformance()["checks"]}
        self.assertIn("prv-2", checks)
        self.assertTrue(checks["prv-2"]["passed"], checks["prv-2"]["detail"])
