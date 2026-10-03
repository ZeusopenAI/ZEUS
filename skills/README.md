# Quang Quy AI / Zeus — Skills Directory

This directory contains reusable, domain-specific skills for the Zeus / Hermes Agent platform.

## Available Skills

### 1. qai-developer-manager

**Purpose**: Principal engineering manager and senior developer for complex software-engineering tasks.

**When to use**:
- Repository-level debugging and multi-file code modifications
- Fixing provider, auth, or model-routing failures
- Android / Termux / Colab environment validation
- Ensuring test coverage, CI verification, and safe rollback mechanisms

Full guide: [skills/qai-developer-manager/SKILL.md](qai-developer-manager/SKILL.md)

---

### 2. hermes-project-analyst-code-manager

**Purpose**: Persistent project management and code analysis for the Hermes Agent runtime.

**When to use**:
- Diagnosing Hermes provider/auth switching issues
- Planning minimal code/config fixes while preserving architecture
- Implementing and validating changes across environments
- Managing Git history, clean commits, and GitHub repository synchronizations

Full guide: [skills/hermes-project-analyst-code-manager/SKILL.md](hermes-project-analyst-code-manager/SKILL.md)

---

### 3. second-brain

**Purpose**: Capture, organize, and recall everything exchanged with ChatGPT, Claude.ai, Gemini, and Hermes into one searchable memory.

**When to use**:
- Ingesting chat exports (`conversations.json`, Claude zip export, Gemini Takeout).
- Recalling past discussions across AI assistants.
- Handing shared memory (`USER.md` / `MEMORY.md`) to external AIs so they continue threads seamlessly.
- Multi-model routing (ChatGPT: strategy, Claude: code, Gemini: research).

Full guide: [docs/second-brain.md](../docs/second-brain.md) & [skills/second-brain/SKILL.md](second-brain/SKILL.md)

---

### 4. flowkit-ai-filmmaker

**Purpose**: Plan, operate, and maintain the standalone FlowKit AI video application (FastAPI/SQLite agent, Chrome MV3 bridge, React dashboard, and FFmpeg post-processing).

**When to use**:
- Running the documented video-production workflow for Shorts, Reels, YouTube, or commercial content.
- Creating and reviewing projects, reference images, scene images, clips, narration, and final exports.
- Diagnosing Google Flow, extension, or pipeline issues; modifying FlowKit code under `flowkit/`.

Character references can improve visual continuity but do not guarantee identical outputs; supported chaining depends on the selected model and current Flow API.

Implementation: [flowkit/](../flowkit/) — standalone FlowKit agent, extension, dashboard, tests, and workflow guides. Start here: [docs/FLOWKIT_INTEGRATION.md](../docs/FLOWKIT_INTEGRATION.md).

Full guide: [skills/flowkit-ai-filmmaker/SKILL.md](flowkit-ai-filmmaker/SKILL.md) & [memory/flowkit-ai-filmmaking.md](../memory/flowkit-ai-filmmaking.md)

---

## Skill Development Guidelines

Each skill should:
- Have a clear, single responsibility
- Include distinct workflow phases
- Specify when and when-not to use it
- Provide safety guardrails and stop conditions
- Define what "done" means
- Support validation and reproducibility
