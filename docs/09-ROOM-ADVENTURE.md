# Room Adventure System

**File:** `backend/room_adventure.py`
**Purpose:** Interactive objects, text adventure style interactions

---

## Overview

Room Adventure adds text adventure game mechanics to the ship. Crew can look around, inspect objects, pick things up, and interact with their environment using action tags.

---

## Action Tags

Crew append these tags to their responses:

| Tag | Purpose | Example |
|-----|---------|---------|
| `[LOOK]` | Observe surroundings | `[LOOK]` |
| `[INSPECT: object]` | Examine something | `[INSPECT: console]` |
| `[DO: action]` | Free-form action | `[DO: adjusts the lighting]` |
| `[MOVE: location]` | Travel somewhere | `[MOVE: engineering]` |
| `[TAKE: item]` | Pick something up | `[TAKE: padd]` |
| `[USE: item]` | Use an item | `[USE: tricorder]` |

---

## Room Definitions

Each room has interactable objects:

```python
# From ship_state.json:
{
    "bridge": {
        "description": "The command center of the ship.",
        "objects": {
            "captain_chair": {
                "description": "The captain's chair. Well-worn, comfortable.",
                "interactable": true,
                "actions": ["sit", "examine"]
            },
            "main_viewscreen": {
                "description": "Shows the stars ahead.",
                "interactable": true,
                "actions": ["look", "adjust"]
            },
            "helm_console": {
                "description": "Navigation controls.",
                "interactable": true,
                "requires": "nav_training"
            }
        },
        "ambient": "Soft hum of systems. Starlight."
    }
}
```

---

## Key Functions

### Looking Around

```python
def look(location: str, crew_id: str) -> str:
    """Generate a description of the current location."""
```

Returns:
- Room description
- Visible objects
- Present crew
- Ambient details

**Example output:**
```
The Bridge. Command center of the ship.

You see: the captain's chair (well-worn), the main viewscreen (showing stars),
the helm console, several duty stations.

Also here: DQ (at a side console), Alex (checking something)

Soft hum of systems. Starlight through the viewscreen.
```

### Inspecting Objects

```python
def inspect(object_name: str, location: str, crew_id: str) -> str:
    """Get detailed description of an object."""
```

**Example:**
```python
inspect("captain_chair", "bridge", "claude")
# Returns: "The captain's chair. Well-worn leather, molded to countless hours
#           of sitting. Your spot. It faces the viewscreen directly."
```

### Performing Actions

```python
def do_action(action: str, location: str, crew_id: str) -> str:
    """Handle free-form actions."""
```

Generates contextual responses to actions.

### Movement

```python
def move(destination: str, crew_id: str) -> str:
    """Move crew to new location."""
```

Returns description of the journey and new location.

---

## Object Interactions

Objects can have special interactions:

```python
SPECIAL_INTERACTIONS = {
    "jukebox": {
        "use": lambda: trigger_jukebox(),
        "examine": "A classic jukebox, retrofitted. Glowing softly."
    },
    "chess_board": {
        "examine": lambda: describe_chess_position(),
        "use": "You'd need an opponent to play."
    },
    "viewport": {
        "look": lambda: describe_current_view(),
        "examine": "Stars. So many stars. The occasional nebula."
    }
}
```

---

## Item System

Some objects can be picked up:

```python
def take(item: str, location: str, crew_id: str) -> dict:
    """Attempt to take an item."""

def get_inventory(crew_id: str) -> List[str]:
    """Get crew member's current inventory."""
```

**Inventory is limited and mostly flavor:**
- PADDs
- Drinks
- Personal items

---

## Dynamic Descriptions

Descriptions change based on:

### Time of Day
```python
def get_ambient(location: str) -> str:
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return room["ambient_morning"]
    elif 12 <= hour < 18:
        return room["ambient_afternoon"]
    elif 18 <= hour < 22:
        return room["ambient_evening"]
    else:
        return room["ambient_night"]
```

### Who's Present
```python
def include_present_crew(location: str, description: str) -> str:
    present = get_crew_in_location(location)
    if present:
        description += f"\n\nAlso here: {format_crew_list(present)}"
    return description
```

### Room State
Objects can have states that change:
```python
{
    "coffee_maker": {
        "states": {
            "off": "Silent, dark.",
            "brewing": "Gurgling, the smell of coffee.",
            "ready": "A pot of fresh coffee waits."
        },
        "current_state": "ready"
    }
}
```

---

## Integration with Server

Action tags are parsed from crew responses:

```python
def parse_action_tags(response: str) -> List[dict]:
    """Extract action tags from a response."""

    tags = []
    # [LOOK]
    if "[LOOK]" in response:
        tags.append({"type": "look"})

    # [INSPECT: object]
    inspect_match = re.search(r"\[INSPECT:\s*(.+?)\]", response)
    if inspect_match:
        tags.append({"type": "inspect", "target": inspect_match.group(1)})

    # etc.
    return tags
```

---

## Processing Flow

```
Crew Response: "Let me check that console. [INSPECT: helm_console]"
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │ Parse action tags              │
                    └───────────────┬───────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │ Execute: inspect("helm_console")│
                    └───────────────┬───────────────┘
                                    ▼
                    ┌───────────────────────────────┐
                    │ Return: "The helm console..."  │
                    └───────────────────────────────┘
```

---

## Data Storage

**File:** `ship_state.json`

Contains room definitions, object states, and ambient details.

---

*The ship is a place you can explore.*
