"""Versioned Approval Manifest projection, persistence bytes, and structural diff."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .model import ApprovalRelevance, CanonicalProposal


APPROVAL_MODEL_VERSION = 1
_MANIFEST_FIELDS = frozenset(
    {
        "approval_model_version",
        "short_name",
        "change_type",
        "scope",
        "acceptance_conditions",
        "tasks",
        "extensions",
    }
)


class ApprovalManifestError(ValueError):
    def __init__(self, code: str, action: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.action = action
        self.message = message


@dataclass(frozen=True, slots=True)
class ApprovalManifest:
    short_name: str
    change_type: str | None
    scope: tuple[str, ...]
    acceptance_conditions: tuple[str, ...]
    tasks: tuple[str, ...]
    extensions: tuple[tuple[str, Any], ...] = ()
    approval_model_version: int = APPROVAL_MODEL_VERSION

    def __post_init__(self) -> None:
        if self.approval_model_version != APPROVAL_MODEL_VERSION:
            raise ApprovalManifestError(
                "ERROR_UNSUPPORTED_APPROVAL_MODEL_VERSION",
                "use_supported_engine",
                f"Unsupported approval model version: {self.approval_model_version!r}",
            )
        if not isinstance(self.short_name, str) or not self.short_name:
            raise _invalid("short_name must be a non-empty string")
        if self.change_type is not None and not isinstance(self.change_type, str):
            raise _invalid("change_type must be a string or null")
        _require_string_tuple("scope", self.scope)
        _require_string_tuple("acceptance_conditions", self.acceptance_conditions)
        _require_string_tuple("tasks", self.tasks)
        namespaces = [namespace for namespace, _ in self.extensions]
        if namespaces != sorted(namespaces) or len(namespaces) != len(set(namespaces)):
            raise _invalid("extension namespaces must be unique and sorted")
        for namespace, value in self.extensions:
            if not isinstance(namespace, str) or not namespace:
                raise _invalid("extension namespace must be a non-empty string")
            _require_json_value(value, context=f"extension {namespace!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_model_version": self.approval_model_version,
            "short_name": self.short_name,
            "change_type": self.change_type,
            "scope": list(self.scope),
            "acceptance_conditions": list(self.acceptance_conditions),
            "tasks": [{"text": text} for text in self.tasks],
            "extensions": {namespace: value for namespace, value in self.extensions},
        }


@dataclass(frozen=True, slots=True)
class ApprovalDifference:
    path: str
    kind: str
    approved: Any = None
    current: Any = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"path": self.path, "kind": self.kind}
        if self.kind != "added":
            value["approved"] = self.approved
        if self.kind != "removed":
            value["current"] = self.current
        return value


def project_approval_manifest(
    model: CanonicalProposal,
    *,
    approval_model_version: int = APPROVAL_MODEL_VERSION,
) -> ApprovalManifest:
    if approval_model_version != APPROVAL_MODEL_VERSION:
        raise ApprovalManifestError(
            "ERROR_UNSUPPORTED_APPROVAL_MODEL_VERSION",
            "use_supported_engine",
            f"Unsupported approval model version: {approval_model_version!r}",
        )
    scope_sections = [section for section in model.sections if section.key == "changes"]
    if len(scope_sections) != 1:
        raise _invalid("canonical model must contain exactly one changes section")
    extensions: list[tuple[str, Any]] = []
    for extension in model.extensions:
        if extension.approval_relevance is not ApprovalRelevance.RELEVANT:
            continue
        _require_json_value(extension.value, context=f"extension {extension.namespace!r}")
        extensions.append((extension.namespace, _json_copy(extension.value)))
    extensions.sort(key=lambda item: item[0])
    return ApprovalManifest(
        approval_model_version=approval_model_version,
        short_name=model.short_name,
        change_type=model.change_type,
        scope=scope_sections[0].semantic_items,
        acceptance_conditions=model.acceptance_conditions,
        tasks=tuple(task.text for task in model.tasks),
        extensions=tuple(extensions),
    )


def serialize_approval_manifest(manifest: ApprovalManifest) -> bytes:
    return (
        json.dumps(
            manifest.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")


def parse_approval_manifest(data: bytes | str) -> ApprovalManifest:
    try:
        text = data.decode("utf-8", errors="strict") if isinstance(data, bytes) else data
        value = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _invalid(f"Approval Manifest is not valid UTF-8 JSON: {error}") from error
    if not isinstance(value, dict):
        raise _invalid("Approval Manifest root must be an object")
    fields = set(value)
    if fields != _MANIFEST_FIELDS:
        missing = sorted(_MANIFEST_FIELDS - fields)
        unknown = sorted(fields - _MANIFEST_FIELDS)
        raise _invalid(f"Approval Manifest fields differ: missing={missing}, unknown={unknown}")
    version = value["approval_model_version"]
    if type(version) is not int or version != APPROVAL_MODEL_VERSION:
        raise ApprovalManifestError(
            "ERROR_UNSUPPORTED_APPROVAL_MODEL_VERSION",
            "use_supported_engine",
            f"Unsupported approval model version: {version!r}",
        )
    scope = _string_array(value["scope"], "scope")
    acceptance = _string_array(value["acceptance_conditions"], "acceptance_conditions")
    task_values = value["tasks"]
    if not isinstance(task_values, list):
        raise _invalid("tasks must be an array")
    tasks: list[str] = []
    for index, task in enumerate(task_values):
        if not isinstance(task, dict) or set(task) != {"text"}:
            raise _invalid(f"tasks[{index}] must contain only text")
        text_value = task["text"]
        if not isinstance(text_value, str) or not text_value:
            raise _invalid(f"tasks[{index}].text must be a non-empty string")
        tasks.append(text_value)
    raw_extensions = value["extensions"]
    if not isinstance(raw_extensions, dict):
        raise _invalid("extensions must be an object")
    extensions = tuple(
        (namespace, _json_copy(extension_value))
        for namespace, extension_value in sorted(raw_extensions.items())
    )
    return ApprovalManifest(
        approval_model_version=version,
        short_name=value["short_name"],
        change_type=value["change_type"],
        scope=scope,
        acceptance_conditions=acceptance,
        tasks=tuple(tasks),
        extensions=extensions,
    )


def load_approval_manifest(path: Path) -> ApprovalManifest:
    if path.is_symlink() or not path.is_file():
        raise _invalid(f"Approval Manifest must be a regular file: {path}")
    try:
        return parse_approval_manifest(path.read_bytes())
    except OSError as error:
        raise _invalid(f"Approval Manifest could not be read: {path}: {error}") from error


def approval_manifest_sha256(manifest_or_bytes: ApprovalManifest | bytes) -> str:
    data = (
        serialize_approval_manifest(manifest_or_bytes)
        if isinstance(manifest_or_bytes, ApprovalManifest)
        else manifest_or_bytes
    )
    return hashlib.sha256(data).hexdigest()


def compare_approval_manifests(
    approved: ApprovalManifest,
    current: ApprovalManifest,
) -> tuple[ApprovalDifference, ...]:
    differences: list[ApprovalDifference] = []
    _diff_values(approved.to_dict(), current.to_dict(), "", differences)
    return tuple(differences)


def _diff_values(
    approved: Any,
    current: Any,
    path: str,
    differences: list[ApprovalDifference],
) -> None:
    if type(approved) is not type(current):
        differences.append(ApprovalDifference(path or "", "changed", approved, current))
        return
    if isinstance(approved, dict):
        for key in sorted(set(approved) | set(current)):
            child_path = f"{path}/{_pointer_escape(key)}"
            if key not in approved:
                differences.append(ApprovalDifference(child_path, "added", current=current[key]))
            elif key not in current:
                differences.append(ApprovalDifference(child_path, "removed", approved=approved[key]))
            else:
                _diff_values(approved[key], current[key], child_path, differences)
        return
    if isinstance(approved, list):
        shared = min(len(approved), len(current))
        for index in range(shared):
            _diff_values(approved[index], current[index], f"{path}/{index}", differences)
        for index in range(shared, len(approved)):
            differences.append(
                ApprovalDifference(f"{path}/{index}", "removed", approved=approved[index])
            )
        for index in range(shared, len(current)):
            differences.append(
                ApprovalDifference(f"{path}/{index}", "added", current=current[index])
            )
        return
    if approved != current:
        differences.append(ApprovalDifference(path or "", "changed", approved, current))


def _pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _string_array(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _invalid(f"{field} must be an array of strings")
    return tuple(value)


def _require_string_tuple(field: str, value: tuple[str, ...]) -> None:
    if not isinstance(value, tuple) or not all(isinstance(item, str) for item in value):
        raise _invalid(f"{field} must be a tuple of strings")


def _require_json_value(value: Any, *, context: str) -> None:
    try:
        json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise _invalid(f"{context} is not a JSON value: {error}") from error


def _json_copy(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))


def _invalid(message: str) -> ApprovalManifestError:
    return ApprovalManifestError(
        "ERROR_APPROVAL_MANIFEST_INVALID",
        "inspect_machine_metadata",
        message,
    )
