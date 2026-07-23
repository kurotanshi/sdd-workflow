from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import (  # noqa: E402
    ArchiveRecord,
    load_legacy_archive_records,
    parse_legacy_index,
    render_archive_index,
    replace_archive_index,
)


FIXTURE = ROOT / "tests/fixtures/archive/legacy"


class LegacyArchiveAdapterTests(unittest.TestCase):
    def test_adapter_preserves_index_only_summary_and_does_not_write(self) -> None:
        before = {
            path.relative_to(FIXTURE): path.read_bytes()
            for path in FIXTURE.rglob("*")
            if path.is_file()
        }
        scan = load_legacy_archive_records(FIXTURE)
        self.assertEqual([item.short_name for item in scan.records], [
            "legacy-completed", "legacy"
        ])
        self.assertEqual(
            scan.records[0].summary,
            "Preserved summary with escaped | pipe and \\ slash.",
        )
        self.assertEqual(scan.records[0].source, "legacy")
        self.assertEqual([item.code for item in scan.diagnostics], ["UNKNOWN_STATE"])
        self.assertIn("missing-summary", scan.diagnostics[0].path)
        after = {
            path.relative_to(FIXTURE): path.read_bytes()
            for path in FIXTURE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)

    def test_duplicate_and_malformed_rows_are_ambiguous(self) -> None:
        rows, diagnostics = parse_legacy_index(
            "- 2025-01-02 | item | completed | one\n"
            "- malformed | row\n"
            "- 2025-01-02 | item | completed | two\n"
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual([item.code for item in diagnostics], ["AMBIGUOUS_STATE"])

    def test_renderer_orders_escapes_and_round_trips_legacy_fields(self) -> None:
        records = (
            ArchiveRecord(
                "2025-01-03-zeta", "zeta", "2025-01-03", "completed",
                "pipe | and slash \\ remain", "legacy",
            ),
            ArchiveRecord(
                "2025-01-02-alpha", "alpha", "2025-01-02", "completed",
                "first", "managed",
            ),
        )
        rendered = render_archive_index(records)
        self.assertEqual(
            rendered.decode(),
            "# SDD Archive\n\n"
            "- 2025-01-02 | alpha | completed | first\n"
            "- 2025-01-03 | zeta | completed | pipe \\| and slash \\\\ remain\n",
        )
        rows, diagnostics = parse_legacy_index(rendered.decode())
        self.assertEqual(diagnostics, ())
        self.assertEqual(rows[1][3], "pipe | and slash \\ remain")

    def test_atomic_index_replacement_is_idempotent(self) -> None:
        import tempfile

        records = load_legacy_archive_records(FIXTURE).records
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "archive"
            archive.mkdir()
            first = replace_archive_index(archive, records)
            first_bytes = (archive / "INDEX.md").read_bytes()
            second = replace_archive_index(archive, reversed(records))
            self.assertEqual(first, second)
            self.assertEqual((archive / "INDEX.md").read_bytes(), first_bytes)


if __name__ == "__main__":
    unittest.main()
