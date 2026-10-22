"""v6.3 D08 run cases (M2c, run-lineage/v1): RUN-CHAIN and RUN-CAMPAIGN on the reduced positive case, with the
result binding written after execution (docs/dev/cross-artifact-check/m2c-design.md). Everything is synthetic and written inside the
given folder; the campaign is a core.partition campaign run with LocalExecutor in that folder, with an execution
bundle frozen by the test (the fake-scheduler example has no freeze step and is not changed)."""
from __future__ import annotations

import copy
import hashlib
import json
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "contracts"))
import analysis_check_cases as cases  # noqa: E402

RUN_SUITE = {"id": "run-lineage", "version": "1.0.0"}
ROOT_ID = "flux-proton-p1"
SCOPE = "species:proton/period:synthetic-period-1"
UNIT = "1/(m2 sr s GV)"
BINNING = {"item": "spec", "pointer": "/extension/observable/variables/0/edges"}
VALUE = 123.456789  # a result value of the synthetic fixture; it must never appear in a report (V70)
AGENT = {"kind": "agent", "id": "claude-code"}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(Path(p).read_bytes())


def run_doc(run_id: str, inputs: list[tuple[str, str]], outputs: dict, exit_status: int = 0, status=("synthetic",)) -> dict:
    from contracts import CONTRACTS_VERSION
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": run_id, "artifact_type": "computational-run",
            "objective": "synthetic v6.3 run-lineage fixture",
            "versions": {"plugin": "0.12.0", "contracts": CONTRACTS_VERSION, "profiles": {}},
            "provenance": {"producer_skill": "hep-computing", "created": "2026-10-16"},
            "inputs": [], "outputs": [], "status": sorted(set(status) | {"unvalidated"}), "unresolved_inputs": [],
            "extension": {"input_manifest": [{"path": p, "sha256": s} for p, s in inputs], "tools": [], "commands": [],
                          "environment": {}, "seeds": {}, "tolerances": {}, "exit_status": exit_status,
                          "output_hashes": dict(outputs)}}


def dataset_record(status: str = "synthetic", dataset_id: str = "synthetic-events-p1") -> dict:
    """The data a run reads, as a frozen dataset record with a dataset status (DR-7: blinding is judged by lineage)."""
    from contracts import CONTRACTS_VERSION
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": dataset_id, "artifact_type": "dataset-record",
            "status": [status] if status in ("synthetic", "simulated") else [], "inputs": [], "outputs": [],
            "extension": {"dataset_id": f"synthetic:{dataset_id}", "source_evidence_ids": [], "status": status,
                          "observable": {"name": "synthetic event counts"}, "covariance": {"status": "absent"}}}


def with_run_lineage(variant=None, data_status: str = "synthetic"):
    """Variant: the run-lineage suite and the data the runs read, on check-context 1.1.0 and the newest 1.1.0
    pre-release suites (release R2: the 1.0.0 run-lineage suite names r-run.binding and r-run.blinding 1.0.0, which
    this checker no longer runs)."""
    def v(c):
        c.context["suites"] = [dict(RUN_SUITE)]
        c.add("dataset-record", "events-p1", "data/events-p1.json", dataset_record(data_status))
        if variant:
            variant(c)
        cases.context_1_1(c)
    return v


class Post:
    """The post-execution state of a frozen case: files written by runs, run records and the binding draft."""

    def __init__(self, root: Path, bundle_path: Path):
        self.root, self.bundle_path = Path(root), Path(bundle_path)
        self.bundle = json.loads(self.bundle_path.read_text())
        lock = next(i for i in self.bundle["items"] if i["role"] == "semantic-lock")
        self.binding = {"binding_version": "1.1.0", "kind": "result-binding",
                        "analysis_bundle_sha256": self.bundle["bundle_digest"], "semantic_lock_sha256": lock["sha256"],
                        "asserted_by": dict(AGENT), "runs": [], "campaigns": [], "results": []}

    def write(self, rel: str, content) -> str:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        data = content if isinstance(content, bytes) else (content if isinstance(content, str) else json.dumps(content, indent=1)).encode()
        p.write_bytes(data)
        return sha_bytes(data)

    def add_run(self, run_id: str, inputs: list[dict], outputs: dict, exit_status: int = 0, ref: str | None = None,
                base: str = "") -> dict:
        """inputs: [{path, source}] with the input's actual bytes digest read from the file; outputs: {path: content}."""
        out_hashes = {p: self.write(p, content) for p, content in outputs.items()}
        manifest = [(i["path"], sha_file(self.root / base / i["path"])) for i in inputs]
        ref = ref or f"runs/{run_id}.computational-run.json"
        doc = run_doc(run_id, manifest, out_hashes, exit_status)
        rec = {"run_id": run_id, "ref": ref, "sha256": self.write(ref, doc), "base": base,
               "inputs": [{"path": i["path"], "source": i["source"]} for i in inputs]}
        self.binding["runs"].append(rec)
        return rec

    def rewrite_run(self, run_id: str, edit) -> None:
        """Edit a run record after the fact (a synthetic tampering case) and keep the binding's digest of it current."""
        rec = next(r for r in self.binding["runs"] if r["run_id"] == run_id)
        doc = json.loads((self.root / rec["ref"]).read_text())
        edit(doc)
        rec["sha256"] = self.write(rec["ref"], doc)

    def result(self, file: str, producer: dict, status=("synthetic",), **over) -> dict:
        r = {"root": ROOT_ID, "file": file, "sha256": sha_file(self.root / file), "producer": producer, "unit": UNIT,
             "scope": SCOPE, "binning": dict(BINNING), "status": list(status)}
        r.update(over)
        self.binding["results"] = [x for x in self.binding["results"] if x["root"] != r["root"]] + [r]
        return r

    def save(self, rel: str = "post/result-binding.json") -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.binding, indent=1))
        return p

    def check(self, project: dict | None = None, snapshots=None, binding=True, view_edit=None):
        from contracts import analysis_check as ac
        view, diags = ac.load_subject(self.bundle_path, self.root)
        if view_edit:
            view_edit(view)
        res = json.loads(self.save().read_text()) if binding else None
        return ac.evaluate(view, diags, results=res, blinding=project, snapshots=snapshots)


def result_artifact(status=("synthetic",), artifact_id: str = "flux-proton-p1-result") -> dict:
    from contracts import CONTRACTS_VERSION
    return {"contract_version": CONTRACTS_VERSION, "artifact_id": artifact_id, "artifact_type": "statistical-result",
            "status": list(status), "extension": {"values": [VALUE, VALUE * 2]}}


def run_chain(root: Path, variant=None, spec_variant=None, status=("synthetic",), snapshots=None,
              data_status: str = "synthetic", with_data: bool = True) -> Post:
    """RUN-CHAIN: run A reads the frozen spec, recipe and a dataset record (dataset status data_status) and writes an
    intermediate product; run B reads that product through an explicit product binding and writes the root's result.
    with_data False: run A records no data input (its lineage has no data leaf)."""
    if snapshots is None:
        bundle = cases.positive_case(root, with_run_lineage(spec_variant, data_status))
    else:
        from contracts import analysis_check as ac
        c = cases.positive_case(root, with_run_lineage(spec_variant, data_status), freeze=False)
        c.write()
        bundle = root / "bundle.json"
        bundle.write_text(json.dumps(ac.freeze(c.root, "case-positive", c.items, c.context, snapshots=snapshots)))
    post = Post(root, bundle)
    post.add_run("run-a", [{"path": "spec.json", "source": {"item": "spec"}},
                           {"path": "recipe.json", "source": {"item": "flux-reduced"}}]
                 + ([{"path": "data/events-p1.json", "source": {"item": "events-p1"}}] if with_data else []),
                 {"work/counts.json": {"counts": [10, 20, 30]}})
    post.add_run("run-b", [{"path": "work/counts.json", "source": {"product": {"run": "run-a", "output": "work/counts.json"}}}],
                 {"results/flux.json": result_artifact(status)})
    post.result("results/flux.json", {"run": "run-b"}, status)
    if variant:
        variant(post)
    return post


# --- RUN-CAMPAIGN ---------------------------------------------------------------------------------------------
WORKER = """
import json, sys
a = dict(zip(sys.argv[1::2], sys.argv[2::2]))
start, stop = int(a["--start"]), int(a["--stop"])
json.dump({"n": stop - start, "sum": sum(range(start, stop))}, open(a["--out"], "w"))
"""


def campaign_artifact(cdir: Path, executor) -> dict:
    sys.path.insert(0, str(ROOT / "adapters" / "batch-schedulers"))
    import batch_campaign
    return batch_campaign.build_artifact(cdir, {"backend": "local", "limits": {"max_total_jobs": 8}}, executor,
                                         ["synthetic"], "synthetic v6.3 run-lineage campaign")


# what the campaign read (result binding 1.1.0, G6): the frozen spec and recipe and the dataset record
CAMPAIGN_INPUTS = ({"path": "spec.json", "source": {"item": "spec"}},
                   {"path": "recipe.json", "source": {"item": "flux-reduced"}},
                   {"path": "data/events-p1.json", "source": {"item": "events-p1"}})


def run_campaign(root: Path, records=None, spec_variant=None, after=None) -> Post:
    """RUN-CAMPAIGN: a two-submission LocalExecutor campaign (pilot chunk, then the rest) with an execution bundle
    frozen first, the adapter's computational-run as the interface record, and the merge result written to a file.
    records(post, cdir) may edit the agent-writable records afterwards (synthetic tampering cases)."""
    from core.partition import bundle as bd
    from core.partition import campaign as cp
    from core.partition import engine
    from core.partition.executors import LocalExecutor
    bundle = cases.positive_case(root, with_run_lineage(spec_variant))
    post = Post(root, bundle)
    worker = root / "worker"
    worker.mkdir(parents=True)
    (worker / "work.py").write_text(WORKER)
    lock = root / "worker-env.lock"
    lock.write_text("synthetic environment\n")
    q = shlex.quote
    cmd = f"{q(sys.executable)} {q(str(worker / 'work.py'))} --start {{start}} --stop {{stop}} --seed {{seed}} --out {{out}} --id {{id}}"
    cdir = cp.init(root / "campaign", engine.make_manifest("synthetic-run-lineage", 12, 4, 5), cmd)
    cfg = {"limits": {"max_total_jobs": 8}}
    digest = bd.freeze(cdir, worker, lock, scope="synthetic test", config=cfg, config_hash=bd.config_hash(cfg))["bundle_digest"]
    ex = LocalExecutor()
    cp.submit(cdir, ex, cfg, approved=True, pilot=True, bundle_digest=digest)
    cp.submit(cdir, ex, cfg, approved=True, bundle_digest=digest)
    cp.poll(cdir, ex)
    merged = cp.merge(cdir)
    assert merged["status"] == "complete", merged
    post.cdir, post.executor, post.exec_digest = cdir, ex, digest
    if records:
        records(post, cdir)
    art = campaign_artifact(cdir, ex)
    run_sha = post.write("runs/campaign.computational-run.json", art)
    _, state = cp.load(cdir)
    post.write("results/merged.json", merged["merged"])
    post.binding["campaigns"] = [{"campaign_uid": state["campaign_uid"], "dir": "campaign",
                                  "run_ref": "runs/campaign.computational-run.json", "run_sha256": run_sha,
                                  "execution_bundle_sha256": digest, "inputs": [dict(i) for i in CAMPAIGN_INPUTS]}]
    post.result("results/merged.json", {"campaign": state["campaign_uid"]})
    if after:  # edits of the records after the interface record was written (synthetic tampering cases)
        after(post, cdir)
    return post


def edit_state(cdir: Path, edit) -> None:
    p = Path(cdir) / "state.json"
    state = json.loads(p.read_text())
    edit(state)
    p.write_text(json.dumps(state, indent=1))


def deep(obj):
    return copy.deepcopy(obj)
