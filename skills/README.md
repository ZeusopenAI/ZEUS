# Skills

Reusable project skills for the Quang Quý AI repository.

## Hermes Project Analyst & Code Manager

Path: `skills/hermes-project-analyst-code-manager/SKILL.md`

Use this skill when diagnosing, repairing, validating, or preparing code changes for the Hermes agent. It prioritizes root-cause analysis, minimal safe changes, secret protection, test evidence, and explicit Git change management.

### Core principles

- Preserve the existing `quangquy-ai` architecture unless a change is explicitly justified.
- Reproduce failures before changing code whenever practical.
- Separate evidence from hypotheses.
- Prefer the smallest reversible fix that addresses the proven root cause.
- Never print, commit, or expose API keys, tokens, cookies, or other credentials.
- Review the complete diff before committing.
- Validate changed behavior and relevant regression paths before declaring completion.
- Do not merge or rewrite protected history without explicit approval.

### Typical prompts

- Diagnose a Hermes runtime/provider failure.
- Trace an authentication or configuration problem.
- Patch Hermes with the minimum safe change.
- Review a Hermes PR and failing checks.
- Validate a repair before merge.
