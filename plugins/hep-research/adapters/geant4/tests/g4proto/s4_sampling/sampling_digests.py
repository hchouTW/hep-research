#!/usr/bin/env python3
"""Section 22: are sampled values that go through transcendental functions bit-identical between E2 (macOS libm) and E5 (glibc)?

Draws fixed sequences with core/simulation/rng.py and prints a SHA-256 of each sampler's values, written with float.hex, so two machines compare by eye or by `compare`. Needs only Python.
Usage: sampling_digests.py [--draws N] [--values FOLDER]      prints JSON with a status key
       sampling_digests.py compare FIRST.json SECOND.json     exit 0 identical, 1 different
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PLUGIN))

from core.simulation import rng  # noqa: E402

SAMPLERS = {"uniform": lambda s: s.group()[0], "gaussian": lambda s: s.gaussian(), "exponential": lambda s: s.exponential(), "poisson_inverse": lambda s: s.poisson(12.5),
            "poisson_ptrs": lambda s: s.poisson(350.0), "binomial_inverse": lambda s: s.binomial(100, 0.2), "binomial_btpe": lambda s: s.binomial(5000, 0.3), "gamma": lambda s: s.gamma(25.0)}


def text_of(value) -> str:
    return value.hex() if isinstance(value, float) else str(value)


def digests(draws: int, folder: Path | None) -> dict:
    key = rng.volume_key(20261107, "sampling-check", 0)
    out = {}
    for name, draw in SAMPLERS.items():
        values = [text_of(draw(rng.SubStream(key, event, 1))) for event in range(draws)]
        joined = "\n".join(values)
        out[name] = hashlib.sha256(joined.encode("utf-8")).hexdigest()
        if folder:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{name}.txt").write_text(joined + "\n", encoding="utf-8")
    return out


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "compare":
        first, second = (json.loads(Path(path).read_text(encoding="utf-8")) for path in sys.argv[2:4])
        different = sorted(name for name in first["digests"] if first["digests"][name] != second["digests"].get(name))
        print(json.dumps({"status": "failed" if different else "ok", "different": different, "draws": [first["draws"], second["draws"]], "platforms": [first["platform"], second["platform"]]}))
        return 1 if different else 0
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--draws", type=int, default=200000)
    parser.add_argument("--values", type=Path)
    args = parser.parse_args()
    print(json.dumps({"status": "ok", "draws": args.draws, "platform": f"{platform.system()} {platform.machine()} Python {platform.python_version()}", "digests": digests(args.draws, args.values)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
