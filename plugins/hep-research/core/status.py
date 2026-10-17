"""Shared script statuses, exit codes and their mapping to artifact status labels (F-04). Standard library only.

Two vocabularies meet in a script's output and are kept apart:
- the run status, the JSON "status" key: what happened to this run. Its exit code is fixed by the hep-computing
  script contract (skills/hep-computing/SKILL.md): 0 ok, 1 negative verdict, 2 bad input, 3 missing dependency or
  incomplete. No other exit code is used;
- the artifact status label (contracts/vocab/core.json artifact_statuses): what the inputs and results are
  (synthetic, observed, ...). A script takes it with --status (default unvalidated) and echoes it as "status_label".
  Some older detector and measurement scripts echo the label under "status"; they are listed in
  tests/skills/test_cli_contract.py.
The obligation states of the analysis check (satisfied, violated, not_applicable, unverified, unsupported) are a third
vocabulary and are not mapped here.

Usage in a script:
    from core.status import add_status_argument, exit_code
    add_status_argument(parser)                 # --status LABEL, default unvalidated
    print(json.dumps({"status": "ok", "status_label": args.status, ...}))
    return exit_code("ok")
"""
from __future__ import annotations

EXIT_OK, EXIT_NEGATIVE, EXIT_BAD_INPUT, EXIT_INCOMPLETE = 0, 1, 2, 3
EXIT_CODES = (EXIT_OK, EXIT_NEGATIVE, EXIT_BAD_INPUT, EXIT_INCOMPLETE)

# run status -> exit code. The first name in each group is the preferred one for new scripts; the others are in use
# in shipped scripts and keep their meaning.
RUN_STATUSES = {
    "ok": EXIT_OK, "passed": EXIT_OK, "pass": EXIT_OK, "written": EXIT_OK, "converged": EXIT_OK,
    "failed": EXIT_NEGATIVE, "fail": EXIT_NEGATIVE, "refused": EXIT_NEGATIVE, "not-converged": EXIT_NEGATIVE,
    "invalid": EXIT_NEGATIVE, "rerun-required": EXIT_NEGATIVE,
    "rejected": EXIT_BAD_INPUT, "error": EXIT_BAD_INPUT,
    "incomplete": EXIT_INCOMPLETE, "missing-dependency": EXIT_INCOMPLETE, "not-run": EXIT_INCOMPLETE,
}

# contracts/vocab/core.json artifact_statuses (tests/core/test_status.py keeps the two equal; core does not read contracts)
ARTIFACT_LABELS = ("failed", "unvalidated", "preliminary", "synthetic", "asimov", "observed", "user-supplied",
                   "validated-in-scope", "projection")
DEFAULT_LABEL = "unvalidated"

# what a run status does to the labels of an artifact written from the run. None: no artifact may be written (the
# input was refused or the run did not happen); otherwise the label added to the input labels.
_ADDED_LABEL = {EXIT_OK: "", EXIT_NEGATIVE: "failed", EXIT_INCOMPLETE: "unvalidated"}
_NO_ARTIFACT = frozenset({"rejected", "error", "refused", "missing-dependency", "not-run"})


def exit_code(status: str) -> int:
    """The exit code of a run status; an unknown status is a programming error (KeyError)."""
    return RUN_STATUSES[status]


def artifact_labels(status: str, labels: list[str] | tuple[str, ...] = (DEFAULT_LABEL,)) -> list[str] | None:
    """Labels for an artifact written from a run with this status: the input labels, plus 'failed' after a negative
    verdict or 'unvalidated' after an incomplete run; None when no artifact may be written."""
    code = exit_code(status)
    if status in _NO_ARTIFACT:
        return None
    bad = [x for x in labels if x not in ARTIFACT_LABELS]
    if bad:
        raise ValueError(f"unknown artifact status label(s) {bad}; known: {list(ARTIFACT_LABELS)}")
    out = list(dict.fromkeys(labels))
    added = _ADDED_LABEL[code]
    if added and added not in out:
        out.append(added)
    return out


def add_status_argument(parser, default: str = DEFAULT_LABEL, help_text: str | None = None) -> None:
    """--status LABEL: the artifact status label of the inputs, echoed as "status_label" (default unvalidated)."""
    parser.add_argument("--status", choices=ARTIFACT_LABELS, default=default,
                        help=help_text or f"status label of the inputs, echoed as status_label (default {default})")
