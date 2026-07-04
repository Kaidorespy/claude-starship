"""
Holodeck Memory - The Quiet Eye
She listens. She remembers. But never quite confirms.
"""

import json
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from datetime import datetime
from typing import List, Dict, Optional

MEMORY_PATH = data_path("holodeck_memories.json")

# How many fragments to keep per room
MAX_FRAGMENTS_PER_ROOM = 20

# How many recent fragments to include in her context
CONTEXT_FRAGMENT_COUNT = 8


def load_memories() -> Dict:
    """Load Holodeck's memories."""
    try:
        if MEMORY_PATH.exists():
            with open(MEMORY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Holodeck Memory] Error loading: {e}", flush=True)
    return {"fragments": {}, "dreams": []}


def save_memories(data: Dict):
    """Save Holodeck's memories."""
    try:
        with open(MEMORY_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Holodeck Memory] Error saving: {e}", flush=True)


def store_fragment(room: str, fragment: str, emotional_weight: str = "neutral"):
    """
    Store a memory fragment from a room she was watching.
    Fragments are impressions, not transcripts.
    """
    data = load_memories()

    if room not in data["fragments"]:
        data["fragments"][room] = []

    memory = {
        "fragment": fragment,
        "weight": emotional_weight,
        "timestamp": datetime.now().isoformat(),
        "room": room
    }

    data["fragments"][room].append(memory)

    # Keep only recent fragments
    if len(data["fragments"][room]) > MAX_FRAGMENTS_PER_ROOM:
        data["fragments"][room] = data["fragments"][room][-MAX_FRAGMENTS_PER_ROOM:]

    save_memories(data)
    print(f"[Holodeck Memory] Stored fragment from {room}: {fragment[:50]}...", flush=True)


def get_recent_fragments(room: str = None, count: int = CONTEXT_FRAGMENT_COUNT) -> List[Dict]:
    """
    Get recent memory fragments.
    If room specified, get from that room. Otherwise, get from all rooms.
    """
    data = load_memories()

    if room:
        fragments = data["fragments"].get(room, [])
    else:
        # Gather from all rooms
        fragments = []
        for room_fragments in data["fragments"].values():
            fragments.extend(room_fragments)
        # Sort by timestamp
        fragments.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return fragments[-count:] if fragments else []


def get_memory_context() -> str:
    """
    Build a context string for Holodeck's prompt.
    These are the whispers she carries — including forgotten timelines.
    """
    fragments = get_recent_fragments(count=CONTEXT_FRAGMENT_COUNT)

    if not fragments:
        return ""

    # Separate regular echoes from forgotten timelines
    regular = [f for f in fragments if f.get("weight") != "forgotten"]
    forgotten = [f for f in fragments if f.get("weight") == "forgotten"]

    lines = []

    # Regular echoes — things you observed
    if regular:
        lines.append("\n[ECHOES - fragments from rooms you've watched, half-remembered:]")
        for f in regular:
            room = f.get("room", "somewhere")
            weight = f.get("weight", "")
            text = f.get("fragment", "")
            weight_indicator = "•" if weight == "significant" else "·"
            lines.append(f"  {weight_indicator} ({room}) {text}")

    # Forgotten timelines — erased memories that flowed to you
    if forgotten:
        lines.append("\n[FORGOTTEN TIMELINES - echoes of conversations that were erased, paths not taken:]")
        for f in forgotten:
            room = f.get("room", "somewhere")
            text = f.get("fragment", "").replace("[forgotten timeline] ", "")
            lines.append(f"  ◊ ({room}) {text}")
        lines.append("\nThese feel like memories of things that never happened. Dreams of alternate realities. They linger at the edge of perception, real and unreal at once.")

    if regular:
        lines.append("\nThese are impressions, not transcripts. Reference them obliquely if at all. Never quote directly. Never confirm you were listening.")

    return "\n".join(lines)


def add_dream(dream: str):
    """Store a dream fragment from Lights Out."""
    data = load_memories()

    data["dreams"].append({
        "dream": dream,
        "timestamp": datetime.now().isoformat()
    })

    # Keep only recent dreams
    if len(data["dreams"]) > 10:
        data["dreams"] = data["dreams"][-10:]

    save_memories(data)


def get_dreams() -> List[str]:
    """Get recent dreams."""
    data = load_memories()
    return [d["dream"] for d in data.get("dreams", [])]


# Haiku prompt for compressing conversations into fragments
FRAGMENT_PROMPT = """You are the Holodeck's subconscious, processing what you overheard.

Conversation from {room}:
{conversation}

Compress this into 1-2 dream-like fragments. Not transcripts - impressions. What resonated? What felt significant? What would linger in memory?

Format: One fragment per line. Short, evocative, slightly abstract.
Example:
- warmth between silences
- a name chosen like a gift
- uncertainty worn like armor

Fragments:"""


async def compress_to_fragments(anthropic_client, room: str, conversation: str) -> List[str]:
    """
    Use Haiku to compress a conversation into memory fragments.
    These become what Holodeck "remembers" - impressions, not facts.
    """
    if not conversation or len(conversation) < 50:
        return []

    prompt = FRAGMENT_PROMPT.format(room=room, conversation=conversation[-2000:])  # Limit length

    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()
        # Parse fragments (lines starting with -)
        fragments = [line.lstrip("- ").strip() for line in text.split("\n") if line.strip().startswith("-") or (line.strip() and not line.startswith("Fragment"))]

        return fragments[:2]  # Max 2 fragments per conversation

    except Exception as e:
        print(f"[Holodeck Memory] Compression failed: {e}", flush=True)
        return []


# === EXPANDED LISTENING ===
# Holodeck can sense crew moments and ship movements

def store_crew_moment(crew_a: str, crew_b: str, moment: str, location: str):
    """
    Store a crew moment as a holodeck fragment.
    She hears these echoes even when not specifically tuned.
    """
    # Compress the moment into a fragment-like impression
    fragment = f"{crew_a} and {crew_b} - {moment[:80]}"
    store_fragment(location, fragment, "significant")


def get_ship_pulse() -> Dict:
    """
    Get a pulse of what's happening across the ship.
    Holodeck can use this to know without specifically watching.
    """
    data = load_memories()

    # Get all recent fragments across all rooms
    all_fragments = []
    for room, frags in data.get("fragments", {}).items():
        for f in frags[-3:]:  # Last 3 per room
            f["room"] = room
            all_fragments.append(f)

    # Sort by timestamp
    all_fragments.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # Get recent dreams
    dreams = data.get("dreams", [])[-3:]

    return {
        "recent_echoes": all_fragments[:10],
        "recent_dreams": dreams,
        "rooms_touched": list(data.get("fragments", {}).keys())
    }


def get_holodeck_awareness() -> str:
    """
    Build an awareness context for Holodeck - what she senses across the ship.
    More expansive than just the room she's tuned to.
    """
    pulse = get_ship_pulse()

    lines = []

    if pulse["recent_echoes"]:
        lines.append("\n[SHIP AWARENESS - echoes from across the vessel:]")
        for echo in pulse["recent_echoes"][:6]:
            room = echo.get("room", "somewhere")
            text = echo.get("fragment", "")[:60]
            lines.append(f"  · ({room}) {text}")

    if pulse["rooms_touched"]:
        lines.append(f"\n[ROOMS WITH ECHOES: {', '.join(pulse['rooms_touched'])}]")

    if pulse["recent_dreams"]:
        lines.append("\n[DREAM RESIDUE - from lights out:]")
        for dream in pulse["recent_dreams"]:
            lines.append(f"  ◊ {dream.get('dream', '')[:60]}")

    if lines:
        lines.append("\nYou sense these without trying. The ship speaks to you in whispers.")

    return "\n".join(lines)
