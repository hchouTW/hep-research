"""Fast-simulation envelopes in the specification (Section 6.2.9, S8): the rules check-spec applies to a fast_sim_envelope requirement.

A fast_sim_envelope requirement selects the envelope templates of a fast-simulation hook. Geant4 attaches a G4VFastSimulationModel to a
G4Region, whose root logical is the envelope, and the model is asked about every track that enters it. Rules: (1) no daughter inside an
envelope, so a model that takes a track over at the envelope's entrance leaves no volume of the specification unvisited unseen; (2) each
envelope declares a region of its own, and no other template falls into that region, so the region's root is the envelope alone and the
model sees no other volume; (3) no model in the specification: which model (a study's, or a test model) belongs to the run card."""
from __future__ import annotations

from core.geometry.numbers import GeometryError

NEED = "fast_sim_envelope"
MODEL_KEYS = ("model", "model_kind", "particles")


def check(nodes: dict, templates: dict, requirements: list, tree: dict) -> None:
    """Rules 1 to 3 for every fast_sim_envelope requirement of the expanded IR. nodes are the specification's templates and world."""
    envelopes: dict[str, int] = {}
    for at, requirement in enumerate(requirements):
        if requirement.get("need") != NEED:
            continue
        where = f"/physics_requirements/{at}"
        model = [key for key in MODEL_KEYS if key in requirement]
        if model:
            raise GeometryError("envelope-model-in-spec", f"{model[0]} belongs to the run card's fast_sim block, not the specification (rule 3)", where)
        selected = requirement.get("templates", [])
        if not selected:
            raise GeometryError("envelope-select", "a fast_sim_envelope requirement selects its envelope templates", where)
        for envelope in selected:
            if envelope in envelopes:
                raise GeometryError("envelope-twice", f"{envelope!r} is the envelope of requirements {envelopes[envelope]} and {at}", where)
            envelopes[envelope] = at
            if tree.get(envelope):
                raise GeometryError("envelope-daughter", f"{len(tree[envelope])} volume(s) placed inside the envelope {envelope!r} (rule 1)", where)
            region = nodes[envelope].get("region")
            if not region:
                raise GeometryError("envelope-region", f"the envelope {envelope!r} declares no region of its own; the model attaches to a region (rule 2)", where)
            sharing = sorted(name for name, record in templates.items() if record["region"] == region and name != envelope)
            if sharing:
                raise GeometryError("envelope-region", f"region {region!r} of the envelope {envelope!r} also holds {sharing}; the envelope must be its only volume (rule 2)", where)
