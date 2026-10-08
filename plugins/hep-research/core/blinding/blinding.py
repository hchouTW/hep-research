"""Blinding helpers for binned outputs, ratios, figures, logs and caches (core module, steward hep-computing).

Advisory when the agent runs them, a safety net when a custodian runs them; never enforcement. Enforcement is input
blinding (the agent reads only released blinded derivatives) plus OS access control outside the agent. Policy (which
regions are blinded) belongs to the collaboration, recorded through hep-analysis and the project config.
A region is {"variable": name, "low": x0, "high": x1}; a bin is blinded when it overlaps [low, high).

- mask_binned(edges, values, region)      -> values with blinded bins replaced by None, plus the mask
- mask_ratio(num, den, mask)              -> ratio with every blinded bin masked (a ratio reveals its numerator)
- seal(edges, values, region, references) -> the numbers an output must never contain (SEALED_KINDS: blinded bin
                                             values, sums, total, cumulative sums, square roots, fractions of the
                                             total, and ratios, differences and (N-B)/sqrt(B) to references);
                                             NOT_SEALED lists what stays unsealed. Invalid edges (not finite and
                                             strictly increasing) raise ValueError, here and in mask_binned
- scan_text / scan_file / scan_paths      -> find sealed numbers in text (logs, CSV, Markdown, JSON, SVG) and
                                             numeric caches (.npy/.npz), within a relative tolerance and at the
                                             printed precision. A sealed value with fewer than 3 significant digits
                                             (a low count such as 0 or 3) matches only a standalone number, not
                                             part of a name, version or date, and its hits are marked "weak".
                                             Text is decoded from its byte-order mark, a UTF-16 byte pattern, UTF-8,
                                             or Latin-1 for other 8-bit text; a file that cannot be decoded, an array
                                             that is not real numeric, and a symlinked directory are unscanned
                                             (incomplete), never a pass. Signs, the Unicode minus and percentages
                                             are handled; OUT_OF_SCOPE_RENDERINGS are not
- agent_view(report)                      -> the fixed status an agent may see (no values, tokens, files or counts)
- check_figure(fig, region, sealed=None)  -> artists drawn inside the blinded range of the x axis (lines,
                                             markers, error bars, bars, steps, histogram outlines, filled areas,
                                             contour fills, 2D histograms and images), and, given the sealed
                                             numbers, any figure text or line/marker y value equal to one;
                                             check_figure_report adds the list of what was not checked

Scan status: "pass" (every output was read and none contains a sealed number), "fail" (a sealed number was found)
or "incomplete" (some output could not be read: a binary format, or nothing was scanned). Only "pass" sets ok.
Strict publication mode (strict=True) also fails an incomplete scan, requires a written reason for every exemption,
and, given the list of outputs to publish, requires a scan record or a named exemption for each of them. An
exemption never hides a file the scanner can read: such files are scanned anyway.

Passing these checks shows that the listed outputs do not contain the sealed numbers at the precisions tested.
It is not an authorization to unblind, and it cannot see values that were transformed in ways not sealed
(rescaled, shifted, smoothed, fitted or otherwise derived numbers): that limitation stays whatever the status.
check_figure looks at the x position of what is drawn on data axes and, given sealed numbers, at every text and at
line and marker y values; FIGURE_LIMITS lists what it does not see. With real data, sealing and scanning are custodian
services (or done by a person outside the agent session); an agent uses them only with synthetic sentinels.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Any

NUMBER = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")
TEXT_SUFFIXES = {".json", ".txt", ".log", ".csv", ".tsv", ".md", ".svg", ".yaml", ".yml", ".tex", ".html",
                 ".out", ".err", ".sh", ".sbatch", ".sub"}  # the last five: batch job logs and job descriptions


def validate_edges(edges) -> list[float]:
    """Bin edges as floats; ValueError unless there are at least two, all finite and strictly increasing. Descending,
    unsorted or NaN edges would otherwise mask and seal nothing (the blinding step must fail closed)."""
    try:
        e = [float(x) for x in edges]
    except (TypeError, ValueError):
        raise ValueError("bin edges must be numbers") from None
    if len(e) < 2:
        raise ValueError("a histogram needs at least two bin edges")
    if not all(math.isfinite(x) for x in e):
        raise ValueError("bin edges must be finite (no NaN or infinity)")
    if any(b <= a for a, b in zip(e, e[1:])):
        raise ValueError("bin edges must be strictly increasing")
    return e


def blinded_mask(edges, region: dict) -> list[bool]:
    lo, hi = float(region["low"]), float(region["high"])
    if not lo < hi:
        raise ValueError("blinded region needs low < high")
    edges = validate_edges(edges)
    return [e1 > lo and e0 < hi for e0, e1 in zip(edges[:-1], edges[1:])]


def mask_binned(edges, values, region: dict) -> dict:
    if len(values) != len(edges) - 1:
        raise ValueError("values need one entry per bin")
    m = blinded_mask(edges, region)
    return {"edges": list(edges), "values": [None if b else v for v, b in zip(values, m)], "blinded_bins": m,
            "blinding": {"region": dict(region), "note": "masked bins carry no value"}}


def mask_ratio(num, den, mask) -> list:
    return [None if (b or n is None or d is None or d == 0) else n / d for n, d, b in zip(num, den, mask)]


SEALED_KINDS = ("each blinded bin value and its square root", "the blinded-region sum and its square root",
                "the grand total", "every cumulative sum from either end that includes a blinded bin",
                "each blinded bin and the blinded-region sum as a fraction of the grand total",
                "per reference: data/reference, reference/data, data-reference and (data-reference)/sqrt(reference) "
                "in each blinded bin and for the blinded-region sums")
NOT_SEALED = ("sums over bin ranges that do not include a blinded bin", "neighbour- or sideband-subtracted counts",
              "fit results, smoothed, rescaled or shifted values", "quantities derived from a reference not passed to seal",
              "products or ratios of two blinded quantities other than those listed")


def seal(edges, values, region: dict, references=()) -> list[float]:
    """Numbers that would reveal blinded content (SEALED_KINDS): blinded bin values and their square roots, the
    blinded-region sum and its square root, the grand total, every cumulative sum from either end that includes a
    blinded bin (integrated yields above or below a threshold, CDF tables), the blinded bins and sum as fractions of
    the total, and for each reference array (for example an MC prediction drawn next to data) the ratio both ways,
    the difference and the significance-like (N-B)/sqrt(B) in each blinded bin and of the blinded-region sums.
    NOT_SEALED lists what stays unsealed. Raises ValueError on invalid edges (validate_edges)."""
    m = blinded_mask(edges, region)
    if len(values) != len(m):
        raise ValueError("values need one entry per bin")
    if any(v is None for v in values):
        raise ValueError("seal needs the unmasked values (got None entries)")
    vals = [float(v) for v in values]
    blind = [v for v, b in zip(vals, m) if b]
    if not blind:
        return []
    total = sum(vals)
    out = blind + [sum(blind), total]
    out += [math.sqrt(v) for v in blind + [sum(blind)] if v > 0]
    if total:
        out += [v / total for v in blind + [sum(blind)]]
    for order in (range(len(vals)), range(len(vals) - 1, -1, -1)):
        acc, seen = 0.0, False
        for i in order:
            acc += vals[i]
            seen = seen or m[i]
            if seen:
                out.append(acc)
    for ref in references:
        rb = [float(r) for r, b in zip(ref, m) if b]
        for v, r in list(zip(blind, rb)) + [(sum(blind), sum(rb))]:
            out.append(v - r)
            if r:
                out.append(v / r)
            if v:
                out.append(r / v)
            if r > 0:
                out.append((v - r) / math.sqrt(r))
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
    mant, _, exp_text = token.lower().partition("e")
    exp = int(exp_text) if exp_text else 0
    decimals = len(mant.split(".")[1]) if "." in mant else 0
    digits = mant.lstrip("+-").replace(".", "").lstrip("0")
    if len(digits) < 3:
        return False
    step = 10.0 ** (exp - decimals)
    return abs(float(token) - target) <= 0.5 * step * (1 + 1e-9)


GROUPED = re.compile(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d*)?(?:[eE][-+]?\d+)?")  # thousands separators: 1,234.5

# Renderings scan_text detects besides plain decimal and exponent forms: thousands commas (1,234.6), the Unicode minus
# (U+2212), a dropped or flipped sign (a deficit printed as a positive number) and percentages (37.12% for 0.3712).
# Renderings it does not detect: OUT_OF_SCOPE_RENDERINGS. A pass says nothing about them.
OUT_OF_SCOPE_RENDERINGS = ("fewer than 3 significant digits (1.2e3)", "unit-scaled values (1.234567 k, 1.2 M)",
                           "SI, European or Swiss digit grouping (1 234,5; 1.234,5; 1'234.5)",
                           "LaTeX or typeset exponents (1.23\\times10^{3})", "JSON \\u escapes and other encodings",
                           "hexadecimal or binary", "values split across tokens or lines")
MINUS_SIGNS = str.maketrans({"\u2212": "-", "\u2012": "-", "\u2013": "-", "\ufe63": "-", "\uff0d": "-"})


def _token_matches(tok: str, x: float, t: float, rtol: float, percent: bool) -> bool:
    """The token, with its sign ignored (a dropped or flipped sign), equals t at full or printed precision; a token
    followed by '%' is also compared as a percentage of t (37.12% for 0.3712)."""
    bare = tok.lstrip("+-")
    if _close(abs(x), abs(t), rtol) or _printed_match(bare, abs(t)):
        return True
    return percent and t != 0 and (_close(abs(x) / 100.0, abs(t), rtol) or _printed_match(bare, abs(t) * 100.0))


def scan_text(text: str, sealed, rtol: float = 1e-9) -> list[dict]:
    """Hits for sealed numbers in text (see OUT_OF_SCOPE_RENDERINGS for what is not detected). Each hit names the
    line, token and sealed value: a detailed report for a custodian or a human, not for the agent."""
    hits = []
    text = text.translate(MINUS_SIGNS)  # one character for one: offsets and line numbers are unchanged
    weak = {t: _significant_digits(t) < WEAK_DIGITS for t in sealed}
    tokens = [(mt.start(), mt.end(), mt.group(0)) for mt in NUMBER.finditer(text)]
    tokens += [(mt.start(), mt.end(), mt.group(0).replace(",", "")) for mt in GROUPED.finditer(text)]
    for start, end, tok in tokens:
        x = float(tok)
        alone = None
        percent = text[end:end + 1] == "%" or text[end:end + 2] == " %"
        for t in sealed:
            if not _token_matches(tok, x, t, rtol, percent):
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
    """Hits in a real numeric array; a single unscanned marker for complex, string, structured or object arrays,
    which can hold sealed values in a form this scan does not read."""
    import numpy as np
    a = np.asarray(arr)
    if a.dtype.kind == "b":
        return []
    if a.dtype.kind not in "fiu":
        return [{"unscanned": True, "reason": f"array dtype {a.dtype} is not real numeric and is not scanned"}]
    flat = a.ravel().astype(float)
    hits = []
    for t in sealed:
        near = np.isclose(flat, t, rtol=rtol, atol=0.0)
        if a.dtype.kind == "f":
            # a float32 or float16 copy of a sealed value is the sealed value rounded to the stored type, which can
            # differ from it by far more than rtol. Match that rounded copy exactly rather than widening rtol: a
            # dtype-wide tolerance flags unrelated neighbours (float16 spacing near 4731 is 4)
            near |= a.ravel() == np.asarray(t).astype(a.dtype)
        idx = np.nonzero(near)[0]
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
                    text = raw.decode(enc)
                except UnicodeDecodeError:
                    continue
                # numeric dumps (float64, float32, int32 written with tofile()) have enough zero bytes to decode
                # as UTF-16, but as control, surrogate or unassigned code points; real UTF-16 text has few
                odd_chars = sum(1 for ch in text if ch not in "\t\n\r\f"
                                and unicodedata.category(ch) in ("Cc", "Cs", "Co", "Cn"))
                if odd_chars > 0.05 * len(text):
                    return None, f"binary content ({odd_chars} of {len(text)} UTF-16 code units are control or " \
                                 "unassigned), not text"
                return text, enc
        return None, "contains NUL bytes and is not UTF-16 text"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    # any 8-bit text: digits, signs and separators are ASCII in all of them. Raw binary (an array written with
    # tofile(), a pickle, a ROOT file without its suffix) also decodes as Latin-1, but as control characters; it must
    # be unscanned, never a pass
    ctrl = sum(1 for b in raw if (b < 32 and b not in (9, 10, 12, 13)) or 127 <= b < 160)
    if ctrl > 0.05 * len(raw):
        return None, f"binary content ({ctrl} of {len(raw)} bytes are control codes), not text"
    return raw.decode("latin-1"), "latin-1"


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
        hits, unscanned = [], []
        for k, arr in arrays.items():
            res = _scan_array(arr, sealed, rtol)
            if res and res[0].get("unscanned"):
                unscanned.append(f"{k or 'array'}: {res[0]['reason']}")
            else:
                hits += [dict(h, array=k) for h in res]
        if unscanned and not hits:
            return [{"unscanned": True, "reason": "; ".join(unscanned)}]
        return hits
    if suf in TEXT_SUFFIXES or suf == "":
        text, enc = decode_text(path.read_bytes())
        if text is None:
            return [{"unscanned": True, "reason": f"text output that cannot be decoded: {enc}"}]
        return [dict(h, encoding=enc) if enc != "utf-8" else h for h in scan_text(text, sealed, rtol)]
    return [{"unscanned": True, "reason": f"binary format '{suf}' is not scanned; produce it from masked data and check it with check_figure or a dedicated reader"}]


LIMITATION = ("a pass means the sealed numbers were not found at the precisions and renderings tested; values "
              "transformed in ways that were not sealed, and the renderings in OUT_OF_SCOPE_RENDERINGS, cannot be detected")


def agent_view(report: dict) -> dict:
    """The only part of a scan report an agent may see: the status and fixed text. No sealed value, token, file,
    line or count of hits (an oracle answer that varied with them would reveal the secret, HC-08). Unscanned files are
    listed, because which files are unreadable does not depend on the sealed values."""
    return {"status": report["status"], "ok": report["ok"],
            "unscanned": [u["file"] for u in report.get("unscanned", [])],
            "limitation": LIMITATION, "out_of_scope_renderings": list(OUT_OF_SCOPE_RENDERINGS),
            "note": "advisory check, not enforcement and not authorization; per-hit details only in the report file"}


def _walk(root: Path) -> tuple[list[Path], list[Path]]:
    """Regular files under root (symlinks to files included) and the symlinked directories found, which are not
    followed. The same on every Python version (Path.rglob follows directory symlinks before 3.13, not after)."""
    import os
    files, links = [], []
    for parent, dirs, names in os.walk(root, followlinks=False):
        for d in dirs:
            if (Path(parent) / d).is_symlink():
                links.append(Path(parent) / d)
        files += [Path(parent) / n for n in names if (Path(parent) / n).is_file()]
    return sorted(files), sorted(links)


def scan_paths(paths, sealed, rtol: float = 1e-9, strict: bool = False, exemptions: dict | None = None,
               outputs=None) -> dict:
    """Scan files and directories. exemptions: {path: reason} for outputs the scanner cannot read (checked another
    way); outputs: in strict mode, every output that will be published (each needs a scan record or an exemption).

    The report is detailed (files, lines, tokens, sealed values): it is for a custodian or a human outside the agent
    session. Agent-visible output must be agent_view(report), a fixed status only."""
    ex = {str(Path(k).resolve()): str(v or "").strip() for k, v in (exemptions or {}).items()}
    report: dict[str, Any] = {"leaks": [], "unscanned": [], "scanned": [], "exempted": [], "reasons": [], "strict": strict,
                              "limitation": LIMITATION}
    for p in paths:
        p = Path(p)
        files, links = _walk(p) if p.is_dir() else ([p], [])
        for link in links:  # never followed, never silently skipped
            report["unscanned"].append({"file": str(link), "reason": "symbolic link to a directory is not followed"})
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


FIGURE_LIMITS = ("a blinded variable drawn on the y axis (only x positions are checked)",
                 "values encoded only in colors, marker sizes or line widths",
                 "lines and spans placed in axes coordinates (axhline, axhspan) are checked only for sealed y values",
                 "images saved without their figure, and figures drawn by other libraries")


def check_figure_report(fig, region: dict, sealed=None, rtol: float = 1e-9) -> dict:
    """{"found": check_figure findings, "unchecked": what this check cannot see in this figure (FIGURE_LIMITS plus
    artists it could not read, such as lines with categorical x data)}. Findings never include sealed values."""
    unchecked = list(FIGURE_LIMITS)
    found = _check_figure(fig, region, sealed, rtol, unchecked)
    return {"found": found, "unchecked": unchecked}


def check_figure(fig, region: dict, sealed=None, rtol: float = 1e-9) -> list[dict]:
    """Artists drawn inside the blinded x range (lines, markers, error bars, bars, filled steps, filled areas, contour
    fills, 2D histograms, images) and, when sealed numbers are given, any text in the figure (titles, axis labels,
    tick labels, legends, tables, colorbar labels, annotations) or line or marker y value that equals one. Findings
    name the artist, never the sealed value. check_figure_report also lists what was not checked."""
    return _check_figure(fig, region, sealed, rtol, [])


def _check_figure(fig, region, sealed, rtol, unchecked: list) -> list[dict]:
    import numpy as np
    from matplotlib.collections import PathCollection, PolyCollection, QuadMesh
    from matplotlib.contour import ContourSet
    from matplotlib.text import Text
    lo, hi = float(region["low"]), float(region["high"])
    found = []
    for ax_i, ax in enumerate(fig.axes):
        for line in ax.get_lines():
            try:
                x, y = np.asarray(line.get_xdata(), float), np.asarray(line.get_ydata(), float)
            except (TypeError, ValueError):
                unchecked.append(f"axes {ax_i}: line {line.get_label()!r} has non-numeric (categorical) data")
                continue
            if sealed and _scan_array(y[np.isfinite(y)], sealed, rtol):
                found.append({"axes": ax_i, "artist": "y-value", "label": line.get_label(), "points": 1})
            if not line.get_transform().contains_branch_seperately(ax.transData)[0]:
                continue  # x in axes coordinates (axhline): no data x position
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
            elif kind in ("Polygon", "PathPatch") and patch.get_transform().contains_branch(ax.transData):
                # hist(histtype='step' or 'stepfilled') draws one Polygon outline per dataset
                verts = patch.get_xy() if kind == "Polygon" else patch.get_path().vertices
                if _outline_inside(verts, lo, hi):
                    found.append({"axes": ax_i, "artist": "outline", "label": patch.get_label(), "points": 1})
        for coll in ax.collections:
            if isinstance(coll, ContourSet):  # contour, contourf: any drawn level inside the range
                xs = [np.asarray(pth.vertices, float)[:, 0] for pth in coll.get_paths()]
                if any(((x >= lo) & (x < hi)).any() for x in xs if x.size):
                    found.append({"axes": ax_i, "artist": "contour", "label": coll.get_label(), "points": 1})
                continue
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
            if sealed and offs.ndim == 2 and len(offs) and _scan_array(offs[:, 1][np.isfinite(offs[:, 1])], sealed, rtol):
                found.append({"axes": ax_i, "artist": "y-value", "label": coll.get_label(), "points": 1})
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
            arr: Any = np.ma.masked_invalid(np.ma.asarray(img.get_array(), float))
            if arr.ndim < 2 or not arr.size:
                continue
            x0, x1 = img.get_extent()[:2]
            cols = np.linspace(x0, x1, arr.shape[1] + 1)
            left, right = np.minimum(cols[:-1], cols[1:]), np.maximum(cols[:-1], cols[1:])
            drawn = ~np.ma.getmaskarray(arr).reshape(arr.shape[0], arr.shape[1], -1).all(axis=(0, 2))
            sel = (right > lo) & (left < hi) & drawn
            if sel.any():
                found.append({"axes": ax_i, "artist": "image", "label": img.get_label(), "points": int(sel.sum())})
    if sealed:  # every text in the figure: titles, axis and tick labels, legends, tables, colorbars, annotations
        try:
            fig.draw_without_rendering()  # tick labels get their text only when the figure is drawn
        except Exception:  # noqa: BLE001 - a figure that cannot be drawn still has its explicit texts checked
            unchecked.append("tick labels: the figure could not be drawn, so tick label text was not generated")
        axes_of: dict[int, int] = {}
        for ax_i, ax in enumerate(fig.axes):
            for t in ax.findobj(Text):
                axes_of.setdefault(id(t), ax_i)
        for ax_i, ax in enumerate(fig.axes):
            for table in ax.tables:  # table cell text is not among the figure's children
                for cell in table.get_celld().values():
                    axes_of.setdefault(id(cell.get_text()), ax_i)
        seen = set()
        cell_texts = [c.get_text() for ax in fig.axes for table in ax.tables for c in table.get_celld().values()]
        for t in fig.findobj(Text) + cell_texts:
            if id(t) in seen or not t.get_visible() or not t.get_text():
                continue
            seen.add(id(t))
            if scan_text(t.get_text(), sealed, rtol):
                found.append({"axes": axes_of.get(id(t)), "artist": "text", "points": 1})
    return found


def _outline_inside(verts, lo: float, hi: float) -> bool:
    """A polygon outline drawn inside the blinded x range at a non-zero height: a vertex strictly inside the range, or
    a segment spanning the whole range (a one-bin window). Vertices on the range edges belong to the neighbouring bins,
    and zero-height baselines carry no content."""
    import numpy as np
    v = np.asarray(verts, float)
    if v.ndim != 2 or len(v) == 0:
        return False
    v = v[np.isfinite(v[:, 0]) & np.isfinite(v[:, 1])]
    if len(v) == 0:
        return False
    x, y = v[:, 0], v[:, 1]
    if ((x > lo) & (x < hi) & (y != 0)).any():
        return True
    xa, xb, ya, yb = x[:-1], x[1:], y[:-1], y[1:]
    return bool(((np.minimum(xa, xb) <= lo) & (np.maximum(xa, xb) >= hi) & (ya != 0) & (yb != 0)).any())


def load_project_blinding(config_path) -> dict:
    """The `blinding` block of a project config (hep-research.project.json): blinded IDs, allowed outputs, regions."""
    cfg = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return cfg.get("blinding") or {"blinded": [], "allowed_outputs": []}
