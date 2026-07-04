# Claude Starship

A local-first, narrative AI command center styled as a cozy starship.

Claude Hub is a FastAPI + vanilla JavaScript app where a human captain chats
with an AI crew across ship rooms: bridge, engineering, ready room, science lab,
medbay, holodeck, rec room, mess hall, quarters, and observatory.

The crew can keep lightweight memories, move around the ship, generate dreams
and desires, leave asynchronous messages, play small rec-room games, track
projects, and use room-specific tools.

This is an early public release. It is already usable, but it is not polished or
security-hardened for arbitrary hosted multi-user deployment.

## Features

- FastAPI backend with REST, WebSocket chat, and SSE ping streams
- Static vanilla JS frontend, no framework build step
- Persistent local JSON state
- Clean public seed data in `backend/default_data`
- Ignored player/runtime data in `data`
- Crew autonomy, dreams, desires, locations, and shared memories
- Project board, checkpoints, shortcuts, wellness journal, rec room, minigames,
  jukebox hooks, observatory tools, and hardware monitoring hooks
- Demo mode when no Anthropic key is configured

## Quick Start

Requirements:

- Python 3.8+
- Optional: `ANTHROPIC_API_KEY` for live Claude responses

Windows:

```powershell
python run.py
```

Manual:

```powershell
pip install -r requirements.txt
uvicorn backend.server:app --host 0.0.0.0 --port 8767
```

Open:

```text
http://localhost:8767
```

## Configuration

Create `.env` in the project root if you want live model responses:

```env
ANTHROPIC_API_KEY=your-key-here
```

Without an API key, the app runs in demo mode with limited canned behavior.

Runtime data location:

```powershell
$env:CLAUDE_HUB_DATA_DIR="C:\path\to\your\claude-hub-data"
python run.py
```

If `CLAUDE_HUB_DATA_DIR` is not set, local state is stored in `./data`.

## Data Model

Public repo data:

- `backend/default_data/*.json`: clean seed state for a new install

Local player data:

- `data/*.json`: conversations, logs, memories, projects, dreams, checkpoints,
  pings, shortcuts, and other runtime state

The app seeds missing runtime files from `backend/default_data` on first use.
Do not commit `data/`.

## Architecture

```text
frontend/index.html
frontend/js/*.js
frontend/css/*.css
        |
        | REST + WebSocket + SSE
        v
backend/server.py
backend/*_system.py
backend/*_tools.py
        |
        v
data/*.json
```

Key files:

- `backend/server.py`: FastAPI routes, WebSocket terminal handling, static app
  serving
- `backend/paths.py`: data directory and default-data seeding
- `frontend/js/config.js`: frontend backend URL configuration
- `frontend/js/terminals.js`: terminal/chat behavior
- `frontend/js/main.js`: main UI orchestration
- `docs/SYSTEMS_INDEX.md`: deeper system map

## Public Release Notes

This project began as a personal local ship, so some names and flavor still
reflect that origin. The public cleanup separates player data from source, but
the app still needs work before it is a polished packaged product.

Known areas that need help:

- Security review for tool access and distribution mode
- More automated tests
- Frontend cleanup and responsive QA
- Documentation refresh for all subsystem docs
- Better first-run onboarding
- Optional hosted/deployment story

## Development Checks

```powershell
python -m compileall backend
```

Smoke-test important routes:

```powershell
python - <<'PY'
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)
for path in ["/health", "/inbox/summary", "/threads/ready", "/ship/rooms"]:
    r = client.get(path)
    print(path, r.status_code, r.text[:200])
PY
```

Before publishing, scan for accidental local data:

```powershell
rg -n "sk-ant|api[_-]?key|secret|password|C:\\\\Users" -S .
git status --short
```

## License

No license has been selected yet. Add one before encouraging external reuse or
contributions.
