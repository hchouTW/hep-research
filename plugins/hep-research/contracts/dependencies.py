#!/usr/bin/env python3
"""Project-level dependency validation: resolve an artifact's input refs inside a project root and check them.

The schema validator (contracts/validate.py) checks one artifact and never opens another file, so it trusts the
caller-supplied inputs[].status, sha256 and type. This layer resolves every ref (relative to --base, default the
project root) and checks, recursively through the sources' own inputs:
  - the ref stays inside the project root (absolute paths outside it, '..' escapes and symlinks out are refused and
    never opened) and the file exists and is a JSON artifact;
  - the declared artifact_type, artifact_id and version (the source's contract_version) match the source;
  - sha256 is 64 hex digits and equals the file's digest (no hash: unresolved, a substitution cannot be detected);
    an input marked "binding": "parameters" (contracts 3.11.0, TRC-06) still needs its hash, its file and a valid
    source, but a changed file is only a warning: the consumer is bound by the digest of the parameters it read,
    which contracts/design.py compares;
  - the sticky statuses the source really carries are declared on the input and carried by the consumer;
  - the source validates: its errors are dependency.source_invalid, and its unresolved findings (a domain-shift check
    that failed, a split check that was not run, ...) are dependency.source_unresolved, so a chain is never more
    established than its weakest source.
An input with "external": true, or a ref with a scheme ('hepdata:...', 'https://...'), is not materialized in the
project: it is reported 'unresolved', never read. Any error or unresolved finding sets dependency_consistency_ok
false. The report is advisory: it never authorizes formal use. formal_use_allowed is always false, because formal use
is decided only by a trusted gate outside the agent-run code (an artifact with no inputs, or '{}', is consistent but
is not thereby allowed).

Every source is also validated as a contract artifact (contracts/validate.py). Protected mode (the project root
declares agent_policy, or --protected; core.protected.guard) first checks the protected inputs and refuses before
reading any source when they cannot be established; inside it the authoritative revocation log is always applied and
the stricter version policy holds. --strict-versions applies only that version policy (a newer minor contract is an
error) to every source; a retired or unknown skill name is an error either way (contracts.skill_names).

Revocations: --revocations names the hash-chained revocation log (contracts/revocation.py), which needs --revocation-head
and --revocation-source; it is verified before any lookup (an empty, cut, edited or stale log, or one whose head does
not match, is an error and nothing is read as 'not revoked'). With --protected the log and head must also be files the
running account neither owns nor can write or replace. The legacy format (JSON Lines {"subject_sha256", "reason"}
without a genesis record) is read with a warning outside protected mode and refused with --protected; an empty legacy
file is an error.

Usage: python3 contracts/dependencies.py ARTIFACT.json --root PROJECT_ROOT [--base DIR] [--revocations LOG
           --revocation-head HEAD --revocation-source SOURCE [--max-status-age S] [--now T]] [--protected]
           [--strict-versions]
Exit codes: 0 ok, 1 errors, 3 unresolved only, 2 unreadable input or bad usage. Output: JSON report on stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts import revocation as rv  # noqa: E402
from contracts.validate import STICKY_STATUSES, geant4_configuration, validate_artifact  # noqa: E402
from core.protected.guard import ProtectedUseRefused, guard, protected_main  # noqa: E402
from contracts import KNOWN_CAPABILITIES  # noqa: E402

SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_DEPTH = 32


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def load_revocations(path) -> tuple[dict, list[str]]:
    """{subject_sha256: event} from a legacy JSON Lines file, plus the problems found (each problem is reported as an
    error). An empty file is a problem: it cannot be told apart from a truncated one."""
    revoked: dict[str, dict] = {}
    problems: list = []
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return {}, [f"cannot read revocations {path}: {exc}"]
    if not any(line.strip() for line in lines):
        return {}, [f"{path} is empty: an empty file is not 'nothing revoked'"]
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except ValueError as exc:
            problems.append(f"line {n}: not JSON ({exc})")
            continue
        dig = ev.get("subject_sha256") if isinstance(ev, dict) else None
        if not (isinstance(dig, str) and HEX64.match(dig)) or not str(ev.get("reason") or "").strip():
            problems.append(f"line {n}: needs subject_sha256 (64 lower-case hex) and a reason")
            continue
        revoked.setdefault(dig, ev)
    return revoked, problems


class _Checker:
    def __init__(self, root: Path, base: Path, revoked: dict | None = None, protected: bool = False, vocab=None,
                 context=None, strict_versions: bool = False):
        self.root, self.base, self.protected, self.vocab, self.context = root, base, protected, vocab, context
        self.strict_versions = strict_versions
        self.revoked = revoked or {}
        self.findings: list[dict] = []
        self.checked: list[str] = []
        self.failed_upstream = False

    def add(self, severity, where, code, message):
        self.findings.append({"severity": severity, "path": where, "code": code, "message": message})

    def resolve(self, ref: str, where: str) -> Path | None:
        """The resolved path of a local ref, or None (with a finding) when it is not inside the root."""
        raw = Path(ref)
        cand = raw if raw.is_absolute() else self.base / raw
        # resolve() follows symlinks, so a link pointing out of the root is caught as well
        res = cand.resolve()
        if not _inside(res, self.root):
            self.add("error", where, "dependency.outside_root", f"ref {ref!r} resolves outside the project root; it is not read")
            return None
        return res

    def artifact(self, path: Path, doc: dict, trail: tuple):
        consumer_status = set(doc.get("status", []))
        for i, inp in enumerate(doc.get("inputs", []) or []):
            where = f"{path.relative_to(self.root)}:$.inputs[{i}]"
            if not isinstance(inp, dict) or not isinstance(inp.get("ref"), str):
                self.add("error", where, "dependency.bad_input", "an input needs a string ref")
                continue
            ref = inp["ref"]
            if inp.get("external") or (SCHEME.match(ref) and not Path(ref).is_absolute() and not re.match(r"^[A-Za-z]:[\\/]", ref)):
                self.add("unresolved", where, "dependency.external_unresolved",
                         f"{ref!r} is not materialized in the project; its content, hash and statuses cannot be checked")
                continue
            sha = inp.get("sha256")
            if sha is not None and not (isinstance(sha, str) and HEX64.match(sha)):
                self.add("error", where, "dependency.bad_hash_format", f"sha256 {sha!r} is not 64 lower-case hex digits")
            src = self.resolve(ref, where)
            if src is None:
                continue
            if not src.is_file():
                self.add("error", where, "dependency.missing", f"{ref!r} does not exist in the project")
                continue
            data = src.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if sha is None:
                self.add("unresolved", where, "dependency.no_hash", f"{ref!r} has no sha256: a substituted source cannot be detected")
            elif HEX64.match(str(sha)) and sha != digest and inp.get("binding") == "parameters":
                # TRC-06: bound by the digest of the parameters read; contracts/design.py compares that digest
                self.add("warning", where, "dependency.parameters_bound_file_changed",
                         f"{ref!r} changed (sha256 {digest}); the input is bound by its parameters, not the whole file")
            elif HEX64.match(str(sha)) and sha != digest:
                self.add("error", where, "dependency.hash_mismatch", f"{ref!r} has sha256 {digest}, the input declares {sha}")
            ev = self.revoked.get(digest) or self.revoked.get("ref:" + src.relative_to(self.root).as_posix())
            if ev is not None:
                self.add("error", where, "dependency.revoked",
                         f"{ref!r} (sha256 {digest[:12]}...) was revoked {ev.get('issued', '')}: {ev.get('reason')}")
            try:
                sdoc = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                self.add("error", where, "dependency.unreadable", f"{ref!r} is not a JSON artifact: {exc}")
                continue
            if not isinstance(sdoc, dict):
                self.add("error", where, "dependency.unreadable", f"{ref!r} is not a JSON object")
                continue
            # every source is itself a contract artifact: an invalid one, an unknown type or required capability, or
            # a newer contract version this reader cannot judge is not a dependency it can vouch for (K02, F08)
            srep = validate_artifact(sdoc, self.vocab, protected=self.protected, context=self.context,
                                     strict_versions=self.strict_versions)
            bad = sorted({f.code for f in srep.errors})
            if bad:
                self.add("error", where, "dependency.source_invalid", f"{ref!r} fails contract validation: {', '.join(bad)}")
            elif any(f.severity == "unresolved" for f in srep.findings):
                open_codes = sorted({f.code for f in srep.findings if f.severity == "unresolved"})
                self.add("unresolved", where, "dependency.source_unresolved",
                         f"{ref!r} is not established: {', '.join(open_codes)}")
            if not bad and any(f.code == "contract.newer_minor" for f in srep.findings):
                self.add("warning", where, "dependency.source_newer_minor",
                         f"{ref!r} uses contract {sdoc.get('contract_version')}, newer than this reader")
            for key, skey, code in (("artifact_type", "artifact_type", "dependency.type_mismatch"),
                                    ("artifact_id", "artifact_id", "dependency.id_mismatch"),
                                    ("version", "contract_version", "dependency.version_mismatch")):
                if key in inp and inp[key] != sdoc.get(skey):
                    self.add("error", where, code, f"input declares {key} {inp[key]!r}; {ref!r} has {sdoc.get(skey)!r}")
            actual = {s for s in sdoc.get("status", []) if s in STICKY_STATUSES}
            declared = set(inp.get("status", []))
            for s in sorted(actual - declared):
                self.add("error", where, "dependency.status_undeclared", f"{ref!r} carries '{s}' but the input does not declare it")
            for s in sorted(actual - consumer_status):
                self.add("error", where, "dependency.status_not_propagated",
                         f"{ref!r} carries '{s}'; the consuming artifact must carry it too")
            if "failed" in actual:
                self.failed_upstream = True
            self.simulated(doc, sdoc, ref, where)
            self.checked.append(str(src.relative_to(self.root)))
            if src in trail:
                self.add("error", where, "dependency.cycle", f"{ref!r} is already in the chain {[str(t.relative_to(self.root)) for t in trail]}")
            elif len(trail) >= MAX_DEPTH:
                self.add("error", where, "dependency.too_deep", f"dependency chain deeper than {MAX_DEPTH}")
            else:
                self.artifact(src, sdoc, trail + (src,))
        self.evidence(path, doc, trail)
        self.configuration(path, doc)

    def simulated(self, doc: dict, sdoc: dict, ref: str, where: str):
        """3.2.0: the inputs of a simulated dataset-record are Geant4 run records (extension.simulation) or a study
        record (extension.study); a communication that uses a simulated table is reminded of the 'Simulation' label."""
        if _dataset_status(doc) == "simulated":
            sext = sdoc.get("extension") or {}
            if sdoc.get("artifact_type") != "computational-run" or not ({"simulation", "study"} & set(sext)):
                self.add("error", where, "dataset.simulated_source",
                         f"{ref!r} is not a simulation run record or study record (computational-run with "
                         "extension.simulation or extension.study)")
        if doc.get("artifact_type") == "communication" and _dataset_status(sdoc) == "simulated":
            self.add("warning", where, "communication.simulated_source",
                     f"{ref!r} is a simulated table: figures and tables from it are labelled 'Simulation' (hep-authoring)")

    def evidence(self, path: Path, doc: dict, trail: tuple):
        """3.1.0: extension.evidence_records, run records the artifact relies on by hash without inheriting their
        labels. Each must resolve inside the root, match its sha256, validate, and be a successful computational-run
        (exit_status 0, no 'failed', output hashes recorded)."""
        records = (doc.get("extension") or {}).get("evidence_records") or []
        for i, rec in enumerate(records if isinstance(records, list) else []):
            where = f"{path.relative_to(self.root)}:$.extension.evidence_records[{i}]"
            if not isinstance(rec, dict) or not isinstance(rec.get("ref"), str):
                self.add("error", where, "evidence.bad_record", "an evidence record needs a string ref")
                continue
            src = self.resolve(rec["ref"], where)
            if src is None:
                continue
            if not src.is_file():
                self.add("error", where, "evidence.missing", f"{rec['ref']!r} does not exist in the project")
                continue
            data = src.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if rec.get("sha256") != digest:
                self.add("error", where, "evidence.hash_mismatch",
                         f"{rec['ref']!r} has sha256 {digest}, the record declares {rec.get('sha256')}")
            try:
                sdoc = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                self.add("error", where, "evidence.unreadable", f"{rec['ref']!r} is not a JSON artifact: {exc}")
                continue
            srep = validate_artifact(sdoc, self.vocab, protected=self.protected, context=self.context,
                                     strict_versions=self.strict_versions)
            bad = sorted({f.code for f in srep.errors})
            if bad:
                self.add("error", where, "evidence.source_invalid", f"{rec['ref']!r} fails contract validation: {', '.join(bad)}")
            if sdoc.get("artifact_type") != "computational-run" or sdoc.get("artifact_id") != rec.get("artifact_id"):
                self.add("error", where, "evidence.type_or_id_mismatch",
                         f"{rec['ref']!r} is {sdoc.get('artifact_type')} {sdoc.get('artifact_id')!r}, the record "
                         f"declares computational-run {rec.get('artifact_id')!r}")
            sext = sdoc.get("extension") or {}
            if sext.get("exit_status") != 0 or "failed" in (sdoc.get("status") or []):
                self.add("error", where, "evidence.run_failed", f"{rec['ref']!r} did not succeed (exit status or 'failed')")
            hashes = sext.get("output_hashes")
            if not isinstance(hashes, dict) or not hashes or not all(isinstance(v, str) and HEX64.match(v)
                                                                      for v in hashes.values()):
                self.add("error", where, "evidence.no_output_hashes", f"{rec['ref']!r} records no output hashes")
            self.checked.append(str(src.relative_to(self.root)))
            if src not in trail and len(trail) < MAX_DEPTH:
                self.artifact(src, sdoc, trail + (src,))


    def configuration(self, path: Path, doc: dict):
        """CV-A1 (A1.3): a benchmark of a study record that states its configuration is re-derived from the run
        record named by its configuration_basis, which must be one of the record's evidence records or inputs (same id
        and sha256): configuration, hash_scheme and target hash must equal what contracts.validate.geant4_configuration
        gives under the benchmark's hash_scheme (spec-v1 for A1 records, tree-v1 from the effective config for records
        from geant4 adapter 0.2.0, A2.6)."""
        ext = doc.get("extension") or {}
        study = ext.get("study")
        records = [r for key in (ext.get("evidence_records"), doc.get("inputs")) if isinstance(key, list) for r in key]
        if not isinstance(study, dict):
            return
        for i, b in enumerate(study.get("benchmarks") or []):
            basis = b.get("configuration_basis") if isinstance(b, dict) else None
            if not isinstance(basis, dict):
                continue
            where = f"{path.relative_to(self.root)}:$.extension.study.benchmarks[{i}].configuration_basis"
            rec = next((r for r in records if isinstance(r, dict) and r.get("artifact_id") == basis.get("artifact_id")
                        and r.get("sha256") == basis.get("sha256")), None)
            if rec is None:
                self.add("error", where, "geant4.configuration_unlinked",
                         f"the run record {basis.get('artifact_id')!r} ({basis.get('sha256')}) the configuration is "
                         "derived from is not an evidence record or input of this study")
                continue
            src = self.resolve(rec.get("ref", ""), where)
            if src is None or not src.is_file():
                continue  # reported by evidence()
            try:
                sdoc = json.loads(src.read_text(encoding="utf-8"))
                conf = geant4_configuration((sdoc.get("extension") or {}).get("simulation") or {}, b.get("target_slabs"),
                                            b.get("hash_scheme") or "spec-v1")
            except (ValueError, OSError) as exc:
                self.add("error", where, "geant4.configuration_mismatch", f"cannot re-derive the configuration: {exc}")
                continue
            diff = [k for k in ("configuration", "hash_scheme", "target_geometry_sha256") if conf[k] != b.get(k)]
            if diff:
                self.add("error", where, "geant4.configuration_mismatch",
                         f"{b.get('benchmark')}: {', '.join(f'{k} {b.get(k)!r} (re-derived {conf[k]!r})' for k in diff)}")


def _dataset_status(doc: dict):
    """extension.status of a dataset-record (published, synthetic, simulated, ...), else None."""
    return (doc.get("extension") or {}).get("status") if doc.get("artifact_type") == "dataset-record" else None


def _event_keys(events) -> dict:
    """{sha256: event} for digest subjects and {"ref:<project-relative path>": event} for artifact or recipe subjects
    named by a path (relative to the project root); the first event per key wins."""
    out: dict = {}
    for ev in reversed(events):
        s = ev["subject"]
        if "sha256" in s:
            out.setdefault(s["sha256"], dict(ev, issued=ev["time"]))
        if "ref" in s and s["kind"] in ("artifact", "recipe"):
            out.setdefault("ref:" + Path(s["ref"]).as_posix(), dict(ev, issued=ev["time"]))
    return out


def _revocation_findings(revocations, head, source, max_age_s, now, protected: bool, account) -> tuple[dict, list[tuple]]:
    """({sha256: event}, [(severity, code, message)]) for the given revocation input; see the module docstring."""
    try:
        first = Path(revocations).read_bytes()[:65536]
    except OSError as exc:
        return {}, [("error", "dependency.revocations_unreadable", f"cannot read revocations: {exc.strerror}")]
    if rv.is_chained_log(first):
        st = rv.load(revocations, head, source=source, now=now, max_age_s=max_age_s, protected=protected,
                     account=account)
        if not st.ok:
            return {}, [("error", "dependency.revocations_unverified",
                         "the revocation log did not verify: " + ", ".join(sorted({f["code"] for f in st.findings})))]
        return _event_keys(st.events), []
    if protected:
        return {}, [("error", "dependency.revocations_legacy",
                     "protected use needs the hash-chained revocation log with its head; the legacy format is refused")]
    revoked, problems = load_revocations(revocations)
    out = [("warning", "dependency.revocations_legacy",
            "legacy revocation events: no chain or head, so a truncated or edited file is not detectable")]
    out += [("error", "dependency.revocations_unreadable", p) for p in problems]
    return revoked, out


def validate_dependencies(artifact_path, project_root, base=None, revocations=None, protected: bool = False, vocab=None,
                          *, revocation_head=None, revocation_source=None, max_status_age_s: int = rv.MAX_STATUS_AGE_S,
                          now=None, account=None, context=None, strict_versions: bool = False) -> dict:
    """See the module docstring. `vocab` (a contracts.vocab.Vocabulary, default the core vocabulary) lets sources that use
    a bound profile's namespaced terms validate; it is additive and changes nothing when omitted. `account`
    (core.protected.trusted_input.Account) replaces the running account in the protected source checks (tests)."""
    root = Path(project_root).resolve()
    path = Path(artifact_path)
    path = (path if path.is_absolute() else Path.cwd() / path).resolve()
    refusals: list = []
    ctx = None
    try:
        ctx = guard("contracts.dependencies.validate_dependencies", paths=[path, root], flag=protected, project=root,
                    context=context, capabilities=KNOWN_CAPABILITIES, now=now, account=account)
    except ProtectedUseRefused as exc:
        refusals = exc.refusals
    protected = protected or bool(refusals) or (ctx is not None and ctx.protected)
    revoked, rfindings = (_revocation_findings(revocations, revocation_head, revocation_source, max_status_age_s, now,
                                               protected, account) if revocations and not refusals else ({}, []))
    if ctx is not None and ctx.protected and ctx.revocations is not None:  # the authoritative log is always applied
        for key, ev in _event_keys(ctx.revocations.events).items():
            revoked.setdefault(key, ev)
    chk = _Checker(root, Path(base).resolve() if base else root, revoked, protected, vocab,
                   ctx if ctx is not None and ctx.protected else None, strict_versions)
    for severity, code, message in rfindings:
        chk.add(severity, "$revocations", code, message)
    for r in refusals:
        chk.add("error", r["path"], r["code"], r["message"])
    if refusals:  # protected use refused: no source is read
        return {"status": "error", "dependency_consistency_ok": False, "formal_use_allowed": False,
                "formal_use": "decided only by the trusted gate, never by this advisory check",
                "revocations_checked": False, "failed_upstream": False, "checked": [], "findings": chk.findings,
                "protected": True, "note": "protected use refused before any dependency was read"}
    if not root.is_dir():
        chk.add("error", "$", "dependency.bad_root", f"project root {project_root} is not a directory")
    elif not _inside(path, root):
        chk.add("error", "$", "dependency.outside_root", f"{artifact_path} lies outside the project root; it is not read")
    elif chk.base != root and not _inside(chk.base, root):
        chk.add("error", "$", "dependency.outside_root", "the ref base directory lies outside the project root")
    else:
        try:
            raw = path.read_bytes()  # read once: the hash and the parsed content come from the same bytes (K09)
            doc = json.loads(raw.decode("utf-8"))
        except (OSError, ValueError) as exc:
            chk.add("error", "$", "dependency.unreadable", f"cannot read {artifact_path}: {exc}")
        else:
            own = hashlib.sha256(raw).hexdigest()
            ev = chk.revoked.get(own) or chk.revoked.get("ref:" + path.relative_to(root).as_posix())
            if ev is not None:
                chk.add("error", "$", "dependency.revoked", f"this artifact was revoked: {ev.get('reason')}")
            if isinstance(doc, dict):
                chk.artifact(path, doc, (path,))
            else:
                chk.add("error", "$", "dependency.unreadable", f"{artifact_path} is not a JSON object")
    sev = {f["severity"] for f in chk.findings}
    status = "error" if "error" in sev else ("unresolved" if "unresolved" in sev else "ok")
    consistent = status == "ok" and not chk.failed_upstream
    return {"status": status, "dependency_consistency_ok": consistent,
            "formal_use_allowed": False, "formal_use": "decided only by the trusted gate, never by this advisory check",
            "revocations_checked": bool(revocations) or (ctx is not None and ctx.protected),
            "protected": protected,
            "failed_upstream": chk.failed_upstream, "checked": chk.checked, "findings": chk.findings,
            "note": "dependency consistency only: a resolved chain says nothing about the physical validity of any artifact"}


@protected_main("contracts.dependencies", keep_flag=True, capabilities=KNOWN_CAPABILITIES)
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("artifact", type=Path)
    ap.add_argument("--root", type=Path, required=True, help="project root: no file outside it is read")
    ap.add_argument("--base", type=Path, help="directory that refs are relative to (default: the project root)")
    ap.add_argument("--revocations", type=Path, help="the hash-chained revocation log (legacy JSON Lines: warning, "
                                                     "refused with --protected)")
    ap.add_argument("--revocation-head", dest="revocation_head", type=Path, help="the log's head (revocation_head.json)")
    ap.add_argument("--revocation-source", dest="revocation_source", help="the status source the head must name")
    ap.add_argument("--max-status-age", dest="max_status_age", type=int, default=rv.MAX_STATUS_AGE_S,
                    help=f"seconds; at most {rv.MAX_STATUS_AGE_S}")
    ap.add_argument("--now", help="evaluate at another time (tests, replay), YYYY-MM-DDTHH:MM:SSZ")
    ap.add_argument("--protected", action="store_true", help="protected mode (core/protected/guard.py): the project's "
                    "protected inputs must be established, the authoritative revocation log applies, and the stricter "
                    "version policy holds")
    ap.add_argument("--strict-versions", dest="strict_versions", action="store_true",
                    help="only the stricter version policy for every source (a newer minor contract is an error), "
                         "without protected mode")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    now = rv._ts(args.now) if args.now else None
    if args.now and now is None:
        print(json.dumps({"status": "unreadable", "error": "--now must be YYYY-MM-DDTHH:MM:SSZ"}))
        return 2
    rep = validate_dependencies(args.artifact, args.root, args.base, args.revocations, args.protected,
                                strict_versions=args.strict_versions,
                                revocation_head=args.revocation_head, revocation_source=args.revocation_source,
                                max_status_age_s=args.max_status_age, now=now)
    print(json.dumps(rep, indent=1))
    if any(f["code"] in ("dependency.bad_root",) for f in rep["findings"]) or \
            (rep["findings"] and rep["findings"][0]["path"] == "$" and rep["findings"][0]["code"] == "dependency.unreadable"):
        return 2
    return {"ok": 0, "error": 1, "unresolved": 3}[rep["status"]]


if __name__ == "__main__":
    sys.exit(main())
