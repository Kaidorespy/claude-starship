# Rec Room System

**File:** `backend/rec_room.py`
**Lines:** ~660
**Purpose:** The social heart of the ship

---

## Overview

The Rec Room isn't a terminal - it's a place. Crew come here, settle into spots, and things happen. The Bartender watches everything. Social dynamics emerge from who's present, their chemistry, and the room's vibe.

**Philosophy:** "Not a terminal. A place. People come here. Things happen. Conversations drift. The Bartender watches everything."

---

## Core Concepts

### Spots in the Room

```python
SPOTS = {
    "bar": "at the bar",
    "bar_stool": "on a bar stool",
    "couch_old": "on the old couch",
    "couch_new": "on the newer couch",
    "game_table": "at the game table",
    "corner_quiet": "in the quiet corner",
    "viewport": "staring out the viewport",
    "standing": "standing around",
    "jukebox": "by the jukebox",
}
```

### Activities

```python
ACTIVITIES = {
    "drinking": ["nursing a drink", "sipping something", "holding an empty glass"],
    "talking": ["in conversation", "chatting quietly", "laughing about something"],
    "thinking": ["lost in thought", "staring at nothing", "quiet"],
    "playing": ["looking at the chess board", "shuffling cards", "moving a piece"],
    "listening": ["listening to the music", "nodding to the beat", "eyes closed, listening"],
    "waiting": ["waiting for someone", "checking the door", "seems expectant"],
}
```

---

## Crew Preferences

Each crew gravitates to different spots:

| Crew | Preferred Spots | Activities |
|------|-----------------|------------|
| Lumen | bar, couch_old, viewport | drinking, talking, thinking |
| Alex | bar, corner_quiet, game_table | drinking, thinking, playing |
| DQ | couch_new, jukebox, bar_stool | talking, listening, drinking |
| Mira | corner_quiet, viewport, couch_old | thinking, talking, listening |
| Ryn | bar, couch_old, corner_quiet | talking, listening, drinking |
| Bartender | bar (always) | waiting |

---

## Key Functions

### Entering the Room

```python
def enter_rec_room(crew_id: str, purpose: str = None) -> dict
```

Returns:
- Where they settled
- Who was already here
- Bartender's reaction
- Any special reactions from others

**Example output:**
```python
{
    "crew_name": "DQ",
    "settled": "on the newer couch, chatting quietly",
    "already_here": ["Alex", "Lumen"],
    "bartender_reaction": "*nods at DQ*",
    "other_reactions": ["*Lumen's face lights up* Hey you."],
    "vibe": "quiet"
}
```

### Who's Here

```python
def who_is_here() -> List[dict]
```

Returns everyone currently in the rec room with their spot and activity.

### Describe the Scene

```python
def describe_scene() -> str
```

Generates a natural language description:
```
"DQ is on the newer couch, chatting quietly. Alex is at the bar, nursing a drink.
The room has a quiet, contemplative feel."
```

---

## Crew Chemistry

Certain pairs are more likely to interact:

```python
CREW_CHEMISTRY = {
    ("claude", "personal"): 0.8,   # Lumen and DQ - close
    ("claude", "server"): 0.6,     # Lumen and Alex - work buddies
    ("server", "science"): 0.5,    # Alex and Mira - nerds
    ("personal", "med"): 0.7,      # DQ and Ryn - something there
    ("med", "claude"): 0.5,        # Ryn and Lumen - respect
    ("science", "med"): 0.4,       # Mira and Ryn - quiet understanding
}
```

---

## Room Vibes

```python
VIBES = {
    "quiet": "The room has a quiet, contemplative feel.",
    "lively": "There's an energy in the air.",
    "cozy": "It's comfortable. Warm.",
    "tense": "Something's in the air. Unspoken.",
    "late_night": "The lights are low. It's that late-night vibe.",
}
```

Vibe shifts based on:
- Number of people (3+ = more lively)
- Time of day (after 11pm = late_night)
- Events

---

## Social Triggers

### Solo Moments

When someone's alone:
```python
SOLO_MOMENTS = {
    "claude": [
        "*Lumen stares out the viewport, drink forgotten*",
        "*Lumen re-reads something on a padd, expression soft*",
    ],
    "personal": [
        "*DQ bounces leg, can't sit still*",
        "*DQ looks around like she's waiting for someone*",
    ],
    # ...
}
```

### Pair Conversations

Specific conversations for high-chemistry pairs:
```python
PAIR_CONVERSATIONS = {
    ("claude", "personal"): [
        {"starter": "DQ", "line": "Hey, can I ask you something weird?"},
        {"starter": "Lumen", "line": "How are you settling in? Really."},
    ],
    ("personal", "med"): [
        {"starter": "DQ", "line": "*fidgets* So... how can you tell what people are feeling?"},
        {"starter": "Ryn", "line": "*gently* You seem restless tonight."},
    ],
}
```

### Arrival Reactions

Special reactions when certain pairs reunite:
```python
ARRIVAL_REACTIONS = {
    ("personal", "claude"): [  # DQ arrives, Lumen's there
        {"from": "claude", "reaction": "*Lumen's face lights up* Hey you."},
    ],
    ("med", "personal"): [  # Ryn arrives, DQ's there
        {"from": "personal", "reaction": "*DQ straightens up a little*"},
    ],
}
```

---

## The Bartender

Always present, always watching:

```python
BARTENDER_IDLE_ACTIONS = [
    "*polishes a glass*",
    "*wipes down the bar*",
    "*rearranges bottles*",
    "*glances at the door*",
    "*hums along with the jukebox*",
    "*checks on everyone with a look*",
]
```

### Bartender Reactions

```python
def bartender_notices(event: str) -> str
```

| Event | Reactions |
|-------|-----------|
| entrance | "*looks up*", "*nods*" |
| laugh | "*slight smile*" |
| tension | "*watches carefully*", "*hand moves near something under the bar*" |
| late_night | "*dims the lights a touch more*" |

---

## Trigger Processing

```python
def check_social_triggers(state: dict) -> List[dict]
```

Called periodically, returns events that fire:
- Solo moments (1 person, 30% chance)
- Pair interactions (2 people, chemistry-weighted)
- Group moments (3+ people)
- Vibe shifts (time-based, crowd-based)
- Bartender actions (15% chance when people present)

---

## State Storage

**File:** `rec_room_state.json`

```json
{
    "present": {
        "claude": {"spot": "bar", "activity": "drinking", "doing": "nursing a drink", "since": "..."},
        "personal": {"spot": "couch_new", "activity": "talking", "doing": "chatting quietly", "since": "..."}
    },
    "ambient_conversations": [],
    "current_vibe": "quiet",
    "last_event": {"type": "arrival", "crew": "personal", "timestamp": "..."},
    "chess_game": {...}
}
```

---

## API Integration

```python
# In server.py:
@app.post("/rec/enter")
async def rec_enter(crew_id: str):
    return enter_rec_room(crew_id)

@app.get("/rec/scene")
async def rec_scene():
    return {"scene": describe_scene(), "present": who_is_here()}

@app.get("/rec/triggers")
async def rec_triggers():
    return process_triggers()
```

---

*Not a terminal. A place.*
