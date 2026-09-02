from __future__ import annotations

import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.atomic_write import atomic_replace_bytes as real_atomic_replace_bytes  # noqa: E402
from sdd_core.recovery_protocol import (  # noqa: E402
    RECOVERY_AREA_NAME,
    RecoveryArtifact,
    execute_staged_recovery,
    inspect_recovery_state,
    restore_staged_recovery,
)
from sdd_core.transitions import TransitionError  # noqa: E402


def artifacts() -> tuple[RecoveryArtifact, ...]:
    return (
        RecoveryArtifact("proposal.md", b"proposal-before", b"proposal-after"),
        RecoveryArtifact("tasks.md", b"tasks-before", b"tasks-after"),
        RecoveryArtifact(
            ".sdd/metadata.json",
            None,
            b'{"metadata_version":1}\n',
        ),
    )


def create_target(root: Path) -> Path:
    target = root / "legacy-change"
    target.mkdir()
    (target / "proposal.md").write_bytes(b"proposal-before")
    (target / "tasks.md").write_bytes(b"tasks-before")
    return target


def execute(target: Path):
    return execute_staged_recovery(
        target,
        kind="repair-proposal-format",
        target_identity="active:legacy-change",
        artifacts=artifacts(),
    )


class RecoveryProtocolTests(unittest.TestCase):
    def test_commit_saves_private_bytes_and_redacted_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = create_target(Path(directory))
            result = execute(target)
            self.assertEqual(result.outcome, "APPLIED")
            self.assertEqual(result.state, "committed")
            self.assertEqual((target / "proposal.md").read_bytes(), b"proposal-after")
            self.assertEqual((target / "tasks.md").read_bytes(), b"tasks-after")
            self.assertEqual(
                (target / ".sdd/metadata.json").read_bytes(),
                b'{"metadata_version":1}\n',
            )

            area = target / RECOVERY_AREA_NAME
            operation = area / result.operation_id
            self.assertEqual(stat.S_IMODE(area.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(operation.stat().st_mode), 0o700)
            for path in operation.rglob("*"):
                if path.is_file():
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            manifest = (operation / "manifest.json").read_text()
            self.assertNotIn("proposal-before", manifest)
            self.assertNotIn("proposal-after", manifest)
            self.assertEqual(inspect_recovery_state(target)[0]["state"], "committed")

    def test_same_operation_retry_resumes_partial_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = create_target(Path(directory))
            failed = False

            def inject(path: Path, data: bytes) -> None:
                nonlocal failed
                if path == target / "tasks.md" and not failed:
                    failed = True
                    raise OSError("injected second-artifact failure")
                real_atomic_replace_bytes(path, data)

            with mock.patch(
                "sdd_core.recovery_protocol.atomic_replace_bytes", side_effect=inject
            ):
                with self.assertRaises(OSError):
                    execute(target)
            self.assertEqual((target / "proposal.md").read_bytes(), b"proposal-after")
            self.assertEqual((target / "tasks.md").read_bytes(), b"tasks-before")
            self.assertEqual(inspect_recovery_state(target)[0]["state"], "applying")

            result = execute(target)
            self.assertEqual(result.outcome, "APPLIED")
            self.assertEqual(result.state, "committed")

    def test_retry_recovers_replacement_before_receipt_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = create_target(Path(directory))
            replaced = False
            failed = False

            def inject(path: Path, data: bytes) -> None:
                nonlocal replaced, failed
                real_atomic_replace_bytes(path, data)
                if path == target / "proposal.md":
                    replaced = True
                elif path.name == "manifest.json" and replaced and not failed:
                    failed = True
                    raise OSError("injected receipt failure")

            with mock.patch(
                "sdd_core.recovery_protocol.atomic_replace_bytes", side_effect=inject
            ):
                with self.assertRaises(OSError):
                    execute(target)
            self.assertEqual((target / "proposal.md").read_bytes(), b"proposal-after")
            result = execute(target)
            self.assertEqual(result.state, "committed")

    def test_conflicting_retry_changes_no_additional_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = create_target(Path(directory))
            result = execute(target)
            (target / "tasks.md").write_bytes(b"later-change")
            proposal_before = (target / "proposal.md").read_bytes()
            with self.assertRaises(TransitionError) as caught:
                execute(target)
            self.assertEqual(caught.exception.code, "ERROR_RECOVERY_RETRY_CONFLICT")
            self.assertEqual((target / "proposal.md").read_bytes(), proposal_before)
            self.assertEqual(result.operation_id, inspect_recovery_state(target)[0]["operation_id"])

    def test_restore_exact_bytes_and_remove_recovery_created_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = create_target(Path(directory))
            committed = execute(target)
            restored = restore_staged_recovery(target, committed.operation_id)
            self.assertEqual(restored.outcome, "RESTORED")
            self.assertEqual((target / "proposal.md").read_bytes(), b"proposal-before")
            self.assertEqual((target / "tasks.md").read_bytes(), b"tasks-before")
            self.assertFalse((target / ".sdd/metadata.json").exists())
            self.assertFalse((target / ".sdd").exists())
            again = restore_staged_recovery(target, committed.operation_id)
            self.assertEqual(again.outcome, "ALREADY_RESTORED")

    def test_restore_can_recover_a_partial_apply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = create_target(Path(directory))
            failed = False

            def inject(path: Path, data: bytes) -> None:
                nonlocal failed
                if path == target / "tasks.md" and not failed:
                    failed = True
                    raise OSError("injected")
                real_atomic_replace_bytes(path, data)

            with mock.patch(
                "sdd_core.recovery_protocol.atomic_replace_bytes", side_effect=inject
            ):
                with self.assertRaises(OSError):
                    execute(target)
            operation_id = str(inspect_recovery_state(target)[0]["operation_id"])
            restored = restore_staged_recovery(target, operation_id)
            self.assertEqual(restored.state, "restored")
            self.assertEqual((target / "proposal.md").read_bytes(), b"proposal-before")
            self.assertEqual((target / "tasks.md").read_bytes(), b"tasks-before")

    def test_later_lifecycle_mutation_prohibits_automatic_restore(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = create_target(Path(directory))
            committed = execute(target)
            (target / "tasks.md").write_bytes(b"completed-later-task")
            proposal_before = (target / "proposal.md").read_bytes()
            with self.assertRaises(TransitionError) as caught:
                restore_staged_recovery(target, committed.operation_id)
            self.assertEqual(caught.exception.code, "ERROR_RECOVERY_RESTORE_UNSAFE")
            self.assertEqual((target / "proposal.md").read_bytes(), proposal_before)
            self.assertEqual((target / "tasks.md").read_bytes(), b"completed-later-task")

    def test_candidate_validation_runs_before_authoritative_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = create_target(Path(directory))

            def reject(_: object) -> None:
                raise ValueError("invalid candidates")

            with self.assertRaises(ValueError):
                execute_staged_recovery(
                    target,
                    kind="repair-proposal-format",
                    target_identity="active:legacy-change",
                    artifacts=artifacts(),
                    validate_candidates=reject,
                )
            self.assertEqual((target / "proposal.md").read_bytes(), b"proposal-before")
            self.assertEqual((target / "tasks.md").read_bytes(), b"tasks-before")
            self.assertFalse((target / ".sdd").exists())


if __name__ == "__main__":
    unittest.main()
