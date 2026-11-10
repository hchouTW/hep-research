"""adapters/calo-cluster, D2 stage 5 of T08: the adapter's records agree with one another and claim no more than the jobs ran.

It reads files only; no recipe, fixture or job runs here. The records are:
- `adapters/calo-cluster/adapter.json`: version, status, each tool's status and tested versions, environment, status rule;
- the `VALIDATION.md` section CALO-CLUSTER-T08: the run of record (docs/adapter-authoring.md, "Changing an adapter");
- the `adapters/calo-cluster` row of `docs/capability-matrix.md` (docs/adapter-authoring.md, Honesty rules);
- `docs/dev/detector-reconstruction/t08-closeout.md`: T08 against its sheet, one status per row, and its summary.

What is checked:
- The adapter claims `demonstrated-on-synthetic-data` for every tool and for itself, and no higher: its jobs ran on the synthetic
  fixture t08-grid/1 and on the labelled simulated-unvalidated zdcsim input, against an independent coding of the same definition
  and the plugin's own earlier outputs, with no reference output from outside the plugin.
- The tested versions are the ones the job of record logged, and the VALIDATION section states each of them.
- adapter.json, the VALIDATION section, the matrix row and the close-out name one and the same job of record for the declared version.
- Every declared test module and every asset `adapter.json` lists has the SHA-256 that job 7557963's manifest (`SOURCES.sha256`
  `c176ffb4...`, 820 files) gives it, pinned below. One changed byte in any of them makes this test fail, until a new job of record
  runs the changed files and the pins and the record are renewed. Exempt: this module (it ran in no job, and the section says so) and the
  records it reads (`adapter.json`, `VALIDATION.md`, `docs/capability-matrix.md`, `t08-closeout.md`, `t08-scenarios.md`), which this
  stage changes. A file declared later without a pin fails too.
- The VALIDATION table's test counts equal the test methods each declared module defines now.
- The close-out's statuses are the four status words, every row not met says what would close it, its summary counts are its
  rows' counts, and its scenario statuses are those of `t08-scenarios.md`.
- No absolute host path in these records.

Run from the plugin root: python -m unittest tests.adapters.test_calo_records -v
"""
from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters" / "calo-cluster"
RECORDS = ROOT / "docs" / "dev" / "detector-reconstruction"
CLOSEOUT = RECORDS / "t08-closeout.md"
SCENARIOS = RECORDS / "t08-scenarios.md"
SECTION_NAME = "CALO-CLUSTER-T08"
CLAIM = "demonstrated-on-synthetic-data"
FIRST_VERSION = "0.1.0"  # the undeclared development version of stages 1 to 4, status proposed
STATUS_WORDS = ("met", "met with readings", "open", "gap")
HOST_PATH = re.compile(r"/ceph|/var/tmp|/tmp/|/dicos|/home/|/sharedfs")
THIS_MODULE = "tests/adapters/test_calo_records.py"
# Each tool's tested versions, as job 7557963's receipt and build log print them (receipt: "Python 3.13.18", "numpy 2.4.6 scipy 1.17.1",
# the reduce environment's pip freeze and sys.version; zdcsim-build.log: "geant4-config ... version 11.4.3", "g++ (GCC) 11.5.0").
TOOL_VERSIONS = (
    ("Python 3.13.18", "NumPy 2.4.6", "SciPy 1.17.1"),
    ("uproot 5.7.7", "awkward 2.14.0", "NumPy 2.5.4", "Python 3.13.2", "Geant4 11.4.3", "GCC 11.5.0"),
)
# The SHA-256 of each declared test module and adapter.json asset in job 7557963's manifest (SOURCES.sha256 c176ffb4..., paths from the
# plugin root). D2 stage 5 fix round 1 (review M4): the job of record ran these bytes; the records claim no change since.
JOB_OF_RECORD_PINS = {
    "adapters/calo-cluster/assets/calo_cluster.py": "31b362e5dd84e889363a4f6c63475cb7e01af4d7722cd600a132ac36c9b19ec9",
    "adapters/calo-cluster/assets/calo_recipe/__init__.py": "a0e23ddcfa478f2fa3922c554f1b2448f721faf4d8a0261ed26ed9f41941e683",
    "adapters/calo-cluster/assets/calo_recipe/cell_chain.py": "7a7c7ee5a1b713aa3de08ae9af4c3dbfcd3bec66748e78fc5cb924adeeccbc5d",
    "adapters/calo-cluster/assets/calo_recipe/cell_input.py": "b09a2e9c541682790dfa0ec9d344d10e680d3480671f4c9c6d3fd1ad8facf768",
    "adapters/calo-cluster/assets/calo_recipe/clustering.py": "f59c804245d7e7295878fa5276438e3165f8c099d84ec4f80554d46883b066d5",
    "adapters/calo-cluster/assets/calo_recipe/configuration.py": "5e28a4b67f6ebc90faf2d12431a5c7d5dfecdfc39e2f0267063395b782af68ec",
    "adapters/calo-cluster/assets/calo_recipe/gain_payload.py": "3ef05a562096e3530c04adeaedb57874958a8e35d49df3d12f8e38dc8169bea1",
    "adapters/calo-cluster/assets/calo_recipe/product.py": "73c2414c0cde4f56e77fb42df6a4b9abdf652dd004154beedd10f90871e78f69",
    "adapters/calo-cluster/assets/calo_recipe/profile.py": "a732993a4065d3922d70822f7444aaaf4b69921624fa858e3d37ca60d099d3b1",
    "adapters/calo-cluster/assets/calo_recipe/recalibration.py": "a3a73ed578c6e6bf81043568d49fb9f708d0e436cb175d84cbfdefda7e321fc1",
    "adapters/calo-cluster/assets/fixture_tools/t08_cai.py": "5fa071d8a9f4392d03704913b353783d04b9f6e84191134438e6f77643e3e225",
    "adapters/calo-cluster/assets/fixture_tools/t08_fixture_files.py": "11b46c1b0db7a6e7e77d6f2dbe88e48cc264f18cd47bd64c22f09225801fbaff",
    "adapters/calo-cluster/assets/fixture_tools/t08_readings.py": "3628b64464cdf8470b967fc84b3a08894c8b0a4d971cb0b6ed5bd7f57e6e31df",
    "adapters/calo-cluster/assets/fixture_tools/t08_scenarios.py": "497a04256d6f21c4e70cdfaec9a0f9dcfdeedcfe979f8934ef74d79536605dc4",
    "adapters/calo-cluster/assets/fixture_tools/t08_zdcsim_cells.py": "0f6dfa3ca4a80948c0941154c4f9d38ce63dfdd8e30e9ad63ff1b351912243dd",
    "adapters/calo-cluster/assets/t08-grid-1.configuration.json": "5fbbea3b4ca81d962c5ca70fa024ddc82dd6e1d2f06e39b354fda56d26483723",
    "adapters/calo-cluster/assets/zdcsim-prototype-v2.configuration.json": "b82b08db784151d4754bb5b53b1bdeae5c1b67c036cd755447475a25ec2f9e1f",
    "tests/adapters/test_calo_cai.py": "f1c4e9061065f902f0ff6f845431a1453e48068b422598d215a3361ebdf5e67f",
    "tests/adapters/test_calo_cluster.py": "a0dd3fecea69b5e55159c67b84ab74e5004936cd284733aa1423724b4daec5f1",
    "tests/adapters/test_calo_scenarios.py": "78ccdc815727a1dd4b0139e404db8833651b8ea092363f09ee09c0e85ce83490",
    "tests/adapters/test_calo_zdcsim.py": "66088e8fc43dffee9cbd60b163d8ba50bab7d31f38d9ac579df292319eb2c8c8",
    "tests/adapters/test_calo_zdcsim_root.py": "853eafe49bbe4710ad9c8f85c67aecae28a5ea9785bd9b3c806cb05e37c99f6d",
    "tests/examples/test_reconstruction_calorimetry.py": "e74afeec904b505b9bde5b6bf0fd1e5e95a19368730a962f285c93fd2232bd62",
}
SHEET_PARTS = ("Background / Objective", "Scope", "Non-goals", "Files", "Input", "Interfaces", "Steps", "Acceptance", "Open item", "Stop")


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
    return next(line for line in matrix.splitlines() if line.startswith("| `adapters/calo-cluster`"))


def jobs_of_record(text: str, version: str) -> list:
    return re.findall(rf"job\s+of\s+record\s+for\s+adapter\s+{re.escape(version)}:\s+job\s+(\d+)", text, flags=re.IGNORECASE)


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


class AdapterClaim(unittest.TestCase):
    def test_every_tool_and_the_adapter_claim_demonstrated_on_synthetic_data(self):
        record = declaration()
        self.assertEqual(record["status"], CLAIM)
        self.assertEqual([tool["status"] for tool in record["tools"]], [CLAIM] * len(TOOL_VERSIONS))
        self.assertRegex(record["version"], r"^\d+\.\d+\.\d+$")
        self.assertNotEqual(record["version"], FIRST_VERSION, "the first recorded status is a change of the adapter: bump its version")

    def test_the_status_rule_names_the_claim_and_the_label_not_taken(self):
        rule = declaration()["status_rule"]
        self.assertTrue(rule.split(";")[1].strip().startswith(f"{CLAIM}:"), rule)
        self.assertIn("not tested-in-declared-environment", rule)
        self.assertIn("simulated-unvalidated", rule)

    def test_each_tool_lists_the_versions_the_job_of_record_logged(self):
        record, section = declaration(), validation_section()
        for tool, words in zip(record["tools"], TOOL_VERSIONS):
            with self.subTest(tool=tool["name"]):
                self.assertTrue(tool["tested_versions"])
                listed = " ".join(tool["tested_versions"])
                for word in words:
                    self.assertIn(word, listed)
                    self.assertIn(word, section)

    def test_the_declared_tests_include_the_example_and_this_module(self):
        tests = declaration()["tests"]
        self.assertIn("../../" + THIS_MODULE, tests)
        self.assertIn("../../tests/examples/test_reconstruction_calorimetry.py", tests)


class JobOfRecord(unittest.TestCase):
    def test_every_record_names_one_and_the_same_job_of_record(self):
        record = declaration()
        version = record["version"]
        named = {
            "adapter.json": jobs_of_record(record["environment"] + " " + record["status_rule"], version),
            "VALIDATION.md": jobs_of_record(validation_section(), version),
            "capability-matrix.md": jobs_of_record(matrix_row(), version),
            "t08-closeout.md": jobs_of_record(CLOSEOUT.read_text(encoding="utf-8"), version),
        }
        for name, jobs in named.items():
            with self.subTest(record=name):
                self.assertTrue(jobs, f"{name} names no job of record for adapter {version}")
        self.assertEqual(len({job for jobs in named.values() for job in jobs}), 1, named)

    def test_the_section_is_the_declared_version_s_first_record(self):
        section = validation_section()
        self.assertIn(f"Adapter {declaration()['version']} ", section)
        self.assertIn(CLAIM, section)
        for word in ("Date", "Commit", "Environment", "Command", "Result"):
            self.assertIn(f"**{word}.**", section)

    def test_the_section_s_test_counts_are_the_modules_as_they_are_now(self):
        section = validation_section()
        declared = [listed[len("../../"):] for listed in declaration()["tests"]]
        for module in declared:
            with self.subTest(module=module):
                if module == THIS_MODULE:
                    self.assertRegex(section, rf"`{re.escape(module)}`[^\n]*in no job")
                    continue
                found = re.search(rf"\| `{re.escape(module)}`[^|]*\| (\d+) run, OK", section)
                self.assertIsNotNone(found, f"the section has no result row for {module}")
                self.assertEqual(int(found.group(1)), method_count(ROOT / module), f"{module} changed after the job of record")


class MatrixRow(unittest.TestCase):
    def test_the_row_states_the_claim_the_version_and_the_section(self):
        row, record = matrix_row(), declaration()
        self.assertIn(f"| {record['status']} |", row)
        self.assertIn(f"adapter {record['version']}", row)
        self.assertIn(f"VALIDATION {SECTION_NAME}", row)
        for stale in ("| proposed |", "no job of record", "not recorded in `VALIDATION.md`", "so no tested version"):
            self.assertNotIn(stale, row)


class CloseOut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = CLOSEOUT.read_text(encoding="utf-8")
        cls.sheet = tables_under(cls.text, "## Sheet items")
        cls.scenarios = tables_under(cls.text, "## Scenarios")

    def statused(self) -> list:
        return [row for row in self.sheet + self.scenarios if row.get("Status", "")]

    def test_every_status_is_a_status_word_and_every_row_not_met_says_what_closes_it(self):
        self.assertTrue(self.sheet and self.scenarios)
        for row in self.sheet + self.scenarios:
            label = next(iter(row.values()))
            status = row.get("Status", "")
            with self.subTest(row=label[:60]):
                if not status:
                    self.assertIn("scenario table", " ".join(row.values()))
                    continue
                self.assertIn(status, STATUS_WORDS)
                evidence = " ".join(value for key, value in row.items() if "evidence" in key.lower())
                self.assertTrue(evidence.strip(), "a row with a status cites its evidence")
                closing = list(row.values())[-1]
                if status != "met":
                    self.assertTrue(closing.strip(), "a row not met says why, and what would close it")

    def test_the_summary_counts_the_rows(self):
        summary = {row["Status"]: int(re.match(r"\d+", row["Rows"]).group(0)) for row in tables_under(self.text, "## Summary")}
        counted = {word: 0 for word in STATUS_WORDS}
        for row in self.statused():
            counted[row["Status"]] += 1
        self.assertEqual(summary, counted)

    def test_every_part_of_the_sheet_has_a_row(self):
        labels = [next(iter(row.values())) for row in self.sheet]
        for part in SHEET_PARTS:
            with self.subTest(part=part):
                self.assertTrue(any(label.startswith(part) for label in labels), part)
        stops = [label for label in labels if label.startswith("Stop")]
        self.assertEqual(len(stops), 2, stops)
        for stage in range(1, 6):
            with self.subTest(failing_first_stage=stage):
                self.assertTrue(any(label.startswith("Steps, failing check first") and f"stage {stage}" in label for label in labels))

    def test_the_scenario_statuses_are_those_of_the_scenario_file(self):
        own = {row["Scenario"]: row["Status"] for row in self.scenarios}
        theirs = {row["Scenario"]: row["Status"] for row in tables_under(SCENARIOS.read_text(encoding="utf-8"), "## Scenarios")}
        self.assertEqual(sorted(own), ["A15", "A32", "A38"])
        for scenario, status in own.items():
            with self.subTest(scenario=scenario):
                self.assertRegex(theirs[scenario], rf"^{re.escape(status)}\b(?! with)")

    def test_the_close_out_states_the_adapter_record(self):
        record = declaration()
        self.assertIn(f"adapter {record['version']}", self.text)
        self.assertIn(f"`{record['status']}`", self.text)


class CodeAsTheJobOfRecordRanIt(unittest.TestCase):
    def test_every_declared_module_and_asset_has_the_bytes_job_7557963_ran(self):
        record = declaration()
        declared = ["adapters/calo-cluster/" + asset for asset in record["assets"]]
        declared += [listed[len("../../"):] for listed in record["tests"] if listed != "../../" + THIS_MODULE]
        for path in declared:
            with self.subTest(path=path):
                self.assertIn(path, JOB_OF_RECORD_PINS, f"{path} is declared but has no pin from the job of record")
                digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                self.assertEqual(digest, JOB_OF_RECORD_PINS[path], f"{path} differs from the bytes job 7557963 ran")

    def test_no_pin_is_left_for_a_file_no_longer_declared(self):
        record = declaration()
        declared = {"adapters/calo-cluster/" + asset for asset in record["assets"]}
        declared |= {listed[len("../../"):] for listed in record["tests"]}
        self.assertEqual(sorted(set(JOB_OF_RECORD_PINS) - declared), [])


class NoHostPath(unittest.TestCase):
    def test_no_record_holds_an_absolute_host_path(self):
        record = declaration()
        texts = {
            "adapter.json": json.dumps(record),
            "VALIDATION.md": validation_section(),
            "capability-matrix.md": matrix_row(),
            "t08-closeout.md": CLOSEOUT.read_text(encoding="utf-8"),
        }
        for name, text in texts.items():
            with self.subTest(record=name):
                self.assertIsNone(HOST_PATH.search(text), name)

    def test_the_pattern_finds_a_host_path(self):
        self.assertIsNotNone(HOST_PATH.search("built in /var/tmp/hdr-user/"))
        self.assertIsNone(HOST_PATH.search("<workdir>/env/py313"))


if __name__ == "__main__":
    unittest.main()
