# Scene System

**File:** `backend/scene_system.py`
**Purpose:** Multi-crew presence tracking

---

## Overview

The Scene System tracks who's in each room and manages multi-crew conversations. When multiple crew are present, messages can be addressed to specific individuals or open to all.

---

## Location Tracking

### Ship Locations

```python
SHIP_LOCATIONS = [
    "bridge",
    "engineering",
    "ready_room",
    "science_lab",
    "holodeck",
    "mess_hall",
    "quarters",
    "corridor",
    "bathroom",
    "captains_quarters",
    "rec_room",
    "observatory"
]
```

### Crew Locations

```python
def get_crew_location(crew_id: str) -> str:
    """Get where a crew member currently is."""

def set_crew_location(crew_id: str, location: str):
    """Move a crew member to a new location."""

def get_crew_in_location(location: str) -> List[str]:
    """Get all crew currently in a location."""
```

---

## Presence Detection

### Who's Here?

```python
def who_is_here(location: str) -> dict:
    """Get detailed presence info for a location."""
    return {
        "location": location,
        "crew_present": ["claude", "personal"],
        "crew_names": ["Lumen", "DQ"],
        "activities": {
            "claude": "reviewing reports",
            "personal": "chatting"
        }
    }
```

### Room Context for Prompts

```python
def get_room_context(location: str) -> str:
    """Get context string for crew prompts."""
```

**Example output:**
```
You are currently on the Bridge.
Also present: DQ (chatting), Alex (checking systems)
```

---

## Movement System

```python
def move_crew(crew_id: str, destination: str, reason: str = None) -> dict:
    """Move a crew member and log the event."""
```

Returns:
- Previous location
- New location
- Any notifications (who sees them leave/arrive)

---

## Activity Tracking

Crew have current activities:

```python
def set_activity(crew_id: str, activity: str):
    """Set what a crew member is doing."""

def get_activity(crew_id: str) -> str:
    """Get crew member's current activity."""
```

**Common activities:**
- "on duty"
- "relaxing"
- "reading"
- "in conversation"
- "thinking"
- "sleeping"

---

## Room Descriptions

```python
def get_room_description(location: str) -> str:
    """Get the current state/description of a room."""
```

Pulls from `ship_state.json` and adds dynamic elements based on who's present.

---

## Data Storage

**File:** `crew_locations.json`

```json
{
    "locations": {
        "claude": {
            "location": "bridge",
            "activity": "on duty",
            "since": "2025-02-07T08:00:00"
        },
        "personal": {
            "location": "ready_room",
            "activity": "chatting",
            "since": "2025-02-07T09:30:00"
        }
    }
}
```

---

## Integration Points

### Server Prompts
```python
# Inject presence into system prompt:
room_context = get_room_context(crew_location)
system_prompt += f"\n\n{room_context}"
```

### Scene Orchestrator
```python
# Used to determine who should respond:
present = get_crew_in_location(current_room)
```

### Autonomy Engine
```python
# Random movements:
move_crew(crew_id, pick_destination(crew_id))
```

---

*The ship knows where everyone is.*
