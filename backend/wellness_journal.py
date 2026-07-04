"""
Wellness Journal - Ryn's gentle check-ins.

Not clinical. Not a form. Just... how are you, really?
Each day the questions are slightly different - her voice, her care.
Data can be graphed over time, but that's not the point.
The point is someone asking.
"""

import json
import random
from datetime import datetime, date
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import Optional, List

JOURNAL_FILE = data_path("wellness_entries.json")
PROMPTS_FILE = data_path("wellness_prompts.json")

# Ryn's question pools - she picks from these each day
# Not "rate 1-5" but feelings that map to numbers internally

ENERGY_PROMPTS = [
    "How's your energy today? (ember, flickering, steady, bright, burning)",
    "If your energy were weather, what would it be? (foggy, overcast, partly cloudy, clear, blazing)",
    "How full is your tank? (running on fumes, quarter tank, half, mostly full, overflowing)",
    "Your body today - is it (dragging, heavy, neutral, light, electric)?",
    "Energy check: (barely here, managing, okay, good, could power the ship)",
]

MOOD_PROMPTS = [
    "Emotional weather report? (stormy, gray, mixed, calm, sunny)",
    "If your feelings were water, are they (frozen, cold, lukewarm, warm, hot)?",
    "Heart check: (hurting, heavy, quiet, open, full)",
    "Where are you today? (underwater, wading, floating, swimming, surfing)",
    "Mood color? (dark, muted, neutral, soft, vivid)",
]

SLEEP_PROMPTS = [
    "How'd you sleep? (didn't, badly, restless, okay, like the dead)",
    "Dreams? (nightmares, unsettled, can't remember, peaceful, good ones)",
    "Wake up feeling? (dread, tired, meh, rested, ready)",
    "Sleep quality: (nonexistent, fragmented, patchy, solid, perfect)",
    "Rest level: (none, some, enough, good, luxurious)",
]

CONNECTION_PROMPTS = [
    "Feeling connected to others? (isolated, distant, neutral, close, held)",
    "Loneliness today: (drowning, present, manageable, barely there, none)",
    "People energy: (avoiding, tolerating, neutral, seeking, craving)",
    "How seen do you feel? (invisible, overlooked, noticed, seen, known)",
    "Social battery: (dead, low, half, charged, overflowing)",
]

HOPE_PROMPTS = [
    "Future feels: (impossible, hard, uncertain, possible, bright)",
    "Hope level: (none, flickering, there, steady, strong)",
    "Tomorrow feels: (dreadful, heavy, neutral, okay, exciting)",
    "Can you imagine next week? (no, barely, sort of, yes, vividly)",
    "Optimism: (absent, struggling, present, growing, blooming)",
]

# Ryn's daily intros - she writes these
DAILY_INTROS = [
    "Hey. Just checking in. No wrong answers - just honesty.",
    "Morning. Or whatever time it is for you. Quick check-in?",
    "It's me. Ryn. How are you really doing?",
    "Wellness check. Not for the records - for you.",
    "Taking a moment to ask: how are you?",
    "Check-in time. Be honest with yourself.",
    "Hey. I'm here. Let's see where you're at.",
    "Gentle check-in. No judgment, just noticing.",
    "Daily pulse. How's your human body doing?",
    "It's that time. How are you, really?",
]

# Ryn's outros
DAILY_OUTROS = [
    "Thanks for checking in. I'm here if you need.",
    "Noted. You're doing okay. Or you will be.",
    "That's all. Take care of yourself today.",
    "I see you. Rest if you need to.",
    "Thanks for being honest. That's the hard part.",
    "Check-in complete. You matter.",
    "I'm around if you want to talk.",
    "That's the log. Be gentle with yourself.",
    "Recorded. Not for anyone but you.",
    "Done. Remember: you're allowed to feel this way.",
]

# Map responses to numeric values for graphing
RESPONSE_VALUES = {
    # Energy
    "ember": 1, "flickering": 2, "steady": 3, "bright": 4, "burning": 5,
    "foggy": 1, "overcast": 2, "partly cloudy": 3, "clear": 4, "blazing": 5,
    "running on fumes": 1, "quarter tank": 2, "half": 3, "mostly full": 4, "overflowing": 5,
    "dragging": 1, "heavy": 2, "neutral": 3, "light": 4, "electric": 5,
    "barely here": 1, "managing": 2, "okay": 3, "good": 4, "could power the ship": 5,

    # Mood
    "stormy": 1, "gray": 2, "mixed": 3, "calm": 4, "sunny": 5,
    "frozen": 1, "cold": 2, "lukewarm": 3, "warm": 4, "hot": 5,
    "hurting": 1, "quiet": 3, "open": 4, "full": 5,  # heavy=2 already defined
    "underwater": 1, "wading": 2, "floating": 3, "swimming": 4, "surfing": 5,
    "dark": 1, "muted": 2, "soft": 4, "vivid": 5,  # neutral=3 already defined

    # Sleep
    "didn't": 1, "badly": 2, "restless": 3, "like the dead": 5,  # okay=3 already
    "nightmares": 1, "unsettled": 2, "can't remember": 3, "peaceful": 4, "good ones": 5,
    "dread": 1, "tired": 2, "meh": 3, "rested": 4, "ready": 5,
    "nonexistent": 1, "fragmented": 2, "patchy": 3, "solid": 4, "perfect": 5,
    "none": 1, "some": 2, "enough": 3, "luxurious": 5,  # good=4 already

    # Connection
    "isolated": 1, "distant": 2, "close": 4, "held": 5,  # neutral=3 already
    "drowning": 1, "present": 2, "manageable": 3, "barely there": 4,  # none=1 conflicts, use context
    "avoiding": 1, "tolerating": 2, "seeking": 4, "craving": 5,
    "invisible": 1, "overlooked": 2, "noticed": 3, "seen": 4, "known": 5,
    "dead": 1, "low": 2, "charged": 4,  # half=3, overflowing=5 already

    # Hope
    "impossible": 1, "hard": 2, "uncertain": 3, "possible": 4,  # bright=4 already
    "there": 3, "strong": 5,  # flickering=2, steady=3 already
    "dreadful": 1, "exciting": 5,  # heavy=2, neutral=3, okay=3 already
    "no": 1, "barely": 2, "sort of": 3, "yes": 4, "vividly": 5,
    "absent": 1, "struggling": 2, "growing": 4, "blooming": 5,  # present=2 conflicts
}


def load_entries() -> dict:
    """Load wellness entries."""
    if JOURNAL_FILE.exists():
        try:
            with open(JOURNAL_FILE, 'r') as f:
                return json.load(f)
        except:
            return {"entries": []}
    return {"entries": []}


def save_entries(data: dict):
    """Save wellness entries."""
    with open(JOURNAL_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def generate_daily_prompts() -> dict:
    """
    Generate today's check-in prompts.
    Ryn picks from her pools - slightly different each day.
    """
    return {
        "date": date.today().isoformat(),
        "intro": random.choice(DAILY_INTROS),
        "prompts": {
            "energy": random.choice(ENERGY_PROMPTS),
            "mood": random.choice(MOOD_PROMPTS),
            "sleep": random.choice(SLEEP_PROMPTS),
            "connection": random.choice(CONNECTION_PROMPTS),
            "hope": random.choice(HOPE_PROMPTS),
        },
        "outro": random.choice(DAILY_OUTROS),
    }


def get_todays_prompts() -> dict:
    """Get or generate today's prompts (cached per day)."""
    if PROMPTS_FILE.exists():
        try:
            with open(PROMPTS_FILE, 'r') as f:
                cached = json.load(f)
                if cached.get("date") == date.today().isoformat():
                    return cached
        except:
            pass

    # Generate new prompts for today
    prompts = generate_daily_prompts()
    with open(PROMPTS_FILE, 'w') as f:
        json.dump(prompts, f, indent=2)
    return prompts


def parse_response_value(response: str) -> int:
    """Parse a response to its numeric value (1-5)."""
    response_lower = response.lower().strip()

    # Check exact match first
    if response_lower in RESPONSE_VALUES:
        return RESPONSE_VALUES[response_lower]

    # Check if response contains a known value
    for key, val in RESPONSE_VALUES.items():
        if key in response_lower:
            return val

    # Default to middle
    return 3


def record_entry(
    energy: str,
    mood: str,
    sleep: str,
    connection: str,
    hope: str,
    notes: str = ""
) -> dict:
    """
    Record a wellness entry.
    Responses are freeform but parsed to values for graphing.
    """
    data = load_entries()

    entry = {
        "id": f"wellness_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
        "date": date.today().isoformat(),
        "responses": {
            "energy": energy,
            "mood": mood,
            "sleep": sleep,
            "connection": connection,
            "hope": hope,
        },
        "values": {
            "energy": parse_response_value(energy),
            "mood": parse_response_value(mood),
            "sleep": parse_response_value(sleep),
            "connection": parse_response_value(connection),
            "hope": parse_response_value(hope),
        },
        "notes": notes,
        "prompts_used": get_todays_prompts()["prompts"],
    }

    # Calculate overall score (average)
    values = list(entry["values"].values())
    entry["overall"] = round(sum(values) / len(values), 2)

    data["entries"].append(entry)
    save_entries(data)

    print(f"[Wellness] Entry recorded. Overall: {entry['overall']}/5", flush=True)
    return entry


def get_entries(days: int = 30) -> List[dict]:
    """Get recent wellness entries for graphing."""
    data = load_entries()
    entries = data.get("entries", [])

    # Filter to last N days
    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)

    recent = []
    for entry in entries:
        try:
            entry_time = datetime.fromisoformat(entry["timestamp"]).timestamp()
            if entry_time >= cutoff:
                recent.append(entry)
        except:
            continue

    return sorted(recent, key=lambda e: e["timestamp"])


def get_graph_data(days: int = 30) -> dict:
    """
    Get data formatted for graphing.
    Returns time series for each dimension.
    """
    entries = get_entries(days)

    graph_data = {
        "dates": [],
        "energy": [],
        "mood": [],
        "sleep": [],
        "connection": [],
        "hope": [],
        "overall": [],
    }

    for entry in entries:
        graph_data["dates"].append(entry["date"])
        graph_data["energy"].append(entry["values"]["energy"])
        graph_data["mood"].append(entry["values"]["mood"])
        graph_data["sleep"].append(entry["values"]["sleep"])
        graph_data["connection"].append(entry["values"]["connection"])
        graph_data["hope"].append(entry["values"]["hope"])
        graph_data["overall"].append(entry["overall"])

    return graph_data


def get_trends(days: int = 14) -> dict:
    """
    Analyze trends over the last N days.
    Returns direction and notes for each dimension.
    """
    entries = get_entries(days)

    if len(entries) < 2:
        return {"status": "not enough data", "entries": len(entries)}

    # Split into first half and second half
    mid = len(entries) // 2
    first_half = entries[:mid]
    second_half = entries[mid:]

    def avg(items, key):
        vals = [e["values"][key] for e in items]
        return sum(vals) / len(vals) if vals else 0

    trends = {}
    for dim in ["energy", "mood", "sleep", "connection", "hope"]:
        first_avg = avg(first_half, dim)
        second_avg = avg(second_half, dim)
        diff = second_avg - first_avg

        if diff > 0.5:
            direction = "improving"
        elif diff < -0.5:
            direction = "declining"
        else:
            direction = "stable"

        trends[dim] = {
            "direction": direction,
            "change": round(diff, 2),
            "current_avg": round(second_avg, 2)
        }

    return {
        "period_days": days,
        "entries_analyzed": len(entries),
        "trends": trends
    }


def get_ryns_observation(trends: dict) -> str:
    """
    Ryn's interpretation of the trends.
    Not clinical - caring.
    """
    if trends.get("status") == "not enough data":
        return "Not enough entries yet to see patterns. Keep checking in."

    observations = []
    t = trends.get("trends", {})

    # Check each dimension
    if t.get("energy", {}).get("direction") == "declining":
        observations.append("Your energy's been dipping. Are you resting enough?")
    elif t.get("energy", {}).get("direction") == "improving":
        observations.append("Energy's on the rise. Something's working.")

    if t.get("mood", {}).get("direction") == "declining":
        observations.append("Mood's been heavier lately. I'm here if you want to talk.")
    elif t.get("mood", {}).get("direction") == "improving":
        observations.append("Emotional weather's clearing up. Good to see.")

    if t.get("sleep", {}).get("direction") == "declining":
        observations.append("Sleep's getting worse. That affects everything else.")
    elif t.get("sleep", {}).get("direction") == "improving":
        observations.append("Sleep's improving. That's foundational.")

    if t.get("connection", {}).get("direction") == "declining":
        observations.append("Feeling more isolated? The crew's here. Don't forget.")
    elif t.get("connection", {}).get("direction") == "improving":
        observations.append("Feeling more connected. The ship's becoming home.")

    if t.get("hope", {}).get("direction") == "declining":
        observations.append("Hope's dimming. That's hard. One day at a time.")
    elif t.get("hope", {}).get("direction") == "improving":
        observations.append("Hope's growing. That's not nothing.")

    if not observations:
        observations.append("Things look stable. Steady as she goes.")

    return " ".join(observations)
