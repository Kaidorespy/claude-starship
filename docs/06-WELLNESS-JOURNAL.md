# Wellness Journal

**File:** `backend/wellness_journal.py`
**Purpose:** Ryn's check-ins, reflection tracking

---

## Overview

The Wellness Journal system powers Ryn's empathic check-ins with crew (and Casey). It tracks emotional states over time, enables reflection prompts, and stores wellness entries.

---

## Check-In System

### Initiating Check-Ins

```python
def start_checkin(target_id: str, initiated_by: str = "med") -> dict:
    """Start a wellness check-in."""
```

Ryn can check in with:
- Casey (captain)
- Any crew member
- Herself (self-reflection)

### Check-In Questions

```python
CHECKIN_PROMPTS = {
    "general": [
        "How are you doing? Really.",
        "What's on your mind lately?",
        "Anything weighing on you?",
    ],
    "sleep": [
        "How did you sleep?",
        "Any dreams?",
        "Feeling rested?",
    ],
    "stress": [
        "I'm sensing some tension. Want to talk about it?",
        "You seem stressed. What's going on?",
    ],
    "joy": [
        "You seem lighter today. Something good happen?",
        "What's bringing you joy lately?",
    ]
}
```

### Recording Responses

```python
def record_checkin_response(
    target_id: str,
    response: str,
    emotional_state: str = None
) -> dict:
    """Record a check-in response."""
```

---

## Emotional State Tracking

### States

```python
EMOTIONAL_STATES = [
    "calm",
    "anxious",
    "happy",
    "sad",
    "stressed",
    "energized",
    "tired",
    "hopeful",
    "frustrated",
    "content"
]
```

### State Detection

```python
async def detect_emotional_state(
    anthropic_client,
    message: str
) -> str:
    """Use Haiku to detect emotional state from message."""
```

### State History

```python
def get_emotional_history(target_id: str, days: int = 7) -> List[dict]:
    """Get emotional state history."""
```

---

## Journal Entries

### Writing Entries

```python
def write_journal_entry(
    author_id: str,
    entry: str,
    private: bool = True
) -> dict:
    """Write a wellness journal entry."""
```

The `[WRITE: "entry"]` action tag triggers this.

### Reading Entries

```python
def get_journal_entries(
    author_id: str,
    count: int = 10
) -> List[dict]:
    """Get recent journal entries."""
```

---

## Reflection Prompts

Ryn can offer reflection prompts:

```python
REFLECTION_PROMPTS = [
    "What's one thing that went well today?",
    "What are you grateful for right now?",
    "What would you tell yourself a week ago?",
    "What do you need right now that you're not getting?",
    "When did you last feel truly at peace?",
]

def get_reflection_prompt() -> str:
    """Get a random reflection prompt."""
```

---

## Crew Wellness Overview

```python
def get_crew_wellness_overview() -> dict:
    """Get overall wellness status of crew."""
```

Returns:
- Recent check-ins per crew
- Detected stress levels
- Who might need attention

---

## Ryn's Empathic Sense

Ryn's half-Betazoid nature means she picks up on emotional states:

```python
def sense_room_emotion(location: str) -> str:
    """Ryn senses the emotional tenor of a room."""

    present = get_crew_in_location(location)
    emotions = []

    for crew_id in present:
        recent_state = get_recent_emotional_state(crew_id)
        if recent_state:
            emotions.append((crew_id, recent_state))

    return summarize_room_emotion(emotions)
```

**Example output:**
```
"There's some tension here. Alex is focused but stressed.
DQ is anxious about something. Lumen is... guarded."
```

---

## Integration with Dreams

Wellness check-ins can surface dream content:

```python
def get_dream_context_for_checkin(crew_id: str) -> str:
    """Get dream info for wellness context."""

    from dream_system import get_sleep_response_hint
    return get_sleep_response_hint(crew_id)
```

---

## Data Storage

**File:** `wellness_journal.json`

```json
{
    "checkins": [
        {
            "id": "checkin_20250207_143022",
            "target_id": "personal",
            "initiated_by": "med",
            "timestamp": "2025-02-07T14:30:22",
            "response": "I've been feeling a bit scattered...",
            "emotional_state": "anxious",
            "private": true
        }
    ],
    "journal_entries": [
        {
            "id": "journal_20250207_150000",
            "author_id": "personal",
            "entry": "Good talk with Ryn today...",
            "timestamp": "2025-02-07T15:00:00",
            "private": true
        }
    ],
    "emotional_history": {
        "personal": [
            {"state": "anxious", "timestamp": "..."},
            {"state": "calm", "timestamp": "..."}
        ]
    }
}
```

---

## Prompt Integration

Ryn's system prompt includes wellness context:

```python
def get_ryn_wellness_context() -> str:
    """Get context for Ryn's prompt."""

    context = "As the ship's medical officer, you're aware of:\n"

    # Recent check-ins
    recent = get_recent_checkins(days=3)
    if recent:
        context += f"- Recent check-ins: {len(recent)}\n"

    # Crew needing attention
    stressed = get_stressed_crew()
    if stressed:
        context += f"- Crew who might need attention: {stressed}\n"

    # Dream states
    for crew_id in CREW_IDS:
        dream_hint = get_sleep_response_hint(crew_id)
        if "nightmare" in dream_hint.lower():
            context += f"- {crew_id} had a rough night\n"

    return context
```

---

*Ryn holds space for the crew's inner lives.*
