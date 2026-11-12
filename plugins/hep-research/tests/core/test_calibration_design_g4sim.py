"""The g4sim items of calib_design.py (Part B sections 6.1, 6.6, 11.4, 14.1, 15.3.19; phase 3, WP-B): g4sim support and
recording levels, the event-interval check with run_seed = logical_run_seed and replica = 0, the seed-block registry,
one digitization path per readout system, and the checks of every g4sim-digi-job/1. Each negative test has its
positive control."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_g4sim_fixtures as G  # noqa: E402

from core.calibration import design_g4sim as DG  # noqa: E402
from core.simulation import digitize, seeds  # noqa: E402

NODES = ("src", "transport", "scint", "sensor", "elec", "readout")


def contract():
    pars = [{"name": "beam_mean", "role": "theta", "nodes": ["src"], "sampling_bounds": [450, 550]},
            {"name": "birks", "role": "theta", "nodes": ["transport"], "sampling_bounds": [0.05, 0.2]},
            {"name": "light_yield", "role": "theta", "nodes": ["scint"], "sampling_bounds": [150, 250]},
            {"name": "gain", "role": "theta", "nodes": ["sensor"], "sampling_bounds": [0.8, 1.2]}]
    return {"simulator": "g4sim", "parameters": pars,
            "stage_graph": {"nodes": [{"id": n, "kernel": "density"} for n in NODES],
                            "edges": [{"from": a, "to": b} for a, b in zip(NODES, NODES[1:])]}}


def plan(**kw):
    p = {"schema": "calibration-plan/1", "kernels": {},
         "methods": {"beam_mean": "analytic-reweighting", "birks": "rerun", "light_yield": "re-digitization",
                     "gain": "re-digitization"},
         "node_binding": {"nodes": {"src": {"g4sim": "source"}, "transport": {"g4sim": "transport",
                                                                              "recording": "column"},
                                    "scint": {"g4sim": "stage:scintillation", "recording": "event_file"},
                                    "sensor": {"g4sim": "stage:sensor", "recording": "event_file"},
                                    "elec": {"g4sim": "stage:electronics", "recording": "event_file"},
                                    "readout": {"g4sim": "stage:strip", "recording": "event_file"}},
                          "parameters": copy.deepcopy(G.BINDINGS)}}
    p.update(kw)
    return p


def docs(**kw):
    d = G.documents(**kw)
    return d


def codes(r):
    return sorted({f["code"] for f in r["findings"]})


class Support(unittest.TestCase):
    """Section 6.1 with g4sim, section 15.3.19."""

    def test_positive_control(self):
        r = DG.support_g4sim(contract(), plan(), docs())
        self.assertEqual((r["status"], r["infeasible"]), ("passed", []), r["findings"])

    def test_moments_recording_is_infeasible(self):
        p = plan()
        p["node_binding"]["nodes"]["transport"]["recording"] = "moments"
        r = DG.support_g4sim(contract(), p, docs())
        self.assertEqual(codes(r), ["support.recording_moments"])
        self.assertEqual(r["infeasible"], ["birks"])
        p["node_binding"]["nodes"]["transport"]["recording"] = {"inputs": "column", "outputs": "event_file"}
        self.assertEqual(DG.support_g4sim(contract(), p, docs())["status"], "passed")
        p["node_binding"]["nodes"]["transport"].pop("recording")
        self.assertEqual(codes(DG.support_g4sim(contract(), p, docs())), ["support.recording_undeclared"])
        p["methods"]["birks"] = "resimulation"                       # a resimulated node needs no records
        self.assertEqual(DG.support_g4sim(contract(), p, docs())["status"], "passed")

    def test_kill_policy_minimum_energy_is_missing_support(self):
        d = docs()
        d["run"]["kill_policy"] = {"min_kinetic_energy_MeV": "1"}
        r = DG.support_g4sim(contract(), plan(), d)
        self.assertEqual(codes(r), ["support.filtered"])
        self.assertEqual(r["infeasible"], ["beam_mean", "birks"])    # at or upstream of the transport node only
        p = plan()
        p["node_binding"]["filters_ignorable"] = [{"filter": "kill_policy.min_kinetic_energy",
                                                   "reason": "every observable is above 1 MeV for every theta'"}]
        r = DG.support_g4sim(contract(), p, d)
        self.assertEqual(r["status"], "passed")
        self.assertEqual({c["parameter"] for c in r["p0_confirms_ignorable_filters"]}, {"beam_mean", "birks"})
        p["node_binding"]["filters_ignorable"][0].pop("reason")      # a declaration without its reason is none
        self.assertEqual(DG.support_g4sim(contract(), p, d)["status"], "failed")

    def test_time_window_pruning_and_zero_suppression(self):
        d = docs()
        d["request"]["scorers"][0]["time_window_ns"] = ["0", "100"]
        d["request"]["truth"] = {"keep": ["primary"]}
        self.assertEqual({f["filter"] for f in DG.support_g4sim(contract(), plan(), d)["findings"]},
                         {"scorer.time_window:zdc_split", "truth.pruning"})
        d = docs()
        d["pipeline"]["stages"].append({"name": "strip", "kind": "readout_external", "parameters": {}})
        r = DG.support_g4sim(contract(), plan(), d)
        self.assertEqual({f["filter"] for f in r["findings"]}, {"zero_suppression:strip"})
        self.assertEqual(r["infeasible"], sorted(["beam_mean", "birks", "light_yield", "gain"]))
        p = plan()
        p["node_binding"]["nodes"].pop("readout")                    # an unbound stage is never silently skipped
        self.assertEqual(codes(DG.support_g4sim(contract(), p, d)), ["support.filter_unbound"])
        d["request"]["truth"] = {"keep": ["all"]}                     # keeping all truth prunes nothing
        self.assertEqual(len(DG.support_g4sim(contract(), plan(), d)["findings"]), 4)

    def test_source_support(self):
        c = contract()
        r = DG.support_g4sim(c, plan(), docs(lo="300", hi="700"))
        self.assertEqual(r["status"], "passed")                       # the mean moves inside the truncation
        p = plan()
        p["node_binding"]["parameters"]["beam_mean"]["pointer"] = "/source/energy/gaussian/truncate_MeV/1"
        c["parameters"][0]["sampling_bounds"] = [650, 800]           # the upper truncation leaves supp q
        self.assertEqual(codes(DG.support_g4sim(c, p, docs())), ["support.missing"])
        c["parameters"][0]["sampling_bounds"] = [600, 700]
        self.assertEqual(DG.support_g4sim(c, p, docs())["status"], "passed")
        p["node_binding"]["parameters"]["beam_mean"]["pointer"] = "/source/position/gaussian_spot/sigma_mm/0"
        self.assertEqual(codes(DG.support_g4sim(contract(), p, docs())), ["support.no_density_function"])

    def test_external_source_has_no_density(self):
        d = docs()
        d["request"]["source"] = {"density": "external", "path": "events.txt", "sha256": "0" * 64}
        self.assertEqual(codes(DG.support_g4sim(contract(), plan(), d)), ["support.source_density"])
        p = plan()
        p["methods"]["beam_mean"] = "resimulation"                   # node 0 not reweighted: no source density needed
        self.assertEqual(DG.support_g4sim(contract(), p, d)["status"], "passed")


def ev(run_id, use, seed, first, n, **kw):
    return {"run_id": run_id, "use": use, "logical_run_seed": seed, "first_event": first, "events": n,
            "run_seed": seed, "replica": 0, **kw}


GOOD = [ev("fit@a", "fit", 11, 0, 1000, set="nominal"), ev("fit@b", "fit", 11, 0, 1000, set="nominal"),
        ev("g8-0", "G8", 11, 1000, 1000, set=0), ev("g8-1", "G8", 11, 2000, 1000, set=1),
        ev("g8-truth", "G8-truth", 12, 0, 100000), ev("val", "validation", 13, 0, 1000),
        ev("p7-1", "P7", 14, 0, 500, set=1), ev("p7-2", "P7", 14, 500, 500, set=2)]


class Intervals(unittest.TestCase):
    """Section 6.6 "Check" and section 15.3.19."""

    def test_positive_control(self):
        r = DG.interval_findings({"evaluations": GOOD})
        self.assertEqual((r["status"], r["flags"]), ("passed", []), r["findings"])

    def test_plan_fields_validate(self):
        from contracts.schema import validate
        p = {"schema": "calibration-plan/1", "kernels": {}, "evaluations": GOOD, "mapping_scans": {},
             "seed_blocks": [{"block": "a", "logical_run_seed": 5, "t": 0, "m_blk": 1, "N_ev": 10}],
             "event_time": {"kind": "linear", "t0_ns": 0, "ns_per_event": 1000}}
        self.assertEqual(validate(p, "calibration_plan.json").errors, [])
        p["evaluations"] = [{"run_id": "x"}]
        self.assertTrue(validate(p, "calibration_plan.json").errors)

    def test_g8_fit_mc_changing_only_the_response(self):
        bad = GOOD + [ev("g8-2", "G8", 11, 0, 1000, set=2, run_seed=11, replica=0)]   # the fit's events re-digitized
        r = DG.interval_findings({"evaluations": bad})
        self.assertEqual(codes(r), ["design.g8_interval_overlap"])
        r = DG.interval_findings({"evaluations": bad, "g8": {"run": False}})          # G8 declared not run
        self.assertEqual((r["status"], r["flags"]), ("passed", ["closure-not-tested"]))

    def test_p7_sets_sharing_events(self):
        bad = [e for e in GOOD if e["run_id"] != "p7-2"] + [ev("p7-2", "P7", 14, 250, 500, set=2)]
        self.assertEqual(codes(DG.interval_findings({"evaluations": bad})), ["design.interval_overlap_sets"])

    def test_validation_on_fit_events(self):
        bad = GOOD + [ev("val2", "validation", 11, 995, 5)]
        self.assertEqual(codes(DG.interval_findings({"evaluations": bad})), ["design.interval_overlap_uses"])
        ok = GOOD + [ev("val2", "validation", 11, 3000, 10)]
        self.assertEqual(DG.interval_findings({"evaluations": ok})["status"], "passed")

    def test_run_seed_and_replica(self):
        bad = [dict(GOOD[0], run_seed=12)] + GOOD[1:]
        self.assertEqual(codes(DG.interval_findings({"evaluations": bad})), ["design.run_seed"])
        bad = [dict(GOOD[0], replica=1)] + GOOD[1:]
        self.assertEqual(codes(DG.interval_findings({"evaluations": bad})), ["design.replica"])
        bad = [ev("x", "fit", 15, 2 ** 32 - 5, 10)]
        self.assertEqual(codes(DG.interval_findings({"evaluations": bad})), ["design.event_range"])

    def test_mapping_runs_and_pde_pairs(self):
        scan = [ev(f"map{i}", "mapping-run", 21, 0, 5000, scan="s", point=i) for i in range(3)]
        shared = {"mapping_scans": {"s": {"seeding": "shared"}}}
        self.assertEqual(DG.interval_findings({"evaluations": scan, **shared})["status"], "passed")
        self.assertEqual(codes(DG.interval_findings({"evaluations": scan})), ["design.interval_overlap_sets"])
        pair = [ev("pde1", "pde-split-pair", 22, 0, 5000, pair="p", efficiency_one=True),
                ev("pdep", "pde-split-pair", 22, 0, 5000, pair="p")]
        self.assertEqual(DG.interval_findings({"evaluations": pair})["status"], "passed")
        prod = [ev("map", "mapping-run", 22, 0, 5000, scan="t", point=0)]
        self.assertEqual(DG.interval_findings({"evaluations": pair + prod})["status"], "passed")
        prod = [ev("map", "mapping-run", 22, 0, 4000, scan="t", point=0)]    # not the identical interval
        self.assertEqual(DG.interval_findings({"evaluations": pair + prod})["status"], "failed")

    def test_seed_blocks(self):
        s, t = DG.block_seed("series", "study", "G7", "ens", 0)
        self.assertEqual((s, t), (seeds.H("series", "study", "G7", "ens", 0, 0), 0))
        s2, t2 = DG.block_seed("series", "study", "G7", "ens", 0, registered={s})
        self.assertEqual((t2, s2), (1, seeds.H("series", "study", "G7", "ens", 0, 1)))
        self.assertEqual(DG.member_interval(3, 1000, 10), (3000, 1000))
        with self.assertRaises(DG.CheckError):
            DG.member_interval(0, 2 ** 31, 4)
        blocks = [{"block": "a", "logical_run_seed": s, "t": 0, "m_blk": 10, "N_ev": 1000},
                  {"block": "b", "logical_run_seed": s2, "t": 1, "m_blk": 10, "N_ev": 1000}]
        self.assertEqual(DG.block_findings(blocks), [])
        self.assertEqual(codes({"findings": DG.block_findings([blocks[0], dict(blocks[1], logical_run_seed=s)])}),
                         ["design.seed_collision"])
        self.assertEqual(codes({"findings": DG.block_findings([dict(blocks[0], m_blk=2 ** 20, N_ev=2 ** 13)])}),
                         ["design.block_size"])

    def test_one_digitization_path_per_readout(self):
        a = [dict(GOOD[0], digitization={"zdc": "job"}), dict(GOOD[1], digitization={"zdc": "job"})]
        self.assertEqual(DG.interval_findings({"evaluations": a})["status"], "passed")
        a[1]["digitization"] = {"zdc": "direct"}
        self.assertEqual(codes(DG.interval_findings({"evaluations": a})), ["design.digi_mixed_paths"])
        a[1]["digitization"] = {"other": "direct"}                    # another readout system may differ
        self.assertEqual(DG.interval_findings({"evaluations": a})["status"], "passed")


SNAPSHOT = {"schema": "condition-snapshot/1", "readout": "zdc", "fields": ["volume", "channel"],
            "defaults": {"gain_factor": 1.0},
            "iovs": [{"start_ns": 0, "end_ns": 10 ** 12, "rows": [{"cell": {"volume": 1, "channel": 0},
                                                                     "gain_factor": 1.1}]}]}


class DigiJobs(unittest.TestCase):
    """Section 6.6 (every g4sim-digi-job/1), section 15.3.19."""

    def setUp(self):
        self.d = G.documents()
        self.ev = ev("fit", "fit", 12345, 0, 20)
        self.job = DG.job_from_documents(self.d["pipeline"], self.d["maps"]["light"], "zdc", [0, 1], 12345)

    def check(self, job, **entry):
        p = {"evaluations": [self.ev], "digi_jobs": [{"job": job, "evaluation": "fit", "readout": "zdc",
                                                      "map": "light", **entry}],
             "node_binding": {"parameters": G.BINDINGS}, "event_time": {"kind": "linear", "t0_ns": 0,
                                                                        "ns_per_event": 1000}}
        return sorted({f["code"] for f in DG.digi_job_findings(p, {**self.d, "conditions": SNAPSHOT})})

    def test_positive_controls(self):
        self.assertEqual(self.check(self.job), [])
        self.assertEqual(self.check(digitize.job_with_keys(self.job), implementation="g4sim_digi"), [])
        at = dict(self.job, stage=dict(self.job["stage"], light_yield_per_MeV=220.0))
        self.assertEqual(self.check(at, theta={"light_yield": 220.0}), [])   # the pipeline at the entry's theta
        cj = DG.job_from_documents(self.d["pipeline"], self.d["maps"]["light"], "zdc", [0, 1], 12345,
                                   conditions=SNAPSHOT, event_time={"kind": "linear", "t0_ns": 0, "ns_per_event": 1000},
                                   interval=(0, 20))
        self.assertEqual(self.check(cj), [])
        digitize.digitize(cj, [(3, 1, 0, 0.2, 0.05, 4)])               # g4sim's own checks accept the built job

    def test_seed_changed_without_recomputing_keys(self):
        keyed = digitize.job_with_keys(self.job)
        self.assertEqual(self.check(dict(keyed, run_seed=999)), ["design.digi_run_seed", "design.digi_stale_keys"])
        self.ev["logical_run_seed"] = 999                              # the evaluation's seed is 999 too
        self.assertEqual(self.check(dict(keyed, run_seed=999)), ["design.digi_stale_keys"])
        self.assertEqual(self.check(digitize.job_with_keys(dict(self.job, run_seed=999))), [])

    def test_replica_keys_and_conditions(self):
        self.assertEqual(self.check(dict(self.job, replica=1)), ["design.digi_replica"])
        self.assertEqual(self.check(self.job, implementation="g4sim_digi"), ["design.digi_keys_missing"])
        cj = DG.job_from_documents(self.d["pipeline"], self.d["maps"]["light"], "zdc", [0, 1], 12345,
                                   conditions=SNAPSHOT, event_time={"kind": "linear", "t0_ns": 0, "ns_per_event": 1000},
                                   interval=(0, 20))
        self.assertEqual(self.check(dict(cj, keys={"stage": [1, 2]})), ["design.digi_keys_with_conditions"])
        self.assertEqual(self.check(cj, implementation="g4sim_digi"), ["design.digi_conditions_not_python"])
        wrong = dict(cj, event_time_ns={**cj["event_time_ns"], "3": 1})
        self.assertEqual(self.check(wrong), ["design.digi_event_time"])
        other = copy.deepcopy(SNAPSHOT)
        other["iovs"][0]["rows"][0]["gain_factor"] = 1.2
        self.assertEqual(self.check(dict(cj, conditions=other)), ["design.digi_documents"])

    def test_fields_differ_from_the_hashed_documents(self):
        for field, change in (("stage", lambda j: j["stage"].update(light_yield_per_MeV=210.0)),
                              ("sensor", lambda j: j["sensor"].update(gain=1.1)),
                              ("electronics", lambda j: j["electronics"].update(threshold=0.5)),
                              ("efficiencies", lambda j: j["efficiencies"].update({"0": [0.1, 0.06]})),
                              ("channels", lambda j: j.update(channels=["b", "a"])),
                              ("timing", lambda j: j.update(timing={"decay_ns": 2.0, "transit": {
                                  "kind": "exponential", "transit_ns": 1.0}}))):
            job = copy.deepcopy(self.job)
            change(job)
            with self.subTest(field):
                self.assertEqual(self.check(job), ["design.digi_documents"])
        self.assertEqual(self.check(self.job, map_replica=0), [])


if __name__ == "__main__":
    unittest.main()
