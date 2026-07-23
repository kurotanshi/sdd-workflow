from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import (  # noqa: E402
    TaskScanResult,
    detect_schema_version,
    parse_with_schema,
    scan_tasks,
    VALID_V2_CHANGE_TYPES,
)


FIXTURES = ROOT / "tests/fixtures/baseline"
MANIFEST = json.loads((FIXTURES / "MANIFEST.json").read_text())


def parse_fixture(fixture: dict[str, object]):
    fixture_path = FIXTURES / str(fixture["path"])
    input_values = fixture["input"]
    assert isinstance(input_values, dict)
    return parse_with_schema(
        short_name=str(fixture["name"]),
        proposal_text=(fixture_path / "proposal.md").read_text(),
        task_scan=scan_tasks(
            (fixture_path / "tasks.md").read_text(),
            path=f"{fixture['path']}/tasks.md",
        ),
        explicit_schema_version=input_values["explicit_schema_version"],
        proposal_path=f"{fixture['path']}/proposal.md",
    )


class ParserFixtureTests(unittest.TestCase):
    def test_manifest_baseline_and_rule_references_are_valid(self) -> None:
        self.assertEqual(MANIFEST["manifest_version"], 1)
        self.assertEqual(MANIFEST["baseline"]["release_tag"], "v0.2.3")
        self.assertEqual(
            MANIFEST["baseline"]["commit"],
            "5facfaca4c1e339d69fb2c14ac26c33062c5596f",
        )
        rules = (FIXTURES / "NORMATIVE_RULES.md").read_text()
        names: set[str] = set()
        for fixture in MANIFEST["fixtures"]:
            self.assertNotIn(fixture["name"], names)
            names.add(fixture["name"])
            for rule in fixture["source_rules"]:
                self.assertIn(f"`{rule}`", rules)

    def test_all_parser_fixtures_match_manifest(self) -> None:
        for fixture in MANIFEST["fixtures"]:
            if fixture["category"] == "discovery":
                continue
            with self.subTest(fixture=fixture["name"]):
                outcome = parse_fixture(fixture)
                expected = fixture["expected"]
                self.assertEqual(outcome.adapter, expected["adapter"])
                self.assertEqual(outcome.readable, expected["readable"])
                self.assertEqual(outcome.mutation_safe, expected["mutation_safe"])
                self.assertEqual(
                    [item.code for item in outcome.diagnostics],
                    expected["diagnostic_codes"],
                )
                if outcome.model is None:
                    continue
                if "schema_version" in expected:
                    self.assertEqual(outcome.model.schema_version, expected["schema_version"])
                if "status" in expected:
                    self.assertEqual(outcome.model.status, expected["status"])
                if "change_type" in expected:
                    self.assertEqual(outcome.model.change_type, expected["change_type"])
                if "task_count" in expected:
                    self.assertEqual(len(outcome.model.tasks), expected["task_count"])
                if "completed_count" in expected:
                    self.assertEqual(
                        sum(item.completed for item in outcome.model.tasks),
                        expected["completed_count"],
                    )
                if "acceptance_condition_count" in expected:
                    self.assertEqual(
                        len(outcome.model.acceptance_conditions),
                        expected["acceptance_condition_count"],
                    )
                if "task_counts_reliable" in expected:
                    self.assertEqual(
                        outcome.task_counts_reliable,
                        expected["task_counts_reliable"],
                    )
                if "abandonment_readable" in expected:
                    self.assertEqual(
                        outcome.abandonment_readable,
                        expected["abandonment_readable"],
                    )

    def test_repeated_input_has_identical_model_and_diagnostics(self) -> None:
        for fixture in MANIFEST["fixtures"]:
            if fixture["category"] == "discovery":
                continue
            with self.subTest(fixture=fixture["name"]):
                documents = {
                    json.dumps(
                        parse_fixture(fixture).to_dict(),
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    for _ in range(10)
                }
                self.assertEqual(len(documents), 1)

    def test_separate_processes_emit_identical_fixture_bytes(self) -> None:
        command = [sys.executable, str(ROOT / "tests/dump_fixture_models.py")]
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        first = subprocess.check_output(command, cwd=ROOT, env=environment)
        second = subprocess.check_output(command, cwd=ROOT, env=environment)
        self.assertEqual(first, second)
        self.assertIsInstance(json.loads(first), dict)

    def test_unknown_schema_is_rejected_before_markdown_or_tasks_are_read(self) -> None:
        class MustNotBeRead:
            def splitlines(self):
                raise AssertionError("unknown schema reached Markdown parsing")

        outcome = parse_with_schema(
            short_name="future-schema",
            proposal_text=MustNotBeRead(),
            task_scan=None,
            explicit_schema_version=99,
        )
        self.assertFalse(outcome.readable)
        self.assertIsNone(outcome.model)
        self.assertEqual(
            [item.code for item in outcome.diagnostics],
            ["ERROR_UNSUPPORTED_SCHEMA_VERSION"],
        )

    def test_unversioned_legacy_falls_back_but_explicit_v1_does_not(self) -> None:
        fixture = next(
            item for item in MANIFEST["fixtures"] if item["name"] == "legacy-statusless"
        )
        unversioned = parse_fixture(fixture)
        fixture_path = FIXTURES / "legacy-statusless"
        explicit = parse_with_schema(
            short_name="legacy-statusless",
            proposal_text=(fixture_path / "proposal.md").read_text(),
            task_scan=scan_tasks((fixture_path / "tasks.md").read_text()),
            explicit_schema_version=1,
        )
        self.assertEqual(unversioned.adapter, "legacy")
        self.assertEqual(
            unversioned.mutation_block_code,
            "ERROR_LEGACY_MUTATION_UNSUPPORTED",
        )
        self.assertEqual(explicit.adapter, "v1")
        self.assertEqual(
            [item.code for item in explicit.diagnostics],
            ["ERROR_REQUIRED_SECTION_MISSING"],
        )

    def test_schema_detection_rejects_non_integer_and_future_values(self) -> None:
        self.assertFalse(detect_schema_version(True).supported)
        self.assertFalse(detect_schema_version("1").supported)
        self.assertTrue(detect_schema_version(2).supported)
        self.assertFalse(detect_schema_version(3).supported)

    def test_minimal_frontmatter_v2_uses_shared_canonical_model(self) -> None:
        proposal = (FIXTURES / "valid-simple/proposal.md").read_text()
        tasks = (FIXTURES / "valid-simple/tasks.md").read_text()
        outcome = parse_with_schema(
            short_name="valid-simple",
            proposal_text="---\nschema_version: 2\n---\n" + proposal,
            task_scan=scan_tasks(tasks),
        )
        self.assertEqual(outcome.adapter, "v2")
        self.assertTrue(outcome.mutation_safe)
        self.assertEqual(outcome.model.schema_version, 2)  # type: ignore[union-attr]
        self.assertEqual(
            outcome.model.extensions[0].to_dict(),  # type: ignore[union-attr]
            {
                "namespace": "sdd.schema",
                "value": {"schema_version": 2},
                "approval_relevance": "relevant",
            },
        )

    def test_frontmatter_metadata_errors_fail_before_task_use(self) -> None:
        class MustNotBeRead:
            @property
            def diagnostics(self):
                raise AssertionError("invalid schema metadata reached task parsing")

        for text, code in (
            ("---\nschema_version: 3\n---\n# future", "ERROR_UNSUPPORTED_SCHEMA_VERSION"),
            ("---\nunknown: 2\n---\n# unknown", "ERROR_UNKNOWN_SCHEMA_FIELD"),
            ("---\nschema_version: '2'\n---\n# invalid", "ERROR_INVALID_SCHEMA_METADATA"),
        ):
            with self.subTest(code=code):
                outcome = parse_with_schema(
                    short_name="invalid-schema",
                    proposal_text=text,
                    task_scan=MustNotBeRead(),
                )
                self.assertFalse(outcome.readable)
                self.assertEqual(outcome.diagnostics[0].code, code)

    def test_v2_accepts_six_primary_types_without_lifecycle_changes(self) -> None:
        proposal = (FIXTURES / "valid-simple/proposal.md").read_text()
        tasks = (FIXTURES / "valid-simple/tasks.md").read_text()
        self.assertEqual(
            VALID_V2_CHANGE_TYPES,
            {"新功能", "修 bug", "重構", "維運", "文件", "研究"},
        )
        for change_type in VALID_V2_CHANGE_TYPES - {"研究"}:
            with self.subTest(change_type=change_type):
                typed = proposal.replace("新功能", change_type, 1)
                outcome = parse_with_schema(
                    short_name="typed-v2",
                    proposal_text="---\nschema_version: 2\n---\n" + typed,
                    task_scan=scan_tasks(tasks),
                )
                self.assertTrue(outcome.mutation_safe, outcome.diagnostics)
                self.assertEqual(outcome.model.change_type, change_type)  # type: ignore[union-attr]

    def test_research_conclusion_is_canonical_but_not_approval_relevant(self) -> None:
        proposal = (FIXTURES / "valid-simple/proposal.md").read_text()
        proposal = proposal.replace("新功能", "研究", 1) + "\n## 結論\n- observed answer\n"
        tasks = (FIXTURES / "valid-simple/tasks.md").read_text()
        outcome = parse_with_schema(
            short_name="research-v2",
            proposal_text="---\nschema_version: 2\n---\n" + proposal,
            task_scan=scan_tasks(tasks),
        )
        self.assertTrue(outcome.mutation_safe, outcome.diagnostics)
        conclusion = next(
            section for section in outcome.model.sections if section.key == "conclusion"  # type: ignore[union-attr]
        )
        self.assertEqual(conclusion.semantic_items, ("observed answer",))
        extension = next(
            item
            for item in outcome.model.extensions  # type: ignore[union-attr]
            if item.namespace == "sdd.research.conclusion"
        )
        self.assertEqual(extension.approval_relevance.value, "excluded")

        completed = proposal.replace("draft", "completed", 1).replace(
            "- observed answer", ""
        )
        invalid = parse_with_schema(
            short_name="research-v2",
            proposal_text="---\nschema_version: 2\n---\n" + completed,
            task_scan=scan_tasks(tasks),
        )
        self.assertIn(
            "ERROR_RESEARCH_CONCLUSION_REQUIRED",
            [item.code for item in invalid.diagnostics],
        )

    def test_ambiguous_fixture_has_only_two_complete_active_candidates(self) -> None:
        workspace = FIXTURES / "ambiguous-active/sdd"
        candidates = sorted(
            path.name
            for path in workspace.iterdir()
            if path.name != "archive"
            and (path / "proposal.md").is_file()
            and (path / "tasks.md").is_file()
        )
        fixture = next(
            item for item in MANIFEST["fixtures"] if item["name"] == "ambiguous-active"
        )
        self.assertEqual(candidates, fixture["expected"]["candidate_names"])


if __name__ == "__main__":
    unittest.main()
