from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "facebook_monetization_os.py"
SPEC = importlib.util.spec_from_file_location("facebook_monetization_os", MODULE_PATH)
assert SPEC and SPEC.loader
OPS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OPS)


class FacebookMonetizationOSTest(unittest.TestCase):
    def setUp(self) -> None:
        self.state, self.backlog, self.errors = OPS.validate(ROOT)

    def test_repository_schema_is_valid(self) -> None:
        self.assertEqual(self.errors, [])

    def test_default_mode_blocks_publication(self) -> None:
        plan = OPS.build_daily_plan(self.state, self.backlog, date(2026, 7, 26))
        self.assertFalse(plan["publish_allowed"])
        self.assertIn("Chưa có kết nối", plan["publish_block_reason"])
        self.assertEqual(len(plan["items"]), 1)

    def test_personal_facebook_is_not_an_automation_target(self) -> None:
        constraints = self.state["channel_constraints"]
        self.assertEqual(constraints["facebook_personal_profile"], "MANUAL_ONLY_IN_NATIVE_APP")
        self.assertEqual(
            constraints["instagram_to_facebook_personal_crosspost"],
            "UNSUPPORTED_BY_AUTOMATION",
        )

    def test_daily_brief_explains_draft_only_boundary(self) -> None:
        plan = OPS.build_daily_plan(self.state, self.backlog, date(2026, 7, 26))
        brief = OPS.render_markdown(plan)
        self.assertIn("Khóa xuất bản", brief)
        self.assertIn("KPI chính", brief)
        self.assertIn(plan["items"][0]["id"], brief)

    def test_incomplete_content_is_reported_without_crashing(self) -> None:
        errors = OPS.validate_backlog([{"id": "INCOMPLETE"}])
        self.assertTrue(any("script_outline" in error for error in errors))

    def test_cli_can_write_a_local_brief(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "brief.md"
            return_code = OPS.main(
                ["--root", str(ROOT), "daily-brief", "--date", "2026-07-26", "--output", str(output)]
            )
            self.assertEqual(return_code, 0)
            self.assertTrue(output.exists())
            self.assertIn("Daily brief", output.read_text(encoding="utf-8"))

    def test_current_state_has_no_secrets(self) -> None:
        payload = json.loads((ROOT / "ops" / "facebook-monetization" / "state.json").read_text(encoding="utf-8"))
        serialized = json.dumps(payload).lower()
        for forbidden in ("sk-", "ghp_", "eaag", "xoxb-"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
