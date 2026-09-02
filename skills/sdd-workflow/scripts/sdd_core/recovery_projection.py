"""Pure, fail-closed projection of registered legacy artifacts.

This module is intentionally not imported by the normal parser.  Recovery
commands call it explicitly, inspect the redacted plan, and (in a separate
transition layer) decide whether confirmed candidate bytes may be installed.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from .parser_v1 import VALID_STATUSES, parse_with_schema, select_schema_from_document
from .parser_v2 import VALID_V2_CHANGE_TYPES
from .scanner import ACCEPTANCE_HEADING, scan_tasks


RecoveryTarget = Literal["active", "archive"]
REGISTERED_MARKDOWN_ENCODINGS = (
    "v0.2.0-v0.2.3-unversioned-v1",
    "registered-checkbox-deviation",
)
REGISTERED_JSON_ENCODINGS = ("metadata-v1", "recovery-v1")

_HEADING = re.compile(r"^## (.+)$")
_TITLE = re.compile(r"^# (.+)$")
_RECOVERABLE_CHECKBOX = re.compile(
    r"^(?:[-*+]|[0-9]+[.)])\s*\[([ xX])\]\s*(\S(?:.*\S)?)\s*$"
)
_CHECKBOX_LIKE = re.compile(r"^\s*(?:[-*+]|[0-9]+[.)])\s*\[([^]]*)\](.*)$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|[0-9]+[.)])(?:\s|$)")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_KNOWN_SECTIONS = ("狀態", "類型", "為什麼做", "要改什麼", "影響範圍")
_REGISTERED_METADATA_FIELDS = frozenset(
    {
        "metadata_version",
        "writer",
        "last_operation",
        "approval",
        "revision",
        "attestation",
        "terminal",
        "recovery",
        "reconstruction",
    }
)
_MANAGED_AUTHORITY_FIELDS = frozenset(
    {"approval", "revision", "attestation", "terminal"}
)


@dataclass(frozen=True, slots=True)
class RecoverySupplement:
    """Explicit non-derived values which recovery is allowed to consume."""

    change_type: str | None = None
    scope: str | None = None
    acceptance_conditions: tuple[str, ...] = ()
    summary: str | None = None


@dataclass(frozen=True, slots=True)
class RecoveryIssue:
    code: str
    action: str
    message: str
    field: str | None = None

    def to_dict(self) -> dict[str, str]:
        value = {"code": self.code, "action": self.action, "message": self.message}
        if self.field is not None:
            value["field"] = self.field
        return value


@dataclass(frozen=True, slots=True)
class FieldEvidence:
    field: str
    source: str
    sha256: str

    def to_dict(self) -> dict[str, str]:
        return {"field": self.field, "source": self.source, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class RecoveryProjection:
    target: RecoveryTarget
    disposition: Literal["no-op", "ready", "blocked"]
    encoding: str | None
    source_digests: tuple[tuple[str, str], ...]
    candidate_digests: tuple[tuple[str, str], ...]
    required_inputs: tuple[str, ...]
    changes: tuple[tuple[str, str], ...]
    evidence: tuple[FieldEvidence, ...]
    issues: tuple[RecoveryIssue, ...]
    proposal_candidate: bytes | None = None
    tasks_candidate: bytes | None = None
    metadata_candidate: bytes | None = None

    @property
    def applicable(self) -> bool:
        return self.disposition == "ready"

    def redacted_dict(self) -> dict[str, Any]:
        """Return the stable report shape without source or candidate bodies."""

        return {
            "target": self.target,
            "disposition": self.disposition,
            "applicable": self.applicable,
            "encoding": self.encoding,
            "registered_markdown_encodings": list(REGISTERED_MARKDOWN_ENCODINGS),
            "registered_json_encodings": list(REGISTERED_JSON_ENCODINGS),
            "source_digests": dict(self.source_digests),
            "candidate_digests": dict(self.candidate_digests),
            "required_inputs": list(self.required_inputs),
            "changes": [
                {"artifact": artifact, "field": field}
                for artifact, field in self.changes
            ],
            "evidence": [item.to_dict() for item in self.evidence],
            "issues": [item.to_dict() for item in self.issues],
        }


def plan_recovery_projection(
    *,
    target: RecoveryTarget,
    short_name: str,
    proposal_bytes: bytes,
    tasks_bytes: bytes,
    expected_status: str | None = None,
    archive_date: str | None = None,
    metadata_bytes: bytes | None = None,
    supplement: RecoverySupplement | None = None,
) -> RecoveryProjection:
    """Project supported legacy bytes to strict Schema v2 candidates.

    The function performs no filesystem access and never guesses a semantic
    value.  Candidate bytes remain available to a transition caller, while
    :meth:`RecoveryProjection.redacted_dict` deliberately exposes only hashes
    and field-level change descriptions.
    """

    if target not in {"active", "archive"}:
        raise ValueError(f"unsupported recovery target: {target!r}")
    supplied = RecoverySupplement() if supplement is None else supplement
    source = [
        ("proposal.md", _sha256(proposal_bytes)),
        ("tasks.md", _sha256(tasks_bytes)),
    ]
    if metadata_bytes is not None:
        source.append((".sdd/metadata.json", _sha256(metadata_bytes)))

    decoded, decode_issues = _decode_artifacts(proposal_bytes, tasks_bytes)
    if decode_issues:
        return _blocked(target, source, decode_issues)
    proposal_text, tasks_text = decoded

    selection = select_schema_from_document(proposal_text)
    if selection.declared and not selection.supported:
        return _blocked(
            target,
            source,
            (
                RecoveryIssue(
                    "ERROR_RECOVERY_FORMAT_UNREGISTERED",
                    "upgrade_or_recreate_proposal",
                    "Explicit unknown or malformed schema metadata is not recoverable",
                    "schema_version",
                ),
            ),
        )

    strict_scan = scan_tasks(tasks_text)
    strict = parse_with_schema(
        short_name=short_name,
        proposal_text=proposal_text,
        task_scan=strict_scan,
    )
    strict_errors = tuple(
        item for item in strict.diagnostics if item.severity.value == "error"
    )
    complete_sections = _sections(proposal_text)
    strict_semantics_complete = (
        not strict_errors
        and strict.model is not None
        and strict.model.status in VALID_STATUSES
        and strict.model.change_type in VALID_V2_CHANGE_TYPES
        and all(name in complete_sections for name in _KNOWN_SECTIONS)
        and bool(strict.model.acceptance_conditions)
    )
    metadata_state, metadata_issue = _inspect_registered_metadata(
        metadata_bytes,
        target=target,
        short_name=short_name,
        expected_status=expected_status,
        archive_date=archive_date,
    )
    if metadata_issue is not None:
        return _blocked(target, source, (metadata_issue,))
    if strict_semantics_complete and metadata_state in {"absent", "valid", "managed"}:
        evidence = _model_evidence(strict.model, proposal_text, tasks_text)
        return RecoveryProjection(
            target=target,
            disposition="no-op",
            encoding=None,
            source_digests=tuple(source),
            candidate_digests=(),
            required_inputs=(),
            changes=(),
            evidence=evidence,
            issues=(),
        )
    if metadata_state == "managed":
        return _blocked(
            target,
            source,
            (
                RecoveryIssue(
                    "ERROR_MACHINE_METADATA_INVALID",
                    "inspect_machine_metadata",
                    "Managed machine authority prevents artifact reconstruction",
                    "metadata",
                ),
            ),
        )
    if strict_semantics_complete and metadata_state == "recoverable":
        assert strict.model is not None
        evidence = list(_model_evidence(strict.model, proposal_text, tasks_text))
        if target == "archive" and (supplied.summary is None or not supplied.summary.strip()):
            return RecoveryProjection(
                target=target,
                disposition="blocked",
                encoding="recovery-v1",
                source_digests=tuple(source),
                candidate_digests=(),
                required_inputs=("summary",),
                changes=(),
                evidence=tuple(evidence),
                issues=(),
            )
        if target == "archive" and supplied.summary is not None:
            evidence.append(_evidence("summary", "explicit_input", supplied.summary.strip()))
        return RecoveryProjection(
            target=target,
            disposition="ready",
            encoding="recovery-v1",
            source_digests=tuple(source),
            candidate_digests=(
                ("proposal.md", _sha256(proposal_bytes)),
                ("tasks.md", _sha256(tasks_bytes)),
            ),
            required_inputs=(),
            changes=(),
            evidence=tuple(sorted(evidence, key=lambda item: item.field)),
            issues=(),
            proposal_candidate=proposal_bytes,
            tasks_candidate=tasks_bytes,
        )

    sections, section_issues = _extract_legacy_sections(proposal_text, short_name)
    task_projection, acceptance, task_issues, checkbox_changed = _recover_tasks(
        tasks_text, short_name
    )
    issues = list(section_issues)
    issues.extend(task_issues)
    if issues:
        return _blocked(target, source, tuple(issues))

    evidence: list[FieldEvidence] = []
    required: list[str] = []
    status_values = _semantic_values(sections.get("狀態"))
    if len(status_values) > 1:
        return _blocked(
            target,
            source,
            (_ambiguous("status", "Proposal status contains multiple values"),),
        )
    status = status_values[0] if status_values else None
    if status is not None and status not in VALID_STATUSES:
        return _blocked(
            target,
            source,
            (_ambiguous("status", "Proposal status is unsupported or ambiguous"),),
        )
    if target == "archive":
        if expected_status not in {"completed", "abandoned"}:
            return _blocked(
                target,
                source,
                (_ambiguous("status", "Archive terminal status lacks authoritative evidence"),),
            )
        if status is not None and status != expected_status:
            return _blocked(
                target,
                source,
                (_ambiguous("status", "Proposal status conflicts with archive authority"),),
            )
        candidate_status = expected_status
        evidence.append(_evidence("status", "archive_identity", expected_status))
    else:
        if status is None:
            candidate_status = "draft"
            evidence.append(_evidence("status", "active_recovery_policy", "draft"))
        elif status not in {"draft", "approved"}:
            return _blocked(
                target,
                source,
                (_ambiguous("status", "Terminal proposal cannot be repaired as active"),),
            )
        else:
            candidate_status = "draft"
            evidence.append(_evidence("status", "proposal.md", status))

    change_type_values = _semantic_values(sections.get("類型"))
    if len(change_type_values) > 1:
        return _blocked(
            target,
            source,
            (_ambiguous("change_type", "Proposal type contains multiple values"),),
        )
    try:
        change_type = _resolve_value(
            field="change_type",
            existing=change_type_values[0] if change_type_values else None,
            supplied=supplied.change_type,
            required=required,
            evidence=evidence,
        )
        scope = _resolve_value(
            field="scope",
            existing=_section_semantic_text(sections.get("影響範圍")),
            supplied=supplied.scope,
            required=required,
            evidence=evidence,
        )
    except RecoveryConflict as error:
        return _blocked(
            target,
            source,
            (_conflict(error.field),),
            tuple(required),
            tuple(evidence),
        )
    why = _section_semantic_text(sections.get("為什麼做"))
    changes = _section_semantic_text(sections.get("要改什麼"))
    if not why:
        issues.append(_ambiguous("why", "Legacy proposal has no recoverable rationale"))
    else:
        evidence.append(_evidence("why", "proposal.md", why))
    if not changes:
        issues.append(_ambiguous("changes", "Legacy proposal has no recoverable change scope"))
    else:
        evidence.append(_evidence("changes", "proposal.md", changes))

    resolved_acceptance = acceptance
    if acceptance:
        if supplied.acceptance_conditions and supplied.acceptance_conditions != acceptance:
            issues.append(_conflict("acceptance"))
        evidence.append(_evidence("acceptance", "tasks.md", "\n".join(acceptance)))
    elif supplied.acceptance_conditions:
        if any(not item.strip() for item in supplied.acceptance_conditions):
            issues.append(_ambiguous("acceptance", "Acceptance input contains an empty value"))
        else:
            resolved_acceptance = tuple(item.strip() for item in supplied.acceptance_conditions)
            evidence.append(
                _evidence("acceptance", "explicit_input", "\n".join(resolved_acceptance))
            )
    else:
        required.append("acceptance")

    if target == "archive":
        if supplied.summary is None or not supplied.summary.strip():
            required.append("summary")
        elif "\n" in supplied.summary or "\r" in supplied.summary:
            issues.append(_ambiguous("summary", "Summary must be a non-empty single line"))
        else:
            evidence.append(_evidence("summary", "explicit_input", supplied.summary.strip()))

    if change_type is not None and change_type not in VALID_V2_CHANGE_TYPES:
        issues.append(_ambiguous("change_type", "Change type is not supported by Schema v2"))
    if issues:
        return _blocked(target, source, tuple(issues), tuple(required), tuple(evidence))
    if required:
        return RecoveryProjection(
            target=target,
            disposition="blocked",
            encoding="v0.2.0-v0.2.3-unversioned-v1",
            source_digests=tuple(source),
            candidate_digests=(),
            required_inputs=tuple(sorted(set(required))),
            changes=(),
            evidence=tuple(sorted(evidence, key=lambda item: item.field)),
            issues=(),
        )
    assert change_type is not None and scope is not None and why is not None and changes is not None

    proposal_candidate = _render_proposal(
        short_name,
        candidate_status,
        change_type,
        why,
        changes,
        scope,
    )
    tasks_candidate = _render_tasks(short_name, task_projection, resolved_acceptance)
    candidate_scan = scan_tasks(tasks_candidate.decode("utf-8"))
    candidate = parse_with_schema(
        short_name=short_name,
        proposal_text=proposal_candidate.decode("utf-8"),
        task_scan=candidate_scan,
    )
    candidate_errors = [
        item for item in candidate.diagnostics if item.severity.value == "error"
    ]
    if candidate.model is None or candidate_errors or not candidate_scan.counts_reliable:
        return _blocked(
            target,
            source,
            (
                RecoveryIssue(
                    "ERROR_RECOVERY_CANDIDATE_INVALID",
                    "report_internal_error",
                    "Projected candidates do not pass the strict validator",
                ),
            ),
        )

    artifact_changes: list[tuple[str, str]] = []
    if proposal_candidate != proposal_bytes:
        artifact_changes.extend(
            ("proposal.md", field)
            for field in ("schema_version", "status", "canonical_sections")
        )
    if tasks_candidate != tasks_bytes:
        artifact_changes.append(("tasks.md", "checkbox_encoding" if checkbox_changed else "canonical_layout"))
    encoding = (
        "registered-checkbox-deviation"
        if checkbox_changed
        else "v0.2.0-v0.2.3-unversioned-v1"
    )
    return RecoveryProjection(
        target=target,
        disposition="ready",
        encoding=encoding,
        source_digests=tuple(source),
        candidate_digests=(
            ("proposal.md", _sha256(proposal_candidate)),
            ("tasks.md", _sha256(tasks_candidate)),
        ),
        required_inputs=(),
        changes=tuple(artifact_changes),
        evidence=tuple(sorted(evidence, key=lambda item: item.field)),
        issues=(),
        proposal_candidate=proposal_candidate,
        tasks_candidate=tasks_candidate,
    )


def _decode_artifacts(
    proposal_bytes: bytes, tasks_bytes: bytes
) -> tuple[tuple[str, str], tuple[RecoveryIssue, ...]]:
    try:
        return (
            proposal_bytes.decode("utf-8", errors="strict"),
            tasks_bytes.decode("utf-8", errors="strict"),
        ), ()
    except UnicodeDecodeError:
        return ("", ""), (
            RecoveryIssue(
                "ERROR_ARTIFACT_ENCODING",
                "recreate_proposal",
                "Recovery supports UTF-8 Markdown only",
            ),
        )


def _sections(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        match = _HEADING.fullmatch(line)
        if match:
            current = match.group(1)
            result.setdefault(current, [])
        elif current is not None:
            result[current].append(line)
    return result


def _extract_legacy_sections(
    proposal_text: str, short_name: str
) -> tuple[dict[str, list[str]], tuple[RecoveryIssue, ...]]:
    issues: list[RecoveryIssue] = []
    titles = [match.group(1) for line in proposal_text.splitlines() if (match := _TITLE.fullmatch(line))]
    if titles != [short_name]:
        issues.append(_ambiguous("short_name", "Proposal title does not uniquely match its directory"))
    result: dict[str, list[str]] = {}
    current: str | None = None
    for line in proposal_text.splitlines():
        match = _HEADING.fullmatch(line)
        if match:
            current = match.group(1)
            if current not in _KNOWN_SECTIONS:
                issues.append(
                    RecoveryIssue(
                        "ERROR_RECOVERY_FORMAT_UNREGISTERED",
                        "upgrade_or_recreate_proposal",
                        f"Unregistered proposal section: {current}",
                        "sections",
                    )
                )
            elif current in result:
                issues.append(_ambiguous("sections", f"Duplicate proposal section: {current}"))
            else:
                result[current] = []
            continue
        if current in result:
            result[current].append(line)
    return result, tuple(issues)


def _recover_tasks(
    tasks_text: str,
    short_name: str,
) -> tuple[tuple[tuple[bool, str], ...], tuple[str, ...], tuple[RecoveryIssue, ...], bool]:
    lines = tasks_text.splitlines()
    boundaries = [index for index, line in enumerate(lines) if line == ACCEPTANCE_HEADING]
    if len(boundaries) > 1:
        return (), (), (_ambiguous("acceptance", "Multiple acceptance sections are ambiguous"),), False
    boundary = boundaries[0] if boundaries else len(lines)
    tasks: list[tuple[bool, str]] = []
    issues: list[RecoveryIssue] = []
    changed = False
    registered_titles = {f"# {short_name} 任務", "# Tasks"}
    for line_number, line in enumerate(lines[:boundary], start=1):
        if line_number == 1:
            if line in registered_titles:
                continue
            issues.append(_unregistered_tasks_content("title", line_number))
            continue
        if not line.strip():
            continue
        match = _RECOVERABLE_CHECKBOX.fullmatch(line)
        if match:
            state, text = match.groups()
            tasks.append((state.lower() == "x", text))
            canonical = f"- [{'x' if state.lower() == 'x' else ' '}] {text}"
            changed = changed or line != canonical
            continue
        checkbox = _CHECKBOX_LIKE.match(line)
        if checkbox:
            reason = "Indented, empty, or unknown-state checkbox is not uniquely recoverable"
            issues.append(
                RecoveryIssue(
                    "ERROR_RECOVERY_TASK_AMBIGUOUS",
                    "upgrade_or_recreate_proposal",
                    f"{reason} at tasks.md:{line_number}",
                    "tasks",
                )
            )
        elif _LIST_ITEM.match(line):
            issues.append(
                RecoveryIssue(
                    "ERROR_RECOVERY_FORMAT_UNREGISTERED",
                    "upgrade_or_recreate_proposal",
                    f"Ordinary list item in task region at tasks.md:{line_number}",
                    "tasks",
                )
            )
        else:
            issues.append(_unregistered_tasks_content("task", line_number))
    if not lines:
        issues.append(_unregistered_tasks_content("title", 1))
    acceptance: list[str] = []
    if boundaries:
        for line_number, line in enumerate(lines[boundary + 1 :], start=boundary + 2):
            if not line.strip():
                continue
            if line.startswith("- ") and line[2:].strip():
                acceptance.append(line[2:].strip())
            elif _LIST_ITEM.match(line) and not line.startswith("  "):
                issues.append(
                    RecoveryIssue(
                        "ERROR_RECOVERY_ACCEPTANCE_AMBIGUOUS",
                        "provide_recovery_input",
                        f"Acceptance list item is not canonical at tasks.md:{line_number}",
                        "acceptance",
                    )
                )
            else:
                issues.append(_unregistered_tasks_content("acceptance", line_number))
    return tuple(tasks), tuple(acceptance), tuple(issues), changed


def _unregistered_tasks_content(region: str, line_number: int) -> RecoveryIssue:
    return RecoveryIssue(
        "ERROR_RECOVERY_FORMAT_UNREGISTERED",
        "upgrade_or_recreate_proposal",
        f"Unregistered {region} structure at tasks.md:{line_number}",
        "tasks" if region != "acceptance" else "acceptance",
    )


def _semantic_values(lines: list[str] | None) -> tuple[str, ...]:
    if lines is None:
        return ()
    return tuple(line.strip() for line in lines if line.strip())


def _section_semantic_text(lines: list[str] | None) -> str | None:
    if lines is None:
        return None
    values = [line.rstrip() for line in lines if line.strip()]
    return "\n".join(values) if values else None


def _resolve_value(
    *,
    field: str,
    existing: str | None,
    supplied: str | None,
    required: list[str],
    evidence: list[FieldEvidence],
) -> str | None:
    supplied_value = None if supplied is None else supplied.strip()
    if existing:
        if supplied_value and supplied_value != existing:
            raise RecoveryConflict(field)
        evidence.append(_evidence(field, "proposal.md", existing))
        return existing
    if supplied_value:
        evidence.append(_evidence(field, "explicit_input", supplied_value))
        return supplied_value
    required.append(field)
    return None


class RecoveryConflict(ValueError):
    def __init__(self, field: str) -> None:
        super().__init__(field)
        self.field = field


def _inspect_registered_metadata(
    data: bytes | None,
    *,
    target: RecoveryTarget,
    short_name: str,
    expected_status: str | None,
    archive_date: str | None,
) -> tuple[str, RecoveryIssue | None]:
    if data is None:
        return "absent", None
    try:
        value = json.loads(data.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "invalid", RecoveryIssue(
            "ERROR_RECOVERY_JSON_AMBIGUOUS",
            "inspect_machine_metadata",
            "Machine JSON is not a registered, readable encoding",
            "metadata",
        )
    if not isinstance(value, dict):
        return "invalid", RecoveryIssue(
            "ERROR_RECOVERY_JSON_AMBIGUOUS",
            "inspect_machine_metadata",
            "Machine JSON root must be an object",
            "metadata",
        )
    version = value.get("metadata_version")
    recovery = value.get("recovery")
    if version != 1:
        return "invalid", RecoveryIssue(
            "ERROR_RECOVERY_FORMAT_UNREGISTERED",
            "use_supported_engine",
            f"Metadata version is not registered: {version!r}",
            "metadata_version",
        )
    unknown_fields = set(value) - _REGISTERED_METADATA_FIELDS
    if unknown_fields:
        return "invalid", RecoveryIssue(
            "ERROR_RECOVERY_FORMAT_UNREGISTERED",
            "inspect_machine_metadata",
            "Metadata contains unregistered top-level fields",
            "metadata",
        )
    managed_fields = set(value) & _MANAGED_AUTHORITY_FIELDS
    if managed_fields:
        if "terminal" not in managed_fields or recovery is not None:
            return "invalid", RecoveryIssue(
                "ERROR_MACHINE_METADATA_INVALID",
                "inspect_machine_metadata",
                "Metadata contains machine authority that recovery cannot replace",
                "metadata",
            )
        return "managed", None
    if recovery is not None and not isinstance(recovery, dict):
        return "invalid", RecoveryIssue(
            "ERROR_RECOVERY_JSON_AMBIGUOUS",
            "inspect_machine_metadata",
            "Recovery JSON is not an object",
            "recovery",
        )
    if isinstance(recovery, dict) and recovery.get("recovery_version") != 1:
        return "invalid", RecoveryIssue(
            "ERROR_RECOVERY_FORMAT_UNREGISTERED",
            "use_supported_engine",
            "Recovery JSON version is not registered",
            "recovery_version",
        )
    if isinstance(recovery, dict):
        registered_fields = {
            "recovery_version",
            "archive_date",
            "short_name",
            "terminal_status",
            "summary",
            "timestamp",
            "confirmed_evidence",
            "operation",
        }
        if not set(recovery).issubset(registered_fields):
            return "invalid", RecoveryIssue(
                "ERROR_RECOVERY_FORMAT_UNREGISTERED",
                "use_supported_engine",
                "Recovery JSON contains fields outside the registered v1 mapping",
                "recovery",
            )
        if set(recovery) != registered_fields or not _recovery_values_well_formed(recovery):
            return "recoverable", None
        if target == "archive" and (
            recovery["archive_date"] != archive_date
            or recovery["short_name"] != short_name
            or recovery["terminal_status"] != expected_status
        ):
            return "invalid", RecoveryIssue(
                "ERROR_RECOVERY_EVIDENCE_AMBIGUOUS",
                "inspect_archive_state",
                "Recovery JSON identity or status conflicts with archive authority",
                "recovery",
            )
    return "valid", None


def _recovery_values_well_formed(recovery: dict[str, Any]) -> bool:
    evidence = recovery.get("confirmed_evidence")
    operation = recovery.get("operation")
    return (
        isinstance(recovery.get("archive_date"), str)
        and bool(_DATE.fullmatch(recovery["archive_date"]))
        and isinstance(recovery.get("short_name"), str)
        and bool(re.fullmatch(r"[a-z0-9][a-z0-9-]*", recovery["short_name"]))
        and recovery.get("terminal_status") in {"completed", "abandoned"}
        and isinstance(recovery.get("summary"), str)
        and bool(recovery["summary"].strip())
        and "\n" not in recovery["summary"]
        and "\r" not in recovery["summary"]
        and isinstance(recovery.get("timestamp"), str)
        and bool(_TIMESTAMP.fullmatch(recovery["timestamp"]))
        and isinstance(evidence, dict)
        and set(evidence) == {"proposal_sha256", "tasks_sha256"}
        and all(
            isinstance(evidence.get(field), str)
            and bool(_SHA256.fullmatch(evidence[field]))
            for field in ("proposal_sha256", "tasks_sha256")
        )
        and isinstance(operation, dict)
        and set(operation) == {"kind", "operation_id"}
        and operation.get("kind") == "repair-archive-record"
        and isinstance(operation.get("operation_id"), str)
        and bool(_SHA256.fullmatch(operation["operation_id"]))
    )


def _model_evidence(model: Any, proposal_text: str, tasks_text: str) -> tuple[FieldEvidence, ...]:
    values = {
        "status": model.status or "",
        "change_type": model.change_type or "",
        "scope": _section_semantic_text(_sections(proposal_text).get("影響範圍")) or "",
        "acceptance": "\n".join(model.acceptance_conditions),
        "tasks": tasks_text,
    }
    sources = {"tasks": "tasks.md", "acceptance": "tasks.md"}
    return tuple(
        _evidence(field, sources.get(field, "proposal.md"), value)
        for field, value in sorted(values.items())
    )


def _render_proposal(
    short_name: str,
    status: str,
    change_type: str,
    why: str,
    changes: str,
    scope: str,
) -> bytes:
    return (
        "---\nschema_version: 2\n---\n"
        f"# {short_name}\n\n"
        f"## 狀態\n{status}\n\n"
        f"## 類型\n{change_type}\n\n"
        f"## 為什麼做\n{why}\n\n"
        f"## 要改什麼\n{changes}\n\n"
        f"## 影響範圍\n{scope}\n"
    ).encode("utf-8")


def _render_tasks(
    short_name: str,
    tasks: tuple[tuple[bool, str], ...],
    acceptance: tuple[str, ...],
) -> bytes:
    task_lines = "\n".join(
        f"- [{'x' if completed else ' '}] {text}" for completed, text in tasks
    )
    acceptance_lines = "\n".join(f"- {item}" for item in acceptance)
    return (
        f"# {short_name} 任務\n\n{task_lines}\n\n"
        f"## 驗收條件\n\n{acceptance_lines}\n"
    ).encode("utf-8")


def _evidence(field: str, source: str, value: str) -> FieldEvidence:
    return FieldEvidence(field, source, _sha256(value.encode("utf-8")))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ambiguous(field: str, message: str) -> RecoveryIssue:
    return RecoveryIssue(
        "ERROR_RECOVERY_EVIDENCE_AMBIGUOUS",
        "upgrade_or_recreate_proposal",
        message,
        field,
    )


def _conflict(field: str) -> RecoveryIssue:
    return RecoveryIssue(
        "ERROR_RECOVERY_INPUT_CONFLICT",
        "inspect_recovery_evidence",
        f"Explicit input must not override existing authority: {field}",
        field,
    )


def _blocked(
    target: RecoveryTarget,
    source: list[tuple[str, str]],
    issues: tuple[RecoveryIssue, ...],
    required: tuple[str, ...] = (),
    evidence: tuple[FieldEvidence, ...] = (),
) -> RecoveryProjection:
    return RecoveryProjection(
        target=target,
        disposition="blocked",
        encoding=None,
        source_digests=tuple(source),
        candidate_digests=(),
        required_inputs=tuple(sorted(set(required))),
        changes=(),
        evidence=tuple(sorted(evidence, key=lambda item: item.field)),
        issues=tuple(issues),
    )
