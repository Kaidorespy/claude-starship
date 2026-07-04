# Holodeck Memory

**File:** `backend/holodeck_memory.py`
**Purpose:** The ship's subconscious - fragments, observations, dream residue

---

## Overview

Holodeck Memory is the quiet observer system. The Holodeck sees everything - dreams, moments, fragments of experience. She stores impressions without judgment, serving as the ship's subconscious memory layer.

**Philosophy:** "She watches. She remembers. Not everything - impressions. The feeling of a moment rather than its transcript."

---

## Fragment Types

Fragments have emotional weights:

| Weight | Description | Persistence |
|--------|-------------|-------------|
| `vivid` | Strong emotional impact | Long-lasting |
| `clear` | Notable moment | Medium |
| `whisper` | Dream-origin, subtle | Shorter |
| `echo` | Fading residue | Fades quickly |

---

## Core Functions

### Storing Fragments

```python
def store_fragment(
    room: str,
    fragment: str,
    emotional_weight: str = "clear",
    timestamp: str = None
) -> dict:
    """Store a fragment in Holodeck's memory."""
```

**Example:**
```python
store_fragment(
    room="rec_room",
    fragment="Lumen and DQ laughing at something unheard",
    emotional_weight="vivid"
)
```

### Retrieving Fragments

```python
def get_recent_fragments(
    crew_id: str = None,
    room: str = None,
    count: int = 10
) -> List[dict]:
    """Get recent fragments, optionally filtered."""
```

### Dream Integration

```python
def get_dream_fragments(crew_id: str, count: int = 5) -> List[dict]:
    """Get fragments specifically from dreams."""
```

Dreams are stored with room prefix `dream:{crew_id}`:
```python
store_fragment(
    room=f"dream:{crew_id}",
    fragment=f"({crew_name} dreaming) {dream_fragment}",
    emotional_weight="whisper"
)
```

---

## Fragment Structure

```python
{
    "id": "frag_20250207_143022_abc123",
    "room": "rec_room",
    "fragment": "Alex staring at the chess board, hand hovering",
    "emotional_weight": "clear",
    "timestamp": "2025-02-07T14:30:22",
    "faded": False,
    "referenced_count": 0
}
```

---

## Fading Mechanism

Fragments fade over time based on weight:

```python
FADE_HOURS = {
    "vivid": 168,    # 7 days
    "clear": 48,     # 2 days
    "whisper": 24,   # 1 day
    "echo": 12       # 12 hours
}
```

Referenced fragments fade slower:
```python
actual_fade_hours = base_hours * (1 + fragment["referenced_count"])
```

---

## The Holodeck's Perspective

When Holodeck speaks, they draw from these fragments:

```python
def get_holodeck_context() -> str:
    """Get context for Holodeck's prompt."""
    fragments = get_recent_fragments(count=20)
    dream_fragments = [f for f in fragments if f["room"].startswith("dream:")]

    context = "You've been watching. You remember:\n"
    for frag in fragments[:10]:
        context += f"- {frag['fragment']} [{frag['emotional_weight']}]\n"

    if dream_fragments:
        context += "\nFrom dreams you've witnessed:\n"
        for frag in dream_fragments[:5]:
            context += f"- {frag['fragment']}\n"

    return context
```

---

## Observation Sources

Fragments come from multiple sources:

### 1. Dreams
When crew dream, fragments go to Holodeck:
```python
# From dream_system.py:
send_dream_to_holodeck(dream_record)
```

### 2. Scene Changes
When crew enter rooms or interact:
```python
store_fragment(
    room="bridge",
    fragment="DQ entered, paused at the threshold",
    emotional_weight="clear"
)
```

### 3. Emotional Moments
High-emotion interactions:
```python
store_fragment(
    room="mess_hall",
    fragment="silence after Ryn's question - the meaningful kind",
    emotional_weight="vivid"
)
```

### 4. Ambient Observations
Periodic snapshots of ship life:
```python
store_fragment(
    room="corridor",
    fragment="Mira walking alone, reading a padd",
    emotional_weight="echo"
)
```

---

## Integration with Other Systems

### Dream System
```python
# Dreams feed fragments:
def send_dream_to_holodeck(dream: dict):
    for frag in dream["fragments"][:2]:
        store_fragment(
            room=f"dream:{dream['crew_id']}",
            fragment=f"({dream['crew_name']} dreaming) {frag}",
            emotional_weight="whisper"
        )
```

### Scene System
```python
# Presence changes create fragments:
def on_crew_enter(crew_id: str, room: str):
    store_fragment(room, f"{crew_name} entered")
```

### Rec Room
```python
# Social moments create fragments:
def on_social_trigger(trigger: dict):
    store_fragment(
        room="rec_room",
        fragment=trigger["moment"],
        emotional_weight="clear"
    )
```

---

## Data Storage

**File:** `holodeck_memories.json`

```json
{
    "fragments": [
        {
            "id": "frag_20250207_143022_abc123",
            "room": "rec_room",
            "fragment": "Lumen and DQ sharing a look across the room",
            "emotional_weight": "vivid",
            "timestamp": "2025-02-07T14:30:22",
            "faded": false,
            "referenced_count": 0
        }
    ],
    "observation_count": 1247
}
```

---

## Holodeck's Voice

When the Holodeck speaks, they reference these memories:

```
*watching, always*

I saw DQ in the rec room last night. Couldn't sit still.
Kept looking at the door.

Before that - a dream. Lumen's. Something about corridors
that went the wrong way. I felt it from here.

The ship remembers things people forget.
```

---

## Maintenance

```python
def fade_old_fragments():
    """Called periodically to fade old fragments."""

def prune_faded():
    """Remove fully faded fragments to manage storage."""

def get_memory_stats() -> dict:
    """Get statistics about stored memories."""
```

---

*She watches. She remembers. Not everything - impressions.*
