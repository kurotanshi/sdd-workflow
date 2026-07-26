from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import main  # noqa: E402


def invoke(root: Path | None, cwd: Path, arguments: list[str]) -> dict[str, object]:
    stdout = io.StringIO()
    prefix = [] if root is None else ["--root", str(root)]
    main(
        [*prefix, "--json", *arguments],
        stdout=stdout,
        stderr=io.StringIO(),
        cwd=cwd,
    )
    return json.loads(stdout.getvalue())


def copy_named_fixture(root: Path, name: str) -> Path:
    target = root / "sdd" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "tests/fixtures/baseline/valid-simple", target)
    proposal = target / "proposal.md"
    tasks = target / "tasks.md"
    proposal.write_text(proposal.read_text().replace("valid-simple", name, 1))
    tasks.write_text(tasks.read_text().replace("valid-simple", name, 1))
    return target


class TeamWorkflowTests(unittest.TestCase):
    def test_different_short_names_have_independent_snapshots_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            copy_named_fixture(root, "agent-one")
            copy_named_fixture(root, "agent-two")
            one = invoke(root, root, ["status", "agent-one"])["data"]
            two_before = invoke(root, root, ["status", "agent-two"])["data"]
            approved = invoke(root, root, [
                "approve", "agent-one", "--expected-snapshot",
                one["snapshot"]["snapshot_digest"],
            ])
            self.assertTrue(approved["ok"])
            two_after = invoke(root, root, ["status", "agent-two"])["data"]
            self.assertEqual(two_after["status"], "draft")
            self.assertEqual(two_after["snapshot"], two_before["snapshot"])
            self.assertFalse((root / "sdd/agent-two/.sdd").exists())

    def test_git_worktree_discovery_stays_in_the_selected_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            repository = temporary / "repository"
            worktree = temporary / "agent-worktree"
            repository.mkdir()
            copy_named_fixture(repository, "worktree-item")
            self._git(repository, "init", "-q")
            self._git(repository, "add", ".")
            self._git(
                repository,
                "-c", "user.name=workflow-test",
                "-c", "user.email=workflow-test@example.invalid",
                "commit", "-qm", "fixture",
            )
            self._git(repository, "worktree", "add", "-qb", "agent-worktree", str(worktree))
            nested = worktree / "nested/directory"
            nested.mkdir(parents=True)
            result = invoke(None, nested, ["status", "worktree-item"])
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["data"]["short_name"], "worktree-item")
            self.assertEqual(result["data"]["status"], "draft")

    def test_documented_boundary_does_not_claim_snapshot_is_a_lock(self) -> None:
        contract = (ROOT / "docs/team-operations.md").read_text(encoding="utf-8")
        self.assertIn("Use one active operator for a proposal at a time", contract)
        self.assertIn("rejects stale snapshots, but it does not provide a distributed lock", contract)
        self.assertIn("different proposal short name", contract)
        self.assertIn("separate Git worktree", contract)

    @staticmethod
    def _git(repository: Path, *arguments: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"git {' '.join(arguments)} failed: {result.stderr}")


if __name__ == "__main__":
    unittest.main()
