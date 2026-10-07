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
                                             printed precision. A sealed value with fewer than 3 significant digits
                                             (a low count such as 0 or 3) matches only a standalone number, not
                                             part of a name, version or date, and its hits are marked "weak".
                                             Text is decoded from its byte-order mark, a UTF-16 byte pattern, UTF-8,
                                             or Latin-1 for other 8-bit text; a file that cannot be decoded is
                                             unscanned (incomplete), never a pass
- check_figure(fig, region, sealed=None)  -> artists drawn inside the blinded range of the x axis (lines,
                                             markers, error bars, bars, steps, filled areas such as fill_between,
                                             2D histograms and images), and, given the sealed numbers, text
                                             artists (ax.text, annotations, titles) that print one

Scan status: "pass" (every output was read and none contains a sealed number), "fail" (a sealed number was found)
or "incomplete" (some output could not be read: a binary format, or nothing was scanned). Only "pass" sets ok.
Strict publication mode (strict=True) also fails an incomplete scan, requires a written reason for every exemption,
and, given the list of outputs to publish, requires a scan record or a named exemption for each of them. An
exemption never hides a file the scanner can read: such files are scanned anyway.

Passing these checks shows that the listed outputs do not contain the sealed numbers at the precisions tested.
It is not an authorization to unblind, and it cannot see values that were transformed in ways not sealed
(rescaled, shifted, smoothed, fitted or otherwise derived numbers): that limitation stays whatever the status.
check_figure looks at the x position of what is drawn on data axes and at the text of text artists; it does not read
tick labels, legends, colorbars, images saved without their figure, or values encoded only in colors or marker
sizes outside the blinded x range.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
TEXT_SUFFIXES = {".json", ".txt", ".log", ".csv", ".tsv", ".md", ".svg", ".yaml", ".yml", ".tex", ".html",
                 ".out", ".err", ".sh", ".sbatch", ".sub"}  # the last five: batch job logs and job descriptions


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


WEAK_DIGITS = 3  # a sealed value with fewer significant digits than this matches only standalone numbers


def _significant_digits(value: float) -> int:
    """Significant digits of the shortest decimal form, without leading or trailing zeros (0 -> 0, 3 -> 1, 120 -> 2)."""
    mant = f"{abs(value):.15g}".lower().split("e")[0].replace(".", "")
    return len(mant.strip("0"))


def _standalone(text: str, start: int, end: int) -> bool:
    """True when text[start:end] is a number on its own: not part of a name (run_3, v3, 3rd), a version (1.3.0),
    a date or range (2023-10-03, 1-3) or a path."""
    before = text[start - 1] if start > 0 else " "
    after = text[end] if end < len(text) else " "
    if before.isalnum() or before in "_./\\:":
        return False
    if before == "-" and start > 1 and text[start - 2].isalnum():
        return False
    if text[start] in "+-" and start > 0 and text[start - 1].isalnum():
        return False
    if after.isalnum() or after in "_/\\:":
        return False
    if after in ".-" and end + 1 < len(text) and text[end + 1].isdigit():
        return False
    return True


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
    weak = {t: _significant_digits(t) < WEAK_DIGITS for t in sealed}
    tokens = [(mt.start(), mt.end(), mt.group(0)) for mt in NUMBER.finditer(text)]
    tokens += [(mt.start(), mt.end(), mt.group(0).replace(",", "")) for mt in GROUPED.finditer(text)]
    for start, end, tok in tokens:
        x = float(tok)
        alone = None
        for t in sealed:
            if not (_close(x, t, rtol) or _printed_match(tok, t)):
                continue
            if weak[t]:
                alone = _standalone(text, start, end) if alone is None else alone
                if not alone:
                    continue
            line = text.count("\n", 0, start) + 1
            hit = {"line": line, "token": tok, "sealed_value": t}
            if weak[t]:
                hit["weak"] = True  # a short sealed value: a standalone match, still possibly unrelated
            hits.append(hit)
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


def decode_text(raw: bytes) -> tuple[str | None, str]:
    """(text, encoding) from a byte-order mark, a UTF-16 byte pattern, strict UTF-8, or Latin-1 for other 8-bit
    text; (None, reason) when the bytes are not text (NUL bytes that are not UTF-16)."""
    for bom, enc in ((b"\xef\xbb\xbf", "utf-8-sig"), (b"\xff\xfe\x00\x00", "utf-32"), (b"\x00\x00\xfe\xff", "utf-32"),
                     (b"\xff\xfe", "utf-16"), (b"\xfe\xff", "utf-16")):
        if raw.startswith(bom):
            try:
                return raw.decode(enc), enc
            except UnicodeDecodeError:
                return None, f"starts with a {enc} byte-order mark but does not decode as {enc}"
    if b"\x00" in raw:
        even, odd = raw[0::2], raw[1::2]
        for enc, zeros in (("utf-16-le", odd), ("utf-16-be", even)):
            if len(raw) % 2 == 0 and zeros and zeros.count(0) >= 0.3 * len(zeros):
                try:
                    return raw.decode(enc), enc
                except UnicodeDecodeError:
                    pass
        return None, "contains NUL bytes and is not UTF-16 text"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("latin-1"), "latin-1"  # any 8-bit text: digits, signs and separators are ASCII in all of them


def scan_file(path: Path, sealed, rtol: float = 1e-9) -> list[dict]:
    path = Path(path)
    suf = path.suffix.lower()
    if suf in (".npy", ".npz"):
        import numpy as np
        if suf == ".npy":  # np.load returns a plain ndarray (no file handle stays open)
            arrays = {"": np.load(path, allow_pickle=False)}
        else:  # NpzFile keeps the archive open until closed
            with np.load(path, allow_pickle=False) as data:
                arrays = {k: data[k] for k in data.files}
        hits = []
        for k, arr in arrays.items():
            hits += [dict(h, array=k) for h in _scan_array(arr, sealed, rtol)]
        return hits
    if suf in TEXT_SUFFIXES or suf == "":
        text, enc = decode_text(path.read_bytes())
        if text is None:
            return [{"unscanned": True, "reason": f"text output that cannot be decoded: {enc}"}]
        return [dict(h, encoding=enc) if enc != "utf-8" else h for h in scan_text(text, sealed, rtol)]
    return [{"unscanned": True, "reason": f"binary format '{suf}' is not scanned; produce it from masked data and check it with check_figure or a dedicated reader"}]


LIMITATION = ("a pass means the sealed numbers were not found at the precisions tested; values transformed in ways "
              "that were not sealed cannot be detected")


def scan_paths(paths, sealed, rtol: float = 1e-9, strict: bool = False, exemptions: dict | None = None,
               outputs=None) -> dict:
    """Scan files and directories. exemptions: {path: reason} for outputs the scanner cannot read (checked another
    way); outputs: in strict mode, every output that will be published (each needs a scan record or an exemption)."""
    ex = {str(Path(k).resolve()): str(v or "").strip() for k, v in (exemptions or {}).items()}
    report = {"leaks": [], "unscanned": [], "scanned": [], "exempted": [], "reasons": [], "strict": strict,
              "limitation": LIMITATION}
    for p in paths:
        p = Path(p)
        files = sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p]
        for f in files:
            res = scan_file(f, sealed, rtol)
            if res and res[0].get("unscanned"):
                why = ex.get(str(f.resolve()))
                if why:
                    report["exempted"].append({"file": str(f), "reason": why})
                else:
                    report["unscanned"].append({"file": str(f), "reason": res[0]["reason"]})
                    if strict and str(f.resolve()) in ex:
                        report["reasons"].append(f"exemption for {f} has no reason")
                continue
            report["scanned"].append(str(f))
            report["leaks"] += [dict(h, file=str(f)) for h in res]
    if strict and outputs is not None:
        recorded = {str(Path(x).resolve()) for x in report["scanned"]} | {str(Path(e["file"]).resolve()) for e in report["exempted"]}
        report["outputs_without_record"] = [str(o) for o in outputs if str(Path(o).resolve()) not in recorded]
    incomplete = []
    if report["unscanned"]:
        incomplete.append(f"{len(report['unscanned'])} output(s) not scanned: " + ", ".join(u["file"] for u in report["unscanned"][:5]))
    if not report["scanned"]:
        incomplete.append("no output was scanned")
    if report.get("outputs_without_record"):
        incomplete.append("outputs with no scan record or exemption: " + ", ".join(report["outputs_without_record"][:5]))
    if report["leaks"]:
        report["status"] = "fail"
        report["reasons"].insert(0, f"{len(report['leaks'])} sealed value(s) found")
    elif incomplete:
        report["status"] = "fail" if strict else "incomplete"
        report["reasons"] += [f"incomplete: {x}" for x in incomplete]
    else:
        report["status"] = "fail" if report["reasons"] else "pass"
    report["ok"] = report["status"] == "pass"
    return report


def check_figure(fig, region: dict, sealed=None, rtol: float = 1e-9) -> list[dict]:
    """Artists drawn inside the blinded x range (lines, markers, error bars, bars, filled steps, filled areas, 2D
    histograms, images) and, when sealed numbers are given, text artists that print one."""
    import numpy as np
    from matplotlib.collections import PathCollection, PolyCollection, QuadMesh
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
            if isinstance(coll, QuadMesh):  # hist2d, pcolormesh: cells overlapping the range with a drawn value
                xy = np.asarray(coll.get_coordinates(), float)
                vals = np.ma.masked_invalid(np.ma.asarray(coll.get_array(), float)).reshape(xy.shape[0] - 1, xy.shape[1] - 1)
                left, right = np.minimum(xy[:-1, :-1, 0], xy[:-1, 1:, 0]), np.maximum(xy[:-1, :-1, 0], xy[:-1, 1:, 0])
                sel = (right > lo) & (left < hi) & ~np.ma.getmaskarray(vals)
                if sel.any():
                    found.append({"axes": ax_i, "artist": "mesh", "label": coll.get_label(), "points": int(sel.sum())})
                continue
            if isinstance(coll, PolyCollection) and not isinstance(coll, PathCollection) \
                    and coll.get_transform().contains_branch(ax.transData):  # fill_between, stackplot, violin bodies
                n_in = 0
                for path in coll.get_paths():
                    v = np.asarray(path.vertices, float)
                    if len(v) and ((v[:, 0] >= lo) & (v[:, 0] < hi) & np.isfinite(v[:, 1])).any():
                        n_in += 1
                if n_in:
                    found.append({"axes": ax_i, "artist": "area", "label": coll.get_label(), "points": n_in})
                continue
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
        for img in ax.images:  # imshow: image columns overlapping the range with a drawn value
            arr = np.ma.masked_invalid(np.ma.asarray(img.get_array(), float))
            if arr.ndim < 2 or not arr.size:
                continue
            x0, x1 = img.get_extent()[:2]
            cols = np.linspace(x0, x1, arr.shape[1] + 1)
            left, right = np.minimum(cols[:-1], cols[1:]), np.maximum(cols[:-1], cols[1:])
            drawn = ~np.ma.getmaskarray(arr).reshape(arr.shape[0], arr.shape[1], -1).all(axis=(0, 2))
            sel = (right > lo) & (left < hi) & drawn
            if sel.any():
                found.append({"axes": ax_i, "artist": "image", "label": img.get_label(), "points": int(sel.sum())})
        if sealed:
            texts = list(ax.texts) + [t for t in (getattr(ax, a, None) for a in ("title", "_left_title", "_right_title")) if t]
            for t in texts:
                hits = scan_text(t.get_text(), sealed, rtol) if t.get_text() else []
                if hits:
                    found.append({"axes": ax_i, "artist": "text", "label": t.get_text()[:60], "points": len(hits),
                                  "sealed_values": sorted({h["sealed_value"] for h in hits})})
    if sealed:
        for t in fig.texts + ([fig._suptitle] if getattr(fig, "_suptitle", None) else []):
            hits = scan_text(t.get_text(), sealed, rtol) if t.get_text() else []
            if hits:
                found.append({"axes": None, "artist": "text", "label": t.get_text()[:60], "points": len(hits),
                              "sealed_values": sorted({h["sealed_value"] for h in hits})})
    return found


def load_project_blinding(config_path) -> dict:
    """The `blinding` block of a project config (hep-research.project.json): blinded IDs, allowed outputs, regions."""
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return cfg.get("blinding") or {"blinded": [], "allowed_outputs": []}
