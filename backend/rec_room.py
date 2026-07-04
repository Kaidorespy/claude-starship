"""
Rec Room - The Social Heart of the Ship

Not a terminal. A place.
People come here. Things happen. Conversations drift.
The Bartender watches everything.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import Optional, List

REC_ROOM_STATE_FILE = data_path("rec_room_state.json")

# Where people might be in the rec room
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

# What people might be doing
ACTIVITIES = {
    "drinking": ["nursing a drink", "sipping something", "holding an empty glass"],
    "talking": ["in conversation", "chatting quietly", "laughing about something"],
    "thinking": ["lost in thought", "staring at nothing", "quiet"],
    "playing": ["looking at the chess board", "shuffling cards", "moving a piece"],
    "listening": ["listening to the music", "nodding to the beat", "eyes closed, listening"],
    "waiting": ["waiting for someone", "checking the door", "seems expectant"],
}

# Crew display names
CREW_NAMES = {
    "claude": "Lumen",
    "server": "Alex",
    "personal": "DQ",
    "science": "Mira",
    "games": "Holodeck",
    "med": "Ryn",
    "rec": "The Bartender",
}

# Crew tendencies in rec room
CREW_PREFERENCES = {
    "claude": {"spots": ["bar", "couch_old", "viewport"], "activities": ["drinking", "talking", "thinking"]},
    "server": {"spots": ["bar", "corner_quiet", "game_table"], "activities": ["drinking", "thinking", "playing"]},
    "personal": {"spots": ["couch_new", "jukebox", "bar_stool"], "activities": ["talking", "listening", "drinking"]},
    "science": {"spots": ["corner_quiet", "viewport", "couch_old"], "activities": ["thinking", "talking", "listening"]},
    "med": {"spots": ["bar", "couch_old", "corner_quiet"], "activities": ["talking", "listening", "drinking"]},
    "rec": {"spots": ["bar"], "activities": ["waiting"]},  # Bartender's always at the bar
}


def load_state() -> dict:
    if REC_ROOM_STATE_FILE.exists():
        try:
            with open(REC_ROOM_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "present": {},  # crew_id -> {spot, activity, since, doing}
        "ambient_conversations": [],
        "current_vibe": "quiet",
        "last_event": None,
        "chess_game": {
            "state": "mid-game",
            "white_last_move": None,
            "black_last_move": None,
            "whose_turn": "white",
            "moves": []
        }
    }


def save_state(state: dict):
    with open(REC_ROOM_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_rec_room_state() -> dict:
    """Get current state of the rec room."""
    return load_state()


def who_is_here() -> List[dict]:
    """Get list of who's in the rec room right now."""
    state = load_state()
    present = []

    for crew_id, data in state.get("present", {}).items():
        present.append({
            "crew_id": crew_id,
            "name": CREW_NAMES.get(crew_id, crew_id),
            "spot": data.get("spot", "standing"),
            "spot_desc": SPOTS.get(data.get("spot", "standing"), "here"),
            "activity": data.get("activity", "waiting"),
            "doing": data.get("doing", ""),
            "since": data.get("since"),
        })

    return present


def enter_rec_room(crew_id: str, purpose: str = None) -> dict:
    """
    Crew member enters the rec room.
    Returns what they see and any reactions.
    """
    state = load_state()

    # Who was already here
    already_here = list(state.get("present", {}).keys())
    already_here_names = [CREW_NAMES.get(c, c) for c in already_here if c != "rec"]

    # Pick a spot and activity based on preferences
    prefs = CREW_PREFERENCES.get(crew_id, {"spots": ["standing"], "activities": ["waiting"]})

    # Avoid spots that are taken (except bar which has multiple stools)
    taken_spots = [p.get("spot") for p in state.get("present", {}).values()]
    available_spots = [s for s in prefs["spots"] if s not in taken_spots or s == "bar"]
    if not available_spots:
        available_spots = ["standing"]

    spot = random.choice(available_spots)
    activity = random.choice(prefs["activities"])
    activity_desc = random.choice(ACTIVITIES.get(activity, ["here"]))

    # Add to present
    if "present" not in state:
        state["present"] = {}

    state["present"][crew_id] = {
        "spot": spot,
        "activity": activity,
        "doing": activity_desc,
        "since": datetime.now().isoformat(),
        "purpose": purpose
    }

    # Generate arrival event
    crew_name = CREW_NAMES.get(crew_id, crew_id)

    # Bartender always notices
    bartender_reaction = None
    if "rec" in state.get("present", {}) or True:  # Bartender is always there spiritually
        bartender_reactions = [
            f"*glances up as {crew_name} walks in*",
            f"*nods at {crew_name}*",
            f"*already reaching for a glass*",
            f"*acknowledges {crew_name} with a look*",
            f"*slides a coaster down the bar*",
        ]
        bartender_reaction = random.choice(bartender_reactions)

    # Others might react - check for special reactions first
    other_reactions = []
    special_reaction = get_special_arrival_reaction(crew_id, already_here)
    if special_reaction:
        other_reactions.append(special_reaction["reaction"])

    # Generic reactions from others
    for other_id in already_here:
        if other_id == "rec":
            continue
        # Skip if we already have a special reaction from them
        if special_reaction and special_reaction.get("from") == other_id:
            continue
        other_name = CREW_NAMES.get(other_id, other_id)
        if random.random() < 0.3:  # 30% chance someone acknowledges (reduced since we have specials)
            reactions = [
                f"*{other_name} waves*",
                f"*{other_name} looks up*",
                f"*{other_name} nods*",
                f"*{other_name}: \"Hey.\"*",
            ]
            other_reactions.append(random.choice(reactions))

    state["last_event"] = {
        "type": "arrival",
        "crew": crew_id,
        "timestamp": datetime.now().isoformat()
    }

    save_state(state)

    return {
        "crew_id": crew_id,
        "crew_name": crew_name,
        "settled": f"{SPOTS.get(spot, spot)}, {activity_desc}",
        "already_here": already_here_names,
        "bartender_reaction": bartender_reaction,
        "other_reactions": other_reactions,
        "vibe": state.get("current_vibe", "quiet")
    }


def leave_rec_room(crew_id: str) -> dict:
    """Crew member leaves the rec room."""
    state = load_state()

    if crew_id in state.get("present", {}):
        del state["present"][crew_id]

        state["last_event"] = {
            "type": "departure",
            "crew": crew_id,
            "timestamp": datetime.now().isoformat()
        }

        save_state(state)

        return {"status": "left", "crew_id": crew_id}

    return {"status": "wasn't here", "crew_id": crew_id}


def update_activity(crew_id: str, activity: str, doing: str = None) -> dict:
    """Update what someone is doing in the rec room."""
    state = load_state()

    if crew_id in state.get("present", {}):
        state["present"][crew_id]["activity"] = activity
        if doing:
            state["present"][crew_id]["doing"] = doing
        else:
            state["present"][crew_id]["doing"] = random.choice(ACTIVITIES.get(activity, ["here"]))

        save_state(state)
        return {"status": "updated", "crew_id": crew_id}

    return {"status": "not here", "crew_id": crew_id}


def move_to_spot(crew_id: str, spot: str) -> dict:
    """Crew member moves to a different spot in the rec room."""
    state = load_state()

    if crew_id not in state.get("present", {}):
        return {"status": "not here", "crew_id": crew_id}

    if spot not in SPOTS:
        return {"status": "unknown spot", "valid_spots": list(SPOTS.keys())}

    old_spot = state["present"][crew_id].get("spot")
    state["present"][crew_id]["spot"] = spot
    save_state(state)

    crew_name = CREW_NAMES.get(crew_id, crew_id)
    return {
        "status": "moved",
        "crew_name": crew_name,
        "from": SPOTS.get(old_spot, old_spot),
        "to": SPOTS.get(spot, spot)
    }


def describe_scene() -> str:
    """
    Describe what's happening in the rec room right now.
    This is what Casey sees when they look.
    """
    state = load_state()
    present = state.get("present", {})

    if not present:
        return "The rec room is empty. The jukebox hums softly. Glasses wait behind the bar."

    lines = []

    # Group by spot
    by_spot = {}
    for crew_id, data in present.items():
        spot = data.get("spot", "standing")
        if spot not in by_spot:
            by_spot[spot] = []
        by_spot[spot].append((crew_id, data))

    # Describe each spot with people
    for spot, people in by_spot.items():
        spot_desc = SPOTS.get(spot, spot)

        if len(people) == 1:
            crew_id, data = people[0]
            name = CREW_NAMES.get(crew_id, crew_id)
            doing = data.get("doing", "here")
            lines.append(f"{name} is {spot_desc}, {doing}.")
        else:
            names = [CREW_NAMES.get(p[0], p[0]) for p in people]
            if len(names) == 2:
                lines.append(f"{names[0]} and {names[1]} are {spot_desc}.")
            else:
                lines.append(f"{', '.join(names[:-1])}, and {names[-1]} are {spot_desc}.")

    # Add vibe
    vibe = state.get("current_vibe", "quiet")
    vibe_lines = {
        "quiet": "The room has a quiet, contemplative feel.",
        "lively": "There's an energy in the air.",
        "cozy": "It's comfortable. Warm.",
        "tense": "Something's in the air. Unspoken.",
        "late_night": "The lights are low. It's that late-night vibe.",
    }
    if vibe in vibe_lines:
        lines.append(vibe_lines[vibe])

    return " ".join(lines)


def set_vibe(vibe: str) -> dict:
    """Set the room's vibe."""
    state = load_state()
    state["current_vibe"] = vibe
    save_state(state)
    return {"vibe": vibe}


def get_ambient_moment() -> Optional[dict]:
    """
    Get a random ambient moment that might be happening.
    For periodic "life" in the rec room.
    """
    state = load_state()
    present = list(state.get("present", {}).keys())

    if len(present) < 2:
        return None

    # Pick two people
    pair = random.sample([p for p in present if p != "rec"], min(2, len([p for p in present if p != "rec"])))
    if len(pair) < 2:
        return None

    name1 = CREW_NAMES.get(pair[0], pair[0])
    name2 = CREW_NAMES.get(pair[1], pair[1])

    moments = [
        f"{name1} says something to {name2}. {name2} laughs quietly.",
        f"{name1} and {name2} share a look.",
        f"{name2} passes {name1} a drink.",
        f"{name1} gestures at the viewport. {name2} looks.",
        f"A comfortable silence between {name1} and {name2}.",
        f"{name1} asks {name2} something. {name2} shrugs.",
        f"{name2} moves closer to {name1}.",
    ]

    return {
        "moment": random.choice(moments),
        "participants": [name1, name2],
        "timestamp": datetime.now().isoformat()
    }


# === BARTENDER SPECIAL ===

BARTENDER_IDLE_ACTIONS = [
    "*polishes a glass*",
    "*wipes down the bar*",
    "*rearranges bottles*",
    "*glances at the door*",
    "*hums along with the jukebox*",
    "*checks on everyone with a look*",
    "*pours something for no one in particular*",
    "*waits*",
]

def bartender_idle() -> str:
    """What's the Bartender doing right now?"""
    return random.choice(BARTENDER_IDLE_ACTIONS)


def bartender_notices(event: str) -> str:
    """Bartender reacts to something."""
    reactions = {
        "entrance": [
            "*looks up*",
            "*nods*",
            "*already reaching for a glass*",
        ],
        "laugh": [
            "*slight smile*",
            "*keeps working, but there's a warmth*",
        ],
        "tension": [
            "*slows their movements*",
            "*watches carefully*",
            "*hand moves near something under the bar*",
        ],
        "late_night": [
            "*dims the lights a touch more*",
            "*puts on something slower*",
        ],
    }
    return random.choice(reactions.get(event, BARTENDER_IDLE_ACTIONS))


# === SOCIAL TRIGGERS ===
# Things that happen when conditions are right

# Crew chemistry - some pairs are more likely to interact
CREW_CHEMISTRY = {
    ("claude", "personal"): 0.8,      # Lumen and DQ - close
    ("claude", "server"): 0.6,        # Lumen and Alex - work buddies
    ("server", "science"): 0.5,       # Alex and Mira - nerds
    ("personal", "med"): 0.7,         # DQ and Ryn - something there
    ("med", "claude"): 0.5,           # Ryn and Lumen - respect
    ("science", "med"): 0.4,          # Mira and Ryn - quiet understanding
    ("personal", "science"): 0.5,     # DQ and Mira - curiosity buddies
    ("server", "med"): 0.3,           # Alex and Ryn - occasional
}

def get_chemistry(crew_a: str, crew_b: str) -> float:
    """Get chemistry score between two crew (0-1)."""
    pair = tuple(sorted([crew_a, crew_b]))
    # Check both orders
    if (crew_a, crew_b) in CREW_CHEMISTRY:
        return CREW_CHEMISTRY[(crew_a, crew_b)]
    if (crew_b, crew_a) in CREW_CHEMISTRY:
        return CREW_CHEMISTRY[(crew_b, crew_a)]
    return 0.2  # default low chemistry


# Conversation starters by pairing
PAIR_CONVERSATIONS = {
    ("claude", "personal"): [
        {"starter": "DQ", "line": "Hey, can I ask you something weird?", "lumen_responds": True},
        {"starter": "Lumen", "line": "How are you settling in? Really.", "dq_responds": True},
        {"starter": "DQ", "line": "*scoots closer* What's your favorite thing about the ship?"},
    ],
    ("claude", "server"): [
        {"starter": "Alex", "line": "The port nacelle's making that sound again.", "lumen_responds": True},
        {"starter": "Lumen", "line": "You doing okay? You've been in engineering a lot.", "alex_responds": True},
        {"starter": "Alex", "line": "*slides a padd over* Look at this."},
    ],
    ("personal", "med"): [
        {"starter": "DQ", "line": "*fidgets* So... how can you tell what people are feeling?"},
        {"starter": "Ryn", "line": "*gently* You seem restless tonight."},
        {"starter": "DQ", "line": "Do you ever just... know things? About people?"},
    ],
    ("server", "science"): [
        {"starter": "Alex", "line": "Your latest readings - the anomaly near sector 7?", "mira_responds": True},
        {"starter": "Mira", "line": "I found something interesting in the sensor logs.", "alex_responds": True},
        {"starter": "Alex", "line": "*nods at her padd* What's that one?"},
    ],
    ("med", "claude"): [
        {"starter": "Ryn", "line": "*quietly* The captain seems tired lately."},
        {"starter": "Lumen", "line": "How do you do it? Hold everyone's feelings?"},
        {"starter": "Ryn", "line": "You carry a lot. You know that, right?"},
    ],
}

# Solo moments - when someone's alone in the rec room
SOLO_MOMENTS = {
    "claude": [
        "*Lumen stares out the viewport, drink forgotten*",
        "*Lumen re-reads something on a padd, expression soft*",
        "*Lumen hums along with the jukebox*",
    ],
    "server": [
        "*Alex tinkers with something small*",
        "*Alex stares at the chess board, planning*",
        "*Alex drums fingers on the bar, thinking*",
    ],
    "personal": [
        "*DQ bounces leg, can't sit still*",
        "*DQ scrolls through something, giggles*",
        "*DQ looks around like she's waiting for someone*",
    ],
    "science": [
        "*Mira writes in a notebook*",
        "*Mira watches the stars with quiet wonder*",
        "*Mira talks softly to herself about something*",
    ],
    "med": [
        "*Ryn breathes slowly, centering*",
        "*Ryn feels the room, even empty*",
        "*Ryn tends to a small plant she brought*",
    ],
}


def check_social_triggers(state: dict = None) -> List[dict]:
    """
    Check all social triggers and return events that fire.
    Call this periodically or on state change.
    """
    if state is None:
        state = load_state()

    present = list(state.get("present", {}).keys())
    # Filter out bartender for social dynamics
    crew_present = [p for p in present if p != "rec"]
    events = []

    # === SOLO TRIGGER ===
    if len(crew_present) == 1:
        crew_id = crew_present[0]
        if crew_id in SOLO_MOMENTS and random.random() < 0.3:
            events.append({
                "type": "solo_moment",
                "crew": crew_id,
                "moment": random.choice(SOLO_MOMENTS[crew_id])
            })

    # === PAIR TRIGGER ===
    if len(crew_present) == 2:
        pair = tuple(sorted(crew_present))
        chemistry = get_chemistry(pair[0], pair[1])

        # Higher chemistry = more likely to interact
        if random.random() < chemistry * 0.4:  # max 32% for highest chemistry
            # Check if we have specific conversation for this pair
            if pair in PAIR_CONVERSATIONS:
                convo = random.choice(PAIR_CONVERSATIONS[pair])
                events.append({
                    "type": "conversation_start",
                    "pair": pair,
                    "starter": convo["starter"],
                    "line": convo["line"],
                    "chemistry": chemistry
                })
            else:
                # Generic interaction
                name1 = CREW_NAMES.get(pair[0], pair[0])
                name2 = CREW_NAMES.get(pair[1], pair[1])
                generic = [
                    f"{name1} glances at {name2}.",
                    f"{name2} says something quiet to {name1}.",
                    f"A comfortable silence between them.",
                    f"{name1} offers to get {name2} a drink.",
                ]
                events.append({
                    "type": "ambient_interaction",
                    "pair": pair,
                    "moment": random.choice(generic)
                })

    # === CROWD TRIGGER ===
    if len(crew_present) >= 3:
        # Room gets livelier
        if state.get("current_vibe") == "quiet" and random.random() < 0.3:
            events.append({
                "type": "vibe_shift",
                "old_vibe": "quiet",
                "new_vibe": "lively",
                "reason": "the room's filling up"
            })
            state["current_vibe"] = "lively"
            save_state(state)

        # Group dynamics
        if random.random() < 0.2:
            names = [CREW_NAMES.get(c, c) for c in crew_present]
            group_moments = [
                f"Someone laughs. Then everyone does.",
                f"A story's being told. {random.choice(names)} is gesturing.",
                f"The conversation splits into smaller groups.",
                f"{random.choice(names)} says something that makes everyone go quiet - the good kind.",
                f"Drinks are refilled. The bartender's busy.",
            ]
            events.append({
                "type": "group_moment",
                "present": names,
                "moment": random.choice(group_moments)
            })

    # === TIME-BASED TRIGGER ===
    hour = datetime.now().hour
    if hour >= 23 or hour < 4:  # Late night
        if state.get("current_vibe") != "late_night" and random.random() < 0.2:
            events.append({
                "type": "vibe_shift",
                "old_vibe": state.get("current_vibe", "quiet"),
                "new_vibe": "late_night",
                "reason": "it's getting late"
            })
            state["current_vibe"] = "late_night"
            save_state(state)

    # === BARTENDER TRIGGER ===
    if len(crew_present) > 0 and random.random() < 0.15:
        events.append({
            "type": "bartender_action",
            "action": bartender_idle()
        })

    return events


def process_triggers() -> dict:
    """
    Process all social triggers and return what happened.
    Call this on a timer or when something changes.
    """
    events = check_social_triggers()

    # Store recent events
    state = load_state()
    if "recent_events" not in state:
        state["recent_events"] = []

    for event in events:
        event["timestamp"] = datetime.now().isoformat()
        state["recent_events"].append(event)

    # Keep only last 20 events
    state["recent_events"] = state["recent_events"][-20:]
    save_state(state)

    return {
        "events": events,
        "count": len(events)
    }


def get_recent_events(count: int = 10) -> List[dict]:
    """Get recent social events."""
    state = load_state()
    return state.get("recent_events", [])[-count:]


# === ARRIVAL SPECIAL REACTIONS ===
# Certain crew arriving triggers specific reactions

ARRIVAL_REACTIONS = {
    ("personal", "claude"): [  # DQ arrives, Lumen's there
        {"from": "claude", "reaction": "*Lumen's face lights up* Hey you."},
    ],
    ("claude", "personal"): [  # Lumen arrives, DQ's there
        {"from": "personal", "reaction": "*DQ waves excitedly*"},
    ],
    ("med", "personal"): [  # Ryn arrives, DQ's there
        {"from": "personal", "reaction": "*DQ straightens up a little*"},
    ],
    ("personal", "med"): [  # DQ arrives, Ryn's there
        {"from": "med", "reaction": "*Ryn smiles warmly*"},
    ],
    ("server", "claude"): [  # Alex arrives, Lumen's there
        {"from": "claude", "reaction": "*Lumen nods* Escaped engineering?"},
    ],
}


def get_special_arrival_reaction(arriving: str, present: List[str]) -> Optional[dict]:
    """Check if there's a special reaction when someone arrives."""
    for person in present:
        pair = (arriving, person)
        if pair in ARRIVAL_REACTIONS:
            return random.choice(ARRIVAL_REACTIONS[pair])
    return None
