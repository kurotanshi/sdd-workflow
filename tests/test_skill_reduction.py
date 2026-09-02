from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/sdd-workflow/SKILL.md"
AUTHORING = ROOT / "skills/sdd-workflow/references/proposal-authoring.md"
SELF_REVIEW = ROOT / "skills/sdd-workflow/references/self-review.md"
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
            "references/self-review.md",
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

    def test_self_review_keeps_its_evidence_and_stop_boundaries(self) -> None:
        skill = SKILL.read_text(encoding="utf-8")
        reference = SELF_REVIEW.read_text(encoding="utf-8")
        for anchor in (
            "Optional on-demand review. Never automatic",
            "Never call `approve` and never implement",
            "`approved`: prose is frozen",
            "grep every caller",
            "Every finding names a concrete location",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, skill + reference)

    def test_self_review_distinguishes_authority_splits_from_duplication(self) -> None:
        text = " ".join(SELF_REVIEW.read_text(encoding="utf-8").split())
        for anchor in (
            "makes a client reimplement a rule already enforced by a server",
            "persists state that can be derived from an existing authority",
            "Two locations are enough for this authority-split check",
            "cannot establish which location should remain authoritative",
            "Similar code alone is not a finding",
            "three or more existing",
        ):
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

    def test_pre_draft_approach_review_stays_evidence_bound(self) -> None:
        text = " ".join(AUTHORING.read_text(encoding="utf-8").split())
        for anchor in (
            "When the review applies, before drafting",
            "one bounded discovery pass",
            "targeted filename and reference searches",
            "architecture decisions",
            "not named by the user",
            "decision-relevant repository evidence",
            "affected core flow and callers",
            "do not scan the repository aimlessly",
            "modify product code",
            "simpler, more secure, or more maintainable alternative",
            "behavior, scope, impact, or acceptance conditions",
            "existing one-question rule",
            "without a separate architecture or security review report",
            "bounded `研究` proposal",
            "one-off read-only review need not enter SDD",
            "neither case expands `自審提案`",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)

    def test_main_proposal_step_requires_bounded_high_risk_discovery(self) -> None:
        text = " ".join(SKILL.read_text(encoding="utf-8").split())
        for anchor in (
            "high-risk review gate applies, before authoring",
            "bounded filename and reference searches",
            "applicable project guidance, architecture decisions, configuration",
            "affected core flow and callers, and tests",
            "do not inspect unrelated directories",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)

    def test_authoring_prefers_vertical_slices_without_file_count_limits(self) -> None:
        text = AUTHORING.read_text(encoding="utf-8")
        for anchor in (
            "order tasks by dependency",
            "vertical slices",
            "leave the system usable",
            "fixed file-count",
            "another planning artifact",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)

    def test_authoring_keeps_unchanged_contracts_approval_relevant(self) -> None:
        text = AUTHORING.read_text(encoding="utf-8")
        for anchor in (
            "decision-relevant behavior, interface, or data contract",
            "one verifiable sentence is enough",
            "add no placeholder",
            "do not add a heading, schema field, template, or artifact",
        ):
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, text)
        changes, impact = text.split("\n## 要改什麼\n", 1)[1].split(
            "\n## 影響範圍\n", 1
        )
        self.assertIn("保持後端 API 不變", changes)
        self.assertNotIn("可能檔案", changes)
        self.assertNotIn("不改後端 API", impact.split("\n```", 1)[0])
        self.assertIn("可能檔案：`src/pages/login.tsx`（預估）", impact)

    def test_implementation_quality_gates_are_conditional_and_evidence_bound(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        for anchor in (
            "minimum context packet",
            "target files",
            "related tests",
            "one existing similar pattern",
            "framework, library, SDK, or tool version",
            "official documentation",
            "necessary source cannot be verified",
            "Definition of Done",
            "An existing script alone is not a declaration",
            "conflicting declarations stop",
            "no declaration means do not invent",
        ):
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
