#!/usr/bin/env python3
"""Chống hồi quy chính sách: Hermes là kênh TÙY CHỌN, không chặn phiên chat.

    python3 -m unittest discover -s scripts/tests -p 'test_hermes_optional_rules.py' -v

Sự cố 23–27/10/2026: luật cũ ("Hermes là chủ", "PHẢI boot", "DỪNG phiên") bị nhân bản
ra nhiều file. Sửa một vài file không đủ — AI vẫn đọc luật cũ ở file khác và dừng việc.
Test này khóa tất cả file luật lại, đồng thời kiểm chứng hành vi thật của wrapper boot.
Xem docs/HERMES_SESSION_ERROR_RCA.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_DIR / "scripts"))

import hermes_owner as hop  # noqa: E402

# Các file mà AI/Hermes đọc làm "luật". RCA excluded: đó là tài liệu lịch sử,
# cần trích dẫn nguyên văn luật cũ để phân tích.
RULE_FILES = (
    "AGENTS.md",
    "README.md",
    ".ai/CONSTITUTION.md",
    ".ai/handoff/INBOX.md",
    ".ai/handoff/README.md",
    "Status.md",
    "memory/MEMORY.md",
    "docs/HERMES_OWNER_PROTOCOL.md",
    "docs/ARENA_VS_HERMES.md",
    "skills/hermes-owner/SKILL.md",
    "skills/README.md",
)

# Cụm từ cũ KHÔNG được phép xuất hiện lại trong file luật.
FORBIDDEN = (
    r"Hermes\s+là\s+chủ",
    r"chủ\s+của\s+repo",
    r"BƯỚC\s+0\s+bắt\s+buộc",
    r"LUẬT\s+BẮT\s+BUỘC\s+MỌI\s+PHIÊN",
    r"mọi\s+phiên\s+agent[^\n]{0,80}(PHẢI|phải)\s+chạy",
    r"không\s+có\s+mệnh\s+lệnh\s+hợp\s+lệ\s+thì\s+phiên\s+(phải\s+)?dừng",
    r"phiên\s+phải\s+DỪNG",
    r"mọi\s+phiên\s+dừng",
    r"không\s+có\s+lệnh\s+hợp\s+lệ\s+thì\s+phiên\s+dừng",
)

OPTIONAL_RE = re.compile(r"(không\s+bắt\s+buộc|TÙY\s+CHỌN|t[ùu]y\s+chọn|tuỳ\s+chọn)", re.IGNORECASE)


class OptionalPolicyTest(unittest.TestCase):
    def test_engine_policy_is_optional(self) -> None:
        self.assertEqual(hop.POLICY, "optional")
        self.assertEqual(hop.empty_state().get("policy"), "optional")

    def test_state_json_declares_optional_policy(self) -> None:
        state = json.loads((REPO_DIR / ".ai/handoff/STATE.json").read_text(encoding="utf-8"))
        self.assertEqual(state.get("policy"), "optional")

    def test_all_rule_files_declare_optional_policy(self) -> None:
        for rel in RULE_FILES:
            with self.subTest(file=rel):
                path = REPO_DIR / rel
                self.assertTrue(path.is_file(), f"thiếu file luật {rel}")
                text = path.read_text(encoding="utf-8")
                self.assertRegex(text, OPTIONAL_RE, f"{rel} không nói rõ Hermes là tùy chọn")

    def test_no_forced_hermes_language_in_rule_files(self) -> None:
        for rel in RULE_FILES:
            text = (REPO_DIR / rel).read_text(encoding="utf-8")
            for pattern in FORBIDDEN:
                with self.subTest(file=rel, pattern=pattern):
                    self.assertIsNone(
                        re.search(pattern, text, re.IGNORECASE),
                        f"{rel} vẫn chứa luật bắt buộc/dừng phiên: /{pattern}/",
                    )

    def test_prompts_and_wrappers_do_not_command_a_stop(self) -> None:
        """Prompt gửi Hermes + wrapper chỉ được nhắc strict như một tùy chọn của Operator."""
        brief = (REPO_DIR / "scripts/hermes_owner_brief.py").read_text(encoding="utf-8")
        self.assertIn("CỐ VẤN TÙY CHỌN", brief)
        self.assertIn("Không được yêu cầu agent dừng phiên", brief)

        boot_sh = (REPO_DIR / "scripts/hermes-session-boot.sh").read_text(encoding="utf-8")
        self.assertIn("KHÔNG BAO GIỜ CHẶN PHIÊN", boot_sh)
        closeout_sh = (REPO_DIR / "scripts/hermes-session-closeout.sh").read_text(encoding="utf-8")
        self.assertIn("TÙY CHỌN", closeout_sh)

        generated = (REPO_DIR / "scripts/gen-zeus-context.py").read_text(encoding="utf-8")
        self.assertIn("Hermes là kênh TÙY CHỌN", generated)


class WrapperBehaviourTest(unittest.TestCase):
    """Chạy wrapper thật trong repo tạm: thiếu gợi ý vẫn thoát 0."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / "scripts").mkdir()
        (self.repo / ".ai" / "handoff").mkdir(parents=True)
        for name in ("hermes_owner.py", "hermes-session-boot.sh"):
            shutil.copy2(REPO_DIR / "scripts" / name, self.repo / "scripts" / name)
        (self.repo / ".ai/handoff/STATE.json").write_text(
            json.dumps(hop.empty_state()), encoding="utf-8"
        )
        (self.repo / ".ai/handoff/INBOX.md").write_text("# chưa có\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _boot(self, *extra: str, env_extra: dict[str, str] | None = None):
        env = os.environ.copy()
        env.pop("HERMES_OWNER_STRICT", None)
        env.update(env_extra or {})
        return subprocess.run(
            ["bash", "scripts/hermes-session-boot.sh", "--offline", *extra],
            cwd=str(self.repo), capture_output=True, text=True, env=env, timeout=60,
        )

    def test_boot_without_directive_never_blocks(self) -> None:
        result = self._boot()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("KHÔNG BẮT BUỘC", result.stdout)
        self.assertNotIn("DỪNG PHIÊN", result.stdout)

    def test_boot_json_reports_non_blocking(self) -> None:
        result = self._boot("--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout[result.stdout.index("{"):])
        self.assertFalse(payload["blocking"])
        self.assertEqual(payload["policy"], "optional")

    def test_strict_is_opt_in_by_flag(self) -> None:
        result = self._boot("--strict")
        self.assertEqual(result.returncode, hop.EXIT_MISSING, result.stdout + result.stderr)
        self.assertIn("DỪNG PHIÊN", result.stdout)

    def test_strict_is_opt_in_by_env(self) -> None:
        result = self._boot(env_extra={"HERMES_OWNER_STRICT": "1"})
        self.assertEqual(result.returncode, hop.EXIT_MISSING, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
