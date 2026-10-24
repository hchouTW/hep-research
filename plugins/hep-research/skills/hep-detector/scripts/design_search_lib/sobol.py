"""Sobol low-discrepancy points (Bratley-Fox with Gray-code order) from the Joe-Kuo direction numbers shipped in
skills/hep-detector/assets/design-search/sobol_joe_kuo.txt. Unscrambled: point k (k >= 0) is the k-th point of the
sequence, equal to scipy.stats.qmc.Sobol(scramble=False) at the same index; callers skip point 0 (all zeros)."""
from __future__ import annotations

from pathlib import Path

BITS = 32
TABLE = Path(__file__).resolve().parents[2] / "assets" / "design-search" / "sobol_joe_kuo.txt"


def load_table(path: Path = TABLE) -> list[tuple[int, int, list[int]]]:
    """(s, a, m) per dimension 2.. in file order."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts or line.startswith("#") or not parts[0].isdigit():
            continue
        s, a = int(parts[1]), int(parts[2])
        rows.append((s, a, [int(x) for x in parts[3:3 + s]]))
    return rows


class Sobol:
    """Sobol points in [0, 1)^dim."""

    def __init__(self, dim: int, path: Path = TABLE):
        table = load_table(path)
        if dim < 1 or dim > len(table) + 1:
            raise ValueError(f"Sobol dimension {dim} outside 1..{len(table) + 1} (the shipped direction numbers)")
        self.dim = dim
        self.v: list[list[int]] = [[1 << (BITS - 1 - i) for i in range(BITS)]]
        for s, a, m in table[:dim - 1]:
            v = [0] * BITS
            for i in range(BITS):
                if i < s:
                    v[i] = m[i] << (BITS - 1 - i)
                else:
                    x = v[i - s] ^ (v[i - s] >> s)
                    for k in range(1, s):
                        if (a >> (s - 1 - k)) & 1:
                            x ^= v[i - k]
                    v[i] = x
            self.v.append(v)

    def points(self, start: int, count: int) -> list[list[float]]:
        """Points start .. start + count - 1 (Gray-code recursion from point 0)."""
        x = [0] * self.dim
        out = []
        scale = float(1 << BITS)
        for k in range(start + count):
            if k >= start:
                out.append([xi / scale for xi in x])
            c = (~k & (k + 1)).bit_length() - 1  # index of the lowest zero bit of k
            if c >= BITS:
                raise ValueError("Sobol index beyond 2^32")
            x = [xi ^ vj[c] for xi, vj in zip(x, self.v)]
        return out
