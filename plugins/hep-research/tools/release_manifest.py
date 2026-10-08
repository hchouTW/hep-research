#!/usr/bin/env python3
"""Code release manifest: the identity of a hep-research release bundle (AGENTIC-R5 T0.2, plan basis §6.6).

The identified object is the release bundle, not a working directory. Its files are the git-listed plugin files
(tracked plus untracked-but-not-ignored, as tools/check_packaging.py lists them) or, outside git (an installed copy, a
`git archive` export), every regular file except caches. The recorded manifests under `release-manifests/` are not
part of any bundle. For each file the manifest records the relative POSIX path, the full SHA-256 of its bytes, its
size and its mode (100755 when any execute bit is set, else 100644). Symbolic links and other non-regular files are
refused. Files are sorted by the UTF-8 bytes of their path. The digest is the SHA-256 of the canonical UTF-8 JSON
(sorted keys, no whitespace) of {"format", "files"}; it is the plugin's code identity. Keep it whole: an abbreviation
is for display only.

Usage:
  python3 tools/release_manifest.py generate [--root DIR] [--out FILE]   write (or print) the manifest
  python3 tools/release_manifest.py digest   [--root DIR]                print the digest only
  python3 tools/release_manifest.py verify   --manifest FILE [--root DIR] compare a tree with a recorded manifest
  python3 tools/release_manifest.py check-published [--base REF]          CI immutability rule (C10)
check-published: every recorded manifest `release-manifests/<version>.json` must match the bundle exported from its
published tag `hep-research--v<version>` (git archive); a manifest whose tag is not pushed yet (the release commit
itself) is listed as pending; with --base, recorded manifests may only be added since REF, never changed or deleted. The working tree (Unreleased) is not checked. Tags without a recorded manifest (releases
before this tool) are listed as unrecorded.
Exit codes: 0 ok (verify: identical), 1 verify found differences or a published bundle changed, 2 unreadable input
or a refused file.
A matching digest shows the bytes are those recorded; it is not an approval of the code or of any use.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contracts.identity import (FORMAT, RECORDS, RefusedFile, bundle_files, digest_of, entry, generate,  # noqa: E402,F401
                                verify)

ROOT = Path(__file__).resolve().parents[1]


TAG_PREFIX = "hep-research--v"


def _git(*args: str, cwd: Path = ROOT, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, timeout=300, **kw)


def check_published(base: str | None = None) -> dict:
    import io
    import tarfile
    import tempfile
    prefix = _git("rev-parse", "--show-prefix", text=True, check=True).stdout.strip()
    top = Path(_git("rev-parse", "--show-toplevel", text=True, check=True).stdout.strip())
    problems, checked, pending = [], [], []
    rec_dir = ROOT / RECORDS
    recorded = sorted(rec_dir.glob("*.json")) if rec_dir.is_dir() else []
    tags = set(_git("tag", "--list", TAG_PREFIX + "*", text=True, check=True).stdout.split())
    for man_path in recorded:
        version = man_path.stem
        tag = TAG_PREFIX + version
        if tag not in tags:  # recorded in the release commit; the tag is pushed once that commit is on main
            pending.append(tag)
            continue
        # the plugin subtree at the archive root; run from the top level, since a subdirectory cwd filters the archive
        archive = _git("archive", "--format=tar", f"{tag}:{prefix}" if prefix else tag, cwd=top)
        if archive.returncode != 0:
            problems.append(f"{tag}: git archive failed: {archive.stderr.decode(errors='replace').strip()}")
            continue
        with tempfile.TemporaryDirectory() as td:
            with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
                tar.extractall(td, filter="data")
            rep = verify(Path(td), json.loads(man_path.read_text(encoding="utf-8")))
        checked.append({"tag": tag, "status": rep["status"], "digest": rep["digest"]})
        if rep["status"] != "identical":
            problems.append(f"{tag}: published bundle differs from its recorded manifest: {rep['differences'][:5]}")
    if base:
        diff = _git("diff", "--name-status", "--no-renames", base, "HEAD", "--", RECORDS, text=True, check=True).stdout
        for line in filter(None, diff.splitlines()):
            status, path = line.split("\t", 1)
            if status != "A":
                problems.append(f"{path}: a recorded release manifest was {'deleted' if status == 'D' else 'changed'}")
    unrecorded = sorted(t for t in tags if not (rec_dir / f"{t[len(TAG_PREFIX):]}.json").exists())
    return {"status": "fail" if problems else "pass", "checked": checked, "pending_tags": pending,
            "unrecorded_tags": unrecorded, "problems": problems}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    cp = sub.add_parser("check-published")
    cp.add_argument("--base", help="git ref: recorded manifests may only be added since it")
    for name in ("generate", "digest", "verify"):
        s = sub.add_parser(name)
        s.add_argument("--root", type=Path, default=ROOT, help="plugin root (default: this checkout)")
        if name == "generate":
            s.add_argument("--out", type=Path)
        if name == "verify":
            s.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "check-published":
            rep = check_published(args.base)
            print(json.dumps(rep, indent=1))
            return 0 if rep["status"] == "pass" else 1
        root = args.root.resolve(strict=True)
        if args.cmd == "verify":
            rep = verify(root, json.loads(args.manifest.read_text(encoding="utf-8")))
            print(json.dumps(rep, indent=1))
            return 0 if rep["status"] == "identical" else 1
        man = generate(root)
        if args.cmd == "digest":
            print(man["digest"])
        elif args.out:
            args.out.write_text(json.dumps(man, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps({"digest": man["digest"], "file_count": man["file_count"], "out": str(args.out)}))
        else:
            print(json.dumps(man, indent=1, ensure_ascii=False))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
