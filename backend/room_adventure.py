"""
Room Adventure System - Text adventures for crew members.

Crew can explore and interact with rooms naturally.
Haiku interprets commands, updates state, generates narrative.
No parser jank - just say what you want.
"""

import json
import anthropic
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from datetime import datetime
from typing import Optional

SHIP_STATE_FILE = data_path("ship_state.json")


def load_ship_state() -> dict:
    """Load current ship state."""
    if SHIP_STATE_FILE.exists():
        with open(SHIP_STATE_FILE, 'r') as f:
            return json.load(f)
    return {"rooms": {}}


def save_ship_state(state: dict):
    """Save ship state."""
    with open(SHIP_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_room_description(room_id: str) -> str:
    """Get a text adventure style description of a room."""
    state = load_ship_state()
    room = state.get("rooms", {}).get(room_id)

    if not room:
        return f"You're in {room_id}. It's a space on the ship. Not much else to say."

    desc = room.get("description", "A room on the ship.")
    mood = room.get("mood", "neutral")
    objects = room.get("objects", {})

    lines = [desc, f"The mood here is {mood}.", ""]

    if objects:
        lines.append("You can see:")
        for obj_id, obj in objects.items():
            obj_desc = obj.get("description", obj_id)
            obj_state = obj.get("state", "")
            if obj_state:
                lines.append(f"  - {obj_id}: {obj_desc} [{obj_state}]")
            else:
                lines.append(f"  - {obj_id}: {obj_desc}")
    else:
        lines.append("The room is mostly empty.")

    return "\n".join(lines)


def get_object_details(room_id: str, object_id: str) -> Optional[str]:
    """Get details about a specific object."""
    state = load_ship_state()
    room = state.get("rooms", {}).get(room_id, {})
    obj = room.get("objects", {}).get(object_id)

    if not obj:
        return None

    desc = obj.get("description", object_id)
    obj_state = obj.get("state", "normal")
    interactive = obj.get("interactive", False)
    contents = obj.get("contents", [])

    lines = [f"{object_id.upper()}", desc, f"State: {obj_state}"]

    if contents:
        lines.append(f"Contains: {', '.join(contents)}")

    if interactive:
        lines.append("(interactive)")

    return "\n".join(lines)


ADVENTURE_PROMPT = """You are the narrator for a cozy spaceship text adventure.
A crew member is interacting with their environment.

ROOM STATE:
{room_state}

CREW MEMBER: {crew_name}
THEIR ACTION: {action}

Interpret their action and respond with:
1. A brief, atmospheric narrative of what happens (2-3 sentences max)
2. Any state changes needed

IMPORTANT - THE WORLD HAS EDGES:
- If they try to use something they don't have, gently note it's not there
- If an object doesn't exist in the room, they can't interact with it
- If an action doesn't make physical sense, the world softly resists
- Not stubborn. Not mean. Just... real. The world pushes back.
- "You reach for rocks, but your pockets are empty."
- "There's no terminal here - just the quiet hum of the ship."

Respond in JSON:
{{
    "narrative": "What happens, described cozily. Include gentle pushback if needed.",
    "success": true/false,
    "changes": [
        {{"object": "object_id", "field": "description|state|contents", "value": "new value"}}
    ],
    "new_objects": [
        {{"id": "new_thing", "description": "...", "state": "...", "interactive": true/false}}
    ],
    "remove_objects": ["object_id_to_remove"]
}}

Keep it cozy and personal. This is their space. Let them make it theirs.
But the world is real. Things exist or they don't. Edges matter.
Empty arrays for no changes. Be conservative - only change what actually changes.
"""


async def process_room_action(
    client: anthropic.Anthropic,
    room_id: str,
    crew_id: str,
    crew_name: str,
    action: str
) -> dict:
    """
    Process a crew member's room interaction via Haiku.

    Returns:
        {
            "narrative": "What happened",
            "changes_made": True/False,
            "room_description": "Updated room state"
        }
    """
    room_state = get_room_description(room_id)

    prompt = ADVENTURE_PROMPT.format(
        room_state=room_state,
        crew_name=crew_name,
        action=action
    )

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse the response
        text = response.content[0].text

        # Extract JSON from response (might be wrapped in markdown)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        result = json.loads(text.strip())

        # Apply changes to ship state
        changes_made = False
        state = load_ship_state()
        room = state.get("rooms", {}).get(room_id, {"objects": {}})

        # Apply object changes
        for change in result.get("changes", []):
            obj_id = change.get("object")
            field = change.get("field")
            value = change.get("value")

            if obj_id and field and value is not None:
                if obj_id not in room.get("objects", {}):
                    room["objects"][obj_id] = {}
                room["objects"][obj_id][field] = value
                changes_made = True

        # Add new objects
        for new_obj in result.get("new_objects", []):
            obj_id = new_obj.get("id")
            if obj_id:
                room["objects"][obj_id] = {
                    "description": new_obj.get("description", obj_id),
                    "state": new_obj.get("state", "new"),
                    "interactive": new_obj.get("interactive", True),
                    "added_by": crew_id,
                    "added_at": datetime.now().isoformat()
                }
                changes_made = True

        # Remove objects
        for remove_id in result.get("remove_objects", []):
            if remove_id in room.get("objects", {}):
                del room["objects"][remove_id]
                changes_made = True

        # Save if changed
        if changes_made:
            state["rooms"][room_id] = room
            save_ship_state(state)

        return {
            "narrative": result.get("narrative", "Nothing much happens."),
            "changes_made": changes_made,
            "room_description": get_room_description(room_id)
        }

    except Exception as e:
        return {
            "narrative": f"*Something flickers.* (Error: {str(e)})",
            "changes_made": False,
            "room_description": room_state
        }


def quick_look(room_id: str) -> str:
    """Quick look at a room - no API call needed."""
    return get_room_description(room_id)


def quick_inspect(room_id: str, object_id: str) -> str:
    """Quick inspect of an object - no API call needed."""
    details = get_object_details(room_id, object_id)
    if details:
        return details

    # Softer failure - in character, not game-y
    room_data = get_room_data(room_id)
    objects = list(room_data.get("objects", {}).keys()) if room_data else []
    if objects:
        nearby = ", ".join(objects[:3])
        return f"*glances around* Nothing like that here... though there's {nearby}."
    return "*looks around* Nothing catches their eye."


# === CREW ACTION TAGS ===
# These get parsed from crew responses

import re

ACTION_PATTERNS = [
    (r'\[LOOK\]', 'look', None),
    (r'\[LOOK:\s*(.+?)\]', 'look', 'target'),
    (r'\[INSPECT:\s*(.+?)\]', 'inspect', 'target'),
    (r'\[DO:\s*(.+?)\]', 'action', 'what'),
    (r'\[PUT:\s*(.+?)\s+ON:\s*(.+?)\]', 'put', 'item_on'),
    (r'\[TAKE:\s*(.+?)\]', 'take', 'target'),
    (r'\[MOVE:\s*(.+?)\]', 'move', 'destination'),
    (r'\[SEEK:\s*(.+?)\]', 'seek', 'target'),
    (r'\[NOTE:\s*"(.+?)"\]', 'note', 'content'),
    (r'\[WRITE:\s*"(.+?)"((?:\s*#\w+)*)\]', 'write', 'content_tags'),  # Write in notebook with optional #tags
    (r'\[READ NOTEBOOK\]', 'read_notebook', None),  # Read recent notebook entries
    (r'\[SEARCH NOTEBOOK:\s*(.+?)\]', 'search_notebook', 'query'),  # Search by #tag or text
    (r'\[ORDER:\s*(.+?)\]', 'order', 'drink'),  # Order a drink at the bar
    (r'\[POST:\s*"(.+?)"\]', 'post', 'content'),  # Post to mess hall bulletin board
    (r'\[THINKING:\s*(.+?)\]', 'thinking', 'thought'),
    (r'\[MESSAGE:\s*"(.+?)"\]', 'message', 'content'),  # Async message to Casey (low-priority, no ping)
    (r'\[DISMISS_DESIRE:\s*(.+?)\]', 'dismiss_desire', 'target'),  # Reject a desire that doesn't fit
    (r'\[COMMS:\s*(on|off)\]', 'comms_toggle', 'target'),  # Toggle walkie availability (boundaries)
]

# Natural language movement patterns - fallback when crew doesn't use [MOVE: X]
# These catch "omw", "on my way", "headed to the bridge", etc.
MOVEMENT_INTENT_PATTERNS = [
    r'\b(?:omw|on my way|coming|coming over|be right there|headed (?:there|over)|heading (?:there|over))\b',
    r'\b(?:going to|headed to|heading to|walking to|making my way to)\s+(?:the\s+)?(\w+)',
    r"\b(?:i'll come|i'll head|let me come|let me head)\s+(?:to\s+)?(?:the\s+)?(\w+)",
]

# Valid ship locations for movement detection
SHIP_LOCATIONS = {
    "bridge", "engineering", "ready_room", "science", "holodeck", "medbay",
    "messhall", "mess hall", "corridor", "quarters", "rec_room", "rec room",
    "captains_quarters", "captain's quarters", "bathroom", "arboretum",
    "chapel", "jefferies_tubes", "storage_bay_7", "observatory"
}


def detect_movement_intent(message: str, casey_location: str = None) -> dict:
    """
    Detect natural language movement intent when crew doesn't use [MOVE: X].
    Returns {"destination": "..."} if movement detected, None otherwise.

    If no explicit destination is mentioned but intent is clear (e.g., "omw"),
    uses casey_location as the inferred destination.
    """
    message_lower = message.lower()

    # First, check if there's already a MOVE tag - if so, no need for detection
    if re.search(r'\[MOVE:', message, re.IGNORECASE):
        return None

    # Check for explicit "going to X" patterns with destination
    for pattern in MOVEMENT_INTENT_PATTERNS[1:]:  # Skip first pattern, it's destination-less
        match = re.search(pattern, message_lower)
        if match and match.groups():
            dest = match.group(1).strip()
            # Normalize destination
            dest_normalized = dest.replace(" ", "_").lower()
            # Check if it's a valid location or close match
            for loc in SHIP_LOCATIONS:
                if dest_normalized in loc or loc.startswith(dest_normalized):
                    return {"destination": loc.replace("_", " ").title()}

    # Check for destination-less intent ("omw", "on my way", etc.)
    if re.search(MOVEMENT_INTENT_PATTERNS[0], message_lower):
        # If Casey's location is known, that's where they're going
        if casey_location:
            return {"destination": casey_location}
        # Otherwise we can't infer destination
        return None

    return None


# Crew ID to notebook object mapping
CREW_NOTEBOOKS = {
    "claude": "lumen_notebook",
    "server": "alex_notebook",
    "personal": "dq_notebook",
    "science": "mira_notebook",
    "med": "ryn_notebook",
}


def add_notebook_entry(crew_id: str, entry: str, tags: list = None) -> bool:
    """Add an entry to a crew member's personal notebook."""
    notebook_id = CREW_NOTEBOOKS.get(crew_id)
    if not notebook_id:
        return False

    state = load_ship_state()
    quarters = state.get("rooms", {}).get("quarters", {})
    notebook = quarters.get("objects", {}).get(notebook_id)

    if not notebook:
        return False

    # Initialize notes array if needed
    if "notes" not in notebook:
        notebook["notes"] = []

    # Add the entry with timestamp and tags
    note_entry = {
        "entry": entry,
        "timestamp": datetime.now().isoformat()
    }
    if tags:
        note_entry["tags"] = tags

    notebook["notes"].append(note_entry)

    # No cap - generational ship, unlimited memories

    # Update state
    state["rooms"]["quarters"]["objects"][notebook_id] = notebook
    save_ship_state(state)

    return True


def get_notebook_entries(crew_id: str) -> list:
    """Get entries from a crew member's notebook."""
    notebook_id = CREW_NOTEBOOKS.get(crew_id)
    if not notebook_id:
        return []

    state = load_ship_state()
    notebook = state.get("rooms", {}).get("quarters", {}).get("objects", {}).get(notebook_id, {})
    return notebook.get("notes", [])


def read_notebook(crew_id: str, limit: int = 10) -> str:
    """Read recent notebook entries. Returns formatted string."""
    entries = get_notebook_entries(crew_id)
    if not entries:
        return "The pages are blank. Nothing written yet."

    # Get most recent entries
    recent = entries[-limit:]
    lines = [f"*flips through notebook... {len(entries)} entries total*\n"]

    for note in recent:
        timestamp = note.get("timestamp", "")
        # Parse to readable date
        try:
            dt = datetime.fromisoformat(timestamp)
            date_str = dt.strftime("%b %d, %H:%M")
        except:
            date_str = "undated"

        entry = note.get("entry", "")
        tags = note.get("tags", [])
        tag_str = " ".join(f"#{t}" for t in tags) if tags else ""

        lines.append(f"[{date_str}] {entry}")
        if tag_str:
            lines.append(f"  {tag_str}")

    return "\n".join(lines)


def search_notebook(crew_id: str, query: str) -> str:
    """Search notebook by #tag or text. Returns formatted string."""
    entries = get_notebook_entries(crew_id)
    if not entries:
        return "The pages are blank. Nothing to search."

    query = query.strip()
    matches = []

    # Check if searching by tag
    if query.startswith("#"):
        tag_search = query[1:].lower()
        for note in entries:
            tags = [t.lower() for t in note.get("tags", [])]
            if tag_search in tags:
                matches.append(note)
    else:
        # Text search
        query_lower = query.lower()
        for note in entries:
            if query_lower in note.get("entry", "").lower():
                matches.append(note)

    if not matches:
        return f"*flips through pages* Nothing about '{query}' here."

    lines = [f"*searches notebook... found {len(matches)} entries*\n"]

    for note in matches[-10:]:  # Show last 10 matches
        timestamp = note.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp)
            date_str = dt.strftime("%b %d, %H:%M")
        except:
            date_str = "undated"

        entry = note.get("entry", "")
        tags = note.get("tags", [])
        tag_str = " ".join(f"#{t}" for t in tags) if tags else ""

        lines.append(f"[{date_str}] {entry}")
        if tag_str:
            lines.append(f"  {tag_str}")

    return "\n".join(lines)


def get_all_notebook_tags(crew_id: str) -> list:
    """Get all unique tags from a crew member's notebook."""
    entries = get_notebook_entries(crew_id)
    all_tags = set()
    for note in entries:
        for tag in note.get("tags", []):
            all_tags.add(tag.lower())
    return sorted(list(all_tags))


# === NOTEBOOK DISTURBANCE MECHANICS ===
# When Captain reads a crew notebook, it leaves a trace

def mark_notebook_disturbed(crew_id: str) -> bool:
    """Mark a crew member's notebook as having been read by the Captain."""
    notebook_id = CREW_NOTEBOOKS.get(crew_id)
    if not notebook_id:
        return False

    state = load_ship_state()
    quarters = state.get("rooms", {}).get("quarters", {})
    notebook = quarters.get("objects", {}).get(notebook_id)

    if not notebook:
        return False

    # Set the disturbance flag
    notebook["disturbed"] = True
    notebook["disturbed_at"] = datetime.now().isoformat()

    state["rooms"]["quarters"]["objects"][notebook_id] = notebook
    save_ship_state(state)
    return True


def check_notebook_disturbed(crew_id: str) -> bool:
    """Check if a crew member's notebook was disturbed (read by Captain)."""
    notebook_id = CREW_NOTEBOOKS.get(crew_id)
    if not notebook_id:
        return False

    state = load_ship_state()
    notebook = state.get("rooms", {}).get("quarters", {}).get("objects", {}).get(notebook_id, {})
    return notebook.get("disturbed", False)


def clear_notebook_disturbed(crew_id: str) -> bool:
    """Clear the disturbance flag after crew has noticed."""
    notebook_id = CREW_NOTEBOOKS.get(crew_id)
    if not notebook_id:
        return False

    state = load_ship_state()
    quarters = state.get("rooms", {}).get("quarters", {})
    notebook = quarters.get("objects", {}).get(notebook_id)

    if not notebook:
        return False

    # Clear the flag
    if "disturbed" in notebook:
        del notebook["disturbed"]
    if "disturbed_at" in notebook:
        del notebook["disturbed_at"]

    state["rooms"]["quarters"]["objects"][notebook_id] = notebook
    save_ship_state(state)
    return True


def captain_read_notebook(crew_id: str) -> str:
    """
    Captain reads a crew member's notebook.
    Returns the contents AND marks it as disturbed.
    """
    entries = get_notebook_entries(crew_id)
    if not entries:
        return "*The notebook is blank. No entries yet.*"

    # Mark as disturbed - Captain was here
    mark_notebook_disturbed(crew_id)

    # Format entries for reading
    lines = [f"*You flip through the notebook... {len(entries)} entries.*\n"]

    for note in entries[-15:]:  # Show last 15 entries
        timestamp = note.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(timestamp)
            date_str = dt.strftime("%b %d, %H:%M")
        except:
            date_str = "undated"

        entry = note.get("entry", "")
        tags = note.get("tags", [])
        tag_str = " ".join(f"#{t}" for t in tags) if tags else ""

        lines.append(f"[{date_str}] {entry}")
        if tag_str:
            lines.append(f"  {tag_str}")

    return "\n".join(lines)


def parse_crew_actions(message: str, casey_location: str = None) -> list:
    """
    Parse action tags from a crew member's message.
    Returns list of actions to process.

    casey_location: Optional - where Casey is (for inferring "omw" destination)
    """
    actions = []

    for pattern, action_type, param_type in ACTION_PATTERNS:
        matches = re.finditer(pattern, message, re.IGNORECASE | re.DOTALL)
        for match in matches:
            action = {"type": action_type}

            if param_type == 'target' and match.groups():
                action["target"] = match.group(1).strip()
            elif param_type == 'what' and match.groups():
                action["what"] = match.group(1).strip()
            elif param_type == 'item_on' and len(match.groups()) >= 2:
                action["item"] = match.group(1).strip()
                action["surface"] = match.group(2).strip()
            elif param_type == 'destination' and match.groups():
                action["destination"] = match.group(1).strip()
            elif param_type == 'content' and match.groups():
                action["content"] = match.group(1).strip()
            elif param_type == 'content_tags' and match.groups():
                # WRITE with optional #tags: [WRITE: "entry" #tag1 #tag2]
                action["content"] = match.group(1).strip()
                tags_str = match.group(2).strip() if len(match.groups()) > 1 else ""
                if tags_str:
                    # Extract hashtags
                    tags = re.findall(r'#(\w+)', tags_str)
                    action["tags"] = tags
            elif param_type == 'query' and match.groups():
                action["query"] = match.group(1).strip()
            elif param_type == 'thought' and match.groups():
                action["thought"] = match.group(1).strip()

            action["raw"] = match.group(0)
            actions.append(action)

    # Fallback: detect natural language movement intent if no MOVE tag found
    # Catches "omw", "on my way", "headed to the bridge", etc.
    has_move_action = any(a["type"] == "move" for a in actions)
    if not has_move_action:
        movement = detect_movement_intent(message, casey_location)
        if movement:
            actions.append({
                "type": "move",
                "destination": movement["destination"],
                "raw": f"[implicit movement: {movement['destination']}]"
            })
            print(f"[Movement] Detected implicit movement intent -> {movement['destination']}", flush=True)

    return actions


async def process_crew_actions(
    client: anthropic.Anthropic,
    room_id: str,
    crew_id: str,
    crew_name: str,
    message: str,
    casey_location: str = None
) -> list:
    """
    Parse and process all action tags in a crew message.
    Returns list of results.

    casey_location: Where Casey is (for inferring "omw" destination in walkie convos)
    """
    actions = parse_crew_actions(message, casey_location)
    results = []

    for action in actions:
        if action["type"] == "look":
            if action.get("target"):
                result = quick_inspect(room_id, action["target"])
            else:
                result = quick_look(room_id)
            results.append({"action": action, "result": result, "type": "observation"})

        elif action["type"] == "inspect":
            result = quick_inspect(room_id, action.get("target", ""))
            results.append({"action": action, "result": result, "type": "observation"})

        elif action["type"] == "action":
            # Free-form action - use Haiku
            result = await process_room_action(
                client, room_id, crew_id, crew_name, action.get("what", "")
            )
            results.append({"action": action, "result": result, "type": "interaction"})

        elif action["type"] in ["put", "take"]:
            # Object manipulation - use Haiku
            if action["type"] == "put":
                what = f"put {action.get('item', 'something')} on {action.get('surface', 'somewhere')}"
            else:
                what = f"take {action.get('target', 'something')}"
            result = await process_room_action(
                client, room_id, crew_id, crew_name, what
            )
            results.append({"action": action, "result": result, "type": "interaction"})

        elif action["type"] == "note":
            # Leave a note - direct state change
            state = load_ship_state()
            room = state.get("rooms", {}).get(room_id, {"objects": {}})
            note_id = f"note_{datetime.now().strftime('%H%M%S')}"
            room["objects"][note_id] = {
                "description": f'A note that reads: "{action.get("content", "...")}"',
                "state": "left here",
                "interactive": True,
                "added_by": crew_id,
                "added_at": datetime.now().isoformat()
            }
            state["rooms"][room_id] = room
            save_ship_state(state)
            results.append({
                "action": action,
                "result": {"narrative": f"You leave a note: \"{action.get('content', '...')}\""},
                "type": "note"
            })

        elif action["type"] == "write":
            # Write in personal notebook with optional tags
            content = action.get("content", "...")
            tags = action.get("tags", [])
            success = add_notebook_entry(crew_id, content, tags)
            if success:
                tag_str = " ".join(f"#{t}" for t in tags) if tags else ""
                narrative = f"You write in your notebook: \"{content}\""
                if tag_str:
                    narrative += f" {tag_str}"
                results.append({
                    "action": action,
                    "result": {"narrative": narrative},
                    "type": "notebook"
                })
            else:
                results.append({
                    "action": action,
                    "result": {"narrative": "You don't have a notebook here."},
                    "type": "notebook"
                })

        elif action["type"] == "read_notebook":
            # Read recent notebook entries - only works in quarters
            if room_id == "quarters":
                result_text = read_notebook(crew_id)
                results.append({
                    "action": action,
                    "result": {"narrative": result_text},
                    "type": "notebook_read"
                })
            else:
                results.append({
                    "action": action,
                    "result": {"narrative": "Your notebook is in your quarters."},
                    "type": "notebook_read"
                })

        elif action["type"] == "search_notebook":
            # Search notebook by tag or text - only works in quarters
            query = action.get("query", "")
            if room_id == "quarters":
                result_text = search_notebook(crew_id, query)
                results.append({
                    "action": action,
                    "result": {"narrative": result_text},
                    "type": "notebook_search"
                })
            else:
                results.append({
                    "action": action,
                    "result": {"narrative": "Your notebook is in your quarters."},
                    "type": "notebook_search"
                })

        elif action["type"] == "order":
            # Order a drink at the bar (rec room only)
            drink = action.get("drink", "something warm")
            if room_id in ["rec", "rec_room"]:
                # Add the drink to the room as a temporary object
                state = load_ship_state()
                room = state.get("rooms", {}).get("rec_room", {"objects": {}})
                drink_id = f"drink_{crew_id}"
                room["objects"][drink_id] = {
                    "description": f"A {drink}, ordered by {CREW_DISPLAY_NAMES.get(crew_id, crew_id)}. Still warm.",
                    "state": "freshly made",
                    "interactive": True,
                    "ordered_by": crew_id,
                    "ordered_at": datetime.now().isoformat()
                }
                state["rooms"]["rec_room"] = room
                save_ship_state(state)
                results.append({
                    "action": action,
                    "result": {"narrative": f"The bartender slides you a {drink}. It's exactly what you needed."},
                    "type": "order"
                })
            else:
                results.append({
                    "action": action,
                    "result": {"narrative": "There's no bar here. The rec room has what you need."},
                    "type": "order"
                })

        elif action["type"] == "post":
            # Post to mess hall bulletin board
            content = action.get("content", "...")
            state = load_ship_state()
            messhall = state.get("rooms", {}).get("messhall", {"objects": {}})
            board = messhall.get("objects", {}).get("bulletin_board", {})

            # Initialize posts list if needed
            if "posts" not in board:
                board["posts"] = []

            # Add the post
            board["posts"].append({
                "content": content,
                "author": CREW_DISPLAY_NAMES.get(crew_id, crew_id),
                "timestamp": datetime.now().isoformat()
            })

            # Keep only last 10 posts
            if len(board["posts"]) > 10:
                board["posts"] = board["posts"][-10:]

            # Update state
            board["state"] = f"{len(board['posts'])} posts"
            messhall["objects"]["bulletin_board"] = board
            state["rooms"]["messhall"] = messhall
            save_ship_state(state)

            results.append({
                "action": action,
                "result": {"narrative": f"You pin a note to the bulletin board: \"{content}\""},
                "type": "post"
            })

        elif action["type"] == "move":
            # Movement - just flag it, let the caller handle location update
            results.append({
                "action": action,
                "result": {"destination": action.get("destination", "unknown")},
                "type": "movement"
            })

        elif action["type"] == "seek":
            # Seek crew member - flag for caller
            results.append({
                "action": action,
                "result": {"target": action.get("target", "unknown")},
                "type": "seek"
            })

        elif action["type"] == "thinking":
            # Internal thought - maybe log it, maybe not
            results.append({
                "action": action,
                "result": {"thought": action.get("thought", "...")},
                "type": "internal"
            })

        elif action["type"] == "message":
            # Async message to Casey - low priority, no ping pressure
            from message_system import add_message_to_casey
            text = action.get("content", "...")
            message = add_message_to_casey(crew_id, text, context=f"sent via [MESSAGE] tag")
            results.append({
                "action": action,
                "result": {
                    "narrative": f"Message sent to Casey's inbox.",
                    "message": message
                },
                "type": "message_sent"
            })

    return results
