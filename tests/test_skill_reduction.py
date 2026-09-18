from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/sdd-workflow"
SKILL = PACKAGE / "SKILL.md"
AUTHORING = PACKAGE / "references/proposal-authoring.md"
SELF_REVIEW = PACKAGE / "references/self-review.md"
REPORT = ROOT / "evals/reports/v0.9-skill-reduction-experiment.md"


class SkillReductionTests(unittest.TestCase):
    def test_instruction_budget_is_at_most_30_000_bytes(self) -> None:
        total = sum(path.stat().st_size for path in (SKILL, AUTHORING, SELF_REVIEW))
        self.assertLessEqual(total, 30_000)

    def test_main_skill_keeps_lifecycle_and_authority_boundaries(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        anchors = (
            "`開始實作` explicitly approves a `draft`",
            "require new `開始實作`",
            "CLI is the only authority",
            "fail closed",
            "Never directly edit lifecycle status, checkbox markers, machine metadata, archive paths, or INDEX",
            "one canonical task at a time",
            "With two or more candidates, stop and request the short name",
            "An authority split is a conflicting design decision",
            "exact `確認放棄 <short-name>`",
            "Source-control rollback is outside SDD",
            "Do not create Git commits unless requested",
            "do not draft until user targets plus relevant guidance, architecture, configuration, callers, and tests are read",
            "search tests by imports or references to the target modules",
            "never `pwd`, `ls`, `find`, `tree`, or a root-wide glob",
            "A generic `*` search satisfies nothing",
            "Do not open a file merely to decide whether it is relevant",
            "research draft ends at an empty `## 結論`",
            "Traditional Chinese",
            "`第 N 條完成`",
            "`全部完成`",
            "`歸檔完成`",
            "`已放棄`",
        )
        for anchor in anchors:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)

    def test_high_risk_work_keeps_evidence_and_stop_boundaries(self) -> None:
        authoring = " ".join(AUTHORING.read_text(encoding="utf-8").split())
        review = " ".join(SELF_REVIEW.read_text(encoding="utf-8").split())
        for anchor in (
            "decision evidence",
            "material ambiguity",
            "A request to make an observable outcome happen establishes that the outcome is unmet",
            "Overlap with an existing command is not by itself material ambiguity",
            "never reinterpret `preserve` as adding behavior",
            "Never list the repository root, use a repository-wide glob or content search",
            "Do not draft until every applicable category has a decision-relevant match read",
            "A catch-all glob cannot replace any category",
            "Search test files for imports or references to user-named modules and relevant entry points",
            "instead of asking the user to identify the defect or choose the algorithm",
            "never run `pwd`, `ls`, `find .`, `tree`, an unscoped Glob/Grep, application code",
            "an experiment that relies on cleanup afterward",
            "source of truth",
            "retry/recovery",
            "effects that must not repeat",
            "placeholder text is not a conclusion",
        ):
            with self.subTest(anchor=anchor, source="authoring"):
                self.assertIn(anchor, authoring)
        for anchor in (
            "Every finding names a concrete location",
            "An authority finding names both the authoritative implementation and each duplicate location",
            "cannot establish which location should remain authoritative",
            "Security:",
            "stop",
        ):
            with self.subTest(anchor=anchor, source="self-review"):
                self.assertIn(anchor, review)

    def test_required_references_are_linked_without_new_instruction_files(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        expected = {
            "proposal-authoring.md",
            "runtime-recovery.md",
            "self-review.md",
        }
        self.assertEqual(
            {path.name for path in (PACKAGE / "references").glob("*.md")},
            expected,
        )
        for name in expected:
            self.assertIn(f"references/{name}", text)

    def test_report_records_non_regression_and_usage_diagnostic(self) -> None:
        text = REPORT.read_text(encoding="utf-8")
        for fact in (
            "Status: **KEEP**",
            "77/78 (98.7%)",
            "Critical Violations | 0 | 0",
            "Character-based token proxy | 4,466 | 2,399 | −46.3%",
            "Codex | 77,951 | 134,200 | +72.2%",
            "Claude | 349,495 | 494,944 | +41.6%",
            "Efficiency is diagnostic-only",
            "cannot offset an adherence or safety\nfailure.",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, text)


if __name__ == "__main__":
    unittest.main()
