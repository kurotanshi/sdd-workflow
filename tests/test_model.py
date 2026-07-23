from __future__ import annotations

import sys
import unittest
from dataclasses import fields
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/sdd-workflow/scripts"))

from sdd_core import (  # noqa: E402
    ApprovalRelevance,
    CANONICAL_EXTENSION_APPROVAL_POLICY,
    CANONICAL_FIELD_APPROVAL_POLICY,
    CanonicalExtension,
    CanonicalProposal,
    CanonicalSection,
    CanonicalTask,
)


class CanonicalModelTests(unittest.TestCase):
    def test_every_top_level_field_declares_approval_relevance(self) -> None:
        self.assertEqual(
            {item.name for item in fields(CanonicalProposal)},
            set(CANONICAL_FIELD_APPROVAL_POLICY),
        )

    def test_approval_projection_excludes_completion_and_excluded_extension(self) -> None:
        model = CanonicalProposal(
            schema_version=1,
            schema_version_declared=False,
            short_name="add-example",
            status="approved",
            change_type="新功能",
            sections=(
                CanonicalSection(
                    "why",
                    "為什麼做",
                    ("reason",),
                    ApprovalRelevance.RELEVANT,
                ),
            ),
            tasks=(CanonicalTask(1, "Do the approved work", True, 3),),
            acceptance_conditions=("observable result",),
            extensions=(
                CanonicalExtension(
                    "sdd.schema",
                    {"schema_version": 2},
                    ApprovalRelevance.RELEVANT,
                ),
                CanonicalExtension(
                    "sdd.research.conclusion",
                    {"items": ["observed result"]},
                    ApprovalRelevance.EXCLUDED,
                ),
            ),
        )

        projection = dict(model.approval_relevant_values())

        self.assertNotIn("status", projection)
        self.assertEqual(projection["tasks"], ("Do the approved work",))
        self.assertEqual(
            tuple((item.namespace, item.value) for item in projection["extensions"]),
            (("sdd.schema", {"schema_version": 2}),),
        )
        self.assertTrue(model.to_dict()["tasks"][0]["completed"])

    def test_every_v2_extension_declares_approval_relevance(self) -> None:
        self.assertEqual(
            CANONICAL_EXTENSION_APPROVAL_POLICY,
            {
                "sdd.schema": ApprovalRelevance.RELEVANT,
                "sdd.research.conclusion": ApprovalRelevance.EXCLUDED,
            },
        )

    def test_duplicate_extension_namespaces_fail(self) -> None:
        extension = CanonicalExtension(
            "duplicate",
            None,
            ApprovalRelevance.EXCLUDED,
        )
        with self.assertRaises(ValueError):
            CanonicalProposal(
                schema_version=1,
                schema_version_declared=False,
                short_name="duplicate-extension",
                status="draft",
                change_type="重構",
                sections=(),
                tasks=(),
                acceptance_conditions=(),
                extensions=(extension, extension),
            )


if __name__ == "__main__":
    unittest.main()
