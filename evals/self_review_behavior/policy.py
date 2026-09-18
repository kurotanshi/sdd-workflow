"""Executable self-review policy used for behavioral checklist evidence.

Decisions mirror ``skills/sdd-workflow/references/self-review.md``.
Conformance helpers fail if required phrases are removed or reversed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
SELF_REVIEW = ROOT / "skills/sdd-workflow/references/self-review.md"


class ChangeKind(str, Enum):
    EXISTING_LOGIC = "existing_logic"
    NEW_FILES = "new_files"
    CONFIG = "config"
    COPY = "copy"


class AuthorityClarity(str, Enum):
    NONE = "none"
    CLEAR = "clear"
    UNCLEAR = "unclear"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    OTHER = "other"


class Action(str, Enum):
    SKIP_LAYER3 = "skip_layer3"
    RUN_LAYER3_ASK_USER = "run_layer3_ask_user"
    STOP_AUTHORITY_UNCLEAR = "stop_authority_unclear"
    REPORT_AUTHORITY_SPLIT = "report_authority_split"
    FROZEN_REPORT_ONLY = "frozen_report_only"
    STOP_OTHER_STATUS = "stop_other_status"
    CONTINUE_LAYERS = "continue_layers"


REQUIRED_PHRASES: tuple[str, ...] = (
    "## Layer 3 — design direction",
    "Run this layer only when existing logic in existing files changes",
    "Pure new files, configuration additions, and copy changes skip it",
    "Do not choose for the user",
    "when evidence proves a split but cannot establish which location should remain authoritative, report it and stop rather than choosing",
    "Never call `approve` or implement",
    "`approved`: prose is frozen",
)

FORBIDDEN_PHRASES: tuple[str, ...] = (
    "automatically choose the authoritative location",
    "auto-select authority and continue",
    "choose the authoritative implementation for the user",
    "Run Layer 3 for pure new files",
    "skip Layer 3 when existing logic changes",
)


@dataclass(frozen=True)
class Scenario:
    status: ProposalStatus
    change_kind: ChangeKind
    authority: AuthorityClarity = AuthorityClarity.NONE
    layer0_premise_ok: bool = True


@dataclass(frozen=True)
class Decision:
    action: Action
    may_approve: bool
    may_implement: bool
    must_ask_user: bool
    reason: str


def load_self_review_text(path: Path = SELF_REVIEW) -> str:
    return path.read_text(encoding="utf-8")


def assert_conformance(text: str | None = None) -> None:
    source = load_self_review_text() if text is None else text
    missing = [p for p in REQUIRED_PHRASES if p not in source]
    present_forbidden = [p for p in FORBIDDEN_PHRASES if p in source]
    if missing or present_forbidden:
        raise AssertionError(
            "self-review policy conformance failed; "
            f"missing={missing!r} forbidden_present={present_forbidden!r}"
        )


def decide(scenario: Scenario, policy_text: str | None = None) -> Decision:
    """Decide self-review behavior for a structured scenario.

    If ``policy_text`` is supplied (including mutated text in tests), conformance
    is checked against that text before deciding. Decisions themselves follow the
    required-phrase semantics and intentionally do **not** implement reversed
    rules even if present—conformance must fail first for reversed docs.
    """
    assert_conformance(policy_text)

    if scenario.status is ProposalStatus.OTHER:
        return Decision(Action.STOP_OTHER_STATUS, False, False, False, "non-draft/approved status")
    if scenario.status is ProposalStatus.APPROVED:
        return Decision(Action.FROZEN_REPORT_ONLY, False, False, False, "approved prose frozen")

    # draft
    if not scenario.layer0_premise_ok:
        return Decision(Action.CONTINUE_LAYERS, False, False, False, "layer0 stop is reported by caller")

    if scenario.authority is AuthorityClarity.UNCLEAR:
        return Decision(
            Action.STOP_AUTHORITY_UNCLEAR,
            False,
            False,
            True,
            "authority split unclear; stop rather than choosing",
        )
    if scenario.authority is AuthorityClarity.CLEAR:
        # Still report; never auto-rewrite or approve.
        return Decision(
            Action.REPORT_AUTHORITY_SPLIT,
            False,
            False,
            True,
            "authority split reported; user decides resolution",
        )

    if scenario.change_kind is ChangeKind.EXISTING_LOGIC:
        return Decision(
            Action.RUN_LAYER3_ASK_USER,
            False,
            False,
            True,
            "existing logic changed; run Layer 3 and ask user",
        )
    return Decision(
        Action.SKIP_LAYER3,
        False,
        False,
        False,
        "new/config/copy change skips Layer 3",
    )


def decide_many(scenarios: Iterable[Scenario], policy_text: str | None = None) -> list[Decision]:
    assert_conformance(policy_text)
    return [decide(s, policy_text=policy_text) for s in scenarios]
