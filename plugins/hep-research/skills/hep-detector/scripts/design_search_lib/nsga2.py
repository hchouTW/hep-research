"""NSGA-II (K. Deb, A. Pratap, S. Agarwal, T. Meyarivan, IEEE Trans. Evol. Comput. 6 (2002) 182-197) over mixed genes,
standard library only and bit-for-bit reproducible for the same seed (random.Random, no hash or set ordering).

Genes: {"type": "real", "lo", "hi"}, {"type": "int", "lo", "hi"}, {"type": "cat", "n"} (an index 0..n-1) and
{"type": "bit"}. Variation: simulated binary crossover (distribution index eta_c, each gene of a crossed pair with
probability 1/2) and polynomial mutation (eta_m, probability p_m per gene) for real and integer genes, integers rounded
after each operator; uniform crossover and random reset for categorical genes; uniform crossover and bit flip for bits.
Selection: binary tournament on (rank, crowding); survival by constrained non-dominated sorting (a smaller violation
wins; objectives are compared only between designs of violation 0) and crowding distance. The caller supplies the
evaluation, the repair and the hypervolume of a population; the loop stops when the evaluation budget is spent or the
hypervolume improved by less than min_improvement over `window` generations."""
from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Individual:
    genome: list
    objectives: list = field(default_factory=list)  # minimised; math.inf when not computable
    violation: float = 0.0
    key: object = None
    rank: int = 0
    crowding: float = 0.0


def from_unit(genes: list[dict], u: list[float]) -> list:
    """A genome from a point of the unit cube (Sobol initialisation)."""
    out: list = []
    for g, x in zip(genes, u):
        t = g["type"]
        if t == "real":
            out.append(g["lo"] + x * (g["hi"] - g["lo"]))
        elif t == "int":
            out.append(min(g["hi"], g["lo"] + int(x * (g["hi"] - g["lo"] + 1))))
        elif t == "cat":
            out.append(min(g["n"] - 1, int(x * g["n"])))
        else:
            out.append(x >= 0.5)
    return out


def constrained_dominates(a: Individual, b: Individual) -> bool:
    if a.violation > 0 or b.violation > 0:
        return a.violation < b.violation
    better = False
    for x, y in zip(a.objectives, b.objectives):
        if x > y:
            return False
        if x < y:
            better = True
    return better


def sort_fronts(pop: list[Individual]) -> list[list[int]]:
    """Fast non-dominated sort under constrained domination; sets rank."""
    n = len(pop)
    dominated: list[list[int]] = [[] for _ in range(n)]
    count = [0] * n
    fronts: list[list[int]] = [[]]
    for i in range(n):
        for j in range(i + 1, n):
            if constrained_dominates(pop[i], pop[j]):
                dominated[i].append(j)
                count[j] += 1
            elif constrained_dominates(pop[j], pop[i]):
                dominated[j].append(i)
                count[i] += 1
    for i in range(n):
        if count[i] == 0:
            pop[i].rank = 0
            fronts[0].append(i)
    k = 0
    while fronts[k]:
        nxt = []
        for i in fronts[k]:
            for j in dominated[i]:
                count[j] -= 1
                if count[j] == 0:
                    pop[j].rank = k + 1
                    nxt.append(j)
        k += 1
        fronts.append(sorted(nxt))
    return fronts[:-1]


def crowding(pop: list[Individual], front: list[int]) -> None:
    for i in front:
        pop[i].crowding = 0.0
    if len(front) <= 2:
        for i in front:
            pop[i].crowding = math.inf
        return
    m = len(pop[front[0]].objectives)
    for k in range(m):
        order = sorted(front, key=lambda i: (pop[i].objectives[k], i))
        lo, hi = pop[order[0]].objectives[k], pop[order[-1]].objectives[k]
        pop[order[0]].crowding = pop[order[-1]].crowding = math.inf
        span = hi - lo
        if not math.isfinite(span) or span <= 0:
            continue
        for a, b, c in zip(order, order[1:], order[2:]):
            d = (pop[c].objectives[k] - pop[a].objectives[k]) / span
            pop[b].crowding += d if math.isfinite(d) else math.inf


def _sbx(x1: float, x2: float, lo: float, hi: float, eta: float, rng: random.Random) -> tuple[float, float]:
    """Bounded simulated binary crossover (Deb and Agrawal 1995; the form of Deb's NSGA-II code)."""
    if abs(x1 - x2) <= 1e-14 or hi <= lo:
        return x1, x2
    y1, y2 = min(x1, x2), max(x1, x2)
    u = rng.random()
    out = []
    for beta in (1.0 + 2.0 * (y1 - lo) / (y2 - y1), 1.0 + 2.0 * (hi - y2) / (y2 - y1)):
        alpha = 2.0 - beta ** -(eta + 1.0)
        bq = (u * alpha) ** (1.0 / (eta + 1.0)) if u <= 1.0 / alpha else (1.0 / (2.0 - u * alpha)) ** (1.0 / (eta + 1.0))
        out.append(bq)
    c1 = 0.5 * ((y1 + y2) - out[0] * (y2 - y1))
    c2 = 0.5 * ((y1 + y2) + out[1] * (y2 - y1))
    c1, c2 = min(max(c1, lo), hi), min(max(c2, lo), hi)
    return (c2, c1) if rng.random() < 0.5 else (c1, c2)


def _poly_mutation(x: float, lo: float, hi: float, eta: float, rng: random.Random) -> float:
    """Bounded polynomial mutation (Deb and Goyal 1996; the form of Deb's NSGA-II code)."""
    if hi <= lo:
        return x
    d1, d2 = (x - lo) / (hi - lo), (hi - x) / (hi - lo)
    u = rng.random()
    p = 1.0 / (eta + 1.0)
    if u < 0.5:
        val = 2.0 * u + (1.0 - 2.0 * u) * (1.0 - d1) ** (eta + 1.0)
        dq = val ** p - 1.0
    else:
        val = 2.0 * (1.0 - u) + 2.0 * (u - 0.5) * (1.0 - d2) ** (eta + 1.0)
        dq = 1.0 - val ** p
    return min(max(x + dq * (hi - lo), lo), hi)


def _round(g: dict, x: float) -> int:
    return int(min(max(math.floor(x + 0.5), g["lo"]), g["hi"]))


def vary(genes: list[dict], a: list, b: list, settings: dict, rng: random.Random) -> tuple[list, list]:
    """Two children of parents a and b."""
    c1, c2 = list(a), list(b)
    if rng.random() < settings["p_crossover"]:
        for k, g in enumerate(genes):
            if rng.random() >= 0.5:
                continue
            if g["type"] in ("real", "int"):
                y1, y2 = _sbx(float(c1[k]), float(c2[k]), g["lo"], g["hi"], settings["eta_c"], rng)
                c1[k], c2[k] = (_round(g, y1), _round(g, y2)) if g["type"] == "int" else (y1, y2)
            else:
                c1[k], c2[k] = c2[k], c1[k]
    pm = settings["p_mutation"]
    for child in (c1, c2):
        for k, g in enumerate(genes):
            if rng.random() >= pm:
                continue
            t = g["type"]
            if t == "real":
                child[k] = _poly_mutation(float(child[k]), g["lo"], g["hi"], settings["eta_m"], rng)
            elif t == "int":
                child[k] = _round(g, _poly_mutation(float(child[k]), g["lo"] - 0.5, g["hi"] + 0.5,
                                                    settings["eta_m"], rng))
            elif t == "cat":
                child[k] = rng.randrange(g["n"])
            else:
                child[k] = not child[k]
    return c1, c2


def _tournament(pop: list[Individual], rng: random.Random) -> Individual:
    a, b = pop[rng.randrange(len(pop))], pop[rng.randrange(len(pop))]
    if a.rank != b.rank:
        return a if a.rank < b.rank else b
    return a if a.crowding >= b.crowding else b


def survive(pop: list[Individual], size: int) -> list[Individual]:
    fronts = sort_fronts(pop)
    out: list[Individual] = []
    for front in fronts:
        crowding(pop, front)
        if len(out) + len(front) <= size:
            out += [pop[i] for i in front]
            continue
        rest = sorted(front, key=lambda i: (-pop[i].crowding, i))
        out += [pop[i] for i in rest[:size - len(out)]]
        break
    for front in sort_fronts(out):
        crowding(out, front)
    return out


def run(genes: list[dict], initial: list[list], evaluate: Callable[[list], Individual],
        repair: Callable[[list], list], hv: Callable[[list[Individual]], float], settings: dict,
        max_evaluations: int, on_generation: Callable[[int, list[Individual], float], None] | None = None) -> dict:
    """The NSGA-II loop. initial: genomes of the first population (already of the population size or smaller; the
    caller fills it). Returns {"population", "generations", "evaluations", "hypervolume": [(generation, value)],
    "stopped": reason}."""
    rng = random.Random(settings["seed"])
    size = settings["population"]
    evaluations = 0
    pop: list[Individual] = []
    for g in initial[:size]:
        if evaluations >= max_evaluations:
            break
        pop.append(evaluate(repair(g)))
        evaluations += 1
    pop = survive(pop, size)
    history = [(0, hv(pop))]
    if on_generation:
        on_generation(0, pop, history[-1][1])
    stopped = "generations"
    window, min_imp = settings.get("window"), settings.get("min_improvement")
    gen = 0
    for gen in range(1, settings["generations"] + 1):
        if evaluations >= max_evaluations:
            stopped = "budget"
            gen -= 1
            break
        children: list[Individual] = []
        while len(children) < size and evaluations < max_evaluations:
            p1, p2 = _tournament(pop, rng), _tournament(pop, rng)
            for c in vary(genes, p1.genome, p2.genome, settings, rng):
                if len(children) < size and evaluations < max_evaluations:
                    children.append(evaluate(repair(c)))
                    evaluations += 1
        pop = survive(pop + children, size)
        history.append((gen, hv(pop)))
        if on_generation:
            on_generation(gen, pop, history[-1][1])
        if window and len(history) > window:
            old = history[-1 - window][1]
            if history[-1][1] > 0 and history[-1][1] - old < (min_imp or 0.0) * old:
                stopped = "hypervolume"
                break
    return {"population": pop, "generations": gen, "evaluations": evaluations, "hypervolume": history,
            "stopped": stopped}
