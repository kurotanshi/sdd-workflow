from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/sdd-workflow"
MATRIX = ROOT / "conformance/install-channels-v1.json"
sys.path.insert(0, str(PACKAGE / "scripts"))

from sdd_core.runtime_discovery import (  # noqa: E402
    RuntimeDiscoveryError,
    discover_runtime,
)


class InstallChannelTests(unittest.TestCase):
    def test_matrix_covers_every_roadmap_channel(self) -> None:
        matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        self.assertEqual(matrix["matrix_version"], 1)
        channels = {item["id"]: item for item in matrix["channels"]}
        self.assertEqual(
            set(channels),
            {
                "claude-code",
                "codex",
                "legacy",
                "manual-copy",
                "native-installer",
                "third-party-installer",
                "dev-link",
            },
        )
        self.assertEqual(
            channels["claude-code"]["host_load_path"],
            "$HOME/.claude/skills/sdd-workflow",
        )
        self.assertEqual(
            channels["codex"]["host_load_path"],
            "$HOME/.agents/skills/sdd-workflow",
        )
        self.assertEqual(channels["legacy"]["support"], "migration-only")
        self.assertEqual(
            channels["third-party-installer"]["host_loading"],
            "must-be-verified",
        )
        self.assertEqual(channels["dev-link"]["support"], "development-only")

    def test_every_complete_copy_layout_passes_runtime_discovery(self) -> None:
        matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        copy_channels = [
            item["id"]
            for item in matrix["channels"]
            if item["package_layout"] == "complete-directory"
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for channel in copy_channels:
                with self.subTest(channel=channel):
                    installed = root / channel / "sdd-workflow"
                    shutil.copytree(PACKAGE, installed)
                    result = discover_runtime(installed)
                    self.assertEqual(result["source"], "package-local")
                    self.assertEqual(
                        result["handshake"]["distribution_id"],
                        "sdd-workflow",
                    )

    def test_dev_link_resolves_the_complete_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            link = Path(directory) / "host-skills/sdd-workflow"
            link.parent.mkdir(parents=True)
            link.symlink_to(PACKAGE, target_is_directory=True)
            result = discover_runtime(link)
        self.assertEqual(Path(result["resolved_path"]), (PACKAGE / "scripts/sdd.py").resolve())

    def test_legacy_partial_copies_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            incomplete = Path(directory) / "legacy-skill"
            incomplete.mkdir()
            shutil.copy2(PACKAGE / "SKILL.md", incomplete / "SKILL.md")
            with self.assertRaises(RuntimeDiscoveryError) as failure:
                discover_runtime(incomplete)
        self.assertEqual(failure.exception.code, "RUNTIME_INCOMPATIBLE")


if __name__ == "__main__":
    unittest.main()
