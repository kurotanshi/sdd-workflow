from __future__ import annotations

import base64
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import build_snapshot, canonical_snapshot_payload  # noqa: E402
from sdd_core.cli import main  # noqa: E402


class SnapshotTests(unittest.TestCase):
    def test_snapshot_v1_fixture_fixes_raw_hashes_and_payload_bytes(self) -> None:
        fixture = json.loads((ROOT / "tests/fixtures/snapshot-v1.json").read_text())
        manifest = build_snapshot(
            base64.b64decode(fixture["proposal_base64"]),
            base64.b64decode(fixture["tasks_base64"]),
        )
        self.assertEqual(manifest.to_dict(), fixture["expected"])
        self.assertEqual(
            canonical_snapshot_payload(manifest),
            fixture["expected_payload_ascii"].encode("ascii"),
        )

    def test_line_endings_bom_and_trailing_spaces_are_not_normalized(self) -> None:
        baseline = build_snapshot(b"same\n", b"tasks\n")
        crlf = build_snapshot(b"same\r\n", b"tasks\n")
        trailing = build_snapshot(b"same\n ", b"tasks\n")
        bom = build_snapshot(b"\xef\xbb\xbfsame\n", b"tasks\n")
        self.assertEqual(
            len(
                {
                    baseline.snapshot_digest,
                    crlf.snapshot_digest,
                    trailing.snapshot_digest,
                    bom.snapshot_digest,
                }
            ),
            4,
        )

    def test_status_json_contains_hashes_of_current_raw_artifacts(self) -> None:
        short_name = "valid-simple"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd" / short_name
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            stdout = io.StringIO()
            stderr = io.StringIO()
            exit_code = main(
                ["--root", str(root), "--json", "status", short_name],
                stdout=stdout,
                stderr=stderr,
                cwd=root,
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            envelope = json.loads(stdout.getvalue())
            expected = build_snapshot(
                (target / "proposal.md").read_bytes(),
                (target / "tasks.md").read_bytes(),
            )
            self.assertEqual(envelope["data"]["snapshot"], expected.to_dict())


if __name__ == "__main__":
    unittest.main()
