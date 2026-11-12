"""Conjugate gradient on the reduced destriping system, restricted to the zero-sum subspace of the baselines, then binning.

With M = P^T P (hits per pixel) and Z = I - P M^-1 P^T, the baselines solve D a = F^T Z y, D = F^T Z F. D has the null vector 1 (a
connected scan: the common offset m + c, a - c), so the iteration starts at a = 0 and projects every residual and direction onto
1-perp: the zero-sum constraint, stated, not jitter. The stopping test uses the recomputed residual, not the recurrence; when the
recurrence collapses above the stopping value the iteration restarts from the recomputed residual, within the budget; a restart
counts one iteration for itself and one for the step that follows it."""
from __future__ import annotations

from dataclasses import dataclass

import numpy

from destripe_recipe import BUDGET_PER_BASELINE


class NotConverged(RuntimeError):
    def __init__(self, iterations: int, relative_residual: float):
        super().__init__(f"not converged: relative residual {relative_residual:.3e} after {iterations} iterations (the budget)")
        self.iterations, self.relative_residual = iterations, relative_residual


@dataclass(frozen=True)
class Solution:
    map: numpy.ndarray
    baselines: numpy.ndarray
    iterations: int
    relative_residual: float
    stopping: float
    max_iterations: int


def _bin(stream, samples: numpy.ndarray) -> numpy.ndarray:
    """M^-1 P^T v: the mean of the samples of each pixel."""
    return numpy.bincount(stream.pixel, weights=samples, minlength=stream.pixels) / numpy.bincount(stream.pixel, minlength=stream.pixels)


def _project_out_sky(stream, samples: numpy.ndarray) -> numpy.ndarray:
    """Z v = v - P M^-1 P^T v."""
    return samples - _bin(stream, samples)[stream.pixel]


def _sum_baselines(stream, samples: numpy.ndarray) -> numpy.ndarray:
    """F^T v."""
    return samples.reshape(stream.baselines, stream.length).sum(axis=1)


def reduced_operator(stream, baselines: numpy.ndarray) -> numpy.ndarray:
    """D a = F^T Z F a."""
    return _sum_baselines(stream, _project_out_sky(stream, numpy.repeat(baselines, stream.length)))


def _zero_sum(vector: numpy.ndarray) -> numpy.ndarray:
    return vector - vector.mean()


def solve(stream, stopping: float, max_iterations: int | None = None) -> Solution:
    budget = BUDGET_PER_BASELINE * stream.baselines if max_iterations is None else max_iterations
    right = _zero_sum(_sum_baselines(stream, _project_out_sky(stream, stream.value)))
    size = float(numpy.linalg.norm(right))
    a = numpy.zeros(stream.baselines)
    if size == 0.0:
        return Solution(_bin(stream, stream.value), a, 0, 0.0, stopping, budget)
    residual = right.copy()
    direction = residual.copy()
    relative = 1.0
    iterations = 0
    while relative > stopping:
        if iterations >= budget:
            raise NotConverged(iterations, relative)
        image = _zero_sum(reduced_operator(stream, direction))
        curvature = float(direction @ image)
        if not curvature > 0.0 or not float(residual @ residual) > 0.0:
            # the recurrence has collapsed (Krylov space exhausted, or rounding) while the recomputed residual is above the
            # stopping value: restart from the recomputed residual; the budget bounds the restarts
            residual = _zero_sum(right - reduced_operator(stream, a))
            direction = residual.copy()
            iterations += 1
            image = _zero_sum(reduced_operator(stream, direction))
            curvature = float(direction @ image)
            if not curvature > 0.0:
                raise NotConverged(iterations, relative)
        step = float(residual @ residual) / curvature
        a = _zero_sum(a + step * direction)
        updated = _zero_sum(residual - step * image)
        direction = _zero_sum(updated + (float(updated @ updated) / float(residual @ residual)) * direction)
        residual = updated
        iterations += 1
        true_residual = _zero_sum(right - reduced_operator(stream, a))
        relative = float(numpy.linalg.norm(true_residual)) / size
    sky = _bin(stream, stream.value - numpy.repeat(a, stream.length))
    return Solution(sky, a, iterations, relative, stopping, budget)
