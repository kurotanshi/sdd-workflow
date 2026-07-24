from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
README_EN = ROOT / "README.en.md"


class QuickstartDocumentationTests(unittest.TestCase):
    def test_first_screen_answers_core_new_user_questions(self) -> None:
        zh = README.read_text(encoding="utf-8")
        en = README_EN.read_text(encoding="utf-8")
        for text, install, workflow in (
            (zh, "## 安裝", "## 第一次 workflow"),
            (en, "## Install", "## Your first workflow"),
        ):
            with self.subTest(readme=text[:20]):
                prefix = text[: text.index("## 工作方式" if text is zh else "## Workflow")]
                self.assertIn("Spec-Driven Development", prefix)
                self.assertIn(install, prefix)
                self.assertIn(workflow, prefix)
                self.assertIn("開始實作", prefix)
                self.assertIn("歸檔", prefix)
                self.assertNotIn("transaction-protocol.md", prefix)
                self.assertLess(len(prefix.splitlines()), 90)

    def test_advanced_categories_exist_and_link_to_canonical_docs(self) -> None:
        categories = {
            "concepts": "protocol-draft.md",
            "operations": "release-checklist.md",
            "compatibility": "compatibility.md",
            "design": "transaction-protocol.md",
            "troubleshooting": "doctor-diagnostics.md",
        }
        for category, target in categories.items():
            with self.subTest(category=category):
                index = ROOT / "docs" / category / "README.md"
                self.assertTrue(index.is_file())
                self.assertIn(target, index.read_text(encoding="utf-8"))

    def test_readmes_are_concise_and_use_current_install_roots(self) -> None:
        for path in (README, README_EN):
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertLess(len(text.splitlines()), 180)
                self.assertIn("~/.agents/skills/sdd-workflow/", text)
                self.assertIn("~/.claude/skills/sdd-workflow/", text)
                self.assertNotIn("~/.codex/skills/", text)
                self.assertRegex(
                    text,
                    re.compile(r"examples/sample-web-api/run-walkthrough\.py"),
                )


if __name__ == "__main__":
    unittest.main()
