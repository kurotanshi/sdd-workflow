from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "skills/sdd-workflow"
SCRIPTS = PACKAGE / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sdd_core.cli import main  # noqa: E402
from sdd_core.runtime_discovery import (  # noqa: E402
    RuntimeDiscoveryError,
    discover_runtime,
)


def handshake_envelope(**overrides: object) -> dict[str, object]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    code = main(
        ["--json", "--handshake"],
        stdout=stdout,
        stderr=stderr,
        cwd=ROOT,
    )
    if code != 0 or stderr.getvalue():
        raise AssertionError("repository handshake failed")
    envelope = json.loads(stdout.getvalue())
    envelope["data"].update(overrides)
    return envelope


def fake_runtime(path: Path, envelope: object) -> Path:
    payload = json.dumps(envelope, sort_keys=True)
    path.write_text(f"print({payload!r})\n", encoding="utf-8")
    return path


class RuntimeDiscoveryTests(unittest.TestCase):
    def test_handshake_is_readonly_and_versioned(self) -> None:
        envelope = handshake_envelope()
        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["command"], "handshake")
        data = envelope["data"]
        self.assertEqual(data["distribution_id"], "sdd-workflow")
        self.assertEqual(data["handshake_version"], 1)
        self.assertEqual(data["engine_generation"], "1.4")
        self.assertEqual(data["capabilities"], sorted(data["capabilities"]))
        self.assertRegex(data["runtime_identity_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(data["skill_sha256"], r"^[0-9a-f]{64}$")

    def test_package_local_runtime_is_the_only_default(self) -> None:
        previous_path = os.environ.get("PATH")
        os.environ["PATH"] = "/path/that/must/not/be/searched"
        try:
            result = discover_runtime(PACKAGE)
        finally:
            if previous_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = previous_path
        self.assertEqual(result["source"], "package-local")
        self.assertEqual(
            Path(result["resolved_path"]),
            (SCRIPTS / "sdd.py").resolve(),
        )
        self.assertEqual(
            result["handshake"]["capabilities"],
            sorted(result["handshake"]["capabilities"]),
        )

    def test_zero_and_multiple_distinct_candidates_fail_closed(self) -> None:
        with self.assertRaises(RuntimeDiscoveryError) as missing:
            discover_runtime(PACKAGE, explicit_candidates=[])
        self.assertEqual(missing.exception.code, "RUNTIME_NOT_FOUND")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = fake_runtime(root / "first.py", handshake_envelope())
            second = fake_runtime(root / "second.py", handshake_envelope())
            with self.assertRaises(RuntimeDiscoveryError) as ambiguous:
                discover_runtime(
                    PACKAGE,
                    explicit_candidates=[first, second],
                )
        self.assertEqual(ambiguous.exception.code, "RUNTIME_AMBIGUOUS")

    def test_duplicate_aliases_resolve_to_one_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = fake_runtime(root / "runtime.py", handshake_envelope())
            alias = root / "alias.py"
            alias.symlink_to(runtime)
            result = discover_runtime(
                PACKAGE,
                explicit_candidates=[runtime, alias],
            )
        self.assertEqual(result["source"], "explicit")
        self.assertEqual(Path(result["resolved_path"]), runtime.resolve())

    def test_malformed_and_incompatible_handshakes_fail_closed(self) -> None:
        cases = {
            "malformed": ("not-json", "RUNTIME_HANDSHAKE_FAILED"),
            "distribution": (
                handshake_envelope(distribution_id="another-runtime"),
                "RUNTIME_INCOMPATIBLE",
            ),
            "capability": (
                handshake_envelope(capabilities=["schema-v1"]),
                "RUNTIME_INCOMPATIBLE",
            ),
            "generation": (
                handshake_envelope(
                    engine_version="1.5.0",
                    engine_generation="1.5",
                ),
                "RUNTIME_INCOMPATIBLE",
            ),
            "missing-version": (
                handshake_envelope(minimum_schema_version=None),
                "RUNTIME_INCOMPATIBLE",
            ),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, (envelope, expected) in cases.items():
                with self.subTest(name=name):
                    runtime = root / f"{name}.py"
                    if envelope == "not-json":
                        runtime.write_text("print('not-json')\n", encoding="utf-8")
                    else:
                        fake_runtime(runtime, envelope)
                    with self.assertRaises(RuntimeDiscoveryError) as failure:
                        discover_runtime(
                            PACKAGE,
                            explicit_candidates=[runtime],
                        )
                    self.assertEqual(failure.exception.code, expected)

    def test_relative_explicit_runtime_is_never_resolved_from_cwd(self) -> None:
        with self.assertRaises(RuntimeDiscoveryError) as failure:
            discover_runtime(
                PACKAGE,
                explicit_candidates=[Path("scripts/sdd.py")],
            )
        self.assertEqual(failure.exception.code, "RUNTIME_INCOMPATIBLE")


if __name__ == "__main__":
    unittest.main()
