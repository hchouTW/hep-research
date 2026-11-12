"""One bin's tests on the statistics core, for T08 and T09 scoring (D4 stage E6c; d4-e6c-brief.md, items 1 and 2). Scoring side.

Sections cited are of t04-values-v4.md (Freeze A). The core (t04_evaluation_core.py, E6a) holds every rule; this module only feeds it one bin
at a time and names the records, so T08 and T09 scoring read the same way:
- pulls(gate, per_event): section 6's three common gates on one pull variable: the location and width pull tests (core.pull_tests: trimmed
  centre and sigma_68 - 1, the bin's own B = 1,000 event-bootstrap replicates, the level of the bin's block) and the tail rate test,
  P(|pull| > 3) at L = 1 % (core.rate_test, objects = the event's pulls, failures = those beyond 3);
- rate(gate, m, y, limit): section 5.2's rate test; efficiency(gate, m, failures, lower_limit): section 5.2's efficiency test;
- an ungated record (section 10, "Ungated": a bin outside a valid range, or listed as reported) is core.mark_ungated with its reason: numbers
  only, inconclusive, required no, its obligation opened by core.workflow_outcome;
- missing(gate, statistic): section 10's "Required output missing" record of a test that cannot be computed (core.missing_output).

Block 1 (tuning, section 3.2) has no evaluation level: the core refuses it (I1 of E6a's review). The block-1 job of this stage prints the same
tests as development readings: the core's named replay path (core.replay_pull_tests, core.replay_rate_test) with the attempt as the number 1
(95 %) and the bin's own bootstrap rows (core.bootstrap_indices of the block-1 identity), every record's bin labelled DEVELOPMENT_LABEL and
its words never a verdict. The efficiency record on that path is the core's flip of the rate record (as core.efficiency_test), tested equal to
core.efficiency_test on a block-11 bin (test_t08_scoring, BinScorerPaths). Blocks other than 1, 11 and 12 are refused here as well.
"""
from __future__ import annotations

import dataclasses

import numpy

from tests.adapters import t04_evaluation_core as core

DEVELOPMENT_BLOCK = 1
DEVELOPMENT_LABEL = "development reading, block 1"
DEVELOPMENT_ATTEMPT = 1            # the replay's attempt number: 95 % (section 3.4's attempt 1), a reading only
TAIL_PULL = 3.0                    # section 6, "Tail": P(|pull| > 3)
TAIL_LIMIT = 0.01                  # section 6, "Tail": L = 1 %
PULL_STATISTICS = ("trimmed-centre", "sigma68-width", "tail")


class ScoringError(ValueError):
    """An input the scoring refuses: a product, a truth file or a bin of another identity, or a block with no level."""


class BinScorer:
    """The tests of one bin. identity: the bin (core.BinIdentity); label: the record's bin text (the identity's label unless a pooled test
    names its pool, section 9.4)."""

    def __init__(self, identity: core.BinIdentity, label: str | None = None):
        self.identity = identity
        self.development = identity.block == DEVELOPMENT_BLOCK
        if not self.development:
            try:
                identity.level
            except core.CoreError as error:
                raise ScoringError(f"{identity.label}: {error}; only block 1 (development readings) or 11 and 12 are scored") from None
        own = label or identity.label
        self.label = f"{DEVELOPMENT_LABEL}: {own}" if self.development else own
        self._rows = {}

    # -- helpers

    def _named(self, record: core.TestResult, required: bool, reason: str, statistic: str | None = None) -> core.TestResult:
        record = dataclasses.replace(record, bin=self.label, statistic=statistic or record.statistic)
        if self.development:
            readings = dict(record.readings, label=DEVELOPMENT_LABEL)
            record = dataclasses.replace(record, required=required, readings=readings)
        if not required:
            record = core.mark_ungated(record, reason)
        return record

    def _rows_for(self, events: int):
        if events not in self._rows:
            self._rows[events] = core.bootstrap_indices(self.identity, events)
        return self._rows[events]

    # -- the tests

    def pulls(self, gate: str, per_event, *, required: bool = True, reason: str = "") -> list:
        """(centre, width, tail) of one pull variable; per_event: one sequence of pulls per event of the bin, empty where the event has none."""
        events = core.EventValues.of(per_event)
        if events.events == 0:
            return [self.missing(gate, statistic, "the bin holds no event", required=required, reason=reason) for statistic in PULL_STATISTICS]
        if self.development:
            centre, width = core.replay_pull_tests(gate, events_as_list(events), attempt=DEVELOPMENT_ATTEMPT, indices=self._rows_for(events.events))
        else:
            centre, width = core.pull_tests(gate, self.identity, events_as_list(events), required=True)
        counts = events.counts.astype(numpy.int64)
        beyond = numpy.array([int((numpy.abs(events.values[s:s + c]) > TAIL_PULL).sum()) for s, c in zip(events.starts, events.counts)], dtype=numpy.int64)
        tail = self.rate(gate, counts, beyond, TAIL_LIMIT, statistic="tail", required=True)
        records = [self._named(centre, required, reason), self._named(width, required, reason)]
        records.append(tail if required else core.mark_ungated(tail, reason))
        return records

    def rate(self, gate: str, m, y, limit: float, *, statistic: str = "rate", required: bool = True, reason: str = "",
             min_events: int | None = None) -> core.TestResult:
        m, y = numpy.asarray(m, dtype=numpy.int64), numpy.asarray(y, dtype=numpy.int64)
        if self.development:
            record = core.replay_rate_test(gate, m, y, limit, attempt=DEVELOPMENT_ATTEMPT, min_events=min_events)
        else:
            record = core.rate_test(gate, self.identity, m, y, limit, min_events=min_events, required=True, statistic=statistic)
        return self._named(record, required, reason, statistic)

    def efficiency(self, gate: str, m, failures, lower_limit: float, *, required: bool = True, reason: str = "") -> core.TestResult:
        m, failures = numpy.asarray(m, dtype=numpy.int64), numpy.asarray(failures, dtype=numpy.int64)
        if self.development:
            rate = core.replay_rate_test(gate, m, failures, 1 - lower_limit, attempt=DEVELOPMENT_ATTEMPT, min_events=core.EFFICIENCY_MINIMUM_EVENTS)
            record = as_efficiency(rate, lower_limit)
        else:
            record = core.efficiency_test(gate, self.identity, m, failures, lower_limit, required=True)
        return self._named(record, required, reason, "efficiency")

    def missing(self, gate: str, statistic: str, why: str, *, required: bool = True, reason: str = "") -> core.TestResult:
        if self.development:
            record = core.TestResult(gate, self.label, statistic, None, None, None, None, None, "inconclusive", 0, DEVELOPMENT_ATTEMPT,
                                     core.CONFIDENCE_OF_ATTEMPT[DEVELOPMENT_ATTEMPT], None, True, f"required output missing: {why}",
                                     {"label": DEVELOPMENT_LABEL})
        else:
            record = dataclasses.replace(core.missing_output(gate, self.identity, statistic, why), bin=self.label)
        return record if required else core.mark_ungated(record, reason or f"ungated; and required output missing: {why}")


def as_efficiency(rate: core.TestResult, lower_limit: float) -> core.TestResult:
    """core.efficiency_test's flip of a rate record on 1 - efficiency (section 5.2: the lower bound on efficiency is 1 - U)."""
    flip = (lambda v: None if v is None else 1 - v)
    return dataclasses.replace(rate, statistic="efficiency", estimate=flip(rate.estimate), lower=flip(rate.upper), upper=flip(rate.lower),
                               limit=lower_limit, readings=dict(rate.readings, failure_rate_limit=1 - lower_limit))


def events_as_list(events: core.EventValues) -> list:
    return [events.values[s:s + c] for s, c in zip(events.starts, events.counts)]


def record_document(record: core.TestResult) -> dict:
    """A record as JSON (the scoring tasks' output, read back by the summary)."""
    return dataclasses.asdict(record)


def record_of(document: dict) -> core.TestResult:
    names = {f.name for f in dataclasses.fields(core.TestResult)}
    if not isinstance(document, dict) or set(document) != names:
        raise ScoringError(f"a record has exactly the keys {sorted(names)}")
    return core.TestResult(**document)


def record_line(record: core.TestResult) -> str:
    """One printed line per record: the gate, its statistic and bin, the result word, its step, the estimate, bounds and limit."""
    def number(v):
        return "-" if v is None else f"{v:.6g}"
    words = record.result
    if record.bin.startswith(DEVELOPMENT_LABEL):
        words = f"{record.result} ({DEVELOPMENT_LABEL}, no verdict)"
    mean = record.readings.get("mean")
    rms = record.readings.get("rms")
    beside = "" if mean is None else f" mean {number(mean)} rms {number(rms)}"
    return (f"TEST {record.gate} | {record.statistic} | {record.bin} | {words} step {record.step} | estimate {number(record.estimate)} "
            f"se {number(record.standard_error)} lower {number(record.lower)} upper {number(record.upper)} limit {number(record.limit)} | "
            f"required {'yes' if record.required else 'no'}{beside}" + (f" | {record.reason}" if record.reason else ""))
