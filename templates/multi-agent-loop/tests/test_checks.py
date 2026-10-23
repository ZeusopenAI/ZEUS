#!/usr/bin/env python3
"""Test cho spec/checks.py — mỗi test ứng với một bẫy hoặc một luật.

    python3 -m unittest discover -s templates/multi-agent-loop/tests -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[1]
CHECKS = TEMPLATE / "spec" / "checks.py"
SCHEMA = TEMPLATE / "spec" / "schema.json"


def run_checks(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKS), *args], capture_output=True, text=True, timeout=120
    )


class ChecksTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "spec").mkdir()
        (self.root / "spec" / "schema.json").write_text(
            SCHEMA.read_text(encoding="utf-8"), encoding="utf-8"
        )
        for name in ("input", "output", "log", "verify", "state"):
            (self.root / name).mkdir()
        self.state = {
            "schema": "multi-agent-loop-state/1",
            "system_day": self._today(),
            "quota": {"max_records_per_day": 100, "used_records_today": 0},
        }
        self.write_state()
        (self.root / "log" / "run.jsonl").write_text(
            json.dumps({
                "at": "2026-10-23T08:00:00Z",
                "started_at": "2026-10-23T08:00:00Z",
                "finished_at": "2026-10-23T08:00:10Z",
                "records": 10,
            }) + "\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------
    @staticmethod
    def _today() -> str:
        import datetime as dt
        return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")

    def write_state(self) -> None:
        (self.root / "state" / "state.json").write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def write_output(self, records: list[dict]) -> None:
        path = self.root / "output" / "batch-0001.jsonl"
        path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def record(**overrides) -> dict:
        base = {
            "id": "r-0001",
            "created_at": "2026-10-23T08:00:01Z",
            "source": "input/raw.jsonl#L1",
            "status": "ok",
            "content": "nội dung mẫu",
            "metrics": {"latency_ms": {"value": 120, "measured_by": "executor", "unit": "ms"}},
        }
        base.update(overrides)
        return base

    def report_path(self, name: str = "verify/checks-test.json") -> str:
        return str(self.root / name)

    def run_report(self, *extra: str) -> tuple[subprocess.CompletedProcess[str], dict | None]:
        report = self.report_path()
        result = run_checks(
            "run", "--root", str(self.root), "--report", report, *extra
        )
        data = None
        if Path(report).exists():
            data = json.loads(Path(report).read_text(encoding="utf-8"))
        return result, data

    # -- 1. Vòng hợp lệ ---------------------------------------------------
    def test_valid_output_passes(self) -> None:
        self.write_output([self.record()])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["overall"], "pass")
        self.assertEqual(report["checks"]["schema"]["status"], "pass")
        self.assertEqual(report["checks"]["fake_zero"]["status"], "pass")

    def test_report_has_snapshot_and_system_day(self) -> None:
        self.write_output([self.record()])
        _, report = self.run_report()
        self.assertEqual(len(report["output_snapshot"]), 64)
        self.assertEqual(report["system_day"], self._today())

    # -- 2. Schema --------------------------------------------------------
    def test_schema_violation_fails(self) -> None:
        self.write_output([self.record(status="not-a-valid-status")])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertEqual(report["checks"]["schema"]["status"], "fail")
        self.assertIn("schema", report["required_failed"])

    def test_partial_status_requires_reason(self) -> None:
        self.write_output([self.record(status="partial")])
        _, report = self.run_report()
        self.assertEqual(report["checks"]["schema"]["status"], "fail")

    def test_non_utc_timestamp_fails(self) -> None:
        self.write_output([self.record(created_at="2026-10-23 08:00:01")])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 4)
        self.assertEqual(report["checks"]["utc_format"]["status"], "fail")

    def test_empty_output_is_not_measured(self) -> None:
        result, _ = self.run_report()
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)

    # -- 3. null + reason -------------------------------------------------
    def test_null_without_reason_fails(self) -> None:
        self.write_output([self.record(metrics={"confidence": {"value": None}})])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 4)
        self.assertEqual(report["checks"]["null_reason"]["status"], "fail")
        self.assertGreater(report["checks"]["null_reason"]["metrics"]["null_without_reason"]["value"], 0)

    def test_null_with_reason_passes(self) -> None:
        self.write_output([self.record(metrics={
            "confidence": {"value": None, "reason": "model không trả score"}})])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["checks"]["null_reason"]["status"], "pass")
        self.assertEqual(report["checks"]["null_reason"]["metrics"]["null_values"]["value"], 1)

    # -- 4. Không ghi 0 giả ----------------------------------------------
    def test_zero_without_evidence_fails(self) -> None:
        self.write_output([self.record(metrics={"errors": {"value": 0, "measured_by": "executor"}})])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 4)
        self.assertEqual(report["checks"]["fake_zero"]["status"], "fail")
        self.assertEqual(report["checks"]["fake_zero"]["metrics"]["unproven_zeros"]["value"], 1)

    def test_zero_with_real_log_evidence_passes(self) -> None:
        self.write_output([self.record(metrics={
            "errors": {"value": 0, "measured_by": "executor",
                       "evidence": "log/run.jsonl#L1"}})])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["checks"]["fake_zero"]["status"], "pass")
        self.assertEqual(report["checks"]["fake_zero"]["metrics"]["zero_values"]["value"], 1)

    def test_zero_with_invented_evidence_fails(self) -> None:
        self.write_output([self.record(metrics={
            "errors": {"value": 0, "measured_by": "executor",
                       "evidence": "log/khong-ton-tai.jsonl#L99"}})])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 4)
        self.assertIn("không tồn tại", " ".join(report["checks"]["fake_zero"]["problems"]))

    # -- 5. Bẫy sinh hàng loạt -------------------------------------------
    def test_high_duplicate_rate_fails(self) -> None:
        records = [self.record(id=f"r-{i:04d}", content="cùng một nội dung") for i in range(20)]
        self.write_output(records)
        result, report = self.run_report()
        self.assertEqual(result.returncode, 4)
        self.assertEqual(report["checks"]["duplicates"]["status"], "fail")

    def test_low_duplicate_rate_passes(self) -> None:
        records = [self.record(id=f"r-{i:04d}", content=f"nội dung riêng {i}") for i in range(20)]
        self.write_output(records)
        result, report = self.run_report()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["checks"]["duplicates"]["status"], "pass")

    def test_absurd_throughput_fails(self) -> None:
        (self.root / "log" / "run.jsonl").write_text(
            json.dumps({
                "started_at": "2026-10-23T08:00:00Z",
                "finished_at": "2026-10-23T08:00:00.23Z",
                "records": 643,
            }) + "\n",
            encoding="utf-8",
        )
        self.write_output([self.record(id=f"r-{i:04d}", content=f"nội dung {i}") for i in range(5)])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 4)
        self.assertEqual(report["checks"]["throughput"]["status"], "fail")
        self.assertGreater(
            report["checks"]["throughput"]["metrics"]["records_per_second"]["value"], 50
        )

    def test_small_sample_distribution_is_null_not_zero(self) -> None:
        self.write_output([self.record(id=f"r-{i:04d}", content=f"abc {i}") for i in range(3)])
        _, report = self.run_report()
        metrics = report["checks"]["length_distribution"]["metrics"]
        self.assertIsNone(metrics["length_outliers"]["value"])
        self.assertIn("reason", metrics["length_outliers"])
        self.assertEqual(report["checks"]["length_distribution"]["status"], "not_measured")

    def test_large_sample_distribution_measured(self) -> None:
        records = [self.record(id=f"r-{i:04d}", content="x" * (50 + i)) for i in range(40)]
        self.write_output(records)
        _, report = self.run_report()
        metrics = report["checks"]["length_distribution"]["metrics"]
        self.assertEqual(metrics["sample_size"]["value"], 40)
        self.assertIsNotNone(metrics["length_outliers"]["value"])

    # -- 6. Múi giờ -------------------------------------------------------
    def test_state_day_drift_warns(self) -> None:
        self.state["system_day"] = "2020-01-01"
        self.write_state()
        self.write_output([self.record()])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["checks"]["day_boundary"]["status"], "warn")
        self.assertIn("day_boundary", report["warnings"])

    def test_missing_system_day_fails(self) -> None:
        self.state.pop("system_day")
        self.write_state()
        self.write_output([self.record()])
        result, report = self.run_report()
        self.assertEqual(result.returncode, 4)
        self.assertEqual(report["checks"]["day_boundary"]["status"], "fail")

    # -- 7. Chống dùng lại báo cáo cũ ------------------------------------
    def test_report_cannot_be_overwritten(self) -> None:
        self.write_output([self.record()])
        self.run_report()
        again, _ = self.run_report()
        self.assertEqual(again.returncode, 5, again.stdout + again.stderr)
        self.assertIn("từ đầu", again.stderr)

    def test_freshness_detects_changed_output(self) -> None:
        self.write_output([self.record()])
        self.run_report()
        fresh = run_checks("freshness", "--root", str(self.root),
                           "--report", self.report_path())
        self.assertEqual(fresh.returncode, 0, fresh.stdout + fresh.stderr)

        self.write_output([self.record(content="nội dung đã đổi")])
        stale = run_checks("freshness", "--root", str(self.root),
                           "--report", self.report_path())
        self.assertEqual(stale.returncode, 5, stale.stdout + stale.stderr)
        self.assertIn("BÁO CÁO CŨ", stale.stderr)

    # -- 8. Ranh giới ghi file -------------------------------------------
    def test_ownership_flags_wrong_cu_ghia(self) -> None:
        repo = self.root
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        for key, value in (("user.email", "t@e.com"), ("user.name", "t")):
            subprocess.run(["git", "-C", str(repo), "config", key, value], check=True)
        (repo / "output").mkdir(exist_ok=True)
        (repo / "output" / "a.jsonl").write_text("{}\n", encoding="utf-8")
        (repo / "spec" / "rules.md").write_text("x\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "init"], check=True)

        (repo / "output" / "a.jsonl").write_text("{}\n{}\n", encoding="utf-8")
        ok = run_checks("ownership", "--root", str(repo), "--role", "executor")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)

        (repo / "spec" / "rules.md").write_text("executor sửa spec — vi phạm\n", encoding="utf-8")
        bad = run_checks("ownership", "--root", str(repo), "--role", "executor")
        self.assertEqual(bad.returncode, 4, bad.stdout + bad.stderr)
        self.assertIn("spec/rules.md", bad.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
