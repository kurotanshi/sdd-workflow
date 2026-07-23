from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills/sdd-workflow/scripts/sdd.py"
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import load_archive_records, replace_archive_index  # noqa: E402
from sdd_core.cli import main  # noqa: E402


def invoke(root: Path, arguments: list[str]) -> tuple[int, dict[str, object]]:
    stdout = io.StringIO()
    code = main(
        ["--root", str(root), "--json", *arguments],
        stdout=stdout,
        stderr=io.StringIO(),
        cwd=root,
    )
    return code, json.loads(stdout.getvalue())


def prepare_complete(root: Path, name: str) -> str:
    target = root / "sdd" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
    proposal = target / "proposal.md"
    tasks = target / "tasks.md"
    proposal.write_text(proposal.read_text().replace("valid-simple", name, 1))
    tasks.write_text(tasks.read_text().replace("valid-simple", name, 1))
    status = invoke(root, ["status", name])[1]["data"]
    code, result = invoke(root, [
        "approve", name, "--expected-snapshot", status["snapshot"]["snapshot_digest"],
    ])
    if code != 0:
        raise AssertionError(result)
    status = invoke(root, ["status", name])[1]["data"]
    task = status["tasks"][1]
    code, result = invoke(root, [
        "complete-task", name, "2",
        "--expected-task-digest", task["task_digest"],
        "--expected-snapshot", status["snapshot"]["snapshot_digest"],
    ])
    if code != 0:
        raise AssertionError(result)
    return invoke(root, ["status", name])[1]["data"]["snapshot"]["snapshot_digest"]


def start_cli(root: Path, arguments: list[str]) -> subprocess.Popen[str]:
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.Popen(
        [sys.executable, str(CLI), "--root", str(root), "--json", *arguments],
        cwd=root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class ConcurrencyTests(unittest.TestCase):
    def test_concurrent_distinct_archives_preserve_authority_and_rebuild_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshots = {
                name: prepare_complete(root, name) for name in ("agent-alpha", "agent-beta")
            }
            processes = [
                start_cli(root, [
                    "archive", name,
                    "--expected-snapshot", snapshots[name],
                    "--summary", f"completed {name}",
                ])
                for name in snapshots
            ]
            results = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=20)
                self.assertEqual(stderr, "")
                results.append((process.returncode, json.loads(stdout)))
            for code, result in results:
                self.assertIn(code, (0, 1), result)
                if code == 1:
                    self.assertEqual(
                        result["errors"][0]["code"],
                        "COMMITTED_DERIVED_ARTIFACT_STALE",
                    )
                    self.assertTrue(result["data"]["committed"])

            archive_root = root / "sdd/archive"
            scan = load_archive_records(archive_root)
            self.assertEqual(scan.diagnostics, ())
            self.assertEqual(
                {item.short_name for item in scan.records},
                {"agent-alpha", "agent-beta"},
            )
            self.assertFalse((root / "sdd/agent-alpha").exists())
            self.assertFalse((root / "sdd/agent-beta").exists())

            validate_code, _ = invoke(root, ["validate-index"])
            if validate_code != 0:
                rebuild_code, rebuild = invoke(root, ["rebuild-index"])
                self.assertEqual(rebuild_code, 0, rebuild)
            self.assertEqual(invoke(root, ["validate-index"])[0], 0)
            self.assertEqual(invoke(root, ["doctor"])[0], 0)

    def test_parallel_rebuilds_are_atomic_and_converge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("rebuild-alpha", "rebuild-beta"):
                snapshot = prepare_complete(root, name)
                code, result = invoke(root, [
                    "archive", name, "--expected-snapshot", snapshot,
                    "--summary", f"completed {name}",
                ])
                self.assertEqual(code, 0, result)
            processes = [start_cli(root, ["rebuild-index"]) for _ in range(6)]
            for process in processes:
                stdout, stderr = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, (stdout, stderr))
                self.assertTrue(json.loads(stdout)["ok"])
            self.assertEqual(invoke(root, ["validate-index"])[0], 0)
            self.assertFalse(list((root / "sdd/archive").glob(".*.tmp")))

    def test_stale_scan_overwrite_is_detected_and_reconstructed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = prepare_complete(root, "stale-alpha")
            self.assertEqual(invoke(root, [
                "archive", "stale-alpha", "--expected-snapshot", first,
                "--summary", "first",
            ])[0], 0)
            archive_root = root / "sdd/archive"
            stale_scan = load_archive_records(archive_root)
            self.assertEqual(len(stale_scan.records), 1)

            second = prepare_complete(root, "stale-beta")
            self.assertEqual(invoke(root, [
                "archive", "stale-beta", "--expected-snapshot", second,
                "--summary", "second",
            ])[0], 0)
            replace_archive_index(archive_root, stale_scan.records)
            code, stale = invoke(root, ["validate-index"])
            self.assertEqual(code, 1)
            self.assertEqual(stale["errors"][0]["code"], "ERROR_INDEX_STALE")
            self.assertEqual(len(load_archive_records(archive_root).records), 2)
            self.assertEqual(invoke(root, ["rebuild-index"])[0], 0)
            self.assertEqual(invoke(root, ["validate-index"])[0], 0)


if __name__ == "__main__":
    unittest.main()
