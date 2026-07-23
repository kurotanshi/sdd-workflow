"""Version-independent internal proposal model.

Markdown adapters terminate at these values. Later workflow logic consumes this
module and does not depend on headings, checkbox syntax, or legacy layout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable

from .diagnostics import Diagnostic


CANONICAL_MODEL_VERSION = 1


class ApprovalRelevance(str, Enum):
    RELEVANT = "relevant"
    EXCLUDED = "excluded"


CANONICAL_FIELD_APPROVAL_POLICY = MappingProxyType(
    {
        "model_version": ApprovalRelevance.EXCLUDED,
        "schema_version": ApprovalRelevance.EXCLUDED,
        "schema_version_declared": ApprovalRelevance.EXCLUDED,
        "short_name": ApprovalRelevance.RELEVANT,
        "status": ApprovalRelevance.EXCLUDED,
        "change_type": ApprovalRelevance.RELEVANT,
        "sections": ApprovalRelevance.RELEVANT,
        "tasks": ApprovalRelevance.RELEVANT,
        "acceptance_conditions": ApprovalRelevance.RELEVANT,
        "diagnostics": ApprovalRelevance.EXCLUDED,
        "extensions": ApprovalRelevance.RELEVANT,
    }
)

CANONICAL_SECTION_APPROVAL_POLICY = MappingProxyType(
    {
        "status": ApprovalRelevance.EXCLUDED,
        "change_type": ApprovalRelevance.EXCLUDED,
        "why": ApprovalRelevance.EXCLUDED,
        "changes": ApprovalRelevance.RELEVANT,
        "impact": ApprovalRelevance.EXCLUDED,
        "conclusion": ApprovalRelevance.EXCLUDED,
    }
)

CANONICAL_EXTENSION_APPROVAL_POLICY = MappingProxyType(
    {
        "sdd.schema": ApprovalRelevance.RELEVANT,
        "sdd.research.conclusion": ApprovalRelevance.EXCLUDED,
    }
)


@dataclass(frozen=True, slots=True)
class CanonicalSection:
    key: str
    heading: str
    body: tuple[str, ...]
    approval_relevance: ApprovalRelevance
    semantic_items: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key or not self.heading:
            raise ValueError("section key and heading must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "heading": self.heading,
            "body": list(self.body),
            "approval_relevance": self.approval_relevance.value,
            "semantic_items": list(self.semantic_items),
        }


@dataclass(frozen=True, slots=True)
class CanonicalTask:
    ordinal: int
    text: str
    completed: bool
    source_line: int
    approval_relevance: ApprovalRelevance = ApprovalRelevance.RELEVANT
    source_text: str | None = None

    def __post_init__(self) -> None:
        if self.ordinal < 1 or self.source_line < 1:
            raise ValueError("task ordinal and source line are one-based")
        if not self.text:
            raise ValueError("task text must not be empty")
        if self.source_text is not None and not self.source_text:
            raise ValueError("task source text must be non-empty when present")

    def to_dict(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "text": self.text,
            "completed": self.completed,
            "source_line": self.source_line,
            "approval_relevance": self.approval_relevance.value,
            "source_text": self.source_text,
        }


@dataclass(frozen=True, slots=True)
class TaskScanResult:
    tasks: tuple[CanonicalTask, ...]
    acceptance_conditions: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    counts_reliable: bool

    def __post_init__(self) -> None:
        if tuple(sorted(self.diagnostics, key=lambda item: item.sort_key)) != self.diagnostics:
            raise ValueError("task diagnostics must use deterministic order")

    @property
    def total_count(self) -> int:
        return len(self.tasks)

    @property
    def completed_count(self) -> int:
        return sum(task.completed for task in self.tasks)

    @property
    def uncompleted_count(self) -> int:
        return self.total_count - self.completed_count


@dataclass(frozen=True, slots=True)
class CanonicalExtension:
    """Namespaced adapter data with an explicit approval-integrity policy."""

    namespace: str
    value: Any
    approval_relevance: ApprovalRelevance

    def __post_init__(self) -> None:
        if not self.namespace:
            raise ValueError("extension namespace must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "namespace": self.namespace,
            "value": self.value,
            "approval_relevance": self.approval_relevance.value,
        }


@dataclass(frozen=True, slots=True)
class CanonicalProposal:
    schema_version: int
    schema_version_declared: bool
    short_name: str
    status: str | None
    change_type: str | None
    sections: tuple[CanonicalSection, ...]
    tasks: tuple[CanonicalTask, ...]
    acceptance_conditions: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...] = ()
    extensions: tuple[CanonicalExtension, ...] = ()
    model_version: int = field(default=CANONICAL_MODEL_VERSION, init=False)

    def __post_init__(self) -> None:
        if self.schema_version < 1:
            raise ValueError("schema version must be positive")
        if not self.short_name:
            raise ValueError("short name must not be empty")
        if tuple(sorted(self.diagnostics, key=lambda item: item.sort_key)) != self.diagnostics:
            raise ValueError("canonical diagnostics must use deterministic order")
        namespaces = [item.namespace for item in self.extensions]
        if len(namespaces) != len(set(namespaces)):
            raise ValueError("canonical extension namespaces must be unique")

    def approval_relevant_values(self) -> Iterable[tuple[str, Any]]:
        """Yield the semantic inputs a later Approval Manifest may project.

        Completion state is deliberately excluded while task text remains
        approval-relevant. The method is an extension hook, not a serialized
        manifest contract.
        """

        yield "short_name", self.short_name
        yield "change_type", self.change_type
        yield "sections", tuple(
            section
            for section in self.sections
            if section.approval_relevance is ApprovalRelevance.RELEVANT
        )
        yield "tasks", tuple(task.text for task in self.tasks)
        yield "acceptance_conditions", self.acceptance_conditions
        yield "extensions", tuple(
            extension
            for extension in self.extensions
            if extension.approval_relevance is ApprovalRelevance.RELEVANT
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_version": self.model_version,
            "schema_version": self.schema_version,
            "schema_version_declared": self.schema_version_declared,
            "short_name": self.short_name,
            "status": self.status,
            "change_type": self.change_type,
            "sections": [section.to_dict() for section in self.sections],
            "tasks": [task.to_dict() for task in self.tasks],
            "acceptance_conditions": list(self.acceptance_conditions),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "extensions": [extension.to_dict() for extension in self.extensions],
        }


@dataclass(frozen=True, slots=True)
class ParseOutcome:
    adapter: str | None
    readable: bool
    mutation_safe: bool
    task_counts_reliable: bool
    abandonment_readable: bool
    model: CanonicalProposal | None
    diagnostics: tuple[Diagnostic, ...]
    mutation_block_code: str | None = None

    def __post_init__(self) -> None:
        if tuple(sorted(self.diagnostics, key=lambda item: item.sort_key)) != self.diagnostics:
            raise ValueError("outcome diagnostics must use deterministic order")
        if self.model is not None and self.model.diagnostics != self.diagnostics:
            raise ValueError("model and outcome diagnostics must agree")
        if not self.readable and self.model is not None:
            raise ValueError("an unreadable outcome cannot contain a canonical model")

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "readable": self.readable,
            "mutation_safe": self.mutation_safe,
            "task_counts_reliable": self.task_counts_reliable,
            "abandonment_readable": self.abandonment_readable,
            "model": None if self.model is None else self.model.to_dict(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "mutation_block_code": self.mutation_block_code,
        }
