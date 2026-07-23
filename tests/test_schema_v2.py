from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import parse_with_schema, scan_tasks  # noqa: E402
from sdd_core.cli import main  # noqa: E402


FIXTURES = ROOT / "tests/fixtures/schema-v2"
MANIFEST = json.loads((FIXTURES / "MANIFEST.json").read_text(encoding="utf-8"))


def parse_path(path: Path):
    return parse_with_schema(
        short_name=path.name,
        proposal_text=(path / "proposal.md").read_text(encoding="utf-8"),
        task_scan=scan_tasks((path / "tasks.md").read_text(encoding="utf-8")),
    )


def conclusion_items(outcome) -> list[str] | None:
    if outcome.model is None:
        return None
    for extension in outcome.model.extensions:
        if extension.namespace == "sdd.research.conclusion":
            return extension.value["items"]
    return None


class SchemaV2FixtureTests(unittest.TestCase):
    def test_manifest_cases_match_deterministic_outcomes(self) -> None:
        self.assertEqual(MANIFEST["schema_version"], 2)
        for fixture in MANIFEST["fixtures"]:
            if fixture["name"] == "six-primary-types":
                continue
            with self.subTest(fixture=fixture["name"]):
                outcome = parse_path(FIXTURES / fixture["path"])
                expected = fixture["expected"]
                if "adapter" in expected:
                    self.assertEqual(outcome.adapter, expected["adapter"])
                if "readable" in expected:
                    self.assertEqual(outcome.readable, expected["readable"])
                if "mutation_safe" in expected:
                    self.assertEqual(outcome.mutation_safe, expected["mutation_safe"])
                if "status" in expected:
                    self.assertEqual(outcome.model.status, expected["status"])
                if "change_type" in expected:
                    self.assertEqual(outcome.model.change_type, expected["change_type"])
                if "conclusion" in expected:
                    self.assertEqual(conclusion_items(outcome), expected["conclusion"])
                if "diagnostic_codes" in expected:
                    self.assertEqual(
                        [item.code for item in outcome.diagnostics],
                        expected["diagnostic_codes"],
                    )

    def test_every_primary_type_has_a_fixture_projection(self) -> None:
        matrix = next(
            item for item in MANIFEST["fixtures"] if item["name"] == "six-primary-types"
        )
        proposal = (FIXTURES / matrix["path"] / "proposal.md").read_text(encoding="utf-8")
        tasks = (FIXTURES / matrix["path"] / "tasks.md").read_text(encoding="utf-8")
        observed: set[str] = set()
        for change_type in matrix["change_types"]:
            outcome = parse_with_schema(
                short_name="typed-v2",
                proposal_text=proposal.replace("新功能", change_type, 1),
                task_scan=scan_tasks(tasks),
            )
            self.assertTrue(outcome.mutation_safe, outcome.diagnostics)
            observed.add(outcome.model.change_type)
        research = parse_path(FIXTURES / matrix["research_path"])
        self.assertTrue(research.mutation_safe, research.diagnostics)
        observed.add(research.model.change_type)
        self.assertEqual(observed, {"新功能", "修 bug", "重構", "維運", "文件", "研究"})

    def test_v1_legacy_and_v2_share_transaction_inputs(self) -> None:
        v1 = parse_path(ROOT / "tests/fixtures/baseline/valid-simple")
        legacy = parse_path(ROOT / "tests/fixtures/baseline/legacy-statusless")
        v2 = parse_path(FIXTURES / "minimal-v2")
        for outcome in (v1, legacy, v2):
            self.assertIsNotNone(outcome.model)
            self.assertTrue(hasattr(outcome.model, "status"))
            self.assertTrue(hasattr(outcome.model, "tasks"))
            self.assertTrue(hasattr(outcome.model, "acceptance_conditions"))
        self.assertEqual(type(v1.model), type(legacy.model))
        self.assertEqual(type(v1.model), type(v2.model))

    def test_public_status_reads_actual_v2_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/minimal-v2"
            target.parent.mkdir(parents=True)
            shutil.copytree(FIXTURES / "minimal-v2", target)
            import io

            stdout = io.StringIO()
            code = main(
                ["--root", str(root), "--json", "status", "minimal-v2"],
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=root,
            )
            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 0, result)
            self.assertEqual(result["data"]["adapter"], "v2")
            self.assertEqual(result["data"]["change_type"], "新功能")

    def test_public_status_rejects_future_schema_before_task_decode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/future-version"
            target.parent.mkdir(parents=True)
            shutil.copytree(FIXTURES / "future-version", target)
            (target / "tasks.md").write_bytes(b"\xff")
            import io

            stdout = io.StringIO()
            code = main(
                ["--root", str(root), "--json", "status", "future-version"],
                stdout=stdout,
                stderr=io.StringIO(),
                cwd=root,
            )
            result = json.loads(stdout.getvalue())
            self.assertEqual(code, 1)
            self.assertEqual(
                result["errors"][0]["code"],
                "ERROR_UNSUPPORTED_SCHEMA_VERSION",
            )


if __name__ == "__main__":
    unittest.main()
