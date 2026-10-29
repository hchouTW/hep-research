#!/usr/bin/env python3
"""hep-review CLI: the coordinator's commands for a recorded, tiered review (protocol hep-review/1).

Commands (every one prints JSON with a "status" key; exit 0 ok, 1 negative verdict, 2 bad input, 3 incomplete):
  r0 --bundle FILE                          R0 consultation from {"intent", "plan", "answers"}; no store is created
  start --context ID --state FILE [--checkpoint LINE]
                                            begin a session: anchor on the checkpoint or record an unanchored start
  append --context ID --state FILE --objects FILE --operation-id ID
                                            commit a JSON list of objects after the store's admission checks
  snapshot --root DIR --paths P [P ...]     controlled reading of materials into store blobs; prints manifest entries
  assign --context ID --state FILE --actor NAME --spec-id ID --plan-revision N --via agent-tool|same-context
         [--invocation-id ID] [--authors-declared]
                                            build and commit an assignment from the host profile (never by hand)
  packets --context ID --assignment ID --drop-root DIR --out FILE
                                            write the packet text for an assignment (snapshot paths, drop path)
  supply --context ID --state FILE --assignment ID --source S --reason R [--contains-evaluation]
                                            commit material supplied to a dispatched reviewer
  ingest --context ID --state FILE --assignment ID --drop-root DIR [--digest HEX]
                                            read a drop file by bytes, derive the record and commit it
  report --context ID --state FILE          layer 1 + layer 2 report, ending with the checkpoint line
  checkpoint --context ID                   the checkpoint line to hand to the user
  export --context ID --out FILE            export the head segment
  verify-export FILE [--checkpoint LINE]    internal consistency and integrity against a checkpoint
  import FILE --state FILE [--checkpoint LINE] --into DIR
                                            verify, then rebuild a store from an export
Common: --store DIR (default $XDG_STATE_HOME/hep-research/hep-review or ~/.local/state/hep-research/hep-review).
The checkpoint line must be copied from tool output, never retyped. Nothing here certifies physics as correct.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # importing siblings and plugin packages leaves no __pycache__ (F-10)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2]))

from contracts import hep_review as H  # noqa: E402
from hep_review_support import continuity as C  # noqa: E402
from hep_review_support import coordinator as K  # noqa: E402
from hep_review_support import export as X  # noqa: E402
from hep_review_support import materials as M  # noqa: E402
from hep_review_support import store as S  # noqa: E402


def emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, indent=1, sort_keys=True, default=str))
    return code


def read_json(path: str):
    return H.ingest_json(Path(path).read_bytes(), max_depth=128)


def open_store(args) -> S.Store:
    return S.Store(Path(args.store) if args.store else S.default_store_dir())


def load_state(path: str) -> C.CoordinatorState:
    return C.CoordinatorState.from_json(Path(path).read_text(encoding="utf-8"))


def save_state(path: str, st: C.CoordinatorState) -> None:
    Path(path).write_text(st.to_json() + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="hep-review coordinator CLI (protocol hep-review/1).",
                                epilog="Every command prints JSON with a status key.")
    p.add_argument("--store", help="store directory (default: the private state directory)")
    sub = p.add_subparsers(dest="command", required=True)
    r0 = sub.add_parser("r0", help="R0 consultation, nothing stored")
    r0.add_argument("--bundle", required=True)
    s = sub.add_parser("start", help="begin a coordinator session")
    s.add_argument("--context", required=True)
    s.add_argument("--state", required=True)
    s.add_argument("--checkpoint")
    s.add_argument("--session", default="coordinator")
    a = sub.add_parser("append", help="commit objects")
    a.add_argument("--context", required=True)
    a.add_argument("--state", required=True)
    a.add_argument("--objects", required=True)
    a.add_argument("--operation-id", required=True)
    sn = sub.add_parser("snapshot", help="capture materials")
    sn.add_argument("--root", required=True)
    sn.add_argument("--paths", nargs="+", required=True)
    asg = sub.add_parser("assign", help="build and commit an assignment from the host profile")
    asg.add_argument("--context", required=True)
    asg.add_argument("--state", required=True)
    asg.add_argument("--actor", required=True)
    asg.add_argument("--spec-id", required=True)
    asg.add_argument("--plan-revision", type=int, required=True)
    asg.add_argument("--via", required=True, choices=["agent-tool", "same-context", "other"])
    asg.add_argument("--invocation-id", help="the host's dispatch record (Agent-tool invocation id)")
    asg.add_argument("--authors-declared", action="store_true", help="the manifest's author lists are declared")
    pk = sub.add_parser("packets", help="write the packet for an assignment")
    pk.add_argument("--context", required=True)
    pk.add_argument("--assignment", required=True)
    pk.add_argument("--drop-root", required=True)
    pk.add_argument("--out", required=True)
    su = sub.add_parser("supply", help="commit material supplied to a dispatched reviewer")
    su.add_argument("--context", required=True)
    su.add_argument("--state", required=True)
    su.add_argument("--assignment", required=True)
    su.add_argument("--source", required=True)
    su.add_argument("--reason", required=True)
    su.add_argument("--contains-evaluation", action="store_true")
    i = sub.add_parser("ingest", help="read a drop file, derive and commit the record")
    i.add_argument("--state", required=True)
    i.add_argument("--context", required=True)
    i.add_argument("--assignment", required=True)
    i.add_argument("--drop-root", required=True)
    i.add_argument("--digest")
    r = sub.add_parser("report", help="two-layer report and checkpoint")
    r.add_argument("--context", required=True)
    r.add_argument("--state", required=True)
    c = sub.add_parser("checkpoint", help="checkpoint line")
    c.add_argument("--context", required=True)
    e = sub.add_parser("export", help="export a segment")
    e.add_argument("--context", required=True)
    e.add_argument("--out", required=True)
    v = sub.add_parser("verify-export", help="verify an export")
    v.add_argument("file")
    v.add_argument("--checkpoint")
    im = sub.add_parser("import", help="verify and import an export")
    im.add_argument("file")
    im.add_argument("--state", required=True)
    im.add_argument("--into", required=True)
    im.add_argument("--checkpoint")
    im.add_argument("--session", default="coordinator")
    return p


def run(args) -> int:
    cmd = args.command
    if cmd == "r0":
        b = read_json(args.bundle)
        out = K.r0_report(b["intent"], b["plan"], b["answers"])
        return emit({"status": "ok", "tier": "R0", "text": out["text"], "layer1": out["layer1"]}, 0)
    if cmd == "verify-export":
        if not Path(args.file).is_file():
            return emit({"status": "rejected", "message": f"no export file {args.file}"}, 2)
        cp =C.parse_checkpoint(args.checkpoint) if args.checkpoint else None
        r = X.verify_export(args.file, cp)
        ok = r["internal_consistency"] == "ok" and r["checkpoint"] != "mismatch"
        return emit(dict(r, status="ok" if ok else "refused"), 0 if ok else 1)
    if cmd == "import":
        cp = C.parse_checkpoint(args.checkpoint) if args.checkpoint else None
        loc = S.check_location(Path(args.into).parent)
        st0, st = X.import_export(args.file, cp, args.into, location=loc, session_id=args.session)
        save_state(args.state, st)
        status = C.head_continuity(st0, st)
        st0.close()
        return emit({"status": "ok", "head_continuity": status}, 0)
    store = open_store(args)
    try:
        if cmd == "start":
            cp = C.parse_checkpoint(args.checkpoint) if args.checkpoint else None
            st = C.start_session(store, args.context, args.session, cp)
            save_state(args.state, st)
            return emit({"status": "ok", "start": st.start, "head_continuity": C.head_continuity(store, st)}, 0)
        if cmd == "append":
            st = load_state(args.state)
            objs = read_json(args.objects)
            res = C.append(store, st, objs if isinstance(objs, list) else [objs], args.operation_id)
            save_state(args.state, st)
            return emit({"status": "ok", "result": res.status, "head": res.head}, 0)
        if cmd == "snapshot":
            m = M.snapshot(args.root, args.paths, store.dir / "blobs")
            return emit({"status": "ok" if not m["coverage_gaps"] else "incomplete", **m}, 0 if not m["coverage_gaps"]
                        else 3)
        if cmd in ("ingest", "packets", "supply"):
            objs = [o for c in store.load_bundle(args.context)["commits"] for o in c["objects"]]
            asg = next(o for o in objs if o["record_kind"] == "assignment" and o["id"] == args.assignment)
        if cmd == "ingest":  # parse and commit in one call: the record is never retyped (spec 12.4)
            st = load_state(args.state)
            rec = K.ingest(store, args.context, asg, args.drop_root, args.digest)
            res = C.append(store, st, [rec], f"op-ingest-{asg['id']}-{rec['raw_submission_ref']['digest'][:12]}")
            save_state(args.state, st)
            return emit({"status": "ok", "result": res.status, "head": res.head, "record_id": rec["id"],
                         "fidelity": rec["submission_fidelity"], "limitations": rec["limitations"]}, 0)
        if cmd == "assign":
            st = load_state(args.state)
            a = K.make_assignment(store, args.context, K.load_host_profile(),
                                  {"via": args.via, "actor": args.actor, "authors_declared": args.authors_declared,
                                   "invocation_id": args.invocation_id}, spec_id=args.spec_id,
                                  plan_revision=args.plan_revision)
            res = C.append(store, st, [a], f"op-assign-{a['id']}")
            save_state(args.state, st)
            return emit({"status": "ok", "assignment": a["id"], "conditions": a["conditions"], "head": res.head}, 0)
        if cmd == "packets":
            text = K.packet_for(store, args.context, asg, args.drop_root)
            Path(args.out).write_text(text, encoding="utf-8")
            return emit({"status": "ok", "packet": args.out, "drop": str(K.drop_path(args.drop_root, asg["id"]))}, 0)
        if cmd == "supply":
            st = load_state(args.state)
            supplied = K.supply(store, args.context, asg, source=args.source, reason=args.reason,
                           contains_evaluation=args.contains_evaluation)
            res = C.append(store, st, [supplied], f"op-{supplied['id']}")
            save_state(args.state, st)
            return emit({"status": "ok", "supply": supplied["id"], "head": res.head}, 0)
        if cmd == "report":
            out = K.report(store, load_state(args.state), args.context)
            return emit({"status": "ok", "text": out["text"], "checkpoint": out["checkpoint"],
                         "attestation": out["attestation"]}, 0)
        if cmd == "checkpoint":
            return emit({"status": "ok", "checkpoint": C.checkpoint_line(store, args.context)}, 0)
        if cmd == "export":
            return emit(X.export(store, args.context, args.out), 0)
    finally:
        store.close()
    return emit({"status": "rejected", "message": f"unknown command {cmd}"}, 2)


def main(argv=None) -> int:
    try:
        args = parser().parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    try:
        return run(args)
    except (H.IngestError, H.BundleError, ValueError, KeyError, FileNotFoundError, StopIteration) as e:
        return emit({"status": "rejected", "message": f"{type(e).__name__}: {e}"}, 2)
    except (S.AdmissionRefused, S.HeadMismatch, S.OperationConflict, C.ContinuityBroken, X.ImportRefused,
            M.ReadRefused) as e:
        return emit({"status": "refused", "message": f"{type(e).__name__}: {e}"}, 1)
    except S.StoreLocationRefused as e:
        return emit({"status": "refused", "message": str(e)}, 1)


if __name__ == "__main__":
    sys.exit(main())
