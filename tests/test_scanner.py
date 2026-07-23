from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import scan_tasks  # noqa: E402


FIXTURES = ROOT / "tests/fixtures/baseline"


class TaskScannerTests(unittest.TestCase):
    def test_invalid_checkbox_fixture_reports_all_exact_locations(self) -> None:
        result = scan_tasks(
            (FIXTURES / "invalid-checkbox/tasks.md").read_text(),
            path="invalid-checkbox/tasks.md",
        )
        self.assertEqual(
            [(item.line, item.column, item.code) for item in result.diagnostics],
            [
                (4, 3, "ERROR_INVALID_TASK_CHECKBOX"),
                (5, 1, "ERROR_INVALID_TASK_CHECKBOX"),
                (6, 1, "ERROR_INVALID_TASK_CHECKBOX"),
            ],
        )
        self.assertEqual(result.total_count, 1)
        self.assertFalse(result.counts_reliable)

    def test_markdown_link_is_other_list_item_not_checkbox(self) -> None:
        result = scan_tasks(
            (FIXTURES / "invalid-list-item/tasks.md").read_text(),
            path="invalid-list-item/tasks.md",
        )
        self.assertEqual(
            [(item.line, item.column, item.code) for item in result.diagnostics],
            [
                (4, 1, "ERROR_INVALID_TASK_LIST_ITEM"),
                (5, 1, "ERROR_INVALID_TASK_LIST_ITEM"),
            ],
        )

    def test_all_characterized_checkbox_variants_are_invalid(self) -> None:
        text = "\n".join(
            (
                "- [ ] valid",
                "  - [ ] nested",
                "* [ ] star",
                "+[ ] plus",
                "-[ ] missing separator",
                "- [X] uppercase",
                "- [xx] double marker",
                "- [] empty marker",
                "1. [ ] ordered dot",
                "2) [ ] ordered paren",
                "## 驗收條件",
                "- [ ] ignored acceptance checkbox",
            )
        )
        result = scan_tasks(text, path="variants/tasks.md")
        self.assertEqual(result.total_count, 1)
        self.assertEqual(len(result.diagnostics), 9)
        self.assertTrue(
            all(item.code == "ERROR_INVALID_TASK_CHECKBOX" for item in result.diagnostics)
        )

    def test_acceptance_boundary_excludes_nested_content(self) -> None:
        result = scan_tasks(
            (FIXTURES / "valid-nested-acceptance/tasks.md").read_text()
        )
        self.assertEqual(result.total_count, 1)
        self.assertEqual(len(result.acceptance_conditions), 2)
        self.assertEqual(result.diagnostics, ())


if __name__ == "__main__":
    unittest.main()
