from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402
from sdd_core.doctor import diagnose_runtime_package  # noqa: E402


def invoke(root: Path, arguments: list[str]) -> tuple[int, dict[str, object]]:
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


class DoctorTests(unittest.TestCase):
    def test_environment_evidence_uses_unknown_instead_of_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sdd/archive").mkdir(parents=True)
            (root / "sdd/archive/INDEX.md").write_text(
                "# SDD Archive\n\n",
                encoding="utf-8",
            )
            code, result = invoke(root, ["doctor"])
        self.assertEqual(code, 0)
        evidence = result["data"]["environment"]
        self.assertEqual(evidence["agent_environment"], "unknown")
        self.assertEqual(evidence["package_source"], "unknown")
        self.assertEqual(evidence["discovery_source"], "unknown")
        self.assertEqual(evidence["skill"]["version"], "unknown")
        self.assertEqual(evidence["runtime"]["distribution_id"], "sdd-workflow")
        self.assertEqual(evidence["schema"]["runtime_supported"], [1, 2])
        self.assertEqual(evidence["repository"]["health"], "healthy")
        self.assertFalse(evidence["version_skew"]["detected"])

    def test_runtime_skill_skew_has_exact_remediation(self) -> None:
        with mock.patch(
            "sdd_core.doctor.load_identity",
            return_value={"skill_sha256": "0" * 64},
        ):
            findings = diagnose_runtime_package()
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].code, "RUNTIME_SKILL_VERSION_SKEW")
        self.assertEqual(
            findings[0].action,
            "reinstall_complete_distribution",
        )

    def test_detects_collision_terminal_active_stale_index_and_temp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            shutil.copytree(ROOT / "tests/fixtures/archive/legacy", archive)
            shutil.rmtree(archive / "2025-01-04-missing-summary")
            active = root / "sdd/legacy-completed"
            shutil.copytree(archive / "2025-01-02-legacy-completed", active)
            index = archive / "INDEX.md"
            lines = index.read_text().splitlines()
            index.write_text("\n".join(lines[:2] + list(reversed(lines[2:]))) + "\n")
            (active / ".metadata.dead.tmp").write_text("partial")
            code, result = invoke(root, ["doctor"])
            self.assertEqual(code, 1)
            findings = result["data"]["findings"]
            codes = {item["code"] for item in findings}
            self.assertIn("ACTIVE_ARCHIVE_COLLISION", codes)
            self.assertIn("STATUS_LOCATION_MISMATCH", codes)
            self.assertIn("ERROR_INDEX_STALE", codes)
            self.assertIn("TEMPORARY_FILE_PRESENT", codes)

    def test_detects_attestation_drift_and_partial_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            archive.mkdir(parents=True)
            (archive / "INDEX.md").write_text("# SDD Archive\n\n")
            active = root / "sdd/valid-simple"
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", active)
            status = invoke(root, ["status", "valid-simple"])[1]["data"]
            self.assertEqual(invoke(root, [
                "approve", "valid-simple", "--expected-snapshot",
                status["snapshot"]["snapshot_digest"],
            ])[0], 0)
            tasks = active / "tasks.md"
            tasks.write_text(tasks.read_text().replace("- [ ] Preserve", "- [x] Preserve"))

            partial = root / "sdd/partial"
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", partial)
            proposal = partial / "proposal.md"
            proposal.write_text(proposal.read_text().replace("draft", "approved", 1))
            (partial / ".sdd").mkdir()
            (partial / ".sdd/metadata.json").write_text("{}")

            code, result = invoke(root, ["doctor"])
            self.assertEqual(code, 1)
            findings = result["data"]["findings"]
            by_code = {item["code"]: item for item in findings}
            self.assertIn("OUT_OF_BAND_DRIFT", by_code)
            self.assertEqual(
                by_code["OUT_OF_BAND_DRIFT"]["action"],
                "inspect_managed_state_drift",
            )
            self.assertIn("PARTIAL_TRANSITION_DETECTED", by_code)

    def test_unknown_and_ambiguous_findings_do_not_invent_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            shutil.copytree(ROOT / "tests/fixtures/archive/legacy", archive)
            index = archive / "INDEX.md"
            index.write_text(
                index.read_text()
                + "- 2025-01-02 | legacy-completed | completed | second summary\n"
            )
            code, result = invoke(root, ["doctor"])
            self.assertEqual(code, 1)
            findings = result["data"]["findings"]
            codes = {item["code"] for item in findings}
            self.assertIn("AMBIGUOUS_STATE", codes)
            self.assertIn("UNKNOWN_STATE", codes)
            for finding in findings:
                message = finding["message"].lower()
                self.assertNotIn("modified by", message)
                self.assertNotIn("caused by", message)


if __name__ == "__main__":
    unittest.main()
