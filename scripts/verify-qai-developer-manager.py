#!/usr/bin/env python3
from pathlib import Path
import re
import sys

skill = Path("skills/qai-developer-manager/SKILL.md")
sources = Path("skills/qai-developer-manager/references/SOURCES.md")

for p in (skill, sources):
    if not p.exists():
        raise SystemExit(f"missing required file: {p}")

s = skill.read_text(encoding="utf-8")
r = sources.read_text(encoding="utf-8")

required_skill = [
    "name: qai-developer-manager",
    "## Mission",
    "## Core rules",
    "### Phase 1 — Triage",
    "### Phase 2 — Research",
    "### Phase 3 — Plan",
    "### Phase 4 — Implement",
    "### Phase 5 — Validate",
    "### Phase 6 — Adversarial review",
    "### Phase 7 — Commit and handoff",
    "## Multi-agent delegation",
    "## Debugging provider/auth failures",
    "## GitHub workflow",
    "## Android/IME workflow",
    "## Definition of done",
    "## Anti-patterns",
]
missing = [x for x in required_skill if x not in s]
assert not missing, f"missing skill invariants: {missing}"

required_sources = [
    "ByteDance DeerFlow",
    "MetaGPT",
    "ChatDev",
    "OpenManus",
    "wshobson/agents",
    "Hugging Face skills",
    "metaswarm",
    "OpenCode",
    "Qwen Code",
    "daVinci-Dev",
    "SWE-Dev",
    "SwarmDo",
]
missing_sources = [x for x in required_sources if x not in r]
assert not missing_sources, f"missing source inspirations: {missing_sources}"

# Guardrails that must remain explicit.
for phrase in [
    "Evidence before edits",
    "Never modify or expose secrets",
    "direct minimal probe",
    "rollback path",
    "A passing lower layer does not override a failing higher layer",
    "Do not keep changing unrelated variables at once",
    "claim success from static CI",
]:
    assert phrase in s, f"guardrail missing: {phrase}"

# Lightweight leak detection for committed skill/reference text.
patterns = [
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"\bAQ\.[0-9A-Za-z._-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
]
for path, text in [(skill, s), (sources, r)]:
    for pat in patterns:
        assert not pat.search(text), f"possible secret in {path}"

# Keep the skill compact enough for progressive loading.
assert len(s.splitlines()) < 260, "SKILL.md grew too large; split references/checklists instead"

print("PASS QAI Developer Manager structural verification")
print(f"skill_lines={len(s.splitlines())} sources_lines={len(r.splitlines())}")
