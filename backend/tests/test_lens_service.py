"""Tests for A3 Lens editor: validation, templates, DB resolve, riskRules preserve."""

from __future__ import annotations

import copy
import json
import unittest

from tests.helpers import close_session, make_session, make_user
from services.lens_service import (
    make_question_template,
    preserve_existing_risk_rules,
    resolve_active_lens,
    save_active_lens,
    suggest_improvement_plan,
    validate_lens,
)
from services.wa_lens_engine import load_lens, list_questions


class LensServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = make_session()
        self.fiona = make_user(
            self.db, username="fiona_lens", role="Security_Reviewer"
        )

    def tearDown(self) -> None:
        close_session(self.db)

    def test_fallback_to_file_when_empty_db(self) -> None:
        lens = resolve_active_lens(self.db)
        self.assertEqual(lens.get("schemaVersion"), "2021-11-01")
        self.assertGreaterEqual(len(list_questions(lens)), 5)

    def test_save_and_resolve_from_db(self) -> None:
        lens = copy.deepcopy(load_lens())
        # tweak a title
        lens["pillars"][0]["questions"][0]["title"] = "Edited security title"
        saved = save_active_lens(self.db, lens, self.fiona)
        self.assertEqual(
            saved["pillars"][0]["questions"][0]["title"], "Edited security title"
        )
        again = resolve_active_lens(self.db)
        self.assertEqual(
            again["pillars"][0]["questions"][0]["title"], "Edited security title"
        )

    def test_preserve_risk_rules_on_existing_questions(self) -> None:
        previous = load_lens()
        incoming = copy.deepcopy(previous)
        q0 = incoming["pillars"][0]["questions"][0]
        original_rules = copy.deepcopy(q0["riskRules"])
        q0["title"] = "New title only"
        q0["riskRules"] = [{"condition": "default", "risk": "HIGH_RISK"}]
        merged = preserve_existing_risk_rules(incoming, previous)
        self.assertEqual(
            merged["pillars"][0]["questions"][0]["riskRules"], original_rules
        )
        self.assertEqual(merged["pillars"][0]["questions"][0]["title"], "New title only")

    def test_validate_rejects_empty_pillar(self) -> None:
        lens = copy.deepcopy(load_lens())
        lens["pillars"][0]["questions"] = []
        with self.assertRaises(ValueError):
            validate_lens(lens)

    def test_new_question_template_and_suggest(self) -> None:
        q = make_question_template("security", "Edge protection")
        self.assertTrue(q["id"].startswith("sec_"))
        self.assertTrue(q["riskRules"])
        text = suggest_improvement_plan("Edge protection")
        self.assertIn("Edge protection", text)

    def test_add_question_then_save(self) -> None:
        lens = copy.deepcopy(load_lens())
        lens["pillars"][0]["questions"].append(
            make_question_template("security", "Extra check")
        )
        saved = save_active_lens(self.db, lens, self.fiona)
        sec = next(p for p in saved["pillars"] if p["id"] == "security")
        self.assertGreaterEqual(len(sec["questions"]), 3)


if __name__ == "__main__":
    unittest.main()
