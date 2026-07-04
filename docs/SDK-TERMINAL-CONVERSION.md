# SDK / Terminal Conversion Plan

The app should not require paid API calls for every crew interaction. API mode
should become optional in settings. The preferred public path is to run model
traffic through a local terminal/CLI bridge when available.

## Goals

- Reduce API cost.
- Let users run through an existing terminal Claude/Codex-style session.
- Keep API mode available for users who want it.
- Let each station choose a provider/mode.
- Preserve streaming responses and tool behavior.
- Keep demo mode for no-key/no-CLI installs.

## Modes

### Demo

No API key and no terminal bridge.

- Canned responses.
- Limited autonomy.
- Safe for first launch.

### API

Current behavior.

- Uses Anthropic SDK/API directly.
- Requires `ANTHROPIC_API_KEY`.
- Best reliability and tool-call structure.
- Expensive if autonomy is active.

### Terminal Bridge

Target cost-saving mode.

- Backend sends prompts to a local terminal process.
- Terminal process runs the model CLI/SDK session.
- Backend captures streamed text and routes it to the ship UI.
- Tool calls may need a simple text protocol rather than native SDK tool blocks.

### Hybrid

Per-station mode selection.

- Bridge/Lumen: terminal
- Engineering: API or terminal with tools
- Autonomy ticks: demo/cheap model/off
- Holodeck: terminal or API

## Settings UI

Add a neutral provider section:

- Response Engine: Demo, Terminal, API
- API Key status: detected/not detected
- Terminal command
- Working directory
- Per-crew overrides
- Autonomy model mode

API should be optional, not presented as required.

## Backend Abstraction

Introduce a provider interface:

```python
class ModelProvider:
    async def stream_chat(self, *, crew_id, system, messages, tools=None):
        yield {"type": "text", "text": "..."}
        yield {"type": "tool_use", "name": "...", "input": {...}}
```

Implement:

- `AnthropicProvider`
- `TerminalProvider`
- `DemoProvider`

Then route all chat through a provider selector instead of calling
`anthropic_client.messages.create(...)` directly throughout `server.py`.

## Terminal Bridge Protocol

First version can be intentionally simple:

Backend writes to process stdin:

```text
--- CLAUDE HUB REQUEST ---
CREW: server
SYSTEM:
...
MESSAGES:
...
--- END REQUEST ---
```

Process stdout returns:

```text
--- CLAUDE HUB RESPONSE ---
text...
--- END RESPONSE ---
```

Later tool protocol:

```text
[[tool:read_file {"path":"README.md"}]]
```

Backend executes allowed tools, then sends:

```text
[[tool_result:<id> ...]]
```

This is less elegant than native SDK tool use, but portable.

## Migration Steps

1. Inventory all direct Anthropic calls.
2. Create provider interface and `AnthropicProvider`.
3. Move existing chat path to provider without behavior change.
4. Add `DemoProvider`.
5. Add settings storage for provider mode.
6. Add `TerminalProvider` for simple text-only streaming.
7. Add terminal tool protocol for Engineering.
8. Route autonomy/dream/desire calls through provider selectors.
9. Add per-room/per-crew provider overrides.
10. Add cost controls for autonomy tick rate and background calls.

## Direct Anthropic Call Sites To Convert

Likely files:

- `backend/server.py`
- `backend/autonomy.py`
- `backend/autonomy_handler.py`
- `backend/background_crew.py`
- `backend/crew_threads.py`
- `backend/desire_system.py`
- `backend/dream_system.py`
- `backend/engineering_handler.py`
- `backend/room_adventure.py`
- `backend/spark_handler.py`

Use `rg "anthropic_client|messages.create|Anthropic"` before starting.

## Cost Controls

- Autonomy off by default for API mode.
- Background crew disabled or low-frequency by default in API mode.
- Dream generation should batch or defer.
- Use cheap/small model for ambient ticks.
- Make terminal mode the visible recommendation when detected.

## Open Questions

- Which terminal CLI should be the first supported target?
- Should terminal sessions be one process per crew or one shared process?
- How should long-running terminal processes recover after crashes?
- How much structured tool calling is required for v1?
- Should API and terminal modes share conversation memory or keep separate logs?

## Non-Goals For First Pass

- Perfect native SDK parity.
- Hosted multi-user deployment.
- Full tool-use protocol for every room.
- Automatic installation of external CLIs.
