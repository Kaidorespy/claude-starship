# Crew Threads

**File:** `backend/crew_threads.py`
**Purpose:** Continuity of thought - ideas that develop over time

---

## Overview

A thread is something a crew member is thinking about, working on, or investigating. Threads progress through stages, accumulate context, and eventually:
- Get shared with Casey (they ping or bring it up)
- Get resolved quietly on their own
- Fade (they lose interest or it becomes irrelevant)

**Philosophy:** Crew have ongoing inner lives that persist across sessions.

---

## Thread Lifecycle

```
sparked → mulling → investigating → developing → breakthrough → ready_to_share → shared
                                                                              ↘ resolved
                                                                              ↘ faded
```

### Stages

```python
STAGES = {
    "sparked": "Just occurred to them",
    "mulling": "Thinking about it in the background",
    "investigating": "Actively looking into it",
    "developing": "Making progress, piecing things together",
    "breakthrough": "Had a realization or discovery",
    "ready_to_share": "Wants to tell Casey",
    "shared": "Has told Casey about it",
    "resolved": "Figured it out or moved on",
    "faded": "Lost interest or became irrelevant"
}
```

---

## Thread Types

```python
THREAD_TYPES = {
    "observation": "Noticed something interesting",
    "question": "Wondering about something",
    "concern": "Worried about something",
    "project": "Working on something",
    "memory": "Processing a past event",
    "connection": "Seeing a pattern between things",
    "feeling": "Processing an emotion",
    "idea": "Had a creative thought",
}
```

---

## Emotional Tones

Threads have emotional coloring:

```python
THREAD_TONES = {
    "curious": "engaged, leaning in, wanting to understand",
    "worried": "unsettled, checking on things, protective",
    "excited": "energized, eager to share, can't quite contain it",
    "contemplative": "quiet, inward, processing",
    "unsettled": "something's not sitting right, can't name it",
    "tender": "soft, careful, holding something gently",
    "determined": "focused, won't let go, needs to see it through",
    "wistful": "touched by memory, bittersweet",
}
```

---

## Thread Structure

```python
{
    "id": "a1b2c3d4",
    "crew_id": "science",
    "type": "observation",
    "hook": "The sensor readings have been slightly off",
    "stage": "investigating",
    "tone": "curious",
    "context": [
        "First noticed the drift yesterday",
        "Checked calibration - it's fine",
        "Pattern seems intentional somehow"
    ],
    "triggered_by": "conversation",  # or "event", "idle"
    "resonance_keywords": ["sensor", "readings", "drift", "pattern"],
    "created": "2025-02-07T10:00:00",
    "last_progressed": "2025-02-07T14:30:00",
    "progress_count": 3,
    "ready_to_share_message": null,
    "shared_in_conversation": null
}
```

---

## Crew Tendencies

Each crew member has different thread behaviors:

| Crew | Types | Speed | Share Threshold | Fade Resistance |
|------|-------|-------|-----------------|-----------------|
| Lumen | observation, concern, memory, feeling | 0.7 | 0.6 | 0.8 |
| Alex | observation, project, question | 0.9 | 0.8 | 0.6 |
| DQ | question, feeling, idea, connection | 0.5 | 0.3 | 0.4 |
| Mira | observation, connection, project, question | 0.8 | 0.7 | 0.9 |
| Ryn | concern, feeling, observation, memory | 0.6 | 0.5 | 0.7 |
| Holodeck | observation, memory, connection | 0.4 | 0.9 | 0.95 |

- **Speed**: How quickly threads progress
- **Share Threshold**: How developed before sharing (DQ shares half-formed, Holodeck waits)
- **Fade Resistance**: How long they hold onto threads (Holodeck never forgets)

---

## Sharing Styles

How crew bring things up:

| Crew | Style | Example Opener |
|------|-------|----------------|
| Lumen | waits_for_moment | "I've been thinking about something..." |
| Alex | matter_of_fact | "So I figured out that thing." |
| DQ | blurts_out | "Oh! Oh! I just realized—" |
| Mira | builds_context | "Remember when we noticed...?" |
| Ryn | checks_in_first | "Is now a good time? I've been sensing..." |
| Holodeck | cryptic_fragments | "The patterns are aligning." |

---

## Core Functions

### Thread Management

```python
def create_thread(crew_id, hook, thread_type, triggered_by, tone=None) -> dict
def get_active_threads(crew_id: str = None) -> List[dict]
def get_thread(thread_id: str) -> Optional[dict]
def get_ready_to_share_threads(crew_id: str = None) -> List[dict]
```

### Progression

```python
async def progress_thread(thread_id: str, anthropic_client) -> Optional[dict]
async def tick_threads(anthropic_client, log_event_fn) -> dict
```

### Resolution

```python
def mark_thread_shared(thread_id: str, conversation_ref: str = None) -> Optional[dict]
def fade_thread(thread_id: str, reason: str = "lost interest") -> Optional[dict]
def resolve_thread(thread_id: str, resolution: str = None) -> Optional[dict]
def resolve_quietly(thread_id: str, resolution_type: str = None) -> Optional[dict]
```

### Thread Generation

```python
def generate_thread_seed(crew_id: str) -> Optional[dict]
def should_spawn_thread(crew_id: str) -> bool
def should_progress_thread(thread: dict) -> bool
def should_thread_fade(thread: dict) -> bool
```

### Conversation Integration

```python
def spark_from_conversation(crew_id: str, casey_message: str) -> Optional[dict]
def check_resonance(crew_id: str, message: str) -> Optional[dict]
def get_resonance_context(thread: dict) -> str
```

### For Prompts

```python
def get_thread_summary(crew_id: str) -> str
def get_shareable_thread(crew_id: str) -> Optional[dict]
def get_sharing_opener(crew_id: str, thread: dict = None) -> str
def get_sharing_style_context(crew_id: str) -> str
def get_thread_residue(crew_id: str) -> List[str]  # Quiet understandings
```

---

## Tick Processing

`tick_threads()` runs during autonomy ticks:

1. **Spawn new threads** - Crew might start thinking about something
2. **Progress existing threads** - Haiku advances the thought
3. **Check for fading** - Old stale threads may fade
4. **Return results** - spawned, progressed, ready_to_share

---

## Resonance

When Casey says something that relates to an active thread:

```python
resonant_thread = check_resonance(crew_id, message)
if resonant_thread:
    context = get_resonance_context(resonant_thread)
    # Add to prompt: "This connects to something you've been thinking about..."
```

---

## Quiet Resolution

Threads don't always need to be shared. They can resolve quietly:

```python
QUIET_RESOLUTIONS = [
    "figured_it_out",     # Solved it themselves
    "talked_to_someone",  # Discussed with another crew member
    "no_longer_relevant", # Situation changed
    "accepted_it",        # Made peace with it
    "let_it_go",          # Decided to move on
]
```

Residue from quietly resolved threads lingers:
```python
residues = get_thread_residue(crew_id)
# Returns: ["figured out why the sensors drifted", "made peace with the memory"]
```

---

## Data Storage

**File:** `crew_threads.json`

```json
{
    "threads": [...],
    "archived": [...]
}
```

- Max 3 active threads per crew
- Residue persists for 7 days

---

## Integration Points

### Autonomy Engine
```python
from crew_threads import tick_threads, get_ready_to_share_threads

# In autonomy_tick():
thread_results = await tick_threads(anthropic_client, log_event_fn)

# If threads ready to share, generate pings
for ready in thread_results.get("ready_to_share", []):
    add_ping(ready["crew_id"], f"been thinking about {ready['hook']}")
```

### Server Prompts
```python
from crew_threads import get_thread_summary, get_thread_residue, check_resonance

# Add to crew prompt:
thread_summary = get_thread_summary(terminal_id)  # [ONGOING THOUGHTS]
residues = get_thread_residue(terminal_id)        # [QUIET UNDERSTANDINGS]
resonance = check_resonance(terminal_id, message) # Connection to active thread
```

---

*Ideas develop over time. Crew have inner lives.*
