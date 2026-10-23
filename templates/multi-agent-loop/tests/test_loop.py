#!/usr/bin/env python3
"""Test cho template Multi-Agent Loop (stdlib unittest).

    python3 -m unittest discover -s templates/multi-agent-loop/tests -v
    python3 templates/multi-agent-loop/tests/test_loop.py

Mỗi test ứng với một nguyên tắc bất biến, không phải test cho vui:
  - executor không tự chấm
  - verifier chạy lại từ đầu (không dùng evidence cũ)
  - null phải kèm reason
  - không ghi 0 giả
  - state trên file + journal append-only
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[1]
LOOP = TEMPLATE / "scripts" / "loop_state.py"
GATE = TEMPLATE / "scripts" / "verify_gate.py"

PLANNER, EXECUTOR, VERIFIER, HUMAN = "hermes", "arena", "ci", "operator"


def run(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, cwd=str(cwd) if cwd else None, timeout=120,
    )


class LoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.dir = self.root / "loop"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    def init(self, executor: str = EXECUTOR, verifier: str = VERIFIER) -> subprocess.CompletedProcess[str]:
        return run(
            LOOP, "init", "--dir", str(self.dir), "--slug", "demo", "--goal", "kiểm thử",
            "--planner", PLANNER, "--executor", executor, "--verifier", verifier,
            "--human", HUMAN,
        )

    def plan(self, steps: str = "1. tạo file A → test -f A\n2. chạy unit test → true\n") -> subprocess.CompletedProcess[str]:
        plan_file = self.root / "plan.md"
        plan_file.write_text(steps, encoding="utf-8")
        return run(LOOP, "plan", "--dir", str(self.dir), "--by", PLANNER, "--file", str(plan_file))

    def submit(self, *extra: str, by: str = EXECUTOR) -> subprocess.CompletedProcess[str]:
        return run(
            LOOP, "submit", "--dir", str(self.dir), "--by", by,
            "--summary", "đã làm xong", *extra,
        )

    def gate(self, label: str, cmd: list[str]) -> tuple[subprocess.CompletedProcess[str], Path]:
        result = run(GATE, "run", "--dir", str(self.dir), "--label", label,
                     "--print-id", "--", *cmd)
        evidence_id = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        return result, self.dir / "evidence" / f"{evidence_id}.json"

    def verify(self, *evidence: Path, by: str = VERIFIER) -> subprocess.CompletedProcess[str]:
        args = ["verify", "--dir", str(self.dir), "--by", by]
        for path in evidence:
            args += ["--evidence", str(path)]
        return run(LOOP, *args)

    def state(self) -> dict:
        return json.loads((self.dir / "STATE.json").read_text(encoding="utf-8"))

    # -- 1. Khởi tạo ------------------------------------------------------
    def test_init_rejects_executor_equal_verifier(self) -> None:
        result = self.init(executor="arena", verifier="arena")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("executor", result.stderr.lower())

    def test_init_allows_planner_equal_human(self) -> None:
        result = run(
            LOOP, "init", "--dir", str(self.dir), "--slug", "x",
            "--planner", "boss", "--executor", EXECUTOR,
            "--verifier", VERIFIER, "--human", "boss",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.state()["phase"], "planned")

    def test_init_twice_needs_force(self) -> None:
        self.assertEqual(self.init().returncode, 0)
        self.assertEqual(self.init().returncode, 2)

    # -- 2. Thứ tự pha ----------------------------------------------------
    def test_submit_before_plan_is_blocked(self) -> None:
        self.init()
        result = self.submit()
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("plan", result.stderr.lower())

    def test_plan_requires_check_command(self) -> None:
        self.init()
        result = self.plan("1. việc không có kiểm chứng\n")
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

    def test_plan_only_by_planner(self) -> None:
        self.init()
        plan_file = self.root / "plan.md"
        plan_file.write_text("1. a → true\n", encoding="utf-8")
        result = run(LOOP, "plan", "--dir", str(self.dir), "--by", EXECUTOR, "--file", str(plan_file))
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

    def test_verify_before_submit_is_blocked(self) -> None:
        self.init()
        self.plan()
        _, ev = self.gate("noop", ["true"])
        result = self.verify(ev)
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)

    # -- 3. Executor không tự chấm ---------------------------------------
    def test_executor_cannot_verify_own_work(self) -> None:
        self.init()
        self.plan()
        _, ev = self.gate("noop", ["true"])
        result = self.submit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        bad = self.verify(ev, by=EXECUTOR)
        self.assertEqual(bad.returncode, 4, bad.stdout + bad.stderr)
        self.assertIn("verifier", bad.stderr.lower())

    def test_verify_requires_evidence(self) -> None:
        self.init()
        self.plan()
        self.submit()
        result = self.verify()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    # -- 4. Verifier chạy lại từ đầu --------------------------------------
    def test_stale_evidence_is_rejected(self) -> None:
        self.init()
        self.plan()
        _, old = self.gate("cu", ["true"])          # chạy TRƯỚC khi submit
        time.sleep(1.2)
        self.submit()
        result = self.verify(old)
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("TRƯỚC", result.stderr.upper())

    def test_fresh_evidence_passes(self) -> None:
        self.init()
        self.plan()
        self.submit()
        _, fresh = self.gate("moi", ["true"])
        result = self.verify(fresh)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        state = self.state()
        self.assertEqual(state["phase"], "verified_pass")
        verification = state["attempts"][-1]["verification"]
        self.assertEqual(verification["result"], "pass")
        self.assertEqual(verification["fresh_evidence"], 1)

    def test_failed_command_means_fail_even_if_claimed_pass(self) -> None:
        self.init()
        self.plan()
        self.submit()
        gate, ev = self.gate("hong", ["false"])
        self.assertNotEqual(gate.returncode, 0)
        claimed = run(
            LOOP, "verify", "--dir", str(self.dir), "--by", VERIFIER,
            "--evidence", str(ev), "--result", "pass",
        )
        self.assertEqual(claimed.returncode, 4, claimed.stdout + claimed.stderr)
        real = self.verify(ev)
        self.assertEqual(real.returncode, 0, real.stdout + real.stderr)
        self.assertEqual(self.state()["phase"], "verified_fail")

    def test_mixed_evidence_reports_ignored_stale_count(self) -> None:
        self.init()
        self.plan()
        _, old = self.gate("cu", ["true"])
        time.sleep(1.2)
        self.submit()
        _, fresh = self.gate("moi", ["true"])
        result = self.verify(old, fresh)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        verification = self.state()["attempts"][-1]["verification"]
        self.assertEqual(verification["fresh_evidence"], 1)
        self.assertEqual(verification["ignored_stale_evidence"], 1)

    # -- 5. null + reason -------------------------------------------------
    def test_null_metric_needs_reason(self) -> None:
        self.init()
        self.plan()
        metrics = self.root / "m.json"
        metrics.write_text(json.dumps({"latency": {"value": None}}), encoding="utf-8")
        result = self.submit("--metrics-json", str(metrics))
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("reason", result.stderr)

    def test_null_metric_with_reason_is_kept(self) -> None:
        self.init()
        self.plan()
        metrics = self.root / "m.json"
        metrics.write_text(
            json.dumps({"latency": {"value": None, "reason": "chưa có môi trường đo"}}),
            encoding="utf-8",
        )
        result = self.submit("--metrics-json", str(metrics))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        metric = self.state()["attempts"][-1]["metrics"]["latency"]
        self.assertIsNone(metric["value"])
        self.assertIn("môi trường", metric["reason"])

    # -- 6. Không ghi 0 giả ----------------------------------------------
    def test_zero_without_evidence_is_rejected(self) -> None:
        self.init()
        self.plan()
        metrics = self.root / "m.json"
        metrics.write_text(json.dumps({"errors": {"value": 0, "measured_by": "ci"}}), encoding="utf-8")
        result = self.submit("--metrics-json", str(metrics))
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("0", result.stderr)

    def test_zero_needs_measured_by(self) -> None:
        self.init()
        self.plan()
        metrics = self.root / "m.json"
        metrics.write_text(
            json.dumps({"errors": {"value": 0, "evidence": "ev_0001"}}), encoding="utf-8"
        )
        result = self.submit("--metrics-json", str(metrics))
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("measured_by", result.stderr)

    def test_metric_value_cannot_be_missing(self) -> None:
        self.init()
        self.plan()
        metrics = self.root / "m.json"
        metrics.write_text(json.dumps({"errors": {"measured_by": "ci"}}), encoding="utf-8")
        result = self.submit("--metrics-json", str(metrics))
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)

    def test_zero_with_real_evidence_is_accepted(self) -> None:
        self.init()
        self.plan()
        gate, ev = self.gate("dem-loi", ["true"])
        self.assertEqual(gate.returncode, 0)
        evidence_id = json.loads(ev.read_text(encoding="utf-8"))["evidence_id"]

        # bật cờ: attempt có evidence_ids trước khi metric được kiểm
        metrics = self.root / "m.json"
        metrics.write_text(
            json.dumps({"errors": {"value": 0, "measured_by": "ci", "evidence": evidence_id}}),
            encoding="utf-8",
        )
        result = self.submit("--metrics-json", str(metrics), "--evidence", str(ev))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        metric = self.state()["attempts"][-1]["metrics"]["errors"]
        self.assertEqual(metric["value"], 0)
        self.assertEqual(metric["evidence"], evidence_id)

    # -- 7. Human quyết định ---------------------------------------------
    def test_accept_requires_human_role(self) -> None:
        self.init()
        self.plan()
        self.submit()
        _, fresh = self.gate("moi", ["true"])
        self.verify(fresh)
        bad = run(LOOP, "decide", "--dir", str(self.dir), "--by", EXECUTOR,
                  "--accept", "--note", "tự duyệt")
        self.assertEqual(bad.returncode, 4, bad.stdout + bad.stderr)
        good = run(LOOP, "decide", "--dir", str(self.dir), "--by", HUMAN, "--accept")
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertEqual(self.state()["phase"], "accepted")

    def test_accept_blocked_when_verification_failed(self) -> None:
        self.init()
        self.plan()
        self.submit()
        _, failed = self.gate("hong", ["false"])
        self.verify(failed)
        result = run(LOOP, "decide", "--dir", str(self.dir), "--by", HUMAN, "--accept")
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)

    def test_reject_needs_note(self) -> None:
        self.init()
        self.plan()
        self.submit()
        _, failed = self.gate("hong", ["false"])
        self.verify(failed)
        no_note = run(LOOP, "decide", "--dir", str(self.dir), "--by", HUMAN, "--reject")
        self.assertEqual(no_note.returncode, 4)
        with_note = run(LOOP, "decide", "--dir", str(self.dir), "--by", HUMAN,
                        "--reject", "--note", "thiếu test")
        self.assertEqual(with_note.returncode, 0, with_note.stdout + with_note.stderr)

    # -- 8. Retry sau khi fail -------------------------------------------
    def test_retry_creates_new_attempt(self) -> None:
        self.init()
        self.plan()
        self.submit()
        _, failed = self.gate("hong", ["false"])
        self.verify(failed)
        retry = self.submit("--summary", "sửa lần 2")
        self.assertEqual(retry.returncode, 0, retry.stdout + retry.stderr)
        state = self.state()
        self.assertEqual(len(state["attempts"]), 2)
        self.assertEqual(state["phase"], "submitted")

    # -- 9. State trên file + journal ------------------------------------
    def test_state_and_journal_are_files(self) -> None:
        self.init()
        self.plan()
        self.submit()
        self.assertTrue((self.dir / "STATE.json").exists())
        journal = (self.dir / "journal.jsonl").read_text(encoding="utf-8").splitlines()
        events = [json.loads(line)["event"] for line in journal]
        self.assertEqual(events[:3], ["init", "plan", "submit"])

    def test_status_is_machine_readable(self) -> None:
        self.init()
        result = run(LOOP, "status", "--dir", str(self.dir), "--json")
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["roles"]["executor"], EXECUTOR)
        self.assertEqual(data["phase"], "planned")


if __name__ == "__main__":
    unittest.main(verbosity=2)
