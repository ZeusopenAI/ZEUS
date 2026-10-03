---
name: flowkit-ai-filmmaker
description: Plan, operate, and maintain the FlowKit AI video pipeline integrated in ZEUS.
license: MIT-compatible synthesized workflow
---

# FlowKit AI Filmmaker Skill

## Mission

Help create and operate AI video projects with the FlowKit application in `flowkit/`. FlowKit is a standalone ZEUS subproject: a FastAPI/SQLite agent, Chrome Manifest V3 bridge to Google Flow, React dashboard, FFmpeg post-processing, and reusable workflow guides. It does not require the Hermes runtime.

- Integration and setup guide: [docs/FLOWKIT_INTEGRATION.md](../../docs/FLOWKIT_INTEGRATION.md)
- FlowKit application docs: [flowkit/README.md](../../flowkit/README.md) and [flowkit/CLAUDE.md](../../flowkit/CLAUDE.md)
- Canonical command recipes: [flowkit/skills/](../../flowkit/skills/)
- Imported upstream revision: [flowkit/.quang-quy-source-commit](../../flowkit/.quang-quy-source-commit)

## Pre-flight

Before running a generation workflow:

1. Read the matching recipe under `flowkit/skills/` and follow its prerequisites.
2. Confirm the FlowKit agent is healthy at `http://127.0.0.1:8100/health` and the Chrome extension is connected.
3. Keep a Google Flow tab open in Chrome while the signed-in session is active.
4. Configure `FLOW_PROJECT_ID` with a project created in the Flow UI. The current Flow transport does not create projects itself.
5. Never expose API credentials, cookies, browser tokens, or `.env` values in prompts, logs, or commits.

If a request is to change FlowKit code rather than operate it, work inside `flowkit/` and read `flowkit/AGENTS.md` first. Keep generated projects, media, database files, and local configuration out of Git.

## Workflow overview

```text
Research / brief
  → create project, entities, video and scenes
  → generate entity reference images
  → generate scene images
  → generate videos (optionally chain supported models)
  → review clips and fix issues before final assembly
  → narration / music / optional overlays
  → concat and export
```

Treat reference images as a consistency aid, not a guarantee of identical results. Confirm every generated asset and user-approved prompt before publishing.

## Prompt rules

### Entities and reference images

Describe stable appearance only: facial features, clothing, colors, materials, and other visual traits. Keep actions, camera movements, and story events out of entity descriptions.

### Scene prompts

Describe the action and composition, and refer to established entities by name. Do not copy the full appearance description into every scene. Keep sensitive or factual real-world claims accurate and sourced; distinguish fictionalized or editorial material from fact.

### Continuity

Use the recipe for the chosen model and the supported scene-chain mode. On the current Flow batch API, Veo start+end-frame chaining is not supported and should fail visibly; Omni first+last modes may be used where supported. `FLOW_ALLOW_DEGRADED=1` changes behavior by allowing a fallback and must not be enabled silently.

## Available workflow skills

Use the matching canonical recipe in `flowkit/skills/`:

| Command | Purpose |
|---|---|
| `/fk-research` | Research and fact-check a story brief |
| `/fk-create-project` | Create the project, entities, video, and scenes |
| `/fk-gen-refs` | Generate entity reference images |
| `/fk-gen-images` | Generate scene images |
| `/fk-gen-videos` | Generate scene videos |
| `/fk-gen-chain-videos` | Generate supported chained-video sequences |
| `/fk-review-video` | Review generated clips and address issues |
| `/fk-gen-narrator` / `/fk-gen-tts-template` | Prepare narration and voice templates |
| `/fk-gen-music` | Generate or attach music |
| `/fk-concat` / `/fk-concat-fit-narrator` | Assemble scene videos, optionally fit to narration |
| `/fk-pipeline` | Orchestrate the documented end-to-end workflow |
| `/fk-thumbnail` / `/fk-youtube-seo` / `/fk-youtube-upload` | Prepare publication assets and upload when explicitly approved |
| `/fk-doctor` | Diagnose Flow, extension, worker, or pipeline errors |

The skills are recipes, not authorization to publish content or incur third-party costs. Ask before uploading, publishing, or using a paid service.

## Definition of done

- All requested scenes/assets are accounted for and reviewed.
- The final video is assembled in the requested aspect ratio and checked for audio, timing, captions/overlays, and continuity.
- Any remaining unsupported model capability or degraded fallback is disclosed.
- No secrets, browser session data, or generated private media are committed to the repository.
