"""Test harness for the independent review mechanism (docs/dev/independent-review-spec.md, P1): a synthetic design
note, an in-process driver for skills/hep-authoring/scripts/review.py with a fixed clock, seed and observation input,
and scripted reviewer and arbiter agents that write records from their packets. All data is synthetic.

The scripted reviewer is a test double: it reads the private canary file to place its control findings, which a real
reviewer never can (spec 10, deliberate fraud is out of scope)."""
from __future__ import annotations

import contextlib
import copy
import datetime
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills" / "hep-authoring" / "scripts"
for _p in (str(PLUGIN), str(SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import review as DRV  # noqa: E402
from contracts import review as R  # noqa: E402

LICENSE = PLUGIN / "LICENSE"
AUTHOR = "author-agent"

DOC = """# Review fixture: a small design note

## 1. Scope

This note is synthetic test data for the independent review mechanism.
The license header is at `LICENSE:2-3`, and the grant of rights starts at `LICENSE:10-11`.
The definitions heading is at `LICENSE:8` of the plugin.
`LICENSE` is version 2.0 of the Apache terms, dated January 2004.
The review schema is `contracts/schemas/review_config.json`, and every config must validate.

## 2. Rules

| Row | Rule |
|---|---|
| 1 | A slot must be dispatched before it can be received. |
| 2 | A record must cite at most 3 contiguous units per claim. |
| 3 | A finding must quote the text it challenges. |
| 4 | An arbiter must differ from both parties. |

As row 2 says, claims stay short and must be contiguous.
As row 4 says, arbiters must be independent of the parties.
Section §3 lists what a finding must contain, and §4 lists the process steps.

## 3. Findings

A finding names its `units`, quotes a `value` and proposes a `correction`.
Each record lists its `claims` with their `verdicts`.
The `limitations` field records what was not checked.
Reviewers keep their notes in the `work` folder.
Every finding has a `severity` label.
A `fix` proposes the edit.

## 4. Process

1. Run start, then next until it says stop.
2. Pass the dispatch message to a new agent:

   ```
   Read and follow the instruction file below exactly.
   REVIEW-DISPATCH nonce=<nonce>
   ```

3. Run returned when the host reports the agent has finished.

審查必須在 3 倍的時間內完成，否則一律退回。
每個 claim 至多引用 3 個單位。
"""

OBS = {"host": {"name": "claude-code", "precondition": "fork-disabled-env", "session_start": None,
                "settings_mtime": None, "settings": {}},
       "instruction_files": {"/fixture/CLAUDE.md": "a" * 64}, "shared_dirs": [], "git_head": None}


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Harness:
    """One synthetic project and private directory, driven in-process with a minute-by-minute clock."""

    def __init__(self, root: Path, doc: str = DOC, config: dict | None = None, seed: str = "7", obs: dict | None = None):
        self.root = Path(root)
        self.project = self.root / "project"
        self.state = self.root / "state"
        self.obs_path = self.root / "observation.json"
        self.doc_rel = "docs/note.md"
        self.t = datetime.datetime(2026, 1, 1, 9, 0, tzinfo=datetime.UTC)
        self.seed = seed
        self.config = config if config is not None else {"config_version": "1.0.0", "models": ["model-a", "model-b"]}
        self.obs = copy.deepcopy(obs if obs is not None else OBS)
        self.log = []

    # setup and commands
    def setup(self):
        (self.project / "docs").mkdir(parents=True, exist_ok=True)
        (self.project / "reviews").mkdir(parents=True, exist_ok=True)
        self.state.mkdir(parents=True, exist_ok=True)
        self.write_doc(DOC if not (self.project / self.doc_rel).exists() else self.read_doc())
        (self.project / "reviews" / "review-config.json").write_text(json.dumps(self.config, indent=1), encoding="utf-8")
        self.save_obs()
        return self

    def save_obs(self):
        self.obs_path.write_text(json.dumps(self.obs), encoding="utf-8")

    def now(self, minutes: int = 1) -> str:
        self.t += datetime.timedelta(minutes=minutes)
        return self.t.strftime("%Y-%m-%dT%H:%M:%SZ")

    def run(self, *argv, minutes: int = 1, expect=None) -> dict:
        args = list(argv) + ["--project", str(self.project), "--now", self.now(minutes), "--observation", str(self.obs_path)]
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"XDG_STATE_HOME": str(self.state)}), contextlib.redirect_stdout(buf):
            code = DRV.main(args)
        out = json.loads(buf.getvalue())
        out["_exit"] = code
        self.log.append((argv[0], out.get("action") or out.get("status")))
        if expect is not None and code != expect:
            raise AssertionError(f"{argv} exited {code}: {out}")
        return out

    def start(self):
        return self.run("start", self.doc_rel, "--seed", self.seed, expect=0)

    def next(self):
        return self.run("next")

    # files
    @property
    def rv(self):
        from review_lib.store import Review
        rid = [p.name for p in (self.project / "reviews").iterdir() if p.is_dir()]
        open_ = [x for x in sorted(rid) if R.fold(Review(self.project, x, self.state / "hep-research" / "reviews").events())["terminal"] is None]
        return Review(self.project, (open_ or sorted(rid))[-1], self.state / "hep-research" / "reviews")

    def read_doc(self) -> str:
        return (self.project / self.doc_rel).read_text(encoding="utf-8")

    def write_doc(self, text: str):
        (self.project / self.doc_rel).parent.mkdir(parents=True, exist_ok=True)
        (self.project / self.doc_rel).write_text(text, encoding="utf-8")

    def st(self):
        return R.fold(self.rv.events())

    def latest_attempt(self, sid: str) -> int:
        st = self.st()
        return max(st["attempts"][(st["round"], sid)])

    def adir(self, sid: str, k: int | None = None) -> Path:
        st = self.st()
        return self.rv.attempt_dir(st["round"], sid, k or self.latest_attempt(sid))

    def slot_info(self, sid: str) -> dict:
        return self.rv.slots()[str(self.st()["round"])][sid]

    def slot_of(self, role: str, lens: str | None = None) -> str:
        for sid, v in sorted(self.rv.slots()[str(self.st()["round"])].items()):
            if v["role"] == role and (lens is None or v.get("lens") == lens):
                return sid
        raise KeyError((role, lens))

    def packet(self, sid: str):
        p = self.adir(sid) / "packet"
        rd = lambda n: json.loads((p / n).read_text(encoding="utf-8"))  # noqa: E731
        return rd("scope.json"), rd("units.json")["units"], (rd("items.json")["items"] if (p / "items.json").exists() else None)

    def canaries(self, sid: str) -> list:
        st = self.st()
        p = self.rv.private_attempt(st["round"], sid, self.latest_attempt(sid)) / "canary.json"
        return json.loads(p.read_text(encoding="utf-8"))["canaries"] if p.exists() else []

    def dispatched(self, sid: str) -> dict:
        st = self.st()
        return st["attempts"][(st["round"], sid)][self.latest_attempt(sid)]["dispatched"]

    def write_record(self, sid: str, record: dict):
        (self.adir(sid) / "review_record.json").write_text(json.dumps(record, indent=1, ensure_ascii=False), encoding="utf-8")

    # scripted reviewer
    def good_record(self, sid: str, identity: str | None = None, findings=(), carry_status="confirmed") -> dict:
        """A record that passes receipt: one claim per deep or focus unit, supported with a locator, control findings on
        every canary (value = the new text, correction = the original), extra findings as given:
        findings = [(unit, severity, verdict)]."""
        scope, units, items = self.packet(sid)
        d = self.dispatched(sid)
        adir = self.adir(sid)
        info = self.slot_info(sid)
        rec = {"packet_sha256": d["packet_sha256"], "dispatch_nonce": d["nonce"],
               "instructions_sha256": d["instructions_sha256"],
               "role": "arbiter" if info["role"] == "arbiter" else "reviewer",
               "reviewer": {"identity": identity or f"reviewer-{sid}-{self.latest_attempt(sid)}", "context": "fresh",
                            "model": info["model"], "host": "claude-code", "slot_id": sid},
               "isolation": {"saw_prior_conversation": False, "host_injected": ["memory file"],
                             "instruction_files_seen": "unknown"},
               "paths_read": [{"path": f"packet/{n}", "sha256": sha(adir / "packet" / n)}
                              for n in ("document.md", "instructions.md", "scope.json", "units.json")],
               "evidence": [{"id": "E1", "basis": "locator", "ref": str(LICENSE), "lines": "2-3", "sha256": sha(LICENSE),
                             "source_kind": "page"}],
               "limitations": "Synthetic scripted reviewer."}
        if info["role"] == "arbiter":
            rec["resolves"] = [{"item_id": it["item_id"],
                                "conclusion": "uphold-finding" if it["type"] == "decline" else "uphold-first",
                                "rationale": "The finding stands on the cited text.", "evidence_ids": ["E1"]}
                               for it in items]
            return rec
        text = {u["id"]: u["text"] for u in units}
        cans = self.canaries(sid) if info["role"] == "lens" else []
        cu = {c["unit"]: c for c in cans}
        deep = scope["deep_units"] + scope["focus_units"]
        extra = {u: (sev, verdict) for u, sev, verdict in findings}
        rec.update({"skim": [], "claims": [], "verdicts": [], "findings": [], "carry_forward": []})
        nf = 0

        def add_finding(u, value, correction, severity, kind):
            nonlocal nf
            nf += 1
            rec["findings"].append({"id": f"F{nf}", "kind": kind, "severity": severity, "units": [u], "value": value,
                                    "correction": correction, "description": f"The value in {u} is wrong.",
                                    "fix": f"Write {correction}."})
            return f"F{nf}"

        fid_of = {}
        for u, c in cu.items():
            fid_of[u] = add_finding(u, c["mutated"].strip(), c["original"].strip(), "medium", "wrong-value")
        for u, (sev, _) in extra.items():
            fid_of[u] = add_finding(u, text[u].strip()[:30], "a corrected statement", sev, "internal-inconsistency")
        for n, u in enumerate(deep, 1):
            rec["claims"].append({"id": f"C{n}", "units": [u], "summary": f"Unit {u} states a checkable fact."})
            if u in fid_of:
                verdict = extra[u][1] if u in extra else "unsupported"
                rec["verdicts"].append({"claim_id": f"C{n}", "verdict": verdict, "rationale": "The value is wrong.",
                                        "evidence_ids": ["E1"], "finding_ids": [fid_of[u]], "refutation_attempts": []})
            else:
                rec["verdicts"].append({"claim_id": f"C{n}", "verdict": "supported", "rationale": "Matches the source.",
                                        "evidence_ids": ["E1"], "finding_ids": [],
                                        "refutation_attempts": [{"method": "compare with the cited file",
                                                                 "target": f"LICENSE:{n}", "outcome": "consistent"}]})
        for u in scope["skim_units"]:
            rec["skim"].append({"unit": u, "mark": "issue", "finding_id": fid_of[u]} if u in fid_of else {"unit": u, "mark": "ok"})
        for c in scope.get("carry_forward", []):
            ent = {"ref": c["ref"], "status": carry_status}
            if carry_status == "confirmed":
                ent["evidence_ids"] = ["E1"]
            rec["carry_forward"].append(ent)
        return rec

    def design_only_units(self, sid: str, exclude=()) -> list[str]:
        """Deep units of a design lens slot in no other lens's scope, outside its shadow's focus and its canaries."""
        st = self.st()
        table = {u["id"]: u for u in json.loads(self.rv.units_path(st["round"]).read_text(encoding="utf-8"))["units"]}
        shadow = self.slot_of("shadow", "design")
        focus = set(self.packet(shadow)[0]["focus_units"]) if (self.adir(shadow) / "packet").exists() else set()
        cu = {c["unit"] for c in self.canaries(sid)}
        scope = self.packet(sid)[0]
        return [u for u in scope["deep_units"] if u not in focus | cu | set(exclude) and table[u]["kind"] == "sentence"
                and not any(v for k, v in table[u]["in_scope"].items() if k != "design")]

    def unit_text(self, uid: str) -> str:
        st = self.st()
        return {u["id"]: u["text"] for u in json.loads(self.rv.units_path(st["round"]).read_text(encoding="utf-8"))["units"]}[uid]

    def copy(self, dest: Path) -> "Harness":
        """A copy of this harness's files under dest (the review directory holds no absolute paths)."""
        shutil.copytree(self.root, dest, dirs_exist_ok=True)
        h = Harness(dest, config=self.config, seed=self.seed, obs=self.obs)
        h.t = self.t
        return h


def dispatch_all(h: Harness, act: dict):
    assert act["action"] == "dispatch", act
    for sid in act["slots"]:
        h.run("dispatch", sid, expect=0)


def tempdir():
    return tempfile.TemporaryDirectory(prefix="hep-review-test-")


def run_e2e(root: Path, stop_at: str | None = None) -> tuple[Harness, dict]:
    """The P1 end-to-end review (acceptance criterion 8), driven only by `next` and the action it prints:
    round 1: four lenses and four shadows; the facts shadow is rejected (4 identical refutation attempts) and
    re-dispatched, the sources lens returns empty (withdraw host-failure), the bypass shadow times out; the design lens
    reports a high and a medium finding; the high one is declined, arbitrated (uphold-finding), then changed with
    --adopted-unverified; the medium one is changed (verified); a sentence is added and one removed.
    round 2: the changes are confirmed (change_confirmed); a new finding is changed and the edit reverted (close ->
    change_reverted), disposed unresolved, escalated, reported, resolved by a human; then closed.
    stop_at names a checkpoint at which to return early ('arbiter-dispatched', 'round1-accepted')."""
    h = Harness(root).setup()
    h.start()
    marks = {"events": []}
    behaviour = {}  # (round, role, lens, attempt) -> what the scripted agent does
    real = {}
    for step in range(400):
        act = h.next()
        if "action" not in act:
            raise AssertionError(f"next failed: {act} after {h.log[-6:]}")
        a = act["action"]
        marks["events"].append(a)
        st = h.st()
        r = st["round"]
        if a == "dispatch":
            for sid in act["slots"]:
                h.run("dispatch", sid, expect=0)
                info = h.slot_info(sid)
                k = h.latest_attempt(sid)
                key = (r, info["role"], info.get("lens"), k)
                if info["role"] == "arbiter":
                    if stop_at == "arbiter-dispatched":
                        return h, marks
                    h.write_record(sid, h.good_record(sid, identity="arbiter-agent"))
                    h.run("returned", sid, expect=0)
                    continue
                behaviour[key] = (
                    "refutation-dup" if key == (1, "shadow", "facts", 1) else
                    "empty" if key == (1, "lens", "sources", 1) else
                    "silent" if key == (1, "shadow", "bypass", 1) else "good")
            # reviewers work after the whole batch is dispatched (the shadows' focus units are then known)
            for sid in act["slots"]:
                info = h.slot_info(sid)
                if info["role"] == "arbiter":
                    continue
                k = h.latest_attempt(sid)
                how = behaviour[(r, info["role"], info.get("lens"), k)]
                if how == "silent":
                    continue
                if how == "empty":
                    h.run("returned", sid, expect=0)
                    continue
                extra = []
                if info["role"] == "lens" and info["lens"] == "design":
                    pick = h.design_only_units(sid)
                    if r == 1:
                        real["X1"], real["X2"] = pick[0], pick[1]
                        extra = [(pick[0], "high", "unsupported"), (pick[1], "medium", "partially-supported")]
                    else:
                        real["Z"] = pick[0]
                        extra = [(pick[0], "medium", "partially-supported")]
                    real[f"design{r}"] = sid
                rec = h.good_record(sid, findings=extra)
                if how == "refutation-dup":
                    for v in rec["verdicts"]:
                        v["refutation_attempts"] = [{"method": "same check", "target": "LICENSE:1", "outcome": "ok"}]
                h.write_record(sid, rec)
                h.run("returned", sid, expect=0)
        elif a == "receive":
            for sid in act["slots"]:
                out = h.run("receive", sid)
                marks["events"].append(f"receive:{out['status']}")
        elif a == "withdraw":
            for sid in act["slots"]:
                h.run("withdraw", sid, "--reason", act["reason"], expect=0)
        elif a == "await":
            h.now(60)  # nothing else happens: the clock runs past the deadline
        elif a == "arbitrate":
            h.run("arbitrate", expect=0)
        elif a == "dispose":
            design = real[f"design{r}"]
            for g in act["findings"]:
                f = st["findings"][g]
                fid = g.split("/")[-1]
                unit = f["units"][0]
                if r == 1 and unit == real["X2"]:
                    if stop_at == "round1-accepted":
                        return h, marks
                    doc = h.read_doc()
                    x2 = h.unit_text(real["X2"])
                    doc = doc.replace(x2, x2[:-1] + ", as revised.", 1)
                    doc = doc.replace("## 1. Scope\n\n", "## 1. Scope\n\nThe `report` field summarises each round.\n\n", 1)
                    doc = doc.replace("每個 claim 至多引用 3 個單位。\n", "", 1)
                    h.write_doc(doc)
                    h.run("dispose", g, "--as", "changed", "--reason", "fixed the statement",
                          "--verified", "locator:LICENSE:2-3", expect=0)
                elif r == 1 and unit == real["X1"] and f["state"] == "open":
                    h.run("dispose", g, "--as", "declined", "--reason", "the statement is intended", expect=0)
                elif r == 1 and unit == real["X1"]:
                    doc = h.read_doc()
                    x1 = h.unit_text(real["X1"])
                    h.write_doc(doc.replace(x1, x1[:-1] + ", now with an example.", 1))
                    h.run("dispose", g, "--as", "changed", "--reason", "adopted the arbiter's view",
                          "--adopted-unverified", expect=0)
                elif r == 2 and g.split("/")[1] == design and f["state"] == "open":
                    marks["round2_source"] = h.read_doc()
                    z = h.unit_text(real["Z"])
                    h.write_doc(marks["round2_source"].replace(z, z[:-1] + ", for now.", 1))
                    h.run("dispose", g, "--as", "changed", "--reason", "clarified", "--verified", "person:author,2026-01-01",
                          expect=0)
                    h.write_doc(marks["round2_source"])  # the edit is reverted before close
                elif r == 2 and f["state"] == "reopened":
                    h.run("dispose", g, "--as", "unresolved", "--reason", "conflicting sources; a human decides", expect=0)
                else:
                    raise AssertionError(f"unexpected finding to dispose: {g} {f}")
        elif a == "rereview":
            out = h.run("rereview", expect=0)
            marks["mapping"] = out["mapping"]
        elif a == "close":
            out = h.run("close")
            marks["events"].append(f"close:{out['status']}")
        elif a == "escalate":
            h.run("escalate", "--reason", "an unresolved finding needs a human", expect=0)
        elif a == "report":
            h.run("report", expect=0)
        elif a == "stop":
            st = h.st()
            if st["terminal"]:
                return h, marks
            pending = R.snapshot(st)["escalation"]["pending"]
            for item in pending:
                h.run("resolve", item, "--by", "maintainer", "--decision", "close",
                      "--reason", "accepted as written after discussion", expect=0)
        elif a == "repair":
            raise AssertionError(f"unexpected repair: {act}")
        else:
            raise AssertionError(f"unknown action {act}")
    raise AssertionError("the review did not finish")
