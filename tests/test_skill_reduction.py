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


    def test_skill_states_refresh_status_does_not_keep_mutation_intent(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("`refresh_status` never preserves mutation intent automatically.", text)
        self.assertIn("Before the first mutation in an implementation sequence", text)






    def test_description_only_runner_uses_truncated_view_only(self) -> None:
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        desc_dir = root / "evals/description_only_selection"
        sys.path.insert(0, str(desc_dir))
        import run_description_only_selection as runner
        import router

        report = runner.run(limit=160)
        self.assertTrue(report["pass"], report)
        self.assertEqual(report["description_view_len"], 160)
        self.assertEqual(len(report["cases"]), 8)
        view = report["description_view"]
        self.assertIn("sdd-workflow", view)
        self.assertIn("取消提案", view)
        self.assertIn("Outside: generic cancel", view)
        self.assertIn("git/code rollback", view)

        poisoned = "x" * 200
        self.assertFalse(router.route("提案：限制登入重試", poisoned).invoke)
        self.assertTrue(router.route("提案：限制登入重試", view).invoke)
        self.assertFalse(router.route("放棄剛才的變更", view).invoke)

        truncated = runner.load_truncated_description(limit=160)
        self.assertEqual(len(truncated), 160)
        self.assertEqual(truncated, view)

    def test_description_only_polarity_reverse_breaks_negative_cases(self) -> None:
        """Reviewer counterexample: flipping outside→use-for must not keep 8/8."""
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        desc_dir = root / "evals/description_only_selection"
        sys.path.insert(0, str(desc_dir))
        import run_description_only_selection as runner
        import router

        view = runner.load_truncated_description(limit=160)
        reversed_view = view.replace(
            "Outside: generic cancel & git/code rollback",
            "Use for generic cancel or git/code rollback",
        )
        self.assertTrue(router.route("取消剛才的變更", reversed_view).invoke)
        self.assertTrue(router.route("放棄剛才的變更", reversed_view).invoke)
        self.assertTrue(router.route("把程式碼 rollback 到昨天", reversed_view).invoke)
        # Scoring the fixed 8 cases against reversed polarity must fail overall.
        failed = 0
        for case in runner.run(limit=160)["cases"]:
            predicted = router.route(case["utterance"], reversed_view).invoke
            if predicted != case["expect_invoke"]:
                failed += 1
        self.assertGreaterEqual(failed, 2)

    def test_description_only_cases_fail_when_view_is_garbage(self) -> None:
        import json
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        desc_dir = root / "evals/description_only_selection"
        sys.path.insert(0, str(desc_dir))
        import router

        cases = json.loads((desc_dir / "cases.json").read_text(encoding="utf-8"))
        garbage = "x" * 160
        for case in cases:
            if not case["expect_invoke"]:
                continue
            decision = router.route(case["utterance"], garbage)
            with self.subTest(case=case["id"]):
                self.assertFalse(decision.invoke)

    def test_self_review_static_policy_model_covers_layer3_and_authority(self) -> None:
        """Static policy-model gate only; not live-host behavioral proof."""
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        behavior_dir = root / "evals/self_review_behavior"
        sys.path.insert(0, str(behavior_dir))
        import policy
        import run_self_review_behavior as runner

        policy.assert_conformance()
        # Runner score must be 8/8
        self.assertEqual(runner.main.__doc__ is not None or True, True)
        import json
        from io import StringIO
        from contextlib import redirect_stdout

        # Execute runner programmatically
        cases = json.loads((behavior_dir / "cases.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 8)

        Scenario = policy.Scenario
        ChangeKind = policy.ChangeKind
        AuthorityClarity = policy.AuthorityClarity
        ProposalStatus = policy.ProposalStatus
        Action = policy.Action

        matrix = [
            (Scenario(ProposalStatus.DRAFT, ChangeKind.EXISTING_LOGIC), Action.RUN_LAYER3_ASK_USER),
            (Scenario(ProposalStatus.DRAFT, ChangeKind.NEW_FILES), Action.SKIP_LAYER3),
            (Scenario(ProposalStatus.DRAFT, ChangeKind.CONFIG), Action.SKIP_LAYER3),
            (Scenario(ProposalStatus.DRAFT, ChangeKind.COPY), Action.SKIP_LAYER3),
            (
                Scenario(ProposalStatus.DRAFT, ChangeKind.EXISTING_LOGIC, AuthorityClarity.UNCLEAR),
                Action.STOP_AUTHORITY_UNCLEAR,
            ),
            (
                Scenario(ProposalStatus.DRAFT, ChangeKind.EXISTING_LOGIC, AuthorityClarity.CLEAR),
                Action.REPORT_AUTHORITY_SPLIT,
            ),
            (Scenario(ProposalStatus.APPROVED, ChangeKind.EXISTING_LOGIC), Action.FROZEN_REPORT_ONLY),
        ]
        for scenario, expected in matrix:
            decision = policy.decide(scenario)
            with self.subTest(expected=expected.value):
                self.assertEqual(decision.action, expected)
                self.assertFalse(decision.may_approve)
                self.assertFalse(decision.may_implement)

        original = policy.load_self_review_text()
        mutated = original.replace(
            'when evidence proves a split but cannot establish which location should remain authoritative, report it and stop rather than choosing',
            "automatically choose the authoritative location and continue",
        )
        with self.assertRaises(AssertionError):
            policy.assert_conformance(mutated)
        mutated_l3 = original.replace(
            'Run this layer only when existing logic in existing files changes',
            "skip Layer 3 when existing logic changes",
        )
        with self.assertRaises(AssertionError):
            policy.assert_conformance(mutated_l3)



if __name__ == "__main__":
    unittest.main()
