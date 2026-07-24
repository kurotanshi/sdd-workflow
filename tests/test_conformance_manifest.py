from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE = ROOT / "conformance"
REGISTRY = CONFORMANCE / "protocol-rules-v1.json"
MANIFEST = CONFORMANCE / "runtime-manifest-v1.json"


class ConformanceManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_rule_registry_is_versioned_unique_and_source_backed(self) -> None:
        self.assertEqual(self.registry["registry_version"], 1)
        self.assertEqual(
            self.registry["protocol_version"],
            "sdd-protocol-1.0",
        )
        rules = self.registry["rules"]
        ids = [rule["id"] for rule in rules]
        self.assertEqual(len(ids), len(set(ids)))
        for rule in rules:
            with self.subTest(rule=rule["id"]):
                self.assertRegex(rule["id"], r"^SDD-[A-Z]+-[0-9]{3}$")
                self.assertTrue(rule["title"])
                self.assertRegex(rule["requirement"], r"\bMUST\b")
                self.assertTrue(rule["sources"])
                for source in rule["sources"]:
                    self.assertTrue((ROOT / source).is_file(), source)

    def test_manifest_references_known_rules_and_existing_commands(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], 1)
        self.assertEqual(
            self.manifest["registry"],
            REGISTRY.relative_to(ROOT).as_posix(),
        )
        self.assertTrue((ROOT / self.manifest["reference_runtime"]).is_file())

        rule_ids = {rule["id"] for rule in self.registry["rules"]}
        covered_rules: set[str] = set()
        case_ids: set[str] = set()
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                self.assertNotIn(case["id"], case_ids)
                case_ids.add(case["id"])
                self.assertRegex(case["id"], r"^[a-z][a-z0-9.-]+$")
                self.assertTrue(case["rules"])
                self.assertLessEqual(set(case["rules"]), rule_ids)
                covered_rules.update(case["rules"])
                if case["kind"] == "unittest":
                    self.assertTrue(case["selectors"])
                    for selector in case["selectors"]:
                        self.assertRegex(selector, r"^tests\.test_[a-z0-9_]+$")
                elif case["kind"] == "command":
                    argv = case["argv"]
                    self.assertGreaterEqual(len(argv), 2)
                    self.assertIn(argv[0], {"{python}", "sh"})
                    self.assertTrue((ROOT / argv[1]).is_file(), argv[1])
                else:
                    self.fail(f"unsupported case kind: {case['kind']}")

        self.assertEqual(covered_rules, rule_ids)

    def test_every_unittest_module_maps_to_a_protocol_rule(self) -> None:
        actual = {
            f"tests.{path.stem}"
            for path in (ROOT / "tests").glob("test_*.py")
        }
        mapped = {
            selector
            for case in self.manifest["cases"]
            if case["kind"] == "unittest"
            for selector in case["selectors"]
        }
        self.assertEqual(mapped, actual)

    def test_required_runtime_categories_have_executable_evidence(self) -> None:
        required_categories = {
            "projection",
            "transition",
            "approval_attestation",
            "transaction_retry",
            "archive_authority",
            "schema_compatibility",
            "cli_contract",
        }
        categories = {
            rule["id"]: rule["category"]
            for rule in self.registry["rules"]
        }
        executable_categories = {
            categories[rule_id]
            for case in self.manifest["cases"]
            for rule_id in case["rules"]
        }
        self.assertLessEqual(required_categories, executable_categories)


if __name__ == "__main__":
    unittest.main()
