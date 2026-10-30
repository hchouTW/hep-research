"""Reconstruction v12 C1: the control-layer derivation against its reference model (Delivery §5.1 last row; DEC-02).

1. Property tests: the model's 92 scenarios run against the implementation (control_layer_support.derivation),
   each as a subtest; the model contributes only the scenario code (control_oracle.py rebinds it).
2. Mutation tests: each of the model's 44 mutations is applied to the implementation's corresponding function and
   must make at least one scenario fail; the implementation is restored after each.
3. Differential tests: the model and the implementation are given the same fact sequences -- every log the 90
   scenarios build, and random sequences -- and must give the same derivation: contract states, execution states,
   accounts, bound artifact per step, label / usable / ok / accepted / owning step / historical failures per artifact,
   per-deliverable status with its histories, admission and publish outcomes (exception and message) and the facts
   written (identities compared through a bijection, since the implementation's identities are SHA-256 digests).
4. Codec round trip: every random implementation log is written as a task record and loaded back (chain verified,
   every batch re-validated) with the same derivation.
The model is located per control_oracle.py: a missing model FAILS in a development checkout and is SKIPPED with an
explicit reason in an installed plugin. The control rules themselves did not pass S0 (N1); agreement with the model
is agreement with unreviewed rules."""
import dataclasses
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import control_oracle as oracle  # noqa: E402
from control_layer_support import derivation as impl  # noqa: E402
from control_layer_support import task_record  # noqa: E402

EXPECTED_SCENARIOS = 92
EXPECTED_MUTATIONS = 44
RANDOM_TRIALS = 300
PER_APPEND_SNAPSHOT_LIMIT = 150


class Api:
    """Uniform access to the model module or the rebound implementation namespace."""

    def __init__(self, namespace):
        self.namespace = namespace

    def __getattr__(self, name):
        return self.namespace[name]


def model_api():
    return Api(vars(oracle.load_model()))


def impl_api():
    return Api(oracle.rebound_namespace())


def plain(value):
    """A comparable plain form: dataclasses by class name and fields, sets sorted, tuples as lists."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return [type(value).__name__, {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}]
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (frozenset, set)):
        return sorted((plain(v) for v in value), key=repr)
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def snapshot(api, log) -> dict:
    snap = {"head": log.head, "mode": log.mode(), "contracts": sorted(api._contracts(log)[1].items()),
            "has_contract": api.has_contract(log)}
    attempts = sorted({f.get("attempt") for f in log.facts if isinstance(f.get("attempt"), str)})
    snap["exec"] = {a: api.exec_status(log, a) for a in attempts}
    snap["accounts"] = (api.in_flight(log), api.used(log))
    if snap["has_contract"]:
        eff = api.contract(log)
        names = list(eff["steps"]) + [n for n in log._by_step_out if n not in eff["steps"] and n != "__check__"]
        digests = []
        for name in names:
            for digest in api.candidates_raw(log, name):
                if digest not in digests:
                    digests.append(digest)
        snap["bound"] = {s: api.bound(log, s) for s in eff["steps"]}
        snap["artifacts"] = {d: [api.label(log, d), api.usable(log, d), api.ok(log, d), api.accepted(log, d),
                                 api.step_of(log, d), plain(api.historical_failures(log, d))] for d in digests}
        snap["deliverables"] = {did: plain(api.report_status(log, did)) for did in eff["deliverables"]}
    return snap


class IdentityMap:
    """Model identities and implementation identities must correspond one to one."""

    def __init__(self, case):
        self.case, self.forward, self.backward = case, {}, {}

    def pair(self, mine, theirs, where):
        if mine is None and theirs is None:
            return
        self.case.assertEqual(self.forward.setdefault(mine, theirs), theirs, f"{where}: identity maps twice")
        self.case.assertEqual(self.backward.setdefault(theirs, mine), mine, f"{where}: identity maps twice")


def compare_facts(case, model_log, impl_log, ids, where):
    case.assertEqual(model_log.head, impl_log.head, f"{where}: head")
    for mf, jf in zip(model_log.facts, impl_log.facts):
        at = f"{where} seq {mf.seq}"
        case.assertEqual((mf.seq, mf.kind, mf.writer), (jf.seq, jf.kind, jf.writer), at)
        mfields, jfields = dict(mf.data), dict(jf.fields)
        for key in ("identity", "old_identity", "new_identity"):
            if key in mfields or key in jfields:
                ids.pair(mfields.pop(key, None), jfields.pop(key, None), at)
        case.assertEqual(plain(mfields), plain(jfields), at)


def outcome(func, *args, **kw):
    """Run one operation; return ('ok', value-ish) or (exception name, message)."""
    try:
        func(*args, **kw)
        return ("ok", None)
    except AssertionError:
        raise
    except Exception as exc:  # noqa: BLE001  (the exception class and message are the compared outcome)
        return (type(exc).__name__, str(exc))


# ---------------------------------------------------------------- random fact sequences

POOL = ["P1", "P2", "P3", "P4", "P5", "P6"]


def random_trace(api, seed: int):
    """A random fact sequence driven through the namespace's own engine and helpers; returns (log, trace)."""
    rnd = random.Random(seed)
    st, dl = api.StepSpec, api.Deliverable
    c1, cx = frozenset({("chkA", "crit1")}), frozenset({("chkA", "x")})
    raw_checked = rnd.random() < .5
    use_ref = rnd.random() < .3
    steps = {"raw": st(program="pRaw", checked=raw_checked, required=frozenset({("chkR", "k")}),
                       allow_rerun=rnd.random() < .5),
             "reco": st(program="pReco", upstream=("raw",), checked=True, required=c1,
                        allow_rerun=rnd.random() < .5, na_allowed=c1 if rnd.random() < .2 else frozenset(),
                        check_inputs=frozenset({("chkA", "ref")}) if use_ref else frozenset())}
    if use_ref:
        steps["ref"] = st(program="pRef")
    samples = {"S": "confirmation", "T": "confirmation", "CR": "control", "B": "blinded"}
    target = rnd.choice(["T2", "T3E", "T3C"])
    dels = {"D": dl("reco", target, confirmation_required=rnd.random() < .8,
                    independent_confirmation=rnd.random() < .3)}
    if raw_checked and rnd.random() < .5:
        dels["D2"] = dl("raw", "T2")
    mode = rnd.choice(["M1", "M1", "M1", "M2"])
    log = api.new_log(steps, samples=samples, budget=rnd.choice([None, None, None, 8.0, 20.0]), deliverables=dels,
                      mode=None if mode == "M1" else mode)
    trace = []
    if mode != "M1" and rnd.random() < .8:
        trace.append(outcome(api.approve, log, log.of("contract")[0]))
    counter = 0
    ops = ["run", "check", "freeze", "recontract", "approve", "reuse", "resolve", "exposure", "decision",
           "publish", "start_cancel"]
    weights = [6, 9, 1.5, 2.5, 1, 0.7, 1.5, 0.5, 0.6, 2, 0.3]
    for _ in range(rnd.randint(10, 36)):
        counter += 1
        known = [d for s in ("raw", "reco", "ref", "side") for d in api.candidates_raw(log, s)]
        eff = api.contract(log) if api.has_contract(log) else None
        op = rnd.choices(ops, weights)[0]
        if op == "run":
            needed = [s for s in ("raw", "ref") if s in (eff or {}).get("steps", {}) and api.bound(log, s) is None]
            step = rnd.choice(needed) if needed and rnd.random() < .6 else rnd.choice(["raw", "reco", "reco", "ref",
                                                                                     "side"])
            out = rnd.choice(POOL) if rnd.random() < .35 else f"N{counter}"
            extra = {}
            if rnd.random() < .25:
                extra["usage"] = rnd.choice([0.0, 0.5, 2.0])
            if rnd.random() < .04:
                extra["observed_exceeds_declared"] = True
            reads = (rnd.choice(["CR", "S", "B"]),) if rnd.random() < .1 else ()
            trace.append(outcome(api.run, log, f"a{counter}", step, out,
                                 end=rnd.choice(["success"] * 9 + ["failure", "timeout", "cancelled"]),
                                 termination=rnd.choice(["confirmed"] * 11 + ["unknown"]), reads=reads, **extra))
        elif op == "check":
            focus = [d for s in ("reco", "raw", "ref") for d in
                     [x for x in api.candidates_raw(log, s) if api.usable(log, x)][-2:]]
            tg = rnd.choice(focus) if focus and rnd.random() < .85 else rnd.choice(known + ["NOPE"])
            owner = api.step_of(log, tg) if eff else None
            required = sorted(eff["steps"][owner].required) if owner in (eff or {}).get("steps", {}) else []
            pair = rnd.choice(required) if required and rnd.random() < .85 else rnd.choice(
                [("chkA", "crit1"), ("chkR", "k"), ("chkA", "x")])
            frozen = any(f.get("step") == "reco" for f in log.of("freeze"))
            sample = rnd.choice(["S", "T"]) if frozen and rnd.random() < .5 else rnd.choice(
                [None] * 7 + ["CR", "CR", "S", "B"])
            trace.append(outcome(api.check, log, tg, *pair,
                                 rnd.choice(["pass"] * 12 + ["fail", "inconclusive", "not-applicable"]),
                                 f"c{counter}", sample=sample, end=rnd.choice(["success"] * 8 + ["failure"]),
                                 termination=rnd.choice(["confirmed"] * 8 + ["unknown"])))
        elif op == "freeze":
            req = api.spec_of(log, "reco").required if eff else c1
            chosen = tuple(rnd.sample(["S", "T"], rnd.randint(0, 2)))
            fields = {"step": "reco", "samples": chosen, "required": req if rnd.random() < .85 else cx}
            if chosen and rnd.random() < .5:
                fields["independent"] = (chosen[-1],)
            trace.append(outcome(log.append, "freeze", "agent", **fields))
        elif op == "recontract":
            trace.append(outcome(_random_recontract, api, log, rnd, known))
        elif op == "approve":
            pending = [f for f in log.of("contract") if api._contracts(log)[1].get(f.seq) == "pending_approval"]
            if pending:
                trace.append(outcome(api.approve, log, rnd.choice(pending)))
        elif op == "reuse":
            if known:
                trace.append(outcome(api.admit, log, log.head, f"r{counter}", rnd.choice(["raw", "reco"]),
                                     cost=0.0, reuse_source=rnd.choice(known + ["NOPE"])))
        elif op == "resolve":
            unknown = [f.get("attempt") for f in log.of("intent") if api.exec_status(log, f.get("attempt")) in
                       ("unknown", "abandoned")]
            if unknown:
                attempt = rnd.choice(unknown)
                if rnd.random() < .4:
                    trace.append(outcome(log.append, "decision", "human", action="abandon", attempt=attempt))
                else:
                    trace.append(outcome(log.append, "reconcile", "B", attempt=attempt,
                                         end=rnd.choice(["success", "success", "failure"]),
                                         termination=rnd.choice(["confirmed", "confirmed", "unknown"]),
                                         outputs=(rnd.choice(POOL + [f"Q{counter}"]),)))
        elif op == "exposure":
            trace.append(outcome(log.append, "exposure", rnd.choice(["agent", "B"]),
                                 sample=rnd.choice(["S", "T", "CR"]),
                                 **({"attempt": f"c{rnd.randint(1, counter)}"} if rnd.random() < .5 else {})))
        elif op == "decision":
            trace.append(outcome(_random_decision, api, log, rnd, known))
        elif op == "publish":
            did = rnd.choice(["D", "D", "D2"])
            head = log.head if rnd.random() < .9 else log.head - 1
            trace.append(outcome(api.publish, log, head, did))
        else:
            attempts = [f.get("attempt") for f in log.of("intent")]
            if attempts:
                kind = rnd.choice(["start", "cancel_request"])
                trace.append(outcome(log.append, kind, "B" if kind == "start" else "C", attempt=rnd.choice(attempts)))
        trace.append(snapshot(api, log))
    return log, trace


def _random_recontract(api, log, rnd, known):
    st, dl = api.StepSpec, api.Deliverable
    eff = api.contract(log)
    reco = eff["steps"]["reco"]
    change = rnd.choice(["program", "program", "program", "required", "upstream", "pin", "rerun", "budget",
                         "target", "add_side", "remove_side", "role", "na", "raw_program", "raw_program"])
    kw = {}
    if change == "program":
        kw["reco"] = dataclasses.replace(reco, program=rnd.choice(["pReco", "pReco2", "pReco3", "pReco "]))
    elif change == "required":
        kw["reco"] = dataclasses.replace(reco, required=rnd.choice([
            frozenset({("chkA", "crit1")}), frozenset({("chkA", "x")}), reco.required | {("chkA", "x")}]))
    elif change == "upstream" and "side" in eff["steps"]:
        kw["reco"] = dataclasses.replace(reco, upstream=tuple(dict.fromkeys(reco.upstream + ("side",))))
    elif change == "pin":
        kw["reco"] = dataclasses.replace(reco, pin=rnd.choice(known + [None]) if known else None)
    elif change == "rerun":
        kw["reco"] = dataclasses.replace(reco, allow_rerun=not reco.allow_rerun)
    elif change == "na":
        kw["reco"] = dataclasses.replace(reco, na_allowed=frozenset() if reco.na_allowed else reco.required)
    elif change == "raw_program":
        kw["raw"] = dataclasses.replace(eff["steps"]["raw"], program=rnd.choice(["pRaw", "pRaw2", "pRaw3"]))
    elif change == "add_side":
        kw["side"] = st(program=rnd.choice(["pSide", "pSide2"]), upstream=("raw",))
    deliverables = dict(eff["deliverables"])
    if change == "target":
        deliverables["D"] = dl("reco", rnd.choice(["T2", "T3E", "T3C"]), confirmation_required=rnd.random() < .7,
                               independent_confirmation=rnd.random() < .5)
    samples = dict(eff["samples"])
    if change == "role":
        samples["CR"] = rnd.choice(["control", "training"])
    budget = "keep" if change != "budget" else rnd.choice([None, 3.0, 20.0])
    if change == "remove_side" and "side" in eff["steps"]:
        steps = {k: v for k, v in eff["steps"].items() if k != "side"}
        steps["reco"] = dataclasses.replace(steps["reco"], upstream=tuple(u for u in reco.upstream if u != "side"))
        return log.append("contract", "agent", spec=api.spec(steps, deliverables, dict(eff["families"]), samples,
                                                              eff["budget"]))
    return api.recontract(log, samples=samples, budget=budget, deliverables=deliverables, **kw)


def _random_decision(api, log, rnd, known):
    kind = rnd.choice(["accept_identity", "assign_producer", "unblind", "approve_stale"])
    if kind == "unblind":
        return log.append("decision", "human", action="unblind", sample="B")
    if kind == "approve_stale":
        contracts = log.of("contract")
        return log.append("decision", "human", action="approve_contract", ref=rnd.choice(contracts).seq)
    if not known:
        return None
    digest = rnd.choice(known)
    if kind == "assign_producer":
        return log.append("decision", "human", action="assign_producer", digest=digest,
                          step=rnd.choice(["raw", "reco", "side"]))
    producers = api.producers(log, digest)
    if not producers:
        return None
    intent = producers[0][1]
    step = intent.get("step")
    if step not in api.contract(log)["steps"]:
        return None
    new_id = api.expected_identity(log, step, api.inputs_of(intent))
    return log.append("decision", "human", action="accept_identity", digest=digest, step=step,
                      old_identity=intent.get("identity"), new_identity=new_id)


# ---------------------------------------------------------------- tests

class ModelTestCase(unittest.TestCase):
    def setUp(self):
        oracle.require_model(self)


class Inventory(ModelTestCase):
    def test_the_model_is_the_expected_one(self):
        model = oracle.load_model()
        self.assertEqual(model.DERIVATION_VERSION, impl.DERIVATION_VERSION)
        self.assertEqual(len(model.TESTS), EXPECTED_SCENARIOS)
        self.assertEqual(len(model.MUTATIONS), EXPECTED_MUTATIONS)

    def test_every_engine_name_of_the_model_exists_in_the_implementation(self):
        self.assertEqual(oracle.model_names_missing_in_impl(), [])

    def test_rebound_scenarios_run_only_implementation_engine_code(self):
        namespace = oracle.rebound_namespace()
        model = oracle.load_model()
        for name in ("Log", "admit", "publish", "label", "bound", "StepSpec", "contract_at_least_as_strict"):
            self.assertIs(namespace[name], getattr(impl, name))
            self.assertIsNot(namespace[name], getattr(model, name))
        self.assertIs(namespace["new_log"].__globals__, namespace)
        self.assertIsInstance(namespace["ALIGN"]["align"], impl.Family)


class Scenarios(ModelTestCase):
    def test_every_model_scenario_passes_against_the_implementation(self):
        funcs = oracle.scenarios(oracle.rebound_namespace())
        self.assertEqual(len(funcs), EXPECTED_SCENARIOS)
        for func in funcs:
            with self.subTest(scenario=func.__name__):
                self.assertEqual(oracle.run_scenarios([func]), [])


class Mutations(ModelTestCase):
    def test_every_model_mutation_of_the_implementation_is_caught(self):
        namespace = oracle.rebound_namespace()
        funcs = oracle.scenarios(namespace)
        slow = [f for f in funcs if f.__name__ in ("t28_scale_linear", "t36_random_invariants")]
        ordered = [f for f in funcs if f not in slow] + slow
        self.assertEqual(len(namespace["MUTATIONS"]), EXPECTED_MUTATIONS)
        for label in namespace["MUTATIONS"]:
            with self.subTest(mutation=label):
                with oracle.Mutated(namespace, label) as applied:
                    self.assertIsNot(getattr(impl, applied.target), applied.original)
                    caught = oracle.run_scenarios(ordered, stop_at_first=True)
                self.assertTrue(caught, f"mutation survived: {label}")
        self.assertEqual(oracle.run_scenarios(funcs), [], "the implementation was not restored")


class Differential(ModelTestCase):
    def _recording(self, api_namespace, base, sink, per_append):
        class Recording(base):
            def __init__(self):
                super().__init__()
                self.snapshots = []
                sink.append(self)

            def append_batch(self, items, expect_head=None):
                written = super().append_batch(items, expect_head)
                if per_append and len(self.facts) <= PER_APPEND_SNAPSHOT_LIMIT:
                    self.snapshots.append(snapshot(Api(api_namespace), self))
                return written
        return Recording

    def test_scenario_fact_sequences_give_the_same_derivation(self):
        model = oracle.load_model()
        model_ns, impl_ns = vars(model), oracle.rebound_namespace()
        total_logs = total_snapshots = 0
        for name in sorted(n for n in impl_ns if n.startswith("t") and n[1:3].isdigit()):
            with self.subTest(scenario=name):
                per_append = name not in ("t28_scale_linear",)
                model_logs, impl_logs = [], []
                saved = (model_ns["Log"], impl_ns["Log"])
                model_ns["Log"] = self._recording(model_ns, saved[0], model_logs, per_append)
                impl_ns["Log"] = self._recording(impl_ns, saved[1], impl_logs, per_append)
                try:
                    getattr(model, name)()
                    impl_ns[name]()
                finally:
                    model_ns["Log"], impl_ns["Log"] = saved
                self.assertEqual(len(model_logs), len(impl_logs))
                ids = IdentityMap(self)
                for index, (mlog, jlog) in enumerate(zip(model_logs, impl_logs)):
                    compare_facts(self, mlog, jlog, ids, f"{name} log {index}")
                    self.assertEqual(mlog.snapshots, jlog.snapshots, f"{name} log {index}: per-append derivation")
                    self.assertEqual(snapshot(Api(model_ns), mlog), snapshot(Api(impl_ns), jlog),
                                     f"{name} log {index}: final derivation")
                    total_logs += 1
                    total_snapshots += len(mlog.snapshots) + 1
        self.assertGreater(total_logs, EXPECTED_SCENARIOS)
        self.assertGreater(total_snapshots, 2000)

    def test_random_fact_sequences_give_the_same_derivation(self):
        model = model_api()
        steps = 0
        for seed in range(RANDOM_TRIALS):
            with self.subTest(seed=seed):
                mlog, mtrace = random_trace(model, seed)
                jlog, jtrace = random_trace(impl_api(), seed)
                self.assertEqual(len(mtrace), len(jtrace))
                for index, (mine, theirs) in enumerate(zip(mtrace, jtrace)):
                    self.assertEqual(mine, theirs, f"seed {seed}, trace entry {index}")
                compare_facts(self, mlog, jlog, IdentityMap(self), f"seed {seed}")
                steps += len(mtrace)
        self.assertGreater(steps, RANDOM_TRIALS * 10)

    def test_random_logs_survive_the_task_record_round_trip(self):
        api = impl_api()
        for seed in range(0, RANDOM_TRIALS, 3):
            with self.subTest(seed=seed):
                jlog, _ = random_trace(api, seed)
                content = task_record.dump_log(jlog)
                loaded = task_record.load_bytes(content)
                self.assertEqual(snapshot(api, loaded.log), snapshot(api, jlog))
                self.assertEqual(task_record.dump_log(loaded.log), content)
                self.assertEqual(loaded.log.batch_start, jlog.batch_start)


if __name__ == "__main__":
    unittest.main()
