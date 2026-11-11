"""Per-number sourcing rules for the experiment:eic content modules (standard library only).

Every number on a checked line of a `facility/` or `detector/` module must equal a number token of the claim text of
a numeric claim cited on the same line that carries a `scope.number_kind` (frozen claims carry none, so they never
source a number). Lines that start with `derived:` follow the derived-line rule instead: a value computed by a named
script from cited numbers. The profile tests and the configuration checker both import this module.

Algorithm (one line at a time):
1. normalise: superscript runs become `^` plus ASCII (`10³³` -> `10^33`), then Unicode NFKC, then U+2212 -> `-`;
2. protect configuration labels (`18x275` -> `18   275`);
3. blank out ids, URLs/DOIs/arXiv ids, ISO dates, years, document references (Table 3.4, §3.2.1, Chapter 8.3, ...),
   unit exponents (`cm^-2`), exponents attached to a letter (`Q^2`), digits inside words that start with a letter
   (`B0`, `PbWO4`) and a leading list marker; each removal keeps the line length, so positions survive;
4. tokenise numbers, with `10^34`, `1e34` and `2.0 x 10^33` read as single numbers.
"""
import math
import re
import unicodedata
from pathlib import Path

PROFILE_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = PROFILE_ROOT.parents[2]

SUPERSCRIPT_ASCII = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8",
                     "⁹": "9", "⁺": "+", "⁻": "-"}
UNIT_PATTERN = (r"(?:GeV|MeV|TeV|keV|eV|tesla|T|mrad|rad|μm|um|nm|mm|cm|m|ns|ps|fb|pb|nb|kHz|MHz|Hz|s|%|degrees|deg)")
PERFORMANCE_WORDS = ("resolution", "separation", "efficiency", "rejection", "purity", "acceptance", "precision",
                     "accuracy", "timing precision", "noise", "misidentification")
NUMBER_KINDS = ("requirement", "design-target", "design-value", "proposal")
RELATIVE_TOLERANCE = 1e-9

LABEL_PATTERN = re.compile(r"(?<![\w.])(\d+)(\s*[x×]\s*)(\d+)(?![\w.^])")
REMOVALS = (
    re.compile(r"eic:[SC]\d\d"),
    re.compile(r"https?://\S+|\b10\.\d{4,9}/\S+|arXiv:\s*\d{4}\.\d{4,5}(?:v\d+)?|\bv\d+\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"(?<![\w.])(?:19|20)\d\d(?![\w.])(?!\s*" + UNIT_PATTERN + r"(?![A-Za-z]))"),
    re.compile(r"(?:\b(?:Tables?|Sections?|Fig\.|Figs\.|Figures?|Eq\.|Eqs\.|Tier|Chapters?|p\.|pp\.|page|pages|Version)"
               r"|§)\s*\d+(?:\.\d+)*(?:\s*[-–]\s*\d+(?:\.\d+)*)?", re.IGNORECASE),
    re.compile(r"(?<![A-Za-z])(?:cm|m|s|mm|nm|μm|um|Hz|fb|pb|nb|GeV|MeV|TeV|keV|eV)(\^?-\d+)"),
    re.compile(r"(?<=[A-Za-z])\^[-+]?\d+"),
    re.compile(r"\b(?![x×]10\^)[A-Za-z]+\d+[A-Za-z\d]*\b"),
    re.compile(r"^\s*\d+[.)](?=\s)"),
)
UNIT_EXPONENT_INDEX = 5
TOKEN_PATTERN = re.compile(r"(?<![\w.])(?:[-+](?=\d))?(?:\d+(?:\.\d+)?\s*[x×]\s*10\^[-+]?\d+|10\^[-+]?\d+"
                           r"|\d+(?:\.\d+)?[eE][-+]?\d+|\d+(?:\.\d+)?)")
CITATION_PATTERN = re.compile(r"eic:C\d\d")
DERIVED_PATTERN = re.compile(r"^\s*(?:[-*]\s+)?derived:")
DERIVED_SCRIPT = "skills/hep-theory/scripts/dis_kinematics.py"


def normalise(line):
    """Step 1: superscripts to `^` plus ASCII, then NFKC, then the Unicode minus to `-`."""
    line = re.sub("[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+", lambda match: "^" + "".join(SUPERSCRIPT_ASCII[c] for c in match.group()), line)
    return unicodedata.normalize("NFKC", line).replace("−", "-")


def _blank(match):
    return " " * len(match.group(0))


def cleaned(line):
    """The normalised line after steps 2-3; every removal is replaced by spaces of the same length."""
    text = normalise(line)
    text = LABEL_PATTERN.sub(lambda m: m.group(1) + " " * len(m.group(2)) + m.group(3), text)
    for index, pattern in enumerate(REMOVALS):
        if index == UNIT_EXPONENT_INDEX:  # blank only the exponent, keep the unit
            text = pattern.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)] + " " * len(m.group(1)), text)
        else:
            text = pattern.sub(_blank, text)
    return text


def to_float(token):
    """A number token as a float, without eval."""
    compact = token.replace(" ", "")
    scientific = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)[x×]10\^([-+]?\d+)", compact)
    if scientific:
        return float(scientific.group(1)) * 10.0 ** int(scientific.group(2))
    power = re.fullmatch(r"([-+]?)10\^([-+]?\d+)", compact)
    if power:
        return (-1.0 if power.group(1) == "-" else 1.0) * 10.0 ** int(power.group(2))
    return float(compact)


def spans(line):
    """(start, end, value) of every number token; positions refer to cleaned(line)."""
    return [(m.start(), m.end(), to_float(m.group(0))) for m in TOKEN_PATTERN.finditer(cleaned(line))]


def tokens(line):
    return [value for _, _, value in spans(line)]


def same_number(first, second):
    return math.isclose(first, second, rel_tol=RELATIVE_TOLERANCE, abs_tol=0.0) or first == second


def contains_number(text, value):
    return any(same_number(value, token) for token in tokens(text))


def is_derived(line):
    return bool(DERIVED_PATTERN.match(line))


def checked_lines(text):
    """(line number, line) of every line the per-number rule covers: not in `## General method`, not in fenced
    code, not a table separator row."""
    in_fence, in_general_method = False, False
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        heading = re.match(r"^(#{1,6})\s+(.*)", stripped)
        if heading:
            level = len(heading.group(1))
            if level <= 2:
                in_general_method = heading.group(2).strip().lower() == "general method"
            if in_general_method:
                continue
        elif in_general_method:
            continue
        if re.fullmatch(r"\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?", stripped):
            continue
        yield number, line


def general_method_lines(text):
    """(line number, line) of the lines inside the `## General method` section."""
    inside = False
    for number, line in enumerate(text.splitlines(), 1):
        heading = re.match(r"^(#{1,6})\s+(.*)", line.strip())
        if heading and len(heading.group(1)) <= 2:
            inside = heading.group(2).strip().lower() == "general method"
            continue
        if inside:
            yield number, line


def sourcing_claims(line, claims):
    """The cited claims on a line that may source a number: numeric and with a scope.number_kind."""
    cited = [claims[cid] for cid in CITATION_PATTERN.findall(line) if cid in claims]
    return [c for c in cited if c.get("numeric_quotation_allowed") and c.get("scope", {}).get("number_kind")]


def unsourced_numbers(line, claims):
    """Number tokens of a non-derived line that no cited numeric claim states."""
    allowed = [value for claim in sourcing_claims(line, claims) for value in tokens(claim["claim"])]
    return [value for value in tokens(line) if not any(same_number(value, known) for known in allowed)]


def proton_mass_gev():
    import sys
    if str(PLUGIN_ROOT) not in sys.path:
        sys.path.insert(0, str(PLUGIN_ROOT))
    import core.constants as constants  # noqa: E402  (plugin core, standard library only)
    return constants.constant("proton_mass_energy", unit="GeV").value


def parse_derived(line):
    """The parts of a derived line: value, unit, script path, flag values (as written)."""
    match = re.match(r"^\s*(?:[-*]\s+)?derived:\s*(\S+)\s+(\S+)\s+from\s+(.*?)\s+via\s+(\S+)\s*(.*)$", line)
    if not match:
        return None
    flags = dict(re.findall(r"--([A-Za-z][\w-]*)\s+(\S+)", match.group(5)))
    return {"value": match.group(1), "unit": match.group(2), "cited": CITATION_PATTERN.findall(match.group(3)),
            "script": match.group(4).strip("`"), "flags": flags}


def derived_line_problems(line, claims):
    """Problems of a derived line under section 7.5 of the task (format, cited inputs, M, script path)."""
    parts = parse_derived(line)
    if parts is None:
        return ["derived line does not follow 'derived: <value> <unit> from eic:Cxx via <script> <flags>'"]
    problems = []
    if not (PLUGIN_ROOT / parts["script"]).is_file():
        problems.append(f"derived line names a script that does not exist: {parts['script']}")
    numeric = sourcing_claims(" ".join(parts["cited"]), claims)
    if not numeric:
        problems.append("derived line cites no numeric claim with a number_kind")
    flags = parts["flags"]
    for flag in ("E-lepton", "E-hadron", "M"):
        if flag not in flags:
            problems.append(f"derived line lacks --{flag}")
    for flag in ("E-lepton", "E-hadron", "crossing-angle-mrad"):
        if flag in flags:
            try:
                value = to_float(flags[flag])
            except ValueError:
                problems.append(f"--{flag} is not a number: {flags[flag]}")
                continue
            if not any(contains_number(c["claim"], value) for c in numeric):
                problems.append(f"--{flag} {flags[flag]} is not a number of a cited numeric claim")
    if "M" in flags:
        try:
            if not same_number(to_float(flags["M"]), proton_mass_gev()):
                problems.append(f"--M {flags['M']} is not the core.constants proton mass written in full")
        except ValueError:
            problems.append(f"--M is not a number: {flags['M']}")
    return problems


def module_problems(text, claims):
    """Per-number and derived-line problems of one module text: list of (line number, message)."""
    problems = []
    for number, line in checked_lines(text):
        if is_derived(line):
            problems += [(number, message) for message in derived_line_problems(line, claims)]
            continue
        for value in unsourced_numbers(line, claims):
            problems.append((number, f"number {value:g} is not stated by a cited numeric claim: {line.strip()[:100]}"))
    return problems


def performance_number_problems(text):
    """Number tokens within 40 characters of a performance word, on the whole cleaned line (outside fenced code)."""
    problems = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        lowered = cleaned(line).lower()
        number_spans = spans(line)
        for word in PERFORMANCE_WORDS:
            for hit in re.finditer(re.escape(word), lowered):
                near = [value for start, end, value in number_spans if end > hit.start() - 40 and start < hit.end() + 40]
                if near:
                    problems.append((number, f"number near the performance word '{word}': {line.strip()[:100]}"))
    return problems
