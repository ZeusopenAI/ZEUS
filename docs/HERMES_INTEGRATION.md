# Hermes integration in Quang Quy AI

Hermes is vendored under `agents/hermes/` as the orchestration runtime for Quang Quy AI.

## Source

- Upstream snapshot: `qquy28888-ops/hermes-agent`, branch `main`
- Exact imported revision: `agents/hermes/.quang-quy-source-commit`
- The original Hermes license and attribution files remain inside `agents/hermes/`.

## Security rules

- Never commit `.env`, API keys, OAuth tokens, cookies, private keys, or service-account JSON.
- Runtime secrets must be stored in VPS environment variables, GitHub Actions Secrets, or an approved secret manager.
- `.env.example` may contain variable names and placeholders only.
- Rotate any credential that was ever committed, even if it was later deleted.

## Deployment model

Production target: VPS Ubuntu + Hermes Gateway + Telegram. GitHub stores code and CI/CD; it does not host the always-on Hermes process.

## Updating Hermes

Run `scripts/update-hermes-snapshot.sh` from a clean integration branch, review the diff, run tests, and open a pull request. Do not update production directly from upstream.
