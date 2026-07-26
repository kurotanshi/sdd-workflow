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

    def test_maintainer_categories_exist_without_expanding_user_journey(self) -> None:
        categories = {
            "concepts": "approval-manifest.md",
            "operations": "release-checklist.md",
            "compatibility": "compatibility.md",
            "design": "architecture.md",
            "troubleshooting": "troubleshooting.md",
        }
        for category, target in categories.items():
            with self.subTest(category=category):
                index = ROOT / "docs" / category / "README.md"
                self.assertTrue(index.is_file())
                self.assertIn(target, index.read_text(encoding="utf-8"))

        for path in (README, README_EN):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("docs/protocol/", text)
            self.assertNotIn("docs/conformance.md", text)

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

    def test_readmes_position_sdd_for_most_change_tasks_without_a_fast_path(self) -> None:
        zh = README.read_text(encoding="utf-8")
        en = README_EN.read_text(encoding="utf-8")

        for phrase in (
            "大多數變更任務",
            "新功能、修 bug、重構、維運與文件調整",
            "小修改可以使用精簡的 proposal",
            "不會因任務很小就略過安全邊界",
            "bundled state-management CLI",
            "日常使用仍透過 Agent 對話完成",
        ):
            with self.subTest(language="zh", phrase=phrase):
                self.assertIn(phrase, zh)

        for phrase in (
            "complete most change tasks",
            "Features, fixes, refactors, maintenance, and documentation",
            "Small edits use concise proposals",
            "skip safety boundaries",
            "bundled state-management CLI",
            "Everyday use remains Agent-driven",
        ):
            with self.subTest(language="en", phrase=phrase):
                self.assertIn(phrase, en)

        self.assertNotIn("單一、低風險小修改", zh)
        self.assertNotIn("A single low-risk edit", en)


if __name__ == "__main__":
    unittest.main()
