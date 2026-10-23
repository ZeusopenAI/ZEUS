#!/usr/bin/env python3
"""Test cho scaffolder scripts/new_loop.py.

    python3 -m unittest discover -s templates/multi-agent-loop/tests -v

Điều quan trọng nhất được kiểm ở đây: **loop sinh ra phải tự đứng được** —
schema + example khớp nhau, state không có 0 giả, và tests của chính nó pass.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[1]
NEW_LOOP = TEMPLATE / "scripts" / "new_loop.py"
PRESETS = ["batch-extract", "bulk-grading", "data-validation"]

_spec = importlib.util.spec_from_file_location("checks_mod", TEMPLATE / "spec" / "checks.py")
checks_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checks_mod)  # type: ignore[union-attr]

try:  # tuỳ chọn: nếu có jsonschema thì đối chiếu với validator chuẩn
    from jsonschema import Draft202012Validator  # type: ignore
except Exception:  # noqa: BLE001
    Draft202012Validator = None  # type: ignore


def run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(NEW_LOOP), *args],
        capture_output=True, text=True, timeout=180, cwd=str(cwd) if cwd else None,
    )


class ScaffoldTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def create(self, preset: str = "batch-extract", name: str | None = None,
               *extra: str) -> tuple[subprocess.CompletedProcess[str], Path]:
        target = self.root / (name or preset)
        result = run("create", "--preset", preset, "--dir", str(target),
                     "--slug", "test-viec", "--owner", "quangquy", *extra)
        return result, target

    # -- 1. Danh sách preset ---------------------------------------------
    def test_list_shows_all_presets(self) -> None:
        result = run("list")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for preset in PRESETS:
            self.assertIn(preset, result.stdout)

    # -- 2. Sinh loop cho từng preset ------------------------------------
    def test_create_each_preset_self_verifies(self) -> None:
        for preset in PRESETS:
            with self.subTest(preset=preset):
                result, target = self.create(preset)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Tự kiểm chứng", result.stdout)
                self.assertTrue((target / "state" / "state.json").exists())

    def test_generated_loop_has_full_structure(self) -> None:
        _, target = self.create()
        for rel in (
            "spec/rules.md", "spec/schema.json", "spec/checks.py",
            "state/state.json", "input/README.md", "output/README.md",
            "verify/README.md", "reports/README.md", "log",
            "examples/example-output.jsonl",
            ".github/workflows/verify.yml", "README.md", ".gitignore",
            "scripts/loop_state.py", "scripts/new_loop.py",
            "tests/test_loop.py", "tests/test_schema_examples.py",
        ):
            self.assertTrue((target / rel).exists(), f"thiếu {rel}")

    # -- 3. Không có 0 giả trong state khởi tạo --------------------------
    def test_state_has_no_fake_zeros(self) -> None:
        _, target = self.create()
        state = json.loads((target / "state" / "state.json").read_text(encoding="utf-8"))
        counters = state["counters"]
        for name, spec in counters.items():
            self.assertIsNone(spec["value"], f"{name} phải là null khi chưa chạy")
            self.assertTrue(str(spec.get("reason") or "").strip(), f"{name} thiếu reason")
        quota = state["quota"]
        self.assertIsNone(quota["used_records_today"]["value"])
        self.assertIsNone(quota["remaining_records"]["value"])

    def test_state_has_utc_system_day_and_roles(self) -> None:
        _, target = self.create()
        state = json.loads((target / "state" / "state.json").read_text(encoding="utf-8"))
        self.assertRegex(state["system_day"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(state["timezone"], "UTC")
        self.assertEqual(state["roles"]["human"], "quangquy")
        self.assertNotEqual(state["roles"]["executor"], state["roles"]["verifier"])

    def test_preset_rules_are_appended(self) -> None:
        _, target = self.create()
        rules = (target / "spec" / "rules.md").read_text(encoding="utf-8")
        self.assertIn("Luật riêng", rules)
        self.assertIn("batch-extract", rules)

    def test_generated_workflow_uses_preset_thresholds(self) -> None:
        _, target = self.create("bulk-grading")
        workflow = (target / ".github" / "workflows" / "verify.yml").read_text(encoding="utf-8")
        self.assertIn("--zero-guard-fields", workflow)
        self.assertIn("score", workflow)
        self.assertIn("--max-duplicate-rate", workflow)
        self.assertIn("--max-records-per-second", workflow)

    # -- 4. Loop sinh ra tự chạy được ------------------------------------
    def test_generated_loop_tests_pass(self) -> None:
        _, target = self.create()
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=str(target), capture_output=True, text=True, timeout=300,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stderr + result.stdout)

    def test_generated_loop_checks_pass_on_example(self) -> None:
        _, target = self.create("data-validation")
        (target / "output").mkdir(exist_ok=True)
        (target / "log").mkdir(exist_ok=True)
        (target / "output" / "batch-0001.jsonl").write_text(
            (target / "examples" / "example-output.jsonl").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (target / "log" / "run-0001.jsonl").write_text(
            json.dumps({"at": "2026-10-23T08:00:00Z", "started_at": "2026-10-23T08:00:00Z",
                        "finished_at": "2026-10-23T08:00:09Z", "records": 3}) + "\n",
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, "spec/checks.py", "run", "--report", "verify/t.json"],
            cwd=str(target), capture_output=True, text=True, timeout=180,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    # -- 5. An toàn khi sinh ---------------------------------------------
    def test_refuses_non_empty_dir(self) -> None:
        target = self.root / "occupied"
        target.mkdir()
        (target / "giu-nguyen.txt").write_text("dữ liệu của bạn", encoding="utf-8")
        result = run("create", "--preset", "batch-extract", "--dir", str(target), "--slug", "x")
        self.assertEqual(result.returncode, 5, result.stdout + result.stderr)
        self.assertTrue((target / "giu-nguyen.txt").exists(), "không được xoá file của người dùng")

    def test_force_overwrites(self) -> None:
        target = self.root / "occupied"
        target.mkdir()
        (target / "giu-nguyen.txt").write_text("x", encoding="utf-8")
        result = run("create", "--preset", "batch-extract", "--dir", str(target),
                     "--slug", "x", "--force")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unknown_preset_is_usage_error(self) -> None:
        result = run("create", "--preset", "khong-co", "--dir", str(self.root / "x"), "--slug", "x")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_no_verify_skips_selftest(self) -> None:
        result, target = self.create("batch-extract", "nhanh", "--no-verify")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("Tự kiểm chứng", result.stdout)
        self.assertTrue((target / "state" / "state.json").exists())

    def test_broken_example_is_caught_and_cleaned_up(self) -> None:
        """Nếu preset có example hỏng, scaffolder phải xoá loop và báo lỗi."""
        broken = self.root / "broken-preset"
        (broken).mkdir()
        preset_dir = TEMPLATE / "presets" / "batch-extract"
        meta = json.loads((preset_dir / "preset.json").read_text(encoding="utf-8"))
        meta["name"] = "_broken_test"
        (broken / "preset.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        (broken / "rules.append.md").write_text(
            (preset_dir / "rules.append.md").read_text(encoding="utf-8"), encoding="utf-8"
        )
        # schema đòi 'fields' nhưng example không có → chắc chắn fail
        (broken / "schema.json").write_text((preset_dir / "schema.json").read_text(encoding="utf-8"),
                                            encoding="utf-8")
        (broken / "example-output.jsonl").write_text(
            json.dumps({"id": "x", "created_at": "2026-10-23T08:00:00Z", "source": "s",
                        "status": "ok", "metrics": {}}) + "\n",
            encoding="utf-8",
        )
        # chèn preset tạm vào template rồi dọn dẹp sau test
        target_preset = TEMPLATE / "presets" / "_broken_test"
        if target_preset.exists():
            self.skipTest("preset tạm đã tồn tại")
        try:
            subprocess.run(["cp", "-r", str(broken), str(target_preset)], check=True)
            target = self.root / "from-broken"
            result = run("create", "--preset", "_broken_test", "--dir", str(target), "--slug", "x")
            self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
            self.assertFalse(target.exists(), "loop hỏng phải bị xoá")
        finally:
            subprocess.run(["rm", "-rf", str(target_preset)], check=False)


class ValidatorParityTest(unittest.TestCase):
    """Validator trong checks.py phải không lỏng hơn JSON Schema chuẩn.

    Lỗi từng xảy ra: schema có `minProperties` nhưng validator bỏ qua ⇒ record sai vẫn "pass".
    """

    def load(self, preset: str) -> dict:
        return json.loads((TEMPLATE / "presets" / preset / "schema.json").read_text(encoding="utf-8"))

    def examples(self, preset: str) -> list[dict]:
        path = TEMPLATE / "presets" / preset / "example-output.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_examples_pass_builtin_validator(self) -> None:
        for preset in PRESETS:
            schema = self.load(preset)
            for index, record in enumerate(self.examples(preset), 1):
                with self.subTest(preset=preset, line=index):
                    self.assertEqual(checks_mod.validate(record, schema, schema), [])

    @unittest.skipIf(Draft202012Validator is None, "chưa cài jsonschema")
    def test_builtin_matches_json_schema_on_examples(self) -> None:
        for preset in PRESETS:
            schema = self.load(preset)
            validator = Draft202012Validator(schema)
            for index, record in enumerate(self.examples(preset), 1):
                with self.subTest(preset=preset, line=index):
                    theirs = list(validator.iter_errors(record))
                    ours = checks_mod.validate(record, schema, schema)
                    self.assertEqual(bool(theirs), bool(ours),
                                     f"lệch kết luận: json-schema={[e.message for e in theirs]}, "
                                     f"checks.py={ours}")

    @unittest.skipIf(Draft202012Validator is None, "chưa cài jsonschema")
    def test_min_properties_is_enforced_by_both(self) -> None:
        schema = self.load("batch-extract")
        record = self.examples("batch-extract")[0]
        record = json.loads(json.dumps(record))
        record["fields"] = {}          # status "ok" nhưng không có trường nào
        ours = checks_mod.validate(record, schema, schema)
        theirs = list(Draft202012Validator(schema).iter_errors(record))
        self.assertTrue(ours, "checks.py phải bắt fields rỗng với status ok")
        self.assertTrue(theirs, "JSON Schema phải bắt fields rỗng với status ok")

    def test_skipped_record_may_have_empty_fields(self) -> None:
        schema = self.load("batch-extract")
        record = next(r for r in self.examples("batch-extract") if r["status"] == "skipped")
        self.assertEqual(checks_mod.validate(record, schema, schema), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
