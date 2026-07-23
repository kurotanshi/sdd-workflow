"""Focused checks for duplicated public contract facts."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core.cli import build_parser  # noqa: E402


def validate_docs() -> None:
    readme_zh = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    contributing_zh = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    contributing_en = (ROOT / "CONTRIBUTING.en.md").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    cli_contract = (ROOT / "docs/cli-contract.md").read_text(encoding="utf-8")
    runtime = (ROOT / "docs/runtime.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    decision_template = (ROOT / "docs/decisions/TEMPLATE.md").read_text(encoding="utf-8")
    friction_log = (ROOT / "docs/friction-log.md").read_text(encoding="utf-8")
    adoption_decision = (
        ROOT / "docs/decisions/2026-07-22-readonly-parsing-adoption.md"
    ).read_text(encoding="utf-8")
    v04_entry = (ROOT / "docs/decisions/2026-07-22-v04-entry.md").read_text(
        encoding="utf-8"
    )
    v04_reassessment = (
        ROOT / "docs/decisions/2026-07-22-v04-entry-reassessment.md"
    ).read_text(encoding="utf-8")
    v04_activation = (
        ROOT / "docs/decisions/2026-07-22-managed-mutation-activation.md"
    ).read_text(encoding="utf-8")
    architecture = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    approval_manifest = (ROOT / "docs/approval-manifest.md").read_text(
        encoding="utf-8"
    )
    managed_state = (ROOT / "docs/managed-state.md").read_text(encoding="utf-8")
    archive_model = (ROOT / "docs/archive-model.md").read_text(encoding="utf-8")
    doctor_diagnostics = (ROOT / "docs/doctor-diagnostics.md").read_text(encoding="utf-8")
    transaction_protocol = (ROOT / "docs/transaction-protocol.md").read_text(encoding="utf-8")
    compatibility = (ROOT / "docs/compatibility.md").read_text(encoding="utf-8")
    schema_v2 = (ROOT / "docs/schema-v2.md").read_text(encoding="utf-8")
    team_operations = (ROOT / "docs/team-operations.md").read_text(encoding="utf-8")
    team_decision = (
        ROOT / "docs/decisions/2026-07-22-team-readiness-entry.md"
    ).read_text(encoding="utf-8")
    entrypoint = (ROOT / "skills/sdd-workflow/scripts/sdd.py").read_text(encoding="utf-8")
    skill = (ROOT / "skills/sdd-workflow/SKILL.md").read_text(encoding="utf-8")

    zh_version = re.search(r"^> 版本 (v\d+\.\d+\.\d+)", readme_zh, re.MULTILINE)
    en_version = re.search(r"^> Version (v\d+\.\d+\.\d+)", readme_en, re.MULTILINE)
    if not zh_version or not en_version or zh_version.group(1) != en_version.group(1):
        raise AssertionError("README versions are inconsistent")
    if zh_version.group(1) != "v0.6.0":
        raise AssertionError("README version does not match the active engine")
    for readme in (readme_zh, readme_en):
        if "[`ROADMAP.md`](./ROADMAP.md)" not in readme:
            raise AssertionError("README is missing ROADMAP link")
        if "`取消提案`" not in readme:
            raise AssertionError("README is missing explicit cancellation trigger")
        for category in (
            "docs/concepts/",
            "docs/operations/",
            "docs/compatibility/",
            "docs/design/",
            "docs/troubleshooting/",
        ):
            if category not in readme:
                raise AssertionError(
                    f"README is missing advanced documentation category: {category}"
                )
        if "~/.agents/skills/sdd-workflow/" not in readme:
            raise AssertionError("README is missing the current Codex install root")
        if "~/.codex/skills/" in readme:
            raise AssertionError("README still recommends the legacy Codex install root")

    for changelog_term in (
        "## v0.3.0",
        "### Breaking",
        "### Rollback",
        "CPython 3.11",
        "`v0.2.4`",
    ):
        if changelog_term not in changelog:
            raise AssertionError(f"CHANGELOG is missing v0.3 contract term: {changelog_term}")

    parser = build_parser()
    cli_help = parser.format_help()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    for command in subparsers.choices:
        if command not in cli_help:
            raise AssertionError(f"CLI help is missing registered command: {command}")
        if f"sdd.py [--root PATH] [--json] {command}" not in cli_contract:
            raise AssertionError(f"CLI contract is missing command syntax: {command}")
    if "public `parse` command are intentionally absent" not in cli_contract:
        raise AssertionError("CLI contract does not exclude public parse command")
    for managed_command in (
        "--expected-snapshot",
        "begin-revision",
        "complete-task",
        "archive <short-name>",
        "abandon <short-name>",
    ):
        if managed_command not in skill:
            raise AssertionError(
                f"managed mutation command is absent from SKILL.md: {managed_command}"
            )

    if "Minimum supported runtime: CPython `3.11`" not in runtime:
        raise AssertionError("runtime document minimum is inconsistent")
    if "MINIMUM_PYTHON = (3, 11)" not in entrypoint:
        raise AssertionError("entrypoint minimum is inconsistent")
    if "python3 scripts/sdd.py" not in runtime:
        raise AssertionError("runtime document is missing the Skill invocation form")
    for platform_row in ("| macOS | Supported |", "| Linux | Supported |", "| Windows | Best effort |"):
        if platform_row not in runtime:
            raise AssertionError(f"runtime platform row is missing: {platform_row}")

    for heading in (
        "## Date",
        "## Versions",
        "## Evaluated scenarios",
        "## Observed evidence",
        "## Rejected alternatives",
        "## Decision",
        "## Rollback boundary",
        "## Sensitive-data review",
    ):
        if heading not in decision_template:
            raise AssertionError(f"decision template is missing field: {heading}")
    for field in (
        "- Date:",
        "- Versions:",
        "- Scenario:",
        "- Observed friction or failure:",
        "- Severity:",
        "- Evidence:",
        "- Manual intervention:",
        "- Disposition:",
        "- Related decision:",
    ):
        if field not in friction_log:
            raise AssertionError(f"friction log is missing field: {field}")
    for privacy_term in ("full user transcript", "credentials", "personal data"):
        if privacy_term not in decision_template or privacy_term not in friction_log:
            raise AssertionError(f"evidence privacy rule is missing: {privacy_term}")
    for decision_term in (
        "## Decision",
        "`GO` for the v0.3 readonly paths only",
        "Codex CLI `0.145.0`",
        "Claude Code `2.1.217`",
        "F-20260722-01",
        "F-20260722-02",
        "F-20260722-03",
        "pin or reinstall prose-only `v0.2.4`",
    ):
        if decision_term not in adoption_decision:
            raise AssertionError(f"adoption decision is missing evidence: {decision_term}")
    for friction_id in ("F-20260722-01", "F-20260722-02", "F-20260722-03"):
        if friction_id not in friction_log:
            raise AssertionError(f"friction log is missing pilot entry: {friction_id}")
    for entry_term in (
        "## Decision",
        "`DEFER`",
        "add-machine-metadata-and-approval-manifest",
        "roadmap completeness is explicitly not entry evidence",
    ):
        if entry_term not in v04_entry:
            raise AssertionError(f"v0.4 entry decision is missing evidence: {entry_term}")
    for reassessment_term in (
        "`GO` for implementing the experimental v0.4 transaction proposals",
        "29 real task completions",
        "F-20260722-04",
        "does not activate any new Skill mutation path",
    ):
        if reassessment_term not in v04_reassessment:
            raise AssertionError(
                f"v0.4 reassessment is missing evidence: {reassessment_term}"
            )
    if "F-20260722-04" not in friction_log:
        raise AssertionError("friction log is missing dogfood usage evidence")
    for activation_term in (
        "`GO` for the coherent v0.4 managed mutation group",
        "Codex CLI `0.145.0`",
        "Claude Code `2.1.217`",
        "F-20260722-05",
        "Pinning `v0.3.0` is safe only",
    ):
        if activation_term not in v04_activation:
            raise AssertionError(
                f"v0.4 activation decision is missing evidence: {activation_term}"
            )
    if "F-20260722-05" not in friction_log:
        raise AssertionError("friction log is missing managed pilot entry")
    for schema_term in (
        "schema_version: 2",
        "`維運`, `文件`, `研究`",
        "`sdd.schema`",
        "`sdd.research.conclusion`",
        "ERROR_UNKNOWN_SCHEMA_FIELD",
        "No label, explicit-impact vocabulary",
    ):
        if schema_term not in schema_v2:
            raise AssertionError(f"Schema v2 contract is missing: {schema_term}")
    for decision_term in (
        "F-20260722-06",
        "F-20260722-07",
        "`NO-GO` for impacts, labels",
    ):
        if decision_term not in (ROOT / "docs/decisions/2026-07-22-schema-v2-entry.md").read_text(encoding="utf-8"):
            raise AssertionError(f"Schema v2 decision is missing evidence: {decision_term}")
    for architecture_term in (
        "`proposal.md` `## 狀態`",
        "`tasks.md` checkbox markers",
        "`.sdd/metadata.json`",
        "`.sdd/approval-manifest.json`",
        "Active metadata version",
        "Approval model version",
        "ERROR_METADATA_STATE_MISMATCH",
        "ERROR_APPROVAL_MANIFEST_REQUIRED",
        "status replacement to `approved` is the authoritative commit point",
        "status replacement to `draft` is the authoritative commit point",
    ):
        if architecture_term not in architecture:
            raise AssertionError(
                f"architecture metadata contract is missing: {architecture_term}"
            )
    for manifest_term in (
        '"approval_model_version": 1',
        '"scope"',
        '"acceptance_conditions"',
        '"tasks"',
        "task `completed`, ordinal, and source line",
        "`## 為什麼做` (`why`)",
        "`## 影響範圍` (`impact`)",
        "Preserve Unicode code points exactly",
        "JSON Pointer",
        "Every `CanonicalProposal` field",
    ):
        if manifest_term not in approval_manifest:
            raise AssertionError(
                f"Approval Manifest contract is missing: {manifest_term}"
            )
    for managed_term in (
        "Attestation version: `1`",
        "`inspect_managed_state_drift`",
        "`projection_sha256`",
        "the `attestation` field itself",
        "task text/digest",
        "cannot identify the editor",
        "read-only commands never create, replace, or refresh an attestation",
        "transitional unattested state",
    ):
        if managed_term not in managed_state:
            raise AssertionError(
                f"managed-state contract is missing: {managed_term}"
            )
    for archive_term in (
        "Archive model version: `1`",
        '"terminal_metadata_version": 1',
        '"source_snapshot"',
        '"operation_id"',
        "legacy INDEX row",
        "never authoritative for managed records",
        "Missing legacy summary is an error",
        "`ARCHIVE_RECORD_MISMATCH`",
        "`AMBIGUOUS_STATE`",
        "`UNKNOWN_STATE`",
    ):
        if archive_term not in archive_model:
            raise AssertionError(f"archive model contract is missing: {archive_term}")
    for doctor_term in (
        "`AMBIGUOUS_STATE`",
        "`UNKNOWN_STATE`",
        "`PARTIAL_TRANSITION_DETECTED`",
        "`OUT_OF_BAND_DRIFT`",
        "does not refresh attestation",
        "do not select the first/last entry automatically",
        "avoids “was modified by,” “caused by,”",
    ):
        if doctor_term not in doctor_diagnostics:
            raise AssertionError(f"doctor evidence contract is missing: {doctor_term}")
    for terminal_term in (
        "directory move",
        "sole authoritative terminal commit point",
        "`COMMITTED_DERIVED_ARTIFACT_STALE`",
        "local calendar date",
        "`ALREADY_APPLIED`",
        "Deleting metadata is not downgrade",
        "does not choose a timestamp",
    ):
        if terminal_term not in transaction_protocol:
            raise AssertionError(f"transaction protocol is missing: {terminal_term}")
    for axis in (
        "CLI output",
        "Proposal schema",
        "Canonical model",
        "Snapshot",
        "Active metadata",
        "Approval model",
        "Managed attestation",
        "Archive model",
        "Terminal metadata",
    ):
        if axis not in compatibility:
            raise AssertionError(f"compatibility matrix is missing axis: {axis}")

    required_checks = {
        "unit",
        "fixtures",
        "package-validation",
        "docs-consistency",
        "install-smoke",
    }
    workflow_jobs = set(re.findall(r"^  ([a-z][a-z0-9-]*):\s*$", workflow, re.MULTILINE))
    if not required_checks <= workflow_jobs:
        raise AssertionError("CI workflow is missing a stable required-check job")
    for check in required_checks:
        if f"    name: {check}\n" not in workflow:
            raise AssertionError(f"CI check display name is unstable: {check}")
        if f"`{check}`" not in contributing_zh or f"`{check}`" not in contributing_en:
            raise AssertionError(f"contributor docs are missing required check: {check}")

    for team_term in (
        "One proposal has exactly one active agent/operator at a time",
        "a separate Git worktree",
        "Archive directories are authoritative",
        "validate-index",
        "rebuild-index",
        "A stale but rebuildable INDEX does not justify a global lock",
    ):
        if team_term not in team_operations:
            raise AssertionError(f"team operation contract is missing: {team_term}")
    for decision_term in (
        "`NO-GO` for a lock or INDEX-level CAS in v0.6.0",
        "Six parallel `rebuild-index` processes",
        "No contention test demonstrated authoritative data loss",
    ):
        if decision_term not in team_decision:
            raise AssertionError(f"team-readiness decision is missing: {decision_term}")
    if "| Engine/release | `0.6.0` active |" not in compatibility:
        raise AssertionError("compatibility engine version is not current")
    if "## v0.6.0" not in changelog:
        raise AssertionError("CHANGELOG is missing the active release")


def main() -> int:
    validate_docs()
    print("docs-consistency: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
