"""Blinding enforcement for binned outputs, ratios, figures, logs and caches (core module, steward hep-computing).

Policy (which regions are blinded) belongs to hep-analysis and the project config; this module only enforces it.
A region is {"variable": name, "low": x0, "high": x1}; a bin is blinded when it overlaps [low, high).

- mask_binned(edges, values, region)      -> values with blinded bins replaced by None, plus the mask
- mask_ratio(num, den, mask)              -> ratio with every blinded bin masked (a ratio reveals its numerator)
- seal(edges, values, region, references) -> the numbers an output must never contain: each blinded bin value,
                                             the blinded-region sum, the grand total, every cumulative sum (from
                                             either end) that includes a blinded bin, and ratios and differences
                                             to reference predictions in blinded bins
- scan_text / scan_file / scan_paths      -> find sealed numbers in text (logs, CSV, Markdown, JSON, SVG) and
                                             numeric caches (.npy/.npz), within a relative tolerance and at the
                                             printed precision
- check_figure(fig, region)               -> data points drawn inside the blinded range of the x axis

Passing these checks shows that the listed outputs do not contain the sealed numbers at the precisions tested.
It is not an authorization to unblind, and it cannot see values that were transformed in ways not sealed.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
TEXT_SUFFIXES = {".json", ".txt", ".log", ".csv", ".tsv", ".md", ".svg", ".yaml", ".yml", ".tex", ".html"}


def blinded_mask(edges, region: dict) -> list[bool]:
    lo, hi = float(region["low"]), float(region["high"])
    if not lo < hi:
        raise ValueError("blinded region needs low < high")
    return [e1 > lo and e0 < hi for e0, e1 in zip(edges[:-1], edges[1:])]


def mask_binned(edges, values, region: dict) -> dict:
    if len(values) != len(edges) - 1:
        raise ValueError("values need one entry per bin")
    m = blinded_mask(edges, region)
    return {"edges": list(edges), "values": [None if b else v for v, b in zip(values, m)], "blinded_bins": m,
            "blinding": {"region": dict(region), "note": "masked bins carry no value"}}


def mask_ratio(num, den, mask) -> list:
    return [None if (b or n is None or d is None or d == 0) else n / d for n, d, b in zip(num, den, mask)]


def seal(edges, values, region: dict, references=()) -> list[float]:
    """Numbers that would reveal blinded content: blinded bin values, their sum, the grand total, every cumulative
    sum from either end that includes a blinded bin (integrated yields above or below a threshold, CDF tables), and
    for each reference array (for example an MC prediction drawn next to data) the ratio and difference in each
    blinded bin and of the blinded-region sums. Sums over other bin ranges are not sealed."""
    m = blinded_mask(edges, region)
    if len(values) != len(m):
        raise ValueError("values need one entry per bin")
    if any(v is None for v in values):
        raise ValueError("seal needs the unmasked values (got None entries)")
    vals = [float(v) for v in values]
    blind = [v for v, b in zip(vals, m) if b]
    if not blind:
        return []
    out = blind + [sum(blind), sum(vals)]
    for order in (range(len(vals)), range(len(vals) - 1, -1, -1)):
        acc, seen = 0.0, False
        for i in order:
            acc += vals[i]
            seen = seen or m[i]
            if seen:
                out.append(acc)
    for ref in references:
        rb = [float(r) for r, b in zip(ref, m) if b]
        out += [v / r for v, r in zip(blind, rb) if r] + [v - r for v, r in zip(blind, rb)]
        if sum(rb):
            out.append(sum(blind) / sum(rb))
    return sorted(set(out))


def _close(x: float, target: float, rtol: float) -> bool:
    return math.isclose(x, target, rel_tol=rtol, abs_tol=0.0) if target != 0 else x == 0


def _printed_match(token: str, target: float) -> bool:
    """True when the token equals the target rounded at the token's own last printed digit (for example
    '1234.6' or '1.235e+03' for 1234.567). Tokens with fewer than 3 significant digits are not matched."""
    mant, _, exp = token.lower().partition("e")
    exp = int(exp) if exp else 0
    decimals = len(mant.split(".")[1]) if "." in mant else 0
    digits = mant.lstrip("+-").replace(".", "").lstrip("0")
    if len(digits) < 3:
        return False
    step = 10.0 ** (exp - decimals)
    return abs(float(token) - target) <= 0.5 * step * (1 + 1e-9)


GROUPED = re.compile(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d*)?(?:[eE][-+]?\d+)?")  # thousands separators: 1,234.5


def scan_text(text: str, sealed, rtol: float = 1e-9) -> list[dict]:
    hits = []
    tokens = [(mt.start(), mt.group(0)) for mt in NUMBER.finditer(text)]
    tokens += [(mt.start(), mt.group(0).replace(",", "")) for mt in GROUPED.finditer(text)]
    for start, tok in tokens:
        x = float(tok)
        for t in sealed:
            if _close(x, t, rtol) or _printed_match(tok, t):
                line = text.count("\n", 0, start) + 1
                hits.append({"line": line, "token": tok, "sealed_value": t})
                break
    return hits


def _scan_array(arr, sealed, rtol) -> list[dict]:
    import numpy as np
    a = np.asarray(arr)
    if a.dtype.kind not in "fiu":
        return []
    flat = a.ravel().astype(float)
    hits = []
    for t in sealed:
        idx = np.nonzero(np.isclose(flat, t, rtol=rtol, atol=0.0))[0]
        hits += [{"index": int(i), "sealed_value": t} for i in idx[:5]]
    return hits


def scan_file(path: Path, sealed, rtol: float = 1e-9) -> list[dict]:
    path = Path(path)
    suf = path.suffix.lower()
    if suf in (".npy", ".npz"):
        import numpy as np
        hits = []
        with np.load(path, allow_pickle=False) as data:
            arrays = {k: data[k] for k in data.files} if suf == ".npz" else {"": data}
            for k, arr in arrays.items():
                hits += [dict(h, array=k) for h in _scan_array(arr, sealed, rtol)]
        return hits
    if suf in TEXT_SUFFIXES or suf == "":
        return scan_text(path.read_text(encoding="utf-8", errors="replace"), sealed, rtol)
    return [{"unscanned": True, "reason": f"binary format '{suf}' is not scanned; produce it from masked data and check it with check_figure or a dedicated reader"}]


def scan_paths(paths, sealed, rtol: float = 1e-9) -> dict:
    report = {"leaks": [], "unscanned": [], "scanned": []}
    for p in paths:
        p = Path(p)
        files = sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p]
        for f in files:
            res = scan_file(f, sealed, rtol)
            if res and res[0].get("unscanned"):
                report["unscanned"].append({"file": str(f), "reason": res[0]["reason"]})
                continue
            report["scanned"].append(str(f))
            report["leaks"] += [dict(h, file=str(f)) for h in res]
    report["ok"] = not report["leaks"]
    return report


def check_figure(fig, region: dict) -> list[dict]:
    """Points drawn inside the blinded x range (lines, markers, error bars, bars, filled steps)."""
    import numpy as np
    lo, hi = float(region["low"]), float(region["high"])
    found = []
    for ax_i, ax in enumerate(fig.axes):
        for line in ax.get_lines():
            x, y = np.asarray(line.get_xdata(), float), np.asarray(line.get_ydata(), float)
            inside = (x >= lo) & (x < hi) & np.isfinite(y)
            if inside.any():
                found.append({"axes": ax_i, "artist": "line", "label": line.get_label(), "points": int(inside.sum())})
        for patch in ax.patches:
            kind = type(patch).__name__
            if kind == "StepPatch":
                data = patch.get_data()
                edges, vals = np.asarray(data.edges, float), np.asarray(data.values, float)
                sel = (edges[1:] > lo) & (edges[:-1] < hi) & np.isfinite(vals)
                if sel.any():
                    found.append({"axes": ax_i, "artist": "steps", "label": patch.get_label(), "points": int(sel.sum())})
            elif kind == "Rectangle" and patch.get_height() not in (0, None) and np.isfinite(patch.get_height()):
                x0, w = patch.get_x(), patch.get_width()
                if x0 + w > lo and x0 < hi:
                    found.append({"axes": ax_i, "artist": "bar", "label": patch.get_label(), "points": 1})
        for coll in ax.collections:
            offs = np.asarray(coll.get_offsets(), float)
            if offs.ndim == 2 and len(offs):
                inside = (offs[:, 0] >= lo) & (offs[:, 0] < hi) & np.isfinite(offs[:, 1])
                if inside.any():
                    found.append({"axes": ax_i, "artist": type(coll).__name__, "label": coll.get_label(), "points": int(inside.sum())})
            for seg in getattr(coll, "get_segments", lambda: [])():
                seg = np.asarray(seg, float)
                if len(seg) and ((seg[:, 0] >= lo) & (seg[:, 0] < hi) & np.isfinite(seg[:, 1])).any():
                    found.append({"axes": ax_i, "artist": "segment", "label": coll.get_label(), "points": 1})
                    break
    return found


def load_project_blinding(config_path) -> dict:
    """The `blinding` block of a project config (hep-research.project.json): blinded IDs, allowed outputs, regions."""
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return cfg.get("blinding") or {"blinded": [], "allowed_outputs": []}
