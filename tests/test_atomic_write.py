from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import atomic_replace_bytes  # noqa: E402


class AtomicWriteTests(unittest.TestCase):
    def test_replaces_bytes_and_preserves_existing_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact"
            target.write_bytes(b"before")
            target.chmod(0o640)
            atomic_replace_bytes(target, b"after")
            self.assertEqual(target.read_bytes(), b"after")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o640)
            self.assertEqual(list(target.parent.glob(".artifact.*.tmp")), [])

    def test_new_file_gets_private_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact"
            atomic_replace_bytes(target, b"value")
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_flush_fsync_and_replace_are_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact"
            target.write_bytes(b"before")
            with mock.patch("sdd_core.atomic_write.os.fsync", wraps=os.fsync) as fsync:
                with mock.patch(
                    "sdd_core.atomic_write.os.replace", wraps=os.replace
                ) as replace:
                    atomic_replace_bytes(target, b"after")
            fsync.assert_called_once()
            replace.assert_called_once()

    def test_replace_failure_preserves_target_and_cleans_temporary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact"
            target.write_bytes(b"before")
            with mock.patch(
                "sdd_core.atomic_write.os.replace", side_effect=OSError("injected")
            ):
                with self.assertRaises(OSError):
                    atomic_replace_bytes(target, b"after")
            self.assertEqual(target.read_bytes(), b"before")
            self.assertEqual(list(target.parent.glob(".artifact.*.tmp")), [])

    def test_rejects_symlink_target(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.write_bytes(b"before")
            link = root / "artifact"
            link.symlink_to(real)
            with self.assertRaises(OSError):
                atomic_replace_bytes(link, b"after")
            self.assertEqual(real.read_bytes(), b"before")


if __name__ == "__main__":
    unittest.main()
