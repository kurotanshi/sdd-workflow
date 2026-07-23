from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import (  # noqa: E402
    ApprovalManifestError,
    approval_manifest_sha256,
    compare_approval_manifests,
    load_approval_manifest,
    parse_approval_manifest,
    parse_with_schema,
    project_approval_manifest,
    scan_tasks,
    serialize_approval_manifest,
)


FIXTURE = ROOT / "tests/fixtures/baseline/valid-simple"


def _parse(proposal: str, tasks: str):
    outcome = parse_with_schema(
        short_name="valid-simple",
        proposal_text=proposal,
        task_scan=scan_tasks(tasks),
    )
    assert outcome.model is not None
    return outcome.model


class ApprovalManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.proposal = (FIXTURE / "proposal.md").read_text(encoding="utf-8")
        self.tasks = (FIXTURE / "tasks.md").read_text(encoding="utf-8")

    def test_projection_matches_v1_contract(self) -> None:
        manifest = project_approval_manifest(_parse(self.proposal, self.tasks))
        self.assertEqual(
            manifest.to_dict(),
            {
                "approval_model_version": 1,
                "short_name": "valid-simple",
                "change_type": "新功能",
                "scope": ["Add deterministic parsing."],
                "acceptance_conditions": [
                    "情境：task order and completion state remain stable"
                ],
                "tasks": [
                    {"text": "Preserve one completed task"},
                    {"text": "Preserve one pending task"},
                ],
                "extensions": {},
            },
        )

    def test_status_completion_why_and_impact_are_excluded(self) -> None:
        approved = project_approval_manifest(_parse(self.proposal, self.tasks))
        changed_proposal = (
            self.proposal.replace("draft", "approved", 1)
            .replace("Characterize the simplest valid v1 proposal.", "Clarified background.")
            .replace("Add parser fixtures.", "Corrected file estimate.")
        )
        changed_tasks = self.tasks.replace("- [ ] Preserve", "- [x] Preserve")
        current = project_approval_manifest(_parse(changed_proposal, changed_tasks))
        self.assertEqual(approved, current)
        self.assertEqual(compare_approval_manifests(approved, current), ())

    def test_scope_task_and_order_changes_have_field_level_diffs(self) -> None:
        approved = project_approval_manifest(_parse(self.proposal, self.tasks))
        changed_proposal = self.proposal.replace(
            "Add deterministic parsing.", "Add a different behavior."
        )
        changed_tasks = self.tasks.replace(
            "Preserve one pending task", "Replace the pending task"
        )
        current = project_approval_manifest(_parse(changed_proposal, changed_tasks))
        self.assertEqual(
            [item.to_dict() for item in compare_approval_manifests(approved, current)],
            [
                {
                    "path": "/scope/0",
                    "kind": "changed",
                    "approved": "Add deterministic parsing.",
                    "current": "Add a different behavior.",
                },
                {
                    "path": "/tasks/1/text",
                    "kind": "changed",
                    "approved": "Preserve one pending task",
                    "current": "Replace the pending task",
                },
            ],
        )

    def test_unicode_code_points_are_not_normalized(self) -> None:
        composed = self.proposal.replace("Add deterministic parsing.", "Café")
        decomposed = self.proposal.replace("Add deterministic parsing.", "Cafe\u0301")
        first = project_approval_manifest(_parse(composed, self.tasks))
        second = project_approval_manifest(_parse(decomposed, self.tasks))
        self.assertNotEqual(first, second)
        self.assertEqual(compare_approval_manifests(first, second)[0].path, "/scope/0")

    def test_serialization_round_trip_and_raw_identity_are_deterministic(self) -> None:
        manifest = project_approval_manifest(_parse(self.proposal, self.tasks))
        encoded = serialize_approval_manifest(manifest)
        self.assertTrue(encoded.endswith(b"\n"))
        self.assertEqual(parse_approval_manifest(encoded), manifest)
        self.assertEqual(approval_manifest_sha256(manifest), approval_manifest_sha256(encoded))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "approval-manifest.json"
            path.write_bytes(encoded)
            self.assertEqual(load_approval_manifest(path), manifest)

    def test_unknown_fields_and_versions_fail_closed(self) -> None:
        manifest = project_approval_manifest(_parse(self.proposal, self.tasks)).to_dict()
        manifest["unknown"] = True
        with self.assertRaises(ApprovalManifestError) as unknown:
            parse_approval_manifest(json.dumps(manifest))
        self.assertEqual(unknown.exception.code, "ERROR_APPROVAL_MANIFEST_INVALID")

        del manifest["unknown"]
        manifest["approval_model_version"] = 2
        with self.assertRaises(ApprovalManifestError) as version:
            parse_approval_manifest(json.dumps(manifest))
        self.assertEqual(
            version.exception.code,
            "ERROR_UNSUPPORTED_APPROVAL_MODEL_VERSION",
        )
        self.assertEqual(version.exception.action, "use_supported_engine")


if __name__ == "__main__":
    unittest.main()
