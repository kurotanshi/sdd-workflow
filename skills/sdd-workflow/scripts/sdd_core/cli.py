"""Non-interactive read-only command adapter."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence, TextIO

from .diagnostics import Diagnostic, Severity
from .discovery import (
    ProjectDiscoveryError,
    ProposalPathError,
    ProposalPaths,
    discover_project_root,
    list_active_proposal_paths,
    resolve_proposal_paths,
)
from .model import ParseOutcome
from .parser_v1 import (
    SUPPORTED_SCHEMA_VERSIONS,
    parse_with_schema,
    select_schema_from_document,
)
from .scanner import scan_tasks
from .snapshot import SnapshotManifest, build_snapshot
from .active_metadata import ActiveMetadataError, parse_active_metadata
from .approval import (
    ApprovalManifestError,
    approval_manifest_sha256,
    compare_approval_manifests,
    parse_approval_manifest,
    project_approval_manifest,
)
from .transitions import TransitionError, approve_proposal, begin_revision, complete_task
from .managed_state import ManagedStateError, compare_attested_state
from .task_identity import task_digest
from .archive_model import load_archive_records
from .archive_index import rebuild_archive_index, validate_archive_index
from .archive_recovery import (
    RepairPreflight,
    execute_archive_repair,
    preflight_archive_repair,
    validate_repairable_target,
)
from .doctor import (
    collect_environment_evidence,
    diagnose_project,
    diagnose_runtime_package,
)
from .summary_input import SummaryInputError
from .summary_input import read_summary
from .terminal_transitions import (
    commit_terminal_transition,
    find_committed_terminal_retry,
    resume_staged_terminal_transition,
    validate_abandon,
    validate_archive,
)
from .version import ENGINE_VERSION
from .runtime_identity import CLI_OUTPUT_VERSION, runtime_handshake


OUTPUT_VERSION = CLI_OUTPUT_VERSION


_ACTION_BY_CODE = {
    "ERROR_PROJECT_ROOT_NOT_FOUND": "select_project_root",
    "ERROR_INVALID_SHORT_NAME": "choose_short_name",
    "ERROR_PROPOSAL_NOT_FOUND": "create_or_select_proposal",
    "ERROR_ARTIFACT_MISSING": "create_or_select_proposal",
    "ERROR_PATH_OUTSIDE_SDD": "inspect_project_path",
    "ERROR_SYMLINK_UNSUPPORTED": "inspect_project_path",
    "ERROR_UNSUPPORTED_SCHEMA_VERSION": "use_supported_engine",
    "ERROR_LEGACY_MUTATION_UNSUPPORTED": "upgrade_or_recreate_proposal",
    "ERROR_ARTIFACT_ENCODING": "fix_artifact_format",
    "ERROR_USAGE": "fix_command_arguments",
    "ERROR_INTERNAL": "report_internal_error",
    "ERROR_COMMAND_NOT_READY": "upgrade_engine",
    "ERROR_INVALID_SOURCE_STATE": "refresh_status",
    "ERROR_SNAPSHOT_MISMATCH": "refresh_status",
    "ERROR_STATUS_FIELD_AMBIGUOUS": "fix_artifact_format",
    "ERROR_MACHINE_METADATA_INVALID": "inspect_machine_metadata",
    "ERROR_METADATA_STATE_MISMATCH": "inspect_machine_metadata",
}


@dataclass(frozen=True, slots=True)
class CliIssue:
    code: str
    action: str
    message: str
    severity: str
    path: str | None = None
    line: int | None = None
    column: int | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "action": self.action,
            "message": self.message,
            "severity": self.severity,
        }
        if self.path is not None:
            value["path"] = self.path
        if self.line is not None:
            value["line"] = self.line
        if self.column is not None:
            value["column"] = self.column
        return value

    @property
    def sort_key(self) -> tuple[str, int, int, str]:
        return (
            self.path or "",
            self.line or 0,
            self.column or 0,
            self.code,
        )


@dataclass(frozen=True, slots=True)
class CommandResult:
    command: str
    data: dict[str, Any]
    warnings: tuple[CliIssue, ...] = ()
    errors: tuple[CliIssue, ...] = ()
    exit_code: int = 0

    def __post_init__(self) -> None:
        if tuple(sorted(self.warnings, key=lambda item: item.sort_key)) != self.warnings:
            raise ValueError("CLI warnings must use deterministic order")
        if tuple(sorted(self.errors, key=lambda item: item.sort_key)) != self.errors:
            raise ValueError("CLI errors must use deterministic order")

    @property
    def ok(self) -> bool:
        return not self.errors and self.exit_code == 0

    def envelope(self) -> dict[str, Any]:
        return {
            "output_version": OUTPUT_VERSION,
            "command": self.command,
            "ok": self.ok,
            "warnings": [item.to_dict() for item in self.warnings],
            "errors": [item.to_dict() for item in self.errors],
            "data": self.data,
        }


class UsageError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ParsedProposal:
    outcome: ParseOutcome
    snapshot: SnapshotManifest | None


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="sdd.py", add_help=True)
    parser.add_argument("--root")
    parser.add_argument("--json", action="store_true", dest="json_mode")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--handshake", action="store_true")
    commands = parser.add_subparsers(dest="command")

    validate = commands.add_parser("validate")
    validate_target = validate.add_mutually_exclusive_group(required=True)
    validate_target.add_argument("short_name", nargs="?")
    validate_target.add_argument("--all", action="store_true", dest="validate_all")

    list_parser = commands.add_parser("list")
    list_parser.add_argument("--state", choices=("active",), required=True)

    status = commands.add_parser("status")
    status.add_argument("short_name")

    preflight = commands.add_parser("abandon-preflight")
    preflight.add_argument("short_name")
    approve = commands.add_parser("approve")
    approve.add_argument("short_name")
    approve.add_argument("--expected-snapshot", required=True)
    approve.add_argument("--establish-manifest", action="store_true")
    revision = commands.add_parser("begin-revision")
    revision.add_argument("short_name")
    revision.add_argument("--expected-snapshot", required=True)
    completion = commands.add_parser("complete-task")
    completion.add_argument("short_name")
    completion.add_argument("task_number", type=int)
    completion.add_argument("--expected-task-digest", required=True)
    completion.add_argument("--expected-snapshot", required=True)
    rebuild = commands.add_parser("rebuild-index")
    rebuild.add_argument("--directory")
    rebuild.add_argument("--summary")
    commands.add_parser("validate-index")
    commands.add_parser("doctor")
    repair = commands.add_parser("repair-archive-record")
    repair.add_argument("directory_name")
    repair.add_argument("--terminal-status", choices=("completed", "abandoned"))
    repair.add_argument("--summary")
    repair.add_argument("--expected-proposal-sha256")
    repair.add_argument("--expected-tasks-sha256")
    for terminal_command in ("archive", "abandon"):
        terminal = commands.add_parser(terminal_command)
        terminal.add_argument("short_name")
        terminal.add_argument("--expected-snapshot", required=True)
        summary = terminal.add_mutually_exclusive_group(required=True)
        summary.add_argument("--summary")
        summary.add_argument("--summary-file")
        terminal.add_argument("--dry-run", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    cwd: str | Path | None = None,
) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    output = sys.stdout if stdout is None else stdout
    error_output = sys.stderr if stderr is None else stderr
    json_requested = "--json" in arguments
    try:
        namespace = build_parser().parse_args(arguments)
        selectors = sum(
            (
                bool(namespace.version),
                bool(namespace.handshake),
                namespace.command is not None,
            )
        )
        if selectors != 1:
            raise UsageError(
                "exactly one command, --version, or --handshake is required"
            )
        result = execute(namespace, cwd=cwd)
    except UsageError as error:
        result = _error_result(
            "usage",
            "ERROR_USAGE",
            "fix_command_arguments",
            str(error),
            exit_code=2,
        )
    except (ProjectDiscoveryError, ProposalPathError) as error:
        result = _error_result(
            _command_hint(arguments),
            error.code,
            error.action,
            error.message,
            exit_code=1,
        )
    except UnicodeDecodeError:
        result = _error_result(
            _command_hint(arguments),
            "ERROR_ARTIFACT_ENCODING",
            "fix_artifact_format",
            "Proposal artifacts must be valid UTF-8",
            exit_code=1,
        )
    except (
        TransitionError,
        ActiveMetadataError,
        ApprovalManifestError,
        ManagedStateError,
        SummaryInputError,
    ) as error:
        result = _error_result(
            _command_hint(arguments),
            error.code,
            error.action,
            error.message,
            exit_code=1,
            data=getattr(error, "data", None),
        )
    except Exception:
        result = _error_result(
            _command_hint(arguments),
            "ERROR_INTERNAL",
            "report_internal_error",
            "Unexpected internal error",
            exit_code=70,
        )

    if json_requested:
        json.dump(
            result.envelope(),
            output,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        output.write("\n")
    else:
        _write_human(result, stdout=output, stderr=error_output)
    return result.exit_code


def execute(namespace: argparse.Namespace, *, cwd: str | Path | None) -> CommandResult:
    if namespace.handshake:
        return CommandResult(
            command="handshake",
            data=runtime_handshake(),
        )
    if namespace.version:
        return CommandResult(
            command="version",
            data={
                "engine_version": ENGINE_VERSION,
                "minimum_schema_version": min(SUPPORTED_SCHEMA_VERSIONS),
                "maximum_schema_version": max(SUPPORTED_SCHEMA_VERSIONS),
            },
        )

    root = discover_project_root(explicit_root=namespace.root, cwd=cwd)
    if namespace.command == "status":
        paths = resolve_proposal_paths(root.path, namespace.short_name)
        parsed = _parse_paths(paths)
        return _status_result(paths, parsed)
    if namespace.command == "validate" and not namespace.validate_all:
        parsed = _parse_one(root.path, namespace.short_name)
        outcome = parsed.outcome
        result = _outcome_result("validate", namespace.short_name, outcome)
        return CommandResult(
            command="validate",
            data={
                "results": [
                    {
                        "short_name": namespace.short_name,
                        "valid": result.ok,
                        "adapter": outcome.adapter,
                    }
                ]
            },
            warnings=result.warnings,
            errors=result.errors,
            exit_code=result.exit_code,
        )
    if namespace.command == "validate" and namespace.validate_all:
        candidates = list_active_proposal_paths(root.path)
        results: list[dict[str, Any]] = []
        warnings: list[CliIssue] = []
        errors: list[CliIssue] = []
        for paths in candidates:
            outcome = _parse_paths(paths).outcome
            item_result = _outcome_result("validate", paths.directory.name, outcome)
            results.append(
                {
                    "short_name": paths.directory.name,
                    "valid": item_result.ok,
                    "adapter": outcome.adapter,
                }
            )
            warnings.extend(item_result.warnings)
            errors.extend(item_result.errors)
        return CommandResult(
            command="validate",
            data={"results": results},
            warnings=tuple(sorted(warnings, key=lambda item: item.sort_key)),
            errors=tuple(sorted(errors, key=lambda item: item.sort_key)),
            exit_code=1 if errors else 0,
        )
    if namespace.command == "list":
        candidates = list_active_proposal_paths(root.path)
        data_candidates: list[dict[str, Any]] = []
        warnings: list[CliIssue] = []
        errors: list[CliIssue] = []
        for paths in candidates:
            outcome = _parse_paths(paths).outcome
            item_result = _outcome_result("list", paths.directory.name, outcome)
            data_candidates.append(item_result.data)
            warnings.extend(item_result.warnings)
            errors.extend(item_result.errors)
        return CommandResult(
            command="list",
            data={"state": "active", "candidates": data_candidates},
            warnings=tuple(sorted(warnings, key=lambda item: item.sort_key)),
            errors=tuple(sorted(errors, key=lambda item: item.sort_key)),
            exit_code=1 if errors else 0,
        )
    if namespace.command == "abandon-preflight":
        parsed = _parse_one(root.path, namespace.short_name)
        return _preflight_result(namespace.short_name, parsed)
    if namespace.command == "approve":
        paths = resolve_proposal_paths(root.path, namespace.short_name)
        parsed = _parse_paths(paths)
        base = _mutation_outcome_result("approve", namespace.short_name, parsed.outcome)
        if not base.ok or parsed.outcome.model is None:
            return base
        transition = approve_proposal(
            paths,
            parsed.outcome.model,
            parsed.snapshot,
            namespace.expected_snapshot,
            establish_manifest=namespace.establish_manifest,
        )
        return CommandResult(
            command="approve",
            data={
                "short_name": namespace.short_name,
                "applied": transition.applied,
                "result": transition.result,
                "operation_id": transition.operation_id,
                "established_manifest": namespace.establish_manifest,
                "before_snapshot": transition.before_snapshot.to_dict(),
                "after_snapshot": transition.after_snapshot.to_dict(),
            },
        )
    if namespace.command == "begin-revision":
        paths = resolve_proposal_paths(root.path, namespace.short_name)
        parsed = _parse_paths(paths)
        base = _mutation_outcome_result(
            "begin-revision", namespace.short_name, parsed.outcome
        )
        if not base.ok or parsed.outcome.model is None:
            return base
        transition = begin_revision(
            paths,
            parsed.outcome.model,
            parsed.snapshot,
            namespace.expected_snapshot,
        )
        return CommandResult(
            command="begin-revision",
            data={
                "short_name": namespace.short_name,
                "applied": transition.applied,
                "operation_id": transition.operation_id,
                "before_snapshot": transition.before_snapshot.to_dict(),
                "after_snapshot": transition.after_snapshot.to_dict(),
                "differences": [item.to_dict() for item in transition.differences],
            },
        )
    if namespace.command == "complete-task":
        paths = resolve_proposal_paths(root.path, namespace.short_name)
        parsed = _parse_paths(paths)
        base = _mutation_outcome_result(
            "complete-task", namespace.short_name, parsed.outcome
        )
        if not base.ok or parsed.outcome.model is None:
            return base
        transition = complete_task(
            paths,
            parsed.outcome.model,
            parsed.snapshot,
            namespace.expected_snapshot,
            namespace.task_number,
            namespace.expected_task_digest,
        )
        return CommandResult(
            command="complete-task",
            data={
                "short_name": namespace.short_name,
                "task_number": namespace.task_number,
                "applied": transition.applied,
                "result": transition.result,
                "operation_id": transition.operation_id,
                "before_snapshot": transition.before_snapshot.to_dict(),
                "after_snapshot": transition.after_snapshot.to_dict(),
            },
        )
    if namespace.command == "rebuild-index":
        archive_root = root.path / "sdd/archive"
        if (namespace.directory is None) != (namespace.summary is None):
            raise UsageError("--directory and --summary are required together")
        provided_summaries: dict[str, str] | None = None
        if namespace.directory is not None:
            validate_repairable_target(archive_root, namespace.directory)
            provided_value = read_summary(inline=namespace.summary, file_path=None)
            base = load_archive_records(archive_root)
            if namespace.directory in {
                record.directory_name for record in base.records
            }:
                raise TransitionError(
                    "ERROR_RECOVERY_SUMMARY_UNEXPECTED",
                    "inspect_archive_state",
                    "Archive directory already has an authoritative summary",
                )
            provided_summaries = {namespace.directory: provided_value}
        scan = load_archive_records(archive_root, provided_summaries)
        if scan.diagnostics:
            issues = tuple(
                CliIssue(
                    item.code,
                    "inspect_archive_state",
                    item.message,
                    "error",
                    path=item.path,
                )
                for item in scan.diagnostics
            )
            return CommandResult(
                command="rebuild-index",
                data={
                    "record_count": len(scan.records),
                    "diagnostics": [item.to_dict() for item in scan.diagnostics],
                },
                errors=tuple(sorted(issues, key=lambda item: item.sort_key)),
                exit_code=1,
            )
        rendered, changed, digest = rebuild_archive_index(archive_root, scan.records)
        data = {
            "record_count": len(scan.records),
            "changed": changed,
            "index_sha256": digest,
            "index_bytes": len(rendered),
        }
        if provided_summaries is not None:
            data["provided_summary_directory"] = namespace.directory
        return CommandResult(command="rebuild-index", data=data)
    if namespace.command == "validate-index":
        archive_root = root.path / "sdd/archive"
        scan = load_archive_records(archive_root)
        if scan.diagnostics:
            issues = tuple(
                CliIssue(
                    item.code, "inspect_archive_state", item.message, "error", path=item.path
                )
                for item in scan.diagnostics
            )
            return CommandResult(
                command="validate-index",
                data={"diagnostics": [item.to_dict() for item in scan.diagnostics]},
                errors=tuple(sorted(issues, key=lambda item: item.sort_key)),
                exit_code=1,
            )
        differences = validate_archive_index(archive_root, scan.records)
        if differences:
            return _error_result(
                "validate-index",
                "ERROR_INDEX_STALE",
                "rebuild_index",
                "Derived archive INDEX differs from canonical records",
                exit_code=1,
                data={"differences": [item.to_dict() for item in differences]},
            )
        return CommandResult(
            command="validate-index",
            data={"record_count": len(scan.records), "valid": True},
        )
    if namespace.command == "doctor":
        findings = tuple(
            sorted(
                (*diagnose_project(root.path), *diagnose_runtime_package()),
                key=lambda item: item.sort_key,
            )
        )
        issues = tuple(
            CliIssue(
                item.code, item.action, item.message, "error", path=item.path
            )
            for item in findings
        )
        return CommandResult(
            command="doctor",
            data={
                "healthy": not findings,
                "findings": [item.to_dict() for item in findings],
                "environment": collect_environment_evidence(root.path, findings),
            },
            errors=tuple(sorted(issues, key=lambda item: item.sort_key)),
            exit_code=1 if findings else 0,
        )
    if namespace.command == "repair-archive-record":
        archive_root = root.path / "sdd/archive"
        execute_inputs = (
            namespace.terminal_status,
            namespace.summary,
            namespace.expected_proposal_sha256,
            namespace.expected_tasks_sha256,
        )
        provided = [value is not None for value in execute_inputs]
        if not any(provided):
            preflight = preflight_archive_repair(archive_root, namespace.directory_name)
            return CommandResult(
                command="repair-archive-record",
                data={"mode": "preflight", **_repair_preflight_data(archive_root, preflight)},
            )
        if not all(provided):
            raise UsageError(
                "repair execution requires --terminal-status, --summary, "
                "--expected-proposal-sha256, and --expected-tasks-sha256 together"
            )
        summary = read_summary(inline=namespace.summary, file_path=None)
        result = execute_archive_repair(
            archive_root,
            namespace.directory_name,
            terminal_status=namespace.terminal_status,
            summary=summary,
            expected_proposal_sha256=namespace.expected_proposal_sha256,
            expected_tasks_sha256=namespace.expected_tasks_sha256,
        )
        data = {
            "mode": "applied",
            **_repair_preflight_data(archive_root, result.preflight),
            "repaired": list(result.repaired),
            "operation_id": result.operation_id,
            "index_rebuilt": result.index_rebuilt,
            "index_sha256": result.index_sha256,
            "diagnostics": [item.to_dict() for item in result.diagnostics],
        }
        if result.diagnostics:
            issues = tuple(
                CliIssue(
                    item.code,
                    "inspect_archive_state",
                    item.message,
                    "error",
                    path=item.path,
                )
                for item in result.diagnostics
            )
            return CommandResult(
                command="repair-archive-record",
                data=data,
                errors=tuple(sorted(issues, key=lambda item: item.sort_key)),
                exit_code=1,
            )
        return CommandResult(command="repair-archive-record", data=data)
    if namespace.command == "archive":
        summary = read_summary(inline=namespace.summary, file_path=namespace.summary_file)
        retry = find_committed_terminal_retry(
            root.path,
            namespace.short_name,
            "archive",
            namespace.expected_snapshot,
            summary,
        )
        if retry is not None:
            return _terminal_commit_result("archive", namespace.short_name, retry)
        paths = resolve_proposal_paths(root.path, namespace.short_name)
        parsed = _parse_paths(paths)
        staged = resume_staged_terminal_transition(
            paths,
            parsed.outcome.model,
            parsed.snapshot,
            "archive",
            namespace.expected_snapshot,
            summary,
        ) if parsed.outcome.model is not None else None
        if staged is not None:
            return _terminal_commit_result("archive", namespace.short_name, staged)
        base = _mutation_outcome_result("archive", namespace.short_name, parsed.outcome)
        if not base.ok or parsed.outcome.model is None:
            return base
        validation = validate_archive(
            paths,
            parsed.outcome.model,
            parsed.snapshot,
            namespace.expected_snapshot,
            summary,
        )
        if namespace.dry_run:
            return CommandResult(
                command="archive",
                data={
                    "short_name": namespace.short_name,
                    "dry_run": True,
                    "would_change": True,
                    "before_snapshot": validation.before_snapshot.to_dict(),
                    "after_snapshot": None,
                    "predicted_changes": list(validation.predicted_changes()),
                    "destination": validation.destination.as_posix(),
                },
            )
        return _terminal_commit_result(
            "archive",
            namespace.short_name,
            commit_terminal_transition(paths, parsed.outcome.model, validation),
        )
    if namespace.command == "abandon":
        summary = read_summary(inline=namespace.summary, file_path=namespace.summary_file)
        retry = find_committed_terminal_retry(
            root.path,
            namespace.short_name,
            "abandon",
            namespace.expected_snapshot,
            summary,
        )
        if retry is not None:
            return _terminal_commit_result("abandon", namespace.short_name, retry)
        paths = resolve_proposal_paths(root.path, namespace.short_name)
        parsed = _parse_paths(paths)
        staged = resume_staged_terminal_transition(
            paths,
            parsed.outcome.model,
            parsed.snapshot,
            "abandon",
            namespace.expected_snapshot,
            summary,
        ) if parsed.outcome.model is not None else None
        if staged is not None:
            return _terminal_commit_result("abandon", namespace.short_name, staged)
        base = _mutation_outcome_result("abandon", namespace.short_name, parsed.outcome)
        if not base.ok or parsed.outcome.model is None:
            return base
        validation = validate_abandon(
            paths,
            parsed.outcome.model,
            parsed.snapshot,
            namespace.expected_snapshot,
            summary,
        )
        if namespace.dry_run:
            return CommandResult(
                command="abandon",
                data={
                    "short_name": namespace.short_name,
                    "dry_run": True,
                    "would_change": True,
                    "before_snapshot": validation.before_snapshot.to_dict(),
                    "after_snapshot": None,
                    "predicted_changes": list(validation.predicted_changes()),
                    "destination": validation.destination.as_posix(),
                },
            )
        return _terminal_commit_result(
            "abandon",
            namespace.short_name,
            commit_terminal_transition(paths, parsed.outcome.model, validation),
        )
    return _error_result(
        namespace.command,
        "ERROR_COMMAND_NOT_READY",
        "upgrade_engine",
        f"Command path is not implemented yet: {namespace.command}",
        exit_code=1,
    )


def _parse_one(project_root: Path, short_name: str) -> ParsedProposal:
    paths = resolve_proposal_paths(project_root, short_name)
    return _parse_paths(paths)


def _parse_paths(paths: ProposalPaths) -> ParsedProposal:
    proposal_bytes = paths.proposal.read_bytes()
    proposal_text = proposal_bytes.decode("utf-8", errors="strict")
    short_name = paths.directory.name
    prefix = f"sdd/{short_name}"
    selection = select_schema_from_document(
        proposal_text,
        path=f"{prefix}/proposal.md",
    )
    if not selection.supported:
        return ParsedProposal(
            outcome=parse_with_schema(
                short_name=short_name,
                proposal_text=proposal_text,
                task_scan=None,
                proposal_path=f"{prefix}/proposal.md",
            ),
            snapshot=None,
        )
    tasks_bytes = paths.tasks.read_bytes()
    tasks_text = tasks_bytes.decode("utf-8", errors="strict")
    task_scan = scan_tasks(tasks_text, path=f"{prefix}/tasks.md")
    outcome = parse_with_schema(
        short_name=short_name,
        proposal_text=proposal_text,
        task_scan=task_scan,
        proposal_path=f"{prefix}/proposal.md",
    )
    return ParsedProposal(
        outcome=outcome,
        snapshot=build_snapshot(proposal_bytes, tasks_bytes),
    )


def _outcome_result(
    command: str,
    short_name: str,
    outcome: ParseOutcome,
    *,
    snapshot: SnapshotManifest | None = None,
) -> CommandResult:
    warnings: list[CliIssue] = []
    errors: list[CliIssue] = []
    for diagnostic in outcome.diagnostics:
        issue = _issue_from_diagnostic(diagnostic)
        (errors if diagnostic.severity is Severity.ERROR else warnings).append(issue)

    data: dict[str, Any] = {
        "short_name": short_name,
        "adapter": outcome.adapter,
        "readable": outcome.readable,
        "mutation_safe": outcome.mutation_safe,
        "task_counts_reliable": outcome.task_counts_reliable,
        "abandonment_readable": outcome.abandonment_readable,
    }
    if outcome.model is not None:
        data.update(
            {
                "status": outcome.model.status,
                "change_type": outcome.model.change_type,
                "tasks": [
                    {
                        "ordinal": task.ordinal,
                        "text": task.text,
                        "source_text": task.source_text,
                        "canonical_text": task.text,
                        "task_digest": task_digest(task.text),
                        "completed": task.completed,
                        "source_line": task.source_line,
                    }
                    for task in outcome.model.tasks
                ],
                "task_count": len(outcome.model.tasks),
                "completed_count": sum(task.completed for task in outcome.model.tasks),
                "acceptance_conditions": list(outcome.model.acceptance_conditions),
            }
        )
        if outcome.model.change_type == "研究":
            for extension in outcome.model.extensions:
                if extension.namespace == "sdd.research.conclusion":
                    data["research_conclusion"] = list(extension.value["items"])
                    break
    if snapshot is not None:
        data["snapshot"] = snapshot.to_dict()
    return CommandResult(
        command=command,
        data=data,
        warnings=tuple(warnings),
        errors=tuple(errors),
        exit_code=1 if errors else 0,
    )


def _mutation_outcome_result(
    command: str,
    short_name: str,
    outcome: ParseOutcome,
) -> CommandResult:
    base = _outcome_result(command, short_name, outcome)
    if not base.ok or outcome.mutation_safe:
        return base
    code = outcome.mutation_block_code or "ERROR_INVALID_SOURCE_STATE"
    issue = CliIssue(
        code=code,
        action=_ACTION_BY_CODE[code],
        message=(
            "Proposal artifact is readable but does not support managed mutation"
            if outcome.mutation_block_code is not None
            else "Proposal is not in a mutation-safe source state"
        ),
        severity="error",
    )
    return CommandResult(
        command=command,
        data=base.data,
        warnings=base.warnings,
        errors=(issue,),
        exit_code=1,
    )


def _status_result(paths: ProposalPaths, parsed: ParsedProposal) -> CommandResult:
    """Project status and fail closed when an active approval is observably invalid."""

    base = _outcome_result(
        "status",
        paths.directory.name,
        parsed.outcome,
        snapshot=parsed.snapshot,
    )
    model = parsed.outcome.model
    if not base.ok or model is None or model.status != "approved":
        return base

    machine = paths.directory / ".sdd"
    manifest_path = machine / "approval-manifest.json"
    metadata_path = machine / "metadata.json"
    present = (manifest_path.is_file(), metadata_path.is_file())
    # An existing legacy approved proposal can still be inspected before the
    # caller explicitly establishes its first managed approval baseline.
    if present == (False, False):
        return base
    if (
        present[0] != present[1]
        or machine.is_symlink()
        or manifest_path.is_symlink()
        or metadata_path.is_symlink()
    ):
        raise TransitionError(
            "ERROR_APPROVAL_MANIFEST_REQUIRED",
            "establish_approval_manifest",
            "Approved proposal has no valid machine approval baseline",
        )

    manifest_bytes = manifest_path.read_bytes()
    manifest = parse_approval_manifest(manifest_bytes)
    metadata = parse_active_metadata(metadata_path.read_bytes())
    if approval_manifest_sha256(manifest_bytes) != metadata.manifest_sha256:
        raise TransitionError(
            "ERROR_APPROVAL_MANIFEST_IDENTITY_MISMATCH",
            "inspect_machine_metadata",
            "Approval Manifest bytes do not match active metadata identity",
        )
    if metadata.approval_state != "active" or metadata.revision is not None:
        raise TransitionError(
            "ERROR_METADATA_STATE_MISMATCH",
            "inspect_machine_metadata",
            "Approved status requires active approval metadata without a revision marker",
        )

    if metadata.attestation is not None:
        drift = compare_attested_state(metadata.attestation, model, metadata)
        if drift:
            issue = CliIssue(
                code="OUT_OF_BAND_DRIFT",
                action="inspect_managed_state_drift",
                message=(
                    "Current managed fields differ from the last attested state; "
                    "the editor or cause is unknown"
                ),
                severity="error",
            )
            return CommandResult(
                command="status",
                data={
                    **base.data,
                    "differences": [item.to_dict() for item in drift],
                },
                warnings=base.warnings,
                errors=(issue,),
                exit_code=1,
            )

    current_manifest = project_approval_manifest(
        model,
        approval_model_version=manifest.approval_model_version,
    )
    differences = compare_approval_manifests(manifest, current_manifest)
    if not differences:
        return base
    issue = CliIssue(
        code="ERROR_APPROVED_PLAN_CHANGED",
        action="begin_revision",
        message="Current approval-relevant content differs from the Approval Manifest",
        severity="error",
    )
    return CommandResult(
        command="status",
        data={
            **base.data,
            "differences": [item.to_dict() for item in differences],
        },
        warnings=base.warnings,
        errors=(issue,),
        exit_code=1,
    )


def _issue_from_diagnostic(diagnostic: Diagnostic) -> CliIssue:
    action = _ACTION_BY_CODE.get(diagnostic.code, "fix_artifact_format")
    return CliIssue(
        code=diagnostic.code,
        action=action,
        message=diagnostic.message,
        severity=diagnostic.severity.value,
        path=diagnostic.path,
        line=diagnostic.line,
        column=diagnostic.column,
    )


def _preflight_result(short_name: str, parsed: ParsedProposal) -> CommandResult:
    base = _outcome_result(
        "abandon-preflight",
        short_name,
        parsed.outcome,
        snapshot=parsed.snapshot,
    )
    degraded_codes = {
        "ERROR_INVALID_TASK_CHECKBOX",
        "ERROR_INVALID_TASK_LIST_ITEM",
    }
    warnings = list(base.warnings)
    errors: list[CliIssue] = []
    for issue in base.errors:
        if issue.code in degraded_codes:
            warnings.append(
                CliIssue(
                    code=issue.code,
                    action=issue.action,
                    message=issue.message,
                    severity="warning",
                    path=issue.path,
                    line=issue.line,
                    column=issue.column,
                )
            )
        else:
            errors.append(issue)
    data = dict(base.data)
    data["working_tree_reverted"] = False
    data["completed_tasks"] = [
        task["text"] for task in data.get("tasks", []) if task["completed"]
    ]
    return CommandResult(
        command="abandon-preflight",
        data=data,
        warnings=tuple(sorted(warnings, key=lambda item: item.sort_key)),
        errors=tuple(sorted(errors, key=lambda item: item.sort_key)),
        exit_code=1 if errors else 0,
    )


def _error_result(
    command: str,
    code: str,
    action: str,
    message: str,
    *,
    exit_code: int,
    data: dict[str, Any] | None = None,
) -> CommandResult:
    return CommandResult(
        command=command,
        data={} if data is None else data,
        errors=(CliIssue(code, action, message, "error"),),
        exit_code=exit_code,
    )


def _terminal_commit_result(command: str, short_name: str, result: Any) -> CommandResult:
    data = {
        "short_name": short_name,
        "result": result.outcome,
        "applied": result.applied,
        "committed": True,
        "operation_id": result.operation_id,
        "before_snapshot": result.validation.before_snapshot.to_dict(),
        "after_snapshot": result.after_snapshot.to_dict(),
        "destination": result.destination.as_posix(),
        "index_diagnostics": list(result.index_diagnostics),
    }
    if result.index_stale:
        return _error_result(
            command,
            "COMMITTED_DERIVED_ARTIFACT_STALE",
            "rebuild_index",
            "Terminal directory move committed but derived INDEX is stale",
            exit_code=1,
            data=data,
        )
    return CommandResult(command=command, data=data)


def _repair_preflight_data(archive_root: Path, preflight: RepairPreflight) -> dict[str, Any]:
    return {
        "directory": preflight.directory_name,
        "destination": (archive_root / preflight.directory_name).as_posix(),
        "short_name": preflight.short_name,
        "archive_date": preflight.archive_date,
        "expected_terminal_status": preflight.expected_terminal_status,
        "current_status": preflight.current_status,
        "missing": list(preflight.missing),
        "evidence": {
            "proposal_sha256": preflight.proposal_sha256,
            "tasks_sha256": preflight.tasks_sha256,
        },
    }


def _command_hint(arguments: Sequence[str]) -> str:
    for argument in arguments:
        if argument in {
            "validate", "list", "status", "abandon-preflight", "approve", "begin-revision",
            "complete-task"
            , "rebuild-index", "validate-index", "doctor"
            , "archive", "abandon", "repair-archive-record"
        }:
            return argument
    if "--version" in arguments:
        return "version"
    if "--handshake" in arguments:
        return "handshake"
    return "usage"


def _write_human(result: CommandResult, *, stdout: TextIO, stderr: TextIO) -> None:
    if result.command == "version" and result.ok:
        stdout.write(
            f"sdd-workflow {result.data['engine_version']} "
            f"(schema {result.data['minimum_schema_version']}.."
            f"{result.data['maximum_schema_version']})\n"
        )
    elif result.command == "handshake" and result.ok:
        stdout.write(
            f"sdd-workflow handshake {result.data['handshake_version']} "
            f"engine={result.data['engine_version']} "
            f"capabilities={len(result.data['capabilities'])}\n"
        )
    elif result.command == "status" and result.data:
        reliability = "reliable" if result.data.get("task_counts_reliable") else "unreliable"
        snapshot = result.data.get("snapshot", {})
        stdout.write(
            f"{result.data['short_name']}: adapter={result.data.get('adapter')} "
            f"status={result.data.get('status')} type={result.data.get('change_type')} "
            f"tasks={result.data.get('completed_count', 0)}/"
            f"{result.data.get('task_count', 0)} counts={reliability} "
            f"snapshot={snapshot.get('snapshot_digest')}\n"
        )
    elif result.command == "validate" and result.data:
        for item in result.data["results"]:
            stdout.write(f"{item['short_name']}: {'valid' if item['valid'] else 'invalid'}\n")
    elif result.command == "list" and result.data:
        for item in result.data["candidates"]:
            stdout.write(f"{item['short_name']}\n")
    elif result.command == "abandon-preflight" and result.data:
        reliability = "reliable" if result.data.get("task_counts_reliable") else "unreliable"
        stdout.write(f"{result.data['short_name']}: abandonment preflight\n")
        stdout.write(f"status: {result.data.get('status')}\n")
        stdout.write(
            f"tasks: {result.data.get('completed_count', 0)}/"
            f"{result.data.get('task_count', 0)} ({reliability})\n"
        )
        for task in result.data.get("completed_tasks", []):
            stdout.write(f"completed: {task}\n")
        stdout.write("working-tree code and git changes will not be reverted\n")
        snapshot = result.data.get("snapshot")
        if snapshot is not None:
            stdout.write(f"proposal.md sha256: {snapshot['proposal_sha256']}\n")
            stdout.write(f"tasks.md sha256: {snapshot['tasks_sha256']}\n")
            stdout.write(f"snapshot digest: {snapshot['snapshot_digest']}\n")
        stdout.write(f"reply exactly: 確認放棄 {result.data['short_name']}\n")
    elif result.command == "approve" and result.data:
        stdout.write(
            f"{result.data['short_name']}: approved "
            f"snapshot={result.data['after_snapshot']['snapshot_digest']}\n"
        )
    elif result.command == "begin-revision" and result.data:
        outcome = "opened" if result.data["applied"] else "already open"
        stdout.write(
            f"{result.data['short_name']}: revision {outcome} "
            f"differences={len(result.data['differences'])} "
            f"snapshot={result.data['after_snapshot']['snapshot_digest']}\n"
        )
    elif result.command == "complete-task" and result.data:
        stdout.write(
            f"{result.data['short_name']}: task {result.data['task_number']} completed "
            f"snapshot={result.data['after_snapshot']['snapshot_digest']}\n"
        )
    elif result.command == "rebuild-index" and result.data:
        stdout.write(
            f"archive INDEX: records={result.data['record_count']} "
            f"changed={str(result.data.get('changed', False)).lower()}\n"
        )
    elif result.command == "validate-index" and result.data:
        stdout.write(
            f"archive INDEX: {'valid' if result.data.get('valid') else 'invalid'}\n"
        )
    elif result.command == "doctor" and result.data:
        stdout.write(
            f"doctor: {'healthy' if result.data.get('healthy') else 'findings present'}\n"
        )
    elif result.command in {"archive", "abandon"} and result.data:
        if result.data.get("dry_run"):
            stdout.write(
                f"{result.data['short_name']}: {result.command} dry-run "
                f"destination={result.data['destination']}\n"
            )
        elif result.data.get("committed"):
            stdout.write(
                f"{result.data['short_name']}: {result.command} committed "
                f"destination={result.data['destination']}\n"
            )

    for issue in (*result.warnings, *result.errors):
        location = ""
        if issue.path is not None:
            location = f" {issue.path}"
            if issue.line is not None:
                location += f":{issue.line}"
                if issue.column is not None:
                    location += f":{issue.column}"
        stderr.write(f"{issue.code}:{location} {issue.message}\n")

    if result.command not in {"version", "handshake"}:
        guidance = _human_guidance(result)
        stream = stderr if result.errors else stdout
        stream.write(f"current state: {guidance['current_state']}\n")
        stream.write(f"next action: {guidance['next_action']}\n")
        stream.write(f"blocked reason: {guidance['blocked_reason']}\n")
        stream.write(f"required user action: {guidance['required_user_action']}\n")
        stream.write(f"authoritative path: {guidance['authoritative_path']}\n")


def _human_guidance(result: CommandResult) -> dict[str, str]:
    data = result.data
    action = result.errors[0].action if result.errors else None
    current_state = _human_current_state(result)
    next_action = _human_next_action(result, action)
    blocked_reason = (
        "; ".join(f"{issue.code}: {issue.message}" for issue in result.errors)
        if result.errors
        else "none"
    )
    return {
        "current_state": current_state,
        "next_action": next_action,
        "blocked_reason": blocked_reason,
        "required_user_action": _human_required_user_action(result, action),
        "authoritative_path": _human_authoritative_path(result, data),
    }


def _human_current_state(result: CommandResult) -> str:
    data = result.data
    if result.command in {"archive", "abandon"} and data.get("committed"):
        return "completed" if result.command == "archive" else "abandoned"
    if result.command == "status" and data.get("status"):
        return str(data["status"])
    if result.errors:
        return "blocked"
    if result.command == "validate":
        return "valid"
    if result.command == "list":
        return f"{len(data.get('candidates', []))} active proposal(s)"
    if result.command == "abandon-preflight":
        return "abandonment preflight complete"
    if result.command == "approve":
        return "approved"
    if result.command == "begin-revision":
        return "draft"
    if result.command == "complete-task":
        return "approved"
    if result.command in {"archive", "abandon"} and data.get("dry_run"):
        return f"{result.command} planned"
    if result.command == "doctor":
        return "healthy" if data.get("healthy") else "findings present"
    if result.command == "validate-index":
        return "index valid" if data.get("valid") else "index invalid"
    if result.command == "rebuild-index":
        return "index rebuilt"
    return "command complete"


def _human_next_action(result: CommandResult, action: str | None) -> str:
    data = result.data
    if action is not None:
        return action.replace("_", " ")
    if result.command == "status":
        tasks = data.get("tasks", [])
        next_task = next(
            (
                task.get("ordinal")
                for task in tasks
                if isinstance(task, dict) and not task.get("completed")
            ),
            None,
        )
        if data.get("status") == "draft":
            return "approve after explicit user authorization"
        if next_task is not None:
            return f"complete task {next_task}"
        return "archive after acceptance"
    if result.command == "validate":
        return "run status"
    if result.command == "list":
        return "select one proposal"
    if result.command == "abandon-preflight":
        return f"wait for exact confirmation: 確認放棄 {data.get('short_name')}"
    if result.command == "approve":
        return "implement the first incomplete task"
    if result.command == "begin-revision":
        return "edit and validate revised proposal scope"
    if result.command == "complete-task":
        return "run status and verify canonical progress"
    if result.command in {"archive", "abandon"} and data.get("dry_run"):
        return f"review dry-run before {result.command}"
    if result.command == "validate-index":
        return "continue workflow"
    if result.command == "rebuild-index":
        return "validate archive index"
    if result.command == "doctor":
        return "continue workflow" if data.get("healthy") else "inspect findings"
    return "none"


def _human_required_user_action(
    result: CommandResult,
    action: str | None,
) -> str:
    if action is not None:
        user_actions = {
            "select_project_root": "select the project root",
            "choose_short_name": "provide a valid proposal short name",
            "create_or_select_proposal": "create or select a proposal",
            "refresh_status": "confirm intent again after a fresh status check",
            "begin_revision": "authorize managed revision and reapproval",
            "begin_revision_and_reapprove": "authorize managed revision and reapproval",
            "establish_approval_manifest": "reconfirm the canonical approved plan",
            "fix_command_arguments": "correct the command arguments",
            "rebuild_index": "none",
        }
        return user_actions.get(action, f"follow the {action.replace('_', ' ')} remediation")
    data = result.data
    if result.command == "status":
        if data.get("status") == "draft":
            return "explicitly approve before implementation"
        if data.get("task_count") == data.get("completed_count"):
            return "accept completed work before archive"
    if result.command == "abandon-preflight":
        return f"reply exactly: 確認放棄 {data.get('short_name')}"
    if result.command == "begin-revision":
        return "review revised scope and explicitly approve it"
    return "none"


def _human_authoritative_path(
    result: CommandResult,
    data: dict[str, Any],
) -> str:
    if data.get("destination"):
        return str(data["destination"])
    if data.get("short_name"):
        return f"sdd/{data['short_name']}"
    for issue in (*result.errors, *result.warnings):
        if issue.path is not None:
            return issue.path
    if result.command in {"rebuild-index", "validate-index"}:
        return "sdd/archive/INDEX.md"
    return "unknown"
