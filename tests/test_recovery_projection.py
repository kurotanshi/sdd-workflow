from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402
from sdd_core.recovery_projection import (  # noqa: E402
    RecoverySupplement,
    plan_recovery_projection,
)
from sdd_core.recovery_protocol import (  # noqa: E402
    RecoveryArtifact,
    execute_staged_recovery,
)


PROPOSAL = b"""# legacy-change

## \xe7\x8b\x80\xe6\x85\x8b
approved

## \xe9\xa1\x9e\xe5\x9e\x8b
\xe6\x96\xb0\xe5\x8a\x9f\xe8\x83\xbd

## \xe7\x82\xba\xe4\xbb\x80\xe9\xba\xbc\xe5\x81\x9a
Preserve a historical proposal.

## \xe8\xa6\x81\xe6\x94\xb9\xe4\xbb\x80\xe9\xba\xbc
- Rebuild its encoding.

## \xe5\xbd\xb1\xe9\x9f\xbf\xe7\xaf\x84\xe5\x9c\x8d
- Test fixtures only.
"""


def tasks(line: str, *, acceptance: bool = True) -> bytes:
    suffix = "\n## \u9a57\u6536\u689d\u4ef6\n\n- \u60c5\u5883\uff1arecovery is explicit.\n" if acceptance else "\n"
    return (f"# legacy-change \u4efb\u52d9\n\n{line}\n" + suffix).encode()


def invoke(root: Path, *arguments: str) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(
        ["--root", str(root), "--json", *arguments],
        stdout=stdout,
        stderr=stderr,
        cwd=root,
    )
    assert stderr.getvalue() == ""
    return code, json.loads(stdout.getvalue())


def apply_arguments(preflight: dict[str, object]) -> list[str]:
    projection = preflight["data"]["projection"]  # type: ignore[index]
    source = projection["source_digests"]
    candidate = projection["candidate_digests"]
    return [
        "--apply",
        "--expected-proposal-sha256",
        source["proposal.md"],
        "--expected-tasks-sha256",
        source["tasks.md"],
        "--expected-candidate-proposal-sha256",
        candidate["proposal.md"],
        "--expected-candidate-tasks-sha256",
        candidate["tasks.md"],
    ]


class RecoveryProjectionTests(unittest.TestCase):
    def test_repository_baseline_and_legacy_archive_fixtures_are_no_op(self) -> None:
        cases = (
            (
                "active",
                "valid-simple",
                ROOT / "tests/fixtures/baseline/valid-simple",
                None,
            ),
            (
                "archive",
                "legacy-completed",
                ROOT
                / "tests/fixtures/archive/legacy/2025-01-02-legacy-completed",
                "completed",
            ),
        )
        for target, short_name, directory, expected_status in cases:
            with self.subTest(target=target):
                plan = plan_recovery_projection(
                    target=target,
                    short_name=short_name,
                    proposal_bytes=(directory / "proposal.md").read_bytes(),
                    tasks_bytes=(directory / "tasks.md").read_bytes(),
                    expected_status=expected_status,
                )
                self.assertEqual(plan.disposition, "no-op", plan.redacted_dict())

    def test_readable_v020_v023_shape_is_no_op(self) -> None:
        plan = plan_recovery_projection(
            target="active",
            short_name="legacy-change",
            proposal_bytes=PROPOSAL,
            tasks_bytes=tasks("- [x] Preserve completed history"),
        )
        self.assertEqual(plan.disposition, "no-op")
        self.assertIsNone(plan.proposal_candidate)
        self.assertEqual(plan.candidate_digests, ())

    def test_registered_top_level_checkbox_variants_have_one_candidate(self) -> None:
        for source, canonical in (
            ("- [X]Done", "- [x] Done"),
            ("* [ ] Pending", "- [ ] Pending"),
            ("+ [x]Done", "- [x] Done"),
            ("1. [ ] Ordered", "- [ ] Ordered"),
            ("2) [X]Ordered done", "- [x] Ordered done"),
        ):
            with self.subTest(source=source):
                plan = plan_recovery_projection(
                    target="active",
                    short_name="legacy-change",
                    proposal_bytes=PROPOSAL,
                    tasks_bytes=tasks(source),
                )
                self.assertEqual(plan.disposition, "ready", plan.redacted_dict())
                assert plan.tasks_candidate is not None
                self.assertIn(canonical, plan.tasks_candidate.decode())
                self.assertEqual(plan.encoding, "registered-checkbox-deviation")

    def test_ambiguous_task_forms_and_ordinary_lists_fail_closed(self) -> None:
        for line in ("  - [x] Indented", "- [] Empty", "- [?] Unknown", "- prose"):
            with self.subTest(line=line):
                plan = plan_recovery_projection(
                    target="active",
                    short_name="legacy-change",
                    proposal_bytes=PROPOSAL,
                    tasks_bytes=tasks(line),
                )
                self.assertEqual(plan.disposition, "blocked")
                self.assertTrue(plan.issues)
                self.assertFalse(plan.candidate_digests)

    def test_missing_non_derived_fields_require_explicit_inputs(self) -> None:
        proposal = PROPOSAL.replace(
            b"## \xe9\xa1\x9e\xe5\x9e\x8b\n\xe6\x96\xb0\xe5\x8a\x9f\xe8\x83\xbd\n\n", b""
        ).replace(
            b"## \xe5\xbd\xb1\xe9\x9f\xbf\xe7\xaf\x84\xe5\x9c\x8d\n- Test fixtures only.\n", b""
        )
        blocked = plan_recovery_projection(
            target="active",
            short_name="legacy-change",
            proposal_bytes=proposal,
            tasks_bytes=tasks("- [X]Done", acceptance=False),
        )
        self.assertEqual(
            blocked.required_inputs, ("acceptance", "change_type", "scope")
        )
        self.assertFalse(blocked.candidate_digests)

        ready = plan_recovery_projection(
            target="active",
            short_name="legacy-change",
            proposal_bytes=proposal,
            tasks_bytes=tasks("- [X]Done", acceptance=False),
            supplement=RecoverySupplement(
                change_type="\u65b0\u529f\u80fd",
                scope="- Recovered scope.",
                acceptance_conditions=("\u60c5\u5883\uff1arecovered acceptance.",),
            ),
        )
        self.assertEqual(ready.disposition, "ready", ready.redacted_dict())

    def test_explicit_input_cannot_override_existing_authority(self) -> None:
        plan = plan_recovery_projection(
            target="active",
            short_name="legacy-change",
            proposal_bytes=PROPOSAL,
            tasks_bytes=tasks("- [X]Done"),
            supplement=RecoverySupplement(scope="Different scope"),
        )
        self.assertEqual(plan.disposition, "blocked")
        self.assertEqual(plan.issues[0].code, "ERROR_RECOVERY_INPUT_CONFLICT")

    def test_multiple_semantic_values_remain_ambiguous_even_with_input(self) -> None:
        proposal = PROPOSAL.replace(
            "\u65b0\u529f\u80fd".encode(),
            "\u65b0\u529f\u80fd\n\u91cd\u69cb".encode(),
        )
        plan = plan_recovery_projection(
            target="active",
            short_name="legacy-change",
            proposal_bytes=proposal,
            tasks_bytes=tasks("* [ ] Pending"),
            supplement=RecoverySupplement(change_type="\u65b0\u529f\u80fd"),
        )
        self.assertEqual(plan.disposition, "blocked")
        self.assertEqual(plan.issues[0].field, "change_type")

    def test_future_schema_and_unregistered_json_versions_fail_closed(self) -> None:
        future = b"---\nschema_version: 99\n---\n" + PROPOSAL
        plan = plan_recovery_projection(
            target="active",
            short_name="legacy-change",
            proposal_bytes=future,
            tasks_bytes=tasks("- [X]Done"),
        )
        self.assertEqual(plan.issues[0].code, "ERROR_RECOVERY_FORMAT_UNREGISTERED")

        metadata = json.dumps({"metadata_version": 7}).encode()
        plan = plan_recovery_projection(
            target="archive",
            short_name="legacy-change",
            proposal_bytes=PROPOSAL.replace(b"approved", b"completed"),
            tasks_bytes=tasks("- [X]Done"),
            expected_status="completed",
            metadata_bytes=metadata,
            supplement=RecoverySupplement(summary="Recovered summary"),
        )
        self.assertEqual(plan.issues[0].code, "ERROR_RECOVERY_FORMAT_UNREGISTERED")

    def test_redacted_report_contains_no_artifact_body(self) -> None:
        secret = "UNIQUE-SENSITIVE-BODY"
        proposal = PROPOSAL.replace(b"Preserve a historical proposal.", secret.encode())
        plan = plan_recovery_projection(
            target="active",
            short_name="legacy-change",
            proposal_bytes=proposal,
            tasks_bytes=tasks("* [ ] Pending"),
        )
        report = json.dumps(plan.redacted_dict(), sort_keys=True)
        self.assertNotIn(secret, report)
        self.assertNotIn("Pending", report)
        self.assertRegex(report, r"[0-9a-f]{64}")


class RecoveryPreflightTests(unittest.TestCase):
    def test_unregistered_task_and_acceptance_content_blocks_without_writes(self) -> None:
        cases = {
            "task prose": (
                "# legacy-change 任務\n\n"
                "UNREGISTERED TASK CONTENT\n"
                "+ [x]Done\n\n"
                "## 驗收條件\n\n"
                "- 情境：recovery is explicit.\n"
            ),
            "unknown heading": (
                "# legacy-change 任務\n\n"
                "### Unknown\n"
                "+ [x]Done\n\n"
                "## 驗收條件\n\n"
                "- 情境：recovery is explicit.\n"
            ),
            "acceptance prose": (
                "# legacy-change 任務\n\n"
                "+ [x]Done\n\n"
                "## 驗收條件\n\n"
                "- 情境：recovery is explicit.\n"
                "UNREGISTERED ACCEPTANCE CONTENT\n"
            ),
        }
        for label, task_text in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                target = root / "sdd/legacy-change"
                target.mkdir(parents=True)
                (target / "proposal.md").write_bytes(PROPOSAL)
                (target / "tasks.md").write_text(task_text)
                before = {
                    path.relative_to(root): path.read_bytes()
                    for path in root.rglob("*")
                    if path.is_file()
                }

                code, envelope = invoke(
                    root, "repair-proposal-format", "legacy-change"
                )

                self.assertEqual(code, 1, envelope)
                self.assertEqual(
                    envelope["errors"][0]["code"],
                    "ERROR_RECOVERY_FORMAT_UNREGISTERED",
                )
                self.assertEqual(
                    envelope["errors"][0]["action"],
                    "upgrade_or_recreate_proposal",
                )
                projection = envelope["data"]["projection"]
                self.assertEqual(projection["disposition"], "blocked")
                self.assertEqual(projection["candidate_digests"], {})
                after = {
                    path.relative_to(root): path.read_bytes()
                    for path in root.rglob("*")
                    if path.is_file()
                }
                self.assertEqual(after, before)

    def test_current_v2_preflight_is_evidence_backed_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/minimal-v2"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/schema-v2/minimal-v2", target)
            before = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            code, envelope = invoke(root, "repair-proposal-format", "minimal-v2")
            self.assertEqual(code, 0, envelope)
            self.assertEqual(
                envelope["data"]["projection"]["disposition"], "no-op"
            )
            after = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_active_cli_preflight_is_read_only_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/legacy-change"
            target.mkdir(parents=True)
            (target / "proposal.md").write_bytes(PROPOSAL)
            (target / "tasks.md").write_bytes(tasks("* [ ] Pending"))
            before = {path.name: path.read_bytes() for path in target.iterdir()}

            code, envelope = invoke(
                root, "repair-proposal-format", "legacy-change"
            )
            self.assertEqual(code, 0, envelope)
            self.assertEqual(envelope["data"]["projection"]["disposition"], "ready")
            self.assertNotIn("Pending", json.dumps(envelope))
            self.assertEqual(
                {path.name: path.read_bytes() for path in target.iterdir()}, before
            )

    def test_active_machine_approval_artifacts_block_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/legacy-change"
            machine = target / ".sdd"
            machine.mkdir(parents=True)
            (target / "proposal.md").write_bytes(PROPOSAL)
            (target / "tasks.md").write_bytes(tasks("* [ ] Pending"))
            (machine / "approval-manifest.json").write_text("{}")
            before = (machine / "approval-manifest.json").read_bytes()

            code, envelope = invoke(
                root, "repair-proposal-format", "legacy-change"
            )
            self.assertEqual(code, 1, envelope)
            self.assertEqual(
                envelope["errors"][0]["action"], "inspect_machine_metadata"
            )
            self.assertEqual((machine / "approval-manifest.json").read_bytes(), before)

    def test_archive_preflight_exposes_same_projection_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            target = archive / "2025-01-02-legacy-change"
            target.mkdir(parents=True)
            (target / "proposal.md").write_bytes(
                PROPOSAL.replace(b"approved", b"completed")
            )
            (target / "tasks.md").write_bytes(tasks("+ [x]Done"))
            (archive / "INDEX.md").write_text(
                "# SDD Archive\n\n- 2025-01-02 | legacy-change | completed | Summary.\n"
            )
            before = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            code, envelope = invoke(
                root, "repair-archive-record", "2025-01-02-legacy-change"
            )
            self.assertEqual(code, 0, envelope)
            self.assertEqual(envelope["data"]["projection"]["disposition"], "ready")
            after = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)


class ActiveRecoveryApplyTests(unittest.TestCase):
    def test_confirmed_apply_outputs_v2_draft_and_preserves_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/legacy-change"
            target.mkdir(parents=True)
            (target / "proposal.md").write_bytes(PROPOSAL)
            (target / "tasks.md").write_bytes(
                tasks("- [X]Completed before recovery").replace(
                    b"\n## ", b"\n* [ ] Pending after recovery\n\n## ", 1
                )
            )
            code, preflight = invoke(
                root, "repair-proposal-format", "legacy-change"
            )
            self.assertEqual(code, 0, preflight)
            arguments = apply_arguments(preflight)

            code, applied = invoke(
                root, "repair-proposal-format", "legacy-change", *arguments
            )
            self.assertEqual(code, 0, applied)
            self.assertTrue(applied["data"]["committed"])
            self.assertEqual(applied["data"]["outcome"], "APPLIED")
            proposal = (target / "proposal.md").read_text()
            rebuilt_tasks = (target / "tasks.md").read_text()
            self.assertTrue(proposal.startswith("---\nschema_version: 2\n---"))
            self.assertIn("\n## \u72c0\u614b\ndraft\n", proposal)
            self.assertIn("- [x] Completed before recovery", rebuilt_tasks)
            self.assertIn("- [ ] Pending after recovery", rebuilt_tasks)
            self.assertFalse((target / ".sdd").exists())

            repeat_code, repeated = invoke(
                root, "repair-proposal-format", "legacy-change", *arguments
            )
            self.assertEqual(repeat_code, 0, repeated)
            self.assertEqual(repeated["data"]["outcome"], "ALREADY_APPLIED")

            status_code, status = invoke(root, "status", "legacy-change")
            self.assertEqual(status_code, 0, status)
            self.assertEqual(status["data"]["status"], "draft")
            approve_code, approved = invoke(
                root,
                "approve",
                "legacy-change",
                "--expected-snapshot",
                status["data"]["snapshot"]["snapshot_digest"],
            )
            self.assertEqual(approve_code, 0, approved)
            approved_snapshot = approved["data"]["after_snapshot"]["snapshot_digest"]
            archive_code, archive = invoke(
                root,
                "archive",
                "legacy-change",
                "--expected-snapshot",
                approved_snapshot,
                "--summary",
                "Must remain blocked by the pending task.",
            )
            self.assertEqual(archive_code, 1, archive)
            self.assertEqual(
                archive["errors"][0]["code"], "ERROR_ARCHIVE_TASKS_INCOMPLETE"
            )

    def test_digest_drift_prevents_apply_without_authoritative_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/legacy-change"
            target.mkdir(parents=True)
            (target / "proposal.md").write_bytes(PROPOSAL)
            (target / "tasks.md").write_bytes(tasks("* [ ] Pending"))
            _, preflight = invoke(root, "repair-proposal-format", "legacy-change")
            arguments = apply_arguments(preflight)
            arguments[2] = "0" * 64
            before = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            code, rejected = invoke(
                root, "repair-proposal-format", "legacy-change", *arguments
            )
            self.assertEqual(code, 1, rejected)
            self.assertEqual(
                rejected["errors"][0]["code"],
                "ERROR_RECOVERY_EVIDENCE_MISMATCH",
            )
            after = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_restore_is_refused_after_reapproval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/legacy-change"
            target.mkdir(parents=True)
            (target / "proposal.md").write_bytes(PROPOSAL)
            (target / "tasks.md").write_bytes(tasks("+ [x]Done"))
            _, preflight = invoke(root, "repair-proposal-format", "legacy-change")
            _, applied = invoke(
                root,
                "repair-proposal-format",
                "legacy-change",
                *apply_arguments(preflight),
            )
            operation_id = applied["data"]["operation_id"]
            _, status = invoke(root, "status", "legacy-change")
            approve_code, _ = invoke(
                root,
                "approve",
                "legacy-change",
                "--expected-snapshot",
                status["data"]["snapshot"]["snapshot_digest"],
            )
            self.assertEqual(approve_code, 0)

            code, rejected = invoke(
                root,
                "repair-proposal-format",
                "legacy-change",
                "--restore-operation",
                operation_id,
            )
            self.assertEqual(code, 1, rejected)
            self.assertEqual(
                rejected["errors"][0]["code"], "ERROR_RECOVERY_RESTORE_UNSAFE"
            )


class RecoveryRoutingAndDoctorTests(unittest.TestCase):
    def test_archive_failure_routes_registered_checkbox_to_active_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/legacy-change"
            target.mkdir(parents=True)
            (target / "proposal.md").write_bytes(PROPOSAL)
            (target / "tasks.md").write_bytes(tasks("* [ ] Pending"))
            code, result = invoke(
                root,
                "archive",
                "legacy-change",
                "--expected-snapshot",
                "0" * 64,
                "--summary",
                "Blocked before mutation.",
            )
            self.assertEqual(code, 1, result)
            self.assertEqual(
                result["errors"][0]["action"], "repair_proposal_format"
            )

    def test_rebuild_index_and_doctor_route_recoverable_archive_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            target = archive / "2025-01-02-legacy-change"
            target.mkdir(parents=True)
            (target / "proposal.md").write_bytes(
                PROPOSAL.replace(b"approved", b"completed")
            )
            (target / "tasks.md").write_bytes(tasks("+ [x]Done"))
            (archive / "INDEX.md").write_text(
                "# SDD Archive\n\n"
                "- 2025-01-02 | legacy-change | completed | Summary.\n"
            )
            before = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            code, rebuilt = invoke(root, "rebuild-index")
            self.assertEqual(code, 1, rebuilt)
            self.assertEqual(
                rebuilt["errors"][0]["action"], "repair_archive_record"
            )
            code, doctor = invoke(root, "doctor")
            self.assertEqual(code, 1, doctor)
            actions = {item["action"] for item in doctor["errors"]}
            self.assertIn("repair_archive_record", actions)
            after = {
                path.relative_to(root): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_doctor_reports_incomplete_private_recovery_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(
                ROOT / "tests/fixtures/baseline/valid-simple", target
            )
            archive = root / "sdd/archive"
            archive.mkdir()
            (archive / "INDEX.md").write_text("# SDD Archive\n\n")

            def stop_after_staging(_: object) -> None:
                raise ValueError("leave staged evidence")

            with self.assertRaises(ValueError):
                execute_staged_recovery(
                    target,
                    kind="repair-proposal-format",
                    target_identity="active:valid-simple",
                    artifacts=(
                        RecoveryArtifact(
                            "proposal.md",
                            (target / "proposal.md").read_bytes(),
                            (target / "proposal.md").read_bytes(),
                        ),
                    ),
                    validate_candidates=stop_after_staging,
                )
            code, doctor = invoke(root, "doctor")
            self.assertEqual(code, 1, doctor)
            staged = [
                item
                for item in doctor["errors"]
                if item["code"] == "RECOVERY_STAGED_STATE"
            ]
            self.assertEqual(len(staged), 1)
            self.assertEqual(staged[0]["action"], "resume_or_restore_recovery")


if __name__ == "__main__":
    unittest.main()
