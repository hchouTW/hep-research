#!/usr/bin/env python3
"""The caller side of cr-provider/1: evaluate a request through a registered provider, as a subprocess.

    from core.provider.runner import ProviderRunner
    with ProviderRunner(registry_path, cache_dir=out / "cache", session="serve") as runner:
        response = runner.evaluate(request)

Order of the checks (each refusal is a failed response or result with its reason, never a silent fallback, R4):
1. the request's structure (invalid-request); 2. the provider is in the registry the caller passed in
(unregistered-provider: nothing runs) and the request names its registered version (provider-version-mismatch);
3. wanted items, decomposability, observables, axes and bin ranges (request_refusal); 4. each point against the declared
domain: out-of-domain is refused unless allow_outside, then the result is labelled outside-validated-range;
5. the cache: a point whose result is cached under the caller-given cache folder, keyed by the point hash
(core.provider.hashing.point_hash, which covers the transport block) and the hash of the requested observables, wanted
items, seed and theory_spec_ref, is answered from the cache without calling the provider (only for deterministic
providers or a fixed seed; only ok results are stored; a request with a theory_spec_ref but no transport block is never
cached, because nothing in it identifies the theory-spec's content); 6. the remaining points go to the provider in one batch: single-shot ('ENTRY --request R --response S' in a
fresh temporary folder) or one long-lived '--serve' session; 7. the provider's response is checked against the
protocol (invalid-response), a crash, a missing response or an unexpected exit code fails every point it was sent
(provider-failed, with the exit code and the end of stderr), a timeout gives provider-timeout. A user-supplied
provider's results carry the label user-supplied. `stats` counts provider calls, points sent and cache hits.

Command line (one request, or a JSON Lines session through one provider --serve session):
  python3 core/provider/runner.py --provider-registry REGISTRY.json --request R.json --response S.json
      [--cache-dir DIR] [--allow-outside-validated-range] [--timeout SECONDS]
  python3 core/provider/runner.py --provider-registry REGISTRY.json --serve [...]
Output (single shot): one JSON object on stdout (status, response, provider_calls, points_sent, cache_hits). Exit 0
ok, 1 failed, 3 incomplete (core/status.py), 2 unusable registry, request file or response path.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import selectors
import subprocess
import sys
import tempfile
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.provider.entrypoint import write_json_atomic  # noqa: E402
from core.provider.hashing import canonical_sha256, point_hash  # noqa: E402
from core.provider.protocol import (  # noqa: E402
    OUTSIDE_LABEL,
    OUTSIDE_OPTION,
    USER_LABEL,
    check_request,
    check_response,
    failed_response,
    failed_result,
    point_refusal,
    request_refusal,
    response_status,
)
from core.provider.registry import RegistryEntry, RegistryError, load_registry, parse_registry  # noqa: E402
from core.status import exit_code  # noqa: E402

DEFAULT_TIMEOUT_S = 3600.0
STDERR_TAIL = 2000
RESPONDED_EXITS = (0, 1, 3)  # exits after which a provider has written a response (core/provider/entrypoint.py)


class ProviderCallError(RuntimeError):
    def __init__(self, reason: str, detail: str):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


def _tail(text: str) -> str:
    text = (text or "").strip()
    return text[-STDERR_TAIL:] if text else "(no stderr)"


def _child_env() -> dict:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


class ServeSession:
    """One provider '--serve' subprocess; send() writes one request line and reads one response line."""

    def __init__(self, entry: RegistryEntry, allow_outside: bool, timeout_s: float, python: str):
        self.timeout_s = timeout_s
        self._workdir = tempfile.TemporaryDirectory(prefix="cr-provider-serve-")
        self._stderr = open(Path(self._workdir.name) / "stderr.txt", "w+", encoding="utf-8")  # noqa: SIM115
        argv = [python, str(entry.entrypoint), "--serve"] + ([OUTSIDE_OPTION] if allow_outside else [])
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
                                     text=True, encoding="utf-8", cwd=self._workdir.name, env=_child_env())
        if self.proc.stdin is None or self.proc.stdout is None:  # pragma: no cover - PIPE always gives both
            raise RuntimeError("the --serve session has no pipes")
        self._to_provider, self._from_provider = self.proc.stdin, self.proc.stdout

    def _stderr_text(self) -> str:
        self._stderr.flush()
        self._stderr.seek(0)
        return self._stderr.read()

    def send(self, request: dict) -> dict:
        if self.proc.poll() is not None:
            raise ProviderCallError("provider-failed", f"the --serve session ended (exit {self.proc.returncode}): "
                                                       f"{_tail(self._stderr_text())}")
        try:
            self._to_provider.write(json.dumps(request, sort_keys=True) + "\n")
            self._to_provider.flush()
        except OSError as exc:
            raise ProviderCallError("provider-failed", f"cannot write to the --serve session: {exc}; "
                                                       f"{_tail(self._stderr_text())}") from None
        with selectors.DefaultSelector() as sel:
            sel.register(self._from_provider, selectors.EVENT_READ)
            if not sel.select(self.timeout_s):
                self.close()
                raise ProviderCallError("provider-timeout", f"no response within {self.timeout_s:g} s")
        line = self._from_provider.readline()
        if not line:
            code = self.proc.wait(timeout=30)
            raise ProviderCallError("provider-failed", f"the --serve session ended without a response (exit {code}): "
                                                       f"{_tail(self._stderr_text())}")
        try:
            return json.loads(line)
        except ValueError as exc:
            raise ProviderCallError("invalid-response", f"the response line is not JSON: {exc}") from None

    def close(self) -> None:
        if self.proc.poll() is None:
            with contextlib.suppress(OSError):
                self._to_provider.close()
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        for stream in (self._to_provider, self._from_provider):
            with contextlib.suppress(OSError, ValueError):
                stream.close()
        self._stderr.close()
        self._workdir.cleanup()


def call_single_shot(entry: RegistryEntry, request: dict, allow_outside: bool, timeout_s: float, python: str) -> dict:
    """One 'ENTRY --request R --response S' call in a fresh temporary folder; the response document."""
    with tempfile.TemporaryDirectory(prefix="cr-provider-call-") as work:
        req, resp = Path(work) / "request.json", Path(work) / "response.json"
        req.write_text(json.dumps(request, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        argv = [python, str(entry.entrypoint), "--request", str(req), "--response", str(resp)]
        try:
            proc = subprocess.run(argv + ([OUTSIDE_OPTION] if allow_outside else []), capture_output=True, text=True,
                                  timeout=timeout_s, cwd=work, env=_child_env())
        except subprocess.TimeoutExpired:
            raise ProviderCallError("provider-timeout", f"no response within {timeout_s:g} s") from None
        except OSError as exc:
            raise ProviderCallError("provider-failed", f"cannot start the provider: {exc}") from None
        if proc.returncode not in RESPONDED_EXITS or not resp.is_file():
            raise ProviderCallError("provider-failed", f"exit {proc.returncode}, "
                                    f"{'a' if resp.is_file() else 'no'} response file: {_tail(proc.stderr)}")
        try:
            return json.loads(resp.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise ProviderCallError("invalid-response", f"the response file is not JSON: {exc}") from None


class ProviderRunner:
    """Evaluate requests through the providers of one registry (a path or a registry document)."""

    def __init__(self, registry, *, cache_dir=None, allow_outside: bool = False, session: str = "single",
                 timeout_s: float = DEFAULT_TIMEOUT_S, python: str | None = None):
        if session not in ("single", "serve"):
            raise ValueError("session is 'single' or 'serve'")
        self.entries = parse_registry(registry) if isinstance(registry, dict) else load_registry(registry)
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.allow_outside = bool(allow_outside)
        self.session = session
        self.timeout_s = float(timeout_s)
        self.python = python or sys.executable
        self.stats = {"provider_calls": 0, "points_sent": 0, "cache_hits": 0}
        self._sessions: dict[str, ServeSession] = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self) -> None:
        for sess in self._sessions.values():
            sess.close()
        self._sessions.clear()

    # ------------------------------------------------------------------ cache
    def _cache_path(self, request: dict, point: dict, entry: RegistryEntry) -> Path | None:
        if self.cache_dir is None or not (entry.declaration["deterministic"] or request.get("seed") is not None):
            return None
        if request.get("transport") is None and request.get("theory_spec_ref"):
            return None  # the theory-spec's content is not in the request: no key can identify it, so no cache
        key = point_hash(request.get("transport"), request["provider"], request["provider_version"], point)
        shape = canonical_sha256({"observables": request["observables"], "want": sorted(request["want"]),
                                  "seed": request.get("seed"), "allow_outside": self.allow_outside,
                                  "theory_spec_ref": request.get("theory_spec_ref")})
        return self.cache_dir / key / f"{shape}.json"

    @staticmethod
    def _cache_read(path: Path | None) -> dict | None:
        if path is None or not path.is_file():
            return None
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None  # an unreadable cache entry is a miss; it is rewritten after the call
        return doc.get("result") if isinstance(doc, dict) and isinstance(doc.get("result"), dict) else None

    @staticmethod
    def _cache_write(path: Path | None, result: dict) -> None:
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(path, {"cache": "cr-provider/1", "result": result})

    # ------------------------------------------------------------------ calls
    def _call(self, entry: RegistryEntry, request: dict) -> dict:
        self.stats["provider_calls"] += 1
        self.stats["points_sent"] += len(request["points"])
        if self.session == "single":
            return call_single_shot(entry, request, self.allow_outside, self.timeout_s, self.python)
        sess = self._sessions.get(entry.provider_id)
        if sess is None or sess.proc.poll() is not None:
            if sess is not None:
                sess.close()
            sess = self._sessions[entry.provider_id] = ServeSession(entry, self.allow_outside, self.timeout_s,
                                                                    self.python)
        try:
            return sess.send(request)
        except ProviderCallError:
            sess.close()
            self._sessions.pop(entry.provider_id, None)
            raise

    def evaluate(self, request) -> dict:
        problems = check_request(request)
        if problems:
            return failed_response(request, "invalid-request", "; ".join(problems))
        entry = self.entries.get(request["provider"])
        if entry is None:
            return failed_response(request, "unregistered-provider",
                                   f"provider {request['provider']!r} is not in the registry the caller passed in "
                                   f"(registered: {sorted(self.entries)})")
        if request["provider_version"] != entry.version:
            return failed_response(request, "provider-version-mismatch",
                                   f"the registry lists {entry.provider_id} version {entry.version!r}, the request "
                                   f"names {request['provider_version']!r}")
        reason, detail, bins_outside = request_refusal(request, entry.declaration, self.allow_outside)
        if reason:
            return failed_response(request, reason, detail)
        extra_labels = {USER_LABEL} if entry.user_supplied else set()
        results: list[dict | None] = [None] * len(request["points"])
        pending: list[tuple[int, Path | None, bool]] = []
        for index, point in enumerate(request["points"]):
            reason, detail, outside = point_refusal(point, entry.declaration, self.allow_outside)
            if reason:
                results[index] = failed_result(index, point, reason, detail, extra_labels)
                continue
            cache_path = self._cache_path(request, point, entry)
            cached = self._cache_read(cache_path)
            if cached is not None:
                self.stats["cache_hits"] += 1
                results[index] = dict(cached, point_index=index, point=dict(point))
            else:
                pending.append((index, cache_path, outside or bins_outside))
        if pending:
            batch = dict(request, points=[request["points"][i] for i, _, _ in pending])
            try:
                answer = self._call(entry, batch)
                problems = check_response(answer, batch)
                if problems:
                    raise ProviderCallError("invalid-response", "; ".join(problems[:5]))
                if not answer["results"]:  # the provider refused the whole batch
                    raise ProviderCallError(answer.get("reason") or "invalid-response",
                                            answer.get("detail") or "the provider refused the request")
            except ProviderCallError as exc:
                for index, _, _ in pending:
                    results[index] = failed_result(index, request["points"][index], exc.reason, exc.detail,
                                                   extra_labels)
            else:
                for (index, cache_path, outside), res in zip(pending, answer["results"]):
                    res = dict(res, point_index=index)
                    if res["status"] == "ok":
                        if outside and OUTSIDE_LABEL not in res["labels"]:
                            res["labels"] = sorted(set(res["labels"]) | {OUTSIDE_LABEL})
                        self._cache_write(cache_path, res)
                    results[index] = res
        labelled = []
        for res in results:
            if extra_labels and res is not None:
                res = dict(res, labels=sorted(set(res["labels"]) | extra_labels))
            labelled.append(res)
        return {"protocol": request["protocol"], "provider": entry.provider_id, "provider_version": entry.version,
                "status": response_status(labelled), "results": labelled}


def _emit(doc: dict) -> None:
    print(json.dumps(doc, indent=1, sort_keys=True))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     epilog="Exit 0 ok, 1 failed, 3 incomplete, 2 unusable input (core/status.py).")
    parser.add_argument("--provider-registry", type=Path, required=True,
                        help="registry file written by tools/provider_registry.py --write")
    parser.add_argument("--request", type=Path, help="request file (with --response)")
    parser.add_argument("--response", type=Path, help="response file to write (with --request)")
    parser.add_argument("--serve", action="store_true",
                        help="JSON Lines on stdin/stdout through one provider --serve session per provider")
    parser.add_argument("--cache-dir", type=Path, help="cache folder (outside the repository); no cache if omitted")
    parser.add_argument(OUTSIDE_OPTION, action="store_true", dest="allow_outside",
                        help=f"evaluate points outside the declared domain, labelled {OUTSIDE_LABEL}")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="seconds per provider call")
    args = parser.parse_args(argv)
    if args.serve == bool(args.request or args.response) or (not args.serve and not (args.request and args.response)):
        parser.error("give --request and --response, or --serve")
    try:
        runner = ProviderRunner(args.provider_registry, cache_dir=args.cache_dir, allow_outside=args.allow_outside,
                                session="serve" if args.serve else "single", timeout_s=args.timeout)
    except RegistryError as exc:
        _emit({"status": "rejected", "error": str(exc)})
        return 2
    with runner:
        if args.serve:
            for line in sys.stdin:
                if not line.strip():
                    continue
                try:
                    response = runner.evaluate(json.loads(line))
                except ValueError as exc:
                    response = failed_response(None, "invalid-request", f"not JSON: {exc}")
                sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
                sys.stdout.flush()
            return 0
        try:
            request = json.loads(args.request.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            _emit({"status": "rejected", "error": f"cannot read the request: {exc}"})
            return 2
        started = time.perf_counter()
        response = runner.evaluate(request)
        try:
            write_json_atomic(args.response, response)
        except OSError as exc:
            _emit({"status": "rejected", "error": f"cannot write the response: {exc}"})
            return 2
        _emit({"status": response["status"], "response": str(args.response), **runner.stats,
               "elapsed_s": round(time.perf_counter() - started, 3)})
        return exit_code(response["status"])


if __name__ == "__main__":
    sys.exit(main())
