from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import (  # noqa: E402
    SUMMARY_MAX_BYTES,
    SummaryInputError,
    fold_summary_for_index,
    read_summary,
)
from sdd_core.cli import UsageError, build_parser  # noqa: E402


class SummaryInputTests(unittest.TestCase):
    def test_inline_is_single_line_and_mutually_exclusive(self) -> None:
        self.assertEqual(read_summary(inline="中英 | summary", file_path=None), "中英 | summary")
        with self.assertRaises(SummaryInputError) as multiline:
            read_summary(inline="one\ntwo", file_path=None)
        self.assertEqual(multiline.exception.code, "ERROR_SUMMARY_INVALID")
        with self.assertRaises(UsageError):
            build_parser().parse_args([
                "archive", "item", "--expected-snapshot", "x",
                "--summary", "one", "--summary-file", "two",
            ])

    def test_file_preserves_original_and_folds_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.txt"
            path.write_bytes("第一行\r\nsecond | line\n".encode("utf-8"))
            value = read_summary(inline=None, file_path=str(path))
            self.assertEqual(value, "第一行\r\nsecond | line\n")
            self.assertEqual(
                fold_summary_for_index(value), "第一行 ⏎ second | line ⏎ "
            )

    def test_file_rejects_stdin_encoding_nul_empty_and_size(self) -> None:
        with self.assertRaises(SummaryInputError) as stdin:
            read_summary(inline=None, file_path="-")
        self.assertEqual(stdin.exception.code, "ERROR_SUMMARY_FILE_READ")
        cases = ((b"\xff", "ERROR_SUMMARY_FILE_ENCODING"), (b"\x00", "ERROR_SUMMARY_INVALID"), (b" \n", "ERROR_SUMMARY_INVALID"), (b"x" * (SUMMARY_MAX_BYTES + 1), "ERROR_SUMMARY_TOO_LARGE"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.txt"
            for data, code in cases:
                with self.subTest(code=code):
                    path.write_bytes(data)
                    with self.assertRaises(SummaryInputError) as caught:
                        read_summary(inline=None, file_path=str(path))
                    self.assertEqual(caught.exception.code, code)


if __name__ == "__main__":
    unittest.main()
