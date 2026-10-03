# FlowKit integrated into ZEUS

FlowKit is maintained in this repository as a self-contained subproject at `flowkit/`. Its Python agent, browser extension, dashboard, skills, docs, and tests stay under that directory; FlowKit's Python and Node dependencies are not added to the ZEUS/Hermes runtime.

## What is included

- `flowkit/agent/` — FastAPI service, SQLite persistence, and video-generation pipeline.
- `flowkit/extension/` — Chrome Manifest V3 bridge for a signed-in Google Flow tab.
- `flowkit/dashboard/` — React/Vite operations dashboard.
- `flowkit/skills/` and `flowkit/.claude/commands/` — FlowKit-specific agent workflows.
- `flowkit/tests/` — Python unit and extension regression tests.
- `flowkit/LICENSE` — original MIT license and attribution.

The imported snapshot is from `ZeusopenAI/flowkit` (`main`, commit `d7977fd51b87d4da2a25a05b896f5cdac064e030`). The commit is also recorded in `flowkit/.quang-quy-source-commit`. This is a vendored snapshot, not a submodule; future FlowKit changes belong in `flowkit/` in ZEUS.

## Quick start

Prerequisites: Python 3.10+, FFmpeg/ffprobe, Chrome, and a Google account with access to Flow. Node.js is only needed for the dashboard build.

Run the setup from the subproject directory so its virtual environment and runtime files stay inside `flowkit/`:

```bash
cd flowkit
./setup.sh
export FLOW_PROJECT_ID="<UUID of a project created in Google Flow>"
source venv/bin/activate
python -m agent.main
```

Then:

1. Open `https://flow.google.com/` in Chrome and sign in; leave the tab open.
2. In `chrome://extensions`, enable Developer mode and load the unpacked `flowkit/extension/` directory.
3. Open `http://127.0.0.1:8100/health` and confirm the agent is healthy and the extension is connected.
4. See [`flowkit/README.md`](../flowkit/README.md), [`flowkit/CLAUDE.md`](../flowkit/CLAUDE.md), and the `/fk-*` guides under `flowkit/skills/` for workflows and API details.

Google Flow projects must be created in the Flow UI and selected with `FLOW_PROJECT_ID`; FlowKit does not create them through the current API. Do not commit API keys, browser cookies, tokens, or `.env` files.

### Dashboard

With the agent running, start the dashboard in a separate terminal:

```bash
cd flowkit/dashboard
npm ci
npm run dev
```

The Vite dev server proxies API and WebSocket requests to the local agent on port `8100`. For a production build, run `npm run build` from `flowkit/dashboard/`.

## Validation

From the repository root, run the relevant checks:

```bash
python -m pip install -r flowkit/requirements.txt -r flowkit/requirements-dev.txt
python -m pytest flowkit/tests/unit -q
node --test flowkit/tests/extension_mv3_bootstrap.test.cjs
npm ci --prefix flowkit/dashboard
npm run build --prefix flowkit/dashboard
```

The root workflow `.github/workflows/flowkit-ci.yml` runs the Python, extension, and dashboard checks when FlowKit files change.

## Security note

The imported snapshot omits a hard-coded Google API-key-shaped value found in the upstream extension and planning notes. The extension declaration was unused by the current Flow batch transport. Treat the old value as exposed if it was real: revoke/rotate it in Google Cloud. Deleting the old GitHub repository does not revoke credentials or remove copies from existing clones and caches.
