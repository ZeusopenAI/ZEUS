#!/usr/bin/env python3
"""Test cho chính workflow CI của template — CI cũng là code, cũng phải bị kiểm.

    python3 -m unittest discover -s templates/multi-agent-loop/tests -v

Vì sao có file này: một step CI đã từng **pass mà không chạy gì** vì heredoc lồng trong
YAML bị shell nuốt mất phần sau `cat > file <<'EOF'`. Step xanh, bộ kiểm không hề chạy —
đúng kiểu "báo cáo không phản ánh việc đã làm" mà template này sinh ra để chặn.

Bốn luật:
  1. Không heredoc trong workflow (dùng fixture có thật trong repo).
  2. Mọi khối `run:` phải qua `bash -n`.
  3. Mọi `uses:` phải pin SHA 40 ký tự (luật của repo ZEUS).
  4. File mà workflow nhắc tới phải tồn tại trong template.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
TEMPLATE = HERE.parents[1]
REPO = TEMPLATE.parents[1]

WORKFLOWS = [REPO / ".github" / "workflows" / "multi-agent-loop-ci.yml"]
WORKFLOWS += sorted((TEMPLATE / ".github" / "workflows").glob("*.yml"))

SHA_RE = re.compile(r"@[0-9a-f]{40}$")
FILE_TOKEN_RE = re.compile(r"(?<![\w/$-])((?:spec|scripts|examples|presets|state|log|input|tests)/[\w./-]+\.(?:jsonl|json|py|md|yml))")

try:  # pyyaml chỉ cần cho luật 2–3; luật 1 chạy được mà không cần gì
    import yaml  # type: ignore
except Exception:  # noqa: BLE001
    yaml = None  # type: ignore


def steps_with_run(workflow: Path) -> list[dict]:
    document = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    steps: list[dict] = []
    for job in (document.get("jobs") or {}).values():
        steps.extend(job.get("steps") or [])
    return steps


class WorkflowGuardTest(unittest.TestCase):
    def test_workflow_files_exist(self) -> None:
        self.assertTrue(WORKFLOWS, "không tìm thấy workflow nào")
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                self.assertTrue(workflow.exists(), f"thiếu {workflow}")

    def test_no_heredoc_in_workflows(self) -> None:
        for workflow in WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                text = workflow.read_text(encoding="utf-8")
                self.assertNotIn(
                    "<<", text,
                    "workflow không được dùng heredoc: heredoc lồng trong YAML từng làm "
                    "step pass mà không chạy dòng nào. Dùng fixture có thật trong repo.",
                )

    def test_no_empty_run_blocks(self) -> None:
        for workflow in WORKFLOWS:
            text = workflow.read_text(encoding="utf-8")
            with self.subTest(workflow=workflow.name):
                self.assertNotRegex(text, r"run:\s*\|\s*\n\s*\n", "khối run rỗng")

    @unittest.skipIf(yaml is None, "chưa cài pyyaml")
    def test_every_run_block_parses(self) -> None:
        for workflow in WORKFLOWS:
            for index, step in enumerate(steps_with_run(workflow)):
                script = step.get("run")
                if not script:
                    continue
                with self.subTest(workflow=workflow.name, step=step.get("name", index)):
                    self.assertTrue(script.strip(), "step có run rỗng")
                    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False,
                                                     encoding="utf-8") as handle:
                        handle.write(script)
                        path = handle.name
                    try:
                        result = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
                    finally:
                        Path(path).unlink(missing_ok=True)
                    self.assertEqual(result.returncode, 0,
                                     f"bash -n lỗi ở step '{step.get('name')}': {result.stderr}")

    @unittest.skipIf(yaml is None, "chưa cài pyyaml")
    def test_actions_are_pinned_to_sha(self) -> None:
        for workflow in WORKFLOWS:
            for index, step in enumerate(steps_with_run(workflow)):
                uses = step.get("uses")
                if not uses:
                    continue
                with self.subTest(workflow=workflow.name, step=step.get("name", index)):
                    self.assertRegex(uses, SHA_RE,
                                     f"'{uses}' chưa pin SHA 40 ký tự — GitHub Actions của repo "
                                     "từ chối action không pin SHA")

    def test_referenced_files_exist(self) -> None:
        for workflow in WORKFLOWS:
            text = workflow.read_text(encoding="utf-8")
            for token in sorted(set(FILE_TOKEN_RE.findall(text))):
                if any(mark in token for mark in ("$", "*")):
                    continue
                with self.subTest(workflow=workflow.name, file=token):
                    self.assertTrue((TEMPLATE / token).exists(),
                                    f"workflow nhắc {token} nhưng template không có file đó")

    def test_ci_runs_the_checker_on_real_output(self) -> None:
        """Step 'bộ kiểm thật' phải thật sự gọi checks.py với fixture có trong repo."""
        text = (REPO / ".github" / "workflows" / "multi-agent-loop-ci.yml").read_text(encoding="utf-8")
        self.assertIn("spec/checks.py run", text)
        self.assertIn("examples/demo-output.jsonl", text)
        self.assertTrue((TEMPLATE / "examples" / "demo-output.jsonl").exists())

    def test_bash_available(self) -> None:
        self.assertIsNotNone(shutil.which("bash"), "test này cần bash")


if __name__ == "__main__":
    unittest.main(verbosity=2)
