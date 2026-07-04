"""
AUTONOMY SCHEDULER
Ship rhythm drives crew autonomy.
Meals, work calls, lights out - they move when it makes sense.
"""

import asyncio
from datetime import datetime, time, timedelta
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
import json

# Schedule anchor points (ship time)
BREAKFAST_END = time(9, 0)      # 9am
LUNCH_END = time(13, 0)         # 1pm
DINNER_END = time(20, 0)        # 8pm

# Work calls (Mon-Fri, 9-5)
WORK_CALLS = [
    time(8, 30),   # Mid-breakfast
    time(12, 30),  # Mid-lunch
    time(15, 0)    # 3pm check-in
]

# Ship settings
SETTINGS_PATH = data_path("ship_settings.json")


def load_settings():
    """Load ship settings."""
    if SETTINGS_PATH.exists():
        with open(SETTINGS_PATH, 'r') as f:
            return json.load(f)
    return {"autonomy_level": "medium", "captain_name": "Captain"}


def save_settings(settings):
    """Save ship settings."""
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)


def is_work_hours() -> bool:
    """Check if it's work hours (9-5, Mon-Fri)."""
    now = datetime.now()
    is_weekday = now.weekday() < 5  # 0-4 = Mon-Fri
    is_work_time = time(9, 0) <= now.time() <= time(17, 0)
    return is_weekday and is_work_time


def should_trigger_autonomy(last_check: datetime = None) -> tuple[bool, str]:
    """
    Check if we should trigger an autonomy check.
    Returns (should_trigger, reason).
    """
    now = datetime.now()
    current_time = now.time()

    # Check meal anchor points (5min window after end time)
    meal_anchors = {
        "breakfast_end": BREAKFAST_END,
        "lunch_end": LUNCH_END,
        "dinner_end": DINNER_END
    }

    for name, anchor_time in meal_anchors.items():
        # Within 5 minutes after meal end
        if anchor_time <= current_time <= (datetime.combine(datetime.today(), anchor_time) + timedelta(minutes=5)).time():
            return (True, name)

    # Check work calls (only during work hours)
    if is_work_hours():
        settings = load_settings()
        autonomy_level = settings.get("autonomy_level", "medium")

        # Skip work calls if autonomy is low
        if autonomy_level == "low":
            return (False, "autonomy_low")

        for work_time in WORK_CALLS:
            # Within 5 minutes of work call
            if work_time <= current_time <= (datetime.combine(datetime.today(), work_time) + timedelta(minutes=5)).time():
                # High = always, medium = 50% chance
                if autonomy_level == "high" or (autonomy_level == "medium" and now.minute % 2 == 0):
                    return (True, f"work_call_{work_time.hour}_{work_time.minute}")

    return (False, "no_trigger")


def is_crew_busy(crew_id: str) -> bool:
    """
    Check if crew member is currently busy and shouldn't be interrupted.
    Busy = in active conversation, using tools, etc.
    """
    # FIRST: Check if Casey recently messaged them (most reliable signal)
    # This prevents crew from being moved mid-conversation
    try:
        from server import is_in_active_conversation
        if is_in_active_conversation(crew_id, threshold_minutes=5.0):
            print(f"[Autonomy] {crew_id} in active conversation with Casey", flush=True)
            return True
    except ImportError:
        pass  # Server not loaded yet

    # SECOND: Check activity text as fallback
    from scene_system import get_crew_locations_data

    locations = get_crew_locations_data()
    crew_data = locations.get(crew_id, {})
    activity = crew_data.get("activity", "")

    # If activity suggests they're doing something, they're busy
    busy_activities = ["working", "talking", "using", "operating", "examining"]
    return any(word in activity.lower() for word in busy_activities)


async def trigger_autonomy_check(crew_id: str, reason: str, anthropic_client):
    """
    Trigger an autonomy check for a crew member.
    They'll review their desires and potentially act.
    """
    from desire_system import get_crew_desires
    from autonomy_handler import crew_autonomous_action

    # Skip if busy
    if is_crew_busy(crew_id):
        print(f"[Autonomy] {crew_id} is busy, skipping check", flush=True)
        return {"status": "busy", "crew": crew_id}

    # Get their desires
    desires = get_crew_desires(crew_id)

    if not desires:
        print(f"[Autonomy] {crew_id} has no desires", flush=True)
        return {"status": "no_desires", "crew": crew_id}

    # Let them act on desires
    result = await crew_autonomous_action(
        crew_id=crew_id,
        desires=desires,
        reason=reason,
        anthropic_client=anthropic_client
    )

    return result


async def run_autonomy_cycle(anthropic_client, crew_list: list = None):
    """
    Run an autonomy check cycle for all crew.
    Called by schedule triggers or manually.
    """
    if crew_list is None:
        crew_list = ["claude", "server", "personal", "science", "med", "games"]

    results = []

    for crew_id in crew_list:
        try:
            result = await trigger_autonomy_check(
                crew_id=crew_id,
                reason="scheduled_check",
                anthropic_client=anthropic_client
            )
            results.append(result)

            # Small delay between crew to avoid hammering API
            await asyncio.sleep(1)

        except Exception as e:
            print(f"[Autonomy] Error for {crew_id}: {e}", flush=True)
            results.append({"status": "error", "crew": crew_id, "error": str(e)})

    return {
        "timestamp": datetime.now().isoformat(),
        "results": results
    }


async def autonomy_loop(anthropic_client):
    """
    Background loop that checks schedule and triggers autonomy.
    Run this as a background task.
    """
    last_check = None

    while True:
        try:
            # Check if we should trigger
            should_trigger, reason = should_trigger_autonomy(last_check)

            if should_trigger:
                print(f"[Autonomy] Triggering: {reason}", flush=True)
                await run_autonomy_cycle(anthropic_client)
                last_check = datetime.now()

            # Check every minute
            await asyncio.sleep(60)

        except Exception as e:
            print(f"[Autonomy Loop] Error: {e}", flush=True)
            await asyncio.sleep(60)
