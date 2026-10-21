#!/usr/bin/env python3
"""Build Geant4 from source in a user work folder from a pinned build spec, and record the build (WP1 M1).

Purpose: a reproducible Geant4 installation for adapters/geant4, with a computational-run record that names the
tag and commit, the CMake options, the compiler, the datasets (MD5 of each downloaded tarball, content hash of each
installed directory) and the output of geant4-config. Nothing is installed system-wide.

Tool and licence boundary: Geant4 (https://github.com/Geant4/geant4) is distributed under the Geant4 Software
License, Version 1.0, 28 June 2006; this plugin is Apache-2.0. The adapter never bundles or copies Geant4: the
source is cloned into the work folder the user names and built there, with the user's approval (cloning and the
dataset download contact github.com and cern.ch).

Method: `build` clones the tag (or reuses a clone in <work>/src after checking its commit), configures with the
spec's CMake options (GEANT4_INSTALL_DATA is forced OFF: the datasets are fetched by this script so that their
MD5s are checked and recorded), builds, installs into <work>/install, then installs the datasets the spec names
from the dataset definitions of the cloned source (cmake/Modules/G4DatasetDefinitions.cmake), either downloaded
(MD5 of the tarball checked) or copied from a user directory. Every installed dataset directory is checked to be
non-empty and gets a content hash (SHA-256 over the sorted relative paths and file hashes). `geant4-config
--check-datasets` is recorded as information only: it checks only that the compiled-in directories exist.
`check` recomputes the version and the dataset content hashes of an installation and compares them with a record.

Usage (from the plugin root):
  python3 adapters/geant4/assets/geant4_build.py build --spec BUILD_SPEC.json --work DIR --record OUT.json [--jobs N] [--created YYYY-MM-DD]
  python3 adapters/geant4/assets/geant4_build.py check --record BUILD.json [--work DIR]
Every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status, status_label, inputs, defaults_used, and the record (build) or the comparison (check).
Exit codes: 0 ok; 1 the build failed, a commit or MD5 does not match, or check found a difference; 2 bad input;
3 git, cmake or a compiler missing. Standard library only.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import (CONTRACTS_VERSION, JsonArgumentParser, SpecError, plugin_version, sha256_file,  # noqa: E402
                      tilde)
from core.status import add_status_argument, exit_code  # noqa: E402

FORCED = {"GEANT4_INSTALL_DATA": "OFF"}
DEFAULT_OPTIONS = {"CMAKE_BUILD_TYPE": "Release", "CMAKE_CXX_STANDARD": "17", "GEANT4_BUILD_MULTITHREADED": "ON",
                   "GEANT4_USE_QT": "OFF", "GEANT4_USE_OPENGL_X11": "OFF", "GEANT4_USE_GDML": "OFF",
                   "GEANT4_USE_SYSTEM_CLHEP": "OFF"}
USER_AGENT = "hep-research-geant4-adapter"  # generic: no personal identifier in network requests
DATA_SUBDIR = Path("share") / "Geant4" / "data"


def md5_file(path: Path) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def tree_hash(root: Path) -> tuple[str, int]:
    """SHA-256 over the sorted (relative path, file SHA-256) pairs of every file under root, and the file count."""
    h, n = hashlib.sha256(), 0
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        h.update(f"{p.relative_to(root).as_posix()}\0{sha256_file(p)}\n".encode())
        n += 1
    return h.hexdigest(), n


def dataset_definitions(src: Path) -> dict[str, dict]:
    """NAME -> {version, filename, extension, envvar, md5} from the cloned source's dataset definitions."""
    text = (src / "cmake" / "Modules" / "G4DatasetDefinitions.cmake").read_text(encoding="utf-8")
    out = {}
    for block in re.findall(r"geant4_add_dataset\((.*?)\)", text, re.S):
        fields = dict(re.findall(r"^\s*(NAME|VERSION|FILENAME|EXTENSION|ENVVAR|MD5SUM)\s+(\S+)", block, re.M))
        if "NAME" in fields:
            out[fields["NAME"]] = {"version": fields["VERSION"], "filename": fields["FILENAME"],
                                   "extension": fields["EXTENSION"], "envvar": fields["ENVVAR"],
                                   "md5": fields["MD5SUM"]}
    return out


def load_spec(path: Path) -> dict:
    spec = json.loads(path.read_text(encoding="utf-8"))
    g = spec.get("geant4") or {}
    for key in ("repository", "tag", "commit"):
        if not isinstance(g.get(key), str) or not g[key]:
            raise SpecError(f"geant4.{key} is required")
    if not re.fullmatch(r"[0-9a-f]{40}", g["commit"]):
        raise SpecError("geant4.commit must be a full 40-character SHA-1")
    opts = spec.get("cmake_options", {})
    if not isinstance(opts, dict) or not all(isinstance(v, str) for v in opts.values()):
        raise SpecError("cmake_options must map option names to strings")
    if opts.get("CMAKE_CXX_STANDARD", "17") not in ("17", "20", "23"):
        raise SpecError("CMAKE_CXX_STANDARD must be 17, 20 or 23 (G4BuildSettings.cmake)")
    for key in FORCED:
        if key in opts and opts[key] != FORCED[key]:
            raise SpecError(f"{key} is forced {FORCED[key]}: datasets are installed by this script")
    ds = spec.get("datasets") or {}
    if ds.get("source") not in ("download", "directory"):
        raise SpecError("datasets.source must be 'download' or 'directory'")
    if not isinstance(ds.get("names"), list) or not ds["names"]:
        raise SpecError("datasets.names must list the datasets the physics settings need")
    if ds["source"] == "download" and not str(ds.get("base_url", "")).startswith("https://"):
        raise SpecError("datasets.base_url must be an https URL")
    if ds["source"] == "directory" and not ds.get("path"):
        raise SpecError("datasets.path is required with source 'directory'")
    return spec


def run(cmd: list[str], log: Path, cwd: Path | None = None) -> int:
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"$ {' '.join(cmd)}\n")
        fh.flush()
        return subprocess.run(cmd, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT, timeout=6 * 3600).returncode


def capture(cmd: list[str]) -> str:
    """Output of a command with the home folder written as ~."""
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return (p.stdout + p.stderr).strip().replace(str(Path.home()) + os.sep, "~" + os.sep)


def fetch(url: str, dest: Path) -> list[str]:
    """Download url to dest; returns the hosts contacted (the redirect chain)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    hosts = [urllib.request.urlparse(url).hostname]
    with urllib.request.urlopen(req, timeout=600) as resp, dest.open("wb") as fh:
        final = urllib.request.urlparse(resp.geturl()).hostname
        if final not in hosts:
            hosts.append(final)
        shutil.copyfileobj(resp, fh, 1 << 20)
    return hosts


def install_datasets(spec: dict, defs: dict, install: Path, work: Path, log: Path) -> tuple[list[dict], list[str]]:
    ds, data = spec["datasets"], install / DATA_SUBDIR
    data.mkdir(parents=True, exist_ok=True)
    out, hosts = [], []
    for name in ds["names"]:
        if name not in defs:
            raise SpecError(f"dataset {name} is not defined by this Geant4 source")
        d = defs[name]
        target = data / f"{name}{d['version']}"
        entry = {"name": name, "version": d["version"], "envvar": d["envvar"], "path": tilde(target),
                 "md5_expected": d["md5"]}
        if ds["source"] == "download":
            tarball = work / "downloads" / f"{d['filename']}.{d['version']}.{d['extension']}"
            tarball.parent.mkdir(parents=True, exist_ok=True)
            url = f"{ds['base_url'].rstrip('/')}/{tarball.name}"
            if not tarball.is_file() or md5_file(tarball) != d["md5"]:
                with log.open("a", encoding="utf-8") as fh:
                    fh.write(f"download {url}\n")
                hosts += [h for h in fetch(url, tarball) if h not in hosts]
            got = md5_file(tarball)
            entry.update(source=url, md5=got, md5_verified=got == d["md5"])
            if got != d["md5"]:
                out.append(entry)
                continue
            if not target.is_dir():
                with tarfile.open(tarball) as tf:
                    tf.extractall(data, filter="data")
        else:
            src_dir = Path(os.path.expanduser(ds["path"])) / target.name
            if not src_dir.is_dir():
                raise SpecError(f"{src_dir} is not a directory")
            if not target.is_dir():
                shutil.copytree(src_dir, target)
            entry.update(source=tilde(src_dir), md5=None, md5_verified=None)
        if not target.is_dir():
            entry.update(content_sha256=None, n_files=0)
        else:
            entry["content_sha256"], entry["n_files"] = tree_hash(target)
        out.append(entry)
    return out, hosts


def cmd_build(args) -> tuple[str, dict]:
    spec = load_spec(args.spec)
    for tool in ("git", "cmake"):
        if not shutil.which(tool):
            return "missing-dependency", {"error": f"{tool} not found on PATH"}
    cxx = (spec.get("compiler") or {}).get("cxx", "c++")
    if not shutil.which(cxx):
        return "missing-dependency", {"error": f"C++ compiler {cxx} not found on PATH"}
    work = args.work.expanduser().resolve()
    src, bld, inst, logs = work / "src", work / "build", work / "install", work / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / "build.log"
    g = spec["geant4"]
    hosts: list[str] = []
    if not src.is_dir():
        hosts.append(urllib.request.urlparse(g["repository"]).hostname)
        if run(["git", "clone", "--branch", g["tag"], "--depth", "1", g["repository"], str(src)], log) != 0:
            return "failed", {"error": "git clone failed", "log": tilde(log)}
    head = capture(["git", "-C", str(src), "rev-parse", "HEAD"])
    if head != g["commit"]:
        return "failed", {"error": f"source commit {head} != spec commit {g['commit']}", "log": tilde(log)}
    options = {**DEFAULT_OPTIONS, **spec.get("cmake_options", {}), **FORCED}
    configure = ["cmake", "-S", str(src), "-B", str(bld), f"-DCMAKE_INSTALL_PREFIX={inst}",
                 f"-DCMAKE_CXX_COMPILER={shutil.which(cxx)}"] + [f"-D{k}={v}" for k, v in sorted(options.items())]
    steps = [configure, ["cmake", "--build", str(bld), "--parallel", str(args.jobs)], ["cmake", "--install", str(bld)]]
    codes = []
    for cmd in steps:
        codes.append(run(cmd, log))
        if codes[-1] != 0:
            break
    datasets, dl_hosts = [], []
    if codes[-1] == 0 and len(codes) == len(steps):
        datasets, dl_hosts = install_datasets(spec, dataset_definitions(src), inst, work, log)
    hosts += dl_hosts
    config = inst / "bin" / "geant4-config"
    info = {}
    if config.is_file():
        info = {"version": capture([str(config), "--version"]),
                "has_multithreading": capture([str(config), "--has-feature", "multithreading"]),
                "check_datasets": capture([str(config), "--check-datasets"]),
                "check_datasets_note": "information only: checks that the compiled-in directories exist"}
    bad_ds = [d["name"] for d in datasets if d.get("md5_verified") is False or not d.get("n_files")]
    ok = (len(codes) == len(steps) and all(c == 0 for c in codes) and not bad_ds
          and info.get("version") == g["tag"].lstrip("v"))
    home = str(Path.home()) + os.sep
    shown = [" ".join(a.replace(home, "~" + os.sep) for a in c) for c in steps[: len(codes)]]
    created = args.created or datetime.date.today().isoformat()
    record = {
        "contract_version": CONTRACTS_VERSION, "artifact_id": f"geant4-build-{g['commit'][:8]}",
        "artifact_type": "computational-run",
        "objective": f"Build Geant4 {g['tag']} (commit {g['commit'][:8]}) from source in {tilde(work)} without "
                     "system-wide installation, for adapters/geant4",
        "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": plugin_version(), "contracts": CONTRACTS_VERSION, "profiles": {}},
        "provenance": {"producer_skill": "hep-detector", "created": created, "evidence_ids": []},
        "inputs": [], "outputs": [], "unresolved_inputs": [],
        "status": ["unvalidated"] if ok else ["unvalidated", "failed"],
        "extension": {
            "input_manifest": [{"path": f"geant4@{g['commit']}/cmake/Modules/G4DatasetDefinitions.cmake",
                                "sha256": sha256_file(src / "cmake" / "Modules" / "G4DatasetDefinitions.cmake")},
                               {"path": tilde(args.spec), "sha256": sha256_file(args.spec)}],
            "tools": [{"name": "Geant4", "version": f"{g['tag']} ({g['commit']})", "source": g["repository"]},
                      {"name": "cmake", "version": capture(["cmake", "--version"]).splitlines()[0]},
                      {"name": cxx, "version": capture([cxx, "--version"]).splitlines()[0]},
                      {"name": "CLHEP", "version": "internal (GEANT4_USE_SYSTEM_CLHEP "
                                                   f"{options['GEANT4_USE_SYSTEM_CLHEP']})"}],
            "commands": shown, "environment": {"platform": platform.platform(), "machine": platform.machine(),
                                               "python": platform.python_version(), "hosts_contacted": hosts,
                                               "work": tilde(work)},
            "seeds": {}, "tolerances": {}, "exit_status": 0 if ok else 1,
            "output_hashes": {d["path"]: d["content_sha256"] for d in datasets if d.get("content_sha256")},
            "build": {"tag": g["tag"], "commit": head, "cmake_options": options,
                      "cmake_cxx_standard": options["CMAKE_CXX_STANDARD"],
                      "multithreaded": options["GEANT4_BUILD_MULTITHREADED"], "install_prefix": tilde(inst),
                      "geant4_config": info, "datasets": datasets, "log": tilde(log), "step_exit_codes": codes}}}
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return ("ok" if ok else "failed"), {"record": str(args.record), "bad_datasets": bad_ds,
                                         "geant4_config": info, "step_exit_codes": codes}


def cmd_check(args) -> tuple[str, dict]:
    rec = json.loads(args.record.read_text(encoding="utf-8"))
    build = rec["extension"]["build"]
    inst = Path(os.path.expanduser(build["install_prefix"]))
    config = inst / "bin" / "geant4-config"
    if not config.is_file():
        return "missing-dependency", {"error": f"{tilde(config)} not found"}
    diffs = []
    version = capture([str(config), "--version"])
    if version != build["geant4_config"].get("version"):
        diffs.append(f"version {version} != {build['geant4_config'].get('version')}")
    for d in build["datasets"]:
        path = Path(os.path.expanduser(d["path"]))
        got = tree_hash(path)[0] if path.is_dir() else None
        if got != d.get("content_sha256"):
            diffs.append(f"dataset {d['name']}: content hash {got} != {d.get('content_sha256')}")
    return ("ok" if not diffs else "failed"), {"version": version, "differences": diffs}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build", help="clone, configure, build, install and fetch datasets; write the build record")
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True, help="work folder (src/, build/, install/, logs/ inside)")
    p.add_argument("--record", type=Path, required=True, help="where to write the computational-run record")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    p.add_argument("--created", help="the created date written into the record (default: today)")
    p = sub.add_parser("check", help="compare an installation with its build record")
    p.add_argument("--record", type=Path, required=True)
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: tilde(v) if isinstance(v, Path) else v for k, v in vars(args).items() if k != "status"}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("jobs", "created", "status") if f"--{k}" not in given and hasattr(args, k)]
    try:
        status, doc = {"build": cmd_build, "check": cmd_check}[args.command](args)
    except (SpecError, KeyError, json.JSONDecodeError) as exc:
        status, doc = "rejected", {"error": str(exc)}
    except OSError as exc:
        status, doc = "failed", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **doc}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
