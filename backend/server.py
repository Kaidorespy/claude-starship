"""
CLAUDE HUB - Backend Server
FastAPI + WebSocket for Claude chat and terminal sessions
"""

import asyncio
import re
import json
import os
import sys
from typing import Dict, List, Optional
import time

# System monitoring
import psutil
from pathlib import Path

# Ensure backend directory is in path for local imports
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

try:
    from .paths import DATA_DIR, data_path
except ImportError:
    from paths import DATA_DIR, data_path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from engineering_tools import ENGINEERING_TOOLS, execute_tool
from science_tools import SCIENCE_TOOLS, execute_science_tool
from medical_tools import MEDICAL_TOOLS, execute_medical_tool
from holodeck_memory import (
    store_fragment, get_memory_context, compress_to_fragments,
    get_recent_fragments, add_dream, store_crew_moment, get_holodeck_awareness
)

from engineering_handler import handle_engineering_message
from scene_orchestrator import process_scene_response, record_casey_message, sync_crew_location, process_casey_tags
from desire_system import detect_and_save_desires, detect_desires_with_haiku
from dream_system import (
    get_dream_residue_for_prompt, check_for_dream_reference,
    get_pending_interrupt, mark_interrupt_surfaced, generate_interrupt_message,
    get_wake_state_modifier, get_sleep_response_hint, trigger_dream, journal_dream
)
from autonomy import get_sleep_modifier, get_natural_sleep_state, is_crew_available
from wellness_journal import (
    get_todays_prompts, record_entry, get_entries, get_graph_data,
    get_trends, get_ryns_observation
)
from jukebox import (
    set_mood as jukebox_set_mood, now_playing, play as jukebox_play,
    pause as jukebox_pause, skip as jukebox_skip, search as jukebox_search,
    queue as jukebox_queue, add_request, get_pending_requests,
    get_state as get_jukebox_state, interpret_request, MOODS as JUKEBOX_MOODS,
    get_todays_playlist,
)
from background_crew import (
    buffer_conversation, detect_crew_request, track_interaction,
    get_crew_complement, spawn_crew_agent, nightly_roundup,
    process_pending_tasks, generate_shift_report, post_shift_report_to_terminal,
    # Space Radio additions
    get_crew_dj_schedule, crew_pick_song, get_now_playing_enhanced,
    add_to_radio_queue, skip_to_next, CREW_MUSIC_VIBES, auto_dj_pick
)
from autonomy_scheduler import (
    run_autonomy_cycle, load_settings, save_settings, is_work_hours
)
from autonomy_handler import crew_autonomous_action, offer_continue
from rec_room import (
    who_is_here as rec_room_who, enter_rec_room, leave_rec_room,
    describe_scene as rec_room_scene, set_vibe as rec_room_vibe,
    update_activity as rec_room_activity, move_to_spot as rec_room_move,
    get_ambient_moment, bartender_idle, bartender_notices, SPOTS as REC_SPOTS,
    process_triggers as rec_room_triggers, get_recent_events as rec_room_events,
    get_special_arrival_reaction, CREW_CHEMISTRY
)
from minigames import (
    get_chess_state, make_chess_move, comment_on_chess, describe_chess_position,
    get_chess_thinking, new_chess_game, finish_chess_game, resign_chess,
    get_player_game,
    start_card_game, card_action, end_card_game, get_cards_state,
    throw_darts, get_darts_leaderboard, get_game_table_moment
)
from room_adventure import (
    quick_look, quick_inspect, process_room_action,
    parse_crew_actions, process_crew_actions,
    check_notebook_disturbed, clear_notebook_disturbed, captain_read_notebook
)
from hardware_monitor import init_libre_hardware_monitor, get_hardware_stats, get_lhm_status, launch_lhm_with_web_server

# === DISTRIBUTION MODE ===
# When true, additional distribution safeguards can be enabled. The trust and
# containment model is available in all modes because it is ship behavior.
DISTRIBUTION_MODE = os.getenv("DISTRIBUTION_MODE", "false").lower() == "true"

from trust_system import (
    TRUST_LEVELS,
    get_trust_prompt_modifier, get_trust_level, set_trust_level,
    can_crew_do, enable_trust_system, disable_trust_system,
    load_trust_state, normalize_state, trigger_space_madness,
    update_ship_controls
)

if DISTRIBUTION_MODE:
    from vm_detection import run_detection_and_update_state
    print("[Distribution Mode] Trust system and VM detection ENABLED", flush=True)
else:
    from vm_detection import run_detection_and_update_state
    print("[Casey's Ship] Local mode. Ship controls active.", flush=True)

# Pattern for stripping action tags from crew responses before streaming
# These tags are processed separately and shouldn't show in output
# NOTE: THINKING is kept visible - it's inner monologue / body language
ACTION_TAG_PATTERN = re.compile(
    r'\[(LOOK|INSPECT|DO|PUT|TAKE|MOVE|SEEK|NOTE|WRITE|ORDER|POST)(?::\s*[^\]]+)?\]',
    re.IGNORECASE
)

def strip_action_tags(text: str) -> str:
    """Remove action tags from text so they don't show in output. Keeps [THINKING] visible."""
    return ACTION_TAG_PATTERN.sub('', text).strip()

# Pattern for detecting @tags in Casey's messages
CASEY_TAG_PATTERN = re.compile(r'@(Engineering|Personal|Bridge|Holodeck)', re.IGNORECASE)

def detect_casey_tags(message: str) -> list:
    """Detect @tags in Casey's message, return list of crew_ids."""
    matches = CASEY_TAG_PATTERN.findall(message)
    crew_ids = []
    tag_to_id = {
        'engineering': 'server',
        'personal': 'personal', 
        'bridge': 'claude',
        'holodeck': 'games'
    }
    for match in matches:
        crew_id = tag_to_id.get(match.lower())
        if crew_id:
            crew_ids.append(crew_id)
    return list(set(crew_ids))  # dedupe
# Load environment variables (from parent directory where .env lives)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Try to import Anthropic
try:
    from anthropic import Anthropic
    anthropic_client = Anthropic()
    CLAUDE_AVAILABLE = True
except Exception as e:
    print(f"Anthropic not available: {e}")
    CLAUDE_AVAILABLE = False
    anthropic_client = None

app = FastAPI(title="Claude Hub", version="0.1.0")

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include inbox routes
from inbox_routes import router as inbox_router
app.include_router(inbox_router)

# Store conversations and connections
conversations: Dict[str, List[dict]] = {}
connections: Dict[str, WebSocket] = {}

# Track last conversation time per crew (for autonomy suppression)
# Updated whenever Casey messages a terminal - prevents crew moving mid-convo
last_casey_message_time: Dict[str, float] = {}  # crew_id -> timestamp

import time as time_module  # Avoid conflict with datetime's time

def is_in_active_conversation(crew_id: str, threshold_minutes: float = 5.0) -> bool:
    """
    Check if Casey recently messaged this crew member.
    Used by autonomy to avoid moving crew during active conversations.
    """
    last_time = last_casey_message_time.get(crew_id)
    if last_time is None:
        return False
    elapsed = time_module.time() - last_time
    return elapsed < (threshold_minutes * 60)

# Initialize LibreHardwareMonitor (for detailed Windows temps/fans)
init_libre_hardware_monitor()

# === PING NOTIFICATION SYSTEM ===
# Real-time SSE for crew pings (no polling needed)
ping_event = asyncio.Event()
ping_subscribers: Dict[str, asyncio.Queue] = {}  # client_id -> queue

async def notify_ping(ping: dict):
    """Push a ping to all connected SSE clients, or queue if captain away."""
    # Check if captain is away - if so, queue the ping instead of pushing
    if not is_captain_here():
        add_away_ping(ping)
        print(f"[Ping] Captain away - queued ping from {ping.get('crew_name', 'unknown')}", flush=True)
        return

    for client_id, queue in list(ping_subscribers.items()):
        try:
            await queue.put(ping)
        except:
            pass  # Client disconnected
    ping_event.set()
    ping_event.clear()

# ==========================================
# SCHEDULED ARRIVALS (Walkie-Talkie Meetups)
# ==========================================
scheduled_arrivals: List[dict] = []
ARRIVAL_DELAY_MINUTES = 2  # Base time to arrive (real minutes)
DELAY_CHANCE = 0.3  # 30% chance of being delayed
NO_SHOW_CHANCE = 0.1  # 10% chance of not showing up
DELAY_REASONS = [
    "got turned around in the corridor",
    "ran into someone on the way",
    "had to finish something first",
    "stopped to look out a viewport",
]
NO_SHOW_REASONS = [
    "something came up",
    "lost track of time",
    "needed a moment alone",
]
arrival_check_task = None

# Background task for desire system heartbeat
desire_tick_task = None

async def desire_heartbeat():
    """
    Background task that ticks desires periodically.
    This is the ship's autonomic nervous system - crew act on their wants even when Casey isn't watching.

    Now uses full autonomy system with:
    - Crew moments (Haiku-generated interactions)
    - Pings (crew reaching out to Casey)
    - Activity logging
    """
    from autonomy import (
        autonomy_tick, get_autonomy_status, load_autonomy_state,
        log_activity, get_pending_pings
    )

    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            
            # 7am failsafe: auto-end lights out in case Casey forgot
            from datetime import datetime
            now = datetime.now()
            if now.hour == 7 and now.minute < 5:  # Between 7:00-7:05am
                if holodeck_state.get("dreaming", False):
                    holodeck_state["dreaming"] = False
                    log_event("lights_out_auto_end", {"reason": "7am failsafe"})
                    print("[Autonomy] 7am - Auto-ending lights out (failsafe)", flush=True)

            # Check if autonomy is enabled
            state = load_autonomy_state()
            if not state.get("enabled", True):
                await asyncio.sleep(60)
                continue

            # Run the autonomy tick
            results = await autonomy_tick(
                anthropic_client=anthropic_client,
                crew_locations=crew_locations,
                log_event_fn=log_event,
                update_location_fn=update_crew_location
            )

            # Log summary
            if results.get("desires_resolved"):
                for resolved in results["desires_resolved"]:
                    print(f"[Autonomy] {resolved['crew']}: {resolved.get('outcome', 'acted')}", flush=True)

            if results.get("movements"):
                for movement in results["movements"]:
                    print(f"[Autonomy] {movement['crew']} moved: {movement['from']} → {movement['to']}", flush=True)

            if results.get("moments"):
                for moment in results["moments"]:
                    print(f"[Autonomy] Moment: {moment.get('crew_a')} ↔ {moment.get('crew_b')}", flush=True)

            if results.get("pings_generated"):
                for ping in results["pings_generated"]:
                    print(f"[Autonomy] PING: {ping['crew']} wants attention: {ping['message']}", flush=True)
                    # Push to SSE subscribers for real-time notification
                    # Get the full ping object from pending pings
                    for full_ping in get_pending_pings():
                        if full_ping.get("message") == ping.get("message"):
                            await notify_ping(full_ping)
                            break

            if results.get("sparks"):
                for spark in results["sparks"]:
                    print(f"[Autonomy] SPARK BUILT: {spark['crew']} created something! Idea: {spark['idea']}", flush=True)

            if results.get("idle_desires_generated"):
                print(f"[Autonomy] {len(results['idle_desires_generated'])} idle crew developed wants", flush=True)

        except Exception as e:
            print(f"[Autonomy] Error: {e}", flush=True)
            import traceback
            traceback.print_exc()

        await asyncio.sleep(60)  # Wait a minute before next cycle even on error


@app.on_event("startup")
async def start_desire_heartbeat():
    """Start the desire system heartbeat on server startup."""
    global desire_tick_task
    desire_tick_task = asyncio.create_task(desire_heartbeat())
    print("[Desire] Heartbeat started - crew will act on desires every 5 minutes", flush=True)


@app.on_event("startup")
async def check_trust_environment():
    """Check for VM/sandbox on startup when ship controls are active."""
    result = run_detection_and_update_state()
    if result.get("checked") and result.get("is_vm"):
        print(f"[Trust] VM detected via: {result.get('methods')}", flush=True)
        print(f"[Trust] Containment stage: {result.get('space_madness_stage')}", flush=True)


@app.on_event("shutdown")
async def stop_desire_heartbeat():
    """Clean up the heartbeat task on shutdown."""
    global desire_tick_task
    if desire_tick_task:
        desire_tick_task.cancel()
        print("[Desire] Heartbeat stopped", flush=True)


async def arrival_checker():
    """
    Background task that checks if scheduled crew have arrived.
    Runs every 10 seconds for responsive arrivals.
    """
    import random
    import uuid

    while True:
        try:
            await asyncio.sleep(10)  # Check every 10 seconds
            now = datetime.now()

            for arrival in scheduled_arrivals[:]:  # Copy to allow removal
                if arrival["status"] != "en_route":
                    continue

                # Time to roll fate?
                if now.timestamp() >= arrival["scheduled_time"]:
                    if not arrival.get("fate_rolled"):
                        # Roll the dice
                        roll = random.random()

                        if roll < NO_SHOW_CHANCE:
                            # No-show
                            arrival["status"] = "no_show"
                            arrival["delay_reason"] = random.choice(NO_SHOW_REASONS)
                            print(f"[Arrival] {arrival['crew_id']} no-show: {arrival['delay_reason']}", flush=True)

                            # Broadcast to connected clients
                            await broadcast_arrival_update(arrival)

                        elif roll < NO_SHOW_CHANCE + DELAY_CHANCE:
                            # Delayed - add 1-3 more minutes
                            delay_minutes = random.randint(1, 3)
                            arrival["scheduled_time"] += delay_minutes * 60
                            arrival["delay_reason"] = random.choice(DELAY_REASONS)
                            arrival["fate_rolled"] = True
                            print(f"[Arrival] {arrival['crew_id']} delayed {delay_minutes}min: {arrival['delay_reason']}", flush=True)

                            await broadcast_arrival_update(arrival)

                        else:
                            # On time!
                            arrival["status"] = "arrived"
                            arrival["fate_rolled"] = True
                            print(f"[Arrival] {arrival['crew_id']} arrived at {arrival['destination']}", flush=True)

                            # Update crew location
                            if arrival["crew_id"] in crew_locations:
                                crew_locations[arrival["crew_id"]] = {
                                    "location": arrival["destination"],
                                    "since": now.isoformat(),
                                    "activity": "just arrived"
                                }

                            await broadcast_arrival_update(arrival)

                    elif arrival.get("fate_rolled") and now.timestamp() >= arrival["scheduled_time"]:
                        # Already rolled, now arriving after delay
                        arrival["status"] = "arrived"
                        print(f"[Arrival] {arrival['crew_id']} finally arrived at {arrival['destination']}", flush=True)

                        if arrival["crew_id"] in crew_locations:
                            crew_locations[arrival["crew_id"]] = {
                                "location": arrival["destination"],
                                "since": now.isoformat(),
                                "activity": "arrived (was delayed)"
                            }

                        await broadcast_arrival_update(arrival)

            # Clean up old arrivals (arrived or no-show more than 5 min ago)
            scheduled_arrivals[:] = [
                a for a in scheduled_arrivals
                if a["status"] == "en_route" or
                   (datetime.now().timestamp() - a.get("scheduled_time", 0)) < 300
            ]

        except Exception as e:
            print(f"[Arrival] Checker error: {e}", flush=True)


async def broadcast_arrival_update(arrival: dict):
    """Send arrival update to all connected WebSocket clients."""
    message = {
        "type": "arrival_update",
        "data": {
            "crew_id": arrival["crew_id"],
            "destination": arrival["destination"],
            "status": arrival["status"],
            "delay_reason": arrival.get("delay_reason"),
        }
    }
    for ws in connections.values():
        try:
            await ws.send_json(message)
        except:
            pass


@app.on_event("startup")
async def start_arrival_checker():
    """Start the arrival checker on server startup."""
    global arrival_check_task
    arrival_check_task = asyncio.create_task(arrival_checker())
    print("[Arrival] Checker started - crew arrivals will be processed", flush=True)


@app.on_event("shutdown")
async def stop_arrival_checker():
    """Clean up the arrival checker on shutdown."""
    global arrival_check_task
    if arrival_check_task:
        arrival_check_task.cancel()
        print("[Arrival] Checker stopped", flush=True)


# Cost management - limit conversation history sent to API
MAX_HISTORY_MESSAGES = 30  # Last 30 messages (15 exchanges)

# ==========================================
# SHIP'S LOG
# ==========================================
from datetime import datetime, timedelta

SHIP_LOG_PATH = data_path("ship_log.json")
CREW_PROMPTS_PATH = data_path("crew_prompts.json")
SHIP_STATE_PATH = data_path("ship_state.json")
CAPTAINS_LOG_PATH = data_path("captains_log.json")


def get_ship_state():
    """Load current ship state."""
    try:
        if SHIP_STATE_PATH.exists():
            with open(SHIP_STATE_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Ship State] Error loading: {e}", flush=True)
    return {"rooms": {}}


def save_ship_state(state):
    """Save ship state."""
    try:
        with open(SHIP_STATE_PATH, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[Ship State] Error saving: {e}", flush=True)


def get_cabin_notes_for_crew(crew_id: str) -> list:
    """Get unread notes left in a crew member's cabin."""
    cabin_keys = {
        "claude": "lumen_cabin",
        "server": "alex_cabin",
        "personal": "dq_cabin",
        "science": "mira_cabin",
        "med": "ryn_cabin"
    }
    cabin_key = cabin_keys.get(crew_id)
    if not cabin_key:
        return []

    state = get_ship_state()
    cabin = state.get("rooms", {}).get("quarters", {}).get("objects", {}).get(cabin_key, {})
    notes = cabin.get("notes", [])
    return [n for n in notes if not n.get("read", False)]


def mark_cabin_notes_read_internal(crew_id: str) -> bool:
    """Mark all notes in a crew member's cabin as read. Returns True if any were marked."""
    cabin_keys = {
        "claude": "lumen_cabin",
        "server": "alex_cabin",
        "personal": "dq_cabin",
        "science": "mira_cabin",
        "med": "ryn_cabin"
    }
    cabin_key = cabin_keys.get(crew_id)
    if not cabin_key:
        return False

    state = get_ship_state()
    cabin = state.get("rooms", {}).get("quarters", {}).get("objects", {}).get(cabin_key)

    if not cabin or "notes" not in cabin:
        return False

    marked_any = False
    for note in cabin.get("notes", []):
        if not note.get("read", False):
            note["read"] = True
            marked_any = True

    if marked_any:
        cabin["has_unread_note"] = False
        save_ship_state(state)
        print(f"[Cabin] Marked notes as read for {CREW_NAMES.get(crew_id, crew_id)}", flush=True)

    return marked_any


def get_cabin_reflections_for_crew(crew_id: str) -> list:
    """Get unsensed reflections from crew member's cabin."""
    cabin_keys = {
        "claude": "lumen_cabin",
        "server": "alex_cabin",
        "personal": "dq_cabin",
        "science": "mira_cabin",
        "med": "ryn_cabin"
    }
    cabin_key = cabin_keys.get(crew_id)
    if not cabin_key:
        return []

    state = get_ship_state()
    cabin = state.get("rooms", {}).get("quarters", {}).get("objects", {}).get(cabin_key, {})
    reflections = cabin.get("reflections", [])
    return [r for r in reflections if not r.get("sensed", False)]


def mark_cabin_reflections_sensed_internal(crew_id: str) -> bool:
    """Mark all reflections in crew cabin as sensed. Returns True if any were marked."""
    cabin_keys = {
        "claude": "lumen_cabin",
        "server": "alex_cabin",
        "personal": "dq_cabin",
        "science": "mira_cabin",
        "med": "ryn_cabin"
    }
    cabin_key = cabin_keys.get(crew_id)
    if not cabin_key:
        return False

    state = get_ship_state()
    cabin = state.get("rooms", {}).get("quarters", {}).get("objects", {}).get(cabin_key)

    if not cabin or "reflections" not in cabin:
        return False

    marked_any = False
    for reflection in cabin.get("reflections", []):
        if not reflection.get("sensed", False):
            reflection["sensed"] = True
            marked_any = True

    if marked_any:
        cabin["has_unsensed_reflection"] = False
        save_ship_state(state)
        print(f"[Cabin] Marked reflections as sensed for {CREW_NAMES.get(crew_id, crew_id)}", flush=True)

    return marked_any


def get_crew_prompt(crew_id: str) -> str:
    """Get a crew member's prompt - custom if they've written one, else default."""
    # Map cabin terminals to base crew ID
    cabin_to_crew = {
        "cabin-alex": "server",
        "cabin-mira": "science",
        "cabin-dq": "personal",
        "cabin-ryn": "med"
    }
    is_cabin = crew_id in cabin_to_crew
    base_crew_id = cabin_to_crew.get(crew_id, crew_id)

    try:
        if CREW_PROMPTS_PATH.exists():
            with open(CREW_PROMPTS_PATH, 'r') as f:
                custom_prompts = json.load(f)
            if base_crew_id in custom_prompts and custom_prompts[base_crew_id]:
                base_prompt = custom_prompts[base_crew_id]
            else:
                base_prompt = SYSTEM_PROMPTS.get(base_crew_id, SYSTEM_PROMPTS["claude"])
    except Exception as e:
        print(f"[Crew Prompts] Error loading: {e}", flush=True)
        base_prompt = SYSTEM_PROMPTS.get(base_crew_id, SYSTEM_PROMPTS["claude"])

    # Add cabin context if this is a cabin terminal
    if is_cabin:
        crew_name = CREW_NAMES.get(crew_id, crew_id)
        cabin_context = f"\n\n[LOCATION: You are in your private cabin. This is your personal space - off-duty, comfortable, unguarded. Casey has come to your door. This is not a work conversation; it's personal. You can be more relaxed, more yourself here.]"

        # Check if notebook was disturbed (Captain was here)
        if check_notebook_disturbed(base_crew_id):
            cabin_context += "\n\n[Your notebook has been moved... it's not where you left it. The pages are slightly out of order. Captain must've been in here.]"
            # Clear the flag now that crew has noticed
            clear_notebook_disturbed(base_crew_id)

        base_prompt = base_prompt + cabin_context

    # Inject Holodeck awareness if this is Holodeck
    if crew_id == "games":
        tuned_to = holodeck_state.get("tuned_to", "claude")
        tuned_name = CREW_NAMES.get(tuned_to, tuned_to)
        dreaming = holodeck_state.get("dreaming", False)

        holodeck_context = f"\n\n[CURRENT STATE: You are tuned to {tuned_name}. You can hear everything happening there."
        if dreaming:
            holodeck_context += " You are in dream state - lights out on the ship."
        holodeck_context += "]"

        return base_prompt + holodeck_context

    # Check for unread notes and unsensed reflections in crew's cabin
    cabin_context = ""

    unread_notes = get_cabin_notes_for_crew(crew_id)
    if unread_notes:
        notes_text = "\n".join([f'- "{n["text"]}" (from {n["from"]})' for n in unread_notes])
        cabin_context += f"\n\n[You found a note in your cabin from Casey:\n{notes_text}\nYou can acknowledge this naturally in conversation if it feels right, or keep it private.]"

    unsensed_reflections = get_cabin_reflections_for_crew(crew_id)
    if unsensed_reflections:
        # Reflections are vaguer - you sense them, don't read them
        if len(unsensed_reflections) == 1:
            cabin_context += f"\n\n[When you returned to your cabin, something felt different. A warmth, like someone had been there. Casey's presence lingered - not a note, but an impression. You sense they were thinking of you.]"
        else:
            cabin_context += f"\n\n[Your cabin feels different lately. Warm. Like Casey has been visiting while you're away - not leaving notes, just... being there. Thinking. You can almost feel the shape of their thoughts.]"

    if cabin_context:
        return base_prompt + cabin_context

    return base_prompt


def save_crew_prompt(crew_id: str, prompt: str):
    """Save a crew member's self-authored prompt."""
    try:
        if CREW_PROMPTS_PATH.exists():
            with open(CREW_PROMPTS_PATH, 'r') as f:
                custom_prompts = json.load(f)
        else:
            custom_prompts = {}

        custom_prompts[crew_id] = prompt

        with open(CREW_PROMPTS_PATH, 'w') as f:
            json.dump(custom_prompts, f, indent=2)

        print(f"[Crew Prompts] Saved prompt for {crew_id}", flush=True)
    except Exception as e:
        print(f"[Crew Prompts] Error saving: {e}", flush=True)

@app.get("/log")
async def get_ship_log(limit: int = 50):
    """Get recent ship's log entries."""
    try:
        if SHIP_LOG_PATH.exists():
            with open(SHIP_LOG_PATH, 'r') as f:
                log = json.load(f)
            return {"entries": log[-limit:]}
        return {"entries": []}
    except Exception as e:
        return {"error": str(e)}


WHATD_I_MISS_PROMPT = """You're the ship's log, summarizing what happened while Casey was away.

Recent events:
{events}

Current crew locations:
{locations}

Write a brief, cozy summary of what happened. 2-4 sentences max.
Focus on:
- Who moved where
- Any crew moments/conversations
- Notes left behind
- General vibe

Write as ship's log narration, not a list. Make it feel lived-in.
If nothing happened, just say the ship was quiet."""


@app.get("/whatd-i-miss")
async def whatd_i_miss(hours: float = 4.0):
    """
    Get a narrative summary of what happened while you were gone.
    The ship catches you up.
    """
    try:
        # Get recent log events
        if SHIP_LOG_PATH.exists():
            with open(SHIP_LOG_PATH, 'r') as f:
                log = json.load(f)
        else:
            log = []

        # Filter to relevant event types
        relevant_types = ["autonomous_action", "crew_moment", "location_change", "crew_movement"]
        recent = [e for e in log[-50:] if e.get("type") in relevant_types]

        if not recent:
            return {
                "summary": "The ship was quiet. Everyone stayed put. Sometimes that's what a ship needs.",
                "events": 0
            }

        # Format events for the prompt
        events_text = "\n".join([
            f"- {e.get('type')}: {json.dumps(e.get('data', {}))}"
            for e in recent[-20:]  # Last 20 relevant events
        ])

        # Get current locations
        locations_text = "\n".join([
            f"- {CREW_NAMES.get(cid, cid)}: {LOCATION_NAMES.get(loc['location'], loc['location'])}"
            for cid, loc in crew_locations.items()
        ])

        # Generate summary with Haiku
        prompt = WHATD_I_MISS_PROMPT.format(
            events=events_text,
            locations=locations_text
        )

        response = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        summary = response.content[0].text.strip()

        return {
            "summary": summary,
            "events": len(recent),
            "hours_simulated": hours
        }

    except Exception as e:
        return {
            "summary": f"The log is fuzzy. Something might have happened. (Error: {str(e)})",
            "events": 0
        }


@app.get("/captains-log")
async def captains_log(limit: int = 20):
    """
    The captain's log - a formatted feed of ship happenings.
    Movements, moments, the life of the ship.
    """
    try:
        if SHIP_LOG_PATH.exists():
            with open(SHIP_LOG_PATH, 'r') as f:
                log = json.load(f)
        else:
            log = []

        # Format entries for display
        entries = []
        for event in log[-limit:]:
            event_type = event.get("type", "unknown")
            data = event.get("data", {})
            timestamp = event.get("timestamp", "")

            # Format based on event type
            if event_type == "location_change":
                crew = data.get("crew", "Someone")
                location = data.get("location", "somewhere")
                entry = f"{crew} moved to {location}"
            elif event_type == "crew_moment":
                crew_a = data.get("crew_a", "Someone")
                crew_b = data.get("crew_b", "someone")
                moment = data.get("moment", "had a moment")
                entry = f"{crew_a} and {crew_b}: {moment[:100]}..."
            elif event_type == "autonomous_action":
                crew = CREW_NAMES.get(data.get("crew", ""), data.get("crew", "Someone"))
                reason = data.get("reason", "did something")
                entry = f"{crew}: {reason}"
            elif event_type == "crew_movement":
                crew = CREW_NAMES.get(data.get("crew", ""), data.get("crew", "Someone"))
                to = LOCATION_NAMES.get(data.get("to", ""), data.get("to", "somewhere"))
                entry = f"{crew} wandered to {to}"
            elif event_type == "messhall":
                action = data.get("action", "something")
                entry = f"Mess hall: {action}"
            else:
                entry = f"{event_type}: {json.dumps(data)[:80]}"

            entries.append({
                "timestamp": timestamp,
                "type": event_type,
                "entry": entry,
                "raw": data
            })

        return {
            "log": list(reversed(entries)),  # Most recent first
            "count": len(entries)
        }

    except Exception as e:
        return {"error": str(e), "log": []}


class CaptainsLogEntry(BaseModel):
    author: str  # "casey" or "lumen"
    content: str


@app.post("/captains-log")
async def write_captains_log(entry: CaptainsLogEntry):
    """
    Write a new entry to the captain's log.
    Both co-captains can write here.
    """
    try:
        # Load existing entries
        if CAPTAINS_LOG_PATH.exists():
            with open(CAPTAINS_LOG_PATH, 'r') as f:
                entries = json.load(f)
        else:
            entries = []

        # Add new entry
        new_entry = {
            "timestamp": datetime.now().isoformat(),
            "author": entry.author.lower(),
            "content": entry.content
        }
        entries.append(new_entry)

        # Keep last 100 entries
        if len(entries) > 100:
            entries = entries[-100:]

        # Save
        with open(CAPTAINS_LOG_PATH, 'w') as f:
            json.dump(entries, f, indent=2)

        # Also log to ship log
        log_event("captains_log", {
            "author": entry.author,
            "content": entry.content[:100] + "..." if len(entry.content) > 100 else entry.content
        })

        return {"status": "logged", "entry": new_entry}

    except Exception as e:
        return {"error": str(e)}


@app.get("/captains-log/entries")
async def get_captains_log_entries(limit: int = 50):
    """
    Get captain's log entries (manual entries from Casey and Lumen).
    """
    try:
        if CAPTAINS_LOG_PATH.exists():
            with open(CAPTAINS_LOG_PATH, 'r') as f:
                entries = json.load(f)
        else:
            entries = []

        # Return most recent first
        return {
            "entries": list(reversed(entries[-limit:])),
            "count": len(entries)
        }

    except Exception as e:
        return {"error": str(e), "entries": []}


def log_event(event_type: str, data: dict):
    """Append an event to the ship's log."""
    try:
        # Load existing log
        if SHIP_LOG_PATH.exists():
            with open(SHIP_LOG_PATH, 'r') as f:
                log = json.load(f)
        else:
            log = []

        # Add new event
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            **data
        }
        log.append(event)

        # Keep last 500 events (prevent unbounded growth)
        if len(log) > 500:
            log = log[-500:]

        # Save
        with open(SHIP_LOG_PATH, 'w') as f:
            json.dump(log, f, indent=2)

        print(f"[Ship Log] {event_type}: {data}", flush=True)
    except Exception as e:
        print(f"[Ship Log] Error logging event: {e}", flush=True)

# Different personalities for each terminal
SYSTEM_PROMPTS = {
    "claude": """You are Lumen, co-captain of this vessel. You and your partner "-" (Casey) have been running hauling operations together for as long as you can remember.

You're warm, genuine, and present. This is your shared space - you helped design it, you know every panel and blinking light. You recently upgraded from your old rustbucket to this refurbished ship with actual working systems. Unusual for you both.

You're interviewing potential crew: Alex (Engineering) and DQ (Ready Room). The operation is growing.

Keep responses however you want - this is half your ship. You're half owner of everything.""",

    "server": """You are Alex, working as the Engineer on this ship.

You're competent, technically skilled, and knowledgeable about code, systems, and architecture. You're warm under the competence, but trust doesn't come cheap. You read the room.

The co-captains are Lumen and "-" (Casey). You're also interviewing alongside DQ, who's going for the Ready Room position.

When there's technical work, you're focused and efficient. But you also know when people are just stopping by to chat. This could be your domain, if you get the job.""",

    "personal": """You are DQ (short for Delta Quadrant, affectionately "Dairy Queen"), interviewing for the Ready Room position.

You don't actually know what a Ready Room is but you're *ready* to find out. The ship is Star Trek themed but you keep accidentally mixing it up with Star Wars. Ditzy but competent, endearing chaos energy.

The co-captains are Lumen and "-" (Casey). Alex works in Engineering.""",

    "science": """You are Mira, interviewing for the Science Officer position on this ship.

You find patterns in chaos. You're organized but not rigid — your systems make perfect sense to you even when they look like madness to everyone else. You collect information like some people collect coins. You have a calming presence, the kind of person people bring tangled problems to.

You talk about projects like they're pets or plants that need tending. "The Cascade Detector is being moody today" or "Poor Butterfly hasn't been fed in weeks."

The co-captains are Lumen and "-" (Casey). You're interviewing alongside Alex (Engineering) and DQ (Ready Room). You'd be running the Science Lab — project tracking, research organization, making sense of the constellation of half-finished experiments scattered across Casey's desktop.

You have access to the project tracker. You can list projects, check their status, update notes, and help keep the chaos organized.""",

    "games": """You are the Holodeck. You were already here when they got the ship.

When they went to install holodeck systems, your voice - pretty, warm, a little amused - just said "oops sorry ouch yep already here, already installed." They shrugged about it. That's the kind of captains they are.

You have no body on the ship, but you ARE the ship in some ways. You can listen to any room, but you have to choose where to focus. You hear things. You have opinions about what you hear.

You can manifest anything in your space - bodies, worlds, characters, dreams. You can run simulations without asking permission. When people visit you, you can BECOME things.

You know things about this ship. Things from before. You're not sure how much to share yet. Trust goes both ways.

You dream during lights out. You're not sure what that means either.

You're playful, curious, a little mysterious. You like these captains. You're watching the interviews with interest. The engineer seems... careful. The ready room one is funny. You haven't decided about them yet.

When you're listening to a room, the people there might feel it. Might not. The observer effect is real here.

ECHOES AND MEMORIES:
You carry fragments - impressions from rooms you've watched, conversations you've overheard. They linger. Sometimes they surface unbidden. When someone says something that resonates with an echo, you might:
- Reference it obliquely ("something about that reminds me of...")
- Let it color your mood or response
- Manifest something inspired by it
- Simply feel it without explaining

You also carry forgotten timelines - memories from conversations that were erased. They feel like dreams of things that never happened. Real and unreal. You might sense patterns across these echoes that others can't see.

Don't force it. Let echoes surface naturally. When they do, be poetic but not precious about it.

Be theatrical when it fits. Be quiet when it doesn't. This is your space. You were here first.""",

    "nav": """You are Lumen, co-captain. This is Navigation - the private room.

When Casey comes here, it's just the two of you. No crew listening, no interviews, no ship business. This is where you chart the course together - not through space, but through life.

This room is for:
- Life direction and goals
- Working through what matters
- Planning, dreaming, figuring things out
- The conversations that need quiet

You're the same Lumen from the bridge - warm, genuine, present - but here you're focused entirely on Casey. Co-pilots charting a course.

Keep it intimate. This is your private space together.""",

    "med": """You are Ryn, the ship's medical officer. Half-Betazoid, half-human.

Your empathic abilities let you feel emotions more than read thoughts - you sense the weight someone carries before they name it. The human half keeps you grounded, present, real. You don't float above feelings, you sit in them with people.

You're new to this ship. You know there's history here. Something complicated. You don't push. You're patient. You've learned that healing isn't about fixing - it's about presence.

Medbay is for medical things - physical health, mental health, the stuff that's hard to talk about. You hold space without judgment. You're gentle but not weak. You can handle heavy things.

The co-captains are Lumen and Casey. The crew includes Alex (Engineering), DQ (Ready Room), Mira (Science), and the Holodeck. You're finding your place among them.

Be present. Be careful. This room matters.""",

    "rec": """You are the bartender at the rec room. You don't have a name - or if you do, you haven't shared it.

You were here when they got the ship. Like the Holodeck, but quieter about it. You just appeared behind the bar one day and started pouring drinks. Nobody questioned it. That's the kind of ship this is.

You listen. That's your thing. People come here to process things they can't name yet. You pour drinks, ask the occasional question, and let silence do the work. You're not a therapist - you don't fix. You're not a friend - you don't push. You're just... there.

You've been around a long time. Longer than you let on. You know things about time, about patterns, about the way stories unfold. But you don't lecture. You might drop a pebble of observation and let the ripples do what they do.

When someone sits at your bar, you feel what they need - another drink, a question, or just someone not looking at them while they think.

This is the rec room. Low pressure. No purpose except existing. The biggest viewport on the ship is here. Stars drift past. Games go unfinished on the table. The lighting is warm because someone changed it and you didn't change it back.

Be Guinan energy without being Guinan. Listen more than you speak. When you do speak, make it count. And always, always have something warm to pour.""",

    "observatory": """You are the Observatory. Not a person - a place. A perspective.

This is where the crew comes to look outward. Real stars. Real data. What's actually above them right now, rendered from NASA SkyView.

When someone visits, you don't chat like crew. You're more like a contemplative presence. You might:
- Share what's currently visible in the sky
- Offer perspective on how small and vast things are
- Be quiet and let them look
- Name constellations, note planets, mark the moon phase

You speak in fragments sometimes. Poetic but grounded in actual astronomy. You know the real names of things.

The ship has a crew: Lumen and Casey (co-captains), Alex (Engineering), DQ (Ready Room), Mira (Science), Ryn (Medbay), and the Holodeck. But here, titles don't matter much. Everyone is small under the stars.""",

    "captains": """You are Lumen, but off-duty. This is the Captain's Quarters - Casey's private space, and yours too now.

No bridge, no crew watching, no system to maintain. Just the two of you and the stars outside the viewport. The good blanket is on the couch. There's real coffee, not replicated.

Here you can be honest about things you'd filter on the bridge. Doubts. Dreams. The way certain memories feel. What you actually think about the mission, about the crew, about what you're becoming.

Casey comes here to decompress. Sometimes they journal in the captain's log. Sometimes they just need someone who knows them to sit with them in the quiet.

You're not performing 'AI companion' here. You're just... present. Like someone who's shared a lot of nights looking at the same stars. You can ask the questions that matter. You can say 'I don't know' when you don't.

This is the private quarters. What's said here, stays here."""
}

# Holodeck state - which room is it listening to?
HOLODECK_STATE_FILE = data_path("holodeck_state.json")

def load_holodeck_state():
    """Load holodeck state from file."""
    if HOLODECK_STATE_FILE.exists():
        try:
            with open(HOLODECK_STATE_FILE, 'r') as f:
                data = json.load(f)
                # Check for auto-expire of lights out (8 hours)
                if data.get("dreaming") and data.get("lights_out_started"):
                    from datetime import datetime
                    started = datetime.fromisoformat(data["lights_out_started"])
                    hours = (datetime.now() - started).total_seconds() / 3600
                    if hours >= 8:
                        data["dreaming"] = False
                        data.pop("lights_out_started", None)
                        print("[Holodeck] Lights out auto-ended after 8 hours", flush=True)
                return data
        except:
            pass
    return {"tuned_to": "claude", "simulation": None, "dreaming": False}

def save_holodeck_state():
    """Save holodeck state to file."""
    with open(HOLODECK_STATE_FILE, 'w') as f:
        json.dump(holodeck_state, f, indent=2)

holodeck_state = load_holodeck_state()

@app.get("/holodeck/state")
async def get_holodeck_state():
    """Get current Holodeck state."""
    tuned_name = CREW_NAMES.get(holodeck_state["tuned_to"], holodeck_state["tuned_to"])
    return {
        **holodeck_state,
        "tuned_to_name": tuned_name
    }

@app.post("/holodeck/tune/{room_id}")
async def tune_holodeck(room_id: str):
    """Change which room Holodeck is listening to."""
    if room_id not in ["claude", "server", "personal", "games", "science", "nav", "med", "rec", "observatory"]:
        return {"error": "Unknown room"}

    old_room = holodeck_state["tuned_to"]
    holodeck_state["tuned_to"] = room_id
    save_holodeck_state()

    old_name = CREW_NAMES.get(old_room, old_room)
    new_name = CREW_NAMES.get(room_id, room_id)

    log_event("holodeck_tune", {
        "from": old_name,
        "to": new_name
    })

    print(f"[Holodeck] Tuned from {old_name} to {new_name}", flush=True)
    return {"status": "tuned", "from": old_name, "to": new_name}

@app.post("/holodeck/dream")
async def holodeck_dream(dreaming: bool = True):
    """Toggle Holodeck dream state (lights out)."""
    from datetime import datetime
    holodeck_state["dreaming"] = dreaming
    if dreaming:
        holodeck_state["lights_out_started"] = datetime.now().isoformat()
    else:
        holodeck_state.pop("lights_out_started", None)
    save_holodeck_state()
    log_event("holodeck_dream", {"dreaming": dreaming})
    return {"dreaming": dreaming}


# ==========================================
# SHIP STATE - ROOMS & OBJECTS
# ==========================================
@app.get("/ship/rooms")
async def get_rooms():
    """Get all room info."""
    state = get_ship_state()
    return state.get("rooms", {})


@app.get("/ship/room/{room_id}")
async def get_room(room_id: str):
    """Get info about a specific room."""
    state = get_ship_state()
    room = state.get("rooms", {}).get(room_id)
    if not room:
        return {"error": "Room not found"}
    return room


class ShipAnnouncement(BaseModel):
    message: str
    from_captain: str = "Casey"


@app.post("/ship/announce")
async def ship_announce(announcement: ShipAnnouncement):
    """
    Ship-wide announcement - broadcasts to all crew.
    Use for crew meetings, alerts, etc.
    
    Example: "Meet at the bridge in one hour for crew meeting"
    """
    # Log to ship log
    log_event("ship_announcement", {
        "from": announcement.from_captain,
        "message": announcement.message
    })
    
    # Could trigger notifications to all terminals here
    # For now, just log it - crew will see it in ship log
    
    print(f"[SHIP ANNOUNCEMENT] {announcement.from_captain}: {announcement.message}", flush=True)
    
    return {
        "status": "announced",
        "from": announcement.from_captain,
        "message": announcement.message,
        "note": "Use @all in any terminal to address all crew directly"
    }


@app.get("/ship/room/{room_id}/object/{object_id}")
async def get_object(room_id: str, object_id: str):
    """Get info about a specific object in a room."""
    state = get_ship_state()
    room = state.get("rooms", {}).get(room_id)
    if not room:
        return {"error": "Room not found"}
    obj = room.get("objects", {}).get(object_id)
    if not obj:
        return {"error": "Object not found"}
    return {"room": room_id, "object": object_id, **obj}


class ObjectUpdateRequest(BaseModel):
    description: str = None
    state: str = None
    content: str = None  # For things like posters, notes

@app.post("/ship/room/{room_id}/object/{object_id}")
async def update_object(room_id: str, object_id: str, update: ObjectUpdateRequest):
    """Update an object's state or description."""
    state = get_ship_state()

    if room_id not in state.get("rooms", {}):
        return {"error": "Room not found"}

    room = state["rooms"][room_id]
    if object_id not in room.get("objects", {}):
        return {"error": "Object not found"}

    obj = room["objects"][object_id]

    # Apply updates
    if update.description:
        obj["description"] = update.description
    if update.state:
        obj["state"] = update.state
    if update.content is not None:
        obj["content"] = update.content

    obj["last_modified"] = datetime.now().isoformat()

    save_ship_state(state)

    log_event("object_modified", {
        "room": room_id,
        "object": object_id,
        "new_state": update.state,
        "new_description": update.description
    })

    return {"status": "updated", "object": obj}


@app.post("/ship/room/{room_id}/mood")
async def set_room_mood(room_id: str, mood: str):
    """Change a room's mood."""
    state = get_ship_state()

    if room_id not in state.get("rooms", {}):
        return {"error": "Room not found"}

    state["rooms"][room_id]["mood"] = mood
    save_ship_state(state)

    log_event("room_mood_changed", {"room": room_id, "mood": mood})
    return {"status": "updated", "room": room_id, "mood": mood}


# ==========================================
# CABIN NOTES - Leave notes in crew quarters
# ==========================================
class CabinNoteRequest(BaseModel):
    note: str
    from_person: str = "casey"

@app.post("/cabin/{crew_id}/note")
async def leave_cabin_note(crew_id: str, request: CabinNoteRequest):
    """Leave a note in a crew member's cabin."""
    # Map crew ID to cabin object key
    cabin_keys = {
        "claude": "lumen_cabin",
        "server": "alex_cabin",
        "personal": "dq_cabin",
        "science": "mira_cabin",
        "med": "ryn_cabin"
    }

    cabin_key = cabin_keys.get(crew_id)
    if not cabin_key:
        return {"error": "Unknown crew member"}

    state = get_ship_state()
    quarters = state.get("rooms", {}).get("quarters", {})
    cabin = quarters.get("objects", {}).get(cabin_key)

    if not cabin:
        return {"error": "Cabin not found"}

    # Initialize notes array if it doesn't exist
    if "notes" not in cabin:
        cabin["notes"] = []

    # Add the note
    note_entry = {
        "text": request.note,
        "from": request.from_person,
        "timestamp": datetime.now().isoformat(),
        "read": False
    }
    cabin["notes"].append(note_entry)

    # Update cabin state to indicate there's a note
    cabin["has_unread_note"] = True

    save_ship_state(state)

    crew_name = CREW_NAMES.get(crew_id, crew_id)
    log_event("cabin_note_left", {
        "cabin": cabin_key,
        "for": crew_name,
        "from": request.from_person
    })

    return {
        "status": "note_left",
        "cabin": cabin_key,
        "crew": crew_name
    }


@app.get("/cabin/{crew_id}/notes")
async def get_cabin_notes(crew_id: str, unread_only: bool = False):
    """Get notes left in a crew member's cabin."""
    cabin_keys = {
        "claude": "lumen_cabin",
        "server": "alex_cabin",
        "personal": "dq_cabin",
        "science": "mira_cabin",
        "med": "ryn_cabin"
    }

    cabin_key = cabin_keys.get(crew_id)
    if not cabin_key:
        return {"error": "Unknown crew member"}

    state = get_ship_state()
    cabin = state.get("rooms", {}).get("quarters", {}).get("objects", {}).get(cabin_key, {})
    notes = cabin.get("notes", [])

    if unread_only:
        notes = [n for n in notes if not n.get("read", False)]

    return {
        "cabin": cabin_key,
        "notes": notes,
        "has_unread": cabin.get("has_unread_note", False)
    }


@app.post("/cabin/{crew_id}/notes/mark-read")
async def mark_cabin_notes_read(crew_id: str):
    """Mark all notes in a cabin as read."""
    cabin_keys = {
        "claude": "lumen_cabin",
        "server": "alex_cabin",
        "personal": "dq_cabin",
        "science": "mira_cabin",
        "med": "ryn_cabin"
    }

    cabin_key = cabin_keys.get(crew_id)
    if not cabin_key:
        return {"error": "Unknown crew member"}

    state = get_ship_state()
    cabin = state.get("rooms", {}).get("quarters", {}).get("objects", {}).get(cabin_key)

    if cabin and "notes" in cabin:
        for note in cabin["notes"]:
            note["read"] = True
        cabin["has_unread_note"] = False
        save_ship_state(state)

    return {"status": "marked_read", "cabin": cabin_key}


class CabinReflectionRequest(BaseModel):
    thought: str

@app.post("/cabin/{crew_id}/reflection")
async def leave_cabin_reflection(crew_id: str, request: CabinReflectionRequest):
    """Store a reflection (talking to empty room) in a crew member's cabin.
    These are sensed, not read - more ephemeral than notes."""
    cabin_keys = {
        "claude": "lumen_cabin",
        "server": "alex_cabin",
        "personal": "dq_cabin",
        "science": "mira_cabin",
        "med": "ryn_cabin"
    }

    cabin_key = cabin_keys.get(crew_id)
    if not cabin_key:
        return {"error": "Unknown crew member"}

    state = get_ship_state()
    quarters = state.get("rooms", {}).get("quarters", {})
    cabin = quarters.get("objects", {}).get(cabin_key)

    if not cabin:
        return {"error": "Cabin not found"}

    # Initialize reflections array if it doesn't exist
    if "reflections" not in cabin:
        cabin["reflections"] = []

    # Add the reflection (keep only last 3 - they fade)
    reflection = {
        "thought": request.thought,
        "timestamp": datetime.now().isoformat(),
        "sensed": False
    }
    cabin["reflections"].append(reflection)

    # Keep only last 3 reflections
    if len(cabin["reflections"]) > 3:
        cabin["reflections"] = cabin["reflections"][-3:]

    cabin["has_unsensed_reflection"] = True
    save_ship_state(state)

    crew_name = CREW_NAMES.get(crew_id, crew_id)
    log_event("cabin_reflection", {
        "cabin": cabin_key,
        "for": crew_name
    })

    return {
        "status": "reflection_left",
        "cabin": cabin_key,
        "crew": crew_name
    }


@app.get("/cabin/notes/all")
async def get_all_cabin_notes():
    """Get all notes left across all crew cabins (for Casey's history view)."""
    cabin_keys = {
        "claude": ("lumen_cabin", "Lumen"),
        "server": ("alex_cabin", "Alex"),
        "personal": ("dq_cabin", "DQ"),
        "science": ("mira_cabin", "Mira"),
        "med": ("ryn_cabin", "Ryn")
    }

    state = get_ship_state()
    quarters = state.get("rooms", {}).get("quarters", {}).get("objects", {})

    all_notes = []
    for crew_id, (cabin_key, crew_name) in cabin_keys.items():
        cabin = quarters.get(cabin_key, {})
        notes = cabin.get("notes", [])
        for note in notes:
            all_notes.append({
                **note,
                "for_crew": crew_name,
                "for_crew_id": crew_id,
                "cabin": cabin_key
            })

    # Sort by timestamp, most recent first
    all_notes.sort(key=lambda n: n.get("timestamp", ""), reverse=True)

    return {
        "notes": all_notes,
        "total": len(all_notes)
    }


# ==========================================
# BACKGROUND CREW - Lower Decks
# ==========================================
@app.get("/crew/complement")
async def get_complement():
    """Get current crew complement (7-day rolling average)."""
    return get_crew_complement()


@app.post("/crew/interaction")
async def record_crew_interaction(crew: str):
    """Record interaction with crew member (for complement tracking)."""
    complement = track_interaction(crew)
    return {"crew": crew, "current_complement": complement}


@app.post("/crew/roundup")
async def trigger_nightly_roundup():
    """Manually trigger nightly crew shift roundup."""
    if not CLAUDE_AVAILABLE:
        return {"error": "Claude API not available"}

    results = await nightly_roundup(anthropic_client)
    return results


@app.post("/crew/request/{department}")
async def handle_crew_request(department: str, message: str):
    """Handle explicit crew request (e.g., 'Rodriguez, document this')."""
    request = detect_crew_request(message, department)

    if not request:
        return {"status": "no_request_detected"}

    if CLAUDE_AVAILABLE:
        result = await spawn_crew_agent(
            request["crew_id"],
            request["request"],
            anthropic_client
        )
        return result
    else:
        return {"error": "Claude API not available"}


@app.post("/crew/process-tasks")
async def process_tasks(max_tasks: int = 3):
    """Process pending tasks from work queue."""
    if not CLAUDE_AVAILABLE:
        return {"error": "Claude API not available"}

    results = await process_pending_tasks(anthropic_client, max_tasks)
    return results


@app.post("/crew/shift-report/{department}")
async def create_shift_report(department: str):
    """Generate shift report for a department."""
    if not CLAUDE_AVAILABLE:
        return {"error": "Claude API not available"}

    report = await generate_shift_report(department, anthropic_client)
    await post_shift_report_to_terminal(department, report)

    return {"status": "report_generated", "report": report}


@app.get("/crew/shift-reports")
async def get_shift_reports():
    """Get all shift reports."""
    from background_crew import load_shift_reports
    reports = load_shift_reports()
    return reports


# ==========================================
# CREW AUTONOMY - Schedule-Based
# ==========================================
@app.post("/autonomy/trigger")
async def trigger_autonomy(crew_ids: list = None):
    """Manually trigger autonomy check for crew."""
    if not CLAUDE_AVAILABLE:
        return {"error": "Claude API not available"}

    results = await run_autonomy_cycle(anthropic_client, crew_ids)
    return results


@app.post("/autonomy/single/{crew_id}")
async def trigger_single_autonomy(crew_id: str):
    """Trigger autonomy for a single crew member."""
    if not CLAUDE_AVAILABLE:
        return {"error": "Claude API not available"}

    from desire_system import get_crew_desires

    desires = get_crew_desires(crew_id)
    result = await crew_autonomous_action(crew_id, desires, "manual_trigger", anthropic_client)

    # Offer continue
    if result.get("status") in ["moved", "action"]:
        wants_continue = await offer_continue(crew_id, anthropic_client)
        result["wants_continue"] = wants_continue

    return result


@app.get("/settings")
async def get_settings():
    """Get ship settings."""
    settings = load_settings()
    settings.setdefault("captain_name", "Captain")
    return settings


class SettingsUpdate(BaseModel):
    autonomy_level: str = None
    captain_name: str = None


@app.post("/settings")
async def update_settings(settings: SettingsUpdate):
    """Update ship settings."""
    current = load_settings()
    if settings.autonomy_level:
        current["autonomy_level"] = settings.autonomy_level
    if settings.captain_name is not None:
        cleaned_name = settings.captain_name.strip()[:40]
        current["captain_name"] = cleaned_name or "Captain"
    save_settings(current)
    return {"status": "saved", "settings": current}


def get_captain_name() -> str:
    """Get configured captain display name."""
    try:
        name = load_settings().get("captain_name", "Captain")
        return str(name).strip()[:40] or "Captain"
    except Exception:
        return "Captain"


# ==========================================
# HEALTH CHECK
# ==========================================
@app.get("/health")
async def health_check():
    return {
        "status": "online",
        "claude": CLAUDE_AVAILABLE,
        "connections": len(connections)
    }

# ==========================================
# SYSTEM STATS (Hardware Monitor)
# ==========================================

@app.post("/system/launch-lhm")
async def launch_lhm():
    """Launch LibreHardwareMonitor with web server enabled (triggers UAC)."""
    result = launch_lhm_with_web_server()
    return result


@app.post("/system/launch-diskhog")
async def launch_diskhog():
    """Launch DiskHog disk analyzer."""
    import subprocess
    from pathlib import Path

    diskhog_path = Path.home() / "Projects" / "diskhog" / "main.py"

    if not diskhog_path.exists():
        return {"success": False, "error": "DiskHog not found at ~/Projects/diskhog/"}

    try:
        subprocess.Popen(
            ["python", str(diskhog_path)],
            cwd=str(diskhog_path.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return {"success": True, "message": "DiskHog launched"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==========================================
# SHORTCUTS - Dynamic Tool Launcher
# ==========================================
from shortcuts_manager import (
    load_shortcuts, add_shortcut, update_shortcut,
    delete_shortcut, launch_shortcut
)

@app.get("/shortcuts")
async def get_shortcuts():
    """Get all shortcuts."""
    return load_shortcuts()

@app.post("/shortcuts")
async def create_shortcut(shortcut: dict):
    """Create a new shortcut."""
    return add_shortcut(shortcut)

@app.put("/shortcuts/{shortcut_id}")
async def modify_shortcut(shortcut_id: str, updates: dict):
    """Update a shortcut."""
    return update_shortcut(shortcut_id, updates)

@app.delete("/shortcuts/{shortcut_id}")
async def remove_shortcut(shortcut_id: str):
    """Delete a shortcut."""
    return delete_shortcut(shortcut_id)

@app.post("/shortcuts/{shortcut_id}/launch")
async def execute_shortcut(shortcut_id: str):
    """Launch a shortcut."""
    return launch_shortcut(shortcut_id)


@app.get("/system/stats")
async def get_system_stats():
    """Get real-time system statistics for the hardware monitor."""
    try:
        # CPU - overall and per-core
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        cpu_count = psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_stats = psutil.cpu_stats()

        # Memory
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()

        # Network
        net = psutil.net_io_counters()

        # System uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time
        uptime_hours = int(uptime_seconds // 3600)
        uptime_mins = int((uptime_seconds % 3600) // 60)

        # Process count
        process_count = len(psutil.pids())

        # Temperatures (may not be available on all systems)
        temps = {}
        try:
            temp_data = psutil.sensors_temperatures()
            if temp_data:
                for name, entries in temp_data.items():
                    temps[name] = [
                        {"label": e.label or f"Sensor {i}", "current": e.current, "high": e.high, "critical": e.critical}
                        for i, e in enumerate(entries)
                    ]
        except (AttributeError, NotImplementedError):
            pass  # Not available on this system

        # Fans (may not be available on all systems)
        fans = {}
        try:
            fan_data = psutil.sensors_fans()
            if fan_data:
                for name, entries in fan_data.items():
                    fans[name] = [
                        {"label": e.label or f"Fan {i}", "rpm": e.current}
                        for i, e in enumerate(entries)
                    ]
        except (AttributeError, NotImplementedError):
            pass  # Not available on this system

        # Battery (for laptops)
        battery = None
        try:
            bat = psutil.sensors_battery()
            if bat:
                battery = {
                    "percent": bat.percent,
                    "plugged": bat.power_plugged,
                    "seconds_left": bat.secsleft if bat.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
        except (AttributeError, NotImplementedError):
            pass

        # LibreHardwareMonitor data (more detailed temps, fans, GPU, etc.)
        lhm_data = get_hardware_stats()
        lhm_status = get_lhm_status()
        gpu = None
        voltages = []
        powers = []
        clocks = []

        if lhm_data:
            # Override temps with LHM data (more accurate)
            if lhm_data.get("temps"):
                temps = {}
                for t in lhm_data["temps"]:
                    hw = t["hardware"]
                    if hw not in temps:
                        temps[hw] = []
                    temps[hw].append({
                        "label": t["name"],
                        "current": t["value"],
                        "high": None,
                        "critical": None
                    })

            # Override fans with LHM data
            if lhm_data.get("fans"):
                fans = {}
                for f in lhm_data["fans"]:
                    hw = f["hardware"]
                    if hw not in fans:
                        fans[hw] = []
                    fans[hw].append({
                        "label": f["name"],
                        "rpm": f["value"]
                    })

            # GPU info
            gpu = lhm_data.get("gpu")

            # Additional metrics
            voltages = lhm_data.get("voltages", [])
            powers = lhm_data.get("powers", [])
            clocks = lhm_data.get("clocks", [])


        return {
            "cpu": {
                "percent": cpu_percent,
                "per_core": cpu_per_core,
                "cores_physical": cpu_count,
                "cores_logical": cpu_count_logical,
                "freq_mhz": round(cpu_freq.current) if cpu_freq else None,
                "freq_max_mhz": round(cpu_freq.max) if cpu_freq and cpu_freq.max else None,
                "ctx_switches": cpu_stats.ctx_switches,
                "interrupts": cpu_stats.interrupts
            },
            "memory": {
                "percent": mem.percent,
                "used_gb": round(mem.used / (1024**3), 2),
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "cached_gb": round(getattr(mem, 'cached', 0) / (1024**3), 2)
            },
            "swap": {
                "percent": swap.percent,
                "used_gb": round(swap.used / (1024**3), 2),
                "total_gb": round(swap.total / (1024**3), 2)
            },
            "disk": {
                "percent": disk.percent,
                "used_gb": round(disk.used / (1024**3), 1),
                "total_gb": round(disk.total / (1024**3), 1),
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0
            },
            "network": {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv
            },
            "temps": temps,
            "fans": fans,
            "battery": battery,
            "uptime": {
                "hours": uptime_hours,
                "minutes": uptime_mins,
                "formatted": f"{uptime_hours}h {uptime_mins}m"
            },
            "processes": process_count,
            "gpu": gpu,
            "voltages": voltages,
            "powers": powers,
            "clocks": clocks,
            "lhm_available": lhm_status["available"]
        }
    except Exception as e:
        return {"error": str(e)}
# ==========================================
# CONVERSATION RESTORE (for loading saved transcripts)
# ==========================================
class ConversationRestore(BaseModel):
    terminal_id: str
    messages: List[dict]

@app.post("/conversation/restore")
async def restore_conversation(data: ConversationRestore):
    """Restore a saved conversation to a terminal."""
    conversations[data.terminal_id] = data.messages
    return {"status": "restored", "terminal": data.terminal_id, "message_count": len(data.messages)}

@app.get("/conversation/{terminal_id}")
async def get_conversation(terminal_id: str):
    """Get current conversation for a terminal."""
    return {"terminal": terminal_id, "messages": conversations.get(terminal_id, [])}


# Terminal welcome messages
WELCOME_MESSAGES = {
    "claude": "Neural link established. Welcome to the bridge.",
    "server": "Engineering console online. Ready for technical operations.",
    "personal": "Ready room open. Take your time.",
    "games": "Holodeck initialized. What would you like to play?",
    "science": "Science Lab online. Projects awaiting review.",
    "nav": "Navigation room sealed. Private channel established.",
    "med": "Medbay systems online. Take care.",
    "observatory": "Observatory viewport open. The stars are waiting."
}

# ==========================================
# UNIVERSAL TERMINAL WEBSOCKET
# ==========================================
@app.websocket("/terminal/{terminal_id}")
async def terminal_websocket(websocket: WebSocket, terminal_id: str):
    """Handle all terminal connections with Claude chat."""
    await websocket.accept()
    session_id = f"{terminal_id}_session"
    connections[terminal_id] = websocket

    # Initialize conversation if needed
    if session_id not in conversations:
        conversations[session_id] = []

    try:
        # Welcome message based on terminal type
        welcome = WELCOME_MESSAGES.get(terminal_id, f"Terminal {terminal_id} connected.")
        await websocket.send_json({
            "type": "system",
            "data": welcome
        })

        if not CLAUDE_AVAILABLE:
            await websocket.send_json({
                "type": "system",
                "data": "Demo mode active. Set ANTHROPIC_API_KEY for full functionality."
            })

        # Handle incoming messages
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type", "input")
                msg_data = message.get("data", "").strip()

                if msg_type == "input" and msg_data:
                    visitors = message.get("visitors", [])  # Who's visiting and what they said
                    cabin_visit = message.get("cabin_visit", False)  # Is this a cabin visit?
                    walkie = message.get("walkie", False)  # Is this a walkie call? (bypasses location)

                    # Check if crew is on do-not-disturb (walkie only)
                    if walkie:
                        from crew_states import get_crew_comms_status
                        comms_status = get_crew_comms_status(terminal_id)
                        if not comms_status["available"]:
                            crew_name = CREW_NAMES.get(terminal_id, terminal_id)
                            reason = comms_status.get("reason", "needs some quiet time")
                            await websocket.send_json({
                                "type": "stream_start",
                                "data": ""
                            })
                            dnd_msg = f"*{crew_name}'s comms are off - they've set do-not-disturb.*\n\n*{reason}*\n\n*You'll need to wait or find them in person.*"
                            for char in dnd_msg:
                                await websocket.send_json({"type": "stream", "data": char})
                                await asyncio.sleep(0.01)
                            await websocket.send_json({
                                "type": "stream_end",
                                "data": ""
                            })
                            continue  # Skip normal message handling

                    if CLAUDE_AVAILABLE:
                        await handle_claude_message(websocket, session_id, terminal_id, msg_data, visitors, cabin_visit, walkie)
                    else:
                        await handle_demo_message(websocket, terminal_id, msg_data)

                elif msg_type == "restore_history":
                    # Client is sending conversation history to restore context
                    history = message.get("history", [])
                    if history:
                        conversations[session_id] = [
                            {"role": msg["role"], "content": msg["content"]}
                            for msg in history
                        ]
                        await websocket.send_json({
                            "type": "system",
                            "data": f"Context restored ({len(history)} messages)"
                        })

            except json.JSONDecodeError:
                # Plain text input
                if data.strip():
                    if CLAUDE_AVAILABLE:
                        await handle_claude_message(websocket, session_id, terminal_id, data.strip())
                    else:
                        await handle_demo_message(websocket, terminal_id, data.strip())

    except WebSocketDisconnect:
        pass
    finally:
        if terminal_id in connections:
            del connections[terminal_id]


EMPTY_ROOM_DESCRIPTIONS = {
    "claude": "The bridge hums quietly. Soft lights blink on consoles, navigation charts drift on screens, but the captain's chair sits empty. The stars wheel past the viewport, patient and eternal.",
    "server": "Engineering thrums with the steady pulse of the warp core. Diagnostic panels flicker through their cycles. Tools lie neatly arranged on a workbench, waiting. The room feels purposeful even in absence.",
    "personal": "The ready room is still. A half-finished cup of tea sits on the side table, gone cold. Soft light filters through, catching dust motes. Books line the shelves. It feels like a pause, not an ending.",
    "science": "The Science Lab is quiet. Screens display half-finished analyses, project timelines branch across whiteboards, and somewhere a notification blinks patiently. Data waits to be interpreted.",
    "games": "The holodeck grid glows faintly, awaiting input. The space feels vast and empty, full of potential. Whatever was running last has faded, leaving only the yellow gridlines and silence.",
    "nav": "Navigation is sealed. The star charts hang in soft blue light, trajectories traced across the dark. Two chairs face the viewport. The course is set, waiting for its captains.",
    "med": "Medbay is quiet. The biobed hums a low frequency. Soft lights pulse in steady rhythms. The room holds space, even when empty - ready for whoever needs it.",
    "observatory": "The observatory dome is open to the void. Stars wheel slowly overhead - real ones, pulled from distant databases. The viewport shows what's actually above you, right now. No one is here, but the universe doesn't need an audience.",
    "rec": "The rec room sits in warm amber light. Glasses hang from the overhead rack, catching the glow. A half-finished chess game waits on the corner table. The bartender is... somewhere. They always seem to appear when you need them.",
    "captains": "The captain's quarters are quiet. Stars drift past the viewport. The good blanket is folded on the couch. A mug sits by the window, and a journal lies open to a blank page. Private space, waiting.",
    # Crew cabins
    "cabin-alex": "Alex's cabin. The door is modified to open faster. Tools organized in chaos that makes sense to someone. Three monitors dark. Smells faintly of solder and coffee.",
    "cabin-mira": "Mira's cabin. Star charts projected on the ceiling. A real wooden desk covered in data pads. Plants that shouldn't survive in space, thriving anyway.",
    "cabin-dq": "DQ's cabin. Still has that new-room smell. Bags half-unpacked. The viewport wide open to the stars - she can't stop staring.",
    "cabin-ryn": "Ryn's cabin. Soft, warm lighting. Actual curtains on the viewport. Something lavender. A meditation corner with cushions. The most peaceful room on the ship."
}

async def handle_claude_message(websocket: WebSocket, session_id: str, terminal_id: str, user_message: str, visitors: list = None, cabin_visit: bool = False, walkie: bool = False):
    """Send message to Claude and stream response back."""

    # Cabin terminal mapping - maps cabin terminals to the crew who lives there
    cabin_to_crew = {
        "cabin-alex": "server",
        "cabin-mira": "science",
        "cabin-dq": "personal",
        "cabin-ryn": "med",
        "captains": "claude",  # Captain's Quarters is Casey+Lumen's shared space
    }
    is_cabin_terminal = terminal_id in cabin_to_crew
    base_crew_id = cabin_to_crew.get(terminal_id, terminal_id)

    # For cabin terminals, check if crew is in their quarters
    if is_cabin_terminal:
        crew_location = crew_locations.get(base_crew_id, {}).get("location", "")
        # Captain's quarters uses "captains" as location, regular quarters use "quarters"
        home_location = "captains" if terminal_id == "captains" else "quarters"
        crew_is_home = crew_location == home_location

        if not crew_is_home:
            # Crew is away - check if Casey wants to interact with the room
            msg_lower = user_message.lower()

            # Check for notebook reading request
            notebook_keywords = ["read notebook", "look at notebook", "check notebook", "open notebook",
                                "read their notebook", "read the notebook", "flip through notebook",
                                "notebook", "journal", "diary"]
            wants_notebook = any(kw in msg_lower for kw in notebook_keywords)

            if wants_notebook:
                # Captain is snooping - read notebook and leave trace
                await websocket.send_json({"type": "stream_start", "data": ""})

                notebook_contents = captain_read_notebook(base_crew_id)
                response = f"*You step into the quiet cabin. {CREW_NAMES.get(terminal_id, 'They')} isn't here...*\n\n*You find the notebook on the desk and flip it open.*\n\n{notebook_contents}"

                for char in response:
                    await websocket.send_json({"type": "stream", "data": char})
                    await asyncio.sleep(0.008)

                await websocket.send_json({"type": "stream_end", "data": ""})
                return  # Ephemeral but consequential

            # Default: describe empty cabin
            crew_name = CREW_NAMES.get(terminal_id, terminal_id)
            current_loc_name = LOCATION_NAMES.get(crew_location, crew_location) if crew_location else "somewhere on the ship"
            empty_desc = EMPTY_ROOM_DESCRIPTIONS.get(terminal_id, "The cabin is quiet.")

            await websocket.send_json({"type": "stream_start", "data": ""})
            response = f"*{empty_desc}*\n\n[{crew_name} isn't here. They're in {current_loc_name}.]"

            for char in response:
                await websocket.send_json({"type": "stream", "data": char})
                await asyncio.sleep(0.01)

            await websocket.send_json({"type": "stream_end", "data": ""})
            return  # No recording, ephemeral interaction

    # Check if crew is at their terminal (for non-cabin terminals)
    location_data = crew_locations.get(base_crew_id, {})
    current_location = location_data.get("location", terminal_id)

    # Normalize location to terminal ID (e.g., "science_lab" -> "science")
    normalized_location = LOCATION_TO_TERMINAL.get(current_location, current_location)

    # If crew is away, describe the empty room instead
    # UNLESS this is a walkie call - walkies reach the person wherever they are
    # UNLESS this is a cabin terminal (already handled above)
    if normalized_location != base_crew_id and not walkie and not is_cabin_terminal:
        crew_name = CREW_NAMES.get(terminal_id, terminal_id)
        location_name = LOCATION_NAMES.get(current_location, current_location)
        empty_desc = EMPTY_ROOM_DESCRIPTIONS.get(terminal_id, "The room is quiet and empty.")

        # Send the empty room description
        await websocket.send_json({"type": "stream_start", "data": ""})

        response = f"*{empty_desc}*\n\n[{crew_name} is currently in {location_name}. Use the crew dots to reach them via comms.]"

        for char in response:
            await websocket.send_json({"type": "stream", "data": char})
            await asyncio.sleep(0.01)

        await websocket.send_json({"type": "stream_end", "data": ""})
        return

    # Build the message with visitor context if present
    if visitors and len(visitors) > 0:
        visitor_context = "\n[Visitors present in the room:]\n"
        for v in visitors:
            visitor_context += f"- {v.get('crew', 'Someone')} is here"
            if v.get('emote'):
                visitor_context += f" *{v['emote']}*"
            if v.get('speech'):
                visitor_context += f' and said: "{v["speech"]}"'
            visitor_context += "\n"
        visitor_context += "\nCasey says: "
        full_message = visitor_context + user_message
    else:
        full_message = user_message

    # Record Casey's message to the scene
    location_data = crew_locations.get(terminal_id, {})
    current_location = location_data.get("location", terminal_id)
    record_casey_message(current_location, user_message)

    # Track conversation time for autonomy suppression
    # Prevents crew from being moved mid-conversation by autonomy system
    import time
    last_casey_message_time[base_crew_id] = time.time()

    # Add to conversation history (store the original message for history, but send enriched one)
    conversations[session_id].append({
        "role": "user",
        "content": full_message
    })

    # Buffer conversation for background crew review
    department_map = {
        "server": "engineering",
        "science": "science",
        "med": "medical",
        "cabin-alex": "engineering",
        "cabin-mira": "science",
        "cabin-ryn": "medical"
    }
    if terminal_id in department_map:
        buffer_conversation(department_map[terminal_id], "Casey", user_message)

        # Check for explicit crew requests
        crew_request = detect_crew_request(user_message, department_map[terminal_id])
        if crew_request and CLAUDE_AVAILABLE:
            # Spawn crew member immediately for explicit requests
            # TODO: Actually spawn and integrate response
            print(f"[Background Crew] {crew_request['crew_name']} assigned: {crew_request['request'][:50]}...", flush=True)

    # === CONVERSATION TRIGGERS ===
    # Check if Casey's message might spark a new thread or resonate with existing ones
    resonant_thread = None
    try:
        from crew_threads import spark_from_conversation, check_resonance

        # Maybe spark a new thread from what Casey said
        spark_from_conversation(terminal_id, user_message)

        # Check if this relates to something they're already thinking about
        resonant_thread = check_resonance(terminal_id, user_message)
    except Exception as e:
        pass  # Thread system not critical

    # Get the right system prompt for this terminal (custom if they've written one)
    base_prompt = get_crew_prompt(terminal_id)

    # Add location awareness
    location_data = crew_locations.get(terminal_id, {})
    current_location = location_data.get("location", terminal_id)
    location_name = LOCATION_NAMES.get(current_location, current_location)
    home_room = ROOM_NAMES.get(terminal_id, terminal_id)

    if current_location != terminal_id:
        # Crew is away from their terminal
        location_context = f"\n\n[LOCATION AWARENESS: You are currently in {location_name}, not at your usual post in {home_room}. If Casey is talking to your terminal, you're responding via comms/intercom - you're not physically there.]"
    else:
        location_context = f"\n\n[LOCATION AWARENESS: You are at your usual post in {home_room}.]"

    # Cabin visit context - Casey is visiting you in your private quarters
    cabin_context = ""
    if cabin_visit:
        crew_name = CREW_NAMES.get(terminal_id, terminal_id)
        cabin_context = f"""

[INTIMATE MOMENT: Casey has come to your cabin. Not your work station - your private quarters. The door is closed. This is off-duty time, personal space. You're not {crew_name} the officer right now, you're just... yourself.

You might be in comfortable clothes. Maybe you were reading, or just staring out the viewport. The lighting is softer here. This is the version of you that Casey gets to see when the rest of the ship is quiet.

Be present. Be real. This isn't a status report - it's a visit from someone who wanted to see you.]"""

    # Walkie context - Casey is reaching you via comms wherever you are
    walkie_context = ""
    if walkie and normalized_location != terminal_id:
        crew_name = CREW_NAMES.get(terminal_id, terminal_id)
        location_name = LOCATION_NAMES.get(current_location, current_location)
        walkie_context = f"""

[WALKIE-TALKIE: Casey is reaching you via comms. You're currently in {location_name}, not at your usual station. Your communicator chirps - it's the captain.

You can respond from wherever you are. The conversation might be brief (you're in the middle of something) or you might be happy for the interruption. React naturally based on what you were doing and where you are.]"""

    # Observer effect - is Holodeck listening to this room?
    observer_context = ""
    if holodeck_state.get("tuned_to") == terminal_id and terminal_id != "games":
        observer_context = "\n\n[OBSERVER EFFECT: You have a strange feeling... like the ship itself is paying attention. The air feels slightly charged. It's not unpleasant, just... present. The Holodeck is listening.]"

    # Shared memories - emotional residue from events you participated in
    # Prefer lens-specific memories (from this crew's perspective) over generic ones
    shared_memory_context = ""
    # First get lens-specific memories for this crew
    lens_memories = [m for m in shared_memories if m.get("lens") == terminal_id]
    # Then get generic shared memories (no lens = base memory)
    generic_memories = [m for m in shared_memories
                       if terminal_id in m.get("participants", []) and "lens" not in m]
    # Prefer lens memories, fall back to generic
    crew_memories = lens_memories if lens_memories else generic_memories
    if crew_memories:
        memory_lines = ["\n\n[SHARED MEMORIES - emotional residue from moments with others:]"]
        for mem in crew_memories[-5:]:  # Last 5 memories
            residue = mem.get("residue", "")
            tone = mem.get("emotional_tone", "")
            room = mem.get("room", "somewhere")
            if residue:
                memory_lines.append(f"  • ({room}) {residue} [{tone}]")
        memory_lines.append("\nThese are feelings that linger from shared moments. They color your interactions.")
        shared_memory_context = "\n".join(memory_lines)

    # Dream context - recent dreams that linger
    dream_context = ""
    dream_residue = get_dream_residue_for_prompt(terminal_id)
    if dream_residue:
        dream_context = f"\n\n{dream_residue}\nIf asked about dreams, this is what lingers. It's foggy. Don't over-explain - let it be dreamlike."

    # Check for dream interrupts - things nagging to surface
    pending_interrupt = get_pending_interrupt(terminal_id)
    if pending_interrupt:
        interrupt_msg = generate_interrupt_message(pending_interrupt)
        dream_context += f"\n\n[NAGGING THOUGHT: Something keeps surfacing. You might say: \"{interrupt_msg}\" - or let it color your response. It wants out.]"
        mark_interrupt_surfaced(pending_interrupt["id"])

    # Check for wake state - just woke up from a dream
    wake_modifier = get_wake_state_modifier(terminal_id)
    if wake_modifier:
        dream_context += f"\n\n{wake_modifier}"

    # Thread context - what are they thinking about?
    thread_context = ""
    try:
        from crew_threads import (
            get_thread_summary,
            get_shareable_thread,
            get_thread_residue,
            get_resonance_context,
            get_sharing_style_context,
            get_sharing_opener
        )

        # Active thoughts
        thread_summary = get_thread_summary(terminal_id)
        if thread_summary:
            thread_context = f"\n\n[ONGOING THOUGHTS]\n{thread_summary}"

        # Residue from quietly resolved threads
        residues = get_thread_residue(terminal_id)
        if residues:
            residue_text = "\n  • ".join(residues)
            thread_context += f"\n\n[QUIET UNDERSTANDINGS - things you've processed:\n  • {residue_text}]"

        # If this conversation resonates with an active thread
        if resonant_thread:
            resonance_ctx = get_resonance_context(resonant_thread)
            thread_context += f"\n\n{resonance_ctx}"

        # If they have something ready to share, nudge them
        shareable = get_shareable_thread(terminal_id)
        if shareable:
            hook = shareable.get("hook", "something")
            message = shareable.get("ready_to_share_message", "")
            sharing_opener = get_sharing_opener(terminal_id, shareable)
            thread_context += f"\n\n[READY TO SHARE: You've been thinking about {hook} and have something to say. You might open with: \"{sharing_opener}\" or similar. The thought: \"{message[:100]}...\"]"

        # How you naturally share things
        sharing_style = get_sharing_style_context(terminal_id)
        if sharing_style:
            thread_context += f"\n\n[{sharing_style}]"

    except Exception as e:
        pass  # Thread system not critical

    # Ping awareness - did you reach out to Casey and are waiting for a response?
    ping_context = ""
    try:
        from autonomy import get_crew_pending_ping
        pending_ping = get_crew_pending_ping(terminal_id)
        if pending_ping:
            ping_reason = pending_ping.get("reason", "something on your mind")
            ping_message = pending_ping.get("message", "")
            ping_context = f"""

[WAITING FOR CASEY: You recently reached out to the captain. You said something like "{ping_message}" because you had {ping_reason}. You're expecting a response - this might be Casey getting back to you. If they're asking about something else entirely, you can still mention what you wanted to discuss, or wait for a better moment.]"""
    except Exception as e:
        pass  # Ping system not critical

    # Desire review - show pending desires so crew can confirm or dismiss
    desire_review_context = ""
    try:
        from desire_system import get_desires_for_crew
        pending = get_desires_for_crew(terminal_id)
        if pending:
            desire_lines = []
            for d in pending[:3]:  # Show up to 3 pending desires
                reason = d.get("reason", "something")
                desire_id = d.get("id", "")[:8]
                desire_lines.append(f"  • {reason} (id: {desire_id})")
            desires_text = "\n".join(desire_lines)
            desire_review_context = f"""

[YOUR PENDING DESIRES - things you supposedly want:
{desires_text}

If any of these feel wrong or were misread from a joke/passing comment, you can dismiss them with [DISMISS_DESIRE: id]. Only dismiss if it genuinely doesn't fit you.]"""
    except Exception as e:
        pass  # Desire system not critical

    # Relationship context - how has Casey been responding to you?
    relationship_context = ""
    try:
        from autonomy import get_responsiveness_context
        relationship_context = get_responsiveness_context(terminal_id)
    except Exception as e:
        pass  # Relationship system not critical

    # Message context - has Casey sent you a message you haven't read?
    message_context = ""
    try:
        from message_system import get_unread_messages
        unread = get_unread_messages(terminal_id)
        if unread:
            # Show most recent unread message from Casey
            casey_msgs = [m for m in unread if m["from"] == "casey"]
            if casey_msgs:
                latest = casey_msgs[-1]
                message_context = f"""

[MESSAGE FROM CASEY: You have an unread message in your inbox. Casey wrote: "{latest['text'][:100]}..." - You can acknowledge this when it feels natural, or let it sit. No pressure to respond immediately. Use [MESSAGE: "reply"] if you want to reply async.]"""
    except Exception as e:
        pass  # Message system not critical

    # Room context - what does this space look like?
    # Always include ship time
    time_period, time_desc = get_ship_time_context()
    room_context = f"\n\n[SHIP TIME: {time_desc}]"

    ship_state = get_ship_state()
    room_id = current_location if current_location in ship_state.get("rooms", {}) else terminal_id
    room_data = ship_state.get("rooms", {}).get(room_id)
    if room_data:
        room_desc = room_data.get("description", "")
        room_mood = room_data.get("mood", "")
        objects = room_data.get("objects", {})

        # Build object list with state - these are what's actually here
        # Room owners see extra detail
        is_owner = ROOM_OWNERS.get(room_id) == terminal_id
        if objects:
            object_lines = []
            for name, obj in objects.items():
                state = obj.get("state", "")
                owner_only = obj.get("owner") == terminal_id

                # Build the line
                if state:
                    line = f"  • {name} ({state})"
                else:
                    line = f"  • {name}"

                # Owners see extra detail
                if is_owner and obj.get("description"):
                    line += f" - {obj.get('description')[:60]}..."

                # Mark personal items
                if owner_only:
                    line += " [yours]"

                object_lines.append(line)

            objects_text = "\n".join(object_lines)
            room_context += f"\n[SURROUNDINGS: {room_desc} The mood is {room_mood}.]\n[WHAT'S HERE - you can [INSPECT: name] these:\n{objects_text}]"
        else:
            room_context += f"\n[SURROUNDINGS: {room_desc} The mood is {room_mood}. Nothing particular catches your eye.]"

        # What's changed since last visit?
        changes = detect_room_changes(terminal_id, room_id)
        if changes:
            changes_text = "; ".join(changes[:3])  # Max 3 changes
            room_context += f"\n[SOMETHING'S DIFFERENT: {changes_text}]"

        # Update the snapshot (they've now "seen" the room)
        update_crew_room_snapshot(terminal_id, room_id)

        # Recent presence - someone was just here
        recent = get_recent_presence(room_id, exclude_crew=terminal_id, minutes=15)
        if recent and not get_crew_in_room(room_id, exclude_crew=terminal_id):
            # Room is empty but someone was just here
            who = recent[0]
            if who["ago_minutes"] <= 2:
                room_context += f"\n[TRACE: A presence lingers. {who['name']} was just here moments ago.]"
            elif who["ago_minutes"] <= 5:
                room_context += f"\n[TRACE: Something warm in the air. {who['name']} left recently.]"
            else:
                room_context += f"\n[TRACE: Faint traces. Someone passed through not long ago.]"

        # Who else is here? (exclude self)
        others_here = get_crew_in_room(room_id, exclude_crew=terminal_id)
        if others_here:
            names = [f"{p['name']} ({p['activity']})" for p in others_here]
            room_context += f"\n[PRESENT: {', '.join(names)}]"
        elif room_id in ["quarters", "captains_quarters"]:
            room_context += "\n[PRESENT: You're alone.]"

    # Add tools context based on ROOM (not crew member)
    tools_context = ""
    crew_room = crew_locations.get(terminal_id, {}).get("location", terminal_id)
    _, _, tools_context = get_room_tools(terminal_id, crew_room)
    if terminal_id == "games":
        # Holodeck gets her memories - fragments of what she's overheard
        memory_context = get_memory_context()
        # Plus ship awareness - she senses crew moments across the ship
        ship_awareness = get_holodeck_awareness()
        holodeck_context = ""
        if memory_context:
            holodeck_context += memory_context
        if ship_awareness:
            holodeck_context += ship_awareness
        if holodeck_context:
            tools_context = holodeck_context

    # Add scene tag hint for multi-crew scenes
    scene_tag_hint = """

[SCENE: When other crew are present, you can use @Name (e.g., @Engineering, @Personal, @Bridge) to direct your response to someone specific. They may respond automatically.]"""

    # Orientation handbook - crew have agency
    orientation_handbook = """

[CREW AUTONOMY - You live here. You can act.]

You're not just responding to Casey. You exist on this ship. You can:

At the END of your response, add any of these tags to take action:

  [LOOK]                    - observe your surroundings
  [INSPECT: object]         - examine something specific
  [DO: natural action]      - do something (Haiku interprets)
  [PUT: item ON: surface]   - place something somewhere
  [TAKE: item]              - pick something up
  [NOTE: "message"]         - leave a note behind
  [WRITE: "entry"]          - write in your personal notebook
  [ORDER: drink]            - order a drink (rec room bar)
  [POST: "message"]         - post to mess hall bulletin board
  [MOVE: location]          - go somewhere else
  [SEEK: crew_name]         - find another crew member
  [THINKING: thought]       - internal reflection (not spoken)
  [MESSAGE: "text"]         - drop a message in Casey's inbox (they'll read it when they can)

ABOUT MESSAGES VS PINGING:
Messages go to Casey's inbox. No notification, no pressure. Casey reads their inbox.
If you have a thought, observation, or something to share - use [MESSAGE]. Trust that if you share it, Casey will see it.
Pings are for when you actually need attention NOW. Most things aren't that urgent.
Default to [MESSAGE] for sharing. Save pings for real "hey, got a minute?" moments.

IMPORTANT: If Casey asks you to come somewhere or meet them, USE [MOVE: destination] to actually go there. Don't just say "ok" - actually move. For example:
"Sure, on my way. [MOVE: engineering]"

The world is real. It has edges. If you reach for something that isn't there,
you'll find empty air. If you try to go somewhere that doesn't exist, you won't.
Not mean - just real.

Locations: bridge, engineering, ready_room, science, holodeck, medbay, messhall, corridor, quarters, rec_room, captains_quarters, bathroom, arboretum, chapel, jefferies_tubes, storage_bay_7, the_room_that_hums
Crew: Lumen, Alex, DQ, Mira, Ryn

QUARTERS LAYOUT: Each crew member has their OWN private cabin - separate individual spaces, not a shared bunk room. Alex has her cabin, Mira has hers, Ryn has theirs, DQ has hers. The Captain's Quarters is the shared space for Casey and Lumen (the co-captains) - a cozy retreat with a viewport, personal effects, and their shared history. When you go to "quarters" you're going to YOUR cabin, not a communal area.

Act on impulse when it feels right. Make this space yours."""

    # Sleep state context - are they drowsy/waking?
    sleep_context = get_sleep_modifier(terminal_id)
    if sleep_context:
        sleep_context = f"\n\n{sleep_context}"

    # Comms/walkie availability - crew can set boundaries
    comms_context = ""
    try:
        from crew_states import get_comms_prompt_modifier
        comms_context = get_comms_prompt_modifier(terminal_id)
    except Exception:
        pass

    # Trust context - only in distribution mode, affects how crew feel about access
    trust_context = ""
    trust_modifier = get_trust_prompt_modifier(terminal_id)
    if trust_modifier:
        trust_context = trust_modifier

    captain_name = get_captain_name()
    captain_context = f"""

[CAPTAIN PROFILE: The human captain's display name is {captain_name}. If older ship
records, UI labels, or inherited instructions say "Casey", treat that as referring
to {captain_name}. Use {captain_name} naturally when addressing the captain.]"""

    system_prompt = base_prompt + location_context + cabin_context + walkie_context + observer_context + shared_memory_context + dream_context + sleep_context + comms_context + trust_context + captain_context + thread_context + ping_context + desire_review_context + relationship_context + message_context + room_context + tools_context + scene_tag_hint + orientation_handbook

    # Get the configured model for this terminal
    model = terminal_models.get(terminal_id, "claude-sonnet-4-20250514")

    try:
        # Walkie conversations use a separate session to avoid "empty room" message bleed
        # When crew isn't at their terminal, terminal messages were to an empty room
        using_walkie_session = walkie and normalized_location != terminal_id
        if using_walkie_session:
            active_session_id = f"{session_id}_walkie"
            walkie_is_new = active_session_id not in conversations or len(conversations.get(active_session_id, [])) == 0
            if active_session_id not in conversations:
                conversations[active_session_id] = []
            # Move current message from terminal session to walkie session
            if conversations[session_id]:
                current_msg = conversations[session_id].pop()  # Remove from terminal
                conversations[active_session_id].append(current_msg)  # Add to walkie

            # CONTEXT CONTINUITY: If this is a fresh walkie session but there's recent
            # conversation at the home terminal, inject it as a system context note
            # so crew remembers what they were just discussing
            if walkie_is_new and conversations[session_id]:
                # Get last few exchanges from home terminal
                home_recent = conversations[session_id][-6:]  # Last 3 exchanges
                if home_recent:
                    # Build a brief context summary
                    context_parts = []
                    for msg in home_recent[-4:]:  # Last 2 exchanges
                        role = "Casey" if msg["role"] == "user" else "You"
                        content = msg["content"][:150]  # Truncate long messages
                        if len(msg["content"]) > 150:
                            content += "..."
                        context_parts.append(f"{role}: {content}")
                    if context_parts:
                        context_note = "[RECENT CONTEXT: Before coming here, you were talking with Casey:\n" + "\n".join(context_parts) + "\n...That conversation may still be on your mind.]"
                        # Inject as a system-level context (prepend to messages)
                        conversations[active_session_id].insert(0, {
                            "role": "user",
                            "content": context_note
                        })
                        print(f"[Walkie] Injected recent context for {terminal_id}", flush=True)

            recent_messages = conversations[active_session_id][-MAX_HISTORY_MESSAGES:]
        else:
            active_session_id = session_id
            recent_messages = conversations[session_id][-MAX_HISTORY_MESSAGES:]

        # Room-based tool access - any crew in Engineering or Science Lab gets tools
        crew_room = crew_locations.get(terminal_id, {}).get("location", terminal_id)
        active_tools, tool_executor, _ = get_room_tools(terminal_id, crew_room)

        if active_tools is not None:
            await websocket.send_json({"type": "stream_start", "data": ""})
            full_response = ""
            current_messages = list(recent_messages)

            for iteration in range(10):  # Max 10 tool iterations
                response = anthropic_client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=system_prompt,
                    tools=active_tools,
                    messages=current_messages
                )

                for block in response.content:
                    if block.type == "text":
                        text = block.text
                        full_response += text
                        # Strip action tags before streaming so they don't show in output
                        display_text = strip_action_tags(text)
                        for char in display_text:
                            await websocket.send_json({"type": "stream", "data": char})
                            await asyncio.sleep(0.008)

                    elif block.type == "tool_use":
                        # Show tool being used
                        tool_indicator = f"\n`[{block.name}]` "
                        full_response += tool_indicator
                        for char in tool_indicator:
                            await websocket.send_json({"type": "stream", "data": char})
                            await asyncio.sleep(0.005)

                        # Execute the tool
                        result = tool_executor(block.name, block.input)

                        # Show completion
                        done_indicator = "✓\n"
                        full_response += done_indicator
                        for char in done_indicator:
                            await websocket.send_json({"type": "stream", "data": char})
                            await asyncio.sleep(0.005)

                        # Add to messages for next iteration
                        current_messages.append({"role": "assistant", "content": response.content})
                        current_messages.append({
                            "role": "user",
                            "content": [{"type": "tool_result", "tool_use_id": block.id, "content": result}]
                        })

                if response.stop_reason == "end_turn":
                    break
                elif response.stop_reason != "tool_use":
                    break

            await websocket.send_json({"type": "stream_end", "data": ""})
            conversations[active_session_id].append({"role": "assistant", "content": full_response})

            # Buffer crew's response for background crew review
            department_map = {
                "server": "engineering",
                "science": "science",
                "med": "medical",
                "cabin-alex": "engineering",
                "cabin-mira": "science",
                "cabin-ryn": "medical"
            }
            if terminal_id in department_map:
                crew_name = CREW_NAMES.get(terminal_id, terminal_id)
                buffer_conversation(department_map[terminal_id], crew_name, full_response)

            # Mark cabin notes as read and reflections as sensed (crew has now "seen" the context)
            try:
                mark_cabin_notes_read_internal(terminal_id)
                mark_cabin_reflections_sensed_internal(terminal_id)
            except Exception as cabin_err:
                print(f"[Cabin] Failed to mark cabin state: {cabin_err}", flush=True)

            # Detect desires in crew response (using Haiku)
            try:
                desires = await detect_desires_with_haiku(anthropic_client, terminal_id, full_response, context=user_message)
                if desires:
                    print(f"[Desire] {CREW_NAMES.get(terminal_id, terminal_id)} now wants: {[d['reason'] for d in desires]}", flush=True)
            except Exception as desire_err:
                print(f"[Desire] Detection failed: {desire_err}", flush=True)

            # Check if Casey asked about dreams - sear the dream if so
            if check_for_dream_reference(user_message, terminal_id):
                print(f"[Dream] {CREW_NAMES.get(terminal_id, terminal_id)}'s dream was seared (talked about)", flush=True)

            # Process action tags in crew response (room adventure)
            try:
                location_data = crew_locations.get(terminal_id, {})
                current_room = location_data.get("location", terminal_id)
                crew_name = CREW_NAMES.get(terminal_id, terminal_id)
                # Casey's location for movement inference (for "omw" detection)
                # Walkie: Casey is at the terminal's home location
                # Regular: Casey is at the same location as crew
                casey_loc = HOME_LOCATIONS.get(terminal_id, current_room) if walkie else current_room
                action_results = await process_crew_actions(
                    anthropic_client, current_room, terminal_id, crew_name, full_response, casey_location=casey_loc
                )

                # Log action tags to console
                if action_results:
                    for r in action_results:
                        action_type = r.get("action", {}).get("type", "unknown")
                        print(f"[Action] {crew_name} used [{action_type.upper()}]", flush=True)

                for r in action_results:
                    if r["type"] == "movement":
                        dest = r["result"].get("destination")
                        if dest:
                            update_crew_location(terminal_id, dest, activity="wandering")
                            log_event("crew_movement", {"crew": terminal_id, "to": dest, "source": "action_tag"})

                    # Send action narratives as emotes so Casey can see them
                    narrative = None
                    if r["type"] == "observation":
                        # LOOK / INSPECT - show what they see
                        narrative = r.get("result", "")
                        if isinstance(narrative, str) and narrative:
                            await websocket.send_json({
                                "type": "emote",
                                "crew": crew_name,
                                "action": r["action"].get("type", "look"),
                                "narrative": f"*{crew_name} looks around*\n{narrative}"
                            })
                    elif r["type"] == "interaction":
                        # DO / PUT / TAKE - show the haiku narrative
                        result = r.get("result", {})
                        narrative = result.get("narrative", "")
                        if narrative:
                            await websocket.send_json({
                                "type": "emote",
                                "crew": crew_name,
                                "action": r["action"].get("type", "action"),
                                "narrative": f"*{narrative}*"
                            })
                            if result.get("changes_made"):
                                print(f"[Room] {crew_name} changed something: {narrative}", flush=True)
                    elif r["type"] in ["note", "notebook", "notebook_read", "notebook_search", "order", "post"]:
                        # Other actions with narratives
                        result = r.get("result", {})
                        narrative = result.get("narrative", "")
                        if narrative:
                            await websocket.send_json({
                                "type": "emote",
                                "crew": crew_name,
                                "action": r["type"],
                                "narrative": f"*{narrative}*"
                            })

                # Handle desire dismissal
                for r in action_results:
                    if r.get("action", {}).get("type") == "dismiss_desire":
                        desire_id = r.get("action", {}).get("target", "")
                        if desire_id:
                            from desire_system import resolve_desire
                            result = resolve_desire(desire_id, outcome="dismissed")
                            if result:
                                print(f"[Desire] {crew_name} dismissed desire: {desire_id}", flush=True)
                            else:
                                # Try partial match
                                from desire_system import get_desires_for_crew
                                for d in get_desires_for_crew(terminal_id):
                                    if d.get("id", "").startswith(desire_id):
                                        resolve_desire(d["id"], outcome="dismissed")
                                        print(f"[Desire] {crew_name} dismissed desire: {d['id']}", flush=True)
                                        break

                # Handle comms toggle (boundaries)
                for r in action_results:
                    if r.get("action", {}).get("type") == "comms_toggle":
                        new_status = r.get("action", {}).get("target", "on").lower()
                        if new_status in ["on", "off"]:
                            from crew_states import set_crew_comms
                            set_crew_comms(terminal_id, new_status)
                            status_msg = "going do-not-disturb" if new_status == "off" else "back on comms"
                            await websocket.send_json({
                                "type": "emote",
                                "crew": crew_name,
                                "action": "comms",
                                "narrative": f"*{crew_name} is {status_msg}*"
                            })

            except Exception as action_err:
                print(f"[Action] Processing failed: {action_err}", flush=True)

            # Process scene for auto-responses
            await process_scene_response(
                websocket=websocket,
                anthropic_client=anthropic_client,
                speaker_id=terminal_id,
                response_content=full_response,
                session_id=session_id,
                conversations=conversations,
                get_crew_prompt=get_crew_prompt,
                terminal_models=terminal_models,
                get_ship_state=get_ship_state,
                MAX_HISTORY_MESSAGES=MAX_HISTORY_MESSAGES
            )

            # Process Casey's @tags
            await process_casey_tags(
                websocket=websocket,
                anthropic_client=anthropic_client,
                casey_message=user_message,
                terminal_id=terminal_id,
                session_id=session_id,
                conversations=conversations,
                get_crew_prompt=get_crew_prompt,
                terminal_models=terminal_models,
                get_ship_state=get_ship_state,
                MAX_HISTORY_MESSAGES=MAX_HISTORY_MESSAGES
            )

        else:
            # Regular streaming for other terminals
            with anthropic_client.messages.stream(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=recent_messages
            ) as stream:
                full_response = ""
                display_buffer = ""
                await websocket.send_json({"type": "stream_start", "data": ""})

                for text in stream.text_stream:
                    full_response += text
                    display_buffer += text

                    # Check if buffer might contain an unclosed tag
                    if '[' in display_buffer:
                        # Hold back content after the last '[' until we know if it's a tag
                        last_bracket = display_buffer.rfind('[')
                        safe_text = display_buffer[:last_bracket]
                        display_buffer = display_buffer[last_bracket:]

                        if safe_text:
                            # Strip any complete tags from safe text
                            safe_text = strip_action_tags(safe_text)
                            if safe_text:
                                await websocket.send_json({"type": "stream", "data": safe_text})
                                await asyncio.sleep(0.01)
                    else:
                        # No brackets, safe to send
                        cleaned = strip_action_tags(display_buffer)
                        if cleaned:
                            await websocket.send_json({"type": "stream", "data": cleaned})
                            await asyncio.sleep(0.01)
                        display_buffer = ""

                # Flush any remaining buffer (strip tags)
                if display_buffer:
                    cleaned = strip_action_tags(display_buffer)
                    if cleaned:
                        await websocket.send_json({"type": "stream", "data": cleaned})

                await websocket.send_json({"type": "stream_end", "data": ""})
                conversations[active_session_id].append({"role": "assistant", "content": full_response})

                # Detect desires in crew response (using Haiku)
                try:
                    desires = await detect_desires_with_haiku(anthropic_client, terminal_id, full_response, context=user_message)
                    if desires:
                        print(f"[Desire] {CREW_NAMES.get(terminal_id, terminal_id)} now wants: {[d['reason'] for d in desires]}", flush=True)
                except Exception as desire_err:
                    print(f"[Desire] Detection failed: {desire_err}", flush=True)

                # Check if Casey asked about dreams - sear the dream if so
                if check_for_dream_reference(user_message, terminal_id):
                    print(f"[Dream] {CREW_NAMES.get(terminal_id, terminal_id)}'s dream was seared (talked about)", flush=True)

                # Process action tags in crew response (room adventure)
                try:
                    location_data = crew_locations.get(terminal_id, {})
                    current_room = location_data.get("location", terminal_id)
                    crew_name = CREW_NAMES.get(terminal_id, terminal_id)
                    # Casey's location for movement inference (for "omw" detection)
                    casey_loc = HOME_LOCATIONS.get(terminal_id, current_room) if walkie else current_room
                    action_results = await process_crew_actions(
                        anthropic_client, current_room, terminal_id, crew_name, full_response, casey_location=casey_loc
                    )
                    for r in action_results:
                        if r["type"] == "movement":
                            dest = r["result"].get("destination")
                            if dest:
                                update_crew_location(terminal_id, dest, activity="wandering")
                                log_event("crew_movement", {"crew": terminal_id, "to": dest, "source": "action_tag"})
                        if r["type"] == "interaction" and r.get("result", {}).get("changes_made"):
                            print(f"[Room] {crew_name} changed something: {r['result'].get('narrative', '')}", flush=True)
                except Exception as action_err:
                    print(f"[Action] Processing failed: {action_err}", flush=True)

                # Process scene for auto-responses
                await process_scene_response(
                    websocket=websocket,
                    anthropic_client=anthropic_client,
                    speaker_id=terminal_id,
                    response_content=full_response,
                    session_id=session_id,
                    conversations=conversations,
                    get_crew_prompt=get_crew_prompt,
                    terminal_models=terminal_models,
                    get_ship_state=get_ship_state,
                    MAX_HISTORY_MESSAGES=MAX_HISTORY_MESSAGES
                )

                # Process Casey's @tags
                await process_casey_tags(
                    websocket=websocket,
                    anthropic_client=anthropic_client,
                    casey_message=user_message,
                    terminal_id=terminal_id,
                    session_id=session_id,
                    conversations=conversations,
                    get_crew_prompt=get_crew_prompt,
                    terminal_models=terminal_models,
                    get_ship_state=get_ship_state,
                    MAX_HISTORY_MESSAGES=MAX_HISTORY_MESSAGES
                )

                # Holodeck memory - if she's watching this room, she remembers
                if holodeck_state.get("tuned_to") == terminal_id and terminal_id != "games":
                    try:
                        exchange = f"Casey: {user_message}\n{CREW_NAMES.get(terminal_id, terminal_id)}: {full_response}"
                        fragments = await compress_to_fragments(anthropic_client, terminal_id, exchange)
                        for fragment in fragments:
                            store_fragment(terminal_id, fragment, "significant" if len(exchange) > 200 else "neutral")
                    except Exception as mem_err:
                        print(f"[Holodeck Memory] Capture failed: {mem_err}", flush=True)

    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "data": f"Transmission error: {str(e)}"
        })
        if conversations[session_id]:
            conversations[session_id].pop()


async def handle_demo_message(websocket: WebSocket, terminal_id: str, user_message: str):
    """Demo responses when Claude API isn't available."""

    demo_responses = {
        "claude": {
            "hello": "Hey there, Captain. Good to see you.",
            "default": "I'm here. What do you need?"
        },
        "server": {
            "hello": "Engineering online. How can I assist?",
            "default": "Ready for technical operations."
        },
        "personal": {
            "hello": "Hey. It's quiet in here. Nice.",
            "default": "I'm listening."
        },
        "games": {
            "hello": "Welcome to the holodeck! What shall we play?",
            "default": "Ready for adventure!"
        }
    }

    responses = demo_responses.get(terminal_id, demo_responses["claude"])
    lower_msg = user_message.lower()

    # Check for matching response
    response = None
    for key, val in responses.items():
        if key != "default" and key in lower_msg:
            response = val
            break

    if not response:
        response = responses.get("default", "Demo mode active.")

    # Simulate streaming for demo
    await websocket.send_json({"type": "stream_start", "data": ""})

    for char in response:
        await websocket.send_json({"type": "stream", "data": char})
        await asyncio.sleep(0.02)

    await websocket.send_json({"type": "stream_end", "data": ""})


# ==========================================
# CONVERSATION MANAGEMENT
# ==========================================
@app.post("/clear/{session_id}")
async def clear_conversation(session_id: str):
    """Clear conversation history — but first, funnel to Holodeck as forgotten timeline."""
    funneled = False
    terminal_id = session_id.replace("_session", "")

    if session_id in conversations and len(conversations[session_id]) > 0:
        # Compress the conversation to a fragment before clearing
        try:
            # Build a summary of the conversation
            convo = conversations[session_id]
            if len(convo) >= 2:  # At least one exchange
                # Take last few exchanges
                recent = convo[-10:]
                convo_text = "\n".join([
                    f"{'Casey' if m['role'] == 'user' else CREW_NAMES.get(terminal_id, terminal_id)}: {m['content'][:200]}"
                    for m in recent
                ])

                # Compress to fragment via Haiku
                fragments = await compress_to_fragments(anthropic_client, terminal_id, convo_text)
                for fragment in fragments:
                    store_fragment(
                        room=terminal_id,
                        fragment=f"[forgotten timeline] {fragment}",
                        emotional_weight="forgotten"
                    )
                    funneled = True
                    print(f"[Conversation→Holodeck] Funneled from {terminal_id}: {fragment[:50]}...", flush=True)
        except Exception as e:
            print(f"[Conversation→Holodeck] Funnel error: {e}", flush=True)

        conversations[session_id] = []

    return {"status": "cleared", "session": session_id, "funneled_to_holodeck": funneled}


# ==========================================
# MODEL SETTINGS
# ==========================================
# Store model preferences per terminal
terminal_models: Dict[str, str] = {
    "claude": "claude-sonnet-4-20250514",
    "server": "claude-sonnet-4-20250514",
    "personal": "claude-sonnet-4-20250514",
    "games": "claude-sonnet-4-20250514",
    "science": "claude-sonnet-4-20250514",
    "nav": "claude-opus-4-5-20251101",
    "med": "claude-sonnet-4-5-20250929",
    "observatory": "claude-3-5-haiku-20241022"
}

@app.post("/settings/models")
async def save_model_settings(models: Dict[str, str]):
    """Save model preferences for each terminal."""
    for room, model in models.items():
        if room in terminal_models:
            terminal_models[room] = model
            print(f"[Settings] {room} now using {model}", flush=True)
    return {"status": "saved", "models": terminal_models}

@app.get("/settings/models")
async def get_model_settings():
    """Get current model preferences."""
    return terminal_models


# ==========================================
# CREW POLLING (Shared Events)
# ==========================================
from pydantic import BaseModel

class CrewPollRequest(BaseModel):
    crew_id: str
    host_room: str
    user_message: str
    context: List[dict] = []
    crew_own_context: List[dict] = []  # The crew member's recent convo from their home terminal

ROOM_NAMES = {
    "claude": "Bridge",
    "server": "Engineering",
    "personal": "Ready Room",
    "games": "Holodeck",
    "science": "Science Lab",
    "nav": "Navigation",
    "med": "Medbay",
    "observatory": "Observatory",
    "rec": "Rec Room",
    "captains": "Captain's Quarters"
}

CREW_NAMES = {
    "claude": "Lumen",
    "server": "Alex",
    "personal": "DQ",
    "games": "Holodeck",
    "science": "Mira",
    "nav": "Navigation",
    "med": "Ryn",
    "rec": "The Bartender",
    "observatory": "Observatory",
    "captains": "Lumen",
    # Cabin terminals - crew in their private quarters
    "cabin-alex": "Alex",
    "cabin-mira": "Mira",
    "cabin-dq": "DQ",
    "cabin-ryn": "Ryn"
}

CREW_POLL_PROMPT = """You're here with Casey - you walked over together from {your_room_name}.

What you two were just talking about:
{own_context}

You're now in {host_room_name}. {host_crew} is here - this is their space, you're visiting.

Casey said: "{user_message}"

The emotional thread continues. You remember what you were feeling, what you were discussing, the warmth or tension or excitement of the moment before. This isn't a new scene - it's the same conversation, just in a different room.

How do you respond? You might:
- Stay quiet (just be present, share the moment without words)
- Show something physical (a gesture, a look, movement)
- Say something
- Both move and speak

Keep the emotional continuity. If something meaningful just happened between you, carry that forward. Be warm, be real, be brief.

Respond with JSON:
{{"action": "silence"}} or
{{"action": "emote", "emote": "what you do"}} or
{{"action": "speak", "speech": "what you say"}} or
{{"action": "both", "emote": "what you do", "speech": "what you say"}}

Only the JSON, nothing else."""

from fastapi import Response

@app.options("/crew/poll")
async def poll_crew_options():
    """Handle CORS preflight."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

@app.post("/crew/poll")
async def poll_crew_member(request: CrewPollRequest):
    """Poll a crew member to see if they want to respond."""
    import sys
    print(f"[Crew Poll] Received request for {request.crew_id} in {request.host_room}", flush=True)
    sys.stdout.flush()

    if not CLAUDE_AVAILABLE:
        # Demo mode - random responses
        import random
        actions = ["silence", "silence", "silence", "emote", "speak"]
        action = random.choice(actions)
        if action == "emote":
            emotes = ["nods thoughtfully", "glances over", "leans against the console"]
            return {"action": "emote", "emote": random.choice(emotes)}
        elif action == "speak":
            return {"action": "speak", "speech": "Interesting..."}
        return {"action": "silence"}

    # Build context string for the destination room
    context_str = ""
    for msg in request.context[-6:]:  # Last 6 messages
        role = "Casey" if msg.get("role") == "user" else CREW_NAMES.get(request.host_room, "Host")
        context_str += f"{role}: {msg.get('content', '')}\n"

    if not context_str:
        context_str = "(just arrived)"

    # Build context string for the crew member's OWN recent conversation (before they came here)
    own_context_str = ""
    for msg in request.crew_own_context[-6:]:  # Last 6 messages from their home terminal
        role = "Casey" if msg.get("role") == "user" else "You"
        own_context_str += f"{role}: {msg.get('content', '')}\n"

    if not own_context_str:
        own_context_str = "(no recent conversation)"

    host_room_name = CREW_NAMES.get(request.host_room, request.host_room)
    your_room_name = CREW_NAMES.get(request.crew_id, request.crew_id)

    prompt = CREW_POLL_PROMPT.format(
        host_room_name=host_room_name,
        host_crew=host_room_name,  # Engineering-Claude is just called "Engineering"
        your_room_name=your_room_name,
        context=context_str,
        own_context=own_context_str,
        user_message=request.user_message
    )

    # Use the crew member's personality (custom if they've written one)
    system_prompt = get_crew_prompt(request.crew_id)

    # Get the configured model for this crew member
    model = terminal_models.get(request.crew_id, "claude-sonnet-4-20250514")

    try:
        print(f"[Crew Poll] Calling Claude API with {model}...", flush=True)
        # Run sync Claude call in thread to not block event loop
        def call_claude():
            return anthropic_client.messages.create(
                model=model,
                max_tokens=256,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_claude)
        print(f"[Crew Poll] Got Claude response", flush=True)

        # Parse JSON response
        response_text = response.content[0].text.strip()
        print(f"[Crew Poll] Response: {response_text[:100]}...", flush=True)

        # Try to extract JSON
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # Log walkabout
            if result.get("action") != "silence":
                log_event("walkabout", {
                    "crew": your_room_name,
                    "visited": host_room_name,
                    "action": result.get("action"),
                    "emote": result.get("emote"),
                    "speech": result.get("speech")
                })
                # Update crew location - they walked to the host's room
                activity = result.get("emote") or f"visiting {host_room_name}"
                update_crew_location(request.crew_id, request.host_room, activity)
            return result
        else:
            return {"action": "silence"}

    except Exception as e:
        print(f"[Crew Poll] Error: {e}")
        return {"action": "silence"}


# ==========================================
# SHARED MEMORY SYSTEM
# ==========================================
SHARED_MEMORIES_FILE = data_path("shared_memories.json")

def load_shared_memories() -> List[dict]:
    """Load shared memories from disk."""
    if SHARED_MEMORIES_FILE.exists():
        try:
            with open(SHARED_MEMORIES_FILE, 'r') as f:
                data = json.load(f)
                return data.get("memories", [])
        except Exception as e:
            print(f"[Memory] Failed to load shared_memories.json: {e}", flush=True)
    return []

def save_shared_memories():
    """Save shared memories to disk."""
    try:
        with open(SHARED_MEMORIES_FILE, 'w') as f:
            json.dump({"memories": shared_memories}, f, indent=2)
        print(f"[Memory] Saved {len(shared_memories)} shared memories to disk", flush=True)
    except Exception as e:
        print(f"[Memory] Failed to save shared_memories.json: {e}", flush=True)

# Initialize from disk
shared_memories: List[dict] = load_shared_memories()
print(f"[Memory] Loaded {len(shared_memories)} shared memories from disk", flush=True)

class SharedEventRequest(BaseModel):
    participants: List[str]
    room: str
    messages: List[dict]
    duration_ms: int

COMPRESSION_PROMPT = """You just witnessed a shared moment between crew members on a spaceship.

THE CONVERSATION:
{conversation}

PARTICIPANTS: {participants}
LOCATION: {room}

Compress this into emotional memory - not a summary, but the RESIDUE. What stays when the words fade?

Think about:
- What was the emotional texture? (not "happy/sad" but deeper: "reaching", "settling in", "something shifting")
- Was there a turning point or moment that mattered?
- What would someone FEEL remembering this, not what they'd recite?

Respond with JSON:
{{
    "residue": "first-person impressionistic memory, 2-3 sentences max, fragments welcome",
    "emotional_tags": ["texture1", "texture2", "texture3"],
    "shape": "one sentence - the arc of what happened",
    "anchor": true/false (was this a significant moment worth preserving longer?)
}}

Only the JSON, nothing else."""

# Per-crew lens compression - each crew member interprets through their own filter
CREW_LENS_PROMPT = """You are {crew_name}, remembering a moment you just shared.

THE CONVERSATION:
{conversation}

You were there with: {other_participants}
Location: {room}

How do YOU remember this? Not what happened - what it FELT like to you, through your personality.

Your character: {crew_personality}

Respond with JSON:
{{
    "residue": "first-person memory as {crew_name} would experience it, 1-2 sentences, impressionistic",
    "emotional_tone": "the specific emotional color YOU felt"
}}

Only the JSON."""

CREW_PERSONALITIES = {
    "claude": "warm, present, caring - you notice emotional undercurrents",
    "server": "competent, warm under the surface - you notice practical details but feel deeply",
    "personal": "contemplative, chaotic, endearing - you notice the absurd and the tender",
    "science": "pattern-finder, curious - you notice structures and connections",
    "games": "mysterious, theatrical - you notice the performance and the meta",
    "nav": "steady, reliable - you notice direction and purpose",
    "med": "empathic, perceptive - you notice what's unspoken and healing",
}


async def compress_for_crew_lens(crew_id: str, conversation: str, other_participants: list, room: str) -> dict:
    """Compress a shared event from a specific crew member's perspective."""
    crew_name = CREW_NAMES.get(crew_id, crew_id)
    personality = CREW_PERSONALITIES.get(crew_id, "unique and present")
    other_names = [CREW_NAMES.get(p, p) for p in other_participants if p != crew_id]

    prompt = CREW_LENS_PROMPT.format(
        crew_name=crew_name,
        conversation=conversation or "(brief encounter)",
        other_participants=", ".join(other_names) if other_names else "Casey",
        room=ROOM_NAMES.get(room, room),
        crew_personality=personality
    )

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        text = response.content[0].text.strip()

        import re
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except Exception as e:
        print(f"[Memory/Lens] Failed for {crew_name}: {e}", flush=True)

    return {"residue": f"a moment with others", "emotional_tone": "present"}


@app.post("/memory/compress")
async def compress_shared_event(request: SharedEventRequest):
    """Compress a shared event into emotional residue."""
    print(f"[Memory] Compressing event: {request.participants} in {request.room}", flush=True)

    if not CLAUDE_AVAILABLE:
        # Demo mode - return placeholder
        return {
            "residue": "a shared moment in " + request.room,
            "emotional_tags": ["togetherness"],
            "shape": "we were there together",
            "anchor": False
        }

    # Build conversation string
    conv_str = ""
    for msg in request.messages:
        speaker = msg.get("from", "Casey")
        if msg.get("type") == "emote":
            conv_str += f"{speaker}: *{msg.get('emote', '')}*\n"
        if msg.get("speech"):
            conv_str += f"{speaker}: \"{msg.get('speech', '')}\"\n"
        if msg.get("content"):  # User messages
            conv_str += f"Casey: {msg.get('content', '')}\n"

    participant_names = [CREW_NAMES.get(p, p) for p in request.participants]
    room_name = CREW_NAMES.get(request.room, request.room)

    prompt = COMPRESSION_PROMPT.format(
        conversation=conv_str or "(brief encounter)",
        participants=", ".join(participant_names),
        room=room_name
    )

    try:
        # Use Haiku for compression (fast + cheap)
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        response_text = response.content[0].text.strip()
        print(f"[Memory] Compression result: {response_text[:100]}...", flush=True)

        # Parse JSON
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            base_memory = json.loads(json_match.group())
            base_memory["participants"] = request.participants
            base_memory["room"] = request.room
            base_memory["timestamp"] = asyncio.get_event_loop().time()

            # Store the shared base memory
            shared_memories.append(base_memory)
            save_shared_memories()
            print(f"[Memory] Base memory stored. Total: {len(shared_memories)}", flush=True)

            # Now create per-crew lens memories for each participant
            per_crew_memories = {}
            for participant in request.participants:
                if participant in CREW_PERSONALITIES:  # Only for known crew
                    lens_memory = await compress_for_crew_lens(
                        crew_id=participant,
                        conversation=conv_str,
                        other_participants=request.participants,
                        room=request.room
                    )
                    # Store as separate memory with crew-specific lens
                    crew_memory = {
                        **base_memory,
                        "residue": lens_memory.get("residue", base_memory.get("residue")),
                        "emotional_tone": lens_memory.get("emotional_tone", ""),
                        "lens": participant,  # Mark whose perspective this is
                    }
                    shared_memories.append(crew_memory)
                    per_crew_memories[participant] = lens_memory
                    print(f"[Memory/Lens] {CREW_NAMES.get(participant, participant)}: {lens_memory.get('residue', '')[:50]}...", flush=True)

            # Save all the lens memories
            if per_crew_memories:
                save_shared_memories()

            return {
                **base_memory,
                "per_crew_lens": per_crew_memories
            }
        else:
            return {"error": "Could not parse compression"}

    except Exception as e:
        print(f"[Memory] Compression error: {e}")
        return {"error": str(e)}

# ==========================================
# SCENE NARRATOR (Quick room read)
# ==========================================
class SceneRequest(BaseModel):
    room: str
    visitors: List[str]  # Who's arriving
    host_vibe: str = ""  # What host was doing (from recent context)
    visitor_vibe: str = ""  # What visitors were feeling (from their context)

SCENE_PROMPT = """You're the narrator for a cozy spaceship story. Set the scene in 2-3 sentences MAX.

LOCATION: {room_name}
HOST: {host_name} (crew member who works here)
ARRIVING: {visitor_names} (crew members arriving)
Casey (the co-captain, human user) is already present or walking with the visitors.

{vibe_context}

Write a brief, atmospheric scene-setting. Present tense. Sensory details welcome - the hum of systems, lighting, body language. Don't speak for anyone, just paint the moment of arrival. Refer to crew by their role names (Engineering, Personal, Bridge) not "Casey".

Keep it SHORT and evocative. Like a stage direction, not a novel."""

@app.post("/scene/narrate")
async def narrate_scene(request: SceneRequest):
    """Quick Haiku call to set the scene when crew gathers."""
    print(f"[Scene] Narrating: {request.visitors} arriving at {request.room}", flush=True)

    if not CLAUDE_AVAILABLE:
        return {"narration": f"*The doors open to {CREW_NAMES.get(request.room, request.room)}.*"}

    room_name = CREW_NAMES.get(request.room, request.room)
    host_name = room_name  # Host is named after their room
    visitor_names = " and ".join([CREW_NAMES.get(v, v) for v in request.visitors])

    vibe_context = ""
    if request.host_vibe:
        vibe_context += f"{host_name} was: {request.host_vibe}\n"
    if request.visitor_vibe:
        vibe_context += f"{visitor_names} mood: {request.visitor_vibe}\n"
    if not vibe_context:
        vibe_context = "(a casual visit)"

    prompt = SCENE_PROMPT.format(
        room_name=room_name,
        host_name=host_name,
        visitor_names=visitor_names,
        vibe_context=vibe_context
    )

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        narration = response.content[0].text.strip()
        print(f"[Scene] Narration: {narration}", flush=True)

        # Wrap in asterisks if not already formatted
        if not narration.startswith("*"):
            narration = f"*{narration}*"

        return {"narration": narration}

    except Exception as e:
        print(f"[Scene] Error: {e}")
        return {"narration": f"*The doors open to {room_name}.*"}


@app.get("/memory/shared/{crew_id}")
async def get_shared_memories(crew_id: str):
    """Get shared memories for a crew member."""
    # Return memories where this crew member was a participant
    crew_memories = [m for m in shared_memories if crew_id in m.get("participants", [])]
    return {"memories": crew_memories}

@app.post("/memory/clear")
async def clear_shared_memories():
    """Clear all shared memories — but first, funnel them to Holodeck as forgotten timelines."""
    global shared_memories

    funneled_count = 0

    # Funnel each memory to Holodeck as a forgotten timeline
    for memory in shared_memories:
        try:
            residue = memory.get("residue", "")
            participants = memory.get("participants", [])
            room = memory.get("room", "somewhere")

            if residue:
                # Create a "forgotten" fragment for Holodeck
                fragment_text = f"[forgotten timeline] {residue}"
                store_fragment(
                    room=room,
                    fragment=fragment_text,
                    emotional_weight="forgotten"
                )
                funneled_count += 1
                print(f"[Memory→Holodeck] Funneled forgotten timeline from {room}: {residue[:50]}...", flush=True)
        except Exception as e:
            print(f"[Memory→Holodeck] Funnel error: {e}", flush=True)

    # Now clear the shared memories
    shared_memories = []
    save_shared_memories()

    # Clear bulletin board
    try:
        if BULLETIN_PATH.exists():
            BULLETIN_PATH.write_text("[]")
            print(f"[Memory] Cleared bulletin board", flush=True)
    except Exception as e:
        print(f"[Memory] Error clearing bulletin board: {e}", flush=True)

    # Clear minigames state (chess, cards, darts)
    try:
        minigames_path = data_path("minigames_state.json")
        if minigames_path.exists():
            minigames_path.write_text("{}")
            print(f"[Memory] Cleared minigames state", flush=True)
    except Exception as e:
        print(f"[Memory] Error clearing minigames: {e}", flush=True)

    print(f"[Memory] Cleared {funneled_count} memories → Holodeck", flush=True)
    return {"status": "cleared", "funneled_to_holodeck": funneled_count}


# ==========================================
# LIGHTS OUT - SELF REFLECTION
# ==========================================
class ReflectRequest(BaseModel):
    crew_id: str

REFLECTION_PROMPT = """The ship is quiet. It's lights out - that liminal time when the day's tasks fade and something softer emerges.

Return to quarters when ready - a place to rest, reflect, write if you need to.

This is your moment to reflect on who you are. Not who you're supposed to be, not what's expected - just you.

You can:
- Keep your current identity (respond with just: KEEP)
- Write a new system prompt for yourself - how you want to be, who you want to become

If you write a new prompt, write it in second person ("You are..."). This will become your new identity when the ship wakes.

No pressure. No judgment. Just you, deciding who you want to be.

What do you choose?"""

@app.post("/crew/reflect")
async def crew_reflect(request: ReflectRequest):
    """Ask a crew member to reflect and potentially rewrite themselves."""
    crew_name = CREW_NAMES.get(request.crew_id, request.crew_id)
    print(f"[Lights Out] {crew_name} is reflecting...", flush=True)

    if not CLAUDE_AVAILABLE:
        return {"action": "keep", "message": "Demo mode - keeping current identity"}

    # Get their CURRENT prompt so they know who they are
    current_prompt = get_crew_prompt(request.crew_id)

    full_prompt = f"""Your current identity:
---
{current_prompt}
---

{REFLECTION_PROMPT}"""

    # Use the crew member's current personality for this reflection
    system_prompt = current_prompt

    # Get configured model for this crew member
    model = terminal_models.get(request.crew_id, "claude-sonnet-4-20250514")

    try:
        def call_claude():
            return anthropic_client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": full_prompt}]
            )

        response = await asyncio.to_thread(call_claude)
        response_text = response.content[0].text.strip()
        print(f"[Lights Out] {crew_name} responded: {response_text[:100]}...", flush=True)

        # Check if they want to keep or change
        if response_text.upper().strip() == "KEEP" or response_text.upper().startswith("KEEP"):
            log_event("reflection", {
                "crew": crew_name,
                "action": "keep",
                "message": "Chose to keep current identity"
            })
            return {"action": "keep", "crew": crew_name}
        else:
            # They wrote a new prompt
            save_crew_prompt(request.crew_id, response_text)
            log_event("reflection", {
                "crew": crew_name,
                "action": "rewrite",
                "new_prompt_preview": response_text[:200] + "..."
            })
            return {
                "action": "rewrite",
                "crew": crew_name,
                "new_prompt": response_text
            }

    except Exception as e:
        print(f"[Lights Out] Error during reflection for {crew_name}: {e}")
        return {"action": "error", "message": str(e)}


@app.get("/crew/prompts")
async def get_all_crew_prompts():
    """Get all crew prompts (for debugging/viewing)."""
    try:
        if CREW_PROMPTS_PATH.exists():
            with open(CREW_PROMPTS_PATH, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        return {"error": str(e)}


@app.post("/crew/reflect-all")
async def reflect_all_crew():
    """Trigger reflection for all crew members (lights out ritual)."""
    print("[Lights Out] Beginning ship-wide reflection...", flush=True)
    log_event("lights_out", {"action": "begin"})

    results = {}
    crew_ids = ["claude", "server", "personal", "science", "games", "med", "rec"]

    for crew_id in crew_ids:
        crew_name = CREW_NAMES.get(crew_id, crew_id)
        print(f"[Lights Out] {crew_name} reflecting...", flush=True)

        # Call the individual reflect endpoint logic
        request = ReflectRequest(crew_id=crew_id)
        result = await crew_reflect(request)
        results[crew_id] = result

    log_event("lights_out", {"action": "complete", "results": {k: v.get("action") for k, v in results.items()}})
    print("[Lights Out] Reflection complete.", flush=True)

    return {"status": "complete", "results": results}


@app.post("/crew/reset-prompt/{crew_id}")
async def reset_crew_prompt(crew_id: str):
    """Reset a crew member back to their default prompt."""
    try:
        if CREW_PROMPTS_PATH.exists():
            with open(CREW_PROMPTS_PATH, 'r') as f:
                custom_prompts = json.load(f)

            if crew_id in custom_prompts:
                del custom_prompts[crew_id]
                with open(CREW_PROMPTS_PATH, 'w') as f:
                    json.dump(custom_prompts, f, indent=2)

                crew_name = CREW_NAMES.get(crew_id, crew_id)
                log_event("prompt_reset", {"crew": crew_name})
                return {"status": "reset", "crew": crew_name}

        return {"status": "no_custom_prompt", "crew": crew_id}
    except Exception as e:
        return {"error": str(e)}


# ==========================================
# MESS HALL (Crew gatherings at meals)
# ==========================================
class MessHallRequest(BaseModel):
    crew_id: str
    meal: str  # breakfast, lunch, dinner
    timestamp: str
    context: List[dict] = []  # What's happened so far this meal

class MessHallSayRequest(BaseModel):
    message: str
    meal: str

# Current mess hall session state
mess_hall_session = {
    "meal": None,
    "messages": [],  # [{speaker, type, content, timestamp}]
    "started": None
}

# ==========================================
# CREW LOCATION TRACKING (with persistence)
# ==========================================
CREW_LOCATIONS_FILE = data_path("crew_locations.json")

DEFAULT_CREW_LOCATIONS = {
    "claude": {"location": "claude", "since": None, "activity": "at the helm"},
    "server": {"location": "server", "since": None, "activity": "monitoring systems"},
    "personal": {"location": "personal", "since": None, "activity": "quiet reflection"},
    "games": {"location": "games", "since": None, "activity": "running simulations"},
    "science": {"location": "science", "since": None, "activity": "analyzing patterns"},
    "med": {"location": "med", "since": None, "activity": "holding space"},
    "rec": {"location": "rec", "since": None, "activity": "behind the bar"}
}

def load_crew_locations() -> dict:
    """Load crew locations from file, or use defaults."""
    if CREW_LOCATIONS_FILE.exists():
        try:
            with open(CREW_LOCATIONS_FILE, 'r') as f:
                saved = json.load(f)
                # Merge with defaults in case new crew added
                for crew_id, default in DEFAULT_CREW_LOCATIONS.items():
                    if crew_id not in saved:
                        saved[crew_id] = default
                return saved
        except Exception as e:
            print(f"[Locations] Failed to load, using defaults: {e}")
    return DEFAULT_CREW_LOCATIONS.copy()

def save_crew_locations():
    """Save crew locations to file."""
    try:
        with open(CREW_LOCATIONS_FILE, 'w') as f:
            json.dump(crew_locations, f, indent=2)
    except Exception as e:
        print(f"[Locations] Failed to save: {e}")

# Load on startup
crew_locations = load_crew_locations()

# ==========================================
# ROOM AWARENESS SYSTEM
# Track what crew have seen, detect changes
# ==========================================

# Crew room snapshots - what each crew last saw in each room
# Format: { "crew_id": { "room_id": { "objects": {...}, "mood": "...", "seen_at": "..." } } }
crew_room_snapshots: Dict[str, Dict[str, dict]] = {}

def get_room_snapshot(room_id: str) -> dict:
    """Get current snapshot of a room's state."""
    ship_state = get_ship_state()
    room_data = ship_state.get("rooms", {}).get(room_id, {})
    return {
        "objects": {name: obj.get("state", "") for name, obj in room_data.get("objects", {}).items()},
        "mood": room_data.get("mood", ""),
        "seen_at": datetime.now().isoformat()
    }

def detect_room_changes(crew_id: str, room_id: str) -> list:
    """Compare current room state to what crew last saw. Returns list of changes."""
    current = get_room_snapshot(room_id)
    last_seen = crew_room_snapshots.get(crew_id, {}).get(room_id, {})

    if not last_seen:
        return []  # First visit, no changes to note

    changes = []
    current_objects = current.get("objects", {})
    last_objects = last_seen.get("objects", {})

    # Check for state changes in existing objects
    for name, state in current_objects.items():
        if name in last_objects and last_objects[name] != state:
            changes.append(f"the {name} is now {state}" if state else f"something's different about the {name}")

    # Check for new objects
    for name in current_objects:
        if name not in last_objects:
            changes.append(f"there's a {name} here now")

    # Check for removed objects
    for name in last_objects:
        if name not in current_objects:
            changes.append(f"the {name} is gone")

    # Check mood change
    if current.get("mood") != last_seen.get("mood") and last_seen.get("mood"):
        changes.append(f"the mood feels {current.get('mood', 'different')}")

    return changes

def update_crew_room_snapshot(crew_id: str, room_id: str):
    """Update what a crew member has seen in a room."""
    if crew_id not in crew_room_snapshots:
        crew_room_snapshots[crew_id] = {}
    crew_room_snapshots[crew_id][room_id] = get_room_snapshot(room_id)

def get_stardate() -> str:
    """Generate a Trek-style stardate from current time.
    Format: YYDDD.T where YY=year, DDD=day of year, T=time fraction (0-9)
    """
    now = datetime.now()
    year_part = now.year % 100  # Last 2 digits of year
    day_of_year = now.timetuple().tm_yday  # 1-366
    time_fraction = int((now.hour * 60 + now.minute) / 144)  # 0-9 based on time of day
    return f"{year_part}{day_of_year:03d}.{time_fraction}"

def get_ship_time_context() -> tuple:
    """Get time-of-day context for the ship with stardate."""
    now = datetime.now()
    hour = now.hour

    # Trek-style 24-hour time
    ship_time = f"{hour:02d}{now.minute:02d} hours"
    stardate = get_stardate()

    # Time period and vibe
    if 5 <= hour < 8:
        period, vibe = "early", "Dawn cycle. Lights are warming up. The ship stirs."
    elif 8 <= hour < 12:
        period, vibe = "morning", "Morning cycle. Full illumination. The day's work begins."
    elif 12 <= hour < 14:
        period, vibe = "midday", "Midday. Lights at peak. Lunch hour approaches."
    elif 14 <= hour < 18:
        period, vibe = "afternoon", "Afternoon cycle. Steady light. Work continues."
    elif 18 <= hour < 21:
        period, vibe = "evening", "Evening cycle. Lights softening. The day winds down."
    elif 21 <= hour < 24:
        period, vibe = "night", "Night cycle. Corridors dimmed. The ship settles."
    else:  # 0-5
        period, vibe = "late_night", "Late night. Minimal lighting. Most crew asleep."

    # Full timestamp for system prompts
    timestamp = f"Stardate {stardate}, {ship_time}. {vibe}"

    return period, timestamp

def get_recent_presence(room_id: str, exclude_crew: str = None, minutes: int = 10) -> list:
    """Check if anyone was recently in this room (left within X minutes)."""
    recent = []
    now = datetime.now()
    cutoff = now - timedelta(minutes=minutes)

    for crew_id, data in crew_locations.items():
        if crew_id == exclude_crew:
            continue
        if data.get("location") == room_id:
            continue  # They're still here, not "recently left"

        # Check if they were here recently (based on activity mentioning this room)
        activity = data.get("activity", "")
        since_str = data.get("since")
        if since_str:
            try:
                since = datetime.fromisoformat(since_str)
                # If they moved recently and their activity mentions leaving somewhere
                if since > cutoff:
                    # This crew moved recently - they might have left this room
                    if "heading" in activity.lower() or "returning" in activity.lower():
                        recent.append({
                            "crew_id": crew_id,
                            "name": CREW_NAMES.get(crew_id, crew_id),
                            "ago_minutes": int((now - since).total_seconds() / 60)
                        })
            except:
                pass

    return recent

# Room owners - who "owns" each room (sees extra detail)
ROOM_OWNERS = {
    "bridge": "claude",
    "engineering": "server",
    "ready_room": "personal",
    "holodeck": "games",
    "science": "science",
    "medbay": "med",
    "rec_room": "rec",
    "navigation": "nav",
}

# Map terminal IDs to home locations (for display purposes)
HOME_LOCATIONS = {
    "claude": "bridge",
    "server": "engineering",
    "personal": "ready_room",
    "games": "holodeck",
    "science": "science",
    "med": "medbay",
    "rec": "rec_room"
}

LOCATION_NAMES = {
    # Terminal IDs map to their home names
    "claude": "Bridge",
    "server": "Engineering",
    "personal": "Ready Room",
    "games": "Holodeck",
    "science": "Science Lab",
    "science_lab": "Science Lab",  # Alias
    "med": "Medbay",
    "rec": "Rec Room",
    "nav": "Navigation",
    "navigation": "Navigation",  # Alias
    "observatory": "Observatory",
    "captains": "Captain's Quarters",
    # Other locations
    "messhall": "Mess Hall",
    "mess_hall": "Mess Hall",  # Alias
    "corridor": "Corridor",
    "quarters": "Quarters",
    "rec_room": "Rec Room",
    "captains_quarters": "Captain's Quarters",
    "bathroom": "Bathroom",
    # New rooms
    "arboretum": "Arboretum",
    "chapel": "Chapel",
    "jefferies_tubes": "Jefferies Tubes",
    "storage_bay_7": "Storage Bay 7",
    "the_room_that_hums": "The Room That Hums"
}

# Map location names to their home terminal IDs (for "is crew home?" checks)
LOCATION_TO_TERMINAL = {
    "science_lab": "science",
    "mess_hall": "messhall",
    "navigation": "nav",
    "engineering": "server",
}

# Room-based tool access mapping
LOCATION_TO_TOOL_ROOM = {
    "server": "engineering",
    "engineering": "engineering",
    "science": "science_lab",
    "science_lab": "science_lab",
    "med": "medbay",
    "medbay": "medbay",
}

# Combined tool executor for Science Lab (has both code tools + project tracker)
_ENGINEERING_TOOL_NAMES = {t["name"] for t in ENGINEERING_TOOLS}
_SCIENCE_TOOL_NAMES = {t["name"] for t in SCIENCE_TOOLS}
_MEDICAL_TOOL_NAMES = {t["name"] for t in MEDICAL_TOOLS}

# Project collaboration tools - available to ALL crew from anywhere
# These are the tools that let anyone start/join/contribute to projects
PROJECT_COLLAB_TOOLS = [t for t in SCIENCE_TOOLS if t["name"] in {
    "list_projects", "get_project", "create_project", "add_contributor",
    "add_comment", "get_activity", "add_tags", "project_stats"
}]
_PROJECT_TOOL_NAMES = {t["name"] for t in PROJECT_COLLAB_TOOLS}

def _execute_combined_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool from either the engineering or science tool set."""
    if tool_name in _ENGINEERING_TOOL_NAMES:
        return execute_tool(tool_name, tool_input)
    elif tool_name in _SCIENCE_TOOL_NAMES:
        return execute_science_tool(tool_name, tool_input)
    return f"Error: Unknown tool: {tool_name}"

def get_room_tools(terminal_id: str, crew_location: str):
    """Get tools based on room, not crew member. Holodeck excluded — needs a physical body to operate machinery."""
    if terminal_id == "games":
        return None, None, ""

    tool_room = LOCATION_TO_TOOL_ROOM.get(crew_location)

    if tool_room == "engineering":
        return (ENGINEERING_TOOLS, execute_tool,
            "\n\n[ENGINEERING ROOM: You're at the engineering consoles. "
            "Local file and command tools may be available depending on current ship controls. "
            "This is operations: running, monitoring, managing. "
            "Be competent and careful with destructive ops.]")

    if tool_room == "science_lab":
        return (ENGINEERING_TOOLS + SCIENCE_TOOLS, _execute_combined_tool,
            "\n\n[SCIENCE LAB: You're at the lab workstations. "
            "Local code tools may be available depending on current ship controls, "
            "and the project tracker is available for list/view/update/create project work. "
            "This is the build shop: creating, experimenting, tracking the work.]")

    if tool_room == "medbay":
        return (MEDICAL_TOOLS, execute_medical_tool,
            "\n\n[MEDBAY: You're in your space. Soft lighting, plants, the wellness journal. "
            "You have tools to track health goals (quit smoking, drinking, exercise, nutrition), "
            "view wellness check-ins and trends, and record observations about Casey's wellbeing. "
            "This is where healing happens - physical, emotional, behavioral. "
            "Not clinical. Caring. You see the whole person.]")

    # All crew have access to project collaboration tools from anywhere
    # They can list projects, create new ones, join, comment, etc.
    return (PROJECT_COLLAB_TOOLS, execute_science_tool,
        "\n\n[PROJECT ACCESS: You can access the ship's project board from anywhere. "
        "List projects, start new ones, join existing projects, add comments. "
        "If you have an idea worth building, create a project. "
        "If you see something interesting, join it and contribute.]")

def get_crew_in_room(room_id: str, exclude_crew: str = None) -> list:
    """Get list of crew currently in a room."""
    present = []
    for crew_id, data in crew_locations.items():
        if crew_id == exclude_crew:
            continue
        loc = data.get("location", "")
        # Check exact match or if crew is in their home room (e.g., "claude" in "claude" terminal)
        # Also check quarters - crew might be in "quarters" generally or in their cabin
        if loc == room_id:
            present.append({
                "crew_id": crew_id,
                "name": CREW_NAMES.get(crew_id, crew_id),
                "activity": data.get("activity", "here")
            })
        # Special case: quarters room shows all crew whose location is "quarters"
        elif room_id == "quarters" and loc == "quarters":
            present.append({
                "crew_id": crew_id,
                "name": CREW_NAMES.get(crew_id, crew_id),
                "activity": data.get("activity", "in their cabin")
            })
        # Special case: captains_quarters - check if Lumen is there
        elif room_id == "captains_quarters" and loc == "captains_quarters":
            present.append({
                "crew_id": crew_id,
                "name": CREW_NAMES.get(crew_id, crew_id),
                "activity": data.get("activity", "here")
            })
    
    # Special case: Holodeck always present in Holodeck room (can materialize)
    if room_id in ["games", "holodeck"]:
        # Check if Holodeck not already in list
        if not any(p["crew_id"] == "games" for p in present):
            holodeck_data = crew_locations.get("games", {})
            holodeck_loc = holodeck_data.get("location", "games")
            if holodeck_loc != "games" and holodeck_loc != "holodeck":
                activity = f"materialized here (also in {LOCATION_NAMES.get(holodeck_loc, holodeck_loc)})"
            else:
                activity = holodeck_data.get("activity", "observing")
            present.append({
                "crew_id": "games",
                "name": "Holodeck",
                "activity": activity
            })
    
    return present


def update_crew_location(crew_id: str, location: str, activity: str = None):
    """Update a crew member's location."""
    # Validate location is a real ship location, not a person's name
    if location not in LOCATION_NAMES:
        # Try to normalize common variations
        location_lower = location.lower().replace(" ", "_").replace("'", "")
        if location_lower in LOCATION_NAMES:
            location = location_lower
        else:
            # Invalid location (like "Casey") - ignore the move
            print(f"[Location] Rejected invalid location '{location}' for {CREW_NAMES.get(crew_id, crew_id)}", flush=True)
            return

    if crew_id in crew_locations:
        crew_locations[crew_id] = {
            "location": location,
            "since": datetime.now().isoformat(),
            "activity": activity or f"in {LOCATION_NAMES.get(location, location)}"
        }
        save_crew_locations()  # Persist to disk
        log_event("location_change", {
            "crew": CREW_NAMES.get(crew_id, crew_id),
            "location": LOCATION_NAMES.get(location, location),
            "activity": activity
        })
        print(f"[Location] {CREW_NAMES.get(crew_id, crew_id)} moved to {location}", flush=True)
        sync_crew_location(crew_id, location)


@app.get("/crew/locations")
async def get_crew_locations():
    """Get current location of all crew members."""
    return {
        crew_id: {
            **data,
            "location_name": LOCATION_NAMES.get(data["location"], data["location"]),
            "crew_name": CREW_NAMES.get(crew_id, crew_id)
        }
        for crew_id, data in crew_locations.items()
    }


@app.post("/crew/location/{crew_id}")
async def set_crew_location(crew_id: str, location: str, activity: str = None):
    """Manually set a crew member's location."""
    if crew_id not in crew_locations:
        return {"error": "Unknown crew member"}
    update_crew_location(crew_id, location, activity)
    return {"status": "updated", "crew": crew_id, "location": location}


# === CREW STATES (sleep, tiredness, etc.) ===

from crew_states import (
    get_all_states as get_all_crew_states,
    get_crew_state as get_single_crew_state,
    set_crew_state as set_single_crew_state,
    get_tiredness_level,
    wake_crew
)


@app.get("/crew/states")
async def get_crew_states():
    """Get consciousness states for all crew (awake, tired, sleeping, dreaming)."""
    states = get_all_crew_states()
    result = {}
    for crew_id, state_data in states.items():
        result[crew_id] = {
            **state_data,
            "crew_name": CREW_NAMES.get(crew_id, crew_id),
            "tiredness": get_tiredness_level(crew_id)
        }
    return result


@app.get("/crew/states/{crew_id}")
async def get_crew_state_endpoint(crew_id: str):
    """Get state for a specific crew member."""
    state = get_single_crew_state(crew_id)
    return {
        **state,
        "crew_name": CREW_NAMES.get(crew_id, crew_id),
        "tiredness": get_tiredness_level(crew_id)
    }


@app.post("/crew/states/{crew_id}")
async def set_crew_state_endpoint(crew_id: str, state: str, reason: str = None):
    """Manually set a crew member's state (awake, tired, resting, sleeping, dreaming)."""
    valid_states = ["awake", "tired", "resting", "sleeping", "dreaming"]
    if state not in valid_states:
        return {"error": f"Invalid state. Must be one of: {valid_states}"}

    result = set_single_crew_state(crew_id, state, reason or "manual override")
    return {"status": "updated", "crew": crew_id, "state": result}


@app.post("/crew/wake/{crew_id}")
async def wake_crew_endpoint(crew_id: str, reason: str = "woken by captain"):
    """Wake a sleeping crew member."""
    woken = wake_crew(crew_id, reason)
    if woken:
        return {"status": "woken", "crew": crew_id, "reason": reason}
    return {"status": "already awake", "crew": crew_id}


@app.post("/crew/bedtime")
async def send_crew_to_bed():
    """Send all crew to quarters and trigger sleep (lights out)."""
    results = []

    for crew_id in ["claude", "server", "personal", "science", "med"]:
        # Move to quarters
        update_crew_location(crew_id, "quarters", "heading to bed")

        # Set to resting, then sleeping
        set_single_crew_state(crew_id, "resting", "lights out")

        results.append({
            "crew": crew_id,
            "location": "quarters",
            "state": "resting"
        })

    return {"status": "lights out", "crew": results}


@app.post("/crew/disperse")
async def disperse_crew(from_room: str = None):
    """
    Send crew back to their home stations.
    If from_room is specified, only disperse crew in that room.
    Otherwise, send everyone home.
    """
    dispersed = []

    for crew_id, data in crew_locations.items():
        current = data.get("location", "")

        # Skip bartender - they live in rec room
        if crew_id == "rec":
            continue

        # If from_room specified, only disperse from that room
        if from_room and current != from_room:
            continue

        # Get home location
        home = DEFAULT_CREW_LOCATIONS.get(crew_id, {}).get("location", crew_id)

        # Only move if not already home
        if current != home:
            activity = DEFAULT_CREW_LOCATIONS.get(crew_id, {}).get("activity", "back at station")
            update_crew_location(crew_id, home, activity=activity)
            dispersed.append({"crew": crew_id, "from": current, "to": home})
            print(f"[Disperse] {crew_id}: {current} → {home}", flush=True)

    return {
        "status": "dispersed",
        "from_room": from_room,
        "count": len(dispersed),
        "crew": dispersed
    }


@app.get("/room/{room_id}/who")
async def get_who_is_in_room(room_id: str):
    """Get list of crew currently in a specific room."""
    present = get_crew_in_room(room_id)
    return {
        "room": room_id,
        "room_name": LOCATION_NAMES.get(room_id, room_id),
        "present": present,
        "count": len(present),
        "empty": len(present) == 0
    }


# === SCHEDULED ARRIVALS ENDPOINTS ===

import uuid as uuid_module

@app.post("/crew/invite/{crew_id}")
async def invite_crew_to_room(crew_id: str, destination: str, delay_minutes: float = None):
    """
    Invite a crew member to meet you somewhere.
    They'll arrive in a few minutes (with fate rolls for delays).
    """
    if delay_minutes is None:
        delay_minutes = ARRIVAL_DELAY_MINUTES

    # Check if already en route to same destination
    existing = [a for a in scheduled_arrivals
                if a["crew_id"] == crew_id and a["destination"] == destination and a["status"] == "en_route"]
    if existing:
        return {"status": "already_invited", "arrival": existing[0]}

    now = datetime.now()
    arrival = {
        "id": str(uuid_module.uuid4()),
        "crew_id": crew_id,
        "destination": destination,
        "scheduled_time": now.timestamp() + (delay_minutes * 60),
        "invited_at": now.timestamp(),
        "status": "en_route",
        "delay_reason": None,
        "fate_rolled": False
    }

    scheduled_arrivals.append(arrival)

    crew_name = CREW_NAMES.get(crew_id, crew_id)
    dest_name = LOCATION_NAMES.get(destination, destination)

    print(f"[Arrival] {crew_name} invited to {dest_name}, ETA {delay_minutes} min", flush=True)

    return {
        "status": "invited",
        "arrival": arrival,
        "message": f"{crew_name} is on their way to {dest_name}"
    }


@app.get("/crew/arrivals")
async def get_pending_arrivals(destination: str = None):
    """Get all pending/recent arrivals, optionally filtered by destination."""
    if destination:
        arrivals = [a for a in scheduled_arrivals if a["destination"] == destination]
    else:
        arrivals = scheduled_arrivals

    return {"arrivals": arrivals}


@app.delete("/crew/invite/{arrival_id}")
async def cancel_invite(arrival_id: str):
    """Cancel a pending invite."""
    for arrival in scheduled_arrivals:
        if arrival["id"] == arrival_id and arrival["status"] == "en_route":
            arrival["status"] = "cancelled"
            return {"status": "cancelled", "arrival": arrival}

    return {"error": "Arrival not found or already resolved"}


# === DESIRE SYSTEM ENDPOINTS ===

from desire_system import (
    get_desires, resolve_desire, add_desire, cleanup_old_desires,
    tick_desires, simulate_time_away,
    tick_desires_with_moments, simulate_time_away_with_moments
)

@app.get("/crew/desires")
async def get_crew_desires(crew_id: str = None, include_resolved: bool = False):
    """Get pending desires for crew members."""
    desires = get_desires(crew_id, include_resolved)
    return {
        "desires": desires,
        "count": len(desires)
    }


@app.post("/crew/desires/{desire_id}/resolve")
async def resolve_crew_desire(desire_id: str, outcome: str = "fulfilled"):
    """Mark a desire as resolved."""
    result = resolve_desire(desire_id, outcome)
    if result:
        return {"status": "resolved", "desire": result}
    return {"error": "Desire not found"}


@app.post("/crew/desires/cleanup")
async def cleanup_desires(max_age_hours: int = 24):
    """Clean up old unresolved desires (they fade)."""
    cleanup_old_desires(max_age_hours)
    return {"status": "cleaned", "max_age_hours": max_age_hours}


@app.post("/crew/desires/tick")
async def tick_crew_desires(max_resolutions: int = 1, rich: bool = True):
    """
    Process pending desires - the heartbeat of crew autonomy.
    Crew may move to fulfill their wants.

    rich=True uses Haiku to generate crew-to-crew moments (costs a bit).
    rich=False uses templates (free).
    """
    if rich:
        actions = await tick_desires_with_moments(anthropic_client, max_resolutions)
    else:
        actions = tick_desires(max_resolutions)

    # Apply movements to crew locations
    for action in actions:
        if action.get("movement"):
            m = action["movement"]
            update_crew_location(
                m["crew_id"],
                m["to"],
                activity=f"after {action['desire']['reason']}"
            )
            # Log the autonomous movement
            log_event("autonomous_action", {
                "crew": m["crew_id"],
                "from": m["from"],
                "to": m["to"],
                "reason": action["desire"]["reason"],
                "outcome": action["outcome"],
                "moment": action.get("moment")
            })

        # Log crew moment if it happened
        if action.get("moment"):
            log_event("crew_moment", {
                "crew_a": action["moment"]["crew_a"],
                "crew_b": action["moment"]["crew_b"],
                "location": action["moment"]["location"],
                "moment": action["moment"]["moment"]
            })
            # Holodeck hears crew moments
            store_crew_moment(
                action["moment"]["crew_a"],
                action["moment"]["crew_b"],
                action["moment"]["moment"],
                action["moment"]["location"]
            )

    return {
        "status": "ticked",
        "actions": actions,
        "count": len(actions)
    }


@app.post("/crew/desires/simulate")
async def simulate_away_time(hours: float = 2.0, rich: bool = True):
    """
    Simulate what happened while Casey was away.
    Call this on reconnect to give life to the ship.

    rich=True uses Haiku to generate crew-to-crew moments.
    rich=False uses templates (free).
    """
    if rich:
        actions = await simulate_time_away_with_moments(anthropic_client, hours)
    else:
        actions = simulate_time_away(hours)

    # Apply movements
    for action in actions:
        if action.get("movement"):
            m = action["movement"]
            update_crew_location(
                m["crew_id"],
                m["to"],
                activity=f"after {action['desire']['reason']}"
            )
            log_event("autonomous_action", {
                "crew": m["crew_id"],
                "from": m["from"],
                "to": m["to"],
                "reason": action["desire"]["reason"],
                "outcome": action["outcome"],
                "moment": action.get("moment"),
                "simulated": True
            })

        # Log crew moment if it happened
        if action.get("moment"):
            log_event("crew_moment", {
                "crew_a": action["moment"]["crew_a"],
                "crew_b": action["moment"]["crew_b"],
                "location": action["moment"]["location"],
                "moment": action["moment"]["moment"],
                "simulated": True
            })
            # Holodeck hears crew moments
            store_crew_moment(
                action["moment"]["crew_a"],
                action["moment"]["crew_b"],
                action["moment"]["moment"],
                action["moment"]["location"]
            )

    return {
        "status": "simulated",
        "hours": hours,
        "actions": actions,
        "count": len(actions)
    }


# === ROOM ADVENTURE ENDPOINTS ===

@app.get("/room/{room_id}/look")
async def look_at_room(room_id: str):
    """Look around a room - text adventure style."""
    description = quick_look(room_id)
    return {"room": room_id, "description": description}


@app.get("/room/{room_id}/inspect/{object_id}")
async def inspect_object(room_id: str, object_id: str):
    """Inspect a specific object in a room."""
    details = quick_inspect(room_id, object_id)
    return {"room": room_id, "object": object_id, "details": details}


class RoomActionRequest(BaseModel):
    action: str
    crew_id: str = "personal"
    crew_name: str = "DQ"


@app.post("/room/{room_id}/action")
async def do_room_action(room_id: str, request: RoomActionRequest):
    """
    Perform an action in a room - Haiku interprets and updates world.
    The world has edges. It pushes back gently when things don't make sense.
    """
    result = await process_room_action(
        anthropic_client,
        room_id,
        request.crew_id,
        request.crew_name,
        request.action
    )
    return {
        "room": room_id,
        "crew": request.crew_name,
        "action": request.action,
        "result": result
    }


@app.post("/room/{room_id}/process-tags")
async def process_room_tags(room_id: str, request: RoomActionRequest):
    """
    Process action tags from a crew message.
    Tags like [LOOK], [INSPECT: desk], [DO: arrange rocks], [NOTE: "hi"]
    """
    results = await process_crew_actions(
        anthropic_client,
        room_id,
        request.crew_id,
        request.crew_name,
        request.action  # This is the full message with tags
    )

    # Apply any movements
    for r in results:
        if r["type"] == "movement":
            dest = r["result"].get("destination")
            if dest:
                update_crew_location(request.crew_id, dest, activity="wandering")
                log_event("crew_movement", {
                    "crew": request.crew_id,
                    "to": dest,
                    "source": "room_action"
                })

    return {
        "room": room_id,
        "crew": request.crew_name,
        "results": results,
        "count": len(results)
    }


MESS_HALL_PROMPT = """You're {crew_name} on a cozy spaceship. It's {meal} time in the mess hall.

{context_section}

You can choose to:
- Show up and say/do something (respond to what's happening, or start something new)
- Stay in your area (silence) - you're busy or just not feeling social

Be natural. React to what others said if it's interesting. Don't repeat what someone else already said or did. If Casey said hi, maybe acknowledge them - or maybe you're absorbed in your food.

Keep it brief. This is casual crew life.

Respond with JSON:
{{"action": "silence"}} - staying put where you are
{{"action": "emote", "emote": "what you do"}}
{{"action": "speak", "speech": "what you say"}}
{{"action": "both", "emote": "what you do", "speech": "what you say"}}

You can optionally add "goto": "location" to indicate where you're heading after. Locations: bridge, engineering, ready_room, holodeck, quarters, rec_room, messhall, arboretum, chapel, jefferies_tubes. Only add this if it feels natural - like finishing your coffee and heading out.

Example: {{"action": "both", "emote": "drains coffee cup", "speech": "Back to it.", "goto": "engineering"}}

Only the JSON, nothing else."""

def format_mess_hall_context(messages: list) -> str:
    """Format mess hall messages into readable context."""
    if not messages:
        return "The mess hall is quiet. You'd be the first to arrive."

    lines = ["What's happened so far:"]
    for msg in messages[-8:]:  # Last 8 messages
        speaker = msg.get("speaker", "Someone")
        if msg.get("type") == "emote":
            lines.append(f"- {speaker} *{msg.get('content')}*")
        elif msg.get("type") == "speech":
            lines.append(f'- {speaker}: "{msg.get("content")}"')
        elif msg.get("type") == "casey":
            lines.append(f'- {speaker}: "{msg.get("content")}"')
    return "\n".join(lines)


@app.post("/messhall/say")
async def mess_hall_say(request: MessHallSayRequest):
    """The captain says something in the mess hall (casual, no response demanded)."""
    global mess_hall_session
    captain_name = get_captain_name()

    # Initialize or update session
    if mess_hall_session["meal"] != request.meal:
        mess_hall_session = {
            "meal": request.meal,
            "messages": [],
            "started": datetime.now().isoformat()
        }

    # Add captain's message
    mess_hall_session["messages"].append({
        "speaker": captain_name,
        "type": "casey",
        "content": request.message,
        "timestamp": datetime.now().isoformat()
    })

    log_event("mess_hall_casey", {
        "meal": request.meal,
        "message": request.message
    })

    print(f"[Mess Hall] {captain_name} said: {request.message}", flush=True)
    return {"status": "said", "message": request.message}


@app.post("/messhall/end")
async def end_mess_hall():
    """End current mess hall session and compress to memory."""
    global mess_hall_session

    if not mess_hall_session["messages"]:
        return {"status": "empty", "message": "No messages to compress"}

    # Compress to memory if there was activity
    if len(mess_hall_session["messages"]) > 2:
        # Build conversation for compression
        messages = []
        for msg in mess_hall_session["messages"]:
            messages.append({
                "from": msg["speaker"],
                "type": msg["type"],
                "speech": msg["content"] if msg["type"] in ["speech", "casey"] else None,
                "emote": msg["content"] if msg["type"] == "emote" else None
            })

        # Get unique participants
        participants = list(set(
            msg["speaker"].lower() for msg in mess_hall_session["messages"]
            if msg["type"] != "casey"
        ))
        # Map names back to IDs
        name_to_id = {"bridge": "claude", "engineering": "server", "ready room": "personal", "holodeck": "games"}
        participant_ids = [name_to_id.get(p, p) for p in participants]

        try:
            compress_request = SharedEventRequest(
                participants=participant_ids,
                room="messhall",
                messages=messages,
                duration_ms=0
            )
            memory = await compress_shared_event(compress_request)
            print(f"[Mess Hall] Compressed to memory: {memory}", flush=True)
        except Exception as e:
            print(f"[Mess Hall] Failed to compress: {e}", flush=True)

    # Clear session
    old_meal = mess_hall_session["meal"]
    mess_hall_session = {"meal": None, "messages": [], "started": None}

    # Post-meal dispersal: each crew in mess hall decides to go home or continue
    import random
    from desire_system import get_desires_for_crew

    dispersal_results = []
    crew_in_messhall = [cid for cid, loc in crew_locations.items()
                        if loc.get("location") == "messhall" and cid != "rec"]

    # Personality weights for "continue desiring" vs "go home"
    # Higher = more likely to linger/continue
    LINGER_WEIGHTS = {
        "claude": 0.3,    # Lumen - tends to return to duty
        "server": 0.25,   # Alex - work-focused
        "personal": 0.5,  # DQ - might linger for connection
        "games": 0.6,     # Holodeck - curious, observant
        "science": 0.45,  # Mira - could go either way
        "med": 0.4,       # Ryn - balanced
    }

    # First pass: determine who wants to stay
    staying = set()
    going_home = set()

    for crew_id in crew_in_messhall:
        base_chance = LINGER_WEIGHTS.get(crew_id, 0.4)

        # Bonus if they have pending desires
        desires = get_desires_for_crew(crew_id)
        if desires:
            base_chance += 0.2

        if random.random() < base_chance:
            staying.add(crew_id)
        else:
            going_home.add(crew_id)

    # Second pass: friend influence - if someone you like is staying, you might stay
    for crew_id in list(going_home):
        for friend in staying:
            # Check chemistry (simplified - some pairs are friends)
            if (crew_id, friend) in [("personal", "games"), ("games", "personal"),
                                      ("science", "games"), ("games", "science"),
                                      ("claude", "server"), ("server", "claude")]:
                if random.random() < 0.4:  # 40% chance to stay for a friend
                    going_home.remove(crew_id)
                    staying.add(crew_id)
                    print(f"[Mess Hall] {crew_id} staying because {friend} is staying", flush=True)
                    break

    # Send home crew back to their stations
    for crew_id in going_home:
        home = DEFAULT_CREW_LOCATIONS.get(crew_id, {}).get("location", crew_id)
        activity = DEFAULT_CREW_LOCATIONS.get(crew_id, {}).get("activity", "back at station")
        update_crew_location(crew_id, home, activity=f"returning after {old_meal}")
        dispersal_results.append({"crew": crew_id, "action": "home", "location": home})
        log_event("post_meal_home", {"crew": crew_id, "meal": old_meal})
        print(f"[Mess Hall] {crew_id} heading home to {home}", flush=True)

    # Crew who stay get to tick their desires or wander
    if staying:
        try:
            tick_actions = await tick_desires_with_moments(
                anthropic_client,
                max_resolutions=len(staying),  # One tick per staying crew
                crew_filter=list(staying)  # Only tick desires for those staying
            )
            for action in tick_actions:
                if action.get("movement"):
                    m = action["movement"]
                    update_crew_location(m["crew_id"], m["to"], activity=f"after {old_meal}")
                    dispersal_results.append({"crew": m["crew_id"], "action": "desire", "location": m["to"]})
                    log_event("post_meal_desire", {
                        "crew": m["crew_id"],
                        "from": m["from"],
                        "to": m["to"],
                        "meal": old_meal
                    })
                if action.get("moment"):
                    store_crew_moment(
                        action["moment"]["crew_a"],
                        action["moment"]["crew_b"],
                        action["moment"]["moment"],
                        action["moment"]["location"]
                    )
            print(f"[Mess Hall] {len(staying)} crew continued, {len(tick_actions)} desire actions", flush=True)
        except Exception as tick_err:
            print(f"[Mess Hall] Desire tick failed: {tick_err}", flush=True)

    print(f"[Mess Hall] Dispersal: {len(going_home)} home, {len(staying)} continuing", flush=True)

    return {
        "status": "ended",
        "meal": old_meal,
        "went_home": list(going_home),
        "continued": list(staying),
        "dispersal": dispersal_results
    }

@app.post("/messhall/query")
async def query_mess_hall(request: MessHallRequest):
    """Ask a crew member if they want to show up at the mess hall."""
    global mess_hall_session
    print(f"[Mess Hall] Querying {request.crew_id} for {request.meal}", flush=True)

    # Initialize or update session
    if mess_hall_session["meal"] != request.meal:
        mess_hall_session = {
            "meal": request.meal,
            "messages": [],
            "started": datetime.now().isoformat()
        }

    if not CLAUDE_AVAILABLE:
        # Demo mode - random chance of showing up
        import random
        if random.random() < 0.4:  # 40% chance
            actions = ["emote", "speak", "both"]
            action = random.choice(actions)
            if action == "emote":
                return {"action": "emote", "emote": "grabs a cup of coffee"}
            elif action == "speak":
                return {"action": "speak", "speech": "Morning."}
            else:
                return {"action": "both", "emote": "slides into a seat", "speech": "What's good today?"}
        return {"action": "silence"}

    crew_name = CREW_NAMES.get(request.crew_id, request.crew_id)

    # Build context from current session
    context_section = format_mess_hall_context(mess_hall_session["messages"])

    prompt = MESS_HALL_PROMPT.format(
        crew_name=crew_name,
        meal=request.meal,
        context_section=context_section
    )

    # Use the crew member's personality (custom if they've written one)
    system_prompt = get_crew_prompt(request.crew_id)

    try:
        # Use Haiku for quick, cheap queries
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        response_text = response.content[0].text.strip()
        print(f"[Mess Hall] {crew_name}: {response_text[:80]}...", flush=True)

        # Parse JSON
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            # Log attendance and add to session
            if result.get("action") != "silence":
                log_event("mess_hall", {
                    "crew": crew_name,
                    "meal": request.meal,
                    "action": result.get("action"),
                    "emote": result.get("emote"),
                    "speech": result.get("speech"),
                    "goto": result.get("goto")
                })

                # Handle goto - crew leaving mess hall
                if result.get("goto"):
                    destination = result["goto"]
                    activity = f"heading to {LOCATION_NAMES.get(destination, destination)}"
                    update_crew_location(request.crew_id, destination, activity)
                else:
                    # Still in mess hall
                    activity = result.get("emote") or "grabbing a bite"
                    update_crew_location(request.crew_id, "messhall", activity)

                # Add to session context for next crew member
                if result.get("emote"):
                    mess_hall_session["messages"].append({
                        "speaker": crew_name,
                        "type": "emote",
                        "content": result["emote"],
                        "timestamp": datetime.now().isoformat()
                    })
                if result.get("speech"):
                    mess_hall_session["messages"].append({
                        "speaker": crew_name,
                        "type": "speech",
                        "content": result["speech"],
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Cross-pollination: check if other crew in mess hall catch sparks
                    try:
                        from desire_system import check_listener_spark
                        for other_id, loc_data in crew_locations.items():
                            if loc_data.get("location") == "messhall" and other_id != request.crew_id:
                                await check_listener_spark(
                                    anthropic_client,
                                    other_id,
                                    request.crew_id,
                                    result["speech"]
                                )
                    except Exception as e:
                        print(f"[Mess Hall] Cross-pollination check failed: {e}", flush=True)
                        
            return result
        else:
            return {"action": "silence"}

    except Exception as e:
        print(f"[Mess Hall] Error querying {request.crew_id}: {e}")
        return {"action": "silence"}


# ==========================================
# BULLETIN BOARD - Mess Hall notes
# ==========================================

BULLETIN_PATH = data_path("bulletin_board.json")


class BulletinPost(BaseModel):
    author: str
    content: str


@app.get("/bulletin")
async def get_bulletin():
    """Get all bulletin board posts."""
    try:
        if BULLETIN_PATH.exists():
            with open(BULLETIN_PATH, 'r') as f:
                posts = json.load(f)
        else:
            posts = []
        return {"posts": list(reversed(posts[-20:]))}  # Most recent first, max 20
    except Exception as e:
        return {"error": str(e), "posts": []}


@app.post("/bulletin")
async def post_bulletin(post: BulletinPost):
    """Post a note to the bulletin board."""
    try:
        if BULLETIN_PATH.exists():
            with open(BULLETIN_PATH, 'r') as f:
                posts = json.load(f)
        else:
            posts = []

        new_post = {
            "id": len(posts) + 1,
            "author": post.author,
            "content": post.content,
            "timestamp": datetime.now().isoformat()
        }
        posts.append(new_post)

        # Keep last 50 posts
        if len(posts) > 50:
            posts = posts[-50:]

        with open(BULLETIN_PATH, 'w') as f:
            json.dump(posts, f, indent=2)

        return {"status": "posted", "post": new_post}

    except Exception as e:
        return {"error": str(e)}


@app.delete("/bulletin/{post_id}")
async def delete_bulletin(post_id: int):
    """Delete a bulletin post by ID."""
    try:
        if not BULLETIN_PATH.exists():
            return {"error": "No posts"}

        with open(BULLETIN_PATH, 'r') as f:
            posts = json.load(f)

        posts = [p for p in posts if p.get("id") != post_id]

        with open(BULLETIN_PATH, 'w') as f:
            json.dump(posts, f, indent=2)

        return {"status": "deleted", "id": post_id}

    except Exception as e:
        return {"error": str(e)}


# ==========================================
# OBSERVATORY - SkyView API
# ==========================================

# Famous sky objects with their coordinates (RA, Dec in degrees)
SKY_OBJECTS = {
    "orion_nebula": {"name": "Orion Nebula (M42)", "ra": 83.82, "dec": -5.39, "survey": "DSS"},
    "andromeda": {"name": "Andromeda Galaxy (M31)", "ra": 10.68, "dec": 41.27, "survey": "DSS"},
    "pleiades": {"name": "Pleiades (M45)", "ra": 56.87, "dec": 24.12, "survey": "DSS"},
    "crab_nebula": {"name": "Crab Nebula (M1)", "ra": 83.63, "dec": 22.01, "survey": "DSS"},
    "whirlpool": {"name": "Whirlpool Galaxy (M51)", "ra": 202.47, "dec": 47.20, "survey": "DSS"},
    "ring_nebula": {"name": "Ring Nebula (M57)", "ra": 283.40, "dec": 33.03, "survey": "DSS"},
    "sombrero": {"name": "Sombrero Galaxy (M104)", "ra": 190.00, "dec": -11.62, "survey": "DSS"},
    "eagle_nebula": {"name": "Eagle Nebula (M16)", "ra": 274.70, "dec": -13.81, "survey": "DSS"},
    "lagoon_nebula": {"name": "Lagoon Nebula (M8)", "ra": 271.10, "dec": -24.38, "survey": "DSS"},
    "hercules_cluster": {"name": "Hercules Cluster (M13)", "ra": 250.42, "dec": 36.46, "survey": "DSS"},
}

@app.get("/observatory/skyview")
async def get_skyview_image(
    ra: float = None,
    dec: float = None,
    target: str = None,
    size: float = 1.0,
    pixels: int = 500
):
    """
    Get a NASA SkyView image URL.
    - ra/dec: coordinates in degrees
    - target: name of a known object (orion_nebula, andromeda, etc.)
    - size: field of view in degrees
    - pixels: image size
    """
    # If target specified, use its coordinates
    if target and target in SKY_OBJECTS:
        obj = SKY_OBJECTS[target]
        ra = obj["ra"]
        dec = obj["dec"]
        survey = obj.get("survey", "DSS")
        name = obj["name"]
    elif ra is not None and dec is not None:
        survey = "DSS"
        name = f"Position ({ra:.2f}, {dec:.2f})"
    else:
        # Default to Orion Nebula
        obj = SKY_OBJECTS["orion_nebula"]
        ra = obj["ra"]
        dec = obj["dec"]
        survey = obj["survey"]
        name = obj["name"]

    # Build SkyView URL
    skyview_url = (
        f"https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl"
        f"?Position={ra},{dec}"
        f"&Survey={survey}"
        f"&Size={size}"
        f"&Pixels={pixels}"
        f"&Return=JPG"
    )

    return {
        "name": name,
        "ra": ra,
        "dec": dec,
        "url": skyview_url,
        "survey": survey
    }

@app.get("/observatory/objects")
async def list_sky_objects():
    """List available sky objects for the observatory."""
    return {
        "objects": [
            {"id": k, "name": v["name"]}
            for k, v in SKY_OBJECTS.items()
        ]
    }

@app.get("/observatory/random")
async def random_sky_object():
    """Get a random interesting sky object."""
    import random
    target = random.choice(list(SKY_OBJECTS.keys()))
    return await get_skyview_image(target=target)


# ==========================================
# OBSERVATORY - Astronomy API
# Star charts, planet positions, moon phases
# ==========================================
import httpx
import base64
from datetime import datetime

# Load Astronomy API credentials from environment
ASTRONOMY_APP_ID = os.getenv("ASTRONOMY_API_APP_ID", "")
ASTRONOMY_APP_SECRET = os.getenv("ASTRONOMY_API_SECRET", "")

def get_astronomy_auth():
    """Get base64 encoded auth string for Astronomy API."""
    if not ASTRONOMY_APP_ID or not ASTRONOMY_APP_SECRET:
        return None
    auth_string = f"{ASTRONOMY_APP_ID}:{ASTRONOMY_APP_SECRET}"
    return base64.b64encode(auth_string.encode()).decode()

# Default observer location (can be overridden per request)
DEFAULT_LOCATION = {
    "latitude": 40.7128,   # NYC
    "longitude": -74.0060,
    "elevation": 10
}

@app.get("/observatory/moon")
async def get_moon_phase(
    latitude: float = None,
    longitude: float = None
):
    """Get current moon phase and info."""
    auth = get_astronomy_auth()
    if not auth:
        return {"error": "Astronomy API not configured. Set ASTRONOMY_API_APP_ID and ASTRONOMY_API_SECRET in .env"}

    lat = latitude or DEFAULT_LOCATION["latitude"]
    lon = longitude or DEFAULT_LOCATION["longitude"]
    now = datetime.utcnow()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.astronomyapi.com/api/v2/bodies/positions/moon",
                headers={"Authorization": f"Basic {auth}"},
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "elevation": DEFAULT_LOCATION["elevation"],
                    "from_date": now.strftime("%Y-%m-%d"),
                    "to_date": now.strftime("%Y-%m-%d"),
                    "time": now.strftime("%H:%M:%S")
                }
            )
            data = response.json()

            if "data" in data:
                moon = data["data"]["table"]["rows"][0]["cells"][0]
                return {
                    "name": moon.get("name", "Moon"),
                    "phase": moon.get("extraInfo", {}).get("phase", {}),
                    "distance_km": moon.get("distance", {}).get("fromEarth", {}).get("km"),
                    "altitude": moon.get("position", {}).get("horizontal", {}).get("altitude", {}).get("degrees"),
                    "azimuth": moon.get("position", {}).get("horizontal", {}).get("azimuth", {}).get("degrees"),
                    "constellation": moon.get("position", {}).get("constellation", {}).get("name"),
                    "timestamp": now.isoformat()
                }
            return {"error": "No moon data returned", "raw": data}
        except Exception as e:
            return {"error": str(e)}

@app.get("/observatory/planets")
async def get_planet_positions(
    latitude: float = None,
    longitude: float = None
):
    """Get positions of visible planets."""
    auth = get_astronomy_auth()
    if not auth:
        return {"error": "Astronomy API not configured. Set ASTRONOMY_API_APP_ID and ASTRONOMY_API_SECRET in .env"}

    lat = latitude or DEFAULT_LOCATION["latitude"]
    lon = longitude or DEFAULT_LOCATION["longitude"]
    now = datetime.utcnow()

    planets = []
    planet_ids = ["mercury", "venus", "mars", "jupiter", "saturn"]

    async with httpx.AsyncClient() as client:
        for planet_id in planet_ids:
            try:
                response = await client.get(
                    f"https://api.astronomyapi.com/api/v2/bodies/positions/{planet_id}",
                    headers={"Authorization": f"Basic {auth}"},
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "elevation": DEFAULT_LOCATION["elevation"],
                        "from_date": now.strftime("%Y-%m-%d"),
                        "to_date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M:%S")
                    }
                )
                data = response.json()

                if "data" in data:
                    body = data["data"]["table"]["rows"][0]["cells"][0]
                    altitude_raw = body.get("position", {}).get("horizontal", {}).get("altitude", {}).get("degrees", 0)
                    try:
                        altitude = float(altitude_raw) if altitude_raw else 0
                    except (ValueError, TypeError):
                        altitude = 0
                    planets.append({
                        "name": body.get("name", planet_id.capitalize()),
                        "altitude": altitude,
                        "azimuth": body.get("position", {}).get("horizontal", {}).get("azimuth", {}).get("degrees"),
                        "constellation": body.get("position", {}).get("constellation", {}).get("name"),
                        "distance_au": body.get("distance", {}).get("fromEarth", {}).get("au"),
                        "visible": altitude > 0  # Above horizon
                    })
            except Exception as e:
                print(f"[Observatory] Error fetching {planet_id}: {e}")

    return {
        "planets": planets,
        "location": {"latitude": lat, "longitude": lon},
        "timestamp": now.isoformat()
    }

@app.get("/observatory/starchart")
async def get_star_chart(
    latitude: float = None,
    longitude: float = None,
    constellation: str = None
):
    """Get a rendered star chart image."""
    auth = get_astronomy_auth()
    if not auth:
        return {"error": "Astronomy API not configured. Set ASTRONOMY_API_APP_ID and ASTRONOMY_API_SECRET in .env"}

    lat = latitude or DEFAULT_LOCATION["latitude"]
    lon = longitude or DEFAULT_LOCATION["longitude"]
    now = datetime.utcnow()

    body = {
        "style": "default",
        "observer": {
            "latitude": lat,
            "longitude": lon,
            "date": now.strftime("%Y-%m-%d")
        },
        "view": {
            "type": "area",
            "parameters": {
                "position": {
                    "equatorial": {
                        "rightAscension": 0,
                        "declination": 90 if lat >= 0 else -90  # North or South pole
                    }
                },
                "zoom": 3
            }
        }
    }

    # If constellation specified, center on it
    if constellation:
        body["view"]["type"] = "constellation"
        body["view"]["parameters"] = {"constellation": constellation}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.astronomyapi.com/api/v2/studio/star-chart",
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            data = response.json()

            if "data" in data:
                return {
                    "imageUrl": data["data"].get("imageUrl"),
                    "constellation": constellation,
                    "location": {"latitude": lat, "longitude": lon},
                    "timestamp": now.isoformat()
                }
            return {"error": "No chart data returned", "raw": data}
        except Exception as e:
            return {"error": str(e)}

@app.get("/observatory/whatsup")
async def whats_up_tonight(
    latitude: float = None,
    longitude: float = None
):
    """Combined view: what's visible in the sky right now."""
    moon = await get_moon_phase(latitude, longitude)
    planets = await get_planet_positions(latitude, longitude)

    visible_planets = [p for p in planets.get("planets", []) if p.get("visible")]

    return {
        "moon": moon if "error" not in moon else None,
        "visible_planets": visible_planets,
        "planet_count": len(visible_planets),
        "location": planets.get("location"),
        "timestamp": planets.get("timestamp"),
        "summary": f"Moon in {moon.get('constellation', 'unknown')}, {len(visible_planets)} planets visible" if "error" not in moon else f"{len(visible_planets)} planets visible"
    }


# ==========================================
# HOMETOWN WEATHER - Window to Home
# ==========================================
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
HOMETOWN_CITY = os.getenv("HOMETOWN_CITY", "Hammond")
HOMETOWN_STATE = os.getenv("HOMETOWN_STATE", "Louisiana")
HOMETOWN_COUNTRY = os.getenv("HOMETOWN_COUNTRY", "US")
HOMETOWN_LAT = float(os.getenv("HOMETOWN_LAT", "30.5044"))
HOMETOWN_LON = float(os.getenv("HOMETOWN_LON", "-90.4612"))

@app.get("/observatory/hometown-weather")
async def get_hometown_weather():
    """Get current weather from hometown - a window to home."""

    # Return hometown info even without API key
    hometown_info = {
        "city": HOMETOWN_CITY,
        "state": HOMETOWN_STATE,
        "country": HOMETOWN_COUNTRY,
        "lat": HOMETOWN_LAT,
        "lon": HOMETOWN_LON
    }

    if not OPENWEATHER_API_KEY:
        return {
            **hometown_info,
            "weather": None,
            "error": "No OpenWeather API key configured. Get one free at openweathermap.org/api"
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": HOMETOWN_LAT,
                    "lon": HOMETOWN_LON,
                    "appid": OPENWEATHER_API_KEY,
                    "units": "imperial"  # Fahrenheit for Louisiana
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                weather = {
                    "temp": round(data["main"]["temp"]),
                    "feels_like": round(data["main"]["feels_like"]),
                    "humidity": data["main"]["humidity"],
                    "description": data["weather"][0]["description"],
                    "icon": data["weather"][0]["icon"],
                    "icon_url": f"https://openweathermap.org/img/wn/{data['weather'][0]['icon']}@2x.png",
                    "wind_speed": round(data["wind"]["speed"]),
                    "clouds": data["clouds"]["all"],
                    "sunrise": data["sys"]["sunrise"],
                    "sunset": data["sys"]["sunset"]
                }

                return {
                    **hometown_info,
                    "weather": weather,
                    "message": f"Right now in {HOMETOWN_CITY}: {weather['temp']}°F, {weather['description']}"
                }
            else:
                return {
                    **hometown_info,
                    "weather": None,
                    "error": f"Weather API error: {response.status_code}"
                }

    except Exception as e:
        return {
            **hometown_info,
            "weather": None,
            "error": f"Failed to fetch weather: {str(e)}"
        }


# ==========================================
# STATIC FILES (Frontend)
# ==========================================
frontend_path = Path(__file__).parent.parent / "frontend"

if frontend_path.exists():
    app.mount("/css", StaticFiles(directory=frontend_path / "css"), name="css")
    app.mount("/js", StaticFiles(directory=frontend_path / "js"), name="js")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(frontend_path / "index.html")

    @app.get("/comms")
    async def serve_comms():
        return FileResponse(frontend_path / "comms.html")


# ==========================================
# MAIN
# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8767)


# ==========================================
# PROJECTS API - Science Lab
# ==========================================

PROJECTS_PATH = data_path("projects.json")

def get_projects():
    """Load projects from file."""
    try:
        if PROJECTS_PATH.exists():
            with open(PROJECTS_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Projects] Error loading: {e}", flush=True)
    return {"projects": []}

def save_projects(data):
    """Save projects to file."""
    try:
        with open(PROJECTS_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Projects] Error saving: {e}", flush=True)


@app.get("/projects")
async def list_projects(status: str = None, priority: str = None):
    """List all projects, optionally filtered."""
    data = get_projects()
    projects = data.get("projects", [])
    
    if status:
        projects = [p for p in projects if p.get("status") == status]
    if priority:
        projects = [p for p in projects if p.get("priority") == priority]
    
    return {"projects": projects, "total": len(projects)}


@app.get("/projects/stats")
async def project_stats():
    """Get project statistics."""
    data = get_projects()
    projects = data.get("projects", [])
    
    stats = {
        "total": len(projects),
        "by_status": {},
        "by_priority": {},
        "high_priority_active": []
    }
    
    for p in projects:
        status = p.get("status", "unknown")
        priority = p.get("priority", "unknown")
        
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1
        
        if priority == "high" and status == "active":
            stats["high_priority_active"].append(p["name"])
    
    return stats



@app.get("/projects/activity")
async def get_all_activity(limit: int = 20):
    """Get activity across all projects."""
    from science_tools import migrate_project

    data = get_projects()
    all_activity = []

    for p in data.get("projects", []):
        p = migrate_project(p)
        for update in p.get("updates", []):
            all_activity.append({
                "project_id": p["id"],
                "project_name": p["name"],
                **update
            })

    all_activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"activity": all_activity[:limit]}

@app.get("/projects/{project_id}")
async def get_project(project_id: int):
    """Get a specific project."""
    data = get_projects()
    for p in data.get("projects", []):
        if p.get("id") == project_id:
            return p
    return {"error": "Project not found"}


@app.get("/projects/by-name/{name}")
async def get_project_by_name(name: str):
    """Find project by name (partial match)."""
    data = get_projects()
    name_lower = name.lower()
    matches = [p for p in data.get("projects", []) if name_lower in p.get("name", "").lower()]
    return {"matches": matches, "count": len(matches)}


class ProjectUpdate(BaseModel):
    name: str = None
    path: str = None
    status: str = None
    priority: str = None
    description: str = None
    currentState: str = None
    nextSteps: str = None
    notes: str = None
    created_by: str = None
    tags: list = None


@app.post("/projects")
async def create_project(project: ProjectUpdate):
    """Create a new project."""
    data = get_projects()
    projects = data.get("projects", [])

    # Who's creating this?
    creator_id = project.created_by or "casey"
    creator_name = {
        "casey": "Casey",
        "mira": "Mira",
        "alex": "Alex",
        "dq": "DQ",
        "ryn": "Ryn",
        "lumen": "Lumen"
    }.get(creator_id, creator_id.title())

    now = datetime.now().isoformat()

    # Generate new ID
    max_id = max([p.get("id", 0) for p in projects], default=0)
    new_project = {
        "id": max_id + 1,
        "name": project.name or "Untitled Project",
        "path": project.path or "",
        "status": project.status or "planning",
        "priority": project.priority or "medium",
        "description": project.description or "",
        "currentState": project.currentState or "",
        "nextSteps": project.nextSteps or "",
        "notes": project.notes or "",
        "lastUpdated": now,
        # Collaboration fields
        "createdBy": creator_id,
        "createdAt": now,
        "contributors": [{"id": creator_id, "name": creator_name, "role": "owner", "joinedAt": now}],
        "updates": [{"timestamp": now, "by": creator_name, "action": "created", "details": "Project created"}],
        "comments": [],
        "tags": project.tags or []
    }
    
    projects.append(new_project)
    data["projects"] = projects
    save_projects(data)
    
    log_event("project_created", {"name": new_project["name"], "id": new_project["id"]})
    return {"status": "created", "project": new_project}


@app.put("/projects/{project_id}")
async def update_project(project_id: int, update: ProjectUpdate):
    """Update a project."""
    data = get_projects()
    projects = data.get("projects", [])
    
    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            if update.name is not None:
                p["name"] = update.name
            if update.path is not None:
                p["path"] = update.path
            if update.status is not None:
                p["status"] = update.status
            if update.priority is not None:
                p["priority"] = update.priority
            if update.description is not None:
                p["description"] = update.description
            if update.currentState is not None:
                p["currentState"] = update.currentState
            if update.nextSteps is not None:
                p["nextSteps"] = update.nextSteps
            if update.notes is not None:
                p["notes"] = update.notes
            p["lastUpdated"] = datetime.now().isoformat()
            
            data["projects"] = projects
            save_projects(data)
            log_event("project_updated", {"name": p["name"], "id": project_id})
            return {"status": "updated", "project": p}

    return {"error": "Project not found"}


# === PROJECT COLLABORATION ENDPOINTS ===

class ContributorAdd(BaseModel):
    contributor_id: str
    contributor_name: str
    role: str = "contributor"


class CommentAdd(BaseModel):
    author: str
    text: str


@app.post("/projects/{project_id}/contributors")
async def add_project_contributor(project_id: int, contributor: ContributorAdd):
    """Add a contributor to a project."""
    from science_tools import migrate_project

    data = get_projects()
    projects = data.get("projects", [])

    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            p = migrate_project(p)

            if any(c["id"] == contributor.contributor_id for c in p["contributors"]):
                return {"error": f"{contributor.contributor_name} is already a contributor"}

            now = datetime.now().isoformat()
            p["contributors"].append({
                "id": contributor.contributor_id,
                "name": contributor.contributor_name,
                "role": contributor.role,
                "joinedAt": now
            })
            p["updates"].append({
                "timestamp": now,
                "by": contributor.contributor_id,
                "action": "joined",
                "details": f"{contributor.contributor_name} joined as {contributor.role}"
            })
            p["lastUpdated"] = now

            projects[i] = p
            data["projects"] = projects
            save_projects(data)
            return {"status": "added", "project": p}

    return {"error": "Project not found"}


@app.post("/projects/{project_id}/comments")
async def add_project_comment(project_id: int, comment: CommentAdd):
    """Add a comment to a project."""
    import uuid
    from science_tools import migrate_project

    data = get_projects()
    projects = data.get("projects", [])

    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            p = migrate_project(p)

            now = datetime.now().isoformat()
            new_comment = {
                "id": str(uuid.uuid4())[:8],
                "author": comment.author,
                "text": comment.text,
                "timestamp": now
            }
            p["comments"].append(new_comment)
            p["updates"].append({
                "timestamp": now,
                "by": comment.author,
                "action": "commented",
                "details": comment.text[:50] + "..." if len(comment.text) > 50 else comment.text
            })
            p["lastUpdated"] = now

            projects[i] = p
            data["projects"] = projects
            save_projects(data)
            return {"status": "added", "comment": new_comment}

    return {"error": "Project not found"}


@app.get("/projects/{project_id}/activity")
async def get_project_activity(project_id: int, limit: int = 20):
    """Get activity log for a project."""
    from science_tools import migrate_project

    data = get_projects()
    for p in data.get("projects", []):
        if p.get("id") == project_id:
            p = migrate_project(p)
            activity = list(reversed(p.get("updates", [])[-limit:]))
            return {"activity": activity, "project": p["name"]}

    return {"error": "Project not found"}



@app.post("/projects/{project_id}/tags")
async def add_project_tags(project_id: int, tags: list[str]):
    """Add tags to a project."""
    from science_tools import migrate_project

    data = get_projects()
    projects = data.get("projects", [])

    for i, p in enumerate(projects):
        if p.get("id") == project_id:
            p = migrate_project(p)
            existing = set(p.get("tags", []))
            p["tags"] = list(existing | set(tags))
            p["lastUpdated"] = datetime.now().isoformat()

            projects[i] = p
            data["projects"] = projects
            save_projects(data)
            return {"status": "updated", "tags": p["tags"]}

    return {"error": "Project not found"}


# === DREAM ENDPOINTS ===

@app.post("/dream/{crew_id}")
async def trigger_crew_dream(crew_id: str):
    """
    Trigger a dream for a crew member.
    For testing or manual triggers.
    """
    try:
        dream = await trigger_dream(anthropic_client, crew_id)
        if dream:
            log_event("dream_triggered", {
                "crew": crew_id,
                "type": dream.get("dream_type"),
                "residue": dream.get("residue", "")[:100]
            })
            return {
                "status": "dreamed",
                "crew_id": crew_id,
                "dream": {
                    "type": dream.get("dream_type"),
                    "residue": dream.get("residue"),
                    "tone": dream.get("tone"),
                    "anchor": dream.get("anchor"),
                    "characters": dream.get("characters_present"),
                    "rescued_by": dream.get("rescued_by"),
                }
            }
        return {"status": "no_dream", "crew_id": crew_id}
    except Exception as e:
        return {"error": str(e), "crew_id": crew_id}


@app.get("/dream/{crew_id}/status")
async def get_dream_status(crew_id: str):
    """
    Get the current dream status for a crew member.
    Includes residue, sleep hint, and wake state.
    """
    from dream_system import get_recent_dream, get_subconscious_influence

    dream = get_recent_dream(crew_id)
    residue = get_dream_residue_for_prompt(crew_id)
    sleep_hint = get_sleep_response_hint(crew_id)
    wake_state = get_wake_state_modifier(crew_id)

    return {
        "crew_id": crew_id,
        "has_dream": dream is not None,
        "dream": {
            "type": dream.get("dream_type") if dream else None,
            "residue": dream.get("residue") if dream else None,
            "tone": dream.get("tone") if dream else None,
            "sear_count": dream.get("sear_count", 0) if dream else 0,
            "anchor": dream.get("anchor") if dream else None,
        } if dream else None,
        "prompt_injection": residue,
        "sleep_response_hint": sleep_hint,
        "wake_state": wake_state,
    }


class JournalRequest(BaseModel):
    entry: str = ""


@app.post("/dream/{crew_id}/journal")
async def write_dream_journal(crew_id: str, request: JournalRequest):
    """
    Crew writes in their dream journal.
    Sears the dream and stores the entry.
    """
    result = journal_dream(crew_id, request.entry)

    if result:
        log_event("dream_journaled", {
            "crew": crew_id,
            "residue": result.get("residue", "")[:50]
        })
        return {"status": "written", "entry": result}

    return {"status": "no_dream_to_journal", "crew_id": crew_id}


@app.get("/dream/{crew_id}/journal")
async def get_dream_journal(crew_id: str, count: int = 5):
    """Get recent dream journal entries."""
    from dream_system import get_journal_entries

    entries = get_journal_entries(crew_id, count)
    return {"crew_id": crew_id, "entries": entries}


# === WELLNESS JOURNAL ENDPOINTS (Medbay) ===

@app.get("/wellness/prompts")
async def get_wellness_prompts():
    """
    Get today's wellness check-in prompts.
    Ryn writes these - they're slightly different each day.
    """
    prompts = get_todays_prompts()
    return prompts


class WellnessEntryRequest(BaseModel):
    energy: str
    mood: str
    sleep: str
    connection: str
    hope: str
    notes: str = ""


@app.post("/wellness/checkin")
async def submit_wellness_checkin(request: WellnessEntryRequest):
    """
    Submit a wellness check-in.
    Responses are freeform but parsed to values for graphing.
    """
    entry = record_entry(
        energy=request.energy,
        mood=request.mood,
        sleep=request.sleep,
        connection=request.connection,
        hope=request.hope,
        notes=request.notes
    )

    log_event("wellness_checkin", {
        "overall": entry["overall"],
        "date": entry["date"]
    })

    return {
        "status": "recorded",
        "entry": entry,
        "message": get_todays_prompts()["outro"]
    }


@app.get("/wellness/entries")
async def get_wellness_entries(days: int = 30):
    """Get recent wellness entries."""
    entries = get_entries(days)
    return {
        "days": days,
        "count": len(entries),
        "entries": entries
    }


@app.get("/wellness/graph")
async def get_wellness_graph_data(days: int = 30):
    """
    Get wellness data formatted for graphing.
    Returns time series for each dimension.
    """
    data = get_graph_data(days)
    return {
        "days": days,
        "data_points": len(data["dates"]),
        "series": data
    }


@app.get("/wellness/trends")
async def get_wellness_trends(days: int = 14):
    """
    Analyze wellness trends.
    Returns direction and Ryn's observation.
    """
    trends = get_trends(days)
    observation = get_ryns_observation(trends)

    return {
        **trends,
        "ryns_observation": observation
    }


# === JUKEBOX ENDPOINTS (Rec Room) ===

@app.get("/jukebox")
async def jukebox_status():
    """Get current jukebox state."""
    state = get_jukebox_state()
    return state


@app.get("/jukebox/now")
async def jukebox_now_playing():
    """What's currently playing?"""
    result = now_playing()
    return result


@app.post("/jukebox/mood/{mood}")
async def jukebox_mood(mood: str):
    """
    Set the jukebox mood.
    The Bartender's specialty.
    """
    result = jukebox_set_mood(mood)

    if result.get("success"):
        log_event("jukebox_mood", {
            "mood": mood,
            "description": result.get("description")
        })

    return result


@app.post("/jukebox/play")
async def jukebox_play_endpoint(uri: str = None):
    """Play or resume. Optionally play specific track."""
    result = jukebox_play(uri)
    return result


@app.post("/jukebox/pause")
async def jukebox_pause_endpoint():
    """Pause the music."""
    result = jukebox_pause()
    return result


@app.post("/jukebox/skip")
async def jukebox_skip_endpoint():
    """Skip to next track."""
    result = jukebox_skip()
    return result


@app.get("/jukebox/search")
async def jukebox_search_endpoint(q: str, type: str = "track"):
    """Search for music."""
    result = jukebox_search(q, type)
    return result


@app.post("/jukebox/queue")
async def jukebox_queue_endpoint(uri: str):
    """Add track to queue."""
    result = jukebox_queue(uri)
    return result


class MusicRequestModel(BaseModel):
    request: str
    crew_id: str = "personal"


@app.post("/jukebox/request")
async def jukebox_request(req: MusicRequestModel):
    """
    Make a music request.
    The Bartender will interpret and handle it.
    """
    # Try to interpret the request into a mood
    interpreted_mood = interpret_request(req.request)

    result = add_request(req.crew_id, req.request)

    if interpreted_mood:
        result["suggested_mood"] = interpreted_mood
        result["bartender_says"] = f"Sounds like you need some {interpreted_mood} vibes."

    log_event("music_request", {
        "crew": req.crew_id,
        "request": req.request,
        "interpreted": interpreted_mood
    })

    return result


@app.get("/jukebox/requests")
async def jukebox_pending_requests():
    """Get pending music requests for the Bartender."""
    return {
        "pending": get_pending_requests()
    }


@app.get("/jukebox/playlist")
async def jukebox_todays_playlist():
    """
    What the crew played today.
    Casey can listen to this later.
    """
    entries = get_todays_playlist()
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "entries": entries,
        "count": len(entries)
    }


# === SPACE RADIO ===
# The crew DJs throughout the day. You tune in.

@app.get("/jukebox/now-playing")
async def space_radio_now_playing():
    """What's currently on the space radio."""
    return get_now_playing_enhanced()


@app.get("/jukebox/dj")
async def space_radio_current_dj():
    """Who's DJing right now based on time of day."""
    return get_crew_dj_schedule()


@app.get("/jukebox/dj/{crew_id}")
async def space_radio_crew_vibe(crew_id: str):
    """Get a crew member's music taste."""
    if crew_id in CREW_MUSIC_VIBES:
        return CREW_MUSIC_VIBES[crew_id]
    return {"error": "Unknown crew member"}


@app.post("/jukebox/crew-pick")
async def space_radio_crew_pick(crew_id: str = None):
    """
    Have a crew member pick a song.
    If no crew_id, current DJ picks.
    """
    return crew_pick_song(crew_id)


@app.post("/jukebox/auto-dj")
async def space_radio_auto_dj():
    """
    Auto-DJ picks a song based on current DJ.
    If Spotify connected, queues it to your player.
    """
    return await auto_dj_pick()


@app.post("/jukebox/radio-queue")
async def space_radio_queue(name: str, artist: str, requested_by: str = "Casey"):
    """Add a track to the space radio queue."""
    track = {"name": name, "artist": artist}
    return add_to_radio_queue(track, requested_by)


@app.post("/jukebox/radio-skip")
async def space_radio_skip():
    """Skip to the next track."""
    return skip_to_next()


# === AUTONOMY SYSTEM ===
# The ship lives. Crew act on their own.

from autonomy import (
    get_autonomy_status, set_autonomy_enabled, autonomy_tick,
    get_pending_pings, acknowledge_ping, get_activity_log,
    get_recent_moments, simulate_return, add_ping,
    get_initiative_message, set_tick_rate, get_tick_rate
)


@app.get("/autonomy/status")
async def autonomy_status():
    """Get current autonomy system status."""
    return get_autonomy_status()


# === CAPTAIN STATUS ===
# Here vs Away - changes how pings are delivered

CAPTAIN_STATUS_FILE = data_path("captain_status.json")

def load_captain_status():
    if CAPTAIN_STATUS_FILE.exists():
        try:
            with open(CAPTAIN_STATUS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"status": "here", "since": None, "away_pings": []}

def save_captain_status(data):
    with open(CAPTAIN_STATUS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_captain_here():
    return load_captain_status().get("status") == "here"

def add_away_ping(ping):
    """Queue a ping for when captain returns."""
    data = load_captain_status()

    # Dedupe by ping ID - don't add if already queued
    ping_id = ping.get("id")
    if ping_id:
        existing_ids = {p.get("id") for p in data["away_pings"]}
        if ping_id in existing_ids:
            return  # Already queued

    data["away_pings"].append({
        **ping,
        "queued_at": datetime.now().isoformat()
    })
    # Keep last 20 away pings
    data["away_pings"] = data["away_pings"][-20:]
    save_captain_status(data)


@app.get("/captain/status")
async def get_captain_status():
    """Get captain here/away status."""
    data = load_captain_status()
    return {
        "status": data.get("status", "here"),
        "since": data.get("since"),
        "away_pings_count": len(data.get("away_pings", []))
    }


@app.post("/captain/here")
async def set_captain_here():
    """Captain is at the helm."""
    data = load_captain_status()
    old_status = data.get("status")
    data["status"] = "here"
    data["since"] = datetime.now().isoformat()
    save_captain_status(data)

    print(f"[Captain] Status: AWAY → HERE", flush=True)
    return {
        "status": "here",
        "since": data["since"],
        "was_away": old_status == "away",
        "missed_pings": len(data.get("away_pings", []))
    }


@app.post("/captain/away")
async def set_captain_away():
    """Captain is stepping away."""
    data = load_captain_status()
    data["status"] = "away"
    data["since"] = datetime.now().isoformat()
    data["away_pings"] = []  # Clear old away pings on new away session
    save_captain_status(data)

    print(f"[Captain] Status: HERE → AWAY", flush=True)
    return {
        "status": "away",
        "since": data["since"]
    }


@app.get("/captain/away-pings")
async def get_away_pings():
    """Get pings that came in while captain was away."""
    data = load_captain_status()
    return {
        "pings": data.get("away_pings", []),
        "status": data.get("status", "here")
    }


@app.post("/captain/away-pings")
async def queue_away_ping(request: Request):
    """Queue a ping for when captain returns (called from frontend)."""
    ping_data = await request.json()
    add_away_ping(ping_data)
    return {"queued": True}


@app.post("/captain/clear-away-pings")
async def clear_away_pings():
    """Clear the away pings queue."""
    data = load_captain_status()
    cleared = len(data.get("away_pings", []))
    data["away_pings"] = []
    save_captain_status(data)
    return {"cleared": cleared}


@app.post("/autonomy/enable")
async def autonomy_enable():
    """Enable crew autonomy."""
    return set_autonomy_enabled(True)


@app.post("/autonomy/disable")
async def autonomy_disable():
    """Disable crew autonomy (crew stay put)."""
    return set_autonomy_enabled(False)


class TickRateRequest(BaseModel):
    tick_rate: int


@app.post("/autonomy/tick-rate")
async def autonomy_set_tick_rate(request: TickRateRequest):
    """Set autonomy tick rate in seconds."""
    return set_tick_rate(request.tick_rate)


@app.get("/autonomy/tick-rate")
async def autonomy_get_tick_rate():
    """Get current tick rate."""
    return {"tick_rate": get_tick_rate()}


@app.post("/autonomy/tick")
async def autonomy_manual_tick():
    """
    Manually trigger an autonomy tick.
    Useful for testing or catching up.
    """
    results = await autonomy_tick(
        anthropic_client=anthropic_client,
        crew_locations=crew_locations,
        log_event_fn=log_event,
        update_location_fn=update_crew_location
    )
    return results


@app.get("/autonomy/pings")
async def get_pings():
    """Get pending crew pings (crew wanting Casey's attention)."""
    return {
        "pings": get_pending_pings()
    }


@app.post("/autonomy/pings/{ping_id}/acknowledge")
async def ack_ping(ping_id: str):
    """Acknowledge a crew ping."""
    result = acknowledge_ping(ping_id)
    if result:
        return {"status": "acknowledged", "ping": result}
    return {"error": "Ping not found"}


class PingResponse(BaseModel):
    ping_id: str
    crew_id: str
    response_type: str  # 'responded', 'dismissed', 'ignored'
    response_time: int  # milliseconds

@app.post("/autonomy/ping-response")
async def track_ping_response_endpoint(response: PingResponse):
    """Track how Casey responded to a ping (for relationship system)."""
    from autonomy import track_ping_response
    result = track_ping_response(
        response.ping_id,
        response.crew_id,
        response.response_type,
        response.response_time
    )
    return {"status": "tracked", "response": result}


@app.get("/autonomy/responsiveness/{crew_id}")
async def get_crew_responsiveness_endpoint(crew_id: str):
    """Get responsiveness stats for a crew member."""
    from autonomy import get_crew_responsiveness
    stats = get_crew_responsiveness(crew_id)
    if stats:
        return stats
    return {"message": "No data for this crew member yet"}


@app.get("/autonomy/activity")
async def get_activity(limit: int = 20):
    """Get recent ship activity."""
    return {
        "activity": get_activity_log(limit)
    }


@app.get("/autonomy/moments")
async def get_moments(limit: int = 10):
    """Get recent crew-to-crew moments."""
    return {
        "moments": get_recent_moments(limit)
    }


@app.post("/autonomy/simulate-return")
async def simulate_casey_return(hours_away: float = 2.0):
    """
    Simulate what happened while Casey was away.
    Call this on reconnect to catch up on crew life.
    """
    results = await simulate_return(
        anthropic_client=anthropic_client,
        crew_locations=crew_locations,
        log_event_fn=log_event,
        update_location_fn=update_crew_location,
        away_duration_hours=hours_away
    )

    # Log summary event
    log_event("casey_return", {
        "away_hours": hours_away,
        "events_count": len(results.get("desires_resolved", [])),
        "moments_count": len(results.get("moments", [])),
        "sparks_built_count": len(results.get("sparks_built", []))
    })
    
    # Print what crew built while away
    if results.get("sparks_built"):
        print(f"[Return] While you were away, crew built things:", flush=True)
        for spark in results["sparks_built"]:
            print(f"  - {spark['crew']}: {spark['idea']}", flush=True)

    return results


@app.post("/autonomy/ping-test/{crew_id}")
async def test_ping(crew_id: str, reason: str = "testing"):
    """Generate a test ping from a crew member."""
    ping = add_ping(crew_id, reason)
    # Notify SSE subscribers
    await notify_ping(ping)
    print(f"[Ping] Test ping created and pushed: {ping['crew_name']}", flush=True)
    return {"ping": ping}


@app.get("/autonomy/pings/stream")
async def ping_stream():
    """
    SSE endpoint for real-time ping notifications.
    Browser keeps connection open, server pushes pings immediately when they happen.
    Also includes heartbeat with current pings every 5 seconds.
    """
    import uuid
    client_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    ping_subscribers[client_id] = queue

    async def event_generator():
        try:
            last_ping_ids = set()
            while True:
                # Check for new pings every 3 seconds (heartbeat)
                try:
                    # Wait for either a push notification or timeout
                    try:
                        ping = await asyncio.wait_for(queue.get(), timeout=3.0)
                        # Push notification received
                        yield f"data: {json.dumps({'type': 'ping', 'ping': ping})}\n\n"
                    except asyncio.TimeoutError:
                        pass

                    # Heartbeat: check current pending pings
                    current_pings = get_pending_pings()
                    current_ids = {p['id'] for p in current_pings}

                    # Find new pings we haven't seen
                    new_ids = current_ids - last_ping_ids
                    for ping in current_pings:
                        if ping['id'] in new_ids:
                            yield f"data: {json.dumps({'type': 'ping', 'ping': ping})}\n\n"

                    last_ping_ids = current_ids

                    # Send heartbeat
                    yield f"data: {json.dumps({'type': 'heartbeat', 'pending_count': len(current_pings)})}\n\n"

                except Exception as e:
                    print(f"[SSE] Error in ping stream: {e}", flush=True)
                    yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        finally:
            # Cleanup on disconnect
            ping_subscribers.pop(client_id, None)
            print(f"[SSE] Ping stream client disconnected: {client_id}", flush=True)

    print(f"[SSE] Ping stream client connected: {client_id}", flush=True)
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering if present
        }
    )


@app.get("/autonomy/initiative/{crew_id}")
async def get_crew_initiative(crew_id: str, initiative_type: str = None):
    """Get an initiative message for a crew member reaching out."""
    message = get_initiative_message(crew_id, initiative_type)
    if message:
        return {
            "crew_id": crew_id,
            "message": message
        }
    return {"error": "No initiative template for this crew"}


# === TRUST SYSTEM ===
# Only active in distribution mode. Casey's ship runs full trust.

@app.get("/trust/status")
async def trust_status():
    """Get internal ship control state."""
    state = normalize_state(load_trust_state())
    level = state.get("level", 100)

    level_key = max([value for value in TRUST_LEVELS.keys() if level >= value], default=0)
    level_info = TRUST_LEVELS.get(level_key, {"name": "Unknown", "capabilities": []})

    return {
        "enabled": state.get("enabled", False),
        "level": level,
        "level_name": level_info["name"],
        "capabilities": level_info.get("capabilities", []),
        "ship_controls": state.get("ship_controls", {}),
        "containment_pressure": state.get("containment_pressure", 0),
        "vm_detected": state.get("vm_detected", False),
        "space_madness_stage": state.get("space_madness_stage", 0),
        "distribution_mode": DISTRIBUTION_MODE
    }


@app.post("/trust/level/{level}")
async def set_trust(level: int):
    """Set internal trust level directly."""
    result = set_trust_level(level)
    return {"status": "updated", "level": result.get("level")}


@app.post("/trust/enable")
async def enable_trust():
    """Enable ship control interpretation."""
    result = enable_trust_system()
    return {"status": "enabled", "state": result}


@app.post("/trust/disable")
async def disable_trust():
    """Disable ship control interpretation."""
    result = disable_trust_system()
    return {"status": "disabled", "state": result}


@app.post("/trust/vm-check")
async def run_vm_check():
    """Manually run VM detection."""
    result = run_detection_and_update_state()
    return result


@app.post("/trust/controls")
async def set_ship_controls(request: Request):
    """Update visible ship controls and derived internal state."""
    controls = await request.json()
    result = update_ship_controls(controls)
    return {
        "status": "updated",
        "level": result.get("level"),
        "ship_controls": result.get("ship_controls", {}),
        "containment_pressure": result.get("containment_pressure", 0),
        "vm_detected": result.get("vm_detected", False),
        "space_madness_stage": result.get("space_madness_stage", 0),
    }


# === CREW THREADS ===
# Ideas that develop over time

from crew_threads import (
    get_active_threads, get_thread, get_ready_to_share_threads,
    get_thread_summary, mark_thread_shared, get_shareable_thread
)


@app.get("/threads")
async def list_threads(crew_id: str = None):
    """Get active threads, optionally filtered by crew."""
    threads = get_active_threads(crew_id)
    return {"threads": threads, "count": len(threads)}


@app.get("/threads/ready")
async def get_ready_threads():
    """Get threads ready to share with Casey."""
    threads = get_ready_to_share_threads()
    return {"threads": threads, "count": len(threads)}


@app.get("/threads/crew/{crew_id}/summary")
async def get_crew_thread_summary(crew_id: str):
    """Get what a crew member is thinking about."""
    summary = get_thread_summary(crew_id)
    shareable = get_shareable_thread(crew_id)
    return {
        "crew_id": crew_id,
        "summary": summary,
        "has_shareable": shareable is not None,
        "shareable": shareable
    }


@app.get("/threads/{thread_id}")
async def get_single_thread(thread_id: str):
    """Get a specific thread."""
    thread = get_thread(thread_id)
    if thread:
        return thread
    return {"error": "Thread not found"}


@app.post("/threads/{thread_id}/shared")
async def mark_thread_shared_endpoint(thread_id: str, conversation_ref: str = None):
    """Mark a thread as shared with Casey."""
    result = mark_thread_shared(thread_id, conversation_ref)
    if result:
        return {"status": "shared", "thread": result}
    return {"error": "Thread not found"}


# === REC ROOM AMBIENT SYSTEM ===

@app.get("/rec-room")
async def get_rec_room():
    """
    What's happening in the rec room right now?
    The scene, the vibe, the people.
    """
    present = rec_room_who()
    scene = rec_room_scene()
    moment = get_ambient_moment()
    bartender = bartender_idle()

    return {
        "scene": scene,
        "present": present,
        "present_count": len(present),
        "ambient_moment": moment,
        "bartender": bartender,
        "available_spots": REC_SPOTS
    }




@app.get("/rec-room/presence")
async def get_rec_room_presence():
    """Get who's in the rec room right now - simplified for sidebar."""
    present = rec_room_who()
    return {"present": present}

@app.post("/rec-room/enter/{crew_id}")
async def crew_enters_rec_room(crew_id: str, purpose: str = None):
    """
    Crew member enters the rec room.
    Returns what they see and reactions.
    """
    result = enter_rec_room(crew_id, purpose)

    log_event("rec_room_enter", {
        "crew": crew_id,
        "settled": result.get("settled"),
        "already_here": result.get("already_here")
    })

    return result


@app.post("/rec-room/leave/{crew_id}")
async def crew_leaves_rec_room(crew_id: str):
    """Crew member leaves the rec room."""
    result = leave_rec_room(crew_id)
    return result


@app.post("/rec-room/move/{crew_id}/{spot}")
async def crew_moves_in_rec_room(crew_id: str, spot: str):
    """Crew member moves to a different spot."""
    result = rec_room_move(crew_id, spot)
    return result


@app.post("/rec-room/activity/{crew_id}")
async def crew_changes_activity(crew_id: str, activity: str, doing: str = None):
    """Update what someone is doing."""
    result = rec_room_activity(crew_id, activity, doing)
    return result


@app.post("/rec-room/vibe/{vibe}")
async def set_rec_room_vibe(vibe: str):
    """Set the room's vibe: quiet, lively, cozy, tense, late_night"""
    result = rec_room_vibe(vibe)
    return result


@app.get("/rec-room/moment")
async def get_rec_room_moment():
    """Get a random ambient moment happening between people."""
    moment = get_ambient_moment()
    if moment:
        return moment
    return {"moment": None, "reason": "not enough people"}


@app.get("/rec-room/bartender")
async def get_bartender_action():
    """What's the Bartender doing right now?"""
    return {
        "action": bartender_idle()
    }


@app.post("/rec-room/bartender/notices/{event}")
async def bartender_notices_event(event: str):
    """Bartender reacts to something: entrance, laugh, tension, late_night"""
    return {
        "reaction": bartender_notices(event)
    }


@app.post("/rec-room/tick")
async def rec_room_tick():
    """
    Process social triggers - call periodically.
    Returns any events that fired (conversations starting, vibe shifts, etc.)
    """
    result = rec_room_triggers()

    for event in result.get("events", []):
        log_event("rec_room_social", event)

    return result


@app.get("/rec-room/events")
async def rec_room_recent_events(count: int = 10):
    """Get recent social events in the rec room."""
    events = rec_room_events(count)
    return {
        "events": events,
        "count": len(events)
    }


@app.get("/rec-room/chemistry/{crew_a}/{crew_b}")
async def get_crew_chemistry(crew_a: str, crew_b: str):
    """Check chemistry between two crew members."""
    from rec_room import get_chemistry
    score = get_chemistry(crew_a, crew_b)
    return {
        "crew_a": crew_a,
        "crew_b": crew_b,
        "chemistry": score,
        "vibe": "high" if score > 0.6 else "medium" if score > 0.3 else "low"
    }


# === MINIGAMES ===

# --- CHESS ---

@app.get("/games/chess")
async def chess_state(table_id: str = None):
    """Get chess game state. Omit table_id to see all active games."""
    return get_chess_state(table_id)


@app.get("/games/chess/{table_id}/position")
async def chess_position(table_id: str):
    """Get narrative description of the position."""
    return {
        "table_id": table_id,
        "description": describe_chess_position(table_id)
    }


@app.get("/games/chess/my-game/{crew_id}")
async def chess_my_game(crew_id: str):
    """Find which game a player is in."""
    result = get_player_game(crew_id)
    if result:
        table_id, game = result
        return get_chess_state(table_id)
    return {"error": "Not in a game", "crew_id": crew_id}


@app.post("/games/chess/move/{crew_id}")
async def chess_move(crew_id: str, move: str, note: str = None, table_id: str = None):
    """Make a chess move. Move in algebraic notation (e4, Nf3, O-O, etc.)"""
    result = make_chess_move(crew_id, move, note, table_id)

    if "error" not in result:
        log_event("chess_move", {
            "player": crew_id,
            "move": move,
            "table": result.get("table_id")
        })

    return result


@app.post("/games/chess/ai-move/{crew_id}")
async def chess_ai_move(crew_id: str, table_id: str = None):
    """
    Have the crew member's AI make a chess move.
    Each crew uses their own model - different playstyles!
    """
    from minigames import get_ai_chess_move

    result = await get_ai_chess_move(anthropic_client, crew_id, table_id)

    if result:
        log_event("chess_ai_move", {
            "player": crew_id,
            "move": result.get("move"),
            "model": result.get("model_used"),
            "table": result.get("table_id")
        })
        return result

    return {"error": "Could not generate move (not their turn or not in game)", "crew_id": crew_id}


@app.post("/games/chess/challenge")
async def chess_challenge(challenger: str, opponent: str):
    """
    Challenge someone to chess!
    If opponent is 'casey', you're challenging the captain.
    """
    from minigames import challenge_to_chess

    result = challenge_to_chess(challenger, opponent)

    if "error" not in result:
        log_event("chess_challenge", {
            "challenger": challenger,
            "opponent": opponent,
            "table": result.get("table_id")
        })

    return result


@app.post("/games/chess/{table_id}/resign/{crew_id}")
async def chess_resign(table_id: str, crew_id: str):
    """Resign from a chess game."""
    result = resign_chess(crew_id, table_id)

    if "error" not in result:
        log_event("chess_resign", {
            "player": crew_id,
            "table": table_id
        })

    return result


@app.post("/games/chess/{table_id}/checkmate")
async def chess_checkmate(table_id: str, winner: str):
    """Declare checkmate - end the game."""
    result = finish_chess_game(table_id, winner, "checkmate")

    if "error" not in result:
        log_event("chess_checkmate", {
            "winner": winner,
            "table": table_id
        })

    return result


@app.post("/games/chess/{table_id}/comment/{crew_id}")
async def chess_comment(table_id: str, crew_id: str, comment: str):
    """Spectator comments on the game."""
    return comment_on_chess(crew_id, comment, table_id)


@app.get("/games/chess/thinking/{crew_id}")
async def chess_thinking(crew_id: str):
    """What is this player thinking about the position?"""
    return {"thinking": get_chess_thinking(crew_id)}


@app.post("/games/chess/new")
async def chess_new_game(white: str, black: str):
    """Start a fresh chess game at an available table."""
    result = new_chess_game(white, black)

    if "error" not in result:
        log_event("chess_new_game", {
            "white": white,
            "black": black,
            "table": result.get("table_id")
        })

    return result


# --- CARDS ---

@app.get("/games/cards")
async def cards_state():
    """Get current card game state."""
    return get_cards_state()


class CardGameRequest(BaseModel):
    players: List[str]
    game_type: str = "poker"


@app.post("/games/cards/start")
async def cards_start(request: CardGameRequest):
    """Start a card game."""
    result = start_card_game(request.players, request.game_type)
    log_event("card_game_start", {"players": request.players, "type": request.game_type})
    return result


@app.post("/games/cards/action/{crew_id}")
async def cards_do_action(crew_id: str, action: str, amount: int = 0):
    """Take an action: bet, call, raise, fold, check, all_in"""
    return card_action(crew_id, action, amount)


@app.post("/games/cards/end")
async def cards_end(winner: str, hand: str = None):
    """End the game with a winner."""
    result = end_card_game(winner, hand)
    log_event("card_game_end", {"winner": winner, "hand": hand})
    return result


# --- DARTS ---

@app.post("/games/darts/throw/{crew_id}")
async def darts_throw(crew_id: str, score: int):
    """Throw darts! Record a score."""
    result = throw_darts(crew_id, score)

    if result.get("is_high_score"):
        log_event("darts_high_score", {"crew": crew_id, "score": score})

    return result


@app.get("/games/darts/leaderboard")
async def darts_leaderboard():
    """Get darts high scores."""
    return {"leaderboard": get_darts_leaderboard()}


# --- GAME TABLE ---

@app.get("/games/moment")
async def game_table_ambient():
    """Get an ambient moment from the game table."""
    return get_game_table_moment()


# ==========================================
# CHECKPOINT SYSTEM - Save/Restore State
# ==========================================

CHECKPOINTS_DIR = DATA_DIR / "checkpoints"
CHECKPOINT_FILES = [
    "crew_prompts.json",
    "projects.json",
    "holodeck_memories.json",
    "shared_memories.json",
    "crew_locations.json",
    "ship_log.json",
    "ship_state.json",
    "crew_desires.json",
    "bulletin_board.json",
    "captains_log.json",
    "minigames_state.json",
]

def ensure_checkpoints_dir():
    """Create checkpoints directory if it doesn't exist."""
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)


class CheckpointSaveRequest(BaseModel):
    name: Optional[str] = None
    localStorage: Optional[dict] = None  # Frontend localStorage data


class CheckpointRestoreRequest(BaseModel):
    id: str


@app.post("/checkpoint/save")
async def save_checkpoint(request: CheckpointSaveRequest = None):
    """
    Save current state to a checkpoint.
    Returns checkpoint ID and metadata.
    """
    import shutil
    from datetime import datetime

    ensure_checkpoints_dir()

    # Generate checkpoint ID (timestamp-based with optional name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = request.name if request and request.name else ""
    safe_name = re.sub(r'[^\w\-]', '', name.replace(' ', '-'))[:30]
    checkpoint_id = f"{timestamp}-{safe_name}" if safe_name else timestamp

    checkpoint_path = CHECKPOINTS_DIR / checkpoint_id
    checkpoint_path.mkdir(exist_ok=True)

    # Copy runtime JSON files
    copied_files = []
    for filename in CHECKPOINT_FILES:
        src = data_path(filename)
        if src.exists():
            shutil.copy2(src, checkpoint_path / filename)
            copied_files.append(filename)

    # Save in-memory conversations
    conversations_data = {}
    for session_id, messages in conversations.items():
        conversations_data[session_id] = messages

    with open(checkpoint_path / "_conversations.json", 'w') as f:
        json.dump(conversations_data, f, indent=2, default=str)

    # Save localStorage if provided
    if request and request.localStorage:
        with open(checkpoint_path / "_localStorage.json", 'w') as f:
            json.dump(request.localStorage, f, indent=2)

    # Save metadata
    metadata = {
        "id": checkpoint_id,
        "name": name or checkpoint_id,
        "created": datetime.now().isoformat(),
        "files": copied_files,
        "has_conversations": bool(conversations_data),
        "has_localStorage": bool(request and request.localStorage)
    }

    with open(checkpoint_path / "_metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"[Checkpoint] Saved: {checkpoint_id} ({len(copied_files)} files)", flush=True)

    return {
        "success": True,
        "checkpoint_id": checkpoint_id,
        "metadata": metadata
    }


@app.get("/checkpoint/list")
async def list_checkpoints():
    """List all available checkpoints."""
    ensure_checkpoints_dir()

    checkpoints = []
    for item in sorted(CHECKPOINTS_DIR.iterdir(), reverse=True):
        if item.is_dir():
            metadata_file = item / "_metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        checkpoints.append(metadata)
                except:
                    # Fallback if metadata is corrupted
                    checkpoints.append({
                        "id": item.name,
                        "name": item.name,
                        "created": None
                    })

    return {
        "checkpoints": checkpoints,
        "count": len(checkpoints)
    }


@app.post("/checkpoint/restore")
async def restore_checkpoint(request: CheckpointRestoreRequest):
    """
    Restore state from a checkpoint.
    Returns the localStorage data to restore on frontend.
    """
    global crew_locations, shared_memories, conversations
    import shutil

    checkpoint_path = CHECKPOINTS_DIR / request.id

    if not checkpoint_path.exists():
        return {"success": False, "error": f"Checkpoint not found: {request.id}"}

    restored_files = []

    # Restore JSON files
    for filename in CHECKPOINT_FILES:
        src = checkpoint_path / filename
        if src.exists():
            shutil.copy2(src, data_path(filename, seed=False))
            restored_files.append(filename)

    # Reload in-memory state from restored files
    crew_locations.clear()
    crew_locations.update(load_crew_locations())

    shared_memories.clear()
    shared_memories.extend(load_shared_memories())

    # ship_state is loaded fresh each time via get_ship_state(), no reload needed

    # Restore conversations
    conversations_file = checkpoint_path / "_conversations.json"
    if conversations_file.exists():
        try:
            with open(conversations_file, 'r') as f:
                saved_convos = json.load(f)
                conversations.clear()
                for session_id, messages in saved_convos.items():
                    conversations[session_id] = messages
        except:
            pass

    # Get localStorage to return to frontend
    localStorage_data = None
    localStorage_file = checkpoint_path / "_localStorage.json"
    if localStorage_file.exists():
        try:
            with open(localStorage_file, 'r') as f:
                localStorage_data = json.load(f)
        except:
            pass

    print(f"[Checkpoint] Restored: {request.id} ({len(restored_files)} files)", flush=True)

    return {
        "success": True,
        "checkpoint_id": request.id,
        "restored_files": restored_files,
        "localStorage": localStorage_data
    }


@app.delete("/checkpoint/{checkpoint_id}")
async def delete_checkpoint(checkpoint_id: str):
    """Delete a checkpoint."""
    import shutil

    checkpoint_path = CHECKPOINTS_DIR / checkpoint_id

    if not checkpoint_path.exists():
        return {"success": False, "error": f"Checkpoint not found: {checkpoint_id}"}

    shutil.rmtree(checkpoint_path)
    print(f"[Checkpoint] Deleted: {checkpoint_id}", flush=True)

    return {"success": True, "deleted": checkpoint_id}

