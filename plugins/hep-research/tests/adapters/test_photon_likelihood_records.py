"""adapters/photon-likelihood, D3 stage 5 of T09: the adapter's records agree with one another and claim no more than the jobs ran.

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
  the D3 stage 5 job (T07's ruling M3: a job's ID cannot sit in a file of its own manifest, so the records name the job, and after a PASS
  the coordinator writes "job <ID>, the D3 stage 5 job" into each), and the T09 stage 4 chain (jobs 7575617, 7576269, 7576270) as the
  latest run of the same code before it.
- Every declared test module, every asset `adapter.json` lists, and the example's `run.py` have the SHA-256 pinned below: for the stage
  1 to 4 files the values of job 7575617's manifest (`SOURCES.sha256` `0c4e5c9c...`, 822 files), for the example and its test the values
  of the D3 stage 5 job's manifest. One changed byte in any of them makes this test fail, until a new job of record runs the changed
  files and the pins and the record are renewed. Exempt: this module and the records it reads (`adapter.json`, `VALIDATION.md`,
  `docs/capability-matrix.md`, `t09-closeout.md`). A file declared later without a pin fails too.
- The VALIDATION table's test counts equal the test methods each declared module defines now; the two modules of this stage are named
  as the D3 stage 5 job's.
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
STAGE5_JOB = "the D3 stage 5 job"
STAGE4_CHAIN = ("7575617", "7576269", "7576270")
# The tool's tested versions, as job 7575617's receipt prints them ("Python 3.13.18", "numpy 2.4.6 scipy 1.17.1").
TOOL_VERSIONS = (("Python 3.13.18", "NumPy 2.4.6", "SciPy 1.17.1"),)
# The SHA-256 of each declared test module and adapter.json asset, and of the example's run.py (paths from the plugin root): the stage 1
# to 4 files as job 7575617's manifest (SOURCES.sha256 0c4e5c9c...) has them, the example and its test as the D3 stage 5 job's manifest.
JOB_OF_RECORD_PINS: dict = {
    "adapters/photon-likelihood/assets/fixture_tools/t09_fixed_points.py": "652af9311ec9ef51c1a7d2da715180e134264314b715b3b86efde48170ee1081",
    "adapters/photon-likelihood/assets/fixture_tools/t09_fixture_files.py": "20640f670329b249c3f81317976f8e5ddaeea9957f7c2a7d50c88359d184f4ed",
    "adapters/photon-likelihood/assets/fixture_tools/t09_independent_likelihood.py": "a12edcb26f754828012b90c69522545fe4cddae3a21f84d0454bc0aca2d18216",
    "adapters/photon-likelihood/assets/fixture_tools/t09_job_lines.py": "13137fc321379c7aa3507ba81a9ae41a9f4b18266ff093aff973c24347faebdd",
    "adapters/photon-likelihood/assets/fixture_tools/t09_readings.py": "beefb0076e7098a25ab1cd8bc2164fb7476601c4e6cc0a397c9357d3b0246355",
    "adapters/photon-likelihood/assets/fixture_tools/t09_topology_readings.py": "762d272ca05ea7c80a133731406e733d45f209c67cc241c01785ec1796fc7c4c",
    "adapters/photon-likelihood/assets/fixture_tools/t09_truth_start.py": "6e49246bcd02d6a2931a0360c5b95cec1639f706ba694767485ba2b2689f275e",
    "adapters/photon-likelihood/assets/light_recipe/__init__.py": "9d16d3ba5ba96a7c0bb2a919b2b9db9ce48020e3f4ef0ccafd358472ac3dbe60",
    "adapters/photon-likelihood/assets/light_recipe/arrival_response.py": "fcbb347d6bb3c04e366a0f28cd0a6f95749ffe71213ab25898d370a170feb14a",
    "adapters/photon-likelihood/assets/light_recipe/charge_response.py": "d619b7411ec8b70c24074d2a6fe9ab98c0ab404f4469f70b6f9bbcc5d4d4cda8",
    "adapters/photon-likelihood/assets/light_recipe/configuration.py": "949aef67168e9051ce85dfb342181e974d9c95e524670bcd65410ce9244e13c3",
    "adapters/photon-likelihood/assets/light_recipe/fit.py": "30d92e448e461084556364e4d2fd4e036c69142dc88b91f08dbf8acfff71a476",
    "adapters/photon-likelihood/assets/light_recipe/joint.py": "aa67f3c5d35f5eac7f7cf5ec4522fb7379ce705822c3ef61e4d80b89e324806e",
    "adapters/photon-likelihood/assets/light_recipe/light_model.py": "c716d4fccb73b75a711033f8cd45f2fbe9640e4483e3339fa74064fc2814552b",
    "adapters/photon-likelihood/assets/light_recipe/likelihood.py": "1e839b9dbbbe04e5867547b3eb8d86b6cbaef06a2ba2025d41d9acb580e1a084",
    "adapters/photon-likelihood/assets/light_recipe/multistart.py": "5953620f7aa3b3b886b67e440a4b1235f983b2c6dc663e03aaed2ce862461449",
    "adapters/photon-likelihood/assets/light_recipe/product.py": "a19d99ca19e680509c231f2696b210782c5d9d57939c41539a1dcd824e17e79f",
    "adapters/photon-likelihood/assets/light_recipe/readout.py": "605debd51cb66dc266e16b56be08df7ef28479df577476d2ad531ea805d205ce",
    "adapters/photon-likelihood/assets/light_recipe/topology.py": "79dc45a9b800936dd3f8288ffbca040fa6ed0487eb38da55d290be8ee8ae802e",
    "adapters/photon-likelihood/assets/photon_likelihood.py": "801f0d3037b123ef495288aaf5426b80dadb397e420d86257bd492e09039aac1",
    "adapters/photon-likelihood/assets/t09-multistart-1.budget.json": "70220b7ddf1679d01d4a9c5397d1fdf124c6f0bd8ed4dca562d9c18e04180307",
    "adapters/photon-likelihood/assets/t09-sphere-1.configuration.json": "ce4f430756f8ea0be1ab1b08eb638f9c38bf305968aa2d6d4e743d5fc68a1508",
    "adapters/photon-likelihood/assets/t09-topology-2.budget.json": "104262a1bfb0f5403a075884d9acd5f5ccbf1fc012d5237b578297f4d98ed7df",
    "examples/reconstruction-photon-likelihood/run.py": "4bc69a2ca5431d3b6bad39bc1d8cea71c15eab743a53840676fb8e50d462c6d5",
    "tests/adapters/test_photon_likelihood.py": "4a84003147fa7ad2b3e41b9ebb32ce4dcf2a2a9b40b67426ca3928b31f7b2472",
    "tests/adapters/test_photon_likelihood_multistart.py": "f77444ede6b99af7ab05337e2d0e5c5d1c7a342c69cb3d29b7279bce9f3da214",
    "tests/adapters/test_photon_likelihood_time.py": "a28fc7c4d17dbc95bcb24838f5cb808402c361fd6f926113d1cc877bdbd05636",
    "tests/adapters/test_photon_likelihood_topology.py": "9c30bccbb4782e56232053d271df7fbec5192bd5d6d38199bd74cc45f988a746",
    "tests/examples/test_reconstruction_photon_likelihood.py": "9ded9bc715547308779fc9c7f3d82edf01d42992aad2772b42c83edf24bf0466",
}
SHEET_PARTS = ("Background / Objective", "Scope", "Non-goals", "Existing work checked", "Files", "Input", "Likelihood", "Interfaces",
               "Steps", "Acceptance", "Open item", "Stop")
# Rows the D3 stage 5 brief names, by a phrase of their label, and the status the rules give them.
NAMED_ROWS = {
    "native backend": "gap",                              # U12 A: the user's decision, recorded as a gap in required delivery (K02)
    "original method sources": "open",                    # source-unverified without network approval
    "quality per": "open",                                # K09 at Freeze B
    "negative checks": "open",                            # v4 9.4's two negative checks, not built
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
    found = re.findall(rf"job\s+of\s+record\s+for\s+adapter\s+{re.escape(version)}:\s+(?:job\s+(\d+),\s+)?the\s+D3\s+stage\s+5\s+job",
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

    def test_every_record_names_the_stage_4_chain_as_the_latest_run_before_it(self):
        for name, text in self.records().items():
            with self.subTest(record=name):
                for job in STAGE4_CHAIN:
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
                if module in (THIS_MODULE, EXAMPLE_TEST) and pending:   # the stage 5 job's modules, until its ID is written (review M4)
                    self.assertRegex(section, rf"\| `{re.escape(module)}`[^\n]*{re.escape(STAGE5_JOB)}")
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
        self.assertIn("`source-unverified`", sources["Evidence"])   # the evidence states the sources' state, not only the label
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
                digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                self.assertEqual(digest, JOB_OF_RECORD_PINS[path], f"{path} differs from the bytes the job of record ran")

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
