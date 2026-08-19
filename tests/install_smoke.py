"""Checkout and isolated-package smoke shared by local and CI platform runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/sdd-workflow"


def run_smoke(expected_platform: str) -> None:
    actual_platform = {"Darwin": "macos", "Linux": "linux"}.get(platform.system())
    if actual_platform != expected_platform:
        raise AssertionError(
            f"platform mismatch: expected {expected_platform}, running {actual_platform}"
        )

    checkout = _run_version(PACKAGE / "scripts/sdd.py", cwd=ROOT)
    _assert_version(checkout)

    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        installed = temporary / "installed-skills/sdd-workflow"
        shutil.copytree(
            PACKAGE,
            installed,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        outside_checkout = temporary / "consumer-project"
        outside_checkout.mkdir()
        installed_result = _run_version(
            installed / "scripts/sdd.py",
            cwd=outside_checkout,
        )
        _assert_version(installed_result)
        _assert_discovery(installed, outside_checkout)

        launcher = subprocess.run(
            [str(installed / "scripts/sdd"), "--version"],
            cwd=outside_checkout,
            env=_clean_environment(),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if launcher.returncode != 0 or "sdd-workflow 1.2.0" not in launcher.stdout:
            raise AssertionError(
                f"installed launcher failed: {launcher.returncode} {launcher.stderr}"
            )
        _tool_directory_smoke(temporary, outside_checkout)
        _dev_link_smoke(temporary, outside_checkout)
        _release_package_smoke(temporary, outside_checkout)


def _tool_directory_smoke(temporary: Path, consumer: Path) -> None:
    for tool, relative in (
        ("claude", Path("claude-home/skills/sdd-workflow")),
        ("codex", Path("agents-home/skills/sdd-workflow")),
    ):
        installed = temporary / relative
        shutil.copytree(PACKAGE, installed)
        _assert_version(_run_version(installed / "scripts/sdd.py", cwd=consumer))
        _assert_discovery(installed, consumer)
        if not (installed / "SKILL.md").is_file():
            raise AssertionError(f"{tool} install lacks SKILL.md")
        if tool == "codex" and not (installed / "agents/openai.yaml").is_file():
            raise AssertionError("Codex install lacks agents/openai.yaml")


def _dev_link_smoke(temporary: Path, consumer: Path) -> None:
    claude_dir = temporary / "dev-link/claude-skills"
    codex_dir = temporary / "dev-link/codex-skills"
    environment = _clean_environment()
    environment.update(
        {
            "CLAUDE_SKILLS_DIR": str(claude_dir),
            "CODEX_SKILLS_DIR": str(codex_dir),
        }
    )
    command = [str(ROOT / "scripts/link-dev.sh")]
    for _ in range(2):
        result = subprocess.run(
            command,
            cwd=consumer,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"dev link failed: {result.stderr}")
    for directory in (claude_dir, codex_dir):
        link = directory / "sdd-workflow"
        if not link.is_symlink() or link.resolve() != PACKAGE.resolve():
            raise AssertionError(f"invalid dev link: {link}")
        _assert_version(_run_version(link / "scripts/sdd.py", cwd=consumer))
        _assert_discovery(link, consumer)
    unlink = subprocess.run(
        [*command, "--unlink"],
        cwd=consumer,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if unlink.returncode != 0 or any(
        (directory / "sdd-workflow").exists() for directory in (claude_dir, codex_dir)
    ):
        raise AssertionError(f"dev unlink failed: {unlink.stderr}")

    collision = claude_dir / "sdd-workflow"
    collision.mkdir()
    rejected = subprocess.run(
        [*command, "--claude-only"],
        cwd=consumer,
        env=environment,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if rejected.returncode == 0 or not collision.is_dir() or collision.is_symlink():
        raise AssertionError("dev link did not preserve an existing destination")


def _release_package_smoke(temporary: Path, consumer: Path) -> None:
    artifacts = [temporary / "release-a.tar.gz", temporary / "release-b.tar.gz"]
    for artifact in artifacts:
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/build-release-package.py"),
                "--output",
                str(artifact),
            ],
            cwd=consumer,
            env=_clean_environment(),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(f"release build failed: {result.stderr}")
    digests = [hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts]
    if digests[0] != digests[1]:
        raise AssertionError("release package is not byte-deterministic")
    extracted = temporary / "release-install"
    extracted.mkdir()
    with tarfile.open(artifacts[0], "r:gz") as archive:
        members = archive.getmembers()
        if not members or any(
            not member.name.startswith("sdd-workflow/")
            or member.issym()
            or member.islnk()
            for member in members
        ):
            raise AssertionError("release package contains an unsafe member")
        for member in members:
            target = extracted / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise AssertionError(f"release package member is not a file: {member.name}")
            target.write_bytes(source.read())
            target.chmod(member.mode)
    installed = extracted / "sdd-workflow"
    _assert_version(_run_version(installed / "scripts/sdd.py", cwd=consumer))
    _assert_discovery(installed, consumer)
    if any(path.name == "__pycache__" or path.suffix == ".pyc" for path in installed.rglob("*")):
        raise AssertionError("release package contains generated Python files")


def _run_version(script: Path, *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), "--json", "--version"],
        cwd=cwd,
        env=_clean_environment(),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _assert_version(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode != 0 or result.stderr:
        raise AssertionError(
            f"sdd.py --version failed: {result.returncode} {result.stderr}"
        )
    envelope = json.loads(result.stdout)
    if not envelope["ok"] or envelope["data"] != {
        "engine_version": "1.2.0",
        "maximum_schema_version": 2,
        "minimum_schema_version": 1,
    }:
        raise AssertionError(f"unexpected version envelope: {envelope}")


def _assert_discovery(package: Path, cwd: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(package / "scripts/discover-runtime.py")],
        cwd=cwd,
        env=_clean_environment(),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0 or result.stderr:
        raise AssertionError(
            f"runtime discovery failed: {result.returncode} {result.stderr}"
        )
    envelope = json.loads(result.stdout)
    if (
        not envelope["ok"]
        or envelope["runtime"]["handshake"]["distribution_id"] != "sdd-workflow"
    ):
        raise AssertionError(f"unexpected discovery envelope: {envelope}")


def _clean_environment() -> dict[str, str]:
    allowed = ("PATH", "LANG", "LC_ALL", "SYSTEMROOT", "WINDIR")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-platform", choices=("macos", "linux"), required=True)
    arguments = parser.parse_args()
    run_smoke(arguments.expect_platform)
    print(f"install-smoke ({arguments.expect_platform}): PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
