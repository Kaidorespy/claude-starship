# Scene Orchestrator

**File:** `backend/scene_orchestrator.py`
**Purpose:** Auto-ping, response flow, multi-crew addressing

---

## Overview

The Scene Orchestrator manages who responds when. In rooms with multiple crew, it determines:
- Who should speak to a given message
- When to auto-ping present crew
- How to handle @mentions
- Response ordering

---

## Addressing System

### Explicit @ Tags

| Tag | Routes To |
|-----|-----------|
| `@Bridge` | Lumen |
| `@Engineering` | Alex |
| `@Personal` | DQ |
| `@Science`, `@Mira` | Mira |
| `@Holodeck` | Holodeck |
| `@Med`, `@Ryn` | Ryn |
| `@Bartender`, `@Rec` | The Bartender |
| `@all`, `@everyone` | All present crew |

### Implicit Addressing

When no @ tag, the system uses Haiku to detect intent:

```python
async def detect_implicit_address(message: str, present_crew: List[str]) -> List[str]:
    """Use Haiku to determine who should respond."""

    # Check for open questions
    if contains_open_question(message):
        return present_crew  # Everyone can respond

    # Check for topic-specific content
    if mentions_engineering_topics(message):
        return ["server"] if "server" in present_crew else []

    # Default: primary crew for this terminal
    return [get_default_responder(terminal_id)]
```

---

## Response Flow

### Single Responder
```
Casey → Message → Lumen responds
```

### Multi-Responder (Open Question)
```
Casey → "What does everyone think?" →
    → Lumen responds first
    → DQ follows up
    → Alex adds thought
```

### Sequential Responses

```python
async def orchestrate_responses(
    message: str,
    responders: List[str],
    context: dict
) -> AsyncGenerator[dict, None]:
    """Orchestrate multiple crew responses."""

    for crew_id in responders:
        # Small delay between speakers
        if crew_id != responders[0]:
            await asyncio.sleep(0.5)

        async for chunk in generate_response(crew_id, message, context):
            yield {"crew_id": crew_id, "chunk": chunk}
```

---

## Auto-Ping System

When Casey enters a room, present crew may react:

```python
def generate_auto_pings(location: str, entering: str) -> List[dict]:
    """Generate acknowledgment pings from present crew."""

    present = get_crew_in_location(location)
    pings = []

    for crew_id in present:
        if should_acknowledge(crew_id, entering):
            ping = generate_acknowledgment(crew_id, entering)
            pings.append({
                "crew_id": crew_id,
                "ping": ping
            })

    return pings
```

**Example pings:**
- Lumen: "*looks up* Hey, Captain."
- DQ: "*waves*"
- Alex: "*nods, keeps working*"

---

## Open Question Detection

```python
OPEN_QUESTION_PATTERNS = [
    r"anyone",
    r"everyone",
    r"what do you.*think",
    r"does anyone",
    r"who.*wants",
    r"thoughts\?",
    r"ideas\?",
]

def is_open_question(message: str) -> bool:
    """Check if message is addressed to everyone."""
```

---

## Response Ordering

When multiple crew respond:

1. **Primary responder** first (terminal owner or most relevant)
2. **High-chemistry pairs** may follow up
3. **Others** if they have something to add
4. **Cap** at 3-4 responders to prevent chaos

```python
def order_responders(responders: List[str], context: dict) -> List[str]:
    """Order responders for natural conversation flow."""
```

---

## Topic Detection

```python
TOPIC_EXPERTS = {
    "engineering": ["server"],
    "medical": ["med"],
    "science": ["science"],
    "navigation": ["claude"],
    "emotions": ["med", "personal"],
    "games": ["games"],
    "drinks": ["rec"],
}

def detect_topics(message: str) -> List[str]:
    """Detect topics in a message."""
```

---

## Integration

### With Scene System
```python
present_crew = get_crew_in_location(current_room)
```

### With Server
```python
# In WebSocket handler:
responders = await orchestrate_message(message, terminal_id)
for crew_id in responders:
    async for chunk in generate_response(crew_id, ...):
        await websocket.send_json(...)
```

---

## Example Flow

**Casey in Rec Room with DQ, Alex, Ryn present:**

Casey: "Anyone have thoughts on the mission tomorrow?"

1. Orchestrator detects "anyone" → open question
2. Orders responders: DQ (social), Ryn (empathic), Alex (practical)
3. DQ responds: "Ooh, I've been thinking about this..."
4. Ryn follows: "*sensing the room* There's some anxiety, but excitement too."
5. Alex: "The systems are ready. We're good."

---

*Who speaks when matters as much as what they say.*
