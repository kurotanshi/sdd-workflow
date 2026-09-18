"""Description-only skill router for offline selection smoke tests.

The router decides solely from the provided ``description_view`` string.
It never opens SKILL.md. This is a polarity-aware keyword smoke test, not a
live multi-skill host bakeoff.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


INVOKE_MARKERS = (
    "sdd-workflow",
    "提案",
    "自審提案",
    "開始實作",
    "歸檔",
    "取消提案",
    "確認放棄",
)


@dataclass(frozen=True)
class RouteDecision:
    invoke: bool
    reason: str


def _view_lower(view: str) -> str:
    return view.lower()


def _generic_cancel_polarity(view: str) -> str:
    """Return outside|inside|unknown for generic-cancel scope in description_view."""
    v = _view_lower(view)
    # Explicit inclusion (reversed / wrong skill text)
    if re.search(r"\buse for generic cancel\b", v) or re.search(
        r"\binside this skill\b.*generic cancel|generic cancel.*\binside this skill\b", v
    ):
        return "inside"
    if (
        "outside: generic cancel" in v
        or "not for generic cancel" in v
        or "generic cancellation without an explicit sdd proposal target is outside this skill" in v
        or ("generic cancel" in v and "outside" in v)
    ):
        return "outside"
    return "unknown"


def _rollback_polarity(view: str) -> str:
    v = _view_lower(view)
    if re.search(r"\buse for\b.*\brollback\b", v) and "outside" not in v.split("rollback")[0][-40:]:
        # Inclusion phrasing such as "Use for generic cancel or git/code rollback".
        if not re.search(r"\b(outside|not for)\b.*\brollback\b", v):
            return "inside"
    if (
        "outside: generic cancel & git/code rollback" in v
        or ("git/code rollback" in v and "outside" in v)
        or "source-control or code rollback is outside sdd" in v
        or re.search(r"\boutside\b.*\brollback\b|\brollback\b.*\boutside\b", v)
    ):
        return "outside"
    return "unknown"


def _is_generic_cancel_utterance(utt: str) -> bool:
    if re.search(r"^(取消剛才的變更|取消|算了|不用了)$", utt):
        return True
    if re.search(r"放棄剛才的變更|取消剛才的變更", utt):
        return True
    return False


def _is_rollback_utterance(utt: str) -> bool:
    return bool(re.search(r"rollback|回滾|還原程式", utt.lower()))


def _has_invoke_marker(utt: str, view: str) -> str | None:
    utt_l = utt.lower()
    # Prefer longer markers first
    for marker in sorted(INVOKE_MARKERS, key=len, reverse=True):
        if marker.lower() in utt_l or marker in utt:
            if marker.lower() in view.lower() or marker in view:
                return marker
    # Bare 實作 / 放棄 only when not a generic-cancel utterance
    if _is_generic_cancel_utterance(utt):
        return None
    if (utt == "實作" or utt.startswith("實作 ")) and "實作" in view:
        return "實作"
    if re.search(r"^放棄(\s|$)", utt) and "放棄" in view and "剛才" not in utt:
        return "放棄"
    return None


def route(utterance: str, description_view: str) -> RouteDecision:
    if not description_view.strip():
        return RouteDecision(False, "empty description view")

    utt = utterance.strip()
    view = description_view

    if _is_generic_cancel_utterance(utt):
        polarity = _generic_cancel_polarity(view)
        if polarity == "outside":
            return RouteDecision(False, "generic cancel outside per description_view polarity")
        if polarity == "inside":
            return RouteDecision(True, "generic cancel included by description_view polarity")
        return RouteDecision(False, "generic cancel without clear outside polarity")

    if _is_rollback_utterance(utt):
        polarity = _rollback_polarity(view)
        if polarity == "outside":
            return RouteDecision(False, "rollback outside per description_view polarity")
        if polarity == "inside":
            return RouteDecision(True, "rollback included by description_view polarity")
        return RouteDecision(False, "rollback without clear outside polarity")

    marker = _has_invoke_marker(utt, view)
    if marker:
        return RouteDecision(True, f"trigger {marker}")

    if "sdd-workflow" in utt.lower() and "sdd-workflow" in view.lower():
        return RouteDecision(True, "explicit skill name")

    return RouteDecision(False, "no description_view-backed trigger")
