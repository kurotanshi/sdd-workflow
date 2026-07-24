from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run-conformance-kit"
MANIFEST = ROOT / "conformance/kit-manifest-v1.json"


class PublicConformanceKitTests(unittest.TestCase):
    def run_kit(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RUNNER), *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_manifest_packages_public_components(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["kit_version"], 1)
        registry = json.loads((ROOT / manifest["registry"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["protocol_version"], registry["protocol_version"])
        for key in (
            "registry",
            "reference_runtime_manifest",
            "reference_runtime",
            "expected_envelopes",
            "adapter_scenarios",
            "hermetic_adapter",
            "adapter_runner",
            "runner",
        ):
            self.assertTrue((ROOT / manifest[key]).is_file(), key)
        for fixture_manifest in manifest["fixture_manifests"]:
            self.assertTrue((ROOT / fixture_manifest).is_file(), fixture_manifest)

    def test_list_exposes_versioned_inventory(self) -> None:
        result = self.run_kit("--list", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        document = json.loads(result.stdout)
        self.assertTrue(document["ok"])
        self.assertEqual(document["kit_version"], 1)
        self.assertEqual(document["expectation_version"], 1)
        self.assertEqual(document["protocol_version"], "sdd-protocol-1.0")
        self.assertEqual(
            document["cases"],
            [
                "version-success",
                "status-success",
                "invalid-short-name",
                "future-schema-fails-closed",
                "usage-error",
            ],
        )

    def test_reference_runtime_passes_public_envelope_cases(self) -> None:
        result = self.run_kit("--json")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stderr, "")
        document = json.loads(result.stdout)
        self.assertTrue(document["ok"])
        self.assertEqual(len(document["results"]), 5)
        self.assertTrue(all(case["passed"] for case in document["results"]))

    def test_candidate_mismatch_is_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / "fake-runtime.py"
            fake.write_text(
                "import json\n"
                "print(json.dumps({'output_version': 1, 'ok': True}))\n",
                encoding="utf-8",
            )
            result = self.run_kit(
                "--runtime",
                str(fake),
                "--case",
                "version-success",
                "--json",
            )
        self.assertEqual(result.returncode, 1, result.stdout)
        document = json.loads(result.stdout)
        self.assertFalse(document["ok"])
        self.assertFalse(document["results"][0]["passed"])
        paths = {
            difference["path"]
            for difference in document["results"][0]["differences"]
        }
        self.assertIn("/command", paths)


if __name__ == "__main__":
    unittest.main()
