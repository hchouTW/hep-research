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

`register` (adapter 0.6.0) records an existing installation instead of building one (conda-forge, an LCG view, a
system package, a site build): it reads the version, prefix, C++ standard, features and dataset list from
geant4-config and cross-checks them with Geant4Config.cmake and Geant4ConfigVersion.cmake (version, C++ standard,
dataset names, variables and expected versions); a disagreement refuses the registration. Each dataset folder is
resolved from --dataset-source: `env` the dataset variable of the current environment, `config` the path
geant4-config reports, `auto` (default) the variable when it is set, else the geant4-config path, with the source used
reported per dataset. A dataset found nowhere, a variable that points to a folder that is not the dataset the
installation expects (name and version; a folder name without the G4 prefix, as conda-forge installs them, is
accepted and reported), or a folder with no file refuses the registration, unless --skip-dataset leaves the dataset
out of the record on purpose. Every recorded folder is content-hashed as `build` does. The record has the shape of a
build record (so every tool of the adapter reads it unchanged) with extension.build.origin `registered`, tag and
commit null and `unknown` listing what a registration cannot show (source commit, build options, the compiler of the
build, dataset MD5s); it also records the compiler and CMake found now, the geant4-config and Geant4Config.cmake paths
and hashes, and a CMake probe (find_package(Geant4) in an empty project, unless --no-cmake-probe): a probe that fails
is recorded and reported, and the programs are then built with `geant4_run.py build-sim --configure-with
geant4-config`. `check` on a registered record re-reads the version and prefix, the two configuration hashes and
the dataset content hashes. Nothing is downloaded and nothing is written into the installation.

Usage (from the plugin root):
  python3 adapters/geant4/assets/geant4_build.py build --spec BUILD_SPEC.json --work DIR --record OUT.json [--jobs N] [--created YYYY-MM-DD]
  python3 adapters/geant4/assets/geant4_build.py register (--geant4-config PATH | --prefix DIR) --record OUT.json
      [--dataset-source auto|env|config] [--skip-dataset NAME ...] [--compiler CXX] [--no-cmake-probe] [--created YYYY-MM-DD]
  python3 adapters/geant4/assets/geant4_build.py check --record BUILD.json
Every subcommand takes --status LABEL (default unvalidated), echoed as status_label.
Output JSON: status, status_label, inputs, defaults_used, and the record (build, register) or the comparison (check).
Exit codes: 0 ok; 1 the build failed, a commit or MD5 does not match, check found a difference, or a registration
was refused (the reasons are listed; no record is written); 2 bad input (also a missing or unreadable spec or
record, or a geant4-config that is not one); 3 git, cmake or a compiler missing (build), or the installation's
geant4-config missing (check). Standard library only.
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
import tempfile
import urllib.request
from pathlib import Path

sys.dont_write_bytecode = True  # importing core leaves no __pycache__ (F-10)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from g4common import (CONTRACTS_VERSION, DATA_VARS, REGISTERED_UNKNOWN, JsonArgumentParser, SpecError,  # noqa: E402
                      expand, plugin_version, sha256_file, tilde)
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


def read_input(path: Path) -> str:
    """The text of an input file; a missing or unreadable one is bad input (SpecError: rejected, exit 2)."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SpecError(f"cannot read {path}: {exc}") from exc


def load_spec(path: Path) -> dict:
    spec = json.loads(read_input(path))
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
            "build": {"origin": "built-from-source", "tag": g["tag"], "commit": head, "cmake_options": options,
                      "cmake_cxx_standard": options["CMAKE_CXX_STANDARD"],
                      "multithreaded": options["GEANT4_BUILD_MULTITHREADED"], "install_prefix": tilde(inst),
                      "geant4_config": info, "datasets": datasets, "log": tilde(log), "step_exit_codes": codes}}}
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return ("ok" if ok else "failed"), {"record": str(args.record), "bad_datasets": bad_ds,
                                         "geant4_config": info, "step_exit_codes": codes}


def cmd_check(args) -> tuple[str, dict]:
    rec = json.loads(read_input(args.record))
    build = rec["extension"]["build"]
    inst = Path(os.path.expanduser(build["install_prefix"]))
    registered = build.get("origin") == "registered"
    reg = build.get("registration") or {}
    config = expand(reg["geant4_config"]) if registered else inst / "bin" / "geant4-config"
    if not config.is_file():
        return "missing-dependency", {"error": f"{tilde(config)} not found"}
    diffs = []
    # read as register reads it: stdout only (a locale warning on stderr is not part of the answer), and a non-zero
    # exit is a broken geant4-config (rejected), not a version change
    version = config_query(config, "--version")
    if version != build["geant4_config"].get("version"):
        diffs.append(f"version {version} != {build['geant4_config'].get('version')}")
    if registered:  # the registration's identity: prefix, geant4-config and Geant4Config.cmake unchanged
        prefix = config_query(config, "--prefix")
        if not same_dir(prefix, build["install_prefix"]):
            diffs.append(f"geant4-config --prefix {tilde(prefix)} != {build['install_prefix']}")
        for key, path_key in (("geant4_config_sha256", "geant4_config"), ("cmake_config_sha256", "cmake_config")):
            path = expand(reg.get(path_key) or "")
            got = sha256_file(path) if reg.get(path_key) and path.is_file() else None
            if got != reg.get(key):
                diffs.append(f"{reg.get(path_key)}: sha256 {got} != {reg.get(key)}")
    for d in build["datasets"]:
        path = Path(os.path.expanduser(d["path"]))
        got = tree_hash(path)[0] if path.is_dir() else None
        if got != d.get("content_sha256"):
            diffs.append(f"dataset {d['name']}: content hash {got} != {d.get('content_sha256')}")
    return ("ok" if not diffs else "failed"), {"version": version, "origin": build.get("origin", "built-from-source"),
                                               "differences": diffs}


# --- register: an existing installation (adapter 0.6.0) -----------------------------------------------------------

TARBALL = re.compile(r"(.+?)\.(\d+(?:\.\d+)*)\.(?:tar\.gz|tgz|tar\.bz2|tar\.xz|zip)")


def same_dir(a, b) -> bool:
    try:
        return Path(os.path.expanduser(str(a))).resolve() == Path(os.path.expanduser(str(b))).resolve()
    except OSError:
        return False


def config_query(config: Path, *flags: str) -> str:
    """geant4-config's output for flags; a non-zero exit is bad input (not a working geant4-config)."""
    p = subprocess.run([str(config), *flags], capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        raise SpecError(f"{tilde(config)} {' '.join(flags)} exited {p.returncode}: {(p.stdout + p.stderr).strip()[:200]}")
    return p.stdout.strip()


def find_cmake_config(prefix: Path) -> Path | None:
    """The folder of Geant4Config.cmake under an installation prefix (lib/ or lib64/, as GNUInstallDirs chose)."""
    for sub in ("lib/cmake/Geant4", "lib64/cmake/Geant4"):
        if (prefix / sub / "Geant4Config.cmake").is_file():
            return prefix / sub
    hits = sorted(prefix.glob("lib*/Geant4-*/Geant4Config.cmake"))  # the layout of some older installations
    return hits[0].parent if hits else None


def read_cmake_config(cmake_dir: Path) -> dict:
    """Version, C++ standard and the dataset descriptions (name -> envvar, path, tarball, md5) that the installation's
    CMake configuration declares."""
    text = (cmake_dir / "Geant4Config.cmake").read_text(encoding="utf-8", errors="replace")
    vfile = cmake_dir / "Geant4ConfigVersion.cmake"
    vtext = vfile.read_text(encoding="utf-8", errors="replace") if vfile.is_file() else ""
    version = re.search(r'set\(PACKAGE_VERSION\s+"([^"]+)"\)', vtext)
    cxx = re.search(r'set\(Geant4_CXX_STANDARD\s+"?(\d+)"?\)', text)
    datasets = {}
    m = re.search(r'set\(Geant4_DATASET_DESCRIPTIONS\s+"([^"]*)"\)', text)
    for item in (m.group(1).split(";") if m else []):
        parts = item.split("|")
        if len(parts) >= 5:
            datasets[parts[0]] = {"envvar": parts[1], "path": parts[2], "tarball": parts[3], "md5": parts[4]}
    return {"version": version.group(1) if version else None, "cxx_standard": cxx.group(1) if cxx else None,
            "datasets": datasets}


def accepted_folders(name: str, version: str) -> dict[str, str]:
    """Folder names that hold dataset `name` at `version`: NAMEversion (Geant4's own installation), or without the G4
    prefix (conda-forge installs G4EMLOW8.8 as EMLOW8.8); folder name -> how it matched."""
    out = {f"{name}{version}": "exact"}
    if name.startswith("G4"):
        out[f"{name[2:]}{version}"] = "without-G4-prefix"
    return out


def folder_problem(path: Path, accepted: dict[str, str]) -> str | None:
    if not path.is_dir():
        return f"{tilde(path)} is not a directory"
    if path.name not in accepted:
        return f"{tilde(path)}: folder {path.name} is not the expected {' or '.join(sorted(accepted))}"
    if not any(x.is_file() for x in path.rglob("*")):
        return f"{tilde(path)} holds no file"
    return None


def resolve_dataset(name: str, envvar: str, config_path: str, version: str, mode: str) -> tuple[dict | None, str | None]:
    """(entry, None) for the folder of one dataset under --dataset-source mode, or (None, why it is refused)."""
    accepted = accepted_folders(name, version)
    env_value = os.environ.get(envvar)
    cfg = Path(config_path)
    if mode in ("env", "auto") and env_value:
        why = folder_problem(Path(env_value), accepted)
        if why:  # a variable that is set but wrong is never passed over silently
            return None, f"{name}: {envvar} is set to a folder that is not the dataset: {why}"
        chosen, source = Path(env_value), "environment"
    elif mode == "env":
        return None, f"{name}: {envvar} is not set (--dataset-source env)"
    else:
        why = folder_problem(cfg, accepted)
        if why:
            where = "" if mode == "config" else f" and {envvar} is not set"
            near = sorted(n for n in accepted if n != cfg.name and (cfg.parent / n).is_dir())
            hint = (f" ({', '.join(near)} exists next to it: set {envvar} to it, e.g. by activating the environment "
                    "that installed it)") if near else ""
            return None, f"{name}: not found: the geant4-config path {why}{where}{hint}"
        chosen, source = cfg, "geant4-config"
    entry = {"name": name, "version": version, "envvar": envvar, "path": tilde(chosen), "resolved_from": source,
             "folder_name_match": accepted[chosen.name], "path_geant4_config": tilde(cfg),
             "path_geant4_config_exists": cfg.is_dir(),
             "environment_value": tilde(env_value) if env_value else None}
    return entry, None


def cmake_probe(cmake_dir: Path, prefix: Path) -> dict:
    """find_package(Geant4) in an empty CMake project against the installation: whether a CMake build of the
    adapter's programs can find it and every dependency it declares (headers and CMake files of its external
    packages included)."""
    cmake = shutil.which("cmake")
    if not cmake:
        return {"ran": False, "reason": "cmake not found on PATH"}
    with tempfile.TemporaryDirectory(prefix="g4probe-") as probe_dir:
        t = Path(probe_dir)
        (t / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.16...3.27)\nproject(g4probe CXX)\n"
                                          "find_package(Geant4 REQUIRED)\n", encoding="utf-8")
        p = subprocess.run([cmake, "-S", str(t), "-B", str(t / "b"), f"-DGeant4_DIR={cmake_dir}",
                            f"-DCMAKE_PREFIX_PATH={prefix}"], capture_output=True, text=True, timeout=600)
    text = (p.stdout + p.stderr).replace(str(Path.home()) + os.sep, "~" + os.sep)
    errors, block = [], None
    for ln in text.splitlines():  # each "CMake Error at ...:" paragraph, its wrapped lines joined
        if ln.startswith("CMake Error"):
            block = []
        elif block is not None and (not ln.strip() or ln.startswith("Call Stack")):
            errors.append(" ".join(block))
            block = None
        elif block is not None:
            block.append(ln.strip())
    if block:
        errors.append(" ".join(block))
    out = {"ran": True, "find_package_ok": p.returncode == 0, "exit": p.returncode}
    if p.returncode != 0:
        out["errors"] = errors[:6] or [ln.strip() for ln in text.splitlines() if ln.strip()][-6:]
        out["advice"] = ("build the adapter's programs with geant4_run.py build-sim --configure-with geant4-config, or "
                         "install the development files of the packages named above into the installation")
    return out


def tool_version(cmd: str) -> dict:
    path = shutil.which(cmd)
    if not path:
        return {"name": cmd, "version": "not found on PATH", "path": None}
    return {"name": cmd, "version": capture([path, "--version"]).splitlines()[0], "path": tilde(path)}


def cmd_register(args) -> tuple[str, dict]:
    if args.geant4_config:
        config = expand(str(args.geant4_config))
        if not config.is_file() or not os.access(config, os.X_OK):
            raise SpecError(f"--geant4-config {tilde(config)} is not an executable file")
    else:
        config = expand(str(args.prefix)) / "bin" / "geant4-config"
        if not config.is_file():
            raise SpecError(f"--prefix {tilde(expand(str(args.prefix)))} has no bin/geant4-config: not a Geant4 installation")
    config = config.resolve()
    version = config_query(config, "--version")
    prefix = Path(config_query(config, "--prefix")).resolve()
    refused = []
    if args.prefix and not same_dir(prefix, args.prefix):
        refused.append(f"geant4-config --prefix is {tilde(prefix)}, not --prefix {tilde(expand(str(args.prefix)))}")
    cxxstd = config_query(config, "--cxxstd")
    features = dict(re.findall(r"^\s*(\w[\w-]*)\[(yes|no)\]", config_query(config, "--features"), re.M))
    tls = subprocess.run([str(config), "--tls-model"], capture_output=True, text=True, timeout=120)
    listed = [ln.split(None, 2) for ln in config_query(config, "--datasets").splitlines() if ln.strip()]
    if any(len(x) != 3 for x in listed):
        raise SpecError("geant4-config --datasets: a line is not 'NAME VARIABLE PATH'")
    check_ds = capture([str(config), "--check-datasets"])
    cmake_dir = find_cmake_config(prefix)
    cm = {"version": None, "cxx_standard": None, "datasets": {}}
    if cmake_dir is None:
        refused.append(f"no Geant4Config.cmake under {tilde(prefix)} (lib/cmake/Geant4, lib64/cmake/Geant4): the "
                       "installation's CMake configuration is needed to cross-check the version and the datasets")
    else:
        cm = read_cmake_config(cmake_dir)
        if cm["version"] != version:
            refused.append(f"Geant4ConfigVersion.cmake says {cm['version']}, geant4-config --version {version}")
        if cm["cxx_standard"] and cm["cxx_standard"] != cxxstd:
            refused.append(f"Geant4Config.cmake C++ standard {cm['cxx_standard']} != geant4-config --cxxstd {cxxstd}")
    unknown_skip = sorted(set(args.skip_dataset or []) - {x[0] for x in listed})
    if unknown_skip:
        raise SpecError(f"--skip-dataset {unknown_skip}: not a dataset of this installation "
                        f"({', '.join(x[0] for x in listed)})")
    datasets, skipped = [], []
    for name, envvar, path in listed:
        if name in (args.skip_dataset or []):
            skipped.append({"name": name, "envvar": envvar, "reason": "--skip-dataset: left out by the user"})
            continue
        desc = cm["datasets"].get(name)
        if cm["datasets"] and desc is None:
            refused.append(f"{name}: listed by geant4-config but not by Geant4Config.cmake")
            continue
        if desc and desc["envvar"] != envvar:
            refused.append(f"{name}: geant4-config names {envvar}, Geant4Config.cmake {desc['envvar']}")
            continue
        m = TARBALL.fullmatch(desc["tarball"]) if desc else None
        base = Path(path).name
        dv = m.group(2) if m else (base[len(name):] if base.startswith(name) and base[len(name):] else None)
        if not dv:
            refused.append(f"{name}: the expected version cannot be read (tarball {desc and desc['tarball']}, "
                           f"folder {base})")
            continue
        if desc and not same_dir(desc["path"], path):
            refused.append(f"{name}: geant4-config path {tilde(path)} != Geant4Config.cmake {tilde(desc['path'])}")
            continue
        entry, why = resolve_dataset(name, envvar, path, dv, args.dataset_source)
        if why:
            refused.append(why)
            continue
        entry.update(md5_expected=desc["md5"] if desc else None, md5=None, md5_verified=None,
                     source="registered installation")
        datasets.append(entry)
    if refused:
        return "refused", {"refused": refused, "note": "no record written; fix the installation or the environment, "
                                                       "or leave a dataset out on purpose with --skip-dataset"}
    for d in datasets:
        d["content_sha256"], d["n_files"] = tree_hash(expand(d["path"]))
    listed_vars = {x[1] for x in listed}
    extra = sorted(v for v in DATA_VARS if v in os.environ and v not in listed_vars)
    probe = cmake_probe(cmake_dir, prefix) if not args.no_cmake_probe else {"ran": False,
                                                                            "reason": "--no-cmake-probe"}
    cxx = tool_version(args.compiler)
    cmake = tool_version("cmake")
    created = args.created or datetime.date.today().isoformat()
    cfg_sha = sha256_file(config)
    cmake_cfg = cmake_dir / "Geant4Config.cmake"
    ident = hashlib.sha256(f"{tilde(prefix)}\0{version}\0{cfg_sha}".encode()).hexdigest()[:8]
    info = {"version": version, "prefix": tilde(prefix), "cxxstd": cxxstd,
            "tls_model": tls.stdout.strip() if tls.returncode == 0 else None,
            "features": features, "has_multithreading": features.get("multithreading"),
            "check_datasets": check_ds,
            "check_datasets_note": "information only: checks that the compiled-in directories exist (a conda-forge "
                                   "installation reports NOTFOUND for folders it installs without the G4 prefix)"}
    record = {
        "contract_version": CONTRACTS_VERSION, "artifact_id": f"geant4-registered-{version}-{ident}",
        "artifact_type": "computational-run",
        "objective": f"Register the existing Geant4 {version} installation at {tilde(prefix)} for adapters/geant4 "
                     "(origin registered: not built by the adapter; source commit, build options and dataset MD5s "
                     "unknown)",
        "bindings": {"experiments": [], "theory": []},
        "versions": {"plugin": plugin_version(), "contracts": CONTRACTS_VERSION, "profiles": {}},
        "provenance": {"producer_skill": "hep-detector", "created": created, "evidence_ids": []},
        "inputs": [], "outputs": [], "unresolved_inputs": [], "status": ["unvalidated"],
        "extension": {
            "input_manifest": [{"path": tilde(config), "sha256": cfg_sha},
                               {"path": tilde(cmake_cfg), "sha256": sha256_file(cmake_cfg)}],
            "tools": [{"name": "Geant4", "version": f"{version} (registered installation, source commit unknown)",
                       "source": tilde(prefix)}, cmake, cxx],
            "commands": [f"{tilde(config)} {f}" for f in ("--version", "--prefix", "--cxxstd", "--tls-model",
                                                          "--features", "--datasets", "--check-datasets")],
            "environment": {"platform": platform.platform(), "machine": platform.machine(),
                            "python": platform.python_version(), "hosts_contacted": [],
                            "dataset_variables_set": {v: tilde(os.environ[v]) for v in DATA_VARS if v in os.environ}},
            "seeds": {}, "tolerances": {}, "exit_status": 0,
            "output_hashes": {d["path"]: d["content_sha256"] for d in datasets},
            "build": {"origin": "registered", "tag": None, "commit": None, "unknown": list(REGISTERED_UNKNOWN),
                      "cmake_options": {}, "cmake_cxx_standard": cxxstd,
                      "multithreaded": {"yes": "ON", "no": "OFF"}.get(features.get("multithreading")),
                      "install_prefix": tilde(prefix), "geant4_config": info, "datasets": datasets,
                      "datasets_skipped": skipped, "log": None, "step_exit_codes": [],
                      "registration": {"geant4_config": tilde(config), "geant4_config_sha256": cfg_sha,
                                       "cmake_config_dir": tilde(cmake_dir), "cmake_config": tilde(cmake_cfg),
                                       "cmake_config_sha256": sha256_file(cmake_cfg),
                                       "cmake_config_version": cm["version"],
                                       "dataset_source": args.dataset_source,
                                       "environment_variables_not_listed": extra,
                                       "cmake_probe": probe, "compiler_now": cxx, "cmake_now": cmake}}}}
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    warnings = []
    if probe.get("ran") and not probe.get("find_package_ok"):
        warnings.append("find_package(Geant4) fails for this installation: " + "; ".join(probe.get("errors", []))[:400]
                        + "; build the programs with geant4_run.py build-sim --configure-with geant4-config")
    if extra:
        warnings.append(f"{', '.join(extra)} set in the environment but not a dataset of this installation: runs "
                        "unset them")
    return "ok", {"record": str(args.record), "version": version, "prefix": tilde(prefix),
                  "datasets": [{k: d[k] for k in ("name", "version", "envvar", "path", "resolved_from",
                                                  "folder_name_match", "n_files")} for d in datasets],
                  "datasets_skipped": skipped, "cmake_probe": probe, "warnings": warnings,
                  "unknown": list(REGISTERED_UNKNOWN)}


def main(argv=None) -> int:
    ap = JsonArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build", help="clone, configure, build, install and fetch datasets; write the build record")
    p.add_argument("--spec", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True, help="work folder (src/, build/, install/, logs/ inside)")
    p.add_argument("--record", type=Path, required=True, help="where to write the computational-run record")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    p.add_argument("--created", help="the created date written into the record (default: today)")
    p = sub.add_parser("register", help="record an existing installation (no build): version, prefix, datasets")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--geant4-config", type=Path, help="the installation's geant4-config")
    g.add_argument("--prefix", type=Path, help="the installation prefix (holds bin/geant4-config)")
    p.add_argument("--record", type=Path, required=True, help="where to write the computational-run record")
    p.add_argument("--dataset-source", choices=("auto", "env", "config"), default="auto",
                   help="where each dataset folder is taken from (default auto: the variable if set, else geant4-config)")
    p.add_argument("--skip-dataset", action="append", metavar="NAME",
                   help="leave this dataset out of the record on purpose (repeatable)")
    p.add_argument("--compiler", default="c++", help="the C++ compiler the programs will be built with (recorded)")
    p.add_argument("--no-cmake-probe", action="store_true", help="skip the find_package(Geant4) probe")
    p.add_argument("--created", help="the created date written into the record (default: today)")
    p = sub.add_parser("check", help="compare an installation with its build or registration record")
    p.add_argument("--record", type=Path, required=True)
    for sp in sub.choices.values():
        add_status_argument(sp)
    args = ap.parse_args(argv)
    inputs = {k: tilde(v) if isinstance(v, Path) else v for k, v in vars(args).items() if k != "status"}
    given = {t.split("=")[0] for t in (sys.argv[1:] if argv is None else argv) if t.startswith("--")}
    defaults = [k for k in ("jobs", "created", "dataset_source", "compiler", "status")
                if f"--{k.replace('_', '-')}" not in given and hasattr(args, k)]
    try:
        status, doc = {"build": cmd_build, "register": cmd_register, "check": cmd_check}[args.command](args)
    except (SpecError, KeyError, json.JSONDecodeError) as exc:
        status, doc = "rejected", {"error": str(exc)}
    except subprocess.TimeoutExpired as exc:
        status, doc = "failed", {"error": f"timed out: {exc}"}
    except OSError as exc:
        status, doc = "failed", {"error": str(exc)}
    print(json.dumps({"status": status, "status_label": args.status, "inputs": inputs, "defaults_used": defaults,
                      **doc}, indent=1))
    return exit_code(status)


if __name__ == "__main__":
    sys.exit(main())
