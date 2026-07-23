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
