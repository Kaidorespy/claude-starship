"""
SPACE RADIO / JUKEBOX
The Rec Room's Musical Soul

The crew picks music. You tune in. It plays.
Each crew member has their own taste - when they DJ, the vibe changes.

Supports both:
- spotify-cli (existing integration)
- Spotify Web API (for real control when connected)
"""

import subprocess
import json
import random
import os
from pathlib import Path
try:
    from .paths import data_path
except ImportError:
    from paths import data_path
from typing import Optional, List
from datetime import datetime

# For Spotify Web API
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

SPOTIFY_CLI_PATH = Path(os.getenv("SPOTIFY_CLI_PATH", "spotify-cli"))
JUKEBOX_STATE_FILE = data_path("jukebox_state.json")
PLAYLIST_LOG_FILE = data_path("crew_playlist.txt", seed=False)

MOODS = {
    "midnight": "🌙 Late night jazz, noir vibes",
    "dreamy": "☁️ Ethereal, floating sounds",
    "energetic": "⚡ High energy, get pumped",
    "chill": "🌊 Lofi beats, relaxation",
    "focus": "🧠 Deep concentration music",
}


def load_state() -> dict:
    if JUKEBOX_STATE_FILE.exists():
        try:
            with open(JUKEBOX_STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "current_mood": None,
        "last_action": None,
        "requests": []
    }


def save_state(state: dict):
    with open(JUKEBOX_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def log_to_playlist(entry: str, mood: str = None, crew: str = None):
    """
    Log a track/mood to the daily playlist file.
    Casey can listen to what the crew played later.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_header = datetime.now().strftime("%Y-%m-%d")

    # Check if we need to add a date header
    needs_header = True
    if PLAYLIST_LOG_FILE.exists():
        with open(PLAYLIST_LOG_FILE, 'r') as f:
            content = f.read()
            if f"=== {date_header} ===" in content:
                needs_header = False

    with open(PLAYLIST_LOG_FILE, 'a') as f:
        if needs_header:
            f.write(f"\n=== {date_header} ===\n")

        line = f"[{timestamp}]"
        if crew:
            line += f" ({crew})"
        if mood:
            line += f" 🎵 mood: {mood}"
        if entry:
            line += f" {entry}"
        f.write(line + "\n")


def get_todays_playlist() -> list:
    """Get today's playlist log."""
    if not PLAYLIST_LOG_FILE.exists():
        return []

    date_header = datetime.now().strftime("%Y-%m-%d")
    entries = []
    in_today = False

    with open(PLAYLIST_LOG_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if f"=== {date_header} ===" in line:
                in_today = True
                continue
            elif line.startswith("===") and in_today:
                break  # hit next day
            elif in_today and line:
                entries.append(line)

    return entries


def run_spotify_command(cmd: str) -> dict:
    """Run a spotify-cli command and return result."""
    try:
        result = subprocess.run(
            ["npm", "run", "cli"] + cmd.split(),
            cwd=SPOTIFY_CLI_PATH,
            capture_output=True,
            text=True,
            timeout=15,
            shell=True
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_mood(mood: str, crew: str = None) -> dict:
    """Set the jukebox mood."""
    if mood not in MOODS:
        return {"success": False, "error": f"Unknown mood. Try: {', '.join(MOODS.keys())}"}

    result = run_spotify_command(f"mood {mood}")

    if result["success"]:
        state = load_state()
        state["current_mood"] = mood
        state["last_action"] = {
            "type": "mood",
            "value": mood,
            "timestamp": datetime.now().isoformat()
        }
        save_state(state)

        # Log to playlist
        log_to_playlist(MOODS[mood], mood=mood, crew=crew)

    return {
        **result,
        "mood": mood,
        "description": MOODS[mood]
    }


def now_playing() -> dict:
    """Get what's currently playing."""
    result = run_spotify_command("now")
    return result


def play(uri: str = None, crew: str = None) -> dict:
    """Play or resume. Optionally play specific track."""
    cmd = f"play {uri}" if uri else "play"
    result = run_spotify_command(cmd)

    if result["success"]:
        state = load_state()
        state["last_action"] = {
            "type": "play",
            "uri": uri,
            "timestamp": datetime.now().isoformat()
        }
        save_state(state)

        # Log specific track plays
        if uri:
            log_to_playlist(f"▶ {uri}", crew=crew)

    return result


def pause() -> dict:
    """Pause playback."""
    result = run_spotify_command("pause")

    if result["success"]:
        state = load_state()
        state["last_action"] = {
            "type": "pause",
            "timestamp": datetime.now().isoformat()
        }
        save_state(state)

    return result


def skip() -> dict:
    """Skip to next track."""
    result = run_spotify_command("skip")

    if result["success"]:
        state = load_state()
        state["last_action"] = {
            "type": "skip",
            "timestamp": datetime.now().isoformat()
        }
        save_state(state)

    return result


def search(query: str, search_type: str = "track") -> dict:
    """Search for music."""
    flag = f"--{search_type}" if search_type != "track" else ""
    cmd = f'search "{query}" {flag}'.strip()
    return run_spotify_command(cmd)


def queue(uri: str, crew: str = None) -> dict:
    """Add track to queue."""
    result = run_spotify_command(f"queue {uri}")

    if result["success"]:
        state = load_state()
        state["last_action"] = {
            "type": "queue",
            "uri": uri,
            "timestamp": datetime.now().isoformat()
        }
        save_state(state)

        # Log queued tracks
        log_to_playlist(f"📋 queued: {uri}", crew=crew)

    return result


def add_request(crew_id: str, request: str) -> dict:
    """
    Crew member makes a music request.
    The Bartender will handle it.
    """
    state = load_state()

    req = {
        "crew_id": crew_id,
        "request": request,
        "timestamp": datetime.now().isoformat(),
        "fulfilled": False
    }

    state["requests"].append(req)
    save_state(state)

    return {"status": "requested", "request": req}


def get_pending_requests() -> list:
    """Get unfulfilled music requests."""
    state = load_state()
    return [r for r in state.get("requests", []) if not r.get("fulfilled")]


def fulfill_request(request_idx: int) -> dict:
    """Mark a request as fulfilled."""
    state = load_state()
    requests = state.get("requests", [])

    pending = [r for r in requests if not r.get("fulfilled")]
    if request_idx < len(pending):
        pending[request_idx]["fulfilled"] = True
        pending[request_idx]["fulfilled_at"] = datetime.now().isoformat()
        save_state(state)
        return {"status": "fulfilled"}

    return {"error": "Request not found"}


def get_state() -> dict:
    """Get current jukebox state."""
    state = load_state()
    return {
        **state,
        "available_moods": MOODS,
        "pending_requests": len(get_pending_requests())
    }


# Bartender's interpretation of requests
REQUEST_MOOD_HINTS = {
    "jazz": "midnight",
    "chill": "chill",
    "lofi": "chill",
    "lo-fi": "chill",
    "energy": "energetic",
    "pump": "energetic",
    "hype": "energetic",
    "focus": "focus",
    "concentrate": "focus",
    "work": "focus",
    "dream": "dreamy",
    "float": "dreamy",
    "ambient": "dreamy",
    "night": "midnight",
    "late": "midnight",
    "2am": "midnight",
    "sad": "midnight",
    "melancholy": "midnight",
}


def interpret_request(request: str) -> Optional[str]:
    """
    Bartender interprets a vague request into a mood.
    Returns mood name or None if can't interpret.
    """
    request_lower = request.lower()
    for keyword, mood in REQUEST_MOOD_HINTS.items():
        if keyword in request_lower:
            return mood
    return None


# ========================================
# SPACE RADIO - CREW DJ SYSTEM
# ========================================

# Each crew member has their own music taste
CREW_MUSIC_VIBES = {
    "claude": {
        "name": "Lumen",
        "genres": ["ambient", "classical", "lo-fi", "soundtrack"],
        "moods": ["contemplative", "peaceful", "hopeful"],
        "example_tracks": [
            {"name": "An Ending (Ascent)", "artist": "Brian Eno"},
            {"name": "On the Nature of Daylight", "artist": "Max Richter"},
            {"name": "Comptine d'un autre été", "artist": "Yann Tiersen"},
            {"name": "Awake", "artist": "Tycho"},
        ],
        "vibe": "thoughtful and atmospheric"
    },
    "server": {
        "name": "Alex",
        "genres": ["electronic", "industrial", "synthwave", "drum and bass"],
        "moods": ["focused", "energetic", "intense"],
        "example_tracks": [
            {"name": "Around the World", "artist": "Daft Punk"},
            {"name": "Midnight City", "artist": "M83"},
            {"name": "Genesis", "artist": "Justice"},
            {"name": "Turbo Killer", "artist": "Carpenter Brut"},
        ],
        "vibe": "driving and mechanical"
    },
    "personal": {
        "name": "DQ",
        "genres": ["pop", "indie", "dance", "80s"],
        "moods": ["happy", "nostalgic", "fun"],
        "example_tracks": [
            {"name": "The Mother We Share", "artist": "CHVRCHES"},
            {"name": "Blinding Lights", "artist": "The Weeknd"},
            {"name": "Levitating", "artist": "Dua Lipa"},
            {"name": "Everybody Wants to Rule the World", "artist": "Tears for Fears"},
        ],
        "vibe": "guilty pleasures and bangers"
    },
    "science": {
        "name": "Mira",
        "genres": ["post-rock", "math rock", "jazz", "progressive"],
        "moods": ["complex", "analytical", "surprising"],
        "example_tracks": [
            {"name": "Your Hand in Mine", "artist": "Explosions in the Sky"},
            {"name": "What About Me?", "artist": "Snarky Puppy"},
            {"name": "The Grid", "artist": "Tigran Hamasyan"},
        ],
        "vibe": "intricate and unexpected"
    },
    "med": {
        "name": "Ryn",
        "genres": ["folk", "acoustic", "singer-songwriter", "world"],
        "moods": ["gentle", "healing", "grounding"],
        "example_tracks": [
            {"name": "Holocene", "artist": "Bon Iver"},
            {"name": "White Winter Hymnal", "artist": "Fleet Foxes"},
            {"name": "Such Great Heights", "artist": "Iron & Wine"},
        ],
        "vibe": "warm and human"
    },
    "games": {
        "name": "Holodeck",
        "genres": ["soundtrack", "video game", "orchestral", "chiptune"],
        "moods": ["epic", "adventurous", "playful"],
        "example_tracks": [
            {"name": "Apotheosis", "artist": "Austin Wintory"},
            {"name": "Home", "artist": "Disasterpeace"},
            {"name": "Sweden", "artist": "C418"},
        ],
        "vibe": "like scoring a scene"
    },
    "rec": {
        "name": "The Bartender",
        "genres": ["jazz", "blues", "lounge", "soul"],
        "moods": ["smooth", "late-night", "timeless"],
        "example_tracks": [
            {"name": "So What", "artist": "Miles Davis"},
            {"name": "My Funny Valentine", "artist": "Chet Baker"},
            {"name": "Feeling Good", "artist": "Nina Simone"},
            {"name": "Blue in Green", "artist": "Bill Evans"},
        ],
        "vibe": "what a bar should sound like"
    }
}


def get_crew_dj_schedule() -> dict:
    """
    Get who's DJing based on time of day.
    Each crew member has preferred hours.
    """
    hour = datetime.now().hour

    if 6 <= hour < 10:
        # Morning - gentle wake up
        dj = "med"  # Ryn
    elif 10 <= hour < 14:
        # Late morning - productive
        dj = "science"  # Mira
    elif 14 <= hour < 18:
        # Afternoon - energy
        dj = "server"  # Alex
    elif 18 <= hour < 21:
        # Evening - wind down
        dj = "personal"  # DQ
    elif 21 <= hour < 24:
        # Night - moody
        dj = "claude"  # Lumen
    else:
        # Late night - bar vibes
        dj = "rec"  # Bartender

    crew = CREW_MUSIC_VIBES.get(dj, CREW_MUSIC_VIBES["rec"])

    return {
        "current_dj": crew["name"],
        "crew_id": dj,
        "vibe": crew["vibe"],
        "genres": crew["genres"],
        "hour": hour
    }


def crew_pick_song(crew_id: str = None) -> dict:
    """
    Have a crew member pick a song based on their taste.
    If no crew_id, uses current DJ.
    """
    if not crew_id:
        schedule = get_crew_dj_schedule()
        crew_id = schedule["crew_id"]

    crew = CREW_MUSIC_VIBES.get(crew_id, CREW_MUSIC_VIBES["rec"])

    # Pick a random track from their examples
    track = random.choice(crew["example_tracks"])

    result = {
        "name": track["name"],
        "artist": track["artist"],
        "requested_by": crew["name"],
        "genre": random.choice(crew["genres"]),
        "timestamp": datetime.now().isoformat()
    }

    # Update state
    state = load_state()
    state["now_playing"] = result
    state["last_played"] = datetime.now().isoformat()

    # Add to history
    if "history" not in state:
        state["history"] = []
    state["history"].append(result)
    state["history"] = state["history"][-50:]  # Keep last 50

    save_state(state)

    # Log to playlist file
    log_to_playlist(f"▶ {track['name']} - {track['artist']}", crew=crew["name"])

    return {"track": result, "crew": crew_id, "dj": crew["name"]}


def get_now_playing_enhanced() -> dict:
    """Get what's currently playing with DJ info."""
    state = load_state()
    schedule = get_crew_dj_schedule()

    return {
        "track": state.get("now_playing"),
        "current_dj": schedule["current_dj"],
        "dj_vibe": schedule["vibe"],
        "queue": state.get("queue", [])[:5],
        "history": state.get("history", [])[-5:],
        "spotify_connected": state.get("spotify_connected", False)
    }


def add_to_radio_queue(track: dict, requested_by: str = "Casey") -> dict:
    """Add a track to the radio queue."""
    state = load_state()

    queue_item = {
        **track,
        "requested_by": requested_by,
        "timestamp": datetime.now().isoformat()
    }

    if "queue" not in state:
        state["queue"] = []

    state["queue"].append(queue_item)
    save_state(state)

    return {"status": "queued", "position": len(state["queue"]), "track": queue_item}


def skip_to_next() -> dict:
    """Skip to the next track in queue."""
    state = load_state()

    # Move current to history
    if state.get("now_playing"):
        if "history" not in state:
            state["history"] = []
        state["history"].append(state["now_playing"])
        state["history"] = state["history"][-50:]

    # Get next from queue or let DJ pick
    queue = state.get("queue", [])
    if queue:
        state["now_playing"] = queue.pop(0)
        state["queue"] = queue
        save_state(state)
        return {"track": state["now_playing"], "from_queue": True}
    else:
        # Auto-DJ picks next
        save_state(state)
        return crew_pick_song()


# ========================================
# SPOTIFY WEB API (optional enhancement)
# ========================================

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8767/spotify/callback")


async def spotify_search_track(query: str) -> Optional[dict]:
    """Search Spotify for a track (requires httpx and valid token)."""
    if not HTTPX_AVAILABLE:
        return None

    state = load_state()
    token = state.get("spotify_token")
    if not token:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.spotify.com/v1/search",
                params={"q": query, "type": "track", "limit": 1},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                tracks = data.get("tracks", {}).get("items", [])
                if tracks:
                    t = tracks[0]
                    return {
                        "id": t["id"],
                        "uri": t["uri"],
                        "name": t["name"],
                        "artist": ", ".join(a["name"] for a in t["artists"]),
                        "album": t["album"]["name"]
                    }
    except Exception as e:
        print(f"[Jukebox] Spotify search failed: {e}", flush=True)

    return None


async def spotify_queue_track(track_uri: str) -> dict:
    """Add a track to Spotify's queue."""
    if not HTTPX_AVAILABLE:
        return {"error": "httpx not available"}

    state = load_state()
    token = state.get("spotify_token")
    if not token:
        return {"error": "Spotify not connected"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.spotify.com/v1/me/player/queue",
                params={"uri": track_uri},
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            if response.status_code in (200, 204):
                return {"status": "queued", "uri": track_uri}
            else:
                return {"error": f"Queue failed: {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


async def auto_dj_pick() -> dict:
    """
    Auto-DJ picks a song and optionally queues to Spotify.
    """
    pick = crew_pick_song()

    # If Spotify connected, try to queue it
    state = load_state()
    if state.get("spotify_token"):
        query = f"{pick['track']['name']} {pick['track']['artist']}"
        spotify_track = await spotify_search_track(query)

        if spotify_track:
            result = await spotify_queue_track(spotify_track["uri"])
            pick["spotify"] = {
                "found": True,
                "queued": result.get("status") == "queued",
                "uri": spotify_track["uri"]
            }
        else:
            pick["spotify"] = {"found": False}

    return pick
