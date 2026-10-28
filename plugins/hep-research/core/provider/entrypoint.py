"""The provider side of cr-provider/1: one command line for every provider entrypoint.

A provider script declares itself (its 'provider' declaration, with the version filled in) and supplies one function,
evaluate_point(request, point, context) -> dict, that returns for one parameter point:
  {"predictions": [<prediction extension, one per requested observable, in order>],   # when "lis" is wanted
   "components": [<component>, ...],                                                    # when "components" is wanted
   "labels": [<artifact status labels of the inputs>], "numerical_tolerance": <relative or None>,
   "computational_run_ref": <reference of the run's computational-run artifact, or None>}
context = {"want": set of wanted items, "outside": True when the point is evaluated beyond the declared domain}.
provider_main() then gives the script its command line:
  SCRIPT --request REQUEST.json --response RESPONSE.json [--allow-outside-validated-range]
  SCRIPT --serve [--allow-outside-validated-range]   (JSON Lines: one request per stdin line, one response per stdout
                                                     line, until end of input)
and applies the protocol before evaluate_point is called: a malformed request (invalid-request), another provider id
or version, a wanted item other than lis/components (unsupported-want), components from a non-decomposable provider,
an undeclared observable or axis, and points outside the declared domain (out-of-domain, unless
--allow-outside-validated-range; the result is then labelled outside-validated-range) are refused without
evaluating. An exception in evaluate_point fails that point with reason provider-error and the message (R4); nothing
falls back silently. While evaluate_point runs, its prints go to stderr, so --serve's stdout carries only responses.
Exit codes (single shot, core/status.py): 0 every point ok; 1 the request was refused or every point failed; 3 some
points failed (incomplete); 2 the request file is unreadable or the response cannot be written. In each case but the
last a response file is written. --serve exits 0 at end of input.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from core.provider.hashing import point_hash
from core.provider.protocol import (
    OUTSIDE_LABEL,
    OUTSIDE_OPTION,
    PROTOCOL,
    check_request,
    failed_response,
    failed_result,
    point_refusal,
    request_refusal,
    response_status,
)
from core.status import exit_code


def respond(request, declaration: dict, evaluate_point, allow_outside: bool = False) -> dict:
    """The response of one provider (its declaration with 'version') to one request."""
    problems = check_request(request)
    if problems:
        return failed_response(request, "invalid-request", "; ".join(problems))
    if request["provider"] != declaration["id"]:
        return failed_response(request, "invalid-request",
                               f"this entrypoint is provider {declaration['id']!r}, not {request['provider']!r}")
    if request["provider_version"] != declaration["version"]:
        return failed_response(request, "provider-version-mismatch",
                               f"this entrypoint is version {declaration['version']!r}, the request names "
                               f"{request['provider_version']!r}")
    reason, detail, bins_outside = request_refusal(request, declaration, allow_outside)
    if reason:
        return failed_response(request, reason, detail)
    want = set(request["want"])
    results = []
    for index, point in enumerate(request["points"]):
        reason, detail, outside = point_refusal(point, declaration, allow_outside)
        if reason:
            results.append(failed_result(index, point, reason, detail))
            continue
        outside = outside or bins_outside
        started = time.perf_counter()
        try:
            with contextlib.redirect_stdout(sys.stderr):
                value = evaluate_point(request, point, {"want": want, "outside": outside})
        except Exception as exc:  # noqa: BLE001 - every provider failure is reported, never swallowed (R4)
            results.append(failed_result(index, point, "provider-error", f"{type(exc).__name__}: {exc}"))
            continue
        labels = set(value.get("labels") or ())
        if outside:
            labels.add(OUTSIDE_LABEL)
        res = {"point_index": index, "point": dict(point), "status": "ok", "labels": sorted(labels)}
        if "lis" in want:
            res["predictions"] = value.get("predictions")
        if "components" in want:
            res["components"] = value.get("components")
        res["evaluation"] = {
            "computational_run_ref": value.get("computational_run_ref"),
            "input_hash": point_hash(request.get("transport"), request["provider"], request["provider_version"], point),
            "elapsed_s": round(time.perf_counter() - started, 6),
            "numerical_tolerance": value.get("numerical_tolerance"),
        }
        results.append(res)
    return {"protocol": PROTOCOL, "provider": request["provider"], "provider_version": request["provider_version"],
            "status": response_status(results), "results": results}


def write_json_atomic(path: Path, doc) -> None:
    path = Path(path)
    fd, partial = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, sort_keys=True)
            fh.write("\n")
        os.replace(partial, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(partial)
        raise


def serve(declaration: dict, evaluate_point, allow_outside: bool, stdin=None, stdout=None) -> int:
    """The JSON Lines loop: one response line per request line; a line that is not JSON gets an invalid-request
    response; blank lines are skipped; end of input ends the session."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except ValueError as exc:
            response = failed_response(None, "invalid-request", f"not JSON: {exc}")
        else:
            response = respond(request, declaration, evaluate_point, allow_outside)
        stdout.write(json.dumps(response, sort_keys=True) + "\n")
        stdout.flush()
    return 0


def provider_main(declaration: dict, evaluate_point, argv=None, description: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=description or f"cr-provider/1 entrypoint of provider "
                                     f"{declaration['id']} (version {declaration['version']})")
    parser.add_argument("--request", type=Path, help="request file (with --response)")
    parser.add_argument("--response", type=Path, help="response file to write (with --request)")
    parser.add_argument("--serve", action="store_true", help="JSON Lines session on stdin/stdout")
    parser.add_argument(OUTSIDE_OPTION, action="store_true", dest="allow_outside",
                        help="evaluate points outside the declared domain; their results are labelled "
                             f"{OUTSIDE_LABEL}")
    args = parser.parse_args(argv)
    if args.serve:
        if args.request or args.response:
            parser.error("--serve takes no --request or --response")
        return serve(declaration, evaluate_point, args.allow_outside)
    if not (args.request and args.response):
        parser.error("give --request and --response, or --serve")
    try:
        request = json.loads(args.request.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        response, code = failed_response(None, "invalid-request", f"cannot read the request: {exc}"), 2
    else:
        response = respond(request, declaration, evaluate_point, args.allow_outside)
        code = exit_code(response["status"])
    try:
        write_json_atomic(args.response, response)
    except OSError as exc:
        print(json.dumps({"status": "rejected", "error": f"cannot write the response: {exc}"}))
        return 2
    print(json.dumps({"status": response["status"], "response": str(args.response)}))
    return code
