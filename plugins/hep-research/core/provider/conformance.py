#!/usr/bin/env python3
"""Conformance of one provider to cr-provider/1: the checks PRV-1 and PRV-2 of the cosmic-ray propagation plan, the
same for every provider (closed form, external code, emulator).

Given the registry, the provider id and one in-domain request, it calls the provider's entrypoint directly (not
through the runner, so the provider's own refusals are tested) and through the runner:
  declared           the provider is in the registry with a valid declaration
  single-shot        'ENTRY --request R --response S' answers with a protocol-valid response whose points are all ok
  serve              one '--serve' session answers the same request twice with protocol-valid responses
  prv-2              single-shot and --serve responses have the same sha256 after removing elapsed_s and time stamps
                     (and the two --serve answers too, for a deterministic provider)
  unsupported-want   a request that wants anything but lis/components (here 'modulated') fails with unsupported-want
  out-of-domain      a point outside the declared domain fails with out-of-domain and no prediction
  outside-allowed    with --allow-outside-validated-range the same point is evaluated and labelled outside-validated-range
  unregistered       the runner refuses a provider id that is not in the registry (unregistered-provider)
  runner-agrees      the runner's response equals the direct single-shot response (PRV-2 comparison; a user-supplied
                     provider's added label user-supplied set aside)
The out-of-domain point is the request's first point with its first domain parameter (sorted names) moved above the
range by its width, unless an explicit point is given. The schema check of the responses (contracts/schemas/
cr_provider.json) is the test helper's part (tests/core/provider_conformance.py), since core does not read contracts.

Command line:
  python3 core/provider/conformance.py --provider-registry REGISTRY.json --provider ID --request R.json
      [--outside-point '{"L_kpc": 40}'] [--timeout SECONDS]
Output: one JSON object (status pass|fail, checks [{id, passed, detail}], responses). Exit 0 pass, 1 a check failed,
2 unusable input.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.provider.hashing import canonical_sha256  # noqa: E402
from core.provider.protocol import (  # noqa: E402
    OUTSIDE_LABEL,
    USER_LABEL,
    check_declaration,
    check_request,
    check_response,
    strip_volatile,
)
from core.provider.registry import REGISTRY_FORMAT, RegistryError, load_registry, parse_registry  # noqa: E402
from core.provider.runner import (  # noqa: E402
    DEFAULT_TIMEOUT_S,
    ProviderCallError,
    ProviderRunner,
    ServeSession,
    call_single_shot,
)


def comparable_hash(response: dict, drop_labels=()) -> str:
    """sha256 of a response without run times and time stamps (and without the given labels): the PRV-2 key."""
    doc = strip_volatile(response)
    for res in doc.get("results", []):
        if drop_labels and isinstance(res.get("labels"), list):
            res["labels"] = [x for x in res["labels"] if x not in drop_labels]
    return canonical_sha256(doc)


def default_outside_point(request: dict, declaration: dict) -> dict | None:
    domain = declaration["domain"]
    if not domain:
        return None
    name = sorted(domain)[0]
    rng = domain[name]
    point = dict(request["points"][0])
    point[name] = rng["max"] + (rng["max"] - rng["min"] or abs(rng["max"]) or 1.0)
    return point


def run_conformance(registry, provider_id: str, request: dict, outside_point: dict | None = None,
                    timeout_s: float = DEFAULT_TIMEOUT_S, python: str | None = None) -> dict:
    """The conformance report; registry is a path or a registry document."""
    checks: list[dict] = []
    responses: dict[str, dict] = {}

    def record(check_id: str, passed: bool, detail: str = "") -> bool:
        checks.append({"id": check_id, "passed": bool(passed), "detail": detail})
        return bool(passed)

    def report() -> dict:
        return {"status": "pass" if checks and all(c["passed"] for c in checks) else "fail", "provider": provider_id,
                "checks": checks, "responses": responses}

    entries = parse_registry(registry) if isinstance(registry, dict) else load_registry(registry)
    entry = entries.get(provider_id)
    problems = check_declaration(entry.declaration) if entry else ["not in the registry"]
    problems += [f"request: {p}" for p in check_request(request)]
    if entry and not problems and (request["provider"] != provider_id or request["provider_version"] != entry.version):
        problems.append(f"the conformance request must name {provider_id} version {entry.version}")
    if not record("declared", not problems, "; ".join(problems)) or entry is None:
        return report()
    python = python or sys.executable

    def direct(req: dict, allow_outside: bool = False) -> dict | None:
        try:
            return call_single_shot(entry, req, allow_outside, timeout_s, python)
        except ProviderCallError as exc:
            record("provider-call", False, f"{exc.reason}: {exc.detail}")
            return None

    single = direct(request)
    if single is not None:
        problems = check_response(single, request)
        bad = [r["point_index"] for r in single.get("results", []) if r.get("status") != "ok"] if not problems else []
        record("single-shot", not problems and not bad and single["status"] == "ok",
               "; ".join(problems) or (f"points {bad} failed: {single['results'][bad[0]].get('reason')} "
                                       f"{single['results'][bad[0]].get('detail', '')}" if bad else ""))
        responses["single-shot"] = single
        if problems:
            single = None  # not comparable: the failure is recorded above

    session = ServeSession(entry, False, timeout_s, python)
    try:
        served = [session.send(request), session.send(request)]
    except ProviderCallError as exc:
        served = None
        record("serve", False, f"{exc.reason}: {exc.detail}")
    finally:
        session.close()
    if served is not None:
        problems = [p for s in served for p in check_response(s, request)]
        record("serve", not problems and all(s["status"] == "ok" for s in served), "; ".join(problems))
        responses["serve"] = served[0]
        if single is not None and not problems:
            same = comparable_hash(single) == comparable_hash(served[0])
            again = comparable_hash(served[0]) == comparable_hash(served[1])
            deterministic = entry.declaration["deterministic"] or request.get("seed") is not None
            record("prv-2", same and (again or not deterministic),
                   "" if same and (again or not deterministic) else
                   ("single-shot and --serve differ" if not same else "two --serve answers differ"))

    bad_want = dict(copy.deepcopy(request), want=["lis", "modulated"])
    refused = direct(bad_want)
    if refused is not None:
        record("unsupported-want", refused.get("status") == "failed" and refused.get("reason") == "unsupported-want"
               and not refused.get("results"), json.dumps({k: refused.get(k) for k in ("status", "reason")}))

    point = outside_point if outside_point is not None else default_outside_point(request, entry.declaration)
    if point is None:
        record("out-of-domain", False, "the declaration has an empty domain; give an outside point")
    else:
        outside_req = dict(copy.deepcopy(request), points=[point])
        refused = direct(outside_req)
        if refused is not None:
            res = (refused.get("results") or [{}])[0]
            record("out-of-domain", res.get("status") == "failed" and res.get("reason") == "out-of-domain"
                   and "predictions" not in res and not check_response(refused, outside_req),
                   json.dumps({k: res.get(k) for k in ("status", "reason", "detail")}))
        allowed = direct(outside_req, allow_outside=True)
        if allowed is not None:
            res = (allowed.get("results") or [{}])[0]
            problems = check_response(allowed, outside_req)
            record("outside-allowed", not problems and res.get("status") == "ok"
                   and OUTSIDE_LABEL in res.get("labels", []),
                   "; ".join(problems) or json.dumps({k: res.get(k) for k in ("status", "reason", "labels")}))
            responses["outside-allowed"] = allowed

    with ProviderRunner({"format": REGISTRY_FORMAT, "providers": []}) as empty_runner:
        refused = empty_runner.evaluate(request)
    record("unregistered", refused["status"] == "failed" and refused.get("reason") == "unregistered-provider"
           and not refused["results"], json.dumps({k: refused.get(k) for k in ("status", "reason")}))

    with ProviderRunner(registry, timeout_s=timeout_s, python=python) as runner:
        via_runner = runner.evaluate(request)
    if single is not None:
        drop = (USER_LABEL,) if entry.user_supplied else ()
        record("runner-agrees", comparable_hash(via_runner, drop) == comparable_hash(single, drop),
               "" if comparable_hash(via_runner, drop) == comparable_hash(single, drop) else
               f"runner status {via_runner['status']}, direct {single['status']}")
        responses["runner"] = via_runner
    return report()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     epilog="Exit 0 pass, 1 a check failed, 2 unusable input.")
    parser.add_argument("--provider-registry", type=Path, required=True, help="registry file")
    parser.add_argument("--provider", required=True, help="provider id")
    parser.add_argument("--request", type=Path, required=True, help="an in-domain request for this provider")
    parser.add_argument("--outside-point", help="JSON object: a point outside the declared domain")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="seconds per provider call")
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
        outside = json.loads(args.outside_point) if args.outside_point else None
        if outside is not None and not isinstance(outside, dict):
            raise ValueError("--outside-point is a JSON object")
        result = run_conformance(args.provider_registry, args.provider, request, outside, args.timeout)
    except (OSError, ValueError, RegistryError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=1, sort_keys=True))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
