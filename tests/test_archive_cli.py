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


def invoke(root: Path, command: str = "rebuild-index") -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(
        ["--root", str(root), "--json", command],
        stdout=stdout,
        stderr=stderr,
        cwd=root,
    )
    assert stderr.getvalue() == ""
    return code, json.loads(stdout.getvalue())


class RebuildIndexTests(unittest.TestCase):
    def test_rebuild_is_deterministic_and_preserves_legacy_directories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            shutil.copytree(ROOT / "tests/fixtures/archive/legacy", archive)
            shutil.rmtree(archive / "2025-01-04-missing-summary")
            before = {
                path.relative_to(archive): path.read_bytes()
                for path in archive.rglob("*")
                if path.is_file() and path.name != "INDEX.md"
            }
            (archive / "INDEX.md").write_text("stale\n")
            first_code, first = invoke(root)
            self.assertEqual(first_code, 1)
            self.assertEqual(first["errors"][0]["code"], "UNKNOWN_STATE")

            shutil.copy(
                ROOT / "tests/fixtures/archive/legacy/INDEX.md", archive / "INDEX.md"
            )
            first_code, first = invoke(root)
            self.assertEqual(first_code, 0, first)
            self.assertFalse(first["data"]["changed"])
            index = (archive / "INDEX.md").read_bytes()
            second_code, second = invoke(root)
            self.assertEqual(second_code, 0, second)
            self.assertFalse(second["data"]["changed"])
            self.assertEqual((archive / "INDEX.md").read_bytes(), index)
            after = {
                path.relative_to(archive): path.read_bytes()
                for path in archive.rglob("*")
                if path.is_file() and path.name != "INDEX.md"
            }
            self.assertEqual(after, before)

    def test_validate_reports_stale_lines_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            shutil.copytree(ROOT / "tests/fixtures/archive/legacy", archive)
            shutil.rmtree(archive / "2025-01-04-missing-summary")
            index = archive / "INDEX.md"
            lines = index.read_text().splitlines()
            index.write_text("\n".join(lines[:2] + list(reversed(lines[2:]))) + "\n")
            before = index.read_bytes()
            code, result = invoke(root, "validate-index")
            self.assertEqual(code, 1)
            self.assertEqual(result["errors"][0]["code"], "ERROR_INDEX_STALE")
            self.assertEqual(result["errors"][0]["action"], "rebuild_index")
            self.assertTrue(result["data"]["differences"][0]["path"].startswith("/lines/"))
            self.assertEqual(index.read_bytes(), before)
            rebuilt, _ = invoke(root)
            self.assertEqual(rebuilt, 0)
            valid, result = invoke(root, "validate-index")
            self.assertEqual(valid, 0, result)
            self.assertTrue(result["data"]["valid"])

    def test_managed_terminal_metadata_rebuilds_deleted_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "sdd/archive"
            target = archive / "2025-02-03-managed"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/completed-terminal", target)
            machine = target / ".sdd"
            machine.mkdir()
            terminal = {
                "terminal_metadata_version": 1,
                "archive_date": "2025-02-03",
                "short_name": "managed",
                "source_status": "approved",
                "terminal_status": "completed",
                "timestamp": "2025-02-03T04:05:06Z",
                "summary": "Managed summary | rendered safely.",
                "destination_directory": "2025-02-03-managed",
                "source_snapshot": {
                    "snapshot_version": 1,
                    "proposal_sha256": "1" * 64,
                    "tasks_sha256": "2" * 64,
                    "snapshot_digest": "3" * 64,
                },
                "operation": {"kind": "archive", "operation_id": "managed-operation"},
            }
            (machine / "metadata.json").write_text(
                json.dumps({"terminal": terminal}, ensure_ascii=False, indent=2) + "\n"
            )
            self.assertFalse((archive / "INDEX.md").exists())
            code, result = invoke(root)
            self.assertEqual(code, 0, result)
            self.assertTrue(result["data"]["changed"])
            index = (archive / "INDEX.md").read_text()
            self.assertIn("managed | completed | Managed summary \\| rendered safely.", index)
            valid, validation = invoke(root, "validate-index")
            self.assertEqual(valid, 0, validation)


if __name__ == "__main__":
    unittest.main()
