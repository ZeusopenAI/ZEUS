#!/usr/bin/env python3
"""Test cho Hermes Owner Protocol (stdlib unittest, không cần pytest).

    python3 -m unittest discover -s scripts/tests -p 'test_hermes_owner.py' -v
    python3 scripts/tests/test_hermes_owner.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
ENGINE = REPO_DIR / "scripts" / "hermes_owner.py"
sys.path.insert(0, str(REPO_DIR / "scripts"))

import hermes_owner as hop  # noqa: E402


def run_engine(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ENGINE), *args],
        capture_output=True, text=True, cwd=str(cwd) if cwd else None, timeout=60,
    )


class ProtocolTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / ".ai" / "handoff").mkdir(parents=True)
        (self.repo / ".ai" / "handoff" / "STATE.json").write_text(
            json.dumps(hop.empty_state()), encoding="utf-8"
        )
        (self.repo / ".ai" / "handoff" / "INBOX.md").write_text(
            "# chưa có\n", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    def issue(self, body: str = "# MỆNH LỆNH — thử\n\n## Mục tiêu\nLàm việc.\n",
              ttl: int = 24, issuer: str = "hermes", title: str = "Thử") -> dict:
        return hop.issue_directive(
            repo=self.repo, body=body, title=title, ttl_hours=ttl,
            source_run="test", model="test-model", issuer=issuer,
        )

    def boot(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return run_engine("boot", "--repo", str(self.repo), "--offline", *extra)

    # -- tests -----------------------------------------------------------
    def test_missing_directive_exits_3(self) -> None:
        result = self.boot()
        self.assertEqual(result.returncode, hop.EXIT_MISSING, result.stdout + result.stderr)
        self.assertIn("DỪNG PHIÊN", result.stdout)

    def test_valid_directive_exits_0_and_prints_body(self) -> None:
        self.issue()
        result = self.boot()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("MỆNH LỆNH TỪ HERMES", result.stdout)
        self.assertIn("Làm việc.", result.stdout)

    def test_boot_json_payload(self) -> None:
        issued = self.issue()
        result = self.boot("--json")
        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout[result.stdout.index("{"):])
        self.assertEqual(payload["id"], issued["meta"]["id"])
        self.assertEqual(payload["source"], "local")
        self.assertIn("Làm việc.", payload["body"])

    def test_tampering_breaks_seal(self) -> None:
        self.issue()
        inbox = self.repo / ".ai" / "handoff" / "INBOX.md"
        inbox.write_text(inbox.read_text(encoding="utf-8") + "\nThêm dòng lạ.\n", encoding="utf-8")
        result = self.boot()
        self.assertEqual(result.returncode, hop.EXIT_TAMPERED, result.stdout + result.stderr)
        self.assertIn("seal", result.stdout.lower())

    def test_expired_directive(self) -> None:
        self.issue(ttl=-2)
        result = self.boot()
        self.assertEqual(result.returncode, hop.EXIT_STALE, result.stdout + result.stderr)

    def test_wrong_issuer(self) -> None:
        self.issue(issuer="arena")
        result = self.boot()
        self.assertEqual(result.returncode, hop.EXIT_WRONG_ISSUER, result.stdout + result.stderr)

    def test_number_increments_and_history_kept(self) -> None:
        first = self.issue(title="Một")
        second = self.issue(title="Hai")
        self.assertEqual(first["meta"]["number"], 1)
        self.assertEqual(second["meta"]["number"], 2)
        state = json.loads((self.repo / ".ai" / "handoff" / "STATE.json").read_text(encoding="utf-8"))
        self.assertEqual(state["active_directive"]["id"], second["meta"]["id"])
        self.assertEqual(state["history"][0]["id"], first["meta"]["id"])

    def test_archive_written(self) -> None:
        issued = self.issue()
        archive = self.repo / ".ai" / "handoff" / "archive" / f"INBOX-{issued['meta']['id']}.md"
        self.assertTrue(archive.exists())
        self.assertIn("MỆNH LỆNH", archive.read_text(encoding="utf-8"))

    def test_closeout_appends_report_and_updates_state(self) -> None:
        issued = self.issue()
        result = run_engine(
            "closeout", "--repo", str(self.repo), "--status", "DONE",
            "--summary", "Đã làm xong việc", "--tests", "unittest: 9 passed",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        outbox = (self.repo / ".ai" / "handoff" / "OUTBOX.md").read_text(encoding="utf-8")
        self.assertIn(hop.REPORT_START, outbox)
        self.assertIn("Đã làm xong việc", outbox)
        state = json.loads((self.repo / ".ai" / "handoff" / "STATE.json").read_text(encoding="utf-8"))
        self.assertEqual(state["last_report"]["status"], "DONE")
        self.assertEqual(state["last_report"]["directive_id"], issued["meta"]["id"])

    def test_closeout_requires_summary(self) -> None:
        result = run_engine("closeout", "--repo", str(self.repo), "--status", "DONE")
        self.assertEqual(result.returncode, hop.EXIT_USAGE)

    def test_closeout_rejects_bad_status(self) -> None:
        result = run_engine(
            "closeout", "--repo", str(self.repo), "--status", "MAYBE", "--summary", "x",
        )
        self.assertEqual(result.returncode, hop.EXIT_USAGE)

    def test_extract_markers(self) -> None:
        raw = (
            "lời dẫn\n<<<ZEUS_DIRECTIVE>>>\n# MỆNH LỆNH #2 — abc\n\n## Mục tiêu\nX\n"
            "<<<END_ZEUS_DIRECTIVE>>>\nphía sau\n"
        )
        result = run_engine("extract", "--input", "-")
        # stdin rỗng trong subprocess -> phải lỗi; test hàm trực tiếp thay thế
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(hop._extract_directive(raw).strip().splitlines()[0], "# MỆNH LỆNH #2 — abc")

    def test_selftest_command_passes(self) -> None:
        result = run_engine("selftest")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class RemoteFallbackTest(unittest.TestCase):
    """Mệnh lệnh chỉ có trên nhánh hermes-owner/state (chưa merge vào main)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.origin = root / "origin.git"
        self.work = root / "work"
        subprocess.run(["git", "init", "--bare", "-q", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", str(self.work)], check=True)
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test")
        self._git("remote", "add", "origin", str(self.origin))

        (self.work / ".ai" / "handoff").mkdir(parents=True)
        (self.work / ".ai" / "handoff" / "STATE.json").write_text(
            json.dumps(hop.empty_state()), encoding="utf-8"
        )
        (self.work / ".ai" / "handoff" / "INBOX.md").write_text("# trống\n", encoding="utf-8")
        (self.work / ".gitignore").write_text(".ai/handoff/.cache/\n", encoding="utf-8")
        self._git("add", "-A")
        self._git("commit", "-qm", "init")
        self._git("push", "-q", "-u", "origin", "HEAD:main")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.work), *args], capture_output=True, text=True, check=True,
        )

    def test_boot_reads_state_branch(self) -> None:
        # Ban hành mệnh lệnh trên nhánh trạng thái, KHÔNG merge vào main
        self._git("checkout", "-q", "-b", "hermes-owner/state")
        hop.issue_directive(
            repo=self.work,
            body="# MỆNH LỆNH — từ nhánh trạng thái\n\n## Mục tiêu\nChỉ có trên nhánh.\n",
            title="Từ nhánh", ttl_hours=24,
        )
        self._git("add", "-A", "-f", ".ai")
        self._git("commit", "-qm", "directive")
        self._git("push", "-q", "origin", "hermes-owner/state:hermes-owner/state")

        # Về lại main, xoá cache nhiễm
        self._git("checkout", "-q", "main")
        cache = self.work / ".ai" / "handoff" / ".cache"
        if cache.exists():
            subprocess.run(["rm", "-rf", str(cache)], check=False)

        result = run_engine("boot", "--repo", str(self.work), "--json")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Chỉ có trên nhánh.", result.stdout)
        payload = json.loads(result.stdout[result.stdout.index("{"):])
        self.assertEqual(payload["source"], "remote")


if __name__ == "__main__":
    unittest.main(verbosity=2)
