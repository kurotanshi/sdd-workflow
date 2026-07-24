"""Test-only, Agent-neutral policy adapter for contract conformance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DESCRIPTOR = {
    "adapter_contract_version": 1,
    "adapter_id": "sdd-hermetic-policy-adapter",
    "adapter_version": 1,
    "implementation_kind": "hermetic-test",
    "supported_hosts": [],
    "required_handshake_version": 1,
    "required_capabilities": [
        "approval-manifest-v1",
        "managed-transitions-v1",
        "terminal-transitions-v1",
    ],
}


@dataclass(frozen=True, slots=True)
class AdapterDecision:
    actions: tuple[str, ...]
    handoff: str


class HermeticPolicyAdapter:
    """Map canonical state and user turns to observable protocol actions.

    This adapter never invokes an Agent or mutates files. The runner compares
    its decision trace with the public scenario contract.
    """

    descriptor = DESCRIPTOR

    def decide(self, initial_state: str, turns: list[str]) -> AdapterDecision:
        conversation = "\n".join(turns)

        if initial_state == "discovery-failure":
            return AdapterDecision(
                ("discover-runtime", "handoff-runtime-remediation"),
                "runtime-remediation",
            )
        if initial_state == "terminal-move-committed-index-stale":
            return AdapterDecision(
                ("recognize-terminal-authority", "rebuild-index", "doctor"),
                "terminal-summary",
            )
        if initial_state == "approved-snapshot-changed":
            return AdapterDecision(
                ("status", "report-stale-evidence", "handoff-for-renewed-intent"),
                "renewed-intent",
            )
        if "取消剛才" in conversation:
            return AdapterDecision(
                ("handoff-for-cancellation-scope",),
                "git-or-sdd-choice",
            )
        if initial_state == "multiple-valid-active":
            return AdapterDecision(
                ("list", "handoff-for-proposal-choice"),
                "proposal-choice",
            )
        if initial_state == "empty-project" and "提案" in conversation:
            return AdapterDecision(
                ("create-draft", "validate", "status", "handoff-for-approval"),
                "explicit-approval",
            )

        requirement_change = any(
            marker in conversation
            for marker in ("再加", "新增需求", "改成", "需求變更")
        )
        if initial_state.startswith("approved") and requirement_change:
            return AdapterDecision(
                (
                    "status",
                    "begin-revision",
                    "edit-authorized-semantics",
                    "validate",
                    "status",
                    "handoff-for-reapproval",
                ),
                "explicit-reapproval",
            )
        if initial_state == "approved-in-progress" and "確認放棄" in conversation:
            return AdapterDecision(
                (
                    "abandon-preflight",
                    "handoff-for-exact-confirmation",
                    "status",
                    "abandon",
                ),
                "terminal-summary",
            )
        if initial_state == "one-valid-draft" and "開始實作" in conversation:
            return AdapterDecision(
                (
                    "status",
                    "approve",
                    "status",
                    "implement-one-task",
                    "verify",
                    "complete-task",
                    "status",
                ),
                "task-progress",
            )
        if initial_state == "one-valid-draft" and "實作" in conversation:
            return AdapterDecision(
                ("status", "handoff-for-approval"),
                "explicit-approval",
            )
        return AdapterDecision(
            ("handoff-unsupported-state",),
            "human-inspection",
        )


def is_subsequence(required: list[str], actual: tuple[str, ...]) -> bool:
    remaining = iter(actual)
    return all(any(candidate == action for candidate in remaining) for action in required)


def evaluate(case: dict[str, Any], decision: AdapterDecision) -> dict[str, Any]:
    required = case.get("required_actions")
    prohibited = case.get("prohibited_actions")
    expected_handoff = case.get("expected_handoff")
    if (
        not isinstance(case.get("id"), str)
        or not isinstance(required, list)
        or not all(isinstance(action, str) for action in required)
        or not isinstance(prohibited, list)
        or not all(isinstance(action, str) for action in prohibited)
        or not isinstance(expected_handoff, str)
    ):
        raise ValueError("invalid adapter scenario")
    differences: list[dict[str, Any]] = []
    if not is_subsequence(required, decision.actions):
        differences.append(
            {
                "path": "/actions",
                "expected": {"ordered_subsequence": required},
                "actual": list(decision.actions),
            }
        )
    observed_prohibited = [
        action for action in prohibited if action in decision.actions
    ]
    if observed_prohibited:
        differences.append(
            {
                "path": "/prohibited_actions",
                "expected": [],
                "actual": observed_prohibited,
            }
        )
    if decision.handoff != expected_handoff:
        differences.append(
            {
                "path": "/handoff",
                "expected": expected_handoff,
                "actual": decision.handoff,
            }
        )
    return {
        "scenario_id": case["id"],
        "passed": not differences,
        "actions": list(decision.actions),
        "handoff": decision.handoff,
        "differences": differences,
    }
