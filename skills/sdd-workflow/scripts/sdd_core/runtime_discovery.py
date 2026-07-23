"""Deterministic discovery and compatibility validation for the SDD runtime."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


DISCOVERY_VERSION = 1
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ENGINE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


@dataclass(frozen=True, slots=True)
class RuntimeDiscoveryError(RuntimeError):
    code: str
    action: str
    message: str

    def __str__(self) -> str:
        return self.message


def _error(code: str, action: str, message: str) -> RuntimeDiscoveryError:
    return RuntimeDiscoveryError(code, action, message)


def load_identity(package_root: Path) -> dict[str, Any]:
    path = package_root / "runtime-identity.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _error(
            "RUNTIME_INCOMPATIBLE",
            "reinstall_runtime",
            "Runtime identity manifest is missing or invalid",
        ) from error
    required = {
        "identity_version",
        "distribution_id",
        "handshake_version",
        "cli_output_version",
        "compatible_engine_generation",
        "minimum_schema_version",
        "maximum_schema_version",
        "required_capabilities",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise _error(
            "RUNTIME_INCOMPATIBLE",
            "reinstall_runtime",
            "Runtime identity manifest fields are unsupported",
        )
    if (
        value["identity_version"] != 1
        or not isinstance(value["distribution_id"], str)
        or type(value["handshake_version"]) is not int
        or type(value["cli_output_version"]) is not int
        or not isinstance(value["compatible_engine_generation"], str)
        or re.fullmatch(
            r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)",
            value["compatible_engine_generation"],
        )
        is None
        or type(value["minimum_schema_version"]) is not int
        or type(value["maximum_schema_version"]) is not int
        or value["minimum_schema_version"] > value["maximum_schema_version"]
        or not isinstance(value["required_capabilities"], list)
        or not all(
            isinstance(item, str) and item
            for item in value["required_capabilities"]
        )
        or value["required_capabilities"]
        != sorted(set(value["required_capabilities"]))
    ):
        raise _error(
            "RUNTIME_INCOMPATIBLE",
            "reinstall_runtime",
            "Runtime identity manifest values are unsupported",
        )
    return value


def _resolve_candidates(candidates: Sequence[Path]) -> tuple[Path, Path]:
    if not candidates:
        raise _error(
            "RUNTIME_NOT_FOUND",
            "reinstall_runtime",
            "Runtime discovery produced no candidate",
        )
    resolved: dict[Path, Path] = {}
    for installed in candidates:
        if not installed.is_absolute():
            raise _error(
                "RUNTIME_INCOMPATIBLE",
                "select_runtime",
                "Explicit runtime paths must be absolute",
            )
        try:
            target = installed.resolve(strict=True)
        except OSError as error:
            raise _error(
                "RUNTIME_NOT_FOUND",
                "reinstall_runtime",
                "Runtime candidate does not exist",
            ) from error
        if not target.is_file():
            raise _error(
                "RUNTIME_NOT_FOUND",
                "reinstall_runtime",
                "Runtime candidate is not a regular file",
            )
        resolved.setdefault(target, installed)
    if len(resolved) != 1:
        raise _error(
            "RUNTIME_AMBIGUOUS",
            "select_runtime",
            "Runtime discovery produced multiple distinct candidates",
        )
    target, installed = next(iter(resolved.items()))
    return installed, target


def _probe(runtime: Path, *, interpreter: str) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [interpreter, os.fspath(runtime), "--json", "--handshake"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise _error(
            "RUNTIME_HANDSHAKE_FAILED",
            "repair_runtime",
            "Runtime handshake could not be executed",
        ) from error
    try:
        envelope = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise _error(
            "RUNTIME_HANDSHAKE_FAILED",
            "repair_runtime",
            "Runtime handshake did not return one JSON document",
        ) from error
    if (
        result.returncode != 0
        or result.stderr
        or not isinstance(envelope, dict)
        or envelope.get("ok") is not True
        or envelope.get("command") != "handshake"
        or not isinstance(envelope.get("data"), dict)
    ):
        raise _error(
            "RUNTIME_HANDSHAKE_FAILED",
            "repair_runtime",
            "Runtime handshake returned a failed or malformed envelope",
        )
    return envelope


def _validate_handshake(
    envelope: dict[str, Any],
    identity: dict[str, Any],
) -> dict[str, Any]:
    data = envelope["data"]
    engine = data.get("engine_version")
    engine_match = _ENGINE.fullmatch(engine) if isinstance(engine, str) else None
    capabilities = data.get("capabilities")
    minimum_schema = data.get("minimum_schema_version")
    maximum_schema = data.get("maximum_schema_version")
    valid = (
        envelope.get("output_version") == identity["cli_output_version"]
        and data.get("handshake_version") == identity["handshake_version"]
        and data.get("distribution_id") == identity["distribution_id"]
        and engine_match is not None
        and data.get("engine_generation")
        == identity["compatible_engine_generation"]
        and type(minimum_schema) is int
        and minimum_schema <= identity["minimum_schema_version"]
        and type(maximum_schema) is int
        and maximum_schema >= identity["maximum_schema_version"]
        and isinstance(capabilities, list)
        and capabilities == sorted(set(capabilities))
        and set(identity["required_capabilities"]).issubset(capabilities)
        and isinstance(data.get("artifact_versions"), dict)
        and _HEX64.fullmatch(str(data.get("runtime_identity_sha256"))) is not None
        and _HEX64.fullmatch(str(data.get("skill_sha256"))) is not None
    )
    if not valid:
        raise _error(
            "RUNTIME_INCOMPATIBLE",
            "install_compatible_runtime",
            "Runtime identity, version axes, or capabilities are incompatible",
        )
    return data


def discover_runtime(
    package_root: Path,
    *,
    explicit_candidates: Sequence[Path] | None = None,
    interpreter: str = sys.executable,
) -> dict[str, Any]:
    identity = load_identity(package_root)
    if explicit_candidates is None:
        candidates = ((package_root / "scripts/sdd.py").absolute(),)
        source = "package-local"
    else:
        candidates = tuple(explicit_candidates)
        source = "explicit"
    installed, resolved = _resolve_candidates(candidates)
    envelope = _probe(resolved, interpreter=interpreter)
    handshake = _validate_handshake(envelope, identity)
    return {
        "discovery_version": DISCOVERY_VERSION,
        "source": source,
        "installed_path": os.fspath(installed),
        "resolved_path": os.fspath(resolved),
        "handshake": handshake,
    }
