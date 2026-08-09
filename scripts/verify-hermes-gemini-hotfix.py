#!/usr/bin/env python3
"""CI verifier for the Q AI Hermes Gemini hotfix.

This does not need a real API key. It validates that the hotfix still applies
cleanly to Hermes' current Gemini native adapter and that the resulting source
has the auth invariants we depend on. The device-side hotfix script performs
the two live tests with the user's local key.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def patch_adapter(source: str) -> str:
    if "Q AI hotfix: native Gemini must receive exactly one authentication" in source:
        return source

    source = source.replace(
        "self.api_key = api_key\n",
        'self.api_key = (api_key or "").strip()\n',
        1,
    )
    needle = "        headers.update(self._default_headers)\n        return headers\n"
    replacement = """        headers.update(self._default_headers)\n\n        # Q AI hotfix: native Gemini must receive exactly one authentication\n        # mechanism. Generic/OpenAI defaults can contain Authorization or a\n        # stale API-key header; remove them, then set Google's key last.\n        _auth_header_names = {\n            \"authorization\", \"api-key\", \"x-api-key\", \"apikey\",\n            \"x-auth-token\", \"x-access-token\", \"x-goog-api-key\",\n        }\n        for _name in list(headers):\n            if _name.lower() in _auth_header_names:\n                headers.pop(_name, None)\n        headers[\"x-goog-api-key\"] = self.api_key\n        return headers\n"""
    if needle not in source:
        raise AssertionError("Gemini adapter _headers() shape changed; hotfix would refuse to patch")
    return source.replace(needle, replacement, 1)


def verify_adapter(path: Path) -> None:
    source = path.read_text(errors="strict")
    assert "class GeminiNativeClient" in source, "not a Gemini native adapter"
    assert "generateContent" in source, "native generateContent route missing"
    assert '"x-goog-api-key"' in source, "upstream adapter does not contain x-goog-api-key"

    patched = patch_adapter(source)
    compile(patched, str(path), "exec")

    assert "Q AI hotfix: native Gemini must receive exactly one authentication" in patched
    assert '"authorization", "api-key", "x-api-key", "apikey"' in patched
    assert 'headers["x-goog-api-key"] = self.api_key' in patched
    assert 'self.api_key = (api_key or "").strip()' in patched

    # The canonical key must be set AFTER default headers are merged/scrubbed.
    update_pos = patched.index("headers.update(self._default_headers)")
    final_key_pos = patched.index('headers["x-goog-api-key"] = self.api_key', update_pos)
    return_pos = patched.index("return headers", final_key_pos)
    assert update_pos < final_key_pos < return_pos

    print(f"PASS adapter: {path}")


def verify_hotfix_script(path: Path) -> None:
    s = path.read_text(errors="strict")
    required = [
        "unset GOOGLE_API_KEY GEMINI_API_KEY",
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
    print(f"PASS hotfix script: {path}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", action="append", required=True)
    ap.add_argument("--script", required=True)
    args = ap.parse_args()

    verify_hotfix_script(Path(args.script))
    for adapter in args.adapter:
        verify_adapter(Path(adapter))
    print("ALL STATIC/STRUCTURAL TESTS PASSED")


if __name__ == "__main__":
    main()
