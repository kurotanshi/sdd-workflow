"""Emit deterministic fixture outcomes for cross-process comparison tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import parse_with_schema, scan_tasks  # noqa: E402


base = ROOT / "tests/fixtures/baseline"
manifest = json.loads((base / "MANIFEST.json").read_text())
outcomes: dict[str, object] = {}
for fixture in manifest["fixtures"]:
    if fixture["category"] == "discovery":
        continue
    fixture_path = base / fixture["path"]
    outcome = parse_with_schema(
        short_name=fixture["name"],
        proposal_text=(fixture_path / "proposal.md").read_text(),
        task_scan=scan_tasks(
            (fixture_path / "tasks.md").read_text(),
            path=f"{fixture['path']}/tasks.md",
        ),
        explicit_schema_version=fixture["input"]["explicit_schema_version"],
        proposal_path=f"{fixture['path']}/proposal.md",
    )
    outcomes[fixture["name"]] = outcome.to_dict()

json.dump(
    outcomes,
    sys.stdout,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
sys.stdout.write("\n")
