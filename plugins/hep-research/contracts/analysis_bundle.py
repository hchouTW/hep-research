#!/usr/bin/env python3
"""Analysis-level bundle (task P5.2, C08, C15): freeze what a formal result of an analysis depends on into one digest
(contracts/schemas/analysis_bundle.json), and verify it later against the project.

freeze(root, analysis, items) reads each item {role, id, ref} under the project root (no '..', no link anywhere on the
path, regular files only), digests it (canonical JSON for .json, bytes otherwise), records the running plugin's code
identity, and returns the bundle with bundle_digest = canonical SHA-256 of every other field. Roles: exactly one
measurement-spec and one environment-lock, at least one recipe; semantics-table, calibration, tool-contract and review
items as the analysis has them. A ref listed twice is refused.

verify(bundle, root) re-digests every item and the bundle itself and reports each difference (changed, missing, link,
digest); with check_plugin it also compares the recorded plugin release with the running one. Nothing here approves a
use: an attestation binds the digest as its subject.bundle_sha256 and a formal-use permit as
subject.analysis_bundle_sha256, so a different digest leaves both without effect.

Usage: python3 contracts/analysis_bundle.py freeze --root DIR --analysis NAME --items ITEMS.json --out FILE
       python3 contracts/analysis_bundle.py verify BUNDLE --root DIR [--check-plugin]
ITEMS.json: [{"role", "id", "ref"}, ...]. Exit 0 frozen or identical, 1 different or refused, 2 unreadable input or bad
usage. Output: JSON. freeze writes FILE once (an existing different file is refused).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.release_manifest import canonical_sha256  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.protected.identity import plugin_release  # noqa: E402

FORMAT = "hep-research-analysis-bundle/1"
ROLES = ("measurement-spec", "recipe", "semantics-table", "calibration", "tool-contract", "environment-lock", "review")
EXACTLY_ONE = ("measurement-spec", "environment-lock")


class BundleRefused(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def digest_of(doc: dict) -> str:
    return canonical_sha256({k: v for k, v in doc.items() if k != "bundle_digest"})


def _read(root: Path, ref: str) -> bytes:
    """The bytes of a project file, refusing escapes, links on the path and non-regular files."""
    rel = Path(ref)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise BundleRefused("bundle.bad_ref", f"{ref!r}: refs are relative to the project root, without '..'")
    cur = root
    try:
        for part in rel.parts:
            cur = cur / part
            try:
                st = os.lstat(cur)
            except FileNotFoundError:
                raise BundleRefused("bundle.missing", f"{ref!r} does not exist") from None
            if stat.S_ISLNK(st.st_mode):
                raise BundleRefused("bundle.link", f"{ref!r}: a link on the path is refused")
        if not stat.S_ISREG(os.lstat(cur).st_mode):
            raise BundleRefused("bundle.not_regular", f"{ref!r} is not a regular file")
        return cur.read_bytes()
    except BundleRefused:
        raise
    except (OSError, ValueError) as exc:  # a file used as a folder, a NUL byte, no permission
        raise BundleRefused("bundle.unreadable", f"{ref!r}: {type(exc).__name__}") from None


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key: two files with different content could share one canonical digest")
    return dict(pairs)


def item_digest(root: Path, ref: str) -> tuple[str, str]:
    data = _read(root, ref)
    if ref.lower().endswith(".json"):
        try:
            return canonical_sha256(json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicates)), "canonical-json"
        except (UnicodeError, ValueError, RecursionError):
            raise BundleRefused("bundle.bad_json", f"{ref!r} is not JSON") from None
    return hashlib.sha256(data).hexdigest(), "bytes"


def freeze(root, analysis: str, items, data_exposure: dict | None = None, identity: dict | None = None) -> dict:
    root = Path(root).resolve()
    if not isinstance(items, list) or not items:
        raise BundleRefused("bundle.no_items", "a bundle needs its items")
    out, seen = [], set()
    for i, it in enumerate(items):
        if not (isinstance(it, dict) and it.get("role") in ROLES and isinstance(it.get("id"), str) and it["id"]
                and isinstance(it.get("ref"), str)):
            raise BundleRefused("bundle.bad_item", f"items[{i}] needs a role from {list(ROLES)}, an id and a ref")
        if it["ref"] in seen:
            raise BundleRefused("bundle.duplicate_ref", f"{it['ref']!r} is listed twice")
        seen.add(it["ref"])
        sha, kind = item_digest(root, it["ref"])
        out.append({"role": it["role"], "id": it["id"], "ref": it["ref"], "sha256": sha, "digest_kind": kind})
    roles = [it["role"] for it in out]
    for r in EXACTLY_ONE:
        if roles.count(r) != 1:
            raise BundleRefused("bundle.roles", f"exactly one {r} item is needed")
    if "recipe" not in roles:
        raise BundleRefused("bundle.roles", "at least one recipe item is needed")
    doc = {"bundle_version": "1.0.0", "format": FORMAT, "analysis": analysis,
           "items": sorted(out, key=lambda x: (ROLES.index(x["role"]), x["ref"])),
           "plugin_release": dict(identity or plugin_release())}
    if data_exposure is not None:
        doc["data_exposure"] = dict(data_exposure)
    doc["bundle_digest"] = digest_of(doc)
    rep = validate(doc, "analysis_bundle.json")
    if not rep.ok:
        raise BundleRefused("bundle.schema", "; ".join(f"{f.path}: {f.code}" for f in rep.errors))
    return doc


def verify(bundle, root, check_plugin: bool = False, identity: dict | None = None) -> dict:
    """{"status": "identical"|"different"|"invalid", "differences": [{"ref", "change"}], "bundle_digest"}."""
    rep = validate(bundle, "analysis_bundle.json")
    if not rep.ok:
        return {"status": "invalid", "differences": [{"ref": f.path, "change": f.code} for f in rep.errors],
                "bundle_digest": None}
    root = Path(root).resolve()
    diffs = []
    if digest_of(bundle) != bundle["bundle_digest"]:
        diffs.append({"ref": "$", "change": "digest"})
    for it in bundle["items"]:
        try:
            sha, kind = item_digest(root, it["ref"])
        except BundleRefused as exc:
            diffs.append({"ref": it["ref"], "change": exc.code.split(".", 1)[1]})
            continue
        if (sha, kind) != (it["sha256"], it["digest_kind"]):
            diffs.append({"ref": it["ref"], "change": "changed"})
    if check_plugin:
        now = identity or plugin_release()
        if (now.get("release"), now.get("digest")) != (bundle["plugin_release"]["release"], bundle["plugin_release"]["digest"]):
            diffs.append({"ref": "$plugin_release", "change": "changed"})
    return {"status": "different" if diffs else "identical", "differences": diffs,
            "bundle_digest": bundle["bundle_digest"],
            "note": "content identity only; an identical bundle is not thereby reviewed or permitted"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("freeze")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--analysis", required=True)
    p.add_argument("--items", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("verify")
    p.add_argument("bundle", type=Path)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--check-plugin", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        if args.cmd == "freeze":
            doc = freeze(args.root, args.analysis, json.loads(args.items.read_text(encoding="utf-8")))
            body = json.dumps(doc, indent=1, sort_keys=True) + "\n"
            if args.out.exists() and args.out.read_text(encoding="utf-8") != body:
                print(json.dumps({"status": "refused", "code": "bundle.exists", "error": f"{args.out} holds another bundle"}))
                return 1
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(body, encoding="utf-8")
            print(json.dumps({"status": "frozen", "bundle_digest": doc["bundle_digest"], "items": len(doc["items"]),
                              "path": str(args.out)}))
            return 0
        rep = verify(json.loads(args.bundle.read_text(encoding="utf-8")), args.root, args.check_plugin)
    except BundleRefused as exc:
        print(json.dumps({"status": "refused", "code": exc.code, "error": str(exc)}))
        return 1
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    print(json.dumps(rep, indent=1))
    return 0 if rep["status"] == "identical" else 1


if __name__ == "__main__":
    sys.exit(main())
