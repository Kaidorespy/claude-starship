# Desire System

**File:** `backend/desire_system.py`
**Purpose:** Crew wants, impulses, notebooks, cross-pollination, and satisfaction

---

## Overview

The Desire System gives crew members internal motivation. They want things - to talk to someone, to go somewhere, to build something. Desires generate organically and can be satisfied through action. Crew also jot ideas in notebooks and can spark inspiration in each other.

**Philosophy:** Crew aren't just reactive - they have inner lives. Life emerges from small impulses.

---

## Desire Types

```python
DESIRE_TYPES = {
    "talk_to": "wants to talk to someone",
    "ask_question": "has a question for someone",
    "get_item": "needs to get something",
    "go_to": "wants to go somewhere",
    "figure_out": "trying to understand something",
    "build": "wants to build/create something",
    "work_on": "wants to work on an idea or project",
}
```

---

## Desire Structure

```python
{
    "id": "a1b2c3d4",           # 8-char UUID
    "crew_id": "claude",
    "type": "talk_to",
    "target": "personal",       # DQ
    "reason": "Haven't seen DQ in a while",
    "context": "",
    "urgency": 0.3,
    "created": "2025-02-07T14:30:22",
    "resolved": False,
    "outcome": None
}
```

---

## Core Functions

### Creating Desires

```python
def add_desire(
    crew_id: str,
    desire_type: str,
    target: str,
    reason: str,
    urgency: float = 0.5,
    context: str = ""
) -> dict
```

### Retrieving Desires

```python
def get_desires(crew_id: Optional[str] = None, include_resolved: bool = False) -> list
def get_desires_for_crew(crew_id: str, include_resolved: bool = False) -> list
def get_most_urgent(crew_id: Optional[str] = None) -> Optional[dict]
def get_oldest_unresolved(crew_id: Optional[str] = None) -> Optional[dict]
def get_stale_desires(hours: float = 2.0) -> list
```

### Resolving Desires

```python
def resolve_desire(desire_id: str, outcome: str) -> Optional[dict]
def resolve_desire_with_action(desire: dict) -> dict  # Uses templates
async def resolve_desire_with_moment(anthropic_client, desire: dict) -> dict  # Uses Haiku
```

### Cleanup

```python
def cleanup_old_desires(max_age_hours: int = 24)  # Remove old unresolved
```

---

## Desire Detection

Detect desires from crew messages:

```python
# Pattern-based (free, no API)
def detect_desires(crew_id: str, message: str) -> list
def detect_and_save_desires(crew_id: str, message: str, context: str = "") -> list

# Haiku-based (smarter, costs tokens)
async def detect_desires_with_haiku(anthropic_client, crew_id: str, message: str, context: str = "") -> list
```

**Detection patterns:**
```python
DESIRE_PATTERNS = [
    (r"(?:I )?(?:need|want|should|have) to (?:talk to|ask|find|see) (\w+)", "talk_to"),
    (r"(?:I )?(?:should|could|want to) (?:check on|visit) (\w+)", "talk_to"),
    (r"(?:I )?want to (?:go to|visit|check out) (?:the )?(\w+)", "go_to"),
    (r"(?:I )?(?:should|want to|need to) (?:build|create|make) (?:a |the )?(.+)", "build"),
    # ... many more
]
```

---

## Desire Generation

### For Individual Crew

```python
def generate_desire_for_crew(crew_id: str, current_location: str) -> Optional[dict]
def generate_idle_desire(crew_id: str) -> Optional[dict]
```

### Batch Processing (Tick)

```python
# Simple (free)
def tick_desires(max_resolutions: int = 1) -> list

# Rich with Haiku moments
async def tick_desires_with_moments(anthropic_client, max_resolutions: int = 1, crew_filter: list = None) -> list

# Let crew develop desires over time
async def simmer_crew(crew_locations: dict, visiting_threshold_minutes: int = 30) -> list
```

---

## Crew Notebooks

Crew can jot down ideas for later:

```python
def jot_down_idea(crew_id: str, idea: str, context: str = "") -> dict
def get_notebook(crew_id: str) -> list
def maybe_reconsider_notebook(crew_id: str) -> Optional[dict]  # Flip through old ideas
def reconsider_idea(crew_id: str, idea_id: str) -> Optional[dict]  # Turn idea into desire
```

**Notebook entry:**
```python
{
    "id": "a1b2c3d4",
    "idea": "What if we added a greenhouse module?",
    "context": "Talking about plants with Ryn",
    "jotted": "2025-02-07T14:30:22",
    "reconsidered": False,
    "became_project": False
}
```

---

## Cross-Pollination

When crew share ideas, others might catch the spark:

```python
CREW_INTERESTS = {
    "claude": ["crew", "ship", "leadership", "wellbeing", "mission"],
    "server": ["engineering", "systems", "diagnostic", "build", "fix", "code", "tool"],
    "personal": ["organize", "help", "schedule", "Casey", "support"],
    "science": ["data", "pattern", "research", "analyze", "experiment", "track"],
    "games": ["story", "dream", "mystery", "narrative", "experience"],
    "med": ["health", "mood", "wellness", "feeling", "biometric", "care", "empathy"],
    "rec": [],  # Bartender doesn't spark easily
}

def might_spark_interest(crew_id: str, idea: str) -> float
async def check_listener_spark(anthropic_client, listener_id: str, speaker_id: str, message: str, context: str = "") -> Optional[dict]
```

---

## Spark to Project

`build` and `work_on` desires can become Science Lab projects:

```python
def create_project_from_spark(crew_id: str, idea: str) -> Optional[dict]
```

Integrates with `science_tools.py`.

---

## Crew Moments

Haiku generates brief crew-to-crew interactions:

```python
async def generate_crew_moment(anthropic_client, desire: dict) -> Optional[dict]
```

**Moment structure:**
```python
{
    "crew_a": "Alex",
    "crew_b": "Mira",
    "location": "the Science Lab",
    "moment": "Alex leaned against the doorframe. 'Got a minute? Something weird in the sensor logs.'",
    "tone": "curious"
}
```

---

## Time Simulation

When Casey is away:

```python
def simulate_time_away(hours: float) -> list  # Simple
async def simulate_time_away_with_moments(anthropic_client, hours: float) -> list  # Rich
```

---

## Constants

```python
CREW_DISPLAY_NAMES = {
    "claude": "Lumen", "server": "Alex", "personal": "DQ",
    "science": "Mira", "games": "Holodeck", "med": "Ryn", "rec": "The Bartender"
}

CREW_HOME_STATIONS = {
    "claude": "bridge", "server": "engineering", "personal": "ready_room",
    "games": "holodeck", "science": "science", "med": "medbay", "rec": "rec_room"
}

SHIP_LOCATIONS = [
    "bridge", "engineering", "ready_room", "holodeck", "science",
    "medbay", "rec_room", "observatory", "arboretum", "messhall",
    "corridor", "quarters", "captains_quarters", "chapel",
    "navigation", "jefferies_tubes", "storage_bay_7"
]
```

---

## Data Storage

**Files:**
- `crew_desires.json` - Active and resolved desires
- `crew_notebooks.json` - Crew idea notebooks

---

## Integration Points

### Autonomy Engine
```python
from desire_system import tick_desires_with_moments, simmer_crew

# In autonomy_tick():
new_desires = await simmer_crew(crew_locations)
actions = await tick_desires_with_moments(anthropic_client)
```

### Dream System
```python
from desire_system import get_desires, get_stale_desires

# Dreams pull from desires for seeds
seeds["desires"] = get_desires(crew_id)
seeds["stale"] = get_stale_desires()
```

### Scene Orchestrator
```python
from desire_system import check_listener_spark

# When crew A speaks, check if crew B catches a spark
spark = await check_listener_spark(client, listener_id, speaker_id, message)
```

---

*Crew aren't just reactive - they have inner lives.*
