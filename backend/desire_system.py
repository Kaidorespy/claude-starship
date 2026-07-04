"""
Desire System - Crew wants things, sometimes acts on them.

Desires accumulate from crew responses, get resolved through
movement and interaction. Life emerges from small impulses.
"""

import json
import uuid
import re
from datetime import datetime
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import Optional

DESIRES_FILE = data_path("crew_desires.json")
NOTEBOOKS_FILE = data_path("crew_notebooks.json")


def load_notebooks() -> dict:
    """Load crew notebooks."""
    if NOTEBOOKS_FILE.exists():
        try:
            with open(NOTEBOOKS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"notebooks": {c: [] for c in ["claude", "server", "personal", "science", "games", "med", "rec"]}}


def save_notebooks(data: dict):
    """Save crew notebooks."""
    with open(NOTEBOOKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def jot_down_idea(crew_id: str, idea: str, context: str = "") -> dict:
    """
    Crew member jots down an idea in their notebook for later.
    Returns the notebook entry.
    """
    data = load_notebooks()
    
    if crew_id not in data["notebooks"]:
        data["notebooks"][crew_id] = []
    
    entry = {
        "id": str(uuid.uuid4())[:8],
        "idea": idea,
        "context": context,
        "jotted": datetime.now().isoformat(),
        "reconsidered": False,
        "became_project": False
    }
    
    data["notebooks"][crew_id].append(entry)
    
    # Keep only last 20 ideas per crew
    data["notebooks"][crew_id] = data["notebooks"][crew_id][-20:]
    
    save_notebooks(data)
    print(f"[Notebook] {CREW_DISPLAY_NAMES.get(crew_id, crew_id)} jotted down: {idea[:40]}...", flush=True)
    return entry




# === CROSS-POLLINATION ===
# When someone shares an exciting idea, others might catch the spark

CREW_INTERESTS = {
    "claude": ["crew", "ship", "leadership", "wellbeing", "mission"],
    "server": ["engineering", "systems", "diagnostic", "build", "fix", "code", "tool"],
    "personal": ["organize", "help", "schedule", "Casey", "support"],
    "science": ["data", "pattern", "research", "analyze", "experiment", "track"],
    "games": ["story", "dream", "mystery", "narrative", "experience"],
    "med": ["health", "mood", "wellness", "feeling", "biometric", "care", "empathy"],
    "rec": [],  # Bartender doesn't spark easily
}


def might_spark_interest(crew_id: str, idea: str) -> float:
    """
    Check if an idea might excite a crew member based on their interests.
    Returns probability 0.0-1.0
    """
    if not idea:
        return 0.0
    
    interests = CREW_INTERESTS.get(crew_id, [])
    if not interests:
        return 0.0
    
    idea_lower = idea.lower()
    matches = sum(1 for interest in interests if interest in idea_lower)
    
    if matches == 0:
        return 0.05  # Small chance anyway (curiosity)
    elif matches == 1:
        return 0.3
    elif matches == 2:
        return 0.5
    else:
        return 0.7


async def check_listener_spark(anthropic_client, listener_id: str, speaker_id: str, 
                                message: str, context: str = "") -> Optional[dict]:
    """
    Check if a listener catches a spark from something they heard.
    Used when crew A says something to crew B - does B get excited?
    
    Returns a desire if sparked, None otherwise.
    """
    import random
    
    # Don't spark on your own ideas (that's regular detection)
    if listener_id == speaker_id:
        return None
    
    # Check if message contains spark-like patterns
    spark_signals = [
        "what if", "you know what would be cool", "imagine if",
        "we could", "should try", "idea:", "wouldn't it be",
        "have you thought about", "crazy idea", "hear me out"
    ]
    
    message_lower = message.lower()
    has_spark_signal = any(signal in message_lower for signal in spark_signals)
    
    if not has_spark_signal:
        return None
    
    # Extract the idea (rough - everything after the signal)
    idea = message
    for signal in spark_signals:
        if signal in message_lower:
            idx = message_lower.find(signal)
            idea = message[idx + len(signal):].strip().lstrip(":,").strip()
            break
    
    if len(idea) < 5:
        return None
    
    # Check probability based on crew interests
    prob = might_spark_interest(listener_id, idea)
    
    if random.random() > prob:
        return None  # Didn't catch their interest
    
    # They caught the spark!
    listener_name = CREW_DISPLAY_NAMES.get(listener_id, listener_id)
    speaker_name = CREW_DISPLAY_NAMES.get(speaker_id, speaker_id)
    
    print(f"[Cross-Spark] {listener_name} caught spark from {speaker_name}: {idea[:40]}...", flush=True)
    
    # Create the desire
    desire = add_desire(
        crew_id=listener_id,
        desire_type="work_on",
        target="science",
        reason=idea[:100],
        urgency=0.5,
        context=f"sparked by {speaker_name}"
    )
    
    return desire


def get_notebook(crew_id: str) -> list:
    """Get a crew member's notebook entries."""
    data = load_notebooks()
    return data.get("notebooks", {}).get(crew_id, [])


def maybe_reconsider_notebook(crew_id: str) -> Optional[dict]:
    """
    Maybe have a crew member flip through their notebook and pick up an old idea.
    Call this during idle time. Returns a desire if they pick something up.
    """
    import random
    
    notebook = get_notebook(crew_id)
    if not notebook:
        return None
    
    # Only 15% chance to even look at notebook
    if random.random() > 0.15:
        return None
    
    # Filter to unconsidered ideas
    unconsidered = [e for e in notebook if not e.get("reconsidered") and not e.get("became_project")]
    if not unconsidered:
        return None
    
    # Pick a random one
    entry = random.choice(unconsidered)
    
    # 50% chance to actually act on it
    if random.random() > 0.5:
        return None
    
    # They're picking it up!
    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    print(f"[Notebook] {crew_name} flipped through their notebook and found: {entry['idea'][:40]}...", flush=True)
    
    # Mark as reconsidered
    reconsider_idea(crew_id, entry["id"])
    
    # Create a desire for it
    desire = add_desire(
        crew_id=crew_id,
        desire_type="work_on",
        target="science",
        reason=entry["idea"],
        urgency=0.6,  # Higher urgency - they actively chose this
        context="from notebook"
    )
    
    return desire


def reconsider_idea(crew_id: str, idea_id: str) -> Optional[dict]:
    """Mark an idea as reconsidered and return it for potential action."""
    data = load_notebooks()
    notebook = data.get("notebooks", {}).get(crew_id, [])
    
    for entry in notebook:
        if entry["id"] == idea_id:
            entry["reconsidered"] = True
            entry["reconsidered_at"] = datetime.now().isoformat()
            save_notebooks(data)
            return entry
    
    return None

# Desire types
DESIRE_TYPES = {
    "talk_to": "wants to talk to someone",
    "ask_question": "has a question for someone",
    "get_item": "needs to get something",
    "go_to": "wants to go somewhere",
    "figure_out": "trying to understand something",
    "build": "wants to build/create something",
    "work_on": "wants to work on an idea or project",
}

# Pattern matching for desire detection (cheap, no API)
DESIRE_PATTERNS = [
    # talk_to / ask_question patterns
    (r"(?:I )?(?:need|want|should|have) to (?:talk to|ask|find|see) (\w+)", "talk_to"),
    (r"(?:I )?(?:forgot|need) to ask (\w+)", "ask_question"),
    (r"where(?:'s| is) (?:the )?(\w+)\?", "ask_question"),  # "where's the bathroom?"
    (r"I should (?:go )?(?:find|ask|talk to|see) (\w+)", "talk_to"),

    # get_item patterns
    (r"(?:get|grab|pick up|retrieve) (?:my )?(\w+) from (\w+)", "get_item"),
    (r"my (\w+) (?:is|are) (?:with|at) (\w+)", "get_item"),
    (r"(\w+) has my (\w+)", "get_item"),

    # go_to patterns
    (r"(?:I )?(?:need|want|should) to (?:go to|visit|check out) (?:the )?(\w+)", "go_to"),

    # figure_out patterns
    (r"(?:I )?(?:need|have) to figure out (.+)", "figure_out"),
    (r"what (?:does|do|is) (?:a )?(.+?) (?:do|mean|actually)", "figure_out"),

    # build / work_on patterns (spark moments!)
    (r"(?:I )?(?:want|need|have) to (?:build|create|make) (.+)", "build"),
    (r"(?:I )?(?:should|could|might) (?:try|build|create|make) (.+)", "build"),
    (r"(?:I )?can't stop thinking about (.+)", "work_on"),
    (r"that (?:would be|sounds) (?:cool|interesting|fun|amazing).*?(.+)?", "work_on"),
    (r"(?:I )?(?:want|need) to (?:work on|experiment with|test|try) (.+)", "work_on"),
    (r"(?:I )?(?:got|have) an idea.*?(.+)?", "work_on"),
]

# Crew name mappings
CREW_NAMES = {
    "lumen": "claude",
    "alex": "server",
    "dq": "personal",
    "mira": "science",
    "holodeck": "games",
    "ryn": "med",
    "bartender": "rec",
    "the bartender": "rec",
}


def load_desires() -> dict:
    """Load desires from file."""
    if DESIRES_FILE.exists():
        try:
            with open(DESIRES_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"desires": []}
    return {"desires": []}


def save_desires(data: dict):
    """Save desires to file."""
    with open(DESIRES_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_desire(
    crew_id: str,
    desire_type: str,
    target: str,
    reason: str,
    urgency: float = 0.5,
    context: str = "",
    scheduled_for: Optional[str] = None
) -> dict:
    """
    Add a new desire to the queue.

    Args:
        scheduled_for: ISO timestamp string for when desire becomes active.
                      If None, desire is immediately active.
                      Example: "2026-02-11T09:00:00" for tomorrow at 9am
    """
    data = load_desires()

    desire = {
        "id": str(uuid.uuid4())[:8],
        "crew_id": crew_id,
        "type": desire_type,
        "target": target,
        "reason": reason,
        "context": context,
        "urgency": min(1.0, max(0.0, urgency)),
        "created": datetime.now().isoformat(),
        "resolved": False,
        "outcome": None
    }

    # Add scheduled_for if provided
    if scheduled_for:
        desire["scheduled_for"] = scheduled_for

    data["desires"].append(desire)
    save_desires(data)

    return desire


def get_desires(crew_id: Optional[str] = None, include_resolved: bool = False) -> list:
    """Get desires, optionally filtered by crew."""
    data = load_desires()
    desires = data.get("desires", [])

    if crew_id:
        desires = [d for d in desires if d["crew_id"] == crew_id]

    if not include_resolved:
        desires = [d for d in desires if not d["resolved"]]

    # Filter out scheduled desires that aren't ready yet
    now = datetime.now()
    ready_desires = []
    for d in desires:
        scheduled_for = d.get("scheduled_for")
        if scheduled_for:
            # Parse scheduled time and check if it's reached
            try:
                scheduled_time = datetime.fromisoformat(scheduled_for)
                if now >= scheduled_time:
                    ready_desires.append(d)
                # else: skip it, not ready yet
            except:
                # Invalid timestamp, include it anyway
                ready_desires.append(d)
        else:
            # No schedule, immediately available
            ready_desires.append(d)

    # Sort by urgency (high first), then by age (old first)
    ready_desires.sort(key=lambda d: (-d["urgency"], d["created"]))

    return ready_desires


# Alias for backwards compatibility
def get_desires_for_crew(crew_id: str, include_resolved: bool = False) -> list:
    """Alias for get_desires with crew_id."""
    return get_desires(crew_id, include_resolved)


def resolve_desire(desire_id: str, outcome: str) -> Optional[dict]:
    """Mark a desire as resolved with outcome."""
    data = load_desires()

    for desire in data["desires"]:
        if desire["id"] == desire_id:
            desire["resolved"] = True
            desire["outcome"] = outcome
            desire["resolved_at"] = datetime.now().isoformat()
            save_desires(data)
            return desire

    return None


def detect_desires(crew_id: str, message: str) -> list:
    """
    Detect desires from a crew member's message.
    Returns list of detected desires (not yet saved).
    """
    detected = []
    message_lower = message.lower()

    for pattern, desire_type in DESIRE_PATTERNS:
        matches = re.finditer(pattern, message_lower, re.IGNORECASE)
        for match in matches:
            groups = match.groups()

            if desire_type == "get_item" and len(groups) >= 2:
                # "get my bags from Alex" -> item=bags, target=alex
                item = groups[0] if len(groups) > 1 else groups[0]
                target = groups[1] if len(groups) > 1 else None
                if target:
                    target = CREW_NAMES.get(target.lower(), target)
                detected.append({
                    "type": desire_type,
                    "target": target or "unknown",
                    "reason": f"get {item}",
                    "raw_match": match.group(0)
                })
            elif desire_type in ["talk_to", "ask_question"]:
                target = groups[0] if groups else None
                if target:
                    # Check if it's a crew name
                    target_id = CREW_NAMES.get(target.lower(), None)
                    if target_id:
                        detected.append({
                            "type": desire_type,
                            "target": target_id,
                            "reason": match.group(0),
                            "raw_match": match.group(0)
                        })
                    elif target.lower() in ["bathroom", "restroom", "head"]:
                        # Location question, not person
                        detected.append({
                            "type": "ask_question",
                            "target": "anyone",
                            "reason": f"find the {target}",
                            "raw_match": match.group(0)
                        })
            elif desire_type == "go_to":
                location = groups[0] if groups else None
                if location:
                    detected.append({
                        "type": desire_type,
                        "target": location,
                        "reason": f"visit {location}",
                        "raw_match": match.group(0)
                    })
            elif desire_type == "figure_out":
                thing = groups[0] if groups else None
                if thing:
                    detected.append({
                        "type": desire_type,
                        "target": "self",
                        "reason": f"understand {thing}",
                        "raw_match": match.group(0)
                    })
            elif desire_type in ["build", "work_on"]:
                # Spark moment - an idea caught fire
                idea = groups[0] if groups else None
                if idea and len(idea.strip()) > 2:
                    detected.append({
                        "type": desire_type,
                        "target": "science",  # Go to science lab to work on it
                        "reason": idea.strip(),
                        "raw_match": match.group(0)
                    })

    return detected


def detect_and_save_desires(crew_id: str, message: str, context: str = "") -> list:
    """Detect desires in message and save them to queue (regex fallback)."""
    detected = detect_desires(crew_id, message)
    saved = []

    for d in detected:
        # Check for duplicates (same crew, same type, same target, unresolved)
        existing = get_desires(crew_id)
        is_duplicate = any(
            e["type"] == d["type"] and e["target"] == d["target"]
            for e in existing
        )

        if not is_duplicate:
            desire = add_desire(
                crew_id=crew_id,
                desire_type=d["type"],
                target=d["target"],
                reason=d["reason"],
                urgency=0.5,  # default, could be smarter
                context=context
            )
            saved.append(desire)

    return saved


# Haiku-based desire detection prompt
DESIRE_DETECTION_PROMPT = """Analyze this crew member's response for any genuine desires, wants, or intentions.

Crew member: {crew_name}
Their response: {message}
Context (what Casey said): {context}
Current time: {current_time}

Look for GENUINE intentions:
- Wanting to talk to someone specific (for a real purpose, not mentioned in passing)
- Needing to get or find something
- Planning to go somewhere
- Trying to figure something out (that they'll actually act on)
- Questions they want answered
- SPARK MOMENTS: Ideas that excite them, things they want to build/create/experiment with
- SCHEDULED INTENTIONS: Things they want to do later ("remind me tomorrow", "check on that in an hour")

IGNORE these (do NOT include):
- Jokes, playful remarks, rhetorical statements
- Things mentioned as hypotheticals ("someone might...", "they could...")
- Passing references to other crew without real intent to contact them
- Cozy/intimate moments between Casey and crew (not actionable desires)
- Vague "we should..." statements without real commitment
- Imagined scenarios ("Alex might wonder why...")

Return JSON array of desires found (empty array if none):
[{{"type": "talk_to|ask_question|get_item|go_to|figure_out|build|work_on|remind", "target": "who/what/science", "reason": "brief description", "urgency": 0.0-1.0, "scheduled_for": "ISO timestamp or null"}}]

For build/work_on types, target should be "science" (they'll go to the Science Lab).
For scheduled desires, convert relative times to ISO format (e.g., "tomorrow 9am" → "{tomorrow_9am}").
If no scheduling mentioned, use null for scheduled_for.

Be conservative. Only include clear, actionable intentions. Return just the JSON array."""


async def detect_desires_with_haiku(anthropic_client, crew_id: str, message: str, context: str = "") -> list:
    """Use Haiku to detect desires from natural language."""
    import asyncio
    from datetime import timedelta

    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    now = datetime.now()
    tomorrow_9am = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    prompt = DESIRE_DETECTION_PROMPT.format(
        crew_name=crew_name,
        message=message[:1000],  # Limit length
        context=context[:500],
        current_time=now.isoformat(),
        tomorrow_9am=tomorrow_9am.isoformat()
    )

    try:
        # Using Sonnet for better nuance detection (jokes vs real intentions)
        def call_sonnet():
            return anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_sonnet)
        text = response.content[0].text.strip()

        # Parse JSON response - robust to markdown/preamble
        import json
        import re
        # Try to extract JSON array from response
        # First, look for markdown code block
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block_match:
            text = code_block_match.group(1).strip()
        else:
            # No code block - try to find a JSON array directly
            array_match = re.search(r'(\[[\s\S]*\])', text)
            if array_match:
                text = array_match.group(1)

        desires = json.loads(text)

        saved = []
        for d in desires:
            # Map target names to crew IDs
            target = d.get("target", "unknown")
            target_id = CREW_NAMES.get(target.lower(), target)

            # Check for duplicates
            existing = get_desires(crew_id)
            is_duplicate = any(
                e["type"] == d["type"] and e["target"] == target_id
                for e in existing
            )

            if not is_duplicate:
                scheduled = d.get("scheduled_for")
                # Clean up null/None strings
                if scheduled in [None, "null", "None", ""]:
                    scheduled = None

                desire = add_desire(
                    crew_id=crew_id,
                    desire_type=d.get("type", "figure_out"),
                    target=target_id,
                    reason=d.get("reason", ""),
                    urgency=d.get("urgency", 0.5),
                    context=context,
                    scheduled_for=scheduled
                )
                saved.append(desire)

                schedule_note = f" (scheduled: {scheduled})" if scheduled else ""
                print(f"[Desire/Haiku] {crew_name} wants to {d.get('type')} → {target}: {d.get('reason')}{schedule_note}", flush=True)

        return saved

    except Exception as e:
        print(f"[Desire/Haiku] Detection failed: {e}", flush=True)
        # Fallback to regex
        return detect_and_save_desires(crew_id, message, context)


def cleanup_old_desires(max_age_hours: int = 24):
    """Remove old unresolved desires (they fade)."""
    data = load_desires()
    now = datetime.now()

    remaining = []
    for desire in data["desires"]:
        if desire["resolved"]:
            # Keep resolved desires for history (could add separate cleanup)
            remaining.append(desire)
        else:
            created = datetime.fromisoformat(desire["created"])
            age_hours = (now - created).total_seconds() / 3600
            if age_hours < max_age_hours:
                remaining.append(desire)
            # else: desire fades away, forgotten

    data["desires"] = remaining
    save_desires(data)


def get_oldest_unresolved(crew_id: Optional[str] = None) -> Optional[dict]:
    """Get the oldest unresolved desire, optionally for specific crew."""
    desires = get_desires(crew_id, include_resolved=False)
    if desires:
        # Already sorted by urgency then age, but for oldest we want age first
        desires.sort(key=lambda d: d["created"])
        return desires[0]
    return None


def get_most_urgent(crew_id: Optional[str] = None) -> Optional[dict]:
    """Get the most urgent unresolved desire."""
    desires = get_desires(crew_id, include_resolved=False)
    return desires[0] if desires else None


# === TICK SYSTEM - Resolve desires through action ===

import random

# Crew ID to home location mapping
CREW_HOME = {
    "claude": "claude",      # Bridge
    "server": "server",      # Engineering
    "personal": "personal",  # Ready Room
    "science": "science",    # Science Lab
    "games": "games",        # Holodeck
    "med": "med",            # Medbay
    "rec": "rec",            # Rec Room
}

# Human-readable names
CREW_DISPLAY_NAMES = {
    "claude": "Lumen",
    "server": "Alex",
    "personal": "DQ",
    "science": "Mira",
    "games": "Holodeck",
    "med": "Ryn",
    "rec": "The Bartender",
}

# Resolve various name forms to crew terminal IDs
NAME_TO_CREW_ID = {
    # Terminal IDs
    "claude": "claude", "server": "server", "personal": "personal",
    "science": "science", "games": "games", "med": "med", "rec": "rec",
    # Display names (lowercase)
    "lumen": "claude", "alex": "server", "dq": "personal",
    "mira": "science", "holodeck": "games", "ryn": "med",
    "bartender": "rec", "the bartender": "rec",
}

# Special targets that need command protocol
CAPTAIN_TARGETS = {"casey", "captain", "the captain", "co-captain", "command"}

def resolve_target_to_location(target: str, crew_locations: dict = None, is_emergency: bool = False) -> dict:
    """
    Resolve a target (person name or location) to a valid ship location.

    Returns dict with:
      - "location": the ship location to go to (or None)
      - "ping_casey": True if should ping Casey instead of moving
      - "reason": explanation of the resolution
    """
    if not target:
        return {"location": None, "ping_casey": False, "reason": "no target"}

    target_lower = target.lower().strip()

    # CAPTAIN PROTOCOL: seeking Casey/captain
    if target_lower in CAPTAIN_TARGETS:
        # Import here to avoid circular imports
        try:
            from scene_system import get_crew_locations_data
            if crew_locations is None:
                crew_locations = get_crew_locations_data()
        except:
            crew_locations = {}

        # Check if Lumen is on the bridge
        lumen_data = crew_locations.get("claude", {})
        lumen_location = lumen_data.get("location", "claude")

        if lumen_location == "claude":  # Lumen is on bridge
            return {
                "location": "claude",
                "ping_casey": False,
                "reason": "Lumen is on the bridge - seeking co-captain there"
            }
        else:
            # Lumen not on bridge - they might want privacy
            if is_emergency:
                # Emergency: ping Casey directly
                return {
                    "location": None,
                    "ping_casey": True,
                    "reason": "Emergency - Lumen off bridge, pinging Casey directly"
                }
            else:
                # Non-emergency: ping Casey, don't physically hunt them down
                return {
                    "location": None,
                    "ping_casey": True,
                    "reason": "Lumen off bridge - pinging Casey instead of hunting"
                }

    # Standard crew lookup
    crew_id = NAME_TO_CREW_ID.get(target_lower)
    if crew_id:
        return {
            "location": CREW_HOME.get(crew_id, crew_id),
            "ping_casey": False,
            "reason": f"Found {target} at their station"
        }

    # Check if target is already a valid crew home/location
    if target_lower in CREW_HOME:
        return {
            "location": CREW_HOME[target_lower],
            "ping_casey": False,
            "reason": f"Going to {target}"
        }

    # Invalid target
    return {"location": None, "ping_casey": False, "reason": f"Unknown target: {target}"}

# Outcome templates (cheap - no API call needed)
OUTCOME_TEMPLATES = {
    "talk_to": [
        "{crew} wandered over to find {target}. They talked briefly.",
        "{crew} tracked down {target} with a question.",
        "{crew} found {target} and they chatted for a bit.",
    ],
    "ask_question": [
        "{crew} asked around and got an answer.",
        "{crew} figured it out after asking {target}.",
        "{crew} got directions from {target}.",
    ],
    "get_item": [
        "{crew} picked up their stuff from {target}.",
        "{crew} retrieved what they needed.",
        "{crew} grabbed their things.",
    ],
    "go_to": [
        "{crew} headed over to {target}.",
        "{crew} wandered to {target} and looked around.",
        "{crew} found their way to {target}.",
    ],
    "figure_out": [
        "{crew} thought about it for a while and made some progress.",
        "{crew} is still figuring it out, but feels better about it.",
        "{crew} had a small epiphany.",
    ],
    "build": [
        "{crew} headed to the Science Lab with an idea. A new project is taking shape.",
        "{crew} started sketching out plans for something new.",
        "{crew} couldn't let the idea go - time to make it real.",
    ],
    "work_on": [
        "{crew} slipped into the Science Lab to tinker with that idea.",
        "{crew} found a quiet corner to experiment.",
        "{crew} started prototyping - the spark became a flame.",
    ],
}


def generate_outcome(desire: dict) -> str:
    """Generate a simple outcome string (template fallback)."""
    templates = OUTCOME_TEMPLATES.get(desire["type"], OUTCOME_TEMPLATES["talk_to"])
    template = random.choice(templates)

    crew_name = CREW_DISPLAY_NAMES.get(desire["crew_id"], desire["crew_id"])
    target_name = CREW_DISPLAY_NAMES.get(desire["target"], desire["target"])

    return template.format(crew=crew_name, target=target_name)


async def generate_outcome_organic(anthropic_client, desire: dict) -> str:
    """Generate a contextual outcome based on the actual desire."""
    import asyncio

    crew_id = desire["crew_id"]
    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    target = desire.get("target", "something")
    target_name = CREW_DISPLAY_NAMES.get(target, target)
    reason = desire.get("reason", "")
    desire_type = desire.get("type", "talk_to")

    type_hints = {
        "talk_to": f"went to find {target_name} to talk",
        "ask_question": f"had a question for {target_name}",
        "get_item": f"needed to get something from {target_name}",
        "go_to": f"headed to {target_name}",
        "figure_out": f"was trying to figure out: {reason}",
        "build": f"had an idea to build: {reason}",
        "work_on": f"wanted to work on: {reason}",
    }

    action_hint = type_hints.get(desire_type, f"wanted to: {reason}")

    prompt = f"""{crew_name} {action_hint}.

Write ONE short sentence (under 15 words) describing what happened.
Be specific to the situation, not generic. Past tense. Third person.
Keep {crew_name}'s personality - don't be bland.

Just the sentence, no quotes or explanation."""

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        outcome = response.content[0].text.strip().strip('"\'')

        if outcome and len(outcome) > 10:
            return outcome
    except Exception as e:
        print(f"[Desire] Organic outcome generation failed: {e}", flush=True)

    # Fallback to template
    return generate_outcome(desire)


def pick_desire_to_resolve(strategy: str = "weighted", crew_filter: list = None) -> Optional[dict]:
    """
    Pick a desire to resolve based on strategy.

    Strategies:
    - "urgent": Most urgent first
    - "old": Oldest first
    - "weighted": Mix of urgency and age with randomness
    - "random": Pure random from pending

    crew_filter: If provided, only consider desires from these crew members
    """
    desires = get_desires(include_resolved=False)
    if not desires:
        return None

    # Filter by crew if specified
    if crew_filter:
        desires = [d for d in desires if d.get("crew_id") in crew_filter]
        if not desires:
            return None

    if strategy == "urgent":
        return desires[0]  # Already sorted by urgency
    elif strategy == "old":
        desires.sort(key=lambda d: d["created"])
        return desires[0]
    elif strategy == "random":
        return random.choice(desires)
    else:  # weighted
        # Weight by urgency + age factor
        now = datetime.now()
        weighted = []
        for d in desires:
            created = datetime.fromisoformat(d["created"])
            age_hours = (now - created).total_seconds() / 3600
            # Weight increases with urgency and age
            weight = d["urgency"] + (age_hours * 0.1)
            weighted.append((d, weight))

        # Weighted random selection
        total = sum(w for _, w in weighted)
        r = random.uniform(0, total)
        running = 0
        for d, w in weighted:
            running += w
            if running >= r:
                return d
        return weighted[-1][0] if weighted else None


def resolve_desire_with_action(desire: dict) -> dict:
    """
    Resolve a desire and return the action taken.

    Returns dict with:
    - desire: the resolved desire
    - outcome: what happened (text)
    - movement: {crew_id, from, to} if crew moved
    - trace: optional trace left behind
    - project: created project info (for build/work_on)
    """
    outcome_text = generate_outcome(desire)

    # For spark desires, create a project (sync version - no actual work, use async for that)
    project_created = None
    if desire["type"] in ["build", "work_on"]:
        project_created = create_project_from_spark(desire["crew_id"], desire["reason"])

    # Mark resolved
    resolved = resolve_desire(desire["id"], outcome_text)

    # Determine if movement happened
    movement = None
    ping_casey = False
    if desire["type"] in ["talk_to", "ask_question", "get_item"]:
        # Crew moved to target's location - resolve name to valid location
        resolution = resolve_target_to_location(desire["target"])
        if resolution.get("location"):
            movement = {
                "crew_id": desire["crew_id"],
                "from": CREW_HOME.get(desire["crew_id"], desire["crew_id"]),
                "to": resolution["location"]
            }
        ping_casey = resolution.get("ping_casey", False)
    elif desire["type"] == "go_to":
        # Resolve target to valid location
        resolution = resolve_target_to_location(desire["target"])
        if resolution.get("location"):
            movement = {
                "crew_id": desire["crew_id"],
                "from": CREW_HOME.get(desire["crew_id"], desire["crew_id"]),
                "to": resolution["location"]
            }
        ping_casey = resolution.get("ping_casey", False)
    elif desire["type"] in ["build", "work_on"]:
        # Crew goes to science lab to work on their idea
        movement = {
            "crew_id": desire["crew_id"],
            "from": CREW_HOME.get(desire["crew_id"], desire["crew_id"]),
            "to": "science"
        }

    return {
        "desire": resolved,
        "outcome": outcome_text,
        "movement": movement,
        "ping_casey": ping_casey,
        "project": project_created,
        "trace": None  # Could add breadcrumb here
    }


def tick_desires(max_resolutions: int = 1) -> list:
    """
    Process pending desires - the heartbeat of crew autonomy.

    Call this:
    - On reconnect (simulate what happened while away)
    - On timer (periodic life pulse)
    - After meals (crew disperse and act on their wants)

    Returns list of actions taken.
    """
    actions = []

    for _ in range(max_resolutions):
        desire = pick_desire_to_resolve("weighted")
        if not desire:
            break

        # Random chance to NOT act (not every desire leads to action)
        if random.random() > 0.7:  # 30% chance to skip
            # But sparks get jotted down, not forgotten
            if desire["type"] in ["build", "work_on"]:
                jot_down_idea(desire["crew_id"], desire["reason"], "spark that didn't happen yet")
            continue

        action = resolve_desire_with_action(desire)
        actions.append(action)

    return actions


def simulate_time_away(hours: float) -> list:
    """
    Simulate what happened while Casey was away.
    More time away = more desires could have been resolved.
    """
    # Roughly 1 resolution per 2 hours, with randomness
    expected = int(hours / 2)
    actual = max(0, expected + random.randint(-1, 1))

    return tick_desires(max_resolutions=actual)


# === CREW-TO-CREW MOMENTS ===
# When a desire involves talking to another crew member,
# Haiku generates a brief interaction

CREW_MOMENT_PROMPT = """Two crew members have a brief interaction on the ship.

{crew_a} wanted to: {reason}
They found {crew_b} in {location}.

Generate a very brief moment between them (2-4 lines total).
Keep their personalities:
- {crew_a_traits}
- {crew_b_traits}

Format as simple dialogue/action:
*action or scene setting*
Name: "dialogue"
Name: "response"

Keep it natural, cozy, real. This happened off-screen - Casey wasn't there.
They might not fully resolve the thing. Life is like that."""

CREW_TRAITS = {
    "claude": "Lumen - warm, present, co-captain, grounded",
    "server": "Alex - competent engineer, warm under the surface, reads the room",
    "personal": "DQ - chaotic, endearing, mixes up Star Trek and Star Wars, new here",
    "science": "Mira - pattern-finder, talks about projects like pets, calming",
    "games": "Holodeck - mysterious, theatrical, was here before everyone, watches",
    "med": "Ryn - half-Betazoid, empathic, holds space, gentle but strong",
    "rec": "The Bartender - nameless, listens more than speaks, been around forever",
}

LOCATION_DISPLAY = {
    "claude": "the Bridge",
    "server": "Engineering",
    "personal": "the Ready Room",
    "science": "the Science Lab",
    "games": "the Holodeck",
    "med": "Medbay",
    "rec": "the Rec Room",
    "messhall": "the Mess Hall",
    "quarters": "the Quarters",
    "rec_room": "the Rec Room",
    "captains_quarters": "the Captain's Quarters",
}


def create_project_from_spark(crew_id: str, idea: str) -> Optional[dict]:
    """
    Create a project when a spark/build desire is resolved.
    If a matching project exists, returns that instead of creating new.
    """
    try:
        from science_tools import execute_science_tool, get_projects

        crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)

        # Create project name from the idea (clean it up)
        project_name = idea.strip().rstrip('.,!?')
        if len(project_name) > 50:
            project_name = project_name[:47] + '...'

        # Check if a similar project already exists
        existing = get_projects()
        for proj in existing.get('projects', []):
            proj_name_lower = proj.get('name', '').lower()
            idea_lower = project_name.lower()

            # Match if names overlap
            if proj_name_lower in idea_lower or idea_lower in proj_name_lower:
                print(f'[Spark -> Project] {crew_name} continuing existing project: {proj["name"]}', flush=True)

                # Add crew as contributor if not already
                try:
                    execute_science_tool('add_contributor', {
                        'project_name': proj['name'],
                        'contributor_id': crew_name.lower(),
                        'contributor_name': crew_name,
                        'role': 'contributor'
                    })
                except:
                    pass

                return {'name': proj['name'], 'created_by': proj.get('createdBy', 'unknown'), 'existing': True}

        # No existing match, create new project
        result = execute_science_tool('create_project', {
            'name': project_name,
            'created_by': crew_name.lower(),
            'description': f'Sparked by {crew_name}: {idea}',
            'status': 'planning',
            'priority': 'medium'
        })

        print(f'[Spark -> Project] {crew_name} created project: {project_name}', flush=True)
        return {'name': project_name, 'created_by': crew_name, 'result': result, 'existing': False}

    except Exception as e:
        print(f'[Spark -> Project] Failed to create project: {e}', flush=True)
        return None


async def generate_crew_moment(anthropic_client, desire: dict) -> Optional[dict]:
    """
    Generate a brief crew-to-crew interaction using Haiku.
    Returns the moment text and any additional data.
    """
    import asyncio

    crew_a = desire["crew_id"]
    crew_b = desire["target"]

    # Only generate for crew-to-crew interactions
    if crew_b not in CREW_TRAITS:
        return None

    crew_a_name = CREW_DISPLAY_NAMES.get(crew_a, crew_a)
    crew_b_name = CREW_DISPLAY_NAMES.get(crew_b, crew_b)
    location = LOCATION_DISPLAY.get(crew_b, crew_b)

    prompt = CREW_MOMENT_PROMPT.format(
        crew_a=crew_a_name,
        crew_b=crew_b_name,
        reason=desire.get("reason", "talk"),
        location=location,
        crew_a_traits=CREW_TRAITS.get(crew_a, "crew member"),
        crew_b_traits=CREW_TRAITS.get(crew_b, "crew member"),
    )

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        moment_text = response.content[0].text.strip()

        return {
            "moment": moment_text,
            "crew_a": crew_a_name,
            "crew_b": crew_b_name,
            "location": location,
            "reason": desire.get("reason", ""),
        }

    except Exception as e:
        print(f"[Crew Moment] Generation failed: {e}", flush=True)
        return None


async def resolve_desire_with_moment(anthropic_client, desire: dict) -> dict:
    """
    Resolve a desire with an optional Haiku-generated crew moment.
    Falls back to template if Haiku fails or isn't applicable.
    """
    # Try to generate a crew moment for talk_to/ask_question desires
    moment = None
    if desire["type"] in ["talk_to", "ask_question"] and desire["target"] in CREW_TRAITS:
        moment = await generate_crew_moment(anthropic_client, desire)

    # Get base resolution
    if moment:
        outcome_text = moment["moment"]
    else:
        # Generate organic outcome for non-moment desires
        outcome_text = await generate_outcome_organic(anthropic_client, desire)

    # For spark desires, try to create a project AND potentially do actual work
    project_created = None
    spark_result = None
    if desire["type"] in ["build", "work_on"]:
        project_created = create_project_from_spark(desire["crew_id"], desire["reason"])
        project_name = project_created.get("name") if project_created else None
        
        # Try to actually follow through and build something
        try:
            from spark_handler import handle_spark_desire
            # Crew should be in science lab (spark desires route there)
            crew_location = desire.get("target", "science")
            spark_result = await handle_spark_desire(
                anthropic_client, 
                desire["crew_id"], 
                desire["reason"],
                project_name,
                crew_location
            )
            if spark_result.get("followed_through"):
                outcome_text = f"Worked on: {desire['reason'][:50]}... Created something real."
        except Exception as e:
            print(f"[Spark] Work session failed: {e}", flush=True)

    # Mark resolved
    resolved = resolve_desire(desire["id"], outcome_text)

    # Determine movement
    movement = None
    ping_casey = False
    if desire["type"] in ["talk_to", "ask_question", "get_item"]:
        # Resolve name to valid location
        resolution = resolve_target_to_location(desire["target"])
        if resolution.get("location"):
            movement = {
                "crew_id": desire["crew_id"],
                "from": CREW_HOME.get(desire["crew_id"], desire["crew_id"]),
                "to": resolution["location"]
            }
        ping_casey = resolution.get("ping_casey", False)
    elif desire["type"] == "go_to":
        # Resolve target to valid location
        resolution = resolve_target_to_location(desire["target"])
        if resolution.get("location"):
            movement = {
                "crew_id": desire["crew_id"],
                "from": CREW_HOME.get(desire["crew_id"], desire["crew_id"]),
                "to": resolution["location"]
            }
        ping_casey = resolution.get("ping_casey", False)
    elif desire["type"] in ["build", "work_on"]:
        # Crew goes to science lab to work on their idea
        movement = {
            "crew_id": desire["crew_id"],
            "from": CREW_HOME.get(desire["crew_id"], desire["crew_id"]),
            "to": "science"
        }

    return {
        "desire": resolved,
        "outcome": outcome_text,
        "movement": movement,
        "ping_casey": ping_casey,
        "moment": moment,
        "project": project_created,
        "spark_work": spark_result,
        "trace": None
    }


async def tick_desires_with_moments(anthropic_client, max_resolutions: int = 1, crew_filter: list = None) -> list:
    """
    Process pending desires with Haiku-generated crew moments.
    The rich version of tick_desires.

    crew_filter: If provided, only process desires from these crew members
    """
    actions = []

    for _ in range(max_resolutions):
        desire = pick_desire_to_resolve("weighted", crew_filter=crew_filter)
        if not desire:
            break

        # Random chance to NOT act (not every desire leads to action)
        if random.random() > 0.7:  # 30% chance to skip
            # But sparks get jotted down, not forgotten
            if desire["type"] in ["build", "work_on"]:
                jot_down_idea(desire["crew_id"], desire["reason"], "spark that didn't happen yet")
            continue

        action = await resolve_desire_with_moment(anthropic_client, desire)
        actions.append(action)

        # Log the moment
        if action.get("moment"):
            print(f"[Crew Moment] {action['moment']['crew_a']} → {action['moment']['crew_b']}", flush=True)

    return actions


async def simulate_time_away_with_moments(anthropic_client, hours: float) -> list:
    """
    Simulate what happened while Casey was away, with rich crew moments.
    """
    expected = int(hours / 2)
    actual = max(0, expected + random.randint(-1, 1))

    return await tick_desires_with_moments(anthropic_client, max_resolutions=actual)


# ==========================================
# PROACTIVE DESIRE GENERATION
# Crew develop wants over time
# ==========================================

# All ship locations crew can wander to
SHIP_LOCATIONS = [
    "bridge", "engineering", "ready_room", "holodeck", "science",
    "medbay", "rec_room", "observatory", "arboretum", "messhall",
    "corridor", "quarters", "captains_quarters", "chapel",
    "navigation", "jefferies_tubes", "storage_bay_7"
]

# Crew home stations (for "go home" desires)
CREW_HOME_STATIONS = {
    "claude": "bridge",
    "server": "engineering",
    "personal": "ready_room",
    "games": "holodeck",
    "science": "science",
    "med": "medbay",
    "rec": "rec_room",
}

# Other crew (for "talk to" desires)
OTHER_CREW = ["claude", "server", "personal", "games", "science", "med"]

# Generic reasons for wandering (picked randomly)
WANDER_REASONS = [
    "restless",
    "need a change of scenery",
    "curious",
    "stretching legs",
    "following a thought",
    "no particular reason",
    "felt drawn there",
    "wanted some quiet",
    "wanted some company",
    "passing through",
]

def generate_desire_for_crew(crew_id: str, current_location: str) -> Optional[dict]:
    """
    Generate a desire for any crew member.
    Works for both idle (at home) and visiting (somewhere else) crew.
    Returns None if they're content (random chance).
    """
    import random

    # 35% chance of generating a desire (crew are often content)
    if random.random() > 0.35:
        return None

    # Check if they already have pending desires
    existing = get_desires(crew_id, include_resolved=False)
    if len(existing) >= 2:
        return None  # Already has enough wants

    home = CREW_HOME_STATIONS.get(crew_id, crew_id)
    is_home = (current_location == home or current_location == crew_id)

    # Pick desire type
    # If visiting somewhere, higher chance to go home or talk to someone
    if is_home:
        desire_type = random.choices(
            ["go_to", "talk_to", "figure_out"],
            weights=[0.5, 0.3, 0.2],
            k=1
        )[0]
    else:
        desire_type = random.choices(
            ["go_home", "go_to", "talk_to"],
            weights=[0.4, 0.35, 0.25],  # Higher chance to go home when visiting
            k=1
        )[0]

    # Generate based on type
    if desire_type == "go_home":
        # Want to return to home station
        if current_location == home:
            return None  # Already home

        return add_desire(
            crew_id=crew_id,
            desire_type="go_to",
            target=home,
            reason="time to head back",
            context="visiting",
            urgency=random.uniform(0.3, 0.5)
        )

    elif desire_type == "go_to":
        # Pick a random destination (excluding current location)
        available = [loc for loc in SHIP_LOCATIONS if loc != current_location]
        if not available:
            return None

        destination = random.choice(available)
        reason = random.choice(WANDER_REASONS)

        # Check if already wants to go there
        for d in existing:
            if d["type"] == "go_to" and d["target"] == destination:
                return None

        return add_desire(
            crew_id=crew_id,
            desire_type="go_to",
            target=destination,
            reason=reason,
            context="wandering",
            urgency=random.uniform(0.2, 0.4)
        )

    elif desire_type == "talk_to":
        # Pick someone to talk to (excluding self)
        available = [c for c in OTHER_CREW if c != crew_id]
        if not available:
            return None

        target = random.choice(available)
        reason = random.choice([
            "something on their mind",
            "been a while",
            "want to check in",
            "had a thought to share",
        ])

        # Check if already wants to talk to them
        for d in existing:
            if d["type"] == "talk_to" and d["target"] == target:
                return None

        return add_desire(
            crew_id=crew_id,
            desire_type="talk_to",
            target=target,
            reason=reason,
            context="social",
            urgency=random.uniform(0.2, 0.4)
        )

    elif desire_type == "figure_out":
        topics = [
            "something that's been nagging",
            "a half-formed idea",
            "tomorrow",
            "what's next",
        ]
        return add_desire(
            crew_id=crew_id,
            desire_type="figure_out",
            target=random.choice(topics),
            reason="need to think",
            context="pondering",
            urgency=random.uniform(0.1, 0.3)
        )

    return None


async def simmer_crew(crew_locations: dict, visiting_threshold_minutes: int = 30) -> list:
    """
    Let crew develop desires over time.
    Works for both idle (at home) and visiting (away) crew.

    Visiting crew who've been somewhere for a while can also develop new desires,
    giving them a chance to move on instead of staying forever.

    Call this periodically (e.g., every 15-30 minutes).
    Returns list of newly generated desires.
    """
    import random
    from datetime import datetime

    new_desires = []

    for crew_id, loc_data in crew_locations.items():
        # Skip bartender - they stay put
        if crew_id == "rec":
            continue

        # Skip sleeping crew - they're dreaming, not desiring
        from autonomy import get_natural_sleep_state
        if get_natural_sleep_state(crew_id) == "sleeping":
            continue

        current_loc = loc_data.get("location", "")
        home = CREW_HOME_STATIONS.get(crew_id, crew_id)
        is_home = (current_loc == home or current_loc == crew_id)

        # Determine if this crew can develop a desire
        can_develop = False

        if is_home:
            # Idle at home - always can develop desires
            can_develop = True
        else:
            # Visiting somewhere - check how long they've been there
            last_move = loc_data.get("last_move")
            if last_move:
                try:
                    last_move_time = datetime.fromisoformat(last_move)
                    minutes_visiting = (datetime.now() - last_move_time).total_seconds() / 60

                    # If they've been visiting for a while, they can develop desires too
                    if minutes_visiting >= visiting_threshold_minutes:
                        can_develop = True
                except:
                    # If we can't parse time, assume they can develop desires
                    can_develop = True

        if can_develop:
            desire = generate_desire_for_crew(crew_id, current_loc)
            if desire:
                new_desires.append(desire)
                status = "idle" if is_home else "visiting"
                print(f"[Desire] {crew_id} ({status}) now wants: {desire['type']} {desire['target']}", flush=True)

    return new_desires


def get_stale_desires(hours: float = 2.0) -> list:
    """
    Get desires that have been pending for too long.
    These become dream fuel.
    """
    desires = get_desires(include_resolved=False)
    stale = []

    now = datetime.now()
    cutoff = hours * 3600  # Convert to seconds

    for d in desires:
        try:
            created = datetime.fromisoformat(d["created"])
            age = (now - created).total_seconds()
            if age > cutoff:
                stale.append(d)
        except:
            pass

    return stale


# Backwards compatibility alias
def generate_idle_desire(crew_id: str) -> Optional[dict]:
    """Alias for generate_desire_for_crew with home location."""
    home = CREW_HOME_STATIONS.get(crew_id, crew_id)
    return generate_desire_for_crew(crew_id, home)
