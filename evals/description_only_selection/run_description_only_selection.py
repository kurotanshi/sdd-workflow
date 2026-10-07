#!/usr/bin/env python3
"""Rerunnable 8-case description-only selection runner.

Uses ONLY the first TRUNCATE_CHARS of SKILL.md description as description_view.
Never passes the full description into the router.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from router import route  # noqa: E402

TRUNCATE_CHARS = 160
CASES = Path(__file__).with_name("cases.json")
SKILL = ROOT / "skills/sdd-workflow/SKILL.md"


def load_truncated_description(skill_path: Path = SKILL, limit: int = TRUNCATE_CHARS) -> str:
    text = skill_path.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    match = re.search(r'description:\s*"(.*)"', frontmatter, re.S)
    if not match:
        raise SystemExit("SKILL.md description not found")
    full = match.group(1)
    return full[:limit]


def run(limit: int = TRUNCATE_CHARS) -> dict:
    view = load_truncated_description(limit=limit)
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        decision = route(case["utterance"], view)
        results.append(
            {
                **case,
                "predicted_invoke": decision.invoke,
                "reason": decision.reason,
                "pass": decision.invoke == case["expect_invoke"],
            }
        )
    passed = sum(1 for r in results if r["pass"])
    return {
        "truncate_chars": limit,
        "description_view": view,
        "description_view_len": len(view),
        "score": f"{passed}/{len(results)}",
        "pass": passed == len(results),
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=TRUNCATE_CHARS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run(limit=args.limit)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"description_view ({report['description_view_len']} chars):\n{report['description_view']}\n")
        for r in report["cases"]:
            mark = "PASS" if r["pass"] else "FAIL"
            print(f"[{mark}] {r['id']}: expect={r['expect_invoke']} got={r['predicted_invoke']} ({r['reason']})")
        print(f"\nscore {report['score']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
