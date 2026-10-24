"""Closure-test reference values for task C (geant4-program.md §C Appendix A).

Curvature variance factor A (sigma_k^2 = A sigma^2 / L^4) of a least-squares parabola y = a + b x + k x^2 / 2
through N equal-weight planes at positions x in [0, L] (L = 1), measurement term only. Exact rational arithmetic.
Prints the equal-spacing value, clustered configurations (coincident planes), the asymptotic large-N limit, and the
best placement found by exhaustive enumeration on a 1/G grid (planes distinct, so minimum spacing 1/G; first at 0
and last at 1). A local search without the grid but with minimum spacing 1/32 converges to the same 47.66.
Standard library only. Design aid, not plugin code.
"""
from fractions import Fraction as Fr
from itertools import combinations
from math import sqrt


def curvature_factor(xs):
    s = [sum(Fr(x) ** p for x in xs) for p in range(5)]
    m = [[s[0], s[1], s[2] / 2], [s[1], s[2], s[3] / 2], [s[2] / 2, s[3] / 2, s[4] / 4]]
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    return (m[0][0] * m[1][1] - m[0][1] * m[1][0]) / det  # [M^-1]_kk


def main(n=6):
    eq = curvature_factor([Fr(i, n - 1) for i in range(n)])
    print(f"equal spacing: A = {float(eq):.2f}")
    def show(label, a):
        print(f"{label}: A = {float(a):.2f}, MDR ratio {sqrt(float(eq / a)):.3f}")

    show("clusters 2/2/2 at 0, 1/2, 1 (coincident)", curvature_factor([0, 0, Fr(1, 2), Fr(1, 2), 1, 1]))
    show("clusters 2/3/1 at 0, 1/2, 1 (coincident)", curvature_factor([0, 0, Fr(1, 2), Fr(1, 2), Fr(1, 2), 1]))
    a, m = min((curvature_factor([0, 0] + [Fr(i, 1000)] * 3 + [1]), Fr(i, 1000))
               for i in range(1, 1000))
    show(f"clusters 2/3/1 at 0, {float(m):.3f}, 1 (best middle position, 1/1000 scan)", a)
    print(f"asymptotic large-N limit (N/4, N/2, N/4 at 0, 1/2, 1): A = 256/N = {256 / n:.2f}, "
          f"MDR ratio {sqrt(float(eq) * n / 256):.3f} (not reachable with N = {n} integer clusters)")
    for g in (16, 32):
        grid = [Fr(i, g) for i in range(g + 1)]
        best = min((c for c in combinations(grid, n) if c[0] == 0 and c[-1] == 1), key=curvature_factor)
        a = curvature_factor(best)
        print(f"best on 1/{g} grid (minimum spacing 1/{g}): A = {float(a):.2f} at {[str(x) for x in best]}, "
              f"MDR ratio {sqrt(float(eq / a)):.3f}")


if __name__ == "__main__":
    main()
