"""The one way a reconstruction sidecar is read (K13; contract-map.md, "Rules for readers"; plan Section 8.1).

read_document checks the format, stops at an unknown required extension, and applies the schema and the semantic rules.
read_sidecar is that function, and every other public function of contracts.reconstruction and contracts.conditions that
reads a sidecar takes whole documents through reader_path, which calls it on each. So no route acts on a sidecar this reader
refuses. contracts.input_inspector reads files, and a JSON document there reaches a fact only through read_document, or, for an
envelope artifact, through contracts.validate.validate_artifact. contracts.candidate_selection takes whole documents through reader_path too.
Two digest functions read no meaning; a converter and an old tool contract are read by their own schemas.
tests/contracts/test_reconstruction_reader.py drives every public function, enumerated from the modules, with an
unknown-format document and with a document carrying an unknown required extension.

A reader refuses with a finding or a safe answer, never an exception: a malformed document ends the same way. An ignored
optional extension is a finding in a report, and a warning (IgnoredExtensionWarning) on a path that returns no report.
That holds in a supported environment: contracts.reconstruction imports NumPy, a mandatory dependency
(tools/check_layering.py), so where it is missing the first read raises ModuleNotFoundError instead of a finding.
"""
from __future__ import annotations

import functools
import inspect
import math
import warnings

from contracts.schema import Report, validate

FORMATS = {"reconstruction-port/1": "reconstruction_port.json", "reconstruction-product/1": "reconstruction_product.json",
           "conditions-payload/1": "conditions_payload.json", "reconstruction-recipe/1": "reconstruction_recipe.json",
           "binding-evidence/1": "binding_evidence.json", "selection-record/1": "selection_record.json",
           "input-signature/1": "input_signature.json", "input-inspection/1": "input_inspection.json",
           "candidate-index/1": "candidate_index.json", "selection-policy/1": "selection_policy.json"}

KNOWN_EXTENSIONS = frozenset({"reconstruction:estimate-v1", "reconstruction:frames-v1", "reconstruction:candidates-v1",
                              "reconstruction:inversion-v1", "reconstruction:counts-v1", "reconstruction:scan-v1",
                              "reconstruction:constraints-v1", "reconstruction:association-v1"})
MALFORMED_DOCUMENT = (TypeError, ValueError, KeyError, IndexError, AttributeError, ZeroDivisionError, OverflowError, RecursionError,
                      ArithmeticError)


class IgnoredExtensionWarning(UserWarning):
    """K13: an unknown optional extension is ignored and reported, also where a path returns no report."""


def _stop_at_extensions(document, report: Report, known_extensions=KNOWN_EXTENSIONS, path: str = "$") -> bool:
    """True when the reader must stop: at an unknown required extension, also in a port nested in a recipe, or at a
    document that does not declare its extensions. An unknown optional extension is ignored and reported."""
    if not isinstance(document, dict) or not isinstance(document.get("required_extensions"), list):
        report.add("error", f"{path}.required_extensions", "reconstruction.reader.extensions_not_declared",
                   "a sidecar is an object that lists its required extensions")
        return True
    required, optional = document["required_extensions"], document.get("optional_extensions", [])
    optional = optional if isinstance(optional, list) else []
    unknown = [extension for extension in required if not isinstance(extension, str) or extension not in known_extensions]
    for extension in unknown:
        report.add("error", f"{path}.required_extensions", "reconstruction.reader.unknown_required_extension",
                   f"this reader does not implement the required extension {extension!r}: it stops here")
    ports = [document.get(field) for field in ("inputs", "outputs")]
    nested = [port for found in ports if isinstance(found, list) for port in found if isinstance(port, dict)]
    stopped = [_stop_at_extensions(port, report, known_extensions, f"{path}.ports") for port in nested]
    if unknown or any(stopped):
        return True
    for extension in optional:
        if not isinstance(extension, str) or extension not in known_extensions:
            report.add("warning", f"{path}.optional_extensions", "reconstruction.reader.unknown_optional_extension",
                       f"the optional extension {extension!r} is not implemented by this reader and was ignored")
    fields = document.get("extensions")
    for extension in fields if isinstance(fields, dict) else []:
        if extension not in required and extension not in optional:
            report.add("error", f"{path}.extensions", "reconstruction.reader.undeclared_extension",
                       f"{extension!r} is in neither required_extensions nor optional_extensions")
        elif extension in known_extensions:
            report.add("warning", f"{path}.extensions", "reconstruction.reader.extension_fields_unread",
                       f"this reader holds {extension!r} in its own block and did not read these fields")
    return False


def _check_finite(value, report: Report, path: str = "$") -> None:
    """JSON parsers accept NaN and infinity; no sidecar means them."""
    if isinstance(value, float) and not math.isfinite(value):
        report.add("error", path, "reconstruction.reader.not_finite", f"{value} is not a finite number")
    elif isinstance(value, dict):
        for key, item in value.items():
            _check_finite(item, report, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _check_finite(item, report, f"{path}[{index}]")


def _report_malformed(error: Exception, report: Report) -> None:
    report.add("error", "$", "reconstruction.reader.malformed", f"the document cannot be read: {type(error).__name__}: {error}")


def read_document(document, known_extensions=KNOWN_EXTENSIONS, path: str = "$") -> Report:
    """Format, K13 extensions, schema, finite numbers, then the semantic rules of the format. Always returns a report."""
    report = Report()
    try:
        _read_into(document, report, known_extensions, path)
    except MALFORMED_DOCUMENT as error:
        _report_malformed(error, report)
    return report


def _read_into(document, report: Report, known_extensions, path: str) -> None:
    from contracts.reconstruction import SIDECAR_CHECKS  # imported here: both reader modules import this one
    kind = document.get("schema") if isinstance(document, dict) else None
    if not isinstance(kind, str) or kind not in FORMATS:
        report.add("error", f"{path}.schema", "reconstruction.reader.unknown_format", f"{kind!r} is not a sidecar format this reader knows")
        return
    if _stop_at_extensions(document, report, known_extensions, path):
        return
    if kind != "reconstruction-product/1":
        _check_no_block_extension(document, report, path)
    validate(document, FORMATS[kind], report=report, path=path)
    _check_finite(document, report, path)
    if report.ok:
        SIDECAR_CHECKS[kind](document, report, path)


def _check_no_block_extension(document: dict, report: Report, path: str) -> None:
    """K13: a required extension changes how a document reads. Every known one belongs to a product block, so on another
    format it promises a meaning nothing here can honour."""
    ports = [document.get(field) for field in ("inputs", "outputs")]
    nested = [port for found in ports if isinstance(found, list) for port in found if isinstance(port, dict)]
    for item in [document] + nested:
        for extension in item.get("required_extensions", []):
            report.add("error", f"{path}.required_extensions", "reconstruction.extension.not_for_this_format", f"{extension} belongs to a block of a product")


def _listed_documents(found) -> list:
    """The documents behind one argument: a document, a list of them, or a mapping from a slot to a document."""
    if isinstance(found, (list, tuple)):
        return list(found)
    return list(found.values()) if isinstance(found, dict) and "schema" not in found else [found]


def reader_path(*parameters: str, refused=None):
    """Wrap a function that reads the documents in these parameters. It runs only if read_document accepts each. Otherwise,
    or on a malformed document, the call returns refused(report, arguments), which by default is the report: a safe answer
    for what the function returns, so `refused` must itself never raise. Warnings join the function's report, or are
    issued as IgnoredExtensionWarning when it returns none."""
    def decorate(function):
        signature = inspect.signature(function)

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            arguments, report = bound.arguments, Report()
            known = arguments.get("known_extensions", KNOWN_EXTENSIONS)
            for parameter in parameters:
                for document in _listed_documents(arguments[parameter]):
                    report.findings.extend(read_document(document, known, f"$.{parameter}").findings)
            if not report.errors:
                try:
                    answer = function(*args, **kwargs)
                except MALFORMED_DOCUMENT as error:
                    _report_malformed(error, report)
                else:
                    if isinstance(answer, Report):
                        answer.findings[:0] = report.findings
                    else:
                        for finding in report.findings:
                            warnings.warn(finding.message, IgnoredExtensionWarning, stacklevel=2)
                    return answer
            return refused(report, arguments) if refused else report
        wrapper.reads_sidecars = True  # type: ignore[attr-defined]
        wrapper.document_parameters = parameters  # type: ignore[attr-defined]
        return wrapper
    return decorate
