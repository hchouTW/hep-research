#!/usr/bin/env python3
"""Project-level dependency validation: resolve an artifact's input refs inside a project root and check them.

The schema validator (contracts/validate.py) checks one artifact and never opens another file, so it trusts the
caller-supplied inputs[].status, sha256 and type. This layer resolves every ref (relative to --base, default the
project root) and checks, recursively through the sources' own inputs:
  - the ref stays inside the project root (absolute paths outside it, '..' escapes and symlinks out are refused and
    never opened) and the file exists and is a JSON artifact;
  - the declared artifact_type, artifact_id and version (the source's contract_version) match the source;
  - sha256 is 64 hex digits and equals the file's digest (no hash: unresolved, a substitution cannot be detected);
  - the sticky statuses the source really carries are declared on the input and carried by the consumer.
An input with "external": true, or a ref with a scheme ('hepdata:...', 'https://...'), is not materialized in the
project: it is reported 'unresolved', never read. Any error or unresolved finding sets formal_use_allowed false: the
artifact may be explored, but not used for a formal result, until its dependencies resolve.

Usage: python3 contracts/dependencies.py ARTIFACT.json --root PROJECT_ROOT [--base DIR]
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

from contracts.validate import STICKY_STATUSES  # noqa: E402

SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_DEPTH = 32


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


class _Checker:
    def __init__(self, root: Path, base: Path):
        self.root, self.base = root, base
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
            elif HEX64.match(str(sha)) and sha != digest:
                self.add("error", where, "dependency.hash_mismatch", f"{ref!r} has sha256 {digest}, the input declares {sha}")
            try:
                sdoc = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                self.add("error", where, "dependency.unreadable", f"{ref!r} is not a JSON artifact: {exc}")
                continue
            if not isinstance(sdoc, dict):
                self.add("error", where, "dependency.unreadable", f"{ref!r} is not a JSON object")
                continue
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
            self.checked.append(str(src.relative_to(self.root)))
            if src in trail:
                self.add("error", where, "dependency.cycle", f"{ref!r} is already in the chain {[str(t.relative_to(self.root)) for t in trail]}")
            elif len(trail) >= MAX_DEPTH:
                self.add("error", where, "dependency.too_deep", f"dependency chain deeper than {MAX_DEPTH}")
            else:
                self.artifact(src, sdoc, trail + (src,))


def validate_dependencies(artifact_path, project_root, base=None) -> dict:
    root = Path(project_root).resolve()
    path = Path(artifact_path)
    path = (path if path.is_absolute() else Path.cwd() / path).resolve()
    chk = _Checker(root, Path(base).resolve() if base else root)
    if not root.is_dir():
        chk.add("error", "$", "dependency.bad_root", f"project root {project_root} is not a directory")
    elif not _inside(path, root):
        chk.add("error", "$", "dependency.outside_root", f"{artifact_path} lies outside the project root; it is not read")
    elif chk.base != root and not _inside(chk.base, root):
        chk.add("error", "$", "dependency.outside_root", "the ref base directory lies outside the project root")
    else:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            chk.add("error", "$", "dependency.unreadable", f"cannot read {artifact_path}: {exc}")
        else:
            if isinstance(doc, dict):
                chk.artifact(path, doc, (path,))
            else:
                chk.add("error", "$", "dependency.unreadable", f"{artifact_path} is not a JSON object")
    sev = {f["severity"] for f in chk.findings}
    status = "error" if "error" in sev else ("unresolved" if "unresolved" in sev else "ok")
    return {"status": status, "formal_use_allowed": status == "ok" and not chk.failed_upstream,
            "failed_upstream": chk.failed_upstream, "checked": chk.checked, "findings": chk.findings,
            "note": "dependency consistency only: a resolved chain says nothing about the physical validity of any artifact"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("artifact", type=Path)
    ap.add_argument("--root", type=Path, required=True, help="project root: no file outside it is read")
    ap.add_argument("--base", type=Path, help="directory that refs are relative to (default: the project root)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    rep = validate_dependencies(args.artifact, args.root, args.base)
    print(json.dumps(rep, indent=1))
    if any(f["code"] in ("dependency.bad_root",) for f in rep["findings"]) or \
            (rep["findings"] and rep["findings"][0]["path"] == "$" and rep["findings"][0]["code"] == "dependency.unreadable"):
        return 2
    return {"ok": 0, "error": 1, "unresolved": 3}[rep["status"]]


if __name__ == "__main__":
    sys.exit(main())
