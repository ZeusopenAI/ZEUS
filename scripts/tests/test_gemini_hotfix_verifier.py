#!/usr/bin/env python3
"""Test cho verifier hotfix Gemini (`scripts/verify-hermes-gemini-hotfix.py`).

Bối cảnh: CI `hermes-gemini-hotfix-ci.yml` và `qai-developer-manager-10x-ci.yml`
đỏ 11 job (23/10/2026) chỉ vì upstream NousResearch đổi shape `_headers()` sang
`**self._auth_headers()`. Verifier cũ coi mọi shape lạ là fail.

Bộ test này khoá lại 3 hành vi:
  1. Shape cũ (headers.update(self._default_headers)) -> vá được, PASS.
  2. Shape upstream mới (đã single-auth)                  -> PASS, không vá.
  3. Shape lạ (không rõ auth)                             -> FAIL (không được xanh giả).

    python3 -m unittest discover -s scripts/tests -p 'test_gemini_hotfix_verifier.py' -v
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[2]
VERIFIER = REPO_DIR / "scripts" / "verify-hermes-gemini-hotfix.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_hermes_gemini_hotfix", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


LEGACY_ADAPTER = '''
class GeminiNativeClient:
    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key

    def _headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        headers.update(self._default_headers)
        return headers

    def generateContent(self):
        return self._headers()
'''

UPSTREAM_SAFE_ADAPTER = '''
class GeminiNativeClient:
    def __init__(self, *, api_key: str) -> None:
        self.api_key, self._default_headers = api_key, {}

    def _auth_headers(self) -> dict:
        return {"x-goog-api-key": self.api_key}

    def _headers(self) -> dict:
        return {"Content-Type": "application/json", **self._auth_headers(),
                "X-Goog-Api-Client": "x", **self._default_headers}

    def generateContent(self):
        return self._headers()
'''

UNKNOWN_SHAPE_ADAPTER = '''
class GeminiNativeClient:
    def __init__(self, *, api_key: str) -> None:
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"x-goog-api-key": self.api_key}

    def generateContent(self):
        return self._headers()
'''


class VerifierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_verifier()

    def _verify(self, adapter_source: str) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
            fh.write(adapter_source)
            path = Path(fh.name)
        try:
            self.mod.verify_adapter(path)
        finally:
            path.unlink()

    def test_legacy_shape_gets_patched(self) -> None:
        patched = self.mod.patch_adapter(LEGACY_ADAPTER)
        self.assertIn(self.mod.HOTFIX_MARKER, patched)
        self.assertIn('headers["x-goog-api-key"] = self.api_key', patched)
        self.assertLess(
            patched.index("headers.update(self._default_headers)"),
            patched.index('headers["x-goog-api-key"] = self.api_key'),
        )
        self._verify(LEGACY_ADAPTER)  # không được raise

    def test_upstream_safe_shape_passes_without_patching(self) -> None:
        self.assertTrue(self.mod.upstream_already_single_auth(UPSTREAM_SAFE_ADAPTER))
        # Không được vá: patch_adapter chỉ dùng cho shape legacy nên phải từ chối shape mới.
        with self.assertRaises(AssertionError):
            self.mod.patch_adapter(UPSTREAM_SAFE_ADAPTER)
        self._verify(UPSTREAM_SAFE_ADAPTER)  # nhưng verifier phải PASS

    def test_unknown_shape_fails_loudly(self) -> None:
        self.assertFalse(self.mod.upstream_already_single_auth(UNKNOWN_SHAPE_ADAPTER))
        with self.assertRaises(AssertionError) as ctx:
            self.mod.patch_adapter(UNKNOWN_SHAPE_ADAPTER)
        self.assertIn("shape changed", str(ctx.exception))

    def test_adapter_without_goog_key_header_fails(self) -> None:
        broken = UNKNOWN_SHAPE_ADAPTER.replace('"x-goog-api-key"', '"x-api-key"')
        with self.assertRaises(AssertionError):
            self._verify(broken)

    def test_real_repo_adapter_passes(self) -> None:
        self._verify((REPO_DIR / "agents/hermes/agent/gemini_native_adapter.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
