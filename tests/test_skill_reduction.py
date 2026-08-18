from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/sdd-workflow/SKILL.md"
AUTHORING = ROOT / "skills/sdd-workflow/references/proposal-authoring.md"
REPORT = ROOT / "evals/reports/v0.9-skill-reduction-experiment.md"


class SkillReductionTests(unittest.TestCase):
    def test_main_skill_is_smaller_than_recorded_full_candidate(self) -> None:
        data = SKILL.read_bytes()
        text = data.decode("utf-8")
        self.assertLess(len(data), 18_333)
        self.assertLess((len(text) + 3) // 4, 4_466)

    def test_safety_anchors_remain_in_main_skill(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        anchors = (
            "開始實作",
            "Requirement changes during implementation or acceptance",
            "fail closed",
            "CLI is the only authority",
            "Abandonment is read-only preflight",
            "COMMITTED_DERIVED_ARTIFACT_STALE",
        )
        for anchor in anchors:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)

    def test_required_references_are_linked_and_present(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for relative in (
            "references/proposal-authoring.md",
            "references/runtime-recovery.md",
        ):
            with self.subTest(relative=relative):
                self.assertIn(relative, text)
                self.assertTrue((SKILL.parent / relative).is_file())

    def test_conditional_intake_branches_remain_in_authoring_reference(self) -> None:
        text = AUTHORING.read_text(encoding="utf-8")
        anchors = (
            "is not automatically the desired",
            "ask exactly one most-critical question",
            "create the draft directly",
            "Never emit a fixed analysis report",
        )
        for anchor in anchors:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)

    def test_conditional_readiness_remains_bounded(self) -> None:
        text = AUTHORING.read_text(encoding="utf-8")
        anchors = (
            "Run this review only for cross-module",
            "low-risk proposal with sufficient information, skip the review",
            "repository feasibility",
            "Do not emit fixed `READY`",
            "source of truth, commit point, retry/recovery behavior",
            "must not repeat",
            "Migration:",
            "External API:",
            "Message publication:",
            "Deployment:",
        )
        for anchor in anchors:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)

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
