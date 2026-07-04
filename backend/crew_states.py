"""
CREW STATES SYSTEM
Tracks crew consciousness: awake, resting, sleeping, dreaming

States:
- awake: Normal operation
- tired: Been awake too long, sluggish
- resting: In quarters, winding down
- sleeping: Actually asleep (no responses)
- dreaming: REM sleep, dreams generate here

Sleep is state-based, not time-based. Crew sleep when:
1. They're in quarters and decide to sleep (late hour + tired)
2. They hit exhaustion threshold (varies by personality)
"""

import json
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from datetime import datetime, timedelta
from typing import Optional, Dict, List

STATES_FILE = data_path("crew_states.json")

# === PERSONALITY-BASED EXHAUSTION ===
# Hours before crew MUST sleep (crash)
EXHAUSTION_LIMITS = {
    "server": 52,      # Alex pushes through, workaholic
    "claude": 40,      # Lumen is reasonable about rest
    "personal": 32,    # DQ crashes relatively early
    "science": 48,     # Mira gets lost in work
    "med": 36,         # Ryn knows the importance of rest
    "games": 999,      # Holodeck doesn't sleep traditionally
    "rec": 999,        # Bartender is... always there
}

# Hours before crew get TIRED (not crashed, just sluggish)
TIRED_THRESHOLDS = {
    "server": 24,
    "claude": 18,
    "personal": 14,
    "science": 20,
    "med": 16,
    "games": 999,
    "rec": 999,
}

# How long crew typically sleep (hours)
SLEEP_DURATIONS = {
    "server": 5,       # Alex runs on minimal sleep
    "claude": 7,       # Lumen sleeps properly
    "personal": 9,     # DQ loves sleep
    "science": 6,      # Mira - efficient sleeper
    "med": 8,          # Ryn - healthy habits
    "games": 0,        # Holodeck doesn't sleep
    "rec": 0,          # Bartender doesn't sleep
}

# Bedtime preferences (24h format) - when they naturally want to sleep
BEDTIME_PREFERENCES = {
    "server": 2,       # Alex is a night owl
    "claude": 23,      # Lumen - reasonable bedtime
    "personal": 22,    # DQ - earlier
    "science": 1,      # Mira - late researcher
    "med": 23,         # Ryn - healthy habits
    "games": None,     # Holodeck - N/A
    "rec": None,       # Bartender - N/A
}

# State transitions
VALID_TRANSITIONS = {
    "awake": ["tired", "resting", "sleeping"],  # Can get tired, or go rest/crash
    "tired": ["resting", "sleeping", "awake"],  # Can rest, crash, or second wind
    "resting": ["sleeping", "awake"],           # Can fall asleep or get back up
    "sleeping": ["dreaming", "awake"],          # Can dream or wake
    "dreaming": ["sleeping", "awake"],          # Can return to sleep or wake
}


def load_states() -> Dict:
    """Load crew states from file."""
    if STATES_FILE.exists():
        try:
            with open(STATES_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_states(data: Dict):
    """Save crew states to file."""
    with open(STATES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_crew_state(crew_id: str) -> Dict:
    """Get state info for a crew member."""
    states = load_states()
    if crew_id not in states:
        states[crew_id] = {
            "state": "awake",
            "last_slept": None,
            "last_state_change": datetime.now().isoformat(),
            "hours_awake": 0
        }
        save_states(states)
    return states[crew_id]


def set_crew_state(crew_id: str, new_state: str, reason: str = None) -> Dict:
    """
    Transition crew to a new state.
    Returns the updated state info.
    """
    states = load_states()
    current = states.get(crew_id, {"state": "awake"})
    old_state = current.get("state", "awake")

    # Validate transition
    if new_state not in VALID_TRANSITIONS.get(old_state, []):
        print(f"[CrewState] Invalid transition for {crew_id}: {old_state} → {new_state}", flush=True)
        # Allow it anyway for flexibility, just warn

    now = datetime.now()
    current["state"] = new_state
    current["last_state_change"] = now.isoformat()

    # Track sleep start/end
    if new_state == "sleeping" and old_state != "sleeping":
        # Just fell asleep
        current["sleep_started"] = now.isoformat()
    elif old_state in ["sleeping", "dreaming"] and new_state == "awake":
        # Just woke up
        current["last_slept"] = now.isoformat()
        current["hours_awake"] = 0
        current.pop("sleep_started", None)

    states[crew_id] = current
    save_states(states)

    print(f"[CrewState] {crew_id}: {old_state} → {new_state}" + (f" ({reason})" if reason else ""), flush=True)
    return current


def update_hours_awake():
    """Update hours_awake for all crew based on last_slept timestamp."""
    states = load_states()
    now = datetime.now()

    for crew_id, state in states.items():
        if state.get("state") in ["sleeping", "dreaming"]:
            continue  # Not awake

        last_slept = state.get("last_slept")
        if last_slept:
            try:
                slept_time = datetime.fromisoformat(last_slept)
                hours = (now - slept_time).total_seconds() / 3600
                state["hours_awake"] = round(hours, 1)
            except:
                state["hours_awake"] = 0
        else:
            # Never slept in our tracking - assume fresh start
            last_change = state.get("last_state_change")
            if last_change:
                try:
                    change_time = datetime.fromisoformat(last_change)
                    hours = (now - change_time).total_seconds() / 3600
                    state["hours_awake"] = round(hours, 1)
                except:
                    state["hours_awake"] = 0

    save_states(states)


def get_tiredness_level(crew_id: str) -> str:
    """
    Get how tired a crew member is.
    Returns: 'rested', 'fine', 'tired', 'exhausted', 'crashing'
    """
    state = get_crew_state(crew_id)

    if state.get("state") in ["sleeping", "dreaming", "resting"]:
        return "resting"

    hours = state.get("hours_awake", 0)
    tired_threshold = TIRED_THRESHOLDS.get(crew_id, 18)
    exhaustion_limit = EXHAUSTION_LIMITS.get(crew_id, 48)

    if hours < tired_threshold * 0.5:
        return "rested"
    elif hours < tired_threshold:
        return "fine"
    elif hours < exhaustion_limit * 0.75:
        return "tired"
    elif hours < exhaustion_limit:
        return "exhausted"
    else:
        return "crashing"


def should_sleep(crew_id: str, current_location: str) -> tuple[bool, str]:
    """
    Check if crew member should transition to sleep.
    Returns (should_sleep, reason)
    """
    state = get_crew_state(crew_id)
    current_state = state.get("state", "awake")

    # Already sleeping
    if current_state in ["sleeping", "dreaming"]:
        return (False, "already sleeping")

    # Non-sleeping crew
    if crew_id in ["games", "rec"]:
        return (False, "doesn't sleep")

    hours_awake = state.get("hours_awake", 0)
    exhaustion_limit = EXHAUSTION_LIMITS.get(crew_id, 48)

    # Locations where crew can sleep (private spaces only)
    sleep_safe_locations = ["quarters", terminal_id]  # Their quarters or their home terminal

    # Forced crash from exhaustion - but only in private spaces
    # (They'd stumble to quarters first, not pass out in the messhall)
    if hours_awake >= exhaustion_limit and current_location in sleep_safe_locations:
        return (True, "exhaustion crash")

    # Near exhaustion - same rule, find a bed first
    if hours_awake >= exhaustion_limit * 0.9 and current_location in sleep_safe_locations:
        return (True, "about to crash")

    # In quarters and tired enough
    if current_location in sleep_safe_locations:
        tired_threshold = TIRED_THRESHOLDS.get(crew_id, 18)
        if hours_awake >= tired_threshold:
            # Check if it's a reasonable bedtime
            hour = datetime.now().hour
            preferred_bedtime = BEDTIME_PREFERENCES.get(crew_id, 23)

            if preferred_bedtime is not None:
                # Within 2 hours of preferred bedtime or past it
                if hour >= preferred_bedtime - 2 or hour < 6:
                    return (True, "bedtime in quarters")

    return (False, "not tired enough or not in quarters")


def should_wake(crew_id: str) -> tuple[bool, str]:
    """
    Check if sleeping crew member should wake up.
    Returns (should_wake, reason)
    """
    state = get_crew_state(crew_id)
    current_state = state.get("state", "awake")

    if current_state not in ["sleeping", "dreaming"]:
        return (False, "not sleeping")

    sleep_started = state.get("sleep_started")
    if not sleep_started:
        return (False, "no sleep start time")

    try:
        started = datetime.fromisoformat(sleep_started)
        hours_slept = (datetime.now() - started).total_seconds() / 3600

        needed_sleep = SLEEP_DURATIONS.get(crew_id, 7)

        if hours_slept >= needed_sleep:
            return (True, f"slept {hours_slept:.1f}h, needed {needed_sleep}h")

        # Could also wake early if something important happens
        # (pings, alarms, etc.) - handled elsewhere

    except:
        pass

    return (False, "still sleeping")


def get_sleep_prompt_modifier(crew_id: str) -> str:
    """
    Get prompt modifier based on crew's tiredness/sleep state.
    Added to system prompt to affect their behavior.
    """
    state = get_crew_state(crew_id)
    current_state = state.get("state", "awake")

    if current_state == "sleeping":
        return "\n\n[STATE: You are asleep. You cannot respond to messages. Zzz.]"

    if current_state == "dreaming":
        return "\n\n[STATE: You are deep in REM sleep, dreaming. You cannot respond to messages.]"

    if current_state == "resting":
        hours = state.get("hours_awake", 0)
        return f"\n\n[STATE: You're in your quarters, winding down after {hours:.0f} hours awake. Relaxed, maybe a bit drowsy. Responses might be shorter, softer.]"

    tiredness = get_tiredness_level(crew_id)
    hours = state.get("hours_awake", 0)

    if tiredness == "rested":
        return ""  # No modifier needed
    elif tiredness == "fine":
        return ""  # Still fine
    elif tiredness == "tired":
        return f"\n\n[STATE: You've been awake {hours:.0f} hours. You're tired. Responses might be shorter, you might yawn, you're thinking about rest.]"
    elif tiredness == "exhausted":
        return f"\n\n[STATE: You've been awake {hours:.0f} hours. You're exhausted. Struggling to focus. Words come harder. You really need to sleep soon.]"
    elif tiredness == "crashing":
        return f"\n\n[STATE: You've been awake {hours:.0f} hours. You're barely functioning. Eyes won't stay open. Sentences trail off. You might fall asleep mid-conversation.]"

    return ""


def check_dream_eligibility(crew_id: str) -> tuple[bool, str]:
    """
    Check if crew member can dream right now.
    Dreams only happen during sleeping state.
    """
    state = get_crew_state(crew_id)
    current_state = state.get("state", "awake")

    if current_state != "sleeping":
        return (False, f"not sleeping (state: {current_state})")

    # Check if they've been asleep long enough for REM
    sleep_started = state.get("sleep_started")
    if sleep_started:
        try:
            started = datetime.fromisoformat(sleep_started)
            hours_slept = (datetime.now() - started).total_seconds() / 3600

            # REM typically starts ~90 minutes into sleep
            if hours_slept < 1.5:
                return (False, f"not in REM yet ({hours_slept:.1f}h asleep)")
        except:
            pass

    return (True, "eligible for dreams")


def process_crew_states(crew_locations: Dict) -> List[Dict]:
    """
    Main tick function - check all crew and transition states as needed.
    Called from autonomy tick.

    Returns list of state changes that occurred.
    """
    update_hours_awake()
    changes = []

    for crew_id in ["claude", "server", "personal", "science", "med"]:
        state = get_crew_state(crew_id)
        current_state = state.get("state", "awake")
        location = crew_locations.get(crew_id, {}).get("location", "unknown")

        # Check if awake crew should sleep
        if current_state in ["awake", "tired", "resting"]:
            should, reason = should_sleep(crew_id, location)
            if should:
                set_crew_state(crew_id, "sleeping", reason)
                changes.append({
                    "crew_id": crew_id,
                    "from": current_state,
                    "to": "sleeping",
                    "reason": reason
                })
                continue

        # Check if sleeping crew should wake
        if current_state in ["sleeping", "dreaming"]:
            should, reason = should_wake(crew_id)
            if should:
                set_crew_state(crew_id, "awake", reason)
                changes.append({
                    "crew_id": crew_id,
                    "from": current_state,
                    "to": "awake",
                    "reason": reason
                })
                continue

        # Check if sleeping crew should enter dream state
        if current_state == "sleeping":
            eligible, reason = check_dream_eligibility(crew_id)
            if eligible:
                # Don't always dream - random chance per check
                import random
                if random.random() < 0.3:  # 30% chance per tick
                    set_crew_state(crew_id, "dreaming", "entered REM")
                    changes.append({
                        "crew_id": crew_id,
                        "from": "sleeping",
                        "to": "dreaming",
                        "reason": "entered REM"
                    })

        # Dreaming crew cycle back to sleeping after a while
        if current_state == "dreaming":
            last_change = state.get("last_state_change")
            if last_change:
                try:
                    changed = datetime.fromisoformat(last_change)
                    minutes_dreaming = (datetime.now() - changed).total_seconds() / 60

                    # Dream cycles are ~20-30 minutes
                    if minutes_dreaming > 25:
                        set_crew_state(crew_id, "sleeping", "dream cycle ended")
                        changes.append({
                            "crew_id": crew_id,
                            "from": "dreaming",
                            "to": "sleeping",
                            "reason": "dream cycle ended"
                        })
                except:
                    pass

        # Awake crew get tired
        if current_state == "awake":
            tiredness = get_tiredness_level(crew_id)
            if tiredness in ["tired", "exhausted", "crashing"]:
                set_crew_state(crew_id, "tired", f"been awake too long")
                changes.append({
                    "crew_id": crew_id,
                    "from": "awake",
                    "to": "tired",
                    "reason": tiredness
                })

    return changes


def wake_crew(crew_id: str, reason: str = "woken") -> bool:
    """Force wake a crew member (ping, alarm, emergency, etc.)"""
    state = get_crew_state(crew_id)
    if state.get("state") in ["sleeping", "dreaming"]:
        set_crew_state(crew_id, "awake", reason)
        return True
    return False


def get_all_states() -> Dict:
    """Get all crew states for display/debugging."""
    update_hours_awake()
    return load_states()


# === COMMS/WALKIE BOUNDARIES ===
# Crew can set themselves to "do not disturb"

def get_crew_comms_status(crew_id: str) -> Dict:
    """
    Get crew's comms/walkie availability.
    Returns: {"available": bool, "since": timestamp, "reason": str}
    """
    states = load_states()
    state = states.get(crew_id, {})

    comms = state.get("comms", "on")  # Default: available
    return {
        "available": comms != "off",
        "status": comms,
        "since": state.get("comms_since"),
        "reason": state.get("comms_reason", "")
    }


def set_crew_comms(crew_id: str, status: str, reason: str = None) -> Dict:
    """
    Toggle crew's comms availability.
    status: "on" or "off"
    """
    states = load_states()
    if crew_id not in states:
        states[crew_id] = {"state": "awake"}

    old_status = states[crew_id].get("comms", "on")
    states[crew_id]["comms"] = status
    states[crew_id]["comms_since"] = datetime.now().isoformat()

    if reason:
        states[crew_id]["comms_reason"] = reason
    elif status == "on":
        states[crew_id].pop("comms_reason", None)

    save_states(states)

    status_word = "off (do not disturb)" if status == "off" else "on"
    print(f"[Comms] {crew_id}: comms now {status_word}" + (f" - {reason}" if reason else ""), flush=True)

    return get_crew_comms_status(crew_id)


def get_comms_prompt_modifier(crew_id: str) -> str:
    """
    Get prompt modifier about comms status.
    Lets crew know they can toggle availability.
    """
    comms = get_crew_comms_status(crew_id)

    if not comms["available"]:
        reason = comms.get("reason", "need some quiet")
        return f"""

[COMMS STATUS: Your walkie is OFF. You set it to do-not-disturb because: {reason}
Casey cannot reach you via walkie right now. You can turn it back on with [COMMS: on] when you're ready.]"""

    # Available - just remind them of the option
    return """

[COMMS STATUS: Your walkie is on. If you need uninterrupted time, you can go do-not-disturb with [COMMS: off].]"""
