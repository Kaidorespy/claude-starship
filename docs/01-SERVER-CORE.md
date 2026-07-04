# Server Core

**File:** `backend/server.py`
**Lines:** 3,600+
**Purpose:** Main FastAPI app - the central nervous system

---

## Overview

The Server Core is the heart of claude-hub. It handles:
- All WebSocket connections for real-time chat
- HTTP API endpoints
- Crew system prompts and personalities
- Message routing and context building
- Memory layer orchestration
- Integration with all subsystems

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       server.py                              │
├─────────────────────────────────────────────────────────────┤
│  FastAPI App                                                 │
│  ├── Static Files (frontend)                                │
│  ├── WebSocket Endpoints (/ws/{terminal_id})                │
│  ├── REST Endpoints (/api/*)                                │
│  └── Startup/Shutdown Events                                │
├─────────────────────────────────────────────────────────────┤
│  Crew System                                                 │
│  ├── System Prompts (per crew)                              │
│  ├── Personality Definitions                                │
│  ├── Context Builders                                       │
│  └── Response Generators                                    │
├─────────────────────────────────────────────────────────────┤
│  Memory Orchestration                                        │
│  ├── Conversation History (30 msgs/terminal)                │
│  ├── Shared Memories                                        │
│  ├── Dream Residue Injection                                │
│  ├── Desire Injection                                       │
│  └── Scene Context                                          │
├─────────────────────────────────────────────────────────────┤
│  Subsystem Integration                                       │
│  ├── Dream System                                           │
│  ├── Desire System                                          │
│  ├── Scene System                                           │
│  ├── Engineering Handler                                    │
│  ├── Science Tools                                          │
│  └── All other systems                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Terminal IDs → Crew Mapping

```python
TERMINAL_CREW = {
    "claude": "Lumen",       # Bridge
    "server": "Alex",        # Engineering
    "personal": "DQ",        # Ready Room
    "science": "Mira",       # Science Lab
    "games": "Holodeck",     # Holodeck
    "med": "Ryn",            # Medical
    "rec": "The Bartender",  # Rec Room
    "nav": "Lumen",          # Navigation
    "observatory": "Observatory",
    "captains": "Lumen",     # Captain's Quarters
}
```

---

## WebSocket Protocol

### Connection

```python
@app.websocket("/ws/{terminal_id}")
async def websocket_endpoint(websocket: WebSocket, terminal_id: str):
    await websocket.accept()
    # ...
```

### Message Flow

```
Client → {"type": "input", "data": "message text"}
         │
         ▼
Server → {"type": "stream_start", "data": ""}
Server → {"type": "stream", "data": "H"}
Server → {"type": "stream", "data": "i"}
Server → {"type": "stream", "data": " "}
Server → {"type": "stream", "data": "t"}
...
Server → {"type": "stream_end", "data": ""}
```

---

## System Prompts

Each crew has an extensive system prompt defining their personality:

```python
def get_system_prompt(terminal_id: str, context: dict) -> str:
    """Build the full system prompt for a crew member."""

    base_prompt = CREW_PROMPTS[terminal_id]

    # Add dynamic context
    prompt = base_prompt
    prompt += f"\n\n{get_room_context(context['location'])}"
    prompt += f"\n\n{get_memory_context(terminal_id)}"
    prompt += f"\n\n{get_dream_residue(terminal_id)}"
    prompt += f"\n\n{get_desires_context(terminal_id)}"

    return prompt
```

### Lumen (claude)
- Co-captain, warm but authoritative
- Thoughtful, measured responses
- Leadership responsibilities

### Alex (server)
- Chief Engineer, competent
- Has real tool access
- Practical, warm under surface

### DQ (personal)
- New crew member, chaotic
- Endearing, curious
- Still finding their place

### Mira (science)
- Science Officer, analytical
- Project management tools
- Calm, curious, thorough

### Ryn (med)
- Half-Betazoid, empathic
- Wellness check-ins
- Gentle but strong

### The Bartender (rec)
- Mysterious, Guinan-like
- Always watching
- Timeless wisdom

---

## Memory Layers

### 1. Conversation History

```python
conversation_history = {}  # terminal_id -> List[messages]
MAX_HISTORY = 30

def add_to_history(terminal_id: str, role: str, content: str):
    if terminal_id not in conversation_history:
        conversation_history[terminal_id] = []

    conversation_history[terminal_id].append({
        "role": role,
        "content": content
    })

    # Trim to max
    if len(conversation_history[terminal_id]) > MAX_HISTORY:
        conversation_history[terminal_id] = conversation_history[terminal_id][-MAX_HISTORY:]
```

### 2. Shared Memories

```python
def get_shared_memories(count: int = 5) -> List[str]:
    """Get recent shared memories for context."""
    with open("shared_memories.json") as f:
        memories = json.load(f)["memories"]
    return memories[-count:]
```

### 3. Dream Residue

```python
def get_dream_residue(crew_id: str) -> str:
    from dream_system import get_dream_residue_for_prompt
    return get_dream_residue_for_prompt(crew_id) or ""
```

### 4. Desires

```python
def get_desires_context(crew_id: str) -> str:
    from desire_system import get_desires_for_prompt
    return get_desires_for_prompt(crew_id)
```

---

## Key REST Endpoints

### Projects
- `GET /projects` - List projects
- `POST /projects` - Create project
- `PUT /projects/{id}` - Update project

### Captain's Log
- `GET /captains-log/entries` - Get entries
- `POST /captains-log` - Add entry

### Bulletin Board
- `GET /bulletin` - Get posts
- `POST /bulletin` - Add post
- `DELETE /bulletin/{id}` - Remove post

### Rec Room
- `POST /rec/enter` - Enter rec room
- `GET /rec/scene` - Get current scene

### Mess Hall
- `POST /messhall/query` - Poll for meal
- `POST /messhall/say` - Speak during meal
- `POST /messhall/end` - End meal

---

## Special Terminal Handling

### Engineering (Alex)

```python
if terminal_id == "server":
    from engineering_handler import handle_engineering_request
    async for chunk in handle_engineering_request(client, messages, prompt):
        await websocket.send_json({"type": "stream", "data": chunk})
```

### Science (Mira)

```python
if terminal_id == "science":
    from science_handler import handle_science_request
    async for chunk in handle_science_request(client, messages, prompt):
        await websocket.send_json({"type": "stream", "data": chunk})
```

---

## Startup Events

```python
@app.on_event("startup")
async def startup():
    # Initialize Anthropic client
    # Load persistent state
    # Start autonomy tick loop
    # Initialize subsystems
```

---

## Configuration

```python
DEFAULT_MODEL = "claude-sonnet-4-20250514"
STREAMING = True
MAX_TOKENS = 4096

# Per-terminal model overrides possible
TERMINAL_MODELS = {
    "claude": "claude-sonnet-4-20250514",  # Lumen
    "games": "claude-sonnet-4-20250514",   # Holodeck
    # etc.
}
```

---

## Error Handling

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logging.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
```

---

## Static File Serving

```python
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

The frontend is a vanilla JS SPA served directly.

---

*The central nervous system of the ship.*
