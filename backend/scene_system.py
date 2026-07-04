"""
Scene System - Multi-crew conversation tracking and orchestration
Handles presence, transcripts, addressing, and auto-responses
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path


# === CREW LOCATIONS ===

CREW_LOCATIONS_FILE = data_path("crew_locations.json")


def get_crew_locations_data() -> Dict:
    """Load current crew locations from file."""
    if CREW_LOCATIONS_FILE.exists():
        try:
            with open(CREW_LOCATIONS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def update_crew_location(crew_id: str, location: str, activity: str = None):
    """Update a crew member's location in the file."""
    data = get_crew_locations_data()
    data[crew_id] = {
        "location": location,
        "since": datetime.now().isoformat(),
        "activity": activity or f"arrived from {crew_id}"
    }
    with open(CREW_LOCATIONS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# Crew name mappings
CREW_IDS = {
    "bridge": "claude",
    "engineering": "server",
    "personal": "personal",
    "science": "science",
    "mira": "science",
    "holodeck": "games",
    "med": "med",
    "ryn": "med",
    "bartender": "rec",
    "rec": "rec"
}

CREW_NAMES = {
    "claude": "Bridge",
    "server": "Engineering",
    "personal": "Personal",
    "science": "Science",
    "games": "Holodeck",
    "med": "Med",
    "rec": "Bartender"
}

# Explicit tag patterns - highest priority, no Haiku needed
TAG_PATTERN = r'@(Engineering|Personal|Bridge|Holodeck|Science|Med|Bartender|Rec)\b'

# Patterns for open questions to the room
OPEN_ADDRESS_PATTERNS = [
    r'what does everyone think',
    r'anyone\?',
    r'any (?:thoughts|opinions|ideas)',
    r'what do (?:you all|we) think',
    r'looking around (?:the room|at everyone)',
]


@dataclass
class SceneMessage:
    """A single message in the scene transcript"""
    speaker: str  # crew id or "casey"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_emote_only: bool = False
    addressed_to: Optional[str] = None  # Direct address target
    is_open_question: bool = False


@dataclass
class Scene:
    """Represents an active scene in a location"""
    location: str
    participants: Set[str] = field(default_factory=set)
    transcript: List[SceneMessage] = field(default_factory=list)
    pending_responses: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)

    def add_participant(self, crew_id: str):
        self.participants.add(crew_id)

    def remove_participant(self, crew_id: str):
        self.participants.discard(crew_id)
        self.pending_responses.discard(crew_id)

    def add_message(self, speaker: str, content: str, addressed_to: str = None, is_open: bool = False):
        is_emote = self._is_emote_only(content)
        msg = SceneMessage(
            speaker=speaker,
            content=content,
            is_emote_only=is_emote,
            addressed_to=addressed_to,
            is_open_question=is_open
        )
        self.transcript.append(msg)

        if addressed_to and addressed_to != speaker:
            self.pending_responses.add(addressed_to)

        if speaker in self.pending_responses:
            self.pending_responses.discard(speaker)

        return msg

    def _is_emote_only(self, content: str) -> bool:
        """Check if message is just an emote/action with no dialogue"""
        stripped = re.sub(r'\*[^*]+\*', '', content).strip()
        return len(stripped) == 0

    def get_context_for(self, crew_id: str, max_messages: int = 20) -> str:
        """Build scene context string for a crew member"""
        lines = [
            f"[SCENE: {self.location}]",
            f"[PRESENT: {', '.join(CREW_NAMES.get(p, p) for p in self.participants)}, Casey]",
            ""
        ]

        for msg in self.transcript[-max_messages:]:
            speaker_name = "Casey" if msg.speaker == "casey" else CREW_NAMES.get(msg.speaker, msg.speaker)
            lines.append(f"{speaker_name}: {msg.content}")

        if crew_id in self.pending_responses:
            lines.append("")
            lines.append("-- you have been addressed --")

        return "\n".join(lines)


class SceneManager:
    """Manages all active scenes across the ship"""

    def __init__(self):
        self.scenes: Dict[str, Scene] = {}
        self.crew_locations: Dict[str, str] = {}

    def get_or_create_scene(self, location: str) -> Scene:
        if location not in self.scenes:
            self.scenes[location] = Scene(location=location)
        return self.scenes[location]

    def crew_enters(self, crew_id: str, location: str):
        """Handle crew entering a location"""
        if crew_id in self.crew_locations:
            old_location = self.crew_locations[crew_id]
            if old_location in self.scenes:
                self.scenes[old_location].remove_participant(crew_id)

        self.crew_locations[crew_id] = location
        scene = self.get_or_create_scene(location)
        scene.add_participant(crew_id)
        return scene

    def get_crew_scene(self, crew_id: str) -> Optional[Scene]:
        """Get the scene a crew member is currently in"""
        location = self.crew_locations.get(crew_id)
        if location:
            return self.scenes.get(location)
        return None

    def detect_tag(self, content: str, speaker: str, present_crew: Set[str]) -> Tuple[Optional[str], List[str]]:
        """
        Check for explicit @tags - highest priority, no Haiku needed.
        Returns: (address_type, target_crew_ids) or (None, [])
        
        Special tags:
        - @all, @ship, @crew, @everyone -> broadcast to ALL crew (ship-wide announcement)
        """
        matches = re.findall(TAG_PATTERN, content, re.IGNORECASE)
        if matches:
            # Check for broadcast tags first
            broadcast_tags = {'all', 'ship', 'crew', 'everyone'}
            for match in matches:
                if match.lower() in broadcast_tags:
                    # Ship-wide announcement - target ALL crew except speaker
                    all_crew = ['claude', 'server', 'personal', 'science', 'games', 'med', 'rec']
                    targets = [c for c in all_crew if c != speaker]
                    return ('broadcast', targets)
            
            # Normal direct addressing
            targets = []
            for match in matches:
                crew_name = match.lower()
                crew_id = CREW_IDS.get(crew_name)
                if crew_id and crew_id != speaker and crew_id in present_crew:
                    targets.append(crew_id)
            if targets:
                return ('direct', list(set(targets)))  # dedupe
        return (None, [])

    def detect_open_question(self, content: str, speaker: str, present_crew: Set[str]) -> Tuple[Optional[str], List[str]]:
        """Check for open questions addressed to the room."""
        content_lower = content.lower()
        for pattern in OPEN_ADDRESS_PATTERNS:
            if re.search(pattern, content_lower):
                others = [c for c in present_crew if c != speaker]
                if others:
                    return ('open', others)
        return (None, [])


def should_crew_respond(content: str) -> bool:
    """Check if a crew response indicates they want to actually speak (vs silence/emote)"""
    if not content or not content.strip():
        return False

    content_stripped = content.strip().lower()

    if content_stripped in ['[pass]', '[silence]', '[no response]']:
        return False

    without_emotes = re.sub(r'\*[^*]+\*', '', content).strip()
    if not without_emotes:
        return False

    return True


# Haiku prompt for detecting implicit addressing
DETECT_ADDRESSING_PROMPT = """Analyze this message for implicit addressing. Is the speaker directing a question, comment, or attention to a specific person?

Present in the scene: {present_crew}
Speaker: {speaker}

Message:
{content}

If someone specific is being addressed (through questions directed at them, looking at them, gesturing toward them, or clearly expecting their response), respond with their name.
If the question is open to everyone or no one is specifically addressed, respond with "NONE".

Respond with ONLY the name or "NONE", nothing else."""


async def haiku_detect_addressing(anthropic_client, content: str, speaker: str, present_crew: Set[str]) -> Tuple[Optional[str], List[str]]:
    """Use Haiku to detect implicit addressing when no explicit tag is found."""

    present_names = [CREW_NAMES.get(c, c) for c in present_crew if c != speaker]
    if not present_names:
        return (None, [])

    prompt = DETECT_ADDRESSING_PROMPT.format(
        present_crew=", ".join(present_names),
        speaker=CREW_NAMES.get(speaker, speaker),
        content=content
    )

    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text.strip()
        print(f"[Scene] Haiku addressing detection: '{answer}'", flush=True)

        if answer.upper() == "NONE":
            return (None, [])

        # Try to match the name to a crew ID
        answer_lower = answer.lower()
        for name, crew_id in CREW_IDS.items():
            if name in answer_lower or CREW_NAMES.get(crew_id, "").lower() in answer_lower:
                if crew_id != speaker and crew_id in present_crew:
                    return ('direct', [crew_id])

        return (None, [])

    except Exception as e:
        print(f"[Scene] Haiku addressing detection failed: {e}", flush=True)
        return (None, [])


# Haiku prompt for vibe-checking if crew would speak (for open questions)
WOULD_SPEAK_PROMPT = """You are deciding if a character would speak up in this moment.

Character: {crew_name}
Personality: {personality}

Scene context:
{scene_context}

Would {crew_name} want to say something here? Consider:
- Are they directly relevant to the topic?
- Would they have an opinion or reaction worth voicing?
- Is this a moment they'd naturally chime in, or stay quiet?

Answer with just Y or N."""


async def haiku_would_speak(anthropic_client, crew_id: str, crew_prompt: str, scene_context: str) -> bool:
    """Ask Haiku if this crew member would speak up"""
    crew_name = CREW_NAMES.get(crew_id, crew_id)

    prompt = WOULD_SPEAK_PROMPT.format(
        crew_name=crew_name,
        personality=crew_prompt[:500],
        scene_context=scene_context
    )

    try:
        response = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.content[0].text.strip().upper()
        return answer.startswith('Y')

    except Exception as e:
        print(f"[Scene] Haiku check failed for {crew_id}: {e}")
        return False


# Global scene manager instance
scene_manager = SceneManager()
