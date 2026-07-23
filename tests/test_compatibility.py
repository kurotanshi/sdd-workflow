from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import (  # noqa: E402
    ENGINE_VERSION,
    diagnose_project,
    engine_generation,
    parse_engine_version,
)
from sdd_core.cli import main  # noqa: E402


class CompatibilityTests(unittest.TestCase):
    def test_v1_versioning_policy_covers_every_release_boundary(self) -> None:
        document = (
            ROOT / "docs/protocol/versioning-policy-v1.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Policy version: `1.0.0`", document)
        for heading in (
            "## 1. Independent version axes",
            "## 2. Semantic Versioning classification",
            "## 3. Deprecation policy",
            "## 4. Proposal schema support",
            "## 5. Wire and machine-envelope support",
            "## 6. Migration release gate",
            "## 7. Rollback policy",
            "## 8. Release evidence",
        ):
            with self.subTest(heading=heading):
                self.assertIn(heading, document)
        for term in (
            "PATCH",
            "MINOR",
            "MAJOR",
            "implicit/explicit Schema v1 and explicit Schema v2",
            "`direct`",
            "`finish-or-abandon`",
            "`restore-backup`",
            "`forward-recovery`",
            "Deleting `.sdd`",
        ):
            with self.subTest(term=term):
                self.assertIn(term, document)

    def test_portable_compatibility_matrix_is_fail_closed(self) -> None:
        document = (ROOT / "docs/compatibility.md").read_text(encoding="utf-8")
        for fact in (
            "| OS | macOS and Linux/Ubuntu",
            "| Python | CPython 3.11",
            "| Agent host | Claude Code Skills and Codex Skills",
            "| Agent model | Model identity is not a runtime compatibility axis",
            "| Proposal schema | implicit/explicit v1 and explicit v2",
            "`RUNTIME_AMBIGUOUS`",
            "`RUNTIME_HANDSHAKE_FAILED`",
            "`RUNTIME_INCOMPATIBLE`",
            "`RUNTIME_SKILL_VERSION_SKEW`",
            "no fallback to bundled or PATH runtime",
            "Agent host/model behavior remains covered",
            "install-methods.md",
            "conformance/install-channels-v1.json",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, document)

    def test_v1_security_scope_migration_and_rollback_are_explicit(self) -> None:
        documents = {
            "security": (
                ROOT / "docs/security-trust-model.md"
            ).read_text(encoding="utf-8"),
            "non_goals": (
                ROOT / "docs/non-goals-v1.md"
            ).read_text(encoding="utf-8"),
            "migration": (
                ROOT / "docs/migration-v1.md"
            ).read_text(encoding="utf-8"),
            "rollback": (
                ROOT / "docs/rollback-v1.md"
            ).read_text(encoding="utf-8"),
        }
        for term in (
            "cooperative local change-control protocol",
            "Hashes, timestamps, writer strings",
            "MUST NOT be interpreted as authenticated identity",
            "no lock, lease",
            "credentials",
            "absolute user paths",
        ):
            with self.subTest(security=term):
                self.assertIn(term, documents["security"])
        for term in (
            "Schema v3",
            "Locking, leases",
            "Web UI",
            "external-platform",
            "Multi-Agent",
        ):
            with self.subTest(non_goal=term):
                self.assertIn(term, documents["non_goals"])
        for term in (
            "does not rewrite proposal data",
            "Direct package upgrade",
            "scripts/discover-runtime.py",
            "rollback-v1.md",
        ):
            with self.subTest(migration=term):
                self.assertIn(term, documents["migration"])
        for term in (
            "class `direct`",
            "`finish-or-abandon`",
            "`restore-backup`",
            "`forward-recovery`",
            "does not",
        ):
            with self.subTest(rollback=term):
                self.assertIn(term, documents["rollback"])

    def test_engine_version_and_generation_are_strict(self) -> None:
        self.assertEqual(ENGINE_VERSION, "0.6.0")
        self.assertEqual(parse_engine_version("0.5.12"), (0, 5, 12))
        self.assertEqual(engine_generation("0.5.12"), (0, 5))
        for invalid in ("v0.5.0", "0.5", "0.5.0-dev", "00.5.0"):
            self.assertIsNone(parse_engine_version(invalid))

    def test_doctor_reports_only_evidenced_writer_generation_skew(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "sdd/valid-simple"
            target.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
            status = self._invoke(root, ["status", "valid-simple"])["data"]
            self._invoke(root, [
                "approve", "valid-simple", "--expected-snapshot",
                status["snapshot"]["snapshot_digest"],
            ])
            metadata_path = target / ".sdd/metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["writer"]["version"] = "0.7.0"
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            findings = diagnose_project(root)
            skew = [item for item in findings if item.code == "ENGINE_VERSION_SKEW"]
            self.assertEqual(len(skew), 1)
            self.assertEqual(skew[0].action, "use_compatible_engine")
            self.assertIn("0.7.0", skew[0].message)
            self.assertNotIn("author", skew[0].message.lower())

    def test_current_engine_reads_v1_and_rejects_future_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root / "sdd/current-v1"
            future = root / "sdd/future-v3"
            current.parent.mkdir(parents=True)
            shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", current)
            (current / "proposal.md").write_text(
                (current / "proposal.md").read_text().replace("valid-simple", "current-v1", 1)
            )
            shutil.copytree(ROOT / "tests/fixtures/schema-v2/future-version", future)
            current_result = self._invoke(root, ["status", "current-v1"])
            future_result = self._invoke(root, ["status", "future-v3"])
            self.assertTrue(current_result["ok"])
            self.assertEqual(
                future_result["errors"][0]["code"],
                "ERROR_UNSUPPORTED_SCHEMA_VERSION",
            )

    @staticmethod
    def _invoke(root: Path, arguments: list[str]) -> dict[str, object]:
        import io

        stdout = io.StringIO()
        main(
            ["--root", str(root), "--json", *arguments],
            stdout=stdout,
            stderr=io.StringIO(),
            cwd=root,
        )
        return json.loads(stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
