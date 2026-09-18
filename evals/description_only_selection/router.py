"""Description-only skill router for offline selection gates.

The router must decide solely from the provided ``description_view`` string.
It never opens SKILL.md and never consults text beyond that view.
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
    "放棄",
    "取消提案",
    "確認放棄",
)

# Bare 實作 is ambiguous in free chat; only treat as invoke when description_view
# presents it as an SDD phase trigger alongside other SDD markers.
PHASE_BARE_IMPLEMENT = "實作"

NEGATIVE_MARKERS = (
    "generic cancel",
    "git/code rollback",
    "source-control or code rollback",
    "without an explicit SDD proposal target",
)


@dataclass(frozen=True)
class RouteDecision:
    invoke: bool
    reason: str


def route(utterance: str, description_view: str) -> RouteDecision:
    """Return whether the skill should be selected using only description_view."""
    if not description_view.strip():
        return RouteDecision(False, "empty description view")

    view = description_view
    utt = utterance.strip()
    utt_l = utt.lower()

    # Negative utterances that the truncated description must be able to reject.
    if re.search(r"^(取消剛才的變更|取消|算了|不用了)$", utt):
        if any(m in view.lower() for m in ("generic cancel", "not generic cancel")):
            return RouteDecision(False, "generic cancellation out of scope per description_view")
    if re.search(r"rollback|回滾|還原程式", utt_l):
        if any(m in view.lower() for m in ("rollback", "git/code rollback")):
            return RouteDecision(False, "vcs/code rollback out of scope per description_view")

    # Explicit skill name
    if "sdd-workflow" in utt_l and "sdd-workflow" in view.lower():
        return RouteDecision(True, "explicit skill name")

    # Chinese / English phase triggers present in BOTH utterance and description_view
    for marker in INVOKE_MARKERS:
        if marker.lower() in utt_l or marker in utt:
            if marker.lower() in view.lower() or marker in view:
                return RouteDecision(True, f"trigger {marker}")

    # Bare implement only if description_view lists it as an SDD trigger.
    if utt == "實作" or utt.startswith("實作 "):
        if "實作" in view and ("開始實作" in view or "sdd" in view.lower()):
            return RouteDecision(True, "bare 實作 with SDD description_view")

    return RouteDecision(False, "no description_view-backed trigger")
