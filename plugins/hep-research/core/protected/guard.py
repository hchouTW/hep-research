"""Protected-use mode at the formal-use entry points (task P1, C07, HC-09, K08, DP-2, DP-4).

Mode (DP-2): an entry point runs in protected mode when the project declares agent_policy, or when it is given
--protected (flag=True). The project is found from an explicit project directory, from every path the entry point
is given, and from the working directory, by looking upward for hep-research.project.json; any one of them with
agent_policy switches the mode on. Omitting a flag cannot switch it off. Outside protected mode nothing changes.

In protected mode establish() reads, as protected inputs (core.protected.trusted_input: regular files with one link
that the running account neither owns, nor can write, nor can replace along their path):
  1. the authoritative copy of agent_policy named by agent_policy.authoritative_copy {location, sha256}: the canonical
     JSON SHA-256 of its content without authoritative_copy must be that digest (the launcher's convention), and the
     content must equal the project's agent_policy without authoritative_copy;
  2. from it, protected_inputs {revocation_log, revocation_head, status_source, max_status_age_s,
     qualification_record}: the revocation log and head are verified (core.protected.revocation_log: an empty, cut,
     edited, truncated, replaced or stale log, or a head from another source, is refused);
  3. the qualification record (contracts/schemas/qualification_record.json): valid now, bound to the canonical SHA-256
     of the authoritative policy and to the running plugin's code identity (core.protected.identity), not revoked.
Formal use (use="formal": publication and other formal-analysis entry points) additionally needs a formal-use permit:
the entry point passes a check (contracts.permit.checker, task P5) that verifies it; without one it is refused.

guard() runs establish() (or reuses the context of the enclosing command, see protected_main) and then refuses an input
file or digest that the verified log revokes, and, when the caller gives its known capabilities, a JSON artifact among
the inputs that requires another capability. Every refusal is a ProtectedUseRefused with codes and paths, never a
value. Nothing here reports a use as allowed: formal_use_allowed is always false; whether a use proceeds is decided
outside the agent-run code. Lower-level functions call guard() themselves, so calling them directly does not skip it.

Limits (stated, not checked here): release_manifest.py and attestation.py are custodian tools run as the custodian
identity, which owns the protected inputs, so they are not guarded (their verdicts bind nothing in the session); a
context established for a command is reused for the library calls it makes and is not re-evaluated while it runs; a
path a nested call names in another project is judged under the command's context; the code identity covers source
files, not bytecode, so a planted timestamp-based `.pyc` matching its source is not detected (identity.verify() only
warns that bytecode is present).

Codes: protected.policy_missing, protected.policy_unanchored, protected.policy_anchor_mismatch,
protected.policy_differs, protected.inputs_missing, protected.qualification_malformed,
protected.qualification_not_valid_now, protected.qualification_other_policy, protected.qualification_other_plugin,
protected.qualification_revoked, protected.formal_use_unavailable, protected.input_revoked,
protected.unknown_capability, protected.input_unreadable, protected.config_unreadable, protected.input_malformed, plus the source.* codes of trusted_input and the revocation.* codes of revocation_log.
"""
from __future__ import annotations

import contextvars
import datetime
import functools
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from core.protected import identity
from core.protected.revocation_log import (MAX_STATUS_AGE_S, TIMESTAMP, RevocationStatus, canonical_sha256, load,
                                           parse_ts)
from core.protected.trusted_input import Account, read_protected

CONFIG_NAME = "hep-research.project.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
INPUT_KEYS = ("revocation_log", "revocation_head", "status_source", "max_status_age_s", "qualification_record")
NOTE = ("advisory: protected-use checks passed or failed; nothing here authorizes a use (formal_use_allowed is always "
        "false), and in-process checks do not stop a process that rewrites the code")
CURRENT: contextvars.ContextVar = contextvars.ContextVar("hep_research_protected_context", default=None)


def plugin_identity() -> dict:
    """The running plugin's {release, digest} (tests replace this function)."""
    return identity.plugin_release()


class ProtectedUseRefused(RuntimeError):
    def __init__(self, entry: str, refusals: list[dict]):
        self.entry, self.refusals = entry, refusals
        super().__init__(f"{entry}: protected use refused: " + ", ".join(sorted({r['code'] for r in refusals})))

    def report(self) -> dict:
        return {"status": "refused", "entry_point": self.entry, "protected": True, "refusals": self.refusals,
                "formal_use_allowed": False, "note": NOTE}


@dataclass
class Context:
    protected: bool
    reasons: list[str] = field(default_factory=list)
    refusals: list[dict] = field(default_factory=list)
    config: str | None = None
    policy: dict | None = None
    revocations: RevocationStatus | None = None
    qualification: dict | None = None

    @property
    def refused(self) -> bool:
        return bool(self.refusals)

    def report(self) -> dict:
        return {"protected": self.protected, "reasons": self.reasons, "refused": self.refused,
                "refusals": self.refusals, "config": self.config,
                "qualification_id": (self.qualification or {}).get("qualification_id"),
                "revocation_log": None if self.revocations is None else self.revocations.summary(),
                "formal_use_allowed": False, "note": NOTE}


def _refusal(code: str, path: str, message: str) -> dict:
    return {"code": code, "path": path, "message": message}


def _config_above(start: Path) -> Path | None:
    cur = start if start.is_dir() else start.parent
    for d in (cur, *cur.parents):
        cand = d / CONFIG_NAME
        if cand.is_file():
            return cand
    return None


def find_configs(paths=(), project=None) -> list[Path]:
    """Project configs that govern the given project directory, paths and the working directory (first found per
    start, upward), in that order, without duplicates."""
    starts: list[Path] = []
    raw = ([] if project is None else [project]) + list(paths)
    for p in raw:  # both the given and the link-free location: a link into a project must not hide it
        try:
            starts += [Path(p).absolute(), Path(os.path.realpath(p))]
        except (TypeError, ValueError, OSError):
            continue
    starts.append(Path.cwd())
    out: list[Path] = []
    for s in starts:
        try:
            c = _config_above(s)
        except OSError:
            c = None
        if c is not None and c not in out:
            out.append(c)
    return out


def detect(paths=(), flag: bool = False, project=None) -> tuple[bool, list[str], Path | None, dict | None]:
    """(on, reasons, config path, config) for the mode rule of DP-2 (see the module docstring)."""
    reasons = ["--protected given"] if flag else []
    chosen: tuple[Path | None, dict | None] = (None, None)
    fallback: tuple[Path | None, dict | None] = (None, None)
    for cfg_path in find_configs(paths, project):
        try:
            raw = cfg_path.read_bytes()
        except OSError:
            raw = None
        try:
            cfg = json.loads((raw or b"").decode("utf-8")) if raw is not None else None
        except (ValueError, UnicodeDecodeError, RecursionError):
            cfg = None
        if cfg is None:
            # an unreadable config cannot show that agent_policy is absent, nor can a malformed one that names it:
            # fail closed; a malformed config that does not name it stays outside protected mode, as before
            if raw is not None and b"agent_policy" not in raw:
                continue
            reasons.append(f"{cfg_path} cannot be read")
            if chosen[0] is None:
                chosen = (cfg_path, None)
            continue
        if isinstance(cfg, dict) and "agent_policy" in cfg:
            reasons.append(f"{cfg_path} declares agent_policy")
            if chosen[0] is None or chosen[1] is None:
                chosen = (cfg_path, cfg)
        elif fallback[0] is None and isinstance(cfg, dict):
            fallback = (cfg_path, cfg)
    if chosen[0] is None:
        chosen = fallback
    return bool(reasons), reasons, chosen[0], chosen[1]


def qualification_problem(q) -> str | None:
    """The rules of contracts/schemas/qualification_record.json written out (core cannot use the schema engine)."""
    keys = {"record_version", "qualification_id", "stage", "host", "plugin", "policy_sha256", "valid_from",
            "valid_until", "issued_by"}
    if not isinstance(q, dict) or set(q) != keys:
        return f"a qualification record has exactly {sorted(keys)}"
    host, plugin = q["host"], q["plugin"]
    if q["record_version"] != "1.0.0" or q["stage"] not in ("S1", "S2", "S3", "S4"):
        return "record_version 1.0.0 and a stage S1..S4"
    if not all(isinstance(q[k], str) and q[k] for k in ("qualification_id", "issued_by")):
        return "qualification_id and issued_by are non-empty"
    if not (isinstance(host, dict) and set(host) == {"surface", "effective_digest"} and isinstance(host["surface"], str)
            and host["surface"] and isinstance(host["effective_digest"], str) and HEX64.match(host["effective_digest"])):
        return "host is {surface, effective_digest (64 hex)}"
    if not (isinstance(plugin, dict) and set(plugin) == {"release", "digest"} and isinstance(plugin["release"], str)
            and VERSION.match(plugin["release"]) and isinstance(plugin["digest"], str) and HEX64.match(plugin["digest"])):
        return "plugin is {release (x.y.z), digest (64 hex)}"
    if not (isinstance(q["policy_sha256"], str) and HEX64.match(q["policy_sha256"])):
        return "policy_sha256 is 64 hex"
    if not all(isinstance(q[k], str) and TIMESTAMP.match(q[k]) for k in ("valid_from", "valid_until")):
        return "valid_from and valid_until are YYYY-MM-DDTHH:MM:SSZ"
    return None


def _json(data: bytes):
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        return None


def _source_refusals(chk, where: str) -> list[dict]:
    return [_refusal(code, where, msg) for code, msg in chk.refusals]


def establish(paths=(), flag: bool = False, project=None, use: str = "protected", now: datetime.datetime | None = None,
              account: Account | None = None) -> Context:
    """The protected-use context for an entry point: off, or on with its refusals (see the module docstring). Malformed
    input never raises: it is a refusal."""
    try:
        return _establish(paths, flag, project, use, now, account)
    except (ValueError, UnicodeError, RecursionError, TypeError, KeyError) as exc:
        return Context(protected=True, reasons=["protected inputs could not be evaluated"],
                       refusals=[_refusal("protected.input_malformed", "$", f"malformed protected input: {type(exc).__name__}")])


def _establish(paths, flag, project, use, now, account) -> Context:
    on, reasons, cfg_path, cfg = detect(paths, flag, project)
    if not on:
        return Context(protected=False)
    now = now or datetime.datetime.now(datetime.UTC)
    ctx = Context(protected=True, reasons=reasons, config=None if cfg_path is None else str(cfg_path))
    if cfg_path is not None and cfg is None:
        ctx.refusals.append(_refusal("protected.config_unreadable", "$config", "the project config cannot be read"))
        return ctx
    policy = (cfg or {}).get("agent_policy")
    if not isinstance(policy, dict):
        ctx.refusals.append(_refusal("protected.policy_missing", "$config",
                                     "protected mode needs a project config with agent_policy"))
        return ctx
    anchor = policy.get("authoritative_copy")
    if not (isinstance(anchor, dict) and isinstance(anchor.get("location"), str) and isinstance(anchor.get("sha256"), str)):
        ctx.refusals.append(_refusal("protected.policy_unanchored", "$config.agent_policy.authoritative_copy",
                                     "no authoritative copy: the project copy of agent_policy is agent-writable"))
        return ctx
    chk = read_protected(anchor["location"], account)
    if not chk.ok:
        ctx.refusals += _source_refusals(chk, "$policy")
        return ctx
    raw_auth = _json(chk.data or b"")
    # the launcher's convention (hep-claude policy_digest): the digest is the canonical JSON SHA-256 of the policy
    # without authoritative_copy, so the root-owned copy may be formatted freely and may name itself
    auth = {k: v for k, v in raw_auth.items() if k != "authoritative_copy"} if isinstance(raw_auth, dict) else None
    if auth is None or canonical_sha256(auth) != anchor["sha256"]:
        ctx.refusals.append(_refusal("protected.policy_anchor_mismatch", "$policy", "the authoritative copy has another digest"))
        return ctx
    if canonical_sha256(auth) != canonical_sha256({k: v for k, v in policy.items() if k != "authoritative_copy"}):
        ctx.refusals.append(_refusal("protected.policy_differs", "$policy",
                                     "the project's agent_policy differs from the authoritative copy"))
        return ctx
    ctx.policy = auth
    inputs = auth.get("protected_inputs")
    age = inputs.get("max_status_age_s") if isinstance(inputs, dict) else None
    if not (isinstance(inputs, dict) and set(INPUT_KEYS) <= set(inputs)
            and all(isinstance(inputs[k], str) and inputs[k] for k in INPUT_KEYS if k != "max_status_age_s")
            and isinstance(age, int) and not isinstance(age, bool) and 0 < age <= MAX_STATUS_AGE_S):
        ctx.refusals.append(_refusal("protected.inputs_missing", "$policy.protected_inputs",
                                     f"the authoritative policy must name {list(INPUT_KEYS)}"))
        return ctx
    rev = load(inputs["revocation_log"], inputs["revocation_head"], source=inputs["status_source"], now=now,
               max_age_s=age, protected=True, account=account)
    if rev.ok:
        ctx.revocations = rev
    else:
        ctx.refusals += [_refusal(f["code"], "$revocations" + f["path"].lstrip("$"), f["message"]) for f in rev.findings]
    qchk = read_protected(inputs["qualification_record"], account)
    if not qchk.ok:
        ctx.refusals += _source_refusals(qchk, "$qualification")
    else:
        q = _json(qchk.data or b"")
        problem = qualification_problem(q)
        if problem:
            ctx.refusals.append(_refusal("protected.qualification_malformed", "$qualification", problem))
        else:
            assert isinstance(q, dict)
            ctx.qualification = q
            vf, vu = parse_ts(q["valid_from"]), parse_ts(q["valid_until"])
            if vf is None or vu is None or not (vf <= now < vu):
                ctx.refusals.append(_refusal("protected.qualification_not_valid_now", "$qualification",
                                             "the qualification is expired or not yet valid"))
            if q["policy_sha256"] != canonical_sha256(auth):
                ctx.refusals.append(_refusal("protected.qualification_other_policy", "$qualification.policy_sha256",
                                             "the qualification binds another policy"))
            ident = plugin_identity()
            if (ident.get("release"), ident.get("digest")) != (q["plugin"]["release"], q["plugin"]["digest"]):
                ctx.refusals.append(_refusal("protected.qualification_other_plugin", "$qualification.plugin",
                                             "the running plugin is not the qualified release (or has no recorded identity)"))
            if rev.ok and any(rev.revoked(kind="qualification", ref=q["qualification_id"], sha256=d)
                              for d in (qchk.sha256, canonical_sha256(q))):
                ctx.refusals.append(_refusal("protected.qualification_revoked", "$qualification", "the qualification is revoked"))
    return ctx


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def input_refusals(ctx: Context, paths=(), digests=(), capabilities=None) -> list[dict]:
    """Refusals for inputs a verified log revokes, and for JSON artifacts requiring a capability not in `capabilities`."""
    out: list[dict] = []
    revs = ctx.revocations
    base = Path(ctx.config).parent if ctx.config else None
    revoked_refs = set()
    if revs is not None and base is not None:  # artifact events that name a project path instead of a digest
        for ev in revs.events:
            s = ev["subject"]
            if s["kind"] in ("artifact", "recipe") and "ref" in s:
                revoked_refs.add(os.path.realpath(base / s["ref"]))
    for p in paths:
        try:
            path = Path(p)
            if path.is_dir():
                continue  # a directory is not an input file; the files read from it are checked where they are read
            digest = _sha256_file(path)
        except (OSError, TypeError, ValueError) as exc:
            out.append(_refusal("protected.input_unreadable", str(p), f"cannot be checked: {type(exc).__name__}"))
            continue
        doc = None
        if path.suffix.lower() == ".json":
            try:
                doc = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, UnicodeDecodeError, RecursionError):
                doc = None
        digests_here = {digest}
        if doc is not None:
            try:
                digests_here.add(canonical_sha256(doc))
            except (ValueError, UnicodeEncodeError, RecursionError):
                pass
        if revs is not None and (any(revs.revoked(sha256=d) for d in digests_here)
                                 or os.path.realpath(path) in revoked_refs):
            out.append(_refusal("protected.input_revoked", str(p), "this input is revoked"))
        if capabilities is not None and doc is not None:
            caps = doc.get("required_capabilities") if isinstance(doc, dict) else None
            unknown = sorted(c for c in caps or [] if isinstance(c, str) and c not in capabilities) if isinstance(caps, list) else []
            if unknown:
                out.append(_refusal("protected.unknown_capability", str(p),
                                    f"requires capabilities this reader does not implement: {unknown}"))
    for d in digests:
        if revs is not None and isinstance(d, str) and revs.revoked(sha256=d.lower()):
            out.append(_refusal("protected.input_revoked", f"sha256:{d[:12]}", "this input is revoked"))
    return out


def guard(entry: str, *, paths=(), flag: bool = False, project=None, use: str = "protected", context: Context | None = None,
          digests=(), capabilities=None, now: datetime.datetime | None = None, account: Account | None = None,
          formal_check=None, formal_paths=None) -> Context:
    """The context for one call of an entry point; raises ProtectedUseRefused in protected mode when anything is refused.
    Outside protected mode it returns an off context and changes nothing. For use="formal", formal_check(ctx, paths)
    returns the refusals of the formal-use permit (contracts.permit.checker); without it formal use is refused.
    formal_paths are the inputs the formal use reads (default: paths)."""
    paths = [p for p in paths if p is not None]
    ctx = context if context is not None else CURRENT.get()
    if ctx is None or not ctx.protected:  # an off context is re-decided for these paths: they may lie in a project
        ctx = establish(paths, flag, project, use, now, account)
    if not ctx.protected:
        return ctx
    refusals = [r for r in ctx.refusals if r["code"] != "protected.formal_use_unavailable"]
    if not refusals:
        refusals = input_refusals(ctx, paths, digests, capabilities)
    if use == "formal" and not refusals:
        if formal_check is None:
            refusals.append(_refusal("protected.formal_use_unavailable", "$use",
                                     "formal use in protected mode needs a formal-use permit (--permit)"))
        else:
            refusals = list(formal_check(ctx, paths if formal_paths is None else list(formal_paths)))
    if refusals:
        raise ProtectedUseRefused(entry, refusals)
    return ctx


def report_findings(exc: ProtectedUseRefused) -> list[tuple[str, str, str]]:
    """(path, code, message) per refusal, for entry points that return a report instead of raising."""
    return [(r["path"], r["code"], r["message"]) for r in exc.refusals]


def _argv_paths(args: list[str]) -> list[str]:
    out = []
    for a in args:
        cand = a.split("=", 1)[1] if a.startswith("--") and "=" in a else a
        if cand and not cand.startswith("-") and len(cand) < 4096:
            try:
                if os.path.exists(cand):
                    out.append(cand)
            except (OSError, ValueError):
                continue
    return out


def protected_main(entry: str, *, use: str = "protected", capabilities=None, keep_flag: bool = False,
                   formal_check_factory=None, formal_inputs=()):
    """Wrap a command-line main(argv): establish the context from the paths in argv and --protected (removed from argv
    unless keep_flag), refuse with exit 3 and a fixed JSON report, otherwise run main with the context set for the
    library calls it makes. Outside protected mode main runs unchanged. For use="formal", formal_check_factory(path)
    builds the permit check from the value of --permit in argv (None when absent), and the permit must cover the
    values of the formal_inputs flags (the files the use reads)."""
    def deco(main):
        @functools.wraps(main)
        def wrapper(argv=None, *extra, **kw):
            args = list(sys.argv[1:] if argv is None else argv)
            flag = "--protected" in args
            if flag and not keep_flag:
                args = [a for a in args if a != "--protected"]
            permit = None
            if "--permit" in args and args.index("--permit") + 1 < len(args):
                permit = args[args.index("--permit") + 1]
            check = formal_check_factory(permit) if (use == "formal" and formal_check_factory and permit) else None
            paths = [p for p in _argv_paths(args) if p != permit]
            formal_paths = [args[i + 1] for i, a in enumerate(args[:-1]) if a in formal_inputs]
            try:
                ctx = guard(entry, paths=paths, flag=flag, use=use, capabilities=capabilities, formal_check=check,
                            formal_paths=formal_paths)
            except ProtectedUseRefused as exc:
                print(json.dumps(exc.report(), indent=1))
                return 3
            token = CURRENT.set(ctx)
            try:
                return main(args, *extra, **kw)
            except ProtectedUseRefused as exc:
                print(json.dumps(exc.report(), indent=1))
                return 3
            finally:
                CURRENT.reset(token)
        return wrapper
    return deco
