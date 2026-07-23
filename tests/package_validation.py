"""Dependency-free validation of the installable skill package."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/sdd-workflow"
SCRIPTS = PACKAGE / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sdd_core.cli import build_parser  # noqa: E402


def validate_package() -> None:
    required = {
        "SKILL.md",
        "agents/openai.yaml",
        "scripts/sdd",
        "scripts/sdd.py",
        "scripts/sdd_core/__init__.py",
        "scripts/sdd_core/active_metadata.py",
        "scripts/sdd_core/approval.py",
        "scripts/sdd_core/archive_model.py",
        "scripts/sdd_core/archive_index.py",
        "scripts/sdd_core/atomic_write.py",
        "scripts/sdd_core/cli.py",
        "scripts/sdd_core/diagnostics.py",
        "scripts/sdd_core/discovery.py",
        "scripts/sdd_core/doctor.py",
        "scripts/sdd_core/model.py",
        "scripts/sdd_core/managed_state.py",
        "scripts/sdd_core/parser_legacy.py",
        "scripts/sdd_core/parser_v1.py",
        "scripts/sdd_core/parser_v2.py",
        "scripts/sdd_core/scanner.py",
        "scripts/sdd_core/snapshot.py",
        "scripts/sdd_core/summary_input.py",
        "scripts/sdd_core/task_identity.py",
        "scripts/sdd_core/terminal_transitions.py",
        "scripts/sdd_core/transitions.py",
        "scripts/sdd_core/version.py",
    }
    files = {
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*")
        if path.is_file()
    }
    missing = required - files
    if missing:
        raise AssertionError(f"missing package files: {sorted(missing)}")
    forbidden = [
        name
        for name in files
        if "__pycache__" in name
        or name.endswith(".pyc")
        or Path(name).name in {"README.md", "CHANGELOG.md"}
    ]
    if forbidden:
        raise AssertionError(f"forbidden generated/user-doc files: {forbidden}")

    skill = (PACKAGE / "SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\nname: sdd-workflow\ndescription:"):
        raise AssertionError("invalid SKILL.md frontmatter")
    metadata = (PACKAGE / "agents/openai.yaml").read_text(encoding="utf-8")
    if "$sdd-workflow" not in metadata:
        raise AssertionError("openai.yaml default prompt must mention $sdd-workflow")

    if os.name == "posix":
        for executable in (SCRIPTS / "sdd", SCRIPTS / "sdd.py"):
            if not executable.stat().st_mode & stat.S_IXUSR:
                raise AssertionError(f"package entry point is not executable: {executable}")

    for source in SCRIPTS.rglob("*.py"):
        compile(source.read_text(encoding="utf-8"), str(source), "exec")

    parser = build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    commands = set(subparsers.choices)
    expected = {
        "validate", "list", "status", "abandon-preflight", "approve", "begin-revision",
        "complete-task"
        , "rebuild-index", "validate-index", "doctor", "archive", "abandon"
    }
    if commands != expected or "parse" in commands:
        raise AssertionError(f"unexpected public CLI commands: {sorted(commands)}")


def main() -> int:
    validate_package()
    print("package-validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
