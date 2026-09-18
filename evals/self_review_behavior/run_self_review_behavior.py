#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from policy import (  # noqa: E402
    Action,
    AuthorityClarity,
    ChangeKind,
    ProposalStatus,
    Scenario,
    assert_conformance,
    decide,
)

CASES = HERE / "cases.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    assert_conformance()
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        scenario = Scenario(
            status=ProposalStatus(case["status"]),
            change_kind=ChangeKind(case["change_kind"]),
            authority=AuthorityClarity(case["authority"]),
        )
        decision = decide(scenario)
        ok = decision.action.value == case["expect_action"]
        if "expect_must_ask_user" in case:
            ok = ok and decision.must_ask_user == case["expect_must_ask_user"]
        if "expect_may_approve" in case:
            ok = ok and decision.may_approve == case["expect_may_approve"]
        if "expect_may_implement" in case:
            ok = ok and decision.may_implement == case["expect_may_implement"]
        # Hard behavioral invariant for every case
        ok = ok and (not decision.may_approve) and (not decision.may_implement)
        results.append({**case, "got_action": decision.action.value, "pass": ok, "reason": decision.reason})
    passed = sum(1 for r in results if r["pass"])
    report = {"score": f"{passed}/{len(results)}", "pass": passed == len(results), "cases": results}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(f"[{'PASS' if r['pass'] else 'FAIL'}] {r['id']}: expect={r['expect_action']} got={r['got_action']}")
        print(f"score {report['score']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
