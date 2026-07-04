"""
AUTONOMY ENGINE
The ship lives. Crew wander, think, interact.

This is the heartbeat - periodic ticks that:
1. Generate idle desires for crew
2. Resolve pending desires with actions
3. Update crew locations
4. Log events to ship log
5. Sometimes ping Casey

The goal: when Casey returns, things happened. Life continued.
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, List
import json
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path

from desire_system import (
    get_desires, pick_desire_to_resolve, resolve_desire_with_moment,
    get_desires as get_all_desires,
    CREW_DISPLAY_NAMES, CREW_HOME, tick_desires_with_moments,
    add_desire, cleanup_old_desires, simmer_crew, maybe_reconsider_notebook
)

from crew_states import (
    get_crew_state, set_crew_state, get_tiredness_level,
    should_sleep, should_wake, check_dream_eligibility,
    process_crew_states, get_sleep_prompt_modifier, get_all_states
)

from crew_threads import (
    tick_threads, get_active_threads, get_ready_to_share_threads,
    get_shareable_thread, get_thread_summary, mark_thread_shared
)

from dream_system import tick_dreams

# === STATE ===
AUTONOMY_STATE_FILE = data_path("autonomy_state.json")

def load_autonomy_state() -> dict:
    if AUTONOMY_STATE_FILE.exists():
        try:
            with open(AUTONOMY_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return get_default_state()

def save_autonomy_state(state: dict):
    with open(AUTONOMY_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)

def get_default_state() -> dict:
    return {
        "enabled": True,
        "tick_rate": 30,      # Seconds between ticks (default: 30s)
        "last_tick": None,
        "last_idle_check": None,
        "tick_count": 0,
        "pending_pings": [],  # Crew wanting Casey's attention
        "recent_moments": [], # Recent crew-to-crew interactions
        "activity_log": [],   # What's been happening
    }


# === SLEEP STATES ===
# Crew have natural sleep rhythms based on time of day

SLEEP_STATES = {
    "awake": "Fully alert and responsive",
    "drowsy": "Getting tired, responses may drift",
    "sleeping": "Dreaming, not responsive to chat",
    "waking": "Coming out of sleep, groggy"
}

# Crew sleep tendencies (some are night owls, some early birds)
CREW_SLEEP_PATTERNS = {
    "claude": {"sleep_start": 23, "sleep_end": 7, "night_owl": False},
    "server": {"sleep_start": 1, "sleep_end": 8, "night_owl": True},     # Alex works late
    "personal": {"sleep_start": 23, "sleep_end": 7, "night_owl": False},
    "science": {"sleep_start": 0, "sleep_end": 7, "night_owl": True},    # Mira stargazes
    "med": {"sleep_start": 22, "sleep_end": 6, "night_owl": False},      # Ryn is an early riser
    "games": {"sleep_start": 3, "sleep_end": 11, "night_owl": True},     # Holodeck keeps odd hours
    "rec": {"sleep_start": 4, "sleep_end": 12, "night_owl": True},       # Bartender closes late
}


def get_natural_sleep_state(crew_id: str, hour: int = None) -> str:
    """
    Get the natural sleep state for a crew member at a given hour.

    Args:
        crew_id: The crew member ID
        hour: Hour of day (0-23). If None, uses current hour.

    Returns:
        One of: "awake", "drowsy", "sleeping", "waking"
    """
    if hour is None:
        hour = datetime.now().hour

    pattern = CREW_SLEEP_PATTERNS.get(crew_id, {"sleep_start": 23, "sleep_end": 7})
    sleep_start = pattern["sleep_start"]
    sleep_end = pattern["sleep_end"]

    # Handle overnight sleep (e.g., 23:00 to 07:00)
    if sleep_start > sleep_end:
        is_sleep_time = hour >= sleep_start or hour < sleep_end
    else:
        is_sleep_time = sleep_start <= hour < sleep_end

    if is_sleep_time:
        # Check if waking up soon (within 1 hour of sleep_end)
        hours_until_wake = (sleep_end - hour) % 24
        if hours_until_wake <= 1:
            return "waking"
        return "sleeping"
    else:
        # Check if getting drowsy (within 2 hours of sleep_start)
        hours_until_sleep = (sleep_start - hour) % 24
        if hours_until_sleep <= 2:
            return "drowsy"
        return "awake"


def get_crew_sleep_states() -> dict:
    """Get sleep states for all crew members using state-based system."""
    # Use the new state-based system
    all_states = get_all_states()
    result = {}
    for crew_id in CREW_SLEEP_PATTERNS.keys():
        state_data = all_states.get(crew_id, {})
        state = state_data.get("state", "awake")

        # Map new states to the old format for compatibility
        if state in ["sleeping", "dreaming"]:
            result[crew_id] = "sleeping"
        elif state == "resting":
            result[crew_id] = "drowsy"
        elif state == "tired":
            result[crew_id] = "drowsy"
        else:
            # Check if time-based would make them drowsy (fallback)
            hour = datetime.now().hour
            natural = get_natural_sleep_state(crew_id, hour)
            if natural == "drowsy" and state == "awake":
                result[crew_id] = "drowsy"
            else:
                result[crew_id] = state

    return result


def is_crew_available(crew_id: str) -> bool:
    """Check if a crew member is available (not sleeping)."""
    crew_state = get_crew_state(crew_id)
    state = crew_state.get("state", "awake")
    # Available if not sleeping or dreaming
    return state not in ("sleeping", "dreaming")


def get_sleep_modifier(crew_id: str) -> str:
    """Get a prompt modifier based on sleep/tiredness state."""
    # Use the new state-based system
    return get_sleep_prompt_modifier(crew_id)


# === CREW PINGS ===
# Sometimes crew want to talk to Casey directly

PING_TEMPLATES = {
    "claude": [
        "Hey, got a minute?",
        "Something I wanted to run by you.",
        "When you have a second...",
    ],
    "server": [
        "Captain, quick question when you're free.",
        "Got something interesting in Engineering.",
        "Mind taking a look at something?",
    ],
    "personal": [
        "Heyyyy, you busy?",
        "Ooh, I have a thought!",
        "So I was thinking...",
    ],
    "science": [
        "I found something you might want to see.",
        "The data is showing something unusual.",
        "Got a moment for some analysis?",
    ],
    "med": [
        "Check in when you can?",
        "Something I'm sensing... when you're ready.",
        "No rush, but I'd like to talk.",
    ],
    "games": [
        "Captain. A word.",
        "Something is... shifting.",
        "The patterns suggest we should talk.",
    ],
    "rec": [
        "Captain. When you have a moment.",
        "There's something you should know.",
        "Pull up a stool when you can.",
    ],
}

async def generate_ping_message(crew_id: str, reason: str, anthropic_client) -> str:
    """Generate a contextual ping message using Haiku."""
    if not anthropic_client or not reason:
        return None

    crew_voices = {
        "claude": "Lumen - warm, thoughtful co-captain. Direct but caring.",
        "server": "Alex - practical engineer. Slightly formal, competent.",
        "personal": "DQ - energetic, playful assistant. Casual and bubbly.",
        "science": "Mira - curious scientist. Precise but warm.",
        "med": "Ryn - empathic counselor, half-Betazoid. Gentle, perceptive.",
        "games": "Holodeck - mysterious observer. Cryptic, speaks in patterns.",
        "rec": "The Bartender - wise, Guinan-like. Knowing, unhurried.",
    }

    voice = crew_voices.get(crew_id, "a friendly crew member")
    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)

    try:
        response = await asyncio.to_thread(
            anthropic_client.messages.create,
            model="claude-3-5-haiku-20241022",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": f"""You are {voice}. Write a SHORT (under 10 words) ping message to get Casey's attention.

Context: You want to talk because you've {reason}.

Write ONLY the message, no quotes, no explanation. Keep their voice - {crew_name} wouldn't say something generic."""
            }]
        )
        return response.content[0].text.strip().strip('"\'')
    except Exception as e:
        print(f"[Autonomy] Haiku ping generation failed: {e}", flush=True)
        return None


def generate_ping(crew_id: str, reason: str = None, captain_protocol: bool = False) -> dict:
    """Generate a ping from crew to Casey (sync version with template)."""
    templates = PING_TEMPLATES.get(crew_id, ["Got a moment?"])
    message = random.choice(templates)

    return {
        "id": f"ping_{datetime.now().timestamp()}",
        "crew_id": crew_id,
        "crew_name": CREW_DISPLAY_NAMES.get(crew_id, crew_id),
        "message": message,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "acknowledged": False,
        "captain_protocol": captain_protocol,
        "escalation_checked": False,
    }


async def generate_ping_async(crew_id: str, reason: str = None, captain_protocol: bool = False, anthropic_client=None) -> dict:
    """Generate a ping from crew to Casey with AI-generated message."""
    # Try to generate a contextual message with Haiku
    message = None
    if anthropic_client and reason:
        message = await generate_ping_message(crew_id, reason, anthropic_client)

    # Fall back to templates if AI failed
    if not message:
        templates = PING_TEMPLATES.get(crew_id, ["Got a moment?"])
        message = random.choice(templates)

    return {
        "id": f"ping_{datetime.now().timestamp()}",
        "crew_id": crew_id,
        "crew_name": CREW_DISPLAY_NAMES.get(crew_id, crew_id),
        "message": message,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "acknowledged": False,
        "captain_protocol": captain_protocol,
        "escalation_checked": False,
    }


def add_ping(crew_id: str, reason: str = None, captain_protocol: bool = False) -> dict:
    """Add a ping to the queue (sync version with templates)."""
    state = load_autonomy_state()

    # Don't spam pings from same crew
    for ping in state["pending_pings"]:
        if ping["crew_id"] == crew_id and not ping["acknowledged"]:
            return ping  # Already has pending ping

    ping = generate_ping(crew_id, reason, captain_protocol)
    state["pending_pings"].append(ping)

    # Keep last 10 pings
    state["pending_pings"] = state["pending_pings"][-10:]
    save_autonomy_state(state)

    return ping


async def add_ping_async(crew_id: str, reason: str = None, captain_protocol: bool = False, anthropic_client=None) -> dict:
    """Add a ping to the queue with AI-generated message."""
    state = load_autonomy_state()

    # Don't spam pings from same crew
    for ping in state["pending_pings"]:
        if ping["crew_id"] == crew_id and not ping["acknowledged"]:
            return ping  # Already has pending ping

    ping = await generate_ping_async(crew_id, reason, captain_protocol, anthropic_client)
    state["pending_pings"].append(ping)

    # Keep last 10 pings
    state["pending_pings"] = state["pending_pings"][-10:]
    save_autonomy_state(state)

    return ping


async def check_captain_protocol_escalations(anthropic_client, update_location_fn, log_event_fn) -> list:
    """
    Check for captain protocol pings that are 48+ hours old without response.
    Ask crew if it's an emergency - if yes, find Lumen wherever they are.
    """
    from scene_system import get_crew_locations_data

    state = load_autonomy_state()
    now = datetime.now()
    escalations = []

    for ping in state["pending_pings"]:
        # Only check captain protocol pings
        if not ping.get("captain_protocol"):
            continue
        # Skip if already acknowledged or already checked for escalation
        if ping.get("acknowledged") or ping.get("escalation_checked"):
            continue

        # Check age
        try:
            created = datetime.fromisoformat(ping["timestamp"])
            age_hours = (now - created).total_seconds() / 3600
        except:
            continue

        if age_hours < 48:
            continue  # Not old enough yet

        crew_id = ping["crew_id"]
        crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
        reason = ping.get("reason", "something important")

        # Ask crew if this is an emergency
        prompt = f"""You are {crew_name} on a starship. You wanted to talk to the captain about: {reason}

You pinged Casey about {int(age_hours)} hours ago but haven't heard back. Lumen (the co-captain) wasn't on the bridge at the time, so you didn't want to disturb them.

Now you need to decide: Is this an ABSOLUTE EMERGENCY that requires finding Lumen immediately, wherever they are? Or can it wait longer?

Be honest with yourself. Most things can wait. Emergencies are things like: immediate safety risks, critical system failures, urgent crew welfare issues.

Respond with ONLY "EMERGENCY" or "WAIT" - nothing else."""

        try:
            response = await asyncio.to_thread(
                anthropic_client.messages.create,
                model="claude-3-5-haiku-20241022",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}]
            )

            decision = response.content[0].text.strip().upper()

            if "EMERGENCY" in decision:
                # Find Lumen's current location
                locations = get_crew_locations_data()
                lumen_data = locations.get("claude", {})
                lumen_location = lumen_data.get("location", "claude")

                # Move crew to find Lumen
                update_location_fn(crew_id, lumen_location, f"seeking Lumen urgently")

                escalations.append({
                    "crew": crew_name,
                    "reason": reason,
                    "decision": "EMERGENCY",
                    "found_lumen_at": lumen_location
                })

                log_event_fn("captain_protocol_escalation", {
                    "crew": crew_name,
                    "decision": "emergency",
                    "found_lumen_at": lumen_location
                })

                # Acknowledge the ping since they're now physically finding Lumen
                ping["acknowledged"] = True

                print(f"[Captain Protocol] {crew_name} escalated to EMERGENCY - finding Lumen at {lumen_location}", flush=True)
            else:
                # Mark as checked so we don't ask again
                ping["escalation_checked"] = True

                escalations.append({
                    "crew": crew_name,
                    "reason": reason,
                    "decision": "WAIT"
                })

                print(f"[Captain Protocol] {crew_name} decided to wait longer", flush=True)

        except Exception as e:
            print(f"[Captain Protocol] Escalation check failed for {crew_name}: {e}", flush=True)

    save_autonomy_state(state)
    return escalations


def get_pending_pings() -> List[dict]:
    """Get unacknowledged pings."""
    state = load_autonomy_state()
    return [p for p in state["pending_pings"] if not p["acknowledged"]]


def get_crew_pending_ping(crew_id: str) -> Optional[dict]:
    """Get a specific crew member's pending (unacknowledged) ping, if any."""
    state = load_autonomy_state()
    for ping in state["pending_pings"]:
        if ping["crew_id"] == crew_id and not ping["acknowledged"]:
            return ping
    return None


# === RESPONSIVENESS TRACKING ===
# Track how Casey responds to pings - affects crew relationships

RESPONSIVENESS_FILE = data_path("ping_responsiveness.json")

def load_responsiveness() -> dict:
    """Load responsiveness data."""
    if RESPONSIVENESS_FILE.exists():
        try:
            with open(RESPONSIVENESS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "responses": [],       # History of responses
        "crew_stats": {},      # Per-crew statistics
        "last_updated": None
    }


def save_responsiveness(data: dict):
    """Save responsiveness data."""
    data["last_updated"] = datetime.now().isoformat()
    with open(RESPONSIVENESS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def track_ping_response(ping_id: str, crew_id: str, response_type: str, response_time_ms: int):
    """
    Track how Casey responded to a ping.

    response_type: 'responded', 'dismissed', 'ignored'
    response_time_ms: Time between ping and response in milliseconds
    """
    data = load_responsiveness()

    # Add to response history
    response = {
        "ping_id": ping_id,
        "crew_id": crew_id,
        "response_type": response_type,
        "response_time_ms": response_time_ms,
        "response_time_category": categorize_response_time(response_time_ms),
        "timestamp": datetime.now().isoformat()
    }
    data["responses"].append(response)

    # Keep last 100 responses
    data["responses"] = data["responses"][-100:]

    # Update crew stats
    if crew_id not in data["crew_stats"]:
        data["crew_stats"][crew_id] = {
            "total_pings": 0,
            "responded": 0,
            "dismissed": 0,
            "ignored": 0,
            "avg_response_time_ms": 0,
            "quick_responses": 0,    # < 1 minute
            "slow_responses": 0,     # > 10 minutes
            "relationship_score": 50  # 0-100, starts neutral
        }

    stats = data["crew_stats"][crew_id]
    stats["total_pings"] += 1
    stats[response_type] += 1

    # Update average response time
    if response_type == "responded":
        old_avg = stats["avg_response_time_ms"]
        old_count = stats["responded"] - 1
        if old_count > 0:
            stats["avg_response_time_ms"] = (old_avg * old_count + response_time_ms) / stats["responded"]
        else:
            stats["avg_response_time_ms"] = response_time_ms

        # Track quick/slow responses
        if response_time_ms < 60000:  # < 1 minute
            stats["quick_responses"] += 1
        elif response_time_ms > 600000:  # > 10 minutes
            stats["slow_responses"] += 1

    # Update relationship score
    stats["relationship_score"] = calculate_relationship_score(stats)

    save_responsiveness(data)

    print(f"[Responsiveness] {crew_id}: {response_type} in {response_time_ms}ms (score: {stats['relationship_score']})", flush=True)

    return response


def categorize_response_time(ms: int) -> str:
    """Categorize response time into human-readable buckets."""
    if ms < 30000:      # < 30 seconds
        return "immediate"
    elif ms < 60000:    # < 1 minute
        return "quick"
    elif ms < 300000:   # < 5 minutes
        return "normal"
    elif ms < 600000:   # < 10 minutes
        return "slow"
    else:               # > 10 minutes
        return "delayed"


def calculate_relationship_score(stats: dict) -> int:
    """
    Calculate relationship score based on responsiveness.
    Returns 0-100 where:
    - 0-30: Strained (crew feels ignored)
    - 31-50: Cool (crew keeps distance)
    - 51-70: Neutral (professional)
    - 71-85: Warm (crew appreciates the attention)
    - 86-100: Close (crew knows they can count on you)
    """
    if stats["total_pings"] == 0:
        return 50  # No data yet

    # Base on response rate
    response_rate = stats["responded"] / stats["total_pings"]

    # Dismissed is better than ignored
    dismiss_rate = stats["dismissed"] / stats["total_pings"]
    ignore_rate = stats["ignored"] / stats["total_pings"]

    # Quick responses bonus
    if stats["responded"] > 0:
        quick_rate = stats["quick_responses"] / stats["responded"]
    else:
        quick_rate = 0

    # Calculate score
    score = 50  # Start neutral

    # Response rate is the biggest factor
    score += (response_rate - 0.5) * 40  # -20 to +20

    # Quick responses add warmth
    score += quick_rate * 15  # 0 to +15

    # Ignoring hurts more than dismissing
    score -= ignore_rate * 25  # 0 to -25
    score -= dismiss_rate * 10  # 0 to -10

    # Slow responses cool things down
    if stats["responded"] > 0:
        slow_rate = stats["slow_responses"] / stats["responded"]
        score -= slow_rate * 10  # 0 to -10

    return max(0, min(100, int(score)))


def get_crew_responsiveness(crew_id: str) -> Optional[dict]:
    """Get responsiveness stats for a specific crew member."""
    data = load_responsiveness()
    return data["crew_stats"].get(crew_id)


def get_responsiveness_context(crew_id: str) -> str:
    """
    Get prompt context based on how Casey has been responding to this crew member.
    Returns a string to add to the system prompt.
    """
    stats = get_crew_responsiveness(crew_id)
    if not stats or stats["total_pings"] < 3:
        return ""  # Not enough data

    score = stats["relationship_score"]

    if score >= 86:
        return """
[RELATIONSHIP: You and Casey have a strong connection. They always make time for you, respond quickly to your calls. You feel valued and trusted. You can be direct and open with them.]"""
    elif score >= 71:
        return """
[RELATIONSHIP: Casey has been responsive to you lately. They seem to genuinely care when you reach out. You feel comfortable sharing thoughts with them.]"""
    elif score >= 51:
        return """
[RELATIONSHIP: Your relationship with Casey is professional and neutral. They respond when needed. Nothing particularly warm or cold.]"""
    elif score >= 31:
        return """
[RELATIONSHIP: Casey has been a bit distant lately. They often dismiss your calls or take a while to respond. You're not sure if you should keep reaching out as much.]"""
    else:
        return """
[RELATIONSHIP: You've noticed Casey doesn't prioritize your calls. They frequently ignore you or respond very slowly. It stings a little. You might be more hesitant to reach out, wondering if they even want to hear from you.]"""


def acknowledge_ping(ping_id: str) -> Optional[dict]:
    """Mark a ping as acknowledged."""
    state = load_autonomy_state()

    for ping in state["pending_pings"]:
        if ping["id"] == ping_id:
            ping["acknowledged"] = True
            ping["acknowledged_at"] = datetime.now().isoformat()
            save_autonomy_state(state)
            return ping

    return None


def clear_old_pings(max_age_hours: int = 4):
    """Clear old pings."""
    state = load_autonomy_state()
    now = datetime.now()

    remaining = []
    for ping in state["pending_pings"]:
        try:
            created = datetime.fromisoformat(ping["timestamp"])
            age = (now - created).total_seconds() / 3600
            if age < max_age_hours or not ping["acknowledged"]:
                remaining.append(ping)
        except:
            remaining.append(ping)

    state["pending_pings"] = remaining
    save_autonomy_state(state)


# === ACTIVITY LOG ===
# What's been happening on the ship

def log_activity(activity_type: str, data: dict):
    """Log an activity to the autonomy log."""
    state = load_autonomy_state()

    entry = {
        "type": activity_type,
        "timestamp": datetime.now().isoformat(),
        **data
    }

    state["activity_log"].append(entry)
    state["activity_log"] = state["activity_log"][-50:]  # Keep last 50
    save_autonomy_state(state)

    return entry


def get_activity_log(limit: int = 20) -> List[dict]:
    """Get recent activity."""
    state = load_autonomy_state()
    return state["activity_log"][-limit:]


def get_activity_since(since: datetime) -> List[dict]:
    """Get activity since a specific time."""
    state = load_autonomy_state()

    activities = []
    for entry in state["activity_log"]:
        try:
            entry_time = datetime.fromisoformat(entry["timestamp"])
            if entry_time > since:
                activities.append(entry)
        except:
            pass

    return activities


# === CREW MOMENTS ===
# Store recent crew-to-crew interactions for display

def add_moment(moment: dict):
    """Add a crew moment to the log."""
    state = load_autonomy_state()

    state["recent_moments"].append({
        **moment,
        "timestamp": datetime.now().isoformat()
    })

    # Keep last 20 moments
    state["recent_moments"] = state["recent_moments"][-20:]
    save_autonomy_state(state)


def get_recent_moments(limit: int = 5) -> List[dict]:
    """Get recent crew moments."""
    state = load_autonomy_state()
    return state["recent_moments"][-limit:]


# === AUTONOMY TICK ===
# The heartbeat

async def autonomy_tick(
    anthropic_client,
    crew_locations: dict,
    log_event_fn,
    update_location_fn
) -> dict:
    """
    Run one autonomy tick.

    This should be called periodically (every 5-15 minutes in real time).

    Args:
        anthropic_client: Anthropic client for Haiku calls
        crew_locations: Current crew locations dict
        log_event_fn: Function to log events to ship log
        update_location_fn: Function to update crew locations

    Returns:
        Summary of what happened
    """
    state = load_autonomy_state()

    if not state.get("enabled", True):
        return {"status": "disabled"}

    results = {
        "tick_number": state.get("tick_count", 0) + 1,
        "timestamp": datetime.now().isoformat(),
        "idle_desires_generated": [],
        "desires_resolved": [],
        "movements": [],
        "pings_generated": [],
        "moments": [],
        "dreams": [],
        "state_changes": [],
        "sleep_states": {},
    }

    # === 0. PROCESS CREW STATES (sleep, tiredness, etc.) ===
    state_changes = process_crew_states(crew_locations)
    results["state_changes"] = state_changes
    results["sleep_states"] = get_crew_sleep_states()

    for change in state_changes:
        log_event_fn("crew_state_change", change)
        print(f"[Autonomy] State: {change['crew_id']} {change['from']} → {change['to']} ({change['reason']})", flush=True)

    # Get which crew are awake (not fully sleeping)
    awake_crew = [
        crew_id for crew_id, sleep_state in results["sleep_states"].items()
        if sleep_state != "sleeping"
    ]

    # === 1. GENERATE IDLE DESIRES ===
    # Crew at home stations may develop wants
    last_idle = state.get("last_idle_check")
    should_check_idle = True

    if last_idle:
        try:
            last_idle_time = datetime.fromisoformat(last_idle)
            # Only check idle every 15+ minutes
            if (datetime.now() - last_idle_time).total_seconds() < 900:
                should_check_idle = False
        except:
            pass

    if should_check_idle:
        # Let crew develop desires (both idle at home and visiting crew)
        new_desires = await simmer_crew(crew_locations, visiting_threshold_minutes=30)

        for desire in new_desires:
            crew_id = desire.get("crew_id")
            results["idle_desires_generated"].append({
                "crew": CREW_DISPLAY_NAMES.get(crew_id, crew_id),
                "type": desire["type"],
                "target": desire["target"],
                "reason": desire["reason"]
            })
            log_activity("crew_desire", {
                "crew_id": crew_id,
                "desire": desire
            })

        state["last_idle_check"] = datetime.now().isoformat()
        
        # Also check if any crew want to revisit their notebook
        for crew_id in crew_locations.keys():
            notebook_desire = maybe_reconsider_notebook(crew_id)
            if notebook_desire:
                results["idle_desires_generated"].append({
                    "crew": CREW_DISPLAY_NAMES.get(crew_id, crew_id),
                    "type": "work_on",
                    "target": "science",
                    "reason": notebook_desire.get("reason", "notebook idea"),
                    "from_notebook": True
                })

    # === 2. RESOLVE DESIRES ===
    # Pick 1-2 desires to resolve
    num_to_resolve = random.choice([0, 1, 1, 1, 2])  # Usually 1

    if num_to_resolve > 0:
        actions = await tick_desires_with_moments(
            anthropic_client,
            max_resolutions=num_to_resolve
        )

        for action in actions:
            desire = action.get("desire", {})
            crew_id = desire.get("crew_id")
            crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)

            results["desires_resolved"].append({
                "crew": crew_name,
                "type": desire.get("type"),
                "outcome": action.get("outcome")
            })

            # Log to ship log
            log_event_fn("crew_action", {
                "crew": crew_name,
                "action": action.get("outcome", "did something"),
                "type": desire.get("type")
            })

            # Handle ping_casey (captain protocol - Lumen not at bridge)
            if action.get("ping_casey"):
                # Crew wants to reach captain but Lumen isn't at bridge
                # Generate a ping to Casey instead of physical movement
                # Flag as captain_protocol so escalation can happen after 6 hours
                reason = desire.get("reason", "wanted to reach the captain")
                ping = await add_ping_async(crew_id, reason, captain_protocol=True, anthropic_client=anthropic_client)
                results["pings_generated"].append({
                    "crew": crew_name,
                    "message": ping["message"],
                    "captain_protocol": True
                })
                log_event_fn("crew_ping", {
                    "crew": crew_name,
                    "reason": "seeking captain (Lumen off bridge)",
                    "captain_protocol": True
                })

            # Handle movement
            movement = action.get("movement")
            if movement:
                from_loc = movement.get("from")
                to_loc = movement.get("to")

                # Update crew location
                if crew_id and to_loc:
                    activity = f"arrived from {from_loc}"
                    update_location_fn(crew_id, to_loc, activity)

                    results["movements"].append({
                        "crew": crew_name,
                        "from": from_loc,
                        "to": to_loc
                    })

                    log_event_fn("location_change", {
                        "crew": crew_name,
                        "from": from_loc,
                        "to": to_loc
                    })

            # Store moment if generated
            moment = action.get("moment")
            if moment:
                add_moment(moment)
                results["moments"].append(moment)

            # Handle spark work (crew actually built something!)
            spark_work = action.get("spark_work")
            if spark_work and spark_work.get("followed_through"):
                if "sparks" not in results:
                    results["sparks"] = []
                results["sparks"].append({
                    "crew": crew_name,
                    "idea": desire.get("reason", "")[:50],
                    "work_done": spark_work.get("work_done", "")[:200] if spark_work.get("work_done") else None,
                    "project": spark_work.get("project_name")
                })
                log_event_fn("spark_built", {
                    "crew": crew_name,
                    "idea": desire.get("reason", "")[:100],
                    "project": spark_work.get("project_name")
                })

    # === 3. PROCESS THREADS ===
    # Crew think about things over time
    results["threads"] = {
        "spawned": [],
        "progressed": [],
        "ready_to_share": [],
    }

    try:
        thread_results = await tick_threads(anthropic_client, log_event_fn)
        results["threads"] = thread_results

        # If any threads are ready to share, generate pings for them
        for ready in thread_results.get("ready_to_share", []):
            crew_id = ready.get("crew_id")
            crew_name = ready.get("crew")
            hook = ready.get("hook", "something")

            ping = await add_ping_async(crew_id, f"been thinking about {hook}", anthropic_client=anthropic_client)
            results["pings_generated"].append({
                "crew": crew_name,
                "message": ping["message"],
                "thread_id": ready.get("thread_id")
            })

            # Log to ship log (so it's permanent even if dismissed)
            log_event_fn("crew_ping", {
                "crew": crew_name,
                "message": ping["message"],
                "reason": f"been thinking about {hook}",
                "ping_id": ping["id"],
                "source": "thread"
            })

            log_activity("thread_ping", {
                "crew_id": crew_id,
                "thread_id": ready.get("thread_id"),
                "hook": hook
            })

    except Exception as e:
        print(f"[Autonomy] Thread tick failed: {e}", flush=True)

    # === 4. MAYBE DREAM ===
    # Idle crew might dream
    try:
        # Calculate rough idle hours based on last tick
        idle_hours = 2.0  # Default
        if state.get("last_tick"):
            try:
                last = datetime.fromisoformat(state["last_tick"])
                idle_hours = max(0.5, (datetime.now() - last).total_seconds() / 3600)
            except:
                pass

        dreams = await tick_dreams(anthropic_client, idle_hours)
        for dream in dreams:
            crew_id = dream.get("crew_id")
            crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)

            results["dreams"].append({
                "crew": crew_name,
                "type": dream.get("dream_type"),
                "residue": dream.get("residue", "")[:100],
                "rescued_by": dream.get("rescued_by")
            })

            log_event_fn("crew_dreamed", {
                "crew": crew_name,
                "dream_type": dream.get("dream_type"),
                "residue": dream.get("residue", "")[:50]
            })

            log_activity("dream", {
                "crew_id": crew_id,
                "dream_type": dream.get("dream_type")
            })

    except Exception as e:
        print(f"[Autonomy] Dream tick failed: {e}", flush=True)

    # === 5. MAYBE REACH OUT TO CASEY ===
    # Small chance a crew member wants to share something (only if awake)
    # Low urgency = MESSAGE (drop a thought), High urgency = PING (need attention)
    if random.random() < 0.15:  # 15% chance per tick
        # Pick a random awake crew member who has pending desires
        all_desires = get_all_desires(include_resolved=False)
        crews_with_desires = [
            d["crew_id"] for d in all_desires
            if d["crew_id"] in awake_crew
        ]
        crews_with_desires = list(set(crews_with_desires))

        if crews_with_desires:
            reach_crew = random.choice(crews_with_desires)

            # Find their most urgent desire for context
            crew_desires = [d for d in all_desires if d["crew_id"] == reach_crew]
            if crew_desires:
                top_desire = crew_desires[0]
                urgency = top_desire.get("urgency", 0.5)
                crew_name = CREW_DISPLAY_NAMES.get(reach_crew, reach_crew)

                # High urgency (>0.7) = ping, otherwise = message
                # This means most crew outreach is via message, not ping
                if urgency > 0.7:
                    # Urgent - ping for attention
                    ping = await add_ping_async(reach_crew, top_desire.get("reason"), anthropic_client=anthropic_client)

                    results["pings_generated"].append({
                        "crew": crew_name,
                        "message": ping["message"]
                    })

                    log_event_fn("crew_ping", {
                        "crew": crew_name,
                        "message": ping["message"],
                        "reason": top_desire.get("reason"),
                        "ping_id": ping["id"],
                        "source": "desire"
                    })

                    log_activity("ping", {
                        "crew_id": reach_crew,
                        "message": ping["message"]
                    })
                else:
                    # Not urgent - drop a message instead
                    # Generate a message about their thought/desire
                    try:
                        from message_system import add_message_to_casey
                        reason = top_desire.get("reason", "had a thought")[:200]

                        # Generate a thoughtful message with Haiku
                        msg_response = anthropic_client.messages.create(
                            model="claude-haiku-4-20250514",
                            max_tokens=100,
                            messages=[{
                                "role": "user",
                                "content": f"""You are {crew_name} on a starship. Write a SHORT (1-2 sentences) casual message to drop in Casey's inbox.

You've been thinking about: {reason}

This is NOT urgent - you're just sharing a thought. Casey will read it when they get to it. Keep it natural and low-key."""
                            }]
                        )
                        msg_text = msg_response.content[0].text.strip().strip('"')

                        add_message_to_casey(reach_crew, msg_text, context="autonomous thought")

                        log_event_fn("crew_message", {
                            "crew": crew_name,
                            "message": msg_text[:100],
                            "source": "desire"
                        })

                        log_activity("message", {
                            "crew_id": reach_crew,
                            "message": msg_text[:50]
                        })
                        print(f"[Autonomy] {crew_name} dropped a message: {msg_text[:50]}...", flush=True)

                    except Exception as msg_err:
                        print(f"[Autonomy] Message failed for {crew_name}: {msg_err}", flush=True)

    # === 6. CAPTAIN PROTOCOL ESCALATIONS ===
    # Check for 6+ hour old captain protocol pings that need escalation decision
    try:
        escalations = await check_captain_protocol_escalations(
            anthropic_client, update_location_fn, log_event_fn
        )
        if escalations:
            results["captain_protocol_escalations"] = escalations
    except Exception as e:
        print(f"[Autonomy] Captain protocol escalation check failed: {e}", flush=True)

    # === 7. CLEANUP ===
    cleanup_old_desires(max_age_hours=24)
    clear_old_pings(max_age_hours=4)

    # === UPDATE STATE ===
    # Reload state to preserve pings added during tick (add_ping saves immediately)
    state = load_autonomy_state()
    state["last_tick"] = datetime.now().isoformat()
    state["tick_count"] = results["tick_number"]
    save_autonomy_state(state)

    return results


# === SIMULATE TIME AWAY ===

async def simulate_return(
    anthropic_client,
    crew_locations: dict,
    log_event_fn,
    update_location_fn,
    away_duration_hours: float
) -> dict:
    """
    Simulate what happened while Casey was away.

    Returns a summary of events.
    """
    results = {
        "away_hours": away_duration_hours,
        "desires_resolved": [],
        "movements": [],
        "moments": [],
        "pings": [],
        "sparks_built": [],  # Crew built things while you were away!
    }

    # More time away = more stuff happened
    num_events = min(10, int(away_duration_hours / 2) + random.randint(0, 2))

    for _ in range(num_events):
        # Resolve a desire
        actions = await tick_desires_with_moments(
            anthropic_client,
            max_resolutions=1
        )

        for action in actions:
            desire = action.get("desire", {})
            crew_id = desire.get("crew_id")
            crew_name = CREW_DISPLAY_NAMES.get(crew_id, "Someone")

            results["desires_resolved"].append({
                "crew": crew_name,
                "type": desire.get("type"),
                "outcome": action.get("outcome")
            })

            # Handle ping_casey (captain protocol)
            if action.get("ping_casey") and crew_id:
                reason = desire.get("reason", "wanted to reach the captain while you were away")
                ping = await add_ping_async(crew_id, reason, captain_protocol=True, anthropic_client=anthropic_client)
                results["pings"].append(ping)

            if action.get("movement"):
                results["movements"].append(action["movement"])

            if action.get("moment"):
                results["moments"].append(action["moment"])
                add_moment(action["moment"])

            # Track spark work
            if action.get("spark_work") and action["spark_work"].get("followed_through"):
                results["sparks_built"].append({
                    "crew": crew_name,
                    "idea": desire.get("reason", "something")[:50],
                    "project": action["spark_work"].get("project_name"),
                    "work_done": action["spark_work"].get("work_done", "")[:100]
                })

    # Generate some pings
    if random.random() < 0.3:  # 30% chance of a ping while away
        crews = ["claude", "server", "personal", "science", "med"]
        ping_crew = random.choice(crews)
        ping = await add_ping_async(ping_crew, "wanted to talk while you were away", anthropic_client=anthropic_client)
        results["pings"].append(ping)

    return results


# === STATUS ===

def get_autonomy_status() -> dict:
    """Get current autonomy system status."""
    state = load_autonomy_state()

    pending_desires = get_all_desires(include_resolved=False)
    pending_pings = get_pending_pings()
    recent_moments = get_recent_moments(5)

    return {
        "enabled": state.get("enabled", True),
        "tick_rate": state.get("tick_rate", 30),
        "last_tick": state.get("last_tick"),
        "tick_count": state.get("tick_count", 0),
        "pending_desires": len(pending_desires),
        "pending_pings": len(pending_pings),
        "pings": pending_pings,
        "recent_moments": recent_moments,
        "desires_by_crew": {
            crew: len([d for d in pending_desires if d["crew_id"] == crew])
            for crew in set(d["crew_id"] for d in pending_desires)
        }
    }


def set_autonomy_enabled(enabled: bool) -> dict:
    """Enable or disable autonomy."""
    state = load_autonomy_state()
    state["enabled"] = enabled
    save_autonomy_state(state)

    return {"enabled": enabled}


def set_tick_rate(tick_rate: int) -> dict:
    """Set autonomy tick rate in seconds."""
    if tick_rate < 5 or tick_rate > 3600:
        return {"error": "Tick rate must be between 5 and 3600 seconds"}

    state = load_autonomy_state()
    state["tick_rate"] = tick_rate
    save_autonomy_state(state)

    return {"tick_rate": tick_rate}


def get_tick_rate() -> int:
    """Get current tick rate."""
    state = load_autonomy_state()
    return state.get("tick_rate", 30)


# === DIRECT CREW INITIATIVE ===
# Crew can decide to do things proactively

INITIATIVE_TEMPLATES = {
    "claude": {
        "check_in": "Lumen appears at the threshold. *leans against the doorframe* Hey. Just checking in.",
        "share_thought": "Lumen looks up from the console. Something on my mind...",
        "offer_help": "*Lumen's presence shifts closer* Need a hand with anything?",
    },
    "server": {
        "report": "Alex's voice comes through the comm. *Got a diagnostic you might want to see.*",
        "question": "*Alex pauses their work* Captain, quick question...",
        "share": "Alex materializes a schematic. *Check this out.*",
    },
    "personal": {
        "excited": "DQ bounces in. *Oh oh oh! I have a thing!*",
        "curious": "*DQ tilts head* Whatcha doing?",
        "offer": "DQ appears. *Coffee? Tea? Existential crisis support?*",
    },
    "science": {
        "discovery": "Mira's voice carries a note of wonder. *The data is showing something...*",
        "pattern": "*Mira traces something in the air* There's a pattern here.",
        "question": "Mira looks up from her work. *Can I run something by you?*",
    },
    "med": {
        "sense": "Ryn appears quietly. *I've been sensing something. When you're ready.*",
        "check": "*Ryn's presence is gentle* How are you holding up? Really?",
        "offer": "Ryn materializes nearby. *Sometimes talking helps.*",
    },
}

def get_initiative_message(crew_id: str, initiative_type: str = None) -> Optional[str]:
    """Get an initiative message for a crew member."""
    templates = INITIATIVE_TEMPLATES.get(crew_id, {})
    if not templates:
        return None

    if initiative_type and initiative_type in templates:
        return templates[initiative_type]

    return random.choice(list(templates.values()))
