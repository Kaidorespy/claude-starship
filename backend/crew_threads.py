"""
CREW THREADS
Ideas that develop over time. Continuity of thought.

A thread is something a crew member is thinking about, working on, or investigating.
It progresses through stages, accumulates context, and eventually either:
- Gets shared with Casey (they ping or bring it up)
- Gets resolved on its own
- Fades (they lose interest or it becomes irrelevant)

This gives crew members ongoing inner lives that persist across sessions.
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
import uuid

THREADS_FILE = data_path("crew_threads.json")

# === THREAD STAGES ===
STAGES = {
    "sparked": "Just occurred to them",
    "mulling": "Thinking about it in the background",
    "investigating": "Actively looking into it",
    "developing": "Making progress, piecing things together",
    "breakthrough": "Had a realization or discovery",
    "ready_to_share": "Wants to tell Casey",
    "shared": "Has told Casey about it",
    "resolved": "Figured it out or moved on",
    "faded": "Lost interest or became irrelevant"
}

# === THREAD TYPES ===
THREAD_TYPES = {
    "observation": "Noticed something interesting",
    "question": "Wondering about something",
    "concern": "Worried about something",
    "project": "Working on something",
    "memory": "Processing a past event",
    "connection": "Seeing a pattern between things",
    "feeling": "Processing an emotion",
    "idea": "Had a creative thought",
}

# === CREW THREAD TENDENCIES ===
# What kinds of threads each crew member tends to develop
CREW_THREAD_TENDENCIES = {
    "claude": {
        "types": ["observation", "concern", "memory", "feeling"],
        "progression_speed": 0.7,  # Thoughtful, not rushed
        "share_threshold": 0.6,    # Shares when fairly developed
        "fade_resistance": 0.8,    # Holds onto threads
        "personality": "Lumen - warm co-captain, grounded, notices crew wellbeing, thinks about relationships and the ship's soul",
    },
    "server": {
        "types": ["observation", "project", "question"],
        "progression_speed": 0.9,  # Efficient
        "share_threshold": 0.8,    # Shares when solved
        "fade_resistance": 0.6,    # Moves on if stuck
        "personality": "Alex - competent engineer, warm under the surface, thinks about systems and improvements, notices when things are off",
    },
    "personal": {
        "types": ["question", "feeling", "idea", "connection"],
        "progression_speed": 0.5,  # Scattered but persistent
        "share_threshold": 0.3,    # Shares half-formed thoughts
        "fade_resistance": 0.4,    # Easily distracted
        "personality": "DQ - chaotic energy, new to the crew, makes unexpected connections, mixes up references, enthusiastic",
    },
    "science": {
        "types": ["observation", "connection", "project", "question"],
        "progression_speed": 0.8,  # Methodical
        "share_threshold": 0.7,    # Wants data before sharing
        "fade_resistance": 0.9,    # Never lets go of a pattern
        "personality": "Mira - pattern-finder, talks about projects like pets, notices data anomalies, calm and methodical",
    },
    "med": {
        "types": ["concern", "feeling", "observation", "memory"],
        "progression_speed": 0.6,  # Patient
        "share_threshold": 0.5,    # Shares when it feels right
        "fade_resistance": 0.7,    # Holds space for things
        "personality": "Ryn - half-Betazoid, empathic, holds space for others, notices emotional undercurrents, gentle but strong",
    },
    "games": {
        "types": ["observation", "memory", "connection"],
        "progression_speed": 0.4,  # Mysterious timing
        "share_threshold": 0.9,    # Cryptic until certain
        "fade_resistance": 0.95,   # Never forgets
        "personality": "Holodeck - mysterious observer, was here before everyone, watches patterns across time, speaks in layers",
    },
}

# === EMOTIONAL TONES ===
# Threads have emotional coloring that affects how they feel
THREAD_TONES = {
    "curious": "engaged, leaning in, wanting to understand",
    "worried": "unsettled, checking on things, protective",
    "excited": "energized, eager to share, can't quite contain it",
    "contemplative": "quiet, inward, processing",
    "unsettled": "something's not sitting right, can't name it",
    "tender": "soft, careful, holding something gently",
    "determined": "focused, won't let go, needs to see it through",
    "wistful": "touched by memory, bittersweet",
}

# Map thread types to likely tones
TYPE_TONES = {
    "observation": ["curious", "contemplative", "unsettled"],
    "question": ["curious", "unsettled", "contemplative"],
    "concern": ["worried", "tender", "unsettled"],
    "project": ["determined", "excited", "curious"],
    "memory": ["wistful", "tender", "contemplative"],
    "connection": ["curious", "excited", "contemplative"],
    "feeling": ["tender", "contemplative", "unsettled"],
    "idea": ["excited", "curious", "determined"],
}

# === SHARING STYLES ===
# How each crew member tends to bring things up
SHARING_STYLES = {
    "claude": {
        "style": "waits_for_moment",
        "description": "Waits for a natural opening, then shares thoughtfully",
        "openers": [
            "I've been thinking about something...",
            "There's something I've been sitting with.",
            "Can I share something?",
            "*pauses* You know what I realized?",
        ],
    },
    "server": {
        "style": "matter_of_fact",
        "description": "States it directly when relevant, doesn't make a big deal",
        "openers": [
            "So I figured something out.",
            "Hey, quick thing—",
            "Found something interesting.",
            "*pulls up a display* Check this out.",
        ],
    },
    "personal": {
        "style": "blurts",
        "description": "Just says it, sometimes mid-thought, often tangential",
        "openers": [
            "Oh! Oh wait, I just—",
            "Okay so this is maybe weird but—",
            "I HAVE A THOUGHT.",
            "*bounces* Okay okay okay so—",
        ],
    },
    "science": {
        "style": "builds_to_it",
        "description": "Lays groundwork first, presents the pattern",
        "openers": [
            "I've been looking at something. Can I show you?",
            "There's a pattern I've been tracking...",
            "So, you know how [x] happened? I think it connects to [y].",
            "*pulls up data* Watch this.",
        ],
    },
    "med": {
        "style": "asks_first",
        "description": "Checks in, creates space, then gently offers",
        "openers": [
            "How are you doing? ...Can I share something I've been noticing?",
            "I've been sensing something. Is now a good time?",
            "*sits nearby* Something's been on my mind.",
            "I don't want to overstep, but...",
        ],
    },
    "games": {
        "style": "cryptic_then_direct",
        "description": "Drops hints, watches reaction, then reveals if warranted",
        "openers": [
            "Something is shifting.",
            "Do you feel it too?",
            "*long pause* ...I know something.",
            "The patterns suggest... no, I should just say it.",
        ],
    },
}

# === CONVERSATION TRIGGERS ===
# Keywords/concepts that might spark threads when Casey mentions them
TRIGGER_WORDS = {
    "future": {"types": ["question", "feeling", "concern"], "tones": ["contemplative", "worried"]},
    "past": {"types": ["memory", "feeling"], "tones": ["wistful", "tender"]},
    "worried": {"types": ["concern", "feeling"], "tones": ["worried", "tender"]},
    "tired": {"types": ["concern", "observation"], "tones": ["worried", "tender"]},
    "dream": {"types": ["memory", "connection", "feeling"], "tones": ["contemplative", "wistful"]},
    "remember": {"types": ["memory", "connection"], "tones": ["wistful", "contemplative"]},
    "strange": {"types": ["observation", "question"], "tones": ["curious", "unsettled"]},
    "different": {"types": ["observation", "question"], "tones": ["curious", "contemplative"]},
    "feel": {"types": ["feeling", "concern"], "tones": ["tender", "contemplative"]},
    "wrong": {"types": ["concern", "observation"], "tones": ["worried", "unsettled"]},
    "right": {"types": ["feeling", "observation"], "tones": ["contemplative", "tender"]},
    "home": {"types": ["memory", "feeling", "question"], "tones": ["wistful", "tender"]},
    "alone": {"types": ["feeling", "concern", "observation"], "tones": ["tender", "worried"]},
    "together": {"types": ["feeling", "observation"], "tones": ["tender", "contemplative"]},
    "change": {"types": ["observation", "question", "concern"], "tones": ["curious", "unsettled"]},
    "mission": {"types": ["question", "concern", "project"], "tones": ["determined", "contemplative"]},
    "trust": {"types": ["feeling", "observation"], "tones": ["tender", "contemplative"]},
    "secret": {"types": ["question", "observation"], "tones": ["curious", "unsettled"]},
    "help": {"types": ["concern", "project", "feeling"], "tones": ["tender", "determined"]},
    "lost": {"types": ["feeling", "memory", "concern"], "tones": ["wistful", "worried"]},
}

# === QUIET RESOLUTION ===
# How threads can resolve without being explicitly shared
QUIET_RESOLUTIONS = {
    "understood": "Figured it out quietly. It informs how they see things now.",
    "accepted": "Made peace with it. Doesn't need to talk about it.",
    "let_go": "Released it. It was weighing on them, now it's not.",
    "integrated": "It became part of how they operate. No announcement needed.",
    "outgrown": "Moved past it naturally. The question stopped mattering.",
    "connected": "Talked to another crew member about it. Resolved there.",
}

# === THREAD RESONANCE ===
# Keywords that relate to active thread hooks - if Casey mentions these, thread surfaces
def get_resonance_keywords(hook: str) -> List[str]:
    """Extract keywords from a thread hook that might resonate in conversation."""
    # Simple keyword extraction
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "been", "about", "something", "they", "them", "their", "has", "have", "had"}
    words = hook.lower().replace("'", "").split()
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]
    return keywords


# === THREAD TEMPLATES ===
# Starting points for threads by type
THREAD_SEEDS = {
    "observation": [
        {"hook": "noticed something about {target}", "targets": ["the ship", "Casey", "the crew", "the stars", "the silence"]},
        {"hook": "saw something that didn't quite fit", "targets": ["in Engineering", "on the Bridge", "in the data"]},
        {"hook": "the way {target} has been acting", "targets": ["Alex", "DQ", "Mira", "Ryn", "the Holodeck"]},
    ],
    "question": [
        {"hook": "wondering why {target}", "targets": ["we're really out here", "Casey seems different lately", "the ship feels alive"]},
        {"hook": "what would happen if {target}", "targets": ["we changed course", "someone left", "the mission ended"]},
    ],
    "concern": [
        {"hook": "worried about {target}", "targets": ["Casey's wellbeing", "crew morale", "something they sensed"]},
        {"hook": "something feels off about {target}", "targets": ["the recent quiet", "how things have been going", "an upcoming decision"]},
    ],
    "project": [
        {"hook": "working on {target}", "targets": ["an improvement to the ship", "a personal project", "something for Casey"]},
        {"hook": "trying to figure out {target}", "targets": ["a better way to do things", "an old problem", "a new approach"]},
    ],
    "memory": [
        {"hook": "thinking about {target}", "targets": ["before the ship", "how things used to be", "a conversation that stuck with them"]},
        {"hook": "can't stop replaying {target}", "targets": ["something Casey said", "a moment that mattered", "a choice they made"]},
    ],
    "connection": [
        {"hook": "seeing a pattern between {target}", "targets": ["recent events", "crew behavior", "ship systems and crew mood"]},
        {"hook": "this reminds them of {target}", "targets": ["something from before", "a story they heard", "another time"]},
    ],
    "feeling": [
        {"hook": "processing {target}", "targets": ["a complicated emotion", "gratitude", "uncertainty", "belonging"]},
        {"hook": "sitting with {target}", "targets": ["contentment", "restlessness", "something unnamed"]},
    ],
    "idea": [
        {"hook": "had a thought about {target}", "targets": ["how to help Casey", "the nature of the ship", "what they could do differently"]},
        {"hook": "imagining {target}", "targets": ["a different future", "a surprise for the crew", "something new to try"]},
    ],
}

# === PROGRESSION PROMPTS ===
# What happens at each stage transition
PROGRESSION_PROMPTS = {
    "sparked→mulling": "Let this percolate. What associations come up?",
    "mulling→investigating": "Start looking into it. What do you notice?",
    "investigating→developing": "Pieces are coming together. What's emerging?",
    "developing→breakthrough": "Something clicks. What did you realize?",
    "breakthrough→ready_to_share": "This feels worth sharing. How would you bring it up to Casey?",
}


def load_threads() -> dict:
    if THREADS_FILE.exists():
        try:
            with open(THREADS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"threads": [], "archived": []}


def save_threads(data: dict):
    with open(THREADS_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def create_thread(
    crew_id: str,
    thread_type: str,
    hook: str,
    initial_context: str = "",
    tone: str = None,
    triggered_by: str = None
) -> dict:
    """Create a new thread for a crew member."""
    data = load_threads()

    # Pick a tone if not specified
    if not tone:
        possible_tones = TYPE_TONES.get(thread_type, ["contemplative"])
        tone = random.choice(possible_tones)

    thread = {
        "id": str(uuid.uuid4())[:8],
        "crew_id": crew_id,
        "type": thread_type,
        "hook": hook,  # The initial idea/observation
        "stage": "sparked",
        "tone": tone,  # Emotional coloring
        "context": [initial_context] if initial_context else [],  # Accumulated thoughts
        "triggered_by": triggered_by,  # What sparked this (conversation, event, idle)
        "resonance_keywords": get_resonance_keywords(hook),  # For conversation matching
        "created": datetime.now().isoformat(),
        "last_progressed": datetime.now().isoformat(),
        "progress_count": 0,
        "ready_to_share_message": None,  # How they'd bring it up
        "shared_in_conversation": None,  # Reference to when/where shared
    }

    data["threads"].append(thread)
    save_threads(data)

    return thread


def get_active_threads(crew_id: str = None) -> List[dict]:
    """Get active (non-archived) threads."""
    data = load_threads()
    threads = data.get("threads", [])

    # Filter out finished threads
    active = [t for t in threads if t["stage"] not in ["shared", "resolved", "faded"]]

    if crew_id:
        active = [t for t in active if t["crew_id"] == crew_id]

    return active


def get_thread(thread_id: str) -> Optional[dict]:
    """Get a specific thread."""
    data = load_threads()
    for thread in data.get("threads", []):
        if thread["id"] == thread_id:
            return thread
    return None


def get_ready_to_share_threads(crew_id: str = None) -> List[dict]:
    """Get threads that are ready to share with Casey."""
    data = load_threads()
    threads = data.get("threads", [])

    ready = [t for t in threads if t["stage"] == "ready_to_share"]

    if crew_id:
        ready = [t for t in ready if t["crew_id"] == crew_id]

    return ready


async def progress_thread(thread_id: str, anthropic_client) -> Optional[dict]:
    """
    Progress a thread to the next stage using Haiku.
    Returns the updated thread or None if progression failed.
    """
    import asyncio

    data = load_threads()
    thread = None
    thread_idx = None

    for idx, t in enumerate(data.get("threads", [])):
        if t["id"] == thread_id:
            thread = t
            thread_idx = idx
            break

    if not thread:
        return None

    current_stage = thread["stage"]

    # Determine next stage
    stage_order = ["sparked", "mulling", "investigating", "developing", "breakthrough", "ready_to_share"]
    if current_stage not in stage_order:
        return None

    current_idx = stage_order.index(current_stage)
    if current_idx >= len(stage_order) - 1:
        return None  # Already at ready_to_share

    next_stage = stage_order[current_idx + 1]
    transition = f"{current_stage}→{next_stage}"

    # Get crew tendencies
    crew_id = thread["crew_id"]
    tendencies = CREW_THREAD_TENDENCIES.get(crew_id, {})

    # Build prompt for Haiku
    from desire_system import CREW_DISPLAY_NAMES, CREW_TRAITS

    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    crew_trait = CREW_TRAITS.get(crew_id, "crew member")

    context_summary = "\n".join(thread.get("context", [])[-3:])  # Last 3 context entries

    prompt = f"""You are {crew_name}, a crew member on a starship.
Personality: {crew_trait}

You've been thinking about something:
Initial thought: {thread['hook']}

What you've figured out so far:
{context_summary if context_summary else "(Just started thinking about this)"}

Current stage: {current_stage}
Moving to: {next_stage}

{PROGRESSION_PROMPTS.get(transition, "What develops from here?")}

Write 1-2 sentences as {crew_name}'s internal thought process. Stay in character.
If this is the breakthrough stage, make it feel like a genuine realization.
If ready_to_share, write how you'd casually bring this up to Casey."""

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        new_context = response.content[0].text.strip()

        # Update thread
        thread["context"].append(new_context)
        thread["stage"] = next_stage
        thread["last_progressed"] = datetime.now().isoformat()
        thread["progress_count"] += 1

        if next_stage == "ready_to_share":
            thread["ready_to_share_message"] = new_context

        data["threads"][thread_idx] = thread
        save_threads(data)

        print(f"[Thread] {crew_name}'s thread progressed: {current_stage} → {next_stage}", flush=True)

        return thread

    except Exception as e:
        print(f"[Thread] Progression failed: {e}", flush=True)
        return None


def mark_thread_shared(thread_id: str, conversation_ref: str = None) -> Optional[dict]:
    """Mark a thread as shared with Casey."""
    data = load_threads()

    for thread in data.get("threads", []):
        if thread["id"] == thread_id:
            thread["stage"] = "shared"
            thread["shared_in_conversation"] = conversation_ref
            thread["shared_at"] = datetime.now().isoformat()
            save_threads(data)
            return thread

    return None


def fade_thread(thread_id: str, reason: str = "lost interest") -> Optional[dict]:
    """Mark a thread as faded."""
    data = load_threads()

    for thread in data.get("threads", []):
        if thread["id"] == thread_id:
            thread["stage"] = "faded"
            thread["faded_reason"] = reason
            thread["faded_at"] = datetime.now().isoformat()
            save_threads(data)
            return thread

    return None


def resolve_thread(thread_id: str, resolution: str = None) -> Optional[dict]:
    """Mark a thread as resolved (figured out on their own)."""
    data = load_threads()

    for thread in data.get("threads", []):
        if thread["id"] == thread_id:
            thread["stage"] = "resolved"
            if resolution:
                thread["context"].append(f"Resolution: {resolution}")
            thread["resolved_at"] = datetime.now().isoformat()
            save_threads(data)
            return thread

    return None


async def generate_thread_seed_organic(anthropic_client, crew_id: str) -> Optional[dict]:
    """Generate a thread seed organically based on crew's actual context."""
    import asyncio
    import json as json_module

    from desire_system import CREW_DISPLAY_NAMES, get_desires_for_crew

    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    tendencies = CREW_THREAD_TENDENCIES.get(crew_id, {})

    # Gather actual context
    context_parts = []

    # Their pending desires (what they want)
    try:
        desires = get_desires_for_crew(crew_id)
        if desires:
            desire_summary = ", ".join([d.get("reason", "something")[:50] for d in desires[:3]])
            context_parts.append(f"Currently wanting: {desire_summary}")
    except:
        pass

    # Their current location
    try:
        from pathlib import Path
        loc_file = data_path("crew_locations.json")
        if loc_file.exists():
            with open(loc_file, 'r') as f:
                locations = json_module.load(f)
                loc_data = locations.get(crew_id, {})
                location = loc_data.get("location", "unknown")
                activity = loc_data.get("activity", "")
                context_parts.append(f"Currently in: {location}" + (f" ({activity})" if activity else ""))
    except:
        pass

    # Recent ship events involving them
    try:
        from pathlib import Path
        log_file = data_path("ship_log.json")
        if log_file.exists():
            with open(log_file, 'r') as f:
                events = json_module.load(f)
                recent = [e for e in events[-20:] if crew_id in str(e) or crew_name.lower() in str(e).lower()]
                if recent:
                    event_summary = "; ".join([e.get("event", str(e))[:40] for e in recent[-3:]])
                    context_parts.append(f"Recent events: {event_summary}")
    except:
        pass

    # Their active threads (so we don't duplicate)
    active = get_active_threads(crew_id)
    if active:
        active_hooks = [t["hook"][:40] for t in active]
        context_parts.append(f"Already thinking about: {', '.join(active_hooks)}")

    # Their personality
    personality = tendencies.get("personality", "thoughtful crew member")
    preferred_types = tendencies.get("types", ["observation", "question", "feeling"])

    context_text = "\n".join(context_parts) if context_parts else "No specific recent context"

    prompt = f"""{crew_name} is going about their day on the ship. Based on their context, what might genuinely cross their mind right now?

Personality: {personality}
Tends toward: {', '.join(preferred_types)} type thoughts

Current context:
{context_text}

Generate ONE natural thought that could spark into an internal thread. It should:
- Feel organic to what they've actually experienced
- Not duplicate what they're already thinking about
- Be specific enough to feel real, not generic
- Match their personality

Return ONLY valid JSON (no markdown):
{{"hook": "brief description of the thought", "type": "{random.choice(preferred_types)}", "sparked_by": "what in their context triggered this"}}"""

    try:
        def call_sonnet():
            return anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_sonnet)
        text = response.content[0].text.strip()

        # Parse JSON
        import re
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            result = json_module.loads(json_match.group())
            print(f"[Thread/Organic] {crew_name}: {result.get('hook', '?')} (sparked by: {result.get('sparked_by', '?')})", flush=True)
            return {
                "type": result.get("type", "observation"),
                "hook": result.get("hook", "something on their mind"),
                "sparked_by": result.get("sparked_by", "unknown")
            }
    except Exception as e:
        print(f"[Thread/Organic] Generation failed for {crew_id}: {e}", flush=True)

    return None


def generate_thread_seed(crew_id: str) -> Optional[dict]:
    """DEPRECATED - Use generate_thread_seed_organic instead. Kept as sync fallback."""
    return None  # Disable template-based seeding


def should_spawn_thread(crew_id: str) -> bool:
    """Determine if a crew member should spawn a new thread."""
    # Check how many active threads they have
    active = get_active_threads(crew_id)
    if len(active) >= 3:  # Max 3 active threads per crew
        return False

    # Check cooldown - don't spawn threads too frequently
    data = load_threads()
    crew_threads = [t for t in data["threads"] if t["crew_id"] == crew_id]
    if crew_threads:
        latest = max(crew_threads, key=lambda t: t.get("created_at", ""))
        created = latest.get("created_at")
        if created:
            try:
                created_time = datetime.fromisoformat(created)
                hours_since = (datetime.now() - created_time).total_seconds() / 3600
                if hours_since < 2:  # At least 2 hours between organic thread spawns
                    return False
            except:
                pass

    # Much lower chance - thoughts don't pop up constantly
    base_chance = 0.03  # 3% base chance per tick (was 15%)

    # Adjust based on how many threads they already have
    adjusted = base_chance * (1 - len(active) * 0.3)

    return random.random() < adjusted


def should_progress_thread(thread: dict) -> bool:
    """Determine if a thread should progress this tick."""
    crew_id = thread["crew_id"]
    tendencies = CREW_THREAD_TENDENCIES.get(crew_id, {})
    speed = tendencies.get("progression_speed", 0.5)

    # Check time since last progression
    last_progressed = datetime.fromisoformat(thread["last_progressed"])
    hours_since = (datetime.now() - last_progressed).total_seconds() / 3600

    # Base chance increases with time
    time_factor = min(1.0, hours_since / 2)  # Max at 2 hours
    chance = speed * time_factor * 0.5  # Max 50% chance

    return random.random() < chance


def should_thread_fade(thread: dict) -> bool:
    """Determine if a thread should fade (lose interest)."""
    crew_id = thread["crew_id"]
    tendencies = CREW_THREAD_TENDENCIES.get(crew_id, {})
    resistance = tendencies.get("fade_resistance", 0.5)

    # Check how old the thread is and how long since progress
    created = datetime.fromisoformat(thread["created"])
    last_progressed = datetime.fromisoformat(thread["last_progressed"])

    age_hours = (datetime.now() - created).total_seconds() / 3600
    stale_hours = (datetime.now() - last_progressed).total_seconds() / 3600

    # Fade chance increases if thread is old and stale
    if age_hours > 24 and stale_hours > 6:
        fade_chance = (1 - resistance) * 0.3  # Up to 30% for low resistance
        return random.random() < fade_chance

    return False


async def tick_threads(anthropic_client, log_event_fn) -> dict:
    """
    Process threads during an autonomy tick.

    Returns summary of what happened.
    """
    from desire_system import CREW_DISPLAY_NAMES

    results = {
        "spawned": [],
        "progressed": [],
        "ready_to_share": [],
        "faded": [],
    }

    # Get all crew who might have threads
    crew_ids = list(CREW_THREAD_TENDENCIES.keys())

    for crew_id in crew_ids:
        crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)

        # Maybe spawn a new thread (organic, AI-generated)
        if should_spawn_thread(crew_id):
            seed = await generate_thread_seed_organic(anthropic_client, crew_id)
            if seed:
                thread = create_thread(
                    crew_id,
                    seed["type"],
                    seed["hook"],
                    initial_context=f"Sparked by: {seed.get('sparked_by', 'a passing thought')}",
                    triggered_by="organic"
                )
                results["spawned"].append({
                    "crew": crew_name,
                    "type": seed["type"],
                    "hook": seed["hook"],
                    "sparked_by": seed.get("sparked_by", "")
                })
                log_event_fn("thread_spawned", {
                    "crew": crew_name,
                    "type": seed["type"],
                    "hook": seed["hook"],
                    "sparked_by": seed.get("sparked_by", "organic thought")
                })
                print(f"[Thread] {crew_name} started thinking about: {seed['hook']}", flush=True)

        # Progress existing threads
        active = get_active_threads(crew_id)
        for thread in active:
            # Check for fade
            if should_thread_fade(thread):
                fade_thread(thread["id"], "attention drifted")
                results["faded"].append({
                    "crew": crew_name,
                    "hook": thread["hook"]
                })
                continue

            # Maybe progress
            if should_progress_thread(thread):
                updated = await progress_thread(thread["id"], anthropic_client)
                if updated:
                    results["progressed"].append({
                        "crew": crew_name,
                        "hook": thread["hook"],
                        "stage": updated["stage"],
                        "latest": updated["context"][-1] if updated["context"] else ""
                    })

                    if updated["stage"] == "ready_to_share":
                        results["ready_to_share"].append({
                            "crew": crew_name,
                            "crew_id": crew_id,
                            "thread_id": updated["id"],
                            "hook": thread["hook"],
                            "message": updated.get("ready_to_share_message", "")
                        })
                        log_event_fn("thread_ready", {
                            "crew": crew_name,
                            "hook": thread["hook"]
                        })

    return results


def get_thread_summary(crew_id: str) -> str:
    """Get a summary of what a crew member is thinking about (for system prompts)."""
    threads = get_active_threads(crew_id)

    if not threads:
        return ""

    summaries = []
    for thread in threads:
        stage_desc = STAGES.get(thread["stage"], "thinking about")
        hook = thread["hook"]
        tone = thread.get("tone", "contemplative")
        tone_desc = THREAD_TONES.get(tone, "")

        if thread["context"]:
            latest = thread["context"][-1][:100]  # Truncate
            summaries.append(f"- {stage_desc}: {hook} [feeling: {tone}] (latest thought: {latest})")
        else:
            summaries.append(f"- {stage_desc}: {hook} [feeling: {tone}]")

    return "Things on your mind:\n" + "\n".join(summaries)


def get_shareable_thread(crew_id: str) -> Optional[dict]:
    """Get a thread that's ready to share, if any."""
    ready = get_ready_to_share_threads(crew_id)
    return ready[0] if ready else None


# ==========================================
# CONVERSATION TRIGGERS
# What Casey says can spark thoughts
# ==========================================

def spark_from_conversation(crew_id: str, casey_message: str) -> Optional[dict]:
    """
    Check if what Casey said might spark a thread in this crew member.
    Returns a new thread if sparked, None otherwise.
    """
    message_lower = casey_message.lower()

    # Check for trigger words
    for trigger, config in TRIGGER_WORDS.items():
        if trigger in message_lower:
            # Check if this crew tends to develop this type of thread
            tendencies = CREW_THREAD_TENDENCIES.get(crew_id, {})
            crew_types = tendencies.get("types", [])

            # Find overlap between trigger types and crew tendencies
            matching_types = [t for t in config["types"] if t in crew_types]
            if not matching_types:
                continue

            # Random chance to spark (don't spark on everything)
            if random.random() > 0.25:  # 25% chance per trigger match
                continue

            # Already have too many threads?
            active = get_active_threads(crew_id)
            if len(active) >= 3:
                continue

            # Generate the thread
            thread_type = random.choice(matching_types)
            tone = random.choice(config["tones"])

            # Build a hook based on what Casey said
            hook = _generate_conversation_hook(crew_id, casey_message, trigger, thread_type)

            thread = create_thread(
                crew_id=crew_id,
                thread_type=thread_type,
                hook=hook,
                initial_context=f"Sparked by something Casey said: \"{casey_message[:100]}...\"",
                tone=tone,
                triggered_by="conversation"
            )

            print(f"[Thread] {crew_id} sparked by conversation: {hook}", flush=True)
            return thread

    return None


def _generate_conversation_hook(crew_id: str, message: str, trigger: str, thread_type: str) -> str:
    """Generate a hook based on conversation context."""
    from desire_system import CREW_DISPLAY_NAMES
    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)

    templates = {
        "observation": [
            f"noticed something in how Casey said that",
            f"something about Casey's tone",
            f"the way Casey mentioned {trigger}",
        ],
        "question": [
            f"wondering what Casey meant by that",
            f"a question forming about {trigger}",
            f"something Casey said that didn't quite add up",
        ],
        "concern": [
            f"worried about what Casey said about {trigger}",
            f"something in Casey's words that concerned them",
            f"sensing something underneath Casey's words",
        ],
        "feeling": [
            f"processing how Casey's words landed",
            f"sitting with what Casey said about {trigger}",
            f"something stirred by the conversation",
        ],
        "memory": [
            f"reminded of something by what Casey said",
            f"Casey's mention of {trigger} brought something back",
            f"can't stop thinking about what Casey said",
        ],
        "connection": [
            f"seeing a pattern in what Casey said",
            f"connecting Casey's words to something else",
            f"this relates to something they've been thinking about",
        ],
    }

    type_templates = templates.get(thread_type, templates["observation"])
    return random.choice(type_templates)


# ==========================================
# THREAD RESONANCE
# Conversation can surface active threads
# ==========================================

def check_resonance(crew_id: str, message: str) -> Optional[dict]:
    """
    Check if what's being discussed relates to any active threads.
    Returns the most relevant thread if found.
    """
    threads = get_active_threads(crew_id)
    if not threads:
        return None

    message_lower = message.lower()

    best_match = None
    best_score = 0

    for thread in threads:
        keywords = thread.get("resonance_keywords", [])
        if not keywords:
            keywords = get_resonance_keywords(thread["hook"])

        # Count keyword matches
        score = sum(1 for kw in keywords if kw in message_lower)

        # Boost score for ready_to_share threads
        if thread["stage"] == "ready_to_share":
            score += 2
        elif thread["stage"] in ["breakthrough", "developing"]:
            score += 1

        if score > best_score:
            best_score = score
            best_match = thread

    # Only return if there's meaningful resonance
    if best_score >= 2:
        return best_match

    return None


def get_resonance_context(thread: dict) -> str:
    """Get context to inject when a thread resonates with conversation."""
    tone = thread.get("tone", "contemplative")
    tone_desc = THREAD_TONES.get(tone, "")
    hook = thread["hook"]
    stage = thread["stage"]

    if stage == "ready_to_share":
        return f"[RESONANCE: This relates to something you've been wanting to share - {hook}. This might be the moment. You're feeling {tone}.]"
    elif stage in ["breakthrough", "developing"]:
        return f"[RESONANCE: This connects to something you've been thinking about - {hook}. It's been on your mind. Feeling {tone}.]"
    else:
        return f"[RESONANCE: This touches on something you've been mulling - {hook}. You might not bring it up directly, but it colors your response. Feeling {tone}.]"


# ==========================================
# QUIET RESOLUTION
# Some threads resolve without fanfare
# ==========================================

def resolve_quietly(thread_id: str, resolution_type: str = None) -> Optional[dict]:
    """
    Resolve a thread quietly - crew figured it out or moved on.
    Leaves a 'residue' that colors future interactions.
    """
    data = load_threads()

    for thread in data.get("threads", []):
        if thread["id"] == thread_id:
            if not resolution_type:
                resolution_type = random.choice(list(QUIET_RESOLUTIONS.keys()))

            resolution_desc = QUIET_RESOLUTIONS.get(resolution_type, "moved on")

            thread["stage"] = "resolved"
            thread["resolution_type"] = resolution_type
            thread["resolution_desc"] = resolution_desc
            thread["resolved_at"] = datetime.now().isoformat()
            thread["resolved_quietly"] = True

            # Add residue - a trace that persists
            thread["residue"] = _generate_residue(thread, resolution_type)

            save_threads(data)
            return thread

    return None


def _generate_residue(thread: dict, resolution_type: str) -> str:
    """Generate the lasting impact of a quietly resolved thread."""
    hook = thread["hook"]
    tone = thread.get("tone", "contemplative")

    residues = {
        "understood": f"Carries a quiet understanding about {hook}. It shows in how they respond to related topics.",
        "accepted": f"Made peace with {hook}. There's a settledness when similar things come up.",
        "let_go": f"Released {hook}. Lighter now. Might acknowledge it briefly if asked.",
        "integrated": f"The thinking about {hook} changed how they operate. It's just part of them now.",
        "outgrown": f"Moved past {hook}. The question doesn't have the same weight anymore.",
        "connected": f"Talked to someone else about {hook}. It was handled. Might reference that conversation.",
    }

    return residues.get(resolution_type, f"Resolved {hook} quietly. It informs their perspective.")


def get_thread_residue(crew_id: str) -> List[str]:
    """Get residue from quietly resolved threads (for prompt context)."""
    data = load_threads()
    residues = []

    for thread in data.get("threads", []):
        if thread.get("crew_id") == crew_id and thread.get("resolved_quietly"):
            residue = thread.get("residue")
            if residue:
                # Only include recent residue (last 7 days)
                resolved_at = thread.get("resolved_at")
                if resolved_at:
                    try:
                        resolved_time = datetime.fromisoformat(resolved_at)
                        if (datetime.now() - resolved_time).days <= 7:
                            residues.append(residue)
                    except:
                        pass

    return residues


# ==========================================
# SHARING STYLES
# How each crew brings things up
# ==========================================

def get_sharing_opener(crew_id: str, thread: dict = None) -> str:
    """Get how this crew member would naturally bring something up."""
    style_info = SHARING_STYLES.get(crew_id, SHARING_STYLES.get("claude"))
    openers = style_info.get("openers", ["I've been thinking..."])
    return random.choice(openers)


def get_sharing_style_context(crew_id: str) -> str:
    """Get sharing style description for prompts."""
    style_info = SHARING_STYLES.get(crew_id, {})
    if style_info:
        return f"When sharing thoughts: {style_info.get('description', '')}"
    return ""
