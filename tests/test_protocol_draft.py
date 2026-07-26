from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/protocol/core-v1.md"
REGISTRY = ROOT / "conformance/protocol-rules-v1.json"


class CoreProtocolV1HistoricalEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = PROTOCOL.read_text(encoding="utf-8")
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_frozen_protocol_evidence_is_self_identifying(self) -> None:
        self.assertIn(
            f"Protocol identifier: `{self.registry['protocol_version']}`",
            self.text,
        )
        self.assertIn("RFC 2119 / RFC 8174", self.text)
        self.assertIn(
            "The reference runtime is one conforming implementation. "
            "Its source code is not\npart of this protocol.",
            self.text,
        )

    def test_required_normative_sections_are_present(self) -> None:
        headings = {
            match.group(1)
            for match in re.finditer(r"^## \d+\. (.+)$", self.text, re.MULTILINE)
        }
        required = {
            "Purpose and conformance",
            "Roles and trust boundaries",
            "Artifact model",
            "Authority",
            "Approval and attestation",
            "Lifecycle and managed transitions",
            "Transaction and recovery protocol",
            "Compatibility and version negotiation",
            "Agent adapter contract",
            "Conformance kit",
            "Security and threat model",
            "Evolution",
        }
        self.assertLessEqual(required, headings)

    def test_v1_freeze_names_scope_and_non_goals(self) -> None:
        self.assertIn("Status: frozen v1.0 historical evidence", self.text)
        self.assertIn("not a current public contract", self.text)
        for term in (
            "authority",
            "lifecycle",
            "approval",
            "attestation",
            "transaction",
            "recovery",
            "compatibility",
            "trust",
            "Schema v3",
            "locking",
            "Web UI",
            "external-platform",
            "multi-Agent orchestration",
        ):
            with self.subTest(term=term):
                self.assertIn(term, self.text)

    def test_every_registered_rule_has_one_normative_protocol_clause(self) -> None:
        registered = {rule["id"] for rule in self.registry["rules"]}
        clauses = re.findall(
            r"^### (SDD-[A-Z]+-[0-9]{3}) — .+$",
            self.text,
            re.MULTILINE,
        )
        self.assertEqual(set(clauses), registered)
        self.assertEqual(len(clauses), len(registered))

        for rule_id in registered:
            clause = re.search(
                rf"^### {re.escape(rule_id)} — .+?\n\n(.+?)(?=\n\n### |\n\n## )",
                self.text,
                re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(clause, rule_id)
            self.assertRegex(clause.group(1), r"\bMUST\b")

    def test_protocol_does_not_make_unsupported_trust_claims(self) -> None:
        self.assertIn(
            "Hashes, metadata, timestamps, and writer identifiers are evidence, "
            "not identity",
            self.text,
        )
        self.assertIn("does not provide process isolation", self.text)
        self.assertIn("Ambiguity always selects", self.text)


if __name__ == "__main__":
    unittest.main()
