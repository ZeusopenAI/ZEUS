# Hermes integration in Quang Quy AI

Hermes is vendored under `agents/hermes/` as the orchestration runtime for Quang Quy AI.

## Source

- History-preserving subtree source: `qquy28888-ops/hermes-agent`, branch `main`
- Exact integrated revision: `agents/hermes/.quang-quy-source-commit`
- The source commit and its ancestry are reachable from the Quang Quy AI history.
- The original Hermes license and attribution files remain inside `agents/hermes/`.

## Security rules

- Never commit `.env`, API keys, OAuth tokens, cookies, private keys, or service-account JSON.
- Runtime secrets must be stored in VPS environment variables, GitHub Actions Secrets, or an approved secret manager.
- `.env.example` may contain variable names and placeholders only.
- Rotate any credential that was ever committed, even if it was later deleted.

## Deployment model

Production target: VPS Ubuntu + Hermes Gateway + Telegram. GitHub stores code and CI/CD; it does not host the always-on Hermes process.

## Updating Hermes

Run `scripts/update-hermes-subtree.sh` from a clean integration branch, review the history-preserving subtree commits, run tests, and open a pull request. Do not update `main` or production directly from the source repository.
