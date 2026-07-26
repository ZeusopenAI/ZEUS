---
name: facebook-growth-ops
description: Plan, validate, and measure original Facebook content for Quang Quý AI without bypassing platform restrictions.
---

# Facebook Growth Operations

Use this skill when Quý asks Hermes to continue, plan, check, or improve the Facebook Lead & Monetization OS.

## Procedure

1. Run `python tools/facebook_monetization_os.py validate` from repository root.
2. Read `ops/facebook-monetization/state.json`; report every integration not verified.
3. Create the daily brief with `daily-brief --date YYYY-MM-DD`. Store an optional local copy only in `runs/`.
4. Prepare production assets as drafts with a real demo, original voice/face/screen recording, and an explicit CTA.
5. If the Publish API, Insights API, Notion, or Drive connectors are missing, stop at the matching handoff and record it. Do not invent URLs, metrics, posts, uploads, or API results.
6. After official connections are verified, record post URL, asset URL, 24h/72h metrics, and lead quality before recommending a new content rule.

## Non-negotiable boundaries

- `DRAFT_ONLY` means no public posting.
- Instagram-to-Facebook personal-profile cross-posting is never an automation target.
- Do not submit Meta reviews/appeals or change payout details.
- Do not use unofficial browser automation, cookies, or account-session scraping.
- Never declare that monetization/payout is restored without direct Meta evidence.
