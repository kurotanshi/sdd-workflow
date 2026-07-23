#!/usr/bin/env python3
"""Resolve one compatible packaged SDD runtime without PATH lookup."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MINIMUM_PYTHON = (3, 11)
sys.dont_write_bytecode = True

if sys.version_info < MINIMUM_PYTHON:
    print(
        json.dumps(
            {
                "discovery_version": 1,
                "ok": False,
                "runtime": None,
                "error": {
                    "code": "RUNTIME_INCOMPATIBLE",
                    "action": "install_compatible_runtime",
                    "message": "Runtime discovery requires Python 3.11 or newer",
                },
            },
            sort_keys=True,
        )
    )
    raise SystemExit(1)

from sdd_core.runtime_discovery import (  # noqa: E402
    RuntimeDiscoveryError,
    discover_runtime,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", action="append", type=Path)
    arguments = parser.parse_args(argv)
    package_root = Path(__file__).resolve().parents[1]
    candidates = arguments.runtime
    try:
        runtime = discover_runtime(
            package_root,
            explicit_candidates=candidates,
        )
    except RuntimeDiscoveryError as error:
        envelope = {
            "discovery_version": 1,
            "ok": False,
            "runtime": None,
            "error": {
                "code": error.code,
                "action": error.action,
                "message": error.message,
            },
        }
        print(json.dumps(envelope, ensure_ascii=False, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "discovery_version": 1,
                "ok": True,
                "runtime": runtime,
                "error": None,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
