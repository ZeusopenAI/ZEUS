# Hermes integration validation

This file records the validation scope for pull request #3.

- Verify the imported source commit and preserved license.
- Reject tracked `.env`, tokens, private keys, cookies, and credential files.
- Scan the imported tree for common Google, OpenAI, GitHub, AWS, Slack, Telegram, and private-key patterns.
- Parse `agents/hermes/pyproject.toml`.
- Compile Python sources without executing application code.
- Validate the update script syntax.
- Keep runtime secrets outside Git and Notion.

The repository is not considered production-ready until VPS deployment, Telegram Gateway, health checks, and rollback have been tested.
