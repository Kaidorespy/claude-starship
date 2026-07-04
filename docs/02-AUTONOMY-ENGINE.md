# Autonomy Engine

**File:** `backend/autonomy.py`
**Purpose:** The heartbeat of the ship - tick system, sleep cycles, activity simulation

---

## Overview

The Autonomy Engine is the background simulation that makes the ship feel alive even when no one is chatting. It runs periodic "ticks" that:
- Generate crew desires (via `simmer_crew()`)
- Process crew thought threads
- Trigger dreams for idle crew
- Resolve pending desires with actions
- Maybe ping Casey for attention
- Manage crew sleep states

**Philosophy:** The ship lives whether you're watching or not.

---

## Tick System

The core is `autonomy_tick()` - the ship's heartbeat:

```python
async def autonomy_tick(
    anthropic_client,
    crew_locations: dict,
    log_event_fn,
    update_location_fn
) -> dict:
    """
    Run one autonomy tick.
    Called periodically (every 5-15 minutes in real time).
    """
```

### What Happens Each Tick

1. **Generate Idle Desires** - `simmer_crew()` lets crew develop wants (every 15+ min)
2. **Resolve Desires** - `tick_desires_with_moments()` resolves 1-2 desires
3. **Process Threads** - `tick_threads()` progresses crew thought threads
4. **Maybe Dream** - `tick_dreams()` triggers dreams for idle crew
5. **Maybe Ping Casey** - 15% chance an awake crew member pings
6. **Cleanup** - Remove old desires (24h) and pings (4h)

### Tick Results

```python
results = {
    "tick_number": 42,
    "timestamp": "2024-02-08T15:30:00",
    "idle_desires_generated": [...],
    "desires_resolved": [...],
    "movements": [...],
    "pings_generated": [...],
    "moments": [...],          # Crew-to-crew interactions
    "dreams": [...],           # Dreams that occurred
    "threads": {...},          # Thread progressions
    "sleep_states": {...},     # Current crew sleep states
}
```

---

## Sleep States

Crew have natural sleep rhythms based on time of day:

```python
SLEEP_STATES = {
    "awake": "Fully alert and responsive",
    "drowsy": "Getting tired, responses may drift",
    "sleeping": "Dreaming, not responsive to chat",
    "waking": "Coming out of sleep, groggy"
}
```

### Crew Sleep Patterns

| Crew | Sleep Start | Wake Time | Style |
|------|-------------|-----------|-------|
| Lumen | 23:00 | 07:00 | Normal |
| Alex | 01:00 | 08:00 | Night owl |
| DQ | 23:00 | 07:00 | Normal |
| Mira | 00:00 | 07:00 | Stargazer |
| Ryn | 22:00 | 06:00 | Early riser |
| Holodeck | 03:00 | 11:00 | Odd hours |
| Bartender | 04:00 | 12:00 | Closes late |

### Sleep Functions

```python
def get_natural_sleep_state(crew_id: str, hour: int = None) -> str:
    """Get sleep state for crew at given hour."""

def get_crew_sleep_states() -> dict:
    """Get sleep states for all crew."""

def is_crew_available(crew_id: str) -> bool:
    """Check if crew is available (not sleeping)."""

def get_sleep_modifier(crew_id: str) -> str:
    """Get prompt modifier based on sleep state."""
```

### Sleep Effects

- **Sleeping crew** don't generate pings or resolve desires
- **Drowsy crew** may have drifting responses
- **Waking crew** may have dream residue clinging to thoughts

---

## Crew Pings

Crew can ping Casey for attention:

```python
PING_TEMPLATES = {
    "claude": ["Hey, got a minute?", "Something I wanted to run by you.", ...],
    "server": ["Captain, quick question when you're free.", ...],
    ...
}
```

### Ping Functions

```python
def add_ping(crew_id: str, reason: str = None) -> dict
def get_pending_pings() -> List[dict]
def acknowledge_ping(ping_id: str) -> Optional[dict]
def clear_old_pings(max_age_hours: int = 4)
```

---

## Activity Logging

Track what's happening on the ship:

```python
def log_activity(activity_type: str, data: dict)
def get_activity_log(limit: int = 20) -> List[dict]
def get_activity_since(since: datetime) -> List[dict]
```

**Activity types:** `crew_desire`, `ping`, `thread_ping`, `dream`, `spark_built`

---

## Crew Moments

Store crew-to-crew interactions:

```python
def add_moment(moment: dict)
def get_recent_moments(limit: int = 5) -> List[dict]
```

---

## Simulate Return

When Casey comes back after being away:

```python
async def simulate_return(
    anthropic_client,
    crew_locations: dict,
    log_event_fn,
    update_location_fn,
    away_duration_hours: float
) -> dict:
    """Simulate what happened while Casey was away."""
```

Returns summary of: desires resolved, movements, moments, pings, sparks built.

---

## Status & Control

```python
def get_autonomy_status() -> dict
    # Returns: enabled, last_tick, tick_count, pending_desires,
    #          pending_pings, pings, recent_moments, desires_by_crew

def set_autonomy_enabled(enabled: bool) -> dict
```

---

## Crew Initiative

Crew can proactively reach out:

```python
INITIATIVE_TEMPLATES = {
    "claude": {
        "check_in": "Lumen appears at the threshold...",
        "share_thought": "Lumen looks up from the console...",
        "offer_help": "*Lumen's presence shifts closer*...",
    },
    ...
}

def get_initiative_message(crew_id: str, initiative_type: str = None) -> Optional[str]
```

---

## State File

**File:** `autonomy_state.json`

```json
{
  "enabled": true,
  "last_tick": "2024-02-08T15:30:00",
  "last_idle_check": "2024-02-08T15:15:00",
  "tick_count": 100,
  "pending_pings": [],
  "recent_moments": [],
  "activity_log": []
}
```

---

## Integration Points

### Server Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /autonomy/tick` | Manually trigger a tick |
| `GET /autonomy/status` | Get system status |
| `POST /autonomy/enable` | Enable/disable |
| `GET /autonomy/pings` | Get pending pings |
| `POST /autonomy/pings/{id}/acknowledge` | Acknowledge ping |
| `GET /autonomy/activity` | Get activity log |
| `GET /autonomy/moments` | Get recent moments |

### Subsystem Integration

```python
# Desires
from desire_system import tick_desires_with_moments, simmer_crew, ...

# Threads
from crew_threads import tick_threads, get_ready_to_share_threads, ...

# Dreams
from dream_system import tick_dreams
```

---

## Background Heartbeat

The server runs a background task that triggers ticks automatically:

```python
async def desire_heartbeat():
    """Background task - runs every 5 minutes."""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        if autonomy_enabled:
            await autonomy_tick(...)
```

---

*The ship lives whether you're watching or not.*
