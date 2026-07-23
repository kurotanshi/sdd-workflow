from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import (  # noqa: E402
    TransitionError,
    build_snapshot,
    parse_with_schema,
    resolve_proposal_paths,
    scan_tasks,
    task_digest,
    validate_complete_task,
)
from sdd_core.cli import main  # noqa: E402
import io  # noqa: E402


def invoke(arguments: list[str], root: Path) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(arguments, stdout=stdout, stderr=stderr, cwd=root)
    assert stderr.getvalue() == ""
    return code, json.loads(stdout.getvalue())


def parsed(root: Path):
    paths = resolve_proposal_paths(root, "valid-simple")
    proposal = paths.proposal.read_bytes()
    tasks = paths.tasks.read_bytes()
    outcome = parse_with_schema(
        short_name="valid-simple",
        proposal_text=proposal.decode(),
        task_scan=scan_tasks(tasks.decode()),
    )
    assert outcome.model is not None
    return paths, outcome.model, build_snapshot(proposal, tasks)


class CompleteTaskValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.target = self.root / "sdd/valid-simple"
        self.target.parent.mkdir(parents=True)
        shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", self.target)
        paths, model, snapshot = parsed(self.root)
        code, result = invoke(
            [
                "--root", str(self.root), "--json", "approve", "valid-simple",
                "--expected-snapshot", snapshot.snapshot_digest,
            ],
            self.root,
        )
        assert code == 0, result

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def validate(self, task_number: int, digest: str, snapshot: str | None = None):
        paths, model, current = parsed(self.root)
        return validate_complete_task(
            paths,
            model,
            current,
            current.snapshot_digest if snapshot is None else snapshot,
            task_number,
            digest,
        )

    def test_validates_approved_task_identity_and_manifest(self) -> None:
        result = self.validate(2, task_digest("Preserve one pending task"))
        self.assertEqual(result.task_ordinal, 2)
        self.assertEqual(result.task_text, "Preserve one pending task")

    def test_rejects_stale_snapshot_before_other_inputs(self) -> None:
        with self.assertRaises(TransitionError) as caught:
            self.validate(99, "wrong", "0" * 64)
        self.assertEqual(caught.exception.code, "ERROR_SNAPSHOT_MISMATCH")

    def test_rejects_missing_ordinal_and_changed_task_identity(self) -> None:
        with self.assertRaises(TransitionError) as ordinal:
            self.validate(99, "0" * 64)
        self.assertEqual(ordinal.exception.code, "ERROR_TASK_NOT_FOUND")

        tasks = self.target / "tasks.md"
        tasks.write_text(tasks.read_text().replace("pending task", "renamed task"))
        with self.assertRaises(TransitionError) as identity:
            self.validate(2, task_digest("Preserve one pending task"))
        self.assertEqual(identity.exception.code, "ERROR_TASK_IDENTITY_MISMATCH")
        self.assertEqual(identity.exception.action, "refresh_status")

    def test_manifest_mismatch_has_field_level_diff(self) -> None:
        proposal = self.target / "proposal.md"
        proposal.write_text(
            proposal.read_text().replace("Add deterministic parsing.", "Different scope.")
        )
        with self.assertRaises(TransitionError) as mismatch:
            self.validate(2, task_digest("Preserve one pending task"))
        self.assertEqual(mismatch.exception.code, "ERROR_APPROVED_PLAN_CHANGED")
        self.assertEqual(mismatch.exception.action, "begin_revision")
        self.assertEqual(mismatch.exception.data["differences"][0]["path"], "/scope/0")

    def test_cli_completes_exact_task_and_updates_attestation(self) -> None:
        paths, model, snapshot = parsed(self.root)
        digest = task_digest(model.tasks[1].text)
        code, result = invoke(
            [
                "--root", str(self.root), "--json", "complete-task", "valid-simple", "2",
                "--expected-task-digest", digest,
                "--expected-snapshot", snapshot.snapshot_digest,
            ],
            self.root,
        )
        self.assertEqual(code, 0, result)
        self.assertTrue(result["data"]["applied"])
        self.assertEqual(result["data"]["result"], "APPLIED")
        self.assertNotEqual(
            result["data"]["before_snapshot"], result["data"]["after_snapshot"]
        )
        self.assertIn("- [x] Preserve one pending task", paths.tasks.read_text())
        metadata = json.loads((self.target / ".sdd/metadata.json").read_text())
        self.assertEqual(metadata["last_operation"]["kind"], "complete-task")
        self.assertTrue(metadata["attestation"]["projection"]["tasks"][1]["completed"])

        retried, retry_result = invoke(
            [
                "--root", str(self.root), "--json", "complete-task", "valid-simple", "2",
                "--expected-task-digest", digest,
                "--expected-snapshot", snapshot.snapshot_digest,
            ],
            self.root,
        )
        self.assertEqual(retried, 0, retry_result)
        self.assertFalse(retry_result["data"]["applied"])
        self.assertEqual(retry_result["data"]["result"], "ALREADY_APPLIED")

    def test_already_applied_is_not_claimed_after_unrelated_byte_change(self) -> None:
        _, model, snapshot = parsed(self.root)
        digest = task_digest(model.tasks[1].text)
        arguments = [
            "--root", str(self.root), "--json", "complete-task", "valid-simple", "2",
            "--expected-task-digest", digest,
            "--expected-snapshot", snapshot.snapshot_digest,
        ]
        self.assertEqual(invoke(arguments, self.root)[0], 0)
        proposal = self.target / "proposal.md"
        proposal.write_text(proposal.read_text() + "\n")
        code, result = invoke(arguments, self.root)
        self.assertEqual(code, 1)
        self.assertEqual(result["errors"][0]["code"], "ERROR_TASK_RETRY_CONFLICT")

    def test_status_does_not_refresh_attestation(self) -> None:
        metadata = self.target / ".sdd/metadata.json"
        before = metadata.read_bytes()
        first = invoke(
            ["--root", str(self.root), "--json", "status", "valid-simple"], self.root
        )
        second = invoke(
            ["--root", str(self.root), "--json", "status", "valid-simple"], self.root
        )
        self.assertEqual(first[0], 0)
        self.assertEqual(second[0], 0)
        self.assertEqual(metadata.read_bytes(), before)

    def test_excluded_prose_edit_only_requires_fresh_snapshot(self) -> None:
        proposal = self.target / "proposal.md"
        proposal.write_text(
            proposal.read_text()
            .replace("Characterize the simplest valid v1 proposal.", "Clarified rationale.")
            .replace("Add parser fixtures.", "Updated path estimate.")
        )
        paths, model, fresh = parsed(self.root)
        digest = task_digest(model.tasks[1].text)
        code, result = invoke(
            [
                "--root", str(self.root), "--json", "complete-task", "valid-simple", "2",
                "--expected-task-digest", digest,
                "--expected-snapshot", fresh.snapshot_digest,
            ],
            self.root,
        )
        self.assertEqual(code, 0, result)
        self.assertIn("- [x] Preserve one pending task", paths.tasks.read_text())

    def test_direct_checkbox_edit_reports_managed_diff_without_attribution(self) -> None:
        tasks = self.target / "tasks.md"
        tasks.write_text(tasks.read_text().replace("- [ ] Preserve", "- [x] Preserve"))
        _, model, snapshot = parsed(self.root)
        code, result = invoke(
            [
                "--root", str(self.root), "--json", "complete-task", "valid-simple", "2",
                "--expected-task-digest", task_digest(model.tasks[1].text),
                "--expected-snapshot", snapshot.snapshot_digest,
            ],
            self.root,
        )
        self.assertEqual(code, 1)
        error = result["errors"][0]
        self.assertEqual(error["code"], "OUT_OF_BAND_DRIFT")
        self.assertEqual(error["action"], "inspect_managed_state_drift")
        self.assertNotIn("agent", error["message"].lower())
        self.assertEqual(result["data"]["differences"][0]["path"], "/tasks/1/completed")

    def test_direct_approved_to_draft_reports_status_drift(self) -> None:
        proposal = self.target / "proposal.md"
        proposal.write_text(proposal.read_text().replace("approved", "draft", 1))
        _, model, snapshot = parsed(self.root)
        code, result = invoke(
            [
                "--root", str(self.root), "--json", "complete-task", "valid-simple", "2",
                "--expected-task-digest", task_digest(model.tasks[1].text),
                "--expected-snapshot", snapshot.snapshot_digest,
            ],
            self.root,
        )
        self.assertEqual(code, 1)
        self.assertEqual(result["errors"][0]["code"], "OUT_OF_BAND_DRIFT")
        self.assertEqual(result["data"]["differences"][0]["path"], "/status")

    def test_machine_metadata_edit_reports_drift(self) -> None:
        metadata_path = self.target / ".sdd/metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["last_operation"]["operation_id"] = "different-evidence"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        _, model, snapshot = parsed(self.root)
        code, result = invoke(
            [
                "--root", str(self.root), "--json", "complete-task", "valid-simple", "2",
                "--expected-task-digest", task_digest(model.tasks[1].text),
                "--expected-snapshot", snapshot.snapshot_digest,
            ],
            self.root,
        )
        self.assertEqual(code, 1)
        self.assertEqual(result["errors"][0]["code"], "OUT_OF_BAND_DRIFT")
        self.assertEqual(
            result["data"]["differences"][0]["path"],
            "/metadata/last_operation/operation_id",
        )

    def test_manifest_identity_mismatch_fails_before_task_write(self) -> None:
        manifest_path = self.target / ".sdd/approval-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["scope"][0] = "tampered"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        paths, model, snapshot = parsed(self.root)
        code, result = invoke(
            [
                "--root", str(self.root), "--json", "complete-task", "valid-simple", "2",
                "--expected-task-digest", task_digest(model.tasks[1].text),
                "--expected-snapshot", snapshot.snapshot_digest,
            ],
            self.root,
        )
        self.assertEqual(code, 1)
        self.assertEqual(
            result["errors"][0]["code"],
            "ERROR_APPROVAL_MANIFEST_IDENTITY_MISMATCH",
        )
        self.assertIn("- [ ] Preserve one pending task", paths.tasks.read_text())

    def test_authorized_revision_can_be_reapproved_with_new_attestation(self) -> None:
        proposal = self.target / "proposal.md"
        proposal.write_text(
            proposal.read_text().replace("Add deterministic parsing.", "Revised scope.")
        )
        revision_snapshot = parsed(self.root)[2].snapshot_digest
        revision = invoke(
            [
                "--root", str(self.root), "--json", "begin-revision", "valid-simple",
                "--expected-snapshot", revision_snapshot,
            ],
            self.root,
        )
        self.assertEqual(revision[0], 0, revision)
        draft_snapshot = parsed(self.root)[2].snapshot_digest
        approved = invoke(
            [
                "--root", str(self.root), "--json", "approve", "valid-simple",
                "--expected-snapshot", draft_snapshot,
            ],
            self.root,
        )
        self.assertEqual(approved[0], 0, approved)
        metadata = json.loads((self.target / ".sdd/metadata.json").read_text())
        self.assertEqual(metadata["approval"]["state"], "active")
        self.assertEqual(metadata["attestation"]["projection"]["status"], "approved")


if __name__ == "__main__":
    unittest.main()
