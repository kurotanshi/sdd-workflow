from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.public_eval_report_check import (
    PUBLIC_REPORT_ROOT,
    PublicReportError,
    validate_report_directory,
    validate_text,
)


class PublicEvalReportTests(unittest.TestCase):
    def test_repository_report_is_safe_and_complete(self) -> None:
        reports = validate_report_directory(PUBLIC_REPORT_ROOT)
        self.assertTrue(
            any(path.name == "v0.7-agent-eval-summary.md" for path in reports)
        )

    def test_each_summary_can_report_its_own_measured_ratio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "v1.0-agent-eval-summary.md"
            report.write_text(
                "# v1\n"
                "- Release gate: **PASS**\n"
                "- Adherence: **76/78 (97.4%)**, above the 95% threshold\n"
                "- Critical Violations: **0**\n"
                "- Secret scan: PASS\n"
                "- Anonymization review: PASS\n"
                "- Manual review: PASS\n",
                encoding="utf-8",
            )
            self.assertEqual(validate_report_directory(Path(directory)), [report])

    def test_sensitive_and_raw_identifiers_are_rejected(self) -> None:
        unsafe = {
            "home": "source: /Users/example/private/run.json",
            "email": "operator: person@example.com",
            "secret": "Authorization: Bearer not-a-real-credential",
            "trace": '"session_id": "private-session"',
        }
        for label, text in unsafe.items():
            with self.subTest(label=label):
                with self.assertRaises(PublicReportError):
                    validate_text(text, source="unsafe.md")

    def test_missing_publication_review_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "v0.7-agent-eval-summary.md"
            report.write_text("# incomplete\n", encoding="utf-8")
            with self.assertRaisesRegex(
                PublicReportError,
                "missing publication facts",
            ):
                validate_report_directory(Path(directory))


if __name__ == "__main__":
    unittest.main()
