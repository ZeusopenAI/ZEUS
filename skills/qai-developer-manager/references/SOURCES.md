# Upstream inspirations — QAI Developer Manager

This file records concepts studied and distilled. It is not a vendored copy of third-party prompts or source code.

## High-signal agent / engineering projects

- ByteDance DeerFlow 2.0 — progressive skill loading, lead-agent/sub-agent decomposition, sandboxing, memory, long-horizon workflows.
- FoundationAgents MetaGPT — role-based multi-agent software-company workflow and structured software-engineering collaboration.
- OpenBMB ChatDev — multi-agent collaboration for software development.
- FoundationAgents OpenManus — general agent harness patterns and tool/sandbox execution.
- wshobson/agents — portable multi-harness skills, agents, commands, orchestration, progressive disclosure, structural validation.
- Hugging Face skills — portable Agent Skills compatible with multiple coding harnesses.
- dsifry/metaswarm — spec-driven SDLC, TDD, review gates, adversarial review, PR shepherding.
- OpenCode — terminal-native coding-agent workflow and repository-level execution.
- Qwen Code — terminal coding agent + Agent Skills packaging.

## Hugging Face / software-engineering model research

- GAIR daVinci-Dev — agent-native software-engineering trajectories with repository context, sequential edits, and feedback-rich execution.
- Z.ai SWE-Dev — issue localization, test generation, repository-oriented training/evaluation and inference scaling.
- SwarmDo A1/A2 — execution-verified patch selection and self-checking agent workflows.

## Distilled principles used in this skill

1. Load only relevant skills/context for the current task.
2. Split complex work into scoped roles; do not let every agent edit the same file concurrently.
3. Treat tests and execution feedback as first-class evidence.
4. Prefer a staged loop: research -> plan -> implement -> validate -> adversarial review -> commit.
5. Preserve a rollback path and avoid secret leakage.
6. Separate upstream/provider failures from local application failures with direct probes.
7. Use CI as structural verification, but do not treat CI as proof of external live-service behavior unless live integration tests actually run.
8. For mobile/runtime work, distinguish build success from device/runtime success.
