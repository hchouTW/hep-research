"""core/calibration/model_identity (simulator calibration phase 3): the g4sim model identity of Part B section 5.1,
clause 1 item 2 of section 5.2, D86, the section 19 derived-fields item (approval A12: integration tests that the
normalization of response-pipeline/1 and of the run card produces no derived fields, run_seed and replica excluded, the
overlay hashed and not the IR), the g4sim-digi-job/1 check against the hashed documents, the model-identity cases of
section 15.3.19 and the g4sim model-identity regression case of section 15.3a. Each negative test has a positive
control. The documents are g4sim's real formats, checked by g4sim's own readers (calibration_g4sim_fixtures)."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration_g4sim_fixtures as G  # noqa: E402
from contracts import geometry  # noqa: E402
from contracts.schema import validate  # noqa: E402
from core.calibration import contract as cc  # noqa: E402
from core.calibration import deps  # noqa: E402
from core.calibration import model_identity as mi  # noqa: E402
from core.canonical import canonical_sha256  # noqa: E402
from core.geometry import identity as gid  # noqa: E402
from core.simulation import conditions, response  # noqa: E402

sys.path.insert(0, str(ROOT / "adapters" / "geant4" / "assets"))
import g4sim_run as G4RUN  # noqa: E402

TABLES = G.tables()
MASKS = mi.masks(G.contract())


def ident(masks=None, **over):
    return mi.identity(G.documents(**over), MASKS if masks is None else masks, TABLES)


class G4simReaders(unittest.TestCase):
    """The fixture documents are what g4sim accepts (precondition of every test below)."""

    def test_documents_pass_g4sim(self):
        self.assertEqual(geometry.check_spec(G.detector_text(), folder=G.SPECS, overlay=G.overlay())["status"], "ok")
        for doc, name in ((G.pipeline(), "response_pipeline.json"), (G.overlay(), "alignment_overlay.json"),
                          (G.snapshot(), "condition_snapshot.json"),
                          (json.loads(G.request_text()), "simulation_request.json")):
            self.assertEqual(validate(doc, name).errors, [], name)
        self.assertEqual(validate(G.run_card(), json.loads(G.RUN_SCHEMA.read_text())).errors, [])
        response.check_pipeline(G.pipeline())
        self.assertEqual(len(response.study_keys(G.pipeline(), ["ecal"])), 8)
        conditions.check_snapshot(G.snapshot(), fields=("volume", "channel"))


class DerivedFields(unittest.TestCase):
    """Section 19 (derived fields of the model identity), approval A12."""

    def test_normalization_adds_no_field(self):
        for name, doc, table in (("response-pipeline", G.pipeline(), "response-pipeline"),
                                 ("run card", G.run_card(), "run-card"),
                                 ("request", json.loads(G.request_text()), "simulation-request"),
                                 ("overlay", G.overlay(), "alignment-overlay"),
                                 ("snapshot", G.snapshot(), "condition-snapshot")):
            with self.subTest(name):
                got = mi.normalize(json.dumps(doc), TABLES[table])
                self.assertEqual(mi.leaf_pointers(got), mi.leaf_pointers(doc))
        spec_text = G.detector_text()
        self.assertEqual(mi.leaf_pointers(mi.read_spec(spec_text, TABLES["detector-spec"])),
                         mi.leaf_pointers(json.loads(spec_text)))

    def test_a_theta_change_moves_only_its_leaf(self):
        """Negative: a theta value that changed a second field would leave a derived value in the hash; the positive
        control is the one bound leaf, which moves."""
        for name, a, b, table, pointer in (
                ("response-pipeline", G.pipeline(200.0), G.pipeline(250.0), "response-pipeline",
                 "/stages/0/parameters/light_yield_per_MeV/value"),
                ("run card", G.run_card(cuts_mm={"default": "0.7"}), G.run_card(cuts_mm={"default": "1.5"}), "run-card",
                 "/physics/cuts_mm/default")):
            with self.subTest(name):
                na, nb = (mi.normalize(json.dumps(x), TABLES[table]) for x in (a, b))
                moved = {p for p in mi.leaf_pointers(na) if _at(na, p) != _at(nb, p)}
                self.assertEqual(moved, {pointer})

    def test_params_expressions_stay_strings(self):
        """g4sim keeps params expressions as strings before expansion, so masking the param masks its uses."""
        a = mi.read_spec(G.detector_text(thickness="w", params={"w": "0.065"}), TABLES["detector-spec"])
        b = mi.read_spec(G.detector_text(thickness="w", params={"w": "0.08"}), TABLES["detector-spec"])
        self.assertEqual(_at(a, "/templates/crystal/modifiers/0/shell/thickness_mm"), "w")
        self.assertEqual(mi.spec_hash(a, ["/params/w"]), mi.spec_hash(b, ["/params/w"]))
        self.assertNotEqual(mi.spec_hash(a), mi.spec_hash(b))

    def test_only_detector_spec_spellings_are_normalized_by_g4sim(self):
        """g4sim's geometry_id is the same for two spellings of a detector-spec value; its run_id and request_id are
        not the same for two spellings of a run-card or request number, so this workflow normalizes those itself."""
        one, two = (geometry.check_spec(G.detector_text(birks=v), folder=G.SPECS) for v in ("0.126", "0.1260"))
        self.assertEqual(one["geometry_id"], two["geometry_id"])
        c1, c2 = G.run_card(), G.run_card()
        c1["kill_policy"]["min_kinetic_energy_MeV"], c2["kill_policy"]["min_kinetic_energy_MeV"] = 1, 1.0
        self.assertNotEqual(*(G4RUN.run_id(one["geometry_id"], "0" * 64, c, G.SHA) for c in (c1, c2)))
        self.assertEqual(*(mi.run_physics_hash(c, TABLES["run-card"]) for c in (c1, c2)))
        rq1 = json.loads(G.request_text())
        rq2 = copy.deepcopy(rq1)
        rq2["source"]["direction"]["fixed"]["vector"] = [0, 0, 1.0]
        self.assertNotEqual(gid.request_id(rq1, one["geometry_id"]), gid.request_id(rq2, one["geometry_id"]))
        self.assertEqual(mi.request_hash(rq1, TABLES["simulation-request"]),
                         mi.request_hash(rq2, TABLES["simulation-request"]))
        p1, p2 = G.pipeline(), G.pipeline()
        p2["stages"][3]["parameters"]["bits"]["value"] = 10.0
        self.assertNotEqual(canonical_sha256(gid.in_decimals(p1)), canonical_sha256(gid.in_decimals(p2)))
        self.assertEqual(mi.pipeline_document_hash(p1, TABLES["response-pipeline"]),
                         mi.pipeline_document_hash(p2, TABLES["response-pipeline"]))
        self.assertEqual(mi.pipeline_document_hash(json.dumps(p1).replace("0.6", "0.60"), TABLES["response-pipeline"]),
                         mi.pipeline_document_hash(p1, TABLES["response-pipeline"]))

    def test_run_seed_and_replica_are_excluded(self):
        self.assertEqual(ident(response_pipeline=G.pipeline(run_seed=99, replica=3)), ident())
        self.assertNotEqual(ident(response_pipeline=_with(G.pipeline(), 2, "excess_noise", 0.2))["response_pipeline"],
                            ident()["response_pipeline"])               # positive control: a non-theta stage value
        with self.assertRaises(mi.IdentityError) as caught:
            mi.pipeline_document_hash(G.pipeline(), TABLES["response-pipeline"], ["/run_seed"])
        self.assertEqual(caught.exception.code, "identity.pipeline_seed")

    def test_the_run_block_is_excluded(self):
        card = G.run_card()
        card["run"].update(events=50, first_event=1000, logical_run_seed=7, threads=1, mode="serial", chunk=4)
        card["output"] = {"csv": "events.csv"}
        self.assertEqual(ident(run_card=card), ident())
        self.assertNotEqual(ident(run_card=G.run_card(decay=False))["run_physics"], ident()["run_physics"])
        with self.assertRaises(mi.IdentityError) as caught:
            mi.run_physics_hash(G.run_card(), TABLES["run-card"], ["/run/events"])
        self.assertEqual(caught.exception.code, "identity.run_block")


class Masking(unittest.TestCase):
    def test_theta_and_phi_fields_are_masked(self):
        """Section 15.3a: a model template keeps its identity when theta, phi and their derived fields change, and
        changes it when a non-parametric physics setting changes."""
        moved = G.documents(detector_spec=G.detector_text(birks="0.2", thickness="0.08"),
                            simulation_request=G.request_text("800"), run_card=G.run_card(cuts_mm={"default": "2"}),
                            response_pipeline=G.pipeline(light_yield=300.0, gain=1.0),
                            condition_snapshot=G.snapshot(threshold=3.0), alignment_overlay=G.overlay("0.07"))
        masks = mi.masks(dict(G.contract(), parameters=G.contract()["parameters"] + [
            G.parameter("shift_x", "theta", "transport", "alignment-overlay", "/shifts/0/delta_mm/0")]))
        self.assertEqual(mi.identity(moved, masks, TABLES), ident(masks))
        for name, over in (("material density", {"detector_spec": G.detector_text(birks="0.126").replace(
                               b'"density_g_cm3": "1.85"', b'"density_g_cm3": "1.9"')}),
                           ("particle", {"simulation_request": G.request_text().replace(b'"e+"', b'"e-"')}),
                           ("physics list", {"run_card": G.run_card(reference_list="QGSP_BERT")}),
                           ("resolution scale", {"response_pipeline": _with(G.pipeline(), 0, "resolution_scale", 0.7)}),
                           ("dead channel", {"condition_snapshot": G.snapshot(dead=True)}),
                           ("event-time rule", {"event_time_rule": {"kind": "linear", "start_ns": 0, "step_ns": 500}}),
                           ("map", {"efficiency_map": G.efficiency_map(seed=8)}),
                           ("build", {"build_environment": dict(G.BUILD, geant4_version="11.3.0")})):
            with self.subTest(name):
                self.assertNotEqual(ident(masks, **over), ident(masks))

    def test_a_container_or_missing_field_is_refused(self):
        spec = mi.read_spec(G.detector_text(), TABLES["detector-spec"])
        self.assertEqual(len(mi.spec_hash(spec, ["/materials/FR4/ionisation/birks_mm_per_MeV"])), 64)  # control
        for pointer, code in (("/materials/FR4", "identity.mask_container"), ("/materials/LYSO/density_g_cm3",
                              "identity.mask_missing"), ("", "identity.pointer")):
            with self.subTest(pointer):
                with self.assertRaises(mi.IdentityError) as caught:
                    mi.spec_hash(spec, [pointer])
                self.assertEqual(caught.exception.code, code)

    def test_sources_and_labels_do_not_change_the_identity(self):
        """A change of provenance_id (labels and sources) does not change the model identity (section 5.1)."""
        a = ident()
        self.assertEqual(ident(detector_spec=G.detector_text(source_of_facts={"/materials": "other source"}),
                               alignment_overlay=G.overlay(description="survey 2"),
                               condition_snapshot=G.snapshot(description="conditions v2")), a)
        spec = json.loads(G.detector_text())
        spec["materials"]["FR4"]["facts"] = "measured"
        self.assertEqual(ident(detector_spec=json.dumps(spec).encode()), a)
        spec["materials"]["FR4"]["density_g_cm3"] = "1.86"
        self.assertNotEqual(ident(detector_spec=json.dumps(spec).encode()), a)       # positive control


class D86(unittest.TestCase):
    def test_overlay_is_the_second_hash_of_the_detector_item(self):
        a, none = ident(), ident(alignment_overlay=None)
        self.assertIsNone(none["detector_spec"][1])
        self.assertEqual(a["detector_spec"][0], none["detector_spec"][0])
        zero = ident(alignment_overlay=G.overlay("0"))
        self.assertNotEqual(zero["detector_spec"], none["detector_spec"])     # a zero-shift overlay is another model
        self.assertNotEqual(zero["detector_spec"], a["detector_spec"])       # unmasked: the shift is physics
        masks = dict(MASKS, **{"alignment-overlay": ["/shifts/0/delta_mm/0"]})
        self.assertEqual(ident(masks, alignment_overlay=G.overlay("0"))["detector_spec"],
                         ident(masks)["detector_spec"])

    def test_decimal_spellings_of_a_shift_give_one_identity(self):
        """A16 (iii): delta_mm entries are decimal strings; "0.05" and "0.050" are one value, one model identity;
        a different value still differs (positive control)."""
        self.assertEqual(ident(alignment_overlay=G.overlay("0.050"))["detector_spec"],
                         ident(alignment_overlay=G.overlay("0.05"))["detector_spec"])
        self.assertNotEqual(ident(alignment_overlay=G.overlay("0.051"))["detector_spec"],
                            ident(alignment_overlay=G.overlay("0.05"))["detector_spec"])
        with self.assertRaises(mi.IdentityError) as caught:
            ident(alignment_overlay=G.overlay("five"))
        self.assertEqual(caught.exception.code, "identity.number")

    def test_an_aligned_model_without_overlay_is_refused(self):
        masks = dict(MASKS, **{"alignment-overlay": ["/shifts/0/delta_mm/0"]})
        with self.assertRaises(mi.IdentityError) as caught:
            ident(masks, alignment_overlay=None)
        self.assertEqual(caught.exception.code, "identity.overlay_missing")

    def test_the_ir_is_never_hashed(self):
        ir = geometry.check_spec(G.detector_text(), folder=G.SPECS, overlay=G.overlay())["ir"]
        self.assertIn("alignment", ir["physical"])
        with self.assertRaises(mi.IdentityError):
            ident(detector_spec=json.dumps(ir).encode())
        self.assertEqual(len(ident()["detector_spec"][0]), 64)                  # control: the specification

    def test_snapshot_and_event_time_rule_fold_into_the_response_item(self):
        unmasked = dict(MASKS, **{"condition-snapshot": []})
        a, none = ident(unmasked), ident(unmasked, condition_snapshot=None, event_time_rule=None)
        self.assertNotEqual(a["response_pipeline"], none["response_pipeline"])
        a = ident()
        self.assertEqual(ident(condition_snapshot=G.snapshot(threshold=9.0))["response_pipeline"],
                         a["response_pipeline"])                                # the theta row value is masked
        self.assertNotEqual(ident(condition_snapshot=G.snapshot(gain_factor=1.1))["response_pipeline"],
                            a["response_pipeline"])                             # control: a psi value is not
        for pointer in ("/iovs/0/rows/0/dead", "/iovs/0/rows/0/temperature_K", "/defaults/gain_factor"):
            with self.subTest(pointer):
                with self.assertRaises(mi.IdentityError) as caught:
                    mi.snapshot_hash(G.snapshot(), TABLES["condition-snapshot"], [pointer], G.EVENT_TIME)
                self.assertEqual(caught.exception.code, "identity.snapshot_pointer")
        with self.assertRaises(mi.IdentityError) as caught:
            ident(event_time_rule=None)
        self.assertEqual(caught.exception.code, "identity.event_time_rule")


class ContractClause1Item2(unittest.TestCase):
    """Section 15.3.19: a model lacking one of the five identity items is rejected; section 15.3a: versions and result
    hashes rebuild in acyclic order (the items come from the documents only, then the contract hash)."""

    def test_valid_g4sim_contract(self):
        items = ident()
        c = G.contract(items)
        r = cc.check(c, G.F.releases(), identities={"nominal": ident()})
        self.assertEqual((r["status"], r["findings"]), ("accepted", []))
        self.assertEqual(cc.lock_hash(c), cc.lock_hash(G.contract(ident())))
        self.assertIn(cc.IDENTITY_UNVERIFIED, cc.check(c, G.F.releases())["deferred"])

    def test_missing_item(self):
        for item in mi.ITEMS:
            with self.subTest(item):
                items = ident()
                items.pop(item)
                got = {f["code"] for f in cc.check(G.contract(items), G.F.releases())["findings"]}
                self.assertIn("models.identity_missing", got)
        got = {f["code"] for f in cc.check(G.contract(None), G.F.releases())["findings"]}
        self.assertIn("models.identity_missing", got)

    def test_malformed_item(self):
        items = ident()
        items["detector_spec"] = items["detector_spec"][0]
        got = {f["code"] for f in cc.check(G.contract(items), G.F.releases())["findings"]}
        self.assertIn("models.identity_form", got)

    def test_declared_item_differs_from_the_documents(self):
        c = G.contract(ident())
        r = cc.check(c, G.F.releases(), identities={"nominal": ident(
            response_pipeline=_with(G.pipeline(), 2, "excess_noise", 0.2))})
        self.assertEqual({f["code"] for f in r["findings"]}, {"models.identity_mismatch"})
        r = cc.check(c, G.F.releases(), identities={})
        self.assertEqual({f["code"] for f in r["findings"]}, {"models.identity_documents"})

    def test_changed_items_mark_a_redo(self):
        """Section 10.3: a changed identity item marks the result as needing a redo (build_hash included)."""
        rebuilt = ident(build_environment=dict(G.BUILD, build_hash="cd" * 32))
        self.assertEqual(mi.changed_items(ident(), rebuilt), ["build_environment"])
        self.assertEqual(mi.changed_items(ident(), ident(simulation_request=G.request_text("900"))), [])


class IdentityChangeRedo(unittest.TestCase):
    """Section 10.3 and 15.3.19 (phase 4): after build_hash changes the result is marked as needing a redo, and so
    after any change of the five masked items; theta, phi values and provenance_id alone do not (A21: without a T2
    record the result is redone; the T2 carry-over itself: test_calibration_deps)."""

    def setUp(self):
        self.result = {"result_sha256": "ef" * 32, "model_identities": [{"model": "nominal", "identity": ident()}]}

    def decide(self, **over):
        return deps.identity_decision(self.result, [{"model": "nominal", "identity": ident(**over)}])

    def test_build_hash_change_marks_a_redo(self):
        d = self.decide(build_environment=dict(G.BUILD, build_hash="cd" * 32))
        self.assertEqual((d["status"], d["decision"], d["changed"]), ("failed", "redo",
                                                                     {"nominal": ["build_environment"]}))
        self.assertEqual(self.decide()["decision"], "unchanged")                  # positive control

    def test_each_identity_change_marks_a_redo(self):
        for name, over, item in (
                ("Geant4 version", {"build_environment": dict(G.BUILD, geant4_version="11.3.0")}, "build_environment"),
                ("data set version", {"build_environment": dict(G.BUILD, datasets={"G4EMLOW": "8.6",
                                                                                   "G4ENSDFSTATE": "2.3"})},
                 "build_environment"),
                ("material", {"detector_spec": G.detector_text().replace(b'"density_g_cm3": "1.85"',
                                                                         b'"density_g_cm3": "1.9"')}, "detector_spec"),
                ("response stage", {"response_pipeline": _with(G.pipeline(), 0, "resolution_scale", 0.7)},
                 "response_pipeline"),
                ("efficiency map", {"efficiency_map": G.efficiency_map(seed=8)}, "response_pipeline")):
            with self.subTest(name):
                d = self.decide(**over)
                self.assertEqual((d["decision"], d["changed"]), ("redo", {"nominal": [item]}))

    def test_theta_values_and_provenance_do_not(self):
        for name, over in (("design point / written-back theta", {"simulation_request": G.request_text("900")}),
                           ("provenance_id", {"detector_spec": G.detector_text(
                               source_of_facts={"/materials": "other source"}),
                               "condition_snapshot": G.snapshot(description="conditions v2")})):
            with self.subTest(name):
                self.assertEqual(self.decide(**over)["decision"], "unchanged")


class DigiJob(unittest.TestCase):
    """Section 5.1 and 15.3.19: a g4sim-digi-job/1 whose stage, sensor, electronics, timing, channels or efficiencies
    differ from the hashed documents is rejected (the check calib_design.py calls)."""

    def setUp(self):
        self.map = G.efficiency_map()
        self.pipe = G.pipeline()
        p = {s["name"]: {k: v["value"] for k, v in s["parameters"].items()} for s in self.pipe["stages"]}
        bins = {str(r["bin"]): response.efficiencies(self.map, r["bin"]) for r in self.map["form"]["bins"]}
        self.timing = {"decay_ns": 40.0, "transit": {"kind": "exponential", "transit_ns": 1.0}}
        self.job = {"schema": "g4sim-digi-job/1", "run_seed": 11, "replica": 0, "readout": "ecal",
                    "channels": list(self.map["channels"]), "stage": {"name": "scintillation", **p["scintillation"]},
                    "efficiencies": bins, "timing": self.timing,
                    "sensor": {"name": "sensor", **p["sensor"]}, "electronics": {"name": "electronics",
                                                                               **p["electronics"]}}

    def findings(self, job, **kw):
        kw.setdefault("map_document", self.map)
        kw.setdefault("timing", self.timing)
        return {f["code"] for f in mi.digi_job_findings(job, self.pipe, **kw)}

    def test_job_from_the_documents(self):
        self.assertEqual(self.findings(self.job), set())
        job = copy.deepcopy(self.job)
        job["stage"]["light_yield_per_MeV"] = 260.0
        self.assertEqual(self.findings(job, theta_values={"stage/light_yield_per_MeV": 260.0}), set())

    def test_each_difference_is_caught(self):
        cases = (("stage", lambda j: j["stage"].update(resolution_scale=0.5), "digi_job.differs"),
                 ("sensor", lambda j: j["sensor"].update(gain=1.2), "digi_job.differs"),
                 ("electronics", lambda j: j["electronics"].update(threshold=3.0), "digi_job.differs"),
                 ("extra field", lambda j: j["sensor"].update(saturation=1), "digi_job.differs"),
                 ("stage name", lambda j: j["sensor"].update(name="other"), "digi_job.stage_missing"),
                 ("channels", lambda j: j.update(channels=["right", "left"]), "digi_job.channels"),
                 ("efficiencies", lambda j: j["efficiencies"].update({"0": [0.0, 0.0]}), "digi_job.efficiencies"),
                 ("timing", lambda j: j["timing"].update(decay_ns=41.0), "digi_job.timing"),
                 ("conditions", lambda j: j.update(conditions=G.snapshot()), "digi_job.conditions"))
        for name, change, code in cases:
            with self.subTest(name):
                job = copy.deepcopy(self.job)
                change(job)
                self.assertIn(code, self.findings(job))
        job = copy.deepcopy(self.job)
        job["stage"]["light_yield_per_MeV"] = 260.0
        self.assertIn("digi_job.differs", self.findings(job))                    # theta not declared
        job = dict(copy.deepcopy(self.job), conditions=G.snapshot())
        self.assertEqual(self.findings(job, snapshot=G.snapshot()), set())
        self.assertIn("digi_job.conditions", self.findings(job, snapshot=G.snapshot(gain_factor=1.5)))
        rep = {str(r["bin"]): response.efficiencies(self.map, r["bin"], 3) for r in self.map["form"]["bins"]}
        self.assertIn("digi_job.efficiencies", self.findings(self.job, map_replica=3))
        self.assertEqual(self.findings(dict(self.job, efficiencies=rep), map_replica=3), set())


def _at(doc, pointer):
    for s in pointer[1:].split("/"):
        doc = doc[int(s)] if isinstance(doc, list) else doc[s]
    return doc


def _with(pipe, stage, name, value):
    pipe["stages"][stage]["parameters"][name]["value"] = value
    return pipe


if __name__ == "__main__":
    unittest.main()
