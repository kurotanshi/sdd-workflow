"""Deterministic project-root and active-candidate discovery primitives."""

from __future__ import annotations

import subprocess
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RootSource(str, Enum):
    EXPLICIT = "explicit"
    GIT = "git"
    UPWARD = "upward"


@dataclass(frozen=True, slots=True)
class ProjectRoot:
    path: Path
    source: RootSource


class ProjectDiscoveryError(RuntimeError):
    def __init__(self, code: str, action: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.action = action
        self.message = message


SHORT_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True, slots=True)
class ProposalPaths:
    project_root: Path
    sdd_root: Path
    directory: Path
    proposal: Path
    tasks: Path


class ProposalPathError(RuntimeError):
    def __init__(self, code: str, action: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.action = action
        self.message = message


def discover_project_root(
    *,
    explicit_root: str | Path | None = None,
    cwd: str | Path | None = None,
) -> ProjectRoot:
    start = Path.cwd() if cwd is None else Path(cwd)
    try:
        start = start.resolve(strict=True)
    except OSError as error:
        raise ProjectDiscoveryError(
            "ERROR_PROJECT_ROOT_NOT_FOUND",
            "select_project_root",
            f"Current directory is unavailable: {start}",
        ) from error
    if not start.is_dir():
        raise ProjectDiscoveryError(
            "ERROR_PROJECT_ROOT_NOT_FOUND",
            "select_project_root",
            f"Current path is not a directory: {start}",
        )

    if explicit_root is not None:
        candidate = Path(explicit_root)
        if not candidate.is_absolute():
            candidate = start / candidate
        return ProjectRoot(
            path=_require_project_root(candidate, label="Explicit root"),
            source=RootSource.EXPLICIT,
        )

    git_root = _git_worktree_root(start)
    if git_root is not None and _has_sdd_directory(git_root):
        return ProjectRoot(path=git_root, source=RootSource.GIT)

    for candidate in (start, *start.parents):
        if _has_sdd_directory(candidate):
            return ProjectRoot(path=candidate, source=RootSource.UPWARD)

    raise ProjectDiscoveryError(
        "ERROR_PROJECT_ROOT_NOT_FOUND",
        "select_project_root",
        f"No project root containing sdd/ was found from: {start}",
    )


def validate_short_name(short_name: str) -> str:
    if not isinstance(short_name, str) or not SHORT_NAME_PATTERN.fullmatch(short_name):
        raise ProposalPathError(
            "ERROR_INVALID_SHORT_NAME",
            "choose_short_name",
            f"Invalid proposal short name: {short_name!r}",
        )
    return short_name


def resolve_proposal_paths(project_root: str | Path, short_name: str) -> ProposalPaths:
    """Resolve direct project-local artifacts without following symlinks."""

    validate_short_name(short_name)
    try:
        root = Path(project_root).resolve(strict=True)
    except OSError as error:
        raise ProposalPathError(
            "ERROR_PROJECT_ROOT_NOT_FOUND",
            "select_project_root",
            f"Project root does not exist: {project_root}",
        ) from error
    sdd = root / "sdd"
    if sdd.is_symlink():
        raise _symlink_error(sdd)
    if not sdd.is_dir():
        raise ProposalPathError(
            "ERROR_PROJECT_ROOT_NOT_FOUND",
            "select_project_root",
            f"Project root does not contain sdd/: {root}",
        )
    sdd_resolved = sdd.resolve(strict=True)
    if not _is_within(sdd_resolved, root):
        raise _outside_error(sdd)

    directory = sdd / short_name
    if directory.is_symlink():
        raise _symlink_error(directory)
    if not directory.is_dir():
        raise ProposalPathError(
            "ERROR_PROPOSAL_NOT_FOUND",
            "create_or_select_proposal",
            f"Proposal directory was not found: {directory}",
        )
    directory_resolved = directory.resolve(strict=True)
    if not _is_within(directory_resolved, sdd_resolved):
        raise _outside_error(directory)

    artifacts: list[Path] = []
    for name in ("proposal.md", "tasks.md"):
        artifact = directory / name
        if artifact.is_symlink():
            raise _symlink_error(artifact)
        if not artifact.is_file():
            raise ProposalPathError(
                "ERROR_ARTIFACT_MISSING",
                "create_or_select_proposal",
                f"Required proposal artifact was not found: {artifact}",
            )
        resolved = artifact.resolve(strict=True)
        if not _is_within(resolved, directory_resolved):
            raise _outside_error(artifact)
        artifacts.append(resolved)

    return ProposalPaths(
        project_root=root,
        sdd_root=sdd_resolved,
        directory=directory_resolved,
        proposal=artifacts[0],
        tasks=artifacts[1],
    )


def list_active_proposal_paths(project_root: str | Path) -> tuple[ProposalPaths, ...]:
    """Return safe complete candidates in lexical short-name order."""

    try:
        root = Path(project_root).resolve(strict=True)
    except OSError as error:
        raise ProposalPathError(
            "ERROR_PROJECT_ROOT_NOT_FOUND",
            "select_project_root",
            f"Project root does not exist: {project_root}",
        ) from error
    sdd = root / "sdd"
    if sdd.is_symlink():
        raise _symlink_error(sdd)
    if not sdd.is_dir():
        raise ProposalPathError(
            "ERROR_PROJECT_ROOT_NOT_FOUND",
            "select_project_root",
            f"Project root does not contain sdd/: {root}",
        )

    candidates: list[ProposalPaths] = []
    for child in sorted(sdd.iterdir(), key=lambda item: item.name):
        if child.name == "archive" or not SHORT_NAME_PATTERN.fullmatch(child.name):
            continue
        if child.is_symlink():
            raise _symlink_error(child)
        if not child.is_dir():
            continue
        proposal = child / "proposal.md"
        tasks = child / "tasks.md"
        if proposal.is_symlink():
            raise _symlink_error(proposal)
        if tasks.is_symlink():
            raise _symlink_error(tasks)
        if not proposal.is_file() or not tasks.is_file():
            continue
        candidates.append(resolve_proposal_paths(root, child.name))
    return tuple(candidates)


def _require_project_root(candidate: Path, *, label: str) -> Path:
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ProjectDiscoveryError(
            "ERROR_PROJECT_ROOT_NOT_FOUND",
            "select_project_root",
            f"{label} does not exist: {candidate}",
        ) from error
    if not resolved.is_dir() or not _has_sdd_directory(resolved):
        raise ProjectDiscoveryError(
            "ERROR_PROJECT_ROOT_NOT_FOUND",
            "select_project_root",
            f"{label} does not contain an sdd/ directory: {resolved}",
        )
    return resolved


def _has_sdd_directory(candidate: Path) -> bool:
    return candidate.is_dir() and (candidate / "sdd").is_dir()


def _git_worktree_root(start: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    if not raw:
        return None
    try:
        root = Path(raw).resolve(strict=True)
    except OSError:
        return None
    return root if root.is_dir() else None


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _symlink_error(path: Path) -> ProposalPathError:
    return ProposalPathError(
        "ERROR_SYMLINK_UNSUPPORTED",
        "inspect_project_path",
        f"Symlinks are unsupported for proposal paths: {path}",
    )


def _outside_error(path: Path) -> ProposalPathError:
    return ProposalPathError(
        "ERROR_PATH_OUTSIDE_SDD",
        "inspect_project_path",
        f"Resolved proposal path is outside project-local sdd/: {path}",
    )
