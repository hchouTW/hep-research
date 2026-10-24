"""Geant4 program A2.4/A2.6 (contracts.validate.geant4_tree_v1): the tree-v1 configuration hash of an effective
config's geometry tree.

- One geometry built twice with other volume names and another creation order gives the same tree_sha256 and target
  hash and a different naming_sha256.
- Changing a physical quantity (thickness, material density or composition, position) changes the hash.
- Moving the whole target leaves the target hash unchanged (transforms relative to the first target placement).
- The configuration decision follows A1.3: vacuum world, no field, every placement in the target -> isolated.
- geant4_configuration dispatches by hash_scheme; a tree that recorded nothing is refused."""
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from contracts.validate import geant4_configuration, geant4_tree_thickness_mm, geant4_tree_v1  # noqa: E402


def h(x: float) -> str:
    return float(x).hex()


def material(name, density, z=14.0, a=28.0855):
    return {"name": name, "density_g_cm3": h(density), "state": "solid", "temperature_K": h(293.15),
            "pressure_Pa": h(101325.0), "mean_excitation_energy_eV": h(173.0),
            "elements": [{"symbol": "X", "z": h(z), "a_g_mole": h(a), "mass_fraction": h(1.0)}]}


def tree(slabs, world="Vac", names=None, order=None, shift=0.0, world_density=1e-25, field=False):
    """A slab stack along x: slabs = [(lv name, material name, density, thickness)]; names renames volumes;
    order permutes the creation order of the placements."""
    names = names or {}
    mats = {world: world_density}
    for _, m, d, _ in slabs:
        mats[m] = d
    rn = names.get
    lvs = [{"id": 0, "name": rn("World", "World"), "solid": {"type": "G4Box", "parameters": {
        "half_x_mm": h(50.0), "half_y_mm": h(50.0), "half_z_mm": h(50.0)}}, "material": rn(world, world),
        "field": {"present": True, "source": "probe"} if field else None}]
    ids = {}
    for lv, m, _, t in slabs:
        if lv not in ids:
            ids[lv] = len(lvs)
            lvs.append({"id": ids[lv], "name": rn(lv, lv), "solid": {"type": "G4Box", "parameters": {
                "half_x_mm": h(t / 2), "half_y_mm": h(10.0), "half_z_mm": h(10.0)}}, "material": rn(m, m), "field": None})
    stack = sum(t for *_, t in slabs)
    x = -stack / 2 + shift
    pls = []
    for k, (lv, _, _, t) in enumerate(slabs):
        pls.append({"name": rn(lv, lv), "copy_number": k, "logical": ids[lv], "mother_logical": 0,
                    "translation_mm": [h(x + t / 2), h(0.0), h(0.0)], "rotation": None, "kind": "placement"})
        x += t
    if order:
        pls = [pls[i] for i in order]
    world_pl = {"name": rn("World", "World"), "copy_number": 0, "logical": 0, "mother_logical": None,
                "translation_mm": [h(0.0)] * 3, "rotation": None, "kind": "placement"}
    return {"geometry": {"tree": {"logical_volumes": lvs, "placements": [world_pl] + pls,
                                  "materials": [material(rn(m, m), d) for m, d in mats.items()],
                                  "global_field": None}}}


STACK = [("Si", "Silicon", 2.33, 0.3), ("Al", "Aluminium", 2.699, 1.0), ("Si", "Silicon", 2.33, 0.3)]


class TreeV1(unittest.TestCase):
    def test_names_and_creation_order_do_not_change_the_physics_hashes(self):
        a = geant4_tree_v1(tree(STACK), ["Si", "Al"])
        renamed = {"Si": "sensor", "Al": "absorber", "Silicon": "G4_Si", "Aluminium": "G4_Al", "World": "Hall",
                   "Vac": "G4_Galactic"}
        b = geant4_tree_v1(tree(STACK, names=renamed, order=[2, 0, 1]), ["sensor", "absorber"])
        self.assertEqual(a["tree_sha256"], b["tree_sha256"])
        self.assertEqual(a["target_geometry_sha256"], b["target_geometry_sha256"])
        self.assertNotEqual(a["naming_sha256"], b["naming_sha256"])
        self.assertEqual(a["configuration"], b["configuration"])

    def test_every_physical_change_changes_the_hash(self):
        base = geant4_tree_v1(tree(STACK), ["Si", "Al"])
        changes = {"thickness": [("Si", "Silicon", 2.33, 0.3), ("Al", "Aluminium", 2.699, 1.1),
                                 ("Si", "Silicon", 2.33, 0.3)],
                   "density": [("Si", "Silicon", 2.33, 0.3), ("Al", "Aluminium", 2.7, 1.0), ("Si", "Silicon", 2.33, 0.3)],
                   "order of slabs": [("Al", "Aluminium", 2.699, 1.0), ("Si", "Silicon", 2.33, 0.3),
                                      ("Si", "Silicon", 2.33, 0.3)]}
        for what, stack in changes.items():
            with self.subTest(change=what):
                c = geant4_tree_v1(tree(stack), ["Si", "Al"])
                self.assertNotEqual(c["target_geometry_sha256"], base["target_geometry_sha256"])
                self.assertNotEqual(c["tree_sha256"], base["tree_sha256"])
        moved = geant4_tree_v1(tree(STACK, shift=5.0), ["Si", "Al"])
        self.assertNotEqual(moved["tree_sha256"], base["tree_sha256"])  # the position in the world is physics
        self.assertEqual(moved["target_geometry_sha256"], base["target_geometry_sha256"])  # the target is the same

    def test_a_repeated_target_moved_by_any_amount_keeps_its_hash(self):
        """Review finding: the reference placement was chosen by hex-string order, which a shift can reorder."""
        pair = [("Pb", "Lead", 11.35, 0.5), ("Pb", "Lead", 11.35, 0.5)]
        ref = geant4_tree_v1(tree(pair), ["Pb"])["target_geometry_sha256"]
        for shift in (0.75, 1.3, -2.6, 7.123):
            with self.subTest(shift=shift):
                self.assertEqual(geant4_tree_v1(tree(pair, shift=shift), ["Pb"])["target_geometry_sha256"], ref)

    def test_composition_changes_the_hash(self):
        t1, t2 = tree(STACK), tree(STACK)
        for m in t2["geometry"]["tree"]["materials"]:
            if m["name"] == "Aluminium":
                m["elements"][0]["z"] = h(13.0)
        self.assertNotEqual(geant4_tree_v1(t1, ["Al"])["target_geometry_sha256"],
                            geant4_tree_v1(t2, ["Al"])["target_geometry_sha256"])

    def test_configuration_decision(self):
        self.assertEqual(geant4_tree_v1(tree(STACK), ["Si", "Al"])["configuration"], "isolated")
        self.assertEqual(geant4_tree_v1(tree(STACK), ["Si"])["configuration"], "embedded")  # Al outside the target
        self.assertEqual(geant4_tree_v1(tree(STACK, world_density=1.2e-3), ["Si", "Al"])["configuration"], "embedded")
        self.assertEqual(geant4_tree_v1(tree(STACK, field=True), ["Si", "Al"])["configuration"], "embedded")

    def test_identical_daughters_are_ordered_by_copy_number_and_counted(self):
        t = tree(STACK)
        pls = t["geometry"]["tree"]["placements"]
        pls[3]["translation_mm"] = pls[1]["translation_mm"]  # two Si copies at the same place
        self.assertEqual(geant4_tree_v1(t, ["Si", "Al"])["canonical_ties"], 1)  # counted once

    def test_random_creation_orders_agree(self):
        stack = [(f"L{k % 3}", f"M{k % 3}", 1.0 + k % 3, 0.1 * (1 + k % 4)) for k in range(12)]
        ref = geant4_tree_v1(tree(stack), ["L0", "L1", "L2"])
        rng = random.Random(5)
        for _ in range(10):
            order = list(range(12))
            rng.shuffle(order)
            got = geant4_tree_v1(tree(stack, order=order), ["L0", "L1", "L2"])
            self.assertEqual((got["tree_sha256"], got["target_geometry_sha256"]),
                             (ref["tree_sha256"], ref["target_geometry_sha256"]))

    def test_thickness_dispatch_and_refusals(self):
        self.assertEqual(geant4_tree_thickness_mm(tree(STACK)), {"Si": 0.3, "Al": 1.0})
        sim = {"effective_config": tree(STACK), "geometry": {"lateral_mm": 20.0, "layers": [
            {"slabs": [{"name": "Si", "material": "G4_Si", "thickness_mm": 0.3}]}], "world": {"material": "G4_Galactic"}}}
        self.assertEqual(geant4_configuration(sim, ["Si", "Al"], "tree-v1")["hash_scheme"], "tree-v1")
        self.assertEqual(geant4_configuration(sim, ["Si"], "spec-v1")["hash_scheme"], "spec-v1")
        with self.assertRaises(ValueError):
            geant4_configuration(sim, ["Si"], "tree-v0")
        with self.assertRaises(ValueError):
            geant4_configuration({"geometry": sim["geometry"]}, ["Si"], "tree-v1")
        with self.assertRaises(ValueError):
            geant4_tree_v1({"geometry": {"tree": None}}, ["Si"])
        with self.assertRaises(ValueError):
            geant4_tree_v1(tree(STACK), ["Pb"])

    def test_the_hash_is_json_of_physics_only(self):
        t = tree(STACK)
        blob = json.dumps(geant4_tree_v1(t, ["Si", "Al"]))
        self.assertNotIn("Silicon", blob)


if __name__ == "__main__":
    unittest.main()
