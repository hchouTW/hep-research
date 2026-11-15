"""adapters/photon-likelihood, D3 stage 5 of T09, renewed in D4 build E1: the adapter's records agree with one another and claim no more
than the jobs ran.

It reads files only; no recipe, fixture or job runs here. The records are:
- `adapters/photon-likelihood/adapter.json`: version, status, the tool's status and tested versions, environment, status rule;
- the `VALIDATION.md` section PHOTON-LIKELIHOOD-T09: the run of record (docs/adapter-authoring.md, "Changing an adapter");
- the `adapters/photon-likelihood` row of `docs/capability-matrix.md` (docs/adapter-authoring.md, Honesty rules);
- `docs/dev/detector-reconstruction/t09-closeout.md`: T09 against its sheet, one status per row, and its summary.

What is checked:
- The adapter claims `demonstrated-on-synthetic-data` for its tool and for itself, and no higher: its jobs ran on the synthetic
  fixture t09-sphere/1, a shared-model closure, and on hand-made events, against an independently written evaluation of the same
  likelihood and the plugin's own earlier outputs, with no reference output from outside the plugin.
- The tested versions are the ones the jobs of record logged, and the VALIDATION section states each of them.
- adapter.json, the VALIDATION section, the matrix row and the close-out name one and the same job of record for the declared version:
  the D4 E1 job for adapter 0.3.0 (T07's ruling M3: a job's ID cannot sit in a file of its own manifest, so the records name the job, and
  after a PASS the coordinator writes "job <ID>, the D4 E1 job" into each), the earlier job of record (job 7578442, the D3 stage 5 job,
  adapter 0.2.0) and the T09 stage 4 chain (jobs 7575617, 7576269, 7576270) as the latest run of the strata.
- Every declared test module, every asset `adapter.json` lists, and the example's `run.py` have the SHA-256 pinned below: for the stage
  1 to 4 files the values of job 7575617's manifest (`SOURCES.sha256` `0c4e5c9c...`, 822 files), for the example and its test the values
  of the D3 stage 5 job's manifest (job 7578442), for the files D4 build E1 changes or adds the values of the D4 E1 job's manifest, and
  for the files the PR #411 CI fix round changed, the values of job 7655492's manifest (a237d5a7…), but for
  `tests/adapters/test_photon_likelihood_topology.py`, changed again in the main full-run fix round after PR #411, the value of job
  7658281's manifest (e86bfafe…). One changed byte in any of them makes this test fail, until a new job of record runs the changed
  files and the pins and the record are renewed. Exempt: this module and the records it reads (`adapter.json`, `VALIDATION.md`,
  `docs/capability-matrix.md`, `t09-closeout.md`). A file declared later without a pin fails too.
- The VALIDATION table's test counts equal the test methods each declared module defines now; the modules the D4 E1 job runs first
  (the negative-check module and this one) are named as the D4 E1 job's until its ID is written.
- The close-out's statuses are the four status words, every row not met says what would close it, its summary counts are its rows'
  counts, every part of the sheet has a row, and the rows the D3 stage 5 brief names are there with the status the rules give.
- No absolute host path in these records.

Run from the plugin root: python -m unittest tests.adapters.test_photon_likelihood_records -v
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "photon-likelihood"
RECORDS = ROOT / "docs" / "dev" / "detector-reconstruction"
CLOSEOUT = RECORDS / "t09-closeout.md"
SECTION_NAME = "PHOTON-LIKELIHOOD-T09"
CLAIM = "demonstrated-on-synthetic-data"
FIRST_VERSION = "0.1.0"  # the undeclared development version of stages 1 to 4, status proposed
STATUS_WORDS = ("met", "met with readings", "open", "gap")
HOST_PATH = re.compile(r"/ceph|/var/tmp|/tmp/|/dicos|/home/|/sharedfs")  # a node name (hpa-wn33) is a record, as in T07 and T08
THIS_MODULE = "tests/adapters/test_photon_likelihood_records.py"
EXAMPLE_TEST = "tests/examples/test_reconstruction_photon_likelihood.py"
EXAMPLE_RUN = "examples/reconstruction-photon-likelihood/run.py"
NEGATIVE_MODULE = "tests/adapters/test_photon_likelihood_negative.py"
JOB_NAME = "the D4 E1 job"                 # the job of record for the declared version (adapter 0.3.0)
JOB_PATTERN = r"the\s+D4\s+E1\s+job"
PENDING_MODULES = (THIS_MODULE, NEGATIVE_MODULE)
EARLIER_RUNS = ("7578442", "7575617", "7576269", "7576270")   # the D3 stage 5 job (adapter 0.2.0) and the T09 stage 4 chain
# The tool's tested versions, as job 7575617's receipt prints them ("Python 3.13.18", "numpy 2.4.6 scipy 1.17.1").
TOOL_VERSIONS = (("Python 3.13.18", "NumPy 2.4.6", "SciPy 1.17.1"),)
# The SHA-256 of each declared test module and adapter.json asset, and of the example's run.py (paths from the plugin root): the stage 1
# to 4 files as job 7575617's manifest (SOURCES.sha256 0c4e5c9c...) has them, the example and its test as the D3 stage 5 job's manifest
# (job 7578442), the files D4 build E1 changes or adds (configuration.py, product.py, photon_likelihood.py; single_photon.py,
# t09_negative_checks.py, the single-photon configuration, the negative-check module) as the D4 E1 job's manifest; for the files the PR #411
# CI fix round changed (test_photon_likelihood_time.py, test_photon_likelihood_topology.py, the example's test and run.py), the values of job
# 7655492's manifest (a237d5a7…); for test_photon_likelihood_topology.py, changed again in the main full-run fix round after PR #411
# (the TwoSourceHarness skip condition needs recording_erfc()), the value of job 7658281's manifest (e86bfafe…).
JOB_OF_RECORD_PINS: dict = {
    "adapters/photon-likelihood/assets/fixture_tools/t09_fixed_points.py": "652af9311ec9ef51c1a7d2da715180e134264314b715b3b86efde48170ee1081",
    "adapters/photon-likelihood/assets/fixture_tools/t09_fixture_files.py": "20640f670329b249c3f81317976f8e5ddaeea9957f7c2a7d50c88359d184f4ed",
    "adapters/photon-likelihood/assets/fixture_tools/t09_independent_likelihood.py": "a12edcb26f754828012b90c69522545fe4cddae3a21f84d0454bc0aca2d18216",
    "adapters/photon-likelihood/assets/fixture_tools/t09_job_lines.py": "13137fc321379c7aa3507ba81a9ae41a9f4b18266ff093aff973c24347faebdd",
    "adapters/photon-likelihood/assets/fixture_tools/t09_negative_checks.py": "bf539ab33baa4f14ca295679c2921e15d31dedf4b8a5b46b3739a557d9f14de8",
    "adapters/photon-likelihood/assets/fixture_tools/t09_readings.py": "beefb0076e7098a25ab1cd8bc2164fb7476601c4e6cc0a397c9357d3b0246355",
    "adapters/photon-likelihood/assets/fixture_tools/t09_topology_readings.py": "762d272ca05ea7c80a133731406e733d45f209c67cc241c01785ec1796fc7c4c",
    "adapters/photon-likelihood/assets/fixture_tools/t09_truth_start.py": "6e49246bcd02d6a2931a0360c5b95cec1639f706ba694767485ba2b2689f275e",
    "adapters/photon-likelihood/assets/light_recipe/__init__.py": "9d16d3ba5ba96a7c0bb2a919b2b9db9ce48020e3f4ef0ccafd358472ac3dbe60",
    "adapters/photon-likelihood/assets/light_recipe/arrival_response.py": "fcbb347d6bb3c04e366a0f28cd0a6f95749ffe71213ab25898d370a170feb14a",
    "adapters/photon-likelihood/assets/light_recipe/charge_response.py": "d619b7411ec8b70c24074d2a6fe9ab98c0ab404f4469f70b6f9bbcc5d4d4cda8",
    "adapters/photon-likelihood/assets/light_recipe/configuration.py": "1a3cf42d34a3acd081cc5a15af531b42a900844f112ee999b15ce583b619022f",
    "adapters/photon-likelihood/assets/light_recipe/fit.py": "30d92e448e461084556364e4d2fd4e036c69142dc88b91f08dbf8acfff71a476",
    "adapters/photon-likelihood/assets/light_recipe/joint.py": "aa67f3c5d35f5eac7f7cf5ec4522fb7379ce705822c3ef61e4d80b89e324806e",
    "adapters/photon-likelihood/assets/light_recipe/light_model.py": "c716d4fccb73b75a711033f8cd45f2fbe9640e4483e3339fa74064fc2814552b",
    "adapters/photon-likelihood/assets/light_recipe/likelihood.py": "1e839b9dbbbe04e5867547b3eb8d86b6cbaef06a2ba2025d41d9acb580e1a084",
    "adapters/photon-likelihood/assets/light_recipe/multistart.py": "5953620f7aa3b3b886b67e440a4b1235f983b2c6dc663e03aaed2ce862461449",
    "adapters/photon-likelihood/assets/light_recipe/product.py": "8642c59a3bb7f4ca65a671ff388b7826b3c906e8e8ebe15e0974169051f1cee7",
    "adapters/photon-likelihood/assets/light_recipe/readout.py": "605debd51cb66dc266e16b56be08df7ef28479df577476d2ad531ea805d205ce",
    "adapters/photon-likelihood/assets/light_recipe/single_photon.py": "dad0238dafeecdfb5ee75e884f540930f3ad512606b06dd6305d7e75beb8b889",
    "adapters/photon-likelihood/assets/light_recipe/topology.py": "79dc45a9b800936dd3f8288ffbca040fa6ed0487eb38da55d290be8ee8ae802e",
    "adapters/photon-likelihood/assets/photon_likelihood.py": "8a4f4fd0e0f24231b56177693defa53c6514f578ded5ba46636c320562df07a6",
    "adapters/photon-likelihood/assets/t09-multistart-1.budget.json": "70220b7ddf1679d01d4a9c5397d1fdf124c6f0bd8ed4dca562d9c18e04180307",
    "adapters/photon-likelihood/assets/t09-sphere-1-single-photon.configuration.json": "5aa052431facfd18c07e05d479b67fcfb717df4e3cd410c781f9d69a29daad98",
    "adapters/photon-likelihood/assets/t09-sphere-1.configuration.json": "ce4f430756f8ea0be1ab1b08eb638f9c38bf305968aa2d6d4e743d5fc68a1508",
    "adapters/photon-likelihood/assets/t09-topology-2.budget.json": "104262a1bfb0f5403a075884d9acd5f5ccbf1fc012d5237b578297f4d98ed7df",
    "examples/reconstruction-photon-likelihood/run.py": "01d1597c971684810356be337cd370498cf967b131140a770d23c8c3fab1c8f3",
    "tests/adapters/test_photon_likelihood.py": "4a84003147fa7ad2b3e41b9ebb32ce4dcf2a2a9b40b67426ca3928b31f7b2472",
    "tests/adapters/test_photon_likelihood_multistart.py": "f77444ede6b99af7ab05337e2d0e5c5d1c7a342c69cb3d29b7279bce9f3da214",
    "tests/adapters/test_photon_likelihood_negative.py": "58b0fec0ad352d67b38491b5aab70f9eee81da4113f94ececef15b2dfb14c049",
    "tests/adapters/test_photon_likelihood_time.py": "41acddee43e0f102262dfdf9e4b92d74a6f4f41ac4d8dc4c64707db7829d569e",
    "tests/adapters/test_photon_likelihood_topology.py": "9145bd6614cec0d520bc9999f70d0e745f7a6daceb40c9a6cf8b517a1a0666b2",
    "tests/examples/test_reconstruction_photon_likelihood.py": "fe47323b1d9a7529147ad912734d8b2f9dd4c9e54818c5c1bc2b5c496e11504d",
}
SHEET_PARTS = ("Background / Objective", "Scope", "Non-goals", "Existing work checked", "Files", "Input", "Likelihood", "Interfaces",
               "Steps", "Acceptance", "Open item", "Stop")
# Rows the D3 stage 5 brief names, by a phrase of their label, and the status the rules give them.
NAMED_ROWS = {
    "native backend": "gap",                              # U12 A: the user's decision, recorded as a gap in required delivery (K02)
    "original method sources": "met with readings",       # the user-approved check by variant (U-W6, t09-sources.md)
    "quality per": "open",                                # K09 at Freeze B
    "negative checks": "met with readings",               # v4 9.4's two negative checks: built in D4 E1, read on block 1 by job 7584387
}


def declaration() -> dict:
    return json.loads((ADAPTER / "adapter.json").read_text(encoding="utf-8"))


def validation_section() -> str:
    text = (ROOT / "VALIDATION.md").read_text(encoding="utf-8")
    start = text.index(f"\n## {SECTION_NAME} ")
    section = text[start + 1:]
    end = section.find("\n## ")
    return section if end < 0 else section[:end]


def matrix_row() -> str:
    matrix = (ROOT / "docs" / "capability-matrix.md").read_text(encoding="utf-8")
    return next(line for line in matrix.splitlines() if line.startswith("| `adapters/photon-likelihood`"))


def jobs_of_record(text: str, version: str) -> list:
    """Each naming of the declared version's job of record: the job's ID once the coordinator wrote it, else 'pending'."""
    found = re.findall(rf"job\s+of\s+record\s+for\s+adapter\s+{re.escape(version)}:\s+(?:job\s+(\d+),\s+)?{JOB_PATTERN}",
                       text, flags=re.IGNORECASE)
    return [job or "pending" for job in found]


def cells(line: str) -> list:
    """The cells of one markdown table line; a pipe inside backticks or escaped is not a separator."""
    parts, current, in_code, index = [], "", False, 0
    body = line.strip()[1:-1] if line.strip().endswith("|") else line.strip()[1:]
    while index < len(body):
        char = body[index]
        if char == "\\" and index + 1 < len(body) and body[index + 1] == "|":
            current += "|"
            index += 2
            continue
        if char == "`":
            in_code = not in_code
        if char == "|" and not in_code:
            parts.append(current.strip())
            current = ""
        else:
            current += char
        index += 1
    parts.append(current.strip())
    return parts


def tables_under(text: str, heading: str) -> list:
    """Rows (header-keyed dicts) of every table between `heading` and the next heading of the same level."""
    level = heading.split(" ")[0]
    start = text.index(f"\n{heading}\n")
    rest = text[start + len(heading) + 2:]
    stop = re.search(rf"\n{re.escape(level)} ", rest)
    body = rest if stop is None else rest[:stop.start()]
    rows, header = [], None
    for line in body.splitlines():
        if not line.startswith("|"):
            header = None
            continue
        row = cells(line)
        if header is None:
            header = row
        elif set("".join(row)) <= set("-: "):
            continue
        else:
            rows.append(dict(zip(header, row)))
    return rows


def method_count(module: Path) -> int:
    return len(re.findall(r"^    def test_", module.read_text(encoding="utf-8"), flags=re.MULTILINE))


def declared_tests() -> list:
    return [listed[len("../../"):] for listed in declaration()["tests"]]


class AdapterClaim(unittest.TestCase):
    def test_the_tool_and_the_adapter_claim_demonstrated_on_synthetic_data(self):
        record = declaration()
        self.assertEqual(record["status"], CLAIM)
        self.assertEqual([tool["status"] for tool in record["tools"]], [CLAIM] * len(TOOL_VERSIONS))
        self.assertRegex(record["version"], r"^\d+\.\d+\.\d+$")
        self.assertNotEqual(record["version"], FIRST_VERSION, "the first recorded status is a change of the adapter: bump its version")

    def test_the_status_rule_names_the_claim_the_label_not_taken_and_the_closure(self):
        rule = declaration()["status_rule"]
        self.assertTrue(rule.split(";")[1].strip().startswith(f"{CLAIM}:"), rule)
        self.assertIn("not tested-in-declared-environment", rule)
        self.assertIn("shared-model closure", rule)
        self.assertIn("no photon-likelihood quality claim", rule)

    def test_the_tool_lists_the_versions_the_jobs_of_record_logged(self):
        record, section = declaration(), validation_section()
        for tool, words in zip(record["tools"], TOOL_VERSIONS):
            with self.subTest(tool=tool["name"]):
                self.assertTrue(tool["tested_versions"])
                listed = " ".join(tool["tested_versions"])
                for word in words:
                    self.assertIn(word, listed)
                    self.assertIn(word, section)

    def test_the_declared_tests_include_the_example_and_this_module(self):
        tests = declared_tests()
        self.assertIn(THIS_MODULE, tests)
        self.assertIn(EXAMPLE_TEST, tests)
        self.assertNotIn("none declared", declaration()["environment"])


class JobOfRecord(unittest.TestCase):
    def records(self) -> dict:
        record = declaration()
        return {"adapter.json": record["environment"] + " " + record["status_rule"], "VALIDATION.md": validation_section(),
                "capability-matrix.md": matrix_row(), "t09-closeout.md": CLOSEOUT.read_text(encoding="utf-8")}

    def test_every_record_names_one_and_the_same_job_of_record(self):
        version = declaration()["version"]
        named = {name: jobs_of_record(text, version) for name, text in self.records().items()}
        for name, jobs in named.items():
            with self.subTest(record=name):
                self.assertTrue(jobs, f"{name} names no job of record for adapter {version}")
        self.assertEqual(len({job for jobs in named.values() for job in jobs}), 1, named)

    def test_every_record_names_the_earlier_job_of_record_and_the_stage_4_chain(self):
        for name, text in self.records().items():
            with self.subTest(record=name):
                for job in EARLIER_RUNS:
                    self.assertIn(job, text)

    def test_the_section_is_the_declared_version_s_first_record(self):
        section = validation_section()
        self.assertIn(f"Adapter {declaration()['version']} ", section)
        self.assertIn(CLAIM, section)
        for word in ("Date", "Commit", "Environment", "Command", "Result"):
            self.assertIn(f"**{word}.**", section)

    def test_the_section_s_test_counts_are_the_modules_as_they_are_now(self):
        section = validation_section()
        pending = jobs_of_record(section, declaration()["version"]) == ["pending"]
        for module in declared_tests():
            with self.subTest(module=module):
                if module in PENDING_MODULES and pending:   # the D4 E1 job's new or changed modules, until its ID is written (review M4)
                    self.assertRegex(section, rf"\| `{re.escape(module)}`[^\n]*{re.escape(JOB_NAME)}")
                    continue
                found = re.search(rf"\| `{re.escape(module)}`[^|]*\| (\d+) run, OK", section)
                self.assertIsNotNone(found, f"the section has no result row for {module}")
                self.assertEqual(int(found.group(1)), method_count(ROOT / module), f"{module} changed after the job of record")


def closeout_counts() -> dict:
    text = CLOSEOUT.read_text(encoding="utf-8")
    return {row["Status"]: int(re.match(r"\d+", row["Rows"]).group(0)) for row in tables_under(text, "## Summary")}


class CountsAgree(unittest.TestCase):
    """Review M1: the matrix row and the VALIDATION section state the close-out's counts, and drop the example's open item once the
    close-out marks the example met."""

    def test_the_matrix_row_and_the_section_state_the_close_out_counts(self):
        c = closeout_counts()
        pattern = (rf"\b{c['met']} met, {c['met with readings']} met with readings, {c['open']} open\b[\s\S]{{0,400}}?"
                   rf"\b{c['gap']} gap\b")
        for name, text in (("capability-matrix.md", matrix_row()), ("VALIDATION.md", validation_section())):
            with self.subTest(record=name):
                self.assertRegex(text, pattern)

    def test_the_example_s_open_item_goes_with_its_row(self):
        rows = tables_under(CLOSEOUT.read_text(encoding="utf-8"), "## Sheet items")
        example = next(row for row in rows if next(iter(row.values())).startswith("Files, proposed: `examples/"))
        for name, text in (("capability-matrix.md", matrix_row()), ("VALIDATION.md", validation_section())):
            with self.subTest(record=name):
                if example["Status"] == "met":
                    self.assertNotRegex(text, r"the example until\s+the\s+D3\s+stage\s+5\s+job")
                else:
                    self.assertRegex(text, r"the example until\s+the\s+D3\s+stage\s+5\s+job")


class MatrixRow(unittest.TestCase):
    def test_the_row_states_the_claim_the_version_and_the_section(self):
        row, record = matrix_row(), declaration()
        self.assertIn(f"| {record['status']} |", row)
        self.assertIn(f"adapter {record['version']}", row)
        self.assertIn(f"VALIDATION {SECTION_NAME}", row)
        self.assertIn("examples/reconstruction-photon-likelihood", row)
        self.assertIn("not a native backend", row)
        for stale in ("| proposed |", "no job of record", "not recorded in `VALIDATION.md`", "so no tested version"):
            self.assertNotIn(stale, row)


class CloseOut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CLOSEOUT.read_text(encoding="utf-8")
        cls.sheet = tables_under(cls.text, "## Sheet items")

    def label_of(self, row) -> str:
        return next(iter(row.values()))

    def test_every_status_is_a_status_word_and_every_row_not_met_says_what_closes_it(self):
        self.assertTrue(self.sheet)
        for row in self.sheet:
            status = row.get("Status", "")
            with self.subTest(row=self.label_of(row)[:60]):
                self.assertIn(status, STATUS_WORDS)
                evidence = " ".join(value for key, value in row.items() if "evidence" in key.lower())
                self.assertTrue(evidence.strip(), "a row with a status cites its evidence")
                closing = list(row.values())[-1]
                if status != "met":
                    self.assertTrue(closing.strip(), "a row not met says why, and what would close it")

    def test_the_summary_counts_the_rows(self):
        summary = {row["Status"]: int(re.match(r"\d+", row["Rows"]).group(0)) for row in tables_under(self.text, "## Summary")}
        counted = {word: 0 for word in STATUS_WORDS}
        for row in self.sheet:
            counted[row["Status"]] += 1
        self.assertEqual(summary, counted)

    def test_every_part_of_the_sheet_has_a_row(self):
        labels = [self.label_of(row) for row in self.sheet]
        for part in SHEET_PARTS:
            with self.subTest(part=part):
                self.assertTrue(any(label.startswith(part) for label in labels), part)
        for stage in range(1, 6):
            with self.subTest(failing_first_stage=stage):
                self.assertTrue(any(label.startswith("Steps, failing check first") and f"stage {stage}" in label for label in labels))

    def test_the_named_rows_have_the_status_the_rules_give(self):
        for phrase, status in NAMED_ROWS.items():
            with self.subTest(row=phrase):
                rows = [row for row in self.sheet if phrase in self.label_of(row)]
                self.assertEqual(len(rows), 1, f"one row whose label holds {phrase!r}")
                self.assertEqual(rows[0]["Status"], status)
        sources = next(row for row in self.sheet if "original method sources" in self.label_of(row))
        self.assertIn("t09-sources.md", sources["Evidence"])       # the evidence names the record of the check by variant
        for variant in ("variant 1", "variant 2", "variant 3"):
            self.assertIn(variant, sources["Evidence"])
        self.assertIn("U12 A", " ".join(next(row for row in self.sheet if "native backend" in self.label_of(row)).values()))

    def test_the_k09_user_item_on_undecided_two_source_events_is_recorded(self):
        two = [row for row in self.sheet if "two simultaneous events" in self.label_of(row)]
        self.assertEqual(len(two), 1)
        self.assertIn("undecided", " ".join(two[0].values()))
        self.assertIn("K09", " ".join(two[0].values()))

    def test_the_close_out_states_the_adapter_record(self):
        record = declaration()
        self.assertIn(f"adapter {record['version']}", self.text)
        self.assertIn(f"`{record['status']}`", self.text)


# The recorded post-D4 change (2026-11-13, D4 closed): the held bytecode line, "sys.dont_write_bytecode = True" before the first plugin or
# sibling import (as adapters/geant4/assets/g4sim_run.py), so tests/skills/test_no_bytecode passes. The file at this digest is the bytes the job
# of record ran plus that one line, and nothing else: job_of_record_digest removes the line before comparing with its pin.
POST_D4_LINE = b"sys.dont_write_bytecode = True\n"
POST_D4_CHANGES = {"adapters/photon-likelihood/assets/photon_likelihood.py": "532260bd261dff01aed4a2455ce391da7e365563a8ee4f68d1632b1088978608"}


def job_of_record_digest(path: str, file_bytes: bytes) -> str:
    """The SHA-256 of the bytes the job of record ran, read from a file's current bytes: its own digest, or, for a file of POST_D4_CHANGES at
    its recorded digest, the digest of the file with the one post-D4 line removed."""
    if path in POST_D4_CHANGES and hashlib.sha256(file_bytes).hexdigest() == POST_D4_CHANGES[path] and file_bytes.count(POST_D4_LINE) == 1:
        file_bytes = file_bytes.replace(POST_D4_LINE, b"", 1)
    return hashlib.sha256(file_bytes).hexdigest()


class CodeAsTheJobOfRecordRanIt(unittest.TestCase):
    def pinned_files(self) -> list:
        record = declaration()
        declared = ["adapters/photon-likelihood/" + asset for asset in record["assets"]]
        declared += [module for module in declared_tests() if module != THIS_MODULE]
        return declared + [EXAMPLE_RUN]

    def test_every_declared_module_and_asset_and_the_example_have_the_bytes_the_jobs_of_record_ran(self):
        for path in self.pinned_files():
            with self.subTest(path=path):
                self.assertIn(path, JOB_OF_RECORD_PINS, f"{path} is declared but has no pin from the job of record")
                digest = job_of_record_digest(path, (ROOT / path).read_bytes())   # the recorded post-D4 change only
                self.assertEqual(digest, JOB_OF_RECORD_PINS[path], f"{path} differs from the bytes the job of record ran")
        # The recorded post-D4 change (the held bytecode line, released after D4): the file at its recorded digest is the bytes the job of
        # record ran plus that one line; any other change, or the line at another digest, is never read as those bytes.
        post_d4 = "adapters/photon-likelihood/assets/photon_likelihood.py"
        file_bytes = (ROOT / post_d4).read_bytes()
        self.assertEqual(hashlib.sha256(file_bytes).hexdigest(), POST_D4_CHANGES[post_d4])
        self.assertEqual(file_bytes.count(POST_D4_LINE), 1)
        self.assertEqual(job_of_record_digest(post_d4, file_bytes), JOB_OF_RECORD_PINS[post_d4])
        for changed in (file_bytes + b"# another change\n", file_bytes.replace(POST_D4_LINE, POST_D4_LINE * 2)):
            self.assertNotEqual(job_of_record_digest(post_d4, changed), JOB_OF_RECORD_PINS[post_d4])
        self.assertEqual(sorted(POST_D4_CHANGES), ["adapters/photon-likelihood/assets/photon_likelihood.py"])

    def test_no_pin_is_left_for_a_file_no_longer_declared(self):
        self.assertEqual(sorted(set(JOB_OF_RECORD_PINS) - set(self.pinned_files())), [])


class NoHostPath(unittest.TestCase):
    def test_no_record_holds_an_absolute_host_path(self):
        record = declaration()
        texts = {
            "adapter.json": json.dumps(record),
            "VALIDATION.md": validation_section(),
            "capability-matrix.md": matrix_row(),
            "t09-closeout.md": CLOSEOUT.read_text(encoding="utf-8"),
        }
        for name, text in texts.items():
            with self.subTest(record=name):
                self.assertIsNone(HOST_PATH.search(text), name)

    def test_the_pattern_finds_a_host_path(self):
        self.assertIsNotNone(HOST_PATH.search("built in /var/tmp/hdr-user/"))
        self.assertIsNone(HOST_PATH.search("<workdir>/env/py313"))


if __name__ == "__main__":
    unittest.main()
