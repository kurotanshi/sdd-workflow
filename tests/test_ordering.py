from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402


PROPOSAL_TEMPLATE = """# {name}

## 狀態
draft

## 類型
新功能

## 為什麼做
ordering fixture

## 要改什麼
- preserve order

## 影響範圍
- tests
"""


def invoke(root: Path, *arguments: str) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        ["--root", str(root), "--json", *arguments],
        stdout=stdout,
        stderr=stderr,
        cwd=root,
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


class OrderingTests(unittest.TestCase):
    def test_candidates_are_sorted_and_tasks_keep_document_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sdd = root / "sdd"
            for name in ("zeta-change", "alpha-change"):
                proposal = sdd / name
                proposal.mkdir(parents=True)
                (proposal / "proposal.md").write_text(
                    PROPOSAL_TEMPLATE.format(name=name),
                    encoding="utf-8",
                )
                (proposal / "tasks.md").write_text(
                    "# tasks\n\n- [ ] second-in-lexical-order\n"
                    "- [x] first-in-lexical-order\n\n"
                    "## 驗收條件\n- 情境：stable\n",
                    encoding="utf-8",
                )

            exit_code, stdout, stderr = invoke(root, "list", "--state", "active")
            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr, "")
            data = json.loads(stdout)["data"]
            self.assertEqual(
                [item["short_name"] for item in data["candidates"]],
                ["alpha-change", "zeta-change"],
            )
            self.assertEqual(
                [task["text"] for task in data["candidates"][0]["tasks"]],
                ["second-in-lexical-order", "first-in-lexical-order"],
            )

    def test_validate_all_and_list_bytes_repeat(self) -> None:
        fixture_root = ROOT / "tests/fixtures/baseline/ambiguous-active"
        first = invoke(fixture_root, "list", "--state", "active")
        second = invoke(fixture_root, "list", "--state", "active")
        self.assertEqual(first, second)
        self.assertEqual(first[0], 0)
        self.assertEqual(first[2], "")
        envelope = json.loads(first[1])
        self.assertEqual(
            [item["short_name"] for item in envelope["data"]["candidates"]],
            ["alpha-change", "beta-change"],
        )

        validate = invoke(fixture_root, "validate", "--all")
        self.assertEqual(validate[0], 0)
        self.assertEqual(
            [item["short_name"] for item in json.loads(validate[1])["data"]["results"]],
            ["alpha-change", "beta-change"],
        )

    def test_diagnostics_are_sorted_by_source_location(self) -> None:
        # Model the invariant directly with issue-shaped data from a malformed
        # standalone proposal copied into the fixture workspace.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/invalid-order"
            target.mkdir(parents=True)
            (target / "proposal.md").write_text("# invalid-order\n", encoding="utf-8")
            (target / "tasks.md").write_text(
                "# tasks\n\n- [X] bad\n  - [ ] nested\n",
                encoding="utf-8",
            )
            exit_code, stdout, stderr = invoke(root, "status", "invalid-order")
            self.assertEqual(exit_code, 1)
            self.assertEqual(stderr, "")
            errors = json.loads(stdout)["errors"]
            keys = [
                (
                    item.get("path", ""),
                    item.get("line", 0),
                    item.get("column", 0),
                    item["code"],
                )
                for item in errors
            ]
            self.assertEqual(keys, sorted(keys))


if __name__ == "__main__":
    unittest.main()
