# Claude Hub Development Notes

Claude Hub is a local-first FastAPI + vanilla JavaScript app for a narrative
spaceship command center with persistent AI crew, rooms, memories, autonomy,
and tools.

## Public Repository Rules

- Do not commit `.env`, API keys, local paths, conversation logs, checkpoints,
  generated project work, or player-specific runtime data.
- Runtime data belongs in `./data` by default, or in the directory set by
  `CLAUDE_HUB_DATA_DIR`.
- Public seed data belongs in `backend/default_data`.
- Backend code should use `backend.paths.data_path("file.json")` for writable
  JSON state.
- Keep distribution mode concerns separate from the private local trust model.

## Running Locally

```powershell
python run.py
```

Or:

```powershell
cd backend
uvicorn server:app --host 0.0.0.0 --port 8767
```

Open `http://localhost:8767`.

## Architecture

- `backend/server.py`: FastAPI app, WebSocket chat, REST routes, static serving.
- `backend/*_system.py`: autonomy, dreams, desires, rooms, memories, tools.
- `frontend/index.html`: single-page ship interface.
- `frontend/js/config.js`: backend URL configuration.
- `frontend/js/terminals.js`: WebSocket terminal/chat handling.
- `frontend/js/main.js`: room navigation and main UI orchestration.
- `backend/default_data`: clean public seed JSON.
- `data`: ignored local/player state.

## Release Checklist

Before publishing:

```powershell
python -m compileall backend
python - <<'PY'
from fastapi.testclient import TestClient
from backend.server import app
client = TestClient(app)
for path in ["/health", "/inbox/summary", "/threads/ready"]:
    r = client.get(path)
    print(path, r.status_code, r.text[:200])
PY
rg -n "sk-ant|api[_-]?key|secret|token|password|C:\\\\Users" -S .
git status --short
```

Review any remaining hits manually. Some words such as `token` may appear in
sample schemas or docs and are not automatically sensitive.
