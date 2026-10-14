#!/usr/bin/env python3
"""Release preparation (task P4.2, C02): from the output of a blinding transform (core.blinding.transforms), write the
release directory and a draft data release manifest (contracts/schemas/release_manifest.json), plus the sealed file the
custodian keeps for output scans. Run by the custodian from its own copies; run by an agent on synthetic data it is an
exercise, and a draft manifest releases nothing: approval, the full check (release_manifest.py with every custodian
option) and publication are the custodian's.

  release directory   released.json only: the released data, with the mode and parameters under "blinding" (no
                      sealed value, no key)
  sealed file         {"sealed": [...], "rtol"} or {"sealed": [], "nothing_sealable": true}, written OUTSIDE the
                      release directory (refused inside it)
  draft manifest      artifacts with SHA-256 and size; transform.code_sha256 = the given code digest, else the running
                      plugin's code identity (contracts.identity; refused when it is unknown); transform.parameters
                      from the mode (no key-like name); protected and retained from the mode; related_releases from the
                      ledger (same analysis or source) and from the exposure record; the other fields from META

META: {"release_id", "source": {"snapshot_id", "sha256"}, "review", "approval_ref", "purposes", "destinations",
"validity", optional "composition_review"}.

Usage: python3 contracts/release_prepare.py --release RELEASE.json --meta META.json --out DIR --sealed-out FILE
           [--manifest-out FILE] [--ledger FILE] [--analysis NAME] [--exposure-record FILE] [--code-digest HEX]
RELEASE.json is a transform output (core.blinding.transforms.*). Exit 0 prepared, 1 refused, 2 unreadable input.
Output: JSON {"status", "manifest", "release_dir", "sealed_file"}; the draft manifest goes to --manifest-out (default
DIR/../<release_id>.manifest.draft.json), never into the release directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.release_manifest import HEX64, KEY_LIKE, MAX_SEALED_RTOL  # noqa: E402
from core.blinding.transforms import MODES  # noqa: E402
from core.protected.guard import guard, protected_main  # noqa: E402
from core.protected.identity import plugin_release  # noqa: E402

META_KEYS = ("release_id", "source", "review", "approval_ref", "purposes", "destinations", "validity")


class PrepareRefused(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _keyish(obj, path="parameters") -> list[str]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if KEY_LIKE.search(str(k)):
                out.append(f"{path}.{k}")
            out += _keyish(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _keyish(v, f"{path}[{i}]")
    return out


def related(meta: dict, ledger, analysis, exposure_record) -> list[str]:
    rid, src = meta["release_id"], meta["source"]["sha256"]
    found = set()
    for e in ledger or []:
        if isinstance(e, dict) and isinstance(e.get("release_id"), str) and e["release_id"] != rid and (
                (analysis is not None and e.get("analysis") == analysis) or e.get("source_sha256") == src):
            found.add(e["release_id"])
    for e in (exposure_record or {}).get("entries") or []:
        if isinstance(e, dict) and isinstance(e.get("release_id"), str) and e["release_id"] != rid:
            found.add(e["release_id"])
    return sorted(found)


RELEASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _write_new(path: Path, data: bytes, mode: int) -> None:
    """Create a file that does not exist yet, without following a link (never overwrite)."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), mode)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def prepare(release: dict, meta: dict, out_dir, sealed_out, *, ledger=None, analysis=None, exposure_record=None,
            code_digest=None, rtol: float = 1e-9) -> dict:
    """Write the release directory and the sealed file; return the draft manifest. See the module docstring. Every
    check runs and every document is built before anything is written; files are created, never overwritten."""
    guard("contracts.release_prepare.prepare", paths=[out_dir, sealed_out])
    if not isinstance(release, dict) or release.get("mode") not in MODES or "released" not in release:
        raise PrepareRefused("prepare.not_a_release", f"not a transform output (mode one of {list(MODES)})")
    if not (isinstance(release.get("protected"), list) and release["protected"] and isinstance(release.get("retained"), list)
            and isinstance(release.get("sealed", []), list)):
        raise PrepareRefused("prepare.not_a_release", "a transform output has protected, retained and sealed lists")
    missing = [k for k in META_KEYS if k not in meta]
    if missing:
        raise PrepareRefused("prepare.meta_incomplete", f"META needs {missing}")
    if not (isinstance(meta["release_id"], str) and RELEASE_ID.match(meta["release_id"])):
        raise PrepareRefused("prepare.bad_release_id", "release_id: letters, digits, '.', '_', '-' only")
    if not (isinstance(meta["source"], dict) and isinstance(meta["source"].get("sha256"), str)):
        raise PrepareRefused("prepare.meta_incomplete", "META source needs a sha256")
    bad = _keyish(release.get("parameters", {}))
    if bad:
        raise PrepareRefused("prepare.keys_present", f"key-like parameter names {bad}")
    out = Path(out_dir).resolve()
    sealed_path = Path(sealed_out).resolve()
    if _inside(sealed_path, out):
        raise PrepareRefused("prepare.sealed_in_release", "the sealed file never goes into the release directory")
    if out.exists() and (Path(out_dir).is_symlink() or not out.is_dir() or any(out.iterdir())):
        raise PrepareRefused("prepare.out_not_empty", f"{out} exists and is not an empty directory")
    if sealed_path.exists() or Path(sealed_out).is_symlink():
        raise PrepareRefused("prepare.sealed_exists", "the sealed file exists: it is never overwritten")
    if code_digest is None:
        ident = plugin_release()
        code_digest = ident.get("digest")
    if not (isinstance(code_digest, str) and HEX64.match(code_digest)):
        raise PrepareRefused("prepare.code_unknown", "the transform code has no recorded identity: give --code-digest")
    if not 0 < rtol <= MAX_SEALED_RTOL:
        raise PrepareRefused("prepare.bad_rtol", f"rtol must be in (0, {MAX_SEALED_RTOL:g}]")
    top = dict(release["released"]) if isinstance(release["released"], dict) else {"released": release["released"]}
    # the transform's description sits under 'blinding', a structure key the sealed-value scan skips (bin edges and
    # region bounds are not data)
    top["blinding"] = dict(top.get("blinding") or {}, mode=release["mode"], parameters=release.get("parameters", {}))
    body = (json.dumps(top, indent=1, sort_keys=True) + "\n").encode("utf-8")
    sealed = [x for x in release.get("sealed", []) if x != 0]
    sealed_doc = {"sealed": sealed, "rtol": rtol} if sealed else {"sealed": [], "nothing_sealable": True, "rtol": rtol}
    manifest = {"manifest_version": "1.0.0", "release_id": meta["release_id"], "source": meta["source"],
                "artifacts": [{"path": "released.json", "sha256": hashlib.sha256(body).hexdigest(), "size": len(body),
                               "format": "json"}],
                "artifact_rules": {"symlinks": "refused", "unlisted_files": "refused"},
                "transform": {"code_sha256": code_digest, "parameters": release.get("parameters", {}),
                              "keys_recorded": False},
                "protected": list(release["protected"]), "retained": list(release["retained"]),
                "review": meta["review"], "approval_ref": meta["approval_ref"], "purposes": meta["purposes"],
                "destinations": meta["destinations"], "validity": meta["validity"],
                "related_releases": related(meta, ledger, analysis, exposure_record)}
    if "composition_review" in meta:
        manifest["composition_review"] = meta["composition_review"]
    out.mkdir(parents=True, exist_ok=True)
    _write_new(out / "released.json", body, 0o644)
    sealed_path.parent.mkdir(parents=True, exist_ok=True)
    _write_new(sealed_path, (json.dumps(sealed_doc) + "\n").encode("utf-8"), 0o600)  # owner-only: it holds the secrets
    return manifest


@protected_main("contracts.release_prepare")
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for name in ("release", "meta", "ledger", "exposure_record"):
        ap.add_argument(f"--{name.replace('_', '-')}", dest=name, type=Path, required=name in ("release", "meta"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sealed-out", dest="sealed_out", type=Path, required=True)
    ap.add_argument("--manifest-out", dest="manifest_out", type=Path)
    ap.add_argument("--analysis")
    ap.add_argument("--code-digest", dest="code_digest")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        docs = {n: None if getattr(args, n) is None else json.loads(getattr(args, n).read_text(encoding="utf-8"))
                for n in ("release", "meta", "ledger", "exposure_record")}
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "unreadable", "error": str(exc)}))
        return 2
    rid = (docs["meta"] or {}).get("release_id") if isinstance(docs["meta"], dict) else None
    if not (isinstance(rid, str) and RELEASE_ID.match(rid)):
        print(json.dumps({"status": "refused", "code": "prepare.bad_release_id", "error": "release_id: letters, digits, '.', '_', '-'"}))
        return 1
    mout = (args.manifest_out or args.out.absolute().parent / f"{rid}.manifest.draft.json").resolve()
    if _inside(mout, args.out.resolve()) or mout == args.sealed_out.resolve() or mout.exists():
        print(json.dumps({"status": "refused", "code": "prepare.manifest_misplaced",
                          "error": "the draft manifest goes outside the release, not over the sealed file or an existing file"}))
        return 1
    if not (isinstance(docs["release"], dict) and isinstance(docs["meta"], dict)):
        print(json.dumps({"status": "unreadable", "error": "--release and --meta are JSON objects"}))
        return 2
    try:
        manifest = prepare(docs["release"], docs["meta"], args.out, args.sealed_out, ledger=docs["ledger"],
                           analysis=args.analysis, exposure_record=docs["exposure_record"], code_digest=args.code_digest)
    except PrepareRefused as exc:
        print(json.dumps({"status": "refused", "code": exc.code, "error": str(exc)}))
        return 1
    except (OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "unreadable", "error": f"{type(exc).__name__}: {exc}"}))
        return 2
    _write_new(mout, (json.dumps(manifest, indent=1) + "\n").encode("utf-8"), 0o644)
    print(json.dumps({"status": "prepared", "manifest": str(mout), "release_dir": str(args.out),
                      "sealed_file": str(args.sealed_out), "related_releases": manifest["related_releases"],
                      "note": "a draft: approval, the full release_manifest.py check and publication are the custodian's"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
