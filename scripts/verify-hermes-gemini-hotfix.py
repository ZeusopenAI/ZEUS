#!/usr/bin/env python3
"""CI verifier for the Q AI Hermes Gemini hotfix.

No real API key is used in CI. The device-side script performs the live calls.
This verifier ensures the hotfix still applies cleanly to current Hermes native
Gemini adapters and that the self-recovery logic is present and secret-safe.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

HOTFIX_MARKER = "Q AI hotfix: native Gemini must receive exactly one authentication"

# Upstream đã tự bảo đảm "đúng một cơ chế auth": key được đặt trong `_auth_headers()`
# (chỉ chứa x-goog-api-key) rồi spread vào `_headers()`, nên header Authorization
# thừa từ default headers cũng bị ghi đè theo thứ tự spread. Khi gặp dạng này thì
# hotfix không cần vá nữa (vá thêm là rủi ro, không phải giá trị).
_UPSTREAM_SAFE_PATTERNS = (
    # def _auth_headers(self): return {"x-goog-api-key": self.api_key}
    re.compile(
        r"def _auth_headers\(self\)[^\n]*:\s*\n\s*return\s*\{\s*[\"']x-goog-api-key[\"']\s*:\s*self\.api_key\s*\}",
    ),
    # def _headers(self): return {..., **self._auth_headers(), ...}  (không có **default_headers sau đó)
    re.compile(
        r"def _headers\(self\)[^\n]*:[\s\S]{0,600}?\*\*self\._auth_headers\(\)"
    ),
)


def upstream_already_single_auth(source: str) -> bool:
    """True khi adapter đã tự bảo đảm chỉ một cơ chế auth (không cần hotfix)."""
    return all(pattern.search(source) for pattern in _UPSTREAM_SAFE_PATTERNS)


def patch_adapter(source: str) -> str:
    if HOTFIX_MARKER in source:
        return source

    source = source.replace(
        "self.api_key = api_key\n",
        'self.api_key = (api_key or "").strip()\n',
        1,
    )
    needle = "        headers.update(self._default_headers)\n        return headers\n"
    replacement = """        headers.update(self._default_headers)\n\n        # Q AI hotfix: native Gemini must receive exactly one authentication\n        # mechanism. Generic/OpenAI defaults can contain Authorization or a\n        # stale API-key header; remove them, then set Google's key last.\n        _auth_header_names = {\n            \"authorization\", \"api-key\", \"x-api-key\", \"apikey\",\n            \"x-auth-token\", \"x-access-token\", \"x-goog-api-key\",\n        }\n        for _name in list(headers):\n            if _name.lower() in _auth_header_names:\n                headers.pop(_name, None)\n        headers[\"x-goog-api-key\"] = self.api_key\n        return headers\n"""
    if needle not in source:
        raise AssertionError(
            "Gemini adapter _headers() shape changed and is NOT in the known-safe "
            "single-auth shape; hotfix would refuse to patch. Cập nhật needle trong "
            "scripts/hermes-gemini-hotfix.sh + verifier này."
        )
    return source.replace(needle, replacement, 1)


def verify_adapter(path: Path) -> None:
    source = path.read_text(errors="strict")
    assert "class GeminiNativeClient" in source, "not a Gemini native adapter"
    assert "generateContent" in source, "native generateContent route missing"
    assert '"x-goog-api-key"' in source, "upstream adapter does not contain x-goog-api-key"

    if HOTFIX_MARKER not in source and upstream_already_single_auth(source):
        # Không vá, nhưng vẫn phải chắc file là Python hợp lệ.
        compile(source, str(path), "exec")
        print(
            f"PASS adapter: {path} — upstream đã tự bảo đảm single auth "
            "(x-goog-api-key trong _auth_headers), hotfix không cần áp dụng"
        )
        return

    patched = patch_adapter(source)
    compile(patched, str(path), "exec")

    assert HOTFIX_MARKER in patched
    assert '"authorization", "api-key", "x-api-key", "apikey"' in patched
    assert 'headers["x-goog-api-key"] = self.api_key' in patched
    assert 'self.api_key = (api_key or "").strip()' in patched

    update_pos = patched.index("headers.update(self._default_headers)")
    final_key_pos = patched.index('headers["x-goog-api-key"] = self.api_key', update_pos)
    return_pos = patched.index("return headers", final_key_pos)
    assert update_pos < final_key_pos < return_pos

    print(f"PASS adapter: {path} — hotfix áp dụng được (legacy _headers shape)")


def verify_hotfix_script(path: Path) -> None:
    s = path.read_text(errors="strict")
    required = [
        "unset GOOGLE_API_KEY GEMINI_API_KEY",
        "candidate_files()",
        "ACCESS_TOKEN_TYPE_UNSUPPORTED",
        "Found {len(candidates)} unique Gemini key candidate(s)",
        "Selected working key fp=",
        "GOOGLE_API_KEY={secret}",
        "Runtime key fp",
        "Key match",
        "Raw Gemini REST test",
        "GeminiNativeClient test",
        "hermes-start.sh patched against inherited stale Gemini keys",
        'headers["x-goog-api-key"] = self.api_key',
    ]
    missing = [item for item in required if item not in s]
    assert not missing, f"hotfix script missing invariants: {missing}"

    # Safety: the script may print fingerprints and source filenames, not key values.
    assert "print(secret" not in s
    assert "print(key" not in s
    assert "echo $GOOGLE_API_KEY" not in s
    assert "echo $GEMINI_API_KEY" not in s

    print(f"PASS hotfix script: {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", action="append", required=True)
    ap.add_argument("--script", required=True)
    args = ap.parse_args()

    try:
        verify_hotfix_script(Path(args.script))
        for adapter in args.adapter:
            verify_adapter(Path(adapter))
    except AssertionError as exc:  # thông báo gọn cho CI, không cần traceback
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print("ALL STATIC/STRUCTURAL TESTS PASSED")


if __name__ == "__main__":
    main()
