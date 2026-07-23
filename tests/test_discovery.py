from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import (  # noqa: E402
    ProjectDiscoveryError,
    ProposalPathError,
    RootSource,
    discover_project_root,
    list_active_proposal_paths,
    resolve_proposal_paths,
    validate_short_name,
)


class ProjectDiscoveryTests(unittest.TestCase):
    def test_explicit_then_git_then_upward_then_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            project = temporary / "project"
            nested = project / "one/two"
            (project / "sdd").mkdir(parents=True)
            nested.mkdir(parents=True)

            explicit = discover_project_root(explicit_root=project, cwd=nested)
            self.assertEqual(explicit.path, project.resolve())
            self.assertIs(explicit.source, RootSource.EXPLICIT)

            with mock.patch(
                "sdd_core.discovery._git_worktree_root", return_value=project.resolve()
            ):
                git = discover_project_root(cwd=nested)
            self.assertEqual(git.path, project.resolve())
            self.assertIs(git.source, RootSource.GIT)

            upward = discover_project_root(cwd=nested)
            self.assertEqual(upward.path, project.resolve())
            self.assertIs(upward.source, RootSource.UPWARD)

            empty = temporary / "empty"
            empty.mkdir()
            with self.assertRaises(ProjectDiscoveryError) as caught:
                discover_project_root(cwd=empty)
            self.assertEqual(caught.exception.code, "ERROR_PROJECT_ROOT_NOT_FOUND")

    def test_invalid_explicit_root_never_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            (project / "sdd").mkdir(parents=True)
            with self.assertRaises(ProjectDiscoveryError):
                discover_project_root(explicit_root=project / "missing", cwd=project)


class ProposalPathSecurityTests(unittest.TestCase):
    def test_short_name_contract(self) -> None:
        for value in ("a", "add-feature", "v2-change-", "123"):
            self.assertEqual(validate_short_name(value), value)
        for value in ("", "..", "../escape", "a/b", r"a\b", "-leading", "Upper", "a.b"):
            with self.subTest(value=value), self.assertRaises(ProposalPathError) as caught:
                validate_short_name(value)
            self.assertEqual(caught.exception.code, "ERROR_INVALID_SHORT_NAME")

    def test_proposal_directory_and_artifact_symlinks_fail_before_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "project"
            outside = base / "outside"
            (root / "sdd").mkdir(parents=True)
            outside.mkdir()
            (outside / "proposal.md").write_bytes(b"\xffoutside")
            (outside / "tasks.md").write_bytes(b"\xffoutside")

            (root / "sdd/linked").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ProposalPathError) as caught:
                resolve_proposal_paths(root, "linked")
            self.assertEqual(caught.exception.code, "ERROR_SYMLINK_UNSUPPORTED")

            artifact_link = root / "sdd/artifact-link"
            artifact_link.mkdir()
            (artifact_link / "proposal.md").symlink_to(outside / "proposal.md")
            (artifact_link / "tasks.md").write_text("tasks", encoding="utf-8")
            with self.assertRaises(ProposalPathError) as caught:
                resolve_proposal_paths(root, "artifact-link")
            self.assertEqual(caught.exception.code, "ERROR_SYMLINK_UNSUPPORTED")

    def test_sdd_symlink_and_missing_artifact_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            real_sdd = base / "real-sdd"
            real_sdd.mkdir()
            linked_root = base / "linked-root"
            linked_root.mkdir()
            (linked_root / "sdd").symlink_to(real_sdd, target_is_directory=True)
            with self.assertRaises(ProposalPathError) as caught:
                resolve_proposal_paths(linked_root, "anything")
            self.assertEqual(caught.exception.code, "ERROR_SYMLINK_UNSUPPORTED")

            root = base / "project"
            candidate = root / "sdd/incomplete"
            candidate.mkdir(parents=True)
            (candidate / "proposal.md").write_text("proposal", encoding="utf-8")
            with self.assertRaises(ProposalPathError) as caught:
                resolve_proposal_paths(root, "incomplete")
            self.assertEqual(caught.exception.code, "ERROR_ARTIFACT_MISSING")

    def test_candidate_listing_is_sorted_and_excludes_archive_and_incomplete(self) -> None:
        fixture = ROOT / "tests/fixtures/baseline/ambiguous-active"
        candidates = list_active_proposal_paths(fixture)
        self.assertEqual(
            [item.directory.name for item in candidates],
            ["alpha-change", "beta-change"],
        )


if __name__ == "__main__":
    unittest.main()
