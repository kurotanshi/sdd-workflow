from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402


def invoke(arguments: list[str], *, cwd: Path = ROOT) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(arguments, stdout=stdout, stderr=stderr, cwd=cwd)
    return exit_code, stdout.getvalue(), stderr.getvalue()


class CliContractTests(unittest.TestCase):
    def test_version_human_and_json_contract(self) -> None:
        human = invoke(["--version"])
        self.assertEqual(human, (0, "sdd-workflow 0.6.0 (schema 1..2)\n", ""))

        exit_code, stdout, stderr = invoke(["--json", "--version"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "")
        envelope = json.loads(stdout)
        self.assertEqual(envelope["output_version"], 1)
        self.assertEqual(envelope["command"], "version")
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["warnings"], [])
        self.assertEqual(envelope["errors"], [])

    def test_json_success_known_error_and_usage_are_one_stdout_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            cases = (
                (["--root", str(root), "--json", "status", "valid-simple"], 0),
                (["--json", "status", "../escape"], 1),
                (["--json", "status"], 2),
                (["--json", "parse"], 2),
            )
            for arguments, expected_exit in cases:
                with self.subTest(arguments=arguments):
                    exit_code, stdout, stderr = invoke(arguments, cwd=root)
                    self.assertEqual(exit_code, expected_exit)
                    self.assertEqual(stderr, "")
                    decoder = json.JSONDecoder()
                    document, end = decoder.raw_decode(stdout)
                    self.assertEqual(stdout[end:], "\n")
                    self.assertEqual(document["ok"], expected_exit == 0)

    def test_human_error_uses_stderr_and_status_matches_documented_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            error = invoke(["status", "../escape"], cwd=root)
            self.assertEqual(error[0], 1)
            self.assertEqual(error[1], "")
            self.assertIn("ERROR_INVALID_SHORT_NAME:", error[2])
            proposal = target / "proposal.md"
            proposal.write_text(proposal.read_text().replace("draft", "approved", 1))
            status = invoke(["--root", str(root), "status", "valid-simple"], cwd=root)
            self.assertEqual(status[0], 0)
            self.assertEqual(status[2], "")
            for field in ("adapter=", "status=approved", "type=", "tasks=", "counts=", "snapshot="):
                self.assertIn(field, status[1])

    def test_status_exposes_task_source_canonical_text_and_stable_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            result = invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )
            self.assertEqual(result[0], 0, result)
            task = json.loads(result[1])["data"]["tasks"][0]
            self.assertIn(task["source_text"][:6], {"- [ ] ", "- [x] "})
            self.assertEqual(task["source_text"][6:], task["canonical_text"])
            self.assertEqual(task["text"], task["canonical_text"])
            self.assertRegex(task["task_digest"], r"^[0-9a-f]{64}$")

            before = json.loads(invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )[1])["data"]["tasks"][1]
            tasks = target / "tasks.md"
            tasks.write_text(tasks.read_text().replace("- [ ] Preserve", "- [x] Preserve"))
            after = json.loads(invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )[1])["data"]["tasks"][1]
            self.assertNotEqual(before["source_text"], after["source_text"])
            self.assertEqual(before["canonical_text"], after["canonical_text"])
            self.assertEqual(before["task_digest"], after["task_digest"])

    def test_status_reports_active_approval_scope_drift_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(
                ROOT / "tests/fixtures/activation-pilot",
                root,
                dirs_exist_ok=True,
            )
            draft = json.loads(
                invoke(
                    ["--root", str(root), "--json", "status", "pilot-change"],
                    cwd=root,
                )[1]
            )
            approved = invoke(
                [
                    "--root",
                    str(root),
                    "--json",
                    "approve",
                    "pilot-change",
                    "--expected-snapshot",
                    draft["data"]["snapshot"]["snapshot_digest"],
                ],
                cwd=root,
            )
            self.assertEqual(approved[0], 0, approved)
            proposal = root / "sdd/pilot-change/proposal.md"
            proposal.write_text(
                proposal.read_text(encoding="utf-8").replace(
                    "Create `result.txt` containing exactly `managed-pilot`.",
                    "Create `result.txt` containing changed unapproved content.",
                ),
                encoding="utf-8",
            )
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in (root / "sdd/pilot-change").rglob("*")
                if path.is_file()
            }
            status = invoke(
                ["--root", str(root), "--json", "status", "pilot-change"],
                cwd=root,
            )
            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in (root / "sdd/pilot-change").rglob("*")
                if path.is_file()
            }
            self.assertEqual(status[0], 1, status)
            envelope = json.loads(status[1])
            self.assertFalse(envelope["ok"])
            self.assertEqual(
                envelope["errors"][0]["code"],
                "ERROR_APPROVED_PLAN_CHANGED",
            )
            self.assertEqual(envelope["errors"][0]["action"], "begin_revision")
            self.assertEqual(envelope["data"]["differences"][0]["path"], "/scope/0")
            self.assertEqual(after, before)

    def test_missing_artifact_and_invalid_utf8_have_stable_codes_and_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incomplete = root / "sdd/incomplete"
            incomplete.mkdir(parents=True)
            (incomplete / "proposal.md").write_text("proposal", encoding="utf-8")
            missing = invoke(
                ["--root", str(root), "--json", "status", "incomplete"],
                cwd=root,
            )
            missing_error = json.loads(missing[1])["errors"][0]
            self.assertEqual(missing_error["code"], "ERROR_ARTIFACT_MISSING")
            self.assertEqual(missing_error["action"], "create_or_select_proposal")

            invalid = root / "sdd/invalid-utf8"
            invalid.mkdir()
            (invalid / "proposal.md").write_bytes(b"\xff")
            (invalid / "tasks.md").write_text("# tasks\n", encoding="utf-8")
            encoding = invoke(
                ["--root", str(root), "--json", "status", "invalid-utf8"],
                cwd=root,
            )
            encoding_error = json.loads(encoding[1])["errors"][0]
            self.assertEqual(encoding_error["code"], "ERROR_ARTIFACT_ENCODING")
            self.assertEqual(encoding_error["action"], "fix_artifact_format")

    def test_internal_failure_is_caught_without_traceback(self) -> None:
        with mock.patch("sdd_core.cli.execute", side_effect=RuntimeError("secret details")):
            exit_code, stdout, stderr = invoke(["--json", "--version"])
        self.assertEqual(exit_code, 70)
        self.assertEqual(stderr, "")
        self.assertNotIn("secret details", stdout)
        self.assertNotIn("Traceback", stdout)
        error = json.loads(stdout)["errors"][0]
        self.assertEqual(error["code"], "ERROR_INTERNAL")
        self.assertEqual(error["action"], "report_internal_error")

    def test_legacy_preflight_preserves_transcript_hash_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/legacy-statusless"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/legacy-statusless", target)
            exit_code, stdout, stderr = invoke(
                ["--root", str(root), "abandon-preflight", "legacy-statusless"],
                cwd=root,
            )
            self.assertEqual(exit_code, 0)
            self.assertIn("WARNING_LEGACY_STATUS_MISSING", stderr)
            matches = re.findall(
                r"^(proposal\.md|tasks\.md) sha256: ([0-9a-f]{64})$",
                stdout,
                re.MULTILINE,
            )
            self.assertEqual(len(matches), 2)

    def test_malformed_validate_reports_every_scanner_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/invalid-checkbox"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/invalid-checkbox", target)
            exit_code, stdout, stderr = invoke(
                ["--root", str(root), "--json", "validate", "invalid-checkbox"],
                cwd=root,
            )
            self.assertEqual(exit_code, 1)
            self.assertEqual(stderr, "")
            errors = json.loads(stdout)["errors"]
            self.assertEqual(
                [(item["line"], item["column"], item["code"]) for item in errors],
                [
                    (4, 3, "ERROR_INVALID_TASK_CHECKBOX"),
                    (5, 1, "ERROR_INVALID_TASK_CHECKBOX"),
                    (6, 1, "ERROR_INVALID_TASK_CHECKBOX"),
                ],
            )

    def test_approve_checks_cas_and_persists_after_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)

            status = invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )
            before = json.loads(status[1])["data"]["snapshot"]["snapshot_digest"]
            stale = invoke(
                [
                    "--root", str(root), "--json", "approve", "valid-simple",
                    "--expected-snapshot", "0" * 64,
                ],
                cwd=root,
            )
            self.assertEqual(stale[0], 1)
            self.assertEqual(json.loads(stale[1])["errors"][0]["code"], "ERROR_SNAPSHOT_MISMATCH")
            self.assertFalse((target / ".sdd").exists())

            approved = invoke(
                [
                    "--root", str(root), "--json", "approve", "valid-simple",
                    "--expected-snapshot", before,
                ],
                cwd=root,
            )
            self.assertEqual(approved[0], 0, approved)
            data = json.loads(approved[1])["data"]
            self.assertNotEqual(data["before_snapshot"], data["after_snapshot"])
            self.assertIn("\napproved\n", (target / "proposal.md").read_text())
            manifest = json.loads((target / ".sdd/approval-manifest.json").read_text())
            metadata = json.loads((target / ".sdd/metadata.json").read_text())
            self.assertEqual(manifest["short_name"], "valid-simple")
            self.assertEqual(metadata["approval"]["state"], "active")
            self.assertEqual(metadata["last_operation"]["kind"], "approve")

    def test_approve_rejects_non_draft_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            proposal = target / "proposal.md"
            proposal.write_text(proposal.read_text().replace("draft", "approved", 1))
            status = invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )
            snapshot = json.loads(status[1])["data"]["snapshot"]["snapshot_digest"]
            result = invoke(
                [
                    "--root", str(root), "--json", "approve", "valid-simple",
                    "--expected-snapshot", snapshot,
                ],
                cwd=root,
            )
            self.assertEqual(result[0], 1)
            self.assertEqual(json.loads(result[1])["errors"][0]["code"], "ERROR_INVALID_SOURCE_STATE")
            self.assertFalse((target / ".sdd").exists())

    def test_begin_revision_records_semantic_diff_and_invalidates_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            before = json.loads(invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )[1])["data"]["snapshot"]["snapshot_digest"]
            approved = json.loads(invoke(
                ["--root", str(root), "--json", "approve", "valid-simple", "--expected-snapshot", before],
                cwd=root,
            )[1])
            proposal = target / "proposal.md"
            proposal.write_text(
                proposal.read_text().replace("Add deterministic parsing.", "Add revised parsing.")
            )
            revision_snapshot = json.loads(invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )[1])["data"]["snapshot"]["snapshot_digest"]
            revision = invoke(
                ["--root", str(root), "--json", "begin-revision", "valid-simple", "--expected-snapshot", revision_snapshot],
                cwd=root,
            )
            self.assertEqual(revision[0], 0, revision)
            data = json.loads(revision[1])["data"]
            self.assertEqual(data["differences"][0]["path"], "/scope/0")
            self.assertIn("\ndraft\n", proposal.read_text())
            metadata = json.loads((target / ".sdd/metadata.json").read_text())
            self.assertEqual(metadata["approval"]["state"], "invalidated")
            self.assertEqual(metadata["revision"]["phase"], "open")
            self.assertEqual(metadata["revision"]["source_snapshot"], revision_snapshot)
            self.assertNotEqual(
                approved["data"]["after_snapshot"]["snapshot_digest"],
                data["after_snapshot"]["snapshot_digest"],
            )

            retry = invoke(
                ["--root", str(root), "--json", "begin-revision", "valid-simple", "--expected-snapshot", revision_snapshot],
                cwd=root,
            )
            self.assertEqual(retry[0], 0, retry)
            self.assertFalse(json.loads(retry[1])["data"]["applied"])

    def test_approved_unversioned_v1_requires_explicit_manifest_establishment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            proposal = target / "proposal.md"
            proposal.write_text(proposal.read_text().replace("draft", "approved", 1))
            original = proposal.read_bytes()
            snapshot = json.loads(invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )[1])["data"]["snapshot"]["snapshot_digest"]

            ordinary = invoke(
                ["--root", str(root), "--json", "approve", "valid-simple", "--expected-snapshot", snapshot],
                cwd=root,
            )
            self.assertEqual(ordinary[0], 1)
            self.assertEqual(json.loads(ordinary[1])["errors"][0]["code"], "ERROR_INVALID_SOURCE_STATE")
            self.assertFalse((target / ".sdd").exists())

            established = invoke(
                [
                    "--root", str(root), "--json", "approve", "valid-simple",
                    "--expected-snapshot", snapshot, "--establish-manifest",
                ],
                cwd=root,
            )
            self.assertEqual(established[0], 0, established)
            data = json.loads(established[1])["data"]
            self.assertTrue(data["established_manifest"])
            self.assertEqual(data["before_snapshot"], data["after_snapshot"])
            self.assertEqual(proposal.read_bytes(), original)
            self.assertNotIn(b"schema", proposal.read_bytes())
            metadata = json.loads((target / ".sdd/metadata.json").read_text())
            self.assertEqual(metadata["last_operation"]["kind"], "establish-manifest")

    def test_establish_manifest_rejects_draft_and_stale_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            snapshot = json.loads(invoke(
                ["--root", str(root), "--json", "status", "valid-simple"], cwd=root
            )[1])["data"]["snapshot"]["snapshot_digest"]
            draft = invoke(
                [
                    "--root", str(root), "--json", "approve", "valid-simple",
                    "--expected-snapshot", snapshot, "--establish-manifest",
                ],
                cwd=root,
            )
            self.assertEqual(json.loads(draft[1])["errors"][0]["code"], "ERROR_INVALID_SOURCE_STATE")
            stale = invoke(
                [
                    "--root", str(root), "--json", "approve", "valid-simple",
                    "--expected-snapshot", "0" * 64, "--establish-manifest",
                ],
                cwd=root,
            )
            self.assertEqual(json.loads(stale[1])["errors"][0]["code"], "ERROR_SNAPSHOT_MISMATCH")


if __name__ == "__main__":
    unittest.main()
