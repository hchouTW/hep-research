"""destriper-product/1: the solver's record, the map and baselines, and the embedded reconstruction-product/1 with the
reconstruction:scan-v1 global block (W7 global grown to the destriping operator; A34: the null mode is named, or fixed by the stated
constraint). One JSON document, sorted keys, shortest round-trip floats; a product is never overwritten."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from destripe_recipe import LABEL, RECIPE

FORMAT = "destriper-product/1"
KEYS = frozenset({"format", "recipe", "label", "product_id", "input", "solver", "method_card", "map", "baselines", "reconstruction_product"})
SOLVER_KEYS = frozenset({"method", "constraint", "stopping", "max_iterations", "iterations", "relative_residual", "residual"})
CONSTRAINTS = ("zero-sum", "none")
ZERO_SUM = "zero-sum of the baselines (astro-ph/0501504, as t11-cells.md F38 records it)"
METHOD = ("conjugate gradient on the reduced destriping system D a = F^T Z y, restricted to the zero-sum subspace of the baselines "
          "(every residual and direction projected), then the map by binning m = M^-1 P^T (y - F a)")
RESIDUAL = "||Pi (F^T Z y - D a)||_2 / ||Pi F^T Z y||_2, recomputed from a at every iteration; Pi removes the mean"


class ProductError(ValueError):
    """A malformed or incomplete product (exit 2)."""


def _names(stream) -> list[str]:
    return [f"map-{p}" for p in range(stream.pixels)] + [f"baseline-{b}" for b in range(stream.baselines)]


def _unit(width: int, index: int) -> list[int]:
    return [int(column == index) for column in range(width)]


def _reported(stream, sky: list[float], offsets: list[float], constraint: str) -> list[dict]:
    width = stream.pixels + stream.baselines
    if constraint == "zero-sum":
        return [{"weights": _unit(width, index), "value": value} for index, value in enumerate(sky + offsets)]
    # no constraint: only combinations orthogonal to the offset mode (1 on the map, -1 on the baselines) are determined
    items = [{"weights": [a - b for a, b in zip(_unit(width, p), _unit(width, 0))], "value": sky[p] - sky[0]} for p in range(1, stream.pixels)]
    items += [{"weights": [a - b for a, b in zip(_unit(width, stream.pixels + k), _unit(width, stream.pixels))], "value": offsets[k] - offsets[0]}
              for k in range(1, stream.baselines)]
    items.append({"weights": [a + b for a, b in zip(_unit(width, 0), _unit(width, stream.pixels))], "value": sky[0] + offsets[0]})
    return items


def scan_block(stream, sky: list[float], offsets: list[float], constraint: str, input_sha256: str, noise_premise: str) -> dict:
    names = _names(stream)
    design = [_unit(len(names), int(p)) for p in stream.pixel]
    for t, row in enumerate(design):
        row[stream.pixels + t // stream.length] = 1
    stated = {"statement": ZERO_SUM, "weights": [0] * stream.pixels + [1] * stream.baselines, "value": 0} if constraint == "zero-sum" else None
    return {"subcase": "global", "source_ref": f"destriper-timestream/1 sha256:{input_sha256}",
            "coordinates": [{"axis": "sample-index", "kind": "index", "unit": "1"}, {"axis": "pixel-index", "kind": "index", "unit": "1"}],
            "conditions_ref": "none: no calibration payload is consumed",
            "response_ref": "pointing: one pixel and one baseline per sample, unit response",
            "noise_model": {"kind": "white-uniform", "premises": [noise_premise]}, "merging": {"kind": "joint-model"},
            "unidentifiable": [] if constraint == "zero-sum" else names,
            "model": {"parameters": names, "design": design, "observation": [float(y) for y in stream.value]},
            "reported": _reported(stream, sky, offsets, constraint), "constraint": stated, "regularization": "none",
            "uniqueness_claim": constraint == "zero-sum"}


def build(stream, solution, constraint: str, product_id: str, input_sha256: str, card_path: Path) -> dict:
    if constraint not in CONSTRAINTS:
        raise ProductError(f"constraint is one of {CONSTRAINTS}")
    sky, offsets = [float(v) for v in solution.map], [float(v) for v in solution.baselines]
    embedded = {"schema": "reconstruction-product/1", "product_id": product_id, "revision": 1, "collection": "destriped-map",
                "native": {"type": "destriper::ScanSolution"}, "presence": "present", "role": "reconstruction-input",
                "conditions_used": [], "required_extensions": ["reconstruction:scan-v1"],
                "scan": scan_block(stream, sky, offsets, constraint, input_sha256, stream.noise_premise)}
    return {"format": FORMAT, "recipe": RECIPE, "label": LABEL, "product_id": product_id,
            "input": {"format": "destriper-timestream/1", "role": "reconstruction-input", "sha256": input_sha256, "samples": stream.samples,
                      "pixels": stream.pixels, "baselines": stream.baselines, "baseline_length": stream.length, "unit": stream.unit},
            "solver": {"method": METHOD, "constraint": constraint, "stopping": solution.stopping, "max_iterations": solution.max_iterations,
                       "iterations": solution.iterations, "relative_residual": solution.relative_residual, "residual": RESIDUAL},
            "method_card": {"path": Path(card_path).name, "sha256": hashlib.sha256(Path(card_path).read_bytes()).hexdigest()},
            "map": sky, "baselines": offsets, "reconstruction_product": embedded}


def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def dumps(document: dict) -> str:
    return json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"


def read(document, card_folder: Path) -> dict:
    """Refuse a malformed or incomplete product; the method card it names must be the one beside the recipe, byte for byte."""
    if not isinstance(document, dict) or document.get("format") != FORMAT:
        raise ProductError(f"not a {FORMAT} document")
    if set(document) != KEYS:
        raise ProductError(f"{FORMAT} has exactly the keys {sorted(KEYS)}; missing {sorted(KEYS - set(document))}, unknown {sorted(set(document) - KEYS)}")
    if document["recipe"] != RECIPE or document["label"] != LABEL:
        raise ProductError(f"the recipe is {RECIPE} with the label {LABEL!r}")
    solver_record = document["solver"]
    if not isinstance(solver_record, dict) or set(solver_record) != SOLVER_KEYS or solver_record["constraint"] not in CONSTRAINTS:
        raise ProductError(f"the solver record has exactly {sorted(SOLVER_KEYS)} and a constraint of {CONSTRAINTS}")
    shape = document["input"]
    for key in ("map", "baselines"):
        if not isinstance(document[key], list) or not all(_number(v) for v in document[key]):
            raise ProductError(f"{key} is a list of numbers")
    if not isinstance(shape, dict) or len(document["map"]) != shape.get("pixels") or len(document["baselines"]) != shape.get("baselines"):
        raise ProductError("the map and baselines do not have the input's pixel and baseline counts")
    for key in ("stopping", "relative_residual"):
        if not _number(solver_record[key]):
            raise ProductError(f"the solver record's {key} is a number")
    if solver_record["relative_residual"] > solver_record["stopping"]:
        raise ProductError("the recorded residual is above the stopping value: a product is written only when converged")
    card = document["method_card"]
    if not isinstance(card, dict) or not isinstance(card.get("path"), str) or not isinstance(card.get("sha256"), str):
        raise ProductError("the method card is an object with a path and a sha256")
    path = Path(card_folder) / card["path"]
    if Path(card["path"]).name != card["path"] or not path.is_file():
        raise ProductError(f"the method card {card['path']!r} is not beside the recipe")
    if hashlib.sha256(path.read_bytes()).hexdigest() != card["sha256"]:
        raise ProductError("the method card differs from the one the product was made with")
    embedded = document["reconstruction_product"]
    if not isinstance(embedded, dict) or not isinstance(embedded.get("scan"), dict) or not isinstance(embedded["scan"].get("reported"), list):
        raise ProductError("the embedded reconstruction-product/1 with a scan block and its reported values is missing")
    try:
        found = [item["value"] for item in embedded["scan"]["reported"]]
    except (TypeError, KeyError) as exc:
        raise ProductError("every reported component of the embedded scan block has a value") from exc
    sky, offsets = document["map"], document["baselines"]
    if solver_record["constraint"] == "zero-sum":
        expected = sky + offsets
    else:
        expected = [sky[p] - sky[0] for p in range(1, len(sky))] + [offsets[k] - offsets[0] for k in range(1, len(offsets))] + [sky[0] + offsets[0]]
    if found != expected:
        raise ProductError("the top-level map and baselines are not the embedded product's reported values")
    return document
