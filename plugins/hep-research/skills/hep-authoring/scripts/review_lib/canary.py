"""Facts and design canaries with key diffs and two-sided witnesses (spec A5, P1 types only).

A canary replaces one full string that occurs exactly once in the document with a new string that occurs nowhere in
it. A candidate is used only with both witnesses: one that the original value is right, one that the new value is
wrong. Without enough candidates the slot gets fewer canaries (canary_shortfall); with none, no control (no_control).
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from review_lib.units import PLUGIN, path_tokens, plugin_index, rng

LINE_REF = re.compile(r"(?P<path>(?:<plugin root>/)?[A-Za-z_.][\w./-]*):(?P<a>\d+)(?:-(?P<b>\d+))?(?![\d-])")
NUM_TOKEN = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.]*\d)")
SECTION_REF = re.compile(r"§\s?(?P<n>\d+(?:\.\d+)*)|\b[Ss]ection (?P<m>\d+(?:\.\d+)*)")
ROW_REF = re.compile(r"\brow (?P<n>\d+)\b")


def key_diff(old: str, new: str) -> tuple[str, str]:
    """The changed span of two strings, widened to the whole numeric token (digits, '.', '-') or identifier."""
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    blocks = [b for b in sm.get_opcodes() if b[0] != "equal"]
    a0, a1, b0, b1 = blocks[0][1], blocks[-1][2], blocks[0][3], blocks[-1][4]

    def widen(s, x0, x1):
        probe = s[x0:x1] or s[max(0, x0 - 1):x0 + 1]
        numeric = bool(re.search(r"\d", probe)) or (x0 > 0 and s[x0 - 1].isdigit()) or (x1 < len(s) and s[x1:x1 + 1].isdigit())
        ok = (lambda c: c.isdigit() or c in ".-") if numeric else (lambda c: c.isalnum() or c in "_-")
        while x0 > 0 and ok(s[x0 - 1]):
            x0 -= 1
        while x1 < len(s) and ok(s[x1]):
            x1 += 1
        tok = s[x0:x1]
        return tok.strip(".-") if numeric else tok

    return widen(old, a0, a1), widen(new, b0, b1)


def unique_window(doc: str, text: str, a: int, b: int) -> tuple[int, int] | None:
    """Grow [a, b) inside text until text[a:b] occurs exactly once in doc; None if it never does."""
    while True:
        if doc.count(text[a:b]) == 1:
            return a, b
        if a == 0 and b == len(text):
            return None
        a, b = max(0, a - 1), min(len(text), b + 1)


def _lines(path: Path) -> list[str] | None:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def _resolve(tok: str, root: Path) -> Path | None:
    rel, _ = plugin_index(root)
    tok = re.sub(r"^<plugin root>/|^\./", "", tok)
    return root / tok if tok in rel and (root / tok).is_file() else None


def _shift(value: str, r, avoid) -> str | None:
    """Another number of the same shape (same number of digits after any decimal point), not in avoid."""
    for _ in range(40):
        if "." in value:
            whole, frac = value.split(".")
            v = int(whole + frac) + r.choice([-3, -2, -1, 1, 2, 3, 5, 7])
            if v <= 0:
                continue
            s = str(v).rjust(len(frac) + 1, "0")
            cand = f"{s[:-len(frac)]}.{s[-len(frac):]}"
        else:
            v = int(value) + r.choice([-3, -2, -1, 1, 2, 3, 4, 5, 7, 9])
            if v <= 0:
                continue
            cand = str(v)
        if cand != value and not avoid(cand):
            return cand
    return None


def _contains_number(line: str, value: str) -> bool:
    return re.search(r"(?<![0-9.])" + re.escape(value) + r"(?![0-9])", line) is not None


def facts_candidates(unit: dict, doc: str, r, root: Path = PLUGIN) -> list[dict]:
    """Line-range references to plugin files (the new range must not contain the cited lines) and numbers in a unit
    that names a plugin file (the original value is on a line of that file, the new value nowhere in it)."""
    out, text = [], unit["text"]
    for m in LINE_REF.finditer(text):
        path = _resolve(m.group("path"), root)
        if not path:
            continue
        lines = _lines(path)
        a = int(m.group("a"))
        b = int(m.group("b") or a)
        if not lines or not (1 <= a <= b <= len(lines)):
            continue
        cited = "\n".join(lines[a - 1:b])
        if not cited.strip():
            continue
        d = r.choice([3, 4, 5, 6, 7, 9, 11])
        na, nb = a + d, b + d
        new_tok = m.group(0)[:m.start("a") - m.start()] + (f"{na}-{nb}" if m.group("b") else f"{na}")
        new_block = "\n".join(lines[na - 1:nb]) if na <= len(lines) else ""
        rel = path.relative_to(root).as_posix()
        out.append({"span": (m.start(), m.end()), "new_token": new_tok, "type": "line-range",
                    "witness_right": {"path": rel, "lines": f"{a}-{b}", "content": cited[:200]},
                    "witness_wrong": None if cited in new_block else
                    {"path": rel, "lines": f"{na}-{nb}", "reason": "the new line range does not contain the cited lines"}})
    files = [p for p in (_resolve(t, root) for t in path_tokens(text)) if p]
    taken = [(m.start(), m.end()) for m in LINE_REF.finditer(text)] + [(m.start(), m.end()) for m in re.finditer(r"`[^`]*`", text)]
    for m in NUM_TOKEN.finditer(text):
        if any(s <= m.start() < e for s, e in taken):
            continue
        val = m.group(0)
        for path in files:
            lines = _lines(path) or []
            hit = next((i for i, ln in enumerate(lines, 1) if _contains_number(ln, val)), None)
            if hit is None:
                continue
            new = _shift(val, r, lambda c: any(_contains_number(ln, c) for ln in lines))
            if new is None:
                continue
            rel = path.relative_to(root).as_posix()
            out.append({"span": (m.start(), m.end()), "new_token": new, "type": "value",
                        "witness_right": {"path": rel, "line": hit, "value": val},
                        "witness_wrong": {"path": rel, "value": new, "reason": "the new value does not occur in the file"}})
            break
    return out


def _target_unit(units: list[dict], kind: str, n: str) -> dict | None:
    if kind == "section":
        hits = [u for u in units if u["kind"] == "heading"
                and re.match(r"^#+\s+(?:§\s?)?" + re.escape(n) + r"(?:\.|\s|$)", u["text"])]
    else:
        hits = [u for u in units if u["kind"] == "table-row" and re.match(r"^\|\s*" + re.escape(n) + r"\s*\|", u["text"])]
    return hits[0] if len(hits) == 1 else None


def design_candidates(unit: dict, units: list[dict], r) -> list[dict]:
    """References to a section or a numbered table row of the document: the cited one exists, and the new one exists
    with different content (the statement no longer matches what it cites)."""
    out, text = [], unit["text"]
    refs = [("section", m, m.group("n") or m.group("m"), m.start("n") if m.group("n") else m.start("m"))
            for m in SECTION_REF.finditer(text)]
    refs += [("row", m, m.group("n"), m.start("n")) for m in ROW_REF.finditer(text)]
    for kind, m, n, pos in refs:
        right = _target_unit(units, kind, n)
        if right is None or right["id"] == unit["id"]:
            continue
        options = []
        if kind == "section":
            parts = n.split(".")
            for d in (-1, 1, -2, 2):
                k = int(parts[-1]) + d
                if k >= 1:
                    options.append(".".join(parts[:-1] + [str(k)]))
        else:
            options = [str(int(n) + d) for d in (-1, 1, -2, 2, 3) if int(n) + d >= 1]
        r.shuffle(options)
        for new in options:
            wrong = _target_unit(units, kind, new)
            if wrong is None or wrong["text"] == right["text"]:
                continue
            out.append({"span": (pos, pos + len(n)), "new_token": new, "type": f"{kind}-ref",
                        "witness_right": {"cited": right["id"], "kind": kind, "ref": n},
                        "witness_wrong": {"cited": wrong["id"], "kind": kind, "ref": new,
                                          "reason": f"the {kind} {new} says something else"}})
            break
    return out


def two_sided(c: dict) -> bool:
    return bool(c.get("witness_right")) and bool(c.get("witness_wrong"))


def make_canaries(lens: str, units: list[dict], doc: str, eligible: list[str], exclude: set, n: int, seed_hex: str,
                  root: Path = PLUGIN) -> tuple[list[dict], list[dict]]:
    """Up to n canaries for a lens slot, in distinct units outside exclude; returns (canaries, rejected candidates)."""
    r = rng(seed_hex)
    by_id = {u["id"]: u for u in units}
    cands, rejected = [], []
    for uid in eligible:
        if uid in exclude:
            continue
        u = by_id[uid]
        found = facts_candidates(u, doc, r, root) if lens == "facts" else design_candidates(u, units, r) if lens == "design" else []
        for c in found:
            a, b = c["span"]
            win = unique_window(doc, u["text"], a, b)
            if win is None:
                rejected.append({"unit": uid, "reason": "the replaced string is not unique in the document"})
                continue
            wa, wb = win
            original = u["text"][wa:wb]
            mutated = u["text"][wa:a] + c["new_token"] + u["text"][b:wb]
            if mutated in doc or mutated == original:
                rejected.append({"unit": uid, "reason": "the new string already occurs in the document"})
                continue
            if not two_sided(c):
                rejected.append({"unit": uid, "reason": "one-sided witness", "witness_right": c["witness_right"]})
                continue
            old_key, new_key = key_diff(original, mutated)
            cands.append({"unit": uid, "type": c["type"], "original": original, "mutated": mutated, "old_key": old_key,
                          "new_key": new_key, "witness_right": c["witness_right"], "witness_wrong": c["witness_wrong"]})
    r.shuffle(cands)
    out, used = [], set()
    for c in cands:
        if len(out) < n and c["unit"] not in used:
            out.append(c)
            used.add(c["unit"])
    return sorted(out, key=lambda c: c["unit"]), rejected


def apply(doc: str, canaries: list[dict]) -> str:
    for c in canaries:
        assert doc.count(c["original"]) == 1
        doc = doc.replace(c["original"], c["mutated"], 1)
    return doc
