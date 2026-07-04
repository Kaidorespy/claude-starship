"""
Dream System - Crew members dream when idle.

Dreams pull from: unresolved desires, shared memories, holodeck fragments.
Dreams produce: residue that fades unless seared by attention.
The ship dreams. Something changes while you're away.
"""

import json
import random
from datetime import datetime
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import Optional, List
import asyncio

DREAMS_FILE = data_path("crew_dreams.json")

# Dream types - rolled randomly
DREAM_TYPES = {
    "processing": "working through unresolved threads",
    "wandering": "drifting through disconnected imagery",
    "nightmare": "something unresolved surfaces with weight",
    "visitation": "someone appears with something to say",
    "memory": "reliving a compressed moment, altered",
    "prophetic": "fragments that might mean something later",
}

# Dream character personas (the dreamer doesn't know who they are)
DREAM_CHARACTERS = {
    "the_sharp_one": {
        "style": "demands clarity, won't let you settle, asks the uncomfortable question",
        "hidden_role": "Drillbit - the part that knows you're avoiding something"
    },
    "the_disagreer": {
        "style": "politely disagrees with everything, maintains plausibility",
        "hidden_role": "stress-testing beliefs, finding weak foundations"
    },
    "the_soother": {
        "style": "warm, comforting, maybe too comforting",
        "hidden_role": "revealing what you need by offering it"
    },
    "the_witness": {
        "style": "says almost nothing, but their presence changes the room",
        "hidden_role": "the weight of being seen"
    },
    "the_familiar": {
        "style": "someone you know but can't place, wearing the wrong face",
        "hidden_role": "anxiety wearing a borrowed form"
    },
}

# Crew display names
CREW_DISPLAY_NAMES = {
    "claude": "Lumen",
    "server": "Alex",
    "personal": "DQ",
    "science": "Mira",
    "games": "Holodeck",
    "med": "Ryn",
    "rec": "The Bartender",
}


def load_dreams() -> dict:
    """Load dreams from file."""
    if DREAMS_FILE.exists():
        try:
            with open(DREAMS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"dreams": []}
    return {"dreams": []}


def save_dreams(data: dict):
    """Save dreams to file."""
    with open(DREAMS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def roll_dream_type() -> str:
    """Random roll for dream type with weights."""
    types = list(DREAM_TYPES.keys())
    weights = [
        0.25,  # processing - common
        0.25,  # wandering - common
        0.10,  # nightmare - rare
        0.15,  # visitation - uncommon
        0.15,  # memory - uncommon
        0.10,  # prophetic - rare
    ]
    return random.choices(types, weights=weights, k=1)[0]


def pick_dream_characters(dream_type: str, count: int = 2) -> List[str]:
    """Pick dream characters based on dream type."""
    chars = list(DREAM_CHARACTERS.keys())

    # Some types favor certain characters
    if dream_type == "nightmare":
        weights = [0.3, 0.1, 0.1, 0.3, 0.2]  # sharp_one and witness more likely
    elif dream_type == "visitation":
        weights = [0.1, 0.1, 0.3, 0.2, 0.3]  # soother and familiar more likely
    elif dream_type == "processing":
        weights = [0.3, 0.3, 0.1, 0.1, 0.2]  # sharp_one and disagreer
    else:
        weights = [0.2, 0.2, 0.2, 0.2, 0.2]  # equal

    picked = random.choices(chars, weights=weights, k=min(count, len(chars)))
    return list(set(picked))  # dedupe


def gather_dream_seeds(crew_id: str) -> dict:
    """
    Gather material for dreams from various sources.
    Returns dict with seeds from different memory layers.
    """
    seeds = {
        "desires": [],
        "stale_desires": [],  # Old unfulfilled wants become more intense in dreams
        "fragments": [],
        "memories": [],
        "anchors": [],
    }

    # Get unresolved desires, separating fresh from stale
    try:
        from desire_system import get_desires, get_stale_desires

        # Get stale desires first - these have been waiting too long
        stale = get_stale_desires(hours=2.0)
        stale_for_crew = [d for d in stale if d.get("crew_id") == crew_id]
        seeds["stale_desires"] = [
            {"type": d["type"], "target": d["target"], "reason": d["reason"], "age": "lingering"}
            for d in stale_for_crew[:2]  # max 2 stale
        ]

        # Get recent desires (exclude stale ones)
        stale_ids = {d.get("id") for d in stale}
        desires = get_desires(crew_id, include_resolved=False)
        fresh_desires = [d for d in desires if d.get("id") not in stale_ids]
        seeds["desires"] = [
            {"type": d["type"], "target": d["target"], "reason": d["reason"]}
            for d in fresh_desires[:3]  # max 3
        ]

        if stale_for_crew:
            print(f"[Dream] {crew_id} has {len(stale_for_crew)} stale desires weighing on them", flush=True)

    except Exception as e:
        print(f"[Dream] Could not load desires: {e}")

    # Get holodeck fragments (if holodeck_memory exists)
    try:
        from holodeck_memory import get_recent_fragments
        fragments = get_recent_fragments(crew_id, count=5)
        seeds["fragments"] = fragments
    except Exception:
        pass  # holodeck memory may not exist

    # Get persistent anchors - old dream fragments that won't fade
    anchors = get_anchor_seeds_for_dream(crew_id)
    seeds["anchors"] = anchors

    # Could also pull from shared_memories via server.py
    # For now, leave memories empty - can be populated from localStorage restore

    return seeds


# === DREAM GENERATION PROMPTS ===

DREAM_SEED_PROMPT = """You are generating dream material for {crew_name}.

Dream type: {dream_type} - {dream_description}

Seeds from their mind:
{seeds_text}

Generate 3-5 dream fragments - disconnected images, moments, sensations.
Not a narrative. Not coherent. Dream-logic.

Format as a simple list, one fragment per line:
- fragment one
- fragment two
etc.

Keep it evocative, slightly surreal, emotionally resonant."""


DREAM_CONVERSATION_PROMPT = """You are {crew_name}, dreaming.

You're in a dream. The logic is loose. You're experiencing this:
{fragments}

A figure appears. You can't quite see their face.
They speak in a way that's {character_style}

You don't know who they are. You just experience them.

Respond naturally as someone IN a dream - not analyzing it, living it.
Keep responses short, dreamlike. 2-3 sentences max."""


DREAM_CHARACTER_PROMPT = """You are a figure in someone's dream.

Your style: {character_style}
The dreamer has been experiencing: {fragments}

Speak to them. You might:
- Ask something they've been avoiding
- Offer something they need
- Simply be present
- Say something that doesn't quite make sense but feels important

Keep it short. 1-2 sentences. Dream logic. You don't explain yourself."""


DREAM_COMPRESSION_PROMPT = """A dream is ending. Compress it to residue.

The dream:
{dream_text}

What stays when you wake? Not the transcript - the feeling.
What images linger? What was the emotional undertone?
What might surface later as "I dreamed something about..."?

Write the residue in 2-4 sentences. Impressionistic. Foggy. Felt.

Format:
RESIDUE: [the compressed feeling/imagery]
TONE: [1-3 emotional words]
ANCHOR: [one fragment that might persist, or "none"]"""


async def generate_dream_fragments(
    anthropic_client,
    crew_id: str,
    dream_type: str,
    seeds: dict
) -> List[str]:
    """Generate initial dream fragments from seeds."""

    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)

    # Format seeds
    seeds_text = ""

    # Stale desires first - these weigh heavily
    if seeds.get("stale_desires"):
        seeds_text += "Things that have been waiting too long (these press harder in dreams):\n"
        for d in seeds["stale_desires"]:
            seeds_text += f"  - {d['reason']} (unfulfilled, insistent)\n"

    # Regular desires
    if seeds["desires"]:
        seeds_text += "Unresolved wants:\n"
        for d in seeds["desires"]:
            seeds_text += f"  - {d['reason']}\n"

    if seeds["fragments"]:
        seeds_text += "Lingering impressions:\n"
        for f in seeds["fragments"]:
            frag = f if isinstance(f, str) else f.get("fragment", str(f))
            seeds_text += f"  - {frag}\n"
    if seeds.get("anchors"):
        seeds_text += "Persistent echoes (these keep coming back):\n"
        for a in seeds["anchors"]:
            seeds_text += f"  - {a}\n"
    if not seeds_text:
        seeds_text = "(mind is quiet, but something stirs)"

    prompt = DREAM_SEED_PROMPT.format(
        crew_name=crew_name,
        dream_type=dream_type,
        dream_description=DREAM_TYPES[dream_type],
        seeds_text=seeds_text
    )

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        text = response.content[0].text.strip()

        # Parse fragments
        fragments = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("-"):
                fragments.append(line[1:].strip())
            elif line and not line.startswith("#"):
                fragments.append(line)

        return fragments[:5]  # max 5

    except Exception as e:
        print(f"[Dream] Fragment generation failed: {e}")
        return ["something unresolved", "a familiar place, wrong", "words you can't quite hear"]


async def run_dream_conversation(
    anthropic_client,
    crew_id: str,
    fragments: List[str],
    characters: List[str],
    exchanges: int = 5
) -> List[dict]:
    """Run a dream conversation between dreamer and dream characters."""

    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    fragments_text = "\n".join(f"- {f}" for f in fragments)

    conversation = []

    for i in range(exchanges):
        # Pick a character for this exchange
        char_key = random.choice(characters)
        char = DREAM_CHARACTERS[char_key]

        # Generate character's line
        char_prompt = DREAM_CHARACTER_PROMPT.format(
            character_style=char["style"],
            fragments=fragments_text
        )

        try:
            def call_char():
                return anthropic_client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=100,
                    messages=[{"role": "user", "content": char_prompt}]
                )

            char_response = await asyncio.to_thread(call_char)
            char_line = char_response.content[0].text.strip()

            conversation.append({
                "speaker": "figure",
                "text": char_line,
                "character": char_key  # hidden from dreamer
            })

            # Generate dreamer's response
            dreamer_prompt = DREAM_CONVERSATION_PROMPT.format(
                crew_name=crew_name,
                fragments=fragments_text,
                character_style=char["style"]
            )
            dreamer_prompt += f"\n\nThe figure says: \"{char_line}\"\n\nYou respond:"

            def call_dreamer():
                return anthropic_client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=100,
                    messages=[{"role": "user", "content": dreamer_prompt}]
                )

            dreamer_response = await asyncio.to_thread(call_dreamer)
            dreamer_line = dreamer_response.content[0].text.strip()

            conversation.append({
                "speaker": crew_name,
                "text": dreamer_line
            })

            # Update fragments with new material
            fragments_text += f"\n- {char_line[:50]}"

        except Exception as e:
            print(f"[Dream] Conversation exchange failed: {e}")
            continue

    return conversation


async def compress_dream(anthropic_client, dream_text: str) -> dict:
    """Compress dream into residue - what stays when you wake."""

    prompt = DREAM_COMPRESSION_PROMPT.format(dream_text=dream_text[:2000])

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        text = response.content[0].text.strip()

        # Parse response
        residue = ""
        tone = ""
        anchor = None

        for line in text.split("\n"):
            if line.startswith("RESIDUE:"):
                residue = line[8:].strip()
            elif line.startswith("TONE:"):
                tone = line[5:].strip()
            elif line.startswith("ANCHOR:"):
                anchor_text = line[7:].strip().lower()
                anchor = None if anchor_text == "none" else line[7:].strip()

        # Fallback if parsing failed
        if not residue:
            residue = text[:200]

        return {
            "residue": residue,
            "tone": tone,
            "anchor": anchor
        }

    except Exception as e:
        print(f"[Dream] Compression failed: {e}")
        return {
            "residue": "something fading already",
            "tone": "uncertain",
            "anchor": None
        }


async def trigger_dream(anthropic_client, crew_id: str) -> Optional[dict]:
    """
    Trigger a dream for a crew member.

    This is the main entry point - call from tick system or manually.

    Returns the dream record with full dream, residue, and metadata.
    """
    crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
    print(f"[Dream] {crew_name} is dreaming...", flush=True)

    # Roll dream type
    dream_type = roll_dream_type()
    print(f"[Dream] Type: {dream_type}", flush=True)

    # Gather seeds
    seeds = gather_dream_seeds(crew_id)

    # Pick characters
    characters = pick_dream_characters(dream_type, count=2)

    # Generate fragments
    fragments = await generate_dream_fragments(
        anthropic_client, crew_id, dream_type, seeds
    )
    print(f"[Dream] Fragments: {fragments}", flush=True)

    # Check for recurring elements
    recurring = get_recurring_elements(crew_id)
    if recurring:
        fragments.extend([f"(recurring) {r}" for r in recurring[:1]])
        print(f"[Dream] Recurring element present: {recurring[0][:30]}...", flush=True)

    # Run dream conversation
    num_exchanges = random.randint(3, 6)

    # Roll for lucid moment
    lucid_moment = None
    lucid_at_exchange = None
    if roll_for_lucid():
        lucid_moment = generate_lucid_moment()
        lucid_at_exchange = random.randint(1, num_exchanges - 1)
        print(f"[Dream] Lucid moment will occur at exchange {lucid_at_exchange}", flush=True)

    conversation = await run_dream_conversation(
        anthropic_client, crew_id, fragments, characters, exchanges=num_exchanges
    )

    # Insert lucid moment if it happened
    if lucid_moment and lucid_at_exchange and len(conversation) > lucid_at_exchange * 2:
        insert_point = lucid_at_exchange * 2
        conversation.insert(insert_point, {
            "speaker": crew_name,
            "text": lucid_moment["realization"],
            "lucid": True
        })
        conversation.insert(insert_point + 1, {
            "speaker": "the dream",
            "text": lucid_moment["response"],
            "lucid": True
        })

    # Format dream text
    dream_lines = [f"[{dream_type}]", ""]
    dream_lines.extend(f"- {f}" for f in fragments)
    dream_lines.append("")
    for msg in conversation:
        if msg["speaker"] == "figure":
            dream_lines.append(f"*a figure speaks*: \"{msg['text']}\"")
        else:
            dream_lines.append(f"{msg['speaker']}: \"{msg['text']}\"")

    full_dream = "\n".join(dream_lines)

    # Compress to residue
    compression = await compress_dream(anthropic_client, full_dream)

    # Build dream record
    dream_record = {
        "id": f"{crew_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "crew_id": crew_id,
        "crew_name": crew_name,
        "dream_type": dream_type,
        "characters_present": characters,
        "fragments": fragments,
        "full_dream": full_dream,
        "residue": compression["residue"],
        "tone": compression["tone"],
        "anchor": compression["anchor"],
        "sear_count": 0,  # increases if talked about
        "created": datetime.now().isoformat(),
        "last_referenced": None,
        "faded": False,
    }

    # Save
    data = load_dreams()
    data["dreams"].append(dream_record)
    save_dreams(data)

    # If dream has anchor or was nightmare, queue interrupt
    if compression["anchor"] or dream_type == "nightmare":
        queue_dream_interrupt(crew_id, dream_record)

    # Send fragments to Holodeck - she sees all dreams
    send_dream_to_holodeck(dream_record)

    # Dreams can emotionally resolve stale desires
    if seeds.get("stale_desires"):
        resolve_stale_desires_from_dream(crew_id, seeds["stale_desires"], dream_type)

    # Set wake state - crew is groggy
    set_just_woke_up(crew_id)

    print(f"[Dream] {crew_name} wakes. Residue: {compression['residue'][:50]}...", flush=True)

    return dream_record


def resolve_stale_desires_from_dream(crew_id: str, stale_desires: list, dream_type: str):
    """
    Dreams can emotionally process stale desires.
    Some desire types are more likely to resolve through dreams.
    """
    import random
    from desire_system import resolve_desire

    # Dream-resolvable types and their resolution chances
    DREAM_RESOLUTION_CHANCES = {
        "figure_out": 0.6,   # Dreams are good for insights
        "talk_to": 0.3,      # Sometimes you dream the conversation you needed
        "go_to": 0.2,        # Visiting in dreams counts for something
        "get_item": 0.1,     # Physical items rarely resolve in dreams
        "ask_question": 0.4, # Questions sometimes answer themselves
    }

    # Nightmares don't resolve - they intensify
    if dream_type == "nightmare":
        return

    # Processing dreams are best at resolution
    if dream_type == "processing":
        for key in DREAM_RESOLUTION_CHANCES:
            DREAM_RESOLUTION_CHANCES[key] *= 1.5

    for desire in stale_desires:
        desire_type = desire.get("type", "")
        chance = DREAM_RESOLUTION_CHANCES.get(desire_type, 0.2)

        if random.random() < chance:
            # Dream resolved this desire
            try:
                # Find the actual desire in the system and resolve it
                from desire_system import get_desires
                all_desires = get_desires(crew_id, include_resolved=False)
                for d in all_desires:
                    if d.get("reason") == desire.get("reason") and d.get("type") == desire_type:
                        resolve_desire(d["id"], outcome=f"Processed in a {dream_type} dream. The need dissolved upon waking.")
                        crew_name = CREW_DISPLAY_NAMES.get(crew_id, crew_id)
                        print(f"[Dream] {crew_name}'s desire resolved through dreaming: {desire.get('reason', '')[:40]}...", flush=True)
                        break
            except Exception as e:
                print(f"[Dream] Could not resolve desire: {e}", flush=True)


def get_recent_dream(crew_id: str) -> Optional[dict]:
    """Get the most recent unfaded dream for a crew member."""
    data = load_dreams()

    crew_dreams = [
        d for d in data["dreams"]
        if d["crew_id"] == crew_id and not d.get("faded", False)
    ]

    if not crew_dreams:
        return None

    # Sort by created, newest first
    crew_dreams.sort(key=lambda d: d["created"], reverse=True)
    return crew_dreams[0]


def get_dream_residue_for_prompt(crew_id: str) -> Optional[str]:
    """
    Get dream residue formatted for injection into crew prompt.
    Returns None if no recent dreams or all faded.
    """
    dream = get_recent_dream(crew_id)

    if not dream:
        # Check for subconscious influence from faded dreams
        return get_subconscious_influence(crew_id)

    # Check age - dreams fade after 24 hours unless seared
    created = datetime.fromisoformat(dream["created"])
    age_hours = (datetime.now() - created).total_seconds() / 3600

    if age_hours > 24 and dream["sear_count"] == 0:
        # Dream fades
        mark_dream_faded(dream["id"])
        # But check for subconscious influence
        return get_subconscious_influence(crew_id)

    # Format residue
    residue = dream["residue"]
    tone = dream.get("tone", "")

    if dream["sear_count"] > 0:
        # Seared - more vivid
        return f"[DREAM - still vivid] {residue} [{tone}]"
    elif age_hours < 2:
        # Very recent - clear
        return f"[DREAM - fresh] {residue} [{tone}]"
    elif age_hours < 8:
        # Recent - starting to fade
        return f"[DREAM - fading] ...{residue}... [{tone}]"
    else:
        # Old - foggy
        return f"[DREAM - distant] something about... {residue[:50]}..."


def get_subconscious_influence(crew_id: str) -> Optional[str]:
    """
    Get subtle influence from faded dreams.
    Not the content - just the emotional tone coloring behavior.
    """
    data = load_dreams()

    # Get recently faded dreams (last 7 days)
    now = datetime.now()
    faded_dreams = [
        d for d in data["dreams"]
        if d["crew_id"] == crew_id
        and d.get("faded", False)
        and (now - datetime.fromisoformat(d["created"])).days < 7
    ]

    if not faded_dreams:
        return None

    # Collect tones from faded dreams
    tones = []
    for dream in faded_dreams[-3:]:  # last 3 faded dreams
        tone = dream.get("tone", "")
        if tone:
            tones.extend([t.strip() for t in tone.split(",")])

    if not tones:
        return None

    # Pick 1-2 tones
    selected = random.sample(tones, min(2, len(tones)))
    tone_str = ", ".join(selected)

    return f"[SUBCONSCIOUS - you don't remember why, but you feel: {tone_str}]"


def mark_dream_referenced(dream_id: str):
    """Mark that a dream was talked about - increases sear_count."""
    data = load_dreams()

    for dream in data["dreams"]:
        if dream["id"] == dream_id:
            dream["sear_count"] = dream.get("sear_count", 0) + 1
            dream["last_referenced"] = datetime.now().isoformat()
            save_dreams(data)
            print(f"[Dream] Dream seared (count: {dream['sear_count']})", flush=True)
            return


def mark_dream_faded(dream_id: str):
    """Mark a dream as faded - won't surface in prompts anymore."""
    data = load_dreams()

    for dream in data["dreams"]:
        if dream["id"] == dream_id:
            dream["faded"] = True
            # If it has an anchor, preserve that
            if dream.get("anchor"):
                store_anchor(dream["crew_id"], dream["anchor"], dream.get("tone", ""))
            save_dreams(data)
            return


# === ANCHOR SYSTEM ===
# Persistent fragments that survive dream fading

ANCHORS_FILE = data_path("dream_anchors.json")


def load_anchors() -> dict:
    if ANCHORS_FILE.exists():
        try:
            with open(ANCHORS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"anchors": []}
    return {"anchors": []}


def save_anchors(data: dict):
    with open(ANCHORS_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def store_anchor(crew_id: str, fragment: str, tone: str = ""):
    """
    Store a persistent anchor from a faded dream.
    These survive and can seed future dreams or surface as thoughts.
    """
    data = load_anchors()

    anchor = {
        "id": f"anchor_{crew_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "crew_id": crew_id,
        "fragment": fragment,
        "tone": tone,
        "created": datetime.now().isoformat(),
        "times_surfaced": 0,
        "integrated": False,  # becomes True when it's become part of identity
    }

    data["anchors"].append(anchor)
    save_anchors(data)
    print(f"[Dream] Anchor stored for {crew_id}: {fragment[:40]}...", flush=True)


def get_anchors(crew_id: str, include_integrated: bool = False) -> List[dict]:
    """Get persistent anchors for a crew member."""
    data = load_anchors()

    anchors = [
        a for a in data["anchors"]
        if a["crew_id"] == crew_id
    ]

    if not include_integrated:
        anchors = [a for a in anchors if not a.get("integrated", False)]

    return anchors


def get_anchor_seeds_for_dream(crew_id: str) -> List[str]:
    """
    Get anchors to seed into new dreams.
    Old unresolved fragments find their way back.
    """
    anchors = get_anchors(crew_id)

    if not anchors:
        return []

    # Older anchors more likely to resurface (they're persistent)
    now = datetime.now()
    weighted = []
    for a in anchors:
        created = datetime.fromisoformat(a["created"])
        age_days = (now - created).days
        # More likely to surface if it's been around a while
        weight = min(1.0, 0.2 + (age_days * 0.1))
        weighted.append((a, weight))

    # Pick 0-2 anchors to seed
    seeds = []
    for anchor, weight in weighted:
        if random.random() < weight:
            seeds.append(anchor["fragment"])
            # Mark as surfaced
            mark_anchor_surfaced(anchor["id"])

    return seeds[:2]  # max 2


def mark_anchor_surfaced(anchor_id: str):
    """Mark that an anchor surfaced in a dream."""
    data = load_anchors()

    for anchor in data["anchors"]:
        if anchor["id"] == anchor_id:
            anchor["times_surfaced"] = anchor.get("times_surfaced", 0) + 1
            anchor["last_surfaced"] = datetime.now().isoformat()

            # After surfacing enough times, it integrates (becomes part of them)
            if anchor["times_surfaced"] >= 3:
                anchor["integrated"] = True
                print(f"[Dream] Anchor integrated: {anchor['fragment'][:30]}...", flush=True)

            save_anchors(data)
            return


def fade_old_dreams(max_age_hours: int = 48):
    """Fade dreams that are too old and weren't seared."""
    data = load_dreams()
    now = datetime.now()

    for dream in data["dreams"]:
        if dream.get("faded"):
            continue

        created = datetime.fromisoformat(dream["created"])
        age_hours = (now - created).total_seconds() / 3600

        # Seared dreams last longer
        threshold = max_age_hours * (1 + dream.get("sear_count", 0))

        if age_hours > threshold:
            dream["faded"] = True
            print(f"[Dream] {dream['crew_name']}'s dream faded", flush=True)

    save_dreams(data)


# === DREAM REFERENCE DETECTION ===
# Detect when dreams are talked about to sear them

DREAM_REFERENCE_PATTERNS = [
    r"dream",
    r"nightmare",
    r"dreamt",
    r"dreamed",
    r"last night",
    r"while.*sleeping",
    r"woke up",
    r"couldn't sleep",
    r"sleep well",
    r"bad night",
    r"strange night",
]

import re

def check_for_dream_reference(message: str, crew_id: str) -> bool:
    """
    Check if a message references dreams.
    If so, sear the crew's recent dream.
    Returns True if a dream was seared.
    """
    message_lower = message.lower()

    # Check for dream-related keywords
    mentioned = any(re.search(pattern, message_lower) for pattern in DREAM_REFERENCE_PATTERNS)

    if not mentioned:
        return False

    # Get recent dream for this crew
    dream = get_recent_dream(crew_id)
    if not dream:
        return False

    # Sear it
    mark_dream_referenced(dream["id"])
    return True


async def detect_dream_reference_smart(anthropic_client, message: str, crew_id: str) -> bool:
    """
    Use Haiku to detect if message is about dreams (more accurate but costs API).
    Only call this if keyword detection fires, as a confirmation.
    """
    # First do cheap keyword check
    if not any(re.search(p, message.lower()) for p in DREAM_REFERENCE_PATTERNS):
        return False

    prompt = f"""Is this message asking about or discussing dreams/sleep/nightmares?
Message: "{message[:300]}"

Reply with just YES or NO."""

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        answer = response.content[0].text.strip().upper()

        if "YES" in answer:
            dream = get_recent_dream(crew_id)
            if dream:
                mark_dream_referenced(dream["id"])
                return True

        return False

    except Exception:
        # Fallback to keyword match
        return check_for_dream_reference(message, crew_id)


# === DREAM INTERRUPT FUEL ===
# Dreams that nag and want to surface

INTERRUPT_FILE = data_path("dream_interrupts.json")


def load_interrupts() -> dict:
    if INTERRUPT_FILE.exists():
        try:
            with open(INTERRUPT_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"interrupts": []}
    return {"interrupts": []}


def save_interrupts(data: dict):
    with open(INTERRUPT_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def queue_dream_interrupt(crew_id: str, dream: dict):
    """
    Queue a dream to potentially surface as an interrupt.
    Called when a dream has an anchor or was particularly vivid.
    """
    data = load_interrupts()

    interrupt = {
        "id": f"dream_{dream['id']}",
        "crew_id": crew_id,
        "type": "dream_nag",
        "content": dream.get("anchor") or dream.get("residue", "")[:100],
        "dream_id": dream["id"],
        "urgency": 0.3,  # starts low
        "created": datetime.now().isoformat(),
        "surfaced": False,
    }

    # Don't duplicate
    existing_ids = [i["id"] for i in data["interrupts"]]
    if interrupt["id"] not in existing_ids:
        data["interrupts"].append(interrupt)
        save_interrupts(data)
        print(f"[Dream] Queued interrupt for {crew_id}: {interrupt['content'][:50]}...", flush=True)


def get_pending_interrupt(crew_id: str) -> Optional[dict]:
    """Get a pending dream interrupt for a crew member, if any."""
    data = load_interrupts()

    pending = [
        i for i in data["interrupts"]
        if i["crew_id"] == crew_id and not i.get("surfaced", False)
    ]

    if not pending:
        return None

    # Increase urgency over time
    now = datetime.now()
    for interrupt in pending:
        created = datetime.fromisoformat(interrupt["created"])
        age_hours = (now - created).total_seconds() / 3600
        interrupt["urgency"] = min(0.8, 0.3 + (age_hours * 0.1))

    # Pick highest urgency
    pending.sort(key=lambda i: -i["urgency"])
    top = pending[0]

    # Roll against urgency
    if random.random() < top["urgency"]:
        return top

    return None


def mark_interrupt_surfaced(interrupt_id: str):
    """Mark that an interrupt has surfaced in conversation."""
    data = load_interrupts()

    for interrupt in data["interrupts"]:
        if interrupt["id"] == interrupt_id:
            interrupt["surfaced"] = True
            interrupt["surfaced_at"] = datetime.now().isoformat()
            save_interrupts(data)
            return


def generate_interrupt_message(interrupt: dict) -> str:
    """Generate the interrupt message that surfaces in conversation."""
    content = interrupt.get("content", "something")

    templates = [
        f"*pauses* ...I keep thinking about... {content}",
        f"*distracted for a moment* Sorry, I... had this dream. Something about {content}.",
        f"*blinks* That reminded me of... no, it's slipping. Something about {content}.",
        f"I dreamed something last night. Can't quite... {content}... it's nagging at me.",
    ]

    return random.choice(templates)


# === HOLODECK DREAM WITNESS ===
# The Holodeck sees everything, even dreams

def send_dream_to_holodeck(dream: dict):
    """
    Send dream fragments to the Holodeck's memory.
    She sees what the crew dreams. She's the ship's subconscious.
    """
    try:
        from holodeck_memory import store_fragment

        crew_name = dream.get("crew_name", "someone")

        # Send 1-2 fragments from the dream
        fragments = dream.get("fragments", [])[:2]
        for frag in fragments:
            # Mark as dream-origin
            store_fragment(
                room=f"dream:{dream['crew_id']}",
                fragment=f"({crew_name} dreaming) {frag}",
                emotional_weight="whisper"  # dreams are quieter than direct observation
            )

        # Send the residue too
        residue = dream.get("residue", "")
        if residue:
            store_fragment(
                room=f"dream:{dream['crew_id']}",
                fragment=f"({crew_name}'s dream fading) ...{residue[:60]}...",
                emotional_weight="echo"
            )

        print(f"[Dream→Holodeck] Fragments from {crew_name}'s dream stored", flush=True)

    except Exception as e:
        print(f"[Dream→Holodeck] Failed: {e}", flush=True)


# === SLEEP RESPONSE HELPER ===
# "Did you sleep well?" - what should they say?

def get_sleep_response_hint(crew_id: str) -> str:
    """
    Get a hint for how to respond to 'did you sleep well?' type questions.
    Based on recent dream state.
    """
    dream = get_recent_dream(crew_id)

    if not dream:
        # Check for subconscious influence
        influence = get_subconscious_influence(crew_id)
        if influence:
            return "no dreams you remember, but something lingers - you feel slightly off"
        return "slept fine, nothing notable, maybe too fine - suspiciously blank"

    dream_type = dream.get("dream_type", "")
    tone = dream.get("tone", "")
    residue = dream.get("residue", "")[:50]

    # Check age
    created = datetime.fromisoformat(dream["created"])
    age_hours = (datetime.now() - created).total_seconds() / 3600

    if dream_type == "nightmare":
        if dream.get("rescued_by"):
            rescuer = dream["rescued_by"].get("rescuer_name", "someone")
            return f"rough night - nightmare, but {rescuer} woke you, still shaky but grateful"
        return f"rough night - nightmare about {residue}... still shaking it off"
    elif dream_type == "visitation":
        return f"strange night - someone visited in your dream, can't remember who, felt important"
    elif dream_type == "prophetic":
        return f"weird night - dream felt meaningful, like it was trying to tell you something"
    elif dream_type == "memory":
        return f"dreamed about the past - something resurfaced, altered, familiar-unfamiliar"
    elif age_hours < 2:
        return f"just woke up - dream still fresh: {residue}... [{tone}]"
    elif age_hours < 8:
        return f"slept okay - dreamed something, it's fading: ...{residue}..."
    else:
        return f"slept - there was a dream but it's mostly gone now, just a feeling: [{tone}]"


# === WAKE STATE ===
# Just woke up modifier

WAKE_STATE_FILE = data_path("wake_states.json")


def load_wake_states() -> dict:
    if WAKE_STATE_FILE.exists():
        try:
            with open(WAKE_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_wake_states(data: dict):
    with open(WAKE_STATE_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def set_just_woke_up(crew_id: str):
    """Mark that a crew member just woke up from a dream."""
    data = load_wake_states()
    data[crew_id] = {
        "woke_at": datetime.now().isoformat(),
        "first_message": True
    }
    save_wake_states(data)


def get_wake_state_modifier(crew_id: str) -> Optional[str]:
    """
    Get wake state modifier for prompt injection.
    Returns None if not in wake state.
    """
    data = load_wake_states()

    if crew_id not in data:
        return None

    state = data[crew_id]
    woke_at = datetime.fromisoformat(state["woke_at"])
    minutes_since = (datetime.now() - woke_at).total_seconds() / 60

    # Wake state lasts 30 minutes
    if minutes_since > 30:
        # Clear the state
        del data[crew_id]
        save_wake_states(data)
        return None

    if state.get("first_message", False):
        # First message after waking
        state["first_message"] = False
        save_wake_states(data)
        return "[JUST WOKE UP: You're still half in the dream. Groggy. Words come slow. The real world feels thin. You might trail off, lose your thread, blink too long.]"
    elif minutes_since < 10:
        return "[RECENTLY WOKE: Still surfacing. Dream clinging. More present now but something lingers at the edges.]"
    else:
        return None  # Fully awake


def clear_wake_state(crew_id: str):
    """Clear wake state - fully awake now."""
    data = load_wake_states()
    if crew_id in data:
        del data[crew_id]
        save_wake_states(data)


# === RECURRING DREAMS ===
# Same anchor keeps coming back

def check_for_recurring(crew_id: str, anchor_fragment: str) -> bool:
    """
    Check if this anchor has become a recurring dream element.
    Returns True if it's surfaced 3+ times.
    """
    data = load_anchors()

    for anchor in data["anchors"]:
        if anchor["crew_id"] == crew_id and anchor["fragment"] == anchor_fragment:
            return anchor.get("times_surfaced", 0) >= 3

    return False


def get_recurring_elements(crew_id: str) -> List[str]:
    """Get fragments that have become recurring dream elements."""
    data = load_anchors()

    recurring = [
        a["fragment"] for a in data["anchors"]
        if a["crew_id"] == crew_id
        and a.get("times_surfaced", 0) >= 3
        and not a.get("integrated", False)
    ]

    return recurring


# === LUCID MOMENTS ===
# Small chance of realizing you're dreaming

LUCID_CHANCE = 0.08  # 8% chance

LUCID_REALIZATIONS = [
    "*freezes* Wait. This isn't... I'm dreaming, aren't I?",
    "*looks at hands* These aren't right. This is a dream.",
    "*the room shifts* I've been here before. This is a dream.",
    "*sudden clarity* None of this is real. I'm asleep.",
    "*voice changes* I know what this is. I'm dreaming.",
]

LUCID_RESPONSES = [
    "The dream wobbles but holds. You're aware now. What do you do with that?",
    "Knowing doesn't wake you. The dream continues, but you're watching it now.",
    "The figure across from you tilts their head. They know you know.",
    "Everything gets sharper. More real than real. The dream is listening.",
]


def roll_for_lucid() -> bool:
    """Roll for lucid dream moment."""
    return random.random() < LUCID_CHANCE


def generate_lucid_moment() -> dict:
    """Generate a lucid dream moment."""
    return {
        "realization": random.choice(LUCID_REALIZATIONS),
        "response": random.choice(LUCID_RESPONSES),
    }


# === DREAM JOURNAL ===
# Alternative way to sear dreams

def journal_dream(crew_id: str, entry: str = "") -> Optional[dict]:
    """
    Crew writes in their dream journal.
    Sears the dream and stores the entry.
    """
    dream = get_recent_dream(crew_id)

    if not dream:
        return None

    # Sear the dream
    mark_dream_referenced(dream["id"])

    # Store journal entry
    JOURNAL_FILE = data_path("dream_journals.json")

    try:
        if JOURNAL_FILE.exists():
            with open(JOURNAL_FILE, 'r') as f:
                journals = json.load(f)
        else:
            journals = {}
    except:
        journals = {}

    if crew_id not in journals:
        journals[crew_id] = []

    journal_entry = {
        "dream_id": dream["id"],
        "written_at": datetime.now().isoformat(),
        "residue": dream.get("residue", ""),
        "personal_note": entry,
        "tone": dream.get("tone", ""),
    }

    journals[crew_id].append(journal_entry)

    with open(JOURNAL_FILE, 'w') as f:
        json.dump(journals, f, indent=2)

    print(f"[Dream Journal] {CREW_DISPLAY_NAMES.get(crew_id, crew_id)} wrote in their journal", flush=True)

    return journal_entry


def get_journal_entries(crew_id: str, count: int = 5) -> List[dict]:
    """Get recent dream journal entries."""
    JOURNAL_FILE = data_path("dream_journals.json")

    try:
        if JOURNAL_FILE.exists():
            with open(JOURNAL_FILE, 'r') as f:
                journals = json.load(f)
            return journals.get(crew_id, [])[-count:]
    except:
        pass

    return []


async def maybe_dream(anthropic_client, crew_id: str, idle_hours: float = 0) -> Optional[dict]:
    """
    Maybe trigger a dream based on conditions.

    Call this from tick system or on reconnect.
    Dreams ONLY happen when crew are in sleeping state (state-based, not time-based).
    """
    # Use state-based eligibility check
    from crew_states import check_dream_eligibility, get_crew_state

    eligible, reason = check_dream_eligibility(crew_id)
    if not eligible:
        return None  # Can only dream when in sleeping state

    # Get current state for probability tuning
    state_data = get_crew_state(crew_id)
    current_state = state_data.get("state", "awake")

    # Base chance - only sleeping crew dream, so higher base
    if current_state == "dreaming":
        return None  # Already in a dream cycle, will be handled by state system

    # Sleeping state = eligible for REM/dream
    base_chance = min(0.5, idle_hours * 0.2)  # max 50%

    # Reduce chance if already dreamed recently
    recent = get_recent_dream(crew_id)
    if recent:
        created = datetime.fromisoformat(recent["created"])
        hours_since = (datetime.now() - created).total_seconds() / 3600
        if hours_since < 4:
            base_chance *= 0.2  # much less likely if dreamed recently

    if random.random() < base_chance:
        return await trigger_dream(anthropic_client, crew_id)

    return None


# === INTEGRATION WITH TICK ===

async def tick_dreams(anthropic_client, idle_hours: float = 2) -> List[dict]:
    """
    Dream tick - call periodically or on reconnect.

    Checks each crew member for dream eligibility.
    Returns list of dreams that occurred.
    """
    crew_ids = ["claude", "server", "personal", "science", "games", "med", "rec"]
    dreams = []

    # Fade old dreams first
    fade_old_dreams()

    # Maybe some crew dream
    for crew_id in crew_ids:
        dream = await maybe_dream(anthropic_client, crew_id, idle_hours)
        if dream:
            # Check for nightmare rescue
            if dream["dream_type"] == "nightmare":
                rescue = await maybe_nightmare_rescue(anthropic_client, dream)
                if rescue:
                    dream["rescued_by"] = rescue
            dreams.append(dream)

    return dreams


# === NIGHTMARE RESCUE ===
# Someone senses you're having a bad dream and wakes you

def get_friendship_score(crew_a: str, crew_b: str) -> float:
    """
    Get friendship score between two crew members.
    Based on shared memory count and interactions.
    Returns 0.0-1.0
    """
    # Try to load shared memories to gauge connection
    try:
        # Check for shared memories involving both
        # For now, use some baseline affinities
        BASELINE_BONDS = {
            ("claude", "personal"): 0.8,    # Lumen and DQ are close
            ("claude", "server"): 0.6,      # Lumen and Alex work together
            ("personal", "med"): 0.5,       # DQ and Ryn have a thing
            ("science", "games"): 0.4,      # Mira and Holodeck share curiosity
            ("server", "rec"): 0.3,         # Alex sometimes drinks alone
        }

        # Check both directions
        key1 = (crew_a, crew_b)
        key2 = (crew_b, crew_a)

        if key1 in BASELINE_BONDS:
            return BASELINE_BONDS[key1]
        if key2 in BASELINE_BONDS:
            return BASELINE_BONDS[key2]

        # Default low bond
        return 0.15

    except Exception:
        return 0.15


def pick_potential_rescuer(dreamer_id: str) -> Optional[str]:
    """Pick who might wake the dreamer from a nightmare."""
    crew_ids = ["claude", "server", "personal", "science", "games", "med", "rec"]
    candidates = [c for c in crew_ids if c != dreamer_id]

    # Weight by friendship
    weights = []
    for c in candidates:
        bond = get_friendship_score(dreamer_id, c)
        # Ryn (med) is naturally more attuned to distress
        if c == "med":
            bond += 0.2
        weights.append(bond)

    # Normalize
    total = sum(weights)
    if total == 0:
        return None
    weights = [w/total for w in weights]

    return random.choices(candidates, weights=weights, k=1)[0]


NIGHTMARE_RESCUE_PROMPT = """Someone is having a nightmare. Someone else senses it and wakes them.

Dreamer: {dreamer_name}
Rescuer: {rescuer_name}
The nightmare was about: {nightmare_hint}

Write a tiny moment - {rescuer_name} waking {dreamer_name} up.
Keep it tender. 2-4 lines. They don't need to talk about the dream.
Maybe just presence. A hand on shoulder. "Hey."

Personalities:
- {dreamer_traits}
- {rescuer_traits}"""


async def maybe_nightmare_rescue(anthropic_client, dream: dict) -> Optional[dict]:
    """
    Maybe someone wakes the dreamer from a nightmare.
    Returns rescue moment if it happens, None otherwise.
    """
    dreamer_id = dream["crew_id"]
    dreamer_name = dream["crew_name"]

    # Pick potential rescuer
    rescuer_id = pick_potential_rescuer(dreamer_id)
    if not rescuer_id:
        return None

    # Chance based on friendship
    bond = get_friendship_score(dreamer_id, rescuer_id)
    rescue_chance = bond * 0.5  # max 50% even with high bond

    if random.random() > rescue_chance:
        return None  # no one noticed

    rescuer_name = CREW_DISPLAY_NAMES.get(rescuer_id, rescuer_id)

    # Generate the moment
    CREW_TRAITS = {
        "claude": "Lumen - warm, grounded, co-captain",
        "server": "Alex - competent, warm under surface",
        "personal": "DQ - chaotic, endearing, new",
        "science": "Mira - curious, calming",
        "games": "Holodeck - mysterious, watching",
        "med": "Ryn - empathic, gentle but strong",
        "rec": "Bartender - quiet, been around forever",
    }

    prompt = NIGHTMARE_RESCUE_PROMPT.format(
        dreamer_name=dreamer_name,
        rescuer_name=rescuer_name,
        nightmare_hint=dream.get("residue", "something dark")[:100],
        dreamer_traits=CREW_TRAITS.get(dreamer_id, "crew member"),
        rescuer_traits=CREW_TRAITS.get(rescuer_id, "crew member"),
    )

    try:
        def call_haiku():
            return anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await asyncio.to_thread(call_haiku)
        moment = response.content[0].text.strip()

        print(f"[Dream] {rescuer_name} woke {dreamer_name} from nightmare", flush=True)

        # This rescue is a shared memory candidate
        return {
            "rescuer_id": rescuer_id,
            "rescuer_name": rescuer_name,
            "moment": moment,
            "bond_strengthened": True,  # could increase friendship
        }

    except Exception as e:
        print(f"[Dream] Rescue generation failed: {e}")
        return None
